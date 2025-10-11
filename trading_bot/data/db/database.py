import re
import json
import os
import psycopg2
from pathlib import Path

# Load configuration from secrets.json
secrets_path = Path(__file__).parent.parent.parent.parent / 'secrets.json'
with open(secrets_path) as f:
    config = json.load(f)

# Initialize Alpaca client
import Initialize
account = Initialize.Account()

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.enums import AssetClass

trading_client = account.trading_client

search_params = GetAssetsRequest(asset_class=AssetClass.US_EQUITY)
assets = trading_client.get_all_assets(search_params)

nasdaq_assets = [asset for asset in assets if asset.exchange == "NASDAQ"]
print(nasdaq_assets)
nasdaq_assets = sorted(nasdaq_assets, key=lambda x: x.fractionable, reverse=True)[:300]

# Database connection using PostgreSQL
conn = psycopg2.connect(
    host=config.get("DB_HOST", "localhost"),
    user=config.get("DB_USER", "postgres"),
    password=config.get("DB_PASSWORD", "postgres"),
    dbname=config.get("DB_NAME", "tradingbot")
)

terms_to_remove = [
    "Inc.", "Inc", "Company", "Corporation", "Corp.", "Limited", "Ltd.", "LLC",
    "Common Stock", "Common Shares", "Stock", "Shares", "Class A Common",
    "Warrants", "Depositary", "Ordinary", ",",
    "Preferred Stock", "Preferred Shares", "Equity", "Securities", "Bonds",
    "Dividend", "Investment", "Options", "Convertible", "ETF", "REIT",
    "Shares Outstanding", "Market Cap", "Tickers", "Shareholder", "Publicly Traded", "IPO"
]


def clean_company_name(company_name):
    pattern = r"\b(" + "|".join(re.escape(term) for term in terms_to_remove) + r")\b"

    match = re.search(pattern, company_name)
    if match:
        cleaned_name = company_name[:match.start()].strip()
        return re.sub(r"\s*,\s*", " ", cleaned_name) 

    return company_name.strip()

# Create a cursor
cursor = conn.cursor()

# Create table with PostgreSQL syntax
create_table_query = """
CREATE TABLE IF NOT EXISTS nasdaq_stock (
    stock_id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    rss_url VARCHAR(255) NOT NULL
);
"""
cursor.execute(create_table_query)
print("Table created or already exists.")

# Clear existing data
truncate_query = "TRUNCATE TABLE nasdaq_stock;"
cursor.execute(truncate_query)
conn.commit()
print("All existing entries removed.")

for asset in nasdaq_assets:
    insert_query = """
    INSERT INTO nasdaq_stock (Symbol, CompanyName, Exchange, RSS_URL)
    VALUES (%s, %s, %s, %s)
    """
    company_name = clean_company_name(asset.name)
    rss_url = chrome.create_alert_for_company(company_name)  # Use the RSS URL generator
    cursor.execute(insert_query, (asset.symbol, asset.name, asset.exchange, rss_url))

mydb.commit()
print("300 most popular NASDAQ stocks inserted successfully!")

cursor.close()
mydb.close()


if __name__ == "__main__":
    print("Fetching and inserting popular NASDAQ stocks...")
