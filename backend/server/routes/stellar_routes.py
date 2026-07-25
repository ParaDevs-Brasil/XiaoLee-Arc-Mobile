"""
stellar_routes.py — Endpoints diretos de operações Stellar (sem AI intermediária).

GET  /stellar/swap/quote          — quote + XDR assinável para pathPaymentStrictSend
GET  /stellar/anchor/info         — assets e endpoints da âncora testanchor.stellar.org
GET  /stellar/anchor/challenge    — challenge SEP-10 da âncora (proxy)
POST /stellar/anchor/deposit      — inicia depósito SEP-24 interativo via testanchor
"""

from __future__ import annotations

import logging
import os

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from server.integrations.stellar_adapter import StellarAdapter

# testanchor.stellar.org — âncora oficial SDF no testnet, sem cadastro
TESTANCHOR_DOMAIN = "testanchor.stellar.org"
TESTANCHOR_AUTH = f"https://{TESTANCHOR_DOMAIN}/auth"
TESTANCHOR_SEP24 = f"https://{TESTANCHOR_DOMAIN}/sep24"

LOG = logging.getLogger(__name__)

router = APIRouter(prefix="/stellar", tags=["stellar"])


@router.get("/swap/quote")
async def get_swap_quote(
    wallet: str = Query(..., description="Endereço Stellar G... do usuário"),
    from_asset: str = Query("XLM"),
    to_asset: str = Query("USDC"),
    amount: float = Query(10.0, gt=0),
):
    """
    Consulta o Stellar DEX via Horizon e retorna quote + XDR não assinado.
    O frontend assina o XDR com Freighter e submete ao Horizon.

    Retorna:
        quote.source_amount     — quanto o usuário envia
        quote.destination_amount — quanto o usuário recebe (~, com slippage 1%)
        xdr                     — XDR da transação (None se sem liquidez)
        network_passphrase      — para o signTransaction do Freighter
        has_liquidity           — se há path disponível
    """
    network = os.getenv("STELLAR_NETWORK", "testnet")
    adapter = StellarAdapter(network=network)

    quote = await adapter.prepare_swap(
        wallet=wallet,
        from_asset=from_asset,
        to_asset=to_asset,
        amount=amount,
    )

    xdr = None
    if quote.destination_amount > 0:
        try:
            xdr = await adapter.build_swap_xdr(
                wallet=wallet,
                from_asset=from_asset,
                to_asset=to_asset,
                send_amount=quote.source_amount,
                min_dest_amount=quote.destination_amount * 0.99,
            )
        except Exception as exc:
            LOG.warning("[stellar/swap] build_swap_xdr failed: %s", exc)

    network_passphrase = (
        "Test SDF Network ; September 2015"
        if network == "testnet"
        else "Public Global Stellar Network ; September 2015"
    )

    return {
        "quote": {
            "from": from_asset,
            "to": to_asset,
            "source_amount": quote.source_amount,
            "destination_amount": quote.destination_amount,
            "fee_xlm": quote.fee_xlm,
            "path": quote.path,
        },
        "xdr": xdr,
        "network_passphrase": network_passphrase,
        "has_liquidity": quote.destination_amount > 0,
    }


# ---------------------------------------------------------------------------
# Anchor SEP-24 — testanchor.stellar.org (âncora oficial SDF no testnet)
# ---------------------------------------------------------------------------

@router.get("/anchor/info")
async def get_anchor_info():
    """
    Retorna assets suportados e endpoints da âncora testanchor.stellar.org.
    Não requer autenticação.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{TESTANCHOR_SEP24}/info")
            resp.raise_for_status()
            info = resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"testanchor indisponível: {exc}") from exc

    return {
        "anchor": TESTANCHOR_DOMAIN,
        "network": "testnet",
        "auth_endpoint": TESTANCHOR_AUTH,
        "sep24_endpoint": TESTANCHOR_SEP24,
        "deposit": info.get("deposit", {}),
        "withdraw": info.get("withdraw", {}),
    }


@router.get("/anchor/challenge")
async def get_anchor_challenge(
    account: str = Query(..., description="Endereço Stellar G... do usuário"),
):
    """
    Obtém o challenge SEP-10 da âncora testanchor para o account informado.
    O frontend assina o XDR retornado com Freighter e envia para /anchor/deposit.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(TESTANCHOR_AUTH, params={"account": account})
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Erro ao obter challenge: {exc}") from exc


class AnchorDepositRequest(BaseModel):
    account: str
    signed_xdr: str
    asset_code: str = "SRT"  # testanchor supports: SRT, native, USDC


@router.post("/anchor/deposit")
async def initiate_anchor_deposit(body: AnchorDepositRequest):
    """
    Fluxo SEP-24 completo:
      1. Troca o XDR assinado (SEP-10) por JWT da âncora testanchor
      2. Inicia depósito interativo com o JWT — retorna URL da UI da âncora
    O frontend abre a URL para o usuário completar o depósito.
    """
    async with httpx.AsyncClient(timeout=15) as client:
        # Step 1 — SEP-10: exchange signed XDR for anchor JWT
        try:
            token_resp = await client.post(
                TESTANCHOR_AUTH,
                json={"transaction": body.signed_xdr},
            )
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"SEP-10 conexão falhou: {exc}") from exc

        if not token_resp.is_success:
            err_body = token_resp.text
            LOG.error("[anchor/deposit] SEP-10 failed %d: %s", token_resp.status_code, err_body)
            raise HTTPException(
                status_code=502,
                detail=f"SEP-10 falhou ({token_resp.status_code}): {err_body}",
            )

        token_data = token_resp.json()
        anchor_jwt = token_data.get("token")
        if not anchor_jwt:
            raise HTTPException(status_code=502, detail=f"testanchor não retornou JWT: {token_data}")

        # Step 2 — SEP-24 interactive deposit
        # testanchor requires multipart/form-data (not x-www-form-urlencoded)
        # amount=5 fits testanchor's min_amount=1, max_amount=10
        deposit_files = {
            "asset_code": (None, body.asset_code),
            "amount": (None, "5"),
        }

        try:
            deposit_resp = await client.post(
                f"{TESTANCHOR_SEP24}/transactions/deposit/interactive",
                headers={"Authorization": f"Bearer {anchor_jwt}"},
                files=deposit_files,
            )
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"SEP-24 conexão falhou: {exc}") from exc

        if not deposit_resp.is_success:
            err_body = deposit_resp.text
            LOG.error("[anchor/deposit] SEP-24 failed %d: %s", deposit_resp.status_code, err_body)
            raise HTTPException(
                status_code=502,
                detail=f"testanchor SEP-24 ({deposit_resp.status_code}): {err_body}",
            )

        result = deposit_resp.json()

    return {
        "url": result.get("url"),
        "id": result.get("id"),
        "type": result.get("type"),
        "anchor": TESTANCHOR_DOMAIN,
        "asset_code": body.asset_code,
    }
