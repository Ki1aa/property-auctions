from datetime import datetime
from typing import Any

from pydantic import BaseModel


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
    cadastral_number: str | None = None
    area_sqm: float | None = None
    municipality: str | None = None
    settlement: str | None = None
    is_izhs_candidate: bool = False
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


class LotListPage(BaseModel):
    items: list[LotListItem]
    total: int
    limit: int
    offset: int


class LotDetail(LotListItem):
    latitude: float | None
    longitude: float | None
    source_url: str | None
    organizer_name: str | None
    organizer_inn: str | None
    land_category: str | None = None
    permitted_use: str | None = None
    permitted_use_codes: str | None = None
    address: str | None = None
    notice_detail_url: str | None = None
    opendata_notice_id: int | None = None
    notice_payload: dict[str, Any] | None = None


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
