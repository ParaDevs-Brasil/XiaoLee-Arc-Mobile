"""
setup_stellar_cctp_treasury.py — Cria a tesouraria Stellar testnet do CCTP (uma vez).

Fluxo:
    1. Reusa STELLAR_TREASURY_SECRET do .env se existir; senão gera keypair novo
    2. Funda a conta com XLM via friendbot (testnet)
    3. Cria trustline pro USDC oficial da Circle (GBBD47IF... — o mesmo do faucet/CCTP)
    4. Imprime o pubkey pra pedir USDC em https://faucet.circle.com -> "Stellar Testnet"

Chave DEDICADA de tesouraria — nunca reaproveitar STELLAR_SERVER_SECRET (SEP-10).

Uso:
    cd backend && ../.venv/bin/python scripts/setup_stellar_cctp_treasury.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(ENV_PATH)

import httpx
from stellar_sdk import Asset, Keypair, Network, Server, TransactionBuilder

from server.integrations.stellar_adapter import HORIZON_TESTNET, usdc_issuer_for

FRIENDBOT = "https://friendbot.stellar.org"


def ensure_keypair() -> Keypair:
    secret = os.getenv("STELLAR_TREASURY_SECRET", "")
    if secret:
        kp = Keypair.from_secret(secret)
        print(f"tesouraria existente no .env: {kp.public_key}")
        return kp

    kp = Keypair.random()
    with ENV_PATH.open("a") as f:
        f.write(f"\n# Tesouraria CCTP Stellar testnet (gerada por setup_stellar_cctp_treasury.py)\n")
        f.write(f"STELLAR_TREASURY_SECRET={kp.secret}\n")
    print(f"tesouraria NOVA gerada e salva no .env: {kp.public_key}")
    return kp


def fund_with_friendbot(pubkey: str) -> None:
    r = httpx.get(FRIENDBOT, params={"addr": pubkey}, timeout=30)
    if r.status_code == 200:
        print("friendbot: conta fundada com 10.000 XLM testnet")
    elif r.status_code == 400 and "createAccountAlreadyExist" in r.text:
        print("friendbot: conta já existia (ok)")
    else:
        raise RuntimeError(f"friendbot falhou: {r.status_code} {r.text[:200]}")


def ensure_usdc_trustline(kp: Keypair) -> None:
    server = Server(HORIZON_TESTNET)
    account = server.load_account(kp.public_key)
    usdc = Asset("USDC", usdc_issuer_for("testnet"))

    existing = server.accounts().account_id(kp.public_key).call()
    for bal in existing.get("balances", []):
        if bal.get("asset_code") == "USDC" and bal.get("asset_issuer") == usdc.issuer:
            print(f"trustline USDC já existe (saldo: {bal.get('balance')})")
            return

    tx = (
        TransactionBuilder(account, Network.TESTNET_NETWORK_PASSPHRASE, base_fee=100)
        .append_change_trust_op(asset=usdc)
        .set_timeout(30)
        .build()
    )
    tx.sign(kp)
    resp = server.submit_transaction(tx)
    print(f"trustline USDC criada: {resp['hash']}")


def main() -> None:
    kp = ensure_keypair()
    fund_with_friendbot(kp.public_key)
    ensure_usdc_trustline(kp)
    print("\nsetup completo. Falta só o USDC:")
    print(f"  https://faucet.circle.com -> 'Stellar Testnet' -> {kp.public_key}")


if __name__ == "__main__":
    main()
