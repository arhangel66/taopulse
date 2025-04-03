from app.common.config import settings
from app.dividends.bittensor_service import DividendService
from app.storage.storage import PeriodicSaveStorage
from app.trade.execute_service import ExecuteService
from app.trade.sentiment_service import SentimentService
from app.trade.trade_service import TradeService
from app.trade.tweets_service import TweetsService, TweetsServiceMocked

dividend_service = DividendService()
# trade_service = TradeService()

if settings.mocked_twitter:
    tweet_service = TweetsServiceMocked(settings.twitter_bearer_token)
else:
    tweet_service = TweetsService(settings.twitter_bearer_token)

sentiment_service = SentimentService(token=settings.chutes_token)
trade_service = TradeService(
    hotkey_ss58=settings.wallet_hotkey,
    wallet_name=settings.wallet_name,
    hotkey_name=settings.hotkey_name,
    network=settings.network,
)

database_url = (
    settings.database_url or "postgresql+asyncpg://postgres:postgres@postgres:5432/taopulse"
)
storage = PeriodicSaveStorage(db_url=database_url, save_interval=2.0)

execute_service = ExecuteService(tweet_service, sentiment_service, trade_service, storage)
