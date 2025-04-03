from datetime import datetime
from typing import List, Dict, Any, Optional

from pydantic import BaseModel


class TradeInstantResult(BaseModel):
    stake_tx_triggered: bool
    netuid: int


class TaoDividentsResult(BaseModel):
    dividends: dict[int, dict[str, int]]
    collected_at: datetime
    cached: bool
    trade: TradeInstantResult
    request_id: str


class StorageDataResponse(BaseModel):
    request_id: str
    tweets: List[Dict[str, Any]] = []
    sentiment: Optional[Dict[str, Any]] = None
    trade: Optional[Dict[str, Any]] = None
    dividend: Optional[Dict[str, Any]] = None
