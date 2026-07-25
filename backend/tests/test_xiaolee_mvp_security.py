import hashlib
import hmac
import importlib
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from server.schemas import IntentResponse, OrchestrationResponse

app_module = importlib.import_module("server.app")


class StubOrchestrator:
    async def execute(self, text: str, user_id: str):
        return {
            "intent": {"action": "help", "confidence": 1.0, "entities": {}},
            "reply_text": "ok",
            "execution": {"status": "ok"},
        }


class StubSolana:
    async def get_swap_quote(self, input_mint: str, output_mint: str, amount_raw: int, slippage_bps: int = 50):
        return {"routePlan": [], "outAmount": "1"}

    async def prepare_swap_transaction(self, quote_response, user_public_key: str):
        return {"swapTransaction": "BASE64_TX", "lastValidBlockHeight": 123}


client = TestClient(app_module.app)


def _set_webhook_secrets():
    object.__setattr__(app_module.settings, "telegram_webhook_secret", "telegram-secret")
    object.__setattr__(app_module.settings, "x_webhook_secret", "x-secret")
    app_module.orchestrator = StubOrchestrator()
    app_module.request_hits.clear()


def test_status_endpoint_returns_running():
    response = client.get("/status")

    assert response.status_code == 200
    assert response.json() == {"status": "running"}


def test_health_endpoint_returns_ok_with_mocked_rpc_health():
    previous_get_health = app_module.solana_client.get_health
    app_module.solana_client.get_health = AsyncMock(return_value={"jsonrpc": "2.0", "result": "ok", "id": 1})
    try:
        response = client.get("/health")
    finally:
        app_module.solana_client.get_health = previous_get_health

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["rpc_health"]["result"] == "ok"


def test_chat_endpoint_returns_compat_shape():
    original_process_inbound = app_module._process_inbound
    app_module._process_inbound = AsyncMock(
        return_value=OrchestrationResponse(
            platform="web",
            user_id="web-user",
            intent=IntentResponse(action="help", confidence=1.0, entities={}),
            reply_text="ok from chat",
            execution={"status": "ok"},
        )
    )
    app_module.request_hits.clear()
    try:
        response = client.post("/chat", json={"message": "oi", "platform": "web", "user_id": "web-user"})
    finally:
        app_module._process_inbound = original_process_inbound

    assert response.status_code == 200
    payload = response.json()
    assert payload["response"][0]["type"] == "text"
    assert payload["response"][0]["content"] == "ok from chat"
    assert payload["intent"]["action"] == "help"
    assert payload["execution"]["status"] == "ok"


def test_telegram_webhook_rejects_missing_secret():
    _set_webhook_secrets()

    response = client.post(
        "/v1/integrations/telegram/webhook",
        json={"message": {"text": "oi", "from": {"id": 1}, "chat": {"id": 9}}},
    )

    assert response.status_code == 401


def test_x_webhook_rejects_invalid_signature():
    _set_webhook_secrets()

    body = b'{"dm":{"sender_id":"1","text":"oi"}}'
    response = client.post(
        "/v1/integrations/x/webhook",
        content=body,
        headers={"Content-Type": "application/json", "x-xiaolee-signature": "invalid"},
    )

    assert response.status_code == 401


def test_x_webhook_accepts_valid_signature():
    _set_webhook_secrets()

    body = b'{"dm":{"sender_id":"1","text":"oi"}}'
    signature = hmac.new(b"x-secret", body, hashlib.sha256).hexdigest()
    original_process_inbound = app_module._process_inbound
    app_module._process_inbound = AsyncMock(
        return_value={
            "platform": "x",
            "user_id": "1",
            "intent": {"action": "help", "confidence": 1.0, "entities": {}},
            "reply_text": "ok",
            "execution": {"status": "ok"},
        }
    )
    try:
        response = client.post(
            "/v1/integrations/x/webhook",
            content=body,
            headers={"Content-Type": "application/json", "x-xiaolee-signature": signature},
        )
    finally:
        app_module._process_inbound = original_process_inbound

    assert response.status_code == 200
    assert response.json()["platform"] == "x"


def test_prepare_swap_returns_unsigned_transaction():
    app_module.solana_client = StubSolana()

    response = client.post(
        "/v1/solana/swap/prepare",
        json={
            "user_public_key": "8Y7NwkjVaY7LHKV8ha2g8xD6LTY64PrtP6Qwzcw7f6Vj",
            "input_mint": "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU",
            "output_mint": "So11111111111111111111111111111111111111112",
            "amount_raw": 1000000,
            "slippage_bps": 50,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["swap_transaction_base64"] == "BASE64_TX"
    assert "Assine" in data["disclaimer"]
