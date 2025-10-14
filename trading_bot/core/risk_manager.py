from dataclasses import dataclass
from typing import Dict, Optional
import numpy as np
from datetime import datetime, timedelta
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame


@dataclass
class RiskParameters:
    max_position_size: float = 0.05  # Max 5% of portfolio per position (reduced from 10%)
    max_portfolio_risk: float = 0.005  # Risk 0.5% of portfolio per trade (reduced from 2%)
    stop_loss_atr_multiplier: float = 2.0
    position_sizing_atr_multiplier: float = 1.0
    max_correlation_threshold: float = 0.7


class RiskManager:
    def __init__(self, trading_client: TradingClient, data_client: StockHistoricalDataClient, risk_params: Optional[RiskParameters] = None):
        self.trading_client = trading_client
        self.data_client = data_client
        self.risk_params = risk_params or RiskParameters()
        self._position_cache = {}
        self._volatility_cache = {}

    def calculate_position_size(self, symbol: str, account_value: float, volatility: float) -> float:
        risk_amount = account_value * self.risk_params.max_portfolio_risk
        print(f"Calculating position for {symbol}: account_value=${account_value:.2f}, risk_amount=${risk_amount:.2f}")
        
        # Get latest quote price instead of trade
        from alpaca.data.requests import StockLatestQuoteRequest
        quote_request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
        quotes = self.data_client.get_stock_latest_quote(quote_request)
        if symbol in quotes:
            price = float(quotes[symbol].ask_price)
        else:
            print(f"Could not get price for {symbol}")
            return 0.0
            
        print(f"Stock {symbol} price: ${price:.2f}, volatility: {volatility:.4f}")
        
        position_size = (risk_amount / (volatility * self.risk_params.position_sizing_atr_multiplier))
        max_position = account_value * self.risk_params.max_position_size
        
        # Calculate final position size
        final_position = min(position_size, max_position) / price
        position_value = final_position * price
        
        print(f"Position calculation: size={final_position:.4f} shares, value=${position_value:.2f}")
        
        # Ensure minimum viable position size (at least $1 worth)
        min_position_value = 1.0
        if position_value < min_position_value:
            print(f"Position size too small for {symbol}: ${position_value:.2f} < ${min_position_value}")
            return 0.0
            
        return final_position

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
                # Get latest quote price instead of trade
                from alpaca.data.requests import StockLatestQuoteRequest
                quote_request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
                quotes = self.data_client.get_stock_latest_quote(quote_request)
                if symbol in quotes:
                    price = float(quotes[symbol].ask_price)
                else:
                    print(f"Could not get price for {symbol}")
                    return
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
            try:
                request_params = StockBarsRequest(
                    symbol_or_symbols=symbol,
                    timeframe=TimeFrame.Day,
                    start=datetime.now() - timedelta(days=20)
                )
                bars = self.data_client.get_stock_bars(request_params)
                
                if symbol in bars:
                    prices = np.array([float(bar.close) for bar in bars[symbol]])
                    if len(prices) > 1:
                        returns = np.log(prices[1:] / prices[:-1])
                        self._volatility_cache[symbol] = np.std(returns) * np.sqrt(252)
                    else:
                        self._volatility_cache[symbol] = 0.02  # Default 2% volatility
                else:
                    self._volatility_cache[symbol] = 0.02
            except Exception as e:
                print(f"Error calculating volatility for {symbol}: {e}")
                self._volatility_cache[symbol] = 0.02
            
        return self._volatility_cache[symbol]

    def _calculate_correlation(self, symbol1: str, symbol2: str) -> float:
        try:
            request_params1 = StockBarsRequest(
                symbol_or_symbols=symbol1,
                timeframe=TimeFrame.Day,
                start=datetime.now() - timedelta(days=60)
            )
            request_params2 = StockBarsRequest(
                symbol_or_symbols=symbol2,
                timeframe=TimeFrame.Day,
                start=datetime.now() - timedelta(days=60)
            )
            
            bars1 = self.data_client.get_stock_bars(request_params1)
            bars2 = self.data_client.get_stock_bars(request_params2)
            
            if symbol1 in bars1 and symbol2 in bars2:
                prices1 = np.array([float(bar.close) for bar in bars1[symbol1]])
                prices2 = np.array([float(bar.close) for bar in bars2[symbol2]])
                
                min_len = min(len(prices1), len(prices2))
                if min_len > 1:
                    returns1 = np.log(prices1[1:min_len] / prices1[:min_len-1])
                    returns2 = np.log(prices2[1:min_len] / prices2[:min_len-1])
                    return np.corrcoef(returns1, returns2)[0, 1]
            
            return 0.0
        except Exception as e:
            print(f"Error calculating correlation: {e}")
            return 0.0