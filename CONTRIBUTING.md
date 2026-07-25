# Como Contribuir para a XiaoLee

> Atualizado em: **2026-04-24** | Sprint 7 concluída.

Bem-vindo! Este documento descreve o fluxo completo para configurar o ambiente local e contribuir com o protocolo XiaoLee.

---

## Pré-requisitos do Sistema

| Ferramenta | Versão Mínima | Uso |
|---|---|---|
| Docker & Docker Compose | 24+ | Stack de produção (PostgreSQL, Redis, Grafana) |
| Node.js & NPM | 18+ | Frontend Next.js e testes |
| Python | 3.12+ | Backend FastAPI |
| Rust & Cargo | 1.75+ | Opcional: compilação de Smart Contracts |
| Solana CLI | 1.18+ | Opcional: ferramentas de rede Solana |
| Anchor CLI | 0.30+ | Opcional: desenvolvimento on-chain |

### Instalando Rust e Solana CLI

```bash
# Instalar Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"

# Instalar Solana CLI
sh -c "$(curl -sSfL https://release.solana.com/v1.18.0/install)"
export PATH="$HOME/.local/share/solana/install/active_release/bin:$PATH"

# Instalar Anchor via AVM
cargo install --git https://github.com/coral-xyz/anchor avm --locked --force
avm install 0.30.0 && avm use 0.30.0
```

---

## Onboarding Rápido (3 minutos)

```bash
# 1. Setup completo (venv + npm + .env)
make init

# 2. Verificar ambiente
make preflight

# 3. Subir dev local (backend + frontend)
make dev
```

**Serviços disponíveis após `make dev`:**

| Serviço | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| Prometheus | http://localhost:8000/metrics |

---

## Modo Docker (Stack Completa)

Sobe PostgreSQL, Redis, backend, frontend, Prometheus e Grafana:

```bash
# Criar .env a partir do template
cp .env.example .env
# Preencha as variáveis obrigatórias

# Subir stack completa (inclui migração automática)
make run-docker
```

| Serviço | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8000 |
| Grafana | http://localhost:3001 |
| Prometheus | http://localhost:9090 |

```bash
# Parar stack
make stop-docker

# Parar e remover volumes (limpar dados)
make stop-docker-clean
```

---

## Variáveis de Ambiente Obrigatórias

| Variável | Descrição | Exemplo |
|---|---|---|
| `GEMINI_API_KEY` | Chave da API Google Gemini | `AIzaSy...` |
| `HELIUS_API_KEY` | Chave da API Helius (RPC Solana) | `your_helius_key` |
| `HELIUS_WEBHOOK_SECRET` | HMAC para validar webhooks Helius | `random_32_chars` |
| `TELEGRAM_WEBHOOK_SECRET` | Secret para webhooks Telegram | `random_32_chars` |
| `X_WEBHOOK_SECRET` | HMAC para webhooks X/Twitter | `random_32_chars` |
| `NEXT_PUBLIC_CORE_API_URL` | URL base da API para o frontend | `http://localhost:8000` |
| `SOLANA_RPC_URL` | URL do nó RPC Solana | `https://api.devnet.solana.com` |

**Opcionais (habilitam funcionalidades adicionais):**

| Variável | Descrição |
|---|---|
| `DATABASE_URL` | PostgreSQL em produção (deixar vazio = SQLite local) |
| `REDIS_URL` | Redis para rate limiting (deixar vazio = in-memory) |
| `SOLANA_ADMIN_KEYPAIR_B58` | Keypair admin para `record_swap` on-chain (deixar vazio = dry_run) |

> Veja `.env.example` para o template completo com todas as variáveis.

---

## Banco de Dados

O banco usa **SQLite por padrão** (desenvolvimento) e **PostgreSQL em produção** (via `DATABASE_URL`).

```bash
# Aplicar migrações (local com SQLite ou produção com PostgreSQL)
make db-migrate

# Ver status das migrações
make db-status

# Criar nova migração após alterar models.py
make db-new-migration MSG="adiciona campo novo"

# Reverter última migração
make db-rollback
```

---

## Rodando os Testes

### Suite Backend (pytest)

```bash
# Suite completa (65 testes)
make test-backend

# Smoke rápido (apenas métricas)
make smoke-backend
```

### Testes Frontend

```bash
make smoke-frontend
# ou
cd frontend && npm test
```

### Testes do Smart Contract (Anchor)

```bash
make anchor-test
# ou
cd solana-program/xiaolee_core && anchor test
```

### Testes de Carga (Locust)

```bash
# Smoke local (20 users, 2 min)
make load-test-smoke

# UI interativa em http://localhost:8089
make load-test-ui

# Staging (requer HOST)
make load-test-staging HOST=https://api-staging.xiaolee.io
```

---

## Estrutura de Branches

```
main → Branch de produção (protegida, requer PR)
feat/* → Novas funcionalidades
fix/* → Correções de bugs
docs/* → Atualizações de documentação
chore/* → Manutenção (deps, config, infra)
```

---

## Padrões de Commit (Conventional Commits)

```
feat: adiciona endpoint POST /campaigns/create
fix: corrige overflow no contrato anchor record_swap
docs: atualiza ARCHITECTURE.md com Sprint 7
chore: atualiza requirements.txt com solders 0.26.0
refactor: extrai rate_limiter para arquivo separado
test: adiciona cenário de PDA derivation no anchor_client
```

---

## Regras de Desenvolvimento

### Backend (Python / FastAPI)

1. Novas rotas: arquivos de router separados (`*_routes.py`).
2. Schemas: Pydantic v2 com tipos estritos.
3. **Nunca commite** `GEMINI_API_KEY`, `SOLANA_ADMIN_KEYPAIR_B58` ou qualquer secret.
4. Novos endpoints: documentar em `docs/API_REFERENCE.md`.
5. Suite deve passar com `make test-backend` (65+ testes).
6. Rate limiting async: use `await _enforce_rate_limit_async(key)` em rotas novas.
7. Banco: use `asyncpg` via `DATABASE_URL` em produção; `aiosqlite` em dev.

### Frontend (Next.js / TypeScript)

1. Interfaces TypeScript em `src/interfaces/` — espelhar exatamente o schema da API.
2. Chamadas de API centralizadas via `src/api/api.tsx`.
3. **Sempre validar** ID do usuário não-vazio antes de fetch (veja `UserData.fetchData()`).
4. Novos hooks em `src/hooks/` com tratamento de erro, loading state e tipagem.
5. Status de campanha: usar enum canônico `enrolled | tasks_verified | paid`.
6. Tratar `HTTP 409 Conflict` em joins duplicados (flag `alreadyJoined`).

### Smart Contracts (Rust / Anchor)

1. **Nunca use `.unwrap()`** em aritmética — sempre `checked_add` / `ok_or(ErrorCode::...)`.
2. Novas instruções: verificação estrita de `has_one = admin`.
3. Operações de estado: seguir padrão **CEI** (Checks → Effects → Interactions).
4. Emitir eventos para todas as mudanças de estado importantes.
5. Testar vetores de ataque: contas não-autorizadas, overflows, replay.
6. Documentar nova instrução em `docs/SMART_CONTRACT.md`.
7. Após rebuild: sincronizar IDL com `make anchor-idl-sync`.

---

## Abrindo um Pull Request

1. Fork e crie branch a partir de `main` (`feat/minha-feature`).
2. Implemente seguindo os padrões acima.
3. Rode `make preflight` — deve passar completamente.
4. Rode `make test-backend` — todos os testes devem passar.
5. Atualize documentação impactada.
6. Abra o PR com descrição clara do que foi feito e por que.
7. Aguarde revisão de pelo menos 1 maintainer.

---

## Checklist de Mainnet

Antes de aprovar qualquer PR que impacte produção:

```bash
make audit-checklist
```

Consulte `docs/MAINNET_READINESS.md` para o checklist completo com 6 gates de aprovação.
