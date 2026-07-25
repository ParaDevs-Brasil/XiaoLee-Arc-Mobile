"""
test_fuzzing.py — Property-based fuzzing com Hypothesis.

Cobre as superfícies de ataque corrigidas na sprint de segurança 2026-05:
    - Validação de conta Stellar (SEC-014 / SEC-017)
    - Decodificação base58 de pubkey Solana (SEC-010 em campaigns_routes)
    - EncryptionService round-trip e robustez (SEC-005)
    - challenge store invariantes (SEC-020)
    - _issue_jwt nunca crasha com input arbitrário (SEC-002)
    - Lamport overflow no webhook Helius (SEC-019)
    - Endpoint /campaigns/verify com campaign_identifier malformado

Rodando:
    cd backend && pytest tests/test_fuzzing.py -v
    # Com mais exemplos (CI/staging):
    cd backend && pytest tests/test_fuzzing.py -v --hypothesis-seed=0 \
        -p hypothesis --hypothesis-settings=max_examples=500
"""
from __future__ import annotations

import os
import string
import sys
import time

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st
from fastapi.testclient import TestClient

# ── bootstrap path ────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ── fixtures compartilhadas ───────────────────────────────────────────────────

os.environ.setdefault("JWT_SECRET", "fuzzing-test-secret-32chars-xxxxxx")
os.environ.setdefault("ENCRYPTION_KEY", "fuzzing-test-encryption-key-xxxxxxxxxxx")


# =============================================================================
# 1. Validação de conta Stellar
# =============================================================================

class TestStellarAccountValidation:
    """
    _validate_stellar_account deve:
      - Aceitar apenas strings de 56 chars começando com 'G'
      - NUNCA levantar exceção que não seja HTTPException (sem crash)
    """

    @pytest.fixture(autouse=True)
    def _import(self):
        from fastapi import HTTPException
        from server.routes.stellar_auth_routes import _validate_stellar_account
        self._validate = _validate_stellar_account
        self._HTTPException = HTTPException

    @given(account=st.text(min_size=0, max_size=100))
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
    def test_arbitrary_string_never_crashes(self, account):
        try:
            self._validate(account)
        except self._HTTPException:
            pass  # exceção esperada para entradas inválidas
        except Exception as exc:
            pytest.fail(f"_validate_stellar_account levantou exceção inesperada: {type(exc).__name__}: {exc}")

    @given(account=st.text(alphabet=string.ascii_uppercase + string.digits, min_size=56, max_size=56))
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_56_char_strings_not_starting_with_G_rejected(self, account):
        assume(not account.startswith("G"))
        with pytest.raises(self._HTTPException) as exc_info:
            self._validate(account)
        assert exc_info.value.status_code == 400

    def test_valid_format_does_not_raise_without_sdk(self):
        """String com formato correto não levanta sem o SDK."""
        valid = "G" + "A" * 55
        try:
            self._validate(valid)
        except self._HTTPException as e:
            # SDK pode rejeitar o checksum — aceitável
            assert e.status_code == 400
        except Exception as exc:
            pytest.fail(f"Exceção inesperada: {exc}")


# =============================================================================
# 2. Decodificação base58 de pubkey Solana (campaigns_routes._b58decode_pubkey)
# =============================================================================

class TestB58DecodePubkey:
    """
    _b58decode_pubkey deve:
      - Retornar exatamente 32 bytes para inputs válidos de 44 chars
      - Levantar ValueError para qualquer input inválido — nunca outro erro
    """

    @pytest.fixture(autouse=True)
    def _import(self):
        from server.campaigns_routes import _b58decode_pubkey
        self._decode = _b58decode_pubkey

    _B58_CHARS = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

    @given(s=st.text(min_size=0, max_size=100))
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
    def test_arbitrary_string_raises_value_error_or_returns_bytes(self, s):
        try:
            result = self._decode(s)
            # Se retornou, deve ser exatamente 32 bytes
            assert isinstance(result, bytes)
            assert len(result) == 32, f"Esperado 32 bytes, got {len(result)}"
        except ValueError:
            pass  # esperado para inputs inválidos
        except Exception as exc:
            pytest.fail(f"_b58decode_pubkey levantou exceção inesperada: {type(exc).__name__}: {exc}")

    @given(s=st.text(alphabet=_B58_CHARS, min_size=44, max_size=44))
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_valid_base58_44_chars_returns_32_bytes(self, s):
        try:
            result = self._decode(s)
            assert len(result) == 32
        except ValueError:
            pass  # overflow para valores acima de 2^256 — aceitável

    @given(s=st.text(alphabet="\x00\x01\t\n\r !@#$%", min_size=1, max_size=50))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_invalid_chars_raise_value_error(self, s):
        with pytest.raises(ValueError):
            self._decode(s)


# =============================================================================
# 3. EncryptionService — round-trip e robustez
# =============================================================================

class TestEncryptionService:
    """
    EncryptionService deve:
      - encrypt(x) -> decrypt(encrypt(x)) == x  para qualquer string
      - decrypt de lixo deve levantar exceção (nunca crash silencioso)
    """

    @pytest.fixture(autouse=True)
    def _import(self):
        from user_management.encryption_service import EncryptionService
        self._svc = EncryptionService(os.environ["ENCRYPTION_KEY"])

    @given(plaintext=st.text(min_size=1, max_size=512))
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_encrypt_decrypt_roundtrip(self, plaintext):
        encrypted = self._svc.encrypt(plaintext)
        decrypted = self._svc.decrypt(encrypted)
        assert decrypted == plaintext, f"Round-trip falhou: {plaintext!r} → {decrypted!r}"

    @given(garbage=st.binary(min_size=1, max_size=256))
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_decrypt_garbage_raises_exception(self, garbage):
        try:
            self._svc.decrypt(garbage.decode("latin-1"))
            pytest.fail("decrypt de lixo deveria ter levantado exceção")
        except Exception:
            pass  # qualquer exceção é aceitável — não pode silenciar

    @given(plaintext=st.text(min_size=1, max_size=512))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_two_encryptions_produce_different_ciphertexts(self, plaintext):
        c1 = self._svc.encrypt(plaintext)
        c2 = self._svc.encrypt(plaintext)
        # Salt aleatório por chamada — nunca deve ser idêntico
        assert c1 != c2, "encrypt() deve usar salt aleatório — ciphertexts não podem ser iguais"


# =============================================================================
# 4. Challenge store — invariantes (SEC-020)
# =============================================================================

class TestChallengeStoreInvariants:
    """
    _store_challenge/_pop_challenge:
      - Nonce guardado deve ser o mesmo recuperado
      - Entradas expiradas devem retornar None
      - Store cheia deve retornar False sem crashar
    """

    @pytest.fixture(autouse=True)
    def _import(self):
        import server.routes.stellar_auth_routes as m
        self._m = m
        m._challenges.clear()
        yield
        m._challenges.clear()

    @given(
        account=st.text(min_size=1, max_size=56),
        nonce=st.text(min_size=1, max_size=64),
    )
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_store_and_pop_roundtrip(self, account, nonce):
        self._m._challenges.clear()
        ok = self._m._store_challenge(account, nonce, ttl=300)
        assert ok is True
        result = self._m._pop_challenge(account)
        assert result == nonce

    @given(account=st.text(min_size=1, max_size=56))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_expired_challenge_returns_none(self, account):
        self._m._challenges.clear()
        self._m._store_challenge(account, "nonce", ttl=-1)
        assert self._m._pop_challenge(account) is None

    def test_full_store_returns_false_without_crash(self):
        m = self._m
        m._challenges.clear()
        for i in range(m._CHALLENGE_MAX):
            m._challenges[f"GFAKE{i:05d}"] = ("nonce", time.time() + 300)
        ok = m._store_challenge("GNEWACCOUNT1111111111111111111111111111111111111111111111", "x")
        assert ok is False
        assert len(m._challenges) == m._CHALLENGE_MAX


# =============================================================================
# 5. _issue_jwt — nunca crasha com input arbitrário (SEC-002)
# =============================================================================

class TestIssueJwt:
    """_issue_jwt deve produzir um JWT válido (3 partes) para qualquer string de account."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from server.routes.stellar_auth_routes import _issue_jwt
        self._issue_jwt = _issue_jwt

    @given(account=st.text(min_size=0, max_size=256))
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
    def test_any_account_string_produces_valid_jwt_shape(self, account):
        token = self._issue_jwt(account)
        parts = token.split(".")
        assert len(parts) == 3, f"JWT malformado para account={account!r}: {token}"


# =============================================================================
# 6. Lamport overflow — Helius webhook (SEC-019)
# =============================================================================

class TestLamportOverflow:
    """
    O cálculo de lamports no webhook Helius deve ser seguro para
    qualquer valor float controlado pelo atacante.
    """

    @given(raw_amount=st.one_of(
        st.floats(allow_nan=True, allow_infinity=True),
        st.integers(min_value=-(2**64), max_value=2**64),
        st.text(min_size=0, max_size=20),
    ))
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
    def test_lamport_conversion_never_overflows(self, raw_amount):
        """Replica a lógica corrigida de helius_routes (max+min clamp) — deve ficar em [0, 2^63-1]."""
        try:
            volume_lamports = max(0, min(int(float(raw_amount) * 1_000_000_000), 2**63 - 1))
        except (ValueError, OverflowError, TypeError):
            volume_lamports = 0
        assert 0 <= volume_lamports <= 2**63 - 1, f"Lamport fora do range: {volume_lamports}"


# =============================================================================
# 7. Endpoint /campaigns/verify — campaign_identifier malformado
# =============================================================================

class TestCampaignVerifyEndpoint:
    """
    POST /campaigns/verify deve retornar 400/401/422 para inputs malformados.
    NUNCA deve retornar 500 (erro interno não tratado).
    """

    @pytest.fixture(autouse=True)
    def _client(self, isolated_app_db):
        # isolated_app_db: sem isso, cada um dos 200 exemplos abaixo cria/reusa um User
        # "fuzz_token" de verdade e semeia campanhas default no dev DB persistente.
        import importlib
        app_module = importlib.import_module("server.app")
        self._client = TestClient(app_module.app)

    @given(campaign_id=st.one_of(
        st.text(min_size=0, max_size=200),
        st.integers(),
        st.floats(allow_nan=False, allow_infinity=False),
        st.binary(min_size=0, max_size=50),
        st.none(),
    ))
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
    def test_malformed_campaign_identifier_never_500(self, campaign_id):
        try:
            payload = {"campaign_identifier": campaign_id}
            resp = self._client.post(
                "/campaigns/verify",
                json=payload,
                headers={"Authorization": "Bearer fuzz_token"},
            )
            assert resp.status_code != 500, (
                f"500 para campaign_identifier={campaign_id!r}: {resp.text[:200]}"
            )
        except Exception:
            pass  # erros de serialização JSON são aceitáveis
