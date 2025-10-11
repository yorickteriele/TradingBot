import asyncio
from datetime import datetime
from trading_bot.core import news_analyzer, initializer
from trading_bot.core.performance_tracker import PerformanceTracker
from trading_bot.core.risk_manager import RiskManager
import mysql.connector
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_db_connection():
    """Create and return a database connection using environment variables."""
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'TradingBot')
    )


def retrieve_all_data():
    """Retrieve all stock data from the database."""
    mydb = get_db_connection()

    cursor = mydb.cursor()

    try:
        select_query = "SELECT * FROM stock"
        cursor.execute(select_query)
        all_data = cursor.fetchall()
        return all_data
    finally:
        cursor.close()
        mydb.close()


async def process_stock(analyzer, stockListEntry, account):
    result = await analyzer.get_stock_analysis(stockListEntry)

    if result is None:
        return

    sentiment = result['sentiment']
    print(f"Stock Symbol: {stockListEntry[1]}" + f" Sentiment: {sentiment}")
    print("-")
    account.trade_stock(stockListEntry[1], sentiment)


async def main():
    check_interval = int(os.getenv('CHECK_INTERVAL', '300'))  # Default 5 minutes
    
    # Initialize components
    analyzer = news_analyzer.NewsAnalyzer()
    account = initializer.Account()
    performance_tracker = PerformanceTracker()
    risk_manager = RiskManager()

    while True:
        print(f"Checking news and trading... \t{datetime.now()}")

        try:
            stock_entries = retrieve_all_data()
            
            # Process stocks with rate limiting
            for i in range(0, len(stock_entries), 5):  # Process 5 stocks at a time
                batch = stock_entries[i:i+5]
                tasks = [process_stock(analyzer, entry, account) for entry in batch]
                await asyncio.gather(*tasks)
                
                # Small delay between batches to avoid rate limiting
                await asyncio.sleep(1)
                
            print(f"Done scanning. Next update in {check_interval // 60} minutes\t{datetime.now()}")
            
        except Exception as e:
            print(f"Error during processing: {e}")
            
        await asyncio.sleep(check_interval)


if __name__ == "__main__":
    asyncio.run(main())
