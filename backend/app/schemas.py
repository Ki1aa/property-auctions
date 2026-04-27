from datetime import datetime

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


class LotDetail(LotListItem):
    latitude: float | None
    longitude: float | None
    source_url: str | None
    organizer_name: str | None
    organizer_inn: str | None


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
