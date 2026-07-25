# XiaoLee Protocol

> **O agente que paga creators "pela fração" — nanopagamentos USDC em tempo real, conforme o trabalho acontece, sem ninguém apertar botão.**

**Lepton Agents Hackathon · Arc / Circle** — Creator Monetization (RFB-06) + Agent-to-Agent (RFB-03) + Selling Agent Services (RFB-02)

[Live demo](#) · [Vídeo (3min)](#) · [Arquitetura Arc](docs/workflows/ARC_LEPTON_ARCHITECTURE.md) · [Posicionamento](docs/POSICIONAMENTO_ARC_LEPTON.md)

---

## How XiaoLee scores on Lepton Hackathon criteria

| Criterion | Weight | How XiaoLee addresses it | Evidence |
|---|---|---|---|
| **Agentic** | 30% | `ClaudeAgentEngine`: autonomous discover → evaluate → pay loop. No human in the loop — the agent decides which creators to pay and how much, within budget constraints. | [`backend/claude_agent.py`](backend/claude_agent.py), `POST /v1/agent/run-campaign` |
| **Traction** | 30% | Creators onboarded, USDC settled on Arc testnet during the event window, live stats/feed for the judges to watch USDC move in real time. | `GET /v1/traction/stats`, `GET /v1/traction/feed` (SSE) — [`backend/server/traction_routes.py`](backend/server/traction_routes.py) |
| **Circle Tools** | 20% | Circle W3S developer wallets for USDC payouts, x402 HTTP 402 nanopayments on Arc, CCTP bridge to move USDC from Sepolia to Arc, App Kit for the frontend wallet. | [`backend/server/integrations/arc_client.py`](backend/server/integrations/arc_client.py), [`backend/server/routes/arc_x402_routes.py`](backend/server/routes/arc_x402_routes.py), [`backend/server/integrations/cctp_client.py`](backend/server/integrations/cctp_client.py) |
| **Innovation** | 20% | ML-DSA-87 (NIST FIPS 204) post-quantum signatures on every payment receipt, plus CCTP cross-chain funding and agent-to-agent identity (ERC-8004, stretch). | [`backend/services/pqc_receipt.py`](backend/services/pqc_receipt.py), [`backend/server/routes/trust_routes.py`](backend/server/routes/trust_routes.py) |

> **Live on Arc testnet:** <!-- TODO(P1-01/P1-02): preencher com números reais antes da submissão --> `X` creators paid · `$Y.YY` USDC settled · avg latency `Zms`
> [Live demo](<URL>) <!-- TODO(P1-04): link do deploy --> · [Video demo](<LOOM_URL>) <!-- TODO(P3-01): link do Loom --> · [Submit form](https://forms.gle/SMqLaw2pMGDe58LFA)

## Quick Start for Judges

```bash
# Test x402 on Arc — no payment yet, must return HTTP 402
curl -X POST https://<URL>/v1/arc/ai/query \
  -H "Content-Type: application/json" \
  -d '{"message":"hello"}'
```

Expected response (`402 Payment Required`) — network/asset are nested inside `payment`:

```json
{
  "error": "Payment Required",
  "message": "Esta query AI requer um micropagamento de 0.10 USDC no Arc...",
  "payment": {
    "version": "x402/1",
    "network": "arc",
    "scheme": "arc",
    "asset": "USDC",
    "amount": "0.10",
    "pay_to": "0x...",
    "blockchain": "ETH-SEPOLIA",
    "expires": 1735689600
  }
}
```

```bash
# Live traction — USDC settled, creators active, latency
curl https://<URL>/v1/traction/stats
```

```bash
# CCTP cross-chain funding — bridge USDC de ETH-Sepolia para o Arc (Innovation 20%)
# Em sandbox (ARC_SANDBOX=true) simula o fluxo E2E de 4 etapas sem tx real:
#   Step 1/4: burning USDC on ETH-SEPOLIA
#   Step 2/4: waiting for Circle attestation
#   Step 3/4: minting USDC on ARC-TESTNET
#   Step 4/4: confirmed
curl -X POST https://<URL>/v1/arc/cctp/bridge \
  -H "Content-Type: application/json" \
  -d '{"amount_usdc": 10.0, "recipient": "0x<endereço_arc>"}'
```

`<URL>` = deploy público (Railway/staging) — preencher assim que o P1-04 estiver concluído.

---

## O problema

Pagar creator hoje é em lote, atrasado, com mínimo de saque e fricção de chain. O micro-trabalho — um post, uma fração de engajamento — **simplesmente não é pagável**: o custo da transação supera o valor pago.

## A solução

XiaoLee é um **agente autônomo de payout**: a marca define um budget em USDC e critérios; o agente **descobre** o trabalho do creator, **avalia**, **decide** quanto pagar e **liquida o nanopagamento USDC na rede Arc** em tempo real — via x402, com gas nativo em USDC e liquidação sub-500ms. Isso era economicamente inviável antes do Arc.

```
marca financia budget USDC → agente detecta trabalho → decide pagar a fração no budget
        → x402 dispara nanopagamento USDC no Arc → creator recebe → dashboard mostra o valor
```

## Como mapeia nos critérios da banca

| Critério | Peso | Onde está |
|---|---|---|
| **Agentic** | 30% | Loop autônomo `discover → evaluate → pay` (`ClaudeAgentEngine`, L2) decidindo dentro de budget |
| **Traction** | 30% | USDC real fluindo na janela — dashboard de pagamentos em tempo real (`metrics.py` + Grafana, L4) |
| **Circle Tools** | 20% | Circle App Kit + x402 + USDC nativo no Arc; CCTP para funding cross-chain (L0/L1) |
| **Innovation** | 20% | Recibo de pagamento assinado com cripto pós-quântica (ML-DSA) + identidade de agente ERC-8004 (L3) |

## Arquitetura em camadas

```
L4 · Traction & Observability  — métricas + Grafana (dashboard de USDC-flow)
L3 · Trust & Proof             — recibo PQC (ML-DSA) + identidade de agente ERC-8004
L2 · Agent Orchestration       — ClaudeAgentEngine: loop discover → evaluate → pay
L1 · Payment Rail              — x402 (HTTP 402) + USDC nativo Arc + anti-replay (PaymentIntent)
L0 · Identity & Wallet         — Circle App Kit (EVM) · CCTP funding cross-chain
```

Verdade detalhada da arquitetura Arc: [`docs/workflows/ARC_LEPTON_ARCHITECTURE.md`](docs/workflows/ARC_LEPTON_ARCHITECTURE.md).

## Quickstart (avaliadores)

```bash
make init          # venv Python + npm + .env
make dev           # backend :8000 + frontend :3000
```

```bash
# Rodar uma campanha de payout autônoma (loop agêntico)
curl -X POST http://localhost:8000/v1/agent/run-campaign \
  -H 'Content-Type: application/json' \
  -d '{"campaign_id": "demo", "budget_usdc": 50, "criteria": "engajamento real"}'

# Acompanhar a execução
curl http://localhost:8000/v1/agent/run-campaign/demo/status
```

Variáveis do sprint Arc (`.env`): `CIRCLE_API_KEY`, `CIRCLE_WALLET_ID`, `ARC_SANDBOX=true`, `ANTHROPIC_API_KEY`, `AGENT_MAX_STEPS=50`.

---

## Base de plataforma (lineage Solana / Stellar)

XiaoLee não nasceu no hackathon. A tese Arc reaproveita uma plataforma madura — agente conversacional, campanhas de creator, rail de pagamento `x402` auditado, observabilidade e i18n EN/PT já em produção. As seções abaixo documentam essa base (originada nas tracks **Solana/Anchor** e **Stellar/Soroban**); elas demonstram o "real progress" sobre o qual a entrega Arc foi construída. Onde houver divergência de chain, o enquadramento **Arc** acima prevalece para o escopo do hackathon.

---

## Interface Atual

| Chat | Dashboard | Campanhas | Notificações |
|---|---|---|---|
| ![Tela do chat XiaoLee](chat.png) | ![Dashboard XiaoLee](dashboard.png) | ![Tela de campanhas XiaoLee](campaings.png) | ![Notificações XiaoLee](notifications.png) |

> Screenshots do design premium com paleta neutra quente + acento único de marca (#d81b78). Toggle EN/PT disponível na Navbar.

---

## Status do Projeto

Progresso: [##########] 99% — Código, UI e deploy completos. Sprint 11 encerrada.

| Bloco | Status | Detalhe |
|---|---|---|
| Core API FastAPI | [##########] 100% | `/health`, `/health/detailed`, `/status`, `/metrics`, `/chat`, `/v1/messages/inbound` |
| Integração Gemini | [##########] 100% | Intent detection + resposta contextual, idioma espelhado (PT/EN automático) |
| Webhook Telegram | [##########] 100% | Secret token validado, bot operacional |
| Webhook X/Twitter (inbound) | [##########] 100% | HMAC SHA-256 validado, endpoint pronto para receber eventos |
| X/Twitter DM (outbound) | [####......] 40% | Código do poller pronto — **requer Twitter Developer App** (ver nota abaixo) |
| Transfer Universal | [##########] 100% | `ModernTransferService` — envia para @handle (Telegram/Twitter) ou endereço de carteira Solana |
| Pre-LLM Transfer Intent | [##########] 100% | Regex detecta "envia X SOL para @user" antes do Gemini — bypassa safety refusal |
| Solana/Jupiter (prepare) | [##########] 100% | Quote + tx unsigned para wallet assinar |
| Wallet-first frontend | [##########] 100% | Connect, prepare, simulate, confirmação explícita, sign/send |
| Campanhas Devnet | [##########] 100% | Join (409 idempotente), verify, claim com proof — custodial (Google/Telegram) sem assinatura Ed25519 |
| Redis Rate Limiting | [##########] 100% | Sliding window + fallback in-memory automático |
| PostgreSQL + Alembic | [##########] 100% | Railway provisiona e migra automaticamente no deploy |
| Docker Compose completo | [##########] 100% | PostgreSQL + Redis + Grafana + migrate one-shot |
| Grafana Dashboard | [##########] 100% | 8 painéis, provisionamento automático |
| Anchor on-chain | [######....] 60% | PDA real (solders), record_swap (dry_run até keypair em produção) |
| Emergency Pause | [##########] 100% | `pause_protocol` / `unpause_protocol` no contrato Rust |
| UI/UX Premium | [##########] 100% | Crossfade de vídeo sem flash, typing indicator (PT/EN), mensagem imediata no envio, auto-scroll inteligente |
| i18n EN/PT | [##########] 100% | `LanguageContext`, toggle na Navbar, todos os componentes traduzidos; Xiaolee responde no idioma do usuário |
| Auth (Web3Auth + Phantom) | [##########] 100% | Google OAuth via Web3Auth, carteira custodial, Phantom devnet, sessão persistida — fallback por `twitter_user_id` |
| Chat History | [##########] 100% | Historico modal com filtros All/You/Xiaolee; persistência dual (in-memory + localStorage); sobrevive fetchData() |
| QA backend | [########..] 80% | **~128 testes coletados** (1 erro de coleta em `scripts/db/test_mcp_migration.py` a corrigir); auditoria interna em `AUDIT.md` |
| Deploy público (Railway) | [##########] 100% | Frontend + backend em produção no Railway; ARG/ENV corretos no Dockerfile |
| Auditoria externa | [..........] 0% -- BLOQUEADOR MAINNET | Não iniciada — P0 para mainnet (não bloqueia demo) |

### Nota: X/Twitter DM

O canal X/Twitter tem **duas camadas** com status distintos:

- **Webhook inbound (100%)** — o endpoint `/v1/integrations/x/webhook` valida HMAC e processa eventos da API oficial. Pronto para receber mensagens assim que configurado no Twitter Developer Portal.
- **DM Poller outbound (bloqueado para hackathon)** — envio ativo de DMs pela XiaoLee exige acesso à [Twitter API v2 DM](https://developer.twitter.com/en/docs/twitter-api/direct-messages/introduction), disponível a partir do plano **Basic ($100/mês)**. A biblioteca `agent-twitter-client` (scraper não-oficial) não é mais viável porque o Twitter removeu o endpoint `guest/activate.json` em 2025.

**Decisão de produto:** o outbound DM via X faz sentido econômico apenas no lançamento em mainnet, quando o volume de usuários justifica o custo do Developer App. Para o hackathon e devnet, o **Telegram está 100% operacional** como canal de mensagens. O X é o canal alvo para mainnet.

---

## Arquitetura do Sistema

### Visão Geral dos Componentes

```mermaid
graph TB
    subgraph CANAIS["Canais de Entrada"]
        FE["Next.js Frontend<br>(Phantom Wallet)"]
        TG["Telegram Bot"]
        XX["X / Twitter DM"]
    end

    subgraph INFRA_ENTRADA["Camada de Entrada"]
        RL["Rate Limiter<br>(Redis Sliding Window)<br>+ fallback in-memory"]
        CORS["CORS Guard<br>(headers restritos por env)"]
    end

    subgraph BACKEND["Backend FastAPI"]
        APP["app.py<br>(lifespan + middleware)"]
        ORCH["OrchestrationService<br>(intent + resposta)"]
        GEM["GeminiClient<br>(intent detection)"]
        SOL["SolanaClient<br>(Jupiter swap prepare)"]
        CAMP["Campaigns Router<br>(join / verify / claim)"]
        NOTIF["Notifications Router<br>(in-app inbox)"]
        HEL["Helius Webhook<br>(confirma swap on-chain)"]
        ANCHOR["AnchorClient<br>(solders: PDA + Borsh + sign)"]
        MET["Metrics<br>(/metrics Prometheus)"]
        HLT["Health<br>(/health/detailed)"]
    end

    subgraph BANCO["Persistência"]
        DB[("PostgreSQL 16<br>(asyncpg + Alembic)")]
        SQLITE[("SQLite<br>(desenvolvimento local)")]
        REDIS[("Redis 7<br>(rate limiting)")]
    end

    subgraph OBS["Observabilidade"]
        PROM["Prometheus<br>:9090"]
        GRAF["Grafana<br>:3001<br>(8 painéis)"]
    end

    subgraph SOLANA["Solana / On-chain"]
        JUP["Jupiter v6<br>(quote + swap tx)"]
        RPC["Solana RPC<br>(Helius)"]
        PROG["XiaoLee Core Program<br>(Anchor / Rust)<br>PDA: global_config + user_state<br>Emergency pause on-chain"]
    end

    TG -->|HMAC secret| APP
    XX -->|HMAC SHA-256| APP
    FE -->|REST JSON| APP

    APP --> RL
    APP --> CORS
    APP --> ORCH
    APP --> CAMP
    APP --> NOTIF
    APP --> HEL
    APP --> MET
    APP --> HLT

    RL <--> REDIS

    ORCH --> GEM
    ORCH --> SOL
    ORCH --> DB

    CAMP --> DB
    NOTIF --> DB
    HEL --> DB
    HEL --> ANCHOR

    SOL --> JUP
    FE -->|sign + send| RPC
    ANCHOR -->|"record_swap<br>(admin keypair)"| PROG
    RPC -->|webhook evento| HEL

    APP -.->|prod| DB
    APP -.->|dev| SQLITE

    MET --> PROM
    PROM --> GRAF
```

---

### Fluxo de Swap Wallet-first

```mermaid
sequenceDiagram
    actor U as Usuário
    participant FE as Frontend Next.js
    participant API as Backend FastAPI
    participant JUP as Jupiter v6
    participant RPC as Solana RPC
    participant HEL as Helius Webhook
    participant ANCH as AnchorClient
    participant PROG as XiaoLee Program

    U->>FE: 1. Conecta carteira Phantom
    U->>FE: 2. Informa token + valor

    FE->>API: POST /v1/solana/swap/prepare
    API->>JUP: GET /quote (token_in, token_out, amount)
    JUP-->>API: Quote + route
    API->>JUP: POST /swap (unsigned tx)
    JUP-->>API: Transação serializada (unsigned)
    API-->>FE: { quote, swap_transaction_base64 }

    FE->>RPC: simulateTransaction()
    RPC-->>FE: Resultado da simulação + logs

    FE->>U: Exibe resumo de execução (rota, estimativa, price impact)
    U->>FE: 3. Marca checkbox de confirmação explícita

    FE->>RPC: sendRawTransaction() com assinatura Phantom
    RPC-->>FE: { signature }
    FE->>U: Swap confirmado — tx na Devnet

    Note over RPC,HEL: Helius monitora a transação on-chain
    RPC-->>HEL: Evento de confirmação (webhook)
    HEL->>API: POST /v1/solana/webhooks/helius
    API->>ANCH: record_swap(twitter_id, volume)
    ANCH->>PROG: Instrução Anchor (PDA + Borsh + admin sign)
    PROG-->>ANCH: Swap gravado on-chain
    API->>API: Persiste notificação in-app
```

---

### Fluxo de Campanha

```mermaid
sequenceDiagram
    actor U as Usuário
    participant FE as Frontend
    participant API as Backend
    participant DB as PostgreSQL
    participant W as Phantom Wallet
    participant PROG as XiaoLee Program

    U->>FE: Visualiza campanha ativa
    FE->>API: POST /campaigns/join
    API->>DB: INSERT participant (UniqueConstraint)
    alt já inscrito
        DB-->>API: Constraint violation
        API-->>FE: 409 Conflict { already_joined: true }
    else nova inscrição
        DB-->>API: OK
        API-->>FE: 201 Created
    end

    U->>FE: Realiza tarefas (swap, follow, retweet)
    FE->>API: POST /campaigns/verify
    API->>DB: UPDATE status = tasks_verified
    API-->>FE: { status: "tasks_verified" }

    U->>W: Assina proof da campanha
    W-->>FE: { proof_signature }
    FE->>API: POST /campaigns/claim { proof_signature }
    API->>API: Valida assinatura ED25519
    API->>DB: INSERT claim_receipt
    API-->>FE: 200 OK { receipt_id, status: "paid" }
    FE->>U: Notificação in-app — recompensa recebida
```

---

### Fluxo de i18n (EN/PT)

```mermaid
graph LR
    LS["localStorage<br>xiaolee_lang"] -->|hidratação| LP["LanguageProvider<br>(React Context)"]
    LP -->|"t(key)"| C1["Navbar"]
    LP -->|"t(key)"| C2["Campaigns"]
    LP -->|"t(key)"| C3["Wallet Modal"]
    LP -->|"t(key)"| C4["Transações Modal"]
    LP -->|"t(key)"| C5["Dashboard"]
    LP -->|"t(key)"| C6["Notifications"]

    subgraph LOCALES["src/locales/"]
        EN["en.json"]
        PT["pt.json"]
    end

    LP -->|"lang === en"| EN
    LP -->|"lang === pt"| PT

    TOGGLE["LangToggle<br>EN / PT pill"] -->|"setLang()"| LP
```

---

## Quickstart

```bash
# 1. Setup completo (venv + npm + .env)
make init

# 2. Subir em modo dev
make dev

# 3. Verificar ambiente
make smoke
```

**OU com Docker (stack completa):**

```bash
cp .env.example .env  # preencha as variáveis
make run-docker
```

| Serviço | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8000 |
| Docs Swagger | http://localhost:8000/docs |
| Grafana | http://localhost:3001 |
| Prometheus | http://localhost:9090 |

---

## Deploy (Render + Railway)

O stack de produção usa **Railway** para o backend FastAPI e **Render** para o frontend Next.js.

### Variáveis de ambiente — Frontend (Railway)

| Variável | Valor |
|---|---|
| `NEXT_PUBLIC_CORE_API_URL` | URL pública do backend no Railway |
| `NEXT_PUBLIC_WEB3AUTH_CLIENT_ID` | Client ID do Web3Auth (dashboard.web3auth.io) |
| `NEXT_PUBLIC_TELEGRAM_BOT_NAME` | Nome do bot Telegram (sem @) |

> No painel do Web3Auth, adicionar a URL do frontend em **Whitelisted URLs** antes do deploy.

### Variáveis de ambiente — Backend (Railway)

| Variável | Descrição |
|---|---|
| `GEMINI_API_KEY` | Chave Google Gemini |
| `DATABASE_URL` | PostgreSQL (Railway provisiona automaticamente) |
| `REDIS_URL` | Redis (Railway provisiona automaticamente) |
| `TELEGRAM_WEBHOOK_SECRET` | Secret webhook Telegram |
| `X_WEBHOOK_SECRET` | HMAC webhook X/Twitter |
| `HELIUS_WEBHOOK_SECRET` | HMAC webhook Helius |
| `SOLANA_ADMIN_KEYPAIR_B58` | Admin keypair para record_swap (opcional — dry_run se ausente) |

### CORS

Após o deploy do frontend no Render, adicionar a URL ao `CORS_ALLOWED_ORIGINS` no Railway para liberar as chamadas do browser.

---

## Variáveis de Ambiente (local)

```bash
cp .env.example .env
```

| Variável | Descrição |
|---|---|
| `GEMINI_API_KEY` | Chave Google Gemini (classifica intenção) |
| `TELEGRAM_WEBHOOK_SECRET` | Secret para webhook Telegram |
| `X_WEBHOOK_SECRET` | HMAC para webhook X/Twitter |
| `HELIUS_WEBHOOK_SECRET` | HMAC para webhook Helius |
| `DATABASE_URL` | PostgreSQL em produção (vazio = SQLite) |
| `REDIS_URL` | Redis para rate limiting (vazio = in-memory) |
| `SOLANA_ADMIN_KEYPAIR_B58` | Admin keypair para `record_swap` (vazio = dry_run) |

---

## Testes

```bash
# Suíte backend completa (65 testes)
make test-backend

# Build frontend limpo
cd frontend && npm run build

# Testes de carga (20 users, 2 min)
make load-test-smoke

# Checklist de mainnet
make audit-checklist
```

---

## Banco de Dados

```bash
# Aplicar migrações (SQLite local ou PostgreSQL via DATABASE_URL)
make db-migrate

# Status das migrações
make db-status

# Nova migração após alterar models.py
make db-new-migration MSG="descricao"
```

---

## Smart Contract

| Item | Valor |
|---|---|
| Program ID | `Fmmpn79Tij8fzYHg31ekZz4MmK9ArGzN59VogfcwhXiM` |
| Cluster | Devnet |
| Instruções | `initialize_global`, `initialize_user`, `record_swap`, `pause_protocol`, `unpause_protocol`, `transfer_admin` |

```bash
make anchor-build
make anchor-deploy-devnet
make anchor-idl-sync
```

---

## Endpoints Principais

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/health` | Health check básico |
| `GET` | `/health/detailed` | Health com latência por dependência |
| `GET` | `/status` | Status resumido |
| `GET` | `/metrics` | Métricas Prometheus |
| `POST` | `/chat` | Chat com agente XiaoLee |
| `POST` | `/v1/messages/inbound` | Mensagem inbound (rate limited) |
| `POST` | `/v1/integrations/telegram/webhook` | Webhook Telegram |
| `POST` | `/v1/integrations/x/webhook` | Webhook X/Twitter (HMAC) |
| `POST` | `/v1/solana/swap/prepare` | Prepara swap (quote + tx unsigned) |
| `POST` | `/v1/solana/webhooks/helius` | Webhook Helius (confirma swap) |
| `GET` | `/campaigns` | Lista campanhas |
| `POST` | `/campaigns/join` | Entra em campanha (409 se já inscrito) |
| `POST` | `/campaigns/verify` | Verifica tarefas |
| `POST` | `/campaigns/claim` | Claim com proof assinado |
| `GET` | `/v1/notifications/me` | Notificações in-app |

> Documentação completa: [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md)

---

## Segurança Implementada

- HMAC SHA-256 para webhooks X e Helius
- Secret token para webhook Telegram
- Rate limiting Redis (sliding window) com fallback in-memory
- CORS headers restritos via `CORS_ALLOWED_ORIGINS` env
- Fluxo não-custodial (chave do usuário nunca toca o backend)
- 409 Conflict idempotente (UniqueConstraint no banco)
- Emergency pause on-chain (`pause_protocol`)
- Container não-root no Dockerfile
- Suporte a secrets via vault (produção)

---

## Linha do Tempo

| Fase | Status | Entregas |
|---|---|---|
| Fase 1 | CONCLUÍDA | FastAPI, Gemini, inbound |
| Fase 2 | CONCLUÍDA | Wallet-first (prepare/simulate/sign/send) |
| Fase 3 | CONCLUÍDA | Webhooks hardening (Telegram/X/Helius) |
| Fase 4 | CONCLUÍDA | QA, observabilidade, CI fullstack |
| Fase 5 | CONCLUÍDA | Idempotência, Anchor client, CORS, 65 testes |
| Fase 6 | CONCLUÍDA | PostgreSQL, Redis, solders, Locust |
| Fase 7 | CONCLUÍDA | Docker completo, Grafana, Emergency pause |
| Fase 8 | CONCLUÍDA | Homologação E2E, testes de carga, UI Premium Refactor |
| Fase 9 | CONCLUÍDA | i18n EN/PT — LanguageContext, toggle navbar, todos os componentes traduzidos, correções de contraste e tamanho de texto |
| Fase 10 | CONCLUÍDA | UX sprint — CampaignCard reativo, Dashboard fix, ActivityFeed unificado, Historico redesenhado, Navbar responsiva xs, Wallet scroll fix, chat history localStorage, Web3Auth auth flow |
| Fase 11 | CONCLUÍDA | Transfer universal (@handle + carteira), pre-LLM intent detection, idioma automático PT/EN, claim reward custodial, crossfade vídeo, typing indicator, auto-scroll inteligente, auth fallback por twitter_user_id |
| Fase 12 | PLANEJADA MAINNET | Twitter Developer App ($100/mês) → DM outbound, auditoria externa, multisig, mainnet beta |

---

## Documentação

| Arquivo | Conteúdo |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Arquitetura completa, diagramas, fluxos |
| [`docs/DESIGN_SYSTEM.md`](docs/DESIGN_SYSTEM.md) | Paleta, ícones, i18n, padrão de cards e layout |
| [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) | Rotas, payloads, códigos de erro |
| [`docs/SMART_CONTRACT.md`](docs/SMART_CONTRACT.md) | Instruções on-chain, PDAs, eventos |
| [`docs/MAINNET_READINESS.md`](docs/MAINNET_READINESS.md) | Gates + checklist para mainnet |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Setup, padrões, como contribuir |
| [`load_tests/README.md`](load_tests/README.md) | Instruções de teste de carga (Locust) |
| [`backend/memory-bank/progress.md`](backend/memory-bank/progress.md) | Trilha de construção detalhada |
