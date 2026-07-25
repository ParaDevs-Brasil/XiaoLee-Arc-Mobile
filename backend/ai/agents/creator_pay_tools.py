"""
creator_pay_tools.py — As 4 tools do loop agêntico de campanhas.

Formato OpenAI — o ClaudeAgentEngine converte para Anthropic internamente.

Contrato congelado (não alterar sem avisar o time):
    pay_creator_nanopayment(intent_id: str, to: str, amount_usdc: float)

Context injetado pelos executores (nunca vai para o modelo):
    campaign_id, budget_usdc, repo (DatabaseRepository), arc_client (ArcClient)
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.repository import DatabaseRepository
    from server.integrations.arc_client import ArcClient

from services.pqc_receipt import sign_receipt as _pqc_sign
from server.metrics import get_registered_creator_wallet as _get_registered_wallet

LOG = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool definitions — formato OpenAI
# ---------------------------------------------------------------------------

DISCOVER_CREATORS_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "discover_creators",
        "description": (
            "Discover eligible creators enrolled in a campaign. "
            "Returns a list of creators with their participation status."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "campaign_id": {
                    "type": "integer",
                    "description": "Campaign ID to search for enrolled creators",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of creators to return (default 20)",
                    "default": 20,
                },
            },
            "required": ["campaign_id"],
        },
    },
}

EVALUATE_CREATOR_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "evaluate_creator",
        "description": (
            "Evaluate a creator's eligibility and score for payment. "
            "Score 0-100: has_followed=30, has_replied=30, has_retweeted=25, tasks_verified=15. "
            "Score >= 50 means eligible. Returns already_paid=true if creator already received payment."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "creator_id": {
                    "type": "string",
                    "description": "Creator twitter handle (e.g. @username)",
                },
                "campaign_id": {
                    "type": "integer",
                    "description": "Campaign ID",
                },
            },
            "required": ["creator_id", "campaign_id"],
        },
    },
}

CHECK_BUDGET_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "check_budget",
        "description": (
            "Check the remaining USDC budget for the current campaign run. "
            "Always call this before pay_creator_nanopayment. "
            "Returns can_pay=false when budget is exhausted — stop the loop when this happens."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "campaign_id": {
                    "type": "integer",
                    "description": "Campaign ID",
                },
            },
            "required": ["campaign_id"],
        },
    },
}

PAY_CREATOR_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "pay_creator_nanopayment",
        "description": (
            "Pay an eligible creator via USDC nanopayment on Arc/Circle. "
            "amount_usdc is YOUR decision, not a fixed value — scale it with the creator's "
            "evaluate_creator score around the campaign's reward_per_creator baseline "
            "(e.g. score 50-69 -> pay less than baseline, 70-89 -> baseline, 90-100 -> pay more). "
            "The server still enforces the hard campaign budget regardless of what you request. "
            "ALWAYS check_budget before calling this. "
            "ALWAYS generate a fresh UUID v4 for intent_id. "
            "Creates a durable intent log before executing to ensure idempotency. "
            "Returns tx hash and receipt on success."
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
                    "description": "Creator Arc/Circle address or twitter_handle",
                },
                "amount_usdc": {
                    "type": "number",
                    "description": (
                        "Amount in USDC to send. Decide this based on the creator's score from "
                        "evaluate_creator relative to reward_per_creator — do not just copy "
                        "reward_per_creator for every creator."
                    ),
                },
            },
            "required": ["intent_id", "to", "amount_usdc"],
        },
    },
}

CREATOR_PAY_TOOLS: list[dict] = [
    DISCOVER_CREATORS_TOOL,
    EVALUATE_CREATOR_TOOL,
    CHECK_BUDGET_TOOL,
    PAY_CREATOR_TOOL,
]

# ---------------------------------------------------------------------------
# Executor factory — injeta contexto sensível sem expor ao modelo
# ---------------------------------------------------------------------------


def make_tool_executors(
    repo: "DatabaseRepository",
    arc_client: "ArcClient",
    campaign_id: int,
    budget_usdc: float,
    reward_per_creator: float = 5.0,
    spent_tracker: dict | None = None,
) -> dict:
    """
    Cria os executores com contexto injetado.

    Retorna dict {tool_name: async_callable(inputs, context) -> dict}.
    O `context` passado pelo engine pode conter flags como _budget_exhausted.

    `spent_tracker`: dict opcional {"usdc": float} compartilhado com outros conjuntos de
    tools (ex: cctp_tools.py) para que o orçamento da campanha seja único mesmo quando o
    agente tem tanto pay_creator_nanopayment (Arc) quanto payout_cross_chain_nanopayment
    (Solana/Stellar) disponíveis. Se omitido, cria um tracker isolado (comportamento
    original, sem mudança pros chamadores existentes).
    """
    # Rastreia gasto em memória durante o run (persiste no DB também)
    spent = spent_tracker if spent_tracker is not None else {"usdc": 0.0}

    async def discover_creators(inputs: dict, context: dict) -> dict:
        cid = inputs.get("campaign_id", campaign_id)
        limit = min(int(inputs.get("limit", 20)), 50)

        creators = await repo.get_campaign_participants(cid, limit=limit)
        LOG.info("[tool] discover_creators campaign=%d found=%d", cid, len(creators))
        return {"creators": creators, "count": len(creators), "campaign_id": cid}

    async def evaluate_creator(inputs: dict, context: dict) -> dict:
        creator_id = str(inputs.get("creator_id", "")).strip()
        cid = inputs.get("campaign_id", campaign_id)

        if not creator_id:
            return {"eligible": False, "reason": "creator_id is required"}

        # Already paid in this campaign?
        already_paid = await repo.get_payment_intent_by_creator(cid, creator_id)
        if already_paid:
            return {
                "creator_id": creator_id,
                "already_paid": True,
                "eligible": False,
                "score": 0,
                "reason": "already paid in this campaign",
            }

        participant = await repo.get_campaign_participant_by_creator(cid, creator_id)
        if not participant:
            return {
                "creator_id": creator_id,
                "eligible": False,
                "score": 0,
                "reason": "not enrolled in this campaign",
            }

        # Score calculation: 0-100
        score = 0
        if participant.get("has_followed"):
            score += 30
        if participant.get("has_replied"):
            score += 30
        if participant.get("has_retweeted"):
            score += 25
        if participant.get("status") == "tasks_verified":
            score += 15

        eligible = score >= 50

        LOG.info(
            "[tool] evaluate_creator creator=%s score=%d eligible=%s",
            creator_id,
            score,
            eligible,
        )
        return {
            "creator_id": creator_id,
            "score": score,
            "eligible": eligible,
            "has_followed": participant.get("has_followed"),
            "has_replied": participant.get("has_replied"),
            "has_retweeted": participant.get("has_retweeted"),
            "status": participant.get("status"),
            "already_paid": False,
        }

    async def check_budget(inputs: dict, context: dict) -> dict:
        remaining = budget_usdc - spent["usdc"]
        can_pay = remaining >= reward_per_creator
        exhausted = remaining <= 0

        LOG.info(
            "[tool] check_budget total=%.4f spent=%.4f remaining=%.4f can_pay=%s",
            budget_usdc,
            spent["usdc"],
            remaining,
            can_pay,
        )

        result = {
            "total_budget_usdc": budget_usdc,
            "spent_usdc": spent["usdc"],
            "remaining_usdc": remaining,
            "can_pay": can_pay,
            "reward_per_creator_usdc": reward_per_creator,
        }
        if exhausted:
            result["budget_exhausted"] = True
        return result

    async def pay_creator_nanopayment(inputs: dict, context: dict) -> dict:
        intent_id = str(inputs.get("intent_id", "")).strip()
        to = str(inputs.get("to", "")).strip()
        amount_usdc = float(inputs.get("amount_usdc", reward_per_creator))

        if not intent_id:
            intent_id = str(uuid.uuid4())
            LOG.warning("[tool] intent_id not provided — generated %s", intent_id)

        if not to:
            return {"error": "to address/handle is required"}

        # Guard: amount must be positive — a zero/negative amount would otherwise pass
        # the "amount_usdc > remaining" check below and, on success, *reduce* spent["usdc"]
        # (spent["usdc"] += amount_usdc), inflating the remaining budget for later payments.
        if amount_usdc <= 0:
            return {
                "error": "amount_usdc must be positive",
                "requested_usdc": amount_usdc,
            }

        # Idempotency: check if intent already exists
        existing = await repo.get_payment_intent(intent_id)
        if existing and existing.status in ("submitted", "confirmed"):
            LOG.info("[tool] duplicate intent %s — returning existing receipt", intent_id)
            return {
                "tx":          existing.arc_tx_hash,
                "receipt_pqc": existing.receipt_pqc or intent_id,
                "duplicate":   True,
                "amount_usdc": float(existing.amount_usdc),
                "to":          to,
            }

        # Guard: budget check + RESERVA atômica (sem await entre o check e o débito).
        # Reservar antes do rail — e não debitar só no sucesso — é o que permite o
        # engine executar tool calls em paralelo sem dois payouts passarem no check
        # com o mesmo saldo. Estornada no except em caso de falha.
        remaining = budget_usdc - spent["usdc"]
        if amount_usdc > remaining:
            return {
                "error": "insufficient_budget",
                "remaining_usdc": remaining,
                "requested_usdc": amount_usdc,
                "budget_exhausted": True,
            }
        spent["usdc"] += amount_usdc

        # 1. Write durable intent BEFORE executing (anti-replay)
        await repo.create_payment_intent(intent_id, campaign_id, to, amount_usdc)
        LOG.info(
            "[tool] intent created intent_id=%s to=%s amount=%.4f",
            intent_id,
            to,
            amount_usdc,
        )

        try:
            # 2. Resolve destino: "to" registrado como creator (handle) resolve para o
            # endereço EVM da wallet do creator. Desde que o onboarding passou a aceitar
            # endereço 0x direto (Connect Wallet), o valor registrado JÁ é o endereço EVM
            # na maioria dos casos — só quando é um Circle Wallet ID (UUID, fluxo legado
            # App Kit) que precisa do lookup via ArcClient.get_wallet_info(). Chamar
            # get_wallet_info() com um 0x… quebra (a Circle espera UUID no path, erro
            # 156009 "Fail to parse id as UUID"). Circle Payments API (transfer_usdc/
            # `/v1/transfers`) NÃO é usada aqui — retorna 403 Forbidden com credenciais de
            # Programmable Wallets (W3S) sandbox, produto incompatível.
            registered_wallet_id = _get_registered_wallet(to)
            if registered_wallet_id and registered_wallet_id.startswith("0x"):
                destination_address = registered_wallet_id
            elif registered_wallet_id:
                wallet_info = await arc_client.get_wallet_info(registered_wallet_id)
                destination_address = wallet_info.get("address", "")
                if not destination_address:
                    raise RuntimeError(f"no EVM address found for creator wallet={registered_wallet_id}")
            else:
                destination_address = to

            tx_hash = await arc_client.send_usdc(
                to_address=destination_address,
                amount_usdc=amount_usdc,
                idempotency_key=intent_id,
            )

            # 3. Assina recibo ML-DSA-87 com o tx_hash real
            receipt_pqc = _pqc_sign(intent_id, to, amount_usdc, tx_hash)

            # 4. Update status to submitted + persiste recibo PQC
            await repo.update_payment_intent(
                intent_id,
                status="submitted",
                tx_hash=tx_hash,
                receipt_pqc=receipt_pqc,
            )

            LOG.info(
                "[tool] payment sent intent=%s to=%s tx=%s amount=%.4f total_spent=%.4f",
                intent_id,
                to,
                tx_hash,
                amount_usdc,
                spent["usdc"],
            )

            return {
                "tx":          tx_hash,
                "receipt_pqc": receipt_pqc,
                "amount_usdc": amount_usdc,
                "to":          to,
                "status":      "submitted",
            }

        except Exception as exc:
            spent["usdc"] -= amount_usdc  # estorna a reserva — o pagamento não saiu
            await repo.update_payment_intent(intent_id, status="failed")
            LOG.error("[tool] payment failed intent=%s error=%s", intent_id, exc)
            return {
                "error": str(exc),
                "intent_id": intent_id,
                "status": "failed",
                "to": to,
            }

    return {
        "discover_creators": discover_creators,
        "evaluate_creator": evaluate_creator,
        "check_budget": check_budget,
        "pay_creator_nanopayment": pay_creator_nanopayment,
    }
