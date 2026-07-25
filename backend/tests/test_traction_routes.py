"""
Testes de POST /v1/payments/settled e GET /v1/traction/stats — cobre o novo caminho de
persistência (settled_payments) introduzido para o dashboard de tração sobreviver a
restart do backend. Nenhum teste aqui deve disparar chamada de rede real à Circle.
"""
import importlib

import pytest
from fastapi.testclient import TestClient

app_module = importlib.import_module("server.app")
from database.database import get_db_session
from database.repository import DatabaseRepository
from server.metrics import clear_metrics

client = TestClient(app_module.app)

_ARC_SECRET = "xle_arc_pay_2026_lepton_f0ntz"


@pytest.fixture(autouse=True)
def _isolated_settings_and_metrics(db_session):
    """Cada teste roda com métricas zeradas, secret previsível e sem credencial Circle
    real ativa (evita qualquer chamada de rede de verdade durante a suíte).

    settings é um dataclass frozen — monkeypatch.setattr não consegue desfazer no
    teardown, então salvamos/restauramos manualmente via object.__setattr__ (mesmo
    padrão de tests/test_helius_webhook.py)."""
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


def _settle(intent_id: str, amount: float = 0.10, creator: str = "@creator_one", tx: str = "0xabc") -> "object":
    return client.post(
        "/v1/payments/settled",
        json={"intent_id": intent_id, "amount": amount, "creator": creator, "tx": tx, "latency_ms": 42.0},
        headers={"X-Arc-Secret": _ARC_SECRET},
    )


@pytest.mark.asyncio
async def test_payment_settled_persists_to_db(db_session):
    resp = _settle("intent-1", amount=0.25, creator="@music_nft", tx="0xreal1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["duplicate"] is False

    repo = DatabaseRepository(db_session)
    stored = await repo.get_settled_payment("intent-1")
    assert stored is not None
    assert stored.tx == "0xreal1"
    assert float(stored.amount_usdc) == 0.25


def test_payment_settled_updates_traction_stats():
    _settle("intent-2", amount=0.50, creator="@web3_creator", tx="0xreal2")

    stats = client.get("/v1/traction/stats").json()
    assert stats["total_usdc"] == 0.50
    assert stats["total_payments"] == 1
    assert stats["active_creators"] == 1
    assert stats["feed"][0]["intent_id"] == "intent-2"


def test_payment_settled_duplicate_intent_id_is_ignored_and_not_double_counted():
    first = _settle("intent-dup", amount=1.0, creator="@c", tx="0xdup")
    second = _settle("intent-dup", amount=1.0, creator="@c", tx="0xdup")

    assert first.json()["duplicate"] is False
    assert second.json()["duplicate"] is True

    stats = client.get("/v1/traction/stats").json()
    assert stats["total_usdc"] == 1.0
    assert stats["total_payments"] == 1


def test_payment_settled_rejects_wrong_arc_secret():
    resp = client.post(
        "/v1/payments/settled",
        json={"intent_id": "intent-bad-secret", "amount": 0.10, "creator": "@c", "tx": "0xbad"},
        headers={"X-Arc-Secret": "wrong-secret"},
    )
    assert resp.status_code == 401


def test_payment_settled_rejects_missing_arc_secret():
    resp = client.post(
        "/v1/payments/settled",
        json={"intent_id": "intent-no-secret", "amount": 0.10, "creator": "@c", "tx": "0xnosecret"},
    )
    assert resp.status_code == 401


def test_payment_settled_does_not_call_circle_when_creator_not_registered(monkeypatch):
    """creator não registrado -> get_registered_creator_wallet retorna None -> não deve
    tentar transferir via Circle, independente de circle_api_key."""
    import server.traction_routes as traction_routes_module

    async def _fail_if_called(*args, **kwargs):
        raise AssertionError("transfer_usdc não deveria ser chamado para creator não registrado")

    monkeypatch.setattr(traction_routes_module, "transfer_usdc", _fail_if_called)

    resp = _settle("intent-no-creator", creator="@unregistered_creator", tx="0xnocreator")
    assert resp.status_code == 200
    assert resp.json()["circle_transfer_id"] is None
