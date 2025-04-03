import json
import logging
from typing import Any, Dict, Optional, Union

import redis
from redis.exceptions import RedisError

from app.common.utils import get_utc_now


class RedisClient:
    """Client for interacting with Redis cache."""

    def __init__(
        self,
        host: str,
        port: int,
        password: Optional[str] = None,
        db: int = 0,
        ttl: int = 120,  # 2 minutes default TTL
        max_connections: int = 10,
    ):
        self.pool = redis.ConnectionPool(
            host=host,
            port=port,
            password=password,
            db=db,
            max_connections=max_connections,
            decode_responses=True,
        )
        self.ttl = ttl
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_redis(self) -> redis.Redis:
        """Get a Redis client from the connection pool."""
        return redis.Redis(connection_pool=self.pool)

    def set_cache(
        self, key: str, value: Union[Dict, list, str], ttl: Optional[int] = None
    ) -> bool:
        """Set a value in the cache with TTL."""
        try:
            r = self.get_redis()
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            expiry = ttl if ttl is not None else self.ttl
            return r.set(key, value, ex=expiry)
        except RedisError as e:
            self.logger.error(f"Error setting cache for key {key}: {str(e)}")
            return False

    def get_cache(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        try:
            r = self.get_redis()
            value = r.get(key)
            if value:
                try:
                    # Try to parse as JSON
                    return json.loads(value)
                except json.JSONDecodeError:
                    # If not JSON, return as is
                    return value
            return None
        except RedisError as e:
            self.logger.error(f"Error getting cache for key {key}: {str(e)}")
            return None

    def delete_cache(self, key: str) -> bool:
        """Delete a value from the cache."""
        try:
            r = self.get_redis()
            return bool(r.delete(key))
        except RedisError as e:
            self.logger.error(f"Error deleting cache for key {key}: {str(e)}")
            return False

    def build_key(self, prefix: str, **kwargs) -> str:
        """Build a cache key with a prefix and kwargs."""
        parts = [prefix]
        for k, v in kwargs.items():
            if v is not None:
                parts.append(f"{k}:{v}")
        return ':'.join(parts)

    def close(self):
        """Close the Redis connection pool."""
        try:
            self.pool.disconnect()
        except Exception as e:
            self.logger.error(f"Error closing Redis connection pool: {str(e)}")
