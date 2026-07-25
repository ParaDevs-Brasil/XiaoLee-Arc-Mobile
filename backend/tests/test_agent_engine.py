"""
Testes do motor agêntico do sprint Lepton (Arc/Circle).

Testa:
  - PaymentIntent model (banco de dados)
  - ArcClient em modo sandbox
  - ClaudeAgentEngine: conversão de tools e estrutura de resultado
  - creator_pay_tools: formato das 4 tools e lógica dos executores
  - DatabaseRepository: métodos de payment intent
"""

import asyncio
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Campaign, CampaignParticipant, PaymentIntent, User
from database.repository import DatabaseRepository
from server.integrations.arc_client import ArcClient
from ai.agents.creator_pay_tools import (
    CREATOR_PAY_TOOLS,
    DISCOVER_CREATORS_TOOL,
    EVALUATE_CREATOR_TOOL,
    CHECK_BUDGET_TOOL,
    PAY_CREATOR_TOOL,
    make_tool_executors,
)
from claude_agent import ClaudeAgentEngine, AgentResult, AgentStep


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_campaign(db_session):
    """Cria uma campanha de teste no banco."""
    c = Campaign(
        creator_twitter_user_id="test_creator",
        name="Test Campaign",
        description="desc",
        campaign_type="social",
        reward_token="USDC",
        reward_per_participant=5.0,
        max_participants=100,
        reward_pool=500.0,
        status="active",
    )
    db_session.add(c)
    return c


def _make_user_and_participant(db_session, campaign_id: int, handle: str, has_followed=True):
    u = User(twitter_handle=handle, twitter_user_id=f"uid_{handle}")
    db_session.add(u)
    return u


# ===========================================================================
# 1. PaymentIntent — modelo de banco
# ===========================================================================


class TestPaymentIntentModel:
    """
    Imagina que o PaymentIntent é um bilhetinho que a XiaoLee guarda
    ANTES de enviar dinheiro. Assim, se a internet cair, ela sabe que
    já estava tentando pagar e não paga de novo.
    """

    @pytest.mark.asyncio
    async def test_create_payment_intent(self, db_session: AsyncSession):
        """Deve criar um PaymentIntent com status 'pending'."""
        campaign = _make_campaign(db_session)
        await db_session.flush()

        intent = PaymentIntent(
            intent_id=str(uuid.uuid4()),
            campaign_id=campaign.id,
            creator_id="@alice",
            amount_usdc=5.0,
            status="pending",
        )
        db_session.add(intent)
        await db_session.commit()
        await db_session.refresh(intent)

        assert intent.id is not None
        assert intent.status == "pending"
        assert float(intent.amount_usdc) == 5.0

    @pytest.mark.asyncio
    async def test_intent_id_must_be_unique(self, db_session: AsyncSession):
        """Dois pagamentos com o mesmo intent_id devem ser barrados pelo banco."""
        campaign = _make_campaign(db_session)
        await db_session.flush()

        same_id = str(uuid.uuid4())
        db_session.add(PaymentIntent(
            intent_id=same_id, campaign_id=campaign.id,
            creator_id="@alice", amount_usdc=5.0,
        ))
        await db_session.commit()

        db_session.add(PaymentIntent(
            intent_id=same_id, campaign_id=campaign.id,
            creator_id="@bob", amount_usdc=5.0,
        ))
        with pytest.raises(Exception):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_update_status_to_submitted(self, db_session: AsyncSession):
        """Depois de pagar, o status deve virar 'submitted' e ter o tx_hash."""
        campaign = _make_campaign(db_session)
        await db_session.flush()

        intent_id = str(uuid.uuid4())
        intent = PaymentIntent(
            intent_id=intent_id, campaign_id=campaign.id,
            creator_id="@carol", amount_usdc=3.0,
        )
        db_session.add(intent)
        await db_session.commit()

        # Simula que o pagamento foi enviado
        intent.status = "submitted"
        intent.arc_tx_hash = "sandbox_tx_abc123"
        intent.executed_at = datetime.now(timezone.utc)
        await db_session.commit()
        await db_session.refresh(intent)

        assert intent.status == "submitted"
        assert intent.arc_tx_hash == "sandbox_tx_abc123"
        assert intent.executed_at is not None


# ===========================================================================
# 2. ArcClient — carteira USDC (modo sandbox)
# ===========================================================================


class TestArcClient:
    """
    O ArcClient é como um caixa eletrônico do Circle.
    No modo sandbox (ARC_SANDBOX=true) ele faz de conta que enviou
    o dinheiro — perfeito para testes sem usar USDC de verdade.
    """

    @pytest.mark.asyncio
    async def test_sandbox_send_returns_fake_tx(self):
        """Em sandbox, send_usdc deve retornar um hash inventado."""
        arc = ArcClient(sandbox=True)
        intent_id = str(uuid.uuid4())

        tx_hash = await arc.send_usdc(
            to_address="0xabc123",
            amount_usdc=5.0,
            idempotency_key=intent_id,
        )

        # O hash inventado começa com 'sandbox_tx_'
        assert tx_hash.startswith("sandbox_tx_")
        assert intent_id[:16] in tx_hash

    @pytest.mark.asyncio
    async def test_sandbox_balance_returns_1000(self):
        """Em sandbox, o saldo é sempre 1000 USDC (fake para demo)."""
        arc = ArcClient(sandbox=True)
        balance = await arc.get_balance("wallet_fake_id")
        assert balance == 1000.0

    @pytest.mark.asyncio
    async def test_sandbox_transfer_status(self):
        """Em sandbox, qualquer transfer está como 'CONFIRMED' (vocabulário real da Circle)."""
        arc = ArcClient(sandbox=True)
        status = await arc.get_transfer_status("any_transfer_id")
        assert status["status"] == "CONFIRMED"

    def test_sandbox_flag_true_by_default_with_env(self, monkeypatch):
        """ARC_SANDBOX=true deve ativar o modo de teste."""
        monkeypatch.setenv("ARC_SANDBOX", "true")
        arc = ArcClient(sandbox=True)
        assert arc.sandbox is True

    def test_live_mode_requires_api_key(self, monkeypatch):
        """Sem CIRCLE_API_KEY em modo live, deve dar erro ao tentar pagar.

        O construtor do ArcClient faz `api_key or os.getenv("CIRCLE_API_KEY", "")` —
        sem isolar a env real, api_key="" cairia pro CIRCLE_API_KEY de verdade do .env
        e este teste dispararia uma chamada HTTP real pra api.circle.com (live).
        """
        monkeypatch.delenv("CIRCLE_API_KEY", raising=False)
        arc = ArcClient(api_key="", sandbox=False)
        with pytest.raises(RuntimeError, match="CIRCLE_API_KEY or CIRCLE_WALLET_ID not configured"):
            asyncio.run(arc.send_usdc("0xabc", 1.0, "intent123"))


# ===========================================================================
# 3. ClaudeAgentEngine — o motor do robô
# ===========================================================================


class TestClaudeAgentEngine:
    """
    O ClaudeAgentEngine é o cérebro do robô. Ele lê as tools no formato
    OpenAI (como uma lista de instruções) e converte para o formato que
    o Claude da Anthropic entende.
    """

    def test_convert_openai_tools_to_anthropic_format(self):
        """Tools no formato OpenAI devem ser convertidas para formato Anthropic."""
        openai_tool = {
            "type": "function",
            "function": {
                "name": "discover_creators",
                "description": "Find creators",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "campaign_id": {"type": "integer"},
                    },
                    "required": ["campaign_id"],
                },
            },
        }

        converted = ClaudeAgentEngine._convert_tools([openai_tool])

        assert len(converted) == 1
        tool = converted[0]
        # Formato Anthropic usa 'name', 'description', 'input_schema'
        assert tool["name"] == "discover_creators"
        assert tool["description"] == "Find creators"
        assert "input_schema" in tool
        assert tool["input_schema"]["type"] == "object"

    def test_convert_all_four_creator_pay_tools(self):
        """Todas as 4 tools devem converter sem erro."""
        converted = ClaudeAgentEngine._convert_tools(CREATOR_PAY_TOOLS)
        names = [t["name"] for t in converted]

        assert len(converted) == 4
        assert "discover_creators" in names
        assert "evaluate_creator" in names
        assert "check_budget" in names
        assert "pay_creator_nanopayment" in names

    def test_agent_result_to_dict(self):
        """AgentResult deve serializar para dict com os campos certos."""
        result = AgentResult(
            run_id="test-run-1",
            status="completed",
            steps=[
                AgentStep(step=1, tool_name="check_budget",
                          tool_input={}, tool_result={"remaining_usdc": 50.0})
            ],
            payments=[{"creator_id": "@alice", "amount_usdc": 5.0}],
            final_message="Done!",
            total_paid_usdc=5.0,
        )

        d = result.to_dict()
        assert d["run_id"] == "test-run-1"
        assert d["status"] == "completed"
        assert d["total_paid_usdc"] == 5.0
        assert len(d["steps"]) == 1
        assert d["steps"][0]["tool_name"] == "check_budget"
        assert len(d["payments"]) == 1


# ===========================================================================
# 4. Creator Pay Tools — as 4 ferramentas do robô
# ===========================================================================


class TestCreatorPayToolsFormat:
    """
    As 4 tools são como as 4 habilidades do robô de campanha:
    buscar, avaliar, checar saldo e pagar.
    """

    def test_discover_creators_tool_has_required_fields(self):
        t = DISCOVER_CREATORS_TOOL["function"]
        assert t["name"] == "discover_creators"
        assert "campaign_id" in t["parameters"]["required"]

    def test_evaluate_creator_tool_has_required_fields(self):
        t = EVALUATE_CREATOR_TOOL["function"]
        assert t["name"] == "evaluate_creator"
        assert "creator_id" in t["parameters"]["required"]
        assert "campaign_id" in t["parameters"]["required"]

    def test_check_budget_tool_has_required_fields(self):
        t = CHECK_BUDGET_TOOL["function"]
        assert t["name"] == "check_budget"
        assert "campaign_id" in t["parameters"]["required"]

    def test_pay_creator_tool_has_frozen_signature(self):
        """
        Contrato congelado: intent_id + to + amount_usdc.
        NUNCA mudar isso sem avisar o time.
        """
        t = PAY_CREATOR_TOOL["function"]
        assert t["name"] == "pay_creator_nanopayment"
        required = t["parameters"]["required"]
        assert "intent_id" in required
        assert "to" in required
        assert "amount_usdc" in required

    def test_all_tools_are_openai_format(self):
        """Todas as tools devem ter type='function' e uma chave 'function'."""
        for tool in CREATOR_PAY_TOOLS:
            assert tool["type"] == "function"
            assert "function" in tool
            assert "name" in tool["function"]
            assert "parameters" in tool["function"]


# ===========================================================================
# 5. Executores das tools — lógica de negócio
# ===========================================================================


class TestToolExecutors:
    """
    Os executores são os 'músculos' das tools.
    A tool diz 'quero pagar', o executor realmente faz o trabalho
    — sem expor a wallet ou o budget pro modelo do Claude.
    """

    @pytest.mark.asyncio
    async def test_check_budget_returns_correct_remaining(self, db_session: AsyncSession):
        """check_budget deve retornar quanto sobra do budget."""
        repo = DatabaseRepository(db_session)
        arc = ArcClient(sandbox=True)

        campaign = _make_campaign(db_session)
        await db_session.flush()

        executors = make_tool_executors(
            repo=repo, arc_client=arc,
            campaign_id=campaign.id, budget_usdc=50.0, reward_per_creator=5.0,
        )

        result = await executors["check_budget"]({"campaign_id": campaign.id}, {})

        assert result["total_budget_usdc"] == 50.0
        assert result["spent_usdc"] == 0.0
        assert result["remaining_usdc"] == 50.0
        assert result["can_pay"] is True
        assert result["reward_per_creator_usdc"] == 5.0

    @pytest.mark.asyncio
    async def test_check_budget_exhausted_when_no_funds(self, db_session: AsyncSession):
        """Com budget zero, can_pay deve ser False e budget_exhausted True."""
        repo = DatabaseRepository(db_session)
        arc = ArcClient(sandbox=True)

        campaign = _make_campaign(db_session)
        await db_session.flush()

        # Budget zero
        executors = make_tool_executors(
            repo=repo, arc_client=arc,
            campaign_id=campaign.id, budget_usdc=0.0, reward_per_creator=5.0,
        )

        result = await executors["check_budget"]({"campaign_id": campaign.id}, {})

        assert result["can_pay"] is False
        assert result.get("budget_exhausted") is True

    @pytest.mark.asyncio
    async def test_evaluate_creator_not_enrolled(self, db_session: AsyncSession):
        """Creator não inscrito na campanha deve ter eligible=False."""
        repo = DatabaseRepository(db_session)
        arc = ArcClient(sandbox=True)
        campaign = _make_campaign(db_session)
        await db_session.flush()

        executors = make_tool_executors(
            repo=repo, arc_client=arc,
            campaign_id=campaign.id, budget_usdc=50.0,
        )

        result = await executors["evaluate_creator"](
            {"creator_id": "@nao_existe", "campaign_id": campaign.id}, {}
        )

        assert result["eligible"] is False
        assert "not enrolled" in result["reason"]

    @pytest.mark.asyncio
    async def test_pay_creator_writes_intent_before_executing(self, db_session: AsyncSession):
        """
        O pagamento DEVE escrever o intent no banco ANTES de chamar o Arc.
        Isso é o anti-replay: se cair a conexão, não paga duas vezes.
        """
        repo = DatabaseRepository(db_session)
        arc = ArcClient(sandbox=True)
        campaign = _make_campaign(db_session)
        await db_session.flush()

        executors = make_tool_executors(
            repo=repo, arc_client=arc,
            campaign_id=campaign.id, budget_usdc=50.0, reward_per_creator=5.0,
        )

        intent_id = str(uuid.uuid4())
        result = await executors["pay_creator_nanopayment"](
            {"intent_id": intent_id, "to": "@alice", "amount_usdc": 5.0}, {}
        )

        # Deve ter retornado o tx_hash do sandbox
        assert "tx" in result
        assert result["tx"].startswith("sandbox_tx_")
        assert result["status"] == "submitted"

        # O intent deve estar no banco com status=submitted
        intent = await repo.get_payment_intent(intent_id)
        assert intent is not None
        assert intent.status == "submitted"
        assert intent.arc_tx_hash is not None

    @pytest.mark.asyncio
    async def test_pay_creator_with_0x_registered_wallet_skips_circle_lookup(self, db_session: AsyncSession):
        """
        REGRESSÃO (achado em produção, 6 jul): creator registrado via
        POST /v1/creator/register com endereço 0x (Connect Wallet) direto — não um
        Circle Wallet ID (UUID). O pay tool NÃO pode chamar arc_client.get_wallet_info()
        nesse caso: a Circle API espera um UUID no path e retorna 400 (código 156009,
        "Fail to parse id as UUID in url"), derrubando TODO pagamento a creators que
        conectaram wallet direto em vez do fluxo legado App Kit. O destino 0x deve ser
        usado tal como está.
        """
        from unittest.mock import AsyncMock
        from server.metrics import register_creator, clear_metrics

        clear_metrics()
        register_creator("carol", "0xAbC1230000000000000000000000000000000456")

        repo = DatabaseRepository(db_session)
        arc = ArcClient(sandbox=True)
        arc.get_wallet_info = AsyncMock(side_effect=AssertionError(
            "get_wallet_info NÃO deveria ser chamado para wallet já em formato 0x"
        ))
        campaign = _make_campaign(db_session)
        await db_session.flush()

        executors = make_tool_executors(
            repo=repo, arc_client=arc,
            campaign_id=campaign.id, budget_usdc=50.0, reward_per_creator=5.0,
        )

        result = await executors["pay_creator_nanopayment"](
            {"intent_id": str(uuid.uuid4()), "to": "@carol", "amount_usdc": 5.0}, {}
        )

        assert "error" not in result, result
        assert result["status"] == "submitted"
        arc.get_wallet_info.assert_not_called()
        clear_metrics()

    @pytest.mark.asyncio
    async def test_pay_creator_idempotent_duplicate(self, db_session: AsyncSession):
        """
        Pagar duas vezes com o mesmo intent_id deve retornar o mesmo resultado
        sem pagar de novo. (Anti-replay)
        """
        repo = DatabaseRepository(db_session)
        arc = ArcClient(sandbox=True)
        campaign = _make_campaign(db_session)
        await db_session.flush()

        executors = make_tool_executors(
            repo=repo, arc_client=arc,
            campaign_id=campaign.id, budget_usdc=100.0, reward_per_creator=5.0,
        )

        intent_id = str(uuid.uuid4())
        inputs = {"intent_id": intent_id, "to": "@bob", "amount_usdc": 5.0}

        result1 = await executors["pay_creator_nanopayment"](inputs, {})
        result2 = await executors["pay_creator_nanopayment"](inputs, {})

        assert result1["tx"] == result2["tx"]
        assert result2.get("duplicate") is True

    @pytest.mark.asyncio
    async def test_pay_creator_blocks_when_budget_exceeded(self, db_session: AsyncSession):
        """
        Tentar pagar mais do que o budget disponível deve retornar erro
        sem criar nenhum intent no banco.
        """
        repo = DatabaseRepository(db_session)
        arc = ArcClient(sandbox=True)
        campaign = _make_campaign(db_session)
        await db_session.flush()

        # Budget de só 1 USDC, mas tentando pagar 5
        executors = make_tool_executors(
            repo=repo, arc_client=arc,
            campaign_id=campaign.id, budget_usdc=1.0, reward_per_creator=5.0,
        )

        intent_id = str(uuid.uuid4())
        result = await executors["pay_creator_nanopayment"](
            {"intent_id": intent_id, "to": "@charlie", "amount_usdc": 5.0}, {}
        )

        assert "error" in result
        assert result["error"] == "insufficient_budget"
        assert result.get("budget_exhausted") is True

        # Nenhum intent deve ter sido criado
        intent = await repo.get_payment_intent(intent_id)
        assert intent is None


# ===========================================================================
# 6. DatabaseRepository — métodos de payment intent
# ===========================================================================


class TestRepositoryPaymentIntents:
    """
    O repositório é o assistente que vai e volta ao banco de dados.
    Aqui testamos se ele busca, cria e atualiza os intents corretamente.
    """

    @pytest.mark.asyncio
    async def test_create_and_get_payment_intent(self, db_session: AsyncSession):
        repo = DatabaseRepository(db_session)
        campaign = _make_campaign(db_session)
        await db_session.flush()

        intent_id = str(uuid.uuid4())
        await repo.create_payment_intent(intent_id, campaign.id, "@diana", 7.5)

        fetched = await repo.get_payment_intent(intent_id)
        assert fetched is not None
        assert fetched.intent_id == intent_id
        assert fetched.creator_id == "@diana"
        assert float(fetched.amount_usdc) == 7.5
        assert fetched.status == "pending"

    @pytest.mark.asyncio
    async def test_update_payment_intent_status(self, db_session: AsyncSession):
        repo = DatabaseRepository(db_session)
        campaign = _make_campaign(db_session)
        await db_session.flush()

        intent_id = str(uuid.uuid4())
        await repo.create_payment_intent(intent_id, campaign.id, "@eve", 3.0)
        await repo.update_payment_intent(intent_id, status="submitted", tx_hash="tx_999")

        fetched = await repo.get_payment_intent(intent_id)
        assert fetched.status == "submitted"
        assert fetched.arc_tx_hash == "tx_999"
        assert fetched.executed_at is not None

    @pytest.mark.asyncio
    async def test_get_payment_intent_by_creator(self, db_session: AsyncSession):
        """Deve encontrar um intent submetido para um creator específico."""
        repo = DatabaseRepository(db_session)
        campaign = _make_campaign(db_session)
        await db_session.flush()

        intent_id = str(uuid.uuid4())
        await repo.create_payment_intent(intent_id, campaign.id, "@frank", 5.0)
        await repo.update_payment_intent(intent_id, status="submitted", tx_hash="tx_frank")

        found = await repo.get_payment_intent_by_creator(campaign.id, "@frank")
        assert found is not None
        assert found.creator_id == "@frank"

    @pytest.mark.asyncio
    async def test_get_payment_intent_by_creator_not_found_for_pending(self, db_session: AsyncSession):
        """Não deve retornar intent com status 'pending' — apenas submitted/confirmed."""
        repo = DatabaseRepository(db_session)
        campaign = _make_campaign(db_session)
        await db_session.flush()

        intent_id = str(uuid.uuid4())
        await repo.create_payment_intent(intent_id, campaign.id, "@grace", 5.0)
        # Status permanece 'pending' — NÃO atualiza

        found = await repo.get_payment_intent_by_creator(campaign.id, "@grace")
        assert found is None  # Pending não conta como pago
