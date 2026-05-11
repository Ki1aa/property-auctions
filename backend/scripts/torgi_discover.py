"""Print OpenData discovery diagnostics (meta.json, resources, selected ingest file).

  cd backend
  python scripts/torgi_discover.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.ingest.discovery import run_torgi_discovery_diagnostic  # noqa: E402


def main() -> None:
    diag = asyncio.run(run_torgi_discovery_diagnostic())
    print("meta_json_url:", diag.meta_json_url or "(not used; direct INGEST_SOURCE_URL override)")
    print("dataset_id:", diag.dataset_id)
    print("available_data_urls (%d):" % len(diag.available_data_urls))
    for u in diag.available_data_urls[:80]:
        print(" ", u)
    if len(diag.available_data_urls) > 80:
        print(" ...", len(diag.available_data_urls) - 80, "more")
    print("available_structure_urls (%d):" % len(diag.available_structure_urls))
    for u in diag.available_structure_urls[:20]:
        print(" ", u)
    print("selected_for_ingest (%d):" % len(diag.selected_ingest_urls))
    for u in diag.selected_ingest_urls:
        print(" ", u)
    print("selected_structure_urls:")
    for u in diag.selected_structure_urls:
        print(" ", u)
    print("primary_ingest_url:", diag.primary_ingest_url)
    print("primary_structure_url:", diag.primary_structure_url)
    if diag.discovery_warning:
        print("warning:", diag.discovery_warning)
    if diag.error:
        print("error:", diag.error)
    print("--- json ---")
    print(
        json.dumps(
            {
                "meta_json_url": diag.meta_json_url,
                "dataset_id": diag.dataset_id,
                "available_data_urls": diag.available_data_urls,
                "available_structure_urls": diag.available_structure_urls,
                "selected_ingest_urls": diag.selected_ingest_urls,
                "selected_structure_urls": diag.selected_structure_urls,
                "primary_ingest_url": diag.primary_ingest_url,
                "primary_structure_url": diag.primary_structure_url,
                "discovery_warning": diag.discovery_warning,
                "error": diag.error,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
