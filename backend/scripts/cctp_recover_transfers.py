"""
cctp_recover_transfers.py — Recovery de transfers CCTP com burn confirmado e mint pendente.

É a contraparte operacional do padrão "intent durável antes de executar": se o processo
morre (ou o mint falha por erro transitório) DEPOIS do burn, o registro em cctp_transfers
fica failed/attested com o source_tx_hash real — o USDC está queimado na origem e a
attestation da Circle continua válida indefinidamente. Este script varre esses registros,
busca message+attestation na iris V2 pelo tx hash do burn e completa o mint no domain
de destino (Solana receive_and_mint / Stellar mint_and_forward via CctpForwarder).

Idempotente: mint já executado on-chain resulta em erro de nonce usado — o registro é
marcado received manualmente nesse caso não é necessário (re-rodar é seguro).

Uso:
    cd backend && ../.venv/bin/python scripts/cctp_recover_transfers.py           # dry-run (lista)
    cd backend && ../.venv/bin/python scripts/cctp_recover_transfers.py --execute
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

import httpx
from sqlalchemy import select

from database.database import init_db
from database.models import CctpTransfer
from server.settings import settings

_, SessionLocal = init_db()

IRIS_V2 = "https://iris-api-sandbox.circle.com/v2/messages"
ARC_DOMAIN = 26
SOLANA_DOMAIN = 5
STELLAR_DOMAIN = 27


def fetch_attested(source_domain: int, tx_hash: str) -> dict | None:
    tx = tx_hash if tx_hash.startswith("0x") else f"0x{tx_hash}"
    r = httpx.get(f"{IRIS_V2}/{source_domain}", params={"transactionHash": tx}, timeout=30)
    if not r.is_success:
        return None
    for m in r.json().get("messages", []):
        if m.get("status") == "complete" and m.get("attestation"):
            return m
    return None


async def complete_mint(transfer: CctpTransfer, message: dict) -> str:
    raw_message = bytes.fromhex(message["message"].removeprefix("0x"))
    attestation = bytes.fromhex(message["attestation"].removeprefix("0x"))

    if transfer.dest_domain == SOLANA_DOMAIN:
        from server.integrations.solana_cctp import SolanaCCTPClient

        client = SolanaCCTPClient(sandbox=False)
        src_usdc = settings.arc_usdc_address
        burn_token_b32 = bytes(12) + bytes.fromhex(src_usdc.removeprefix("0x"))
        result = await client.receive_and_mint(
            raw_message=raw_message,
            attestation=attestation,
            recipient_owner_b58=transfer.counterparty,
            source_domain=transfer.source_domain,
            burn_token_bytes_32=burn_token_b32,
        )
        return result.tx_hash

    if transfer.dest_domain == STELLAR_DOMAIN:
        from server.integrations.stellar_cctp import StellarCCTPClient

        client = StellarCCTPClient(sandbox=False)
        result = await client.mint_and_forward(raw_message=raw_message, attestation=attestation)
        return result.tx_hash

    raise RuntimeError(f"dest_domain {transfer.dest_domain} sem cliente de recovery")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="completa os mints (default: só lista)")
    args = parser.parse_args()

    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(CctpTransfer)
                .where(CctpTransfer.status.in_(("failed", "attested")))
                .order_by(CctpTransfer.id)
            )
        ).scalars().all()

        candidates = [t for t in rows if t.source_tx_hash and not t.source_tx_hash.startswith("0xSANDBOX")]
        print(f"{len(candidates)} transfer(s) com burn real e mint pendente:")
        for t in candidates:
            print(f"  {t.intent_id[:8]} | {t.status} | domain {t.source_domain}->{t.dest_domain} | "
                  f"{float(t.amount_usdc):.4f} USDC -> {t.counterparty[:12]}... | burn={t.source_tx_hash[:16]}...")

        if not args.execute or not candidates:
            if candidates:
                print("\n(rode com --execute pra completar os mints)")
            return

        for t in candidates:
            print(f"\nrecuperando {t.intent_id[:8]}...")
            message = fetch_attested(t.source_domain, t.source_tx_hash)
            if not message:
                print("  attestation não disponível na iris — pulando")
                continue
            try:
                dest_tx = await complete_mint(t, message)
            except Exception as exc:
                print(f"  mint falhou: {exc}")
                continue
            t.status = "received"
            t.dest_tx_hash = dest_tx
            t.error_message = None
            print(f"  RECUPERADO: mint tx={dest_tx}")

        await session.commit()
        print("\nrecovery concluído.")


if __name__ == "__main__":
    asyncio.run(main())
