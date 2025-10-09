from datetime import datetime, timedelta
import asyncio
from news_analysis import NewsAnalyzer


class StockNewsAnalyzer:
    def __init__(self, model_name="ProsusAI/finbert"):
        self.news_analyzer = NewsAnalyzer(model_name)
        self.latest_articles = {}

    async def get_stock_analysis(self, stockListEntry):
        company_name = stockListEntry[2]
        rss_url = stockListEntry[3]
        
        # Add the Google Alert RSS feed to the news sources
        if company_name not in self.latest_articles:
            self.latest_articles[company_name] = datetime.now()
            self.news_analyzer.add_news_source(f"google_alerts_{company_name}", rss_url, 0.7)
            
        # Get aggregated sentiment from all sources
        sentiment, confidence = await self.news_analyzer.get_aggregated_sentiment(company_name)
        
        if confidence > 0:
            self.latest_articles[company_name] = datetime.now()
            return {
                'title': f"Aggregated news sentiment for {company_name}",
                'sentiment': sentiment,
                'confidence': confidence
            }
        
        return None

