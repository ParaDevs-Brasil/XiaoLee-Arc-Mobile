"""
Batch 2/N — fuzzing com Hypothesis do caminho de tração (POST /v1/payments/settled)
e do recibo pós-quântico (services/pqc_receipt.py — ML-DSA-87).

Segue a mesma convenção de tests/test_fuzzing.py (sprint de segurança 2026-05):
classes por superfície, @given + @settings(suppress_health_check=[HealthCheck.too_slow]).

Nota de performance: ML-DSA-87 (dilithium-py, pure-Python) leva ~0.3-0.4s por
assinatura — os testes que assinam de verdade usam max_examples baixo (5-8) de
propósito, os que só verificam/parseiam (sem assinar) usam mais exemplos.
"""
from __future__ import annotations

import importlib

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
from fastapi.testclient import TestClient

app_module = importlib.import_module("server.app")


# =============================================================================
# 1. POST /v1/payments/settled — nunca 500 pra input arbitrário
# =============================================================================

class TestPaymentSettledEndpointFuzzing:
    """O endpoint público de settlement precisa devolver 422 (validação) ou 200,
    nunca 500, pra qualquer JSON malformado que um cliente adversarial mande."""

    @pytest.fixture(autouse=True)
    def _client(self, isolated_app_db):
        # isolated_app_db: sem isso, os 150+200 exemplos do Hypothesis abaixo escrevem
        # direto em backend/xiao_lee.db (o dev DB de verdade) via settled_payments —
        # foi assim que a tabela acumulou lixo (unicode aleatorio, amounts absurdos).
        self._client = TestClient(app_module.app, raise_server_exceptions=False)
        original_secret = app_module.settings.arc_payment_secret
        object.__setattr__(app_module.settings, "arc_payment_secret", "")
        yield
        object.__setattr__(app_module.settings, "arc_payment_secret", original_secret)

    @given(
        intent_id=st.one_of(st.text(max_size=200), st.integers(), st.none()),
        amount=st.one_of(
            st.floats(allow_nan=True, allow_infinity=True),
            st.text(max_size=20),
            st.integers(),
            st.none(),
            st.booleans(),
        ),
        creator=st.one_of(st.text(max_size=200), st.integers(), st.none()),
        tx=st.one_of(st.text(max_size=200), st.integers(), st.none()),
    )
    @settings(max_examples=150, suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
    def test_arbitrary_payload_never_500(self, intent_id, amount, creator, tx):
        try:
            resp = self._client.post(
                "/v1/payments/settled",
                json={"intent_id": intent_id, "amount": amount, "creator": creator, "tx": tx},
            )
        except ValueError:
            return  # NaN/Infinity que o próprio httpx recusa serializar — não chega a sair
        assert resp.status_code != 500, f"500 para payload intent_id={intent_id!r} amount={amount!r}: {resp.text[:200]}"

    @given(extra_fields=st.dictionaries(st.text(max_size=30), st.text(max_size=100), max_size=10))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
    def test_extra_unknown_fields_never_500(self, extra_fields):
        """Campos extras não declarados no schema devem ser ignorados, não crashar."""
        payload = {"intent_id": "x", "amount": 0.1, "creator": "@c", "tx": "0xtx", **extra_fields}
        resp = self._client.post("/v1/payments/settled", json=payload)
        assert resp.status_code != 500


# =============================================================================
# 2. verify_receipt — nunca crasha, nunca aceita lixo como válido
# =============================================================================

class TestPqcVerifyReceiptFuzzing:
    """verify_receipt precisa lidar com QUALQUER string sem levantar exceção —
    é chamado por terceiros verificando recibos publicados, incluindo atacantes."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from services.pqc_receipt import verify_receipt
        self._verify = verify_receipt

    @given(garbage=st.text(max_size=500))
    @settings(max_examples=300, suppress_health_check=[HealthCheck.too_slow])
    def test_arbitrary_string_never_raises_and_never_reports_valid(self, garbage):
        result = self._verify(garbage)
        assert result["valid"] is False
        assert result["error"] is not None

    @given(garbage=st.binary(max_size=300))
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_arbitrary_bytes_as_latin1_never_raises(self, garbage):
        result = self._verify(garbage.decode("latin-1"))
        assert result["valid"] is False

    @given(
        fake_sig=st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=", min_size=1, max_size=200),
        fake_payload=st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=", min_size=1, max_size=200),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_base64_shaped_garbage_never_reports_valid(self, fake_sig, fake_payload):
        """String com a FORMA certa (base64.base64) mas conteúdo aleatório nunca
        pode passar como assinatura válida — testa contra falso positivo."""
        result = self._verify(f"{fake_sig}.{fake_payload}")
        assert result["valid"] is False


# =============================================================================
# 3. sign_receipt / verify_receipt — round-trip real e detecção de adulteração
# =============================================================================

class TestPqcSignVerifyRoundtrip:
    """Assinatura real (ML-DSA-87, ~0.3-0.4s/op) — max_examples baixo de propósito."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from server.settings import settings  # dispara load_dotenv() -> chave persistente
        from services.pqc_receipt import sign_receipt, verify_receipt
        self._sign = sign_receipt
        self._verify = verify_receipt

    @given(
        intent_id=st.text(min_size=1, max_size=64),
        to=st.text(min_size=1, max_size=64),
        amount=st.floats(min_value=0.000001, max_value=1_000_000, allow_nan=False, allow_infinity=False),
        tx=st.text(min_size=1, max_size=80),
    )
    @settings(max_examples=6, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_sign_then_verify_always_valid_for_arbitrary_valid_input(self, intent_id, to, amount, tx):
        receipt = self._sign(intent_id, to, amount, tx)
        result = self._verify(receipt)
        assert result["valid"] is True
        assert result["payload"]["intent_id"] == intent_id

    @given(
        intent_id=st.text(min_size=1, max_size=64),
        amount=st.floats(min_value=0.01, max_value=1000, allow_nan=False, allow_infinity=False),
        flip_position=st.integers(min_value=0, max_value=99),
    )
    @settings(max_examples=6, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_tampering_signature_always_invalidates(self, intent_id, amount, flip_position):
        receipt = self._sign(intent_id, "0xabc", amount, "0xtx")
        sig_b64, payload_b64 = receipt.split(".", 1)

        pos = flip_position % len(sig_b64)
        # troca um char por outro caractere válido de base64 diferente do original
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
        original = sig_b64[pos]
        replacement = next(c for c in alphabet if c != original)
        tampered_sig = sig_b64[:pos] + replacement + sig_b64[pos + 1:]

        result = self._verify(f"{tampered_sig}.{payload_b64}")
        assert result["valid"] is False

    @given(
        intent_id=st.text(min_size=1, max_size=64),
        amount=st.floats(min_value=0.01, max_value=1000, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=6, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_tampering_amount_in_payload_always_invalidates(self, intent_id, amount):
        """Ataque realista: pegar um recibo real e tentar mudar o valor pago mantendo
        a assinatura original — precisa falhar (é isso que a assinatura garante)."""
        receipt = self._sign(intent_id, "0xabc", amount, "0xtx")
        sig_b64, payload_b64 = receipt.split(".", 1)

        import base64
        import json
        payload = json.loads(base64.b64decode(payload_b64))
        payload["amount_usdc"] = "999999.000000"  # atacante tenta inflar o valor
        tampered_payload_b64 = base64.b64encode(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).decode()

        result = self._verify(f"{sig_b64}.{tampered_payload_b64}")
        assert result["valid"] is False


# =============================================================================
# 4. _canonical — formatação determinística do payload assinado
# =============================================================================

class TestPqcCanonicalPayload:
    @pytest.fixture(autouse=True)
    def _import(self):
        from services.pqc_receipt import _canonical
        self._canonical = _canonical

    @given(amount=st.floats(min_value=-1_000_000, max_value=1_000_000, allow_nan=False, allow_infinity=False))
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_amount_always_formatted_with_six_decimals(self, amount):
        import json
        payload = json.loads(self._canonical("i", "0xabc", amount, "0xtx", ts=1000))
        decimals = payload["amount_usdc"].split(".")[-1]
        assert len(decimals) == 6

    @given(
        to=st.text(min_size=0, max_size=100),
        arc_tx_hash=st.text(min_size=0, max_size=100),
    )
    @settings(max_examples=150, suppress_health_check=[HealthCheck.too_slow])
    def test_to_and_tx_hash_always_lowercased(self, to, arc_tx_hash):
        import json
        payload = json.loads(self._canonical("i", to, 1.0, arc_tx_hash, ts=1000))
        assert payload["to"] == to.lower()
        assert payload["arc_tx_hash"] == arc_tx_hash.lower()

    @given(intent_id=st.text(min_size=0, max_size=200))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_arbitrary_intent_id_never_crashes_canonicalization(self, intent_id):
        result = self._canonical(intent_id, "0xabc", 1.0, "0xtx", ts=1000)
        assert isinstance(result, bytes)
