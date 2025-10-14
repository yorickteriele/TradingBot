import re
import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)


# Terms to remove from company names
TERMS_TO_REMOVE = [
    "Inc.", "Inc", "Company", "Corporation", "Corp.", "Limited", "Ltd.", "LLC",
    "Common Stock", "Common Shares", "Stock", "Shares", "Class A Common",
    "Warrants", "Depositary", "Ordinary", ",",
    "Preferred Stock", "Preferred Shares", "Equity", "Securities", "Bonds",
    "Dividend", "Investment", "Options", "Convertible", "ETF", "REIT",
    "Shares Outstanding", "Market Cap", "Tickers", "Shareholder", "Publicly Traded", "IPO"
]


class Database:
    """Database class that manages PostgreSQL connections and operations."""

    _instance = None

    def __new__(cls, config: Optional[Dict] = None):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance.config = config or cls.load_config()
            cls._instance.conn = None
            cls._instance.ensure_connection()
        return cls._instance

    @staticmethod
    def load_config() -> Dict[str, str]:
        load_dotenv()
        return {
            "DB_HOST": os.environ.get("DB_HOST", "localhost"),
            "DB_USER": os.environ.get("DB_USER", "postgres"),
            "DB_PASSWORD": os.environ.get("DB_PASSWORD", "postgres"),
            "DB_NAME": os.environ.get("DB_NAME", "tradingbot")
        }

    def __enter__(self):
        self.ensure_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
       pass

    def connect(self) -> None:
        """Establish database connection."""
        try:
            self.conn = psycopg2.connect(
                host=self.config.get("DB_HOST", "localhost"),
                user=self.config.get("DB_USER", "postgres"),
                password=self.config.get("DB_PASSWORD", "postgres"),
                dbname=self.config.get("DB_NAME", "tradingbot")
            )
            logger.info("Database connection established")
        except psycopg2.Error as e:
            logger.error(f"Database connection error: {e}")
            raise

    def ensure_connection(self):
        if self.conn is None:
            self.connect()
    
    def initialize_database(self) -> None:
        """Initialize the database table."""
        self.ensure_connection()
        cursor = self.conn.cursor()
        try:
            # Create table with PostgreSQL syntax
            create_table_query = """
            CREATE TABLE IF NOT EXISTS nasdaq_stock (
                stock_id SERIAL PRIMARY KEY,
                symbol VARCHAR(10) NOT NULL,
                company_name VARCHAR(255) NOT NULL,
                exchange VARCHAR(50) NOT NULL,
                rss_url VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            cursor.execute(create_table_query)
            self.conn.commit()
            logger.info("Table created or already exists")
            
        except psycopg2.Error as e:
            logger.error(f"Error creating table: {e}")
            raise
        finally:
            cursor.close()
    
    def clear_existing_data(self) -> None:
        """Clear existing data from the nasdaq_stock table."""
        self.ensure_connection()
        cursor = self.conn.cursor()
        try:
            truncate_query = "TRUNCATE TABLE nasdaq_stock;"
            cursor.execute(truncate_query)
            self.conn.commit()
            logger.info("All existing entries removed")
        except psycopg2.Error as e:
            logger.error(f"Error truncating table: {e}")
            raise
        finally:
            cursor.close()
    
    def insert_stock_data(self, symbol: str, company_name: str, exchange: str, rss_url: str) -> bool:
        """Insert stock data into the database."""
        self.ensure_connection()
        cursor = self.conn.cursor()
        try:
            insert_query = """
            INSERT INTO nasdaq_stock (symbol, company_name, exchange, rss_url)
            VALUES (%s, %s, %s, %s);
            """
            cursor.execute(insert_query, (symbol, company_name, exchange, rss_url))
            self.conn.commit()
            return True
        except psycopg2.Error as e:
            logger.error(f"Error inserting stock data for {symbol}: {e}")
            self.conn.rollback()
            return False
        finally:
            cursor.close()

    def get_all_stocks(self) -> List[tuple]:
        """Return all stocks as tuples (symbol, name, rss_url)."""
        self.ensure_connection()
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT symbol, company_name, rss_url FROM nasdaq_stock;")
            return cursor.fetchall()

    def get_last_article_on_stock(self, stock_symbol) -> Optional[datetime]:
        """Return the last article timestamp for a stock, or None if not found."""
        self.ensure_connection()
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT last_article_timestamp FROM stock_news_tracking WHERE stock_symbol = %s;",
                    (stock_symbol,)
                )
                result = cursor.fetchone()
                if result and result[0]:
                    return result[0] if isinstance(result[0], datetime) else datetime.fromisoformat(result[0])
                return None
        except psycopg2.Error as e:
            logger.error(f"Error fetching last article for {stock_symbol}: {e}", exc_info=True)
            self.conn.rollback()  # Important: rollback the failed transaction
            return None

    def update_last_article(self, stock_symbol, last_article_timestamp: datetime):
        """Update the last article timestamp for a stock."""
        self.ensure_connection()
        with self.conn.cursor() as cursor:
            try:
                cursor.execute(
                    """
                    INSERT INTO stock_news_tracking (stock_symbol, last_article_timestamp, updated_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (stock_symbol) 
                    DO UPDATE SET last_article_timestamp = EXCLUDED.last_article_timestamp,
                                  updated_at = EXCLUDED.updated_at;
                    """,
                    (stock_symbol, last_article_timestamp, datetime.now())
                )
            except psycopg2.Error as e:
                logger.error(f"Error updating last article for {stock_symbol}: {e}", exc_info=True)
                self.conn.rollback()

def clean_company_name(company_name: str) -> str:
    """Clean company name by removing common corporate terms."""
    pattern = r"\b(" + "|".join(re.escape(term) for term in TERMS_TO_REMOVE) + r")\b"
    
    match = re.search(pattern, company_name, re.IGNORECASE)
    if match:
        cleaned_name = company_name[:match.start()].strip()
        return re.sub(r"\s*,\s*", " ", cleaned_name)
    
    return company_name.strip()

def get_nasdaq_assets(top_n: int = 300) -> List:
    """Fetch NASDAQ assets from Alpaca, prioritizing popular fractional stocks."""
    try:
        from trading_bot.core.initializer import Account
        from alpaca.trading.requests import GetAssetsRequest
        from alpaca.trading.enums import AssetClass
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockLatestQuoteRequest
        
        account = Account()
        trading_client = account.trading_client
        
        search_params = GetAssetsRequest(asset_class=AssetClass.US_EQUITY)
        assets = trading_client.get_all_assets(search_params)
        
        # Filter for NASDAQ fractional stocks that are tradable and active
        nasdaq_assets = [
            asset for asset in assets 
            if asset.exchange == "NASDAQ" 
            and asset.fractionable 
            and asset.tradable 
            and asset.status == "active"
            and not asset.symbol.endswith(('W', 'R', 'U'))  # Exclude warrants, rights, units
        ]
        logger.info(f"Found {len(nasdaq_assets)} tradable fractional NASDAQ assets")
        
        # List of popular NASDAQ stocks (by market cap and liquidity)
        # This ensures we get the most well-known and actively traded stocks
        popular_nasdaq = [
            'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'COST',
            'ASML', 'NFLX', 'AMD', 'PEP', 'ADBE', 'CSCO', 'TMUS', 'CMCSA', 'INTC', 'INTU',
            'TXN', 'QCOM', 'AMGN', 'HON', 'AMAT', 'SBUX', 'ISRG', 'BKNG', 'VRTX', 'ADI',
            'GILD', 'REGN', 'PANW', 'MU', 'LRCX', 'ADP', 'MDLZ', 'SNPS', 'KLAC', 'CDNS',
            'MELI', 'PYPL', 'ABNB', 'CRWD', 'MAR', 'MRVL', 'ORLY', 'CSX', 'ADSK', 'FTNT',
            'NXPI', 'WDAY', 'DASH', 'ROP', 'PCAR', 'MNST', 'AEP', 'CPRT', 'PAYX', 'ROST',
            'ODFL', 'KDP', 'FAST', 'EA', 'VRSK', 'CTSH', 'DXCM', 'GEHC', 'BKR', 'TEAM',
            'CTAS', 'KHC', 'IDXX', 'EXC', 'CCEP', 'LULU', 'XEL', 'FANG', 'TTWO', 'ZS',
            'ANSS', 'ON', 'DDOG', 'CDW', 'WBD', 'BIIB', 'GFS', 'CSGP', 'MDB', 'ILMN'
        ]
        
        # Create a priority score: popular stocks get higher priority
        def get_priority_score(asset):
            symbol = asset.symbol
            if symbol in popular_nasdaq:
                # Higher score for more popular stocks (earlier in the list)
                return 10000 - popular_nasdaq.index(symbol)
            else:
                # Lower score for other stocks
                return 0
        
        # Sort by popularity score
        nasdaq_assets = sorted(nasdaq_assets, key=get_priority_score, reverse=True)
        
        # Take top N
        nasdaq_assets = nasdaq_assets[:top_n]
        logger.info(f"Selected top {len(nasdaq_assets)} most popular fractional NASDAQ assets")
        
        return nasdaq_assets
    except Exception as e:
        logger.error(f"Error fetching NASDAQ assets: {e}")
        raise


def process_nasdaq_stocks(clear_existing: bool = True, top_n: int = 300) -> None:
    """Main function to process NASDAQ stocks and create Google Alerts."""
    from trading_bot.utils.browser import GoogleAlertsManager
    
    error_log_path = Path('google_alerts_errors.log')
    
    # Get NASDAQ assets
    logger.info("Fetching NASDAQ assets from Alpaca...")
    nasdaq_assets = get_nasdaq_assets(top_n)
    
    # Initialize database connection using the new Database class
    with Database() as db:
        db.initialize_database()
        
        if clear_existing:
            db.clear_existing_data()
        
        # Create Google Alerts Manager with context manager
        logger.info("Starting Google Alerts automation...")
        with GoogleAlertsManager(screenshot_dir='screenshots') as alerts_manager:
            successful = 0
            failed = 0
            
            try:
                for i, asset in enumerate(nasdaq_assets, 1):
                    try:
                        company_name = clean_company_name(asset.name)
                        logger.info(f"Processing {i}/{len(nasdaq_assets)}: {company_name} ({asset.symbol})")
                        
                        # Get RSS URL from Google Alerts
                        rss_url = alerts_manager.create_alert_for_company(company_name)
                        
                        if not rss_url:
                            logger.warning(f"Failed to create alert for {company_name}, skipping...")
                            failed += 1
                            continue
                        
                        # Insert into database using the Database class
                        if db.insert_stock_data(asset.symbol, company_name, asset.exchange, rss_url):
                            logger.info(f"Successfully added {company_name} to database")
                            successful += 1
                        else:
                            failed += 1
                        
                        # Add a small delay between requests to avoid rate limiting
                        time.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"Error processing {asset.name} ({asset.symbol}): {e}")
                        failed += 1
                        # Save error to a log file
                        with open(error_log_path, 'a', encoding='utf-8') as f:
                            f.write(f"{time.ctime()} - Error processing {asset.name} ({asset.symbol}): {str(e)}\n")
                        continue
                
            except KeyboardInterrupt:
                logger.warning("Script interrupted by user")
            finally:
                logger.info(f"\nProcessing complete: {successful} successful, {failed} failed")


def main():
    """Entry point for the script."""
    try:
        logger.info("Starting NASDAQ stock processing...")
        process_nasdaq_stocks(clear_existing=True, top_n=300)
        logger.info("NASDAQ stocks processed successfully!")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
