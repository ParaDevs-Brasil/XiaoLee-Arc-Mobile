# XiaoLee — Guia de Deploy em Mainnet (Multi-chain)

> Runbook de produção para colocar a XiaoLee online com segurança.
> Atualizado em: **2026-05-30** | Reconciliado para arquitetura **híbrida Solana + Stellar**.
>
> Pré-requisito: todos os gates de `docs/MAINNET_READINESS.md` da track-alvo verdes,
> incluindo **auditoria externa** (BLOQUEADOR). Este guia cobre a mecânica de deploy,
> não substitui os gates de segurança.

---

## 0. Ordem de execução

```
1. Secrets & Vault (compartilhado)
2. Track Solana  -> deploy Anchor (mainnet-beta)        [se ativando Solana]
3. Track Stellar -> deploy Soroban + asset XLEE/SAC     [se ativando Stellar]
4. Backend + Frontend (HTTPS)
5. Banco gerenciado + observabilidade
```

As tracks são independentes: você pode ativar Solana, Stellar, ou ambas. O backend e o
frontend são compartilhados e leem a chain via coluna `chain` / wallet conectada.

---

## 1. Secrets Vault & Variáveis de Ambiente (compartilhado)

NUNCA armazene secrets de produção em disco ou `.env` sem proteção.

### Opções de vault
- **AWS Secrets Manager** (recomendado em EC2): IAM Role + SDK puxa no startup.
- **Doppler / HashiCorp Vault**: sincroniza secrets no build container via CLI.

### Secrets obrigatórios (validados no startup do backend)

| Secret | Track | Uso |
|---|---|---|
| `JWT_SECRET` | Ambos | Sessão (SEP-10/auth). Backend faz raise se ausente (SEC-002). |
| `ENCRYPTION_KEY` | Ambos | Criptografia de dados custodiais. |
| `GEMINI_API_KEY` | Ambos | Intent/persona. |
| `DATABASE_URL` | Ambos | PostgreSQL gerenciado. |
| `REDIS_URL` | Ambos | Rate limiting. |
| `TELEGRAM_WEBHOOK_SECRET` | Ambos | Webhook Telegram. |
| `X_WEBHOOK_SECRET` | Ambos | HMAC webhook X. |
| `HELIUS_WEBHOOK_SECRET` | Solana | HMAC webhook Helius (fail-closed, SEC-011). |
| `SOLANA_ADMIN_KEYPAIR_B58` | Solana | `record_swap` admin sign. |
| `STELLAR_SERVER_SECRET` | Stellar | Keypair SEP-10 (challenge sign). Sem ele, auth retorna 503 (SEC-008/015). |
| `STELLAR_X402_WALLET` | Stellar | Carteira receptora x402. Sem ela, retorna 503 (SEC-004/016). |
| `STELLAR_ADMIN_SECRET` | Stellar | Admin do contrato Soroban (`record_reward`). |

> Os fail-open antigos foram fechados na auditoria interna: ausência de secret = 503, não "aceita tudo".

---

## 2. Track Solana — Deploy do Programa Anchor (mainnet-beta)

> Pré-requisito: programa auditado externamente.

### Gerar keypair admin (cold storage + vault)
```bash
solana-keygen new --outfile admin-keypair.json
cat admin-keypair.json | python3 -c "import sys,json,base58; print(base58.b58encode(bytes(json.load(sys.stdin))).decode())"
# Guarde o Base58 no vault como SOLANA_ADMIN_KEYPAIR_B58 e DELETE o arquivo após backup seguro
```

### Deploy
```bash
# Anchor.toml: [provider] cluster = "mainnet", wallet = "~/.config/solana/id.json"
cd solana-program/xiaolee_core
anchor build
anchor deploy --provider.cluster mainnet     # ~3 SOL para rent/deploy
anchor run initialize_global --provider.cluster mainnet
```
Verifique o Program ID em Solscan e troque o admin EOA por **multisig (Squads)** antes de TVL real.

---

## 3. Track Stellar — Deploy Soroban + Asset XLEE/SAC

> Pré-requisito: contrato Soroban escrito (Gate 1B do readiness — **hoje pendente**) e auditado.

### 3.1 Keypairs (cold storage + vault)
```bash
# Admin do contrato e issuer do asset DEVEM ser keypairs distintos
stellar keys generate xlee-admin   --network mainnet
stellar keys generate xlee-issuer  --network mainnet
# Exporte os secrets (S...) para o vault: STELLAR_ADMIN_SECRET, e o issuer para emissão
```

### 3.2 Emitir asset XLEE + deploy do SAC
```bash
# 1. Emitir XLEE a partir da conta issuer (changeTrust + payment) via SDK
# 2. Deploy do Stellar Asset Contract para uso programático no Soroban:
stellar contract asset deploy --asset XLEE:G<ISSUER> --network mainnet
```

### 3.3 Deploy do contrato xiaolee_core (Soroban)
```bash
cd <crate-soroban>            # crate ainda não existe — ver RT seção 10 / Gate 1B
stellar contract build
stellar contract deploy --wasm target/.../xiaolee_core.wasm --network mainnet
# initialize(admin, xlee_sac) — passa o endereço do SAC emitido em 3.2
```
Troque o admin por **multisig nativo Stellar** antes de TVL real. Configure o backend
(`StellarAdapter.record_reward`) para apontar ao contract ID de mainnet.

### 3.4 SEP-10 / x402 em produção
- `STELLAR_SERVER_SECRET` e `STELLAR_X402_WALLET` no vault (sem eles, os endpoints retornam 503).
- `/health/detailed` deve passar a incluir Horizon/Stellar RPC.

---

## 4. Hospedagem & HTTPS (Frontend + Backend, compartilhado)

### Opção A: Vercel + EC2 (recomendado)
- **Frontend (Vercel):** HTTPS automático. `NEXT_PUBLIC_CORE_API_URL` -> domínio do backend.
- **Backend/DB (EC2/DigitalOcean):** `docker-compose up -d`.

### Opção B: VPS única com reverse proxy (Caddy)
```caddyfile
xiaolee.io        { reverse_proxy localhost:3000 }
api.xiaolee.io    { reverse_proxy localhost:8000 }
```
```bash
XIAOLEE_ENV=production docker-compose -f docker-compose.yml up -d
```
Habilite **HSTS** no proxy (gate de segurança pendente).

---

## 5. Banco de Dados & Observabilidade (compartilhado)

Substitua os containers locais por serviços gerenciados:
- **AWS RDS** (PostgreSQL 16) — atualize `DATABASE_URL`
- **AWS ElastiCache** (Redis) — atualize `REDIS_URL`

```bash
cd backend && alembic upgrade head    # aplica schema incl. coluna multi-chain `chain`
```

Logs e métricas via Grafana (porta 3001) + Prometheus. Para Stellar, indexação por
Horizon `event_stream` (ADR-007 do RT).

---

## Checklist final antes de "dinheiro real"

- [ ] Auditoria externa concluída na(s) track(s) ativada(s) — **BLOQUEADOR**
- [ ] Admin migrado para multisig (Squads/Solana, multisig nativo/Stellar)
- [ ] Todos os secrets no vault; nenhum fail-open (confirmar 503 quando ausente)
- [ ] HTTPS + HSTS ativos
- [ ] Backup automático do DB gerenciado
- [ ] Monitor + alertas de incidente configurados
- [ ] Rollout gradual com TVL limitado (10% -> 50% -> 100%)

> Estado atual: a track Solana tem contrato (devnet, pré-auditoria); a track Stellar **não tem
> contrato Soroban escrito ainda**. Nenhuma das duas está liberada para mainnet com fundos reais
> até a auditoria externa. Ver `docs/MAINNET_READINESS.md`.
