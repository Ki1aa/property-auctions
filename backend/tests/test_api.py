from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Lot, OpenDataNotice, Organizer


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
    assert len(lots_response.json()) == 1
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

    only_izhs = client.get("/api/lots", params={"is_izhs": "true"}).json()
    assert [item["source_id"] for item in only_izhs] == ["lot-izhs"]

    by_area = client.get("/api/lots", params={"min_area": 500}).json()
    assert {item["source_id"] for item in by_area} == {"lot-izhs"}

    by_max_price = client.get("/api/lots", params={"max_start_price": 2_000_000}).json()
    assert {item["source_id"] for item in by_max_price} == {"lot-izhs"}

    by_cadastral = client.get("/api/lots", params={"cadastral_number": "72:23"}).json()
    assert [item["source_id"] for item in by_cadastral] == ["lot-izhs"]

    by_categories = client.get(
        "/api/lots",
        params=[("category", "ZK"), ("category", "178FZ")],
    ).json()
    assert {item["source_id"] for item in by_categories} == {"lot-izhs", "lot-other"}

    single_cat = client.get("/api/lots", params={"category": "ZK"}).json()
    assert [item["source_id"] for item in single_cat] == ["lot-izhs"]


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


def test_opendata_notices_multi_filter_and_facets():
    TestingSessionLocal = _setup_inmemory_app()

    db = TestingSessionLocal()
    db.add(
        OpenDataNotice(
            reg_num="r1",
            document_type="notice",
            href="https://example.com/1",
            bidd_type_code="ZK",
            payload={},
        )
    )
    db.add(
        OpenDataNotice(
            reg_num="r2",
            document_type="protocol",
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
    assert {n["reg_num"] for n in both_bidd} == {"r1", "r2"}

    both_doc = client.get(
        "/api/opendata-notices",
        params=[("document_type", "notice"), ("document_type", "protocol")],
    ).json()
    assert {n["reg_num"] for n in both_doc} == {"r1", "r2"}


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
