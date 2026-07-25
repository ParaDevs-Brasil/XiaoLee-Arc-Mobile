#!/usr/bin/env python3
"""
backfill_real_payments.py — grava no DB as 16 transações USDC reais confirmadas na Arc
testnet em 29/jun/2026 (20:31–21:50 BRT), feitas manualmente por f0ntz antes da tabela
`settled_payments` existir (o feed de tração era só in-memory e foi perdido em restart).

Escreve direto via DatabaseRepository.create_settled_payment — NÃO passa pela rota HTTP
POST /v1/payments/settled, porque esse endpoint dispara um Circle transfer real para o
creator se houver wallet registrada (settings.circle_api_key) e isso recriaria as
transferências já feitas ontem. Backfill é só registro contábil/histórico.

Idempotente: intent_id = tx hash (re-rodar o script não duplica linhas).

Uso:
  cd backend && ../.venv/bin/python scripts/backfill_real_payments.py
"""
from __future__ import annotations

import asyncio
import pathlib
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from database.database import init_db  # noqa: E402
from database.repository import DatabaseRepository  # noqa: E402

# (creator_handle, amount_usdc, tx_hash) — fonte: thread do time, 29/jun/2026 20:31–21:50 BRT.
# latency_ms não foi capturada no momento (chamadas manuais) — fica 0.0, sinalizando "sem telemetria".
REAL_PAYMENTS: list[tuple[str, float, str]] = [
    ("@agent_arc_native", 0.10, "0x73f7399d74af55a0dca6e17e8b853b00770ba25c5059ef290809307abbd87de1"),
    ("@music_nft",        0.10, "0xa0b1f3c5f0ccb8a28424413ce65baa963c7dd7cd64e7773cc6155d4409cd7b3a"),
    ("@music_nft",        0.50, "0x96d66e972ed976b8adcf18484f4b030a99135da3b67cb01a06da29df84bd7cad"),
    ("@music_nft",        0.25, "0x047704b703d42a17a496a5ba5f952c5719dc0a3a90cb462bd0b72f7b4cef3bb9"),
    ("@music_nft",        0.05, "0x2bad16e5cffb530b576a036f2584d7bfc2dfe6425f8e23b0aa28169174199863"),
    ("@xiaolee_demo",     1.00, "0x159c53758b9018e95511dccd0000dfb7b2cbf2877e56d1762f3e2c68e3e6e0cc"),
    ("@xiaolee_demo",     0.20, "0x6e0aec76cd7eb6d9b51369514efe9307f5c3e5b290b90afec8874e1a817b29ac"),
    ("@xiaolee_demo",     0.20, "0x7de073ed7f64c0a6780ddf2308d4ea6f658c5bc4f948fe057a26c6de0a2e6119"),
    ("@xiaolee_demo",     0.05, "0x84143d387f9c7409352829cfc1264752cf58419ad873c1d105bbd7f3a483fd3e"),
    ("@web3_creator",     0.15, "0x20a6617794a71127fecbc7010e37ec9f40d95f23696a2ebf0e376fc6352c2e5b"),
    ("@web3_creator",     0.15, "0xc703e5345df46e411a6066a4b659adf942218481e58ffabf701dfa6ae3475177"),
    ("@web3_creator",     0.05, "0x55f5b0b881072fb5d61e7c0d4be2acf47331be850710d88ce36b776ca01cf1f8"),
    ("@web3_creator",     0.05, "0xf616670ada0f82011d62e7437be7c178b24d1967d380413deaf5721741412c14"),
    ("@pixel_art",        0.50, "0x5ffa584c24d3825653ae2643c815d3c2c9d42112bb87e18c2ec82e2d66925d10"),
    ("@solana_dev",       0.10, "0x0ce6cd0a30898b56d5e2eca983ae33cbc512af18a478cf77a87f29ca658f0165"),
    ("@defi_builder",     0.10, "0xc9ca2bce5c05ba22a4b447029bb70394900db9ed4e6104ea93345d9f900afc3b"),
]

_WINDOW_START = datetime(2026, 6, 29, 20, 31, 0, tzinfo=timezone(timedelta(hours=-3)))
_WINDOW_END   = datetime(2026, 6, 29, 21, 50, 0, tzinfo=timezone(timedelta(hours=-3)))


async def main() -> None:
    _, session_factory = init_db()

    step = (_WINDOW_END - _WINDOW_START) / max(len(REAL_PAYMENTS) - 1, 1)

    inserted, skipped = 0, 0
    async with session_factory() as session:
        repo = DatabaseRepository(session)
        for i, (creator, amount, tx) in enumerate(REAL_PAYMENTS):
            ts = (_WINDOW_START + step * i).isoformat()
            is_new = await repo.create_settled_payment(
                intent_id=tx,  # tx hash é único e real — serve de chave de idempotência
                creator_handle=creator,
                amount_usdc=amount,
                tx=tx,
                latency_ms=0.0,
                ts=ts,
            )
            if is_new:
                inserted += 1
                print(f"  [ok] {creator:<20} ${amount:.2f} USDC | {tx[:20]}...")
            else:
                skipped += 1
                print(f"  [skip] já existia: {tx[:20]}...")

    total = sum(a for _, a, _ in REAL_PAYMENTS)
    print()
    print(f"Inseridos: {inserted} | já existentes: {skipped} | total no lote: ${total:.2f} USDC")
    print("Reinicie o backend (make dev) para hidratar o dashboard com esses dados.")


if __name__ == "__main__":
    asyncio.run(main())
