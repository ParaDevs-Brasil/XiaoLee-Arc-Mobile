# XiaoLee on Arc — Arquitetura Lepton Agents Hackathon

> **Janela:** 15–29 jun 2026 · **Hoje:** 20 jun (D1) · **Submissão:** 29 jun
> **Régua de nota:** Agentic 30% · Traction 30% (USDC fluindo de verdade) · Circle Tools 20% · Innovation 20%
> **Princípio:** toda peça aqui cai em uma das 4 notas. Se não cai, é vaidade técnica e fica fora.

---

## Tese

Agente conversacional (XiaoLee) que **descobre creators, avalia, e paga por fração via nanopagamento
USDC** no Arc — autônomo, dentro de budget, com recibo pós-quântico verificável. Trilho:
x402 (HTTP 402) → USDC nativo no Arc → CCTP para inflow cross-chain.

---

## Mapa de reúso (o que NÃO se reescreve)

| Componente existente | Status | Reúso no Arc |
|---|---|---|
| `backend/claude_agent.py` (loop agêntico nativo Anthropic) | ✅ maduro | **100%** — base do loop autônomo |
| `backend/server/routes/x402_routes.py` (protocolo 402 + anti-replay) | ✅ auditado | **Esqueleto 100%**, backend de chain troca |
| `UsedPayment` (claim atômico anti-replay, fix TOCTOU SEC-001) | ✅ auditado | **100%** — idempotência de pagamento |
| `OrchestrationService` (tools injetadas, wallet nunca é param) | ✅ | padrão reaproveita; tools novas |
| `metrics.py` (Prometheus) | ✅ | base do dashboard de Traction |
| `stellar_adapter.py` (`verify_payment`) | ✅ | **molde** para `arc_adapter.py` |

---

## Arquitetura em camadas

```
┌──────────────────────────────────────────────────────────────┐
│ L4 · TRACTION & OBSERVABILITY        (Traction 30%)           │
│   metrics.py (existe) + dashboard USDC-flow tempo real (Mari) │
├──────────────────────────────────────────────────────────────┤
│ L3 · TRUST & PROOF                   (Innovation 20%)         │
│   PQC: recibo assinado ML-DSA  ·  ERC-8004 agent identity     │
│   [STRETCH] 1 prova ZK atrás de flag — só depois do core      │
├──────────────────────────────────────────────────────────────┤
│ L2 · AGENT ORCHESTRATION             (Agentic 30%)            │
│   ClaudeAgentEngine (existe) → loop descobrir→avaliar→pagar   │
│   "sem SPOF" = idempotência + intent log durável + retry      │
├──────────────────────────────────────────────────────────────┤
│ L1 · PAYMENT RAIL  ("os rails")      (Traction + Circle 20%)  │
│   x402 HTTP 402 (esqueleto existe) → USDC no Arc (gas USDC)   │
│   CCTP inflow cross-chain · anti-replay UsedPayment (existe)  │
├──────────────────────────────────────────────────────────────┤
│ L0 · IDENTITY & WALLET                                        │
│   EVM wallet via Circle App Kit · agent key (PQC-anchored)    │
└──────────────────────────────────────────────────────────────┘
```

### L0 — Identidade & Wallet
- Usuário/agente: wallet EVM via **Circle App Kit** (Send/Bridge/Swap/Unified Balance).
- Chave do agente ancorada por **ERC-8004** (identidade on-chain do agente) → entra em Innovation.
- Substitui SEP-10/Freighter (Stellar) por fluxo EVM. Não-custodial mantido.

### L1 — Payment Rail (PRIORIDADE MÁXIMA — é Traction + Circle Tools)
- **`arc_adapter.py`** (novo, espelha `stellar_adapter.py`): `verify_payment(tx, dest, min_usdc)`
  contra RPC da testnet **Canteen**.
- **x402**: reaproveita o fluxo 402 inteiro de `x402_routes.py`. Troca só:
  - asset `XLM` → **`USDC`**
  - verificação Horizon → **RPC Arc**
  - construção XDR (`/payment-tx`) → tx EVM via App Kit / viem
- **Anti-replay**: `UsedPayment` reaproveita 100% (claim atômico antes do orchestrator).
- **CCTP**: trazer USDC de outra chain pro Arc. **Diferencial, não pré-requisito** — entra D2/D3.

### L2 — Agent Orchestration (Agentic 30%)
- `ClaudeAgentEngine` (existe) roda o loop multi-step.
- **Tools novas** (formato OpenAI, convertidas p/ Anthropic pelo engine):
  - `discover_creators(criteria)` — descobre candidatos
  - `evaluate_creator(id)` — pontua contra RFB-06
  - `check_budget()` — saldo restante da campanha
  - `pay_creator_nanopayment(id, amount_usdc)` — dispara o rail L1
- **"Sem SPOF" — a versão honesta de hackathon** (NÃO multi-região/leader-election):
  1. **Idempotência**: todo pagamento tem `intent_id`; `UsedPayment` impede duplo gasto.
  2. **Intent log durável**: registra intenção ANTES de executar; recupera no restart.
  3. **Degradação graciosa**: se chain cai, agente enfileira e responde "pendente", não trava.
  4. **Stateless workers**: estado no DB, não em memória → qualquer worker assume.

### L3 — Trust & Proof (Innovation 20%)
- **PQC (escopo cirúrgico):** assinar o **recibo do pagamento** com **ML-DSA**.
  Não reescreve protocolo, não toca consenso. Só: pagamento confirmado → recibo assinado PQC →
  verificável por terceiro. Diferencial limpo e demonstrável.
- **ERC-8004:** identidade do agente on-chain → "agent-to-agent" verificável.
- **[STRETCH] ZK — UMA prova só, atrás de feature flag, SÓ depois do core fluir:**
  candidata mais forte = provar que o creator atingiu o critério da campanha (ex: threshold de
  engajamento) **sem revelar o dado bruto**. Se D5 chegar e o core não estiver verde, **corta sem dó**.

### L4 — Traction & Observability (Traction 30%)
- `metrics.py` (existe) + métricas USDC-flow: total pago, nº pagamentos, latência, creators ativos.
- Dashboard tempo real (Mari) mostrando **USDC saindo ao vivo** — é a prova que o juiz quer ver.

---

## As 3 costuras de API (congelar D0 — evita SPOF de integração)

1. **Agent ↔ Chain**: `pay_creator_nanopayment(intent_id, to, amount_usdc) -> {tx, receipt_pqc}`
2. **Chain ↔ Traction**: evento `payment_settled{intent_id, amount, ts, tx}` → métricas
3. **Agent ↔ Frontend**: stream do loop (descobriu/avaliou/pagou) pro chat

---

## Triagem brutal (o que ENTRA vs o que é ARMADILHA)

| Item | Decisão | Razão |
|---|---|---|
| x402 USDC no Arc | ✅ CORE | Traction + Circle, é o produto |
| Loop agêntico de pagamento | ✅ CORE | Agentic 30%, já tem o engine |
| Recibo PQC (ML-DSA) | ✅ INNOVATION | escopo cirúrgico, demonstrável |
| ERC-8004 identidade | ✅ INNOVATION | a2a verificável |
| CCTP | 🟡 D2/D3 | diferencial, não bloqueia demo |
| Idempotência/intent log | ✅ CORE | é o "sem SPOF" real e barato |
| **ZK multicamadas** | 🔴 CORTA | não move nota, queima 9 dias, sem demo |
| ZK 1 prova (flag) | 🟡 STRETCH | só se core verde em D5 |
| HA multi-região / leader-election | 🔴 FORA | infra de produção, não de hackathon |

---

## Cronograma (do plano, amarrado nas camadas)

- **D0 sex19** — setup + congelar 3 costuras
- **D1 sáb20** — *(hoje)* mapa de reúso ✅ + esta arquitetura
- **D2 dom21** — L1: `arc_adapter.py` + 1º nanopagamento USDC e2e na Canteen
- **D3 seg22** — L1 CCTP + splits · L2 tools de creator-pay
- **D4 ter23** — L2 loop autônomo a2a · L4 dashboard
- **D5 qua24** — L3 PQC + ERC-8004 · usuários reais · **integration freeze** · decisão ZK (entra/corta)
- **D6 qui25** — vídeo (<3min) + repo público
- **D7 26–28** — buffer + traction (USDC fluindo de verdade na janela)
- **29** — submit
