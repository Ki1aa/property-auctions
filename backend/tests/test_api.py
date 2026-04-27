from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Lot, Organizer


def test_lots_list_and_map_endpoint():
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
