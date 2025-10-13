from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional
import aiohttp
import asyncio
import feedparser
from transformers import pipeline
from newspaper import Article
from pathlib import Path
import sys
import logging

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from trading_bot.data.db.database import Database

logger = logging.getLogger(__name__)

@dataclass
class NewsArticle:
    title: str
    content: str
    source: str
    url: str
    published_date: datetime
    sentiment_score: float = 0.0
    relevance_score: float = 0.0
    source_reliability: float = 0.0
    entity_mentions: Dict[str, int] = None


class NewsAnalyzer:
    def __init__(self, model_name: str = "ProsusAI/finbert"):
        self.sources = {
            "google_alerts": []
        }
        
        self.source_reliability = {
            "google_alerts": 0.7,
            "reuters": 0.9,
            "bloomberg": 0.9,
            "yahoo_finance": 0.8,
            "seeking_alpha": 0.75,
        }
        
        logger.info("Loading FinBERT sentiment model...")
        try:
            self.sentiment_analyzer = pipeline("sentiment-analysis", model=model_name)
            logger.info("FinBERT model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading FinBERT: {e}")
            logger.error("Falling back to default sentiment model")
            self.sentiment_analyzer = pipeline("sentiment-analysis")
        
        self.latest_articles = {}

    async def fetch_article_content(self, url: str) -> Optional[str]:
        try:
            article = Article(url)
            await asyncio.to_thread(article.download)
            await asyncio.to_thread(article.parse)
            return article.text
        except Exception as e:
            print(f"Error fetching article content: {e}")
            return None

    async def analyze_article(self, title: str, content: str, source: str, url: str) -> NewsArticle:
        try:
            # Analyze sentiment
            text_to_analyze = title + " " + content[:512]
            sentiment_results = await asyncio.to_thread(
                self.sentiment_analyzer, text_to_analyze
            )
            
            # FinBERT returns labels: 'positive', 'negative', 'neutral'
            # Map sentiment labels to scores (case-insensitive)
            label = sentiment_results[0]["label"].lower()
            score = sentiment_results[0].get("score", 0.5)  # Confidence score
            
            sentiment_map = {
                "positive": 1.0,
                "negative": -1.0,
                "neutral": 0.0
            }
            sentiment_score = sentiment_map.get(label, 0.0) * score
            
            # Simple relevance calculation based on content length and title
            # More sophisticated NER can be added later if needed
            relevance_score = min(len(content) / 1000.0, 1.0) * 0.5 + 0.5
            
            return NewsArticle(
                title=title,
                content=content,
                source=source,
                url=url,
                published_date=datetime.now(),
                sentiment_score=sentiment_score,
                relevance_score=relevance_score,
                source_reliability=self.source_reliability.get(source, 0.5),
                entity_mentions={}
            )
        except Exception as e:
            logger.error(f"Error analyzing article: {e}")
            # Return neutral sentiment on error
            return NewsArticle(
                title=title,
                content=content,
                source=source,
                url=url,
                published_date=datetime.now(),
                sentiment_score=0.0,
                relevance_score=0.5,
                source_reliability=self.source_reliability.get(source, 0.5),
                entity_mentions={}
            )

    async def get_latest_news(self, rss_url: str, stock_symbol: str, last_timestamp: Optional[datetime] = None) -> \
    Optional[NewsArticle]:
        """
        Get the latest relevant news article from RSS feed if newer than last_timestamp.
        Updates the last_article_timestamp in the database automatically.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(rss_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    feed_content = await response.text()
                    feed = feedparser.parse(feed_content)
                    if not feed.entries:
                        return None

                    entry = feed.entries[0]

                    # Parse entry date
                    entry_date = None
                    for attr in ['published_parsed', 'updated_parsed']:
                        if hasattr(entry, attr) and getattr(entry, attr):
                            entry_date = datetime(*getattr(entry, attr)[:6])
                            break
                    if not entry_date:
                        entry_date = datetime.now()

                    # Skip if older than last processed
                    if last_timestamp and entry_date <= last_timestamp:
                        logger.debug(
                            f"Article for {stock_symbol} is older than last processed ({entry_date} <= {last_timestamp})")
                        return None

                    # Check relevance
                    title_lower = entry.title.lower()
                    content_lower = getattr(entry, 'summary', getattr(entry, 'description', '')).lower()
                    if not self._is_article_relevant(stock_symbol, title_lower, content_lower):
                        logger.debug(f"Article for {stock_symbol} not relevant: {entry.title[:50]}...")
                        return None

                    # Fetch article content
                    content = await self.fetch_article_content(entry.link)
                    if not content or len(content) < 50:
                        content = getattr(entry, 'summary', getattr(entry, 'description', entry.title))

                    # Analyze article
                    article = await self.analyze_article(entry.title, content, "google_alerts", entry.link)
                    article.published_date = entry_date

                    # Update last article timestamp in DB
                    db = Database()
                    db.update_last_article(stock_symbol, entry_date)

                    logger.info(f"Found new relevant article for {stock_symbol}: {entry.title[:50]}...")
                    return article

        except Exception as e:
            logger.error(f"Error fetching latest news for {stock_symbol}: {e}", exc_info=True)
            return None

    def _is_article_relevant(self, stock_symbol: str, title_lower: str, content_lower: str) -> bool:
        """Check if article is relevant to the stock symbol."""
        # Check for exact symbol match
        if stock_symbol.lower() in title_lower or stock_symbol.lower() in content_lower:
            return True
        
        # Check for common company name variations
        relevance_map = {
            'AMD': ['amd', 'advanced micro'],
            'AAPL': ['apple', 'aapl'],
            'MSFT': ['microsoft', 'msft'],
            'GOOGL': ['google', 'alphabet', 'googl'],
            'AMZN': ['amazon', 'amzn'],
            'TSLA': ['tesla', 'tsla'],
            'META': ['meta', 'facebook'],
            'NVDA': ['nvidia', 'nvda'],
            'PEP': ['pepsi', 'pep'],
            'ADBE': ['adobe', 'adbe'],
            'CSCO': ['cisco', 'csco'],
            'COST': ['costco', 'cost'],
            'AVGO': ['broadcom', 'avgo'],
        }
        
        if stock_symbol in relevance_map:
            for keyword in relevance_map[stock_symbol]:
                if keyword in title_lower or keyword in content_lower:
                    return True
        
        # For other stocks, be more lenient - check if symbol appears anywhere
        if len(stock_symbol) >= 3 and stock_symbol.lower() in title_lower:
            return True
            
        return False

    async def get_stock_analysis(self, stock_entry: tuple) -> Optional[Dict]:
        """
        Analyze news for a specific stock and return sentiment analysis.
        Only processes new articles since the last analysis.
        
        Args:
            stock_entry: Tuple containing (symbol, company_name, rss_url)
            
        Returns:
            Dictionary with sentiment and confidence score
        """
        try:
            symbol, company_name, rss_url = stock_entry[:3]

            # Fetch and analyze news for this stock (only new articles)
            # Fetch last article timestamp from DB
            db = Database()
            last_article_time = db.get_last_article_on_stock(symbol)

            article = await self.get_latest_news(rss_url, symbol, last_article_time)
            if article:
                score = article.sentiment_score
                sentiment = (
                    "Positive" if score > 0.15
                    else "Negative" if score < -0.15
                    else "Neutral"
                )
                confidence = abs(score)
            else:
                return None

            return {
                "symbol": symbol,
                "company_name": company_name,
                "sentiment": sentiment,
                "confidence": confidence,
                "timestamp": datetime.now()
            }
        except Exception as e:
            logger.error(f"Error analyzing stock {stock_entry}: {e}", exc_info=True)
            return None

