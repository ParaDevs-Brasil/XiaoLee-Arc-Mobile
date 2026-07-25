from __future__ import annotations

from typing import Any, Dict

import httpx


class TelegramClient:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token

    @property
    def enabled(self) -> bool:
        return bool(self.bot_token)

    async def send_message(self, chat_id: str | int, text: str) -> Dict[str, Any]:
        if not self.enabled:
            return {"success": False, "error": "Telegram bot token not configured"}

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": str(chat_id),
            "text": text,
            "disable_web_page_preview": True,
        }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            body = response.json()

        if body.get("ok"):
            return {"success": True, "result": body.get("result", {})}

        return {"success": False, "error": body}