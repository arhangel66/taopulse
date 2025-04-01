from fastapi import APIRouter

from app.api.schemas import TaoDividentsResult
from app.common.logging import get_logger
from app.common.utils import get_utc_now
from app.construct import dividend_service, trade_service

# Initialize logger
logger = get_logger(__name__)

# v1
router = APIRouter(tags=["v1"], prefix="/api/v1")

DEFAULT_NETUID = 18


def get_cached_result(cache_key: str):
    return None


@router.get("/tao_dividends")
async def get_tao_dividends(
        netuid: str | None = None, hotkey: str | None = None, trade: bool = False
):
    logger.info(
        f"Received request for tao_dividends with netuid={netuid}, hotkey={hotkey}, trade={trade}"
    )
    cache_key = f"{netuid}_{hotkey}"
    cached_result = get_cached_result(cache_key)
    if cached_result:
        logger.info(f"Returning cached result for {cache_key}")
        result = cached_result
        result.cached = True
        return result

    # if cache_result exists - return cache result
    logger.debug("Cache miss, querying blockchain")
    dividends = await dividend_service.get_dividends(netuid, hotkey)

    netuid_for_trade = netuid if netuid else DEFAULT_NETUID
    logger.debug(f"Processing trade with netuid={netuid_for_trade}, trade={trade}")
    trade_result = await trade_service.trade(netuid_for_trade, trade)

    result = TaoDividentsResult(
        dividends=dividends, cached=False, collected_at=get_utc_now(), trade=trade_result
    )
    # save to cache
    logger.info("Returning fresh result")
    return result
