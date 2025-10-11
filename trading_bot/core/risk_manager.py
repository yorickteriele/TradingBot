from dataclasses import dataclass
from typing import Dict, Optional
import numpy as np
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.client import TradingClient


@dataclass
class RiskParameters:
    max_position_size: float = 0.1
    max_portfolio_risk: float = 0.02
    stop_loss_atr_multiplier: float = 2.0
    position_sizing_atr_multiplier: float = 1.0
    max_correlation_threshold: float = 0.7


class RiskManager:
    def __init__(self, trading_client: TradingClient, risk_params: Optional[RiskParameters] = None):
        self.trading_client = trading_client
        self.risk_params = risk_params or RiskParameters()
        self._position_cache = {}
        self._volatility_cache = {}

    def calculate_position_size(self, symbol: str, account_value: float, volatility: float) -> float:
        risk_amount = account_value * self.risk_params.max_portfolio_risk
        price = float(self.trading_client.get_latest_trade(symbol).price)
        position_size = (risk_amount / (volatility * self.risk_params.position_sizing_atr_multiplier))
        max_position = account_value * self.risk_params.max_position_size
        
        return min(position_size, max_position) / price

    def calculate_stop_loss(self, symbol: str, side: OrderSide, entry_price: float, volatility: float) -> float:
        atr_distance = volatility * self.risk_params.stop_loss_atr_multiplier
        if side == OrderSide.BUY:
            return entry_price - atr_distance
        return entry_price + atr_distance

    def check_portfolio_correlation(self, symbol: str, portfolio: Dict[str, float]) -> bool:
        if not portfolio:
            return True
            
        correlations = []
        for existing_symbol in portfolio:
            if existing_symbol != symbol:
                correlation = self._calculate_correlation(symbol, existing_symbol)
                correlations.append(abs(correlation))
                
        return max(correlations, default=0) < self.risk_params.max_correlation_threshold

    def execute_trade_with_risk_management(self, symbol: str, sentiment: str) -> None:
        try:
            account = self.trading_client.get_account()
            portfolio = {p.symbol: float(p.qty) for p in self.trading_client.get_all_positions()}
            volatility = self._get_volatility(symbol)
            
            if "Positive" in sentiment and self.check_portfolio_correlation(symbol, portfolio):
                price = float(self.trading_client.get_latest_trade(symbol).price)
                position_size = self.calculate_position_size(symbol, float(account.equity), volatility)
                stop_loss = self.calculate_stop_loss(symbol, OrderSide.BUY, price, volatility)
                
                order = MarketOrderRequest(
                    symbol=symbol,
                    qty=position_size,
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.DAY,
                    stop_loss={'stop_price': stop_loss}
                )
                self.trading_client.submit_order(order)
                
            elif "Negative" in sentiment and symbol in portfolio:
                order = MarketOrderRequest(
                    symbol=symbol,
                    qty=portfolio[symbol],
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.DAY
                )
                self.trading_client.submit_order(order)
                
        except Exception as e:
            print(f"Error executing trade with risk management: {e}")

    def _get_volatility(self, symbol: str) -> float:
        if symbol not in self._volatility_cache:
            bars = self.trading_client.get_bars(
                symbol,
                start=(pd.Timestamp.now() - pd.Timedelta(days=20)).isoformat(),
                end=pd.Timestamp.now().isoformat(),
                timeframe='1Day'
            )
            
            prices = np.array([float(bar.close) for bar in bars])
            returns = np.log(prices[1:] / prices[:-1])
            self._volatility_cache[symbol] = np.std(returns) * np.sqrt(252)
            
        return self._volatility_cache[symbol]

    def _calculate_correlation(self, symbol1: str, symbol2: str) -> float:
        bars1 = self.trading_client.get_bars(
            symbol1,
            start=(pd.Timestamp.now() - pd.Timedelta(days=60)).isoformat(),
            end=pd.Timestamp.now().isoformat(),
            timeframe='1Day'
        )
        
        bars2 = self.trading_client.get_bars(
            symbol2,
            start=(pd.Timestamp.now() - pd.Timedelta(days=60)).isoformat(),
            end=pd.Timestamp.now().isoformat(),
            timeframe='1Day'
        )
        
        prices1 = np.array([float(bar.close) for bar in bars1])
        prices2 = np.array([float(bar.close) for bar in bars2])
        
        returns1 = np.log(prices1[1:] / prices1[:-1])
        returns2 = np.log(prices2[1:] / prices2[:-1])
        
        return np.corrcoef(returns1, returns2)[0, 1]