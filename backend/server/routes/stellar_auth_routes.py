"""
stellar_auth_routes.py — SEP-10 authentication endpoints.

Implementa o fluxo não-custodial de autenticação Stellar (ADR-002 / PDR-005):
    GET  /auth/stellar/challenge?account=G...  — emite challenge XDR
    POST /auth/stellar/token                   — valida XDR assinado, emite JWT

O servidor mantém um keypair dedicado (STELLAR_SERVER_SECRET) apenas para
challenges — nunca usado para fundos.

JWT emitido: { sub: account, stellar_wallet: account, chain: "stellar", exp }
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import secrets
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

LOG = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/stellar", tags=["stellar-auth"])

# ---------------------------------------------------------------------------
# Stellar SDK optional import — graceful fallback para testes sem a lib
# ---------------------------------------------------------------------------

def _load_stellar_sdk():
    try:
        from stellar_sdk import Keypair, Network, TransactionEnvelope
        from stellar_sdk.sep.stellar_web_authentication import (
            build_challenge_transaction,
            read_challenge_transaction,
            verify_challenge_transaction_signed_by_client_master_key,
        )
        return Keypair, Network, TransactionEnvelope, build_challenge_transaction, read_challenge_transaction, verify_challenge_transaction_signed_by_client_master_key
    except ImportError:
        return None


_SDK = _load_stellar_sdk()

# ---------------------------------------------------------------------------
# Settings — lidos do environment
# ---------------------------------------------------------------------------

def _server_secret() -> str:
    return os.getenv("STELLAR_SERVER_SECRET", "")


def _jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET", "")
    if not secret:
        raise RuntimeError(
            "JWT_SECRET environment variable is required but not set. "
            "Set a strong random value (e.g. `openssl rand -hex 32`) before starting the server."
        )
    return secret


def _network() -> str:
    return os.getenv("STELLAR_NETWORK", "testnet")


def _home_domain() -> str:
    return os.getenv("STELLAR_HOME_DOMAIN", "xiaolee.io")


# ---------------------------------------------------------------------------
# JWT (minimal — PyJWT or manual HMAC)
# ---------------------------------------------------------------------------

def _issue_jwt(account: str, expires_in: int = 86400) -> str:
    """Issues a compact JWT signed with HMAC-SHA256. Uses PyJWT if available."""
    try:
        import jwt as pyjwt
        now = int(time.time())
        payload = {
            "sub": account,
            "stellar_wallet": account,
            "chain": "stellar",
            "iat": now,
            "exp": now + expires_in,
        }
        return pyjwt.encode(payload, _jwt_secret(), algorithm="HS256")
    except ImportError:
        pass

    # Manual fallback — base64url(header).base64url(payload).signature
    import json as _json

    def _b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    header = _b64url(_json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    now = int(time.time())
    payload_data = {
        "sub": account,
        "stellar_wallet": account,
        "chain": "stellar",
        "iat": now,
        "exp": now + expires_in,
    }
    payload = _b64url(_json.dumps(payload_data).encode())
    signing_input = f"{header}.{payload}".encode()
    sig = hmac.new(_jwt_secret().encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64url(sig)}"


# ---------------------------------------------------------------------------
# Challenge store (in-memory, TTL 5 min, hard cap 5 000 entries)
# ---------------------------------------------------------------------------
# SEC-020: bounded to prevent unbounded memory growth under enumeration attacks.
# On each store() call expired entries are swept first; if the dict is still at
# capacity after the sweep a 429 is returned by the caller.
# ---------------------------------------------------------------------------

_challenges: dict[str, tuple[str, float]] = {}  # account → (nonce, expires_at)
_CHALLENGE_MAX = 5_000


def _sweep_expired_challenges() -> None:
    now = time.time()
    expired = [acct for acct, (_, exp) in _challenges.items() if now > exp]
    for acct in expired:
        _challenges.pop(acct, None)


def _store_challenge(account: str, nonce: str, ttl: int = 300) -> bool:
    """Stores a challenge. Returns False if the store is full after sweeping expired entries."""
    if account not in _challenges and len(_challenges) >= _CHALLENGE_MAX:
        _sweep_expired_challenges()
        if len(_challenges) >= _CHALLENGE_MAX:
            LOG.warning("[SEP-10] challenge store at capacity (%d) — rejecting new challenge", _CHALLENGE_MAX)
            return False
    _challenges[account] = (nonce, time.time() + ttl)
    return True


def _pop_challenge(account: str) -> Optional[str]:
    entry = _challenges.pop(account, None)
    if not entry:
        return None
    nonce, expires_at = entry
    if time.time() > expires_at:
        return None
    return nonce


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


class TokenRequest(BaseModel):
    account: str
    transaction: str  # base64-encoded signed XDR


class TokenResponse(BaseModel):
    token: str
    account: str
    chain: str = "stellar"


def _validate_stellar_account(account: str) -> None:
    """Validates Stellar account format using SDK checksum when available."""
    if not account.startswith("G") or len(account) != 56:
        raise HTTPException(status_code=400, detail="Invalid Stellar account format")
    sdk = _load_stellar_sdk()
    if sdk:
        Keypair = sdk[0]
        try:
            Keypair.from_public_key(account)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid Stellar account format")


@router.get("/challenge")
async def get_challenge(account: str = Query(..., description="Stellar public key G...")):
    """
    SEP-10 step 1: emite challenge transaction XDR para o account informado.
    O frontend deve ter o Freighter assinar este XDR e enviar para /auth/stellar/token.
    """
    _validate_stellar_account(account)

    nonce = secrets.token_hex(32)
    if not _store_challenge(account, nonce):
        raise HTTPException(status_code=429, detail="Too many pending challenges. Try again later.")

    sdk = _load_stellar_sdk()
    if sdk is None:
        # stellar-sdk não instalado — retorna challenge simplificado para dev
        LOG.warning("[SEP-10] stellar-sdk not installed, returning mock challenge")
        mock_xdr = base64.b64encode(f"mock-challenge:{account}:{nonce}".encode()).decode()
        return {
            "transaction": mock_xdr,
            "network_passphrase": "Test SDF Network ; September 2015",
            "note": "Install stellar-sdk for real SEP-10 challenges",
        }

    Keypair, Network, TransactionEnvelope, build_challenge_transaction, _read_fn, _verify_fn = sdk

    server_secret = _server_secret()
    if not server_secret:
        LOG.error("[SEP-10] STELLAR_SERVER_SECRET not configured — cannot issue challenge")
        raise HTTPException(
            status_code=503,
            detail="Authentication service temporarily unavailable: server secret not configured.",
        )
    server_kp = Keypair.from_secret(server_secret)

    network = _network()
    network_passphrase = (
        Network.TESTNET_NETWORK_PASSPHRASE
        if network == "testnet"
        else Network.PUBLIC_NETWORK_PASSPHRASE
    )

    try:
        challenge_xdr = build_challenge_transaction(
            server_secret=server_kp.secret,
            client_account_id=account,
            home_domain=_home_domain(),
            web_auth_domain=_home_domain(),
            network_passphrase=network_passphrase,
            timeout=300,
        )
        return {
            "transaction": challenge_xdr,
            "network_passphrase": network_passphrase,
        }
    except Exception as exc:
        LOG.error("[SEP-10] build_challenge_transaction failed | %s", exc)
        raise HTTPException(status_code=500, detail="Failed to build SEP-10 challenge") from exc


@router.post("/token", response_model=TokenResponse)
async def get_token(body: TokenRequest):
    """
    SEP-10 step 2: valida o XDR assinado pelo Freighter e emite JWT.

    O JWT retornado deve ser usado como Bearer token em todas as requisições
    autenticadas. Payload: { sub, stellar_wallet, chain: "stellar", exp }.
    """
    account = body.account
    signed_xdr = body.transaction

    _validate_stellar_account(account)

    sdk = _load_stellar_sdk()
    if sdk is None:
        # Sem SDK — aceita mock challenge apenas se nonce bater exatamente
        try:
            decoded = base64.b64decode(signed_xdr).decode()
            nonce = _pop_challenge(account)
            if nonce and decoded == f"mock-challenge:{account}:{nonce}":
                token = _issue_jwt(account)
                return TokenResponse(token=token, account=account)
        except Exception:
            pass
        raise HTTPException(status_code=401, detail="Invalid or expired challenge")

    Keypair, Network, TransactionEnvelope, _build_fn, read_fn, verify_fn = sdk

    server_secret = _server_secret()
    if not server_secret:
        LOG.error("[SEP-10] STELLAR_SERVER_SECRET not configured — refusing to issue token")
        raise HTTPException(
            status_code=503,
            detail="Authentication service temporarily unavailable: server secret not configured.",
        )

    server_kp = Keypair.from_secret(server_secret)
    network = _network()
    network_passphrase = (
        Network.TESTNET_NETWORK_PASSPHRASE
        if network == "testnet"
        else Network.PUBLIC_NETWORK_PASSPHRASE
    )

    try:
        # read_challenge_transaction extrai o client_account_id do XDR
        challenge = read_fn(
            challenge_transaction=signed_xdr,
            server_account_id=server_kp.public_key,
            home_domains=_home_domain(),
            web_auth_domain=_home_domain(),
            network_passphrase=network_passphrase,
        )
        client_account_id = challenge.client_account_id

        # verify_challenge_transaction_signed_by_client_master_key lança exceção se inválido
        verify_fn(
            challenge_transaction=signed_xdr,
            server_account_id=server_kp.public_key,
            home_domains=_home_domain(),
            web_auth_domain=_home_domain(),
            network_passphrase=network_passphrase,
        )
    except Exception as exc:
        LOG.warning("[SEP-10] verify failed | account=%s | %s", account, exc)
        raise HTTPException(status_code=401, detail="SEP-10 verification failed") from exc

    token = _issue_jwt(client_account_id)
    LOG.info("[SEP-10] token issued | account=%s", client_account_id)
    return TokenResponse(token=token, account=client_account_id)
