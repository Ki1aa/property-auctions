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

    # Empty means ingest all regions; comma-separated codes can narrow ingest scope.
    target_region_codes: str = ""
    izhs_keywords: str = "ИЖС,индивидуальное жилищное строительство,для индивидуального жилого"
    ingest_fetch_notice_details: bool = True
    ingest_detail_max_per_run: int = 200

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    # When true, Telegram alerts are sent only for lots with is_izhs_candidate.
    telegram_alert_only_izhs: bool = False
    # Telegram sendMessage: hide link preview on the first URL (alerts stay compact).
    telegram_disable_web_page_preview: bool = True
    # Hard cap for Bot API text length (Telegram limit is 4096).
    telegram_max_message_length: int = 4096
    # Extra attempts when Telegram returns HTTP 429 (rate limit).
    telegram_send_max_retries: int = 2
    # Base URL of the SPA (no trailing slash), e.g. https://monitor.example.com — for Telegram and API deep links.
    app_public_base_url: str = ""
    # Best-effort Domclick/Avito/Cian search URLs from cadastral/address; disable if you want fewer outbound links.
    include_marketplace_search_urls: bool = True
    # Marketplace listing search templates; `{q}` is replaced with URL-encoded query (see external_lot_links).
    domclick_search_template: str = "https://domclick.ru/search?query={q}"
    avito_land_search_template: str = "https://www.avito.ru/all/zemelnye_uchastki?q={q}"
    cian_land_search_template: str = "https://www.cian.ru/kupit-uchastok/?text={q}"

    # NSPD geoportal (nspd.gov.ru). Off by default; enable when server has route to RU endpoints.
    nspd_enabled: bool = False
    nspd_base_url: str = "https://nspd.gov.ru"
    nspd_geoportal_search_path: str = "/api/geoportal/v1/search/geoportal"
    # 1 = land plots per recon scripts.
    nspd_geoportal_thematic_id: int = 1
    nspd_timeout_seconds: int = 30
    # Max NSPD HTTP calls per ingest run; 0 = no limit.
    nspd_max_per_run: int = 100
    # Skip new NSPD fetch if last enrichment is newer than this many days.
    nspd_refresh_after_days: int = 14

    # If true, run one operational ingest when ingest_runs is empty (dev convenience).
    # Set false in production to avoid heavy work on process start.
    run_ingest_on_startup: bool = False


settings = Settings()
