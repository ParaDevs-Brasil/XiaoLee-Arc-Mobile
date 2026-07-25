"""
Testes do repositório de SettledPayment — o feed de tração persistido que substitui
o estado 100% in-memory de server/metrics.py (perdido a cada restart do backend).
"""
import pytest

from database.repository import DatabaseRepository


@pytest.mark.asyncio
async def test_create_settled_payment_persists_and_returns_true(db_session):
    repo = DatabaseRepository(db_session)

    is_new = await repo.create_settled_payment(
        intent_id="0xabc123",
        creator_handle="@creator_one",
        amount_usdc=0.50,
        tx="0xabc123",
        latency_ms=120.0,
        ts="2026-06-29T20:31:00-03:00",
    )

    assert is_new is True

    stored = await repo.get_settled_payment("0xabc123")
    assert stored is not None
    assert stored.creator_handle == "@creator_one"
    assert float(stored.amount_usdc) == 0.50
    assert stored.tx == "0xabc123"


@pytest.mark.asyncio
async def test_create_settled_payment_is_idempotent_by_intent_id(db_session):
    repo = DatabaseRepository(db_session)

    first = await repo.create_settled_payment(
        intent_id="dup-intent",
        creator_handle="@creator_two",
        amount_usdc=1.0,
        tx="0xdup",
        latency_ms=80.0,
    )
    second = await repo.create_settled_payment(
        intent_id="dup-intent",
        creator_handle="@creator_two",
        amount_usdc=1.0,
        tx="0xdup",
        latency_ms=80.0,
    )

    assert first is True
    assert second is False

    all_payments = await repo.list_settled_payments()
    assert len([p for p in all_payments if p.intent_id == "dup-intent"]) == 1


@pytest.mark.asyncio
async def test_create_settled_payment_without_ts_defaults_to_now(db_session):
    repo = DatabaseRepository(db_session)

    await repo.create_settled_payment(
        intent_id="no-ts",
        creator_handle="@creator_three",
        amount_usdc=0.10,
        tx="0xnots",
        latency_ms=50.0,
    )

    stored = await repo.get_settled_payment("no-ts")
    assert stored.settled_at is not None


@pytest.mark.asyncio
async def test_list_settled_payments_is_chronological_ascending(db_session):
    repo = DatabaseRepository(db_session)

    await repo.create_settled_payment(
        intent_id="later",
        creator_handle="@c",
        amount_usdc=0.05,
        tx="0x2",
        latency_ms=10.0,
        ts="2026-06-29T21:00:00+00:00",
    )
    await repo.create_settled_payment(
        intent_id="earlier",
        creator_handle="@c",
        amount_usdc=0.05,
        tx="0x1",
        latency_ms=10.0,
        ts="2026-06-29T20:00:00+00:00",
    )

    ordered = await repo.list_settled_payments()
    assert [p.intent_id for p in ordered] == ["earlier", "later"]


@pytest.mark.asyncio
async def test_get_settled_payment_returns_none_when_missing(db_session):
    repo = DatabaseRepository(db_session)
    assert await repo.get_settled_payment("does-not-exist") is None
