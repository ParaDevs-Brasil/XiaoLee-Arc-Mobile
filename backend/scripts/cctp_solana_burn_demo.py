"""
cctp_solana_burn_demo.py — Primeiro burn USDC REAL Solana devnet -> Arc via CCTP V2.

Fluxo:
    1. Checa saldos da tesouraria (SOL pra fee + USDC devnet) — instrui faucets se vazio
    2. deposit_for_burn real no TokenMessengerMinterV2 (SolanaCCTPClient, sandbox=False)
    3. Poll da attestation na iris-api V2 (endpoint /v2/messages, diferente do /v1 usado
       no fluxo EVM Sepolia — V2 indexa por tx hash, não por message hash)
    4. Com --receive: completa o mint no Arc via ArcNativeClient.receive_cctp_message

Uso:
    cd backend && ../.venv/bin/python scripts/cctp_solana_burn_demo.py [--amount 0.1] [--receive]

Pré-requisitos (uma vez):
    - SOLANA_TREASURY_KEYPAIR_B58 no .env (já gerada em 03/07/2026)
    - SOL devnet:  https://faucet.solana.com   -> colar o pubkey da tesouraria
    - USDC devnet: https://faucet.circle.com   -> "Solana Devnet" -> mesmo pubkey
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

import aiohttp

from server.settings import settings
from server.integrations.solana_cctp import SolanaCCTPClient, SOLANA_CCTP_DOMAIN

IRIS_V2_SANDBOX = "https://iris-api-sandbox.circle.com/v2/messages"
ARC_DOMAIN = 26
ATTEST_TIMEOUT_S = 300
ATTEST_INTERVAL_S = 5


async def rpc(session: aiohttp.ClientSession, method: str, params: list) -> dict:
    async with session.post(
        settings.solana_rpc_url,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
    ) as r:
        return await r.json()


def arc_agent_address() -> str:
    """Endereço EVM do agente no Arc (destinatário do mint) — derivado da private key."""
    from web3 import Web3

    return Web3().eth.account.from_key(settings.arc_agent_private_key).address


async def check_funding(client: SolanaCCTPClient) -> bool:
    pubkey = client.address
    async with aiohttp.ClientSession() as s:
        sol = await rpc(s, "getBalance", [pubkey])
        sol_balance = sol.get("result", {}).get("value", 0) / 1e9
    usdc_balance = await client.get_usdc_balance()

    print(f"tesouraria: {pubkey}")
    print(f"  SOL devnet:  {sol_balance:.4f}")
    print(f"  USDC devnet: {usdc_balance:.4f}")

    ok = True
    if sol_balance < 0.01:
        print("  FALTA SOL -> https://faucet.solana.com (colar o pubkey acima)")
        ok = False
    if usdc_balance < 0.1:
        print("  FALTA USDC -> https://faucet.circle.com -> 'Solana Devnet' (mesmo pubkey)")
        ok = False
    return ok


async def poll_attestation_v2(source_tx: str) -> dict:
    """Poll da iris V2: GET /v2/messages/{sourceDomain}?transactionHash={tx}.
    Retorna o primeiro message com attestation completa."""
    url = f"{IRIS_V2_SANDBOX}/{SOLANA_CCTP_DOMAIN}"
    deadline = asyncio.get_event_loop().time() + ATTEST_TIMEOUT_S

    async with aiohttp.ClientSession() as s:
        while asyncio.get_event_loop().time() < deadline:
            async with s.get(url, params={"transactionHash": source_tx}) as r:
                if r.status == 404:
                    print("  attestation ainda não indexada...")
                elif r.ok:
                    data = await r.json()
                    msgs = data.get("messages", [])
                    for m in msgs:
                        if m.get("status") == "complete" and m.get("attestation"):
                            return m
                    print(f"  status: {[m.get('status') for m in msgs]}")
                else:
                    print(f"  iris {r.status}: {(await r.text())[:120]}")
            await asyncio.sleep(ATTEST_INTERVAL_S)

    raise TimeoutError(f"attestation não chegou em {ATTEST_TIMEOUT_S}s (tx={source_tx})")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--amount", type=float, default=0.1)
    parser.add_argument("--receive", action="store_true", help="completa o mint no Arc após a attestation")
    args = parser.parse_args()

    client = SolanaCCTPClient(sandbox=False)
    if not client.treasury_keypair_b58:
        print("SOLANA_TREASURY_KEYPAIR_B58 não configurada no .env")
        sys.exit(1)

    if not await check_funding(client):
        print("\nFundear a tesouraria primeiro (links acima) e rodar de novo.")
        sys.exit(1)

    recipient = arc_agent_address()
    recipient_b32 = bytes(12) + bytes.fromhex(recipient[2:])
    print(f"\nburn {args.amount} USDC Solana devnet -> Arc (domain {ARC_DOMAIN})")
    print(f"mint_recipient no Arc: {recipient}")

    result = await client.burn_usdc(
        amount_usdc=args.amount,
        destination_domain=ARC_DOMAIN,
        mint_recipient_bytes32=recipient_b32,
    )
    print(f"\nBURN CONFIRMADO: {result.tx_hash}")
    print(f"explorer: https://explorer.solana.com/tx/{result.tx_hash}?cluster=devnet")

    print("\naguardando attestation da Circle (iris V2)...")
    message = await poll_attestation_v2(result.tx_hash)
    print("ATTESTATION COMPLETA")
    print(f"  message: {message['message'][:60]}...")
    print(f"  attestation: {message['attestation'][:60]}...")

    if args.receive:
        from server.integrations.arc_native import ArcNativeClient

        arc = ArcNativeClient(sandbox=False)
        raw_message = bytes.fromhex(message["message"].removeprefix("0x"))
        attestation = bytes.fromhex(message["attestation"].removeprefix("0x"))
        rx = await arc.receive_cctp_message(
            msg_transmitter=settings.arc_cctp_msg_transmitter,
            raw_message=raw_message,
            attestation=attestation,
        )
        print(f"\nMINT NO ARC CONFIRMADO: {rx.tx_hash}")
    else:
        print("\n(rode com --receive pra completar o mint no Arc)")

    print(json.dumps({"source_tx": result.tx_hash, "status": "attested"}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
