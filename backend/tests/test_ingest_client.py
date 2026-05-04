import asyncio
import httpx
import pytest

from app.services.ingest.client import fetch_json_payload, fetch_json_payload_with_meta


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
    return httpx.Response(200, text=html, headers={"content-type": "text/html; charset=utf-8"}, request=request)


def test_fetch_json_payload_supports_direct_json_url(monkeypatch):
    source_url = "https://example.com/data-20260427T0000-20260428T0000-structure-20240401.json"
    payload = {"data": [{"id": 1}]}

    def fake_client_factory(*args, **kwargs):
        return FakeAsyncClient({source_url: _json_response(source_url, payload)}, kwargs.get("timeout", 30))

    monkeypatch.setattr(httpx, "AsyncClient", fake_client_factory)

    result = asyncio.run(fetch_json_payload(source_url))
    assert result == payload


def test_fetch_json_payload_with_meta_returns_sha256(monkeypatch):
    source_url = "https://example.com/data-20260427T0000-20260428T0000-structure-20240401.json"
    payload = {"data": [{"id": 1}]}

    def fake_client_factory(*args, **kwargs):
        return FakeAsyncClient({source_url: _json_response(source_url, payload)}, kwargs.get("timeout", 30))

    monkeypatch.setattr(httpx, "AsyncClient", fake_client_factory)

    result, sha256 = asyncio.run(fetch_json_payload_with_meta(source_url))
    assert result == payload
    assert len(sha256) == 64


def test_fetch_json_payload_rejects_html_response(monkeypatch):
    source_url = "https://example.com/card"
    html = "<html><body>not json</body></html>"

    def fake_client_factory(*args, **kwargs):
        return FakeAsyncClient({source_url: _html_response(source_url, html)}, kwargs.get("timeout", 30))

    monkeypatch.setattr(httpx, "AsyncClient", fake_client_factory)

    with pytest.raises(RuntimeError, match="returned HTML instead of JSON"):
        asyncio.run(fetch_json_payload(source_url))
