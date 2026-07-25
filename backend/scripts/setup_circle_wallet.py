#!/usr/bin/env python3
"""
setup_circle_wallet.py — Cria a developer-controlled wallet do agente XiaoLee no Circle W3S.

Execute UMA VEZ após configurar o entity secret no Circle console:
    console.circle.com → Developer → Entity Secret → Set Secret

Pré-requisitos:
    .env: CIRCLE_API_KEY=TEST_API_KEY:...
          CIRCLE_BLOCKCHAIN=ETH-SEPOLIA   (ou ARC-SEPOLIA quando disponível)

Saída:
    CIRCLE_WALLET_ID=<uuid>
    CIRCLE_WALLET_ADDRESS=0x...

Copie esses valores para o .env e mude ARC_SANDBOX=false.
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import sys
import uuid

import httpx
from dotenv import find_dotenv, load_dotenv

# Garante que `server.*` seja importável ao rodar o script direto.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from server.integrations.circle_crypto import entity_secret_ciphertext  # noqa: E402

load_dotenv(find_dotenv(usecwd=False))

_W3S_SANDBOX = "https://api.circle.com/v1/w3s"
_W3S_LIVE    = "https://api.circle.com/v1/w3s"


async def main() -> None:
    api_key       = os.getenv("CIRCLE_API_KEY", "")
    entity_secret = os.getenv("CIRCLE_ENTITY_SECRET", "")
    blockchain    = os.getenv("CIRCLE_BLOCKCHAIN", "ETH-SEPOLIA")
    sandbox       = os.getenv("ARC_SANDBOX", "true").lower() == "true"
    base          = _W3S_SANDBOX if sandbox else _W3S_LIVE

    if not api_key:
        print("[ERRO] CIRCLE_API_KEY não configurada no .env")
        sys.exit(1)

    if not entity_secret:
        print("[ERRO] CIRCLE_ENTITY_SECRET não configurada no .env")
        print("       Gere em console.circle.com → Developer → Configurator (32 bytes hex).")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }

    mode_tag = "SANDBOX" if sandbox else "LIVE"
    print(f"[setup] Circle W3S — modo {mode_tag} | blockchain={blockchain}")
    print(f"[setup] base_url={base}")
    print()

    async with httpx.AsyncClient(timeout=30) as client:

        # 1. Criar wallet set (exige entitySecretCiphertext fresco)
        ws_key  = str(uuid.uuid4())
        ws_resp = await client.post(
            f"{base}/developer/walletSets",
            json={
                "idempotencyKey":         ws_key,
                "entitySecretCiphertext": await entity_secret_ciphertext(api_key, entity_secret, base),
                "name":                   "xiaolee-agent",
            },
            headers=headers,
        )
        if not ws_resp.is_success:
            print(f"[ERRO] walletSet creation: {ws_resp.status_code} — {ws_resp.text[:400]}")
            print()
            print("Verifique:")
            print("  1. CIRCLE_API_KEY está correto")
            print("  2. Entity secret foi configurado em console.circle.com")
            sys.exit(1)

        wallet_set_id = ws_resp.json().get("data", {}).get("walletSet", {}).get("id", "")
        print(f"[ok] walletSetId={wallet_set_id}")

        # 2. Criar wallet (novo ciphertext — não reutilizar o anterior)
        w_key   = str(uuid.uuid4())
        w_resp  = await client.post(
            f"{base}/developer/wallets",
            json={
                "idempotencyKey":         w_key,
                "entitySecretCiphertext": await entity_secret_ciphertext(api_key, entity_secret, base),
                "walletSetId":            wallet_set_id,
                "blockchains":            [blockchain],
                "count":                  1,
            },
            headers=headers,
        )
        if not w_resp.is_success:
            print(f"[ERRO] wallet creation: {w_resp.status_code} — {w_resp.text[:400]}")
            sys.exit(1)

        wallets = w_resp.json().get("data", {}).get("wallets", [])
        if not wallets:
            print("[ERRO] nenhuma wallet retornada pela API")
            sys.exit(1)

        wallet     = wallets[0]
        wallet_id  = wallet.get("id", "")
        address    = wallet.get("address", "")

    print(f"[ok] wallet criada")
    print()
    print("=" * 60)
    print("Adicione ao .env:")
    print("=" * 60)
    print(f"CIRCLE_WALLET_ID={wallet_id}")
    print(f"# CIRCLE_WALLET_ADDRESS={address}   (informativo)")
    print(f"ARC_SANDBOX=false")
    print("=" * 60)
    print()
    print("Próximo passo: fondar a wallet com USDC de teste")
    if sandbox:
        print(f"  → Circle faucet: https://faucet.circle.com")
        print(f"  → Endereço: {address}")
    print()
    print(f"Depois: POST /v1/arc/wallet para verificar saldo.")


if __name__ == "__main__":
    asyncio.run(main())
