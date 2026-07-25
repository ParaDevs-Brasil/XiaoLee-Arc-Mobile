# Arquitetura XiaoLee — Estado Atual

> Atualizado em: **2026-05-10** | Sprint 11 — Transfer universal, UX de chat e AI bilíngue.

> **Escopo (reconciliado 2026-05-30):** os diagramas e fluxos abaixo descrevem a **track Solana
> (Anchor/Jupiter/Helius)**. A XiaoLee evoluiu para **multi-chain (Solana + Stellar)**. A
> arquitetura Stellar (StellarAdapter, SEP-10, Stellar DEX path payments, Soroban, EtherFuse,
> x402) está documentada em [`RT_XIAOLEE_STELLAR.md`](RT_XIAOLEE_STELLAR.md) seções 6–11.
> A camada Stellar off-chain já existe e foi auditada (`../AUDIT.md`); o contrato Soroban
> on-chain ainda não foi escrito. Estado consolidado: [`MAINNET_READINESS.md`](MAINNET_READINESS.md).
>
> A afirmação anterior de "99% — só falta auditoria/mainnet" valia para a track Solana isolada
> e **não reflete** o estado multi-chain (a track Stellar on-chain está em ~0%).

---

## 1. Visão Geral

XiaoLee é um protocolo DeFi conversacional que combina:

- **Backend FastAPI** — orquestração de mensagens, rate limiting (Redis), campanhas e integrações.
- **Gemini AI** — classificação de intenção e resposta contextual.
- **Solana Devnet + Jupiter** — fluxo de swap wallet-first (não-custodial).
- **Anchor (XiaoLee Core)** — registro on-chain de swaps, PDAs de usuário, emergency pause.
- **Frontend Next.js** — conexão Phantom, prepare/simulate/sign/send, campanhas, dashboard.

**Princípio central:** wallet-first e não-custodial. O backend prepara e orquestra; a assinatura sempre fica com o usuário.

---

## 2. Progresso por Camada

| Camada | Status | Entregas |
|---|---|---|
| Backend Core (FastAPI) | [##########] 100% | `/health`, `/health/detailed`, `/status`, `/chat`, `/metrics`, `/v1/messages/inbound` |
| Webhook Telegram | [##########] 100% | Secret token validado, bot operacional |
| Webhook X/Twitter (inbound) | [##########] 100% | HMAC SHA-256 validado, endpoint pronto |
| X/Twitter DM outbound | [####......] 40% | Poller implementado — requer Twitter Developer App para ativar em produção |
| Helius Webhook | [##########] 100% | HMAC validado, best-effort record_swap |
| IA (Gemini) | [##########] 100% | Intent detection + resposta contextual |
| Swap Prepare (Jupiter) | [##########] 100% | Quote + tx unsigned para assinatura em wallet |
| Wallet Execution (Frontend) | [##########] 100% | Connect, prepare, simulate, confirmação explícita, sign/send |
| UI/UX e Responsividade | [##########] 100% | Crossfade de vídeo (sem flash), typing indicator PT/EN, mensagem imediata no envio, auto-scroll inteligente, AnimePanel contido no grid |
| Auth (Web3Auth + Phantom) | [##########] 100% | Google OAuth via Web3Auth, carteira custodial gerada, Phantom devnet; `get_user_from_session()` aceita `twitter_user_id` como Bearer |
| Chat History | [##########] 100% | `addLocalChatMessage` persiste em localStorage; `getChatHistory` merge dedup; Historico modal com filtros All/You/Xiaolee |
| Campanhas | [##########] 100% | Join (409 idempotente), verify, claim com proof; custodial (google_*/tg_*) dispensado de Ed25519 |
| Transfer Universal | [##########] 100% | `ModernTransferService` resolve @telegram, @twitter, endereço Solana base58; pending transfer se destinatário sem conta |
| AI Bilíngue + Transfer Intent | [##########] 100% | Xiaolee espelha idioma do usuário; regex pre-LLM detecta transfer intent e bypassa safety refusal do Gemini |
| Redis Rate Limiting | [##########] 100% | Sliding window + fallback in-memory automático |
| PostgreSQL + Alembic | [########..] 80% | Migração gerada; requer provisionamento em produção |
| Docker Compose | [##########] 100% | PostgreSQL + Redis + Grafana + migrate one-shot |
| Observabilidade | [##########] 100% | `/metrics` Prometheus, Grafana 8 painéis, `/health/detailed` |
| Anchor on-chain | [######....] 60% | AnchorClient com PDA real (solders), record_swap (dry_run até keypair em produção) |
| Emergency Pause | [##########] 100% | `pause_protocol` / `unpause_protocol` / `transfer_admin` no contrato |
| Testes de carga | [######....] 60% | Locust 3 cenários; executar em staging |
| QA suite | [##########] 100% | **65 testes passando**, 6 skips legados |
| Auditoria externa | [..........] 0% -- BLOQUEADOR | Não iniciada — bloqueia mainnet |

### Evolução por Sprint

| Sprint | Status | Entregas Principais |
|---|---|---|
| Fase 1 | Concluida | Base FastAPI, Gemini, rotas de inbound |
| Fase 2 | Concluida | Fluxo wallet-first (prepare/simulate/sign/send) |
| Fase 3 | Concluida | Hardening de webhooks (Telegram/X/Helius) |
| Fase 4 | Concluida | QA expandido, observabilidade HTTP, CI fullstack |
| Fase 5 | Concluida | Idempotência 409, Anchor Client, CORS hardening, 65 testes |
| Fase 6 | Concluida | PostgreSQL/Alembic, Redis Rate Limit, solders PDA, Locust |
| Fase 7 | Concluida | Docker Compose completo, Grafana, Emergency Pause Rust, Makefile, UI Mobile hardening |
| Fase 8 | Concluida | UI Premium Refactor: Dashboard e Notifications redesenhados (SVG icons inline, paleta unificada, responsividade mobile¹, Navbar com ícones premium) |
| Fase 9 | Concluida | i18n EN/PT: `LanguageContext`, `useLanguage()`, `t()` com dot-path + interpolação `{{var}}`, toggle EN/PT na Navbar, locale files `en.json`/`pt.json`, todos os componentes traduzidos, correções de contraste e tamanho de texto |
| Fase 10 | Concluida | UX sprint: CampaignCard reativo (fix pós-claim), Dashboard fix (Carteira Desconectada), ActivityFeed unificado (campanhas+notifs), errorCode pattern em hooks, Navbar xs responsiva, Historico redesenhado + chat history localStorage, Wallet scroll fix, Withdraw/Deposit → Wallet modal |
| Fase 11 | Concluida | Transfer universal (`ModernTransferService`), pre-LLM transfer intent detection, Xiaolee bilíngue (espelha idioma), claim reward custodial sem Ed25519, crossfade de vídeo sem flash, typing indicator PT/EN, mensagem imediata no envio, auto-scroll inteligente, auth fallback por `twitter_user_id` |
| Fase 12 | Planejada | Twitter Developer App, auditoria externa, multisig, mainnet beta |

---

## 3. Arquitetura de Alto Nível

```mermaid
graph TB
subgraph "Clientes"
FE[Next.js Frontend]
TG[Telegram Bot]
XX[X/Twitter DM]
end

subgraph "Backend FastAPI"
API[app.py + Rate Limiter Redis]
ORCH[OrchestrationService]
GEM[GeminiClient]
SOL[SolanaClient + Jupiter]
CAMP[Campaigns Router]
NOTIF[Notifications Router]
HEL[Helius Webhook]
ANCHOR[AnchorClient + solders]
DB[(PostgreSQL via asyncpg)]
REDIS[(Redis — Rate Limit)]
end

subgraph "Observabilidade"
PROM[Prometheus /metrics]
GRAF[Grafana Dashboard]
end

subgraph "Solana"
JUP[Jupiter v6 API]
RPC[Solana RPC / Helius]
PROG[XiaoLee Core Program]
end

FE --> API
TG --> API
XX --> API

API --> REDIS
API --> ORCH
ORCH --> GEM
ORCH --> SOL
API --> CAMP
API --> NOTIF
API --> HEL

HEL --> ANCHOR
ANCHOR --> PROG

ORCH --> DB
CAMP --> DB
NOTIF --> DB
HEL --> DB

SOL --> JUP
SOL --> RPC

API --> PROM
PROM --> GRAF
```

---

## 4. Fluxos Críticos

### 4.1 Inbound IA

1. Mensagem entra por `/v1/messages/inbound` (ou webhook Telegram/X).
2. Rate limiter (Redis sliding window) verifica limite por chave.
3. Backend valida segredo/HMAC e orquestra intent via Gemini.
4. Resposta persistida e entregue no canal de origem.

**Canais de entrada:**

| Canal | Status | Observação |
|---|---|---|
| Frontend Next.js | Operacional | REST direto |
| Telegram Bot | Operacional | Secret token validado |
| X/Twitter (inbound webhook) | Pronto | HMAC SHA-256; requer configuração no Twitter Developer Portal |
| X/Twitter (DM outbound) | Planejado — mainnet | Requer Twitter Developer App Basic ($100/mês); biblioteca unofficial não-viável desde 2025 |

### 4.2 Swap Wallet-first

1. Frontend chama `/v1/solana/swap/prepare` — quote + tx unsigned.
2. Frontend simula na Devnet e exige confirmação explícita do usuário.
3. Wallet Phantom assina e envia para o RPC Solana.
4. Helius webhook notifica o backend após confirmação.
5. Backend chama `record_swap` via `AnchorClient` (best-effort, dry_run até keypair configurada).

### 4.3 Campanhas

1. Usuário chama `POST /campaigns/join` — `UniqueConstraint` garante idempotência (409 Conflict se já inscrito).
2. `POST /campaigns/verify` — verifica tarefas e emite `campaign:tasks_verified`.
3. `POST /campaigns/claim` — valida proof. Usuários custodiais (`google_*`/`tg_*`) dispensados de assinatura Ed25519; apenas Phantom precisa assinar.

### 4.4 Transfer Universal

```
Usuário (chat): "envia 2 SOL para @jistriane"
       ↓
response_generator.py
  1. Regex pre-LLM detecta: amount=2, token=SOL, recipient="jistriane"
  2. Chama ModernTransferService.transfer_tokens() diretamente
       ↓
ModernTransferService._resolve_recipient_with_enhanced_logic()
  1. É endereço base58? → busca Wallet no DB → resolve user_id
  2. É @handle? → busca por twitter_handle OU telegram_chat_id (case-insensitive)
  3. Não encontrado? → cria pending transfer (tokens guardados até o destinatário criar conta)
       ↓
Resultado: TRANSFER_SUCCESS_DIRECT ou TRANSFER_SUCCESS_PENDING
```

**Formatos aceitos pelo chat:**
- `"envia 2 SOL para @jistriane"` — handle Telegram ou Twitter
- `"send 1.5 USDC to EZKVUN9R..."` — endereço Solana base58
- `"manda 3 XLEE pra @brazilliancare"` — PT-BR também detectado

### 4.5 Fluxo de Chat Autenticado

```
POST /chat  { Authorization: Bearer <token> }
       ↓
get_user_from_session()
  1. Busca WebSession por session_id (google_session_*, tg_session_*)
  2. Fallback: busca User por twitter_user_id diretamente (google_*, tg_*, devnet_*)
       ↓
handle_chat_request(user, is_authenticated=True)
       ↓
generate_response()  [response_generator.py]
  1. Verifica token 6-dígitos → auth flow
  2. Verifica pending confirmations → executa ação pendente
  3. Pre-LLM transfer intent (regex) → transfer_token direto
  4. Pre-LLM confirm intent (regex) → confirm_action direto
  5. Fallback → Gemini com tools + system prompt bilíngue
```

### 4.6 Observabilidade

### 4.7 Observabilidade

1. Cada request HTTP é registrado em `xiaolee_http_requests_total` e `xiaolee_http_request_duration_seconds_avg`.
2. `GET /metrics` expõe métricas em formato Prometheus.
3. Grafana consome via datasource provisionado automaticamente.
4. `GET /health/detailed` verifica DB, Solana RPC, Gemini e Jupiter com latência por dependência.

---

## 5. Segurança Implementada

| Mecanismo | Status |
|---|---|
| HMAC para webhook X | OK |
| Secret token webhook Telegram | OK |
| Secret HMAC webhook Helius | OK |
| Rate limit por usuário/plataforma (Redis) | OK |
| CORS headers restritos (`CORS_ALLOWED_HEADERS` env) | OK |
| Fluxo não-custodial (sem chave privada do usuário no backend) | OK |
| Simulação + confirmação manual antes do envio | OK |
| 409 Conflict idempotente (UniqueConstraint DB) | OK |
| Emergency pause on-chain (`pause_protocol`) | OK |
| Admin keypair via env / vault (não hardcoded) | OK |
| PostgreSQL connection pool com `pool_pre_ping` | OK |
| Container não-root (Dockerfile) | OK |
| Auditoria externa | Pendente Pendente |
| HTTPS + HSTS em produção | Pendente Pendente |
| Multisig Gnosis Safe como admin | Pendente Pendente |
| Secrets via vault (não .env simples) | Pendente Pendente |

---

## 6. Estrutura de Diretórios (relevante)

```text
XiaoLee/
├── backend/
│ ├── alembic/ # Migrações de schema (Alembic async)
│ ├── database/
│ │ ├── database.py # Suporte dual SQLite/PostgreSQL
│ │ └── models.py
│ ├── server/
│ │ ├── app.py # FastAPI + lifespan + CORS + rate limiter
│ │ ├── rate_limiter.py # Redis sliding window + fallback in-memory
│ │ ├── settings.py # Env vars (DATABASE_URL, REDIS_URL, ...)
│ │ ├── metrics.py # Contadores Prometheus
│ │ ├── campaigns_routes.py
│ │ ├── notifications_routes.py
│ │ ├── webhooks/
│ │ │ └── helius_routes.py # record_swap best-effort
│ │ └── integrations/
│ │ └── anchor_client.py # PDA derivation + solders + submit
│ └── tests/ # 65 testes passando
├── frontend/
│ ├── src/
│ │ ├── components/ # Wallet, CampaignCard, Dashboard
│ │ ├── hooks/ # useJoinCampaign (409 tratado)
│ │ └── idl/ # xiaolee_core.json (IDL real)
├── solana-program/
│ └── xiaolee_core/
│ └── src/lib.rs # Program + emergency pause + events
├── load_tests/
│ └── locustfile.py # 3 cenários (Critical, ReadOnly, Chat)
├── ops/
│ ├── prometheus.yml
│ └── grafana/ # Dashboard provisionado automaticamente
├── docs/
│ ├── API_REFERENCE.md
│ ├── ARCHITECTURE.md # Este arquivo
│ ├── DESIGN_SYSTEM.md # Paleta, ícones, padrão de cards e layout
│ ├── SMART_CONTRACT.md
│ └── MAINNET_READINESS.md # 6 gates com checklist
├── docker-compose.yml # PostgreSQL + Redis + Grafana + migrate
├── .env.example # Template completo de variáveis
└── Makefile # db-migrate, load-test, anchor-build, ...
```

---

## 7. UX de Chat — Decisões de Implementação (Sprint 11)

### Typing Indicator & Feedback Visual

```
Usuário envia mensagem
  → setMessage("") imediato (input limpa)
  → setMsgs([...prev, { sent, response: "__typing__" }])  ← aparece na tela
  → API call (async)
  → resposta chega → replace último item com conteúdo real
```

O sentinel `"__typing__"` é renderizado como bolha animada com três pontinhos (`typing-dot` CSS) e texto `digitando... / typing...` em itálico.

### Auto-Scroll Inteligente

```
scrollContainerRef (div overflow-y-auto)
  → onScroll: atualiza isNearBottomRef (true se < 80px do fundo)

useEffect([msgs]):
  if isNearBottomRef.current → messagesEndRef.scrollIntoView(smooth)

handleSendMessage:
  isNearBottomRef.current = true  ← força scroll no envio
```

Comportamento: scroll automático só quando o usuário já está perto do fundo **ou** acabou de enviar uma mensagem.

### Crossfade de Vídeo (Pfp.tsx)

```
activeSrc  (opacity: 1, sempre visível)
pendingSrc (opacity: 0, carregando em background)
  → onCanPlay → swapToPending()
       → fade: active opacity 0 → 250ms → activeSrc = pendingSrc, opacity 1
```

Elimina o flash branco que ocorria ao usar `key={videoKey}` para forçar remount do `<video>`.

---

## 8. Próximos Passos

### Fase 11 — Concluída

Deploy Railway operacional. Frontend e backend em produção com CI automático via GitHub push.

### Fase 12 — Mainnet

1. **Twitter Developer App Basic ($100/mês)** — ativar DM outbound da XiaoLee via API oficial v2. O webhook inbound (`/v1/integrations/x/webhook`) já está pronto; só falta o token de acesso com permissão de DM.
2. **Provisionar PostgreSQL 16+** e rodar `make db-migrate`.
3. **Configurar `SOLANA_ADMIN_KEYPAIR_B58`** no vault → testar `record_swap` submit real em devnet.
4. **HTTPS + HSTS** no servidor de produção.
5. **Contratar auditores** — mínimo 2 firmas independentes (ver `docs/MAINNET_READINESS.md`).
6. **Multisig Gnosis Safe** como admin do protocolo (substituir EOA).
7. **`make load-test-staging`** — validar p95 < 500ms.
8. **Mainnet beta** com TVL limitado + bug bounty ativo.

---

## 9. Notas Operacionais

### CI/CD

GitHub Actions (`fullstack-ci.yml`) roda em todo push para `main`:
- **Backend:** `pytest -q --ignore=tests/test_anchor_integration.py` (65 testes, ignora teste de integração Anchor que requer validador local)
- **Frontend:** `npm run lint` + `npm run build`

### X/Twitter DM — Decisão de Arquitetura

O poller de DMs (`backend/server/integrations/x_poller.py`) está implementado e suporta três modos de auth (login, env cookies, arquivo de cookies). Está desativado em produção por enquanto porque:

1. A biblioteca `agent-twitter-client` (não-oficial) parou de funcionar em 2025 — o Twitter removeu `guest/activate.json` da v1.1 API.
2. A API oficial v2 com permissão de DM requer o plano **Basic ($100/mês)** no Twitter Developer Portal.
3. Para hackathon/devnet, o **Telegram é o canal principal** e cobre 100% do fluxo conversacional.

A ativação do X DM outbound é o primeiro passo da Fase 11 (mainnet), quando o volume de usuários justifica o custo.

### Testes Legados

Scripts de integração com Twikit e ferramentas de suporte antigas foram mantidos como referência. Estão skipados no pytest para não quebrar a suíte principal. A suíte ativa é de **65 testes passando**.

---

## 9. Arquitetura Frontend

### 9.1 UserData — Singleton de Estado Global

`UserData` é uma classe estática que centraliza todo o estado do usuário no frontend. Não é um Context React — é um singleton acessível de qualquer lugar sem prop drilling.

```
UserData (static class)
├── user_info        — twitter_user_id, twitter_handle, created_at
├── session_id       — token usado no header Authorization
├── balances         — TokenBalance[]
├── campaigns        — UserCampaignParticipation[]
├── history
│   ├── chat_history — ChatHistoryItem[] (in-memory, sobrescrito por fetchData)
│   ├── swaps        — SwapHistoryItem[]
│   └── transactions — TransactionHistoryItem[]
└── devnet_wallet_public_key
```

**Persistência em localStorage:**

| Chave | Conteúdo | Sobrevive fetchData? |
|---|---|---|
| `xiaolee_devnet_session` | session_id (token de auth) | Sim |
| `xiaolee_user_info` | UserInfo serializado | Sim |
| `xiaolee_chat_history` | ChatHistoryItem[] (até 200) | Sim — merge por timestamp |
| `connected_wallet` | Public key Phantom | Sim |

`getChatHistory()` faz merge entre localStorage e in-memory com deduplicação por `user_message.timestamp`, garantindo que mensagens locais não somem após `fetchData()` sobrescrever `history.chat_history`.

### 9.2 Fluxo de Autenticação

```mermaid
flowchart TD
    A[Página carrega] --> B{localStorage\nxiaolee_devnet_session?}
    B -- sim --> C[UserData.restoreSession()]
    B -- não --> D[Navbar monta]

    C --> E[session_id + user_info restaurados]
    D --> F{Usuário clica\nLogin}

    F --> G[Web3Auth Google OAuth]
    F --> H[Phantom Wallet Connect]

    G --> I[UserData.setDevnetWalletSession\ncustodial_wallet_address]
    H --> J[UserData.setDevnetWalletSession\npublic_key Phantom]

    I --> K[fetchData → setUserData]
    J --> K
    E --> K

    K --> L[CustomEvent userDataLoaded]
    L --> M[Dashboard / ActivityFeed\natualizam via listener]
```

**Sessões disponíveis:**
- `devnet_guest_*` — guest anônimo criado automaticamente
- `devnet_wallet_<pubkey>` — Phantom conectado
- token Web3Auth — Google OAuth via custodial wallet

### 9.3 Navegação de Telas

```mermaid
flowchart LR
    CHAT["/\nChat Principal\nXiaolee + AnimePFP"] -->|Navbar| CAMP
    CHAT -->|Navbar| DASH
    CHAT -->|Navbar| NOTIF
    CHAT -->|Botão Histórico| HIST

    CAMP["/campaigns\nCampanhas\nJoin/Verify/Claim"]
    DASH["/dashboard\nDashboard\nStats + Activity + Economy"]
    NOTIF["/notifications\nNotificações\nIn-app inbox"]

    HIST["Modal Historico\nChat filtrado\nAll/You/Xiaolee"]
    WALL["Modal Wallet\nBalance + Tokens\n+ Swap"]

    CHAT -->|Withdraw/Deposit/Wallet| WALL
    CAMP -->|Wallet button| WALL
```

### 9.4 Fluxo de Dados — Chat e Histórico

```mermaid
sequenceDiagram
    actor U as Usuário
    participant CP as ChatPanel
    participant UC as useChat
    participant API as Backend /chat
    participant UD as UserData
    participant LS as localStorage
    participant HI as Historico Modal

    U->>CP: digita mensagem + Send
    CP->>UC: sendChatMessage(msg)
    UC->>API: POST /chat { message, Authorization }
    API-->>UC: { response, animations, intent }
    UC-->>CP: response
    CP->>UD: addLocalChatMessage(msg, response)
    UD->>LS: push em xiaolee_chat_history (max 200)
    UD->>UD: dispatch userDataLoaded

    U->>HI: abre modal Histórico
    HI->>UD: getChatHistory()
    UD->>LS: lê xiaolee_chat_history
    UD-->>HI: merge(localStorage + in-memory) sorted por timestamp
    HI-->>U: exibe bolhas filtradas (All/You/Xiaolee)
```

### 9.5 Fluxo de Dados — Campanhas e ActivityFeed

```mermaid
flowchart TD
    API_CAMP[Backend /campaigns] -->|useUserCampaigns| CAMP_STATE
    API_NOTIF[Backend /notifications/me] -->|useNotifications| NOTIF_STATE

    CAMP_STATE --> CAMP_CARD[CampaignCard\nprop: userCampaignParticipation\nestado reativo — sem cache estático]
    CAMP_STATE --> ACTIVITY
    NOTIF_STATE --> ACTIVITY

    ACTIVITY[ActivityFeed\nmerge dedup por claim_receipt_id\nsintético: campaign paid → item de claim]
    ACTIVITY --> DASH[Dashboard\nActivityFeed maxItems=5]
```

**Deduplicação no ActivityFeed:** notificações cujo `related_signature` coincide com `claim_receipt_id` de uma campanha paga são excluídas — o item sintético da campanha substitui, evitando duplicatas quando o webhook Helius também gera notificação.
