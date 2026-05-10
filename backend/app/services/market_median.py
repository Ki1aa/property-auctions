"""Median ₽/sotka from MarketComparable listings; separate from internal auction baseline."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Lot, MarketComparable
from app.services.lot_baseline import LotValuation, price_per_sotka


def _comparable_per_sotka(row: MarketComparable) -> float | None:
    if row.price_rub is None or row.area_sqm is None or row.area_sqm <= 0:
        return None
    return float(row.price_rub) / (float(row.area_sqm) / 100.0)


def load_market_median_stats(db: Session) -> dict[str, tuple[float, int]]:
    """region_code -> (median_per_sotka, n); includes '_global' when enough rows."""
    rows = db.scalars(select(MarketComparable)).all()
    by_region: dict[str | None, list[float]] = defaultdict(list)
    global_vals: list[float] = []
    for row in rows:
        p = _comparable_per_sotka(row)
        if p is None or p <= 0:
            continue
        global_vals.append(p)
        by_region[row.region_code].append(p)

    out: dict[str, tuple[float, int]] = {}
    for reg, vals in by_region.items():
        if reg is None or not vals:
            continue
        key = str(reg).strip()
        if len(vals) >= 2:
            out[key] = (round(float(median(vals)), 2), len(vals))
    if len(global_vals) >= 3:
        out["_global"] = (round(float(median(global_vals)), 2), len(global_vals))
    return out


def _pick_market_row(
    lot: Lot, stats: dict[str, tuple[float, int]]
) -> tuple[float, int, str] | None:
    region = str(lot.region or "").strip()
    if region and region in stats:
        med, n = stats[region]
        return med, n, "region"
    g = stats.get("_global")
    if g:
        med, n = g
        return med, n, "global"
    return None


def _investment_score(lot: Lot, valuation: LotValuation) -> float | None:
    disc = valuation.discount_to_market
    if disc is None:
        disc = valuation.discount_to_baseline
    if disc is None:
        return None
    score = max(0.0, min(1.0, float(disc))) * 100.0
    if lot.is_izhs_candidate:
        score *= 1.12
    if (lot.cadastral_number or "").strip():
        score *= 1.05
    return round(min(100.0, score), 1)


def valuation_with_market(
    lot: Lot,
    valuation: LotValuation,
    market_stats: dict[str, tuple[float, int]],
) -> LotValuation:
    picked = _pick_market_row(lot, market_stats)
    current = price_per_sotka(lot.start_price, lot.area_sqm)
    if picked is None or current is None:
        return replace(
            valuation,
            investment_score=_investment_score(lot, valuation),
        )

    med, n, scope = picked
    if med <= 0:
        return replace(valuation, investment_score=_investment_score(lot, valuation))

    market_discount = round((med - current) / med, 4)
    scope_ru = "региону" if scope == "region" else "всем аналогам в базе"
    reason = f"Медиана рыночных объявлений по {scope_ru} ({n} шт.)."
    merged = replace(
        valuation,
        market_baseline_price_per_sotka=med,
        discount_to_market=market_discount,
        market_valuation_reason=reason,
    )
    return replace(merged, investment_score=_investment_score(lot, merged))
