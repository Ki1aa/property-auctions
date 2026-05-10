"""HTTP client for NSPD geoportal search (land parcels by cadastral number).

Primary endpoint from recon: GET .../api/geoportal/v1/search/geoportal?query=<cad>&thematicSearchId=1
Disabled when settings.nspd_enabled is False (no network).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

from app.config import settings

DEFAULT_GEOPORTAL_PATH = "/api/geoportal/v1/search/geoportal"


def parse_geoportal_response(payload: Any) -> list[dict[str, Any]]:
    """Normalize JSON body to a list of GeoJSON-like feature dicts."""
    if not isinstance(payload, dict):
        return []
    for key in ("data", "features", "items", "results"):
        raw = payload.get(key)
        if isinstance(raw, list):
            return [x for x in raw if isinstance(x, dict)]
    return []


def extract_feature_collection_items(payload: Any) -> list[dict[str, Any]]:
    """Alias for parse_geoportal_response (explicit name for GeoJSON FeatureCollection-style APIs)."""
    return parse_geoportal_response(payload)


@dataclass(frozen=True)
class NspdGeoportalClient:
    """Sync client; use from scripts or wrap in asyncio.to_thread from async code."""

    base_url: str
    thematic_search_id: int
    timeout_seconds: float
    verify_tls: bool = True

    @classmethod
    def from_settings(cls) -> NspdGeoportalClient:
        base = (settings.nspd_base_url or "https://nspd.gov.ru").rstrip("/")
        return cls(
            base_url=base,
            thematic_search_id=settings.nspd_geoportal_thematic_id,
            timeout_seconds=float(settings.nspd_timeout_seconds),
            verify_tls=settings.nspd_verify_tls,
        )

    def search_by_cadastral(self, cadastral_number: str) -> list[dict[str, Any]] | None:
        if not settings.nspd_enabled:
            return None
        cad = (cadastral_number or "").strip()
        if not cad:
            return None
        path = (settings.nspd_geoportal_search_path or DEFAULT_GEOPORTAL_PATH).strip()
        if not path.startswith("/"):
            path = "/" + path
        q = quote(cad, safe=":")
        url = f"{self.base_url}{path}?query={q}&thematicSearchId={self.thematic_search_id}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "ru,en;q=0.8",
            "Referer": f"{self.base_url}/",
            "Origin": self.base_url,
        }
        with httpx.Client(
            timeout=self.timeout_seconds,
            headers=headers,
            follow_redirects=True,
            verify=self.verify_tls,
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            payload = response.json()
        return parse_geoportal_response(payload)
