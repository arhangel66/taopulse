from asyncio.tasks import sleep

from app.api.schemas import TradeInstantResult
from app.common.config import settings
from app.common.logging import get_logger
from app.storage.storage import PeriodicSaveStorage
from app.trade.schemas import ExecuteInput
from app.trade.sentiment_service import SentimentService
from app.trade.trade_service import TradeService
from app.trade.tweets_service import TweetsService
import asyncio

# Initialize logger
logger = get_logger(__name__)


class ExecuteService:
    def __init__(
        self,
        tweets_service: TweetsService,
        sentiment_service: SentimentService,
        trade_service: TradeService,
        storage: PeriodicSaveStorage,
    ):
        self.tweets_service = tweets_service
        self.sentiment_service = sentiment_service
        self.trade_service = trade_service
        self.storage = storage

    async def trade(self, input: ExecuteInput) -> TradeInstantResult:
        logger.info(f"Processing trade request {input}")

        if input.trade is False:
            logger.debug("Trade flag is False, skipping trade operation")
            return TradeInstantResult(stake_tx_triggered=False, netuid=input.netuid)

        # todo add task to celery instead
        asyncio.create_task(self.background_process(input))

        return TradeInstantResult(stake_tx_triggered=True, netuid=input.netuid)

    async def background_process(self, input: ExecuteInput):
        tweets_result = await self.tweets_service.get_bittensor_tweets(input.netuid)
        self.storage.add_twitter(tweets_result, input.request_id)
        if not tweets_result.is_success:
            logger.error(f"Failed to fetch tweets for netuid {input.netuid}")
            return

        sentiment_result = await self.sentiment_service.sentiment_tweets(tweets_result.tweets)
        self.storage.add_sentiment(sentiment_result, tweets_result.tweets, input.request_id)
        logger.info(f"Sentiment result: {sentiment_result}")
        if not sentiment_result.is_success:
            logger.error(f"Failed to fetch sentiment for netuid {input.netuid}")
            return

        logger.info(f"Trade starting")
        result = await self.trade_service.trade(
            input.netuid, input.hotkey, sentiment_result.sentiment
        )

        self.storage.add_trade(result, input.request_id, sentiment_result.sentiment)
        logger.info(f"Trade result: {result}")


if __name__ == "__main__":

    async def main():
        from app.trade.tweets_service import TweetsService

        datura = TweetsService(settings.twitter_bearer_token)
        sentiment = SentimentService(token=settings.chutes_token)
        service = ExecuteService(datura, sentiment, None)
        result = await service.background_process(ExecuteInput(request_id="123", trade=True))
        print(result)

    asyncio.run(main())
