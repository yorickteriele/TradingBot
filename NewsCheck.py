import feedparser
from datetime import datetime, timedelta
import ollama
import asyncio
import aiohttp


class StockNewsAnalyzer:
    def __init__(self, model="llama3.2"):
        self.model = model
        self.latestArticles = {}

    async def get_latest_news(self, rss_url, company_name):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(rss_url) as response:
                    data = await response.text()
                    feed = feedparser.parse(data)
                    if not feed.get('entries'):
                        return None

                    item = feed['entries'][0]
                    try:
                        article_time = datetime.fromisoformat(item['published'].replace("Z", "+00:00")).astimezone(tz=None).replace(tzinfo=None)


                        if company_name not in self.latestArticles:
                            self.latestArticles[company_name] = datetime.now()

                        last_time = self.latestArticles[company_name]


                        if article_time > last_time:
                            self.latestArticles[company_name] = article_time
                            return item
                        return None
                    except KeyError:
                        return None
            except aiohttp.ClientConnectorError as e:
                print(f"Network error while accessing {rss_url}: {e}")
                return None
            except Exception as e:
                print(f"Unexpected error while accessing {rss_url}: {e}")
                return None

    async def analyze_article_sentiment(self, title, description, companyName):
        prompt = f"""
                Article Title: {title}
                Article Description: {description}
                Company it's about: {companyName}

                Determine the sentiment about {companyName}'s stock based on the article. Base your answer on the title and description. Ensure it is relevant to {companyName}'s stock and not unrelated.

                Return Positive if it indicates or implies potential growth, optimism, or a direct/indirect positive impact on the stock.
                Return Negative if it indicates or implies potential decline, concern, or a direct/indirect negative impact on the stock.
                Return Neutral if it is unclear, balanced, or unrelated to stock performance.

                Prioritize optimism in the interpretation when the impact is ambiguous but leans positively.

                Only return the sentiment in 1 word. Positive, Neutral, or Negative. In this format:
                [Sentiment]
        """

        response = ollama.chat(
            model=self.model,
            messages=[{'role': 'user', 'content': prompt}],
            stream=True
        )

        result = ""
        for message in response:
            result += message['message']['content']

        return result.strip()

    async def get_stock_analysis(self, stockListEntry):
        company_name = stockListEntry[2] 
        rss_url = stockListEntry[3]

        news_item = await self.get_latest_news(rss_url, company_name)

        if news_item is None:
            return None

        title = news_item['title']
        description = news_item['description']
        sentiment = await self.analyze_article_sentiment(title, description, company_name)
        return {
            'title': title,
            'sentiment': sentiment
        }

