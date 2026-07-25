import pytest

from server.integrations.telegram_adapter import TelegramAdapter
from server.integrations.x_adapter import XAdapter
from server.orchestration.service import OrchestrationService


class FakeGemini:
    async def classify_intent(self, user_text: str, history=None):
        return {"action": "fallback", "confidence": 0.0, "entities": {}}

    async def generate_reply(self, instruction: str, user_text: str, history=None):
        return "Resposta generica de ajuda"


class FakeSolana:
    async def get_balance(self, wallet_address: str):
        return {"wallet": wallet_address, "lamports": 3_000_000_000, "sol": 3.0}

    async def get_swap_quote(self, input_mint: str, output_mint: str, amount_raw: int, slippage_bps: int = 50):
        return {"outAmount": "42000000", "inputMint": input_mint, "outputMint": output_mint, "amount": str(amount_raw)}


@pytest.mark.asyncio
async def test_detect_balance_intent_with_wallet():
    # claude_engine=None força o caminho legado (Gemini/regras) — sem isso, com
    # ANTHROPIC_API_KEY configurada no ambiente, o construtor ligaria o
    # ClaudeAgentEngine de verdade e chamaria a API real da Anthropic aqui.
    service = OrchestrationService(gemini=FakeGemini(), solana=FakeSolana(), claude_engine=None)

    result = await service.execute(
        "consulta saldo da carteira 7vfCXTUXx5X5qM9A2inA1rYv9r8h7xjFh8H6gVn8jYdA",
        "user-1",
    )

    assert result["intent"].action == "check_balance"
    assert "3.000000 SOL" in result["reply_text"]


@pytest.mark.asyncio
async def test_detect_swap_quote_intent():
    # claude_engine=None força o caminho legado (Gemini/regras) — sem isso, com
    # ANTHROPIC_API_KEY configurada no ambiente, o construtor ligaria o
    # ClaudeAgentEngine de verdade e chamaria a API real da Anthropic aqui.
    service = OrchestrationService(gemini=FakeGemini(), solana=FakeSolana(), claude_engine=None)

    result = await service.execute("quero swap 10 usdc para sol", "user-2")

    assert result["intent"].action == "swap_quote"
    assert "Cotacao Jupiter" in result["reply_text"]
    assert result["execution"]["outAmount"] == "42000000"


@pytest.mark.asyncio
async def test_help_fallback_uses_gemini_reply():
    # claude_engine=None força o caminho legado (Gemini/regras) — sem isso, com
    # ANTHROPIC_API_KEY configurada no ambiente, o construtor ligaria o
    # ClaudeAgentEngine de verdade e chamaria a API real da Anthropic aqui.
    service = OrchestrationService(gemini=FakeGemini(), solana=FakeSolana(), claude_engine=None)

    result = await service.execute("me explica o que voce faz", "user-3")

    assert result["intent"].action == "help"
    assert result["reply_text"] == "Resposta generica de ajuda"


def test_telegram_adapter_normalization():
    adapter = TelegramAdapter()
    normalized = adapter.normalize_update(
        {
            "message": {
                "message_id": 9,
                "text": "saldo",
                "from": {"id": 123, "username": "alice"},
                "chat": {"id": 77},
            }
        }
    )

    assert normalized["platform"] == "telegram"
    assert normalized["user_id"] == "123"
    assert normalized["metadata"]["chat_id"] == 77


def test_x_adapter_normalization():
    adapter = XAdapter()
    normalized = adapter.normalize_event(
        {
            "dm": {
                "id": "evt-1",
                "sender_id": "321",
                "sender_handle": "bob",
                "text": "quote 1 usdc",
                "conversation_id": "c-1",
            }
        }
    )

    assert normalized["platform"] == "x"
    assert normalized["user_id"] == "321"
    assert normalized["metadata"]["conversation_id"] == "c-1"
