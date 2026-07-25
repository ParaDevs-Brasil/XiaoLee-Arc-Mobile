# Posicionamento XiaoLee — Lepton Agents Hackathon (Arc/Circle)

**Pra:** time XiaoLee (BrazillianCare, Jeiel, Mari)
**De:** f0ntz
**Data:** 23/06/2026 · **Submissão:** 29/06/2026 · **Freeze:** 24/06/2026
**Status:** D4. 1 dia útil de feature antes do freeze.

> Documento único de posicionamento. Tudo que a gente construir, demonstrar e narrar serve pra provar **uma frase**. Se um recurso não prova essa frase, ele não entra nos 3 minutos de vídeo.

---

## A frase (statement)

> **XiaoLee é o agente que paga creators "pela fração" — nanopagamentos USDC em tempo real, conforme o trabalho acontece, sem ninguém apertar botão.**

Decora isso. É a abertura do pitch, a primeira linha do README e a tese do vídeo.

---

## Sequência: posicionamento decide o técnico, não o contrário

Não dá pra terminar "tudo" em 1 dia útil. O posicionamento é o filtro que diz qual fatia do técnico é obrigatória e qual é "se sobrar":

1. **Posicionamento (este doc)** → define a única afirmação que a demo precisa provar.
2. **Técnico = só o e2e que prova a afirmação** → esse é o gate, verde no freeze (24/jun).
3. **PQC / CCTP / a2a = munição de Innovation** → entram só se o gate já estiver verde.

---

## A categoria que a gente reivindica

Não somos "mais uma plataforma de creator economy" (commodity, banca não pontua). Somos:

> **Autonomous creator payouts** — pagamento de creator que um *agente* executa sozinho, na fração, em tempo real — em vez de um financeiro processando lote no fim do mês.

Cobre 3 RFBs alvo de uma vez:
- **RFB-06 Creator Monetization** (o quê) — foco primário do round
- **RFB-03 Agent-to-Agent** (como — o agente paga)
- **RFB-02 Selling Agent Services** (o XiaoLee é um serviço-agente contratável)

---

## ICP + dor

- **Quem:** marca/host rodando campanha com muitos micro-creators.
- **Dor hoje:** pagamento é em lote, atrasado, com mínimo de saque, taxa de bridge e fricção de chain. Micro-trabalho (um post, uma fração de engajamento) **não é pagável** porque o custo da transação > o valor pago.
- **A virada:** nanopagamento só vira possível quando o gas é desprezível e nativo em USDC.

---

## Why now — e por que no Arc (é onde ganhamos os 20% de Circle Tools)

Argumento mais forte e o que justifica não sermos "mais um app de pagamento":

- **Gas nativo em USDC + sub-500ms** → nanopagamento vira economicamente viável pela primeira vez. Pagar US$ 0,02 pela fração não fecha se o gas come tudo.
- **x402** → o agente paga via HTTP, na hora, sem checkout.
- **CCTP** → traz USDC de qualquer chain pro Arc; a marca financia de onde já tem caixa.
- **Unified Balance / App Kit** → a parte que a gente mostra rodando.

Mensagem central: **"Esse produto era impossível antes do Arc. O Arc é o que destrava o nanopagamento de creator."**

---

## Diferenciação (contra o que vão comparar a gente)

| Comparado a… | Nosso corte |
|---|---|
| Pagamento de creator tradicional (lote, mensal) | Tempo real, na fração, autônomo — sem financeiro no meio. |
| XiaoLee na Solana (versão anterior) | Aqui o gas USDC nativo + x402 viabilizam a *micro*-fração; na Solana era pagamento, não nanopagamento. |
| Outro agente de pagamento genérico | XiaoLee **decide quem merece e quanto** dentro de budget (Agentic) e já tem campanhas + persona maduras. |

---

## Hierarquia de mensagem (mapeada aos pesos da banca)

Sempre nesta ordem — abrir pela autonomia, fechar pela inovação:

1. **Autonomia** — *Agentic 30%* — "o agente descobre, avalia e paga sozinho, dentro do budget". Mostrar o loop decidindo (dono: Jeiel).
2. **Dinheiro real fluindo** — *Traction 30%* — "X usuários, Y USDC pago na janela". Número real na tela (dona: Mari).
3. **Nativo do Arc** — *Circle Tools 20%* — App Kit / x402 / Unified Balance visíveis em ação (dono: f0ntz).
4. **Recibo assinado + identidade de agente** — *Innovation 20%* — PQC (ML-DSA) + ERC-8004 — **só se o gate estiver verde**. É o fecho, não a abertura.

---

## O gate técnico que esse posicionamento define

E2e mínimo que tem que estar verde no freeze (24/jun) — é o que prova a frase:

> marca financia budget em USDC → agente XiaoLee detecta trabalho do creator → decide pagar a fração dentro do budget → x402 dispara nanopagamento USDC no Arc → creator recebe na hora → dashboard mostra o valor.

- Se esse fluxo roda com **um usuário real**, temos produto e tese provável.
- PQC, CCTP e a2a são adornos desse fluxo. Nenhum adorno salva se o fluxo acima não roda.

---

## Os 3 riscos que matam (e a regra)

1. **Escopo > tempo.** PQC + CCTP + a2a + traction num dia só é inflado. **Corta PQC/CCTP pra "se sobrar".** Valem 20%; não arrisca os 60% de Agentic+Traction por eles.
2. **Traction fake.** Demo semeada não conta — a banca mede USDC real fluindo na janela. Precisa de gente real mandando USDC antes de 29.
3. **Autonomia não demonstrada.** Se o vídeo não mostrar o agente decidindo e pagando sozinho, Agentic 30% despenca mesmo com o código pronto. A narrativa do vídeo é parte do produto.

---

## Regra de ouro do time até 29/jun

Toda decisão de escopo passa por: **"isso prova a frase única e move Agentic ou Traction?"** Se não, é "se sobrar tempo".
