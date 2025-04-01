from app.common.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


class DividendService:
    async def get_dividends(
        self, netuid: int | None = None, hotkey: str | None = None
    ) -> dict[int, dict[str, int]]:
        logger.info(f"Querying dividends with netuid={netuid}, hotkey={hotkey}")
        # for ever
        logger.debug("Returning mock dividend data for now")
        return {}
