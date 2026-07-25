# XiaoLee API Reference

> Atualizado em: **2026-04-24** | Sprint 7 concluída.
> Base URL local: `http://localhost:8000`
> Base URL produção: `https://api.xiaolee.io` (a configurar)

Todas as respostas são JSON. Autenticação via `Authorization: Bearer <session_id>` nos endpoints de campanha e notificações.

**Rate Limiting:** 60 req/min por chave (Redis sliding window com fallback in-memory).
**CORS:** headers restritos via `CORS_ALLOWED_HEADERS` env — não usa wildcard em produção.

## 1. Status e Diagnóstico

### `GET /health`

Health check básico. Retorna `503` se o RPC da Solana não responder.

Resposta típica:

```json
{
"status": "ok",
"service": "XiaoLee Core API",
"version": "2.0.0-mvp",
"environment": "dev",
"solana_cluster": "devnet",
"rpc_health": { "jsonrpc": "2.0", "result": "ok", "id": 1 },
"gemini_enabled": true
}
```

---

### `GET /health/detailed`

Health check granular com status e latência de cada dependência.
Ideal para sistemas de monitoramento (UptimeRobot, Grafana, Datadog).

Resposta `200 OK`:

```json
{
"status": "ok",
"service": "XiaoLee Core API",
"version": "2.0.0-mvp",
"environment": "dev",
"dependencies": {
"database": { "status": "ok", "latency_ms": 0.42 },
"solana_rpc": { "status": "ok", "latency_ms": 134.5, "cluster": "devnet" },
"gemini": { "status": "enabled", "model": "gemini-pro" },
"jupiter": { "status": "ok", "latency_ms": 421.3, "out_amount_raw": "123456" }
}
}
```

Status possíveis por dependência: `ok` | `degraded` | `error` | `timeout` | `enabled` | `disabled`.

---

### `GET /status`

Status resumido do backend.

```json
{ "status": "running" }
```

---

### `GET /metrics`

Endpoint Prometheus text format com contadores HTTP e de eventos de campanha.

```text
# HELP xiaolee_http_requests_total Total de requests HTTP processadas.
# TYPE xiaolee_http_requests_total counter
xiaolee_http_requests_total{method="GET",path="/status",status="200"} 1

# HELP xiaolee_campaign_events_total Eventos de campanha por tipo.
# TYPE xiaolee_campaign_events_total counter
xiaolee_campaign_events_total{event="join"} 5
xiaolee_campaign_events_total{event="join_duplicate"} 2
xiaolee_campaign_events_total{event="verify"} 3
xiaolee_campaign_events_total{event="claim"} 1
```

## 2. Chat e Orquestração

### `POST /chat`

Endpoint simplificado para interação textual.

Request típico:

```json
{
"message": "swap 0.1 SOL para USDC",
"platform": "web",
"user_id": "web-user-123"
}
```

Resposta típica:

```json
{
"response": [{ "type": "text", "content": "..." }],
"intent": { "action": "swap", "confidence": 0.98, "entities": {} },
"execution": {},
"code": null,
"animations": null
}
```

### `POST /v1/messages/inbound`

Entrada principal para mensagens normalizadas de canais.

Schema principal: `platform`, `user_id`, `text` e `metadata` opcional.

Exemplo de request:

```json
{
"platform": "telegram",
"user_id": "123456",
"text": "swap 0.1 SOL para USDC"
}
```

Exemplo de resposta:

```json
{
"platform": "telegram",
"user_id": "123456",
"intent": { "action": "swap", "confidence": 0.98, "entities": {} },
"reply_text": "Posso preparar a transacao para voce.",
"execution": {}
}
```

## 3. Webhooks de Integração

### `POST /v1/integrations/telegram/webhook`

Webhook Telegram.

Segurança:

- Header `X-Telegram-Bot-Api-Secret-Token` deve corresponder ao valor configurado (`TELEGRAM_WEBHOOK_SECRET`).

### `POST /v1/integrations/x/webhook`

Webhook X/Twitter.

Segurança:

- Header `X-XiaoLee-Signature` com assinatura HMAC SHA256 validada no backend.

### `POST /v1/solana/webhooks/helius`

Recebe eventos on-chain de confirmação/falha.

Segurança:

- Header `Authorization` deve bater com `HELIUS_WEBHOOK_SECRET`.

Resposta de sucesso:

```json
{ "status": "success", "processed_events": 1 }
```

## 4. Solana Swap

### `POST /v1/solana/swap/prepare`

Prepara a transação de swap sem assinatura (wallet-first).

Request esperado:

- `user_public_key`
- `input_mint`
- `output_mint`
- `amount_raw`
- `slippage_bps`

Exemplo de request:

```json
{
"user_public_key": "8Y7NwkjVaY7LHKV8ha2g8xD6LTY64PrtP6Qwzcw7f6Vj",
"input_mint": "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU",
"output_mint": "So11111111111111111111111111111111111111112",
"amount_raw": 1000000,
"slippage_bps": 50
}
```

Exemplo de resposta:

```json
{
"cluster": "devnet",
"quote": {
"outAmount": "...",
"otherAmountThreshold": "..."
},
"swap_transaction_base64": "...",
"last_valid_block_height": 12345678,
"disclaimer": "Transacao somente preparada. Assine na wallet e confirme antes do envio."
}
```

## 5. Campanhas e Usuários

Observação: no estado atual, rotas de campanha não têm prefixo `/v1`.

### `GET /auth/status/{token}`

Valida token/sessão.

### `GET /user/{user_id}`

Consulta dados resumidos do usuário.

### `GET /campaigns`

Lista campanhas disponíveis.

Retorna campanhas ativas persistidas em SQLite, com seed inicial quando o banco está vazio.

### `GET /campaigns/me`

Lista campanhas relacionadas ao usuário autenticado.

Header esperado:

- `Authorization: Bearer <token>`

Cada item retornado pode incluir `claim_receipt_id` quando o usuário já concluiu o claim da recompensa.

Compatibilidade legada: `GET /campaigns/user` continua aceito, mas o endpoint oficial é `/campaigns/me`.

### `POST /campaigns/create`

Cria campanha.

Payload principal: `title`, `description`, `campaign_type`, `reward_token`, `reward_per_participant`, `max_participants`, `profile_to_follow`, `tweet_id_to_engage`.

### `POST /campaigns/join`

Inscreve o usuário em uma campanha.

**Header:** `Authorization: Bearer <session_token>`

**Body:**
```json
{ "campaign_identifier": "1" }
```

**Respostas:**

| Código | Condição | Body |
|---|---|---|
| `200 OK` | Inscrição realizada | `{"success": true, "message": "Successfully joined..."}` |
| `409 Conflict` | Usuário já inscrito | `{"detail": "You have already joined this campaign"}` |
| `400 Bad Request` | Campanha inativa ou cheia | `{"success": false, "error": "..."}` |
| `401 Unauthorized` | Sessão inválida | `{"detail": "Invalid session"}` |

> [ATENCAO] O código `409 Conflict` é o sinal canônico para join duplicado. Clientes **não devem** tratar 409 como erro — o estado do usuário já está correto.

---

### `POST /campaigns/verify`

Verifica tarefas associadas à campanha (follow, retweet, etc).

**Header:** `Authorization: Bearer <session_token>`

**Body:** `{ "campaign_identifier": "1" }`

**Resposta `200 OK`:**
```json
{ "success": true, "message": "All tasks verified successfully!", "all_tasks_completed": true }
```

---

### `POST /campaigns/claim`

Solicita claim de recompensa. Requer que as tarefas já estejam verificadas.

**Body:**
```json
{
"campaign_identifier": "1",
"wallet_public_key": "...",
"wallet_signature": "...",
"proof_message": "XiaoLee Devnet claim|campaign:1|session:...|wallet:...|ts:...",
"proof_encoding": "base64"
}
```

**Resposta `200 OK` (sucesso):**
```json
{
"success": true,
"message": "50.0 $XLEE claimed successfully!",
"transaction_id": "...",
"claim_receipt_id": "...",
"reward_amount": 50,
"reward_token": "$XLEE",
"wallet_public_key": "...",
"proof_submitted": true
}
```

**Resposta `400 Bad Request` (sem proof):**
```json
{ "detail": "wallet_public_key is required for Devnet claim" }
```

---

## 6. Contratos On-chain (Solana/Anchor)

### Programa XiaoLee Core

| Campo | Valor |
|---|---|
| **Program ID** | `Fmmpn79Tij8fzYHg31ekZz4MmK9ArGzN59VogfcwhXiM` |
| **Cluster** | `devnet` |
| **IDL** | `frontend/src/idl/xiaolee_core.json` |
| **Versão** | `0.1.0` |

### Instruções

| Instrução | Signer | Descrição |
|---|---|---|
| `initialize_global()` | Admin | Cria GlobalConfig PDA — executado uma única vez |
| `initialize_user(twitter_id)` | Usuário | Cria UserState PDA vinculado ao Twitter ID |
| `record_swap(volume)` | **Admin only** | Incrementa swap_count e total_volume do usuário |

> [ATENCAO] `record_swap` exige a autoridade admin como signer. Usuários não chamam esta instrução diretamente — o backend intermediará após confirmar swaps via webhook Helius (planejado para Sprint 6).

### PDAs

```typescript
// UserState PDA — um por usuário
seeds = ["user", twitter_id_bytes]
// Exemplo: PublicKey.findProgramAddressSync(
// [Buffer.from("user"), Buffer.from("xiaolee_user_123")],
// new PublicKey("Fmmpn79Tij8fzYHg31ekZz4MmK9ArGzN59VogfcwhXiM")
// )

// GlobalConfig PDA — único no protocolo
seeds = ["global_config"]
```

### Estrutura `UserState`

```rust
pub struct UserState {
pub twitter_id: String, // max 50 chars
pub swap_count: u64, // total de swaps registrados
pub total_volume: u64, // volume acumulado em lamports
pub bump: u8,
}
```

### Códigos de Erro On-chain

| Código | Nome | Mensagem |
|---|---|---|
| `6000` | `MathOverflow` | Math operation overflow |
| `6001` | `StringTooLong` | String length exceeds maximum allowed limit of 50 |
| `6002` | `Unauthorized` | Unauthorized: You are not the protocol admin |

---

## 7. Notificações


### `GET /v1/notifications/me`

Lista notificações de um usuário.

Header esperado:

- `Authorization: Bearer <token>`

O backend usa apenas o token da sessão Devnet para resolver o usuário atual.

Retorna `success` e `notifications` ordenadas da mais recente para a mais antiga.

Para claims de campanha, o `related_signature` e o `metadata.claim_receipt_id` carregam o receipt persistido.

Compatibilidade legada: `GET /v1/notifications/{twitter_user_id}` continua aceito, mas o endpoint oficial é `/v1/notifications/me`.

### `POST /v1/notifications/{notification_id}/ack`

Marca notificação como entregue/reconhecida.

Header esperado:

- `Authorization: Bearer <token>`

O ACK só é aceito quando o token pertence ao dono da notificação.

Resposta:

```json
{ "success": true, "notification_id": 1, "status": "delivered" }
```

## 7. Status Codes e Erros

Formato de erro padrão FastAPI:

```json
{
"detail": "mensagem"
}
```

Códigos comuns:

- `200` sucesso
- `400` payload inválido
- `401` não autorizado
- `404` recurso não encontrado
- `429` rate limit
- `500` erro interno
- `503` RPC da Solana indisponível

Observacao de maturidade: esta referencia descreve o contrato HTTP atual do MVP em Devnet. Itens de readiness para producao/mainnet estao fora do escopo deste documento.
