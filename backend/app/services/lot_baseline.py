"""Internal auction baseline (median ₽/sotka); shared by REST API and Telegram alerts."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from statistics import median
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Lot


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


def derived_prices(start_price: float | None, area_sqm: float | None) -> tuple[float | None, float | None]:
    """Rub per sotka (100 m²) and per m² from notice start_price and area; not market valuation."""
    if start_price is None or area_sqm is None or area_sqm <= 0:
        return None, None
    per_sqm = start_price / area_sqm
    per_sotka = start_price / (area_sqm / 100.0)
    return (round(per_sotka, 2), round(per_sqm, 2))


def price_per_sotka(start_price: float | None, area_sqm: float | None) -> float | None:
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


def load_baseline_index(db: Session) -> dict[str, dict[Any, BaselineStats] | BaselineStats | None]:
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
        value = price_per_sotka(start_price, area_sqm)
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


def lot_valuation(lot: Lot, index: dict[str, dict[Any, BaselineStats] | BaselineStats | None]) -> LotValuation:
    current = price_per_sotka(lot.start_price, lot.area_sqm)
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


def has_positive_discount(valuation: LotValuation) -> bool:
    return valuation.discount_to_baseline is not None and valuation.discount_to_baseline > 0
