from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import numpy as np


@dataclass
class Trade:
    symbol: str
    entry_time: datetime
    entry_price: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    position_size: float = 0
    pnl: Optional[float] = None
    sentiment: str = ""
    stop_loss: Optional[float] = None

    def calculate_pnl(self):
        if self.exit_price and self.entry_price and self.position_size:
            self.pnl = (self.exit_price - self.entry_price) * self.position_size
        return self.pnl


class PerformanceTracker:
    def __init__(self):
        self.trades: List[Trade] = []
        self.current_positions: Dict[str, Trade] = {}
        
    def record_entry(self, symbol: str, price: float, size: float, sentiment: str, stop_loss: Optional[float] = None):
        trade = Trade(
            symbol=symbol,
            entry_time=datetime.now(),
            entry_price=price,
            position_size=size,
            sentiment=sentiment,
            stop_loss=stop_loss
        )
        self.current_positions[symbol] = trade
        self.trades.append(trade)
        
    def record_exit(self, symbol: str, price: float):
        if symbol in self.current_positions:
            trade = self.current_positions[symbol]
            trade.exit_time = datetime.now()
            trade.exit_price = price
            trade.calculate_pnl()
            del self.current_positions[symbol]
            
    def get_performance_metrics(self):
        closed_trades = [t for t in self.trades if t.exit_price is not None]
        if not closed_trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0
            }
            
        pnls = [t.pnl for t in closed_trades if t.pnl is not None]
        winning_trades = len([p for p in pnls if p > 0])
        
        returns = pd.Series(pnls)
        cumulative_returns = (1 + returns).cumprod()
        rolling_max = cumulative_returns.expanding(min_periods=1).max()
        drawdowns = (cumulative_returns - rolling_max) / rolling_max
        
        return {
            'total_trades': len(closed_trades),
            'win_rate': winning_trades / len(closed_trades) if closed_trades else 0,
            'total_pnl': sum(pnls),
            'sharpe_ratio': self._calculate_sharpe_ratio(returns),
            'max_drawdown': abs(drawdowns.min()) if not drawdowns.empty else 0
        }
    
    def get_trade_history(self) -> pd.DataFrame:
        data = []
        for trade in self.trades:
            data.append({
                'symbol': trade.symbol,
                'entry_time': trade.entry_time,
                'entry_price': trade.entry_price,
                'exit_time': trade.exit_time,
                'exit_price': trade.exit_price,
                'position_size': trade.position_size,
                'pnl': trade.pnl,
                'sentiment': trade.sentiment,
                'stop_loss': trade.stop_loss
            })
        return pd.DataFrame(data)
    
    def get_current_positions(self) -> pd.DataFrame:
        data = []
        for symbol, trade in self.current_positions.items():
            data.append({
                'symbol': symbol,
                'entry_time': trade.entry_time,
                'entry_price': trade.entry_price,
                'position_size': trade.position_size,
                'current_pnl': 0,  # This should be updated with current price
                'stop_loss': trade.stop_loss
            })
        return pd.DataFrame(data)
    
    def _calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        if returns.empty:
            return 0
        excess_returns = returns - risk_free_rate/252  # Daily risk-free rate
        if excess_returns.std() == 0:
            return 0
        return np.sqrt(252) * excess_returns.mean() / excess_returns.std()