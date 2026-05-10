from datetime import datetime
from typing import Any

from pydantic import BaseModel


class LotNoticeAttributeItem(BaseModel):
    code: str
    value_text: str | None = None
    value_json: Any | None = None
    source: str = "notice_detail"
    ordinal: int = 0


class LotListItem(BaseModel):
    id: int
    source_id: str
    title: str
    status: str | None
    region: str | None
    category: str | None
    start_price: float | None
    current_price: float | None
    start_date: datetime | None
    end_date: datetime | None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    source_url: str | None = None
    cadastral_number: str | None = None
    area_sqm: float | None = None
    municipality: str | None = None
    settlement: str | None = None
    is_izhs_candidate: bool = False
    notice_reg_num: str | None = None
    notice_lot_number: str | None = None
    notice_lot_count: int | None = None
    # From notice: start_price / area; not market valuation. None if price or area missing.
    start_price_per_sotka: float | None = None
    start_price_per_sqm: float | None = None
    # Internal baseline from loaded auction data; not an external market valuation.
    baseline_price_per_sotka: float | None = None
    discount_to_baseline: float | None = None
    valuation_confidence: str | None = None
    valuation_baseline_scope: str | None = None
    valuation_baseline_sample_size: int | None = None
    valuation_reason: str | None = None
    # NSPD enrichment: none = never fetched; enriched = got card/area/cost/address; no_data = fetch OK but empty.
    nspd_data_status: str | None = None
    # True when NSPD or notice lat/lon can anchor map links.
    map_centroid_available: bool = False
    # Median ₽/sotka from imported MarketComparable rows (separate from auction baseline).
    market_baseline_price_per_sotka: float | None = None
    discount_to_market: float | None = None
    market_valuation_reason: str | None = None
    investment_score: float | None = None
    # Deep links (see external_lot_links); Domclick search URLs are best-effort when enabled.
    app_lot_url: str | None = None
    # Concrete GIS Torgi lot page when notice and lot numbers are known.
    torgi_url: str | None = None
    # GIS Torgi notice page; separate from the concrete lot link.
    torgi_notice_url: str | None = None
    torgi_json_url: str | None = None
    # NSPD public map entry point; cadastral number is shown separately to paste/search there.
    nspd_map_url: str | None = None
    # Public cadastral map (ПКК): nspd.gov.ru map query by cadastral number (PKK is hosted on NSPD).
    pkk_map_url: str | None = None
    domclick_map_url: str | None = None
    domclick_search_url: str | None = None
    domclick_search_url_cadastral: str | None = None


class LotListPage(BaseModel):
    items: list[LotListItem]
    total: int
    limit: int
    offset: int


class LotDetail(LotListItem):
    latitude: float | None
    longitude: float | None
    organizer_name: str | None
    organizer_inn: str | None
    land_category: str | None = None
    permitted_use: str | None = None
    permitted_use_codes: str | None = None
    address: str | None = None
    notice_detail_url: str | None = None
    opendata_notice_id: int | None = None
    notice_payload: dict[str, Any] | None = None
    nspd_specified_area_sqm: float | None = None
    nspd_readable_address: str | None = None
    nspd_cost_value: float | None = None
    nspd_centroid_latitude: float | None = None
    nspd_centroid_longitude: float | None = None
    nspd_map_coordinate_x: float | None = None
    nspd_map_coordinate_y: float | None = None
    nspd_card_id: str | None = None
    nspd_card_type: str | None = None
    nspd_enriched_at: datetime | None = None
    map_anchor_latitude: float | None = None
    map_anchor_longitude: float | None = None
    map_anchor_source: str | None = None
    map_anchor_updated_at: datetime | None = None
    notice_attributes: list[LotNoticeAttributeItem] = []


class MapPoint(BaseModel):
    lot_id: int
    title: str
    status: str | None
    latitude: float
    longitude: float


class HealthResponse(BaseModel):
    status: str


class IngestRunView(BaseModel):
    id: int
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    fetched_count: int
    upserted_count: int
    changed_count: int
    processed_files: int = 0
    failed_files: int = 0
    last_error_source_url: str | None = None
    error_kind: str | None = None
    error_message: str | None


class IngestStatusView(BaseModel):
    is_running: bool
    scheduler_running: bool
    next_run_at: datetime | None = None
    ingest_mode: str
    interval_minutes: int
    run_on_startup: bool
    fetch_notice_details: bool
    detail_max_per_run: int
    target_region_codes: str
    ingest_only_land_lots: bool = True
    telegram_alert_region_codes: str = ""
    telegram_digest_enabled: bool = False
    telegram_digest_interval_minutes: int = 30
    telegram_digest_next_at: datetime | None = None


class ManualIngestStartResponse(BaseModel):
    started: bool
    message: str


class OpenDataNoticeListItem(BaseModel):
    id: int
    reg_num: str
    document_type: str | None
    publish_date: datetime | None
    bidd_type_code: str | None
    href: str


class OpenDataNoticeListPage(BaseModel):
    items: list[OpenDataNoticeListItem]
    total: int
    limit: int
    offset: int


class LotFacets(BaseModel):
    category: list[str]
    status: list[str]
    region: list[str]
    municipality: list[str]


class OpenDataNoticeFacets(BaseModel):
    bidd_type_code: list[str]
    document_type: list[str]


class LotQualityMetrics(BaseModel):
    region: str | None = None
    total: int
    izhs_candidates: int
    with_municipality: int
    with_cadastral: int
    with_area: int
    with_start_price: int
    with_price_per_sotka: int
    with_baseline: int
    with_positive_discount: int
    with_nspd_enriched: int = 0
    with_map_centroid: int = 0
