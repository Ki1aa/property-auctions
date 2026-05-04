import asyncio
import hashlib
import json
import logging
import os
import tempfile
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def _request_with_retries(client: httpx.AsyncClient, url: str, retries: int) -> httpx.Response:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning("Fetch attempt %s/%s failed: %s", attempt, retries, exc)
            if attempt < retries:
                await asyncio.sleep(attempt * 2)
    raise RuntimeError(f"Unable to fetch data from {url}: {last_error}")


async def fetch_json_payload_with_meta(url: str) -> tuple[dict[str, Any] | list[dict[str, Any]], str]:
    retries = settings.ingest_retry_count
    timeout = settings.ingest_timeout_seconds

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await _request_with_retries(client, url, retries)
        content_type = response.headers.get("content-type", "").lower()
        if "html" in content_type and "<html" in response.text.lower():
            raise RuntimeError(f"URL returned HTML instead of JSON: {url}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise RuntimeError(f"URL did not return valid JSON: {url}") from exc
        sha256 = hashlib.sha256(response.content).hexdigest()
        return payload, sha256


async def fetch_json_payload(url: str) -> dict[str, Any] | list[dict[str, Any]]:
    payload, _sha256 = await fetch_json_payload_with_meta(url)
    return payload


def save_raw_payload(payload: Any, run_id: int) -> str:
    temp_dir = tempfile.gettempdir()
    os.makedirs(temp_dir, exist_ok=True)
    path = os.path.join(temp_dir, f"ingest_run_{run_id}.json")
    with open(path, "w", encoding="utf-8") as raw_file:
        json.dump(payload, raw_file, ensure_ascii=False)
    return path
