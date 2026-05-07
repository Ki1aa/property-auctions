import asyncio
from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import IngestManifest, IngestRun, Lot, OpenDataNotice
from app.services.ingest.discovery import DiscoveredDatasetFile, DiscoveryPlan
from app.services.ingest.service import run_ingest


def _db_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return SessionLocal()


def test_run_ingest_writes_manifest_and_is_idempotent(monkeypatch):
    db = _db_session()
    file_ref = DiscoveredDatasetFile(
        source_url="https://example.com/data-20260427T0000-20260428T0000-structure-20240401.json",
        structure_url="https://example.com/structure-20240401.json",
        data_from=datetime(2026, 4, 27, tzinfo=timezone.utc),
        data_to=datetime(2026, 4, 28, tzinfo=timezone.utc),
        schema_version="20240401",
        source_kind="registry",
    )

    async def fake_discovery_plan(*, mode: str, last_processed_to):
        return DiscoveryPlan(files=[file_ref], source_kind="registry", dataset_id="7710568760-notice")

    async def fake_fetch_with_meta(url: str):
        return {"items": [{"id": "lot-1", "title": "Lot 1"}]}, "a" * 64

    async def fake_fetch_json(url: str):
        return {"fields": []}

    def fake_normalize(item):
        return {
            "source_id": "lot-1",
            "title": "Lot 1",
            "status": "active",
            "region": "RU",
            "category": "test",
            "start_price": None,
            "current_price": None,
            "start_date": None,
            "end_date": None,
            "latitude": None,
            "longitude": None,
            "source_url": "https://example.com/lot-1",
            "organizer": {"source_id": "org-1", "name": "Org", "inn": None, "kpp": None},
            "raw": {"id": "lot-1"},
        }

    async def fake_notify(*args, **kwargs):
        return None

    monkeypatch.setattr("app.services.ingest.service.build_discovery_plan", fake_discovery_plan)
    monkeypatch.setattr("app.services.ingest.service.fetch_json_payload_with_meta", fake_fetch_with_meta)
    monkeypatch.setattr("app.services.ingest.service.fetch_json_payload", fake_fetch_json)
    monkeypatch.setattr("app.services.ingest.service.normalize_lot", fake_normalize)
    monkeypatch.setattr("app.services.ingest.service.notify_lot_event", fake_notify)
    monkeypatch.setattr("app.services.ingest.service.settings.target_region_codes", "")

    first = asyncio.run(run_ingest(db))
    second = asyncio.run(run_ingest(db))

    lots = db.scalars(select(Lot)).all()
    manifests = db.scalars(select(IngestManifest)).all()
    runs = db.scalars(select(IngestRun).order_by(IngestRun.id)).all()

    assert first["upserted_count"] == 1
    assert first["processed_files"] == 1
    assert first["failed_files"] == 0
    assert second["upserted_count"] == 0
    assert second["processed_files"] == 0
    assert second["failed_files"] == 0
    assert len(lots) == 1
    assert len(manifests) == 1
    assert manifests[0].status == "processed"
    assert len(runs) == 2
    assert runs[0].status == "success"
    assert runs[0].processed_files == 1
    assert runs[0].failed_files == 0
    assert runs[1].status == "noop"


def test_run_ingest_marks_unknown_schema(monkeypatch):
    db = _db_session()
    file_ref = DiscoveredDatasetFile(
        source_url="https://example.com/data-20260427T0000-20260428T0000-structure-20990101.json",
        structure_url="https://example.com/structure-20990101.json",
        data_from=datetime(2026, 4, 27, tzinfo=timezone.utc),
        data_to=datetime(2026, 4, 28, tzinfo=timezone.utc),
        schema_version="20990101",
        source_kind="registry",
    )

    async def fake_discovery_plan(*, mode: str, last_processed_to):
        return DiscoveryPlan(files=[file_ref], source_kind="registry", dataset_id="7710568760-notice")

    async def fake_fetch_with_meta(url: str):
        return {"items": [{"id": "lot-1"}]}, "b" * 64

    async def fake_fetch_json(url: str):
        return {"fields": []}

    monkeypatch.setattr("app.services.ingest.service.build_discovery_plan", fake_discovery_plan)
    monkeypatch.setattr("app.services.ingest.service.fetch_json_payload_with_meta", fake_fetch_with_meta)
    monkeypatch.setattr("app.services.ingest.service.fetch_json_payload", fake_fetch_json)
    monkeypatch.setattr("app.services.ingest.service.settings.supported_structure_versions", "20240401")

    result = asyncio.run(run_ingest(db))
    manifests = db.scalars(select(IngestManifest)).all()
    runs = db.scalars(select(IngestRun)).all()

    assert result["upserted_count"] == 0
    assert result["processed_files"] == 0
    assert result["failed_files"] == 1
    assert len(manifests) == 1
    assert manifests[0].status == "schema_migration_required"
    assert manifests[0].error_kind == "schema_migration_required"
    assert len(runs) == 1
    assert runs[0].status == "failed"
    assert runs[0].failed_files == 1
    assert runs[0].last_error_source_url == file_ref.source_url
    assert runs[0].error_kind == "schema_migration_required"


def test_run_ingest_rejects_torgi_error_envelope(monkeypatch):
    db = _db_session()
    file_ref = DiscoveredDatasetFile(
        source_url="https://example.com/data-20260504T0000-20260505T0000-structure-20240401.json",
        structure_url="https://example.com/structure-20240401.json",
        data_from=datetime(2026, 5, 4, tzinfo=timezone.utc),
        data_to=datetime(2026, 5, 5, tzinfo=timezone.utc),
        schema_version="20240401",
        source_kind="registry",
    )

    async def fake_discovery_plan(*, mode: str, last_processed_to):
        return DiscoveryPlan(files=[file_ref], source_kind="registry", dataset_id="7710568760-notice")

    async def fake_fetch_with_meta(url: str):
        return {"error": "Slice not published yet"}, "e" * 64

    monkeypatch.setattr("app.services.ingest.service.build_discovery_plan", fake_discovery_plan)
    monkeypatch.setattr("app.services.ingest.service.fetch_json_payload_with_meta", fake_fetch_with_meta)

    result = asyncio.run(run_ingest(db))
    manifests = db.scalars(select(IngestManifest)).all()
    runs = db.scalars(select(IngestRun)).all()

    assert result["upserted_count"] == 0
    assert result["processed_files"] == 0
    assert result["failed_files"] == 1
    assert len(manifests) == 1
    assert manifests[0].status == "failed"
    assert manifests[0].error_kind == "source_unavailable"
    assert manifests[0].error is not None
    assert len(runs) == 1
    assert runs[0].status == "failed"
    assert runs[0].failed_files == 1
    assert runs[0].last_error_source_url == file_ref.source_url
    assert runs[0].error_kind == "source_unavailable"


def test_run_ingest_applies_region_filter_and_detail_enrichment(monkeypatch):
    db = _db_session()
    file_ref = DiscoveredDatasetFile(
        source_url="https://example.com/data-20260427T0000-20260428T0000-structure-20240401.json",
        structure_url="https://example.com/structure-20240401.json",
        data_from=datetime(2026, 4, 27, tzinfo=timezone.utc),
        data_to=datetime(2026, 4, 28, tzinfo=timezone.utc),
        schema_version="20240401",
        source_kind="registry",
    )

    async def fake_discovery_plan(*, mode: str, last_processed_to):
        return DiscoveryPlan(files=[file_ref], source_kind="registry", dataset_id="7710568760-notice")

    async def fake_fetch_with_meta(url: str):
        payload = {"items": [{"id": "lot-tyumen"}, {"id": "lot-moscow"}]}
        return payload, "c" * 64

    detail_calls: list[str] = []

    async def fake_fetch_json(url: str):
        detail_calls.append(url)
        if "tyumen" in url:
            return {
                "lots": [
                    {
                        "lotName": "Участок ИЖС в Тюмени",
                        "estateAddress": "Тюменская обл., г. Тюмень",
                        "cadastralNumbers": ["72:23:0123456:7"],
                        "estateArea": 1200,
                        "permittedUse": "Для индивидуального жилищного строительства",
                        "landCategory": "Земли населённых пунктов",
                    }
                ]
            }
        return {"fields": []}

    def fake_normalize(item):
        is_tyumen = item["id"] == "lot-tyumen"
        return {
            "source_id": item["id"],
            "title": "placeholder",
            "status": "active",
            "region": "72" if is_tyumen else "77",
            "category": "ZK" if is_tyumen else "178FZ",
            "start_price": None,
            "current_price": None,
            "start_date": None,
            "end_date": None,
            "latitude": None,
            "longitude": None,
            "source_url": f"https://example.com/notice_{item['id']}.json",
            "organizer": {"source_id": "org-1", "name": "Org", "inn": None, "kpp": None},
            "raw": item,
        }

    async def fake_notify(*args, **kwargs):
        return None

    monkeypatch.setattr("app.services.ingest.service.build_discovery_plan", fake_discovery_plan)
    monkeypatch.setattr("app.services.ingest.service.fetch_json_payload_with_meta", fake_fetch_with_meta)
    monkeypatch.setattr("app.services.ingest.service.fetch_json_payload", fake_fetch_json)
    monkeypatch.setattr("app.services.ingest.service.normalize_lot", fake_normalize)
    monkeypatch.setattr("app.services.ingest.service.notify_lot_event", fake_notify)
    monkeypatch.setattr("app.services.ingest.service.settings.target_region_codes", "72")
    monkeypatch.setattr("app.services.ingest.service.settings.ingest_fetch_notice_details", True)
    monkeypatch.setattr("app.services.ingest.service.settings.izhs_keywords", "ИЖС,индивидуальное жилищное")

    result = asyncio.run(run_ingest(db))

    lots = db.scalars(select(Lot)).all()

    assert result["upserted_count"] == 1
    assert len(lots) == 1
    saved = lots[0]
    assert saved.source_id == "lot-tyumen"
    assert saved.cadastral_number == "72:23:0123456:7"
    assert saved.area_sqm == 1200.0
    assert "ИЖС" in saved.title or "Тюмени" in saved.title
    assert saved.is_izhs_candidate is True
    # Detail fetched only for the lot that passed the region filter, plus structure URL.
    assert any("notice_lot-tyumen" in url for url in detail_calls)
    assert not any("notice_lot-moscow" in url for url in detail_calls)


def test_run_ingest_retries_failed_detail_fetch_once(monkeypatch):
    db = _db_session()
    file_ref = DiscoveredDatasetFile(
        source_url="https://example.com/data-20260427T0000-20260428T0000-structure-20240401.json",
        structure_url="https://example.com/structure-20240401.json",
        data_from=datetime(2026, 4, 27, tzinfo=timezone.utc),
        data_to=datetime(2026, 4, 28, tzinfo=timezone.utc),
        schema_version="20240401",
        source_kind="registry",
    )

    async def fake_discovery_plan(*, mode: str, last_processed_to):
        return DiscoveryPlan(files=[file_ref], source_kind="registry", dataset_id="7710568760-notice")

    async def fake_fetch_with_meta(url: str):
        return {"items": [{"id": "lot-tyumen"}]}, "d" * 64

    detail_calls: list[str] = []

    async def fake_fetch_json(url: str):
        if "structure" in url:
            return {"fields": []}
        detail_calls.append(url)
        if len([u for u in detail_calls if u == url]) == 1:
            raise RuntimeError("Server disconnected without sending a response")
        return {
            "lots": [
                {
                    "lotName": "Участок ИЖС в Тюмени",
                    "cadastralNumbers": ["72:23:0123456:7"],
                    "estateArea": 1200,
                    "permittedUse": "Для индивидуального жилищного строительства",
                    "landCategory": "Земли населённых пунктов",
                }
            ]
        }

    def fake_normalize(item):
        return {
            "source_id": item["id"],
            "title": "placeholder",
            "status": "active",
            "region": "72",
            "category": "ZK",
            "start_price": None,
            "current_price": None,
            "start_date": None,
            "end_date": None,
            "latitude": None,
            "longitude": None,
            "source_url": f"https://example.com/notice_{item['id']}.json",
            "organizer": {"source_id": "org-1", "name": "Org", "inn": None, "kpp": None},
            "raw": item,
        }

    async def fake_notify(*args, **kwargs):
        return None

    async def fake_sleep(_seconds: float):
        return None

    monkeypatch.setattr("app.services.ingest.service.build_discovery_plan", fake_discovery_plan)
    monkeypatch.setattr("app.services.ingest.service.fetch_json_payload_with_meta", fake_fetch_with_meta)
    monkeypatch.setattr("app.services.ingest.service.fetch_json_payload", fake_fetch_json)
    monkeypatch.setattr("app.services.ingest.service.normalize_lot", fake_normalize)
    monkeypatch.setattr("app.services.ingest.service.notify_lot_event", fake_notify)
    monkeypatch.setattr("app.services.ingest.service.asyncio.sleep", fake_sleep)
    monkeypatch.setattr("app.services.ingest.service.settings.target_region_codes", "72")
    monkeypatch.setattr("app.services.ingest.service.settings.ingest_fetch_notice_details", True)
    monkeypatch.setattr("app.services.ingest.service.settings.izhs_keywords", "ИЖС")

    result = asyncio.run(run_ingest(db))
    saved = db.scalars(select(Lot)).one()

    assert result["upserted_count"] == 1
    assert saved.cadastral_number == "72:23:0123456:7"
    # First call raised, retry succeeded → detail fetched twice for the same href.
    assert detail_calls.count("https://example.com/notice_lot-tyumen.json") == 2


def test_run_ingest_links_lot_to_opendata_notice(monkeypatch):
    db = _db_session()
    file_ref = DiscoveredDatasetFile(
        source_url="https://example.com/data-20260427T0000-20260428T0000-structure-20240401.json",
        structure_url="https://example.com/structure-20240401.json",
        data_from=datetime(2026, 4, 27, tzinfo=timezone.utc),
        data_to=datetime(2026, 4, 28, tzinfo=timezone.utc),
        schema_version="20240401",
        source_kind="registry",
    )

    async def fake_discovery_plan(*, mode: str, last_processed_to):
        return DiscoveryPlan(files=[file_ref], source_kind="registry", dataset_id="7710568760-notice")

    opendata_item = {
        "regNum": "72000000000000000123",
        "documentType": "notice",
        "publishDate": "2026-04-27T10:00:00Z",
        "biddTypeCode": "ZK",
        "ownershipFormsCode": "1",
        "subjectEstateCode": "100",
        "subjectRightHolderCode": "72",
        "rightHolderCode": "RH-1",
        "bidderOrgCode": "BO-1",
        "href": "https://example.com/docs/notice_72000000000000000123_abc.json",
    }

    async def fake_fetch_with_meta(url: str):
        return {"listObjects": [opendata_item]}, "e" * 64

    async def fake_fetch_json(url: str):
        return {"fields": []}

    async def fake_notify(*args, **kwargs):
        return None

    monkeypatch.setattr("app.services.ingest.service.build_discovery_plan", fake_discovery_plan)
    monkeypatch.setattr("app.services.ingest.service.fetch_json_payload_with_meta", fake_fetch_with_meta)
    monkeypatch.setattr("app.services.ingest.service.fetch_json_payload", fake_fetch_json)
    monkeypatch.setattr("app.services.ingest.service.notify_lot_event", fake_notify)
    monkeypatch.setattr("app.services.ingest.service.settings.target_region_codes", "")
    monkeypatch.setattr("app.services.ingest.service.settings.ingest_fetch_notice_details", False)

    result = asyncio.run(run_ingest(db))

    notices = db.scalars(select(OpenDataNotice)).all()
    lots = db.scalars(select(Lot)).all()

    assert result["upserted_count"] == 1
    assert len(notices) == 1
    assert len(lots) == 1
    notice = notices[0]
    lot = lots[0]
    assert notice.href == opendata_item["href"]
    assert notice.reg_num == opendata_item["regNum"]
    assert notice.structure_version == "20240401"
    assert lot.opendata_notice_id == notice.id

    # Re-running on the same input must not duplicate the notice (upsert).
    db_again = _db_session()
    monkeypatch.setattr("app.services.ingest.service.build_discovery_plan", fake_discovery_plan)
    monkeypatch.setattr("app.services.ingest.service.fetch_json_payload_with_meta", fake_fetch_with_meta)
    asyncio.run(run_ingest(db_again))
    asyncio.run(run_ingest(db_again))
    assert len(db_again.scalars(select(OpenDataNotice)).all()) == 1
    assert len(db_again.scalars(select(Lot)).all()) == 1


def test_run_ingest_does_not_create_lot_from_clarifications(monkeypatch):
    db = _db_session()
    file_ref = DiscoveredDatasetFile(
        source_url="https://example.com/data-20260506T0000-20260507T0000-structure-20240401.json",
        structure_url="https://example.com/structure-20240401.json",
        data_from=datetime(2026, 5, 6, tzinfo=timezone.utc),
        data_to=datetime(2026, 5, 7, tzinfo=timezone.utc),
        schema_version="20240401",
        source_kind="registry",
    )
    opendata_item = {
        "regNum": "72000000000000000456",
        "documentType": "clarifications",
        "publishDate": "2026-05-07T10:00:00Z",
        "biddTypeCode": "ZK",
        "subjectEstateCode": "72",
        "subjectRightHolderCode": "72",
        "rightHolderCode": "RH-1",
        "bidderOrgCode": "BO-1",
        "href": "https://example.com/docs/clarifications_72000000000000000456_abc.json",
    }

    async def fake_discovery_plan(*, mode: str, last_processed_to):
        return DiscoveryPlan(files=[file_ref], source_kind="registry", dataset_id="7710568760-notice")

    async def fake_fetch_with_meta(url: str):
        return {"listObjects": [opendata_item]}, "f" * 64

    async def fake_fetch_json(url: str):
        return {"fields": []}

    monkeypatch.setattr("app.services.ingest.service.build_discovery_plan", fake_discovery_plan)
    monkeypatch.setattr("app.services.ingest.service.fetch_json_payload_with_meta", fake_fetch_with_meta)
    monkeypatch.setattr("app.services.ingest.service.fetch_json_payload", fake_fetch_json)
    monkeypatch.setattr("app.services.ingest.service.settings.target_region_codes", "72")

    result = asyncio.run(run_ingest(db))

    assert result["upserted_count"] == 0
    assert len(db.scalars(select(OpenDataNotice)).all()) == 1
    assert len(db.scalars(select(Lot)).all()) == 0


def test_run_ingest_applies_cancel_event_to_existing_lot(monkeypatch):
    db = _db_session()
    db.add(Lot(source_id="72000000000000000789", title="Existing lot", status="PUBLISHED"))
    db.commit()
    file_ref = DiscoveredDatasetFile(
        source_url="https://example.com/data-20260506T0000-20260507T0000-structure-20240401.json",
        structure_url="https://example.com/structure-20240401.json",
        data_from=datetime(2026, 5, 6, tzinfo=timezone.utc),
        data_to=datetime(2026, 5, 7, tzinfo=timezone.utc),
        schema_version="20240401",
        source_kind="registry",
    )
    opendata_item = {
        "regNum": "72000000000000000789",
        "documentType": "noticeCancel",
        "publishDate": "2026-05-07T10:00:00Z",
        "biddTypeCode": "ZK",
        "subjectEstateCode": "72",
        "subjectRightHolderCode": "72",
        "rightHolderCode": "RH-1",
        "bidderOrgCode": "BO-1",
        "href": "https://example.com/docs/noticeCancel_72000000000000000789_abc.json",
    }

    async def fake_discovery_plan(*, mode: str, last_processed_to):
        return DiscoveryPlan(files=[file_ref], source_kind="registry", dataset_id="7710568760-notice")

    async def fake_fetch_with_meta(url: str):
        return {"listObjects": [opendata_item]}, "g" * 64

    async def fake_fetch_json(url: str):
        return {"fields": []}

    monkeypatch.setattr("app.services.ingest.service.build_discovery_plan", fake_discovery_plan)
    monkeypatch.setattr("app.services.ingest.service.fetch_json_payload_with_meta", fake_fetch_with_meta)
    monkeypatch.setattr("app.services.ingest.service.fetch_json_payload", fake_fetch_json)
    monkeypatch.setattr("app.services.ingest.service.settings.target_region_codes", "72")

    result = asyncio.run(run_ingest(db))
    saved = db.scalars(select(Lot)).one()

    assert result["upserted_count"] == 0
    assert result["changed_count"] == 1
    assert saved.status == "CANCELED"
