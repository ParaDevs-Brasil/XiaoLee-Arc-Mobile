from __future__ import annotations

from typing import Any, Dict

import httpx


class XClient:
    def __init__(self, bearer_token: str, api_base_url: str = "https://api.x.com"):
        self.bearer_token = bearer_token
        self.api_base_url = api_base_url.rstrip("/")

    @property
    def enabled(self) -> bool:
        return bool(self.bearer_token)

    async def send_dm(self, recipient_id: str | int, text: str) -> Dict[str, Any]:
        if not self.enabled:
            return {"success": False, "error": "X bearer token not configured"}

        url = f"{self.api_base_url}/2/dm_conversations/with/{recipient_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json",
        }
        payload = {"text": text}

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            body = response.json()

        # X responses can vary by API tier; treat successful HTTP as success.
        return {"success": True, "result": body}