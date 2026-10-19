from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Lingxi Agent Service"
    app_env: str = "dev"
    app_host: str = "127.0.0.1"
    app_port: int = 8000

    chat_base_url: str | None = None
    chat_api_key: str | None = None
    chat_model: str | None = None

    database_url: str = (
        "mysql+asyncmy://root:CHANGE_ME_MYSQL_PASSWORD@127.0.0.1:3307/lingxi_agent"
    )
    test_database_url: str = (
        "mysql+asyncmy://root:CHANGE_ME_MYSQL_PASSWORD@127.0.0.1:3307/lingxi_agent_test"
    )
    checkpointer_db_path: str = "data/checkpoints.sqlite"

    business_grpc_target: str = "127.0.0.1:9090"
    business_grpc_timeout_seconds: float = 3.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
