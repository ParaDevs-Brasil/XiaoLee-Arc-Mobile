"""
test_wallet_link_route.py — `POST /auth/wallet`, vínculo autenticado de carteira.

O endereço de carteira é o destino de payout do usuário: é para lá que o agente
manda USDC. Quem consegue gravá-lo redireciona dinheiro.

A rota legada `POST /user/{user_id}/wallet` recebe o `user_id` pela URL e não
verifica autorização nenhuma — qualquer um reivindica o endereço de um usuário
que ainda não configurou o dele. Estes testes fixam o comportamento do
substituto: o dono sai da sessão, nunca da request.
"""
from __future__ import annotations

import importlib
import os
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import select

os.environ.setdefault("JWT_SECRET", "wallet-test-jwt-secret-32-chars-ok")
os.environ.setdefault("ENCRYPTION_KEY", "wallet-test-encryption-key-xxxxx")

from database.database import get_db_session
from database.models import User, Wallet, WebSession

app_module = importlib.import_module("server.app")
client = TestClient(app_module.app)

ADDRESS = "0x1234567890abcdef1234567890AbCdEf12345678"
OTHER_ADDRESS = "0xfeedfacefeedfacefeedfacefeedfacefeedface"


@pytest_asyncio.fixture
async def db(db_session):
    async def _override():
        yield db_session

    app_module.app.dependency_overrides[get_db_session] = _override
    yield db_session
    app_module.app.dependency_overrides.pop(get_db_session, None)


async def _session_for(db, twitter_user_id: str, *, expired: bool = False) -> str:
    """Cria usuário + sessão e devolve o token."""
    db.add(User(twitter_user_id=twitter_user_id, twitter_handle=twitter_user_id))
    token = f"sess_{twitter_user_id}"
    delta = timedelta(days=-1) if expired else timedelta(days=30)
    db.add(
        WebSession(
            session_id=token,
            twitter_user_id=twitter_user_id,
            expires_at=datetime.utcnow() + delta,
        )
    )
    await db.commit()
    return token


def _link(token: str | None, payload: dict):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.post("/auth/wallet", json=payload, headers=headers)


class TestHappyPath:
    @pytest.mark.asyncio
    async def test_links_wallet_to_the_session_owner(self, db):
        token = await _session_for(db, "user_a")
        resp = _link(token, {"address": ADDRESS, "chain": "arc"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["address"] == ADDRESS

        user = (
            await db.execute(select(User).where(User.twitter_user_id == "user_a"))
        ).scalars().first()
        wallet = (
            await db.execute(select(Wallet).where(Wallet.user_id == user.id))
        ).scalars().first()
        assert wallet is not None
        assert wallet.address == ADDRESS

    @pytest.mark.asyncio
    async def test_relinking_the_same_address_is_idempotent(self, db):
        token = await _session_for(db, "user_a")
        _link(token, {"address": ADDRESS, "chain": "arc"})
        resp = _link(token, {"address": ADDRESS, "chain": "arc"})
        assert resp.status_code == 200
        assert (await db.execute(select(Wallet))).scalars().all().__len__() == 1

    @pytest.mark.asyncio
    async def test_user_can_replace_their_own_address(self, db):
        """Trocar de carteira é operação legítima do dono — não pode travar."""
        token = await _session_for(db, "user_a")
        _link(token, {"address": ADDRESS, "chain": "arc"})
        resp = _link(token, {"address": OTHER_ADDRESS, "chain": "arc"})
        assert resp.status_code == 200
        assert resp.json()["address"] == OTHER_ADDRESS

        wallets = (await db.execute(select(Wallet))).scalars().all()
        assert len(wallets) == 1
        assert wallets[0].address == OTHER_ADDRESS


class TestRejections:
    @pytest.mark.asyncio
    async def test_without_session_is_401(self, db):
        assert _link(None, {"address": ADDRESS}).status_code == 401

    @pytest.mark.asyncio
    async def test_unknown_session_is_401(self, db):
        assert _link("sess_inexistente", {"address": ADDRESS}).status_code == 401

    @pytest.mark.asyncio
    async def test_expired_session_is_401(self, db):
        token = await _session_for(db, "user_a", expired=True)
        assert _link(token, {"address": ADDRESS}).status_code == 401

    @pytest.mark.asyncio
    async def test_rejected_request_creates_no_wallet(self, db):
        _link("sess_inexistente", {"address": ADDRESS})
        assert (await db.execute(select(Wallet))).scalars().all() == []

    @pytest.mark.asyncio
    async def test_missing_address_is_400(self, db):
        token = await _session_for(db, "user_a")
        assert _link(token, {}).status_code == 400

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "bad",
        [
            "não-é-endereço",
            "0x123",  # curto demais
            "1234567890abcdef1234567890abcdef12345678",  # sem 0x
            "0x1234567890abcdef1234567890abcdef1234567g",  # caractere inválido
            "",
            "   ",
        ],
    )
    async def test_malformed_address_is_400(self, db, bad):
        token = await _session_for(db, "user_a")
        assert _link(token, {"address": bad}).status_code == 400


class TestOwnershipIsFromSession:
    """O ponto da rota: o dono sai do token, nunca do corpo ou da URL."""

    @pytest.mark.asyncio
    async def test_cannot_target_another_user_via_body(self, db):
        """Regressão direta do furo de `POST /user/{user_id}/wallet`."""
        await _session_for(db, "vitima")
        attacker = await _session_for(db, "atacante")

        resp = _link(
            attacker,
            {"address": ADDRESS, "user_id": "vitima", "twitter_user_id": "vitima"},
        )
        assert resp.status_code == 200

        vitima = (
            await db.execute(select(User).where(User.twitter_user_id == "vitima"))
        ).scalars().first()
        stolen = (
            await db.execute(select(Wallet).where(Wallet.user_id == vitima.id))
        ).scalars().first()
        assert stolen is None, "endereço foi gravado no usuário errado"
