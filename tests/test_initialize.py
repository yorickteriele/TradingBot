import pytest
from unittest.mock import Mock, patch
from Initialize import Account

@pytest.fixture
def mock_trading_client():
    return Mock()

@pytest.fixture
def mock_data_client():
    return Mock()

@pytest.fixture
def mock_secrets():
    return {
        'API_KEY': 'test_key',
        'API_SECRET': 'test_secret'
    }

@pytest.fixture
def account(mock_trading_client, mock_data_client, mock_secrets):
    with patch('Initialize.TradingClient', return_value=mock_trading_client), \
         patch('Initialize.StockHistoricalDataClient', return_value=mock_data_client), \
         patch('json.load', return_value=mock_secrets):
        return Account()

def test_get_portfolio(account, mock_trading_client):
    mock_position = Mock()
    mock_position.symbol = 'AAPL'
    mock_position.qty = '10'
    mock_trading_client.get_all_positions.return_value = [mock_position]
    
    portfolio = account.get_portfolio()
    assert portfolio == {'AAPL': 10.0}
    mock_trading_client.get_all_positions.assert_called_once()

def test_get_buying_power(account, mock_trading_client):
    mock_account = Mock()
    mock_account.buying_power = '1000.0'
    mock_trading_client.get_account.return_value = mock_account
    
    buying_power = account.get_buying_power()
    assert buying_power == 1000.0
    mock_trading_client.get_account.assert_called_once()

def test_get_stock_price(account, mock_data_client):
    mock_bar = Mock()
    mock_bar.close = 150.0
    mock_data_client.get_stock_bars.return_value = [mock_bar]
    
    price = account.get_stock_price('AAPL')
    assert price == 150.0
    mock_data_client.get_stock_bars.assert_called_once_with('AAPL', timeframe='1Min', limit=1)