import hashlib
import html
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AlertEvent, Lot, OpenDataNotice
from app.services.alerts.telegram import send_telegram_message
from app.services.external_lot_links import (
    app_public_lot_url,
    avito_search_url,
    domclick_land_search_url,
    pkk_map_url,
    torgi_public_url,
)


def _esc_html_text(value: object) -> str:
    return html.escape(str(value), quote=False)


def _esc_html_attr(value: str) -> str:
    return html.escape(value, quote=True)


async def notify_lot_event(db: Session, lot: Lot, event_type: str, payload: str) -> None:
    if settings.telegram_alert_only_izhs and not lot.is_izhs_candidate:
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

    notice_payload: dict[str, Any] | None = None
    if lot.opendata_notice_id is not None:
        notice = db.scalar(select(OpenDataNotice).where(OpenDataNotice.id == lot.opendata_notice_id))
        if notice is not None and isinstance(notice.payload, dict):
            notice_payload = notice.payload

    t_url = torgi_public_url(lot, notice_payload)
    pkk = pkk_map_url(lot.cadastral_number)
    app_u = app_public_lot_url(lot.id)
    dom = domclick_land_search_url(lot)
    avi = avito_search_url(lot)

    lines: list[str] = [
        f"<b>{_esc_html_text(event_type)}</b>",
        "",
        f"<b>{_esc_html_text(lot.title)}</b>",
        f"Статус: {_esc_html_text(lot.status or '—')}",
        f"Регион: {_esc_html_text(lot.region or '—')}",
        f"Кадастр: {_esc_html_text(lot.cadastral_number or '—')}",
        f"Площадь (м²): {_esc_html_text(lot.area_sqm if lot.area_sqm is not None else '—')}",
        f"Адрес: {_esc_html_text(lot.address or '—')}",
        f"Стартовая цена: {_esc_html_text(lot.start_price if lot.start_price is not None else '—')}",
        f"Текущая цена: {_esc_html_text(lot.current_price if lot.current_price is not None else '—')}",
    ]
    if valuation.baseline_price_per_sotka is not None:
        lines.append(f"Baseline ₽/сотка: {_esc_html_text(valuation.baseline_price_per_sotka)}")
    if valuation.discount_to_baseline is not None:
        lines.append(f"Дисконт к baseline: {_esc_html_text(round(valuation.discount_to_baseline * 100, 2))}%")
    lines.append(f"Дата начала: {_esc_html_text(lot.start_date.isoformat() if lot.start_date else '—')}")
    lines.append(f"Дата окончания: {_esc_html_text(lot.end_date.isoformat() if lot.end_date else '—')}")
    lines.append("")
    lines.append("Ссылки:")
    link_parts: list[str] = []
    if app_u:
        link_parts.append(f'<a href="{_esc_html_attr(app_u)}">Монитор</a>')
    if t_url:
        link_parts.append(f'<a href="{_esc_html_attr(t_url)}">ГИС Торги</a>')
    if pkk:
        link_parts.append(f'<a href="{_esc_html_attr(pkk)}">ПКК</a>')
    if dom:
        link_parts.append(f'<a href="{_esc_html_attr(dom)}">Домклик (поиск)</a>')
    if avi:
        link_parts.append(f'<a href="{_esc_html_attr(avi)}">Авито (поиск)</a>')
    lines.append(" | ".join(link_parts) if link_parts else "—")

    message = "\n".join(lines)
    await send_telegram_message(
        settings.telegram_bot_token,
        settings.telegram_chat_id,
        message,
        parse_mode="HTML",
    )
    db.add(AlertEvent(lot_id=lot.id, event_type=event_type, event_hash=event_hash))
