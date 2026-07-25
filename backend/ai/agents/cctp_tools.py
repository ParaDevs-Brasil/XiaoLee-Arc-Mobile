"""
cctp_tools.py — tool agêntica de payout cross-chain via CCTP real (Arc -> Solana/Stellar).

Formato OpenAI — o ClaudeAgentEngine converte para Anthropic internamente. Tool NOVA,
não mexe no contrato congelado de pay_creator_nanopayment (creator_pay_tools.py).

Fluxo: burn no Arc (CCTPClient.burn_and_attest, domain 26 -> domain do destino) ->
attestation Circle -> mint no destino real (SolanaCCTPClient.receive_and_mint ou
StellarCCTPClient.mint_and_forward). Mesmo padrão de intent durável ANTES de executar
usado em pay_creator_nanopayment, mas persistido em CctpTransfer (não PaymentIntent).

Destino Stellar: o burn no Arc usa depositForBurnWithHook (exige CCTPClient com
abi_version=2) — mint_recipient/destination_caller = contrato CctpForwarder e o
endereço Stellar real do criador vai no hook_data (ver stellar_cctp.build_hook_data).
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from database.repository import DatabaseRepository
    from server.integrations.cctp_client import CCTPClient
    from server.integrations.solana_cctp import SolanaCCTPClient
    from server.integrations.stellar_cctp import StellarCCTPClient

from services.pqc_receipt import sign_receipt as _pqc_sign
from server.integrations.solana_cctp import SOLANA_CCTP_DOMAIN
from server.integrations.stellar_cctp import STELLAR_CCTP_DOMAIN

LOG = logging.getLogger(__name__)

ARC_CCTP_DOMAIN = 26

PAYOUT_CROSS_CHAIN_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "payout_cross_chain_nanopayment",
        "description": (
            "Pay an eligible creator whose registered wallet is on Solana or Stellar "
            "(not Arc/EVM) via real CCTP (burn on Arc, mint on destination chain). "
            "Use this instead of pay_creator_nanopayment when the creator's `chain` "
            "field (from discover_creators/evaluate_creator) is 'solana' or 'stellar'. "
            "ALWAYS check_budget before calling this. ALWAYS generate a fresh UUID v4 "
            "for intent_id."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "intent_id": {
                    "type": "string",
                    "description": "Fresh UUID v4 idempotency key (generate a new one each call)",
                },
                "to": {
                    "type": "string",
                    "description": "Creator's native address on the destination chain (Solana pubkey or Stellar strkey)",
                },
                "amount_usdc": {
                    "type": "number",
                    "description": "Amount in USDC to send",
                },
                "destination_chain": {
                    "type": "string",
                    "enum": ["solana", "stellar"],
                    "description": "Which chain the creator's wallet is on",
                },
            },
            "required": ["intent_id", "to", "amount_usdc", "destination_chain"],
        },
    },
}

CCTP_TOOLS: list[dict] = [PAYOUT_CROSS_CHAIN_TOOL]


def _solana_mint_recipient_ata(solana_cctp_client, owner_b58: str) -> bytes:
    """mintRecipient de um transfer CCTP com destino Solana é o TOKEN ACCOUNT (ATA) do
    destinatário, não a wallet — regra da Circle pra SVM. A ATA é criada de forma
    idempotente pelo receive_and_mint, então não precisa existir ainda."""
    from solders.pubkey import Pubkey

    owner = Pubkey.from_string(owner_b58)
    mint = Pubkey.from_string(solana_cctp_client.usdc_mint)
    return bytes(solana_cctp_client.derive_associated_token_address(owner, mint))


def make_cctp_tool_executors(
    repo: "DatabaseRepository",
    arc_cctp_client: "CCTPClient",
    solana_cctp_client: "SolanaCCTPClient",
    stellar_cctp_client: "StellarCCTPClient",
    campaign_id: int,
    budget_usdc: float,
    reward_per_creator: float = 5.0,
    spent_tracker: Optional[dict] = None,
) -> dict:
    """
    Cria o executor de payout_cross_chain_nanopayment com contexto injetado.

    `spent_tracker` deve ser o MESMO dict passado para
    creator_pay_tools.make_tool_executors quando ambos os conjuntos de tools estão
    registrados juntos — garante orçamento único da campanha entre Arc e cross-chain.
    """
    spent = spent_tracker if spent_tracker is not None else {"usdc": 0.0}

    async def payout_cross_chain_nanopayment(inputs: dict, context: dict) -> dict:
        intent_id = str(inputs.get("intent_id", "")).strip()
        to = str(inputs.get("to", "")).strip()
        destination_chain = str(inputs.get("destination_chain", "")).strip().lower()
        amount_usdc = float(inputs.get("amount_usdc", reward_per_creator))

        if not intent_id:
            intent_id = str(uuid.uuid4())
            LOG.warning("[tool] intent_id not provided — generated %s", intent_id)

        if not to:
            return {"error": "to address is required"}

        if destination_chain not in ("solana", "stellar"):
            return {"error": "destination_chain must be 'solana' or 'stellar'", "destination_chain": destination_chain}

        if amount_usdc <= 0:
            return {"error": "amount_usdc must be positive", "requested_usdc": amount_usdc}

        existing = await repo.get_cctp_transfer(intent_id)
        if existing and existing.status in ("received",):
            LOG.info("[tool] duplicate cctp intent %s — returning existing receipt", intent_id)
            return {
                "tx": existing.dest_tx_hash,
                "receipt_pqc": existing.receipt_pqc or intent_id,
                "duplicate": True,
                "amount_usdc": float(existing.amount_usdc),
                "to": to,
            }

        # Guard de orçamento + RESERVA atômica (sem await entre check e débito) —
        # pré-requisito da execução paralela de tools no engine: dois payouts
        # concorrentes não podem ambos passar no check com o mesmo saldo.
        # Estorno no except em caso de falha (mesmo padrão de creator_pay_tools).
        remaining = budget_usdc - spent["usdc"]
        if amount_usdc > remaining:
            return {
                "error": "insufficient_budget",
                "remaining_usdc": remaining,
                "requested_usdc": amount_usdc,
                "budget_exhausted": True,
            }
        spent["usdc"] += amount_usdc

        dest_domain = SOLANA_CCTP_DOMAIN if destination_chain == "solana" else STELLAR_CCTP_DOMAIN

        # 1. Intent durável ANTES de executar (anti-replay, recovery pós-crash)
        await repo.create_cctp_transfer(
            intent_id=intent_id,
            direction="outflow",
            source_domain=ARC_CCTP_DOMAIN,
            dest_domain=dest_domain,
            counterparty=to,
            amount_usdc=amount_usdc,
            campaign_id=campaign_id,
        )
        LOG.info("[tool] cctp transfer created intent_id=%s to=%s chain=%s amount=%.4f", intent_id, to, destination_chain, amount_usdc)

        try:
            t0 = time.monotonic()
            destination_caller_bytes32 = None
            hook_data = b""
            if destination_chain == "solana":
                mint_recipient_bytes32 = _solana_mint_recipient_ata(solana_cctp_client, to)
            else:
                # REGRA CCTP-Stellar (fundos presos permanentemente se violar):
                # mint_recipient E destination_caller do burn apontam pro contrato
                # CctpForwarder — NUNCA pra conta do usuário. O destinatário real vai
                # codificado no hook_data (v0: magic + version/len BE + strkey UTF-8).
                from server.integrations.stellar_cctp import build_hook_data

                mint_recipient_bytes32 = stellar_cctp_client.forwarder_bytes32()
                destination_caller_bytes32 = mint_recipient_bytes32
                hook_data = build_hook_data(to)

            # 2. Burn no Arc + attestation
            burn_state = await arc_cctp_client.burn_and_attest(
                amount_usdc=amount_usdc,
                recipient_bytes32=mint_recipient_bytes32,
                destination_domain=dest_domain,
                destination_caller_bytes32=destination_caller_bytes32,
                hook_data=hook_data,
            )
            burn_attest_s = time.monotonic() - t0
            await repo.update_cctp_transfer(
                intent_id, status="attested",
                source_tx_hash=burn_state.source_tx_hash,
                message_hash=burn_state.message_hash,
            )

            # 3. Mint no destino real
            if destination_chain == "solana":
                # token_pair PDA no Solana é derivado do endereço do token QUEIMADO na
                # origem (USDC do Arc, EVM 20 bytes → left-pad pra 32). Validado contra
                # o layout do receive_message real na devnet.
                src_usdc = arc_cctp_client.src_usdc or ""
                if src_usdc.startswith("0x") and len(src_usdc) == 42:
                    burn_token_b32 = bytes(12) + bytes.fromhex(src_usdc[2:])
                else:
                    if not arc_cctp_client.sandbox:
                        raise RuntimeError(
                            "[cctp_tools] ARC_USDC_ADDRESS/CCTP_SOURCE_USDC inválido — "
                            "necessário pro token_pair PDA do mint no Solana"
                        )
                    burn_token_b32 = bytes(32)
                mint_result = await solana_cctp_client.receive_and_mint(
                    raw_message=burn_state.raw_message,
                    attestation=burn_state.attestation,
                    recipient_owner_b58=to,
                    source_domain=ARC_CCTP_DOMAIN,
                    burn_token_bytes_32=burn_token_b32,
                )
            else:
                mint_result = await stellar_cctp_client.mint_and_forward(
                    raw_message=burn_state.raw_message,
                    attestation=burn_state.attestation,
                )

            # 4. Recibo PQC + status final
            receipt_pqc = _pqc_sign(intent_id, to, amount_usdc, mint_result.tx_hash)
            await repo.update_cctp_transfer(
                intent_id, status="received",
                dest_tx_hash=mint_result.tx_hash,
                receipt_pqc=receipt_pqc,
            )

            total_s = time.monotonic() - t0
            LOG.info(
                "[tool] cctp payout complete intent=%s to=%s chain=%s tx=%s total_spent=%.4f "
                "burn_attest=%.1fs mint=%.1fs total=%.1fs",
                intent_id, to, destination_chain, mint_result.tx_hash, spent["usdc"],
                burn_attest_s, total_s - burn_attest_s, total_s,
            )

            return {
                "tx": mint_result.tx_hash,
                "receipt_pqc": receipt_pqc,
                "amount_usdc": amount_usdc,
                "to": to,
                "destination_chain": destination_chain,
                "status": "received",
                # latência medida por etapa — vai pro steps do run e pro dashboard
                "latency": {
                    "burn_attest_s": round(burn_attest_s, 1),
                    "mint_s": round(total_s - burn_attest_s, 1),
                    "total_s": round(total_s, 1),
                },
            }

        except Exception as exc:
            spent["usdc"] -= amount_usdc  # estorna a reserva — o pagamento não saiu
            await repo.update_cctp_transfer(intent_id, status="failed", error_message=str(exc))
            LOG.error("[tool] cctp payout failed intent=%s error=%s", intent_id, exc)
            return {"error": str(exc), "intent_id": intent_id, "status": "failed", "to": to}

    return {"payout_cross_chain_nanopayment": payout_cross_chain_nanopayment}
