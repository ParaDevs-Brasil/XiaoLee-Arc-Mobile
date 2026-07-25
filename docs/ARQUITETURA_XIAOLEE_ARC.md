# Arquitetura XiaoLee — Stack Arc/USDC

> Hackathon Lepton Agents (Circle/Arc/Canteen) — deadline 6 jul 2026
> Criterios: Agentic 30% · Traction 30% · Circle Tools 20% · Innovation 20%

---

## 1. Estado atual dos componentes Arc

### arc_client.py — `backend/server/integrations/arc_client.py`

**Status: PRONTO**

Circle Programmable Wallets (W3S), developer-controlled wallet. Suporta sandbox completo (zero chamadas de rede, dados deterministicos).

Metodos relevantes:
- `send_usdc(to, amount_usdc, idempotency_key)` — envia USDC via Circle W3S; retorna arc_tx_hash (live) ou fake_id (sandbox)
- `get_transfer_result(circle_id)` — estado atual de uma transacao Circle; retorna `TransferResult.confirmed`
- `get_usdc_balance()` — saldo USDC na wallet do agente; sandbox = 1000.0 USDC
- `get_wallet_info()` — endereco EVM, blockchain, estado da wallet

Dependencia interna: `circle_crypto.py` gera `entitySecretCiphertext` fresco por transacao (exigido pela Circle em developer wallets).

Pendente: `ARC-SEPOLIA` nao esta na tabela `_SANDBOX_USDC_TOKEN_IDS`. Se o blockchain configurado for `ARC-SEPOLIA`, o token_id sera buscado via API Circle (requer conectividade e credenciais validas).

---

### arc_native.py — `backend/server/integrations/arc_native.py`

**Status: PRONTO**

Cliente EVM direto (Web3.py), assina com `ARC_AGENT_PRIVATE_KEY`. Caminho soberano sem Circle W3S.

Funcoes:
- `send_usdc(to, amount_usdc)` — ERC-20 transfer direto no Arc; gas pago em USDC
- `receive_cctp_message(msg_transmitter, raw_message, attestation)` — chama `receiveMessage()` no Arc para completar o bridge CCTP (permissionless)
- `get_usdc_balance()` — saldo on-chain ground truth

Pendente: `web3>=6.20.0` e `eth_abi` devem estar no `requirements.txt`. Se ausentes, falha com RuntimeError na inicializacao lazy.

---

### arc_routes.py — `backend/server/routes/arc_routes.py`

**Status: PRONTO**

Prefixo `/v1/arc`, tag `arc`. Ja incluido em `app.py`.

Endpoints existentes:
- `GET /v1/arc/wallet` — info + saldo USDC da wallet do agente
- `GET /v1/arc/wallet/balance` — saldo rapido para o dashboard Traction
- `POST /v1/arc/cctp/bridge` — bridge USDC de outra chain para o Arc
- `GET /v1/arc/cctp/status/{message_hash}` — status de attestation Circle (iris-api)
- `GET /v1/arc/healthcheck` — valida conectividade com Circle API

---

### arc_x402_routes.py — `backend/server/routes/arc_x402_routes.py`

**Status: CRIADO nesta sessao**

Prefixo `/v1/arc/ai`, tag `arc-x402`. Ainda NAO incluido em `app.py` (pendente — ver secao 7).

Endpoints:
- `POST /v1/arc/ai/query` — AI query com gate x402 Arc/USDC
- `GET /v1/arc/ai/query/payment-info` — info do pagamento atual
- `GET /v1/arc/ai/query/verify-transfer` — debug: verifica circle_id manualmente

---

### cctp_client.py — `backend/server/integrations/cctp_client.py`

**Status: PRONTO**

Bridge USDC de qualquer chain EVM para o Arc via CCTP v2. Fluxo 4 passos: approve → depositForBurn → poll_attestation (iris-api) → receiveMessage no Arc.

Pendentes (aguardar docs do Discord Lepton):
- `ARC_CCTP_MSG_TRANSMITTER` — endereco do MessageTransmitter no Arc Canteen
- `ARC_CCTP_USDC` — endereco do USDC no Arc Canteen
- `ARC_CCTP_DOMAIN` — domain ID do Arc no CCTP (default: 7, confirmar)

---

### pqc_receipt.py — `backend/services/pqc_receipt.py`

**Status: PRONTO**

Assina recibos de pagamento com ML-DSA-87 (FIPS 204). Em dev sem `PQC_SECRET_KEY`, gera keypair efemero com warning.

Interface publica:
- `sign_receipt(intent_id, to, amount_usdc, arc_tx_hash)` — retorna `"<sig_b64>.<payload_b64>"`
- `verify_receipt(receipt_pqc)` — verifica independentemente (sem a chave privada)
- `generate_keypair()` — CLI para gerar par permanente

Pendente: `dilithium-py` deve estar no `requirements.txt`.

---

### x402_routes.py — `backend/server/routes/x402_routes.py`

**Status: FUNCIONANDO, mas aponta para Stellar/XLM**

Este e o gap critico (ver secao 4). O router responde em `/v1/ai` e retorna `"network": "stellar"` no 402.

---

### claude_agent.py — `backend/claude_agent.py`

**Status: EXISTE (ClaudeAgentEngine)**

Loop agentioco multi-step Anthropic. Base do criterio Agentic 30%.

---

### creator_pay_tools.py — `backend/ai/agents/creator_pay_tools.py`

**Status: EXISTE**

4 tools do agente: `discover_creators`, `evaluate_creator`, `check_budget`, `pay_creator_nanopayment`. A tool `pay_creator_nanopayment(intent_id, to, amount_usdc)` usa ArcClient.send_usdc() internamente com `idempotency_key=str(uuid4())`.

---

## 2. Fluxo end-to-end

```
User
  |
  | POST /v1/arc/ai/query   (sem X-Payment)
  v
arc_x402_routes.py
  |  _arc_x402_enabled() == True
  |  _build_payment_info() → pay_to = ARC_X402_WALLET_ADDRESS, asset=USDC, blockchain=ETH-SEPOLIA
  |
  +---> 402 Payment Required
        body.payment  = { version, network="arc", asset="USDC", amount, pay_to, blockchain, expires }
        header X-Payment-Required = JSON acima

User (ou cliente automatico)
  |
  | Envia USDC via Circle W3S para pay_to
  | Obtem circle_id da transacao Circle
  |
  | POST /v1/arc/ai/query   (com header X-Payment: {"circle_id": "..."})
  v
arc_x402_routes.py
  |
  | _verify_payment_arc(x_payment, arc)
  |   json.loads(x_payment) → circle_id
  |   ArcClient.get_transfer_result(circle_id)
  |     sandbox: TransferResult(confirmed=True, ...)  [sem chamada de rede]
  |     live:    GET /v1/w3s/transactions/{circle_id}  via Circle API
  |              valida: status=CONFIRMED, to==ARC_X402_WALLET_ADDRESS, amount>=preco
  |
  | payment_valid == True
  |
  | db.add(UsedPayment(tx_hash=circle_id, user_id, amount_xlm=price_usdc, network="arc"))
  | db.flush()  → IntegrityError se circle_id ja usado (anti-replay SEC-001)
  |
  | repo.get_or_create_user("web", user_id)
  | repo.get_user_history(user.id, limit=10)
  | repo.log_dm(...)
  |
  | orchestrator.execute(text_with_ctx, user_id, history=history)
  |   OrchestrationService detecta intent
  |   ClaudeAgentEngine executa loop multi-step se intent == campaign/pay
  |   Retorna { reply_text, intent, execution }
  |
  | repo.log_dm(...)  (resposta do bot)
  | db.commit()
  |
  +---> 200 OK
        { reply, intent, execution, arc_x402_verified=True, payment_network="arc", payment_asset="USDC" }
```

---

## 3. Mapa de arquivos

| Responsabilidade | Arquivo |
|---|---|
| x402 Arc/USDC gate | `backend/server/routes/arc_x402_routes.py` |
| x402 Stellar/XLM (legado) | `backend/server/routes/x402_routes.py` |
| Circle W3S client (send/verify USDC) | `backend/server/integrations/arc_client.py` |
| Circle W3S crypto (entitySecretCiphertext) | `backend/server/integrations/circle_crypto.py` |
| EVM nativo no Arc (fallback W3S) | `backend/server/integrations/arc_native.py` |
| Bridge CCTP (Sepolia → Arc) | `backend/server/integrations/cctp_client.py` |
| Rotas Arc (wallet, CCTP, healthcheck) | `backend/server/routes/arc_routes.py` |
| PQC receipt (ML-DSA-87) | `backend/services/pqc_receipt.py` |
| Anti-replay (UsedPayment) | `backend/database/models.py` — classe UsedPayment |
| Orchestration (intent + tools) | `backend/server/orchestration/service.py` |
| Loop agentioco (ClaudeAgentEngine) | `backend/claude_agent.py` |
| Creator pay tools | `backend/ai/agents/creator_pay_tools.py` |
| Payment intent log (idempotencia) | `backend/database/models.py` — classe PaymentIntent |
| Traction metrics (Prometheus) | `backend/server/metrics.py` |
| Traction dashboard routes | `backend/server/traction_routes.py` |
| Settings / env vars | `backend/server/settings.py` |
| FastAPI app + router includes | `backend/server/app.py` |

---

## 4. Gap critico: x402 em Stellar vs Arc

### O problema

`x402_routes.py` (prefixo `/v1/ai`) retorna no header `X-Payment-Required`:
```json
{ "network": "stellar", "scheme": "stellar", "asset": "XLM", "amount": "0.5" }
```

Se um juiz testar `POST /v1/ai/query`, ve Stellar/XLM. O criterio Circle Tools (20%) fica comprometido.

### O que muda no arc_x402_routes.py

| Campo | Stellar (x402_routes.py) | Arc (arc_x402_routes.py) |
|---|---|---|
| `network` | `"stellar"` | `"arc"` |
| `scheme` | `"stellar"` | `"arc"` |
| `asset` | `"XLM"` | `"USDC"` |
| `amount` | `"0.5"` | `"0.10"` |
| `pay_to` | `STELLAR_X402_WALLET` (G...) | `ARC_X402_WALLET_ADDRESS` (0x...) |
| Verificacao | `StellarAdapter.verify_payment(tx_hash)` | `ArcClient.get_transfer_result(circle_id)` |
| X-Payment header | `{"tx_hash": "..."}` | `{"circle_id": "..."}` |
| Prefixo URL | `/v1/ai` | `/v1/arc/ai` |
| Env var preco | `STELLAR_X402_PRICE_XLM` | `ARC_X402_PRICE_USDC` |
| Env var habilitar | `STELLAR_X402_ENABLED` | `ARC_X402_ENABLED` |

Os dois routers coexistem enquanto a migracao nao e completa. Ambos usam o mesmo `UsedPayment` para anti-replay (campo `network` distingue "stellar" vs "arc").

### Caveat de verificacao em live mode

`ArcClient.get_transfer_result(circle_id)` chama `GET /v1/w3s/transactions/{circle_id}` autenticado com a API key do servidor. Em live, a Circle pode restringir visibilidade de transacoes de outras wallets. Para producao, substituir por verificacao on-chain via ArcNativeClient (checar evento Transfer ERC-20 no tx_hash via RPC). Em sandbox e na demo do hackathon, `get_transfer_result` sempre retorna `confirmed=True`.

---

## 5. Stack para o juiz

### Agentic 30%

Demonstrar:
- `ClaudeAgentEngine` (`backend/claude_agent.py`) rodando loop multi-step autonomo
- Rota `POST /v1/agent/run-campaign` acionando o agente
- Sequencia observable no log: `discover_creators → evaluate_creator → check_budget → pay_creator_nanopayment`
- Idempotencia: `PaymentIntent` gravado antes de executar; restart recupera sem duplo gasto

Arquivos chave: `backend/claude_agent.py`, `backend/ai/agents/creator_pay_tools.py`, `backend/server/orchestration/service.py`

### Traction 30%

Demonstrar:
- USDC real saindo ao vivo: `ArcClient.send_usdc()` confirmado on-chain (ou sandbox com logs)
- Dashboard: `GET /v1/arc/wallet/balance` mostrando saldo diminuindo
- Prometheus em `/metrics` com counters de pagamentos
- `GET /v1/traction/*` — endpoints de traction com historico de pagamentos

Arquivos chave: `backend/server/integrations/arc_client.py`, `backend/server/traction_routes.py`, `backend/server/metrics.py`

### Circle Tools 20%

Demonstrar:
- `POST /v1/arc/ai/query` retornando `"network": "arc", "asset": "USDC"` no 402
- `ArcClient` (W3S developer-controlled wallet) como rail de pagamento
- `POST /v1/arc/cctp/bridge` — CCTP cross-chain (bonus)
- `GET /v1/arc/healthcheck` — Circle API conectada

Arquivos chave: `backend/server/routes/arc_x402_routes.py`, `backend/server/integrations/arc_client.py`, `backend/server/integrations/cctp_client.py`, `backend/server/routes/arc_routes.py`

### Innovation 20%

Demonstrar:
- Recibo PQC: apos pagamento confirmado, `pqc_receipt.sign_receipt(...)` gera `receipt_pqc` armazenado em `PaymentIntent.receipt_pqc`
- Verificacao independente via `verify_receipt(receipt_pqc)` — terceiro pode validar sem chave privada
- Algoritmo: ML-DSA-87 (FIPS 204), nivel AES-256
- ERC-8004 identidade do agente on-chain (stretch)

Arquivos chave: `backend/services/pqc_receipt.py`

---

## 6. Variaveis de ambiente para o Arc testnet Canteen

### Obrigatorias para o x402 Arc funcionar

```bash
# Wallet que recebe os micropagamentos x402
ARC_X402_WALLET_ADDRESS=0x...        # endereco EVM da wallet do servidor no Arc

# Preco por query em USDC (default: 0.10)
ARC_X402_PRICE_USDC=0.10

# Habilita/desabilita o gate x402 (default: true)
ARC_X402_ENABLED=true
```

### Circle / Arc (W3S)

```bash
CIRCLE_API_KEY=TEST_API_KEY:...      # chave da Circle API (sandbox ou live)
CIRCLE_WALLET_ID=...                 # ID da wallet developer-controlled no Circle
CIRCLE_ENTITY_SECRET=...             # 32 bytes hex — exigido por toda tx live
CIRCLE_BLOCKCHAIN=ETH-SEPOLIA        # chain na API Circle (testar ARC-SEPOLIA se disponivel)
CIRCLE_USDC_TOKEN_ID=                # deixar vazio para resolucao automatica via API

# false = chamadas reais para Circle API; true = sandbox sem rede (default: true)
ARC_SANDBOX=true
```

### Arc nativo (EVM direto — fallback W3S)

```bash
ARC_RPC_URL=https://...              # RPC do Arc Canteen testnet (obter no Discord Lepton)
ARC_AGENT_PRIVATE_KEY=0x...          # chave privada do agente para assinar txs EVM
ARC_USDC_ADDRESS=0x...               # endereco do contrato USDC no Arc Canteen
ARC_CHAIN_ID=0                       # 0 = auto-detect via eth_chainId
```

### CCTP (cross-chain bridge — habilitar em D2/D3)

```bash
CCTP_ENABLED=false                   # habilitar quando Arc Canteen suportar CCTP
CCTP_SOURCE_RPC=https://...          # RPC da chain fonte (ex: Ethereum Sepolia)
CCTP_SIGNER_PRIVATE_KEY=0x...        # chave que assina o depositForBurn na chain fonte
ARC_CCTP_MSG_TRANSMITTER=0x...       # contrato MessageTransmitter no Arc (pegar no Discord)
ARC_CCTP_USDC=0x...                  # USDC no Arc Canteen
ARC_CCTP_DOMAIN=7                    # domain ID do Arc no CCTP (confirmar no Discord)
```

### PQC — recibos pos-quanticos

```bash
PQC_ENABLED=true
PQC_SECRET_KEY=                      # base64 da chave secreta ML-DSA-87 — NUNCA commitar
PQC_PUBLIC_KEY=                      # base64 da chave publica — pode ser publica

# Gerar par permanente (uma vez):
# python3 -c "from services.pqc_receipt import generate_keypair; generate_keypair()"
```

### LLM / Agente

```bash
ANTHROPIC_API_KEY=sk-ant-...         # para ClaudeAgentEngine
LLM_PROVIDER=anthropic               # ativa o loop agentioco Claude no OrchestrationService
ANTHROPIC_MODEL=claude-sonnet-4-6
AGENT_MAX_STEPS=50                   # trava de seguranca do loop
```

---

## 7. O que resta para integrar arc_x402_routes no app.py

Adicionar 2 linhas em `backend/server/app.py`:

```python
# Linha de import (junto com os outros routers, aprox. linha 43):
from server.routes.arc_x402_routes import router as arc_x402_router

# Linha de include (junto com os outros includes, aprox. linha 132):
app.include_router(arc_x402_router)
```

Expor o header no CORS (ja esta em `settings.py` como default, mas confirmar):
```bash
CORS_ALLOWED_HEADERS=Content-Type,Authorization,Accept,X-Requested-With,X-Payment,X-Payment-Required,X-Arc-Secret
```

Definir a variavel obrigatoria antes de subir:
```bash
ARC_X402_WALLET_ADDRESS=0x<endereco_da_wallet_circle>
```

Testar com:
```bash
# Deve retornar 402 com network=arc e asset=USDC
curl -X POST http://localhost:8000/v1/arc/ai/query \
     -H "Content-Type: application/json" \
     -d '{"message": "hello"}'

# Verificar circle_id (sandbox aceita qualquer valor)
curl "http://localhost:8000/v1/arc/ai/query/verify-transfer?circle_id=test-123"

# Simular pagamento em sandbox
curl -X POST http://localhost:8000/v1/arc/ai/query \
     -H "Content-Type: application/json" \
     -H "X-Payment: {\"circle_id\": \"test-circle-id\"}" \
     -d '{"message": "quem e voce?", "user_id": "demo_user"}'
```
