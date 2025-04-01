from app.api.schemas import TradeResult
from app.common.config import settings
from app.common.logging import get_logger
from app.trade.datura import DaturaService
from app.trade.llm import SentimentService

# Initialize logger
logger = get_logger(__name__)


class TradeService:
    def __init__(self, twitts_service: DaturaService, sentiment_service: SentimentService, trade_service):
        self.twitts_service = twitts_service
        self.sentiment_service = sentiment_service
        self.trade_service = trade_service


    async def trade(self, netuid_for_trade: int, trade: bool) -> TradeResult:
        logger.info(f"Processing trade request with netuid={netuid_for_trade}, trade={trade}")
        if trade is False:
            logger.debug("Trade flag is False, skipping trade operation")
            return TradeResult(stake_tx_triggered=False, netuid=netuid_for_trade)

        twitts = await self.twitts_service.get_bittensor_tweets(netuid_for_trade)
        sentiment = await self.sentiment_service.sentiment_twits(twitts)
        result = await self.trade_sentiment(sentiment)
        # schedule trade.
        logger.info("Would schedule trade here, but not implemented yet")
        return TradeResult(stake_tx_triggered=False, netuid=netuid_for_trade)



if __name__ == "__main__":
    async def main():
        from app.trade.datura import DaturaService
        datura = DaturaService(settings.twitter_bearer_token)
        sentiment = SentimentService(token=settings.chutes_token)
        service = TradeService(datura, sentiment, None)
        result = await service.trade(1, True)
        print(result)


    import asyncio
    asyncio.run(main())