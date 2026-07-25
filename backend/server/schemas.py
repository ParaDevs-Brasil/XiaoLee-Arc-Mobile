from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class InboundMessage(BaseModel):
    platform: str = Field(description="telegram | x")
    user_id: str
    username: Optional[str] = None
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IntentRequest(BaseModel):
    user_id: str
    text: str


class IntentResponse(BaseModel):
    action: str
    confidence: float
    entities: Dict[str, Any] = Field(default_factory=dict)


class OrchestrationResponse(BaseModel):
    platform: str
    user_id: str
    intent: IntentResponse
    reply_text: str
    execution: Dict[str, Any] = Field(default_factory=dict)


class SwapPrepareRequest(BaseModel):
    user_public_key: str
    input_mint: str
    output_mint: str
    amount_raw: int
    slippage_bps: int = 50


class SwapPrepareResponse(BaseModel):
    cluster: str
    quote: Dict[str, Any]
    swap_transaction_base64: str
    last_valid_block_height: Optional[int] = None
    disclaimer: str


# ── Traction / RFB-06 ─────────────────────────────────────────────────────

class PaymentSettledEvent(BaseModel):
    """Evento emitido pelo agente ao confirmar pagamento USDC on-chain."""
    intent_id: str = Field(description="ID da intenção que gerou o pagamento")
    # allow_inf_nan=False: Infinity passaria em `gt=0` (inf > 0) e corromperia
    # permanentemente o total acumulado em server/metrics.py (_usdc_total += inf).
    amount: float = Field(gt=0, allow_inf_nan=False, description="Valor em USDC")
    creator: str = Field(description="@handle do creator")
    tx: str = Field(description="Hash da transação on-chain")
    ts: Optional[str] = Field(default=None, description="ISO timestamp (preenchido pelo backend se omitido)")
    latency_ms: float = Field(default=0.0, ge=0, description="Latência da confirmação em ms")


class TractionSnapshot(BaseModel):
    total_usdc: float
    total_payments: int
    active_creators: int
    registered_creators: int = 0
    avg_latency_ms: float
    p95_latency_ms: float
    feed: list[Dict[str, Any]]


class CreatorRegisterRequest(BaseModel):
    twitter_handle: str = Field(description="@handle do creator no X/Twitter")
    # Legado — mantido para compat; o endereço agora vem de wallet_address (wallet conectada)
    circle_wallet_id: Optional[str] = Field(default=None, description="Legado: endereço/Circle wallet ID")
    # Prova de posse: assinatura da wallet conectada (impede registrar endereço de terceiros).
    wallet_address: Optional[str] = Field(default=None, description="Endereço nativo da wallet conectada")
    chain: Optional[str] = Field(default=None, description="arc | solana | stellar")
    signed_message: Optional[str] = Field(default=None, description="Mensagem-desafio assinada pela wallet")
    signature: Optional[str] = Field(default=None, description="Assinatura da mensagem (hex EIP-191 ou base64 Ed25519)")
    proof_encoding: Optional[str] = Field(default=None, description="eip191 | base64")
