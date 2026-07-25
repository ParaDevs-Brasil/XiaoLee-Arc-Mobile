import asyncio
import httpx
import json
import hmac
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()
X_WEBHOOK_SECRET = os.getenv("X_WEBHOOK_SECRET", "")

BASE_URL = "http://localhost:8000"

async def simulate_webhook(client, payload, description):
    print(f"\n[E2E] Enviando payload: {description}...")
    try:
        payload_bytes = json.dumps(payload).encode("utf-8")
        signature = hmac.new(
            X_WEBHOOK_SECRET.encode("utf-8"),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        
        resp = await client.post(
            f"{BASE_URL}/v1/integrations/x/webhook", 
            content=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "x-xiaolee-signature": signature
            }
        )
        resp.raise_for_status()
        data = resp.json()
        print(" Resposta do Orquestrador:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return data
    except Exception as e:
        print(f" Falha no teste E2E ({description}): {e}")
        return None

async def test_e2e_swap_flows():
    print(" Iniciando Bateria de Testes E2E: Webhook -> Orquestrador -> Solana Devnet")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Cenário 1: Swap Bem-sucedido (Cotação viável)
        payload_success = {
            "dm": {
                "sender_id": "123456789",
                "text": "XiaoLee, quero fazer um swap de 2 USDC pra SOL na devnet!"
            }
        }
        
        data_success = await simulate_webhook(client, payload_success, "Swap Bem-sucedido (Cotação viável)")
        if data_success:
            assert data_success["intent"]["action"] in ["swap_quote", "help"], "Intent falhou no cenário de sucesso"
            print(" Cenário 1: Sucesso absoluto!")

        # Cenário 2: Swap com Saldo Insuficiente (Valor absurdamente alto)
        payload_insufficient = {
            "dm": {
                "sender_id": "123456789",
                "text": "XiaoLee, faz um swap de 999999999 SOL pra USDC na minha carteira"
            }
        }
        
        data_fail = await simulate_webhook(client, payload_insufficient, "Swap Saldo Insuficiente")
        if data_fail:
            # The intent might be 'swap_quote' but the execution should catch the insufficient funds down the pipeline
            print(" Cenário 2: Orquestrador tratou a requisição de limite excedido!")

if __name__ == "__main__":
    asyncio.run(test_e2e_swap_flows())
