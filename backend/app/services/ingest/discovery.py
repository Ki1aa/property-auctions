from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from urllib.parse import urljoin

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_DATA_FILE_RE = re.compile(
    r"(?P<base>https?://[^\s\"'<>]+/)"
    r"data-(?P<from>\d{8}T\d{4})-(?P<to>\d{8}T\d{4})-structure-(?P<schema>\d+)\.json",
    re.IGNORECASE,
)
_DIRECT_DATASET_LINK_RE = re.compile(
    r"https?://[^\s\"'<>]+/data-\d{8}T\d{4}-\d{8}T\d{4}-structure-\d+\.json",
    re.IGNORECASE,
)
_HREF_JSON_RE = re.compile(r"""href=["']([^"']+\.json(?:\?[^"']*)?)["']""", re.IGNORECASE)
_OPEN_DATA_FIELD_RE = re.compile(
    r"Гиперссылка\s*\(URL\)\s*на\s*открытые\s*данные.*?(https?://[^\s\"'<>]+\.json)",
    re.IGNORECASE | re.DOTALL,
)


@dataclass
class DiscoveredDatasetFile:
    source_url: str
    structure_url: str | None
    data_from: datetime | None
    data_to: datetime | None
    schema_version: str | None
    source_kind: str


@dataclass
class DiscoveryPlan:
    files: list[DiscoveredDatasetFile]
    source_kind: str
    dataset_id: str


def _parse_torgi_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%Y%m%dT%H%M")
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc)


def _normalize_json_link(base_url: str, candidate: str) -> str:
    return urljoin(base_url, candidate.strip()).replace("&amp;", "&")


def _build_structure_url(file_url: str, schema_version: str | None) -> str | None:
    if not schema_version:
        return None
    match = _DATA_FILE_RE.search(file_url)
    if match:
        return f"{match.group('base')}structure-{schema_version}.json"
    return None


def _parse_dataset_file_url(url: str, source_kind: str) -> DiscoveredDatasetFile:
    match = _DATA_FILE_RE.search(url)
    if not match:
        return DiscoveredDatasetFile(
            source_url=url,
            structure_url=None,
            data_from=None,
            data_to=None,
            schema_version=None,
            source_kind=source_kind,
        )
    schema_version = match.group("schema")
    return DiscoveredDatasetFile(
        source_url=url,
        structure_url=_build_structure_url(url, schema_version),
        data_from=_parse_torgi_dt(match.group("from")),
        data_to=_parse_torgi_dt(match.group("to")),
        schema_version=schema_version,
        source_kind=source_kind,
    )


async def _request_with_retries(client: httpx.AsyncClient, url: str, retries: int) -> httpx.Response:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning("Discovery attempt %s/%s failed for %s: %s", attempt, retries, url, exc)
            if attempt < retries:
                await asyncio_sleep(attempt * 2)
    raise RuntimeError(f"Unable to fetch discovery URL {url}: {last_error}")


async def asyncio_sleep(seconds: int) -> None:
    import asyncio

    await asyncio.sleep(seconds)


def _dataset_sort_key(entry: DiscoveredDatasetFile) -> tuple[datetime, datetime, str]:
    dt_to = entry.data_to or datetime.min.replace(tzinfo=timezone.utc)
    dt_from = entry.data_from or datetime.min.replace(tzinfo=timezone.utc)
    return dt_to, dt_from, entry.source_url


def _pick_latest(entries: list[DiscoveredDatasetFile]) -> DiscoveredDatasetFile:
    return max(entries, key=_dataset_sort_key)


def _iter_dicts(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("meta", "datasets", "items", "data", "results", "content"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _match_dataset(candidate: dict[str, Any], dataset_id: str) -> bool:
    searchable_keys = (
        "id",
        "identifier",
        "dataset_id",
        "slug",
        "identification_number",
        "registrationNumber",
    )
    lowered = dataset_id.lower()
    for key in searchable_keys:
        value = candidate.get(key)
        if isinstance(value, str) and lowered in value.lower():
            return True
    return False


def _extract_dataset_links(node: Any, base_url: str, acc: set[str]) -> None:
    if isinstance(node, dict):
        for value in node.values():
            _extract_dataset_links(value, base_url, acc)
        return
    if isinstance(node, list):
        for value in node:
            _extract_dataset_links(value, base_url, acc)
        return
    if isinstance(node, str):
        normalized = _normalize_json_link(base_url, node)
        if _DATA_FILE_RE.search(normalized):
            acc.add(normalized)


async def _discover_from_registry(client: httpx.AsyncClient) -> list[DiscoveredDatasetFile]:
    response = await _request_with_retries(client, settings.torgi_opendata_registry_url, settings.ingest_retry_count)
    payload = response.json()
    entries = _iter_dicts(payload)
    if not entries:
        raise RuntimeError("Registry payload does not contain dataset entries")

    dataset = next((entry for entry in entries if _match_dataset(entry, settings.torgi_opendata_dataset_id)), None)
    if dataset is None:
        raise RuntimeError(f"Dataset {settings.torgi_opendata_dataset_id} not found in registry")

    links: set[str] = set()
    _extract_dataset_links(dataset, settings.torgi_opendata_registry_url, links)
    if not links:
        meta_link = dataset.get("link")
        if isinstance(meta_link, str) and meta_link:
            meta_url = _normalize_json_link(settings.torgi_opendata_registry_url, meta_link)
            meta_response = await _request_with_retries(client, meta_url, settings.ingest_retry_count)
            meta_payload = meta_response.json()
            _extract_dataset_links(meta_payload, meta_url, links)
    if not links:
        raise RuntimeError("Registry dataset does not provide data-*.json links")

    return [_parse_dataset_file_url(url, "registry") for url in sorted(links)]


def _extract_dataset_url_from_card(
    html: str, card_url: str, source_kind: str = "card"
) -> list[DiscoveredDatasetFile]:
    links: list[str] = []

    preferred_match = _OPEN_DATA_FIELD_RE.search(html)
    if preferred_match:
        links.append(_normalize_json_link(card_url, preferred_match.group(1)))

    links.extend(match.group(0) for match in _DIRECT_DATASET_LINK_RE.finditer(html))

    for match in _HREF_JSON_RE.finditer(html):
        links.append(_normalize_json_link(card_url, match.group(1)))

    filtered = [url for url in links if _DATA_FILE_RE.search(url)]
    unique = list(dict.fromkeys(filtered))
    if not unique:
        raise RuntimeError("Dataset card parsed, but no valid data-*.json links were found")
    return [_parse_dataset_file_url(url, source_kind) for url in unique]


async def _discover_from_card_url(
    client: httpx.AsyncClient, card_url: str, source_kind: str = "card"
) -> list[DiscoveredDatasetFile]:
    response = await _request_with_retries(client, card_url, settings.ingest_retry_count)
    return _extract_dataset_url_from_card(response.text, card_url, source_kind)


async def _discover_from_card(client: httpx.AsyncClient) -> list[DiscoveredDatasetFile]:
    return await _discover_from_card_url(client, settings.torgi_opendata_card_url)


def _from_direct_override() -> list[DiscoveredDatasetFile]:
    if not settings.ingest_source_url:
        return []
    if not _DATA_FILE_RE.search(settings.ingest_source_url):
        return []
    file_ref = _parse_dataset_file_url(settings.ingest_source_url, "direct")
    if settings.ingest_structure_url:
        file_ref.structure_url = settings.ingest_structure_url
    return [file_ref]


def _daterange(start_date: date, end_date: date) -> list[date]:
    values: list[date] = []
    current = start_date
    while current <= end_date:
        values.append(current)
        current += timedelta(days=1)
    return values


def _replace_file_interval(template_url: str, day_from: date, day_to: date, schema_version: str | None) -> str:
    if not schema_version:
        schema_version = "20240401"
    return _DATA_FILE_RE.sub(
        lambda m: (
            f"{m.group('base')}data-{day_from.strftime('%Y%m%d')}T0000-"
            f"{day_to.strftime('%Y%m%d')}T0000-structure-{schema_version}.json"
        ),
        template_url,
    )


def _planned_dates(last_processed_to: datetime | None, mode: str) -> tuple[date, date]:
    today = datetime.now(timezone.utc).date()
    if mode == "backfill":
        if not settings.backfill_from:
            raise RuntimeError("BACKFILL_FROM must be set when INGEST_MODE=backfill")
        start = datetime.strptime(settings.backfill_from, "%Y-%m-%d").date()
        end = datetime.strptime(settings.backfill_to, "%Y-%m-%d").date() if settings.backfill_to else today
        return start, end

    if last_processed_to:
        start = last_processed_to.date()
    else:
        offset_day = today + timedelta(days=settings.ingest_daily_offset_days)
        start = offset_day
    if start > today:
        start = today
    return start, today


def _plan_files_with_watermark(
    available: list[DiscoveredDatasetFile],
    mode: str,
    last_processed_to: datetime | None,
) -> list[DiscoveredDatasetFile]:
    if not available:
        return []

    latest = _pick_latest(available)
    start_date, end_date = _planned_dates(last_processed_to, mode)

    scheduled: list[DiscoveredDatasetFile] = []
    if _DATA_FILE_RE.search(latest.source_url):
        for day in _daterange(start_date, end_date):
            next_day = day + timedelta(days=1)
            url = _replace_file_interval(latest.source_url, day, next_day, latest.schema_version)
            scheduled.append(_parse_dataset_file_url(url, latest.source_kind))
    else:
        scheduled.append(latest)

    if mode == "operational":
        # Do not merge the full registry into operational runs: that would sort from the
        # oldest monthly/daily slice and re-fetch history on every tick. Watermark work
        # should stay within the planned date window built from the latest template URL.
        planned = sorted({item.source_url: item for item in scheduled}.values(), key=_dataset_sort_key)
        return planned if planned else [latest]

    by_url: dict[str, DiscoveredDatasetFile] = {item.source_url: item for item in scheduled}
    by_url.update({item.source_url: item for item in available})
    return sorted(by_url.values(), key=_dataset_sort_key)


async def build_discovery_plan(
    *,
    mode: str,
    last_processed_to: datetime | None,
) -> DiscoveryPlan:
    # Validate date window early to fail fast before network discovery.
    if mode == "backfill":
        _planned_dates(last_processed_to, mode)

    timeout = settings.ingest_timeout_seconds
    async with httpx.AsyncClient(timeout=timeout) as client:
        direct = _from_direct_override()
        if direct:
            files = _plan_files_with_watermark(direct, mode, last_processed_to)
            return DiscoveryPlan(files=files, source_kind="direct", dataset_id=settings.torgi_opendata_dataset_id)

        override_url = (settings.ingest_source_url or "").strip()
        if override_url:
            discovered = await _discover_from_card_url(client, override_url, source_kind="card_override")
            source_kind = "card_override"
        else:
            try:
                discovered = await _discover_from_registry(client)
                source_kind = "registry"
            except Exception as registry_exc:  # noqa: BLE001
                logger.warning("Registry discovery failed, trying card fallback: %s", registry_exc)
                discovered = await _discover_from_card(client)
                source_kind = "card"

    files = _plan_files_with_watermark(discovered, mode, last_processed_to)
    return DiscoveryPlan(files=files, source_kind=source_kind, dataset_id=settings.torgi_opendata_dataset_id)
