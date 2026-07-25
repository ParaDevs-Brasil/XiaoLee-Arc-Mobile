"""
trust_routes.py — Endpoints de verificação PQC pública.

Qualquer pessoa pode verificar um recibo de pagamento do XiaoLee Agent
sem depender de nenhuma infraestrutura do XiaoLee — basta a public key
(disponível em GET /v1/trust/public-key) e a biblioteca dilithium-py.

Rotas:
    GET  /v1/trust/public-key        → public key ML-DSA-87 em base64
    POST /v1/trust/verify-receipt    → verifica um receipt_pqc
    GET  /v1/trust/healthcheck       → confirma que PQC está ativo
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field

LOG = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/trust", tags=["trust"])


# ── Schemas ────────────────────────────────────────────────────────────────


class VerifyRequest(BaseModel):
    receipt_pqc: str = Field(
        ...,
        description="Campo receipt_pqc retornado pelo pay_creator_nanopayment",
        min_length=10,
    )
    public_key_b64: str = Field(
        default="",
        description=(
            "Public key ML-DSA-87 em base64 para verificação independente. "
            "Se vazio, usa a chave carregada do env (PQC_PUBLIC_KEY)."
        ),
    )


class VerifyResponse(BaseModel):
    valid:         bool
    payload:       dict | None = None
    error:         str | None  = None
    algo:          str
    verified_with: str | None  = None


class PublicKeyResponse(BaseModel):
    algo:           str
    public_key_b64: str
    key_size_bytes: int


# ── Handlers ───────────────────────────────────────────────────────────────


@router.get("/public-key", response_model=PublicKeyResponse)
async def get_public_key():
    """
    Retorna a public key ML-DSA-87 do XiaoLee Agent Signer.

    Use esta chave para verificar receipts independentemente, sem precisar
    chamar nenhum endpoint do XiaoLee — apenas dilithium-py localmente.

    Armazene esta chave junto com os receipts para auditoria futura.
    """
    try:
        from services.pqc_receipt import public_key_b64
        pk_b64 = public_key_b64()
        import base64
        return PublicKeyResponse(
            algo="ML-DSA-87",
            public_key_b64=pk_b64,
            key_size_bytes=len(base64.b64decode(pk_b64)),
        )
    except Exception as exc:
        LOG.error("[trust] public-key error: %s", exc)
        raise HTTPException(status_code=503, detail=f"PQC não disponível: {exc}")


@router.post("/verify-receipt", response_model=VerifyResponse)
async def verify_receipt(req: VerifyRequest):
    """
    Verifica um receipt_pqc ML-DSA-87.

    O receipt_pqc é retornado pelo agente em cada pagamento USDC confirmado.
    Inclui a assinatura e o payload canônico (intent_id, to, amount, tx_hash, ts).

    Tamper-proof: qualquer alteração no payload invalida a assinatura.
    Post-quantum: resistente a ataques de computadores quânticos (FIPS 204).
    """
    try:
        from services.pqc_receipt import verify_receipt as _verify
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="dilithium-py não instalado — PQC indisponível neste servidor",
        )

    result = _verify(req.receipt_pqc, req.public_key_b64)

    return VerifyResponse(
        valid=result["valid"],
        payload=result.get("payload"),
        error=result.get("error"),
        algo=result.get("algo", "ML-DSA-87"),
        verified_with=result.get("verified_with"),
    )


@router.get("/healthcheck")
async def trust_healthcheck():
    """Status do subsistema PQC — inclui tamanho das chaves e algoritmo."""
    try:
        from services.pqc_receipt import public_key_b64, _load_keypair
        import base64
        import os

        pk_b64  = public_key_b64()
        pk, sk  = _load_keypair()
        has_env = bool(os.getenv("PQC_SECRET_KEY"))

        return {
            "ok":              True,
            "algo":            "ML-DSA-87",
            "fips":            "204",
            "pk_size_bytes":   len(pk),
            "sk_size_bytes":   len(sk),
            "pk_b64_preview":  pk_b64[:20] + "...",
            "key_source":      "env" if has_env else "ephemeral",
            "warning":         None if has_env else (
                "Keypair efêmero — assinaturas não verificáveis após restart. "
                "Configure PQC_SECRET_KEY e PQC_PUBLIC_KEY em produção."
            ),
        }
    except Exception as exc:
        LOG.error("[trust] healthcheck error: %s", exc)
        return {"ok": False, "error": str(exc)}
