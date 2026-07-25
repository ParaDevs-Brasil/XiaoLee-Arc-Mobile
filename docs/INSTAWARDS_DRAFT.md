# XiaoLee — Instawards Draft
## AI Conversational DeFi Layer on Stellar: x402 Micropayments + On-Chain Campaign Rewards


---

## 1. Project & Team Information

| Field | Value |
|---|---|
| **Project Name** | XiaoLee |
| **Team Name** | XiaoLee / ParaDevs |
| **Primary Contact (Name + Email)** | [PREENCHER — nome + email do responsável] |
| **Ambassador Chapter** | Brazil |
| **Ambassador Chapter Lead** | Caio Mattos |
| **Date Submitted** | 2026-05-22 |
| **Suggested Sprint Start Date** | 2026-06-01 |

---

## 2. Instawards Overview & Intent

### 2.1 Instawards Purpose (for Builder Context)

This Instaward funds a focused 30-day engineering sprint to deliver two production-ready Stellar integrations into XiaoLee, an AI conversational DeFi layer already live on Railway with 74 security tests passing and 11 development sprints completed on Solana:

1. **x402 micropayments** — HTTP-native XLM/USDC payments per AI query, live on Stellar Testnet
2. **On-chain campaign reward settlement** — Soroban `xiaolee_core` contract handling $XLEE distribution, verifiable on Stellar Testnet

XiaoLee already has a working backend (FastAPI, 65+ tests), frontend (Next.js 15), campaign engine, and Stellar auth (SEP-10). The missing piece is connecting the AI interface to Stellar's settlement layer — which is exactly what this Instaward delivers.

---

## 3. Problem Statement & Objective

### Problem Being Addressed

Creator campaign platforms face a fundamental trust gap: brands pay creators based on social engagement, but there is no trustless, auditable settlement layer. Today's process relies on manual verification, off-chain records, and direct wallet transfers — creating disputes, delayed payments, and zero on-chain auditability.

Simultaneously, AI-native products that charge per query lack a frictionless micropayment rail. Credit cards have high minimums and fees. Subscriptions don't match usage-based pricing. There is no HTTP-native payment primitive for AI queries — until x402 on Stellar.

XiaoLee addresses both problems: it is the interface between a user's natural language request and Stellar's settlement infrastructure. But without the Soroban contract live and x402 integrated, the product cannot charge for queries or settle campaign rewards on-chain.

**What is currently blocking progress:**
- Soroban `xiaolee_core` is 60% implemented — the contract logic is written but not deployed on Testnet
- x402 endpoint exists in the codebase but is not connected to real Stellar payment verification
- Campaign claim flow writes to PostgreSQL but does not invoke the Soroban contract

**Why this is worth solving now:**
- The 37 Graus / SDF program creates a direct path to EtherFuse (on/off ramp), the Stellar DEX, and the Brazilian market (150M Pix users)
- XiaoLee is the only conversational DeFi interface with Pix-native onboarding positioned for the LATAM creator economy
- Both deliverables are 80% done — this Instaward closes the last 20% needed for a live Testnet demo

### Objective

At the end of 30 days, XiaoLee will have:
1. A live Soroban `xiaolee_core` contract on Stellar Testnet handling $XLEE reward distribution with verifiable on-chain transaction hashes
2. A working x402 micropayment endpoint accepting XLM/USDC per AI query with real Stellar transaction verification

---

## 4. Scope of Work (30-Day Deliverables)

### 4.1 In-Scope Deliverables

| Deliverable | Description | Why This Matters |
|---|---|---|
| **Deliverable 1** — Soroban `xiaolee_core` on Testnet | Deploy the `xiaolee_core` Soroban contract on Stellar Testnet. Implement `initialize`, `initialize_user`, `record_reward`, `pause_protocol`. Emit `$XLEE` via SAC to campaign participants. Wire backend `StellarAdapter.record_reward()` to invoke the contract on every verified campaign claim. | Trustless, auditable campaign reward settlement. Anyone can verify on-chain that $XLEE was distributed correctly — no dependency on XiaoLee's database. |
| **Deliverable 2** — x402 Micropayments Live | Connect `/v1/ai/query` to real Stellar payment verification: accept `X-Payment` header with `tx_hash`, verify on Horizon that the transaction sent XLM/USDC to XiaoLee's wallet, use `UsedPayment` anti-replay table (already implemented), return AI response only after on-chain confirmation. Includes `GET /v1/ai/query/payment-info` returning current price and destination wallet. | XiaoLee becomes the first AI agent that charges per query via HTTP-native Stellar micropayments. Demonstrates the x402 protocol as a sustainable AI monetization model on Stellar. |
| **Deliverable 3** *(optional)* — Demo + Documentation | Demo video (< 3 min) showing: (1) user connects Freighter, (2) joins campaign, (3) completes tasks, (4) $XLEE lands on Testnet with transaction hash, (5) pays for AI query via x402 XLM. README updated with Stellar-specific setup. Architecture diagram showing full flow from Freighter → SEP-10 → StellarAdapter → Soroban → SAC. | Verifiable evidence for SCF/Instawards reviewers. Clear entry point for ecosystem builders who want to extend XiaoLee or fork the pattern. |

### Out-of-Scope (Explicitly Not Included)

- Mainnet deployment (planned for 37 Graus Phase 3)
- EtherFuse Pix on/off ramp integration (Phase 2 of 37 Graus roadmap)
- Aquarius AMM integration
- Mobile app
- Production SRE / advanced alerting
- Cross-chain integrations

### 4.2 Budget Request

| Item | Amount | Rationale |
|---|---|---|
| Engineering — Soroban contract + backend wiring | $2,500 | Finalize `xiaolee_core` Rust contract, deploy on Testnet, wire `StellarAdapter.record_reward()` to invoke the contract, integration tests |
| Engineering — x402 payment verification | $1,500 | Connect `/v1/ai/query` to Horizon verification, payment info endpoint, anti-replay integration, load tests |
| Documentation + demo production | $500 | Architecture doc, demo video recording and editing, README update |
| Buffer / infra (Railway, Testnet ops) | $500 | Testnet account funding, Railway hosting during sprint, tooling |
| **Total** | **$5,000** | Within Instawards cap |

---

## 5. 30-Day Execution Plan & Timeline

### 5.1 Weekly Breakdown

| Week | Planned Work | Expected Output |
|---|---|---|
| **Week 1** | Finalize Soroban contract: `initialize`, `initialize_user`, `record_reward` with `require_auth()`, `pause_protocol`. Local tests with `soroban-cli`. Emit `$XLEE` via SAC mock. | Soroban contract compiles and passes local unit tests. `soroban_core` binary ready for Testnet deploy. |
| **Week 2** | Deploy `xiaolee_core` on Stellar Testnet. Emit `$XLEE` asset, deploy SAC. Wire `StellarAdapter.record_reward()` to invoke contract. Test full campaign → claim → on-chain flow end-to-end. | First real `record_reward` transaction on Stellar Testnet with verifiable tx hash. Campaign claim triggers Soroban invocation. |
| **Week 3** | Connect x402 endpoint to real Horizon verification. Implement `GET /v1/ai/query/payment-info`. Run anti-replay + concurrency tests. Load test: 50 concurrent x402 requests, p95 < 500ms. | x402 endpoint live on Testnet: pays XLM → Horizon verifies → AI responds. Anti-replay confirmed via `UsedPayment` table. |
| **Week 4** | Record demo video. Update README with Stellar setup instructions. Write architecture doc. Final security review. Submit evidence. | Demo video, updated docs, GitHub commit history as evidence trail. |

---

## 6. Evidence of Completion (Required)

### 6.1 Planned Evidence to Be Submitted

| Deliverable | Evidence Type | Description |
|---|---|---|
| **Deliverable 1** — Soroban on Testnet | GitHub repo + Testnet contract ID + transaction hashes | Contract source code in `/solana-program/xiaolee_core` (Rust/Soroban). Testnet contract ID (`C...`). At least 3 `record_reward` transaction hashes on Stellar Testnet Explorer showing $XLEE transferred to participant wallets after campaign claim. |
| **Deliverable 2** — x402 Live | API endpoint demo + Horizon tx hash + curl output | `curl` command showing `X-Payment: {"tx_hash": "..."}` accepted by `/v1/ai/query`, Horizon explorer link proving XLM was received by XiaoLee wallet, AI response returned after payment. |
| **Deliverable 3** — Demo + Docs | Video link + GitHub PR | Video (< 3 min) on YouTube/Loom showing Freighter connect → campaign join → claim with Testnet tx hash → x402 payment → AI response. GitHub PR with updated README and architecture diagram. |

### 6.2 Evidence Verification Checklist (For Ambassador Use)

| Deliverable | Evidence Present | Evidence Partial | Evidence Missing | Comments |
|---|---|---|---|---|
| Soroban contract deployed | ☐ | ☐ | ☐ | Contract ID + tx hashes visible on Stellar Expert Testnet |
| record_reward emits $XLEE | ☐ | ☐ | ☐ | Token balance change verifiable in Freighter or Stellar Expert |
| x402 endpoint accepts XLM | ☐ | ☐ | ☐ | Horizon tx hash + curl output showing 200 OK after payment |
| Anti-replay working | ☐ | ☐ | ☐ | Second request with same tx_hash returns 409 |
| Demo video | ☐ | ☐ | ☐ | Full flow from Freighter connect to AI response via x402 |

---

## 7. Next-Step Alignment

### 7.1 Anticipated Next Step After Completion

**x Apply to SCF Build Award**

After this Instaward, XiaoLee will have:
- A live Soroban contract with on-chain reward distribution
- A working x402 micropayment model generating revenue per AI query
- Real Testnet traction (campaign completions, swap volume, x402 payments)

The SCF Build Award application will focus on:
- EtherFuse integration (Pix ↔ Stellar stablecoins — Phase 2 of 37 Graus roadmap)
- Mainnet deploy of `xiaolee_core`
- GTM: 3 active LATAM creators, 1,000 users, 50 Pix transactions

---

## 8. Instawards Constraints Acknowledgement

By submitting this SOW, the Builder acknowledges:

- **x** This scope will be completed within 30 days or less
- **x** Instawards support execution, not open-ended exploration
- **x** A project may receive no more than two follow-on Instawards
- **x** Each Instaward is capped at $5,000
- **x** Total Instawards funding may not exceed $15,000

---

## 9. Submission Confirmation

Once finalized, this Statement of Work will be submitted by the Ambassador Chapter Lead via the Instawards Airtable submission form for review and approval.

---

## Apêndice — Contexto do Projeto (para referência interna)

### O que já está construído (não precisa de financiamento)

| Componente | Status |
|---|---|
| Backend FastAPI (Python 3.12) | ✅ 100% — 65+ testes, CI verde |
| Frontend Next.js 15 (TypeScript) | ✅ 100% — Deploy Railway ativo |
| SEP-10 auth (Freighter + JWT) | ✅ 100% — Testado com stellar-sdk |
| Campaign engine (join/verify/claim) | ✅ 100% — PostgreSQL + Alembic |
| Anti-replay x402 (UsedPayment table) | ✅ 100% — TOCTOU-safe via db.flush() |
| HMAC webhooks (Helius, Telegram, X) | ✅ 100% — compare_digest, fail-closed |
| Observabilidade (Prometheus + Grafana) | ✅ 100% — 8 painéis |
| Auditoria de segurança (23 CVEs) | ✅ 100% — Sprint 2026-05 concluída |
| Soroban `xiaolee_core` Rust | 🟡 60% — Lógica escrita, deploy pendente |
| x402 payment verification (Horizon) | 🟡 70% — Endpoint existe, verificação real pendente |
| StellarAdapter.record_reward() | 🟡 50% — Interface definida, invocação Soroban pendente |

### Por que Stellar / Por que agora

- **EtherFuse** (parceiro oficial 37 Graus) = acesso direto ao rail Pix ↔ Stellar para 150M usuários brasileiros
- **x402** = único protocolo de micropagamento HTTP-nativo para AI queries — XiaoLee é caso de uso ideal
- **Soroban** = auditabilidade on-chain para campanhas — diferencial competitivo vs. qualquer plataforma de creator marketing centralizada
- **37 Graus** = programa SDF com $20k em prêmios, mentoria direta, residência Rio 08–11/06 — janela estratégica única
