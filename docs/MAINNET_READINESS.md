# XiaoLee — Mainnet Readiness Checklist (Multi-chain)

> Documento de referência para o rollout controlado do protocolo XiaoLee em mainnet.
> Atualizado em: **2026-05-30** | Reconciliado para arquitetura **híbrida multi-chain** (Solana + Stellar).
>
> **Decisão de arquitetura:** XiaoLee mantém duas tracks on-chain em paralelo. A track Solana
> (Anchor) já tem contrato em devnet; a track Stellar (Soroban) é a direção estratégica do
> programa 37 Graus e ainda não tem contrato escrito. O backend, o frontend e a infra são
> compartilhados pelas duas tracks (coluna `chain` no DB desde a migração `20260515_stellar_columns.py`).

---

## Como ler este documento

Cada gate marca o estado real verificado no código (não aspiracional). Onde Solana e Stellar
divergem, há colunas separadas. Mainnet só é liberada quando **todos os gates da track escolhida**
estiverem verdes E os gates compartilhados (backend, infra, segurança) estiverem verdes.

| Legenda | Significado |
|---|---|
| Concluido | Verificado no código / em produção |
| Em andamento | Iniciado, incompleto |
| Pendente | Não iniciado |
| BLOQUEADOR | Impede mainnet com fundos reais |

---

## Status Geral

| Categoria | Track | Status | Progresso |
|---|---|---|---|
| Contrato on-chain — Solana (Anchor) | Solana | Em andamento | [######....] 60% — devnet ok; `record_swap` submit real pendente keypair |
| Contrato on-chain — Soroban (Stellar) | Stellar | Pendente | [..........] 0% — **contrato NÃO escrito** (só spec no RT) |
| Backend API (compartilhado) | Ambos | Em andamento | [########..] 80% — ~128 testes coletados (1 erro de coleta a corrigir), auditoria interna feita |
| Frontend (compartilhado) | Ambos | Em andamento | [#######...] 70% — Freighter + Anchor convivem; limpeza do híbrido pendente |
| Camada Stellar off-chain (Horizon/SEP-10/x402) | Stellar | Concluido | [##########] 100% — `stellar_adapter`, `stellar_auth`, `x402` auditados (AUDIT.md) |
| PostgreSQL + Alembic (multi-chain) | Ambos | Concluido | [##########] 100% — coluna `chain` + `stellar_wallet` migradas |
| Redis Rate Limiting | Ambos | Em andamento | [########..] 80% — código + fallback; configurar `REDIS_URL` em prod |
| Deploy Railway/Render | Ambos | Em andamento | [######....] 60% — configs prontas; provisionar serviços |
| Telegram Bot | Ambos | Concluido | [##########] 100% — canal principal operacional |
| X/Twitter DM outbound | Ambos | Em andamento | [####......] 40% — requer Twitter Developer App ($100/mês) |
| Asset $XLEE — Solana (SPL) | Solana | Em andamento | — |
| Asset $XLEE — Stellar (SAC/SEP-41) | Stellar | Pendente | [..........] 0% — não emitido |
| Auditoria externa | Ambos | Pendente | [..........] 0% -- **BLOQUEADOR** |
| Secrets / Vault | Ambos | Pendente | [..........] 0% — keypairs, DB pass, Redis pass, JWT_SECRET |
| HTTPS + HSTS | Ambos | Pendente | [..........] 0% — configurar no deploy |
| Multisig (admin) | Ambos | Pendente | [..........] 0% — substituir EOA antes do mainnet |
| Bug bounty | Ambos | Pendente | [..........] 0% — após auditoria |

> Auditoria interna de segurança (Sprint 2026-05): 23 findings corrigidos, ver `AUDIT.md`.
> Isso **não substitui** auditoria externa independente para mainnet com TVL real.

---

## Gate 1A — Contrato On-chain Solana (Anchor)

| Item | Status | Evidência |
|---|---|---|
| Program ID confirmado | Concluido | `Fmmpn79Tij8fzYHg31ekZz4MmK9ArGzN59VogfcwhXiM` |
| Código do programa | Concluido | `solana-program/xiaolee_core/programs/xiaolee_core/src/lib.rs` |
| IDL real no frontend | Concluido | `frontend/src/idl/xiaolee_core.json` |
| Cluster alinhado (devnet) | Concluido | `Anchor.toml`, `useXiaoLeeProgram.ts` |
| `initialize_global` / `initialize_user` | Concluido | Executado em devnet |
| `record_swap` — serialização | Concluido | Discriminador correto, Borsh u64 |
| `record_swap` — submit real | PENDENTE P0 | Requer `SOLANA_ADMIN_KEYPAIR_B58` |
| Emergency pause (`pause_protocol`) | Concluido | No contrato Rust |
| Auditoria externa do programa | BLOQUEADOR | 0% |

### Ações P0 (track Solana)
- [ ] Configurar `SOLANA_ADMIN_KEYPAIR_B58` em produção via vault
- [ ] `anchor deploy --provider.cluster mainnet`
- [ ] Verificar Program ID em Solscan
- [ ] `initialize_global` na mainnet
- [ ] Testar `record_swap` com keypair real em devnet antes do mainnet

---

## Gate 1B — Contrato On-chain Stellar (Soroban) — NÃO INICIADO

> **Este é o P0 que destrava a track Stellar.** O contrato `xiaolee_core` Soroban está
> especificado no `RT_XIAOLEE_STELLAR.md` (seção 10), mas **não existe código** — não há
> crate Rust/Soroban no repositório (só o programa Anchor de Solana).

| Item | Status | Spec |
|---|---|---|
| Crate Soroban `xiaolee_core` criado | Pendente | RT seção 10 |
| `initialize(admin, xlee_sac)` | Pendente | `require_auth`, GlobalConfig em instance storage |
| `initialize_user(twitter_id)` | Pendente | persistent storage + TTL bump |
| `record_reward(admin, twitter_id, amount)` | Pendente | `require_auth` + `checked_add` + transfer via SAC |
| `pause_protocol` / `unpause_protocol` | Pendente | emergency pause |
| `transfer_admin` | Pendente | migração de autoridade |
| Eventos (`reward_recorded`, etc.) | Pendente | RT seção 10 |
| Testes do contrato | Pendente | — |
| Deploy em **Testnet** | Pendente | P0 |
| Deploy em **Mainnet** | Pendente | só após auditoria |

### Ações P0 (track Stellar)
- [ ] Escrever o crate Soroban conforme spec do RT (auth, overflow check, eventos)
- [ ] Testes unitários do contrato (`soroban test`)
- [ ] `stellar contract deploy` em **Testnet**
- [ ] Emitir asset `XLEE` + `stellar contract asset deploy` (SAC) em Testnet
- [ ] Integrar `StellarAdapter.record_reward` ao contrato real (hoje é stub/off-chain)
- [ ] Só então: deploy Mainnet (pós-auditoria)

---

## Gate 2 — Backend API (compartilhado)

| Item | Status | Evidência |
|---|---|---|
| Suíte de testes | Em andamento | ~128 testes coletados; **1 erro de coleta** em `scripts/db/test_mcp_migration.py` a corrigir |
| CORS headers restritos | Concluido | `CORS_ALLOWED_HEADERS` env, não wildcard |
| Rate limiting | Concluido | Redis + fallback in-memory |
| Idempotência (409) | Concluido | `uq_participant_campaign_user` |
| Observabilidade `/metrics` | Concluido | Prometheus |
| `/health/detailed` | Concluido | DB, Solana, Gemini; **falta Horizon/Stellar RPC** |
| SEP-10 auth (Stellar) | Concluido | `stellar_auth_routes.py` — auditado (SEC-008/014/015) |
| x402 micropagamento | Concluido | `x402_routes.py` — anti-replay auditado (SEC-001/013) |
| Helius webhook | Concluido | HMAC validado (SEC-007/011 corrigidos) |
| PostgreSQL multi-chain | Concluido | coluna `chain`, `stellar_wallet` |
| Redis em produção | Pendente | configurar `REDIS_URL` |
| `JWT_SECRET` obrigatório no startup | Concluido | raise se ausente (SEC-002) |
| Secrets via vault | Pendente | HashiCorp/AWS/Doppler |

### Ação imediata
- [ ] Corrigir erro de coleta em `backend/scripts/db/test_mcp_migration.py` para a suíte rodar limpa

---

## Gate 3 — Frontend (compartilhado, híbrido)

| Item | Status | Evidência |
|---|---|---|
| Build TypeScript limpo | Concluido | exit 0 |
| Wallet Solana (Anchor) | Concluido | `useXiaoLeeProgram.ts`, `Wallet.tsx` |
| Wallet Stellar (Freighter) | Concluido | `StellarWallet.tsx`, `utils/stellar.ts` |
| Seleção/abstração de chain na UI | Pendente | hooks Anchor e Freighter convivem sem switch unificado |
| 409 Conflict tratado | Concluido | `useJoinCampaign.ts` |
| i18n EN/PT | Concluido | `LanguageContext`, locales completos |
| Contraste/legibilidade | Concluido | sem opacidade em texto |

### Decisão pendente (híbrido)
- [ ] Definir UX de troca de chain (Solana vs Stellar) ou detectar por wallet conectada
- [ ] Remover hooks mortos se uma track for desativada

---

## Gate 4 — Banco de Dados (compartilhado)

| Item | Status | Notas |
|---|---|---|
| SQLite (dev) | Concluido | aiosqlite |
| PostgreSQL (prod) | Concluido | asyncpg + pool_pre_ping |
| Alembic async | Concluido | migrações versionadas |
| Migração multi-chain | Concluido | `20260515_stellar_columns.py` |
| DB de produção provisionada | Pendente | PostgreSQL 16 gerenciado (RDS/Railway) |

```bash
export DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/xiaolee_prod"
cd backend && alembic upgrade head
```

---

## Gate 5 — Performance (SLA, compartilhado)

| Métrica | Target | Status |
|---|---|---|
| p50 | < 200ms | Pendente teste de carga em staging |
| p95 | < 500ms | Pendente |
| p99 | < 1000ms | Pendente |
| Error rate | < 1% | Pendente |

Os endpoints Stellar (SEP-10, swap path payment) ainda não foram medidos sob carga —
o `locustfile.py` já tem as classes (`XiaoLeeStellarAuth`), falta executar em staging.

---

## Gate 6 — Segurança (compartilhado)

| Item | Status | Prazo |
|---|---|---|
| Auditoria interna (Semgrep + crypto + fuzzing) | Concluido | 23 findings corrigidos — `AUDIT.md` |
| Auditoria externa — contratos | BLOQUEADOR | iniciar antes de mainnet |
| Auditoria externa — backend API | BLOQUEADOR | junto com contratos |
| Bug bounty | Pendente | após auditoria |
| Secrets em vault | Pendente | — |
| HTTPS + HSTS | Pendente | no deploy |

### Auditores por chain

| Track | Especialização | Candidatos |
|---|---|---|
| Solana (Anchor/Rust) | Solana programs | Ottersec (osec.io), Sec3 (sec3.dev), Trail of Bits |
| Stellar (Soroban/Rust) | Soroban | Veridise, OtterSec (Soroban), Certora; revisão community SDF (Discord) como pré-auditoria |
| Backend/DeFi | App + protocolo | Trail of Bits, Sherlock (sherlock.xyz) |

> Mínimo **2 auditorias independentes** por track antes de mainnet com TVL real.

---

## Gate 7 — X/Twitter DM Outbound (compartilhado, não bloqueia hackathon)

| Item | Status | Detalhe |
|---|---|---|
| Webhook inbound HMAC | Concluido | `/v1/integrations/x/webhook` valida SHA-256 |
| Poller implementado | Concluido | `x_poller.py` |
| Twitter API oficial (DM v2) | Pendente | requer Developer App, escopo `dm.write` |
| Plano mínimo | Pendente | Basic ($100/mês) |

`agent-twitter-client` (scraper) inviável desde 2025 (Twitter removeu `guest/activate.json`).
Telegram cobre 100% do fluxo conversacional até a ativação do X.

---

## Plano de Rollout (multi-chain)

```
Agora — Reconciliação + Soroban
├── Reconciliar docs para multi-chain (este doc, DEPLOY_MAINNET, README, ARCHITECTURE, SMART_CONTRACT)
├── Escrever contrato Soroban xiaolee_core (Gate 1B) + testes
├── Corrigir erro de coleta de testes (Gate 2)
└── Deploy Soroban em Testnet + emitir XLEE/SAC Testnet

Pré-Mainnet
├── Track Solana: SOLANA_ADMIN_KEYPAIR_B58 no vault, record_swap submit real
├── Track Stellar: StellarAdapter.record_reward integrado ao contrato real
├── Secrets/vault + HTTPS/HSTS + multisig (ambas tracks)
├── Testes de carga em staging (p95 < 500ms) incluindo endpoints Stellar
└── Contratar auditores (uma por track + backend)

Auditoria
├── Auditoria contratos (Anchor + Soroban) — 2–4 semanas cada
├── Correções pós-auditoria
├── Pen test frontend
└── Bug bounty em testnet pública

Mainnet Beta
├── Deploy mainnet com TVL limitado (track por track)
├── Monitor (Tenderly/Defender p/ Solana; Horizon stream p/ Stellar)
└── Rollout gradual 10% -> 50% -> 100% + bug bounty público
```

---

## Resposta a Incidentes

| Severidade | Definição | Tempo | Ação |
|---|---|---|---|
| P0 | Fundos em risco / sistema down | < 15 min | Pausar contratos (`pause_protocol`), war room |
| P1 | Funcionalidade crítica degradada | < 1 hora | Hotfix, comunicado |
| P2 | Funcionalidade não-crítica | < 24 horas | Fix planejado |

**Contatos de emergência (configurar antes do mainnet):**
- Admin multisig — Solana (Squads) e Stellar (multisig nativo)
- Monitor — Tenderly Alerts (Solana) + Horizon event_stream (Stellar)
- Canal de incidentes — Discord #incident-response
