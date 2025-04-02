from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.common.config import settings
from app.common.schemas import BaseResponse


class Tweet(BaseModel):
    text: str
    created_at: datetime


class ExecuteInput(BaseModel):
    request_id: str
    trade: bool
    netuid: int = Field(default=settings.default_netuid)
    hotkey: str = Field(default=settings.default_hotkey)


class TweetResponse(BaseResponse):
    tweets: list[Tweet]


class SentimentResponse(BaseResponse):
    sentiment: int
    tweets_count: int


class ActionEnum(StrEnum):
    stake = "stake"
    unstake = "unstake"


class TradeResult(BaseResponse):
    action: ActionEnum | None = None
    amount: float | None = None
