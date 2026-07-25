# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Commands

```bash
# Setup (first time)
make init                  # instala venv Python + npm + copia .env.example

# Desenvolvimento local
make dev                   # uvicorn (backend :8000) + next dev (frontend :3000) em paralelo

# Testes
make test-backend          # pytest completo (65+ testes)
make smoke                 # smoke rápido: test_metrics.py + swap.test.ts
make ci-local              # pipeline CI completa: lint + test + build

# Banco de dados (Alembic)
make db-migrate            # aplica migrações
make db-new-migration MSG="descricao"  # gera nova migração autogenerate
make db-status             # histórico + revisão atual

# Docker (stack completa: PostgreSQL + Redis + Grafana)
make run-docker            # sobe tudo; prometheus :9090, grafana :3001
make stop-docker

# Solana / Anchor
make anchor-build
make anchor-deploy-devnet
make anchor-idl-sync       # copia IDL para frontend/src/idl/

# Testes de carga
make load-test-smoke       # 20 users, 2 min, localhost:8000
```

### Comandos diretos (sem make)

```bash
# Backend — rodar um único teste
cd backend && ../.venv/bin/pytest tests/test_campaigns.py -v

# Frontend — lint e build
cd frontend && npm run lint
cd frontend && npm run build

# Frontend — testes unitários (vitest)
cd frontend && npm test

# Alembic direto
cd backend && ../.venv/bin/alembic upgrade head
```

---

## Arquitetura

### Contexto do Sprint Atual — Hackathon Lepton (Arc/Circle, deadline 29 jun 2026)

O projeto pivotou de **Stellar → Arc (EVM, USDC nativo)**. A verdade da arquitetura atual está em `docs/workflows/ARC_LEPTON_ARCHITECTURE.md`. Os arquivos `docs/ARCHITECTURE.md`, `backend/memory-bank/systemPatterns.md` e `backend/memory-bank/techContext.md` são da era Stellar — úteis para entender **padrões de código**, não a chain ativa.

Critérios de nota do hackathon: **Agentic 30% · Traction 30% · Circle Tools 20% · Innovation 20%**

### Camadas da Arquitetura

```
L4 · Traction & Observability  — metrics.py + Grafana (dashboard USDC-flow)
L3 · Trust & Proof             — PQC receipt ML-DSA, ERC-8004 agent identity [stretch]
L2 · Agent Orchestration       — ClaudeAgentEngine → loop discover→evaluate→pay
L1 · Payment Rail              — x402 HTTP 402 + USDC Arc + anti-replay UsedPayment
L0 · Identity & Wallet         — Circle App Kit (EVM), Freighter/Web3Auth (legado Stellar)
```

### Backend (`backend/`)

**Entrypoint:** `backend/server/app.py` — FastAPI com `lifespan` que inicia DB, rate limiter Redis e pollers (Telegram/X).

**Módulos principais:**

| Caminho | Responsabilidade |
|---|---|
| `server/orchestration/service.py` | `OrchestrationService` — detecta intent + despacha para tool correta. **Padrão crítico:** wallet/budget NUNCA são parâmetros do modelo — injetados pelo executor. |
| `ai/llm_client.py` | `generate_response_with_tools` + `continue_conversation_with_tool_results` — loop multi-step base. |
| `ai/agents/cmo_architect.py` | Exemplo de agente especializado: `detect()` + `build_system_prompt()` + `build_user_prompt()`. Usar como molde para novos agentes. |
| `ai/mcp_tools.py` | Ferramentas MCP expostas (`play_animation`, etc.) em formato OpenAI. |
| `server/integrations/` | Clientes externos: `gemini_client.py`, `solana_client.py`, `stellar_adapter.py`, `arc_client.py` (a criar), `telegram_client.py`, `x_client.py`, `anchor_client.py`, `helius_client.py`. |
| `server/routes/x402_routes.py` | Protocolo HTTP 402 — esqueleto auditado, reaproveitado para payments Arc. |
| `database/models.py` | SQLAlchemy 2.0 (Mapped[] + mapped_column). Modelos: `User`, `Campaign`, `CampaignParticipant`, `SwapHistory`, `ProcessedDM`. `PaymentIntent` ainda não existe — criar via migração. |
| `database/repository.py` | `DatabaseRepository` — camada de acesso a dados. |
| `server/rate_limiter.py` | Sliding window Redis com fallback in-memory automático. |
| `server/metrics.py` | Prometheus (`/metrics`). |
| `services/modern_transfer_service.py` | Transfer universal: `@handle` Telegram/Twitter → `ModernTransferService`. |

**O loop agêntico (L2 — gap crítico a construir):**

- `backend/claude_agent.py` (`ClaudeAgentEngine`) — **não existe ainda**. É o P0 do sprint.
- `backend/ai/agents/creator_pay_tools.py` — **não existe ainda**. As 4 tools: `discover_creators`, `evaluate_creator`, `check_budget`, `pay_creator_nanopayment`.
- Tools devem estar em **formato OpenAI**; o `ClaudeAgentEngine` converte para Anthropic.
- `pay_creator_nanopayment(intent_id, to, amount_usdc)` — contrato de interface **congelado**. Não alterar assinatura sem avisar o time.

### Frontend (`frontend/`)

Next.js 15 + React 19 + TypeScript + Tailwind 4 + Vitest.

**Estrutura relevante:**

| Caminho | Responsabilidade |
|---|---|
| `src/app/` | App Router — rotas: `/`, `/campaigns`, `/dashboard`, `/notifications`, `/landing` |
| `src/contexts/LanguageContext.tsx` | i18n EN/PT via React Context + `localStorage`. `t(key)` para strings. |
| `src/locales/en.json` + `pt.json` | Strings de i18n. |
| `src/idl/xiaolee_core.json` | IDL do programa Anchor (gerado por `make anchor-idl-sync`). |
| `src/components/navbar/` | Navbar responsiva + `Wallet.tsx` (Phantom/Web3Auth). |
| `src/api/` | Wrappers Axios para o backend. |

Testes frontend usam **Vitest** (não Jest). Rodar com `npm test`.

### Solana / Anchor (`solana-program/xiaolee_core/`)

- Program ID: `Fmmpn79Tij8fzYHg31ekZz4MmK9ArGzN59VogfcwhXiM` (Devnet)
- Instruções: `initialize_global`, `initialize_user`, `record_swap`, `pause_protocol`, `unpause_protocol`, `transfer_admin`
- `SOLANA_ADMIN_KEYPAIR_B58` ausente → `record_swap` roda em `dry_run`

### Banco de Dados

SQLite em dev (sem `DATABASE_URL`), PostgreSQL em produção. Migrações via Alembic em `backend/alembic/`.

Pytest usa `asyncio_mode = auto` (`backend/pytest.ini`). Para testes DB, o marker é `@pytest.mark.db`.

---

## Variáveis de Ambiente Novas (Sprint Arc)

```bash
CIRCLE_API_KEY=           # Arc/Circle API Key
CIRCLE_WALLET_ID=         # ID da wallet de pagamento USDC
ARC_SANDBOX=true          # false em produção
ANTHROPIC_API_KEY=        # para o ClaudeAgentEngine
AGENT_MAX_STEPS=50        # trava de segurança do loop agêntico
```

---

## Padrões Críticos

- **Wallet nunca é parâmetro do modelo.** Sempre injetada pelo executor via contexto.
- **Intent log durável antes de executar.** Gravar `PaymentIntent` com `status=pending` antes de chamar o rail — garante idempotência em restart.
- **Anti-replay via `UsedPayment` / `payment_intents`.** Todo pagamento tem `intent_id` único (UUID v4).
- **Degradação graciosa.** Se chain cai, enfileirar e responder `"status": "queued"` — não travar o loop.

## Rotas do Agente (a criar)

```
POST /v1/agent/run-campaign          → { campaign_id, budget_usdc, criteria }
GET  /v1/agent/run-campaign/{id}/status
```
