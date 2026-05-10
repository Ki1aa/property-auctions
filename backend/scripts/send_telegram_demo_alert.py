"""Send one realistic demo lot alert via real notify_lot_event (uses TELEGRAM_* from .env).

Seeds an in-memory SQLite DB with baseline lots + one discounted IZHS lot, then sends
the same HTML message shape as production ingest alerts.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base
from app.models import Lot, Organizer
from app.services.alerts.service import notify_lot_event

DEMO_REG = "72000000000000008888"
DEMO_JSON = (
    f"https://torgi.gov.ru/new/opendata/7710568760-notice/notice_{DEMO_REG}_"
    "00000000-0000-0000-0000-00000000demo.json"
)


async def _run() -> None:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env", file=sys.stderr)
        raise SystemExit(1)

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = Session()

    org = Organizer(source_id="demo-org", name="Демо-организатор")
    db.add(org)
    db.flush()

    # Baseline: median ~200k RUB/sotka (10 sotok = 1000 m2 @ 2M RUB).
    for i in range(5):
        db.add(
            Lot(
                source_id=f"demo-baseline-seed-{i}",
                title=f"Seed lot {i}",
                status="active",
                region="72",
                category="ZK",
                start_price=2_000_000.0,
                area_sqm=1000.0,
                organizer_id=org.id,
                is_izhs_candidate=False,
            )
        )

    start = datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
    end = datetime(2026, 6, 15, 18, 0, tzinfo=timezone.utc)

    demo = Lot(
        source_id=f"{DEMO_REG}:lot:1",
        title="Земельный участок под ИЖС (демо-карточка монитора)",
        status="active",
        region="72",
        category="ZK",
        start_price=1_400_000.0,
        current_price=1_400_000.0,
        start_date=start,
        end_date=end,
        area_sqm=1000.0,
        organizer_id=org.id,
        cadastral_number="72:01:0000000:42",
        land_category="земли населённых пунктов",
        permitted_use="для индивидуального жилищного строительства",
        permitted_use_codes="2.1",
        address="Тюменская обл., демо-адрес для примера",
        municipality="Тюменский муниципальный район",
        settlement="Демо-населённый пункт",
        notice_reg_num=DEMO_REG,
        notice_lot_number="1",
        notice_lot_count=1,
        is_izhs_candidate=True,
        source_url=DEMO_JSON,
        notice_detail_url=DEMO_JSON,
        nspd_centroid_latitude=57.1522,
        nspd_centroid_longitude=65.5272,
    )
    db.add(demo)
    db.commit()

    demo_id = db.scalar(select(Lot.id).where(Lot.source_id == f"{DEMO_REG}:lot:1"))
    row = db.scalar(select(Lot).where(Lot.id == demo_id))
    await notify_lot_event(db, row, "new_lot", "demo-product-alert-v1")
    db.commit()
    db.close()
    print("Demo alert sent.")


if __name__ == "__main__":
    asyncio.run(_run())
