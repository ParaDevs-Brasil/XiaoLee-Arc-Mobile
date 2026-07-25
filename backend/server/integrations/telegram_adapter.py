from __future__ import annotations

from typing import Any, Dict


class TelegramAdapter:
    def normalize_update(self, update: Dict[str, Any]) -> Dict[str, Any]:
        message = update.get("message", {})
        from_user = message.get("from", {})
        chat = message.get("chat", {})

        return {
            "platform": "telegram",
            "user_id": str(from_user.get("id", "unknown")),
            "username": from_user.get("username"),
            "text": message.get("text", ""),
            "metadata": {
                "chat_id": chat.get("id"),
                "message_id": message.get("message_id"),
            },
        }
