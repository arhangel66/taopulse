from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
import json
from typing import Dict, Any

from app.api.schemas import TaoDividentsResult, StorageDataResponse
from app.common.config import settings
from app.common.logging import get_logger
from app.common.utils import get_utc_now
from app.construct import dividend_service, execute_service, storage
from app.common.context import update_log_context, generate_request_id
from app.trade.schemas import ExecuteInput
from app.api.security import get_current_active_user, Token, fake_hash_password
from app.api.security.auth import fake_users_db, User
from app.common.redis_client import redis_client

# Initialize logger
logger = get_logger(__name__)

# v1
router = APIRouter(tags=["v1"], prefix="/api/v1")

DEFAULT_NETUID = 18


async def get_cached_result(cache_key: str):
    """Get cached result from Redis"""
    try:
        return await redis_client.get_cache(cache_key)
    except Exception as e:
        logger.error(f"Error getting cached result for key {cache_key}: {e}")
        return None


async def set_cached_result(cache_key: str, result: Any, ttl: int = 120):
    """Save result to Redis cache with TTL"""
    try:
        return await redis_client.set_cache(cache_key, result, ttl=ttl)
    except Exception as e:
        logger.error(f"Error setting cached result for key {cache_key}: {e}")
        return False


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """Эндпоинт для получения токена доступа"""
    user_dict = fake_users_db.get(form_data.username)
    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = User(**user_dict)
    hashed_password = fake_hash_password(form_data.password)
    if not hashed_password == user_dict["hashed_password"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # В этой упрощенной версии просто возвращаем имя пользователя как токен
    return {"access_token": user.username, "token_type": "bearer"}


@router.get("/tao_dividends")
async def get_tao_dividends(
    netuid: str | None = None,
    hotkey: str | None = None,
    trade: bool = False,
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    # Generate a request_id for this API call
    request_id = generate_request_id()

    # Update the log context with request-specific information
    update_log_context(
        request_id=request_id,
    )

    logger.info(
        f"Received request for tao_dividends with netuid={netuid}, hotkey={hotkey}, trade={trade}, request_id={request_id}, user={current_user.username}"
    )
    cache_key = f"tao_dividends:{netuid}_{hotkey}_{trade}"
    cached_result = await get_cached_result(cache_key)
    if cached_result:
        cached_result["cached"] = True
        logger.info(f"Returning cached result for {cache_key}")
        return cached_result

    # if cache_result exists - return cache result
    logger.debug("Cache miss, querying blockchain")
    dividends = await dividend_service.get_dividends(netuid, hotkey)
    storage.add_dividends(dividends, request_id, netuid, hotkey, trade)

    execute_input = ExecuteInput(
        request_id=request_id,
        trade=trade,
        netuid=netuid or settings.default_netuid,
        hotkey=hotkey or settings.default_hotkey,
    )
    execute_instant = await execute_service.trade(execute_input)

    result = TaoDividentsResult(
        dividends=dividends,
        cached=False,
        collected_at=get_utc_now(),
        trade=execute_instant,
        request_id=request_id,
    )
    # save to cache with 2-minute TTL
    await set_cached_result(cache_key, result, ttl=settings.cache_ttl)

    logger.info("Returning fresh result")
    return result


@router.get("/storage/{request_id}", response_model=StorageDataResponse)
async def get_storage_data(
    request_id: str, current_user: Annotated[User, Depends(get_current_active_user)] = None
):
    """
    Retrieve all stored data for a specific request_id
    """
    logger.info(
        f"Retrieving storage data for request_id={request_id}, user={current_user.username}"
    )

    try:
        # Get tweets
        tweets = await storage.get_tweets_by_request_id(request_id)
        tweets_list = [
            {
                "id": str(tweet.id),
                "text": tweet.text,
                "created_at_twitter": (
                    tweet.created_at_twitter.isoformat() if tweet.created_at_twitter else None
                ),
                "created_at": tweet.created_at.isoformat(),
                "netuid": tweet.netuid,
                "query_text": tweet.query_text,
            }
            for tweet in tweets
        ]

        # Get sentiment analysis
        sentiment = await storage.get_sentiment_by_request_id(request_id)
        sentiment_data = None
        if sentiment:
            sentiment_data = {
                "id": str(sentiment.id),
                "score": sentiment.score,
                "is_success": sentiment.is_success,
                "message": sentiment.message,
                "tweets_count": sentiment.tweets_count,
                "created_at": sentiment.created_at.isoformat(),
                "netuid": sentiment.netuid,
                "hotkey": sentiment.hotkey,
                "analysis_breakdown": sentiment.analysis_breakdown,
            }

        # Get trade
        trade = await storage.get_trade_by_request_id(request_id)
        trade_data = None
        if trade:
            trade_data = {
                "id": str(trade.id),
                "netuid": trade.netuid,
                "hotkey": trade.hotkey,
                "amount": trade.amount,
                "action": trade.action,
                "is_success": trade.is_success,
                "message": trade.message,
                "sentiment_score": trade.sentiment_score,
                "created_at": trade.created_at.isoformat(),
            }

        # Get dividend
        dividend = await storage.get_dividend_by_request_id(request_id)
        dividend_data = None
        if dividend:
            dividend_data = {
                "id": str(dividend.id),
                "netuid": dividend.netuid,
                "hotkey": dividend.hotkey,
                "trade_triggered": dividend.trade_triggered,
                "data": dividend.data,
                "created_at": dividend.created_at.isoformat(),
            }

        response = StorageDataResponse(
            request_id=request_id,
            tweets=tweets_list,
            sentiment=sentiment_data,
            trade=trade_data,
            dividend=dividend_data,
        )

        logger.info(
            f"Retrieved storage data for request_id={request_id}: "
            f"{len(tweets_list)} tweets, "
            f"sentiment: {'yes' if sentiment_data else 'no'}, "
            f"trade: {'yes' if trade_data else 'no'}, "
            f"dividend: {'yes' if dividend_data else 'no'}"
        )

        return response

    except Exception as e:
        logger.error(f"Error retrieving storage data for request_id={request_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve storage data: {str(e)}")
