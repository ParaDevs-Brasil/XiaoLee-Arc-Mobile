"""
fix_dex_price.py — Corrige a taxa XLM/USDC no DEX testnet.

Problema: offer 113468 vende USDC a 0.1 XLM/USDC (1 XLM = 10 USDC) — irreal.
Real:     XLM ~$0.10, USDC $1.00 → 1 USDC = ~10 XLM.

Solução em 2 passos:
  1. Emissor faz manage_buy_offer para comprar e queimar todos os 49k USDC do offer antigo.
  2. Emissor coloca nova offer: vende USDC a 10 XLM/USDC (emite tokens sob demanda).
"""

import os

import requests
from stellar_sdk import (
    Asset,
    Keypair,
    Network,
    TransactionBuilder,
)
from stellar_sdk.server import Server

HORIZON = "https://horizon-testnet.stellar.org"

ISSUER_SECRET = os.environ["STELLAR_ISSUER_SECRET"]  # REDACTED_ROTATE_BEFORE_USE — set in .env, never hardcode
USDC_ISSUER   = "GAAXKLIMFWX7XLKVXGUVJI7X533OOZH2YS2RLMQVY3TP5QLXRRWXHDI5"
OLD_OFFER_ID  = 113468


def check_old_offer() -> float:
    r = requests.get(
        f"{HORIZON}/offers",
        params={
            "selling_asset_type": "credit_alphanum4",
            "selling_asset_code": "USDC",
            "selling_asset_issuer": USDC_ISSUER,
        },
        timeout=10,
    )
    records = r.json().get("_embedded", {}).get("records", [])
    for o in records:
        if int(o["id"]) == OLD_OFFER_ID:
            amt = float(o["amount"])
            print(f"Offer {OLD_OFFER_ID} encontrada: {amt} USDC a {o['price']} XLM/USDC")
            return amt
    print("Offer antiga não encontrada (já foi drenada ou não existe).")
    return 0.0


def drain_and_reset():
    keypair = Keypair.from_secret(ISSUER_SECRET)
    server  = Server(HORIZON)
    usdc    = Asset("USDC", USDC_ISSUER)
    xlm     = Asset.native()

    old_amount = check_old_offer()

    account = server.load_account(keypair.public_key)
    builder = TransactionBuilder(
        source_account=account,
        network_passphrase=Network.TESTNET_NETWORK_PASSPHRASE,
        base_fee=200,
    )

    if old_amount > 0:
        # Passo 1: Emissor compra todos os USDC do offer antigo (queima os tokens)
        # price = max XLM por USDC que o emissor topa pagar (acima de 0.1 → preenche offer)
        buy_amount = f"{old_amount:.7f}"
        print(f"\nPasso 1: Comprando {buy_amount} USDC do offer antigo @ até 0.2 XLM/USDC...")
        builder.append_manage_buy_offer_op(
            selling=xlm,
            buying=usdc,
            amount=buy_amount,
            price="0.2",   # willing to pay up to 0.2 XLM/USDC → preenche o 0.1 offer
            offer_id=0,
        )
    else:
        print("\nPasso 1: pulado (offer antiga não existe).")

    # Passo 2: Emissor cria nova offer: vende USDC (emite on-demand) a 10 XLM/USDC
    print(f"Passo 2: Criando offer 50.000 USDC a 10 XLM/USDC...")
    builder.append_manage_sell_offer_op(
        selling=usdc,
        buying=xlm,
        amount="50000",
        price="10",   # 10 XLM por 1 USDC — taxa realista
        offer_id=0,   # 0 = nova offer
    )

    builder.set_timeout(60)
    tx = builder.build()
    tx.sign(keypair)

    resp = server.submit_transaction(tx)
    print(f"\nTx hash : {resp['hash']}")
    print(f"Ledger  : {resp['ledger']}")
    print(f"\nhttps://stellar.expert/explorer/testnet/tx/{resp['hash']}")

    # Confirma resultado
    print("\n--- Ofertas USDC→XLM agora ---")
    r = requests.get(
        f"{HORIZON}/offers",
        params={
            "selling_asset_type": "credit_alphanum4",
            "selling_asset_code": "USDC",
            "selling_asset_issuer": USDC_ISSUER, 
            "selling_asset_issuer": USDC_ISSUER,
        },
        timeout=10,
    )
    for o in r.json().get("_embedded", {}).get("records", []):
        print(f"  Offer {o['id']}: {o['amount']} USDC @ {o['price']} XLM/USDC  (seller={o['seller'][:8]}...)")


if __name__ == "__main__":
    drain_and_reset()
