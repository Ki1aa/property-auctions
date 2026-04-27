import asyncio
import json
import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def fetch_json_payload(url: str) -> dict[str, Any] | list[dict[str, Any]]:
    retries = settings.ingest_retry_count
    timeout = settings.ingest_timeout_seconds
    last_error: Exception | None = None

    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(1, retries + 1):
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning("Fetch attempt %s/%s failed: %s", attempt, retries, exc)
                if attempt < retries:
                    await asyncio.sleep(attempt * 2)

    raise RuntimeError(f"Unable to fetch JSON from {url}: {last_error}")


def save_raw_payload(payload: Any, run_id: int) -> str:
    path = f"/tmp/ingest_run_{run_id}.json"
    with open(path, "w", encoding="utf-8") as raw_file:
        json.dump(payload, raw_file, ensure_ascii=False)
    return path
