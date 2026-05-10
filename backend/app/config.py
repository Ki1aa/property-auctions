from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

NspdFieldMergePolicy = Literal["notice_only", "nspd_when_notice_missing", "prefer_nspd"]


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
    # MVP scope: persist only land plots / land-right lots, not vehicles or other assets.
    ingest_only_land_lots: bool = True

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    # Master switch: set false to disable all Telegram sends (ingest still runs).
    telegram_alerts_enabled: bool = True
    # When true, Telegram alerts are sent only for lots with is_izhs_candidate.
    telegram_alert_only_izhs: bool = False
    # When true, skip Telegram if cadastral_number is empty (after detail ingest).
    telegram_alert_require_cadastral: bool = False
    # When true, require either internal baseline discount or notice price per sotka (reduces noise).
    telegram_alert_require_discount_or_per_sotka: bool = False
    # Skip alerts that have no practical decision signal: not IZHS, no cadastral, no area-based price/baseline.
    telegram_alert_skip_low_signal: bool = True
    # Minimum discount_to_baseline (0..1) to send; unset = no threshold.
    # Lots without baseline still pass unless telegram_alert_require_baseline_for_discount is true.
    telegram_alert_min_discount_to_baseline: float | None = None
    # When min discount is set, skip lots without a calculated baseline discount.
    telegram_alert_require_baseline_for_discount: bool = False
    # Telegram sendMessage: hide link preview on the first URL (alerts stay compact).
    telegram_disable_web_page_preview: bool = True
    # Hard cap for Bot API text length (Telegram limit is 4096).
    telegram_max_message_length: int = 4096
    # Extra attempts when Telegram returns HTTP 429 (rate limit).
    telegram_send_max_retries: int = 2
    # Optional HTTP(S) proxy for Telegram Bot API, e.g. http://127.0.0.1:7890.
    telegram_proxy_url: str = ""
    # Telegram Bot API send timeout in seconds.
    telegram_timeout_seconds: float = 20.0
    # Batch alerts into one Telegram message on an interval (uses telegram_digest_items table).
    telegram_digest_enabled: bool = False
    telegram_digest_interval_minutes: int = 30
    # Base URL of the SPA (no trailing slash), e.g. https://monitor.example.com — for Telegram and API deep links.
    app_public_base_url: str = ""
    # Best-effort Domclick/Avito/Cian search URLs from cadastral/address; off by default because they can return captcha/empty results.
    include_marketplace_search_urls: bool = False
    # Minimal always-visible aggregator links by cadastral/region; no scraping, just manual lookup entry points.
    include_marketplace_quick_links: bool = True
    # Map links around a known lot centroid; useful for manual analog inspection and does not scrape aggregators.
    include_marketplace_map_urls: bool = True
    marketplace_map_radius_km: float = 5.0
    # Marketplace listing search templates; `{q}` is replaced with URL-encoded query (see external_lot_links).
    domclick_search_template: str = "https://domclick.ru/search?query={q}"
    avito_land_search_template: str = "https://www.avito.ru/all/zemelnye_uchastki?q={q}"
    cian_land_search_template: str = "https://www.cian.ru/kupit-zemelniy-uchastok/?text={q}"

    # NSPD geoportal (nspd.gov.ru). Off by default; enable when server has route to RU endpoints.
    nspd_enabled: bool = False
    nspd_base_url: str = "https://nspd.gov.ru"
    nspd_geoportal_search_path: str = "/api/geoportal/v1/search/geoportal"
    # 1 = land plots per recon scripts.
    nspd_geoportal_thematic_id: int = 1
    nspd_timeout_seconds: int = 30
    # Keep true by default; set false only for local split-tunnel environments with broken TLS chain.
    nspd_verify_tls: bool = True
    # Max NSPD HTTP calls per ingest run; 0 = no limit.
    nspd_max_per_run: int = 100
    # Skip new NSPD fetch if last enrichment is newer than this many days.
    nspd_refresh_after_days: int = 14
    # How to merge NSPD area into Lot.area_sqm (notice detail remains primary by default).
    nspd_merge_area_policy: NspdFieldMergePolicy = "notice_only"
    # How to merge NSPD readable address into Lot.address.
    nspd_merge_address_policy: NspdFieldMergePolicy = "notice_only"

    # If true, run one operational ingest when ingest_runs is empty (dev convenience).
    # Set false in production to avoid heavy work on process start.
    run_ingest_on_startup: bool = False

    @field_validator("telegram_alert_min_discount_to_baseline", mode="before")
    @classmethod
    def _empty_discount_to_none(cls, v: object) -> object:
        if v == "" or v is None:
            return None
        return v

    @field_validator("nspd_merge_area_policy", "nspd_merge_address_policy", mode="before")
    @classmethod
    def _normalize_nspd_merge_policy(cls, v: object) -> object:
        if v == "" or v is None:
            return "notice_only"
        return v


settings = Settings()
