"""
arc_client.py — Circle Programmable Wallets (W3S) client para pagamentos USDC no Arc.

Usa a API W3S de developer-controlled wallets. Autenticação por request:
  - Authorization: Bearer CIRCLE_API_KEY
  - entitySecretCiphertext: RSA-OAEP fresco do CIRCLE_ENTITY_SECRET, gerado A CADA
    transação (a Circle invalida cada ciphertext após o uso). Ver circle_crypto.py.

Endpoint real (não Payments API):
    POST /v1/w3s/developer/transactions/transfer   ← este, não /v1/transfers

Estados Circle:
    INITIATED → QUEUED → SENT → CONFIRMED   (caminho feliz)
                              → FAILED       (rejeição on-chain)

Sandbox (ARC_SANDBOX=true):
    Zero chamadas de rede. Retorna dados determinísticos a partir do intent_id.
    Seguro para CI/CD e demos sem credenciais Circle.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

import httpx

from server.integrations.circle_crypto import entity_secret_ciphertext

LOG = logging.getLogger(__name__)

_W3S_SANDBOX = "https://api.circle.com/v1/w3s"
_W3S_LIVE    = "https://api.circle.com/v1/w3s"

_POLL_INTERVAL_S  = 2.5
_POLL_TIMEOUT_S   = 120.0
_TERMINAL_STATES  = {"CONFIRMED", "COMPLETE", "FAILED", "CANCELLED"}

# Token IDs de USDC no sandbox Circle (estáveis, não mudam entre deploys)
_SANDBOX_USDC_TOKEN_IDS: dict[str, str] = {
    "ETH-SEPOLIA":  "5797fbd6-3795-519d-84ca-ec4c5f80c3b1",
    "AVAX-FUJI":    "e4f549f9-a910-59b1-b5cd-8f972871f5db",
    "ARB-SEPOLIA":  "1b88f684-f7e2-5c2c-ba03-eb9f5aab5a23",
    "BASE-SEPOLIA": "c11a2d52-5794-5d37-a4fe-b18e51ea2e0a",
    "ARC-TESTNET":  "ef87c8c3-85de-598a-af50-c5135eecfa74",
}


@dataclass
class TransferResult:
    circle_id:    str    # UUID da transação na Circle
    arc_tx_hash:  str    # Hash on-chain (vazio até CONFIRMED)
    status:       str    # Estado Circle: INITIATED|QUEUED|SENT|CONFIRMED|FAILED
    amount_usdc:  float
    to:           str
    confirmed:    bool = False
    sandbox:      bool = False


class ArcClient:
    """
    Cliente Circle W3S para o agente XiaoLee enviar USDC no Arc.

    Instância por worker — stateless exceto pelo cache do token_id.
    """

    def __init__(
        self,
        api_key:       str = "",
        wallet_id:     str = "",
        blockchain:    str = "",
        usdc_token_id: str = "",
        entity_secret: str = "",
        sandbox:       bool = True,
    ):
        self.api_key       = api_key       or os.getenv("CIRCLE_API_KEY",       "")
        self.wallet_id     = wallet_id     or os.getenv("CIRCLE_WALLET_ID",     "")
        # Entity secret (32 bytes hex) — usado para gerar o entitySecretCiphertext por tx.
        self.entity_secret = entity_secret or os.getenv("CIRCLE_ENTITY_SECRET", "")
        # Nome do blockchain na API Circle: "ETH-SEPOLIA", "ARB-SEPOLIA", "ARC-SEPOLIA"…
        self.blockchain    = blockchain    or os.getenv("CIRCLE_BLOCKCHAIN",    "ETH-SEPOLIA")
        # Token ID do USDC nessa chain — resolvido automaticamente se vazio
        self._token_id     = usdc_token_id or os.getenv("CIRCLE_USDC_TOKEN_ID", "")
        self.sandbox       = sandbox
        self._base         = _W3S_SANDBOX if sandbox else _W3S_LIVE

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
        }

    async def _resolve_token_id(self) -> str:
        """Retorna o ID do USDC na chain configurada, buscando da API se necessário."""
        if self._token_id:
            return self._token_id

        # Consulta mapa conhecido primeiro (funciona em modo sandbox e live)
        tid = _SANDBOX_USDC_TOKEN_IDS.get(self.blockchain, "")
        if tid:
            self._token_id = tid
            return tid

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self._base}/tokens",
                headers=self._headers(),
                params={"blockchain": self.blockchain},
            )
            if not resp.is_success:
                raise RuntimeError(
                    f"[arc] tokens fetch error {resp.status_code}: {resp.text[:300]}"
                )

        tokens = resp.json().get("data", {}).get("tokens", [])
        for t in tokens:
            if "USDC" in t.get("symbol", "").upper():
                self._token_id = t["id"]
                LOG.info("[arc] USDC token_id=%s on %s", self._token_id, self.blockchain)
                return self._token_id

        raise RuntimeError(f"[arc] USDC token not found on {self.blockchain}")

    # ------------------------------------------------------------------
    # Balance
    # ------------------------------------------------------------------

    async def get_usdc_balance(self, wallet_id: Optional[str] = None) -> float:
        """Saldo USDC disponível na wallet do agente."""
        wid = wallet_id or self.wallet_id

        if self.sandbox:
            LOG.debug("[arc] SANDBOX balance wallet=%s → 1000.0 USDC", wid)
            return 1000.0

        if not self.api_key or not wid:
            raise RuntimeError("CIRCLE_API_KEY or CIRCLE_WALLET_ID not configured")

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self._base}/wallets/{wid}/balances",
                headers=self._headers(),
            )
            if not resp.is_success:
                raise RuntimeError(
                    f"[arc] balance error {resp.status_code}: {resp.text[:300]}"
                )

        for tb in resp.json().get("data", {}).get("tokenBalances", []):
            sym = tb.get("token", {}).get("symbol", "").upper()
            tid = tb.get("token", {}).get("id", "")
            if "USDC" in sym or tid == self._token_id:
                return float(tb.get("amount", "0"))
        return 0.0

    # Alias usado pelos testes existentes
    async def get_balance(self, wallet_id: Optional[str] = None) -> float:
        return await self.get_usdc_balance(wallet_id)

    # ------------------------------------------------------------------
    # Transfer
    # ------------------------------------------------------------------

    async def send_usdc(
        self,
        to_address:       str,
        amount_usdc:      float,
        idempotency_key:  str,
        wait_confirmed:   bool  = True,
        timeout_s:        float = _POLL_TIMEOUT_S,
    ) -> str:
        """
        Envia USDC via Circle W3S (developer-controlled wallet).

        Retorna:
          sandbox  → fake id determinístico (sem rede)
          live     → arc_tx_hash on-chain se wait_confirmed=True,
                     circle_id se wait_confirmed=False

        idempotency_key = intent_id (UUID v4) — garante anti-replay.
        """
        if self.sandbox:
            fake_id = f"sandbox_tx_{idempotency_key[:16]}"
            LOG.info(
                "[arc] SANDBOX %.4f USDC → %s | fake_id=%s",
                amount_usdc, to_address, fake_id,
            )
            return fake_id

        if not self.api_key or not self.wallet_id:
            raise RuntimeError("CIRCLE_API_KEY or CIRCLE_WALLET_ID not configured")

        token_id = await self._resolve_token_id()

        # Ciphertext fresco por transação — exigido pela Circle em developer wallets.
        ciphertext = await entity_secret_ciphertext(
            self.api_key, self.entity_secret, self._base,
        )

        payload = {
            "idempotencyKey":         idempotency_key,
            "entitySecretCiphertext": ciphertext,
            "walletId":               self.wallet_id,
            "tokenId":                token_id,
            "destinationAddress":     to_address,
            "amounts":                [f"{amount_usdc:.6f}"],
            "feeLevel":               "MEDIUM",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self._base}/developer/transactions/transfer",
                json=payload,
                headers=self._headers(),
            )
            if not resp.is_success:
                raise RuntimeError(
                    f"[arc] transfer error {resp.status_code}: {resp.text[:400]}"
                )

        circle_id = resp.json().get("data", {}).get("id", "")
        LOG.info(
            "[arc] transfer initiated %.4f USDC → %s | circle_id=%s",
            amount_usdc, to_address, circle_id,
        )

        if not wait_confirmed:
            return circle_id

        result = await self._poll_until_terminal(circle_id, timeout_s=timeout_s)

        if result.status in ("FAILED", "CANCELLED"):
            raise RuntimeError(
                f"[arc] transfer {circle_id} ended with status={result.status}"
            )

        tx_hash = result.arc_tx_hash or circle_id
        LOG.info(
            "[arc] transfer confirmed circle_id=%s arc_tx_hash=%s",
            circle_id, tx_hash,
        )
        return tx_hash

    # ------------------------------------------------------------------
    # Transaction status
    # ------------------------------------------------------------------

    async def get_transfer_result(self, circle_id: str) -> TransferResult:
        """Estado atual de uma transação Circle."""
        if self.sandbox:
            return TransferResult(
                circle_id=circle_id, arc_tx_hash=circle_id,
                status="CONFIRMED", amount_usdc=0.0,
                to="", confirmed=True, sandbox=True,
            )

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self._base}/transactions/{circle_id}",
                headers=self._headers(),
            )
            if not resp.is_success:
                raise RuntimeError(
                    f"[arc] tx status error {resp.status_code}: {resp.text[:300]}"
                )

        tx     = resp.json().get("data", {}).get("transaction", {})
        status = tx.get("state", "UNKNOWN")
        amounts = tx.get("amounts", ["0"])

        return TransferResult(
            circle_id=circle_id,
            arc_tx_hash=tx.get("txHash", ""),
            status=status,
            amount_usdc=float(amounts[0]) if amounts else 0.0,
            to=tx.get("destinationAddress", ""),
            confirmed=status in ("CONFIRMED", "COMPLETE"),
            sandbox=False,
        )

    # Alias backwards-compat
    async def get_transfer_status(self, transfer_id: str) -> dict:
        result = await self.get_transfer_result(transfer_id)
        return {
            "id":           result.circle_id,
            "status":       result.status,
            "arc_tx_hash":  result.arc_tx_hash,
            "confirmed":    result.confirmed,
        }

    async def _poll_until_terminal(
        self,
        circle_id: str,
        timeout_s: float = _POLL_TIMEOUT_S,
    ) -> TransferResult:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            result = await self.get_transfer_result(circle_id)
            LOG.debug("[arc] poll circle_id=%s status=%s", circle_id, result.status)
            if result.status in _TERMINAL_STATES:
                return result
            await asyncio.sleep(_POLL_INTERVAL_S)

        raise TimeoutError(
            f"[arc] transfer {circle_id} não confirmou em {timeout_s:.0f}s"
        )

    # ------------------------------------------------------------------
    # Wallet info (usado pelo setup script e debug)
    # ------------------------------------------------------------------

    async def get_wallet_info(self, wallet_id: Optional[str] = None) -> dict:
        """Dados da wallet Circle: endereço EVM, blockchain, estado."""
        wid = wallet_id or self.wallet_id

        if self.sandbox:
            return {
                "id":         wid,
                "address":    "0xSANDBOX_ADDRESS",
                "state":      "LIVE",
                "blockchain": self.blockchain,
            }

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self._base}/wallets/{wid}",
                headers=self._headers(),
            )
            if not resp.is_success:
                raise RuntimeError(
                    f"[arc] wallet info error {resp.status_code}: {resp.text[:300]}"
                )
        return resp.json().get("data", {}).get("wallet", {})
