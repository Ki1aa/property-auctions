from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import IngestRun, Lot, OpenDataNotice, Organizer
from app.schemas import IngestRunView, LotDetail, LotListItem, MapPoint, OpenDataNoticeListItem

router = APIRouter(prefix="/api")


@router.get("/lots", response_model=list[LotListItem])
def list_lots(
    region: str | None = None,
    status: str | None = None,
    category: str | None = None,
    limit: int = Query(default=100, le=1000),
    db: Session = Depends(get_db),
):
    filters = []
    if region:
        filters.append(Lot.region == region)
    if status:
        filters.append(Lot.status == status)
    if category:
        filters.append(Lot.category == category)

    stmt = select(Lot).order_by(desc(Lot.updated_at)).limit(limit)
    if filters:
        stmt = stmt.where(and_(*filters))
    rows = db.scalars(stmt).all()
    return [LotListItem.model_validate(row, from_attributes=True) for row in rows]


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


@router.get("/opendata-notices", response_model=list[OpenDataNoticeListItem])
def list_opendata_notices(
    document_type: str | None = None,
    bidd_type_code: str | None = None,
    reg_num: str | None = None,
    limit: int = Query(default=200, le=1000),
    db: Session = Depends(get_db),
):
    filters = []
    if document_type:
        filters.append(OpenDataNotice.document_type == document_type)
    if bidd_type_code:
        filters.append(OpenDataNotice.bidd_type_code == bidd_type_code)
    if reg_num:
        filters.append(OpenDataNotice.reg_num == reg_num)

    stmt = select(OpenDataNotice).order_by(desc(OpenDataNotice.publish_date)).limit(limit)
    if filters:
        stmt = stmt.where(and_(*filters))

    rows = db.scalars(stmt).all()
    return [OpenDataNoticeListItem.model_validate(row, from_attributes=True) for row in rows]
