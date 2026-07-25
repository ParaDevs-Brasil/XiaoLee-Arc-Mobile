"""
test_cctp_tools.py — payout_cross_chain_nanopayment: intent durável, guards de
orçamento/valor, idempotência, orçamento compartilhado com pay_creator_nanopayment,
E2E sandbox completo (burn no Arc + mint no destino).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ai.agents.cctp_tools import make_cctp_tool_executors
from ai.agents.creator_pay_tools import make_tool_executors
from database.models import Campaign
from database.repository import DatabaseRepository
from server.integrations.arc_client import ArcClient
from server.integrations.cctp_client import CCTPClient
from server.integrations.solana_cctp import SolanaCCTPClient
from server.integrations.stellar_cctp import StellarCCTPClient


def _make_campaign(db_session):
    c = Campaign(
        creator_twitter_user_id="test_creator",
        name=f"CCTP Test Campaign {uuid.uuid4()}",
        description="desc",
        reward_token="USDC",
        reward_per_participant=5.0,
        max_participants=10,
        reward_pool=100.0,
    )
    db_session.add(c)
    return c


def _make_executors(repo, campaign_id, budget_usdc=50.0, spent_tracker=None, abi_version=2):
    # abi_version=2 espelha a produção (agent_routes.py) — Arc é V2-only e o payout
    # Stellar emite hook_data, que o guard do CCTPClient rejeita na ABI V1.
    return make_cctp_tool_executors(
        repo=repo,
        arc_cctp_client=CCTPClient(sandbox=True, abi_version=abi_version),
        solana_cctp_client=SolanaCCTPClient(sandbox=True),
        stellar_cctp_client=StellarCCTPClient(sandbox=True),
        campaign_id=campaign_id,
        budget_usdc=budget_usdc,
        spent_tracker=spent_tracker,
    )


class TestPayoutCrossChainHappyPath:
    @pytest.mark.asyncio
    async def test_solana_payout_creates_transfer_and_returns_tx(self, db_session: AsyncSession):
        repo = DatabaseRepository(db_session)
        campaign = _make_campaign(db_session)
        await db_session.flush()

        executors = _make_executors(repo, campaign.id)
        intent_id = str(uuid.uuid4())
        solana_addr = "11111111111111111111111111111111"

        result = await executors["payout_cross_chain_nanopayment"](
            {"intent_id": intent_id, "to": solana_addr, "amount_usdc": 5.0, "destination_chain": "solana"},
            {},
        )

        assert "error" not in result
        assert result["status"] == "received"
        assert result["tx"]
        assert result["receipt_pqc"]

        transfer = await repo.get_cctp_transfer(intent_id)
        assert transfer is not None
        assert transfer.status == "received"
        assert transfer.direction == "outflow"
        assert transfer.dest_domain == 5  # Solana

    @pytest.mark.asyncio
    async def test_stellar_payout_creates_transfer_and_returns_tx(self, db_session: AsyncSession):
        repo = DatabaseRepository(db_session)
        campaign = _make_campaign(db_session)
        await db_session.flush()

        executors = _make_executors(repo, campaign.id)
        intent_id = str(uuid.uuid4())

        result = await executors["payout_cross_chain_nanopayment"](
            {
                "intent_id": intent_id,
                "to": "GAAXKLIMFWX7XLKVXGUVJI7X533OOZH2YS2RLMQVY3TP5QLXRRWXHDI5",
                "amount_usdc": 3.0,
                "destination_chain": "stellar",
            },
            {},
        )

        assert "error" not in result
        assert result["status"] == "received"

        transfer = await repo.get_cctp_transfer(intent_id)
        assert transfer.dest_domain == 27  # Stellar

    @pytest.mark.asyncio
    async def test_stellar_payout_with_invalid_strkey_fails_before_burn(self, db_session: AsyncSession):
        """Strkey inválido tem que falhar ANTES do burn — depois dele os fundos ficariam
        presos no CctpForwarder sem recovery."""
        repo = DatabaseRepository(db_session)
        campaign = _make_campaign(db_session)
        await db_session.flush()

        executors = _make_executors(repo, campaign.id)
        intent_id = str(uuid.uuid4())
        result = await executors["payout_cross_chain_nanopayment"](
            {"intent_id": intent_id, "to": "GNOT_A_VALID_STRKEY", "amount_usdc": 1.0, "destination_chain": "stellar"},
            {},
        )
        assert "error" in result
        transfer = await repo.get_cctp_transfer(intent_id)
        assert transfer.status == "failed"

    @pytest.mark.asyncio
    async def test_stellar_payout_on_v1_abi_client_is_rejected(self, db_session: AsyncSession):
        """hook_data só existe na ABI V2 — cliente V1 (config errada) deve falhar com
        mensagem clara em vez de queimar sem hook (fundos presos)."""
        repo = DatabaseRepository(db_session)
        campaign = _make_campaign(db_session)
        await db_session.flush()

        executors = _make_executors(repo, campaign.id, abi_version=1)
        result = await executors["payout_cross_chain_nanopayment"](
            {
                "intent_id": str(uuid.uuid4()),
                "to": "GAAXKLIMFWX7XLKVXGUVJI7X533OOZH2YS2RLMQVY3TP5QLXRRWXHDI5",
                "amount_usdc": 1.0,
                "destination_chain": "stellar",
            },
            {},
        )
        assert "error" in result
        assert "abi_version=2" in result["error"]


class TestPayoutCrossChainGuards:
    @pytest.mark.asyncio
    async def test_negative_amount_rejected(self, db_session: AsyncSession):
        repo = DatabaseRepository(db_session)
        campaign = _make_campaign(db_session)
        await db_session.flush()

        executors = _make_executors(repo, campaign.id)
        result = await executors["payout_cross_chain_nanopayment"](
            {"intent_id": str(uuid.uuid4()), "to": "x", "amount_usdc": -1.0, "destination_chain": "solana"},
            {},
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_invalid_destination_chain_rejected(self, db_session: AsyncSession):
        repo = DatabaseRepository(db_session)
        campaign = _make_campaign(db_session)
        await db_session.flush()

        executors = _make_executors(repo, campaign.id)
        result = await executors["payout_cross_chain_nanopayment"](
            {"intent_id": str(uuid.uuid4()), "to": "x", "amount_usdc": 1.0, "destination_chain": "arc"},
            {},
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_amount_exceeding_budget_rejected(self, db_session: AsyncSession):
        repo = DatabaseRepository(db_session)
        campaign = _make_campaign(db_session)
        await db_session.flush()

        executors = _make_executors(repo, campaign.id, budget_usdc=2.0)
        result = await executors["payout_cross_chain_nanopayment"](
            {"intent_id": str(uuid.uuid4()), "to": "x", "amount_usdc": 5.0, "destination_chain": "solana"},
            {},
        )
        assert result.get("error") == "insufficient_budget"
        assert result.get("budget_exhausted") is True

    @pytest.mark.asyncio
    async def test_duplicate_intent_returns_existing_receipt(self, db_session: AsyncSession):
        repo = DatabaseRepository(db_session)
        campaign = _make_campaign(db_session)
        await db_session.flush()

        executors = _make_executors(repo, campaign.id)
        intent_id = str(uuid.uuid4())
        payload = {"intent_id": intent_id, "to": "11111111111111111111111111111111", "amount_usdc": 5.0, "destination_chain": "solana"}

        first = await executors["payout_cross_chain_nanopayment"](payload, {})
        second = await executors["payout_cross_chain_nanopayment"](payload, {})

        assert second.get("duplicate") is True
        assert second["tx"] == first["tx"]


class TestConcurrentBudgetReservation:
    @pytest.mark.asyncio
    async def test_parallel_payouts_cannot_double_spend(self, db_session: AsyncSession):
        """O engine executa tool calls do mesmo turno em paralelo (asyncio.gather) —
        dois payouts concorrentes com orçamento pra UM só não podem ambos passar no
        check. A reserva atômica (débito antes do rail) garante isso."""
        repo = DatabaseRepository(db_session)
        campaign = _make_campaign(db_session)
        await db_session.flush()

        spent_tracker = {"usdc": 0.0}
        executors = _make_executors(repo, campaign.id, budget_usdc=8.0, spent_tracker=spent_tracker)

        import asyncio

        results = await asyncio.gather(
            executors["payout_cross_chain_nanopayment"](
                {"intent_id": str(uuid.uuid4()), "to": "11111111111111111111111111111111",
                 "amount_usdc": 5.0, "destination_chain": "solana"}, {},
            ),
            executors["payout_cross_chain_nanopayment"](
                {"intent_id": str(uuid.uuid4()), "to": "GAAXKLIMFWX7XLKVXGUVJI7X533OOZH2YS2RLMQVY3TP5QLXRRWXHDI5",
                 "amount_usdc": 5.0, "destination_chain": "stellar"}, {},
            ),
        )

        succeeded = [r for r in results if "tx" in r]
        rejected = [r for r in results if r.get("error") == "insufficient_budget"]
        assert len(succeeded) == 1
        assert len(rejected) == 1
        assert spent_tracker["usdc"] == pytest.approx(5.0)

    @pytest.mark.asyncio
    async def test_failed_payout_refunds_reservation(self, db_session: AsyncSession):
        """Falha DEPOIS da reserva (strkey inválido explode dentro do try) tem que
        estornar — senão orçamento vaza a cada erro de rail."""
        repo = DatabaseRepository(db_session)
        campaign = _make_campaign(db_session)
        await db_session.flush()

        spent_tracker = {"usdc": 0.0}
        executors = _make_executors(repo, campaign.id, budget_usdc=8.0, spent_tracker=spent_tracker)

        result = await executors["payout_cross_chain_nanopayment"](
            {"intent_id": str(uuid.uuid4()), "to": "GNOT_A_VALID_STRKEY",
             "amount_usdc": 5.0, "destination_chain": "stellar"}, {},
        )
        assert "error" in result
        assert spent_tracker["usdc"] == pytest.approx(0.0)


class TestSharedBudgetAcrossToolSets:
    @pytest.mark.asyncio
    async def test_arc_and_cross_chain_payouts_share_budget(self, db_session: AsyncSession):
        """Um pagamento Arc e um cross-chain no MESMO run devem consumir o MESMO
        orçamento — sem spent_tracker compartilhado, o agente poderia gastar 2x."""
        repo = DatabaseRepository(db_session)
        campaign = _make_campaign(db_session)
        await db_session.flush()

        spent_tracker = {"usdc": 0.0}
        arc_executors = make_tool_executors(
            repo=repo, arc_client=ArcClient(sandbox=True),
            campaign_id=campaign.id, budget_usdc=8.0, reward_per_creator=5.0,
            spent_tracker=spent_tracker,
        )
        cctp_executors = _make_executors(repo, campaign.id, budget_usdc=8.0, spent_tracker=spent_tracker)

        arc_result = await arc_executors["pay_creator_nanopayment"](
            {"intent_id": str(uuid.uuid4()), "to": "0xArcCreator", "amount_usdc": 5.0}, {},
        )
        assert "error" not in arc_result

        # Restam 3.0 — pedir 5.0 no cross-chain deve estourar o orçamento COMPARTILHADO
        cctp_result = await cctp_executors["payout_cross_chain_nanopayment"](
            {
                "intent_id": str(uuid.uuid4()),
                "to": "11111111111111111111111111111111",
                "amount_usdc": 5.0,
                "destination_chain": "solana",
            },
            {},
        )
        assert cctp_result.get("error") == "insufficient_budget"
        assert cctp_result["remaining_usdc"] == pytest.approx(3.0)
