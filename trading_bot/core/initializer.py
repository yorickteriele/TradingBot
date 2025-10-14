from alpaca.data.historical import StockHistoricalDataClient
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide
from alpaca.data.requests import StockLatestQuoteRequest
from trading_bot.core.risk_manager import RiskManager
import os
import logging

logger = logging.getLogger(__name__)


class Account:
    def __init__(self, performance_tracker=None):
        self.API_KEY = os.getenv('ALPACA_API_KEY')
        self.API_SECRET = os.getenv('ALPACA_SECRET_KEY')
        
        self.trading_client = TradingClient(self.API_KEY, self.API_SECRET)
        self.data_client = StockHistoricalDataClient(self.API_KEY, self.API_SECRET)
        self.risk_manager = RiskManager(self.trading_client, self.data_client)
        self.performance_tracker = performance_tracker


    def get_data_client(self):
        return self.data_client

    def get_trading_client(self):
        return self.trading_client

    def get_portfolio(self):
        return {position.symbol: float(position.qty) for position in self.trading_client.get_all_positions()}

    def get_buying_power(self):
        account = self.trading_client.get_account()
        return float(account.buying_power)

    def trade_stock(self, symbol, sentiment):
        try:
            current_price = self.get_stock_price(symbol)
            if not current_price:
                logger.info(f"Could not get price for {symbol}")
                return

            portfolio = self.get_portfolio()
            
            # Use risk manager if available, otherwise simple trading logic
            if self.risk_manager:
                if "Positive" in sentiment and symbol not in portfolio:
                    volatility = self.risk_manager._get_volatility(symbol)
                    size = self.risk_manager.calculate_position_size(symbol, self.get_buying_power(), volatility)
                    stop_loss = self.risk_manager.calculate_stop_loss(symbol, OrderSide.BUY, current_price, volatility)
                    
                    if self.performance_tracker:
                        self.performance_tracker.record_entry(symbol, current_price, size, sentiment, stop_loss)
                    
                    self.risk_manager.execute_trade_with_risk_management(symbol, sentiment)
                    logger.info(f"BUY {symbol} at ${current_price:.2f} - Size: {size:.2f}")

                elif "Negative" in sentiment and symbol in portfolio:
                    self.risk_manager.execute_trade_with_risk_management(symbol, sentiment)
                    
                    if self.performance_tracker:
                        self.performance_tracker.record_exit(symbol, current_price)

                    logger.info(f"SELL {symbol} at ${current_price:.2f}")
            else:
                # Simple trading without risk management
                if "Positive" in sentiment and symbol not in portfolio:
                    logger.info(f"Would BUY {symbol} at ${current_price:.2f} (risk manager not configured)")
                elif "Negative" in sentiment and symbol in portfolio:
                    logger.info(f"Would SELL {symbol} at ${current_price:.2f} (risk manager not configured)")

        except Exception as e:
            logger.info(f"Error trading {symbol}: {e}")

    def get_stock_price(self, symbol):
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quotes = self.data_client.get_stock_latest_quote(request)
            if symbol in quotes:
                return float(quotes[symbol].ask_price)
            return None
        except Exception as e:
            logger.info(f"Error getting price for {symbol}: {e}")
            return None
