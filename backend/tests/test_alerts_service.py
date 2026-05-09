import asyncio

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Lot, Organizer
from app.services.alerts.service import notify_lot_event


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal


def test_notify_lot_event_sends_html_with_links(monkeypatch, db_session):
    sent: dict = {}

    async def capture_send(token: str, chat_id: str, text: str, **kwargs):
        sent["text"] = text
        sent["kwargs"] = kwargs

    monkeypatch.setattr("app.services.alerts.service.send_telegram_message", capture_send)
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_bot_token", "t")
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_chat_id", "1")
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_alert_only_izhs", False)
    monkeypatch.setattr("app.services.alerts.service.settings.app_public_base_url", "https://app.example")
    monkeypatch.setattr("app.services.alerts.service.settings.include_marketplace_search_urls", True)

    db = db_session()
    org = Organizer(source_id="o1", name="Org")
    db.add(org)
    db.flush()
    lot = Lot(
        source_id="72000000000000005555",
        title="Test <lot>",
        status="active",
        region="72",
        organizer_id=org.id,
        cadastral_number="72:01:1:1",
        area_sqm=600.0,
        address="Street & Co",
        start_price=1_000_000.0,
        is_izhs_candidate=False,
        source_url="https://torgi.gov.ru/n.json",
    )
    db.add(lot)
    db.commit()
    lot_id = db.scalar(select(Lot.id))
    db.refresh(lot)
    db.close()

    db2 = db_session()
    lot_row = db2.scalar(select(Lot).where(Lot.id == lot_id))

    async def _run():
        await notify_lot_event(db2, lot_row, "new_lot", "payload-for-hash")

    asyncio.run(_run())
    db2.commit()
    db2.close()

    assert sent["kwargs"].get("parse_mode") == "HTML"
    assert "<b>new_lot</b>" in sent["text"]
    assert "Test &lt;lot&gt;" in sent["text"]
    assert "Street &amp; Co" in sent["text"]
    assert "https://app.example/lots/" in sent["text"]
    assert "torgi.gov.ru" in sent["text"]
    assert "pkk.rosreestr.ru" in sent["text"]
