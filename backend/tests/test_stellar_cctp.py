"""
test_stellar_cctp.py — StellarCCTPClient: sandbox E2E (sem rede) + derivação do endereço
Stellar Asset Contract (SAC) do USDC, que não depende de rede (mesmo padrão sandbox-first
de test_trust_lane.py / test_solana_cctp.py).
"""

from __future__ import annotations

import pytest

from server.integrations.stellar_cctp import (
    CCTP_FORWARDER_TESTNET,
    StellarCCTPClient,
    TOKEN_MESSENGER_MINTER_V2_TESTNET,
    build_hook_data,
)


class TestStellarCCTPClientSandbox:
    @pytest.mark.asyncio
    async def test_burn_usdc_sandbox_returns_deterministic_fake_tx(self):
        client = StellarCCTPClient(sandbox=True)
        result = await client.burn_usdc(
            amount_usdc=5.0,
            destination_domain=26,
            mint_recipient_bytes32=bytes(32),
        )
        assert result.confirmed is True
        assert result.status == 1
        assert "sandbox" in result.tx_hash

    @pytest.mark.asyncio
    async def test_mint_and_forward_sandbox_returns_deterministic_fake_tx(self):
        client = StellarCCTPClient(sandbox=True)
        result = await client.mint_and_forward(raw_message=bytes(100), attestation=bytes(65))
        assert result.confirmed is True
        assert "sandbox" in result.tx_hash

    @pytest.mark.asyncio
    async def test_healthcheck_sandbox(self):
        client = StellarCCTPClient(sandbox=True)
        health = await client.healthcheck()
        assert health["ok"] is True
        assert health["sandbox"] is True

    def test_address_sandbox_without_treasury_secret(self):
        client = StellarCCTPClient(sandbox=True)
        assert client.address == "SANDBOX_STELLAR_CCTP_TREASURY"


class TestStellarCCTPUsdcSacAddress:
    """Stellar Asset Contract address é determinístico (asset code+issuer+network passphrase)
    — não depende de rede, testável direto via Asset.contract_id()."""

    def test_usdc_sac_address_is_deterministic(self):
        client = StellarCCTPClient(sandbox=True, network="testnet")
        addr_1 = client._usdc_sac_address()
        addr_2 = client._usdc_sac_address()
        assert addr_1 == addr_2
        assert addr_1.startswith("C")  # contract strkey

    def test_usdc_sac_address_differs_between_networks(self):
        testnet_client = StellarCCTPClient(sandbox=True, network="testnet")
        mainnet_client = StellarCCTPClient(sandbox=True, network="mainnet")
        assert testnet_client._usdc_sac_address() != mainnet_client._usdc_sac_address()

    def test_default_contract_matches_confirmed_circle_address(self):
        client = StellarCCTPClient(sandbox=True)
        assert client.tmm_contract == TOKEN_MESSENGER_MINTER_V2_TESTNET


class TestHookData:
    """Formato v0 do hook_data validado contra o source do CctpForwarder da Circle
    (message_test.rs: magic 24 bytes zero, version/length u32 BIG-endian, strkey UTF-8)."""

    RECIPIENT_G = "GAAXKLIMFWX7XLKVXGUVJI7X533OOZH2YS2RLMQVY3TP5QLXRRWXHDI5"

    def test_layout_matches_forwarder_contract(self):
        hook = build_hook_data(self.RECIPIENT_G)
        strkey_utf8 = self.RECIPIENT_G.encode("utf-8")
        assert hook[0:24] == bytes(24)                                  # magic zerado
        assert hook[24:28] == (0).to_bytes(4, "big")                    # version 0 BE
        assert hook[28:32] == len(strkey_utf8).to_bytes(4, "big")       # length BE
        assert hook[32:] == strkey_utf8                                 # strkey UTF-8
        assert len(hook) == 32 + 56                                     # strkey G tem 56 chars

    def test_accepts_contract_strkey(self):
        hook = build_hook_data(CCTP_FORWARDER_TESTNET)
        assert hook[32:].decode("utf-8") == CCTP_FORWARDER_TESTNET

    def test_invalid_strkey_raises_before_any_burn(self):
        with pytest.raises(ValueError, match="strkey"):
            build_hook_data("GNOT_A_VALID_STRKEY")

    def test_evm_address_raises(self):
        with pytest.raises(ValueError, match="strkey"):
            build_hook_data("0x4D4cE599a800769a22F796E42966c7B0089F6BC3")


class TestForwarderBytes32:
    def test_roundtrips_through_strkey_encode(self):
        from stellar_sdk import StrKey

        client = StellarCCTPClient(sandbox=True)
        raw = client.forwarder_bytes32()
        assert len(raw) == 32
        assert StrKey.encode_contract(raw) == CCTP_FORWARDER_TESTNET


class TestStellarCCTPLiveGuards:
    @pytest.mark.asyncio
    async def test_burn_without_treasury_secret_raises_runtime_error(self, monkeypatch):
        # Mesmo isolamento do teste Solana: sem delenv, uma STELLAR_TREASURY_SECRET real
        # no .env de dev faria este teste tocar a rede live em vez de disparar o guard.
        monkeypatch.delenv("STELLAR_TREASURY_SECRET", raising=False)
        client = StellarCCTPClient(sandbox=False, treasury_secret="")
        with pytest.raises(RuntimeError, match="STELLAR_TREASURY_SECRET"):
            await client.burn_usdc(amount_usdc=1.0, destination_domain=26, mint_recipient_bytes32=bytes(32))

    @pytest.mark.asyncio
    async def test_mint_and_forward_without_treasury_secret_raises_runtime_error(self, monkeypatch):
        monkeypatch.delenv("STELLAR_TREASURY_SECRET", raising=False)
        client = StellarCCTPClient(sandbox=False, treasury_secret="")
        with pytest.raises(RuntimeError, match="STELLAR_TREASURY_SECRET"):
            await client.mint_and_forward(raw_message=bytes(10), attestation=bytes(10))
