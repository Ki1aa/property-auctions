import asyncio
from datetime import datetime, timezone

import httpx
import pytest

from app.services.ingest.discovery import build_discovery_plan


class FakeAsyncClient:
    def __init__(self, responses: dict[str, httpx.Response], timeout: int):
        self._responses = responses
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, url: str) -> httpx.Response:
        if url not in self._responses:
            raise httpx.ConnectError(f"Unexpected URL requested in test: {url}")
        return self._responses[url]


def _json_response(url: str, payload):
    request = httpx.Request("GET", url)
    return httpx.Response(200, json=payload, headers={"content-type": "application/json"}, request=request)


def _html_response(url: str, html: str):
    request = httpx.Request("GET", url)
    return httpx.Response(200, text=html, headers={"content-type": "text/html"}, request=request)


def test_discovery_uses_registry_primary(monkeypatch):
    registry_url = "https://torgi.gov.ru/new/opendata/list.json"
    dataset_url = "https://torgi.gov.ru/new/opendata/7710568760-notice/data-20260427T0000-20260428T0000-structure-20240401.json"
    payload = [
        {
            "id": "7710568760-notice",
            "resources": [{"url": dataset_url}],
        }
    ]

    monkeypatch.setattr("app.services.ingest.discovery.settings.ingest_source_url", "")
    def fake_client_factory(*args, **kwargs):
        return FakeAsyncClient({registry_url: _json_response(registry_url, payload)}, kwargs.get("timeout", 30))

    monkeypatch.setattr(httpx, "AsyncClient", fake_client_factory)

    plan = asyncio.run(build_discovery_plan(mode="operational", last_processed_to=None))
    assert plan.source_kind == "registry"
    assert len(plan.files) >= 1
    assert all("7710568760-notice" in item.source_url for item in plan.files)
    assert all("data-" in item.source_url for item in plan.files)


def test_discovery_falls_back_to_card(monkeypatch):
    registry_url = "https://torgi.gov.ru/new/opendata/list.json"
    card_url = "https://torgi.gov.ru/new/public/opendata/61f2a3bf11d8ab36f6c1b275"
    dataset_url = "https://torgi.gov.ru/new/opendata/7710568760-notice/data-20260427T0000-20260428T0000-structure-20240401.json"
    card_html = f"<html><body><a href=\"{dataset_url}\">data</a></body></html>"

    monkeypatch.setattr("app.services.ingest.discovery.settings.ingest_source_url", "")
    def fake_client_factory(*args, **kwargs):
        request = httpx.Request("GET", registry_url)
        registry_error = httpx.Response(503, text="service unavailable", request=request)
        return FakeAsyncClient(
            {
                registry_url: registry_error,
                card_url: _html_response(card_url, card_html),
            },
            kwargs.get("timeout", 30),
        )

    monkeypatch.setattr(httpx, "AsyncClient", fake_client_factory)

    plan = asyncio.run(build_discovery_plan(mode="operational", last_processed_to=None))
    assert plan.source_kind == "card"
    assert len(plan.files) >= 1
    assert all("data-" in item.source_url for item in plan.files)


def test_discovery_supports_direct_override(monkeypatch):
    direct_url = "https://example.com/data-20260427T0000-20260428T0000-structure-20240401.json"
    monkeypatch.setattr("app.services.ingest.discovery.settings.ingest_source_url", direct_url)
    monkeypatch.setattr("app.services.ingest.discovery.settings.ingest_structure_url", "https://example.com/structure-20240401.json")

    plan = asyncio.run(build_discovery_plan(mode="operational", last_processed_to=None))
    assert plan.source_kind == "direct"
    assert plan.files[0].structure_url == "https://example.com/structure-20240401.json"
    assert "example.com" in plan.files[0].source_url
    assert "data-" in plan.files[0].source_url


def test_discovery_treats_source_url_card_as_card_override(monkeypatch):
    card_url = "https://torgi.gov.ru/new/public/opendata/61f2a3bf11d8ab36f6c1b275"
    dataset_url = "https://torgi.gov.ru/new/opendata/7710568760-notice/data-20260427T0000-20260428T0000-structure-20240401.json"
    card_html = f"<html><body><a href=\"{dataset_url}\">data</a></body></html>"

    monkeypatch.setattr("app.services.ingest.discovery.settings.ingest_source_url", card_url)

    def fake_client_factory(*args, **kwargs):
        return FakeAsyncClient({card_url: _html_response(card_url, card_html)}, kwargs.get("timeout", 30))

    monkeypatch.setattr(httpx, "AsyncClient", fake_client_factory)

    plan = asyncio.run(build_discovery_plan(mode="operational", last_processed_to=None))
    assert plan.source_kind == "card_override"
    assert len(plan.files) >= 1
    assert all("data-" in item.source_url for item in plan.files)


def test_discovery_operational_plans_catchup_with_watermark(monkeypatch):
    registry_url = "https://torgi.gov.ru/new/opendata/list.json"
    dataset_url = "https://torgi.gov.ru/new/opendata/7710568760-notice/data-20260427T0000-20260428T0000-structure-20240401.json"
    payload = [{"id": "7710568760-notice", "resources": [{"url": dataset_url}]}]

    monkeypatch.setattr("app.services.ingest.discovery.settings.ingest_source_url", "")
    def fake_client_factory(*args, **kwargs):
        return FakeAsyncClient({registry_url: _json_response(registry_url, payload)}, kwargs.get("timeout", 30))

    monkeypatch.setattr(httpx, "AsyncClient", fake_client_factory)
    watermark = datetime(2026, 4, 26, 0, 0, tzinfo=timezone.utc)

    plan = asyncio.run(build_discovery_plan(mode="operational", last_processed_to=watermark))
    assert len(plan.files) >= 1
    assert all("data-" in file.source_url for file in plan.files)


def test_discovery_backfill_requires_start_date(monkeypatch):
    monkeypatch.setattr("app.services.ingest.discovery.settings.ingest_source_url", "")
    monkeypatch.setattr("app.services.ingest.discovery.settings.backfill_from", "")
    with pytest.raises(RuntimeError, match="BACKFILL_FROM must be set"):
        asyncio.run(build_discovery_plan(mode="backfill", last_processed_to=None))
