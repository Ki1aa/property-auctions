import httpx


async def send_telegram_message(
    bot_token: str,
    chat_id: str,
    text: str,
    *,
    parse_mode: str | None = None,
    disable_web_page_preview: bool | None = None,
) -> None:
    if not bot_token or not chat_id:
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload: dict = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if disable_web_page_preview is not None:
        payload["disable_web_page_preview"] = disable_web_page_preview
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
