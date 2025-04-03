import asyncio
import pytest
import logging
from unittest.mock import AsyncMock, MagicMock, patch
import os
import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging to suppress logs during tests
logging.basicConfig(level=logging.ERROR)


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_substrate():
    """Mock AsyncSubstrateInterface for tests."""
    substrate = AsyncMock()
    substrate.get_chain_head.return_value = "0x1234567890abcdef"
    substrate.get_block_number.return_value = 1000000
    substrate.query.return_value = AsyncMock(value=1000)
    
    # Configure query_map behavior
    mock_iter = AsyncMock()
    mock_iter.__aiter__.return_value = [("key1", AsyncMock(value=100)), ("key2", AsyncMock(value=200))]
    substrate.query_map.return_value = mock_iter
    
    return substrate


@pytest.fixture
def mock_subtensor():
    """Mock AsyncSubtensor for tests."""
    subtensor = AsyncMock()
    subtensor.__aenter__.return_value = subtensor
    subtensor.__aexit__.return_value = None
    subtensor.add_stake.return_value = True
    subtensor.unstake.return_value = True
    return subtensor


@pytest.fixture
def mock_wallet():
    """Mock Wallet for tests."""
    wallet = MagicMock()
    wallet.coldkey_file = MagicMock()
    wallet.coldkey_file.save_password_to_env = MagicMock()
    wallet.unlock_coldkey = MagicMock()
    wallet.hotkey = MagicMock()
    wallet.hotkey.ss58_address = "5Cr4JKFyCMgeQScSu14SVoKAMLaabEt6Bvc6fxL8eok2nsa"
    return wallet


@pytest.fixture
def mock_db_session():
    """Mock SQLAlchemy session for tests."""
    session = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = None
    session.begin.return_value.__aenter__.return_value = None
    session.begin.return_value.__aexit__.return_value = None
    session.commit = AsyncMock()
    session.add_all = MagicMock()
    return session


@pytest.fixture
def mock_async_session_maker(mock_db_session):
    """Mock SQLAlchemy sessionmaker for tests."""
    session_maker = MagicMock()
    session_maker.return_value = mock_db_session
    return session_maker


@pytest.fixture
def mock_redis_pool():
    """Mock Redis pool for tests."""
    redis_conn = AsyncMock()
    redis_conn.get.return_value = None  # Default to cache miss
    redis_conn.set.return_value = True
    
    pool = AsyncMock()
    pool.__aenter__.return_value = redis_conn
    pool.__aexit__.return_value = None
    
    return pool
