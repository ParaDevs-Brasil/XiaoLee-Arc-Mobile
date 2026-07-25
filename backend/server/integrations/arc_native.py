"""
arc_native.py — Cliente EVM direto para o Arc (Canteen testnet / mainnet).

Complementa o arc_client.py (Circle W3S). Onde o W3S é o caminho gerenciado
(Circle Tools 20%), o arc_native é o caminho soberano: o agente assina com
sua própria chave privada Arc, sem passar pela API Circle.

Usado para:
  1. Transferências USDC diretas no Arc (fallback W3S ou pagamentos internos)
  2. receiveMessage() do CCTP — permissionless, qualquer endereço pode chamar
  3. Consulta de saldo on-chain (ground truth, não depende da Circle API)
  4. Estimativa de gas USDC no Arc

No Arc, o gas token é USDC nativo. Transferências ERC-20 e txs normais
pagam gas em USDC — a conta precisa de saldo USDC suficiente para o gas.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Optional

LOG = logging.getLogger(__name__)

# ABI mínimo — apenas as funções que o agente chama
_ERC20_ABI = [
    {
        "name": "transfer",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "to",     "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "bool"}],
    },
    {
        "name": "balanceOf",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "account", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
    },
    {
        "name": "decimals",
        "type": "function",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint8"}],
    },
    {
        "name": "approve",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount",  "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "bool"}],
    },
]

_MSG_TRANSMITTER_ABI = [
    {
        "name": "receiveMessage",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "message",     "type": "bytes"},
            {"name": "attestation", "type": "bytes"},
        ],
        "outputs": [{"name": "success", "type": "bool"}],
    },
    {
        "name": "usedNonces",
        "type": "function",
        "stateMutability": "view",
        "inputs": [
            {"name": "source_and_nonce", "type": "bytes32"},
        ],
        "outputs": [{"name": "", "type": "bool"}],
    },
]

_TX_TIMEOUT_S = 120


@dataclass
class TxResult:
    tx_hash:   str
    confirmed: bool
    gas_used:  int = 0
    status:    int = 0   # 1 = success, 0 = reverted


class ArcNativeClient:
    """
    Cliente EVM nativo para o Arc. O agente assina com ARC_AGENT_PRIVATE_KEY.

    Instanciação é leve (lazy web3 init — apenas quando necessário).
    """

    def __init__(
        self,
        rpc_url:      str = "",
        private_key:  str = "",
        usdc_address: str = "",
        chain_id:     Optional[int] = None,
        sandbox:      bool = True,
    ):
        self.rpc_url      = rpc_url      or os.getenv("ARC_RPC_URL",            "")
        self.private_key  = private_key  or os.getenv("ARC_AGENT_PRIVATE_KEY",  "")
        self.usdc_address = usdc_address or os.getenv("ARC_USDC_ADDRESS",       "")
        self._chain_id    = chain_id
        self.sandbox      = sandbox
        self._w3          = None   # lazy init
        self._decimals    = None   # cached

    # ------------------------------------------------------------------
    # Lazy web3 init
    # ------------------------------------------------------------------

    def _web3(self):
        if self._w3 is not None:
            return self._w3

        try:
            from web3 import Web3
            from web3.middleware import ExtraDataToPOAMiddleware
        except ImportError:
            raise RuntimeError(
                "web3 não instalado. Rode: pip install web3>=6.20.0"
            )

        if not self.rpc_url:
            raise RuntimeError("ARC_RPC_URL não configurado")

        w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={"timeout": 30}))
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        self._w3 = w3
        return w3

    def _account(self):
        try:
            from web3 import Web3
        except ImportError:
            raise RuntimeError("web3 não instalado. Rode: pip install web3>=6.20.0")
        if not self.private_key:
            raise RuntimeError("ARC_AGENT_PRIVATE_KEY não configurado")
        return Web3().eth.account.from_key(self.private_key)

    @property
    def address(self) -> str:
        if self.sandbox:
            return "0xSANDBOX_ARC_AGENT"
        return self._account().address

    # ------------------------------------------------------------------
    # Saldo USDC on-chain (ground truth)
    # ------------------------------------------------------------------

    async def get_usdc_balance(self, address: Optional[str] = None) -> float:
        if self.sandbox:
            LOG.debug("[arc_native] SANDBOX balance → 1000.0 USDC")
            return 1000.0

        w3  = self._web3()
        acc = address or self._account().address

        if not self.usdc_address:
            raise RuntimeError("ARC_USDC_ADDRESS não configurado")

        from web3 import Web3
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(self.usdc_address),
            abi=_ERC20_ABI,
        )
        decimals  = await self._get_decimals(contract)
        raw_bal   = contract.functions.balanceOf(
            Web3.to_checksum_address(acc)
        ).call()
        return raw_bal / 10 ** decimals

    async def _get_decimals(self, contract) -> int:
        if self._decimals is not None:
            return self._decimals
        self._decimals = contract.functions.decimals().call()
        return self._decimals

    # ------------------------------------------------------------------
    # Transferência USDC direta no Arc
    # ------------------------------------------------------------------

    async def send_usdc(
        self,
        to:               str,
        amount_usdc:      float,
        idempotency_key:  str = "",
    ) -> TxResult:
        """
        ERC-20 USDC transfer direto no Arc.
        Gas pago em USDC (gas token nativo do Arc).
        """
        if self.sandbox:
            fake = f"sandbox_native_tx_{idempotency_key[:12] if idempotency_key else to[:8]}"
            LOG.info("[arc_native] SANDBOX transfer %.4f USDC → %s | tx=%s", amount_usdc, to, fake)
            return TxResult(tx_hash=fake, confirmed=True, status=1)

        w3  = self._web3()
        acc = self._account()

        from web3 import Web3
        contract  = w3.eth.contract(
            address=Web3.to_checksum_address(self.usdc_address),
            abi=_ERC20_ABI,
        )
        decimals  = await self._get_decimals(contract)
        amount_u  = int(amount_usdc * 10 ** decimals)
        chain_id  = self._chain_id or w3.eth.chain_id

        tx = contract.functions.transfer(
            Web3.to_checksum_address(to),
            amount_u,
        ).build_transaction({
            "from":     acc.address,
            "nonce":    w3.eth.get_transaction_count(acc.address),
            "chainId":  chain_id,
            "gasPrice": w3.eth.gas_price,
        })
        tx["gas"] = w3.eth.estimate_gas(tx)

        signed  = acc.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction).hex()
        LOG.info("[arc_native] USDC transfer sent tx=%s amount=%.4f → %s", tx_hash, amount_usdc, to)

        receipt = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: w3.eth.wait_for_transaction_receipt(tx_hash, timeout=_TX_TIMEOUT_S),
        )
        result = TxResult(
            tx_hash=tx_hash,
            confirmed=receipt["status"] == 1,
            gas_used=receipt.get("gasUsed", 0),
            status=receipt["status"],
        )
        if not result.confirmed:
            raise RuntimeError(f"[arc_native] USDC transfer reverted: tx={tx_hash}")

        LOG.info("[arc_native] USDC transfer confirmed tx=%s gas_used=%d", tx_hash, result.gas_used)
        return result

    # ------------------------------------------------------------------
    # CCTP — receiveMessage no Arc (permissionless)
    # ------------------------------------------------------------------

    async def receive_cctp_message(
        self,
        msg_transmitter: str,
        raw_message:     bytes,
        attestation:     bytes,
    ) -> TxResult:
        """
        Chama MessageTransmitter.receiveMessage() no Arc.

        Permissionless: qualquer endereço pode chamar — a attestation
        Circle prova que o burn aconteceu na chain fonte.

        raw_message  = bytes completos do evento MessageSent (NÃO o hash)
        attestation  = assinatura Circle do iris-api (bytes)
        """
        if self.sandbox:
            fake = f"sandbox_cctp_receive_{raw_message[:4].hex()}"
            LOG.info("[arc_native] SANDBOX receiveMessage tx=%s", fake)
            return TxResult(tx_hash=fake, confirmed=True, status=1)

        w3  = self._web3()
        acc = self._account()

        from web3 import Web3
        transmitter = w3.eth.contract(
            address=Web3.to_checksum_address(msg_transmitter),
            abi=_MSG_TRANSMITTER_ABI,
        )
        chain_id = self._chain_id or w3.eth.chain_id

        tx = transmitter.functions.receiveMessage(
            raw_message,
            attestation,
        ).build_transaction({
            "from":     acc.address,
            "nonce":    w3.eth.get_transaction_count(acc.address),
            "chainId":  chain_id,
            "gasPrice": w3.eth.gas_price,
        })
        tx["gas"] = w3.eth.estimate_gas(tx)

        signed  = acc.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction).hex()
        LOG.info("[arc_native] receiveMessage sent tx=%s", tx_hash)

        receipt = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: w3.eth.wait_for_transaction_receipt(tx_hash, timeout=_TX_TIMEOUT_S),
        )
        result = TxResult(
            tx_hash=tx_hash,
            confirmed=receipt["status"] == 1,
            gas_used=receipt.get("gasUsed", 0),
            status=receipt["status"],
        )
        if not result.confirmed:
            raise RuntimeError(f"[arc_native] receiveMessage reverted: tx={tx_hash}")

        LOG.info(
            "[arc_native] CCTP message received on Arc tx=%s gas_used=%d",
            tx_hash, result.gas_used,
        )
        return result

    # ------------------------------------------------------------------
    # Healthcheck
    # ------------------------------------------------------------------

    async def healthcheck(self) -> dict:
        if self.sandbox:
            return {"ok": True, "sandbox": True, "address": self.address}
        try:
            w3 = self._web3()
            block = w3.eth.block_number
            balance = await self.get_usdc_balance()
            return {
                "ok":         True,
                "sandbox":    False,
                "address":    self.address,
                "block":      block,
                "usdc_balance": balance,
            }
        except Exception as exc:
            return {"ok": False, "sandbox": False, "error": str(exc)}
