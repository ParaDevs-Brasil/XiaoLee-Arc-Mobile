"""
mainnet_proof.py — Executa transações reais na MAINNET Stellar com as wallets do usuário.

Objetivo: gerar prova de "produto ao vivo na mainnet" (Desafio 1) e "usuários reais
com carteiras ativas" (Desafio 3) do programa 37 Graus.

O que faz, por wallet:
  - Se a conta tem trustline de USDC: executa um SWAP real XLM -> USDC via Stellar DEX
    (pathPaymentStrictSend para a própria conta). Isso é exatamente o swap da XiaoLee.
  - Se não tem trustline: faz um pagamento mínimo de XLM para a próxima wallet da lista.
  - Assina LOCALMENTE com a secret key e submete ao Horizon mainnet.
  - Imprime o tx_hash e o link no explorer.

SEGURANÇA:
  - As secret keys (S...) NUNCA são enviadas para lugar nenhum além do Horizon oficial.
  - Leia as secrets de um arquivo local que NÃO entra no git (ver --secrets-file).
  - Valores são minúsculos por padrão (0.2 XLM) e há confirmação antes de enviar.

USO:
  1) Crie um arquivo local com UMA secret key (S...) por linha, ex: mainnet_secrets.txt
  2) Rode (dry-run primeiro, não envia nada):
       .venv/bin/python backend/scripts/stellar/mainnet_proof.py --secrets-file mainnet_secrets.txt --dry-run
  3) Execute de verdade:
       .venv/bin/python backend/scripts/stellar/mainnet_proof.py --secrets-file mainnet_secrets.txt --yes
"""

from __future__ import annotations

import argparse
import sys
import time
from decimal import Decimal

from stellar_sdk import (
    Asset,
    Keypair,
    Network,
    Server,
    TransactionBuilder,
)
from stellar_sdk.exceptions import BaseHorizonError, NotFoundError

HORIZON_MAINNET = "https://horizon.stellar.org"
PASSPHRASE = Network.PUBLIC_NETWORK_PASSPHRASE
# USDC oficial da Circle na mainnet Stellar
USDC_MAINNET_ISSUER = "GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN"
USDC = Asset("USDC", USDC_MAINNET_ISSUER)
EXPLORER = "https://stellar.expert/explorer/public/tx/"


def load_secrets(path: str) -> list[str]:
    out = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            s = line.strip()
            if s and s.startswith("S") and len(s) == 56:
                out.append(s)
    if not out:
        sys.exit(f"Nenhuma secret key valida (S..., 56 chars) encontrada em {path}")
    return out


def has_usdc_trustline(account_json: dict) -> bool:
    for b in account_json.get("balances", []):
        if (
            b.get("asset_code") == "USDC"
            and b.get("asset_issuer") == USDC_MAINNET_ISSUER
        ):
            return True
    return False


def build_swap(server: Server, kp: Keypair, send_amount: str, slippage: float):
    """pathPaymentStrictSend XLM -> USDC para a propria conta (swap real no DEX)."""
    pub = kp.public_key
    source = server.load_account(pub)

    # Quote: quanto de USDC sai de send_amount XLM
    paths = (
        server.strict_send_paths(Asset.native(), send_amount, [USDC]).call()
    )
    records = paths.get("_embedded", {}).get("records", [])
    if not records:
        return None  # sem rota -> caller faz fallback
    best = max(records, key=lambda r: Decimal(r.get("destination_amount", "0")))
    dest_amount = Decimal(best["destination_amount"])
    dest_min = (dest_amount * Decimal(1 - slippage)).quantize(Decimal("0.0000001"))

    tx = (
        TransactionBuilder(source, PASSPHRASE, base_fee=200)
        .add_text_memo("XiaoLee swap mainnet")
        .append_path_payment_strict_send_op(
            destination=pub,
            send_asset=Asset.native(),
            send_amount=send_amount,
            dest_asset=USDC,
            dest_min=str(dest_min),
            path=[Asset(p["asset_code"], p["asset_issuer"]) if p.get("asset_type") != "native" else Asset.native() for p in best.get("path", [])],
        )
        .set_timeout(120)
        .build()
    )
    return tx, f"swap {send_amount} XLM -> ~{dest_amount} USDC"


def build_payment(server: Server, kp: Keypair, dest_pub: str, amount: str):
    source = server.load_account(kp.public_key)
    tx = (
        TransactionBuilder(source, PASSPHRASE, base_fee=200)
        .add_text_memo("XiaoLee payment mainnet")
        .append_payment_op(destination=dest_pub, asset=Asset.native(), amount=amount)
        .set_timeout(120)
        .build()
    )
    return tx, f"payment {amount} XLM -> {dest_pub[:6]}...{dest_pub[-4:]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--secrets-file", required=True, help="arquivo com 1 secret key (S...) por linha")
    ap.add_argument("--amount", default="0.2", help="quantia XLM por tx (default 0.2)")
    ap.add_argument("--slippage", type=float, default=0.03, help="slippage do swap (default 3%%)")
    ap.add_argument("--count", type=int, default=5, help="quantas transacoes executar (default 5)")
    ap.add_argument("--dry-run", action="store_true", help="nao envia, so mostra o plano")
    ap.add_argument("--yes", action="store_true", help="confirma o envio real")
    args = ap.parse_args()

    secrets = load_secrets(args.secrets_file)
    keypairs = [Keypair.from_secret(s) for s in secrets]
    pubs = [kp.public_key for kp in keypairs]
    server = Server(HORIZON_MAINNET)

    print(f"\nMAINNET Stellar | {len(keypairs)} wallets | meta: {args.count} transacoes\n")

    results = []
    sent = 0
    for i, kp in enumerate(keypairs):
        if sent >= args.count:
            break
        pub = kp.public_key
        try:
            acc_json = server.accounts().account_id(pub).call()
        except NotFoundError:
            print(f"[{pub[:6]}...] conta nao existe na mainnet — pulando")
            continue

        try:
            if has_usdc_trustline(acc_json):
                built = build_swap(server, kp, args.amount, args.slippage)
                if built is None:
                    dest = pubs[(i + 1) % len(pubs)]
                    built = build_payment(server, kp, dest, args.amount)
            else:
                dest = pubs[(i + 1) % len(pubs)]
                built = build_payment(server, kp, dest, args.amount)
        except Exception as exc:  # noqa: BLE001
            print(f"[{pub[:6]}...] erro ao montar tx: {exc}")
            continue

        tx, desc = built
        print(f"[{pub[:6]}...{pub[-4:]}] {desc}")

        if args.dry_run or not args.yes:
            results.append((pub, "DRY-RUN", desc))
            sent += 1
            continue

        tx.sign(kp)
        try:
            resp = server.submit_transaction(tx)
            h = resp["hash"]
            print(f"    OK -> {EXPLORER}{h}")
            results.append((pub, h, desc))
            sent += 1
            time.sleep(1)
        except BaseHorizonError as exc:
            codes = getattr(exc, "extras", {}) or {}
            print(f"    FALHOU: {codes.get('result_codes', exc)}")
            results.append((pub, "FALHOU", desc))

    print("\n===== RESUMO =====")
    for pub, h, desc in results:
        link = f"{EXPLORER}{h}" if h not in ("DRY-RUN", "FALHOU") else h
        print(f"{pub[:6]}...{pub[-4:]} | {desc}\n   {link}")

    ok = [r for r in results if r[1] not in ("DRY-RUN", "FALHOU")]
    if not args.dry_run and args.yes:
        print(f"\n{len(ok)} transacoes confirmadas na mainnet.")
    elif args.dry_run or not args.yes:
        print("\nDRY-RUN. Para enviar de verdade, rode de novo com --yes")


if __name__ == "__main__":
    main()
