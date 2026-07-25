"""
stellar_cctp.py — Circle CCTP V2 real em Stellar (domain 27) via contratos Soroban:
TokenMessengerMinterV2 (burn) + MessageTransmitterV2 + CctpForwarder (mint inbound).

Sem SDK Python oficial da Circle pra Stellar (só @stellar/stellar-sdk em TS) — invocação
feita via stellar-sdk (Python) >= 14, que já suporta Soroban nativamente
(TransactionBuilder.append_invoke_contract_function_op + SorobanServer).

Assinaturas de função extraídas do source real
(github.com/circlefin/stellar-cctp, branch master):
    deposit_for_burn(caller: Address, amount: i128, destination_domain: u32,
                      mint_recipient: BytesN<32>, burn_token: Address,
                      destination_caller: BytesN<32>, max_fee: i128,
                      min_finality_threshold: u32)
        — contracts/token-messenger-minter-v2/src/contract.rs:237
    mint_and_forward(message: Bytes, attestation: Bytes)
        — permissionless (sem require_auth do caller) — contracts/cctp-forwarder/src/contract.rs:140

Contratos Soroban confirmados (testnet, developers.circle.com/cctp/references/stellar-contracts):
    TokenMessengerMinterV2: CDNG7HXAPBWICI2E3AUBP3YZWZELJLYSB6F5CC7WLDTLTHVM74SLRTHP
    MessageTransmitterV2:   CBJ6MTCKKZG73PMDZCJMSFRD7DQEMI4FKDH7CGDSV4W6FHCRBCQAVVJY
    CctpForwarder:          CA66Q2WFBND6V4UEB7RD4SAXSVIWMD6RA4X3U32ELVFGXV5PJK4T4VSZ

ATENÇÃO — regra que não pode ser violada (fundos ficam presos permanentemente, sem
recovery, se errar): para QUALQUER transfer CCTP com Stellar como destino (outra chain
queimando USDC pra mintar aqui), `mint_recipient` e `destination_caller` no depositForBurn
da chain de ORIGEM devem apontar pro contrato CctpForwarder acima — nunca pra conta do
usuário Stellar diretamente. O endereço Stellar real do destinatário vai em `hook_data`
(formato documentado em developers.circle.com/cctp/references/stellar — strkey UTF-8;
montar com build_hook_data() deste módulo). cctp_client.py (EVM) já suporta via
burn_and_attest(hook_data=..., destination_caller_bytes32=forwarder_bytes32());
solana_cctp.py como origem ainda não gera hook_data.

USDC em Stellar tem 7 casas decimais (vs 6 nas outras chains suportadas) — normalização
entre decimais é feita pelo próprio contrato Soroban, não precisa ser replicada aqui.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

from server.integrations.stellar_adapter import usdc_issuer_for

LOG = logging.getLogger(__name__)

TOKEN_MESSENGER_MINTER_V2_TESTNET = "CDNG7HXAPBWICI2E3AUBP3YZWZELJLYSB6F5CC7WLDTLTHVM74SLRTHP"
MESSAGE_TRANSMITTER_V2_TESTNET = "CBJ6MTCKKZG73PMDZCJMSFRD7DQEMI4FKDH7CGDSV4W6FHCRBCQAVVJY"
CCTP_FORWARDER_TESTNET = "CA66Q2WFBND6V4UEB7RD4SAXSVIWMD6RA4X3U32ELVFGXV5PJK4T4VSZ"

STELLAR_CCTP_DOMAIN = 27
USDC_DECIMALS_STELLAR = 7
_FINALITY_THRESHOLD_FINALIZED = 2000

# hook_data v0 do CctpForwarder (contracts/cctp-forwarder/src/message.rs):
# bytes 0-23 magic (zeros) | 24-27 version u32 BE (=0) | 28-31 len u32 BE | 32+ strkey UTF-8
_HOOK_MAGIC = bytes(24)
_HOOK_VERSION = 0


def build_hook_data(recipient_strkey: str) -> bytes:
    """
    Monta o hook_data que o CctpForwarder usa pra encaminhar o mint ao destinatário
    real em Stellar. Endianness big-endian validada contra o source da Circle
    (message_test.rs usa to_be_bytes). Aceita conta (G...), contrato (C...) ou
    muxed (M...) — valida o strkey via SDK antes, porque um strkey inválido só
    falharia DEPOIS do burn na origem, com os fundos já presos no forwarder.
    """
    from stellar_sdk import StrKey

    if recipient_strkey.startswith("G"):
        valid = StrKey.is_valid_ed25519_public_key(recipient_strkey)
    elif recipient_strkey.startswith("C"):
        valid = StrKey.is_valid_contract(recipient_strkey)
    elif recipient_strkey.startswith("M"):
        valid = StrKey.is_valid_med25519_public_key(recipient_strkey)
    else:
        valid = False
    if not valid:
        raise ValueError(f"[stellar_cctp] strkey Stellar inválido pra hook_data: {recipient_strkey!r}")

    recipient_utf8 = recipient_strkey.encode("utf-8")
    return (
        _HOOK_MAGIC
        + _HOOK_VERSION.to_bytes(4, "big")
        + len(recipient_utf8).to_bytes(4, "big")
        + recipient_utf8
    )


@dataclass
class TxResult:
    tx_hash: str
    confirmed: bool
    status: int = 0


class StellarCCTPClient:
    """
    Cliente CCTP V2 real para Stellar via Soroban. Chave de tesouraria DEDICADA — nunca
    reaproveitar STELLAR_SERVER_SECRET (SEP-10, comentário explícito "nunca usado para
    fundos" em settings.py — não violar).
    """

    def __init__(
        self,
        soroban_rpc_url: str = "",
        treasury_secret: str = "",
        network: str = "testnet",
        token_messenger_minter: str = "",
        cctp_forwarder: str = "",
        sandbox: bool = True,
    ):
        self.network = network or os.getenv("STELLAR_NETWORK", "testnet")
        self.soroban_rpc_url = soroban_rpc_url or os.getenv(
            "STELLAR_SOROBAN_RPC_URL",
            "https://soroban-testnet.stellar.org"
            if self.network == "testnet"
            else "https://mainnet.sorobanrpc.com",
        )
        self.treasury_secret = treasury_secret or os.getenv("STELLAR_TREASURY_SECRET", "")
        self.tmm_contract = token_messenger_minter or os.getenv(
            "STELLAR_CCTP_TOKEN_MESSENGER_MINTER", TOKEN_MESSENGER_MINTER_V2_TESTNET
        )
        self.forwarder_contract = cctp_forwarder or os.getenv("STELLAR_CCTP_FORWARDER", CCTP_FORWARDER_TESTNET)
        self.sandbox = sandbox

    @property
    def address(self) -> str:
        if self.sandbox or not self.treasury_secret:
            return "SANDBOX_STELLAR_CCTP_TREASURY"
        from stellar_sdk import Keypair

        return Keypair.from_secret(self.treasury_secret).public_key

    def forwarder_bytes32(self) -> bytes:
        """Endereço do CctpForwarder decodificado do strkey C... pros 32 bytes crus que
        o depositForBurn da chain de ORIGEM espera em mint_recipient/destination_caller
        (transfers com destino Stellar). Determinístico, não toca rede."""
        from stellar_sdk import StrKey

        raw = StrKey.decode_contract(self.forwarder_contract)
        if len(raw) != 32:
            raise ValueError(f"[stellar_cctp] forwarder decodificado com {len(raw)} bytes (esperado 32)")
        return raw

    def _usdc_sac_address(self) -> str:
        """Endereço Soroban (Stellar Asset Contract) do USDC clássico — derivado
        deterministicamente do asset code+issuer via Asset.contract_id(), reaproveitando
        usdc_issuer_for() já usado por stellar_adapter.py."""
        from stellar_sdk import Asset

        network_passphrase = self._network_passphrase()
        asset = Asset("USDC", usdc_issuer_for(self.network))
        return asset.contract_id(network_passphrase)

    def _network_passphrase(self) -> str:
        from stellar_sdk import Network

        return Network.TESTNET_NETWORK_PASSPHRASE if self.network == "testnet" else Network.PUBLIC_NETWORK_PASSPHRASE

    # ------------------------------------------------------------------
    # Burn — Stellar como chain de origem (ex: Stellar -> Arc, funding de campanha)
    # ------------------------------------------------------------------

    async def burn_usdc(
        self,
        amount_usdc: float,
        destination_domain: int,
        mint_recipient_bytes32: bytes,
        destination_caller_bytes32: Optional[bytes] = None,
        max_fee_usdc: float = 0.0,
    ) -> TxResult:
        """
        deposit_for_burn real no TokenMessengerMinterV2 — queima USDC em Stellar e emite
        mensagem CCTP pro domain destino. min_finality_threshold=2000 (finalized, sem taxa
        de fast-transfer — max_fee=0 é válido nesse modo).
        """
        if self.sandbox:
            fake = f"sandbox_stellar_burn_{destination_domain}_{amount_usdc}"
            LOG.info("[stellar_cctp] SANDBOX burn %.4f USDC -> domain=%d | tx=%s", amount_usdc, destination_domain, fake)
            return TxResult(tx_hash=fake, confirmed=True, status=1)

        if not self.treasury_secret:
            raise RuntimeError("[stellar_cctp] STELLAR_TREASURY_SECRET não configurado")

        from stellar_sdk import Keypair, SorobanServer, TransactionBuilder, scval

        kp = Keypair.from_secret(self.treasury_secret)
        server = SorobanServer(self.soroban_rpc_url)

        amount_raw = int(amount_usdc * 10 ** USDC_DECIMALS_STELLAR)
        max_fee_raw = int(max_fee_usdc * 10 ** USDC_DECIMALS_STELLAR)
        dest_caller = destination_caller_bytes32 or bytes(32)

        # O TMM saca o USDC via transfer_from — exige allowance no SAC antes do burn
        # (mesmo padrão approve->depositForBurn do fluxo EVM). Sem isso a simulação
        # falha com "not enough allowance to spend" (Error(Contract, #9)).
        approve_hash = await self._approve_usdc(server, kp, amount_raw + max_fee_raw)
        await self._wait_success(server, approve_hash)
        LOG.info("[stellar_cctp] USDC approve confirmado tx=%s", approve_hash)

        source = server.load_account(kp.public_key)  # sequence pós-approve
        tx = (
            TransactionBuilder(source, self._network_passphrase(), base_fee=10_000)
            .append_invoke_contract_function_op(
                contract_id=self.tmm_contract,
                function_name="deposit_for_burn",
                parameters=[
                    scval.to_address(kp.public_key),
                    scval.to_int128(amount_raw),
                    scval.to_uint32(destination_domain),
                    scval.to_bytes(bytes(mint_recipient_bytes32)),
                    scval.to_address(self._usdc_sac_address()),
                    scval.to_bytes(bytes(dest_caller)),
                    scval.to_int128(max_fee_raw),
                    scval.to_uint32(_FINALITY_THRESHOLD_FINALIZED),
                ],
            )
            .set_timeout(30)
            .build()
        )
        tx_hash = await self._prepare_sign_send(server, tx, kp)
        await self._wait_success(server, tx_hash)
        LOG.info("[stellar_cctp] deposit_for_burn confirmado tx=%s amount=%.4f domain=%d", tx_hash, amount_usdc, destination_domain)
        return TxResult(tx_hash=tx_hash, confirmed=True, status=1)

    # ------------------------------------------------------------------
    # Mint — Stellar como chain de destino (ex: Arc -> Stellar, payout de creator)
    # ------------------------------------------------------------------

    async def mint_and_forward(self, raw_message: bytes, attestation: bytes) -> TxResult:
        """
        mint_and_forward real no CctpForwarder — permissionless (não exige que o
        caller seja o destinatário), mas precisa de uma conta fonte pra pagar o fee da tx.
        Usa a tesouraria por conveniência (não custodia o valor — o mint vai direto pro
        forward_recipient codificado no hook_data da mensagem original).
        """
        if self.sandbox:
            fake = f"sandbox_stellar_mint_{len(raw_message)}"
            LOG.info("[stellar_cctp] SANDBOX mint_and_forward | tx=%s", fake)
            return TxResult(tx_hash=fake, confirmed=True, status=1)

        if not self.treasury_secret:
            raise RuntimeError("[stellar_cctp] STELLAR_TREASURY_SECRET não configurado")

        from stellar_sdk import Keypair, SorobanServer, TransactionBuilder, scval

        kp = Keypair.from_secret(self.treasury_secret)
        server = SorobanServer(self.soroban_rpc_url)
        source = server.load_account(kp.public_key)

        tx = (
            TransactionBuilder(source, self._network_passphrase(), base_fee=10_000)
            .append_invoke_contract_function_op(
                contract_id=self.forwarder_contract,
                function_name="mint_and_forward",
                parameters=[
                    scval.to_bytes(raw_message),
                    scval.to_bytes(attestation),
                ],
            )
            .set_timeout(30)
            .build()
        )
        tx_hash = await self._prepare_sign_send(server, tx, kp)
        await self._wait_success(server, tx_hash)
        LOG.info("[stellar_cctp] mint_and_forward confirmado tx=%s", tx_hash)
        return TxResult(tx_hash=tx_hash, confirmed=True, status=1)

    # ------------------------------------------------------------------
    # Healthcheck
    # ------------------------------------------------------------------

    async def healthcheck(self) -> dict:
        if self.sandbox:
            return {"ok": True, "sandbox": True, "address": self.address}
        try:
            from stellar_sdk import SorobanServer

            server = SorobanServer(self.soroban_rpc_url)
            health = server.get_health()
            return {"ok": True, "sandbox": False, "address": self.address, "soroban_status": str(health.status)}
        except Exception as exc:
            return {"ok": False, "sandbox": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Soroban — approve + prepare (simula footprint) + assina + envia
    # ------------------------------------------------------------------

    async def _approve_usdc(self, server, kp, amount_raw: int) -> str:
        """approve(from, spender=TMM, amount, expiration_ledger) no SAC do USDC —
        allowance de vida curta (~1000 ledgers ≈ 80 min), só o necessário pro burn."""
        from stellar_sdk import TransactionBuilder, scval

        source = server.load_account(kp.public_key)
        expiration_ledger = server.get_latest_ledger().sequence + 1000
        tx = (
            TransactionBuilder(source, self._network_passphrase(), base_fee=10_000)
            .append_invoke_contract_function_op(
                contract_id=self._usdc_sac_address(),
                function_name="approve",
                parameters=[
                    scval.to_address(kp.public_key),
                    scval.to_address(self.tmm_contract),
                    scval.to_int128(amount_raw),
                    scval.to_uint32(expiration_ledger),
                ],
            )
            .set_timeout(30)
            .build()
        )
        return await self._prepare_sign_send(server, tx, kp)

    async def _wait_success(self, server, tx_hash: str, timeout_s: float = 45.0) -> None:
        """Aguarda o tx sair de NOT_FOUND — o burn só simula certo com o approve já
        aplicado no ledger, então não dá pra encadear os dois sem esperar."""
        import asyncio

        from stellar_sdk.soroban_rpc import GetTransactionStatus

        deadline = asyncio.get_event_loop().time() + timeout_s
        while asyncio.get_event_loop().time() < deadline:
            resp = server.get_transaction(tx_hash)
            if resp.status == GetTransactionStatus.SUCCESS:
                return
            if resp.status == GetTransactionStatus.FAILED:
                raise RuntimeError(f"[stellar_cctp] tx falhou on-chain: {tx_hash}")
            await asyncio.sleep(1.5)
        raise TimeoutError(f"[stellar_cctp] tx não confirmou em {timeout_s:.0f}s: {tx_hash}")

    async def _prepare_sign_send(self, server, tx, keypair, attempts: int = 5) -> str:
        import asyncio

        from stellar_sdk.exceptions import PrepareTransactionException

        # prepare (simulação) pode falhar transitoriamente logo após a attestation da
        # Circle fechar — recoveries manuais com os MESMOS bytes passaram ~4-6 min depois
        # (04/07, 3 ocorrências). Retry só nesse tipo de erro; janela total ~5 min
        # (na prática o tool agêntico já esperou a attestation por minutos — mais 5 é ok).
        prepared = None
        for attempt in range(1, attempts + 1):
            try:
                prepared = server.prepare_transaction(tx)
                break
            except PrepareTransactionException as exc:
                sim_error = getattr(getattr(exc, "simulate_transaction_response", None), "error", None)
                if attempt == attempts:
                    raise RuntimeError(
                        f"[stellar_cctp] simulação falhou após {attempts} tentativas: {sim_error}"
                    ) from exc
                LOG.warning(
                    "[stellar_cctp] simulação falhou (tentativa %d/%d): %s — retry em 30s",
                    attempt, attempts, sim_error,
                )
                await asyncio.sleep(30)
        prepared.sign(keypair)
        response = server.send_transaction(prepared)
        status = getattr(response, "status", None)
        if status == "ERROR":
            raise RuntimeError(f"[stellar_cctp] Soroban send_transaction error: {response}")
        return response.hash
