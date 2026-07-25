"""
arc_routes.py — Rotas Circle/Arc: wallet info, saldo USDC, bridge CCTP.

Endpoints:
    GET  /v1/arc/wallet          → info da wallet do agente (endereço, saldo)
    POST /v1/arc/cctp/bridge     → inicia bridge USDC de outra chain para Arc
    GET  /v1/arc/cctp/status/{msg_hash} → status de um bridge em andamento

CCTP é protegido por flag CCTP_ENABLED — retorna 503 se desabilitado.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from server.integrations.arc_client import ArcClient
from server.settings import settings

LOG = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/arc", tags=["arc"])

# Every connected wallet polls these idempotent, read-only methods on its own
# timer (chain id, gas price, latest block, balance) — with many browser tabs
# sharing the single upstream Canteen RPC token, the duplicate traffic alone
# is enough to trip its rate limit and MetaMask's own "-32002 too many
# errors" breaker. Short TTL cache keyed by (method, params) cuts that
# duplicate load; safe with a single backend worker (in-process, no
# cross-worker staleness).
_RPC_CACHE_TTL: dict[str, float] = {
    "eth_chainId": 300.0,
    "eth_gasPrice": 3.0,
    "eth_blockNumber": 2.0,
    "eth_feeHistory": 3.0,
    "eth_getBalance": 2.0,
    "eth_getBlockByNumber": 2.0,
}
_rpc_cache: dict[tuple[str, str], tuple[float, object]] = {}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _arc_client() -> ArcClient:
    return ArcClient(
        api_key=settings.circle_api_key,
        wallet_id=settings.circle_wallet_id,
        blockchain=settings.circle_blockchain,
        usdc_token_id=settings.circle_usdc_token_id,
        sandbox=settings.arc_sandbox,
    )


def _cctp_client():
    from server.integrations.cctp_client import CCTPClient
    return CCTPClient(
        source_rpc=settings.cctp_source_rpc,
        arc_rpc=settings.arc_rpc_url,
        signer_key=settings.cctp_signer_private_key,
        sandbox=settings.arc_sandbox,
    )


# ---------------------------------------------------------------------------
# Wallet
# ---------------------------------------------------------------------------


@router.get("/wallet")
async def get_agent_wallet():
    """
    Retorna endereço EVM e saldo USDC da wallet do agente.
    Útil para verificar se o setup Circle está correto antes de rodar campanha.
    """
    arc = _arc_client()
    try:
        info    = await arc.get_wallet_info()
        balance = await arc.get_usdc_balance()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return {
        "wallet_id":   arc.wallet_id,
        "address":     info.get("address", ""),
        "blockchain":  info.get("blockchain", arc.blockchain),
        "state":       info.get("state", "UNKNOWN"),
        "usdc_balance": balance,
        "sandbox":     arc.sandbox,
    }


@router.get("/wallet/balance")
async def get_agent_balance():
    """Saldo USDC disponível (rota rápida para o dashboard Traction)."""
    arc = _arc_client()
    try:
        balance = await arc.get_usdc_balance()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return {"usdc_balance": balance, "sandbox": arc.sandbox}


@router.get("/chain-config")
async def get_chain_config(request: Request):
    """Config da chain Arc para a wallet (wallet_switchEthereumChain / addEthereumChain).

    rpcUrls aponta para o NOSSO proxy (/v1/arc/rpc), não para o RPC autenticado do
    Canteen: a MetaMask fala com o RPC direto do navegador para estimar fee/saldo, e o
    RPC do Canteen (com token na URL) não é utilizável pelo browser — daí "Network fee:
    Unavailable". O proxy repassa com o token server-side.
    """
    if not settings.arc_chain_id:
        raise HTTPException(status_code=503, detail="ARC_CHAIN_ID not configured")
    proxy_url = str(request.base_url).rstrip("/") + "/v1/arc/rpc"
    return {
        "chainIdHex": hex(settings.arc_chain_id),
        "chainId": settings.arc_chain_id,
        "chainName": "Arc Testnet",
        "rpcUrls": [proxy_url],
        "blockExplorerUrls": ["https://testnet.arcscan.app"],
        "nativeCurrency": {"name": "USDC", "symbol": "USDC", "decimals": 18},
    }


@router.post("/rpc")
async def arc_rpc_proxy(request: Request):
    """Proxy JSON-RPC para o RPC do Arc (Canteen), adicionando o token server-side.

    A wallet do usuário (MetaMask/Rabby) usa esta URL como RPC da rede Arc, então
    consegue estimar fee, ler saldo e enviar tx sem precisar do RPC autenticado
    (que não é alcançável/utilizável pelo navegador)."""
    if not settings.arc_rpc_url:
        raise HTTPException(status_code=503, detail="ARC_RPC_URL not configured")
    import httpx

    raw_body = await request.body()
    try:
        payload = json.loads(raw_body)
    except ValueError:
        payload = None

    method = payload.get("method") if isinstance(payload, dict) else None
    ttl = _RPC_CACHE_TTL.get(method) if method else None
    cache_key = (method, json.dumps(payload.get("params"), sort_keys=True)) if ttl else None

    if cache_key:
        cached = _rpc_cache.get(cache_key)
        if cached and cached[0] > time.monotonic():
            body = json.dumps({"jsonrpc": "2.0", "id": payload.get("id"), "result": cached[1]}).encode()
            return Response(content=body, media_type="application/json")

    async def _forward() -> "httpx.Response":
        async with httpx.AsyncClient(timeout=20) as client:
            return await client.post(
                settings.arc_rpc_url,
                content=raw_body,
                headers={"Content-Type": "application/json"},
            )

    try:
        upstream = await _forward()
        if upstream.status_code >= 500:
            await asyncio.sleep(0.3)
            upstream = await _forward()
    except Exception as exc:
        LOG.warning("arc rpc proxy failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"arc rpc proxy failed: {exc}")

    if cache_key and upstream.status_code == 200:
        try:
            data = upstream.json()
        except ValueError:
            data = {}
        if "result" in data:
            _rpc_cache[cache_key] = (time.monotonic() + ttl, data["result"])

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type="application/json",
    )


@router.get("/gas-fees")
async def get_gas_fees():
    """Fee EIP-1559 atual do Arc para a wallet incluir na tx.

    Wallets (MetaMask/Rabby) mostram "Network fee: Unavailable" e travam a
    assinatura quando não conseguem estimar o fee numa testnet custom. Com
    maxFeePerGas/maxPriorityFeePerGas explícitos no payload, elas não precisam estimar.
    """
    if not settings.arc_rpc_url:
        raise HTTPException(status_code=503, detail="ARC_RPC_URL not configured")
    try:
        import asyncio

        def _read() -> dict:
            from web3 import Web3

            w3 = Web3(Web3.HTTPProvider(settings.arc_rpc_url, request_kwargs={"timeout": 15}))
            blk = w3.eth.get_block("latest")
            base = blk.get("baseFeePerGas") or w3.eth.gas_price
            try:
                priority = w3.eth.max_priority_fee
            except Exception:
                priority = int(2e9)  # 2 gwei fallback
            # margem: cobre 2 subidas de base fee + priority
            max_fee = base * 2 + priority
            return {"maxFeePerGas": max_fee, "maxPriorityFeePerGas": priority}

        fees = await asyncio.to_thread(_read)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"arc fee read failed: {exc}")

    return {
        "maxFeePerGasHex": hex(fees["maxFeePerGas"]),
        "maxPriorityFeePerGasHex": hex(fees["maxPriorityFeePerGas"]),
        "maxFeePerGas": fees["maxFeePerGas"],
        "maxPriorityFeePerGas": fees["maxPriorityFeePerGas"],
    }


@router.get("/balance/{address}")
async def get_address_balance(address: str):
    """Saldo USDC on-chain de QUALQUER endereço 0x no Arc (leitura direta no RPC).

    Usado pela tela XiaoLee Wallet e pelo chat para mostrar o saldo da wallet
    conectada do usuário — não confundir com /wallet/balance (treasury do agente).
    """
    import re as _re

    if not _re.fullmatch(r"0x[0-9a-fA-F]{40}", address):
        raise HTTPException(status_code=422, detail="address must be a 0x EVM address")
    if not settings.arc_rpc_url or not settings.arc_usdc_address:
        raise HTTPException(status_code=503, detail="ARC_RPC_URL/ARC_USDC_ADDRESS not configured")

    try:
        balance = await read_arc_usdc_balance(address)
    except Exception as exc:
        LOG.warning("arc.balance read failed for %s: %s", address, exc)
        raise HTTPException(status_code=503, detail=f"arc rpc read failed: {exc}")

    return {"address": address, "chain": "arc", "usdc_balance": balance}


async def read_arc_usdc_balance(address: str) -> float:
    """Lê o saldo USDC (6 decimais) de um endereço 0x direto no RPC do Arc.

    Reutilizada pela rota acima e pela tool agêntica do chat (orchestration).
    """
    import asyncio

    def _read() -> float:
        from web3 import Web3

        w3 = Web3(Web3.HTTPProvider(settings.arc_rpc_url, request_kwargs={"timeout": 15}))
        erc20_abi = [{
            "name": "balanceOf", "type": "function", "stateMutability": "view",
            "inputs": [{"name": "account", "type": "address"}],
            "outputs": [{"name": "", "type": "uint256"}],
        }]
        usdc = w3.eth.contract(
            address=Web3.to_checksum_address(settings.arc_usdc_address), abi=erc20_abi
        )
        raw = usdc.functions.balanceOf(Web3.to_checksum_address(address)).call()
        return raw / 1_000_000

    return await asyncio.to_thread(_read)


# ---------------------------------------------------------------------------
# CCTP bridge
# ---------------------------------------------------------------------------


class BridgeRequest(BaseModel):
    amount_usdc: float
    recipient:   str          # endereço EVM no Arc que receberá o USDC
    source_rpc:  str = ""     # sobrescreve env CCTP_SOURCE_RPC se fornecido


class BridgeResponse(BaseModel):
    source_tx_hash: str
    arc_tx_hash:    str
    amount_usdc:    float
    recipient:      str
    message_hash:   str
    sandbox:        bool


@router.post("/cctp/bridge", response_model=BridgeResponse)
async def cctp_bridge(payload: BridgeRequest):
    """
    Faz bridge de USDC de uma chain EVM para o Arc via CCTP.

    Requer CCTP_ENABLED=true e variáveis de ambiente configuradas.
    Em sandbox (ARC_SANDBOX=true), simula o bridge sem chamadas on-chain.
    """
    if not settings.cctp_enabled and not settings.arc_sandbox:
        raise HTTPException(
            status_code=503,
            detail="CCTP não habilitado. Configure CCTP_ENABLED=true no .env.",
        )

    if payload.amount_usdc <= 0:
        raise HTTPException(status_code=400, detail="amount_usdc deve ser positivo")

    if not payload.recipient or not payload.recipient.startswith("0x"):
        raise HTTPException(status_code=400, detail="recipient deve ser um endereço EVM 0x...")

    cctp = _cctp_client()
    if payload.source_rpc:
        cctp.source_rpc = payload.source_rpc

    try:
        result = await cctp.bridge_usdc_to_arc(
            amount_usdc=payload.amount_usdc,
            recipient=payload.recipient,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc))

    return BridgeResponse(
        source_tx_hash=result.source_tx_hash,
        arc_tx_hash=result.arc_tx_hash,
        amount_usdc=result.amount_usdc,
        recipient=result.recipient,
        message_hash=result.message_hash,
        sandbox=result.sandbox,
    )


@router.get("/cctp/status/{message_hash}")
async def cctp_attestation_status(message_hash: str):
    """
    Consulta o status de attestation Circle para um bridge em andamento.
    Retorna o estado da iris-api (pending | complete) sem aguardar.
    """
    import httpx as _httpx

    iris = (
        "https://iris-api-sandbox.circle.com/v1/attestations"
        if settings.arc_sandbox
        else "https://iris-api.circle.com/v1/attestations"
    )

    try:
        async with _httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{iris}/{message_hash}")
            if resp.status_code == 404:
                return {"status": "pending", "message_hash": message_hash}
            if not resp.is_success:
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"iris-api error: {resp.text[:200]}",
                )
            return resp.json() | {"message_hash": message_hash}
    except _httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail=f"iris-api unreachable: {exc}")


# ---------------------------------------------------------------------------
# Healthcheck Circle API
# ---------------------------------------------------------------------------


@router.get("/healthcheck")
async def arc_healthcheck():
    """Valida conectividade com a Circle API e configuração do cliente."""
    arc = _arc_client()

    if arc.sandbox:
        return {
            "ok":       True,
            "sandbox":  True,
            "message":  "ARC_SANDBOX=true — Circle API não é chamada",
            "wallet_id": arc.wallet_id or "(não configurado)",
        }

    if not arc.api_key:
        return {"ok": False, "sandbox": False, "message": "CIRCLE_API_KEY não configurada"}

    try:
        info = await arc.get_wallet_info()
        return {
            "ok":        True,
            "sandbox":   False,
            "address":   info.get("address", ""),
            "state":     info.get("state", "UNKNOWN"),
            "blockchain": info.get("blockchain", arc.blockchain),
        }
    except RuntimeError as exc:
        return {"ok": False, "sandbox": False, "message": str(exc)}
