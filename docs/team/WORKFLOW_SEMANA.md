# Workflow da Semana — Sprint Lepton (Arc)

> **Janela:** 15–29 jun · **Submissão:** 29 jun · **Time:** f0ntz · Jeiel · Mari
> **Submissão exige:** GitHub público + vídeo <3min + link live + métricas de traction.

## Como a gente trabalha (regras do sprint)

- **Trunk-based.** Branch curta a partir de `develop`, merge no mesmo dia. **Sem PR gatekeeping**
  — revisão é no sync, confiança 100%. Nada de branch viva por 3 dias.
- **Feature flags** pra tudo que pode quebrar a demo (ex: CCTP, ZK). Core sempre verde.
- **Sync 2x/dia, 15 min** (manhã + noite). Pauta fixa: *o que travou / o que merge hoje / a costura tá verde?*
- **Integração fim-a-fim TODO fim de dia.** Staging na testnet **Canteen** sempre verde. Se quebrou,
  a prioridade nº1 do dia seguinte é consertar antes de qualquer feature nova.
- **As 3 costuras de API estão CONGELADAS** (ver abaixo). Mudou costura? Avisa os outros 2 ANTES.

## As 3 costuras (interface congelada — ninguém muda sozinho)

1. **Agent ↔ Chain** (Jeiel↔f0ntz): `pay_creator_nanopayment(intent_id, to, amount_usdc) -> {tx, receipt_pqc}`
2. **Chain ↔ Traction** (f0ntz↔Mari): evento `payment_settled{intent_id, amount, ts, tx}`
3. **Agent ↔ Frontend** (Jeiel↔Mari): stream do loop (descobriu/avaliou/pagou) pro chat/dashboard

## Divisão por dono (quem carrega qual nota)

| Pessoa | Papel | Carrega |
|---|---|---|
| **f0ntz** | Chain & Trust Lead | Rail USDC/x402, CCTP, PQC, ERC-8004, repo/vídeo → **Circle 20% + ½ Innovation** |
| **Jeiel** | Agent Brain Lead | Loop autônomo descobrir→avaliar→pagar, a2a, orquestração → **Agentic 30% + ½ Innovation** |
| **Mari** | Traction & Creator Lead | Onboarding 0-fricção, RFB-06, dashboard USDC ao vivo, métricas → **Traction 30%** |

## Cronograma dia-a-dia (D = dia do sprint)

| Dia | Data | f0ntz (Chain/Trust) | Jeiel (Agent) | Mari (Traction) |
|---|---|---|---|---|
| D2 | **dom 21** | `arc_adapter.py` + **1º nanopagamento USDC e2e** na Canteen | stub das 4 tools do agente, plugar no `ClaudeAgentEngine` | esqueleto do dashboard + ler GTM/Instawards |
| D3 | seg 22 | CCTP inflow + splits | loop descobrir→avaliar→pagar (1ª versão) | fluxo onboarding creator (RFB-06) |
| D4 | ter 23 | suporte às costuras, hardening do rail | loop a2a autônomo dentro de budget | dashboard USDC tempo real + 1ºs creators reais |
| D5 | qua 24 | PQC (recibo ML-DSA) + ERC-8004 · **INTEGRATION FREEZE** | polir loop, casos de erro | usuários reais pagando · **decisão ZK: entra ou corta** |
| D6 | qui 25 | gravar/montar vídeo <3min + repo público | ajudar roteiro do vídeo (parte agêntica) | métricas pro vídeo + screenshots |
| D7 | 26–28 | buffer + traction (USDC fluindo de verdade na janela) | buffer + bugs | empurrar traction real |
| — | **29** | **SUBMIT** | — | — |

## Definição de "pronto" (o que conta como entregue)
Nada conta até **passar na integração e2e do fim do dia, na Canteen.** Código que não roda no
staging compartilhado não existe. Demo > código bonito.

## Onde travar dúvida
- Costura/chain → f0ntz
- Lógica do agente/tools → Jeiel
- Creator/produto/métrica → Mari
- Arquitetura geral → `docs/ARC_LEPTON_ARCHITECTURE.md`
