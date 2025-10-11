import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from trading_bot.core.news_analyzer import NewsAnalyzer, NewsArticle, NewsSource

@pytest.fixture
def news_analyzer():
    with patch('news_analysis.pipeline') as mock_pipeline:
        mock_pipeline.return_value = Mock(return_value=[{'label': 'positive', 'score': 0.9}])
        analyzer = NewsAnalyzer()
        return analyzer

@pytest.mark.asyncio
async def test_analyze_article(news_analyzer):
    title = "Company XYZ Reports Strong Earnings"
    content = "Company XYZ announced better than expected earnings for Q3 2025"
    source = "reuters"
    url = "https://example.com/article"
    
    article = await news_analyzer.analyze_article(title, content, source, url)
    
    assert isinstance(article, NewsArticle)
    assert article.title == title
    assert article.content == content
    assert article.source == source
    assert article.url == url
    assert article.sentiment_score == 1.0  # Positive sentiment
    assert 0 <= article.relevance_score <= 1.0
    assert article.source_reliability == 0.9  # Reuters reliability score

@pytest.mark.asyncio
async def test_fetch_article_content(news_analyzer):
    with patch('newspaper.Article') as MockArticle:
        mock_article = Mock()
        mock_article.text = "Sample article content"
        MockArticle.return_value = mock_article
        
        content = await news_analyzer.fetch_article_content("https://example.com/article")
        assert content == "Sample article content"
        
        MockArticle.assert_called_once_with("https://example.com/article")
        mock_article.download.assert_called_once()
        mock_article.parse.assert_called_once()

@pytest.mark.asyncio
async def test_get_aggregated_sentiment(news_analyzer):
    mock_articles = [
        NewsArticle(
            title="Positive News",
            content="Good content",
            source="reuters",
            url="https://example.com/1",
            published_date=datetime.now(),
            sentiment_score=0.8,
            relevance_score=0.9,
            source_reliability=0.9
        ),
        NewsArticle(
            title="Negative News",
            content="Bad content",
            source="bloomberg",
            url="https://example.com/2",
            published_date=datetime.now(),
            sentiment_score=-0.6,
            relevance_score=0.7,
            source_reliability=0.9
        )
    ]
    
    with patch.object(news_analyzer, 'get_articles_from_source', return_value=mock_articles):
        sentiment, confidence = await news_analyzer.get_aggregated_sentiment("AAPL")
        assert sentiment in ["Positive", "Negative", "Neutral"]
        assert 0 <= confidence <= 1.0

def test_add_news_source(news_analyzer):
    name = "test_source"
    url = "https://example.com/feed"
    reliability = 0.8
    
    news_analyzer.add_news_source(name, url, reliability)
    
    assert url in news_analyzer.sources[name]
    assert news_analyzer.source_reliability[name] == reliability

def test_update_source_reliability(news_analyzer):
    name = "reuters"
    new_reliability = 0.95
    
    news_analyzer.update_source_reliability(name, new_reliability)
    assert news_analyzer.source_reliability[name] == new_reliability
    
    # Test bounds
    news_analyzer.update_source_reliability(name, 1.5)
    assert news_analyzer.source_reliability[name] == 1.0
    
    news_analyzer.update_source_reliability(name, -0.5)
    assert news_analyzer.source_reliability[name] == 0.0