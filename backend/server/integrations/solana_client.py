from __future__ import annotations

from typing import Any, Dict

import httpx
from server.settings import settings

class SolanaClient:
    def __init__(self, rpc_url: str, jupiter_quote_url: str, jupiter_swap_url: str):
        self.rpc_url = rpc_url
        self.jupiter_quote_url = jupiter_quote_url
        self.jupiter_swap_url = jupiter_swap_url

    async def get_health(self) -> Dict[str, Any]:
        payload = {"jsonrpc": "2.0", "id": 1, "method": "getHealth"}
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.post(self.rpc_url, json=payload)
            response.raise_for_status()
            return response.json()

    async def get_balance(self, wallet_address: str) -> Dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [wallet_address],
        }
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.post(self.rpc_url, json=payload)
            response.raise_for_status()
            data = response.json()

        lamports = data.get("result", {}).get("value", 0)
        sol = lamports / 1_000_000_000
        return {"wallet": wallet_address, "lamports": lamports, "sol": sol}

    async def get_swap_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount_raw: int,
        slippage_bps: int = 50,
    ) -> Dict[str, Any]:
        if settings.solana_cluster == "devnet":
            # Mock para Devnet: Jupiter nao suporta Devnet
            return {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "inAmount": str(amount_raw),
                "outAmount": str(int(amount_raw * 0.98)),  # Fake exchange rate
                "otherAmountThreshold": str(int(amount_raw * 0.95)),
                "swapMode": "ExactIn",
                "slippageBps": slippage_bps,
                "platformFee": None,
                "priceImpactPct": "0.01",
                "routePlan": []
            }
            
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount_raw),
            "slippageBps": str(slippage_bps),
        }
        async with httpx.AsyncClient(timeout=18) as client:
            response = await client.get(self.jupiter_quote_url, params=params)
            response.raise_for_status()
            return response.json()

    async def prepare_swap_transaction(self, quote_response: Dict[str, Any], user_public_key: str) -> Dict[str, Any]:
        if settings.solana_cluster == "devnet":
            import base64
            from solders.hash import Hash
            from solders.message import MessageV0
            from solders.pubkey import Pubkey
            from solders.signature import Signature
            from solders.system_program import TransferParams, transfer
            from solders.transaction import VersionedTransaction

            # Fetch real blockhash so the tx can be simulated and confirmed
            bh_payload = {
                "jsonrpc": "2.0", "id": 1,
                "method": "getLatestBlockhash",
                "params": [{"commitment": "finalized"}],
            }
            async with httpx.AsyncClient(timeout=12) as client:
                bh_resp = await client.post(self.rpc_url, json=bh_payload)
                bh_resp.raise_for_status()
                bh_data = bh_resp.json()

            blockhash_str = bh_data["result"]["value"]["blockhash"]
            last_valid = bh_data["result"]["value"]["lastValidBlockHeight"]

            # Build a real self-transfer (1 lamport, user → user) as devnet demo tx
            pk = Pubkey.from_string(user_public_key)
            ix = transfer(TransferParams(from_pubkey=pk, to_pubkey=pk, lamports=1))
            msg = MessageV0.try_compile(
                payer=pk,
                instructions=[ix],
                address_lookup_table_accounts=[],
                recent_blockhash=Hash.from_string(blockhash_str),
            )
            # Unsigned — Phantom will fill the signature
            tx = VersionedTransaction.populate(msg, [Signature.default()])
            tx_b64 = base64.b64encode(bytes(tx)).decode()

            return {"swapTransaction": tx_b64, "lastValidBlockHeight": last_valid}
            
        payload = {
            "quoteResponse": quote_response,
            "userPublicKey": user_public_key,
            "wrapAndUnwrapSol": True,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(self.jupiter_swap_url, json=payload)
            response.raise_for_status()
            return response.json()
