from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models import Lot, LotSnapshot
from app.services.ingest.service import _upsert_lot


def test_upsert_creates_snapshot_and_is_idempotent():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db: Session = SessionLocal()

    payload = {
        "source_id": "lot-1",
        "title": "Тестовый лот",
        "status": "active",
        "region": "ХМАО",
        "category": "Имущество",
        "start_price": 10.0,
        "current_price": 12.0,
        "start_date": None,
        "end_date": None,
        "latitude": None,
        "longitude": None,
        "source_url": "https://example.com",
        "organizer": {"source_id": "org-1", "name": "Орг 1", "inn": None, "kpp": None},
        "raw": {"id": "lot-1", "price": 12.0},
    }

    import asyncio

    changed_first = asyncio.run(_upsert_lot(db, payload))
    changed_second = asyncio.run(_upsert_lot(db, payload))

    lots = db.scalars(select(Lot)).all()
    snapshots = db.scalars(select(LotSnapshot)).all()

    assert changed_first is True
    assert changed_second is False
    assert len(lots) == 1
    assert len(snapshots) == 1
