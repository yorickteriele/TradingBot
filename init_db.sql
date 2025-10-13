-- Database initialization script for Trading Bot
-- This creates the necessary tables for storing stock information and trading data

-- Create stocks table

CREATE TABLE IF NOT EXISTS nasdaq_stock(
    stock_id SERIAL PRIMARY KEY,
    symbol VARCHAR(10)  NOT NULL UNIQUE,
    company_name VARCHAR(255) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    rss_url VARCHAR(255) NOT NULL
);


-- Create index on symbol for faster lookups
CREATE INDEX IF NOT EXISTS idx_stocks_symbol ON nasdaq_stock(symbol);
CREATE INDEX IF NOT EXISTS idx_stocks_active ON nasdaq_stock(active);


-- Create trades table
CREATE TABLE IF NOT EXISTS trades(
    trade_id SERIAL PRIMARY KEY,
    stock_id INT NOT NULL,
    trade_type VARCHAR(10) NOT NULL CHECK (trade_type IN ('buy', 'sell')),
    quantity INT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    trade_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (stock_id) REFERENCES nasdaq_stock(stock_id)
);

-- Create stock_news_tracking table to track last processed article timestamp per stock
CREATE TABLE IF NOT EXISTS stock_news_tracking(
    stock_symbol VARCHAR(10) PRIMARY KEY,
    last_article_timestamp TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_stock_news_tracking_symbol ON stock_news_tracking(stock_symbol);