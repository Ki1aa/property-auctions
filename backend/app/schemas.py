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
    is_izhs_candidate: bool = False


class LotDetail(LotListItem):
    latitude: float | None
    longitude: float | None
    source_url: str | None
    organizer_name: str | None
    organizer_inn: str | None
    land_category: str | None = None
    permitted_use: str | None = None
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
    error_message: str | None


class OpenDataNoticeListItem(BaseModel):
    id: int
    reg_num: str
    document_type: str | None
    publish_date: datetime | None
    bidd_type_code: str | None
    href: str


class LotFacets(BaseModel):
    category: list[str]
    status: list[str]
    region: list[str]


class OpenDataNoticeFacets(BaseModel):
    bidd_type_code: list[str]
    document_type: list[str]
