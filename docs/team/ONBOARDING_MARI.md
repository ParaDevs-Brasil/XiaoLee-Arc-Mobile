# Onboarding — Mari (Traction & Creator Lead)

> Você carrega **Traction 30%** — empatado como a maior nota. O juiz quer ver **USDC fluindo de
> verdade na janela do hackathon.** Sua missão: creators reais entrando sem fricção e um dashboard
> que mostra o dinheiro saindo AO VIVO.

## Leia, nesta ordem (não leia o resto)
1. `docs/ARC_LEPTON_ARCHITECTURE.md` — INTEIRO (foca L4 · Traction & Observability)
2. `docs/team/WORKFLOW_SEMANA.md`
3. `backend/memory-bank/productContext.md` — contexto de produto (rápido, bom começo)
4. `docs/GTM_XIAOLEE.md` — narrativa de produto e de creators
5. `docs/INSTAWARDS_DRAFT.md` + `Instawards - Bounties (1).docx` — modelo de campanha (base do RFB-06)
6. `docs/DESIGN_SYSTEM.md` — tokens visuais pro dashboard
7. (pro vídeo) `docs/XIAOLEE_INVESTOR_TECH_DOC.md` — visão/pitch

> ⚠️ `productContext` é era-Stellar: use pra entender *o produto e o creator*, mas a verdade do
> sprint (USDC no Arc) é o `ARC_LEPTON_ARCHITECTURE.md`.

## RFB-06 (Creator Monetization) é o nosso foco primário
O round premia agentes que **monetizam creators**. Seu fluxo: creator entra → agente descobre/avalia →
paga em USDC por fração. Você desenha a ponta do creator: **onboarding 0-fricção** (menos cliques
possível até receber o 1º USDC) e o **dashboard que prova a traction**.

## O que JÁ EXISTE e é seu ponto de partida
- **`backend/server/metrics.py`** — Prometheus já instrumentado (`record_http_request`,
  `record_campaign_event`, `render_prometheus_metrics`). É a base das suas métricas de USDC-flow.
- Frontend: Next.js (export estático). Design tokens em `docs/DESIGN_SYSTEM.md`.

## Sua entrega — o dashboard de Traction (é o que o juiz vê)
Mostrar, em tempo real:
- **Total USDC pago** (o número que importa)
- **Nº de nanopagamentos** + **creators ativos**
- **Latência média** do pagamento (sub-500ms é o nosso diferencial — mostre isso)
- Feed ao vivo: "Agente pagou 0.10 USDC para @creator · há 3s"

> Os dados vêm da **costura Chain↔Traction** (congelada): evento
> `payment_settled{intent_id, amount, ts, tx}` que o f0ntz emite. Combinem o formato no D0.

## Onboarding de creator (0-fricção)
Cada clique a mais é creator perdido. Meta: do "cheguei" até "elegível a receber USDC" no menor
número de passos. Wallet via Circle App Kit (o f0ntz te passa o fluxo). Documente os passos pra
gente reusar no vídeo.

## Traction REAL > traction de mentira
A nota é medida **na janela do hackathon**. Não adianta número inflado — tem que ser USDC saindo
de verdade na Canteen. A partir do D4, sua prioridade é **trazer gente real pra usar** (mesmo que
poucos) e capturar tudo (prints, métricas) pro vídeo.

## Sua semana (resumo)
- **D2 dom21:** esqueleto do dashboard + ler GTM/Instawards
- **D3 seg22:** fluxo de onboarding creator (RFB-06)
- **D4 ter23:** dashboard USDC tempo real + primeiros creators reais
- **D5 qua24:** usuários reais pagando, capturar métricas
- **D6 qui25:** métricas + screenshots pro vídeo (você tem o material que vende a traction)
