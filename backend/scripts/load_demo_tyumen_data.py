"""Load reproducible Tyumen demo data from data/raw into the dev database.

This script is offline-only: it uses source discovery artifacts saved under
data/raw and never calls Torgi or NSPD. It is meant to make the MVP demo
repeatable when live access to Russian public services is unavailable.

Usage:
    python scripts/load_demo_tyumen_data.py
    python scripts/load_demo_tyumen_data.py --reset
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from dateutil import parser as date_parser
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal
from app.models import AlertEvent, IngestManifest, IngestRun, Lot, LotSnapshot, OpenDataNotice, Organizer
from app.services.ingest.detail_parser import match_izhs, parse_notice_detail, split_keywords
from app.services.ingest.normalizer import normalize_lot
from app.services.lot_identity import notice_identity_from_values
from app.config import settings
from scripts.dev_sync_schema import sync as sync_dev_schema


DEFAULT_UNION_PATH = ROOT_DIR / "data" / "raw" / "torgi_opendata_tyumen_union.json"
DEFAULT_DETAIL_DIR = ROOT_DIR / "data" / "raw" / "torgi_sample_lots_full_20260507"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_dt(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date_parser.parse(value)
    except (TypeError, ValueError):
        return None


def _payload_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _notice_payload(detail: dict[str, Any]) -> dict[str, Any]:
    return (
        detail.get("exportObject", {})
        .get("structuredObject", {})
        .get("notice", {})
    )


def _first_lot(detail: dict[str, Any]) -> dict[str, Any]:
    lots = _notice_payload(detail).get("lots")
    if isinstance(lots, list) and lots and isinstance(lots[0], dict):
        return lots[0]
    return {}


def _organizer_data(item: dict[str, Any], detail: dict[str, Any] | None) -> dict[str, str | None]:
    if detail:
        org_info = _notice_payload(detail).get("bidderOrg", {}).get("orgInfo", {})
        if isinstance(org_info, dict):
            source_id = org_info.get("code") or org_info.get("INN") or item.get("bidderOrgCode")
            name = org_info.get("name")
            if source_id or name:
                return {
                    "source_id": str(source_id or item.get("bidderOrgCode") or "unknown"),
                    "name": str(name or item.get("bidderOrgCode") or "Не указан"),
                    "inn": org_info.get("INN"),
                    "kpp": org_info.get("KPP"),
                }
    normalized = normalize_lot(item)
    return normalized["organizer"]


def _upsert_notice(db: Session, item: dict[str, Any], structure_version: str) -> OpenDataNotice:
    href = item["href"]
    publish_date = _parse_dt(item.get("publishDate"))
    notice = db.scalar(select(OpenDataNotice).where(OpenDataNotice.href == href))
    if notice is None:
        notice = OpenDataNotice(
            reg_num=item.get("regNum", ""),
            document_type=item.get("documentType"),
            publish_date=publish_date,
            href=href,
            bidder_org_code=item.get("bidderOrgCode"),
            right_holder_code=item.get("rightHolderCode"),
            bidd_type_code=item.get("biddTypeCode"),
            ownership_forms_code=item.get("ownershipFormsCode"),
            subject_estate_code=item.get("subjectEstateCode"),
            subject_right_holder_code=item.get("subjectRightHolderCode"),
            payload=item,
            structure_version=structure_version,
        )
        db.add(notice)
        db.flush()
        return notice

    notice.reg_num = item.get("regNum", notice.reg_num)
    notice.document_type = item.get("documentType")
    notice.publish_date = publish_date
    notice.bidder_org_code = item.get("bidderOrgCode")
    notice.right_holder_code = item.get("rightHolderCode")
    notice.bidd_type_code = item.get("biddTypeCode")
    notice.ownership_forms_code = item.get("ownershipFormsCode")
    notice.subject_estate_code = item.get("subjectEstateCode")
    notice.subject_right_holder_code = item.get("subjectRightHolderCode")
    notice.payload = item
    notice.structure_version = structure_version
    db.flush()
    return notice


def _reset_demo_tables(db: Session) -> None:
    for model in (AlertEvent, LotSnapshot, Lot, Organizer, OpenDataNotice, IngestManifest, IngestRun):
        db.execute(delete(model))
    db.commit()


def _detail_by_reg_num(detail_dir: Path) -> dict[str, Path]:
    if not detail_dir.exists():
        return {}
    return {path.stem: path for path in detail_dir.glob("*.json") if path.is_file()}


def load_demo_data(*, union_path: Path, detail_dir: Path, reset: bool, target_region: str) -> dict[str, int]:
    sync_dev_schema()
    union = _load_json(union_path)
    items = union.get("items", [])
    if not isinstance(items, list):
        raise RuntimeError("Некорректный union-файл: ожидается поле items[].")

    details = _detail_by_reg_num(detail_dir)
    structure_version = str(union.get("schema_version") or "20240401")
    keywords = split_keywords(settings.izhs_keywords)

    counts = {
        "opendata_notices": 0,
        "details_found": 0,
        "lots_upserted": 0,
        "lots_skipped_no_detail": 0,
        "lots_skipped_region": 0,
        "izhs_candidates": 0,
        "with_price_per_sotka": 0,
    }

    db = SessionLocal()
    try:
        if reset:
            _reset_demo_tables(db)

        for item in items:
            if not isinstance(item, dict) or not item.get("href"):
                continue
            _upsert_notice(db, item, structure_version)
            counts["opendata_notices"] += 1
        db.commit()

        for item in items:
            if not isinstance(item, dict) or item.get("documentType") != "notice":
                continue
            reg_num = item.get("regNum")
            if not isinstance(reg_num, str) or not reg_num:
                continue
            detail_path = details.get(reg_num)
            if detail_path is None:
                counts["lots_skipped_no_detail"] += 1
                continue

            detail = _load_json(detail_path)
            counts["details_found"] += 1
            parsed = parse_notice_detail(detail)
            normalized = normalize_lot(item)
            if parsed.get("subject_region_code"):
                normalized["region"] = parsed["subject_region_code"]
            if target_region and str(normalized.get("region") or "") != target_region:
                counts["lots_skipped_region"] += 1
                continue

            first_lot = _first_lot(detail)
            if first_lot.get("lotStatus"):
                normalized["status"] = first_lot.get("lotStatus")
            normalized["cadastral_number"] = parsed.get("cadastral_number")
            normalized["area_sqm"] = parsed.get("area_sqm")
            normalized["land_category"] = parsed.get("land_category")
            normalized["permitted_use"] = parsed.get("permitted_use")
            permitted_use_codes = parsed.get("permitted_use_codes")
            if isinstance(permitted_use_codes, list):
                normalized["permitted_use_codes"] = ", ".join(str(code) for code in permitted_use_codes if code)
            normalized["address"] = parsed.get("address")
            normalized["municipality"] = parsed.get("municipality")
            normalized["settlement"] = parsed.get("settlement")
            normalized["notice_detail_url"] = item.get("href")
            normalized["raw"] = detail
            if parsed.get("lot_name"):
                normalized["title"] = parsed["lot_name"]
            if parsed.get("start_price") is not None:
                normalized["start_price"] = parsed["start_price"]
            normalized["is_izhs_candidate"] = match_izhs(detail, keywords)

            organizer_data = _organizer_data(item, detail)
            organizer = db.scalar(select(Organizer).where(Organizer.source_id == organizer_data["source_id"]))
            if organizer is None:
                organizer = Organizer(**organizer_data)
                db.add(organizer)
                db.flush()
            else:
                organizer.name = organizer_data["name"] or organizer.name
                organizer.inn = organizer_data["inn"]
                organizer.kpp = organizer_data["kpp"]

            notice = db.scalar(select(OpenDataNotice).where(OpenDataNotice.href == item["href"]))
            lot = db.scalar(select(Lot).where(Lot.source_id == normalized["source_id"]))
            if lot is None:
                lot = Lot(source_id=normalized["source_id"], title=normalized["title"], organizer_id=organizer.id)
                db.add(lot)
                db.flush()

            lot.title = normalized["title"]
            lot.status = normalized["status"]
            lot.region = normalized["region"]
            lot.category = normalized["category"]
            lot.start_price = normalized["start_price"]
            lot.current_price = normalized["current_price"]
            lot.start_date = normalized["start_date"]
            lot.end_date = normalized["end_date"]
            lot.latitude = normalized["latitude"]
            lot.longitude = normalized["longitude"]
            lot.source_url = normalized["source_url"]
            lot.organizer_id = organizer.id
            lot.cadastral_number = normalized.get("cadastral_number")
            lot.area_sqm = normalized.get("area_sqm")
            lot.land_category = normalized.get("land_category")
            lot.permitted_use = normalized.get("permitted_use")
            lot.permitted_use_codes = normalized.get("permitted_use_codes")
            lot.address = normalized.get("address")
            lot.municipality = normalized.get("municipality")
            lot.settlement = normalized.get("settlement")
            lot.notice_detail_url = normalized.get("notice_detail_url")
            identity = notice_identity_from_values(
                source_id=normalized.get("source_id"),
                notice_payload=notice.payload if notice and isinstance(notice.payload, dict) else None,
            )
            lot.notice_reg_num = identity.reg_num
            lot.notice_lot_number = identity.lot_number
            lot.notice_lot_count = identity.lot_count
            lot.is_izhs_candidate = bool(normalized.get("is_izhs_candidate"))
            lot.opendata_notice_id = notice.id if notice else None

            payload_hash = _payload_hash(detail)
            existing_snapshot = db.scalar(
                select(LotSnapshot).where(LotSnapshot.lot_id == lot.id, LotSnapshot.payload_hash == payload_hash)
            )
            if existing_snapshot is None:
                db.add(LotSnapshot(lot_id=lot.id, payload_hash=payload_hash, payload=detail))

            counts["lots_upserted"] += 1
            counts["izhs_candidates"] += int(bool(lot.is_izhs_candidate))
            counts["with_price_per_sotka"] += int(
                lot.start_price is not None and lot.area_sqm is not None and lot.area_sqm > 0
            )

        db.commit()
    finally:
        db.close()

    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Загрузить offline demo-набор Тюменской области в dev-БД.")
    parser.add_argument("--union-file", default=str(DEFAULT_UNION_PATH))
    parser.add_argument("--detail-dir", default=str(DEFAULT_DETAIL_DIR))
    parser.add_argument("--target-region", default="72")
    parser.add_argument("--reset", action="store_true", help="Очистить dev-таблицы перед загрузкой demo-набора.")
    args = parser.parse_args()

    counts = load_demo_data(
        union_path=Path(args.union_file),
        detail_dir=Path(args.detail_dir),
        reset=args.reset,
        target_region=args.target_region,
    )

    print("Demo Tyumen data loaded:")
    print(f"- union: {args.union_file}")
    print(f"- detail dir: {args.detail_dir}")
    print(f"- reset: {args.reset}")
    for key, value in counts.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
