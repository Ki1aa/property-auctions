import hashlib
import html
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AlertEvent, Lot, LotSnapshot, OpenDataNotice, TelegramDigestItem
from app.services.alerts.telegram import send_telegram_message
from app.services.external_lot_links import (
    app_public_lot_url,
    domclick_land_map_url,
    domclick_land_search_url,
    domclick_land_search_url_cadastral_only,
    nspd_lot_map_url,
    pkk_lot_map_url,
    torgi_notice_html_url,
    torgi_notice_json_link_when_distinct,
    torgi_public_url,
)
from app.services.lot_baseline import LotValuation, derived_prices, load_baseline_index, lot_valuation
from app.services.market_median import load_market_median_stats, valuation_with_market
from app.services.lot_identity import lot_notice_identity

logger = logging.getLogger(__name__)


def _esc_html_text(value: object) -> str:
    return html.escape(str(value), quote=False)


def _esc_html_attr(value: str) -> str:
    return html.escape(value, quote=True)


def _append_unique_link(
    parts: list[str],
    seen: set[str],
    href: str | None,
    label: str,
) -> None:
    if not href:
        return
    if href in seen:
        return
    seen.add(href)
    parts.append(f'<a href="{_esc_html_attr(href)}">{_esc_html_text(label)}</a>')


def _yes_no(value: bool) -> str:
    return "да" if value else "нет"


def _telegram_alert_region_codes() -> set[str]:
    return {
        item.strip()
        for item in settings.telegram_alert_region_codes.split(",")
        if item.strip()
    }


def _passes_telegram_region_filter(lot: Lot) -> bool:
    codes = _telegram_alert_region_codes()
    if not codes:
        return True
    return str(lot.region or "").strip() in codes


def _telegram_region_scope_note() -> str | None:
    codes = sorted(_telegram_alert_region_codes())
    if not codes:
        return None
    if codes == ["72"]:
        return "Оповещения Telegram настроены только на Тюменскую область (регион 72)."
    return "Оповещения Telegram настроены только на регионы: " + ", ".join(codes) + "."


def _format_number(value: float | None, *, digits: int = 2) -> str:
    if value is None:
        return "—"
    rounded = round(float(value), digits)
    if rounded == int(rounded):
        return f"{int(rounded):,}".replace(",", " ")
    return f"{rounded:,.{digits}f}".replace(",", " ").replace(".", ",")


def _format_money(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{_format_number(value, digits=0)} ₽"


def _format_percent(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{round(value * 100, 2)}%"


def _format_datetime(value: object) -> str:
    if value is None:
        return "—"
    if hasattr(value, "strftime"):
        return value.strftime("%d.%m.%Y %H:%M")  # type: ignore[attr-defined]
    return str(value)


def _event_label(event_type: str) -> str:
    return {
        "new_lot": "Новый лот",
        "changed_lot": "Изменилась цена лота",
    }.get(event_type, event_type)


def _nspd_status(lot: Lot) -> str:
    if lot.nspd_enriched_at is None:
        return "не проверялось"
    if lot.nspd_specified_area_sqm is not None or lot.nspd_readable_address or lot.nspd_cost_value is not None:
        parts: list[str] = ["найдено"]
        if lot.nspd_specified_area_sqm is not None:
            parts.append(f"площадь {_format_number(lot.nspd_specified_area_sqm)} м²")
        if lot.nspd_cost_value is not None:
            parts.append(f"кадастровая стоимость {_format_money(lot.nspd_cost_value)}")
        return ", ".join(parts)
    return "проверено, данные не найдены"


def _alert_verdict(lot: Lot, valuation: LotValuation) -> tuple[str, list[str]]:
    reasons: list[str] = []
    discount = valuation.discount_to_baseline

    if lot.is_izhs_candidate:
        reasons.append("ВРИ похож на ИЖС/ЛПХ/садоводство")
    else:
        reasons.append("ВРИ не подтверждён как ИЖС-кандидат")

    if lot.cadastral_number:
        reasons.append("есть кадастровый номер")
    else:
        reasons.append("нет кадастрового номера")

    if discount is not None:
        if discount >= 0.25:
            reasons.append(f"сильный дисконт к baseline: {_format_percent(discount)}")
        elif discount >= 0.1:
            reasons.append(f"умеренный дисконт к baseline: {_format_percent(discount)}")
        elif discount > 0:
            reasons.append(f"небольшой дисконт к baseline: {_format_percent(discount)}")
        else:
            reasons.append(f"дороже или на уровне baseline: {_format_percent(discount)}")
    else:
        reasons.append(valuation.valuation_reason or "baseline пока не рассчитан")

    if lot.is_izhs_candidate and lot.cadastral_number and discount is not None and discount >= 0.1:
        return "интересно, смотреть глубже", reasons
    if lot.cadastral_number and discount is not None and discount >= 0.25:
        return "проверить вручную, сильный дисконт", reasons
    if not lot.cadastral_number or lot.area_sqm is None or lot.start_price is None:
        return "недостаточно данных для оценки", reasons
    if discount is not None and discount <= 0:
        return "низкий приоритет по baseline", reasons
    return "проверить при наличии времени", reasons


def _notice_identity(lot: Lot, latest_payload: dict[str, Any] | None) -> tuple[str | None, str | None, int | None]:
    identity = lot_notice_identity(lot, latest_payload)
    return identity.reg_num, identity.lot_number, identity.lot_count


def _notice_line(lot: Lot, latest_payload: dict[str, Any] | None) -> str:
    reg_num, lot_number, lot_count = _notice_identity(lot, latest_payload)
    if not reg_num and not lot_number:
        sid = (lot.source_id or "").strip()
        if sid and len(sid) <= 80 and not sid.lower().startswith("http"):
            return f"ГИС: извещение не определено (source_id: {sid})"
        if lot.id:
            return f"ГИС: извещение не определено (id лота в мониторе: {lot.id})"
        return "ГИС: извещение не определено"
    parts: list[str] = []
    if reg_num:
        parts.append(f"извещение {reg_num}")
    if lot_number and lot_count:
        parts.append(f"лот {lot_number} из {lot_count}")
    elif lot_number:
        parts.append(f"лот {lot_number}")
    return "ГИС: " + ", ".join(parts)


def _compact_join(parts: list[object | None], sep: str = ", ") -> str:
    cleaned = [str(part).strip() for part in parts if part is not None and str(part).strip()]
    return sep.join(cleaned) if cleaned else "—"


def _valuation_line(valuation: LotValuation) -> str:
    pieces: list[str] = []
    if valuation.baseline_price_per_sotka is not None:
        pieces.append(f"baseline {_format_money(valuation.baseline_price_per_sotka)}/сотка")
    if valuation.discount_to_baseline is not None:
        pieces.append(f"дисконт {_format_percent(valuation.discount_to_baseline)}")
    if valuation.market_baseline_price_per_sotka is not None:
        pieces.append(f"рынок {_format_money(valuation.market_baseline_price_per_sotka)}/сотка")
    if valuation.discount_to_market is not None:
        pieces.append(f"дисконт к рынку {_format_percent(valuation.discount_to_market)}")
    if valuation.investment_score is not None:
        pieces.append(f"score {valuation.investment_score}")
    if valuation.valuation_confidence:
        pieces.append(f"уверенность {valuation.valuation_confidence}")
    return _compact_join(pieces, " | ")


def _why_interesting_text(lot: Lot, valuation: LotValuation, start_price_per_sotka: float | None) -> str:
    parts: list[str] = []
    if lot.is_izhs_candidate:
        parts.append("ИЖС-кандидат")
    if (lot.cadastral_number or "").strip():
        parts.append("есть кадастр")
    if start_price_per_sotka is not None:
        parts.append(f"цена {_format_money(start_price_per_sotka)}/сотка")
    if valuation.discount_to_baseline is not None and valuation.discount_to_baseline > 0:
        parts.append(f"ниже внутр. baseline на {_format_percent(valuation.discount_to_baseline)}")
    if valuation.discount_to_market is not None and valuation.discount_to_market > 0:
        parts.append(f"ниже медианы объявлений на {_format_percent(valuation.discount_to_market)}")
    if valuation.investment_score is not None:
        parts.append(f"investment_score≈{valuation.investment_score}")
    return "; ".join(parts)


def _is_low_signal_alert(lot: Lot, valuation: LotValuation, start_price_per_sotka: float | None) -> bool:
    """True when sending this to Telegram would be noise for the MVP decision flow."""
    if lot.is_izhs_candidate:
        return False
    if (lot.cadastral_number or "").strip():
        return False

    idn = lot_notice_identity(lot, None)
    has_notice = bool((idn.reg_num or "").strip())
    worthless_metrics = start_price_per_sotka is None and valuation.discount_to_baseline is None
    if worthless_metrics:
        return True
    disc = valuation.discount_to_baseline
    meaningful_discount = disc is not None and disc > 0
    if not has_notice and not meaningful_discount:
        # No GIS regNum and no positive baseline signal — noise (e.g. test rows with only price/area).
        return True
    return False


async def notify_lot_event(db: Session, lot: Lot, event_type: str, payload: str) -> None:
    if not settings.telegram_alerts_enabled:
        return
    if not (settings.telegram_bot_token or "").strip() or not (settings.telegram_chat_id or "").strip():
        return
    if not _passes_telegram_region_filter(lot):
        return
    if settings.telegram_alert_only_izhs and not lot.is_izhs_candidate:
        return
    if settings.telegram_alert_require_cadastral and not (lot.cadastral_number or "").strip():
        return

    event_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    baseline_index = load_baseline_index(db)
    market_stats = load_market_median_stats(db)
    valuation = valuation_with_market(lot, lot_valuation(lot, baseline_index), market_stats)
    start_price_per_sotka, start_price_per_sqm = derived_prices(lot.start_price, lot.area_sqm)
    if settings.telegram_alert_skip_low_signal and _is_low_signal_alert(lot, valuation, start_price_per_sotka):
        return

    if settings.telegram_alert_require_discount_or_per_sotka:
        if valuation.discount_to_baseline is None and start_price_per_sotka is None:
            return

    min_disc = settings.telegram_alert_min_discount_to_baseline
    if min_disc is not None:
        if valuation.discount_to_baseline is None:
            if settings.telegram_alert_require_baseline_for_discount:
                return
        elif valuation.discount_to_baseline < min_disc:
            return

    exists = db.scalar(
        select(AlertEvent).where(
            AlertEvent.lot_id == lot.id,
            AlertEvent.event_type == event_type,
            AlertEvent.event_hash == event_hash,
        )
    )
    if exists:
        return

    if settings.telegram_digest_enabled:
        dup = db.scalar(
            select(TelegramDigestItem.id).where(
                TelegramDigestItem.lot_id == lot.id,
                TelegramDigestItem.event_type == event_type,
                TelegramDigestItem.event_hash == event_hash,
            )
        )
        if dup:
            return
        db.add(TelegramDigestItem(lot_id=lot.id, event_type=event_type, event_hash=event_hash))
        db.commit()
        return

    notice_payload: dict[str, Any] | None = None
    if lot.opendata_notice_id is not None:
        notice = db.scalar(select(OpenDataNotice).where(OpenDataNotice.id == lot.opendata_notice_id))
        if notice is not None and isinstance(notice.payload, dict):
            notice_payload = notice.payload
    latest_snapshot = db.scalar(
        select(LotSnapshot).where(LotSnapshot.lot_id == lot.id).order_by(LotSnapshot.id.desc())
    )
    latest_payload = latest_snapshot.payload if latest_snapshot is not None and isinstance(latest_snapshot.payload, dict) else None

    t_url = torgi_public_url(lot, notice_payload, latest_payload)
    t_notice_url = torgi_notice_html_url(lot, notice_payload)
    t_json = torgi_notice_json_link_when_distinct(lot, notice_payload, latest_payload)
    nspd_u = nspd_lot_map_url(lot)
    app_u = app_public_lot_url(lot.id)
    dom_map = domclick_land_map_url(lot)
    dom = domclick_land_search_url(lot)
    dom_cad = domclick_land_search_url_cadastral_only(lot)
    verdict, verdict_reasons = _alert_verdict(lot, valuation)
    location = _compact_join([lot.municipality, lot.settlement, lot.region])
    land_line = _compact_join(
        [
            f"{_format_number(lot.area_sqm)} м²" if lot.area_sqm is not None else None,
            lot.land_category,
            lot.permitted_use,
            f"ВРИ {lot.permitted_use_codes}" if lot.permitted_use_codes else None,
        ],
        " | ",
    )
    current_price_part = ""
    if lot.current_price is not None and lot.current_price != lot.start_price:
        current_price_part = f" | сейчас {_format_money(lot.current_price)}"

    lines: list[str] = [
        f"<b>{_esc_html_text(_event_label(event_type))}: {_esc_html_text(verdict)}</b>",
        "",
        f"<b>{_esc_html_text(lot.title)}</b>",
        _esc_html_text(_notice_line(lot, latest_payload)),
        f"Локация: {_esc_html_text(location)}",
        f"Кадастр: {_esc_html_text(lot.cadastral_number or '—')}",
        f"Земля: {_esc_html_text(land_line)}",
        f"ИЖС: {_esc_html_text(_yes_no(lot.is_izhs_candidate))} | НСПД: {_esc_html_text(_nspd_status(lot))}",
        f"Цена: старт {_esc_html_text(_format_money(lot.start_price))}{_esc_html_text(current_price_part)}",
        f"Цена за сотку: {_esc_html_text(_format_money(start_price_per_sotka))} | за м²: {_esc_html_text(_format_money(start_price_per_sqm))}",
        f"Оценка: {_esc_html_text(_valuation_line(valuation))}",
        f"Заявки: {_esc_html_text(_format_datetime(lot.start_date))} - {_esc_html_text(_format_datetime(lot.end_date))}",
        f"Сигналы: {_esc_html_text('; '.join(verdict_reasons))}",
    ]
    why = _why_interesting_text(lot, valuation, start_price_per_sotka)
    if why:
        lines.append("")
        lines.append(f"<b>Почему интересно:</b> {_esc_html_text(why)}")
    if valuation.valuation_reason and valuation.valuation_reason not in verdict_reasons:
        lines.append(f"Пояснение baseline: {_esc_html_text(valuation.valuation_reason)}")
    if lot.address:
        lines.append(f"Адрес: {_esc_html_text(lot.address)}")
    lines.append("")
    lines.append("Ссылки:")
    link_parts: list[str] = []
    seen_urls: set[str] = set()
    _append_unique_link(link_parts, seen_urls, app_u, "Монитор")
    _append_unique_link(link_parts, seen_urls, t_url, "ГИС Торги (лот)")
    _append_unique_link(link_parts, seen_urls, t_notice_url, "ГИС Торги (извещение)")
    _append_unique_link(link_parts, seen_urls, pkk_lot_map_url(lot), "ПКК (НСПД)")
    _append_unique_link(link_parts, seen_urls, nspd_u, "НСПД (ФГИС ЕГРН)")
    _append_unique_link(link_parts, seen_urls, dom_map, "Домклик (карта)")
    if settings.domclick_cadastral_search_enabled:
        _append_unique_link(link_parts, seen_urls, dom_cad, "Домклик (поиск, кадастр)")
    if settings.include_marketplace_search_urls:
        _append_unique_link(link_parts, seen_urls, dom, "Домклик (поиск, расширенный)")
    _append_unique_link(link_parts, seen_urls, t_json, "ГИС Торги (JSON)")
    lines.append(" | ".join(link_parts) if link_parts else "—")
    lines.append("")
    lines.append("<i>Baseline считается по уже загруженным торгам, это ещё не рыночная оценка по объявлениям.</i>")
    if settings.domclick_cadastral_search_enabled or settings.include_marketplace_search_urls:
        lines.append(
            "<i>Домклик (поиск): шаблонный запрос по кадастру/адресу; не гарантирует карточку участка.</i>"
        )
    if dom_map:
        lines.append(
            "<i>Домклик: карта объявлений вокруг участка для оценки цен соседних лотов; не официальная оценка.</i>"
        )
    if nspd_u:
        lines.append("<i>НСПД: если карта не откроет участок автоматически, вставьте кадастровый номер в поиск.</i>")
    region_note = _telegram_region_scope_note()
    if region_note:
        lines.append(f"<i>{_esc_html_text(region_note)}</i>")

    message = "\n".join(lines)
    try:
        await send_telegram_message(
            settings.telegram_bot_token,
            settings.telegram_chat_id,
            message,
            parse_mode="HTML",
            disable_web_page_preview=settings.telegram_disable_web_page_preview,
        )
    except Exception:
        logger.warning("Telegram alert send failed for lot_id=%s event=%s", lot.id, event_type, exc_info=True)
        return
    db.add(AlertEvent(lot_id=lot.id, event_type=event_type, event_hash=event_hash))


async def flush_telegram_digest(db: Session) -> None:
    if not settings.telegram_alerts_enabled or not settings.telegram_digest_enabled:
        return
    if not (settings.telegram_bot_token or "").strip() or not (settings.telegram_chat_id or "").strip():
        return

    rows = list(db.scalars(select(TelegramDigestItem).order_by(TelegramDigestItem.id)).all())
    if not rows:
        return

    baseline_index = load_baseline_index(db)
    market_stats = load_market_median_stats(db)
    parts: list[str] = [
        "<b>Дайджест лотов</b>",
        f"<i>Событий: {len(rows)}</i>",
        "",
    ]
    region_note = _telegram_region_scope_note()
    if region_note:
        parts.append(f"<i>{_esc_html_text(region_note)}</i>")
        parts.append("")
    sent_items: list[TelegramDigestItem] = []
    for item in rows:
        row_lot = db.get(Lot, item.lot_id)
        if not row_lot:
            db.delete(item)
            continue
        if not _passes_telegram_region_filter(row_lot):
            db.delete(item)
            continue
        sent_items.append(item)
        valuation = valuation_with_market(row_lot, lot_valuation(row_lot, baseline_index), market_stats)
        per_sotka, _ = derived_prices(row_lot.start_price, row_lot.area_sqm)
        why = _why_interesting_text(row_lot, valuation, per_sotka)
        label = _event_label(item.event_type)
        parts.append(
            f"<b>{_esc_html_text(label)}</b> · id {row_lot.id}<br/>"
            f"{_esc_html_text(row_lot.title)}<br/>"
            f"<i>{_esc_html_text(why or '—')}</i>"
        )
        parts.append("")

    if not sent_items:
        db.commit()
        return

    body = "\n".join(parts).strip()
    max_len = max(500, settings.telegram_max_message_length - 64)
    if len(body) > max_len:
        body = body[:max_len] + "\n<i>…обрезано</i>"

    try:
        await send_telegram_message(
            settings.telegram_bot_token,
            settings.telegram_chat_id,
            body,
            parse_mode="HTML",
            disable_web_page_preview=settings.telegram_disable_web_page_preview,
        )
    except Exception:
        logger.warning("Telegram digest send failed", exc_info=True)
        return
    for item in sent_items:
        db.add(AlertEvent(lot_id=item.lot_id, event_type=item.event_type, event_hash=item.event_hash))
        db.delete(item)
    db.commit()
