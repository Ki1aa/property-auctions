import asyncio

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Lot, LotSnapshot, Organizer
from app.services.alerts.service import notify_lot_event
from app.services.lot_baseline import LotValuation


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
    monkeypatch.setattr("app.services.alerts.service.settings.include_marketplace_map_urls", True)

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
        nspd_centroid_latitude=57.1522,
        nspd_centroid_longitude=65.5272,
        source_url="https://torgi.gov.ru/new/opendata/7710568760-notice/notice_72000000000000005555_702bf5e5-c1fe-43d9-b713-b52e485c6eea.json",
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
    assert "<b>Новый лот: проверить при наличии времени</b>" in sent["text"]
    assert "ГИС: извещение 72000000000000005555" in sent["text"]
    assert "Сигналы:" in sent["text"]
    assert "ИЖС: нет" in sent["text"]
    assert "Baseline считается по уже загруженным торгам" in sent["text"]
    assert "Test &lt;lot&gt;" in sent["text"]
    assert "Street &amp; Co" in sent["text"]
    assert "https://app.example/lots/" in sent["text"]
    assert "torgi.gov.ru" in sent["text"]
    assert "pkk.rosreestr.ru" not in sent["text"]
    assert "НСПД карта" in sent["text"]
    assert "https://nspd.gov.ru/map?thematic=PKK" in sent["text"]
    assert "query=72:01:1:1" in sent["text"]
    assert "Домклик (карта района)" in sent["text"]
    assert "offer_type=lot" in sent["text"]
    assert "cian.ru" in sent["text"]
    assert sent["kwargs"].get("disable_web_page_preview") is True


def test_notify_skipped_when_telegram_disabled(monkeypatch, db_session):
    sent: dict = {}

    async def capture_send(*a, **kw):
        sent["hit"] = True

    monkeypatch.setattr("app.services.alerts.service.send_telegram_message", capture_send)
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_alerts_enabled", False)
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_bot_token", "t")
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_chat_id", "1")

    db = db_session()
    org = Organizer(source_id="o2", name="Org")
    db.add(org)
    db.flush()
    lot = Lot(
        source_id="s1",
        title="L",
        status="active",
        region="72",
        organizer_id=org.id,
        is_izhs_candidate=False,
        source_url="https://torgi.gov.ru/x.json",
    )
    db.add(lot)
    db.commit()
    lot_row = db.scalar(select(Lot).where(Lot.source_id == "s1"))
    asyncio.run(notify_lot_event(db, lot_row, "new_lot", "p1"))
    db.commit()
    db.close()
    assert "hit" not in sent


def test_notify_skipped_when_require_cadastral(monkeypatch, db_session):
    sent: dict = {}

    async def capture_send(*a, **kw):
        sent["hit"] = True

    monkeypatch.setattr("app.services.alerts.service.send_telegram_message", capture_send)
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_alerts_enabled", True)
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_alert_require_cadastral", True)
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_bot_token", "t")
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_chat_id", "1")

    db = db_session()
    org = Organizer(source_id="o3", name="Org")
    db.add(org)
    db.flush()
    lot = Lot(
        source_id="s2",
        title="L",
        organizer_id=org.id,
        is_izhs_candidate=False,
        cadastral_number=None,
        source_url="https://torgi.gov.ru/x.json",
    )
    db.add(lot)
    db.commit()
    lot_row = db.scalar(select(Lot).where(Lot.source_id == "s2"))
    asyncio.run(notify_lot_event(db, lot_row, "new_lot", "p2"))
    db.commit()
    db.close()
    assert "hit" not in sent


def test_notify_skips_low_signal_lot_by_default(monkeypatch, db_session):
    sent: dict = {}

    async def capture_send(*a, **kw):
        sent["hit"] = True

    monkeypatch.setattr("app.services.alerts.service.send_telegram_message", capture_send)
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_alerts_enabled", True)
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_alert_skip_low_signal", True)
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_bot_token", "t")
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_chat_id", "1")

    db = db_session()
    org = Organizer(source_id="o8", name="Org")
    db.add(org)
    db.flush()
    lot = Lot(
        source_id="low-signal",
        title="Тестовый лот",
        region="ХМАО",
        organizer_id=org.id,
        cadastral_number=None,
        area_sqm=None,
        start_price=10.0,
        current_price=12.0,
        is_izhs_candidate=False,
        source_url="https://torgi.gov.ru/x.json",
    )
    db.add(lot)
    db.commit()
    lot_row = db.scalar(select(Lot).where(Lot.source_id == "low-signal"))
    asyncio.run(notify_lot_event(db, lot_row, "new_lot", "p-low"))
    db.commit()
    db.close()

    assert "hit" not in sent


def test_notify_low_signal_can_be_forced_for_debug(monkeypatch, db_session):
    sent: dict = {}

    async def capture_send(token: str, chat_id: str, text: str, **kwargs):
        sent["text"] = text

    monkeypatch.setattr("app.services.alerts.service.send_telegram_message", capture_send)
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_alerts_enabled", True)
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_alert_skip_low_signal", False)
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_bot_token", "t")
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_chat_id", "1")

    db = db_session()
    org = Organizer(source_id="o9", name="Org")
    db.add(org)
    db.flush()
    lot = Lot(
        source_id="low-signal-debug",
        title="Тестовый лот",
        region="ХМАО",
        organizer_id=org.id,
        area_sqm=None,
        start_price=10.0,
        current_price=12.0,
        is_izhs_candidate=False,
        source_url="https://torgi.gov.ru/x.json",
    )
    db.add(lot)
    db.commit()
    lot_row = db.scalar(select(Lot).where(Lot.source_id == "low-signal-debug"))
    asyncio.run(notify_lot_event(db, lot_row, "new_lot", "p-low-debug"))
    db.commit()
    db.close()

    assert "<b>Новый лот: недостаточно данных для оценки</b>" in sent["text"]
    assert "Сигналы:" in sent["text"]
    assert "Нет площади для расчёта цены за сотку." in sent["text"]
    assert "Почему попало" not in sent["text"]


def test_notify_skipped_when_discount_below_min(monkeypatch, db_session):
    sent: dict = {}

    async def capture_send(*a, **kw):
        sent["hit"] = True

    def fake_valuation(lot, idx):
        return LotValuation(discount_to_baseline=0.05)

    monkeypatch.setattr("app.services.alerts.service.send_telegram_message", capture_send)
    monkeypatch.setattr("app.services.lot_baseline.lot_valuation", fake_valuation)
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_alert_min_discount_to_baseline", 0.1)
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_bot_token", "t")
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_chat_id", "1")

    db = db_session()
    org = Organizer(source_id="o4", name="Org")
    db.add(org)
    db.flush()
    lot = Lot(
        source_id="s3",
        title="L",
        organizer_id=org.id,
        is_izhs_candidate=False,
        source_url="https://torgi.gov.ru/x.json",
    )
    db.add(lot)
    db.commit()
    lot_row = db.scalar(select(Lot).where(Lot.source_id == "s3"))
    asyncio.run(notify_lot_event(db, lot_row, "new_lot", "p3"))
    db.commit()
    db.close()
    assert "hit" not in sent


def test_notify_sent_when_discount_meets_min(monkeypatch, db_session):
    sent: dict = {}

    async def capture_send(*a, **kw):
        sent["hit"] = True

    def fake_valuation(lot, idx):
        return LotValuation(discount_to_baseline=0.15)

    monkeypatch.setattr("app.services.alerts.service.send_telegram_message", capture_send)
    monkeypatch.setattr("app.services.lot_baseline.lot_valuation", fake_valuation)
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_alert_min_discount_to_baseline", 0.1)
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_bot_token", "t")
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_chat_id", "1")
    monkeypatch.setattr("app.services.alerts.service.settings.app_public_base_url", "https://app.example")

    db = db_session()
    org = Organizer(source_id="o5", name="Org")
    db.add(org)
    db.flush()
    lot = Lot(
        source_id="s4",
        title="L",
        organizer_id=org.id,
        is_izhs_candidate=False,
        source_url="https://torgi.gov.ru/x.json",
    )
    db.add(lot)
    db.commit()
    lot_row = db.scalar(select(Lot).where(Lot.source_id == "s4"))
    asyncio.run(notify_lot_event(db, lot_row, "new_lot", "p4"))
    db.commit()
    db.close()
    assert sent.get("hit") is True


def test_notify_skipped_when_min_discount_requires_missing_baseline(monkeypatch, db_session):
    sent: dict = {}

    async def capture_send(*a, **kw):
        sent["hit"] = True

    def fake_valuation(lot, idx):
        return LotValuation(discount_to_baseline=None)

    monkeypatch.setattr("app.services.alerts.service.send_telegram_message", capture_send)
    monkeypatch.setattr("app.services.lot_baseline.lot_valuation", fake_valuation)
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_alert_min_discount_to_baseline", 0.1)
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_alert_require_baseline_for_discount", True)
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_bot_token", "t")
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_chat_id", "1")

    db = db_session()
    org = Organizer(source_id="o7", name="Org")
    db.add(org)
    db.flush()
    lot = Lot(
        source_id="s6",
        title="L",
        organizer_id=org.id,
        is_izhs_candidate=True,
        cadastral_number="72:01:1:3",
        source_url="https://torgi.gov.ru/x.json",
    )
    db.add(lot)
    db.commit()
    lot_row = db.scalar(select(Lot).where(Lot.source_id == "s6"))
    asyncio.run(notify_lot_event(db, lot_row, "new_lot", "p6"))
    db.commit()
    db.close()
    assert "hit" not in sent


def test_notify_verdict_marks_interesting_izhs_discount(monkeypatch, db_session):
    sent: dict = {}

    async def capture_send(token: str, chat_id: str, text: str, **kwargs):
        sent["text"] = text

    def fake_valuation(lot, idx):
        return LotValuation(
            baseline_price_per_sotka=200_000.0,
            discount_to_baseline=0.25,
            valuation_confidence="medium",
            valuation_reason="fake baseline",
        )

    monkeypatch.setattr("app.services.alerts.service.send_telegram_message", capture_send)
    monkeypatch.setattr("app.services.lot_baseline.lot_valuation", fake_valuation)
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_alert_min_discount_to_baseline", None)
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_bot_token", "t")
    monkeypatch.setattr("app.services.alerts.service.settings.telegram_chat_id", "1")
    monkeypatch.setattr("app.services.alerts.service.settings.include_marketplace_search_urls", False)

    db = db_session()
    org = Organizer(source_id="o6", name="Org")
    db.add(org)
    db.flush()
    lot = Lot(
        source_id="72000000000000005556:lot:2",
        title="ИЖС участок",
        organizer_id=org.id,
        cadastral_number="72:01:1:2",
        area_sqm=1000.0,
        start_price=1_500_000.0,
        permitted_use="для индивидуального жилищного строительства",
        permitted_use_codes="2.1",
        is_izhs_candidate=True,
        source_url="https://torgi.gov.ru/x.json",
    )
    db.add(lot)
    db.flush()
    db.add(
        LotSnapshot(
            lot_id=lot.id,
            payload_hash="snapshot",
            payload={"_notice_lot_count": 3, "_notice_lot": {"lotNumber": "2"}},
        )
    )
    db.commit()
    lot_row = db.scalar(select(Lot).where(Lot.source_id == "72000000000000005556:lot:2"))
    asyncio.run(notify_lot_event(db, lot_row, "new_lot", "p5"))
    db.commit()
    db.close()

    assert "<b>Новый лот: интересно, смотреть глубже</b>" in sent["text"]
    assert "ГИС: извещение 72000000000000005556, лот 2 из 3" in sent["text"]
    assert "ВРИ похож на ИЖС" in sent["text"]
    assert "дисконт 25.0%" in sent["text"]
