import csv
from collections import defaultdict
from dataclasses import dataclass
from io import StringIO
from statistics import median
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import and_, case, desc, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import IngestRun, Lot, OpenDataNotice, Organizer
from app.schemas import (
    IngestRunView,
    LotDetail,
    LotFacets,
    LotListItem,
    LotListPage,
    MapPoint,
    OpenDataNoticeFacets,
    OpenDataNoticeListItem,
    OpenDataNoticeListPage,
)

router = APIRouter(prefix="/api")

LotsSort = Literal[
    "updated_at_desc",
    "price_per_sotka_asc",
    "price_per_sotka_desc",
    "discount_to_baseline_desc",
]


@dataclass(frozen=True)
class BaselineStats:
    price_per_sotka: float
    sample_size: int
    scope: str


@dataclass(frozen=True)
class LotValuation:
    baseline_price_per_sotka: float | None = None
    discount_to_baseline: float | None = None
    valuation_confidence: str | None = None
    valuation_baseline_scope: str | None = None
    valuation_baseline_sample_size: int | None = None
    valuation_reason: str | None = None


def _normalize_str_list(values: list[str] | None) -> list[str] | None:
    if not values:
        return None
    cleaned = [v.strip() for v in values if v and v.strip()]
    return cleaned or None


def _derived_prices(start_price: float | None, area_sqm: float | None) -> tuple[float | None, float | None]:
    """Rub per sotka (100 m²) and per m² from notice start_price and area; not market valuation."""
    if start_price is None or area_sqm is None or area_sqm <= 0:
        return None, None
    per_sqm = start_price / area_sqm
    per_sotka = start_price / (area_sqm / 100.0)
    return (round(per_sotka, 2), round(per_sqm, 2))


def _price_per_sotka(start_price: float | None, area_sqm: float | None) -> float | None:
    if start_price is None or area_sqm is None or area_sqm <= 0:
        return None
    return start_price / (area_sqm / 100.0)


def _baseline_bucket(values: list[float], scope: str) -> BaselineStats | None:
    if not values:
        return None
    return BaselineStats(
        price_per_sotka=round(float(median(values)), 2),
        sample_size=len(values),
        scope=scope,
    )


def _load_baseline_index(db: Session) -> dict[str, dict[Any, BaselineStats] | BaselineStats | None]:
    rows = db.execute(
        select(Lot.region, Lot.category, Lot.start_price, Lot.area_sqm).where(
            Lot.start_price.is_not(None),
            Lot.area_sqm.is_not(None),
            Lot.area_sqm > 0,
        )
    ).all()
    by_region_category: dict[tuple[str | None, str | None], list[float]] = defaultdict(list)
    by_region: dict[str | None, list[float]] = defaultdict(list)
    by_category: dict[str | None, list[float]] = defaultdict(list)
    global_values: list[float] = []

    for region, category, start_price, area_sqm in rows:
        value = _price_per_sotka(start_price, area_sqm)
        if value is None:
            continue
        by_region_category[(region, category)].append(value)
        by_region[region].append(value)
        by_category[category].append(value)
        global_values.append(value)

    return {
        "region_category": {
            key: stats
            for key, values in by_region_category.items()
            if (stats := _baseline_bucket(values, "region_category")) is not None
        },
        "region": {
            key: stats
            for key, values in by_region.items()
            if (stats := _baseline_bucket(values, "region")) is not None
        },
        "category": {
            key: stats
            for key, values in by_category.items()
            if (stats := _baseline_bucket(values, "category")) is not None
        },
        "global": _baseline_bucket(global_values, "global"),
    }


def _baseline_scope_label(scope: str) -> str:
    labels = {
        "region_category": "региону и виду торгов",
        "region": "региону",
        "category": "виду торгов",
        "global": "всем лотам с ценой и площадью",
    }
    return labels.get(scope, scope)


def _confidence(stats: BaselineStats) -> str:
    if stats.scope in {"region_category", "region"} and stats.sample_size >= 10:
        return "high"
    if stats.scope in {"region_category", "region", "category"} and stats.sample_size >= 5:
        return "medium"
    return "low"


def _pick_baseline(lot: Lot, index: dict[str, dict[Any, BaselineStats] | BaselineStats | None]) -> BaselineStats | None:
    region_category = index["region_category"]
    if isinstance(region_category, dict):
        stats = region_category.get((lot.region, lot.category))
        if stats and stats.sample_size >= 3:
            return stats

    by_region = index["region"]
    if isinstance(by_region, dict):
        stats = by_region.get(lot.region)
        if stats and stats.sample_size >= 3:
            return stats

    by_category = index["category"]
    if isinstance(by_category, dict):
        stats = by_category.get(lot.category)
        if stats and stats.sample_size >= 5:
            return stats

    global_stats = index["global"]
    if isinstance(global_stats, BaselineStats) and global_stats.sample_size >= 10:
        return global_stats
    return None


def _lot_valuation(lot: Lot, index: dict[str, dict[Any, BaselineStats] | BaselineStats | None]) -> LotValuation:
    current = _price_per_sotka(lot.start_price, lot.area_sqm)
    if current is None:
        return LotValuation(valuation_reason="Нет стартовой цены или площади для расчёта.")

    baseline = _pick_baseline(lot, index)
    if baseline is None or baseline.price_per_sotka <= 0:
        return LotValuation(valuation_reason="Недостаточно лотов с ценой и площадью для baseline.")

    discount = (baseline.price_per_sotka - current) / baseline.price_per_sotka
    return LotValuation(
        baseline_price_per_sotka=baseline.price_per_sotka,
        discount_to_baseline=round(discount, 4),
        valuation_confidence=_confidence(baseline),
        valuation_baseline_scope=baseline.scope,
        valuation_baseline_sample_size=baseline.sample_size,
        valuation_reason=(
            f"Сравнение с медианой по {_baseline_scope_label(baseline.scope)} "
            f"на основе {baseline.sample_size} лотов."
        ),
    )


def _lot_list_item(lot: Lot, valuation: LotValuation | None = None) -> LotListItem:
    ps, pm = _derived_prices(lot.start_price, lot.area_sqm)
    valuation = valuation or LotValuation()
    return LotListItem(
        id=lot.id,
        source_id=lot.source_id,
        title=lot.title,
        status=lot.status,
        region=lot.region,
        category=lot.category,
        start_price=lot.start_price,
        current_price=lot.current_price,
        start_date=lot.start_date,
        end_date=lot.end_date,
        cadastral_number=lot.cadastral_number,
        area_sqm=lot.area_sqm,
        is_izhs_candidate=bool(lot.is_izhs_candidate),
        start_price_per_sotka=ps,
        start_price_per_sqm=pm,
        baseline_price_per_sotka=valuation.baseline_price_per_sotka,
        discount_to_baseline=valuation.discount_to_baseline,
        valuation_confidence=valuation.valuation_confidence,
        valuation_baseline_scope=valuation.valuation_baseline_scope,
        valuation_baseline_sample_size=valuation.valuation_baseline_sample_size,
        valuation_reason=valuation.valuation_reason,
    )


def _lot_filters(
    region: str | None,
    status: str | None,
    category: list[str] | None,
    is_izhs: bool | None,
    min_area: float | None,
    max_area: float | None,
    max_start_price: float | None,
    cadastral_number: str | None,
) -> list:
    filters: list = []
    if region:
        filters.append(Lot.region == region)
    if status:
        filters.append(Lot.status == status)
    categories = _normalize_str_list(category)
    if categories:
        filters.append(Lot.category.in_(categories))
    if is_izhs is not None:
        filters.append(Lot.is_izhs_candidate.is_(is_izhs))
    if min_area is not None:
        filters.append(Lot.area_sqm >= min_area)
    if max_area is not None:
        filters.append(Lot.area_sqm <= max_area)
    if max_start_price is not None:
        filters.append(Lot.start_price <= max_start_price)
    if cadastral_number:
        filters.append(Lot.cadastral_number.ilike(f"%{cadastral_number}%"))
    return filters


def _lots_count(db: Session, filters: list) -> int:
    q = select(func.count(Lot.id))
    if filters:
        q = q.where(and_(*filters))
    return int(db.scalar(q) or 0)


def _lots_select_ordered(sort: LotsSort):
    price_per_sotka_expr = case(
        (
            and_(Lot.area_sqm.is_not(None), Lot.area_sqm > 0, Lot.start_price.is_not(None)),
            Lot.start_price / (Lot.area_sqm / 100.0),
        ),
        else_=None,
    )
    stmt = select(Lot)
    if sort == "price_per_sotka_asc":
        stmt = stmt.order_by(price_per_sotka_expr.asc().nulls_last(), desc(Lot.updated_at))
    elif sort == "price_per_sotka_desc":
        stmt = stmt.order_by(price_per_sotka_expr.desc().nulls_last(), desc(Lot.updated_at))
    else:
        stmt = stmt.order_by(desc(Lot.updated_at))
    return stmt


@router.get("/lots", response_model=LotListPage)
def list_lots(
    region: str | None = None,
    status: str | None = None,
    category: list[str] | None = Query(default=None),
    is_izhs: bool | None = None,
    min_area: float | None = None,
    max_area: float | None = None,
    max_start_price: float | None = None,
    cadastral_number: str | None = None,
    sort: LotsSort = "updated_at_desc",
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    filters = _lot_filters(region, status, category, is_izhs, min_area, max_area, max_start_price, cadastral_number)
    total = _lots_count(db, filters)
    baseline_index = _load_baseline_index(db)

    if sort == "discount_to_baseline_desc":
        stmt = select(Lot)
        if filters:
            stmt = stmt.where(and_(*filters))
        all_rows = db.scalars(stmt).all()
        valuations = {row.id: _lot_valuation(row, baseline_index) for row in all_rows}
        sorted_rows = sorted(
            all_rows,
            key=lambda row: (
                valuations[row.id].discount_to_baseline is not None,
                valuations[row.id].discount_to_baseline
                if valuations[row.id].discount_to_baseline is not None
                else -1_000_000.0,
            ),
            reverse=True,
        )
        rows = sorted_rows[offset : offset + limit]
        return LotListPage(
            items=[_lot_list_item(row, valuations[row.id]) for row in rows],
            total=total,
            limit=limit,
            offset=offset,
        )

    stmt = _lots_select_ordered(sort)
    if filters:
        stmt = stmt.where(and_(*filters))
    stmt = stmt.offset(offset).limit(limit)
    rows = db.scalars(stmt).all()
    valuations = {row.id: _lot_valuation(row, baseline_index) for row in rows}
    return LotListPage(
        items=[_lot_list_item(row, valuations[row.id]) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/export/lots.csv")
def export_lots_csv(
    region: str | None = None,
    status: str | None = None,
    category: list[str] | None = Query(default=None),
    is_izhs: bool | None = None,
    min_area: float | None = None,
    max_area: float | None = None,
    max_start_price: float | None = None,
    cadastral_number: str | None = None,
    sort: LotsSort = "updated_at_desc",
    max_rows: int = Query(default=10_000, ge=1, le=50_000),
    db: Session = Depends(get_db),
):
    filters = _lot_filters(region, status, category, is_izhs, min_area, max_area, max_start_price, cadastral_number)
    baseline_index = _load_baseline_index(db)

    if sort == "discount_to_baseline_desc":
        stmt = select(Lot)
        if filters:
            stmt = stmt.where(and_(*filters))
        rows = db.scalars(stmt).all()
        valuations = {row.id: _lot_valuation(row, baseline_index) for row in rows}
        rows = sorted(
            rows,
            key=lambda row: (
                valuations[row.id].discount_to_baseline is not None,
                valuations[row.id].discount_to_baseline
                if valuations[row.id].discount_to_baseline is not None
                else -1_000_000.0,
            ),
            reverse=True,
        )[:max_rows]
    else:
        stmt = _lots_select_ordered(sort)
        if filters:
            stmt = stmt.where(and_(*filters))
        stmt = stmt.limit(max_rows)
        rows = db.scalars(stmt).all()
        valuations = {row.id: _lot_valuation(row, baseline_index) for row in rows}

    buf = StringIO()
    buf.write("\ufeff")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(
        [
            "id",
            "source_id",
            "title",
            "status",
            "region",
            "category",
            "start_price",
            "current_price",
            "area_sqm",
            "start_price_per_sotka",
            "start_price_per_sqm",
            "baseline_price_per_sotka",
            "discount_to_baseline",
            "valuation_confidence",
            "valuation_baseline_scope",
            "valuation_baseline_sample_size",
            "cadastral_number",
            "is_izhs_candidate",
            "start_date",
            "end_date",
            "source_url",
        ]
    )
    for lot in rows:
        ps, pm = _derived_prices(lot.start_price, lot.area_sqm)
        valuation = valuations[lot.id]
        writer.writerow(
            [
                lot.id,
                lot.source_id,
                lot.title,
                lot.status or "",
                lot.region or "",
                lot.category or "",
                lot.start_price if lot.start_price is not None else "",
                lot.current_price if lot.current_price is not None else "",
                lot.area_sqm if lot.area_sqm is not None else "",
                ps if ps is not None else "",
                pm if pm is not None else "",
                valuation.baseline_price_per_sotka if valuation.baseline_price_per_sotka is not None else "",
                valuation.discount_to_baseline if valuation.discount_to_baseline is not None else "",
                valuation.valuation_confidence or "",
                valuation.valuation_baseline_scope or "",
                valuation.valuation_baseline_sample_size
                if valuation.valuation_baseline_sample_size is not None
                else "",
                lot.cadastral_number or "",
                "1" if lot.is_izhs_candidate else "0",
                lot.start_date.isoformat() if lot.start_date else "",
                lot.end_date.isoformat() if lot.end_date else "",
                lot.source_url or "",
            ]
        )

    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="lots_export.csv"'},
    )


@router.get("/lots/facets", response_model=LotFacets)
def lot_facets(db: Session = Depends(get_db)):
    def distinct_strings(column):
        rows = db.scalars(
            select(column)
            .where(column.is_not(None))
            .where(column != "")
            .distinct()
            .order_by(column)
        ).all()
        return [r for r in rows if r]

    return LotFacets(
        category=distinct_strings(Lot.category),
        status=distinct_strings(Lot.status),
        region=distinct_strings(Lot.region),
    )


@router.get("/lots/{lot_id}", response_model=LotDetail)
def get_lot(lot_id: int, db: Session = Depends(get_db)):
    row = db.execute(
        select(Lot, Organizer)
        .join(Organizer, Organizer.id == Lot.organizer_id, isouter=True)
        .where(Lot.id == lot_id)
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Lot not found")
    lot, organizer = row

    notice_payload: dict[str, Any] | None = None
    if lot.opendata_notice_id is not None:
        notice = db.scalar(select(OpenDataNotice).where(OpenDataNotice.id == lot.opendata_notice_id))
        if notice is not None and isinstance(notice.payload, dict):
            notice_payload = notice.payload

    ps, pm = _derived_prices(lot.start_price, lot.area_sqm)
    valuation = _lot_valuation(lot, _load_baseline_index(db))
    return LotDetail(
        id=lot.id,
        source_id=lot.source_id,
        title=lot.title,
        status=lot.status,
        region=lot.region,
        category=lot.category,
        start_price=lot.start_price,
        current_price=lot.current_price,
        start_date=lot.start_date,
        end_date=lot.end_date,
        latitude=lot.latitude,
        longitude=lot.longitude,
        source_url=lot.source_url,
        organizer_name=organizer.name if organizer else None,
        organizer_inn=organizer.inn if organizer else None,
        cadastral_number=lot.cadastral_number,
        area_sqm=lot.area_sqm,
        is_izhs_candidate=bool(lot.is_izhs_candidate),
        start_price_per_sotka=ps,
        start_price_per_sqm=pm,
        baseline_price_per_sotka=valuation.baseline_price_per_sotka,
        discount_to_baseline=valuation.discount_to_baseline,
        valuation_confidence=valuation.valuation_confidence,
        valuation_baseline_scope=valuation.valuation_baseline_scope,
        valuation_baseline_sample_size=valuation.valuation_baseline_sample_size,
        valuation_reason=valuation.valuation_reason,
        land_category=lot.land_category,
        permitted_use=lot.permitted_use,
        address=lot.address,
        notice_detail_url=lot.notice_detail_url,
        opendata_notice_id=lot.opendata_notice_id,
        notice_payload=notice_payload,
    )


@router.get("/lots-map", response_model=list[MapPoint])
def map_points(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Lot).where(Lot.latitude.is_not(None), Lot.longitude.is_not(None)).order_by(desc(Lot.updated_at)).limit(5000)
    ).all()
    return [
        MapPoint(
            lot_id=row.id,
            title=row.title,
            status=row.status,
            latitude=row.latitude,  # type: ignore[arg-type]
            longitude=row.longitude,  # type: ignore[arg-type]
        )
        for row in rows
    ]


@router.get("/ingest-runs", response_model=list[IngestRunView])
def get_ingest_runs(limit: int = Query(default=20, ge=1, le=200), db: Session = Depends(get_db)):
    rows = db.scalars(select(IngestRun).order_by(desc(IngestRun.started_at)).limit(limit)).all()
    return [IngestRunView.model_validate(row, from_attributes=True) for row in rows]


@router.get("/opendata-notices/facets", response_model=OpenDataNoticeFacets)
def opendata_notice_facets(db: Session = Depends(get_db)):
    def distinct_strings(column):
        rows = db.scalars(
            select(column)
            .where(column.is_not(None))
            .where(column != "")
            .distinct()
            .order_by(column)
        ).all()
        return [r for r in rows if r]

    return OpenDataNoticeFacets(
        bidd_type_code=distinct_strings(OpenDataNotice.bidd_type_code),
        document_type=distinct_strings(OpenDataNotice.document_type),
    )


@router.get("/opendata-notices", response_model=OpenDataNoticeListPage)
def list_opendata_notices(
    document_type: list[str] | None = Query(default=None),
    bidd_type_code: list[str] | None = Query(default=None),
    reg_num: str | None = None,
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    filters = []
    doc_types = _normalize_str_list(document_type)
    if doc_types:
        filters.append(OpenDataNotice.document_type.in_(doc_types))
    bidd_types = _normalize_str_list(bidd_type_code)
    if bidd_types:
        filters.append(OpenDataNotice.bidd_type_code.in_(bidd_types))
    if reg_num:
        filters.append(OpenDataNotice.reg_num == reg_num)

    total_stmt = select(func.count(OpenDataNotice.id))
    if filters:
        total_stmt = total_stmt.where(and_(*filters))
    total = int(db.scalar(total_stmt) or 0)

    stmt = select(OpenDataNotice).order_by(desc(OpenDataNotice.publish_date)).offset(offset).limit(limit)
    if filters:
        stmt = stmt.where(and_(*filters))

    rows = db.scalars(stmt).all()
    return OpenDataNoticeListPage(
        items=[OpenDataNoticeListItem.model_validate(row, from_attributes=True) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
