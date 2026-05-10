import asyncio
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def send_telegram_message(
    bot_token: str,
    chat_id: str,
    text: str,
    *,
    parse_mode: str | None = None,
    disable_web_page_preview: bool | None = None,
    max_length: int | None = None,
    max_retries: int | None = None,
    proxy_url: str | None = None,
    timeout_seconds: float | None = None,
) -> None:
    if not bot_token or not chat_id:
        return

    cap = max_length if max_length is not None else settings.telegram_max_message_length
    if cap > 0 and len(text) > cap:
        suffix = "\n…(truncated)"
        text = text[: max(0, cap - len(suffix))] + suffix

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload: dict = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if disable_web_page_preview is not None:
        payload["disable_web_page_preview"] = disable_web_page_preview

    retries = max_retries if max_retries is not None else settings.telegram_send_max_retries
    backoff_s = 1.5
    timeout = timeout_seconds if timeout_seconds is not None else settings.telegram_timeout_seconds
    proxy = proxy_url if proxy_url is not None else settings.telegram_proxy_url
    client_kwargs: dict[str, object] = {"timeout": timeout}
    if proxy.strip():
        client_kwargs["proxy"] = proxy.strip()

    async with httpx.AsyncClient(**client_kwargs) as client:
        for attempt in range(retries + 1):
            response = await client.post(url, json=payload)
            if response.status_code == 429 and attempt < retries:
                retry_after_raw = response.headers.get("retry-after")
                try:
                    wait_s = float(retry_after_raw) if retry_after_raw else backoff_s
                except (TypeError, ValueError):
                    wait_s = backoff_s
                wait_s = max(wait_s, backoff_s)
                logger.warning("Telegram rate limited (429), retry in %ss", wait_s)
                await asyncio.sleep(wait_s)
                continue
            response.raise_for_status()
            return
