"""
Batch 1/N — guard-rails de gasto do loop agêntico (pay_creator_nanopayment / check_budget).

Cobre o que tests/test_agent_engine.py ainda não cobre: valores adversariais de
amount_usdc, corrida de concorrência no mesmo intent_id, e o limite real do escopo do
budget (por execução do agente, não por campanha ao longo do tempo).
"""
import uuid

import pytest

from ai.agents.creator_pay_tools import make_tool_executors
from database.models import Campaign
from database.repository import DatabaseRepository
from server.integrations.arc_client import ArcClient


def _make_campaign(db_session):
    c = Campaign(
        creator_twitter_user_id="test_creator",
        name="Test Campaign Spending",
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


@pytest.mark.asyncio
async def test_pay_creator_rejects_negative_amount(db_session):
    """amount_usdc negativo não pode passar pelo guard de budget e, pior, reduzir
    spent["usdc"] (o que inflaria o orçamento restante para pagamentos seguintes)."""
    repo = DatabaseRepository(db_session)
    arc = ArcClient(sandbox=True)
    campaign = _make_campaign(db_session)
    await db_session.flush()

    executors = make_tool_executors(
        repo=repo, arc_client=arc, campaign_id=campaign.id, budget_usdc=50.0, reward_per_creator=5.0,
    )

    result = await executors["pay_creator_nanopayment"](
        {"intent_id": str(uuid.uuid4()), "to": "@attacker", "amount_usdc": -100.0}, {},
    )

    assert "error" in result
    assert result["error"] == "amount_usdc must be positive"

    budget_after = await executors["check_budget"]({"campaign_id": campaign.id}, {})
    assert budget_after["remaining_usdc"] == 50.0  # não deve ter sido inflado


@pytest.mark.asyncio
async def test_pay_creator_rejects_zero_amount(db_session):
    repo = DatabaseRepository(db_session)
    arc = ArcClient(sandbox=True)
    campaign = _make_campaign(db_session)
    await db_session.flush()

    executors = make_tool_executors(
        repo=repo, arc_client=arc, campaign_id=campaign.id, budget_usdc=50.0, reward_per_creator=5.0,
    )

    result = await executors["pay_creator_nanopayment"](
        {"intent_id": str(uuid.uuid4()), "to": "@c", "amount_usdc": 0.0}, {},
    )

    assert result.get("error") == "amount_usdc must be positive"


@pytest.mark.asyncio
async def test_negative_amount_cannot_be_used_to_fund_a_second_overspend(db_session):
    """Tentativa de exploit: pagar -X pra 'sobrar' orçamento, depois pagar mais que o
    budget original permitiria. Deve falhar no primeiro passo e o segundo pagamento
    continuar limitado ao budget real."""
    repo = DatabaseRepository(db_session)
    arc = ArcClient(sandbox=True)
    campaign = _make_campaign(db_session)
    await db_session.flush()

    executors = make_tool_executors(
        repo=repo, arc_client=arc, campaign_id=campaign.id, budget_usdc=10.0, reward_per_creator=5.0,
    )

    negative_attempt = await executors["pay_creator_nanopayment"](
        {"intent_id": str(uuid.uuid4()), "to": "@attacker", "amount_usdc": -1000.0}, {},
    )
    assert "error" in negative_attempt

    overspend_attempt = await executors["pay_creator_nanopayment"](
        {"intent_id": str(uuid.uuid4()), "to": "@c", "amount_usdc": 11.0}, {},
    )
    assert overspend_attempt.get("error") == "insufficient_budget"


@pytest.mark.asyncio
async def test_rapid_duplicate_calls_with_same_intent_id_only_pay_once(db_session):
    """Duas chamadas em sequência rápida com o mesmo intent_id (ex: retry duplo do
    agente) não podem resultar em spent["usdc"] contado em dobro.

    Nota: AsyncSession do SQLAlchemy não suporta duas operações *de fato* concorrentes
    na mesma sessão (asyncio.gather sobre o mesmo `db_session` estoura
    IllegalStateChangeError) — isso testa a idempotência do lado da aplicação, não
    concorrência real de I/O."""
    repo = DatabaseRepository(db_session)
    arc = ArcClient(sandbox=True)
    campaign = _make_campaign(db_session)
    await db_session.flush()

    executors = make_tool_executors(
        repo=repo, arc_client=arc, campaign_id=campaign.id, budget_usdc=50.0, reward_per_creator=5.0,
    )

    intent_id = str(uuid.uuid4())
    first = await executors["pay_creator_nanopayment"]({"intent_id": intent_id, "to": "@c", "amount_usdc": 5.0}, {})
    second = await executors["pay_creator_nanopayment"]({"intent_id": intent_id, "to": "@c", "amount_usdc": 5.0}, {})

    assert first.get("status") == "submitted"
    assert second.get("duplicate") is True

    budget_after = await executors["check_budget"]({"campaign_id": campaign.id}, {})
    assert budget_after["spent_usdc"] == 5.0  # nunca 10.0 (dobro)


@pytest.mark.asyncio
async def test_pay_creator_with_huge_amount_does_not_bypass_budget(db_session):
    repo = DatabaseRepository(db_session)
    arc = ArcClient(sandbox=True)
    campaign = _make_campaign(db_session)
    await db_session.flush()

    executors = make_tool_executors(
        repo=repo, arc_client=arc, campaign_id=campaign.id, budget_usdc=10.0, reward_per_creator=5.0,
    )

    result = await executors["pay_creator_nanopayment"](
        {"intent_id": str(uuid.uuid4()), "to": "@c", "amount_usdc": 1e18}, {},
    )
    assert result.get("error") == "insufficient_budget"


@pytest.mark.asyncio
async def test_check_budget_with_zero_total_budget_cannot_pay(db_session):
    repo = DatabaseRepository(db_session)
    arc = ArcClient(sandbox=True)
    campaign = _make_campaign(db_session)
    await db_session.flush()

    executors = make_tool_executors(
        repo=repo, arc_client=arc, campaign_id=campaign.id, budget_usdc=0.0, reward_per_creator=5.0,
    )

    budget = await executors["check_budget"]({"campaign_id": campaign.id}, {})
    assert budget["can_pay"] is False
    assert budget["budget_exhausted"] is True


@pytest.mark.asyncio
async def test_separate_agent_runs_do_not_share_in_memory_spend_state(db_session):
    """Caracteriza um gap conhecido (não corrigido nesta sessão, ver docs/LEPTON_SPRINT_PLAN.md):
    spent["usdc"] vive só na closure de make_tool_executors(), criada do zero a cada
    POST /v1/agent/run-campaign. Duas execuções separadas da MESMA campanha, cada uma
    com budget_usdc=10, juntas podem gastar 20 mesmo que a intenção seja um teto único
    de 10 por campanha — porque nenhuma reconcilia o gasto já persistido em payment_intents
    antes de começar. Este teste documenta o comportamento atual; se um dia alguém
    reconciliar o spend no boot do executor, este teste vai falhar e precisa virar
    uma asserção de que o SEGUNDO run já nasce sabendo do gasto do primeiro."""
    repo = DatabaseRepository(db_session)
    arc = ArcClient(sandbox=True)
    campaign = _make_campaign(db_session)
    await db_session.flush()

    run_1 = make_tool_executors(
        repo=repo, arc_client=arc, campaign_id=campaign.id, budget_usdc=10.0, reward_per_creator=5.0,
    )
    paid_1 = await run_1["pay_creator_nanopayment"](
        {"intent_id": str(uuid.uuid4()), "to": "@creator_a", "amount_usdc": 10.0}, {},
    )
    assert paid_1.get("status") == "submitted"

    run_2 = make_tool_executors(
        repo=repo, arc_client=arc, campaign_id=campaign.id, budget_usdc=10.0, reward_per_creator=5.0,
    )
    budget_at_start_of_run_2 = await run_2["check_budget"]({"campaign_id": campaign.id}, {})

    # Gap conhecido: run_2 acha que tem o budget cheio de novo, mesmo já tendo sido
    # gasto $10 nesta campanha pelo run_1.
    assert budget_at_start_of_run_2["remaining_usdc"] == 10.0
