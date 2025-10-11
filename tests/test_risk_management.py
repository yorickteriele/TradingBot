import pytest
from unittest.mock import Mock, patch
import numpy as np
from datetime import datetime, timedelta
from trading_bot.core.risk_manager import RiskManager, RiskParameters
from alpaca.trading.enums import OrderSide

@pytest.fixture
def mock_trading_client():
    client = Mock()
    mock_account = Mock()
    mock_account.equity = "100000"
    client.get_account.return_value = mock_account
    return client

@pytest.fixture
def risk_manager(mock_trading_client):
    return RiskManager(mock_trading_client)

def test_calculate_position_size(risk_manager, mock_trading_client):
    mock_trade = Mock()
    mock_trade.price = "100.0"
    mock_trading_client.get_latest_trade.return_value = mock_trade
    
    position_size = risk_manager.calculate_position_size("AAPL", 100000.0, 0.2)
    
    assert position_size > 0
    assert position_size <= 100000.0 / 100.0  # Max position size check

def test_calculate_stop_loss(risk_manager):
    entry_price = 100.0
    volatility = 0.2
    
    long_stop = risk_manager.calculate_stop_loss("AAPL", OrderSide.BUY, entry_price, volatility)
    short_stop = risk_manager.calculate_stop_loss("AAPL", OrderSide.SELL, entry_price, volatility)
    
    assert long_stop < entry_price
    assert short_stop > entry_price

def test_check_portfolio_correlation(risk_manager, mock_trading_client):
    with patch.object(risk_manager, '_calculate_correlation', return_value=0.5):
        portfolio = {"MSFT": 10.0}
        result = risk_manager.check_portfolio_correlation("AAPL", portfolio)
        assert result is True
        
        with patch.object(risk_manager, '_calculate_correlation', return_value=0.8):
            result = risk_manager.check_portfolio_correlation("AAPL", portfolio)
            assert result is False

def test_execute_trade_with_risk_management_buy(risk_manager, mock_trading_client):
    mock_trade = Mock()
    mock_trade.price = "100.0"
    mock_trading_client.get_latest_trade.return_value = mock_trade
    mock_trading_client.get_all_positions.return_value = []
    
    with patch.object(risk_manager, '_get_volatility', return_value=0.2), \
         patch.object(risk_manager, 'check_portfolio_correlation', return_value=True):
        
        risk_manager.execute_trade_with_risk_management("AAPL", "Positive")
        mock_trading_client.submit_order.assert_called_once()
        
        order_args = mock_trading_client.submit_order.call_args[0][0]
        assert order_args.symbol == "AAPL"
        assert order_args.side == OrderSide.BUY
        assert 'stop_price' in order_args.stop_loss

def test_execute_trade_with_risk_management_sell(risk_manager, mock_trading_client):
    mock_trading_client.get_all_positions.return_value = [
        Mock(symbol="AAPL", qty="10")
    ]
    
    risk_manager.execute_trade_with_risk_management("AAPL", "Negative")
    mock_trading_client.submit_order.assert_called_once()
    
    order_args = mock_trading_client.submit_order.call_args[0][0]
    assert order_args.symbol == "AAPL"
    assert order_args.side == OrderSide.SELL
    assert order_args.qty == 10.0