# Trading Bot - News Sentiment Analysis

An automated trading bot that analyzes news articles from multiple financial sources and makes stock trading decisions based on sentiment analysis using AI/ML models.

## Features

- **News Sentiment Analysis**: Uses FinBERT (financial sentiment analysis model) to analyze news from Reuters, Bloomberg, Yahoo Finance, and other sources
- **Automated Trading**: Executes buy/sell orders through Alpaca API based on sentiment scores
- **Risk Management**: Implements position sizing, stop-loss orders, and portfolio correlation checks
- **Performance Tracking**: Tracks trades, calculates P&L, win rate, Sharpe ratio, and drawdown
- **Multi-source News**: Aggregates news from multiple reliable financial sources with weighted reliability scores
- **Async Processing**: Efficient asynchronous processing of multiple stocks simultaneously

## How It Works

1. **News Collection**: The bot fetches news articles from configured RSS feeds (Reuters, Bloomberg, Yahoo Finance, etc.)
2. **Sentiment Analysis**: Each article is analyzed using FinBERT to determine if the sentiment is Positive, Negative, or Neutral
3. **Weighted Scoring**: Sentiments are weighted by source reliability and article relevance
4. **Trading Decisions**:
   - **Positive Sentiment** → Buy stock (if not already holding)
   - **Negative Sentiment** → Sell stock (if currently holding)
   - **Neutral Sentiment** → No action
5. **Risk Management**: Position sizes are calculated based on account value, volatility, and risk parameters
6. **Execution**: Orders are submitted to Alpaca with stop-loss protection

## Prerequisites

- Python 3.8+
- PostgreSQL database
- Alpaca trading account (paper or live)
- Docker (optional, for containerized deployment)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd TradingBot
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Database

Create a PostgreSQL database and initialize the schema:

```bash
# Create database
createdb tradingbot

# Initialize tables
psql -d tradingbot -f init_db.sql
```

### 4. Configure Environment Variables

Copy the template and fill in your credentials:

```bash
copy env.template .env
```

Edit `.env` with your Alpaca API credentials:

```env
ALPACA_API_KEY=PKHOKG7ODBSRVCFJZBU6
ALPACA_SECRET_KEY=86gt74JgclwPhZbepaefFeTZj0ByzFFRHgDj9l8p
DB_HOST=localhost
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=tradingbot
CHECK_INTERVAL=300
```

Alternatively, create a `secrets.json` file:

```json
{
    "API_KEY": "your_alpaca_api_key",
    "API_SECRET": "your_alpaca_secret_key",
    "DB_HOST": "localhost",
    "DB_USER": "postgres",
    "DB_PASSWORD": "postgres",
    "DB_NAME": "tradingbot"
}
```

### 5. Get Alpaca API Credentials

1. Sign up at [Alpaca](https://alpaca.markets/)
2. Create a paper trading account (recommended for testing)
3. Generate API keys from the dashboard
4. Add keys to your `.env` file or `secrets.json`

## Usage

### Run Locally

```bash
python main.py
```

The bot will:

- Initialize all components
- Fetch stock list from database (or use defaults)
- Analyze news for each stock every 5 minutes (configurable)
- Execute trades based on sentiment
- Display performance metrics

### Run with Docker

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f bot

# Stop services
docker-compose down
```

## Configuration

### Risk Parameters

Edit `trading_bot/core/risk_manager.py` to adjust risk settings:

```python
@dataclass
class RiskParameters:
    max_position_size: float = 0.1          # Max 10% of portfolio per position
    max_portfolio_risk: float = 0.02        # Risk 2% of portfolio per trade
    stop_loss_atr_multiplier: float = 2.0   # Stop loss at 2x ATR
    position_sizing_atr_multiplier: float = 1.0
    max_correlation_threshold: float = 0.7  # Avoid highly correlated positions
```

### News Sources

Add or modify news sources in `trading_bot/core/news_analyzer.py`:

```python
self.sources = {
    "reuters": ["https://www.reutersagency.com/feed/..."],
    "bloomberg": ["https://www.bloomberg.com/feeds/..."],
    # Add your custom RSS feeds here
}
```

### Stock Watchlist

Add stocks to monitor by inserting into the database:

```sql
INSERT INTO stocks (symbol, company_name, sector, industry) 
VALUES ('NVDA', 'NVIDIA Corporation', 'Technology', 'Semiconductors');
```

## Project Structure

```python
TradingBot/
├── trading_bot/
│   ├── core/
│   │   ├── news_analyzer.py       # News fetching and sentiment analysis
│   │   ├── initializer.py         # Account and trading client setup
│   │   ├── risk_manager.py        # Risk management and position sizing
│   │   └── performance_tracker.py # Trade tracking and metrics
│   ├── data/
│   │   └── db/                    # Database files
│   └── utils/
│       └── browser.py             # Web scraping utilities
├── main.py                        # Main bot entry point
├── init_db.sql                    # Database schema
├── requirements.txt               # Python dependencies
├── docker-compose.yml             # Docker configuration
├── Dockerfile.bot                 # Bot container
└── README.md                      # This file
```

## Database Schema

### `stocks` Table

- Stores stock symbols and company information
- Default stocks: AAPL, MSFT, GOOGL, AMZN, TSLA, etc.

### `trades` Table

- Records all trade entries and exits
- Tracks P&L, sentiment, and stop-loss levels

### `news_articles` Table

- Caches analyzed news to avoid reprocessing
- Stores sentiment scores and relevance

## Performance Metrics

The bot tracks:

- **Total Trades**: Number of completed trades
- **Win Rate**: Percentage of profitable trades
- **Total P&L**: Cumulative profit/loss
- **Sharpe Ratio**: Risk-adjusted returns
- **Max Drawdown**: Largest peak-to-trough decline

## Important Notes

**Risk Warning**: This bot is for educational purposes. Always test with paper trading first. Real trading involves significant risk of loss.

**API Limits**: Be mindful of Alpaca API rate limits. The bot includes rate limiting (3 stocks per batch, 2-second delays).

**Model Downloads**: First run will download FinBERT and NER models (~1GB). This may take several minutes.

**News Access**: Some RSS feeds may require authentication or have rate limits. Monitor logs for errors.

## Troubleshooting

### Database Connection Error

```
Database error: could not connect to server
```

**Solution**: Ensure PostgreSQL is running and credentials in `.env` are correct.

### Alpaca API Error

```
ERROR: ALPACA_API_KEY and ALPACA_SECRET_KEY must be set!
```

**Solution**: Add your Alpaca credentials to `.env` or `secrets.json`.

### Model Download Issues

```
Error loading model: Connection timeout
```

**Solution**: Check internet connection. Models are downloaded from Hugging Face on first run.

### No News Found

```
Sentiment: Neutral | Confidence: 0.00
```

**Solution**: RSS feeds may be down or require authentication. Check feed URLs are accessible.

## Development

### Run Tests

```bash
pytest tests/
```

### Add New Features

1. Create feature branch
2. Implement changes
3. Add tests
4. Submit pull request

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## Support

For issues or questions, please open a GitHub issue.
