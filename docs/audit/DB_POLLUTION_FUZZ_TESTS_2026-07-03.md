# Incidente — testes de fuzzing escrevendo no dev DB persistente (`backend/xiao_lee.db`)

> **Detectado e corrigido em:** 2026-07-03 · **Por:** f0ntz (com Claude Code)

## O que aconteceu

Ao investigar uma pergunta sobre transações reais na Arc testnet, encontramos 52 linhas em
`settled_payments` (tabela que alimenta `/v1/traction/stats` e o SSE `/v1/traction/feed` — o
dashboard público que o júri do Lepton vai abrir). Só 16 eram reais (as transações on-chain de
29/jun, ver `backend/scripts/backfill_real_payments.py`). As outras 36 eram lixo: strings unicode
aleatórias, `amount_usdc` na casa de `10^16`–`10^74`, `tx` vazio ou idêntico ao `intent_id`.

**Causa raiz:** vários arquivos de teste usam `TestClient(app_module.app)` — a instância real do
FastAPI — sem sobrescrever a dependência `get_db_session`. Isso faz esses testes escreverem
direto no SQLite de desenvolvimento (`backend/xiao_lee.db`) em vez de um banco isolado. Testes
de fuzzing com Hypothesis (`test_fuzz_traction.py`, 200 exemplos) são os que mais geram lixo
porque literalmente enviam texto/números/bytes aleatórios como payload.

**Por que importa além de "sujeira":** `server/metrics.py::hydrate_traction()` recarrega
`settled_payments` inteiro para dentro das métricas em memória **toda vez que o backend sobe**
(`app.py`, evento de `lifespan`). Ou seja: a cada restart do servidor, o dashboard público
herdava esse lixo — USDC totals astronômicos, handles de creator corrompidos — bem na frente do
júri.

## Correção

1. **`tests/conftest.py`** — nova fixture `isolated_app_db(db_session)`: sobrescreve
   `get_db_session` no app real, apontando para o SQLite em memória isolado por teste
   (`test_engine`/`db_session`, já existentes). Reaproveita o mesmo padrão que
   `test_traction_routes.py` e outros 6 arquivos já usavam individualmente — só que agora
   centralizado, em vez de cada arquivo reimplementar o override.
2. Arquivos que faltavam o isolamento e foram corrigidos (fixture aplicada):
   - `tests/test_fuzz_traction.py::TestPaymentSettledEndpointFuzzing` (o principal poluidor —
     200+ exemplos batendo em `POST /v1/payments/settled`)
   - `tests/test_agent_routes_and_register_fuzzing.py::TestRunCampaignValidation` e
     `TestCreatorRegisterEndpoint` (registro de creator + validação de `run-campaign`)
   - `tests/test_fuzzing.py::TestCampaignVerifyEndpoint` (cria/reusa `User("fuzz_token")` +
     semeia campanhas default a cada exemplo)
3. **`backend/xiao_lee.db`** — `settled_payments` limpo: das 52 linhas, mantidas só as 16 com
   `tx` batendo em `backend/scripts/backfill_real_payments.py` (as transações reais). Total
   restante: **16 pagamentos, $3.55 USDC, 7 creators** — bate com o esperado.

## Verificação

- Suíte completa: 439 passed, 7 skipped (antes e depois da limpeza, mesma contagem).
- `settled_payments` = 16 linhas após rodar a suíte completa de novo (não voltou a poluir).

## O que NÃO foi tocado

- `payment_intents` (4 linhas, todas `status=failed`, sem `tx_hash`) — são tentativas reais
  falhas do fluxo do agente, não lixo de fuzzing. Histórico operacional normal, não precisa
  limpeza.
- Arquivos de teste que usam `TestClient(app)` mas mockam a lógica de negócio antes de qualquer
  escrita real (ex: `test_xiaolee_mvp_security.py`, que substitui `_process_inbound` por
  `AsyncMock` antes de bater no DB) — confirmados como já seguros, não precisam da fixture.

## Se aparecer de novo

Qualquer novo arquivo de teste que use `TestClient(app_module.app)` (a app real, não os
executores/repositório isolados via `db_session` direto) deve incluir `isolated_app_db` como
dependência da sua fixture `autouse`, seguindo o padrão acima.
