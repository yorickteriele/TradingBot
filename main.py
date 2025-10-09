import asyncio
from datetime import datetime
import NewsCheck
import Initialize
import mysql.connector


def retrieve_all_data():
    mydb = mysql.connector.connect(
        host="localhost",
        user="phpadmin",
        password="phpadmin",
        database="TradingBot"
    )

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
    checkInterval = 300
    analyzer = NewsCheck.StockNewsAnalyzer()
    account = Initialize.Account()

    while True:
        print(f"Checking news and trading... \t{datetime.now()}")

        stock_entries = retrieve_all_data()

        tasks = [process_stock(analyzer, entry, account) for entry in stock_entries]
        await asyncio.gather(*tasks)

        print(f"Done scanning now waiting for {checkInterval} seconds \t{datetime.now()}")
        await asyncio.sleep(checkInterval)


if __name__ == "__main__":
    asyncio.run(main())
