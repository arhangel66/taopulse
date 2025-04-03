from datetime import timedelta, datetime
from time import time
from typing import List, Dict, Any, Optional

import aiohttp

from app.common.config import settings
from app.common.logging import get_logger
from app.common.utils import get_utc_now
from app.trade.schemas import TweetResponse, Tweet

logger = get_logger(__name__)


class TweetsService:
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://apis.datura.ai/twitter"

    async def fetch_tweets(
        self,
        query: str,
        count: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        min_likes: int = 0,
    ) -> List[Dict[str, Any]]:
        """Fetch tweets from Twitter API.

        Args:
            query: Search query string
            count: Number of tweets to retrieve
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            min_likes: Minimum number of likes

        Returns:
            List of tweet objects
        """
        # Set default dates if not provided
        if not start_date:
            start_date = (get_utc_now() - timedelta(days=7)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = (get_utc_now() + timedelta(days=1)).strftime("%Y-%m-%d")

        payload = {
            "query": query,
            "blue_verified": False,
            "end_date": end_date,
            "is_image": False,
            "is_quote": False,
            "is_video": False,
            "lang": "en",
            "min_likes": min_likes,
            "min_replies": 0,
            "min_retweets": 0,
            "sort": "Top",
            "start_date": start_date,
            "count": count,
        }

        headers = {"Authorization": f"{self.token}", "Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url, json=payload, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"Twitter API error: {response.status} - {error_text}")

    async def get_bittensor_tweets(self, netuid: int, count: int = 10) -> TweetResponse:
        """Fetch tweets related to Bittensor.

        Args:
            netuid: Bittensor subnet ID (optional)
            count: Number of tweets to retrieve

        Returns:
            List of tweet objects
        """
        t1 = time()
        try:
            logger.info(f"Fetching tweets for netuid {netuid}")

            query = f"Bittensor netuid {netuid}"

            response = await self.fetch_tweets(query=query, count=count)
            tweets = [
                Tweet(
                    text=twit["text"],
                    created_at=datetime.strptime(twit["created_at"], "%a %b %d %H:%M:%S %z %Y"),
                )
                for twit in response
            ]
            tweets = tweets[:count]
            result = TweetResponse(
                tweets=tweets,
                duration=round(time() - t1, 2),
            )
            logger.info(f"Received {len(tweets)} tweets for netuid {netuid}")
            return result
        except Exception as e:
            logger.error(f"Error fetching tweets: {e}")
            return TweetResponse(
                tweets=[],
                duration=round(time() - t1, 2),
                message=str(e),
                is_success=False,
            )


class TweetsServiceMocked(TweetsService):
    async def fetch_tweets(
        self,
        query: str,
        count: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        min_likes: int = 0,
    ) -> List[Dict[str, Any]]:
        """Mocked function to fetch tweets from Twitter API."""
        return [
            {
                "text": "this is good",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            for _ in range(count)
        ]


if __name__ == "__main__":

    async def main():
        service = TweetsService(settings.twitter_bearer_token)
        tweets = await service.get_bittensor_tweets(1)
        print(tweets)

    import asyncio

    asyncio.run(main())
