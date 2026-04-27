from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str = "postgresql+psycopg://gis_user:gis_password@db:5432/gis_torgi"
    ingest_source_url: str = "https://torgi.gov.ru/new/public/opendata/61f2a3bf11d8ab36f6c1b275"
    ingest_interval_minutes: int = 1440
    ingest_timeout_seconds: int = 30
    ingest_retry_count: int = 3
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


settings = Settings()
