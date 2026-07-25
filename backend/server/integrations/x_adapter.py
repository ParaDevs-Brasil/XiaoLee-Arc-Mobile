from __future__ import annotations

from typing import Any, Dict


class XAdapter:
    def normalize_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        dm = event.get("dm", {})
        return {
            "platform": "x",
            "user_id": str(dm.get("sender_id", "unknown")),
            "username": dm.get("sender_handle"),
            "text": dm.get("text", ""),
            "metadata": {
                "conversation_id": dm.get("conversation_id"),
                "event_id": dm.get("id"),
            },
        }
