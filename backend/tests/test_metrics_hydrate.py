"""
Testes de server.metrics.hydrate_traction — reconstrói o estado in-memory de tração
a partir de linhas persistidas no DB. Chamado no boot do app (lifespan) para o
dashboard sobreviver a restart do backend.
"""
from server.metrics import clear_metrics, get_traction_snapshot, hydrate_traction, record_payment_settled


def test_hydrate_traction_rebuilds_totals_and_feed():
    clear_metrics()

    hydrate_traction([
        {
            "intent_id": "0x1",
            "amount_usdc": 0.10,
            "creator_handle": "@agent_arc_native",
            "tx": "0x1",
            "latency_ms": 0.0,
            "ts": "2026-06-29T20:31:00-03:00",
        },
        {
            "intent_id": "0x2",
            "amount_usdc": 0.50,
            "creator_handle": "@music_nft",
            "tx": "0x2",
            "latency_ms": 0.0,
            "ts": "2026-06-29T20:40:00-03:00",
        },
    ])

    snap = get_traction_snapshot()
    assert snap["total_usdc"] == 0.60
    assert snap["total_payments"] == 2
    assert snap["active_creators"] == 2
    assert [e["intent_id"] for e in snap["feed"]] == ["0x2", "0x1"]  # mais recente primeiro


def test_hydrate_traction_is_idempotent_on_duplicate_intent_id():
    clear_metrics()

    rows = [{
        "intent_id": "dup",
        "amount_usdc": 1.0,
        "creator_handle": "@c",
        "tx": "0xdup",
        "latency_ms": 0.0,
        "ts": "2026-06-29T20:00:00-03:00",
    }]

    hydrate_traction(rows)
    hydrate_traction(rows)  # boot duas vezes não pode duplicar o total

    snap = get_traction_snapshot()
    assert snap["total_usdc"] == 1.0
    assert snap["total_payments"] == 1


def test_hydrate_traction_then_new_payment_does_not_double_count():
    clear_metrics()

    hydrate_traction([{
        "intent_id": "0xold",
        "amount_usdc": 1.0,
        "creator_handle": "@c",
        "tx": "0xold",
        "latency_ms": 0.0,
        "ts": "2026-06-29T20:00:00-03:00",
    }])

    # Tentativa de "reprocessar" o mesmo evento via fluxo normal (ex: replay HTTP) — deve
    # ser ignorada porque hydrate_traction já marcou intent_id como processado.
    is_new = record_payment_settled(
        intent_id="0xold",
        amount_usdc=1.0,
        latency_ms=0.0,
        creator_handle="@c",
        tx="0xold",
    )
    assert is_new is False

    snap = get_traction_snapshot()
    assert snap["total_usdc"] == 1.0
    assert snap["total_payments"] == 1
