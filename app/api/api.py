from fastapi import APIRouter

from app.api.schemas import TaoDividentsResult
from app.common.config import settings
from app.common.logging import get_logger
from app.common.utils import get_utc_now
from app.construct import dividend_service, execute_service
from app.common.context import update_log_context, generate_request_id
from app.trade.schemas import ExecuteInput

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
    # Generate a request_id for this API call
    request_id = generate_request_id()

    # Update the log context with request-specific information
    update_log_context(
        request_id=request_id,
    )

    logger.info(
        f"Received request for tao_dividends with netuid={netuid}, hotkey={hotkey}, trade={trade}, request_id={request_id}"
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

    execute_input = ExecuteInput(
        request_id=request_id,
        trade=trade,
        netuid=netuid or settings.default_netuid,
        hotkey=hotkey or settings.default_hotkey,
    )
    execute_instant = await execute_service.trade(execute_input)

    result = TaoDividentsResult(
        dividends=dividends, cached=False, collected_at=get_utc_now(), trade=execute_instant
    )
    # save to cache
    logger.info("Returning fresh result")
    return result
