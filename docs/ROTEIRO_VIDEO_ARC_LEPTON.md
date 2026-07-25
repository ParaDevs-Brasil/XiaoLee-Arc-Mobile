# Roteiro do Vídeo — XiaoLee · Lepton Agents Hackathon (Arc/Circle)

**Pra:** time XiaoLee (BrazillianCare, Jeiel, Mari)
**De:** f0ntz
**Data:** 23/06/2026 · **Submissão:** 29/06/2026
**Formato exigido:** vídeo < 3min (180s). Julgamento assíncrono.
**Base:** [POSICIONAMENTO_ARC_LEPTON.md](./POSICIONAMENTO_ARC_LEPTON.md) — este roteiro prova a frase única daquele doc.

> Regra: cada segundo serve a um dos 4 pesos da banca. Se uma cena não move Agentic / Traction / Circle Tools / Innovation, ela sai. Tudo abaixo soma 180s.

---

## Mapa de pesos → tempo de tela

A banca pesa: **Agentic 30% · Traction 30% · Circle Tools 20% · Innovation 20%.** O vídeo aloca tempo proporcional:

| Bloco | Peso que serve | Tempo |
|---|---|---|
| Abertura / frase | enquadra tudo | 0–15s |
| Autonomia do agente | Agentic 30% | 15–70s |
| Dinheiro real fluindo | Traction 30% | 70–120s |
| Nativo do Arc | Circle Tools 20% | 120–150s |
| Recibo assinado / identidade | Innovation 20% | 150–170s |
| Fecho | CTA + tese | 170–180s |

---

## Roteiro cena a cena

### Cena 1 — Abertura (0–15s) · enquadra tudo
- **Tela:** logo XiaoLee + a frase em texto grande.
- **Narração:** "Pagar creator hoje é lote, atrasado, com mínimo de saque. A fração de trabalho não é pagável — o gas come o valor. XiaoLee resolve isso: o agente paga creators pela fração, em USDC, em tempo real, sem ninguém apertar botão."
- **Por quê:** estabelece a dor e a tese nos primeiros 15s. Banca assíncrona decide nos primeiros segundos.

### Cena 2 — Autonomia do agente (15–70s) · Agentic 30%
- **Tela:** o loop rodando ao vivo — agente **descobre** trabalho do creator → **avalia** → **decide** pagar a fração dentro do budget. Mostrar a decisão acontecendo (log/UI), não um botão sendo clicado.
- **Narração:** "Quem decide quem recebe e quanto é o agente. Ele opera dentro de um budget definido pela marca, avalia o trabalho e dispara o pagamento sozinho."
- **Cuidado:** isto é 30% da nota. Tem que ficar **visível que é autônomo**. Nada de "aqui eu clico pra pagar".
- **Dono:** Jeiel.

### Cena 3 — Dinheiro real fluindo (70–120s) · Traction 30%
- **Tela:** dashboard de pagamentos em tempo real — **número real** de USDC pago + usuários reais na janela. Mostrar uma transação real liquidando ao vivo.
- **Narração:** "Não é mock. Na janela do hackathon, X usuários receberam Y USDC de verdade. Aqui está um pagamento liquidando agora."
- **Cuidado:** demo semeada não conta. Precisa de número real. Se o número for pequeno, mostre mesmo assim — real pequeno > fake grande.
- **Dona:** Mari.

### Cena 4 — Nativo do Arc (120–150s) · Circle Tools 20%
- **Tela:** x402 disparando o nanopagamento + App Kit / Unified Balance visível. Destacar gas nativo em USDC e a latência sub-500ms.
- **Narração:** "Isso era impossível antes do Arc. Gas nativo em USDC e liquidação sub-500ms são o que tornam o nanopagamento viável. x402 paga via HTTP, na hora; CCTP traz USDC de qualquer chain pro Arc."
- **Dono:** f0ntz.

### Cena 5 — Recibo assinado / identidade de agente (150–170s) · Innovation 20%
- **Tela:** recibo do pagamento assinado (PQC / ML-DSA) + identidade de agente ERC-8004.
- **Narração:** "Cada pagamento gera um recibo assinado com cripto pós-quântica e identidade de agente verificável on-chain."
- **Condicional:** só entra se o gate técnico estiver verde. Se PQC não ficou pronto, **corta esta cena** e estica Traction — não arrisca o vídeo por 20% que não rodou.

### Cena 6 — Fecho (170–180s) · CTA + tese
- **Tela:** frase única de novo + link live + GitHub.
- **Narração:** "XiaoLee: o agente que paga creators pela fração. Autônomo, em USDC, nativo do Arc. Link e código na descrição."

---

## Checklist de produção (dono: f0ntz, DevRel)

- [ ] Gravar com o e2e **real** rodando (gate do freeze 24/jun verde antes de gravar).
- [ ] Capturar a cena de Traction com número de verdade — gravar perto de 28/jun pra ter volume.
- [ ] Manter < 180s. Cronometrar. Se passar, cortar da cena 5 primeiro.
- [ ] Sem jargão sem prova: toda claim na tela tem que aparecer acontecendo.
- [ ] Áudio limpo, legível em mute (legenda nas claims principais — julgamento assíncrono pode rodar sem som).
- [ ] Link live + repo público funcionando no momento da submissão.

---

## Regra de corte (se faltar tempo de produção)

Ordem de prioridade do que mantém: **Cena 3 (Traction) > Cena 2 (Agentic) > Cena 4 (Arc) > Cena 5 (Innovation).**
Se precisar cortar, corta de baixo pra cima. Nunca sacrifica Traction ou Agentic — são 60% da nota.
