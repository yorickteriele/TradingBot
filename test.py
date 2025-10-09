import Initialize

account = Initialize.Account()

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.enums import AssetClass

# Trading client from the account setup
trading_client = account.trading_client

# Search for US equities
search_params = GetAssetsRequest(asset_class=AssetClass.US_EQUITY)
assets = trading_client.get_all_assets(search_params)

# Create a dictionary to count symbols per exchange
exchange_counts = {}

for asset in assets:
    exchange = asset.exchange  # Get the exchange of the asset
    if exchange in exchange_counts:
        exchange_counts[exchange] += 1
    else:
        exchange_counts[exchange] = 1

# Print the result
print("Exchange Counts:")
for exchange, count in exchange_counts.items():
    print(f"{exchange}: {count}")
