# QA Plan XiaoLee MVP

Atualizacao documental: **2026-04-24**.

## Escopo validado

- Normalizacao de payloads Telegram e X
- Roteamento de intencao
- Execucao de saldo/cotacao no orquestrador
- Resposta fallback de ajuda
- Responsividade UI Mobile (100dvh, teclado virtual)

## Testes implementados

- backend/tests/test_xiaolee_mvp_orchestration.py
  - test_detect_balance_intent_with_wallet
  - test_detect_swap_quote_intent
  - test_help_fallback_uses_gemini_reply
  - test_telegram_adapter_normalization
  - test_x_adapter_normalization
- frontend/src/utils/swap.test.ts
  - validates amount conversions and quote summary extraction
- frontend/src/components/navbar/Wallet.test.tsx
  - phantom missing guidance
  - prepare + simulate + explicit confirmation + send flow
  - simulation error blocks send
  - selected token decimals are respected in prepare payload
  - prepare endpoint non-200 error is surfaced to user
  - input/output equal token is rejected before API call
  - invalid amount (zero/non-numeric) is rejected before API call
  - wallet signature rejection is surfaced to user
  - network/RPC send failure is surfaced to user
- backend/tests/test_helius_webhook.py
  - persiste evento on-chain e atualiza transaction history
  - cria notificacao de entrega em X quando configurado
- backend/tests/test_notifications_routes.py
  - ack atualiza status para delivered e marca delivered_at
- backend/tests/test_campaign_claim_proof.py
  - valida assinatura Ed25519 do claim
  - persiste claim_receipt_id no participante
  - cria notificacao in-app vinculada ao receipt
- backend/tests/test_metrics.py
  - expõe métricas HTTP em formato Prometheus

## CI / Operação

- `.github/workflows/fullstack-ci.yml`
  - backend pytest
  - frontend lint
  - frontend vitest
  - frontend build

## Execucao mais recente

Observacao: os resultados abaixo representam o snapshot operacional mais recente reportado para o MVP em Devnet.

- Backend principal: `../.venv/bin/pytest -q`
- Resultado: **34 passed, 8 skipped**
- Skips: scripts legados de Twikit e integrações externas que exigem dependências opcionais não instaladas no ambiente local
- Frontend: `npm test`
- Resultado: **13 passed**
- Workflow fullstack CI: backend + frontend + build adicionados e alinhados ao estado atual do repositório

## Matriz de rastreabilidade (endpoint x teste)

| Endpoint / Fluxo | Teste(s) | Status |
|---|---|---|
| `POST /v1/messages/inbound` | `backend/tests/test_xiaolee_mvp_orchestration.py` | Coberto |
| `POST /v1/integrations/telegram/webhook` | `backend/tests/test_xiaolee_mvp_security.py` | Coberto |
| `POST /v1/integrations/x/webhook` | `backend/tests/test_xiaolee_mvp_security.py` | Coberto |
| `POST /v1/solana/swap/prepare` | `backend/tests/test_xiaolee_mvp_security.py`, `frontend/src/components/navbar/Wallet.test.tsx` | Coberto |
| `POST /v1/solana/webhooks/helius` | `backend/tests/test_helius_webhook.py` | Coberto |
| `GET /v1/notifications/me` | `backend/tests/test_notifications_routes.py` | Coberto |
| `POST /v1/notifications/{notification_id}/ack` | `backend/tests/test_notifications_routes.py` | Coberto |
| `POST /campaigns/claim` | `backend/tests/test_campaign_claim_proof.py` | Coberto |
| `GET /health` | `backend/tests/test_xiaolee_mvp_security.py` | Coberto |
| `GET /status` | `backend/tests/test_xiaolee_mvp_security.py` | Coberto |
| `POST /chat` | `backend/tests/test_xiaolee_mvp_security.py` | Coberto |

## Estrategia de regressao

1. Rodar testes unitarios a cada PR
  - backend: `../.venv/bin/pytest -q`
  - frontend: npm test
2. Executar smoke local da API:
   - GET /health
   - POST /v1/messages/inbound
3. Adicionar testes de contrato para webhooks reais
4. Manter smoke local como validacao complementar de ambiente (Docker/RPC)

## Criterios de aceite do MVP

- API sobe com Docker
- Endpoint /health retorna status ok e checagem RPC
- Mensagem de saldo com carteira retorna valor em SOL
- Mensagem de swap retorna cotacao Jupiter
- Frontend prepara swap, simula em devnet e exige confirmacao explicita antes de assinar/enviar
- Suite principal do backend passa sem quebra de coleta, com scripts legados isolados por skip explícito
