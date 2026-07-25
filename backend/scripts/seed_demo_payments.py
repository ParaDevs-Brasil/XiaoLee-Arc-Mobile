"""
Dispara pagamentos de demo no endpoint /v1/payments/settled para testar o dashboard
sem depender do agente Arc.

Uso:
  python backend/scripts/seed_demo_payments.py
  python backend/scripts/seed_demo_payments.py --host https://api.xiaolee.io --count 20
"""
from __future__ import annotations

import argparse
import random
import time
import uuid

import requests

CREATORS = [
    "@xiaolee_demo",
    "@creator_br",
    "@defi_builder",
    "@nft_artist",
    "@solana_dev",
    "@web3_creator",
    "@music_nft",
    "@pixel_art",
]

AMOUNTS = [0.05, 0.10, 0.15, 0.20, 0.25, 0.50, 1.00]


def seed(host: str, count: int, secret: str, delay: float) -> None:
    url = f"{host}/v1/payments/settled"
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["X-Arc-Secret"] = secret

    print(f"Disparando {count} pagamentos demo → {url}\n")

    for i in range(1, count + 1):
        creator = random.choice(CREATORS)
        amount = random.choice(AMOUNTS)
        latency = round(random.uniform(80, 490), 1)
        payload = {
            "intent_id": str(uuid.uuid4()),
            "amount": amount,
            "creator": creator,
            "tx": "demo_" + uuid.uuid4().hex[:16],
            "latency_ms": latency,
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=5)
            status = "OK" if resp.ok else f"ERR {resp.status_code}"
            print(f"  [{i:02d}/{count}] {status} | {creator} | ${amount:.2f} USDC | {latency}ms")
        except Exception as exc:
            print(f"  [{i:02d}/{count}] FALHOU: {exc}")

        if delay > 0 and i < count:
            time.sleep(delay)

    print("\nPronto. Abra /traction para ver o dashboard.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://localhost:8000")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--secret", default="")
    parser.add_argument("--delay", type=float, default=0.3, help="segundos entre pagamentos")
    args = parser.parse_args()

    seed(args.host, args.count, args.secret, args.delay)
