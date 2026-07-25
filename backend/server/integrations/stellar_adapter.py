"""
stellar_adapter.py — StellarAdapter: camada de abstração para Stellar/Horizon/Soroban.

Encapsula toda interação com a rede Stellar:
    - Consulta de saldo via Horizon REST API
    - Path payments (swaps) via Stellar DEX
    - Envio de pagamentos
    - Health check do Horizon

Segue o ADR-001 do RT XiaoLee Stellar: o OrchestrationService delega ao StellarAdapter
conforme a intenção detectada pelo Gemini.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

LOG = logging.getLogger(__name__)

HORIZON_TESTNET = "https://horizon-testnet.stellar.org"
HORIZON_MAINNET = "https://horizon.stellar.org"

# Asset IDs conhecidos por rede
# USDC testnet oficial da Circle (faucet.circle.com e CCTP V2 usam este issuer;
# o antigo GAAXKLIM... era asset de anchor de teste da era SEP-24 — não é queimável no CCTP)
USDC_TESTNET_ISSUER = "GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5"
# USDC mainnet emitido pela Circle (asset oficial na Public Network)
USDC_MAINNET_ISSUER = "GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN"
USDC_TESTNET = f"USDC:{USDC_TESTNET_ISSUER}"


def _is_testnet(network: str) -> bool:
    return (network or "testnet").lower() == "testnet"


def usdc_issuer_for(network: str) -> str:
    """Retorna o issuer USDC correto para a rede (mainnet usa o issuer da Circle)."""
    return USDC_TESTNET_ISSUER if _is_testnet(network) else USDC_MAINNET_ISSUER


@dataclass
class BalanceResult:
    wallet: str
    xlm: float
    assets: List[Dict[str, Any]]
    network: str


@dataclass
class SwapQuote:
    source_asset: str
    destination_asset: str
    source_amount: float
    destination_amount: float
    path: List[str]
    fee_xlm: float
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TxResult:
    success: bool
    tx_hash: Optional[str]
    ledger: Optional[int]
    error: Optional[str]


class StellarAdapter:
    """
    Abstração para interações com Stellar Horizon e Soroban.
    Segue ADR-001: isolamento completo da lógica de protocolo Stellar.
    """

    def __init__(self, network: str = "testnet", horizon_url: str = ""):
        self.network = network
        self.horizon_url = horizon_url or (
            HORIZON_TESTNET if _is_testnet(network) else HORIZON_MAINNET
        )
        # Issuer USDC correto para a rede ativa (mainnet = Circle)
        self.usdc_issuer = usdc_issuer_for(network)

    # ------------------------------------------------------------------
    # Account / Balance
    # ------------------------------------------------------------------

    async def get_account(self, wallet: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=12) as client:
            resp = await client.get(f"{self.horizon_url}/accounts/{wallet}")
            resp.raise_for_status()
            return resp.json()

    async def get_balance(self, wallet: str) -> BalanceResult:
        data = await self.get_account(wallet)
        xlm = 0.0
        assets: List[Dict[str, Any]] = []
        for b in data.get("balances", []):
            if b.get("asset_type") == "native":
                xlm = float(b.get("balance", 0))
            else:
                assets.append(
                    {
                        "asset_code": b.get("asset_code", ""),
                        "asset_issuer": b.get("asset_issuer", ""),
                        "balance": float(b.get("balance", 0)),
                    }
                )
        return BalanceResult(wallet=wallet, xlm=xlm, assets=assets, network=self.network)

    # ------------------------------------------------------------------
    # Stellar DEX — Path Payments
    # ------------------------------------------------------------------

    async def find_payment_paths_strict_send(
        self,
        source_asset: str,
        source_amount: str,
        destination_asset: str,
        source_account: str = "",
    ) -> Dict[str, Any]:
        """
        Usa /paths/strict-send: fixa o source_amount (XLM a enviar) e descobre
        quanto de destination_asset (USDC) o usuário recebe.
        source_asset: "XLM" ou "USDC:ISSUER"
        destination_asset: "XLM" ou "USDC:ISSUER"
        """
        params: Dict[str, str] = {"source_amount": source_amount}

        if source_asset.upper() == "XLM":
            params["source_asset_type"] = "native"
        else:
            code, issuer = source_asset.split(":", 1)
            params["source_asset_type"] = "credit_alphanum4"
            params["source_asset_code"] = code
            params["source_asset_issuer"] = issuer

        # strict-send usa destination_assets (não destination_account)
        if destination_asset.upper() == "XLM":
            params["destination_assets"] = "native"
        else:
            params["destination_assets"] = destination_asset  # "USDC:ISSUER"

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.horizon_url}/paths/strict-send", params=params
            )
            resp.raise_for_status()
            return resp.json()

    async def prepare_swap(
        self,
        wallet: str,
        from_asset: str,
        to_asset: str,
        amount: float,
    ) -> SwapQuote:
        """
        Prepara um swap via Stellar DEX — retorna quote sem assinar.
        Usa strict-send: amount = XLM a enviar → calcula USDC a receber.
        """
        try:
            # Resolve assets para formato "ASSET:ISSUER" ou "XLM"
            def _resolve(asset: str) -> str:
                if asset.upper() == "XLM":
                    return "XLM"
                if asset.upper() == "USDC" and ":" not in asset:
                    return f"USDC:{self.usdc_issuer}"
                return asset

            src_asset_param  = _resolve(from_asset)
            dest_asset_param = _resolve(to_asset)

            paths_data = await self.find_payment_paths_strict_send(
                source_asset=src_asset_param,
                source_amount=str(amount),
                destination_asset=dest_asset_param,
                source_account=wallet,
            )
            records = paths_data.get("_embedded", {}).get("records", [])
            if not records:
                return SwapQuote(
                    source_asset=from_asset,
                    destination_asset=to_asset,
                    source_amount=amount,
                    destination_amount=0.0,
                    path=[],
                    fee_xlm=0.00001,
                    raw={"error": "no_path_found"},
                )
            # strict-send: pega o record com maior destination_amount
            best = max(records, key=lambda r: float(r.get("destination_amount", 0)))
            src_amount = float(best.get("source_amount", amount))
            dst_amount = float(best.get("destination_amount", 0))
            path_assets = [
                p.get("asset_code", "XLM") for p in best.get("path", [])
            ]
            return SwapQuote(
                source_asset=from_asset,
                destination_asset=to_asset,
                source_amount=src_amount,
                destination_amount=dst_amount,
                path=path_assets,
                fee_xlm=0.00001,
                raw=best,
            )
        except Exception as exc:
            LOG.error("[StellarAdapter] prepare_swap error | %s", exc)
            return SwapQuote(
                source_asset=from_asset,
                destination_asset=to_asset,
                source_amount=amount,
                destination_amount=0.0,
                path=[],
                fee_xlm=0.00001,
                raw={"error": str(exc)},
            )

    async def build_swap_xdr(
        self,
        wallet: str,
        from_asset: str,
        to_asset: str,
        send_amount: float,
        min_dest_amount: float,
    ) -> str:
        """
        Constrói XDR não assinado de pathPaymentStrictSend.
        O frontend assina com Freighter e submete ao Horizon.
        """
        try:
            from stellar_sdk import Network, TransactionBuilder, Asset
            from stellar_sdk import Account as StellarAccount
        except ImportError as exc:
            raise RuntimeError("stellar-sdk não instalado") from exc

        network_passphrase = (
            Network.TESTNET_NETWORK_PASSPHRASE
            if self.network == "testnet"
            else Network.PUBLIC_NETWORK_PASSPHRASE
        )

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self.horizon_url}/accounts/{wallet}")
            resp.raise_for_status()
            acc_data = resp.json()

        sequence = int(acc_data["sequence"])
        source = StellarAccount(wallet, sequence)

        def _asset(code: str) -> Asset:
            if code.upper() == "XLM":
                return Asset.native()
            # USDC na rede ativa (testnet ou mainnet/Circle)
            return Asset("USDC", self.usdc_issuer)

        min_dest = max(min_dest_amount, 0.0000001)
        dst_asset = _asset(to_asset)

        # Verifica se o usuário já tem trustline para o asset de destino
        needs_trustline = False
        if to_asset.upper() != "XLM":
            for bal in acc_data.get("balances", []):
                if (
                    bal.get("asset_code", "").upper() == to_asset.upper()
                    and bal.get("asset_issuer") == USDC_TESTNET_ISSUER
                ):
                    break
            else:
                needs_trustline = True  # não tem trustline — inclui no tx

        builder = TransactionBuilder(
            source_account=source,
            network_passphrase=network_passphrase,
            base_fee=100,
        )

        if needs_trustline:
            builder.append_change_trust_op(dst_asset, "1000000")

        builder.append_path_payment_strict_send_op(
            destination=wallet,
            send_asset=_asset(from_asset),
            send_amount=f"{send_amount:.7f}",
            dest_asset=dst_asset,
            dest_min=f"{min_dest:.7f}",
            path=[],
        )
        builder.set_timeout(300)

        return builder.build().to_xdr()

    # ------------------------------------------------------------------
    # Transaction lookup (health / event verification)
    # ------------------------------------------------------------------

    async def get_transaction(self, tx_hash: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=12) as client:
            resp = await client.get(f"{self.horizon_url}/transactions/{tx_hash}")
            resp.raise_for_status()
            return resp.json()

    async def verify_payment(
        self, tx_hash: str, expected_destination: str, min_amount_xlm: float
    ) -> bool:
        """
        Verifica se uma transação transferiu pelo menos min_amount_xlm para expected_destination.
        Usado pelo middleware x402 para validar micropagamentos.
        """
        try:
            tx = await self.get_transaction(tx_hash)
            if tx.get("successful") is not True:
                LOG.warning("[x402] verify_payment: tx NOT successful | tx=%s", tx_hash)
                return False
            ops_url = tx.get("_links", {}).get("operations", {}).get("href", "").split("{")[0]
            if not ops_url:
                LOG.warning("[x402] verify_payment: no operations link | tx=%s", tx_hash)
                return False
            async with httpx.AsyncClient(timeout=12) as client:
                ops_resp = await client.get(ops_url)
                ops_resp.raise_for_status()
                ops = ops_resp.json().get("_embedded", {}).get("records", [])
            for op in ops:
                if op.get("type") not in ("payment", "path_payment_strict_send", "path_payment_strict_receive"):
                    continue
                dest = op.get("to", "") or op.get("destination", "")
                asset_type = op.get("asset_type", "")
                raw_amount = float(op.get("amount", 0))
                LOG.info(
                    "[x402] verify_payment op | tx=%s | dest=%s | expected=%s | asset=%s | amount=%.7f | min=%.7f",
                    tx_hash, dest, expected_destination, asset_type, raw_amount, min_amount_xlm,
                )
                if dest == expected_destination and asset_type == "native" and raw_amount >= min_amount_xlm:
                    return True
            LOG.warning(
                "[x402] verify_payment: no matching op | tx=%s | expected_dest=%s",
                tx_hash, expected_destination,
            )
            return False
        except Exception as exc:
            LOG.warning("[StellarAdapter] verify_payment failed | tx=%s | %s", tx_hash, exc)
            return False

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    async def get_health(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(f"{self.horizon_url}/")
            resp.raise_for_status()
            data = resp.json()
            return {
                "status": "ok",
                "network": self.network,
                "horizon_url": self.horizon_url,
                "core_latest_ledger": data.get("core_latest_ledger"),
                "history_latest_ledger": data.get("history_latest_ledger"),
            }
