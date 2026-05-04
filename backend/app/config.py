from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str = "postgresql+psycopg://gis_user:gis_password@db:5432/gis_torgi"
    ingest_source_url: str = "https://torgi.gov.ru/new/public/opendata/61f2a3bf11d8ab36f6c1b275"
    ingest_structure_url: str = ""
    ingest_mode: str = "operational"
    backfill_from: str = ""
    backfill_to: str = ""
    torgi_opendata_registry_url: str = "https://torgi.gov.ru/new/opendata/list.json"
    torgi_opendata_dataset_id: str = "7710568760-notice"
    torgi_opendata_card_url: str = "https://torgi.gov.ru/new/public/opendata/61f2a3bf11d8ab36f6c1b275"
    ingest_daily_offset_days: int = -1
    ingest_provider: str = "torgi_opendata"
    supported_structure_versions: str = "20240401"
    ingest_interval_minutes: int = 1440
    ingest_timeout_seconds: int = 30
    ingest_retry_count: int = 3

    # Land plot focus (Tyumen + IZHS).
    target_region_codes: str = ""
    izhs_keywords: str = "ИЖС,индивидуальное жилищное строительство,для индивидуального жилого,2.1"
    ingest_fetch_notice_details: bool = True
    ingest_detail_max_per_run: int = 200

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


settings = Settings()
