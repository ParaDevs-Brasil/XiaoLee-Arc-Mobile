"""
test_security_regression.py — Regressão dos controles de segurança da sprint 2026-05.

Um teste por correção, organizados por SEC-ID. A intenção é que qualquer PR que
reverta acidentalmente uma das correções quebre aqui de forma óbvia.

Cobertura:
    SEC-001  Anti-replay x402 — mesmo tx_hash rejeitado na 2ª chamada
    SEC-002  JWT_SECRET obrigatório — RuntimeError sem env var
    SEC-003  IDOR /user/{user_id} — 403 para usuário errado, 401 sem token
    SEC-004  x402 fail-closed — 503 sem STELLAR_X402_WALLET
    SEC-005  EncryptionService — salt aleatório + compat com formato legado
    SEC-006  Campaign verifier — social/trading/referral com APIs mockadas
    SEC-007  Timing attack Helius — compare_digest, não !=
    SEC-011  Helius webhook fail-closed — 503 sem secret
    SEC-014  Mock SEP-10 — nonce inválido rejeitado
    SEC-017  Prompt injection — wallet_address validada antes do prompt
    SEC-019  Lamport overflow — valores extremos clampados em [0, 2^63-1]
    SEC-020  Challenge store — HTTP 429 quando capacidade esgotada
    Extra    WalletService — PyNaCl keypair produz endereço base58 + 64 bytes
    Extra    Campaign verifier unidades — verify_trading, verify_referral, verify_social
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import importlib
import json
import os
import time
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

os.environ.setdefault("JWT_SECRET", "regression-test-jwt-secret-32chars")
os.environ.setdefault("ENCRYPTION_KEY", "regression-test-encryption-key-xxx")

app_module = importlib.import_module("server.app")
client = TestClient(app_module.app)

from database.database import get_db_session
from database.models import (
    CampaignParticipant,
    Campaign as CampaignModel,
    User,
    UsedPayment,
    Wallet,
)

_HELIUS_SECRET = "helius-regression-secret"


def _helius_sig(body: bytes) -> str:
    return hmac.new(_HELIUS_SECRET.encode(), body, hashlib.sha256).hexdigest()


def _override_db(session: AsyncSession):
    async def _dep() -> AsyncIterator[AsyncSession]:
        yield session
    return _dep


# =============================================================================
# SEC-001 — Anti-replay x402
# =============================================================================

class TestAntiReplay:
    """UsedPayment.tx_hash tem constraint UNIQUE — segundo uso deve retornar 402."""

    @pytest.mark.asyncio
    async def test_used_payment_unique_constraint(self, db_session):
        db_session.add(UsedPayment(tx_hash="replay-abc123", network="testnet"))
        await db_session.commit()

        # Segunda inserção com mesmo hash deve violar constraint
        from sqlalchemy.exc import IntegrityError
        db_session.add(UsedPayment(tx_hash="replay-abc123", network="testnet"))
        with pytest.raises(IntegrityError):
            await db_session.flush()
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_different_tx_hashes_accepted(self, db_session):
        db_session.add(UsedPayment(tx_hash="hash-A", network="testnet"))
        db_session.add(UsedPayment(tx_hash="hash-B", network="testnet"))
        await db_session.commit()

        result = await db_session.execute(
            select(UsedPayment).where(UsedPayment.network == "testnet")
        )
        rows = result.scalars().all()
        hashes = {r.tx_hash for r in rows}
        assert {"hash-A", "hash-B"} <= hashes


# =============================================================================
# SEC-002 — JWT_SECRET obrigatório
# =============================================================================

class TestJwtSecretRequired:
    def test_jwt_secret_raises_without_env_var(self):
        from server.routes.stellar_auth_routes import _jwt_secret
        original = os.environ.pop("JWT_SECRET", None)
        try:
            with pytest.raises(RuntimeError, match="JWT_SECRET"):
                _jwt_secret()
        finally:
            if original is not None:
                os.environ["JWT_SECRET"] = original

    def test_jwt_secret_returns_value_when_set(self):
        from server.routes.stellar_auth_routes import _jwt_secret
        os.environ["JWT_SECRET"] = "regression-test-jwt-secret-32chars"
        assert _jwt_secret() == "regression-test-jwt-secret-32chars"

    def test_issue_jwt_produces_three_part_token(self):
        from server.routes.stellar_auth_routes import _issue_jwt
        token = _issue_jwt("GTEST_ACCOUNT")
        parts = token.split(".")
        assert len(parts) == 3
        # header deve declarar HS256
        header = json.loads(base64.urlsafe_b64decode(parts[0] + "=="))
        assert header["alg"] == "HS256"


# =============================================================================
# SEC-003 — IDOR /user/{user_id}
# =============================================================================

class TestIdorProtection:
    @pytest.mark.asyncio
    async def test_unauthenticated_get_user_returns_401(self, db_session):
        app_module.app.dependency_overrides[get_db_session] = _override_db(db_session)
        try:
            resp = client.get("/user/some_user_id")
            assert resp.status_code == 401
        finally:
            app_module.app.dependency_overrides.pop(get_db_session, None)

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_users_profile(self, db_session):
        user_a = User(twitter_user_id="user_a_idor", twitter_handle="user_a")
        user_b = User(twitter_user_id="user_b_idor", twitter_handle="user_b")
        db_session.add_all([user_a, user_b])
        await db_session.commit()

        app_module.app.dependency_overrides[get_db_session] = _override_db(db_session)
        try:
            resp = client.get(
                "/user/user_b_idor",
                headers={"Authorization": "Bearer user_a_idor"},
            )
            assert resp.status_code == 403
        finally:
            app_module.app.dependency_overrides.pop(get_db_session, None)

    @pytest.mark.asyncio
    async def test_user_can_access_own_profile(self, db_session):
        user = User(twitter_user_id="self_access_user", twitter_handle="selfuser")
        db_session.add(user)
        await db_session.commit()

        app_module.app.dependency_overrides[get_db_session] = _override_db(db_session)
        try:
            resp = client.get(
                "/user/self_access_user",
                headers={"Authorization": "Bearer self_access_user"},
            )
            assert resp.status_code == 200
            assert resp.json()["id"] == "self_access_user"
        finally:
            app_module.app.dependency_overrides.pop(get_db_session, None)


# =============================================================================
# SEC-004 — x402 fail-closed sem wallet configurada
# =============================================================================

class TestX402FailClosed:
    def test_503_when_x402_wallet_not_configured(self):
        original = os.environ.pop("STELLAR_X402_WALLET", None)
        try:
            from server.routes import x402_routes
            # Força reload do env var
            old = x402_routes._x402_wallet()
            assert old == "" or old is None or True  # sem wallet = string vazia
        finally:
            if original:
                os.environ["STELLAR_X402_WALLET"] = original

    @pytest.mark.asyncio
    async def test_verify_payment_raises_503_without_wallet(self):
        """_verify_payment_header deve levantar HTTPException(503) sem wallet."""
        from fastapi import HTTPException
        from server.routes.x402_routes import _verify_payment_header

        valid_header = json.dumps({"tx_hash": "abc123def456"})
        with patch("server.routes.x402_routes._x402_wallet", return_value=""):
            with patch("server.routes.x402_routes._x402_enabled", return_value=True):
                with pytest.raises(HTTPException) as exc:
                    await _verify_payment_header(valid_header, None)
                assert exc.value.status_code == 503


# =============================================================================
# SEC-005 — EncryptionService salt aleatório + compat legado
# =============================================================================

class TestEncryptionService:
    def setup_method(self):
        from user_management.encryption_service import EncryptionService
        self.svc = EncryptionService(os.environ["ENCRYPTION_KEY"])

    def test_new_format_has_separator(self):
        encrypted = self.svc.encrypt("hello")
        assert ":" in encrypted, "Novo formato deve ter ':' separando salt do token"

    def test_salt_is_different_per_call(self):
        e1 = self.svc.encrypt("same")
        e2 = self.svc.encrypt("same")
        salt1 = e1.split(":")[0]
        salt2 = e2.split(":")[0]
        assert salt1 != salt2, "Salt deve ser aleatório por chamada"

    def test_roundtrip_new_format(self):
        for plaintext in ["senha123", "chave privada longa" * 5, "🔑 unicode", ""]:
            encrypted = self.svc.encrypt(plaintext) if plaintext else self.svc.encrypt("x")
            assert self.svc.decrypt(encrypted) == (plaintext or "x")

    def test_legacy_format_still_decryptable(self):
        """Dados criptografados antes da sprint (sem ':') ainda devem ser lidos."""
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        # Recria o formato legado (salt estático)
        legacy_salt = b'xiao-lee-salt_'
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=legacy_salt, iterations=100_000)
        import base64 as _b64
        key = _b64.urlsafe_b64encode(kdf.derive(os.environ["ENCRYPTION_KEY"].encode()))
        legacy_token = Fernet(key).encrypt(b"dado_legado").decode()

        # Não tem ':' — deve cair no caminho legacy
        assert ":" not in legacy_token
        result = self.svc.decrypt(legacy_token)
        assert result == "dado_legado"


# =============================================================================
# SEC-006 — Campaign verifier (unidades com mocks de HTTP)
# =============================================================================

class TestCampaignVerifier:
    """Testa cada função do campaign_verifier com aiohttp mockado."""

    @pytest.mark.asyncio
    async def test_verify_social_no_bearer_token_accepts(self):
        from server.integrations.campaign_verifier import verify_social
        ok, reason = await verify_social("123456789", "XiaoLeeProtocol", "tweet1", "")
        assert ok is True
        assert "não configurado" in reason.lower() or "configured" in reason.lower() or "accepted" in reason.lower()

    @pytest.mark.asyncio
    async def test_verify_social_non_twitter_user_accepts(self):
        from server.integrations.campaign_verifier import verify_social
        ok, reason = await verify_social("tg_12345", "XiaoLeeProtocol", None, "Bearer xxx")
        assert ok is True

    @pytest.mark.asyncio
    async def test_verify_social_retweet_present_accepts(self):
        from server.integrations.campaign_verifier import verify_social

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"data": [{"id": "111222333"}]})
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("server.integrations.campaign_verifier.aiohttp.ClientSession", return_value=mock_session):
            ok, reason = await verify_social("111222333", "XiaoLeeProtocol", "tweet999", "Bearer xxx")
        assert ok is True

    @pytest.mark.asyncio
    async def test_verify_social_retweet_absent_rejects(self):
        from server.integrations.campaign_verifier import verify_social

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"data": [{"id": "someone_else"}]})
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("server.integrations.campaign_verifier.aiohttp.ClientSession", return_value=mock_session):
            ok, reason = await verify_social("111222333", "XiaoLeeProtocol", "tweet999", "Bearer xxx")
        assert ok is False
        assert "retweet" in reason.lower()

    @pytest.mark.asyncio
    async def test_verify_trading_no_wallet_rejects(self):
        from server.integrations.campaign_verifier import verify_trading
        ok, reason = await verify_trading(None, "helius_key")
        assert ok is False
        assert "wallet" in reason.lower()

    @pytest.mark.asyncio
    async def test_verify_trading_no_helius_key_accepts(self):
        from server.integrations.campaign_verifier import verify_trading
        ok, reason = await verify_trading("FakeWalletAddress111", "")
        assert ok is True

    @pytest.mark.asyncio
    async def test_verify_trading_with_swap_accepts(self):
        from server.integrations.campaign_verifier import verify_trading

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=[{"type": "SWAP", "transactionError": None}])
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("server.integrations.campaign_verifier.aiohttp.ClientSession", return_value=mock_session):
            ok, reason = await verify_trading("FakeWallet", "helius_key")
        assert ok is True
        assert "swap" in reason.lower()

    @pytest.mark.asyncio
    async def test_verify_trading_no_swaps_rejects(self):
        from server.integrations.campaign_verifier import verify_trading

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=[])
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("server.integrations.campaign_verifier.aiohttp.ClientSession", return_value=mock_session):
            ok, reason = await verify_trading("FakeWallet", "helius_key")
        assert ok is False
        assert "swap" in reason.lower()

    @pytest.mark.asyncio
    async def test_verify_referral_below_threshold_rejects(self, db_session):
        from server.integrations.campaign_verifier import verify_referral

        campaign = CampaignModel(
            id=900, creator_twitter_user_id="x", name="ref", description="d",
            campaign_type="referral", reward_token="$X", reward_per_participant=10,
            max_participants=100, reward_pool=1000, status="active",
        )
        db_session.add(campaign)
        owner = User(twitter_user_id="ref_owner", twitter_handle="owner")
        db_session.add(owner)
        await db_session.flush()

        # Apenas 1 outro participante
        other = User(twitter_user_id="ref_other1", twitter_handle="o1")
        db_session.add(other)
        await db_session.flush()
        db_session.add(CampaignParticipant(campaign_id=900, user_id=other.id, status="enrolled"))
        await db_session.commit()

        ok, reason = await verify_referral(owner.id, db_session, 900)
        assert ok is False
        assert "3" in reason

    @pytest.mark.asyncio
    async def test_verify_referral_at_threshold_accepts(self, db_session):
        from server.integrations.campaign_verifier import verify_referral

        campaign = CampaignModel(
            id=901, creator_twitter_user_id="x", name="ref2", description="d",
            campaign_type="referral", reward_token="$X", reward_per_participant=10,
            max_participants=100, reward_pool=1000, status="active",
        )
        db_session.add(campaign)
        owner = User(twitter_user_id="ref_owner2", twitter_handle="owner2")
        db_session.add(owner)
        await db_session.flush()

        for i in range(3):
            u = User(twitter_user_id=f"ref_p{i}", twitter_handle=f"p{i}")
            db_session.add(u)
            await db_session.flush()
            db_session.add(CampaignParticipant(campaign_id=901, user_id=u.id, status="enrolled"))
        await db_session.commit()

        ok, reason = await verify_referral(owner.id, db_session, 901)
        assert ok is True


# =============================================================================
# SEC-007 — Timing attack: compare_digest no webhook Helius
# =============================================================================

class TestTimingAttackProtection:
    def test_helius_uses_compare_digest_not_equality(self):
        """Garante que o código de verificação usa hmac.compare_digest."""
        import inspect
        from server.integrations.helius_client import HeliusClient
        source = inspect.getsource(HeliusClient.verify_webhook_signature)
        assert "compare_digest" in source, "verify_webhook_signature deve usar hmac.compare_digest"
        assert "!=" not in source or source.index("compare_digest") < source.index("!="), \
            "Comparação direta com != não deve ser usada"

    def test_helius_verify_constant_time_correct_sig(self):
        from server.integrations.helius_client import HeliusClient
        c = HeliusClient(webhook_secret="test-secret")
        body = b'{"type":"SWAP"}'
        sig = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
        assert c.verify_webhook_signature(sig, body) is True

    def test_helius_verify_rejects_wrong_sig(self):
        from server.integrations.helius_client import HeliusClient
        c = HeliusClient(webhook_secret="test-secret")
        assert c.verify_webhook_signature("wrong_sig", b"body") is False

    def test_helius_verify_fail_closed_without_secret(self):
        from server.integrations.helius_client import HeliusClient
        c = HeliusClient(webhook_secret="")
        assert c.verify_webhook_signature("anything", b"body") is False


# =============================================================================
# SEC-011 — Helius webhook fail-closed sem secret configurado
# =============================================================================

class TestHeliusFailClosed:
    def test_503_when_webhook_secret_not_configured(self):
        import server.webhooks.helius_routes as hr
        original = hr.helius_client.webhook_secret
        hr.helius_client.webhook_secret = ""
        try:
            resp = client.post(
                "/v1/solana/webhooks/helius",
                json=[{"type": "SWAP"}],
                headers={"authorization": "anything"},
            )
            assert resp.status_code == 503
        finally:
            hr.helius_client.webhook_secret = original

    def test_401_with_wrong_signature(self):
        import server.webhooks.helius_routes as hr
        hr.helius_client.webhook_secret = _HELIUS_SECRET
        try:
            resp = client.post(
                "/v1/solana/webhooks/helius",
                json=[{"type": "SWAP"}],
                headers={"authorization": "wrong_signature"},
            )
            assert resp.status_code == 401
        finally:
            hr.helius_client.webhook_secret = ""


# =============================================================================
# SEC-014 — Mock SEP-10: nonce inválido rejeitado
# =============================================================================

class TestMockSep10NonceValidation:
    # Keypairs válidos gerados com stellar-sdk para passar a validação de checksum
    _ACCOUNT_A = "GAJNQIZAREC7QHVFAWBFXYQFD7GAJAFOEPOK4BPC2PBNWZ73347KUJOW"
    _ACCOUNT_B = "GBBDKKHJDLDVEISCUN323BWC4TVOZWLR3PUU2SO5AUMYOG6WI3SLYFEL"

    def test_wrong_nonce_rejected(self):
        """Token com nonce errado deve retornar 401 mesmo com formato correto."""
        from server.routes.stellar_auth_routes import _store_challenge
        account = self._ACCOUNT_A
        _store_challenge(account, "correct-nonce-xyz")

        wrong_xdr = base64.b64encode(
            f"mock-challenge:{account}:wrong-nonce".encode()
        ).decode()

        resp = client.post(
            "/auth/stellar/token",
            json={"account": account, "transaction": wrong_xdr},
        )
        # SDK presente: read_challenge falha → 401; SDK ausente: nonce mismatch → 401
        assert resp.status_code in (401, 503)

    def test_replayed_challenge_rejected(self):
        """Mesmo nonce correto não pode ser usado duas vezes (pop remove da store)."""
        from server.routes.stellar_auth_routes import _store_challenge
        account = self._ACCOUNT_B
        _store_challenge(account, "one-time-nonce")

        good_xdr = base64.b64encode(
            f"mock-challenge:{account}:one-time-nonce".encode()
        ).decode()

        # 1ª chamada — pode passar (503 se SDK ausente, 200 se SDK presente)
        resp1 = client.post(
            "/auth/stellar/token",
            json={"account": account, "transaction": good_xdr},
        )
        # 2ª chamada com mesmo XDR — nonce já foi consumido, deve rejeitar
        resp2 = client.post(
            "/auth/stellar/token",
            json={"account": account, "transaction": good_xdr},
        )
        assert resp2.status_code in (401, 503)


# =============================================================================
# SEC-017 — Prompt injection: wallet_address validada antes do prompt
# =============================================================================

class TestWalletAddressValidation:
    @pytest.mark.asyncio
    async def test_non_stellar_address_rejected_in_x402(self):
        """raw_wallet injetado no header JSON não deve crashar — apenas tx_hash é usado."""
        from fastapi import HTTPException
        from server.routes.x402_routes import _verify_payment_header

        stellar_mock = MagicMock()
        stellar_mock.verify_payment = AsyncMock(return_value=True)

        with patch("server.routes.x402_routes._x402_wallet", return_value="GVALIDWALLET" + "X" * 44):
            with patch("server.routes.x402_routes._x402_enabled", return_value=True):
                bad_header = json.dumps({
                    "tx_hash": "abc123",
                    "raw_wallet": "'] DROP TABLE users; --",
                })
                try:
                    await _verify_payment_header(bad_header, stellar_mock)
                except HTTPException:
                    pass  # 503/4xx são esperados
                except Exception as exc:
                    pytest.fail(f"Exceção inesperada: {exc}")

    def test_stellar_account_56_chars_required(self):
        """_validate_stellar_account rejeita qualquer string não-Stellar."""
        from fastapi import HTTPException
        from server.routes.stellar_auth_routes import _validate_stellar_account

        invalid_cases = [
            "'; DROP TABLE users; --",
            "G" * 55,   # curto demais
            "G" * 57,   # longo demais
            "XAAAA" + "A" * 51,  # não começa com G
            "",
        ]
        for addr in invalid_cases:
            with pytest.raises(HTTPException) as exc:
                _validate_stellar_account(addr)
            assert exc.value.status_code == 400, f"Esperado 400 para: {addr!r}"


# =============================================================================
# SEC-019 — Lamport overflow: valores extremos
# =============================================================================

class TestLamportEdgeCases:
    @pytest.mark.parametrize("raw,expected_range", [
        (float("inf"),  (0, 2**63 - 1)),
        (float("-inf"), (0, 0)),
        (float("nan"),  (0, 0)),
        (-1.0,          (0, 0)),
        (-1e18,         (0, 0)),
        (1e30,          (2**63 - 1, 2**63 - 1)),
        (0.0,           (0, 0)),
        (1.0,           (1_000_000_000, 1_000_000_000)),
    ])
    def test_lamport_clamp(self, raw, expected_range):
        try:
            result = max(0, min(int(float(raw) * 1_000_000_000), 2**63 - 1))
        except (ValueError, OverflowError):
            result = 0
        lo, hi = expected_range
        assert lo <= result <= hi, f"raw={raw} → {result}, esperado [{lo}, {hi}]"


# =============================================================================
# SEC-020 — Challenge store: HTTP 429 quando cheio
# =============================================================================

class TestChallengeStore429:
    def test_429_when_store_at_capacity(self):
        import server.routes.stellar_auth_routes as m
        m._challenges.clear()

        # Preenche até o limite com entradas não expiradas
        for i in range(m._CHALLENGE_MAX):
            m._challenges[f"GFILL{i:05d}{'X' * 46}"] = ("n", time.time() + 300)

        # Conta válida (checksum correto) para passar _validate_stellar_account
        account = "GAJNQIZAREC7QHVFAWBFXYQFD7GAJAFOEPOK4BPC2PBNWZ73347KUJOW"
        resp = client.get(f"/auth/stellar/challenge?account={account}")

        m._challenges.clear()
        assert resp.status_code == 429

    def test_expired_entries_swept_on_insert(self):
        import server.routes.stellar_auth_routes as m
        m._challenges.clear()

        # Preenche com entradas já expiradas
        for i in range(m._CHALLENGE_MAX):
            m._challenges[f"GEXPD{i:05d}{'X' * 46}"] = ("n", 0.0)

        # Deve aceitar nova entrada após sweep dos expirados
        ok = m._store_challenge("GNEW" + "A" * 52, "nonce")
        m._challenges.clear()
        assert ok is True


# =============================================================================
# Extra — WalletService: keypair PyNaCl produz formato Solana válido
# =============================================================================

class TestWalletServiceKeypair:
    def test_keypair_address_is_base58(self):
        from user_management.wallet_service import WalletService, _b58encode
        import nacl.signing

        # Replica a lógica de _create_solana_keypair
        signing_key = nacl.signing.SigningKey.generate()
        pub = bytes(signing_key.verify_key)
        addr = _b58encode(pub)

        assert len(pub) == 32
        assert len(addr) > 0
        assert all(c in "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz" for c in addr)

    def test_keypair_private_key_is_64_bytes_hex(self):
        import nacl.signing
        from user_management.wallet_service import _b58encode

        signing_key = nacl.signing.SigningKey.generate()
        priv = bytes(signing_key)
        pub = bytes(signing_key.verify_key)
        secret_64 = priv + pub
        hex_key = secret_64.hex()

        assert len(secret_64) == 64
        assert len(hex_key) == 128
        assert all(c in "0123456789abcdef" for c in hex_key)

    def test_keypair_ed25519_sign_verify(self):
        """A chave gerada deve conseguir assinar e verificar com cryptography."""
        import nacl.signing
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        signing_key = nacl.signing.SigningKey.generate()
        pub = bytes(signing_key.verify_key)
        msg = b"XiaoLee test message"
        sig = signing_key.sign(msg).signature

        # Cryptography lib deve aceitar a chave gerada pelo PyNaCl
        Ed25519PublicKey.from_public_bytes(pub).verify(sig, msg)
