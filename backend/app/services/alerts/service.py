import hashlib
import html
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AlertEvent, Lot, LotSnapshot, OpenDataNotice
from app.services.alerts.telegram import send_telegram_message
from app.services.external_lot_links import (
    app_public_lot_url,
    avito_search_url,
    avito_search_url_cadastral_only,
    cian_land_search_url,
    cian_land_search_url_cadastral_only,
    domclick_land_map_url,
    domclick_land_search_url,
    domclick_land_search_url_cadastral_only,
    nspd_lot_map_url,
    torgi_notice_html_url,
    torgi_notice_json_link_when_distinct,
    torgi_public_url,
)
from app.services.lot_baseline import LotValuation, derived_prices


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
        "changed_lot": "Изменение лота",
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
    source_id = (lot.source_id or "").strip()
    notice_reg_num: str | None = None
    lot_number: str | None = None
    lot_count: int | None = None

    if ":lot:" in source_id:
        notice_reg_num, lot_number = source_id.split(":lot:", 1)
    elif source_id.isdigit():
        notice_reg_num = source_id

    if latest_payload:
        raw_count = latest_payload.get("_notice_lot_count")
        if isinstance(raw_count, int) and raw_count > 0:
            lot_count = raw_count
        elif isinstance(raw_count, str) and raw_count.isdigit():
            lot_count = int(raw_count)

        raw_lot = latest_payload.get("_notice_lot")
        if isinstance(raw_lot, dict):
            raw_number = raw_lot.get("lotNumber")
            if raw_number is not None and str(raw_number).strip():
                lot_number = str(raw_number).strip()

        raw_index = latest_payload.get("_notice_lot_index")
        if lot_number is None and isinstance(raw_index, int):
            lot_number = str(raw_index + 1)

    if lot_count and lot_count > 1 and lot_number is None:
        lot_number = "1"

    return notice_reg_num, lot_number, lot_count


def _notice_line(lot: Lot, latest_payload: dict[str, Any] | None) -> str:
    reg_num, lot_number, lot_count = _notice_identity(lot, latest_payload)
    if not reg_num and not lot_number:
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
    if valuation.valuation_confidence:
        pieces.append(f"уверенность {valuation.valuation_confidence}")
    return _compact_join(pieces, " | ")


def _is_low_signal_alert(lot: Lot, valuation: LotValuation, start_price_per_sotka: float | None) -> bool:
    """True when sending this to Telegram would be noise for the MVP decision flow."""
    return (
        not lot.is_izhs_candidate
        and not (lot.cadastral_number or "").strip()
        and start_price_per_sotka is None
        and valuation.discount_to_baseline is None
    )


async def notify_lot_event(db: Session, lot: Lot, event_type: str, payload: str) -> None:
    if not settings.telegram_alerts_enabled:
        return
    if settings.telegram_alert_only_izhs and not lot.is_izhs_candidate:
        return
    if settings.telegram_alert_require_cadastral and not (lot.cadastral_number or "").strip():
        return

    event_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    exists = db.scalar(
        select(AlertEvent).where(
            AlertEvent.lot_id == lot.id,
            AlertEvent.event_type == event_type,
            AlertEvent.event_hash == event_hash,
        )
    )
    if exists:
        return

    from app.services.lot_baseline import load_baseline_index, lot_valuation

    valuation = lot_valuation(lot, load_baseline_index(db))
    start_price_per_sotka, start_price_per_sqm = derived_prices(lot.start_price, lot.area_sqm)
    if settings.telegram_alert_skip_low_signal and _is_low_signal_alert(lot, valuation, start_price_per_sotka):
        return

    min_disc = settings.telegram_alert_min_discount_to_baseline
    if min_disc is not None:
        if valuation.discount_to_baseline is None:
            if settings.telegram_alert_require_baseline_for_discount:
                return
        elif valuation.discount_to_baseline < min_disc:
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

    t_url = torgi_public_url(lot, notice_payload)
    t_json = torgi_notice_json_link_when_distinct(lot, notice_payload)
    nspd_u = nspd_lot_map_url(lot)
    app_u = app_public_lot_url(lot.id)
    dom_map = domclick_land_map_url(lot)
    dom = domclick_land_search_url(lot)
    dom_cad = domclick_land_search_url_cadastral_only(lot)
    avi = avito_search_url(lot)
    avi_cad = avito_search_url_cadastral_only(lot)
    cian = cian_land_search_url(lot)
    cian_cad = cian_land_search_url_cadastral_only(lot)
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
    if valuation.valuation_reason and valuation.valuation_reason not in verdict_reasons:
        lines.append(f"Пояснение baseline: {_esc_html_text(valuation.valuation_reason)}")
    if lot.address:
        lines.append(f"Адрес: {_esc_html_text(lot.address)}")
    lines.append("")
    lines.append("Ссылки:")
    link_parts: list[str] = []
    seen_urls: set[str] = set()
    _append_unique_link(link_parts, seen_urls, app_u, "Монитор")
    torgi_primary_label = "ГИС Торги (страница)" if torgi_notice_html_url(lot, notice_payload) else "ГИС Торги"
    _append_unique_link(link_parts, seen_urls, t_url, torgi_primary_label)
    _append_unique_link(link_parts, seen_urls, nspd_u, "НСПД карта")
    _append_unique_link(link_parts, seen_urls, dom_map, "Домклик (карта района)")
    if settings.include_marketplace_search_urls:
        if lot.cadastral_number:
            _append_unique_link(link_parts, seen_urls, dom_cad, "Домклик (поиск, кадастр)")
            _append_unique_link(link_parts, seen_urls, avi_cad, "Авито (поиск, кадастр)")
            _append_unique_link(link_parts, seen_urls, cian_cad, "Циан (поиск, кадастр)")
        else:
            _append_unique_link(link_parts, seen_urls, dom, "Домклик (поиск, адрес)")
            _append_unique_link(link_parts, seen_urls, avi, "Авито (поиск, адрес)")
            _append_unique_link(link_parts, seen_urls, cian, "Циан (поиск, адрес)")
    _append_unique_link(link_parts, seen_urls, t_json, "ГИС Торги (JSON)")
    lines.append(" | ".join(link_parts) if link_parts else "—")
    lines.append("")
    lines.append("<i>Baseline считается по уже загруженным торгам, это ещё не рыночная оценка Циан.</i>")
    if settings.include_marketplace_search_urls:
        lines.append(
            "<i>Площадки: шаблонный поиск по кадастру/адресу; не гарантирует карточку участка.</i>"
        )
    if dom_map:
        lines.append("<i>Домклик-карта открывает район вокруг центроида; это ручной поиск аналогов, не оценка.</i>")
    if nspd_u:
        lines.append("<i>НСПД: если карта не откроет участок автоматически, вставьте кадастровый номер в поиск.</i>")

    message = "\n".join(lines)
    await send_telegram_message(
        settings.telegram_bot_token,
        settings.telegram_chat_id,
        message,
        parse_mode="HTML",
        disable_web_page_preview=settings.telegram_disable_web_page_preview,
    )
    db.add(AlertEvent(lot_id=lot.id, event_type=event_type, event_hash=event_hash))
