import json
from typing import Any, Optional, Dict, Union

import orjson
import redis
from fastapi.encoders import jsonable_encoder
from redis.connection import ConnectionPool

from app.common.config import settings
from app.common.logging import get_logger

logger = get_logger(__name__)


class RedisClient:
    """Redis client for caching and other Redis operations."""

    _pool: Optional[ConnectionPool] = None
    _client: Optional[redis.Redis] = None

    @classmethod
    def get_connection_pool(cls) -> ConnectionPool:
        """Get or create a Redis connection pool."""
        if cls._pool is None:
            logger.info(
                f"Creating Redis connection pool with {settings.redis_pool_max_connections} max connections"
            )
            cls._pool = redis.ConnectionPool(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password or None,
                max_connections=settings.redis_pool_max_connections,
                decode_responses=True,
            )
        return cls._pool

    @classmethod
    def get_client(cls) -> redis.Redis:
        """Get or create a Redis client."""
        if cls._client is None:
            logger.info(f"Creating Redis client connecting to {settings.redis_host}:{settings.redis_port}")
            cls._client = redis.Redis(connection_pool=cls.get_connection_pool())
        return cls._client

    @classmethod
    async def set_cache(cls, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a value in the cache.
        
        Args:
            key: The cache key
            value: The value to store (will be JSON serialized)
            ttl: Time to live in seconds, if None uses the default from settings
            
        Returns:
            bool: True if the value was set successfully, False otherwise
        """
        try:
            client = cls.get_client()
            ttl = ttl or settings.cache_ttl
            serialized_value = orjson.dumps(value, default=jsonable_encoder)
            result = client.set(key, serialized_value, ex=ttl)
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
            return result
        except redis.RedisError as e:
            logger.error(f"Error setting cache: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error setting cache: {e}")
            return False

    @classmethod
    async def get_cache(cls, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            The value if found and valid, None otherwise
        """
        try:
            client = cls.get_client()
            value = client.get(key)
            if value:
                logger.debug(f"Cache hit: {key}")
                return orjson.loads(value)
            logger.debug(f"Cache miss: {key}")
            return None
        except redis.RedisError as e:
            logger.error(f"Error getting cache: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding cached JSON value: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting cache: {e}")
            return None

    @classmethod
    async def delete_cache(cls, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            bool: True if the key was deleted, False otherwise
        """
        try:
            client = cls.get_client()
            result = client.delete(key)
            logger.debug(f"Cache deleted: {key}")
            return bool(result)
        except redis.RedisError as e:
            logger.error(f"Error deleting cache: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting cache: {e}")
            return False

    @classmethod
    async def health_check(cls) -> bool:
        """
        Check if Redis is healthy.
        
        Returns:
            bool: True if Redis is healthy, False otherwise
        """
        try:
            client = cls.get_client()
            return client.ping()
        except redis.RedisError as e:
            logger.error(f"Redis health check failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in Redis health check: {e}")
            return False


# Create singleton instances
redis_client = RedisClient()
