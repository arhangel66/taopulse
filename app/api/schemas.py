from datetime import datetime

from pydantic import BaseModel


class TradeInstantResult(BaseModel):
    stake_tx_triggered: bool
    netuid: int


class TaoDividentsResult(BaseModel):
    dividends: dict[int, dict[str, int]]
    collected_at: datetime
    cached: bool
    trade: TradeInstantResult
