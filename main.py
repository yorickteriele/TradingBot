import asyncio
from datetime import datetime

from numpy.f2py.auxfuncs import throw_error

from trading_bot.core import news_analyzer, initializer
from trading_bot.core.performance_tracker import PerformanceTracker
from trading_bot.data.db.database import Database
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging TODO maybe other file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

# Color setup
COLORS = {
    "DEBUG": "\033[37m",   # Gray
    "INFO": "\033[36m",    # Cyan
    "WARNING": "\033[33m", # Yellow
    "ERROR": "\033[31m",   # Red
    "CRITICAL": "\033[41m" # Red background
}
RESET = "\033[0m"

# Monkey-patch the default formatter
old_factory = logging.getLogRecordFactory()
def record_factory(*args, **kwargs):
    record = old_factory(*args, **kwargs)
    color = COLORS.get(record.levelname, "")
    record.levelname = f"{color}{record.levelname}"
    return record
logging.setLogRecordFactory(record_factory)

logger = logging.getLogger(__name__)

def retrieve_all_data():
    try:
        with Database() as db:
            return db.get_all_stocks()
    except Exception as e:
        logger.error(f"Database error: {e}", exc_info=True)
        raise

async def main():
    check_interval = int(os.getenv('CHECK_INTERVAL', '300'))  # Default 5 minutes
    
    logger.info("=" * 60)
    logger.info("Trading Bot - News Sentiment Analysis")
    logger.info("=" * 60)
    
    # Initialize components with proper dependencies
    logger.info("Initializing components...")
    analyzer = news_analyzer.NewsAnalyzer()
    performance_tracker = PerformanceTracker()
    account = initializer.Account(performance_tracker)
    
    logger.info("Bot initialized successfully!")
    logger.info(f"Check interval: {check_interval // 60} minutes")
    logger.info("=" * 60)

    while True:
        logger.info("Checking news and analyzing sentiment...")

        try:
            stock_entries = retrieve_all_data()
            logger.info(f"Analyzing {len(stock_entries)} stocks...\n")

            # Run all stock analyses concurrently
            tasks = [asyncio.create_task(analyzer.get_stock_analysis(stock)) for stock in stock_entries]
            results = await asyncio.gather(*tasks)

            for result in results:
                if isinstance(result, Exception) or result is None:
                    continue

                try:
                    sentiment = result['sentiment']
                    confidence = result.get('confidence', 0.0)
                    symbol = result['symbol']

                    logger.info(f"Stock: {symbol} | Sentiment: {sentiment} | Confidence: {confidence:.2f}")

                    if confidence > 0.3:
                        account.trade_stock(symbol, sentiment)
                    else:
                        logger.info(f"  Skipping trade - confidence too low")

                    logger.info("-" * 50)
                except Exception as e:
                    logger.info(f"Error processing result: {e}")

            # Display performance metrics
            metrics = performance_tracker.get_performance_metrics()
            logger.info(f"\n{'=' * 60}")
            logger.info("Performance Summary:")
            logger.info(f"  Total Trades: {metrics['total_trades']}")
            logger.info(f"  Win Rate: {metrics['win_rate']:.2%}")
            logger.info(f"  Total P&L: ${metrics['total_pnl']:.2f}")
            logger.info(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
            logger.info(f"  Max Drawdown: {metrics['max_drawdown']:.2%}")
            logger.info(f"{'=' * 60}")

            logger.info(f"\nDone scanning. Next update in {check_interval // 60} minutes")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")

        await asyncio.sleep(check_interval)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.error("\n\nBot stopped by user")
    except Exception as e:
        logger.error(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
