"""
test_solana_cctp.py — SolanaCCTPClient: sandbox E2E (sem rede) + derivação de PDAs.

Sandbox mode é o caminho testável sem devnet real (mesmo padrão de test_trust_lane.py
para CCTPClient/ArcNativeClient) — as contas/seeds do modo live foram extraídas do
source oficial da Circle (circlefin/solana-cctp-contracts) mas exigem validação contra
uma tx real de devnet antes de habilitar SOLANA_CCTP_ENABLED=true.
"""

from __future__ import annotations

import pytest

from server.integrations.solana_cctp import SolanaCCTPClient, TOKEN_MESSENGER_MINTER_V2


class TestSolanaCCTPClientSandbox:
    @pytest.mark.asyncio
    async def test_burn_usdc_sandbox_returns_deterministic_fake_tx(self):
        client = SolanaCCTPClient(sandbox=True)
        result = await client.burn_usdc(
            amount_usdc=5.0,
            destination_domain=26,
            mint_recipient_bytes32=bytes(32),
        )
        assert result.confirmed is True
        assert result.status == 1
        assert "sandbox" in result.tx_hash

    @pytest.mark.asyncio
    async def test_receive_and_mint_sandbox_returns_deterministic_fake_tx(self):
        client = SolanaCCTPClient(sandbox=True)
        result = await client.receive_and_mint(
            raw_message=bytes(116),
            attestation=bytes(65),
            recipient_owner_b58="11111111111111111111111111111111",
            source_domain=26,
            burn_token_bytes_32=bytes(32),
        )
        assert result.confirmed is True
        assert "sandbox" in result.tx_hash

    @pytest.mark.asyncio
    async def test_get_usdc_balance_sandbox_no_network_call(self):
        client = SolanaCCTPClient(sandbox=True)
        balance = await client.get_usdc_balance()
        assert balance == 1000.0

    @pytest.mark.asyncio
    async def test_healthcheck_sandbox(self):
        client = SolanaCCTPClient(sandbox=True)
        health = await client.healthcheck()
        assert health["ok"] is True
        assert health["sandbox"] is True

    def test_address_sandbox_without_keypair(self):
        client = SolanaCCTPClient(sandbox=True)
        assert client.address == "SANDBOX_SOLANA_CCTP_TREASURY"


class TestSolanaCCTPPdaDerivation:
    """PDAs não dependem de rede — só de solders + program id, testáveis diretamente.
    Seeds conferidos contra o source oficial da Circle (não são valores arbitrários)."""

    def test_derive_token_messenger_is_deterministic(self):
        client = SolanaCCTPClient(sandbox=True)
        pda_1 = client.derive_token_messenger()
        pda_2 = client.derive_token_messenger()
        assert str(pda_1) == str(pda_2)

    def test_derive_remote_token_messenger_differs_per_domain(self):
        client = SolanaCCTPClient(sandbox=True)
        pda_arc = client.derive_remote_token_messenger(26)
        pda_eth = client.derive_remote_token_messenger(0)
        assert str(pda_arc) != str(pda_eth)

    def test_derive_local_token_differs_per_mint(self):
        from solders.pubkey import Pubkey

        client = SolanaCCTPClient(sandbox=True)
        mint_a = Pubkey.from_string("4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU")
        mint_b = Pubkey.from_string("11111111111111111111111111111111")
        assert str(client.derive_local_token(mint_a)) != str(client.derive_local_token(mint_b))

    def test_derive_associated_token_address_deterministic(self):
        from solders.pubkey import Pubkey

        client = SolanaCCTPClient(sandbox=True)
        owner = Pubkey.from_string("11111111111111111111111111111111")
        mint = Pubkey.from_string("4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU")
        ata_1 = client.derive_associated_token_address(owner, mint)
        ata_2 = client.derive_associated_token_address(owner, mint)
        assert str(ata_1) == str(ata_2)

    def test_default_program_ids_match_confirmed_circle_addresses(self):
        client = SolanaCCTPClient(sandbox=True)
        assert client.tmm_program == TOKEN_MESSENGER_MINTER_V2


class TestSolanaCCTPLiveGuards:
    @pytest.mark.asyncio
    async def test_burn_without_treasury_keypair_raises_runtime_error(self, monkeypatch):
        # O construtor cai pro env var quando o arg é vazio — remover do ambiente
        # garante que o guard dispara ANTES de qualquer chamada de rede, mesmo com a
        # tesouraria real configurada no .env da máquina de dev.
        monkeypatch.delenv("SOLANA_TREASURY_KEYPAIR_B58", raising=False)
        client = SolanaCCTPClient(sandbox=False, treasury_keypair_b58="")
        with pytest.raises(RuntimeError, match="SOLANA_TREASURY_KEYPAIR_B58"):
            await client.burn_usdc(amount_usdc=1.0, destination_domain=26, mint_recipient_bytes32=bytes(32))
