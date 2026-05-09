"""Send a one-off test message using TELEGRAM_* from .env (smoke test for production setup)."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Allow `python scripts/send_telegram_test.py` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.services.alerts.telegram import send_telegram_message


async def main() -> None:
    parser = argparse.ArgumentParser(description="Send a test Telegram message.")
    parser.add_argument(
        "--text",
        default="GIS Torgi Monitor: тест доставки.",
        help="Message body (plain text)",
    )
    args = parser.parse_args()
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env", file=sys.stderr)
        raise SystemExit(1)
    await send_telegram_message(
        settings.telegram_bot_token,
        settings.telegram_chat_id,
        args.text,
        disable_web_page_preview=settings.telegram_disable_web_page_preview,
    )
    print("Sent.")


if __name__ == "__main__":
    asyncio.run(main())
