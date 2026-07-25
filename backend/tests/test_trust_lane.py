"""
test_trust_lane.py — Testes da f0ntz trust lane (PQC + Arc nativo + CCTP).

Cobertura:
  1. PQCReceipt         — sign, verify, tamper, fallback sem dilithium
  2. ArcNativeClient    — sandbox: transfer, balance, receiveMessage, healthcheck
  3. CCTPClient         — sandbox bridge, extração de MessageSent, config guard
  4. Trust routes       — GET /v1/trust/public-key, POST verify-receipt, healthcheck
  5. PaymentIntent PQC  — coluna receipt_pqc no banco, update pelo repository
  6. creator_pay_tools  — recibo ML-DSA-87 gerado no pagamento; idempotência

Deps opcionais:
  dilithium-py → testes PQC reais são *skippados* se não instalado
  eth-abi      → teste de extração MessageSent é *skippado* se não instalado
  web3         → idem

Rodar:
    cd backend && ../.venv/bin/pytest tests/test_trust_lane.py -v
"""

from __future__ import annotations

import asyncio
import base64
import json
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Campaign, PaymentIntent
from database.repository import DatabaseRepository
from server.integrations.arc_client import ArcClient
from server.integrations.arc_native import ArcNativeClient, TxResult
from server.integrations.cctp_client import BridgeState, BridgeStep, CCTPClient
from server.routes.trust_routes import router as trust_router


# ─── App mínimo para testar as rotas sem carregar o servidor inteiro ──────
_app = FastAPI()
_app.include_router(trust_router)
_trust_client = TestClient(_app)


# ─── Helpers ──────────────────────────────────────────────────────────────

def _make_campaign(db_session) -> Campaign:
    c = Campaign(
        creator_twitter_user_id="pqc_test_creator",
        name="PQC Test Campaign",
        description="test",
        campaign_type="social",
        reward_token="USDC",
        reward_per_participant=5.0,
        max_participants=10,
        reward_pool=50.0,
        status="active",
    )
    db_session.add(c)
    return c


# ===========================================================================
# 1. PQCReceipt
# ===========================================================================


class TestPQCReceipt:
    """
    Testa a assinatura e verificação ML-DSA-87 dos recibos de pagamento.
    Se dilithium-py não estiver instalado, os testes de criptografia são
    skippados automaticamente — o fallback para intent_id é testado sem ele.
    """

    def test_sign_returns_dot_separated_string(self):
        """sign_receipt deve retornar 'A.B' onde A e B são base64 válidos."""
        from services.pqc_receipt import sign_receipt

        result = sign_receipt("intent-123", "0xABC", 5.0, "0xTX")
        # Formato válido: "<sig_b64>.<payload_b64>" OU fallback (intent_id, sem ponto)
        if "." in result:
            sig_b64, payload_b64 = result.split(".", 1)
            # Deve ser decodificável como base64
            base64.b64decode(sig_b64)
            base64.b64decode(payload_b64)
        else:
            # Fallback: dilithium não instalado — retornou intent_id
            assert result == "intent-123"

    def test_sign_fallback_when_dilithium_missing(self, monkeypatch):
        """Se dilithium falhar, sign_receipt deve retornar intent_id (nunca raise)."""
        import services.pqc_receipt as mod

        # Força _load_keypair a falhar
        monkeypatch.setattr(mod, "_load_keypair", lambda: (_ for _ in ()).throw(RuntimeError("mocked")))

        result = mod.sign_receipt("fallback-id", "0xADDR", 1.0, "0xTXHASH")
        assert result == "fallback-id"

    def test_canonical_payload_is_deterministic(self):
        """Mesmo input deve sempre produzir o mesmo payload canônico."""
        from services.pqc_receipt import _canonical

        p1 = _canonical("id-1", "0xabc", 5.0, "0xtx", ts=1719000000)
        p2 = _canonical("id-1", "0xabc", 5.0, "0xtx", ts=1719000000)
        assert p1 == p2

    def test_canonical_payload_has_sorted_keys(self):
        """O payload canônico deve ter chaves ordenadas (JSON determinístico)."""
        from services.pqc_receipt import _canonical

        payload_bytes = _canonical("id-1", "0xABC", 5.0, "0xTX", ts=1719000000)
        d = json.loads(payload_bytes)
        # O campo 'to' deve ser lowercase
        assert d["to"] == "0xabc"
        assert d["arc_tx_hash"] == "0xtx"
        assert d["v"] == 1
        assert d["algo"] == "ML-DSA-87"
        assert d["amount_usdc"] == "5.000000"

    def test_verify_wrong_format_no_dot(self):
        """verify_receipt com formato errado deve retornar valid=False."""
        from services.pqc_receipt import verify_receipt

        result = verify_receipt("INVALIDSIGNATURE_NO_DOT")
        assert result["valid"] is False
        assert result["error"] is not None

    def test_verify_invalid_base64(self):
        """Partes que não são base64 válido devem retornar valid=False."""
        from services.pqc_receipt import verify_receipt

        result = verify_receipt("!!not_base64!!.!!also_not!!")
        assert result["valid"] is False

    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("dilithium_py"),
        reason="dilithium-py não instalado",
    )
    def test_sign_and_verify_roundtrip(self):
        """Assinar e verificar com a mesma key deve retornar valid=True."""
        from services.pqc_receipt import sign_receipt, verify_receipt

        intent_id   = str(uuid.uuid4())
        receipt_pqc = sign_receipt(intent_id, "0xRecipient", 3.14, "0xTxHash1234")

        # Deve ter sido assinado de verdade (não fallback)
        assert "." in receipt_pqc, "Esperava assinatura ML-DSA-87, não fallback"

        result = verify_receipt(receipt_pqc)
        assert result["valid"] is True
        assert result["payload"]["intent_id"] == intent_id
        assert result["payload"]["amount_usdc"] == "3.140000"
        assert result["algo"] == "ML-DSA-87"

    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("dilithium_py"),
        reason="dilithium-py não instalado",
    )
    def test_verify_tampered_payload_fails(self):
        """Alterar o payload após assinar deve invalidar a assinatura."""
        from services.pqc_receipt import sign_receipt, verify_receipt

        receipt_pqc = sign_receipt("id-2", "0xRec", 5.0, "0xTxA")
        assert "." in receipt_pqc

        sig_b64, payload_b64 = receipt_pqc.split(".", 1)
        # Decode → tamper → re-encode
        payload = json.loads(base64.b64decode(payload_b64))
        payload["amount_usdc"] = "99999.000000"  # tamper!
        tampered_payload_b64 = base64.b64encode(json.dumps(payload, sort_keys=True).encode()).decode()

        tampered = f"{sig_b64}.{tampered_payload_b64}"
        result = verify_receipt(tampered)
        assert result["valid"] is False

    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("dilithium_py"),
        reason="dilithium-py não instalado",
    )
    def test_public_key_b64_is_valid_base64(self):
        """A public key deve ser base64 com tamanho correto (ML-DSA-87: 2592 bytes)."""
        from services.pqc_receipt import public_key_b64

        pk_b64 = public_key_b64()
        pk_bytes = base64.b64decode(pk_b64)
        assert len(pk_bytes) == 2592, f"ML-DSA-87 pk deve ter 2592 bytes, got {len(pk_bytes)}"


# ===========================================================================
# 2. ArcNativeClient
# ===========================================================================


class TestArcNativeClient:
    """
    ArcNativeClient em modo sandbox — sem RPC real, sem chave privada.
    Todos os métodos devem funcionar e retornar valores fake coerentes.
    """

    @pytest.mark.asyncio
    async def test_sandbox_send_usdc_returns_tx_result(self):
        """Em sandbox, send_usdc deve retornar TxResult com confirmed=True."""
        arc = ArcNativeClient(sandbox=True)
        result = await arc.send_usdc("0xRecipient", 5.0, "key-abc")

        assert isinstance(result, TxResult)
        assert result.confirmed is True
        assert result.status == 1
        assert "sandbox_native_tx_" in result.tx_hash

    @pytest.mark.asyncio
    async def test_sandbox_balance_returns_1000(self):
        """Em sandbox, saldo USDC on-chain é sempre 1000.0 (dummy)."""
        arc = ArcNativeClient(sandbox=True)
        balance = await arc.get_usdc_balance()
        assert balance == 1000.0

    @pytest.mark.asyncio
    async def test_sandbox_receive_cctp_message(self):
        """Em sandbox, receiveMessage retorna TxResult confirmado."""
        arc = ArcNativeClient(sandbox=True)
        result = await arc.receive_cctp_message(
            msg_transmitter="0xMsgTransmitter",
            raw_message=bytes(range(8)),
            attestation=b"\x01\x02",
        )
        assert result.confirmed is True
        assert "sandbox_cctp_receive_" in result.tx_hash

    @pytest.mark.asyncio
    async def test_sandbox_healthcheck_returns_ok(self):
        """Healthcheck em sandbox deve retornar ok=True sem chamar RPC."""
        arc = ArcNativeClient(sandbox=True)
        h = await arc.healthcheck()
        assert h["ok"] is True
        assert h["sandbox"] is True

    def test_sandbox_address(self):
        """Em sandbox, o endereço é um placeholder, não uma chave derivada."""
        arc = ArcNativeClient(sandbox=True)
        assert arc.address.startswith("0x")

    def test_missing_rpc_raises_runtime_error(self, monkeypatch):
        """Sem ARC_RPC_URL (env isolado), _web3() deve lançar RuntimeError."""
        monkeypatch.delenv("ARC_RPC_URL", raising=False)
        arc = ArcNativeClient(rpc_url="", sandbox=False)
        with pytest.raises(RuntimeError):
            arc._web3()

    def test_missing_private_key_raises_runtime_error(self, monkeypatch):
        """Sem ARC_AGENT_PRIVATE_KEY (env isolado), _account() deve lançar RuntimeError."""
        monkeypatch.delenv("ARC_AGENT_PRIVATE_KEY", raising=False)
        arc = ArcNativeClient(private_key="", sandbox=False)
        with pytest.raises(RuntimeError):
            arc._account()


# ===========================================================================
# 3. CCTPClient
# ===========================================================================


class TestCCTPClient:
    """
    CCTPClient: bridge Sepolia → Arc via CCTP v2.
    O bug crítico corrigido (raw_message ≠ message_hash) é validado pelo
    teste de extração do evento MessageSent.
    """

    @pytest.mark.asyncio
    async def test_sandbox_bridge_returns_both_tx_hashes(self):
        """Em sandbox, bridge_usdc_to_arc retorna source_tx_hash e arc_tx_hash."""
        cctp = CCTPClient(sandbox=True)
        result = await cctp.bridge_usdc_to_arc(10.0, "0xRecipientOnArc")

        assert result.source_tx_hash
        assert result.arc_tx_hash
        assert result.amount_usdc == 10.0
        assert result.recipient == "0xRecipientOnArc"
        assert result.sandbox is True

    @pytest.mark.asyncio
    async def test_sandbox_bridge_different_recipients_different_hashes(self):
        """Dois bridges para endereços diferentes devem ter hashes distintos."""
        cctp = CCTPClient(sandbox=True)
        r1 = await cctp.bridge_usdc_to_arc(1.0, "0xAAAAAAAA")
        r2 = await cctp.bridge_usdc_to_arc(1.0, "0xBBBBBBBB")
        assert r1.source_tx_hash != r2.source_tx_hash

    def test_bridge_state_default_is_pending(self):
        """BridgeState inicial deve estar em PENDING."""
        state = BridgeState(amount_usdc=5.0, recipient="0xABC")
        assert state.step == BridgeStep.PENDING
        assert state.raw_message == b""
        assert state.attestation == b""

    def test_validate_config_raises_on_missing_rpc(self):
        """validate_config deve listar variáveis faltando e levantar RuntimeError."""
        cctp = CCTPClient(source_rpc="", arc_rpc="", signer_key="", sandbox=False)
        with pytest.raises(RuntimeError, match="variáveis faltando"):
            cctp._validate_config()

    def test_validate_config_passes_when_all_set(self):
        """validate_config não deve levantar quando todas as vars estão presentes."""
        cctp = CCTPClient(
            source_rpc="http://fake-rpc",
            arc_rpc="http://fake-arc-rpc",
            signer_key="0x" + "a" * 64,
            arc_key="0x" + "b" * 64,
            sandbox=False,
        )
        cctp._validate_config()  # não deve lançar

    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("eth_abi")
        or not __import__("importlib").util.find_spec("web3"),
        reason="eth_abi ou web3 não instalados",
    )
    def test_extract_message_from_receipt_correct_raw_message(self):
        """
        _extract_message_from_receipt deve retornar os bytes ORIGINAIS do
        evento MessageSent — NÃO keccak256(raw_message).

        Este teste valida o bug crítico corrigido: a versão antiga passava
        message_hash (32 bytes) ao receiveMessage(), o que sempre reverte.
        """
        import eth_abi
        from web3 import Web3

        from server.integrations.cctp_client import (
            CCTPClient,
            _MESSAGE_SENT_TOPIC,
        )

        # Mensagem de teste com conteúdo reconhecível
        raw_message = b"XiaoLee Arc CCTP test message " + bytes(range(32))

        # Simula o ABI encoding do evento MessageSent(bytes message)
        encoded_data = eth_abi.encode(["bytes"], [raw_message])

        # Monta um receipt sintético com o tópico correto
        topic_bytes = bytes.fromhex(_MESSAGE_SENT_TOPIC[2:])
        fake_receipt = {
            "logs": [
                {
                    "topics": [topic_bytes],
                    "data": encoded_data,
                }
            ]
        }

        w3 = Web3()
        extracted_raw, extracted_hash = CCTPClient._extract_message_from_receipt(w3, fake_receipt)

        # A mensagem extraída DEVE ser os bytes originais
        assert extracted_raw == raw_message, (
            "raw_message extraído difere do original — bug de extração"
        )

        # O hash DEVE ser keccak256(raw_message) — diferente do raw_message
        expected_hash = w3.keccak(raw_message).hex()
        assert extracted_hash == expected_hash

        # Garantia de que os dois são DIFERENTES (o bug era confundir os dois)
        assert extracted_raw != extracted_hash.encode(), (
            "raw_message e message_hash não devem ser iguais — eram iguais na versão bugada"
        )
        assert len(extracted_raw) != 32, (
            f"raw_message não deve ter 32 bytes (seria um hash) — got {len(extracted_raw)}"
        )

    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("eth_abi"),
        reason="eth_abi não instalado",
    )
    def test_extract_message_raises_when_event_not_found(self):
        """Deve lançar RuntimeError se o log do MessageSent não existir no receipt."""
        from web3 import Web3
        from server.integrations.cctp_client import CCTPClient

        fake_receipt = {"logs": []}  # sem o evento
        w3 = Web3()

        with pytest.raises(RuntimeError, match="MessageSent"):
            CCTPClient._extract_message_from_receipt(w3, fake_receipt)


# ===========================================================================
# 4. Trust routes
# ===========================================================================


class TestTrustRoutes:
    """
    Testa os endpoints /v1/trust usando um app FastAPI mínimo.
    Não sobe o servidor completo — apenas o router isolado.
    """

    def test_get_public_key_returns_200_or_503(self):
        """
        GET /v1/trust/public-key deve retornar 200 (dilithium instalado)
        ou 503 (dilithium ausente). Nunca 500.
        """
        resp = _trust_client.get("/v1/trust/public-key")
        assert resp.status_code in (200, 503)

    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("dilithium_py"),
        reason="dilithium-py não instalado",
    )
    def test_get_public_key_returns_200(self):
        """GET /v1/trust/public-key deve retornar 200 com os campos corretos."""
        resp = _trust_client.get("/v1/trust/public-key")
        assert resp.status_code == 200
        data = resp.json()
        assert data["algo"] == "ML-DSA-87"
        assert isinstance(data["public_key_b64"], str)
        assert len(data["public_key_b64"]) > 100

    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("dilithium_py"),
        reason="dilithium-py não instalado",
    )
    def test_get_public_key_is_valid_base64(self):
        """A public key retornada deve ser base64 decodificável."""
        resp = _trust_client.get("/v1/trust/public-key")
        data = resp.json()
        decoded = base64.b64decode(data["public_key_b64"])
        assert len(decoded) > 0

    def test_verify_receipt_wrong_format_returns_422_or_invalid(self):
        """Receipts sem '.' devem retornar valid=False (não 500)."""
        resp = _trust_client.post(
            "/v1/trust/verify-receipt",
            json={"receipt_pqc": "INVALIDSIGNATURE_NO_DOT"},
        )
        assert resp.status_code in (200, 422)
        if resp.status_code == 200:
            assert resp.json()["valid"] is False

    def test_verify_receipt_empty_raises_422(self):
        """receipt_pqc vazio deve falhar na validação do Pydantic (min_length=10)."""
        resp = _trust_client.post(
            "/v1/trust/verify-receipt",
            json={"receipt_pqc": "short"},
        )
        assert resp.status_code == 422

    def test_trust_healthcheck_returns_200(self):
        """GET /v1/trust/healthcheck deve retornar 200 com campo ok (True se dilithium instalado)."""
        resp = _trust_client.get("/v1/trust/healthcheck")
        assert resp.status_code == 200
        data = resp.json()
        assert "ok" in data
        # ok=True se dilithium instalado; ok=False se não (mas nunca 500)
        dilithium_available = bool(__import__("importlib").util.find_spec("dilithium_py"))
        if dilithium_available:
            assert data["ok"] is True
            assert data["algo"] == "ML-DSA-87"

    @pytest.mark.skipif(
        not __import__("importlib").util.find_spec("dilithium_py"),
        reason="dilithium-py não instalado",
    )
    def test_verify_receipt_valid_roundtrip_via_http(self):
        """Assinar localmente e verificar via endpoint deve retornar valid=True."""
        from services.pqc_receipt import sign_receipt

        intent_id   = str(uuid.uuid4())
        receipt_pqc = sign_receipt(intent_id, "0xCreator", 5.0, "0xTxHash999")

        if "." not in receipt_pqc:
            pytest.skip("sign_receipt retornou fallback — dilithium pode estar com problema")

        resp = _trust_client.post(
            "/v1/trust/verify-receipt",
            json={"receipt_pqc": receipt_pqc},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["payload"]["intent_id"] == intent_id


# ===========================================================================
# 5. PaymentIntent — coluna receipt_pqc no banco
# ===========================================================================


class TestPaymentIntentPQC:
    """
    Garante que a coluna receipt_pqc existe no modelo e é persistida
    corretamente pelo repository.update_payment_intent().
    """

    @pytest.mark.asyncio
    async def test_model_has_receipt_pqc_field(self, db_session: AsyncSession):
        """PaymentIntent deve ter o atributo receipt_pqc."""
        campaign = _make_campaign(db_session)
        await db_session.flush()

        intent = PaymentIntent(
            intent_id=str(uuid.uuid4()),
            campaign_id=campaign.id,
            creator_id="@pqc_test",
            amount_usdc=5.0,
            status="pending",
            receipt_pqc="test_receipt_pqc_value",
        )
        db_session.add(intent)
        await db_session.commit()
        await db_session.refresh(intent)

        assert intent.receipt_pqc == "test_receipt_pqc_value"

    @pytest.mark.asyncio
    async def test_repository_stores_receipt_pqc_on_update(self, db_session: AsyncSession):
        """update_payment_intent deve persistir receipt_pqc no banco."""
        campaign = _make_campaign(db_session)
        await db_session.flush()

        repo      = DatabaseRepository(db_session)
        intent_id = str(uuid.uuid4())

        await repo.create_payment_intent(intent_id, campaign.id, "@creator_pqc", 5.0)

        pqc_value = "fake_sig_b64.fake_payload_b64"
        await repo.update_payment_intent(
            intent_id,
            status="submitted",
            tx_hash="0xTestTx",
            receipt_pqc=pqc_value,
        )

        stored = await repo.get_payment_intent(intent_id)
        assert stored is not None
        assert stored.status == "submitted"
        assert stored.arc_tx_hash == "0xTestTx"
        assert stored.receipt_pqc == pqc_value

    @pytest.mark.asyncio
    async def test_receipt_pqc_is_null_when_not_set(self, db_session: AsyncSession):
        """PaymentIntent sem receipt_pqc deve ter None (nullable)."""
        campaign = _make_campaign(db_session)
        await db_session.flush()

        intent = PaymentIntent(
            intent_id=str(uuid.uuid4()),
            campaign_id=campaign.id,
            creator_id="@no_pqc",
            amount_usdc=1.0,
            status="pending",
        )
        db_session.add(intent)
        await db_session.commit()
        await db_session.refresh(intent)

        assert intent.receipt_pqc is None

    @pytest.mark.asyncio
    async def test_update_without_receipt_pqc_does_not_clear_it(self, db_session: AsyncSession):
        """update_payment_intent sem receipt_pqc não deve apagar o valor existente."""
        campaign = _make_campaign(db_session)
        await db_session.flush()

        repo      = DatabaseRepository(db_session)
        intent_id = str(uuid.uuid4())

        await repo.create_payment_intent(intent_id, campaign.id, "@creator2", 5.0)
        await repo.update_payment_intent(
            intent_id, status="submitted",
            tx_hash="0xTxFirst", receipt_pqc="original_pqc",
        )

        # Segunda update SEM receipt_pqc — não deve apagar
        await repo.update_payment_intent(intent_id, status="confirmed")

        stored = await repo.get_payment_intent(intent_id)
        assert stored.receipt_pqc == "original_pqc"


# ===========================================================================
# 6. creator_pay_tools — PQC no fluxo de pagamento
# ===========================================================================


class TestCreatorPayToolsPQC:
    """
    Testa que o recibo PQC é gerado e retornado no fluxo de pagamento,
    e que duplicatas retornam o recibo já armazenado no banco.
    """

    @pytest.mark.asyncio
    async def test_payment_returns_receipt_pqc_field(self, db_session: AsyncSession):
        """pay_creator_nanopayment deve retornar receipt_pqc (assinado ou fallback)."""
        from ai.agents.creator_pay_tools import make_tool_executors

        campaign = _make_campaign(db_session)
        await db_session.flush()

        arc    = ArcClient(sandbox=True)
        repo   = DatabaseRepository(db_session)
        tools  = make_tool_executors(repo, arc, campaign.id, 50.0, 5.0)
        pay_fn = tools["pay_creator_nanopayment"]

        intent_id = str(uuid.uuid4())
        result = await pay_fn(
            {"intent_id": intent_id, "to": "0xCreatorAddr", "amount_usdc": 5.0},
            {},
        )

        assert "receipt_pqc" in result
        assert result["receipt_pqc"]  # não vazio
        # O campo nunca deve ser None ou empty string
        assert isinstance(result["receipt_pqc"], str)
        assert len(result["receipt_pqc"]) > 5

    @pytest.mark.asyncio
    async def test_payment_tx_and_receipt_pqc_are_consistent(self, db_session: AsyncSession):
        """O tx_hash e receipt_pqc devem vir juntos e o intent deve estar no banco."""
        from ai.agents.creator_pay_tools import make_tool_executors

        campaign = _make_campaign(db_session)
        await db_session.flush()

        arc   = ArcClient(sandbox=True)
        repo  = DatabaseRepository(db_session)
        tools = make_tool_executors(repo, arc, campaign.id, 50.0, 5.0)

        intent_id = str(uuid.uuid4())
        result = await tools["pay_creator_nanopayment"](
            {"intent_id": intent_id, "to": "0xAddrB", "amount_usdc": 5.0},
            {},
        )

        # Verificar que o intent foi salvo no banco com o receipt_pqc
        stored = await repo.get_payment_intent(intent_id)
        assert stored is not None
        assert stored.status == "submitted"
        assert stored.arc_tx_hash == result["tx"]
        # receipt_pqc no banco deve bater com o retornado na resposta
        assert stored.receipt_pqc == result["receipt_pqc"]

    @pytest.mark.asyncio
    async def test_duplicate_intent_returns_stored_receipt_pqc(self, db_session: AsyncSession):
        """Segundo pagamento com mesmo intent_id deve retornar o receipt_pqc do banco."""
        from ai.agents.creator_pay_tools import make_tool_executors

        campaign = _make_campaign(db_session)
        await db_session.flush()

        arc   = ArcClient(sandbox=True)
        repo  = DatabaseRepository(db_session)
        tools = make_tool_executors(repo, arc, campaign.id, 50.0, 5.0)

        intent_id = str(uuid.uuid4())
        inputs = {"intent_id": intent_id, "to": "0xDuplicateAddr", "amount_usdc": 5.0}

        # Primeiro pagamento
        first = await tools["pay_creator_nanopayment"](inputs, {})
        assert "error" not in first, f"Primeiro pagamento falhou: {first}"
        first_receipt = first["receipt_pqc"]

        # Segundo pagamento — idempotência
        second = await tools["pay_creator_nanopayment"](inputs, {})
        assert second.get("duplicate") is True
        # Deve retornar o mesmo recibo armazenado
        assert second["receipt_pqc"] == first_receipt

    @pytest.mark.asyncio
    async def test_insufficient_budget_returns_error(self, db_session: AsyncSession):
        """Tentar pagar mais que o budget deve retornar budget_exhausted=True."""
        from ai.agents.creator_pay_tools import make_tool_executors

        campaign = _make_campaign(db_session)
        await db_session.flush()

        arc   = ArcClient(sandbox=True)
        repo  = DatabaseRepository(db_session)
        # Budget de 3 USDC, mas tentamos pagar 5
        tools = make_tool_executors(repo, arc, campaign.id, 3.0, 5.0)

        result = await tools["pay_creator_nanopayment"](
            {"intent_id": str(uuid.uuid4()), "to": "0xAddr", "amount_usdc": 5.0},
            {},
        )

        assert result.get("error") == "insufficient_budget"
        assert result.get("budget_exhausted") is True
