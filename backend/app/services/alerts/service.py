import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AlertEvent, Lot
from app.services.alerts.telegram import send_telegram_message


async def notify_lot_event(db: Session, lot: Lot, event_type: str, payload: str) -> None:
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

    message = (
        f"Торги: {event_type}\n"
        f"Лот: {lot.title}\n"
        f"Статус: {lot.status or 'n/a'}\n"
        f"Регион: {lot.region or 'n/a'}\n"
        f"Цена: {lot.current_price or lot.start_price or 'n/a'}\n"
        f"Ссылка: {lot.source_url or 'n/a'}"
    )
    await send_telegram_message(settings.telegram_bot_token, settings.telegram_chat_id, message)
    db.add(AlertEvent(lot_id=lot.id, event_type=event_type, event_hash=event_hash))
