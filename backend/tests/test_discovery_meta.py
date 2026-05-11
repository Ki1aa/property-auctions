"""Tests for GIS Torgi meta.json-based OpenData discovery."""

from datetime import date, datetime, timezone

import pytest

from app.config import settings
from app.services.ingest.discovery import (
    _plan_meta_files_with_watermark,
    parse_meta_dataset_to_files,
)


def _notice_meta_two_slices() -> dict:
    base = "https://torgi.gov.ru/new/opendata/7710568760-notice"
    u_old = f"{base}/data-20260426T0000-20260427T0000-structure-20240401.json"
    u_mid = f"{base}/data-20260427T0000-20260428T0000-structure-20240401.json"
    u_next = f"{base}/data-20260428T0000-20260429T0000-structure-20240401.json"
    ghost = f"{base}/data-20991231T0000-21000101T0000-structure-20240401.json"
    struct = f"{base}/structure-20240401.json"
    return {
        "data": [
            {"source": u_old, "structure": "20240401", "created": "20260427T0000"},
            {"source": u_mid, "structure": "20240401", "created": "20260428T0000"},
            {"source": u_next, "structure": "20240401", "created": "20260429T0000"},
            {"source": ghost, "structure": "20240401", "created": "20991231T0000"},
        ],
        "structure": [{"source": struct, "created": "20240401"}],
    }


def test_parse_meta_picks_supported_schema_and_structure(monkeypatch):
    monkeypatch.setattr(settings, "supported_structure_versions", "20240401", raising=False)
    meta = _notice_meta_two_slices()
    files, all_src, skipped, err = parse_meta_dataset_to_files(
        meta, source_kind="test", meta_json_url="https://example.com/meta.json"
    )
    assert err is None
    assert len(files) == 4
    urls = {f.source_url for f in files}
    assert all(u in urls for u in all_src)
    assert not skipped
    assert all(f.structure_url == meta["structure"][0]["source"] for f in files)


def test_parse_meta_skips_row_when_structure_version_missing_from_meta_block(monkeypatch):
    monkeypatch.setattr(settings, "supported_structure_versions", "20240401", raising=False)
    base = "https://torgi.gov.ru/new/opendata/7710568760-notice"
    u = f"{base}/data-20260427T0000-20260428T0000-structure-20240401.json"
    meta = {
        "data": [{"source": u, "structure": "20240401"}],
        "structure": [{"source": f"{base}/structure-20999999.json", "created": "x"}],
    }
    files, _, skipped, err = parse_meta_dataset_to_files(
        meta, source_kind="test", meta_json_url="https://example.com/meta.json"
    )
    assert not files
    assert err
    assert "structure" in err.lower()
    assert skipped


def test_parse_meta_filters_unsupported_schema_version(monkeypatch):
    monkeypatch.setattr(settings, "supported_structure_versions", "20250501", raising=False)
    meta = _notice_meta_two_slices()
    files, all_src, _, err = parse_meta_dataset_to_files(
        meta, source_kind="test", meta_json_url="https://example.com/meta.json"
    )
    assert not files
    assert err
    assert "7710568760-notice" in all_src[0] or len(all_src) >= 1


def test_plan_meta_prefers_slices_in_window_not_synthetic(monkeypatch):
    monkeypatch.setattr(settings, "supported_structure_versions", "20240401", raising=False)
    meta = _notice_meta_two_slices()
    files, _, _, err = parse_meta_dataset_to_files(meta, source_kind="test", meta_json_url="m")
    assert not err

    def _fixed_planned(_lp, mode):
        if mode == "operational":
            return date(2026, 4, 27), date(2026, 4, 28)
        raise AssertionError

    monkeypatch.setattr("app.services.ingest.discovery._planned_dates", _fixed_planned)
    planned, warn, sel_err = _plan_meta_files_with_watermark(files, "operational", None)
    assert not sel_err
    assert len(planned) == 2
    urls = [p.source_url for p in planned]
    assert any("20260427T0000-20260428" in u for u in urls)
    assert any("20260428T0000-20260429" in u for u in urls)
    assert not any("20991231" in u for u in urls)


def test_plan_meta_operational_fallback_latest_when_no_day_match(monkeypatch):
    monkeypatch.setattr(settings, "supported_structure_versions", "20240401", raising=False)
    meta = _notice_meta_two_slices()
    files, _, _, err = parse_meta_dataset_to_files(meta, source_kind="test", meta_json_url="m")
    assert not err

    def _empty_window(_lp, mode):
        if mode == "operational":
            return date(2020, 1, 1), date(2020, 1, 2)
        raise AssertionError

    monkeypatch.setattr("app.services.ingest.discovery._planned_dates", _empty_window)
    planned, warn, sel_err = _plan_meta_files_with_watermark(
        files, "operational", datetime(2020, 1, 1, tzinfo=timezone.utc)
    )
    assert not sel_err
    assert len(planned) == 1
    assert warn
    assert "20991231" in planned[0].source_url or "20260427" in planned[0].source_url


def test_plan_meta_backfill_returns_error_when_no_overlap(monkeypatch):
    monkeypatch.setattr(settings, "supported_structure_versions", "20240401", raising=False)
    monkeypatch.setattr(settings, "backfill_from", "2020-01-01", raising=False)
    monkeypatch.setattr(settings, "backfill_to", "2020-01-05", raising=False)
    meta = _notice_meta_two_slices()
    files, _, _, err = parse_meta_dataset_to_files(meta, source_kind="test", meta_json_url="m")
    assert not err
    planned, warn, sel_err = _plan_meta_files_with_watermark(files, "backfill", None)
    assert not planned
    assert sel_err
    assert "2020-01-01" in sel_err
