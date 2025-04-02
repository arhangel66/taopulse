from pydantic.v1 import BaseSettings


class Settings(BaseSettings):
    """Twitter API settings."""

    twitter_bearer_token: str
    chutes_token: str

    default_netuid: int
    default_hotkey: str

    wallet_hotkey: str
    wallet_name: str
    hotkey_name: str
    network: str
    wallet_password: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
# print(settings)
