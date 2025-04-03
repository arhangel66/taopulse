from pydantic.v1 import BaseSettings
import secrets


class Settings(BaseSettings):
    """Twitter API settings."""

    twitter_bearer_token: str
    mocked_twitter: bool = False
    chutes_token: str

    default_netuid: int
    default_hotkey: str

    wallet_hotkey: str
    wallet_name: str
    hotkey_name: str
    network: str
    wallet_password: str

    # Redis configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    cache_ttl: int = 120  # Cache expiration time in seconds (2 minutes)
    redis_pool_max_connections: int = 10  # Maximum number of connections in the Redis connection pool
    
    # Database configuration
    database_url: str = "postgresql+asyncpg://taopulse:taopulse@localhost:5432/taopulse"
    
    # Security configuration
    secret_key: str = secrets.token_urlsafe(32)  # u0413u0435u043du0435u0440u0430u0446u0438u044f u0441u043bu0443u0447u0430u0439u043du043eu0433u043e u043au043bu044eu0447u0430, u0435u0441u043bu0438 u043du0435 u0443u043au0430u0437u0430u043d u0432 .env

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
# print(settings)
