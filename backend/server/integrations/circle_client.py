"""
Circle Payments client — RFB-06 Creator Monetization.

Docs: https://developers.circle.com/reference

Endpoints usados:
  GET  /v1/wallets/{walletId}        — valida wallet de creator no registro
  GET  /v1/wallets/{walletId}/balances — consulta saldo USDC da wallet treasury
  POST /v1/transfers                  — envia USDC da wallet treasury para creator
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

import httpx

from server.settings import settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.circle.com"
_USDC_TOKEN_ID = "usd-coin"  # slug usado nos filtros de balance


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.circle_api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _is_configured() -> bool:
    return bool(settings.circle_api_key and settings.circle_platform_wallet_id)


# ── Wallet ─────────────────────────────────────────────────────────────────

async def get_wallet(wallet_id: str) -> dict[str, Any] | None:
    """
    Retorna os dados da wallet, {} se não foi possível verificar (erro de API),
    ou None apenas se a Circle retornar 404 explícito (carteira definitivamente inexistente).
    """
    if not settings.circle_api_key:
        return {}
    async with httpx.AsyncClient(base_url=_BASE_URL, timeout=8.0) as client:
        try:
            r = await client.get(f"/v1/wallets/{wallet_id}", headers=_headers())
            if r.status_code == 404:
                return None
            if not r.is_success:
                logger.warning("circle.get_wallet non-success status=%s — allowing registration", r.status_code)
                return {}
            return r.json().get("data") or {}
        except Exception as exc:
            logger.warning("circle.get_wallet failed: %s — allowing registration", exc)
            return {}


async def get_platform_balance_usdc() -> float:
    """Retorna saldo USDC disponível na wallet treasury da plataforma."""
    if not _is_configured():
        return 0.0
    async with httpx.AsyncClient(base_url=_BASE_URL, timeout=8.0) as client:
        try:
            r = await client.get(
                f"/v1/wallets/{settings.circle_platform_wallet_id}/balances",
                headers=_headers(),
            )
            r.raise_for_status()
            balances = r.json().get("data", {}).get("available", [])
            for b in balances:
                if b.get("currency") == "USD":
                    return float(b.get("amount", 0))
            return 0.0
        except Exception as exc:
            logger.warning("circle.get_platform_balance failed: %s", exc)
            return 0.0


# ── Transfers ──────────────────────────────────────────────────────────────

async def transfer_usdc(
    destination_wallet_id: str,
    amount_usdc: float,
    idempotency_key: str | None = None,
) -> dict[str, Any] | None:
    """
    Envia USDC da wallet treasury da plataforma para o creator.
    Retorna o objeto de transfer da Circle ou None em caso de falha.

    idempotency_key: usar intent_id do agente para evitar duplicatas.
    """
    if not _is_configured():
        logger.warning("circle.transfer_usdc: CIRCLE_API_KEY ou CIRCLE_WALLET_ID não configurados")
        return None

    payload = {
        "idempotencyKey": idempotency_key or str(uuid.uuid4()),
        "source": {
            "type": "wallet",
            "id": settings.circle_platform_wallet_id,
        },
        "destination": {
            "type": "wallet",
            "id": destination_wallet_id,
        },
        "amount": {
            "amount": f"{amount_usdc:.2f}",
            "currency": "USD",
        },
    }

    async with httpx.AsyncClient(base_url=_BASE_URL, timeout=15.0) as client:
        try:
            r = await client.post("/v1/transfers", json=payload, headers=_headers())
            r.raise_for_status()
            data = r.json().get("data")
            logger.info(
                "circle.transfer_usdc | to=%s | amount=%.2f | transfer_id=%s | status=%s",
                destination_wallet_id,
                amount_usdc,
                data.get("id") if data else "?",
                data.get("status") if data else "?",
            )
            return data
        except httpx.HTTPStatusError as exc:
            logger.error(
                "circle.transfer_usdc HTTP error: %s — %s",
                exc.response.status_code,
                exc.response.text,
            )
            return None
        except Exception as exc:
            logger.error("circle.transfer_usdc failed: %s", exc)
            return None
