# Onboarding — Jeiel (Agent Brain Lead)

> Você carrega **Agentic 30% + metade do Innovation (agent-to-agent)**. É a maior fatia de nota.
> Sua missão: o agente que **descobre creator → avalia → paga em USDC, sozinho, dentro de budget.**

## Leia, nesta ordem (não leia o resto)
1. `docs/ARC_LEPTON_ARCHITECTURE.md` — INTEIRO (foca L2 · Agent Orchestration)
2. `docs/team/WORKFLOW_SEMANA.md`
3. `backend/memory-bank/systemPatterns.md` — padrões de arquitetura/código (rápido, vale muito)
4. `backend/memory-bank/techContext.md` — stack técnica
5. `docs/ARCHITECTURE.md` — só pra entender o padrão (era Stellar, mas a estrutura vale)
6. `docs/API_REFERENCE.md` — endpoints de orchestration/x402
7. `AUDIT.md` — 23 findings de segurança já corrigidos (saber o que NÃO repetir)

> ⚠️ `systemPatterns/techContext/ARCHITECTURE` são era-Stellar: use pra entender *estrutura e
> padrões do código*, mas a verdade do sprint é o `ARC_LEPTON_ARCHITECTURE.md`.

## O que JÁ EXISTE e é seu ponto de partida (não reescreva)
- **`backend/claude_agent.py`** — `ClaudeAgentEngine`: loop nativo Anthropic, multi-step
  (chama modelo → executa tool → devolve resultado → repete até parar). Prompt caching pronto.
  Converte tools formato OpenAI → Anthropic (`openai_tools_to_anthropic`). **Este é o teu motor.**
- **`backend/server/orchestration/service.py`** — `OrchestrationService`: como tools são injetadas,
  como o wallet NUNCA é parâmetro do modelo (vem injetado pelo executor). Copia esse padrão.
- Hoje as tools são Stellar (`stellar_get_balance`, `stellar_swap_quote`). Você troca por tools de creator-pay.

## Sua entrega (as 4 tools novas — formato OpenAI, o engine converte)
```
discover_creators(criteria)        -> lista de candidatos
evaluate_creator(creator_id)       -> score contra critério da campanha (RFB-06)
check_budget()                     -> USDC restante na campanha
pay_creator_nanopayment(intent_id, to, amount_usdc) -> {tx, receipt_pqc}   # chama o rail do f0ntz
```
> `pay_creator_nanopayment` é a **costura Agent↔Chain** (congelada). Você chama, o f0ntz implementa
> o miolo on-chain. Combinem o contrato no D0 e NÃO mudem sem avisar.

## O loop autônomo (coração do Agentic 30%)
O agente deve, em uma única conversa, encadear: `discover → evaluate → check_budget → pay`
**sozinho**, decidindo quanto pagar e parando quando o budget acaba. Isso é "agentic" de verdade —
não é responder pergunta, é **executar uma campanha**. Use o `max_steps` do engine como trava de segurança.

## "Sem ponto único de falha" — a versão honesta (faça ISSO, não HA de produção)
1. Todo pagamento tem `intent_id`; a tabela `UsedPayment` (já existe) impede gasto duplo.
2. Registre a **intenção ANTES de executar** (intent log durável) → no restart, recupera de onde parou.
3. Se a chain cai, **enfileira e responde "pendente"**, não trava o loop.
4. Estado no DB, nunca em memória → qualquer worker assume.

## Sua semana (resumo)
- **D2 dom21:** stub das 4 tools + plugar no `ClaudeAgentEngine` (mock o pay_ no início)
- **D3 seg22:** loop descobrir→avaliar→pagar, 1ª versão real
- **D4 ter23:** loop a2a autônomo dentro de budget
- **D5 qua24:** polir, casos de erro, intent log durável
- **D6 qui25:** ajudar roteiro do vídeo (a parte agêntica é o que impressiona o juiz)

## Stretch (Innovation, só se sobrar): agent-to-agent
Dois agentes negociando/pagando entre si via ERC-8004 (identidade on-chain). Só DEPOIS do core verde.
