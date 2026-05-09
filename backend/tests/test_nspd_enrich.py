from datetime import datetime

from app.models import Lot
from app.services.nspd.enrich import apply_nspd_features_to_lot, extract_nspd_options_from_feature
from app.services.nspd.geometry import epsg3857_to_4326, polygon_centroid_lat_lon


def test_extract_nspd_options_from_feature():
    feature = {
        "properties": {
            "options": {
                "specified_area": 1234.5,
                "cost_value": 1_000_000,
                "readable_address": "Test addr",
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


def test_apply_nspd_features_empty_clears():
    lot = Lot(
        source_id="x",
        title="t",
        is_izhs_candidate=False,
        nspd_specified_area_sqm=999.0,
        nspd_readable_address="old",
    )
    apply_nspd_features_to_lot(lot, [])
    assert lot.nspd_specified_area_sqm is None
    assert lot.nspd_readable_address is None
    assert lot.nspd_enriched_at is not None
    assert isinstance(lot.nspd_enriched_at, datetime)


def test_epsg3857_origin():
    lat, lon = epsg3857_to_4326(0.0, 0.0)
    assert abs(lat) < 0.01 and abs(lon) < 0.01


def test_polygon_centroid_invalid():
    assert polygon_centroid_lat_lon({"type": "Point", "coordinates": [0, 0]}) is None
