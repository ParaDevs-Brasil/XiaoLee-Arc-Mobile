# Backlog — Transferência USDC por handle via chat (Telegram/X), com pagamento pendente até onboarding

> **Status:** proposto em 2026-07-02, **adiado** — foco atual é fechar os bloqueantes do Lepton
> (#39, #40, #41, #43) e deixar o backend/infra 100% antes de puxar escopo novo.
> **Dono sugerido:** Gustavo (Circle Tools / backend) — tool nova no `ChatAgentEngine`.
> **Não é o mesmo fluxo do `ClaudeAgentEngine`** (pagamento automático de creators de campanha,
> `backend/claude_agent.py`) — isso aqui é o usuário pedindo por chat "manda X USDC pro @fulano".

---

## 1. A ideia

Deixar o agente de chat agêntico o bastante pra rodar por Telegram (webhook/poller já existe e já
opera) e, no futuro, por X — capturando o handle de quem interage. Quando alguém pede pra
transferir USDC para um handle:

- Se o destinatário **já tem conta/wallet Arc** → transfere na hora.
- Se **não tem ainda** → o valor fica reservado/pendente contra aquele handle, e é liberado de
  verdade assim que a pessoa criar conta (ou conectar wallet).

Sobre X: **decisão já tomada e documentada** (`README.md:166-168`) — outbound via X exige Twitter
API v2 DM (plano Basic, $100/mês) ou um scraper não-oficial que parou de funcionar em 2025. Pra
esta janela do hackathon, X fica de fora; Telegram é o canal operacional.

---

## 2. Por que não é só "plugar uma tool" — 3 furos reais encontrados no código

### 2.1 Telegram não captura o @handle, só o ID numérico
- `server/integrations/telegram_poller.py:75` — `user_id = str(message["from"]["id"])`.
- `database/repository.py:15-28` (`get_or_create_user`) — todo usuário vira
  `twitter_handle = f"telegram_{user_id}"` (handle sintético, não o `@username` real).
- `server/integrations/telegram_adapter.py:15` até extrai `username` do update do Telegram, mas
  **nada no pipeline persiste esse valor** hoje.
- **Consequência:** se alguém disser "manda 10 USDC pro @joaosilva" hoje, não existe forma de
  resolver esse handle pra ninguém — a base não sabe quem é "@joaosilva".

### 2.2 `PendingTransfer` já existe, mas está preso ao ledger interno simulado, não ao Arc real
- `database/models.py:113-122` — modelo `PendingTransfer` (`from_twitter_handle`,
  `recipient_twitter_handle`, `amount`, `status: pending|claimed`) já implementa exatamente o
  padrão "reserva contra handle, libera quando a conta existir".
- Mas `services/modern_transfer_service.py` move saldo via `_add_balance`/`_subtract_balance`
  contra a tabela `TokenBalance` — **contabilidade interna**, não custódia on-chain.
- O `ArcClient.send_usdc` (USDC de verdade na testnet) só é chamado hoje dentro do
  `pay_creator_nanopayment` (`ai/agents/creator_pay_tools.py:255-365`), que pertence ao fluxo de
  campanha, não ao chat.
- **Consequência:** não existe ponte hoje entre "reservei USDC pra esse handle" e "mandei USDC de
  verdade quando a conta for criada".

### 2.3 O agente de chat não tem nenhuma tool de transferência
- Tools expostas ao `ChatAgentEngine` hoje: só `stellar_get_balance` e `stellar_swap_quote`
  (`server/orchestration/service.py:26-53`, `STELLAR_AGENT_TOOLS`).
- Nem transferência Stellar nem Arc/Circle estão disponíveis nesse loop — o pivô pra Arc só tocou
  o motor de pagamento de campanha (`ClaudeAgentEngine`), não o agente conversacional
  (`ChatAgentEngine`, `backend/chat_agent.py`).

---

## 3. Escopo mínimo recomendado (quando for retomado)

1. **Capturar e persistir o `username` do Telegram** no `get_or_create_user` — resolve o furo 2.1.
2. **Nova tool `arc_transfer_usdc`** no `ChatAgentEngine`:
   - destino com wallet Arc já registrada → chama `arc_client.send_usdc` direto.
   - destino sem wallet → cria um registro pendente (variante de `PendingTransfer` com
     `amount_usdc` real, sem tocar em `TokenBalance`).
3. **Hook de liquidação no onboarding** — ao `POST /v1/creator/register` (ou equivalente) criar a
   wallet Arc de alguém, checar se há pendências pro handle dela e disparar o `send_usdc` real
   nesse momento.

Estimativa: feature nova de verdade (mexe em modelo de identidade + tabela nova/estendida), não um
ajuste pontual. Vale retomar depois que #39/#40/#41/#43 estiverem verdes — é um diferencial forte
de Agentic/Innovation pro vídeo, mas não é bloqueante de nota como os itens P1.
