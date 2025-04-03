import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.declarative import declarative_base

from app.common.utils import get_utc_now

Base = declarative_base()


class BaseModel(AsyncAttrs):
    """Base model with common fields for all tables."""

    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    request_id = Column(String, nullable=False, index=True)
    duration = Column(Float, nullable=True)  # Store execution time in seconds


class Tweet(Base, BaseModel):
    """Model for storing tweets."""

    __tablename__ = "tweets"

    text = Column(Text, nullable=False)
    created_at_twitter = Column(DateTime(timezone=True), nullable=True)
    tweet_id = Column(String, nullable=True, index=True)

    # Additional fields for query context
    netuid = Column(Integer, nullable=False, index=True)
    query_text = Column(String, nullable=True)


class SentimentAnalysis(Base, BaseModel):
    """Model for storing sentiment analysis results."""

    __tablename__ = "sentiment_analyses"

    score = Column(Integer, nullable=False)  # Range from -100 to +100
    is_success = Column(Boolean, nullable=False, default=False)
    message = Column(Text, nullable=True)
    tweets_count = Column(Integer, nullable=False, default=0)

    # Context for the analysis
    netuid = Column(Integer, nullable=False, index=True)
    hotkey = Column(String, nullable=True, index=True)

    # Optional fields for more detailed analysis
    analysis_breakdown = Column(JSONB, nullable=True)


class Trade(Base, BaseModel):
    """Model for storing trade/stake operations."""

    __tablename__ = "trades"

    netuid = Column(Integer, nullable=False, index=True)
    hotkey = Column(String, nullable=False, index=True)
    amount = Column(Float, nullable=True)  # Amount of TAO
    action = Column(String, nullable=True)  # 'stake' or 'unstake' from ActionEnum
    is_success = Column(Boolean, nullable=False, default=False)
    message = Column(Text, nullable=True)
    sentiment_score = Column(
        Integer, nullable=True
    )  # Store the sentiment score that triggered this trade


class Dividend(Base, BaseModel):
    """Model for storing dividend data."""

    __tablename__ = "dividends"

    netuid = Column(String, nullable=True, index=True)
    hotkey = Column(String, nullable=True, index=True)
    trade_triggered = Column(Boolean, nullable=False, default=False)

    # Store the raw dividend data
    data = Column(JSONB, nullable=True)
