import asyncio
from time import time
from typing import Dict, List, Optional
import datetime
import json
import orjson
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.common.logging import get_logger
from app.common.utils import get_utc_now
from app.storage.models import Base, Tweet, SentimentAnalysis, Trade, Dividend
from app.trade.schemas import SentimentResponse, Tweet as TweetSchema
from app.trade.schemas import TweetResponse, TradeResult
from fastapi.encoders import jsonable_encoder

logger = get_logger(__name__)


class PeriodicSaveStorage:
    """
    Storage class that periodically bulk inserts objects into the database.
    Items are queued and then inserted in batches every save_interval seconds.
    """

    def __init__(
        self,
        db_url: str,
        save_interval: float = 1.0,
        max_queue_size: int = 1000,
    ):
        """
        Initialize the storage.

        Args:
            db_url: Database connection URL
            save_interval: How often to save queued items (in seconds)
            max_queue_size: Maximum items to queue before forcing a save
        """
        self.db_url = db_url
        self.save_interval = save_interval
        self.max_queue_size = max_queue_size

        # Create separate queues for each model type
        self.queues: Dict[str, List[Base]] = {
            "tweets": [],
            "sentiment_analyses": [],
            "trades": [],
            "dividends": [],
        }

        self.engine = create_async_engine(db_url)
        self.async_session = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

        self._running = False
        self._task = None

    async def start(self):
        """Start the periodic save task."""
        if self._running:
            return

        # Initialize database schema
        async with self.engine.begin() as conn:
            # Create tables if they don't exist
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database schema initialized")

        self._running = True
        self._task = asyncio.create_task(self._periodic_save())
        logger.info("PeriodicSaveStorage started")

    async def stop(self):
        """Stop the periodic save task and save any remaining items."""
        if not self._running:
            return

        self._running = False
        if self._task:
            await self._task
            self._task = None

        # Save any remaining items
        await self._save_all()
        logger.info("PeriodicSaveStorage stopped")

    async def _periodic_save(self):
        """Task that periodically saves all queued items."""
        while self._running:
            try:
                await asyncio.sleep(self.save_interval)
                await self._save_all()
            except Exception as e:
                logger.error(f"Error in periodic save: {e}")

    async def _save_all(self):
        t1 = time()
        """Save all queued items for all model types."""
        for model_type, queue in self.queues.items():
            if queue:
                try:
                    count = len(queue)
                    items_to_save = queue.copy()
                    self.queues[model_type] = []

                    async with self.async_session() as session:
                        async with session.begin():
                            session.add_all(items_to_save)
                        await session.commit()

                    logger.info(f"Saved {count} {model_type}, time: {time() - t1:.2f}s")
                except Exception as e:
                    # Put items back in queue if save fails
                    self.queues[model_type].extend(items_to_save)
                    logger.error(f"Error saving {model_type}: {e}")

    def queue_item(self, model_type: str, item: Base):
        """
        Queue an item for saving.

        Args:
            model_type: Type of model ("tweets", "sentiment_analyses", "trades", or "dividends")
            item: SQLAlchemy model instance to save
        """
        if model_type not in self.queues:
            raise ValueError(f"Unknown model type: {model_type}")

        self.queues[model_type].append(item)

        # Force save if queue gets too large
        if len(self.queues[model_type]) >= self.max_queue_size:
            asyncio.create_task(self._save_model_type(model_type))

    async def _save_model_type(self, model_type: str):
        """Save all queued items for a specific model type."""
        if not self.queues[model_type]:
            return

        try:
            count = len(self.queues[model_type])
            items_to_save = self.queues[model_type].copy()
            self.queues[model_type] = []

            async with self.async_session() as session:
                async with session.begin():
                    session.add_all(items_to_save)
                await session.commit()

            logger.info(f"Saved {count} {model_type}")
        except Exception as e:
            # Put items back in queue if save fails
            self.queues[model_type].extend(items_to_save)
            logger.error(f"Error saving {model_type}: {e}")

    # Required public interface methods

    def add_sentiment(
        self, sentiment: SentimentResponse, tweets: list[TweetSchema], request_id: str
    ):
        """
        Add sentiment analysis and related tweets to storage.

        Args:
            sentiment: Sentiment analysis results
            tweets: List of tweets that were analyzed
            request_id: Unique request identifier
        """
        # Extract netuid from first tweet if available
        netuid = getattr(tweets[0], "netuid", 0) if tweets else 0

        # Create and queue sentiment analysis model
        sentiment_model = SentimentAnalysis(
            score=sentiment.sentiment,
            is_success=sentiment.is_success,
            message=sentiment.message,
            tweets_count=sentiment.tweets_count,
            duration=sentiment.duration,
            request_id=request_id,
            netuid=netuid,
            created_at=get_utc_now(),
        )
        self.queue_item("sentiment_analyses", sentiment_model)

        # Create and queue tweet models
        for tweet in tweets:
            # Сохраняем дату с часовым поясом
            tweet_model = Tweet(
                text=tweet.text,
                created_at_twitter=tweet.created_at,  # Сохраняем с часовым поясом
                request_id=request_id,
                netuid=netuid,
                created_at=get_utc_now(),
            )
            self.queue_item("tweets", tweet_model)

    def add_twitter(self, tweets_response: TweetResponse, request_id: str):
        """
        Add Twitter response data to storage.

        Args:
            tweets_response: Response from Twitter API with tweets
            request_id: Unique request identifier
        """
        # Extract netuid from API request context if available
        netuid = getattr(tweets_response, "netuid", 0)

        # Create and queue tweet models
        for tweet in tweets_response.tweets:
            # Сохраняем дату с часовым поясом
            tweet_model = Tweet(
                text=tweet.text,
                created_at_twitter=tweet.created_at,  # Сохраняем с часовым поясом
                request_id=request_id,
                netuid=netuid,
                created_at=get_utc_now(),
                duration=tweets_response.duration,
            )
            self.queue_item("tweets", tweet_model)
        logger.info(f"Added {len(tweets_response.tweets)} tweets to storage")

    def add_trade(self, trade: TradeResult, request_id: str, sentiment: int):
        """
        Add trade result to storage.

        Args:
            trade: Result of trade operation
            request_id: Unique request identifier
            sentiment: Sentiment score that triggered this trade
        """
        # Extract netuid and hotkey from context if available
        netuid = getattr(trade, "netuid", 0)
        hotkey = getattr(trade, "hotkey", "")

        # Create and queue trade model
        trade_model = Trade(
            action=trade.action,
            amount=trade.amount,
            is_success=trade.is_success,
            message=trade.message,
            duration=trade.duration,
            request_id=request_id,
            netuid=netuid,
            hotkey=hotkey,
            sentiment_score=sentiment,
            created_at=get_utc_now(),
        )
        self.queue_item("trades", trade_model)

    def add_dividends(
        self,
        dividends: dict,
        request_id: str,
        netuid: str | None = None,
        hotkey: str | None = None,
        trade: bool = False,
    ):
        """
        Add dividend data to storage.

        Args:
            dividends: Dividend data dictionary
            request_id: Unique request identifier
            netuid: Optional subnet ID
            hotkey: Optional hotkey
            trade: Whether trade was triggered based on dividends
        """
        # Prepare dividends data to ensure all datetimes are compatible

        # Create and queue dividend model
        dividend_model = Dividend(
            netuid=netuid,
            hotkey=hotkey,
            trade_triggered=trade,
            data=orjson.dumps(dividends, default=jsonable_encoder).decode(),
            request_id=request_id,
            created_at=get_utc_now(),
        )
        self.queue_item("dividends", dividend_model)

    # Helper query methods

    async def get_tweets_by_request_id(self, request_id: str) -> List[Tweet]:
        """Get all tweets associated with a request ID."""
        async with self.async_session() as session:
            result = await session.execute(select(Tweet).where(Tweet.request_id == request_id))
            return result.scalars().all()

    async def get_sentiment_by_request_id(self, request_id: str) -> Optional[SentimentAnalysis]:
        """Get sentiment analysis associated with a request ID."""
        async with self.async_session() as session:
            result = await session.execute(
                select(SentimentAnalysis).where(SentimentAnalysis.request_id == request_id)
            )
            return result.scalars().first()

    async def get_trade_by_request_id(self, request_id: str) -> Optional[Trade]:
        """Get trade associated with a request ID."""
        async with self.async_session() as session:
            result = await session.execute(select(Trade).where(Trade.request_id == request_id))
            return result.scalars().first()

    async def get_dividend_by_request_id(self, request_id: str) -> Optional[Dividend]:
        """Get dividend data associated with a request ID."""
        async with self.async_session() as session:
            result = await session.execute(
                select(Dividend).where(Dividend.request_id == request_id)
            )
            return result.scalars().first()
