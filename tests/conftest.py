"""
Pytest configuration file for the trading bot test suite.
"""
import pytest
import os
import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def test_config():
    """Provide test configuration data."""
    return {
        "api_key": "test_key",
        "api_secret": "test_secret",
        "base_url": "https://paper-api.alpaca.markets",
        "data_feed": "iex"
    }

@pytest.fixture
def mock_db():
    """Provide a mock database connection."""
    class MockDB:
        def __init__(self):
            self.data = {}
        
        def insert(self, key, value):
            self.data[key] = value
        
        def get(self, key):
            return self.data.get(key)
    
    return MockDB()