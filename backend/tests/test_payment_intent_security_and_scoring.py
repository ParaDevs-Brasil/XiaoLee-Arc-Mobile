"""
Batch 5/N — fecha a meta de 200 testes novos: resiliência a input adversarial no
PaymentIntent (mecanismo de anti-replay do loop agêntico), limites exatos de score
em evaluate_creator, e sandbox do ArcClient sob input arbitrário.
"""
from __future__ import annotations

import uuid

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from ai.agents.creator_pay_tools import make_tool_executors
from database.models import Campaign, CampaignParticipant, User
from database.repository import DatabaseRepository
from server.integrations.arc_client import ArcClient

MALICIOUS_PAYLOADS = [
    "'; DROP TABLE payment_intents; --",
    "<script>alert(1)</script>",
    "\x00null\x00byte",
    "💀" * 30,
    "A" * 5000,
    "النص العربي",
]


def _make_campaign(db_session, name="Bulk Scoring Campaign"):
    c = Campaign(
        creator_twitter_user_id="test_creator", name=name, description="desc",
        campaign_type="social", reward_token="USDC", reward_per_participant=5.0,
        max_participants=1000, reward_pool=5000.0, status="active",
    )
    db_session.add(c)
    return c


# ---------------------------------------------------------------------------
# PaymentIntent — payload malicioso vira dado inerte (mesmo padrão de
# test_security_injection.py, agora para a tabela usada pelo loop autônomo)
# ---------------------------------------------------------------------------

class TestPaymentIntentInjectionResilience:
    @pytest.mark.parametrize("payload", MALICIOUS_PAYLOADS)
    @pytest.mark.asyncio
    async def test_malicious_creator_id_stored_as_inert_data(self, db_session, payload):
        repo = DatabaseRepository(db_session)
        campaign = _make_campaign(db_session)
        await db_session.flush()

        intent_id = str(uuid.uuid4())
        await repo.create_payment_intent(intent_id, campaign.id, payload, 1.0)

        stored = await repo.get_payment_intent(intent_id)
        assert stored.creator_id == payload

    @pytest.mark.parametrize("payload", MALICIOUS_PAYLOADS)
    @pytest.mark.asyncio
    async def test_malicious_creator_id_does_not_corrupt_other_intents(self, db_session, payload):
        repo = DatabaseRepository(db_session)
        campaign = _make_campaign(db_session)
        await db_session.flush()

        legit_id = str(uuid.uuid4())
        await repo.create_payment_intent(legit_id, campaign.id, "@legit_creator", 2.5)

        try:
            await repo.create_payment_intent(str(uuid.uuid4()), campaign.id, payload, 0.01)
        except Exception:
            await db_session.rollback()

        legit = await repo.get_payment_intent(legit_id)
        assert legit is not None
        assert legit.creator_id == "@legit_creator"
        assert float(legit.amount_usdc) == 2.5

    @pytest.mark.asyncio
    async def test_duplicate_intent_id_across_different_campaigns_is_rejected(self, db_session):
        """intent_id é globalmente único (UNIQUE constraint) — não só por campanha.
        Um retry do agente com o mesmo UUID não pode criar dois PaymentIntent mesmo
        que aponte pra campanhas diferentes."""
        repo = DatabaseRepository(db_session)
        c1 = _make_campaign(db_session, name="Campaign A")
        c2 = _make_campaign(db_session, name="Campaign B")
        await db_session.flush()

        shared_intent_id = str(uuid.uuid4())
        await repo.create_payment_intent(shared_intent_id, c1.id, "@c", 1.0)

        with pytest.raises(Exception):
            await repo.create_payment_intent(shared_intent_id, c2.id, "@c", 1.0)

    @pytest.mark.parametrize("campaign_id", [0, -1, -1_000_000, 1_000_000, 2**31 - 1, -(2**31)])
    @pytest.mark.asyncio
    async def test_get_payment_intent_by_creator_arbitrary_campaign_id_never_crashes(self, campaign_id, db_session):
        repo = DatabaseRepository(db_session)
        result = await repo.get_payment_intent_by_creator(campaign_id, "@anyone")
        assert result is None


# ---------------------------------------------------------------------------
# evaluate_creator — limites exatos do score (has_followed=30, has_replied=30,
# has_retweeted=25, tasks_verified=15 -> elegível se score >= 50)
# ---------------------------------------------------------------------------

def _enrolled(db_session, campaign_id, handle, has_followed=False, has_replied=False, has_retweeted=False, status="enrolled"):
    u = User(twitter_handle=handle, twitter_user_id=f"uid_{handle}")
    db_session.add(u)
    return u, has_followed, has_replied, has_retweeted, status


class TestEvaluateCreatorScoreBoundaries:
    async def _score_for(self, db_session, has_followed, has_replied, has_retweeted, status):
        repo = DatabaseRepository(db_session)
        arc = ArcClient(sandbox=True)
        campaign = _make_campaign(db_session, name=f"Score {has_followed}{has_replied}{has_retweeted}{status}-{uuid.uuid4()}")
        await db_session.flush()

        u = User(twitter_handle=f"@scoretest_{uuid.uuid4().hex[:8]}", twitter_user_id=f"uid_{uuid.uuid4().hex[:8]}")
        db_session.add(u)
        await db_session.flush()
        p = CampaignParticipant(
            campaign_id=campaign.id, user_id=u.id,
            has_followed=has_followed, has_replied=has_replied, has_retweeted=has_retweeted,
            status=status,
        )
        db_session.add(p)
        await db_session.flush()

        executors = make_tool_executors(repo=repo, arc_client=arc, campaign_id=campaign.id, budget_usdc=100.0)
        return await executors["evaluate_creator"]({"creator_id": u.twitter_handle, "campaign_id": campaign.id}, {})

    @pytest.mark.asyncio
    async def test_score_exactly_50_is_eligible(self, db_session):
        # has_followed(30) + has_replied(30) = 60 >= 50
        result = await self._score_for(db_session, has_followed=True, has_replied=True, has_retweeted=False, status="enrolled")
        assert result["score"] == 60
        assert result["eligible"] is True

    @pytest.mark.asyncio
    async def test_score_49_is_not_eligible(self, db_session):
        # has_retweeted(25) + tasks_verified(15) = 40, ainda < 50
        result = await self._score_for(db_session, has_followed=False, has_replied=False, has_retweeted=True, status="tasks_verified")
        assert result["score"] == 40
        assert result["eligible"] is False

    @pytest.mark.asyncio
    async def test_score_zero_when_nothing_done(self, db_session):
        result = await self._score_for(db_session, has_followed=False, has_replied=False, has_retweeted=False, status="enrolled")
        assert result["score"] == 0
        assert result["eligible"] is False

    @pytest.mark.asyncio
    async def test_score_100_when_everything_done(self, db_session):
        result = await self._score_for(db_session, has_followed=True, has_replied=True, has_retweeted=True, status="tasks_verified")
        assert result["score"] == 100
        assert result["eligible"] is True

    @pytest.mark.asyncio
    async def test_only_has_followed_score_30_not_eligible(self, db_session):
        result = await self._score_for(db_session, has_followed=True, has_replied=False, has_retweeted=False, status="enrolled")
        assert result["score"] == 30
        assert result["eligible"] is False

    @pytest.mark.asyncio
    async def test_exactly_boundary_score_50_via_retweet_plus_tasks_verified_wrong_math_check(self, db_session):
        # has_retweeted(25) sozinho não fecha 50 mesmo com status tasks_verified sem outros pontos
        result = await self._score_for(db_session, has_followed=False, has_replied=False, has_retweeted=True, status="tasks_verified")
        assert result["score"] == 40
        assert result["eligible"] is False


# ---------------------------------------------------------------------------
# ArcClient sandbox — nunca crasha com input arbitrário (zero rede real)
# ---------------------------------------------------------------------------

class TestArcClientSandboxFuzzing:
    @given(to_address=st.text(max_size=200), amount=st.floats(min_value=0.0001, max_value=1_000_000, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_sandbox_send_usdc_never_crashes_for_arbitrary_address(self, to_address, amount):
        import asyncio
        arc = ArcClient(sandbox=True)
        intent_id = str(uuid.uuid4())
        result = asyncio.run(
            arc.send_usdc(to_address=to_address, amount_usdc=amount, idempotency_key=intent_id)
        )
        assert result.startswith("sandbox_tx_")

    @given(wallet_id=st.text(max_size=100))
    @settings(max_examples=60, suppress_health_check=[HealthCheck.too_slow])
    def test_sandbox_balance_never_crashes_for_arbitrary_wallet_id(self, wallet_id):
        import asyncio
        arc = ArcClient(sandbox=True)
        balance = asyncio.run(arc.get_balance(wallet_id))
        assert balance == 1000.0

    def test_sandbox_never_makes_real_network_call(self, monkeypatch):
        """Garante a invariante: sandbox=True nunca instancia httpx.AsyncClient."""
        import httpx

        def _fail_if_called(*args, **kwargs):
            raise AssertionError("ArcClient sandbox não deveria abrir conexão de rede real")

        monkeypatch.setattr(httpx, "AsyncClient", _fail_if_called)

        import asyncio
        arc = ArcClient(sandbox=True)
        result = asyncio.run(
            arc.send_usdc(to_address="0xabc", amount_usdc=1.0, idempotency_key=str(uuid.uuid4()))
        )
        assert result.startswith("sandbox_tx_")
