import pytest
from datetime import datetime
from performance import PerformanceTracker, Trade

@pytest.fixture
def tracker():
    return PerformanceTracker()

def test_record_entry(tracker):
    tracker.record_entry("AAPL", 150.0, 10, "Positive", 145.0)
    assert len(tracker.trades) == 1
    assert len(tracker.current_positions) == 1
    assert "AAPL" in tracker.current_positions
    
    trade = tracker.trades[0]
    assert trade.symbol == "AAPL"
    assert trade.entry_price == 150.0
    assert trade.position_size == 10
    assert trade.sentiment == "Positive"
    assert trade.stop_loss == 145.0

def test_record_exit(tracker):
    tracker.record_entry("AAPL", 150.0, 10, "Positive", 145.0)
    tracker.record_exit("AAPL", 160.0)
    
    assert len(tracker.current_positions) == 0
    assert len(tracker.trades) == 1
    
    trade = tracker.trades[0]
    assert trade.exit_price == 160.0
    assert trade.pnl == 100.0  # (160 - 150) * 10

def test_performance_metrics_empty(tracker):
    metrics = tracker.get_performance_metrics()
    assert metrics['total_trades'] == 0
    assert metrics['win_rate'] == 0
    assert metrics['total_pnl'] == 0
    assert metrics['sharpe_ratio'] == 0
    assert metrics['max_drawdown'] == 0

def test_performance_metrics(tracker):
    # Add some trades
    tracker.record_entry("AAPL", 150.0, 10, "Positive", 145.0)
    tracker.record_exit("AAPL", 160.0)
    
    tracker.record_entry("MSFT", 200.0, 5, "Positive", 195.0)
    tracker.record_exit("MSFT", 190.0)
    
    metrics = tracker.get_performance_metrics()
    assert metrics['total_trades'] == 2
    assert metrics['win_rate'] == 0.5  # One winning trade, one losing trade
    assert metrics['total_pnl'] == 50.0  # (160-150)*10 + (190-200)*5
    assert metrics['sharpe_ratio'] >= 0  # Should be a valid number
    assert metrics['max_drawdown'] >= 0  # Should be a valid number

def test_get_trade_history(tracker):
    tracker.record_entry("AAPL", 150.0, 10, "Positive", 145.0)
    tracker.record_exit("AAPL", 160.0)
    
    history = tracker.get_trade_history()
    assert len(history) == 1
    assert "symbol" in history.columns
    assert "entry_price" in history.columns
    assert "exit_price" in history.columns
    assert "pnl" in history.columns

def test_get_current_positions(tracker):
    tracker.record_entry("AAPL", 150.0, 10, "Positive", 145.0)
    
    positions = tracker.get_current_positions()
    assert len(positions) == 1
    assert "symbol" in positions.columns
    assert "entry_price" in positions.columns
    assert "position_size" in positions.columns
    assert "stop_loss" in positions.columns