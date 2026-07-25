"""
cctp_client.py — Circle CCTP v2: bridge USDC entre duas chains EVM suportadas pela Circle
(não mais hardcoded em Sepolia->Arc — qualquer par domain/contratos EVM funciona, ex:
Arc->Base, Base->Arc). Solana e Stellar também têm CCTP real (via Anchor/Soroban, não EVM)
mas usam clientes separados: solana_cctp.py, stellar_cctp.py.

FLUXO COMPLETO (4 passos, todos auditáveis on-chain):
    1. approve()          USDC.approve(TokenMessenger, amount) na chain fonte
    2. depositForBurn()   queima USDC, emite MessageSent(bytes message)
    3. poll_attestation() aguarda Circle assinar o proof (iris-api, até 5 min)
    4. receive_on_arc()   ArcNativeClient.receive_cctp_message(raw_message, attest)

DIFERENCIAL vs. implementação naive:
  - raw_message é extraído do evento MessageSent e passado integralmente ao
    receiveMessage() — a versão bugada passava keccak256(message) (32 bytes),
    o que reverte silenciosamente no contrato.
  - approve é minerado antes do depositForBurn (sem race condition de nonce).
  - attestation é decodificada de hex antes de enviar ao contrato.
  - BridgeState rastreia cada etapa — recovery após crash sem duplo burn.
  - Sandbox simula E2E sem tocar contratos ou Circle API.

Contratos CCTP v2 Sepolia (defaults embutidos — não altere sem checar o
Circle docs, esses endereços são estáveis em testnet):
    TokenMessenger:     0x9f3B8679c73C2Fef8b59B4f3444d4e156fb70AA5
    MessageTransmitter: 0x7865fAfC2db2093669d92c0197ea5d5852Ab1e6f
    USDC:               0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import httpx

LOG = logging.getLogger(__name__)

# ── Circle Attestation API ──────────────────────────────────────────────────
_IRIS_SANDBOX = "https://iris-api-sandbox.circle.com/v1/attestations"
_IRIS_LIVE    = "https://iris-api.circle.com/v1/attestations"
# V2 é indexada por TX HASH do burn (não por message hash) — burns V2 NÃO aparecem no
# /v1/attestations; poll antigo travaria pra sempre (validado 03/07 nos fluxos Solana/Arc)
_IRIS_V2_SANDBOX = "https://iris-api-sandbox.circle.com/v2/messages"
_IRIS_V2_LIVE    = "https://iris-api.circle.com/v2/messages"

# ── Contratos CCTP v2 em Ethereum Sepolia ──────────────────────────────────
_SEPOLIA_TOKEN_MESSENGER     = "0x9f3B8679c73C2Fef8b59B4f3444d4e156fb70AA5"
_SEPOLIA_MSG_TRANSMITTER     = "0x7865fAfC2db2093669d92c0197ea5d5852Ab1e6f"
_SEPOLIA_USDC                = "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238"
_CCTP_DOMAIN_ETHEREUM        = 0

# ── Tópico do evento MessageSent (keccak256 da assinatura) ─────────────────
_MESSAGE_SENT_TOPIC = (
    "0x8c5261668696ce22758910d05bab8f186d6eb247ceac2af2e82c7dc17669b036"
)

# ── Timings ─────────────────────────────────────────────────────────────────
_ATTEST_INITIAL_WAIT_S = 8.0    # Circle leva alguns segundos após o burn
_ATTEST_INTERVAL_S     = 4.0
_ATTEST_TIMEOUT_S      = 300.0
_TX_TIMEOUT_S          = 120.0

# ── ABIs (source chain — apenas funções necessárias) ────────────────────────
_USDC_ABI = [
    {
        "name": "approve",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount",  "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "bool"}],
    },
    {
        "name": "decimals",
        "type": "function",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint8"}],
    },
]

_TOKEN_MESSENGER_ABI = [
    {
        "name": "depositForBurn",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "amount",            "type": "uint256"},
            {"name": "destinationDomain", "type": "uint32"},
            {"name": "mintRecipient",     "type": "bytes32"},
            {"name": "burnToken",         "type": "address"},
        ],
        "outputs": [{"name": "nonce", "type": "uint64"}],
    },
]

# CCTP V2: depositForBurn tem 7 params — o selector V1 de 4 params NEM EXISTE nos
# contratos V2 (Arc é V2-only). Validado on-chain em 03/07/2026
# (burn Arc→Solana tx 86fc04e4b53c1338252cf38150ac0b04de1807949bb146a2beb960c1c73dac39).
_TOKEN_MESSENGER_V2_ABI = [
    {
        "name": "depositForBurn",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "amount",               "type": "uint256"},
            {"name": "destinationDomain",    "type": "uint32"},
            {"name": "mintRecipient",        "type": "bytes32"},
            {"name": "burnToken",            "type": "address"},
            {"name": "destinationCaller",    "type": "bytes32"},
            {"name": "maxFee",               "type": "uint256"},
            {"name": "minFinalityThreshold", "type": "uint32"},
        ],
        "outputs": [],
    },
]

# depositForBurnWithHook: mesmos 7 params V2 + hookData — obrigatório quando o destino é
# Stellar (mintRecipient/destinationCaller = CctpForwarder, destinatário real no hookData).
_TOKEN_MESSENGER_V2_HOOK_ABI = [
    {
        "name": "depositForBurnWithHook",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "amount",               "type": "uint256"},
            {"name": "destinationDomain",    "type": "uint32"},
            {"name": "mintRecipient",        "type": "bytes32"},
            {"name": "burnToken",            "type": "address"},
            {"name": "destinationCaller",    "type": "bytes32"},
            {"name": "maxFee",               "type": "uint256"},
            {"name": "minFinalityThreshold", "type": "uint32"},
            {"name": "hookData",             "type": "bytes"},
        ],
        "outputs": [],
    },
]

# minFinalityThreshold=2000 = transferência standard/finalized (sem taxa, maxFee=0 válido)
_V2_MIN_FINALITY_FINALIZED = 2000


# ── Enums + dataclasses ─────────────────────────────────────────────────────

class BridgeStep(str, Enum):
    PENDING      = "pending"
    BURNED       = "burned"        # depositForBurn minerado
    ATTESTING    = "attesting"     # aguardando iris-api
    ATTESTED     = "attested"      # Circle assinou o proof
    RECEIVED     = "received"      # receiveMessage minerado no Arc


@dataclass
class BridgeState:
    """
    Rastreia o progresso de um bridge para possibilitar recovery após crash.
    Se o processo morrer depois do burn mas antes do receive, você pode
    chamar CCTPClient.finalize_bridge(state) com o state salvo.
    """
    step:            BridgeStep = BridgeStep.PENDING
    source_tx_hash:  str        = ""
    raw_message:     bytes      = field(default_factory=bytes)  # bytes do MessageSent
    message_hash:    str        = ""                            # keccak256(raw_message)
    attestation:     bytes      = field(default_factory=bytes)  # assinado pelo Circle
    arc_tx_hash:     str        = ""
    amount_usdc:     float      = 0.0
    recipient:       str        = ""
    error:           str        = ""


@dataclass
class BridgeResult:
    source_tx_hash: str
    arc_tx_hash:    str
    amount_usdc:    float
    recipient:      str
    message_hash:   str   = ""
    sandbox:        bool  = False


class CCTPClient:
    """
    Bridge USDC entre duas chains EVM suportadas pela Circle via CCTP v2 — não é mais
    hardcoded em Sepolia->Arc (Fase A da expansão multi-chain): qualquer par domain/contratos
    EVM da Circle funciona (ex: Arc->Base, Base->Arc), reaproveitando o mesmo fluxo
    approve->depositForBurn->attestation->receiveMessage. Os nomes `arc_*` nos atributos
    internos são retrocompatíveis (Arc continua sendo o destino padrão quando nada é
    sobrescrito) mas representam genericamente "a chain destino".

    Usa ArcNativeClient para o receiveMessage — o agente assina com sua própria chave,
    sem depender da Circle W3S API. Solana e Stellar (que também têm CCTP real, mas via
    programas Anchor / contratos Soroban, não EVM) são clientes separados
    (solana_cctp.py / stellar_cctp.py), orquestrados junto deste via o mesmo CctpTransfer.
    """

    def __init__(
        self,
        source_rpc:  str = "",
        arc_rpc:     str = "",
        signer_key:  str = "",    # chave que assina o burn na chain fonte
        arc_key:     str = "",    # chave da chain destino para receiveMessage (pode ser a mesma)
        sandbox:     bool = True,
        # Generalização multi-chain EVM — todos opcionais, default preserva o comportamento
        # original (fonte = Sepolia, destino = Arc). Sobrescrever permite qualquer par de
        # chains EVM suportadas pela Circle.
        source_domain:            Optional[int] = None,
        source_usdc:              str = "",
        source_token_messenger:   str = "",
        dest_domain:              Optional[int] = None,
        dest_usdc:                str = "",
        dest_message_transmitter: str = "",
        # 1 = ABI legada (Sepolia v1, 4 params). 2 = CCTP V2 (7 params) — obrigatório
        # quando a chain FONTE é V2-only (Arc). Só afeta o depositForBurn do burn.
        abi_version:              int = 1,
    ):
        self.source_rpc = source_rpc or os.getenv("CCTP_SOURCE_RPC",         "")
        self.arc_rpc    = arc_rpc    or os.getenv("ARC_RPC_URL",             "")
        self.signer_key = signer_key or os.getenv("CCTP_SIGNER_PRIVATE_KEY", "")
        # chave da chain destino — fallback para ARC_AGENT_PRIVATE_KEY ou signer_key
        self.arc_key    = arc_key or os.getenv("ARC_AGENT_PRIVATE_KEY", "") or self.signer_key
        self.sandbox    = sandbox
        self._iris      = _IRIS_SANDBOX if sandbox else _IRIS_LIVE
        # Na Circle, iris "sandbox" = TESTNET e iris sem sufixo = MAINNET — independe do
        # nosso sandbox (fake). Burns live em chains testnet (caso atual: Arc/Solana/Stellar
        # testnet) atestam no host sandbox; CCTP_IRIS_ENV=production quando migrar pra mainnet.
        self._iris_v2   = (
            _IRIS_V2_LIVE
            if os.getenv("CCTP_IRIS_ENV", "sandbox") == "production"
            else _IRIS_V2_SANDBOX
        )

        # Chain fonte — default Sepolia (compat retro), mas qualquer chain EVM da Circle serve
        self.src_usdc   = source_usdc or os.getenv("CCTP_SOURCE_USDC",            _SEPOLIA_USDC)
        self.src_tm     = source_token_messenger or os.getenv("CCTP_SOURCE_TOKEN_MESSENGER",  _SEPOLIA_TOKEN_MESSENGER)
        self.src_domain = source_domain if source_domain is not None else int(os.getenv("CCTP_SOURCE_DOMAIN", str(_CCTP_DOMAIN_ETHEREUM)))

        # Chain destino — default Arc, mas qualquer chain EVM da Circle serve
        self.arc_mt     = dest_message_transmitter or os.getenv("ARC_CCTP_MSG_TRANSMITTER",    "")
        self.arc_domain = dest_domain if dest_domain is not None else int(os.getenv("ARC_CCTP_DOMAIN", "26"))
        self.arc_usdc   = dest_usdc or os.getenv("ARC_CCTP_USDC",               "")
        self.abi_version = abi_version

    # ------------------------------------------------------------------
    # Entry point principal
    # ------------------------------------------------------------------

    async def bridge_usdc_to_arc(
        self,
        amount_usdc: float,
        recipient:   str,
    ) -> BridgeResult:
        """
        Bridge completo Sepolia → Arc.
        recipient = endereço EVM no Arc que receberá o USDC.

        Retorna BridgeResult com ambos os tx hashes para o recibo PQC.
        """
        if self.sandbox:
            return await self._sandbox_bridge(amount_usdc, recipient)

        self._require_web3()
        self._validate_config()

        state = BridgeState(amount_usdc=amount_usdc, recipient=recipient)

        try:
            # Passo 1+2: approve + depositForBurn
            state = await self._step_burn(state)

            # Passo 3: attestation Circle
            state = await self._step_attest(state)

            # Passo 4: receiveMessage no Arc
            state = await self._step_receive(state)

        except Exception as exc:
            state.error = str(exc)
            LOG.error(
                "[cctp] bridge failed at step=%s: %s",
                state.step.value, exc, exc_info=True,
            )
            raise RuntimeError(
                f"CCTP bridge falhou em step={state.step.value}: {exc}"
            ) from exc

        return BridgeResult(
            source_tx_hash=state.source_tx_hash,
            arc_tx_hash=state.arc_tx_hash,
            amount_usdc=state.amount_usdc,
            recipient=state.recipient,
            message_hash=state.message_hash,
            sandbox=False,
        )

    async def _sandbox_bridge(self, amount_usdc: float, recipient: str) -> BridgeResult:
        """Simula o fluxo CCTP completo (burn -> attest -> mint -> confirm) sem tocar
        contratos ou a API da Circle — log numerado pensado para a demo do hackathon
        (issue P2-02): o júri/vídeo precisa ver as 4 etapas, não só um resultado final.
        """
        short = recipient[2:10] if recipient.startswith("0x") else recipient[:8]
        source_tx = f"0xSANDBOX_{short}_src"
        arc_tx = f"0xSANDBOX_{short}_arc"

        LOG.info("[cctp] Step 1/4: burning %.4f USDC on ETH-SEPOLIA...", amount_usdc)
        await asyncio.sleep(0.4)

        LOG.info("[cctp] Step 2/4: waiting for Circle attestation...")
        await asyncio.sleep(0.4)

        LOG.info("[cctp] Step 3/4: minting USDC on ARC-TESTNET...")
        await asyncio.sleep(0.4)

        LOG.info("[cctp] Step 4/4: confirmed. tx_hash=%s", arc_tx)

        return BridgeResult(
            source_tx_hash=source_tx,
            arc_tx_hash=arc_tx,
            amount_usdc=amount_usdc,
            recipient=recipient,
            message_hash=f"0x{'0' * 64}",
            sandbox=True,
        )

    async def burn_and_attest(
        self,
        amount_usdc: float,
        recipient_bytes32: bytes,
        destination_domain: int,
        destination_caller_bytes32: Optional[bytes] = None,
        hook_data: bytes = b"",
    ) -> BridgeState:
        """
        Burn + attestation SEM o passo de receive EVM (_step_receive usa ArcNativeClient,
        só serve quando o destino também é EVM). Usar quando o destino real é Solana
        (solana_cctp.SolanaCCTPClient.receive_and_mint) ou Stellar
        (stellar_cctp.StellarCCTPClient.mint_and_forward) — o chamador completa o mint
        com o raw_message + attestation devolvidos aqui.

        `recipient_bytes32` já deve estar no formato de 32 bytes esperado pelo domain
        destino (endereço Solana é nativamente 32 bytes; para Stellar como destino, deve
        ser o endereço do contrato CctpForwarder — nunca a conta do usuário, ver
        stellar_cctp.py).

        `hook_data` não-vazio troca o depositForBurn pelo depositForBurnWithHook (só
        existe na ABI V2) — destino Stellar codifica o destinatário real aqui
        (stellar_cctp.build_hook_data). `destination_caller_bytes32` default bytes(32)
        (qualquer um pode chamar o receive); destino Stellar exige o CctpForwarder.
        """
        if hook_data and self.abi_version != 2:
            raise RuntimeError(
                "[cctp] hook_data exige abi_version=2 — depositForBurnWithHook não existe na ABI V1"
            )
        if self.sandbox:
            r = f"0xSANDBOX_burn_and_attest_domain{destination_domain}"
            return BridgeState(
                step=BridgeStep.ATTESTED,
                source_tx_hash=f"{r}_src",
                amount_usdc=amount_usdc,
                recipient=recipient_bytes32.hex(),
                message_hash=f"0x{'0' * 64}",
                raw_message=b"\x00" * 116,
                attestation=b"\x00" * 65,
            )

        self._require_web3()
        self._validate_config()

        state = BridgeState(amount_usdc=amount_usdc, recipient=recipient_bytes32.hex())
        original_domain = self.arc_domain
        try:
            self.arc_domain = destination_domain
            state.recipient = recipient_bytes32.hex()
            # reaproveita _step_burn, mas com mint_recipient já em bytes32 puro (não um
            # endereço 0x... — precisamos passar direto, sem o zfill de endereço EVM).
            state = await self._burn_raw(state, recipient_bytes32, destination_caller_bytes32, hook_data)
            state = await self._step_attest(state)
        finally:
            self.arc_domain = original_domain

        return state

    async def _burn_raw(
        self,
        state: BridgeState,
        mint_recipient_bytes32: bytes,
        destination_caller_bytes32: Optional[bytes] = None,
        hook_data: bytes = b"",
    ) -> BridgeState:
        """Variante de _step_burn que aceita mint_recipient já em bytes32 (não deriva de
        um endereço EVM 0x...) — necessária pra destinos Solana (endereço nativo 32 bytes)
        e Stellar (CctpForwarder + hook_data com o destinatário real)."""
        from web3 import Web3
        from web3.middleware import ExtraDataToPOAMiddleware

        w3 = Web3(Web3.HTTPProvider(self.source_rpc, request_kwargs={"timeout": 30}))
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        acc = w3.eth.account.from_key(self.signer_key)

        usdc_contract = w3.eth.contract(address=Web3.to_checksum_address(self.src_usdc), abi=_USDC_ABI)
        decimals = usdc_contract.functions.decimals().call()
        amount_u = int(state.amount_usdc * 10 ** decimals)
        chain_id = w3.eth.chain_id

        nonce_0 = w3.eth.get_transaction_count(acc.address, "pending")
        approve_tx = usdc_contract.functions.approve(
            Web3.to_checksum_address(self.src_tm), amount_u,
        ).build_transaction({"from": acc.address, "nonce": nonce_0, "chainId": chain_id, "gasPrice": w3.eth.gas_price})
        approve_tx["gas"] = w3.eth.estimate_gas(approve_tx)
        signed_a = acc.sign_transaction(approve_tx)
        approve_hash = w3.eth.send_raw_transaction(signed_a.raw_transaction).hex()
        approve_receipt = await asyncio.get_event_loop().run_in_executor(
            None, lambda: w3.eth.wait_for_transaction_receipt(approve_hash, timeout=_TX_TIMEOUT_S),
        )
        if approve_receipt["status"] != 1:
            raise RuntimeError(f"[cctp] approve reverted: tx={approve_hash}")

        nonce_1 = w3.eth.get_transaction_count(acc.address, "pending")
        dest_caller = bytes(destination_caller_bytes32 or bytes(32))
        if hook_data and self.abi_version != 2:
            raise RuntimeError(
                "[cctp] hook_data exige abi_version=2 — depositForBurnWithHook não existe na ABI V1"
            )
        if self.abi_version == 2 and hook_data:
            messenger = w3.eth.contract(address=Web3.to_checksum_address(self.src_tm), abi=_TOKEN_MESSENGER_V2_HOOK_ABI)
            burn_fn = messenger.functions.depositForBurnWithHook(
                amount_u, self.arc_domain, bytes(mint_recipient_bytes32),
                Web3.to_checksum_address(self.src_usdc),
                dest_caller,                    # destino Stellar: CctpForwarder obrigatório
                0,                              # maxFee: 0 na transferência standard
                _V2_MIN_FINALITY_FINALIZED,
                bytes(hook_data),
            )
        elif self.abi_version == 2:
            messenger = w3.eth.contract(address=Web3.to_checksum_address(self.src_tm), abi=_TOKEN_MESSENGER_V2_ABI)
            burn_fn = messenger.functions.depositForBurn(
                amount_u, self.arc_domain, bytes(mint_recipient_bytes32),
                Web3.to_checksum_address(self.src_usdc),
                dest_caller,                    # default bytes(32): qualquer um pode chamar receive
                0,                              # maxFee: 0 na transferência standard
                _V2_MIN_FINALITY_FINALIZED,
            )
        else:
            messenger = w3.eth.contract(address=Web3.to_checksum_address(self.src_tm), abi=_TOKEN_MESSENGER_ABI)
            burn_fn = messenger.functions.depositForBurn(
                amount_u, self.arc_domain, bytes(mint_recipient_bytes32), Web3.to_checksum_address(self.src_usdc),
            )
        burn_tx = burn_fn.build_transaction(
            {"from": acc.address, "nonce": nonce_1, "chainId": chain_id,
             "gasPrice": w3.eth.gas_price, "gas": 350_000}
        )
        # Gas explícito (350k) em vez de estimate_gas: o nó do Arc exige saldo pro TETO da
        # estimativa (~4.2M gas), não pro consumo real (~250k) — com saldo USDC justo a
        # estimativa falha antes de tentar. Tentamos refinar via estimativa quando dá.
        try:
            burn_tx["gas"] = w3.eth.estimate_gas({k: v for k, v in burn_tx.items() if k != "gas"})
        except Exception:
            LOG.info("[cctp] estimate_gas falhou (teto do nó > saldo) — usando gas fixo 350k")
        signed_b = acc.sign_transaction(burn_tx)
        burn_hash = w3.eth.send_raw_transaction(signed_b.raw_transaction).hex()
        burn_receipt = await asyncio.get_event_loop().run_in_executor(
            None, lambda: w3.eth.wait_for_transaction_receipt(burn_hash, timeout=_TX_TIMEOUT_S),
        )
        if burn_receipt["status"] != 1:
            raise RuntimeError(f"[cctp] depositForBurn reverted: tx={burn_hash}")

        raw_message, message_hash = self._extract_message_from_receipt(w3, burn_receipt)
        state.step = BridgeStep.BURNED
        state.source_tx_hash = burn_hash
        state.raw_message = raw_message
        state.message_hash = message_hash
        return state

    async def finalize_bridge(self, state: BridgeState) -> BridgeResult:
        """
        Retoma um bridge parcial a partir do BridgeState salvo.
        Útil quando o processo crasha depois do burn mas antes do receive.
        """
        if state.step == BridgeStep.BURNED:
            state = await self._step_attest(state)
        if state.step == BridgeStep.ATTESTED:
            state = await self._step_receive(state)

        return BridgeResult(
            source_tx_hash=state.source_tx_hash,
            arc_tx_hash=state.arc_tx_hash,
            amount_usdc=state.amount_usdc,
            recipient=state.recipient,
            message_hash=state.message_hash,
            sandbox=False,
        )

    # ------------------------------------------------------------------
    # Passo 1+2: approve + depositForBurn
    # ------------------------------------------------------------------

    async def _step_burn(self, state: BridgeState) -> BridgeState:
        from web3 import Web3
        from web3.middleware import ExtraDataToPOAMiddleware

        w3  = Web3(Web3.HTTPProvider(self.source_rpc, request_kwargs={"timeout": 30}))
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        acc = w3.eth.account.from_key(self.signer_key)

        usdc_contract = w3.eth.contract(
            address=Web3.to_checksum_address(self.src_usdc),
            abi=_USDC_ABI,
        )
        decimals  = usdc_contract.functions.decimals().call()
        amount_u  = int(state.amount_usdc * 10 ** decimals)
        chain_id  = w3.eth.chain_id

        # --- 1. approve (espera receipt antes do burn para evitar nonce race) ---
        nonce_0  = w3.eth.get_transaction_count(acc.address, "pending")
        approve_tx = usdc_contract.functions.approve(
            Web3.to_checksum_address(self.src_tm),
            amount_u,
        ).build_transaction({
            "from":    acc.address,
            "nonce":   nonce_0,
            "chainId": chain_id,
            "gasPrice": w3.eth.gas_price,
        })
        approve_tx["gas"] = w3.eth.estimate_gas(approve_tx)
        signed_a = acc.sign_transaction(approve_tx)
        approve_hash = w3.eth.send_raw_transaction(signed_a.raw_transaction).hex()
        LOG.info("[cctp] approve sent tx=%s", approve_hash)

        approve_receipt = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: w3.eth.wait_for_transaction_receipt(approve_hash, timeout=_TX_TIMEOUT_S),
        )
        if approve_receipt["status"] != 1:
            raise RuntimeError(f"[cctp] approve reverted: tx={approve_hash}")
        LOG.info("[cctp] approve confirmed block=%s", approve_receipt["blockNumber"])

        # --- 2. depositForBurn ---
        messenger = w3.eth.contract(
            address=Web3.to_checksum_address(self.src_tm),
            abi=_TOKEN_MESSENGER_ABI,
        )
        # mintRecipient: endereço Arc padded to bytes32 (big-endian, zero-padded)
        recipient_clean = state.recipient[2:] if state.recipient.startswith("0x") else state.recipient
        mint_recipient  = bytes.fromhex(recipient_clean.lower().zfill(64))

        nonce_1 = w3.eth.get_transaction_count(acc.address, "pending")
        burn_tx = messenger.functions.depositForBurn(
            amount_u,
            self.arc_domain,
            mint_recipient,
            Web3.to_checksum_address(self.src_usdc),
        ).build_transaction({
            "from":    acc.address,
            "nonce":   nonce_1,
            "chainId": chain_id,
            "gasPrice": w3.eth.gas_price,
        })
        burn_tx["gas"] = w3.eth.estimate_gas(burn_tx)
        signed_b    = acc.sign_transaction(burn_tx)
        burn_hash   = w3.eth.send_raw_transaction(signed_b.raw_transaction).hex()
        LOG.info("[cctp] depositForBurn sent tx=%s amount_u=%d", burn_hash, amount_u)

        burn_receipt = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: w3.eth.wait_for_transaction_receipt(burn_hash, timeout=_TX_TIMEOUT_S),
        )
        if burn_receipt["status"] != 1:
            raise RuntimeError(f"[cctp] depositForBurn reverted: tx={burn_hash}")

        # Extrair raw_message + message_hash do evento MessageSent
        raw_message, message_hash = self._extract_message_from_receipt(w3, burn_receipt)
        LOG.info("[cctp] burn confirmed tx=%s msg_hash=%s", burn_hash, message_hash)

        state.step           = BridgeStep.BURNED
        state.source_tx_hash = burn_hash
        state.raw_message    = raw_message
        state.message_hash   = message_hash
        return state

    # ------------------------------------------------------------------
    # Passo 3: attestation
    # ------------------------------------------------------------------

    async def _step_attest(self, state: BridgeState) -> BridgeState:
        state.step = BridgeStep.ATTESTING

        # Circle leva alguns segundos após o burn para indexar
        await asyncio.sleep(_ATTEST_INITIAL_WAIT_S)

        if self.abi_version == 2:
            # Burns V2 NÃO aparecem no /v1/attestations (indexação por message hash é
            # só V1) — o poll V1 travaria até o timeout. V2 indexa por tx hash do burn.
            # CRÍTICO: usar a MENSAGEM da resposta da iris, não a do evento MessageSent —
            # a iris preenche finalityThresholdExecuted e assina a versão preenchida;
            # a mensagem crua do receipt + attestation da iris dá InvalidAttesterSignature
            # no receive do destino (visto no run live de 04/07, Solana erro 6027).
            iris_msg = await self._poll_attestation_v2(state.source_tx_hash)
            attestation_hex = iris_msg["attestation"]
            message_hex = iris_msg.get("message", "")
            if message_hex:
                msg_clean = message_hex[2:] if message_hex.startswith("0x") else message_hex
                state.raw_message = bytes.fromhex(msg_clean)
        else:
            attestation_hex = await self._poll_attestation(state.message_hash)
        # hex → bytes (remove 0x prefix se presente)
        hex_clean       = attestation_hex[2:] if attestation_hex.startswith("0x") else attestation_hex
        state.attestation = bytes.fromhex(hex_clean)

        LOG.info(
            "[cctp] attestation received msg_hash=%s attest_len=%d",
            state.message_hash, len(state.attestation),
        )
        state.step = BridgeStep.ATTESTED
        return state

    async def _poll_attestation(self, message_hash: str) -> str:
        """Retorna o attestation hex quando Circle confirmar. Timeout 5 min."""
        url      = f"{self._iris}/{message_hash}"
        deadline = time.monotonic() + _ATTEST_TIMEOUT_S

        async with httpx.AsyncClient(timeout=15) as client:
            while time.monotonic() < deadline:
                try:
                    resp = await client.get(url)
                except httpx.RequestError as exc:
                    LOG.warning("[cctp] iris-api unreachable: %s — retrying", exc)
                    await asyncio.sleep(_ATTEST_INTERVAL_S)
                    continue

                if resp.status_code == 404:
                    LOG.debug("[cctp] attestation not indexed yet")
                    await asyncio.sleep(_ATTEST_INTERVAL_S)
                    continue

                if not resp.is_success:
                    LOG.warning("[cctp] iris-api %s: %s", resp.status_code, resp.text[:100])
                    await asyncio.sleep(_ATTEST_INTERVAL_S)
                    continue

                data   = resp.json()
                status = data.get("status")
                if status == "complete":
                    return data["attestation"]

                LOG.debug("[cctp] attestation status=%s", status)
                await asyncio.sleep(_ATTEST_INTERVAL_S)

        raise TimeoutError(
            f"[cctp] attestation não chegou em {_ATTEST_TIMEOUT_S:.0f}s | msg_hash={message_hash}"
        )

    async def _poll_attestation_v2(self, source_tx_hash: str) -> dict:
        """Iris V2: GET /v2/messages/{srcDomain}?transactionHash={burn_tx}. Retorna o
        primeiro message completo (dict com 'message' E 'attestation' — os dois têm que
        vir da MESMA resposta, ver _step_attest). Polling validado on-chain em 03-04/07."""
        tx = source_tx_hash if source_tx_hash.startswith("0x") else f"0x{source_tx_hash}"
        url      = f"{self._iris_v2}/{self.src_domain}"
        deadline = time.monotonic() + _ATTEST_TIMEOUT_S

        async with httpx.AsyncClient(timeout=15) as client:
            while time.monotonic() < deadline:
                try:
                    resp = await client.get(url, params={"transactionHash": tx})
                except httpx.RequestError as exc:
                    LOG.warning("[cctp] iris-api v2 unreachable: %s — retrying", exc)
                    await asyncio.sleep(_ATTEST_INTERVAL_S)
                    continue

                if resp.status_code == 404:
                    LOG.debug("[cctp] v2 message not indexed yet")
                elif resp.is_success:
                    for m in resp.json().get("messages", []):
                        if m.get("status") == "complete" and m.get("attestation"):
                            return m
                    LOG.debug("[cctp] v2 attestation still pending")
                else:
                    LOG.warning("[cctp] iris-api v2 %s: %s", resp.status_code, resp.text[:100])
                await asyncio.sleep(_ATTEST_INTERVAL_S)

        raise TimeoutError(
            f"[cctp] attestation V2 não chegou em {_ATTEST_TIMEOUT_S:.0f}s | tx={source_tx_hash}"
        )

    # ------------------------------------------------------------------
    # Passo 4: receiveMessage no Arc
    # ------------------------------------------------------------------

    async def _step_receive(self, state: BridgeState) -> BridgeState:
        from server.integrations.arc_native import ArcNativeClient

        arc = ArcNativeClient(
            rpc_url=self.arc_rpc,
            private_key=self.arc_key,
            usdc_address=self.arc_usdc,
            sandbox=False,
        )

        if not self.arc_mt:
            raise RuntimeError(
                "[cctp] ARC_CCTP_MSG_TRANSMITTER não configurado — "
                "obtenha o endereço no Discord do hackathon Lepton"
            )

        result = await arc.receive_cctp_message(
            msg_transmitter=self.arc_mt,
            raw_message=state.raw_message,
            attestation=state.attestation,
        )

        state.step        = BridgeStep.RECEIVED
        state.arc_tx_hash = result.tx_hash
        LOG.info("[cctp] USDC minted on Arc tx=%s", state.arc_tx_hash)
        return state

    # ------------------------------------------------------------------
    # Extração do MessageSent
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_message_from_receipt(w3, receipt) -> tuple[bytes, str]:
        """
        Extrai raw_message e message_hash do evento MessageSent no receipt.

        MessageSent(bytes message) — o data é ABI-encoded como (bytes).
        message_hash = keccak256(raw_message) — usado para query da iris-api.

        NÃO retorna o hash como mensagem. raw_message e message_hash são
        coisas diferentes e não são intercambiáveis.
        """
        import eth_abi
        from web3 import Web3

        logs = receipt.get("logs", [])
        for log in logs:
            topics = log.get("topics", [])
            if not topics:
                continue

            t0 = topics[0]
            if isinstance(t0, bytes):
                topic_hex = "0x" + t0.hex()
            else:
                topic_hex = str(t0)
            if topic_hex.lower() != _MESSAGE_SENT_TOPIC.lower():
                continue

            # data do log = abi.encode(bytes message)
            raw_data = log["data"]
            if isinstance(raw_data, bytes):
                data_bytes = raw_data
            elif isinstance(raw_data, str):
                clean = raw_data[2:] if raw_data.startswith("0x") else raw_data
                data_bytes = bytes.fromhex(clean)
            else:
                continue

            # Decode ABI: (bytes) → raw_message
            (raw_message,) = eth_abi.decode(["bytes"], data_bytes)

            # keccak256(raw_message) = hash para a iris-api
            message_hash = Web3.keccak(raw_message).hex()

            return raw_message, message_hash

        raise RuntimeError(
            "[cctp] evento MessageSent não encontrado no receipt. "
            "Verifique se o endereço do TokenMessenger está correto."
        )

    # ------------------------------------------------------------------
    # Guards
    # ------------------------------------------------------------------

    @staticmethod
    def _require_web3() -> None:
        try:
            import web3       # noqa
            import eth_abi    # noqa
        except ImportError:
            raise RuntimeError(
                "Dependências EVM não instaladas.\n"
                "Rode: pip install web3>=6.20.0\n"
                "Ou desative com CCTP_ENABLED=false."
            )

    def _validate_config(self) -> None:
        missing = []
        if not self.source_rpc:   missing.append("CCTP_SOURCE_RPC")
        if not self.arc_rpc:      missing.append("ARC_RPC_URL")
        if not self.signer_key:   missing.append("CCTP_SIGNER_PRIVATE_KEY")
        if not self.arc_key:      missing.append("ARC_AGENT_PRIVATE_KEY")
        if missing:
            raise RuntimeError(
                f"[cctp] variáveis faltando: {', '.join(missing)}"
            )
