"""Read-only MVP GIS API (parallel to legacy /api/lots)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models_mvp import MvpGisLot, MvpGisNotice

router = APIRouter(prefix="/api/mvp", tags=["mvp-gis"])


@router.get("/stats")
def mvp_stats(db: Session = Depends(get_db)) -> dict:
    notices = db.scalar(select(func.count()).select_from(MvpGisNotice)) or 0
    lots = db.scalar(select(func.count()).select_from(MvpGisLot)) or 0
    r72 = db.scalar(select(func.count()).select_from(MvpGisLot).where(MvpGisLot.region_code == "72")) or 0
    return {"mvp_gis_notices": notices, "mvp_gis_lots": lots, "lots_region_72": r72}


@router.get("/lots")
def mvp_lots_list(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    total = db.scalar(select(func.count()).select_from(MvpGisLot)) or 0
    rows = db.scalars(select(MvpGisLot).order_by(MvpGisLot.id.desc()).offset(offset).limit(limit)).all()
    items = [
        {
            "id": r.id,
            "lot_external_id": r.lot_external_id,
            "notice_number": r.notice_number,
            "lot_number": r.lot_number,
            "region_code": r.region_code,
            "title": r.title,
            "signal_level": r.signal_level,
            "is_land": r.is_land,
            "is_ignored": r.is_ignored,
            "notice_url": r.notice_url,
            "lot_url": r.lot_url,
            "nspd_url": r.nspd_url,
        }
        for r in rows
    ]
    return {"total": total, "limit": limit, "offset": offset, "items": items}
