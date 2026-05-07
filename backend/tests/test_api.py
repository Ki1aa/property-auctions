from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import IngestRun, Lot, OpenDataNotice, Organizer


def _setup_inmemory_app():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestingSessionLocal


def test_lots_list_and_map_endpoint():
    TestingSessionLocal = _setup_inmemory_app()

    db = TestingSessionLocal()
    organizer = Organizer(source_id="org-x", name="Орг")
    db.add(organizer)
    db.flush()
    db.add(
        Lot(
            source_id="lot-x",
            title="Лот X",
            organizer_id=organizer.id,
            status="active",
            region="ХМАО",
            category="Аренда",
            latitude=61.0,
            longitude=73.0,
        )
    )
    db.commit()
    db.close()

    client = TestClient(app)
    lots_response = client.get("/api/lots")
    map_response = client.get("/api/lots-map")

    assert lots_response.status_code == 200
    lots_body = lots_response.json()
    assert lots_body["total"] == 1
    assert len(lots_body["items"]) == 1
    assert map_response.status_code == 200
    assert len(map_response.json()) == 1


def test_lots_filters_izhs_and_area():
    TestingSessionLocal = _setup_inmemory_app()

    db = TestingSessionLocal()
    db.add(
        Lot(
            source_id="lot-izhs",
            title="ИЖС Тюмень",
            status="active",
            region="72",
            municipality="г.о. город Тюмень",
            category="ZK",
            cadastral_number="72:23:0123456:7",
            area_sqm=1200.0,
            is_izhs_candidate=True,
            start_price=1_000_000,
        )
    )
    db.add(
        Lot(
            source_id="lot-other",
            title="Не-ИЖС",
            status="active",
            region="77",
            category="178FZ",
            cadastral_number="77:01:0001234:5",
            area_sqm=300.0,
            is_izhs_candidate=False,
            start_price=5_000_000,
        )
    )
    db.commit()
    db.close()

    client = TestClient(app)

    only_izhs = client.get("/api/lots", params={"is_izhs": "true"}).json()["items"]
    assert [item["source_id"] for item in only_izhs] == ["lot-izhs"]

    by_area = client.get("/api/lots", params={"min_area": 500}).json()["items"]
    assert {item["source_id"] for item in by_area} == {"lot-izhs"}

    by_max_price = client.get("/api/lots", params={"max_start_price": 2_000_000}).json()["items"]
    assert {item["source_id"] for item in by_max_price} == {"lot-izhs"}

    by_cadastral = client.get("/api/lots", params={"cadastral_number": "72:23"}).json()["items"]
    assert [item["source_id"] for item in by_cadastral] == ["lot-izhs"]

    by_municipality = client.get("/api/lots", params={"municipality": "г.о. город Тюмень"}).json()["items"]
    assert [item["source_id"] for item in by_municipality] == ["lot-izhs"]

    with_cadastral = client.get("/api/lots", params={"has_cadastral": "true"}).json()["items"]
    assert {item["source_id"] for item in with_cadastral} == {"lot-izhs", "lot-other"}

    with_price_per_sotka = client.get("/api/lots", params={"has_price_per_sotka": "true"}).json()["items"]
    assert {item["source_id"] for item in with_price_per_sotka} == {"lot-izhs", "lot-other"}

    by_categories = client.get(
        "/api/lots",
        params=[("category", "ZK"), ("category", "178FZ")],
    ).json()["items"]
    assert {item["source_id"] for item in by_categories} == {"lot-izhs", "lot-other"}

    single_cat = client.get("/api/lots", params={"category": "ZK"}).json()["items"]
    assert [item["source_id"] for item in single_cat] == ["lot-izhs"]

    izhs_row = next(i for i in only_izhs if i["source_id"] == "lot-izhs")
    assert izhs_row["municipality"] == "г.о. город Тюмень"
    assert izhs_row["start_price_per_sqm"] is not None
    assert abs(izhs_row["start_price_per_sqm"] - (1_000_000 / 1200.0)) < 0.02
    assert izhs_row["start_price_per_sotka"] is not None
    assert abs(izhs_row["start_price_per_sotka"] - (1_000_000 / 12.0)) < 0.02

    paged = client.get("/api/lots", params={"limit": 1, "offset": 0}).json()
    assert paged["total"] == 2
    assert len(paged["items"]) == 1
    p2 = client.get("/api/lots", params={"limit": 1, "offset": 1}).json()
    assert len(p2["items"]) == 1
    assert p2["items"][0]["source_id"] != paged["items"][0]["source_id"]

    by_price_asc = client.get("/api/lots", params={"sort": "price_per_sotka_asc"}).json()["items"]
    assert [item["source_id"] for item in by_price_asc] == ["lot-izhs", "lot-other"]
    by_price_desc = client.get("/api/lots", params={"sort": "price_per_sotka_desc"}).json()["items"]
    assert [item["source_id"] for item in by_price_desc] == ["lot-other", "lot-izhs"]

    csv_r = client.get("/api/export/lots.csv", params={"is_izhs": "true"})
    assert csv_r.status_code == 200
    assert "lot-izhs" in csv_r.text
    assert "source_url" in csv_r.text.split("\n")[0]
    assert "municipality" in csv_r.text.split("\n")[0]

    csv_categories = client.get(
        "/api/export/lots.csv",
        params=[("category", "ZK"), ("category", "178FZ")],
    )
    assert csv_categories.status_code == 200
    assert "lot-izhs" in csv_categories.text
    assert "lot-other" in csv_categories.text


def test_lots_return_baseline_valuation_and_discount_sort():
    TestingSessionLocal = _setup_inmemory_app()

    db = TestingSessionLocal()
    for source_id, start_price in [
        ("lot-cheap", 500_000),
        ("lot-middle", 1_000_000),
        ("lot-expensive", 2_000_000),
    ]:
        db.add(
            Lot(
                source_id=source_id,
                title=source_id,
                status="active",
                region="72",
                category="ZK",
                area_sqm=1000.0,
                start_price=start_price,
                is_izhs_candidate=True,
            )
        )
    db.commit()
    db.close()

    client = TestClient(app)
    body = client.get("/api/lots", params={"sort": "discount_to_baseline_desc"}).json()

    assert [item["source_id"] for item in body["items"]] == ["lot-cheap", "lot-middle", "lot-expensive"]
    cheap = body["items"][0]
    assert cheap["start_price_per_sotka"] == 50_000
    assert cheap["baseline_price_per_sotka"] == 100_000
    assert cheap["discount_to_baseline"] == 0.5
    assert cheap["valuation_confidence"] == "low"
    assert cheap["valuation_baseline_scope"] == "region_category"
    assert cheap["valuation_baseline_sample_size"] == 3
    assert "медианой" in cheap["valuation_reason"]

    csv_r = client.get("/api/export/lots.csv", params={"sort": "discount_to_baseline_desc"})
    assert csv_r.status_code == 200
    assert "baseline_price_per_sotka" in csv_r.text.split("\n")[0]
    assert "discount_to_baseline" in csv_r.text.split("\n")[0]

    discounted = client.get("/api/lots", params={"has_positive_discount": "true"}).json()
    assert [item["source_id"] for item in discounted["items"]] == ["lot-cheap"]

    quality = client.get("/api/lots/quality", params={"region": "72"}).json()
    assert quality["total"] == 3
    assert quality["izhs_candidates"] == 3
    assert quality["with_area"] == 3
    assert quality["with_start_price"] == 3
    assert quality["with_price_per_sotka"] == 3
    assert quality["with_baseline"] == 3
    assert quality["with_positive_discount"] == 1


def test_query_limits_reject_non_positive_values():
    _setup_inmemory_app()
    client = TestClient(app)

    cases = [
        ("/api/lots", {"limit": 0}),
        ("/api/lots", {"limit": -1}),
        ("/api/export/lots.csv", {"max_rows": 0}),
        ("/api/export/lots.csv", {"max_rows": -1}),
        ("/api/ingest-runs", {"limit": 0}),
        ("/api/opendata-notices", {"limit": 0}),
    ]
    for path, params in cases:
        response = client.get(path, params=params)
        assert response.status_code == 422


def test_ingest_runs_exposes_observability_fields():
    TestingSessionLocal = _setup_inmemory_app()

    db = TestingSessionLocal()
    db.add(
        IngestRun(
            status="partial_failed",
            source_url="https://example.com/latest-data.json",
            fetched_count=120,
            upserted_count=30,
            changed_count=4,
            processed_files=2,
            failed_files=1,
            last_error_source_url="https://example.com/broken-data.json",
            error_kind="source_unavailable",
            error_message="Источник временно недоступен",
        )
    )
    db.commit()
    db.close()

    client = TestClient(app)
    response = client.get("/api/ingest-runs")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["processed_files"] == 2
    assert body[0]["failed_files"] == 1
    assert body[0]["last_error_source_url"] == "https://example.com/broken-data.json"
    assert body[0]["error_kind"] == "source_unavailable"


def test_ingest_status_and_manual_start_endpoint(monkeypatch):
    _setup_inmemory_app()

    class DummyScheduler:
        running = True

    monkeypatch.setattr("app.api.ingest_scheduler.is_ingest_running", lambda: False)
    monkeypatch.setattr("app.api.ingest_scheduler.next_scheduled_ingest_at", lambda: None)
    monkeypatch.setattr("app.api.ingest_scheduler.start_manual_ingest", lambda mode="operational": True)
    monkeypatch.setattr("app.api.ingest_scheduler.scheduler", DummyScheduler())

    client = TestClient(app)
    status = client.get("/api/ingest-status")
    assert status.status_code == 200
    status_body = status.json()
    assert status_body["is_running"] is False
    assert status_body["scheduler_running"] is True
    assert status_body["interval_minutes"] >= 1
    assert "target_region_codes" in status_body

    start = client.post("/api/ingest-runs/start")
    assert start.status_code == 200
    assert start.json()["started"] is True


def test_manual_start_reports_existing_running_ingest(monkeypatch):
    _setup_inmemory_app()

    monkeypatch.setattr("app.api.ingest_scheduler.start_manual_ingest", lambda mode="operational": False)

    client = TestClient(app)
    response = client.post("/api/ingest-runs/start")

    assert response.status_code == 200
    assert response.json()["started"] is False
    assert "уже выполняется" in response.json()["message"]


def test_lot_facets_endpoint():
    TestingSessionLocal = _setup_inmemory_app()

    db = TestingSessionLocal()
    db.add(
        Lot(
            source_id="a",
            title="A",
            status="notice",
            region="72",
            category="ZK",
        )
    )
    db.add(
        Lot(
            source_id="b",
            title="B",
            status="protocol",
            region="86",
            category="178FZ",
        )
    )
    db.commit()
    db.close()

    client = TestClient(app)
    r = client.get("/api/lots/facets")
    assert r.status_code == 200
    body = r.json()
    assert set(body["category"]) == {"178FZ", "ZK"}
    assert set(body["status"]) == {"notice", "protocol"}
    assert set(body["region"]) == {"72", "86"}
    assert body["municipality"] == []


def test_opendata_notices_multi_filter_and_facets():
    TestingSessionLocal = _setup_inmemory_app()

    db = TestingSessionLocal()
    db.add(
        OpenDataNotice(
            reg_num="r1",
            document_type="notice",
            publish_date=datetime(2026, 5, 1, tzinfo=timezone.utc),
            href="https://example.com/1",
            bidd_type_code="ZK",
            payload={},
        )
    )
    db.add(
        OpenDataNotice(
            reg_num="r2",
            document_type="protocol",
            publish_date=datetime(2026, 5, 2, tzinfo=timezone.utc),
            href="https://example.com/2",
            bidd_type_code="178FZ",
            payload={},
        )
    )
    db.commit()
    db.close()

    client = TestClient(app)
    facets = client.get("/api/opendata-notices/facets").json()
    assert set(facets["bidd_type_code"]) == {"178FZ", "ZK"}
    assert set(facets["document_type"]) == {"notice", "protocol"}

    both_bidd = client.get(
        "/api/opendata-notices",
        params=[("bidd_type_code", "ZK"), ("bidd_type_code", "178FZ")],
    ).json()
    assert both_bidd["total"] == 2
    assert both_bidd["limit"] == 200
    assert both_bidd["offset"] == 0
    assert {n["reg_num"] for n in both_bidd["items"]} == {"r1", "r2"}

    both_doc = client.get(
        "/api/opendata-notices",
        params=[("document_type", "notice"), ("document_type", "protocol")],
    ).json()
    assert {n["reg_num"] for n in both_doc["items"]} == {"r1", "r2"}

    first_page = client.get("/api/opendata-notices", params={"limit": 1, "offset": 0}).json()
    second_page = client.get("/api/opendata-notices", params={"limit": 1, "offset": 1}).json()
    assert first_page["total"] == 2
    assert first_page["items"][0]["reg_num"] == "r2"
    assert second_page["items"][0]["reg_num"] == "r1"


def test_lot_detail_returns_notice_payload_when_linked():
    from sqlalchemy import select

    TestingSessionLocal = _setup_inmemory_app()

    db = TestingSessionLocal()
    notice = OpenDataNotice(
        reg_num="72000000000000000123",
        document_type="notice",
        href="https://example.com/docs/notice_72000000000000000123_abc.json",
        payload={"regNum": "72000000000000000123", "biddTypeCode": "ZK", "extra": "raw"},
    )
    db.add(notice)
    db.flush()
    notice_id = notice.id
    db.add(
        Lot(
            source_id="lot-with-notice",
            title="Лот с привязкой",
            status="active",
            region="72",
            opendata_notice_id=notice_id,
        )
    )
    db.commit()
    lot_id = db.scalar(select(Lot.id))
    db.close()

    client = TestClient(app)
    response = client.get(f"/api/lots/{lot_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["opendata_notice_id"] == notice_id
    assert body["notice_payload"] is not None
    assert body["notice_payload"]["regNum"] == "72000000000000000123"
    assert body["notice_payload"]["extra"] == "raw"


def test_lot_detail_returns_null_notice_payload_when_not_linked():
    from sqlalchemy import select

    TestingSessionLocal = _setup_inmemory_app()

    db = TestingSessionLocal()
    db.add(
        Lot(
            source_id="lot-naked",
            title="Без notice",
            status="active",
            region="72",
        )
    )
    db.commit()
    lot_id = db.scalar(select(Lot.id))
    db.close()

    client = TestClient(app)
    response = client.get(f"/api/lots/{lot_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["opendata_notice_id"] is None
    assert body["notice_payload"] is None
