#!/usr/bin/env python3
"""
test_x402.py — Teste end-to-end do protocolo x402 da XiaoLee.

Fluxo completo:
    1. Gera keypair Stellar testnet
    2. Funda com Friendbot (gratuito)
    3. Envia 0.5 XLM para a carteira x402 do servidor com memo "xiaolee-ai-query"
    4. Usa o tx_hash no header X-Payment para desbloquear a query AI
    5. Imprime a resposta da XiaoLee

Uso:
    /home/f0ntz/ParaDevs-XIAOLEE/XiaoLee/.venv/bin/python scripts/test_x402.py
"""

import json
import sys
import time

import requests
from stellar_sdk import Asset, Keypair, Network, TransactionBuilder
from stellar_sdk.server import Server

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

HORIZON = "https://horizon-testnet.stellar.org"
FRIENDBOT = "https://friendbot.stellar.org"
XIAOLEE_API = "http://localhost:8000"
NETWORK_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE

# Destino do pagamento (x402 wallet do servidor — vem do /v1/ai/query/payment-info)
def get_payment_info():
    r = requests.get(f"{XIAOLEE_API}/v1/ai/query/payment-info", timeout=10)
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Passo 1: Gerar keypair e fundar com Friendbot
# ---------------------------------------------------------------------------

def setup_testnet_account():
    keypair = Keypair.random()
    print(f"\n[1] Keypair gerado:")
    print(f"    Public : {keypair.public_key}")
    print(f"    Secret : {keypair.secret}")

    print(f"\n[2] Fundando com Friendbot...")
    r = requests.get(FRIENDBOT, params={"addr": keypair.public_key}, timeout=30)
    if not r.ok:
        print(f"    ERRO Friendbot: {r.status_code} {r.text[:200]}")
        sys.exit(1)
    print(f"    OK — conta criada com 10.000 XLM de teste")
    return keypair


# ---------------------------------------------------------------------------
# Passo 2: Construir e submeter transação de pagamento
# ---------------------------------------------------------------------------

def submit_payment(keypair: Keypair, destination: str, amount: str, memo: str) -> str:
    server = Server(HORIZON)
    account = server.load_account(keypair.public_key)

    tx = (
        TransactionBuilder(
            source_account=account,
            network_passphrase=NETWORK_PASSPHRASE,
            base_fee=100,
        )
        .add_text_memo(memo)
        .append_payment_op(
            destination=destination,
            asset=Asset.native(),
            amount=amount,
        )
        .set_timeout(30)
        .build()
    )

    tx.sign(keypair)
    print(f"\n[3] Submetendo pagamento de {amount} XLM para {destination[:20]}...")
    response = server.submit_transaction(tx)
    tx_hash = response["hash"]
    print(f"    tx_hash : {tx_hash}")
    print(f"    ledger  : {response.get('ledger')}")
    return tx_hash


# ---------------------------------------------------------------------------
# Passo 3: Enviar query com X-Payment
# ---------------------------------------------------------------------------

def query_x402(tx_hash: str, message: str, stellar_wallet: str):
    x_payment = json.dumps({"tx_hash": tx_hash, "network": "testnet"})

    print(f"\n[4] Enviando query AI com X-Payment header...")
    print(f"    X-Payment : {x_payment}")
    print(f"    Mensagem  : {message}")

    r = requests.post(
        f"{XIAOLEE_API}/v1/ai/query",
        headers={
            "Content-Type": "application/json",
            "X-Payment": x_payment,
        },
        json={
            "message": message,
            "stellar_wallet": stellar_wallet,
        },
        timeout=60,
    )

    print(f"\n[5] Resposta HTTP {r.status_code}")
    if r.ok:
        data = r.json()
        print(f"\n{'='*60}")
        print(f"XiaoLee AI (via x402):")
        print(f"{'='*60}")
        print(data.get("reply", "(sem resposta)"))
        print(f"{'='*60}")
        print(f"intent       : {data.get('intent')}")
        print(f"x402_verified: {data.get('x402_verified')}")
    else:
        print(f"ERRO: {r.status_code}")
        print(r.text[:500])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("XiaoLee x402 — Teste end-to-end (Stellar Testnet)")
    print("=" * 60)

    # Obter info de pagamento do servidor
    print("\n[0] Consultando payment-info do servidor...")
    pinfo = get_payment_info()
    pay_to = pinfo["pay_to"]
    amount = pinfo["amount"]
    memo = pinfo["memo"]
    print(f"    pay_to : {pay_to}")
    print(f"    amount : {amount} XLM")
    print(f"    memo   : {memo}")

    # Garantir que o endereço destino existe no testnet
    print(f"\n[1b] Garantindo que a carteira x402 do servidor existe no testnet...")
    r_dest = requests.get(FRIENDBOT, params={"addr": pay_to}, timeout=30)
    if r_dest.ok:
        print(f"     OK — {pay_to[:20]}... criada/já existia")
    else:
        # Pode ser 400 se a conta já existir — tudo bem
        print(f"     {r_dest.status_code} — conta já existia ou friendbot recusou")

    # Setup conta testnet do usuário
    keypair = setup_testnet_account()

    # Pequeno delay para o Horizon indexar as contas
    print("\n    Aguardando Horizon indexar as contas (4s)...")
    time.sleep(4)

    # Submeter pagamento
    tx_hash = submit_payment(keypair, pay_to, amount, memo)

    # Pequeno delay para garantir que o Horizon confirmou o tx
    print("\n    Aguardando confirmação do tx (3s)...")
    time.sleep(3)

    # Query AI com o tx_hash
    message = sys.argv[1] if len(sys.argv) > 1 else "analise minha carteira Stellar e me explique o protocolo x402"
    query_x402(tx_hash, message, keypair.public_key)
