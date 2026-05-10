from datetime import datetime

from app.models import Lot
from app.services.nspd.enrich import (
    apply_nspd_features_to_lot,
    extract_nspd_options_from_feature,
    merge_nspd_into_notice_fields,
)
from app.services.nspd.geometry import epsg3857_to_4326, polygon_centroid_lat_lon


def test_extract_nspd_options_from_feature():
    feature = {
        "properties": {
            "options": {
                "specified_area": 1234.5,
                "cost_value": 1_000_000,
                "readable_address": "Test addr",
                "objectId": 291667829,
                "category": 36384,
            }
        },
        "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]},
    }
    out = extract_nspd_options_from_feature(feature)
    assert out["nspd_specified_area_sqm"] == 1234.5
    assert out["nspd_cost_value"] == 1_000_000
    assert out["nspd_readable_address"] == "Test addr"
    assert out["nspd_centroid_latitude"] is not None
    assert out["nspd_centroid_longitude"] is not None
    assert out["nspd_card_id"] == "291667829"
    assert out["nspd_card_type"] == "36384"


def test_apply_nspd_features_empty_clears():
    lot = Lot(
        source_id="x",
        title="t",
        is_izhs_candidate=False,
        nspd_specified_area_sqm=999.0,
        nspd_readable_address="old",
        nspd_card_id="old-id",
        nspd_card_type="old-type",
        nspd_centroid_latitude=57.0,
        nspd_centroid_longitude=65.0,
        latitude=55.0,
        longitude=66.0,
    )
    apply_nspd_features_to_lot(lot, [])
    assert lot.nspd_specified_area_sqm is None
    assert lot.nspd_readable_address is None
    assert lot.nspd_card_id is None
    assert lot.nspd_card_type is None
    assert lot.nspd_enriched_at is not None
    assert isinstance(lot.nspd_enriched_at, datetime)
    assert lot.nspd_centroid_latitude is None
    assert lot.map_anchor_latitude == 55.0
    assert lot.map_anchor_longitude == 66.0
    assert lot.map_anchor_source == "notice"


def test_epsg3857_origin():
    lat, lon = epsg3857_to_4326(0.0, 0.0)
    assert abs(lat) < 0.01 and abs(lon) < 0.01


def test_polygon_centroid_invalid():
    assert polygon_centroid_lat_lon({"type": "Point", "coordinates": [0, 0]}) is None


def test_merge_notice_only_keeps_lot_fields(monkeypatch):
    monkeypatch.setattr("app.services.nspd.enrich.settings.nspd_merge_area_policy", "notice_only")
    monkeypatch.setattr("app.services.nspd.enrich.settings.nspd_merge_address_policy", "notice_only")
    lot = Lot(source_id="m1", title="t", is_izhs_candidate=False, area_sqm=500.0, address="Notice addr")
    merge_nspd_into_notice_fields(lot, 999.0, "NSPD addr")
    assert lot.area_sqm == 500.0
    assert lot.address == "Notice addr"


def test_merge_prefer_nspd_overwrites(monkeypatch):
    monkeypatch.setattr("app.services.nspd.enrich.settings.nspd_merge_area_policy", "prefer_nspd")
    monkeypatch.setattr("app.services.nspd.enrich.settings.nspd_merge_address_policy", "prefer_nspd")
    lot = Lot(source_id="m2", title="t", is_izhs_candidate=False, area_sqm=500.0, address="Notice addr")
    merge_nspd_into_notice_fields(lot, 600.0, "NSPD addr")
    assert lot.area_sqm == 600.0
    assert lot.address == "NSPD addr"


def test_merge_nspd_when_notice_missing(monkeypatch):
    monkeypatch.setattr("app.services.nspd.enrich.settings.nspd_merge_area_policy", "nspd_when_notice_missing")
    monkeypatch.setattr("app.services.nspd.enrich.settings.nspd_merge_address_policy", "nspd_when_notice_missing")
    lot = Lot(source_id="m3", title="t", is_izhs_candidate=False, area_sqm=None, address="  ")
    merge_nspd_into_notice_fields(lot, 700.0, "Filled")
    assert lot.area_sqm == 700.0
    assert lot.address == "Filled"


def test_apply_nspd_features_runs_merge(monkeypatch):
    monkeypatch.setattr("app.services.nspd.enrich.settings.nspd_merge_area_policy", "prefer_nspd")
    monkeypatch.setattr("app.services.nspd.enrich.settings.nspd_merge_address_policy", "notice_only")
    feature = {
        "properties": {"options": {"specified_area": 42.0, "readable_address": "A"}},
        "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]},
    }
    lot = Lot(source_id="m4", title="t", is_izhs_candidate=False, area_sqm=1.0, address="keep")
    apply_nspd_features_to_lot(lot, [feature])
    assert lot.area_sqm == 42.0
    assert lot.address == "keep"
    assert lot.nspd_specified_area_sqm == 42.0
    assert lot.map_anchor_source == "nspd_polygon"
    assert lot.map_anchor_latitude is not None


def test_apply_nspd_features_sets_card_identifiers():
    feature = {
        "id": 291667829,
        "properties": {"options": {"specified_area": 42.0}, "category": 36384},
        "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]},
    }
    lot = Lot(source_id="m5", title="t", is_izhs_candidate=False)
    apply_nspd_features_to_lot(lot, [feature])
    assert lot.nspd_card_id == "291667829"
    assert lot.nspd_card_type == "36384"
    assert lot.map_anchor_source == "nspd_polygon"
