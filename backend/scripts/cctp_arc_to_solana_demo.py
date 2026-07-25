"""
cctp_arc_to_solana_demo.py — Volta: burn USDC REAL no Arc testnet -> mint na Solana devnet.

Fecha a bidirecionalidade provada on-chain (a ida Solana->Arc foi em 03/07/2026,
burn 3TnoWEkp... / mint 18d9bd94...).

Diferenças vs. o fluxo EVM v1 (Sepolia) do cctp_client.py:
  - Arc é CCTP V2: depositForBurn tem 7 params (amount, destinationDomain, mintRecipient,
    burnToken, destinationCaller, maxFee, minFinalityThreshold) — a ABI v1 de 4 params
    nem existe no contrato V2 (selector diferente).
  - Destino Solana: mintRecipient = ATA (token account) da tesouraria, NÃO a wallet.
  - Attestation: iris /v2/messages/{srcDomain}?transactionHash= (V2, por tx hash).

Uso:
    cd backend && ../.venv/bin/python scripts/cctp_arc_to_solana_demo.py [--amount 0.05]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

import aiohttp

from server.settings import settings
from server.integrations.solana_cctp import SolanaCCTPClient

IRIS_V2_SANDBOX = "https://iris-api-sandbox.circle.com/v2/messages"
ARC_DOMAIN = 26
SOLANA_DOMAIN = 5
ATTEST_TIMEOUT_S = 300
ATTEST_INTERVAL_S = 5

# depositForBurn V2 — 7 params (github.com/circlefin/evm-cctp-contracts, TokenMessengerV2)
_TOKEN_MESSENGER_V2_ABI = [
    {
        "name": "depositForBurn",
        "type": "function",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "amount",                "type": "uint256"},
            {"name": "destinationDomain",     "type": "uint32"},
            {"name": "mintRecipient",         "type": "bytes32"},
            {"name": "burnToken",             "type": "address"},
            {"name": "destinationCaller",     "type": "bytes32"},
            {"name": "maxFee",                "type": "uint256"},
            {"name": "minFinalityThreshold",  "type": "uint32"},
        ],
        "outputs": [],
    },
]

_ERC20_ABI = [
    {"name": "approve", "type": "function", "stateMutability": "nonpayable",
     "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}],
     "outputs": [{"name": "", "type": "bool"}]},
    {"name": "decimals", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint8"}]},
    {"name": "balanceOf", "type": "function", "stateMutability": "view",
     "inputs": [{"name": "account", "type": "address"}], "outputs": [{"name": "", "type": "uint256"}]},
]


def burn_on_arc(amount_usdc: float, mint_recipient_b32: bytes) -> tuple[str, bytes, str]:
    """approve + depositForBurn V2 no Arc. Retorna (tx_hash, raw_message, agent_addr)."""
    from web3 import Web3
    from web3.middleware import ExtraDataToPOAMiddleware

    from server.integrations.cctp_client import CCTPClient

    w3 = Web3(Web3.HTTPProvider(settings.arc_rpc_url, request_kwargs={"timeout": 30}))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    acc = w3.eth.account.from_key(settings.arc_agent_private_key)

    usdc_addr = settings.arc_cctp_usdc or settings.arc_usdc_address
    usdc = w3.eth.contract(address=Web3.to_checksum_address(usdc_addr), abi=_ERC20_ABI)
    decimals = usdc.functions.decimals().call()
    amount_u = int(amount_usdc * 10 ** decimals)
    balance = usdc.functions.balanceOf(acc.address).call() / 10 ** decimals
    chain_id = w3.eth.chain_id
    print(f"agente Arc: {acc.address} | saldo USDC: {balance:.4f} | chain_id: {chain_id}")
    if balance < amount_usdc + 0.02:
        raise RuntimeError(f"saldo insuficiente (precisa {amount_usdc} + ~0.02 de gas USDC)")

    tm_addr = Web3.to_checksum_address(settings.arc_cctp_token_messenger)

    # 1. approve
    nonce = w3.eth.get_transaction_count(acc.address, "pending")
    tx_a = usdc.functions.approve(tm_addr, amount_u).build_transaction(
        {"from": acc.address, "nonce": nonce, "chainId": chain_id, "gasPrice": w3.eth.gas_price}
    )
    tx_a["gas"] = w3.eth.estimate_gas(tx_a)
    signed = acc.sign_transaction(tx_a)
    h_a = w3.eth.send_raw_transaction(signed.raw_transaction).hex()
    r_a = w3.eth.wait_for_transaction_receipt(h_a, timeout=120)
    assert r_a["status"] == 1, f"approve reverteu: {h_a}"
    print(f"approve ok: {h_a}")

    # 2. depositForBurn V2 (maxFee=0, minFinality=2000 = standard/finalized, sem taxa)
    # Gas limit EXPLÍCITO: a estimativa automática do nó Arc usa um teto inflado (~4.2M gas)
    # e exige saldo pra cobrir o teto inteiro, não o consumo real (~250k) — com saldo justo
    # o estimate_gas falha antes mesmo de tentar.
    messenger = w3.eth.contract(address=tm_addr, abi=_TOKEN_MESSENGER_V2_ABI)
    gas_price = w3.eth.gas_price
    gas_limit = 350_000
    upfront = gas_limit * gas_price / 1e18
    print(f"gasPrice: {gas_price / 1e9:.2f} gwei | reserva de gas: {upfront:.4f} USDC")
    nonce = w3.eth.get_transaction_count(acc.address, "pending")
    tx_b = messenger.functions.depositForBurn(
        amount_u, SOLANA_DOMAIN, mint_recipient_b32,
        Web3.to_checksum_address(usdc_addr), bytes(32), 0, 2000,
    ).build_transaction(
        {"from": acc.address, "nonce": nonce, "chainId": chain_id,
         "gasPrice": gas_price, "gas": gas_limit}
    )
    signed = acc.sign_transaction(tx_b)
    h_b = w3.eth.send_raw_transaction(signed.raw_transaction).hex()
    r_b = w3.eth.wait_for_transaction_receipt(h_b, timeout=120)
    assert r_b["status"] == 1, f"depositForBurn reverteu: {h_b}"

    raw_message, msg_hash = CCTPClient._extract_message_from_receipt(w3, r_b)
    print(f"BURN NO ARC CONFIRMADO: {h_b} (msg {len(raw_message)} bytes)")
    return h_b, raw_message, acc.address


async def poll_attestation_v2(source_tx: str) -> dict:
    url = f"{IRIS_V2_SANDBOX}/{ARC_DOMAIN}"
    tx_param = source_tx if source_tx.startswith("0x") else f"0x{source_tx}"
    deadline = asyncio.get_event_loop().time() + ATTEST_TIMEOUT_S
    async with aiohttp.ClientSession() as s:
        while asyncio.get_event_loop().time() < deadline:
            async with s.get(url, params={"transactionHash": tx_param}) as r:
                if r.ok:
                    data = await r.json()
                    for m in data.get("messages", []):
                        if m.get("status") == "complete" and m.get("attestation"):
                            return m
                    print(f"  status: {[m.get('status') for m in data.get('messages', [])]}")
                elif r.status == 404:
                    print("  attestation ainda não indexada...")
                else:
                    print(f"  iris {r.status}: {(await r.text())[:120]}")
            await asyncio.sleep(ATTEST_INTERVAL_S)
    raise TimeoutError(f"attestation não chegou em {ATTEST_TIMEOUT_S}s")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--amount", type=float, default=0.05)
    args = parser.parse_args()

    solana = SolanaCCTPClient(sandbox=False)
    from solders.pubkey import Pubkey

    mint = Pubkey.from_string(solana.usdc_mint)
    treasury_pk = solana._treasury_pubkey()
    treasury_ata = solana.derive_associated_token_address(treasury_pk, mint)
    print(f"tesouraria Solana: {treasury_pk}")
    print(f"ATA destino (mintRecipient): {treasury_ata}")
    balance_before = await solana.get_usdc_balance()
    print(f"saldo USDC Solana ANTES: {balance_before:.4f}\n")

    burn_tx, raw_message, _ = burn_on_arc(args.amount, bytes(treasury_ata))

    print("\naguardando attestation da Circle (iris V2, domain 26)...")
    message = await poll_attestation_v2(burn_tx)
    print("ATTESTATION COMPLETA")

    raw_msg = bytes.fromhex(message["message"].removeprefix("0x"))
    attestation = bytes.fromhex(message["attestation"].removeprefix("0x"))

    usdc_arc = settings.arc_cctp_usdc or settings.arc_usdc_address
    burn_token_b32 = bytes(12) + bytes.fromhex(usdc_arc[2:])

    print("\nexecutando receiveMessage na Solana...")
    rx = await solana.receive_and_mint(
        raw_message=raw_msg,
        attestation=attestation,
        recipient_owner_b58=str(treasury_pk),
        source_domain=ARC_DOMAIN,
        burn_token_bytes_32=burn_token_b32,
    )
    print(f"MINT NA SOLANA CONFIRMADO: {rx.tx_hash}")
    print(f"explorer: https://explorer.solana.com/tx/{rx.tx_hash}?cluster=devnet")

    await asyncio.sleep(5)
    balance_after = await solana.get_usdc_balance()
    print(f"\nsaldo USDC Solana DEPOIS: {balance_after:.4f} (delta {balance_after - balance_before:+.4f})")


if __name__ == "__main__":
    asyncio.run(main())
