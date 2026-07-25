# XiaoLee — Status Hackathon Lepton
> Branch: `feature/agent-brain-lead` | Deadline: **29 jun 2026** | Hoje: 22 jun 2026
> Scoring: **Agentic 30% · Traction 30% · Circle Tools 20% · Innovation 20%**

---

## O que foi construído

### Loop Agêntico (Agentic 30%) — COMPLETO
- **`backend/claude_agent.py`** — `ClaudeAgentEngine`: loop nativo Anthropic SDK, converte tools OpenAI→Anthropic, trava em `AGENT_MAX_STEPS`
- **`backend/ai/agents/creator_pay_tools.py`** — 4 tools em formato OpenAI:
  - `discover_creators(criteria)` — busca participantes com score ≥ 50
  - `evaluate_creator(creator_id)` — pontua engajamento real (follow + retweet)
  - `check_budget(spent, budget)` — guarda o agente dentro do orçamento
  - `pay_creator_nanopayment(intent_id, to, amount_usdc)` — dispara o rail de pagamento
- **`backend/server/routes/agent_routes.py`** — `POST /v1/agent/run-campaign` + `GET .../status` com polling
- **`backend/database/models.py`** — modelo `PaymentIntent` (log durável, anti-replay UUID v4)
- **`backend/database/repository.py`** — 7 métodos para `PaymentIntent` + participants
- **Migração Alembic** — `20260622_add_payment_intents.py`
- **E2E validado**: 12 steps, 3 pagamentos × $5 USDC, 2 skipped (score < 50), summary em markdown

### Payment Rail Circle/Arc (Circle Tools 20%) — PARCIAL
- **`backend/server/integrations/arc_client.py`** — `ArcClient` integrado à Circle Programmable Wallets API (W3S)
  - Modo sandbox (`ARC_SANDBOX=true`): retorna tx hashes simulados localmente
  - Modo live (`ARC_SANDBOX=false`): chama `POST /v1/w3s/developer/transactions/transfer`
- **`backend/server/routes/x402_routes.py`** — esqueleto HTTP 402 auditado, anti-replay `UsedPayment`

### Frontend (Painel do Agente) — COMPLETO
- **`frontend/src/hooks/useAgentStatus.ts`** — hook que posta `/run-campaign` e faz polling a cada 2.5s
- **`frontend/src/components/campaigns/AgentStatus.tsx`** — painel colapsável: badge de status, USDC gasto, lista de pagamentos, steps do agente
- **`frontend/src/components/campaigns/CampaignCard.tsx`** — renderiza `AgentStatus` apenas para `isCreator=true`
- Landing page deployada (Dockerfile isolado + Railway config)

### Testes — 91/91 PASSANDO
- 26 testes novos para `ClaudeAgentEngine` + tools + ArcClient
- Correções de 4 falhas pré-existentes:
  - `notifications_routes`: 404 para usuário desconhecido
  - `orchestration/service`: `reply_text` direto dos dados Solana (check_balance + swap_quote)
  - `helius_routes`: secret lido de `settings` no request time (não cacheado no startup)

### Infra & Configuração
- **`backend/server/settings.py`** — variáveis Arc/Agent: `CIRCLE_API_KEY`, `CIRCLE_WALLET_ID`, `ARC_SANDBOX`, `ANTHROPIC_API_KEY`, `CLAUDE_MODEL`, `AGENT_MAX_STEPS`
- **`.env.example`** — atualizado com todas as novas variáveis
- **`backend/requirements.txt`** — `anthropic>=0.111.0`, `openai>=1.0.0`
- **D5 polimento**: negation detection, `_extract_amount` melhorado, intent swap question vs action

---

## O que FALTA — por prioridade

### 🔴 BLOQUEANTE — Variáveis Circle não configuradas

O pagamento real de USDC **NÃO FUNCIONA** sem estas variáveis preenchidas corretamente:

```bash
# .env — preencher ANTES de rodar em modo live

CIRCLE_API_KEY=TEST_API_KEY:xxxx:xxxx    # ← chave do console.circle.com
CIRCLE_WALLET_ID=<uuid-da-wallet>         # ← ID da wallet criada na W3S API
ARC_SANDBOX=true                          # ← mudar para false para USDC real
```

**Por que está bloqueando:**
- `ARC_SANDBOX=true` faz todos os pagamentos serem simulados (tx hash fake tipo `sandbox_tx_xxxx`)
- O juiz do hackathon precisa ver USDC fluindo de verdade na testnet — sem isso, **Traction 30% = zero**
- A `CIRCLE_API_KEY` já foi gerada no console, mas precisa do **entity secret** configurado no console antes de criar wallets

**Passos para desbloquear (em ordem):**
1. Acessar **console.circle.com → Developer → Entity Secret → Set Secret**
2. Colar o ciphertext gerado (ver seção técnica abaixo)
3. Executar script de criação de wallet (pronto em `scripts/setup_circle_wallet.py`)
4. Atualizar `.env` com `CIRCLE_WALLET_ID=<id retornado>` e `CIRCLE_ENTITY_SECRET=<hex>`
5. Mudar `ARC_SANDBOX=false`
6. Testar: `POST /v1/agent/run-campaign` e verificar tx hash real na Sepolia testnet

**Ciphertext para o console (entity secret já gerado):**
```
CTronPCF8Gh8m5vCVbDA1vKikORm2Qmh22c7i1oRmm51xd0Cj0IwBvzNKN+w2cOmZNmfW+kPK4NUR1SfhUALTehT9vZmU9AcHZx0wD12HFlFTUJK4os0Upx2ty7r4kqHk1Xeal6nq2w0t+SxgZoDwj3v5mIbcRvkRtMVl6wCgnFCIUPdmXOR6F6/nF7H7hlosJGqFvfS4YCR+ZfRUO5G5y/bPIHF4bs8vKRrA++wsIEbT42xacZuFXIeho9DNZUCJK67nyfNVi9dZrno3ZyeEorItG5E9vtIEhY0+5QAor/RJwd5HVmJQD1VqdjxHdf8gtwG8BMRxnDgO7qVX6T1Nv0cBR0OMBwl+yR4TgNE4YO503QAFzPNDooOJQ7mW6yc3nW3WEvgqXY32Iu7aksNvEEJuteIox2aPIhs63LcRARoTSVPw1Nnj1lGS9lSpIIIr7SiYb3mbnpm9mHFO2ASn5qDefxV1BAiYWtOhcgt9Sqmuw7ioA98+FzwI6+GaUaBQUFX9bavvGazXvMSlr9n8yUQ6JgDbN2RQ7sNIM0ZhF/wwvT0UVEPYgdXMdxdf6SQ1aNrUg7866nJQBRWiod0J6OBNHZXKLXHjOOzt6Rcarnb/F0xxZBAPpwfoyjuuyrpOJ8h1vJ35Nc9c6ykVjUvWk4tjjolHLqwVNuiN4rrWIY=
```

```bash
# Adicionar no .env após configurar no console:
CIRCLE_ENTITY_SECRET=<REDACTED_ROTATE_BEFORE_USE>
```

---

### 🟡 FALTA — Traction 30% (prova visual para o júri)

- **Dashboard USDC-flow**: métricas Prometheus de pagamentos + painel no frontend mostrando USDC saindo em tempo real
  - `metrics.py` já existe com Prometheus — falta adicionar: `usdc_paid_total`, `payments_count`, `agent_steps_total`
  - Grafana já está na stack Docker — falta criar o dashboard de USDC-flow
- **Seed de creators reais**: ter wallets Sepolia reais para os 3 creators que recebem pagamento na demo

### 🟡 FALTA — Innovation 20%

- **Recibo PQC ML-DSA**: assinar o `PaymentIntent` com criptografia pós-quântica após confirmação do pagamento
  - Escopo: 1 arquivo `backend/services/pqc_receipt.py` + campo `receipt_pqc` no `PaymentIntent`
  - Biblioteca: `pqcrypto` ou `dilithium-py`
- **ERC-8004 agent identity**: identidade do agente on-chain — stretch, só se tudo acima estiver verde

### 🟡 FALTA — D6/D7

- **Vídeo demo ≤ 3min**: roteiro = campanha → participantes → Run Agent → 3 pagamentos USDC → tabela de summary
- **README público**: arquitetura em camadas (L0–L4), critérios do hackathon mapeados, badge de testes

---

## Resumo por critério

| Critério | Peso | Status |
|---|---|---|
| **Agentic** | 30% | ✅ Loop completo, 4 tools, E2E validado |
| **Traction** | 30% | 🔴 Bloqueado — precisa Circle vars + USDC real |
| **Circle Tools** | 20% | 🟡 Parcial — sandbox ok, live bloqueado pelas vars |
| **Innovation** | 20% | ❌ PQC não implementado ainda |

**Score atual estimado: ~30/100** (só o Agentic garantido)
**Score com Circle desbloqueado + PQC: ~80/100**

---

## Comandos para retomar

```bash
# Rodar testes (91/91 devem passar)
cd backend && ../.venv/bin/pytest tests/ -q

# Subir stack completa
make run-docker

# Após configurar Circle — criar wallet e testar pagamento real
python3 scripts/setup_circle_wallet.py

# Iniciar dev local
make dev
```
