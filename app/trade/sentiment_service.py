import re
import time

import aiohttp

from app.common.logging import get_logger
from app.trade.schemas import Tweet, SentimentResponse

logger = get_logger(__name__)
query = """
You are an expert in sentiment analysis, specializing in social media content related to blockchain and AI technologies. Your task is to analyze a set of tweets about Bittensor and decentralized AI, providing an overall sentiment score and a concise explanation of your reasoning.

Here is the list of tweets you need to analyze:

<tweets>
{TWEETS}
</tweets>

Please follow these steps to complete the sentiment analysis:

1. Read through all the tweets carefully.

2. Analyze each tweet, considering:
   - Positive and negative language
   - Enthusiasm (e.g., emojis, exclamation marks)
   - Potential sarcasm or irony
   - The overall context of Bittensor and decentralized AI

3. Assign a sentiment score to each tweet on a scale from -100 (extremely negative) to +100 (extremely positive).

4. Calculate an overall sentiment score for the entire set of tweets. This should be a weighted average, giving more importance to strongly positive or negative tweets.

5. Provide a concise analysis of your findings. Focus on the most significant factors influencing the overall sentiment. Highlight key phrases or recurring themes, and briefly mention any challenges in determining the sentiment (e.g., ambiguous language, mixed messages).

6. Give your final sentiment score as a single number between -100 and +100.

Wrap your analysis in the following tags:

<sentiment_breakdown>
- List each tweet with its individual sentiment score.
- Identify and quote key phrases that strongly influence sentiment.
- Note any recurring themes or patterns across tweets.
- Highlight any challenges in determining sentiment.
- Explain the reasoning behind the final weighted average score.
</sentiment_breakdown>

<score>
[Your final sentiment score here, as a single number between -100 and +100]
</score>

Remember to keep your analysis concise, focusing on the most significant insights that led to your final score.
"""


class SentimentService:
    def __init__(self, token: str):
        """Initialize the SentimentService with an API token.

        Args:
            token: The API token for the LLM service
        """
        self.token = token
        self.headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}

    async def invoke_chute(
        self,
        prompt: str,
        model: str = "unsloth/Llama-3.2-3B-Instruct",
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> dict:
        """Invoke the LLM API to get a response.

        Args:
            prompt: The prompt to send to the LLM
            model: The model to use
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature

        Returns:
            The response message from the LLM
        """
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://llm.chutes.ai/v1/chat/completions", headers=self.headers, json=body
            ) as response:
                data = await response.json()
                return data["choices"][0]["message"]

    async def sentiment_tweets(self, tweets: list[Tweet]) -> SentimentResponse:
        """Analyze sentiment of a list of tweets.

        Args:
            tweets: List of tweets to analyze

        Returns:
            Sentiment score as an integer between -100 and +100
        """
        logger.info(f"Analyzing sentiment of {len(tweets)} tweets")
        t1 = time.time()
        cleaned_tweets = [self.clean_twit(tweet.text) for tweet in tweets]
        if len(cleaned_tweets) == 0:
            return SentimentResponse(
                sentiment=0,
                is_success=False,
                message="No tweets to analyze",
                duration=time.time() - t1,
                tweets_count=len(tweets),
            )
        final_query = query.format(TWEETS=cleaned_tweets)

        response = await self.invoke_chute(final_query)

        # Extract the score from the response
        content = response.get("content", "")
        score_match = re.search(r"<score>[\s\S]*?(\d+)[\s\S]*?</score>", content)

        if score_match:
            return SentimentResponse(
                sentiment=int(score_match.group(1)),
                is_success=True,
                message="Sentiment score extracted successfully",
                duration=time.time() - t1,
                tweets_count=len(tweets),
            )
        else:
            logger.error(f"Failed to extract sentiment score from content: {content}")
            return SentimentResponse(
                sentiment=0,
                is_success=False,
                message="Failed to extract sentiment score",
                duration=time.time() - t1,
                tweets_count=len(tweets),
            )

    def clean_twit(self, twit: str) -> str:
        """
        Clean text by removing usernames, URLs, and special characters
        """
        # Remove usernames
        text = re.sub(r"@\w+", "", twit)

        # Remove URLs
        text = re.sub(r"https?://\S+", "", text)

        # Convert hashtags to words (optional)
        text = re.sub(r"#(\w+)", r"\1", text)

        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text
