"""
cctp_arc_to_stellar_demo.py — Burn USDC REAL Arc -> mint em Stellar via CctpForwarder.

Diferente dos outros demos, este usa o CAMINHO DE PRODUÇÃO inteiro:
CCTPClient.burn_and_attest(hook_data=...) — o mesmo código que o agente chama via
payout_cross_chain_nanopayment — e StellarCCTPClient.mint_and_forward no destino.

REGRA CCTP-Stellar exercitada aqui (fundos presos se violar): mint_recipient e
destination_caller do burn no Arc = contrato CctpForwarder; o destinatário Stellar real
vai no hook_data (v0: magic + version/len BE + strkey UTF-8).

Uso:
    cd backend && ../.venv/bin/python scripts/cctp_arc_to_stellar_demo.py [--amount 0.05] [--to G...]

--to default: a própria tesouraria Stellar (já tem trustline USDC — o forward exige).
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
from server.integrations.cctp_client import CCTPClient
from server.integrations.stellar_adapter import HORIZON_TESTNET, usdc_issuer_for
from server.integrations.stellar_cctp import (
    STELLAR_CCTP_DOMAIN,
    StellarCCTPClient,
    build_hook_data,
)


async def stellar_usdc_balance(account: str) -> float:
    usdc_issuer = usdc_issuer_for("testnet")
    async with aiohttp.ClientSession() as s:
        async with s.get(f"{HORIZON_TESTNET}/accounts/{account}") as r:
            if r.status == 404:
                return -1.0
            data = await r.json()
    for bal in data.get("balances", []):
        if bal.get("asset_code") == "USDC" and bal.get("asset_issuer") == usdc_issuer:
            return float(bal.get("balance", 0))
    return -1.0


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--amount", type=float, default=0.05)
    parser.add_argument("--to", default="", help="strkey Stellar destinatário (default: tesouraria)")
    args = parser.parse_args()

    stellar = StellarCCTPClient(sandbox=False)
    if not stellar.treasury_secret:
        print("STELLAR_TREASURY_SECRET não configurada — rodar setup_stellar_cctp_treasury.py")
        sys.exit(1)
    recipient = args.to or stellar.address

    balance_before = await stellar_usdc_balance(recipient)
    if balance_before < 0:
        print(f"AVISO: {recipient} sem conta/trustline USDC — o forward vai falhar. Abortando.")
        sys.exit(1)

    arc = CCTPClient(
        source_rpc=settings.arc_rpc_url,
        signer_key=settings.arc_agent_private_key,
        source_domain=settings.arc_cctp_domain,
        source_usdc=settings.arc_usdc_address,
        source_token_messenger=settings.arc_cctp_token_messenger,
        sandbox=False,
        abi_version=2,
    )

    forwarder_b32 = stellar.forwarder_bytes32()
    hook = build_hook_data(recipient)

    print(f"burn {args.amount} USDC Arc -> Stellar (domain {STELLAR_CCTP_DOMAIN})")
    print(f"mint_recipient/destination_caller: CctpForwarder {stellar.forwarder_contract}")
    print(f"destinatário real (hook_data): {recipient}")
    print(f"saldo USDC destino antes: {balance_before:.7f}")

    state = await arc.burn_and_attest(
        amount_usdc=args.amount,
        recipient_bytes32=forwarder_b32,
        destination_domain=STELLAR_CCTP_DOMAIN,
        destination_caller_bytes32=forwarder_b32,
        hook_data=hook,
    )
    print(f"\nBURN NO ARC CONFIRMADO: {state.source_tx_hash}")
    print("ATTESTATION COMPLETA (iris V2)")

    mint = await stellar.mint_and_forward(
        raw_message=state.raw_message,
        attestation=state.attestation,
    )
    print(f"\nMINT+FORWARD EM STELLAR CONFIRMADO: {mint.tx_hash}")
    print(f"explorer: https://stellar.expert/explorer/testnet/tx/{mint.tx_hash}")

    balance_after = await stellar_usdc_balance(recipient)
    print(f"saldo USDC destino depois: {balance_after:.7f} (Δ {balance_after - balance_before:+.7f})")

    print(json.dumps({
        "arc_burn_tx": state.source_tx_hash,
        "stellar_mint_tx": mint.tx_hash,
        "recipient": recipient,
        "delta_usdc": round(balance_after - balance_before, 7),
    }, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
