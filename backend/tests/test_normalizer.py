from app.services.ingest.normalizer import normalize_lot


def test_normalize_lot_maps_minimal_fields():
    raw = {
        "id": "123",
        "name": "Лот 1",
        "status": "published",
        "regionName": "ХМАО",
        "startPrice": 1000,
        "location": {"latitude": 61.1, "longitude": 73.4},
        "organizer": {"inn": "8600000000", "name": "Администрация"},
    }
    normalized = normalize_lot(raw)

    assert normalized["source_id"] == "123"
    assert normalized["title"] == "Лот 1"
    assert normalized["region"] == "ХМАО"
    assert normalized["start_price"] == 1000
    assert normalized["latitude"] == 61.1
    assert normalized["organizer"]["name"] == "Администрация"
