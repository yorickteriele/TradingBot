from alpaca.data.historical import StockHistoricalDataClient
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
import json
from risk_management import RiskManager, RiskParameters

class Account:
    def __init__(self, risk_params=None):
        with open('secrets.json') as f:
            secrets = json.load(f)
            self.API_KEY = secrets['API_KEY']
            self.API_SECRET = secrets['API_SECRET']
        
        self.trading_client = TradingClient(self.API_KEY, self.API_SECRET)
        self.data_client = StockHistoricalDataClient(self.API_KEY, self.API_SECRET)
        self.risk_manager = RiskManager(self.trading_client, risk_params)

    def get_portfolio(self):
        return {position.symbol: float(position.qty) for position in self.trading_client.get_all_positions()}

    def get_buying_power(self):
        account = self.trading_client.get_account()
        return float(account.buying_power)

    def trade_stock(self, symbol, sentiment):
        try:
            self.risk_manager.execute_trade_with_risk_management(symbol, sentiment)
        except Exception as e:
            print(f"Error: {e}")

    def get_stock_price(self, symbol):
        bars = self.data_client.get_stock_bars(symbol, timeframe="1Min", limit=1)
        if bars:
            return bars[0].close
        return None
