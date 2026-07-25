"""
cctp_routes.py — Rotas de operação para o CCTP multi-chain (Solana + Stellar reais).

Endpoints:
    GET /v1/cctp/treasury/{chain}/balance  → saldo USDC da tesouraria (solana | stellar)
    GET /v1/cctp/healthcheck               → status agregado das duas chains

Protegido por SOLANA_CCTP_ENABLED / STELLAR_CCTP_ENABLED — retorna 503 se desabilitado
(mesmo padrão de CCTP_ENABLED em arc_routes.py). Nunca expõe a chave de tesouraria, só o
endereço derivado.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from server.settings import settings

LOG = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/cctp", tags=["cctp"])


def _solana_client():
    from server.integrations.solana_cctp import SolanaCCTPClient
    return SolanaCCTPClient(
        rpc_url=settings.solana_rpc_url,
        treasury_keypair_b58=settings.solana_treasury_keypair_b58,
        usdc_mint=settings.solana_usdc_mint,
        sandbox=settings.bridge_sandbox,
    )


def _stellar_client():
    from server.integrations.stellar_cctp import StellarCCTPClient
    return StellarCCTPClient(
        treasury_secret=settings.stellar_treasury_secret,
        network=settings.stellar_network,
        sandbox=settings.bridge_sandbox,
    )


@router.get("/treasury/{chain}/balance")
async def treasury_balance(chain: str):
    chain = chain.lower()
    if chain == "solana":
        if not settings.solana_cctp_enabled and not settings.bridge_sandbox:
            raise HTTPException(status_code=503, detail="SOLANA_CCTP_ENABLED=false")
        client = _solana_client()
        try:
            balance = await client.get_usdc_balance()
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        return {"chain": "solana", "address": client.address, "usdc_balance": balance, "sandbox": client.sandbox}

    if chain == "stellar":
        if not settings.stellar_cctp_enabled and not settings.bridge_sandbox:
            raise HTTPException(status_code=503, detail="STELLAR_CCTP_ENABLED=false")
        client = _stellar_client()
        return {"chain": "stellar", "address": client.address, "sandbox": client.sandbox}

    raise HTTPException(status_code=400, detail="chain must be 'solana' or 'stellar'")


@router.get("/healthcheck")
async def cctp_healthcheck():
    """Status agregado das tesourarias Solana e Stellar (não falha se uma estiver desabilitada)."""
    solana_health: dict = {"enabled": settings.solana_cctp_enabled}
    stellar_health: dict = {"enabled": settings.stellar_cctp_enabled}

    if settings.solana_cctp_enabled or settings.bridge_sandbox:
        solana_health.update(await _solana_client().healthcheck())
    if settings.stellar_cctp_enabled or settings.bridge_sandbox:
        stellar_health.update(await _stellar_client().healthcheck())

    return {"solana": solana_health, "stellar": stellar_health, "sandbox": settings.bridge_sandbox}
