from alpaca.data.historical import StockHistoricalDataClient
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
import json

class Account:
    def __init__(self):
        with open('secrets.json') as f:
            secrets = json.load(f)
            self.API_KEY = secrets['API_KEY']
            self.API_SECRET = secrets['API_SECRET']
        
        self.trading_client = TradingClient(self.API_KEY, self.API_SECRET)
        self.data_client = StockHistoricalDataClient(self.API_KEY, self.API_SECRET)

    def get_portfolio(self):
        return {position.symbol: float(position.qty) for position in self.trading_client.get_all_positions()}

    def get_buying_power(self):
        account = self.trading_client.get_account()
        return float(account.buying_power)

    def trade_stock(self, symbol, sentiment):
        try:
            portfolio = self.get_portfolio()
            buying_power = self.get_buying_power()
            ten_percent_buying_power = round(buying_power * 0.3, 2)

            if "Positive" in sentiment:
                order = MarketOrderRequest(
                    symbol=symbol,
                    notional=ten_percent_buying_power,
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.DAY
                )
                self.trading_client.submit_order(order)
                print(f"Bought 10% of buying power (${ten_percent_buying_power:.2f}) of {symbol}")

            elif "Negative" in sentiment and symbol in portfolio:
                order = MarketOrderRequest(
                    symbol=symbol,
                    qty=portfolio[symbol],
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.DAY
                )
                self.trading_client.submit_order(order)
                print(f"Sold all shares of {symbol}")

        except Exception as e:
            print(f"Error: {e}")

    def get_stock_price(self, symbol):
        bars = self.data_client.get_stock_bars(symbol, timeframe="1Min", limit=1)
        if bars:
            return bars[0].close
        return None
