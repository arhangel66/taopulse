import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import datetime
import asyncio
from app.storage.storage import PeriodicSaveStorage
from app.storage.models import Tweet, SentimentAnalysis, Trade, Dividend
from app.trade.schemas import TweetResponse, SentimentResponse, TradeResult, Tweet as TweetSchema


@pytest.mark.asyncio
async def test_initialize_storage(mock_async_session_maker):
    """Test that storage initialization creates tables."""
    # Arrange
    mock_conn = AsyncMock()
    mock_conn.run_sync = AsyncMock()
    
    # Patch engine.begin() to properly support async context manager
    class MockBeginContextManager:
        async def __aenter__(self):
            return mock_conn
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    mock_engine = AsyncMock()
    mock_engine.begin = MagicMock(return_value=MockBeginContextManager())
    
    # Create a completed future instead of an AsyncMock for the task
    mock_task = asyncio.Future()
    mock_task.set_result(None)  # Завершённая задача
    
    # Patch asyncio.create_task to avoid background task
    with patch('app.storage.storage.create_async_engine', return_value=mock_engine), \
         patch('app.storage.storage.sessionmaker', return_value=mock_async_session_maker), \
         patch('app.storage.storage.asyncio.create_task', return_value=mock_task):
        # Act
        storage = PeriodicSaveStorage("postgresql+asyncpg://test:test@localhost/test")
        await storage.start()
        
        # Assert
        assert storage._running is True
        mock_engine.begin.assert_called_once()
        mock_conn.run_sync.assert_called_once()
        
        # Отключаем задачу напрямую, без await
        storage._running = False
        storage._task = None


@pytest.mark.asyncio
async def test_queue_and_save_items(mock_async_session_maker):
    """Test that items are queued and saved correctly."""
    # Arrange
    mock_engine = AsyncMock()
    
    # Создаем правильные асинхронные контекстные менеджеры с вложенностью
    class MockBeginContextManager:
        async def __aenter__(self):
            return None
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    class MockSessionContextManager:
        def __init__(self):
            self.session = AsyncMock()
            self.session.add_all = AsyncMock()
            self.session.commit = AsyncMock()
            self.session.begin = MagicMock(return_value=MockBeginContextManager())
        
        async def __aenter__(self):
            return self.session
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    # Создаем экземпляр нашего контекстного менеджера и назначаем его как возвращаемое значение mock_async_session_maker
    mock_session_cm = MockSessionContextManager()
    mock_async_session_maker.return_value = mock_session_cm
    
    with patch('app.storage.storage.create_async_engine', return_value=mock_engine), \
         patch('app.storage.storage.sessionmaker', return_value=mock_async_session_maker), \
         patch('app.storage.storage.asyncio.create_task', return_value=AsyncMock()):
        # Act
        storage = PeriodicSaveStorage(
            "postgresql+asyncpg://test:test@localhost/test", 
            save_interval=0.1, 
            max_queue_size=5
        )
        
        # Create some test items
        tweet = Tweet(text="Test tweet", netuid=18, request_id="test-request", created_at=datetime.datetime.now(datetime.UTC))
        storage.queue_item("tweets", tweet)
        
        # Verify item was queued
        assert len(storage.queues["tweets"]) == 1
        assert storage.queues["tweets"][0] == tweet
        
        # Force a save
        await storage._save_all()
        
        # Assert correct database operations were called
        mock_session_cm.session.add_all.assert_called_once()
        mock_session_cm.session.commit.assert_called_once()
        
        # Verify queue was cleared
        assert len(storage.queues["tweets"]) == 0


@pytest.mark.asyncio
async def test_add_sentiment(mock_async_session_maker):
    """Test that add_sentiment correctly processes sentiment and tweets."""
    # Arrange
    mock_engine = AsyncMock()
    
    with patch('app.storage.storage.create_async_engine', return_value=mock_engine), \
         patch('app.storage.storage.sessionmaker', return_value=mock_async_session_maker), \
         patch('app.storage.storage.get_utc_now', return_value=datetime.datetime(2025, 4, 3, 12, 0, 0)):
        # Act
        storage = PeriodicSaveStorage("postgresql+asyncpg://test:test@localhost/test")
        
        # Create test sentiment and tweets
        sentiment = SentimentResponse(
            sentiment=5,
            is_success=True,
            message="Success",
            tweets_count=2,
            duration=1.5
        )
        
        tweets = [
            TweetSchema(
                text="Test tweet 1",
                created_at=datetime.datetime(2025, 4, 3, 11, 0, 0),
                netuid=18
            ),
            TweetSchema(
                text="Test tweet 2",
                created_at=datetime.datetime(2025, 4, 3, 11, 30, 0),
                netuid=18
            )
        ]
        
        # Call the method under test
        storage.add_sentiment(sentiment, tweets, "test-request-id")
        
        # Assert - проверяем, что созданы правильные элементы
        assert len(storage.queues["sentiment_analyses"]) == 1
        assert len(storage.queues["tweets"]) == 2
        
        # Verify sentiment analysis was created correctly
        sentiment_analysis = storage.queues["sentiment_analyses"][0]
        assert sentiment_analysis.score == 5
        assert sentiment_analysis.is_success is True
        assert sentiment_analysis.message == "Success"
        assert sentiment_analysis.tweets_count == 2
        assert sentiment_analysis.duration == 1.5
        assert sentiment_analysis.request_id == "test-request-id"
        assert sentiment_analysis.netuid == 0  # Ожидаем 0, так как netuid не является частью схемы Tweet
        
        # Verify tweets were created correctly
        assert storage.queues["tweets"][0].text == "Test tweet 1"
        assert storage.queues["tweets"][1].text == "Test tweet 2"


@pytest.mark.asyncio
async def test_add_dividends(mock_async_session_maker):
    """Test that add_dividends correctly processes dividend data."""
    # Arrange
    mock_engine = AsyncMock()
    
    with patch('app.storage.storage.create_async_engine', return_value=mock_engine), \
         patch('app.storage.storage.sessionmaker', return_value=mock_async_session_maker), \
         patch('app.storage.storage.get_utc_now', return_value=datetime.datetime(2025, 4, 3, 12, 0, 0)):
        # Act
        storage = PeriodicSaveStorage("postgresql+asyncpg://test:test@localhost/test")
        
        # Create test dividend data
        dividend_data = {
            "18": {
                "5Cr4JKFyCMgeQScSu14SVoKAMLaabEt6Bvc6fxL8eok2nsa": 1000,
                "5F2CsUDVbRbVMXTh9fAzF9GacjVX7UapvRxidrxe7z8BYckQ": 2000
            },
            "19": {
                "5Cr4JKFyCMgeQScSu14SVoKAMLaabEt6Bvc6fxL8eok2nsa": 500
            }
        }
        
        # Call the method under test - исправляем вызов метода, убираем параметр duration
        storage.add_dividends(dividend_data, "test-request-id")
        
        # Assert - должен быть только 1 элемент (Dividend объект с данными в JSON)
        assert len(storage.queues["dividends"]) == 1
        
        # Verify dividend record was created correctly
        dividend = storage.queues["dividends"][0]
        assert dividend.request_id == "test-request-id"
        assert dividend.created_at is not None
