"""Tests for MVP GIS (mvp_gis_* pipeline helpers)."""

import pytest

from app.config import settings
from app.services.mvp.classify import classify_normalized_lot, lot_passes_telegram_signal, signal_rank
from app.services.mvp.content_hash import BUSINESS_HASH_FIELDS, compute_content_hash
from app.services.mvp.land_filter_config import validate_land_filter_for_ingest
from app.services.mvp.link_builder import build_nspd_search_url, build_notice_url, build_lot_url


def test_build_notice_url():
    u = build_notice_url("22000172340000000699")
    assert "22000172340000000699" in u
    assert u.startswith("https://torgi.gov.ru/new/public/notices/view/")


def test_build_lot_url():
    u = build_lot_url("22000172340000000699", 1)
    assert "22000172340000000699_1" in u.replace("%", "")


def test_build_nspd_query():
    u = build_nspd_search_url("72:01:1:1")
    assert "query=72%3A01%3A1%3A1" in u or "query=72" in u


def test_content_hash_excludes_urls(monkeypatch):
    monkeypatch.setattr(settings, "ingest_land_filter_bidd_type_codes", "ZK", raising=False)
    monkeypatch.setattr(settings, "ingest_land_filter_relaxed", False, raising=False)
    a = {
        "title": "T",
        "description": None,
        "cadastral_number": None,
        "address": None,
        "area_sqm": 100.0,
        "start_price": 1.0,
        "status": "active",
        "application_start": None,
        "application_end": None,
        "auction_date": None,
        "permitted_use": None,
        "land_category": None,
        "notice_url": "http://x",
        "lot_url": "http://y",
    }
    b = dict(a)
    b["notice_url"] = "http://z"
    assert compute_content_hash(a) == compute_content_hash(b)
    assert set(BUSINESS_HASH_FIELDS) == set(
        [
            "title",
            "description",
            "cadastral_number",
            "address",
            "area_sqm",
            "start_price",
            "status",
            "application_start",
            "application_end",
            "auction_date",
            "permitted_use",
            "land_category",
        ]
    )


def test_validate_land_filter_empty(monkeypatch):
    monkeypatch.setattr(settings, "ingest_land_filter_bidd_type_codes", "", raising=False)
    monkeypatch.setattr(settings, "ingest_land_filter_relaxed", False, raising=False)
    with pytest.raises(RuntimeError):
        validate_land_filter_for_ingest(dry_run=False)
    validate_land_filter_for_ingest(dry_run=True)


def test_classify_vehicle_blacklist(monkeypatch):
    monkeypatch.setattr(settings, "ingest_land_filter_bidd_type_codes", "ZK", raising=False)
    monkeypatch.setattr(settings, "ingest_land_filter_relaxed", False, raising=False)
    n = {
        "title": "Продажа автомобиля легкового",
        "category": "ZK",
        "region": "72",
        "raw": {},
    }
    cl = classify_normalized_lot(n)
    assert cl["is_ignored"] is True
    assert cl["is_land"] is True


def test_classify_building_with_cadastre_not_blacklisted(monkeypatch):
    monkeypatch.setattr(settings, "ingest_land_filter_bidd_type_codes", "ZK", raising=False)
    monkeypatch.setattr(settings, "ingest_land_filter_relaxed", False, raising=False)
    n = {
        "title": "Земельный участок со зданием 72:01:0000000:1",
        "category": "ZK",
        "region": "72",
        "raw": {},
    }
    cl = classify_normalized_lot(n)
    assert cl["is_ignored"] is False


def test_signal_rank_telegram_gate(monkeypatch):
    monkeypatch.setattr(settings, "telegram_min_signal_level", "HIGH", raising=False)
    assert lot_passes_telegram_signal("HIGH") is True
    assert lot_passes_telegram_signal("MEDIUM") is False
    assert signal_rank("HIGH") > signal_rank("LOW")
