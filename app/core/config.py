from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "neo-reels-backend"
    log_level: str = "info"

    database_url: str
    redis_url: str

    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "videos"
    minio_region: str = "us-east-1"

    jwt_secret_key: str
    jwt_refresh_secret_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 43200

    allowed_content_types: list[str] = [
        "video/mp4",
        "video/quicktime",
        "video/x-m4v",
        "video/webm",
    ]
    max_upload_size_bytes: int = 1024 * 1024 * 500


@lru_cache
def get_settings() -> Settings:
    return Settings()
