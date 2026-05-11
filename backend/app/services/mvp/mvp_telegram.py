"""Telegram notifications for mvp_gis_lots (region 72 + signal threshold)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models_mvp import MvpGisLot, MvpGisTelegramEvent
from app.services.alerts.telegram import send_telegram_message
from app.services.mvp.classify import lot_passes_telegram_signal
from app.services.mvp.link_builder import build_lot_url, build_notice_url, build_nspd_search_url

logger = logging.getLogger(__name__)


def _build_message(lot: MvpGisLot, event_type: str) -> str:
    label = "Новый лот" if event_type == "new_lot" else "Обновление по лоту"
    lines = [
        f"<b>{label}</b>",
        "",
        f"<b>{lot.title or '—'}</b>",
        f"Регион: {lot.region_code or '—'} | Сигнал: {lot.signal_level}",
        f"Кадастр: {lot.cadastral_number or '—'}",
        "",
        "Ссылки:",
    ]
    nn, ln = lot.notice_number, lot.lot_number
    lines.append(f"Извещение: {lot.notice_url or build_notice_url(nn)}")
    lines.append(f"Лот: {lot.lot_url or build_lot_url(nn, ln)}")
    if lot.cadastral_number:
        lines.append(f"НСПД: {lot.nspd_url or build_nspd_search_url(lot.cadastral_number)}")
    if lot.domclick_url:
        lines.append(f"Домклик: {lot.domclick_url}")
    return "\n".join(lines)


async def notify_mvp_lot_if_needed(
    db: Session,
    lot: MvpGisLot,
    *,
    event_type: str,
    content_hash: str,
) -> None:
    if not settings.telegram_alerts_enabled:
        return
    if not (settings.telegram_bot_token or "").strip() or not (settings.telegram_chat_id or "").strip():
        return
    if str(lot.region_code or "").strip() != "72":
        return
    if not lot_passes_telegram_signal(lot.signal_level):
        return

    now = datetime.now(timezone.utc)
    stale_before = now - timedelta(minutes=max(1, settings.telegram_pending_stale_minutes))

    row = db.scalar(
        select(MvpGisTelegramEvent).where(
            MvpGisTelegramEvent.lot_id == lot.id,
            MvpGisTelegramEvent.event_type == event_type,
            MvpGisTelegramEvent.content_hash == content_hash,
        )
    )

    if row is not None and row.status == "sent":
        return
    if (
        row is not None
        and row.status == "pending"
        and row.created_at
        and row.created_at >= stale_before
    ):
        return

    if row is None:
        row = MvpGisTelegramEvent(
            lot_id=lot.id,
            event_type=event_type,
            content_hash=content_hash,
            status="pending",
            created_at=now,
        )
        db.add(row)
    else:
        row.status = "pending"
        row.error_text = None
    db.flush()

    message = _build_message(lot, event_type)
    row.message_text = message

    try:
        mid = await send_telegram_message(
            settings.telegram_bot_token,
            settings.telegram_chat_id,
            message,
            parse_mode="HTML",
            disable_web_page_preview=settings.telegram_disable_web_page_preview,
        )
        row.status = "sent"
        row.sent_at = datetime.now(timezone.utc)
        row.telegram_message_id = mid
        row.error_text = None
    except Exception as exc:  # noqa: BLE001
        logger.warning("MVP Telegram send failed lot_id=%s: %s", lot.id, exc, exc_info=True)
        row.status = "failed"
        row.error_text = str(exc)[:4000]
    db.flush()
