from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import aiohttp
import asyncio
import feedparser
from bs4 import BeautifulSoup
import numpy as np
from transformers import pipeline
from newspaper import Article
import json


@dataclass
class NewsSource:
    name: str
    url: str
    reliability_score: float
    specialization: str  # 'finance', 'general', 'tech'
    update_frequency: int  # minutes


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
            "google_alerts": [],  # RSS URLs from Google Alerts
            "reuters": ["https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best"],
            "bloomberg": ["https://www.bloomberg.com/feeds/securities.xml"],
            "yahoo_finance": ["https://finance.yahoo.com/news/rssindex"],
            "seeking_alpha": ["https://seekingalpha.com/market_currents.xml"],
        }
        
        self.source_reliability = {
            "google_alerts": 0.7,
            "reuters": 0.9,
            "bloomberg": 0.9,
            "yahoo_finance": 0.8,
            "seeking_alpha": 0.75,
        }
        
        self.sentiment_analyzer = pipeline("sentiment-analysis", model=model_name)
        self.ner_pipeline = pipeline("ner", model="dbmdz/bert-large-cased-finetuned-conll03-english")
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
        sentiment_results = await asyncio.to_thread(
            self.sentiment_analyzer, title + " " + content[:512]
        )
        
        # Map sentiment labels to scores
        sentiment_map = {
            "positive": 1.0,
            "negative": -1.0,
            "neutral": 0.0
        }
        sentiment_score = sentiment_map.get(sentiment_results[0]["label"], 0.0)
        
        # Named Entity Recognition
        ner_results = await asyncio.to_thread(
            self.ner_pipeline, content[:512]
        )
        
        # Count entity mentions
        entity_mentions = {}
        for ent in ner_results:
            if ent["entity"].startswith("B-"):  # Beginning of entity
                entity = ent["word"]
                entity_mentions[entity] = entity_mentions.get(entity, 0) + 1

        # Calculate relevance based on entity mentions and content length
        relevance_score = min(len(entity_mentions) / 10.0, 1.0)
        
        return NewsArticle(
            title=title,
            content=content,
            source=source,
            url=url,
            published_date=datetime.now(),
            sentiment_score=sentiment_score,
            relevance_score=relevance_score,
            source_reliability=self.source_reliability.get(source, 0.5),
            entity_mentions=entity_mentions
        )

    async def get_articles_from_source(self, source_name: str, urls: List[str]) -> List[NewsArticle]:
        articles = []
        async with aiohttp.ClientSession() as session:
            for url in urls:
                try:
                    async with session.get(url) as response:
                        feed_content = await response.text()
                        feed = feedparser.parse(feed_content)
                        
                        for entry in feed.entries[:5]:  # Get latest 5 articles
                            content = await self.fetch_article_content(entry.link)
                            if not content:
                                continue
                                
                            article = await self.analyze_article(
                                entry.title,
                                content,
                                source_name,
                                entry.link
                            )
                            articles.append(article)
                            
                except Exception as e:
                    print(f"Error processing {url}: {e}")
                    
        return articles

    async def get_aggregated_sentiment(self, symbol: str) -> Tuple[str, float]:
        all_articles = []
        
        # Fetch articles from all sources in parallel
        tasks = []
        for source_name, urls in self.sources.items():
            task = self.get_articles_from_source(source_name, urls)
            tasks.append(task)
            
        results = await asyncio.gather(*tasks)
        for articles in results:
            all_articles.extend(articles)
            
        if not all_articles:
            return "Neutral", 0.0
            
        # Calculate weighted sentiment score
        weighted_sentiments = []
        weights = []
        
        for article in all_articles:
            # Weight based on source reliability and article relevance
            weight = article.source_reliability * article.relevance_score
            weighted_sentiments.append(article.sentiment_score * weight)
            weights.append(weight)
            
        if not weights:
            return "Neutral", 0.0
            
        # Calculate weighted average
        final_sentiment = np.average(weighted_sentiments, weights=weights)
        
        # Convert to categorical sentiment with confidence
        if final_sentiment > 0.2:
            return "Positive", abs(final_sentiment)
        elif final_sentiment < -0.2:
            return "Negative", abs(final_sentiment)
        else:
            return "Neutral", abs(final_sentiment)

    def add_news_source(self, name: str, url: str, reliability: float):
        if name not in self.sources:
            self.sources[name] = []
        self.sources[name].append(url)
        self.source_reliability[name] = reliability

    def update_source_reliability(self, name: str, reliability: float):
        if name in self.source_reliability:
            self.source_reliability[name] = max(0.0, min(1.0, reliability))