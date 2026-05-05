from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import IngestRun, Lot, OpenDataNotice, Organizer
from app.schemas import (
    IngestRunView,
    LotDetail,
    LotFacets,
    LotListItem,
    MapPoint,
    OpenDataNoticeFacets,
    OpenDataNoticeListItem,
)
from typing import Any

router = APIRouter(prefix="/api")


def _normalize_str_list(values: list[str] | None) -> list[str] | None:
    if not values:
        return None
    cleaned = [v.strip() for v in values if v and v.strip()]
    return cleaned or None


@router.get("/lots", response_model=list[LotListItem])
def list_lots(
    region: str | None = None,
    status: str | None = None,
    category: list[str] | None = Query(default=None),
    is_izhs: bool | None = None,
    min_area: float | None = None,
    max_area: float | None = None,
    max_start_price: float | None = None,
    cadastral_number: str | None = None,
    limit: int = Query(default=100, le=1000),
    db: Session = Depends(get_db),
):
    filters = []
    if region:
        filters.append(Lot.region == region)
    if status:
        filters.append(Lot.status == status)
    categories = _normalize_str_list(category)
    if categories:
        filters.append(Lot.category.in_(categories))
    if is_izhs is not None:
        filters.append(Lot.is_izhs_candidate.is_(is_izhs))
    if min_area is not None:
        filters.append(Lot.area_sqm >= min_area)
    if max_area is not None:
        filters.append(Lot.area_sqm <= max_area)
    if max_start_price is not None:
        filters.append(Lot.start_price <= max_start_price)
    if cadastral_number:
        filters.append(Lot.cadastral_number.ilike(f"%{cadastral_number}%"))

    stmt = select(Lot).order_by(desc(Lot.updated_at)).limit(limit)
    if filters:
        stmt = stmt.where(and_(*filters))
    rows = db.scalars(stmt).all()
    return [LotListItem.model_validate(row, from_attributes=True) for row in rows]


@router.get("/lots/facets", response_model=LotFacets)
def lot_facets(db: Session = Depends(get_db)):
    def distinct_strings(column):
        rows = db.scalars(
            select(column)
            .where(column.is_not(None))
            .where(column != "")
            .distinct()
            .order_by(column)
        ).all()
        return [r for r in rows if r]

    return LotFacets(
        category=distinct_strings(Lot.category),
        status=distinct_strings(Lot.status),
        region=distinct_strings(Lot.region),
    )


@router.get("/lots/{lot_id}", response_model=LotDetail)
def get_lot(lot_id: int, db: Session = Depends(get_db)):
    row = db.execute(
        select(Lot, Organizer)
        .join(Organizer, Organizer.id == Lot.organizer_id, isouter=True)
        .where(Lot.id == lot_id)
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Lot not found")
    lot, organizer = row

    notice_payload: dict[str, Any] | None = None
    if lot.opendata_notice_id is not None:
        notice = db.scalar(select(OpenDataNotice).where(OpenDataNotice.id == lot.opendata_notice_id))
        if notice is not None and isinstance(notice.payload, dict):
            notice_payload = notice.payload

    return LotDetail(
        id=lot.id,
        source_id=lot.source_id,
        title=lot.title,
        status=lot.status,
        region=lot.region,
        category=lot.category,
        start_price=lot.start_price,
        current_price=lot.current_price,
        start_date=lot.start_date,
        end_date=lot.end_date,
        latitude=lot.latitude,
        longitude=lot.longitude,
        source_url=lot.source_url,
        organizer_name=organizer.name if organizer else None,
        organizer_inn=organizer.inn if organizer else None,
        cadastral_number=lot.cadastral_number,
        area_sqm=lot.area_sqm,
        is_izhs_candidate=bool(lot.is_izhs_candidate),
        land_category=lot.land_category,
        permitted_use=lot.permitted_use,
        address=lot.address,
        notice_detail_url=lot.notice_detail_url,
        opendata_notice_id=lot.opendata_notice_id,
        notice_payload=notice_payload,
    )


@router.get("/lots-map", response_model=list[MapPoint])
def map_points(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Lot).where(Lot.latitude.is_not(None), Lot.longitude.is_not(None)).order_by(desc(Lot.updated_at)).limit(5000)
    ).all()
    return [
        MapPoint(
            lot_id=row.id,
            title=row.title,
            status=row.status,
            latitude=row.latitude,  # type: ignore[arg-type]
            longitude=row.longitude,  # type: ignore[arg-type]
        )
        for row in rows
    ]


@router.get("/ingest-runs", response_model=list[IngestRunView])
def get_ingest_runs(limit: int = Query(default=20, le=200), db: Session = Depends(get_db)):
    rows = db.scalars(select(IngestRun).order_by(desc(IngestRun.started_at)).limit(limit)).all()
    return [IngestRunView.model_validate(row, from_attributes=True) for row in rows]


@router.get("/opendata-notices/facets", response_model=OpenDataNoticeFacets)
def opendata_notice_facets(db: Session = Depends(get_db)):
    def distinct_strings(column):
        rows = db.scalars(
            select(column)
            .where(column.is_not(None))
            .where(column != "")
            .distinct()
            .order_by(column)
        ).all()
        return [r for r in rows if r]

    return OpenDataNoticeFacets(
        bidd_type_code=distinct_strings(OpenDataNotice.bidd_type_code),
        document_type=distinct_strings(OpenDataNotice.document_type),
    )


@router.get("/opendata-notices", response_model=list[OpenDataNoticeListItem])
def list_opendata_notices(
    document_type: list[str] | None = Query(default=None),
    bidd_type_code: list[str] | None = Query(default=None),
    reg_num: str | None = None,
    limit: int = Query(default=200, le=1000),
    db: Session = Depends(get_db),
):
    filters = []
    doc_types = _normalize_str_list(document_type)
    if doc_types:
        filters.append(OpenDataNotice.document_type.in_(doc_types))
    bidd_types = _normalize_str_list(bidd_type_code)
    if bidd_types:
        filters.append(OpenDataNotice.bidd_type_code.in_(bidd_types))
    if reg_num:
        filters.append(OpenDataNotice.reg_num == reg_num)

    stmt = select(OpenDataNotice).order_by(desc(OpenDataNotice.publish_date)).limit(limit)
    if filters:
        stmt = stmt.where(and_(*filters))

    rows = db.scalars(stmt).all()
    return [OpenDataNoticeListItem.model_validate(row, from_attributes=True) for row in rows]
