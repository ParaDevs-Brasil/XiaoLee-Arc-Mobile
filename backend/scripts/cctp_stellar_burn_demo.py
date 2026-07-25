"""
cctp_stellar_burn_demo.py — Burn USDC REAL Stellar testnet -> Arc via CCTP V2 (Soroban).

Fluxo (espelha cctp_solana_burn_demo.py, domain 27 em vez de 5):
    1. Checa saldos da tesouraria (XLM pra fee + USDC testnet) — instrui faucets se vazio
    2. deposit_for_burn real no TokenMessengerMinterV2 Soroban (StellarCCTPClient, sandbox=False)
    3. Poll da attestation na iris-api V2 (/v2/messages/27?transactionHash=)
    4. Com --receive: completa o mint no Arc via ArcNativeClient.receive_cctp_message

Uso:
    cd backend && ../.venv/bin/python scripts/cctp_stellar_burn_demo.py [--amount 0.5] [--receive]

Pré-requisitos (uma vez):
    - scripts/setup_stellar_cctp_treasury.py (gera STELLAR_TREASURY_SECRET + trustline)
    - USDC testnet: https://faucet.circle.com -> "Stellar Testnet" -> pubkey da tesouraria

Nota de decimais: USDC em Stellar tem 7 casas (vs 6 no Arc/Solana) — a normalização é
feita pelo contrato Soroban da Circle; aqui só convertemos float -> raw de 7 casas.
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
from server.integrations.stellar_adapter import HORIZON_TESTNET, usdc_issuer_for
from server.integrations.stellar_cctp import StellarCCTPClient, STELLAR_CCTP_DOMAIN

IRIS_V2_SANDBOX = "https://iris-api-sandbox.circle.com/v2/messages"
ARC_DOMAIN = 26
ATTEST_TIMEOUT_S = 300
ATTEST_INTERVAL_S = 5


def arc_agent_address() -> str:
    """Endereço EVM do agente no Arc (destinatário do mint) — derivado da private key."""
    from web3 import Web3

    return Web3().eth.account.from_key(settings.arc_agent_private_key).address


async def check_funding(client: StellarCCTPClient) -> bool:
    pubkey = client.address
    usdc_issuer = usdc_issuer_for("testnet")
    xlm_balance = 0.0
    usdc_balance = 0.0

    async with aiohttp.ClientSession() as s:
        async with s.get(f"{HORIZON_TESTNET}/accounts/{pubkey}") as r:
            if r.status == 404:
                print(f"conta {pubkey} não existe — rodar setup_stellar_cctp_treasury.py primeiro")
                return False
            account = await r.json()

    for bal in account.get("balances", []):
        if bal.get("asset_type") == "native":
            xlm_balance = float(bal.get("balance", 0))
        elif bal.get("asset_code") == "USDC" and bal.get("asset_issuer") == usdc_issuer:
            usdc_balance = float(bal.get("balance", 0))

    print(f"tesouraria: {pubkey}")
    print(f"  XLM testnet:  {xlm_balance:.4f}")
    print(f"  USDC testnet: {usdc_balance:.4f}")

    ok = True
    if xlm_balance < 1:
        print("  FALTA XLM -> rodar setup_stellar_cctp_treasury.py (friendbot)")
        ok = False
    if usdc_balance < 0.1:
        print("  FALTA USDC -> https://faucet.circle.com -> 'Stellar Testnet' (pubkey acima)")
        ok = False
    return ok


async def poll_attestation_v2(source_tx: str) -> dict:
    """Poll da iris V2: GET /v2/messages/{27}?transactionHash={tx} — mesma API indexada
    por tx hash validada no fluxo Solana (NÃO usar o /v1/attestations do fluxo EVM v1)."""
    url = f"{IRIS_V2_SANDBOX}/{STELLAR_CCTP_DOMAIN}"
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
    parser.add_argument("--amount", type=float, default=0.5)
    parser.add_argument("--receive", action="store_true", help="completa o mint no Arc após a attestation")
    args = parser.parse_args()

    client = StellarCCTPClient(sandbox=False)
    if not client.treasury_secret:
        print("STELLAR_TREASURY_SECRET não configurada — rodar setup_stellar_cctp_treasury.py")
        sys.exit(1)

    if not await check_funding(client):
        print("\nFundear a tesouraria primeiro (instruções acima) e rodar de novo.")
        sys.exit(1)

    recipient = arc_agent_address()
    recipient_b32 = bytes(12) + bytes.fromhex(recipient[2:])
    print(f"\nburn {args.amount} USDC Stellar testnet -> Arc (domain {ARC_DOMAIN})")
    print(f"mint_recipient no Arc: {recipient}")

    result = await client.burn_usdc(
        amount_usdc=args.amount,
        destination_domain=ARC_DOMAIN,
        mint_recipient_bytes32=recipient_b32,
    )
    print(f"\nBURN CONFIRMADO: {result.tx_hash}")
    print(f"explorer: https://stellar.expert/explorer/testnet/tx/{result.tx_hash}")

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
