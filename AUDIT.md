# XiaoLee Security Audit — Sprint 2026-05

> **Desafio 1 — Auditoria de Segurança**
> Identificar e corrigir pelo menos 1 vulnerabilidade crítica no produto.

Auditores: Thiago Monteiro + Jeiel  
Data: 2026-05-21  
Branch base: `develop` (ce081a2)  
Escopo: backend Python (FastAPI), frontend Next.js, infraestrutura Docker/Railway

---

## Resumo Executivo

| Severidade | Qtd | Status |
|------------|-----|--------|
| CRÍTICO    | 4   | ✅ 4/4 corrigidos (SEC-001, SEC-002, SEC-011, SEC-012) |
| ALTO       | 9   | ✅ 9/9 corrigidos (SEC-003, SEC-004, SEC-013, SEC-014, SEC-015, SEC-016, SEC-017, SEC-019 — SEC-006 é lógica de negócio) |
| MÉDIO      | 7   | ✅ 7/7 corrigidos |
| BAIXO      | 3   | ✅ 3 avaliados — SEC-022 corrigido, SEC-023 false positive, SEC-009 aceito (UX) |

**Scan:** Semgrep 1.163.0 OSS — Python (p/security-audit, p/secrets, p/python, p/fastapi, p/owasp-top-ten, p/cwe-top-25, Trail of Bits) + JS/TS (p/javascript, p/typescript, p/react, p/nextjs) + Docker (p/dockerfile). Resultados em `static_analysis_semgrep_2/`.

**Deep audit:** Crypto/timing analysis (Trail of Bits methodology) em `encryption_service.py`, `stellar_auth_routes.py`, `helius_routes.py`, `x402_routes.py`.

**Supply chain:** Trail of Bits Supply Chain Risk Auditor — 11 dependências flagradas, 5 de alto risco. Resultados em `.supply-chain-risk-auditor/results.md`. Ações: `google-generativeai` e `react-draggable` removidos (mortos), `next-themes` substituído por contexto React nativo, `solders` reduzido a `anchor_client.py` + PyNaCl adicionado, Dependabot configurado.

**Fuzzing:** Hypothesis property-based fuzzing em `tests/test_fuzzing.py` — 15 testes, ~2 500 exemplos gerados. Encontrou e corrigiu 2 bugs reais: `_b58decode_pubkey` (`OverflowError` não capturado) e `helius_routes` (lamports negativos sem clamp inferior).

**Load test:** `load_tests/locustfile.py` — 5 classes de usuário incluindo `XiaoLeeStellarAuth` (stress SEP-10 + challenge flood) e `XiaoLeeSecurityStress` (replay de pagamento, bypass de campanhas, SQL injection em identifiers).

**Suite final:** 61 testes passando, 6 skipped, 3 pré-existentes com falha (test_notifications_routes, test_xiaolee_mvp_orchestration — não relacionados à sprint de segurança).

---

## Vulnerabilidades Encontradas

---

### [SEC-001] 🔴 CRÍTICO — Payment Replay Attack no protocolo x402

**Arquivo:** `backend/server/routes/x402_routes.py` (linha 93–120)  
**Arquivo:** `backend/server/integrations/stellar_adapter.py` (linha 290–329)

**Descrição:**  
O endpoint `POST /v1/ai/query` verifica se um `tx_hash` Stellar é válido via Horizon, mas **não registra os hashes já utilizados**. Isso permite que um atacante reutilize a mesma transação de pagamento (XLM) infinitas vezes para obter respostas da AI sem pagar novamente.

**Exploração:**
```bash
# 1. Paga UMA vez (0.5 XLM)
TX_HASH="abc123..."

# 2. Reutiliza o mesmo hash N vezes — todas passam na verificação
curl -X POST /v1/ai/query \
  -H "X-Payment: {\"tx_hash\": \"$TX_HASH\", \"network\": \"testnet\"}" \
  -d '{"message": "query grátis"}'
# → 200 OK em TODAS as chamadas
```

**Risco:** Fraude financeira direta. O produto cobra por queries mas não impede reuso do pagamento.

**Correção:** Criar tabela `UsedPayment` no banco de dados e rejeitar `tx_hash` já processado.

**Status:** ✅ Corrigido (2026-05-22) — `database/models.py` (`UsedPayment`), `alembic/versions/20260522_used_payments.py`, `server/routes/x402_routes.py` (check + registro pós-processamento)

**Responsável:** Thiago  
**Issue:** #SEC-001

---

### [SEC-002] 🔴 CRÍTICO — JWT Secret hardcoded com valor padrão conhecido

**Arquivo:** `backend/server/routes/stellar_auth_routes.py` (linha 60)

```python
def _jwt_secret() -> str:
    return os.getenv("JWT_SECRET", "xiaolee-stellar-jwt-secret-change-in-prod")
```

**Descrição:**  
Se a variável `JWT_SECRET` não estiver definida no ambiente (Railway, Docker, local), o sistema usa um segredo fixo e publicamente conhecido no código-fonte. Qualquer pessoa com acesso ao repositório pode forjar JWTs válidos para qualquer conta Stellar.

**Exploração:**
```python
import jwt
# Forja token para qualquer carteira
forged = jwt.encode(
    {"sub": "GAVICTIMWALLET...", "stellar_wallet": "GAVICTIMWALLET...", "chain": "stellar"},
    "xiaolee-stellar-jwt-secret-change-in-prod",
    algorithm="HS256"
)
# → Token aceito como autêntico pela API
```

**Risco:** Comprometimento total da autenticação Stellar. Atacante pode se autenticar como qualquer usuário.

**Correção:** Lançar exceção na startup se `JWT_SECRET` não estiver definido, igual ao `ENCRYPTION_KEY` em `config.py`.

**Status:** ✅ Corrigido (2026-05-22) — `_jwt_secret()` levanta `RuntimeError` se `JWT_SECRET` não estiver definido. Startup loga aviso de vars ausentes em `app.py`.

**Responsável:** Jeiel  
**Issue:** #SEC-002

---

### [SEC-003] 🔴 ALTO — IDOR: endpoint /user/{user_id} sem autenticação

**Arquivo:** `backend/server/campaigns_routes.py` (linha 474–523)

```python
@router.get("/user/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, db: AsyncSession = Depends(get_db_session)):
    # Sem verificação de Authorization!
```

**Descrição:**  
O endpoint `GET /user/{user_id}` retorna dados de qualquer usuário (perfil, carteiras, campanhas) sem exigir autenticação. Qualquer pessoa pode enumerar usuários e acessar dados de todos os participantes.

**Risco:** Vazamento de `wallet_public_key`, histórico de campanhas, e identificadores de conta de qualquer usuário da plataforma.

**Correção:** Exigir Bearer token e validar que o usuário autenticado está consultando o próprio perfil (ou adicionar role de admin).

**Status:** ✅ Corrigido (2026-05-22) — `GET /user/{user_id}` agora exige Bearer token via `_resolve_user()` e retorna 403 se `authed_user.twitter_user_id != user_id`.

**Responsável:** Jeiel  
**Issue:** #SEC-003

---

### [SEC-004] 🔴 ALTO — Fail-open no x402: aceita qualquer pagamento sem carteira configurada

**Arquivo:** `backend/server/routes/x402_routes.py` (linha 108–113)

```python
pay_to = _x402_wallet()
if not pay_to:
    # Sem carteira configurada — aceita qualquer hash em dev para facilitar testes
    LOG.warning("[x402] STELLAR_X402_WALLET not set — skipping on-chain verification")
    return True  # ← qualquer tx_hash passa!
```

**Descrição:**  
Se `STELLAR_X402_WALLET` não estiver definido no ambiente, o sistema aceita **qualquer string** como `tx_hash` válido sem verificação on-chain. Um deploy esquecendo de setar esta variável expõe o produto inteiro sem cobrança.

**Risco:** Acesso gratuito a todos os recursos premium se o deploy for feito sem a variável de ambiente.

**Correção:** Falhar explicitamente (HTTP 503) quando `STELLAR_X402_WALLET` não estiver configurado, em vez de aceitar tudo.

**Status:** ✅ Corrigido (2026-05-22) — `server/routes/x402_routes.py`: `return True` substituído por `raise HTTPException(503)`

**Responsável:** Thiago  
**Issue:** #SEC-004

---

### [SEC-005] 🔴 ALTO — Salt estático no serviço de criptografia

**Arquivo:** `backend/user_management/encryption_service.py` (linha 16)

```python
def _derive_key(self, master_key: str) -> bytes:
    salt = b'xiao-lee-salt_'  # ← salt fixo e hardcoded!
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
```

**Descrição:**  
O PBKDF2 usa um salt estático e idêntico para todas as derivações de chave. Isso elimina a proteção que o salt oferece — se a `ENCRYPTION_KEY` vazar, rainbow tables pré-computadas para este salt específico podem ser usadas para decifrar todos os dados.

**Risco:** Se a master key vazar, todos os dados criptografados (private keys custodiais) ficam suscetíveis a ataques offline otimizados.

**Correção:** Gerar um salt aleatório por dado criptografado e armazenar junto ao ciphertext.

**Status:** ✅ Corrigido (2026-05-22) — `user_management/encryption_service.py`: `encrypt()` gera `os.urandom(16)` por chamada, output `base64(salt):fernet_token`. `decrypt()` mantém compat com dados legados (sem prefixo → usa salt estático antigo).

**Responsável:** Thiago  
**Issue:** #SEC-005

---

### [SEC-006] 🟡 MÉDIO — Campaign task verification bypass (verificação falsa)

**Arquivo:** `backend/server/campaigns_routes.py` (linha 764–795)

**Descrição:**  
O endpoint `POST /campaigns/verify` marca as tarefas como verificadas sem fazer nenhuma verificação real (não chama API do Twitter para checar follow/retweet, não valida swap on-chain). Qualquer usuário autenticado pode completar campanhas sem realizar as tarefas.

**Risco:** Fraude nas campanhas — qualquer participante pode reivindicar recompensas sem completar as tarefas exigidas.

**Correção:** Implementar verificação real por tipo de campanha (`social` → verificar Twitter API, `trading` → verificar Helius/Anchor).

**Status:** ✅ Corrigido (2026-05-22) — `server/integrations/campaign_verifier.py` criado com verificação real por tipo:
- `social`: retweet verificado via Twitter API v2 (`/tweets/:id/retweeted_by`, app-only Bearer). Follow logado para auditoria (não disponível com Bearer token). Custodial (Telegram/Google) aceito via sessão autenticada.
- `trading`: Helius API `/addresses/:wallet/transactions?type=SWAP` — exige ≥1 SWAP bem-sucedido na carteira custodial.
- `referral`: proxy metric — exige ≥3 outros participantes no mesmo campaign (referral codes são feature futura).
- Ambas APIs ausentes: fail-open com aviso de log (graceful degradation em dev).

**Responsável:** Jeiel  
**Issue:** #SEC-006

---

### [SEC-007] 🟡 MÉDIO — Timing attack no webhook Helius

**Arquivo:** `backend/server/webhooks/helius_routes.py` (linha 45)

```python
if helius_client.webhook_secret and authorization != helius_client.webhook_secret:
```

**Descrição:**  
A comparação do segredo do webhook Helius usa `!=` (comparação de string padrão do Python), que é vulnerável a timing attacks. Atacantes podem inferir o comprimento e bytes do segredo medindo tempos de resposta. O restante do código já usa corretamente `hmac.compare_digest()`.

**Correção:**
```python
if helius_client.webhook_secret and not hmac.compare_digest(
    authorization or "", helius_client.webhook_secret
):
```

**Status:** ✅ Corrigido (2026-05-22) — `helius_routes.py` usa `hmac.compare_digest` na comparação do header.

**Responsável:** Jeiel  
**Issue:** #SEC-007

---

### [SEC-008] 🟡 MÉDIO — SEP-10 bypassa verificação quando STELLAR_SERVER_SECRET ausente

**Arquivo:** `backend/server/routes/stellar_auth_routes.py` (linha 237–240)

```python
server_secret = _server_secret()
if not server_secret:
    LOG.warning("[SEP-10] STELLAR_SERVER_SECRET not set — skipping server sig verification")
    token = _issue_jwt(account)  # ← emite JWT sem verificar assinatura!
    return TokenResponse(token=token, account=account)
```

**Descrição:**  
Se `STELLAR_SERVER_SECRET` não estiver configurado, o endpoint `/auth/stellar/token` emite um JWT válido para qualquer `account` enviado no body, sem verificar se o cliente realmente assinou o challenge. Combinado com SEC-002 (JWT secret padrão), cria vetor de ataque sem configuração.

**Correção:** Recusar com HTTP 503 se o secret não estiver configurado, não silenciosamente aceitar.

**Status:** ✅ Corrigido (2026-05-22) — `server/routes/stellar_auth_routes.py`: bloco `if not server_secret` agora levanta `HTTPException(503)` em vez de emitir JWT sem verificação.

**Responsável:** Thiago  
**Issue:** #SEC-008

---

### [SEC-009] 🟢 BAIXO — Enumeração de tokens via /auth/status/{token}

**Arquivo:** `backend/server/campaigns_routes.py` (linha 388)

**Descrição:**  
Tokens desconhecidos retornam `{"status": "pending"}` em vez de `{"status": "expired"}` ou 404. Isso permite distinguir entre tokens válidos-mas-expirados e tokens inexistentes.

**Responsável:** A definir  
**Issue:** #SEC-009

---

### [SEC-010] 🟢 BAIXO — Endpoint de debug público `/v1/ai/query/verify-tx`

**Arquivo:** `backend/server/routes/x402_routes.py` (linha 213–225)

**Descrição:**  
O endpoint `GET /v1/ai/query/verify-tx?tx_hash=...` é público e permite que qualquer pessoa verifique transações Stellar contra a carteira do servidor. Expõe a carteira receptora e pode ser abusado para reconhecimento.

**Responsável:** A definir  
**Issue:** #SEC-010

---

---

## Novos Achados — Rodada 2 (Semgrep + Crypto Audit 2026-05-22)

---

### [SEC-011] 🔴 CRÍTICO — Helius webhook fail-open (sem secret configurado aceita tudo)

**Arquivo:** `backend/server/integrations/helius_client.py` (linha 12–13)  
**Arquivo:** `backend/server/webhooks/helius_routes.py` (linha 44–46)

**Descrição:**  
`verify_webhook_signature()` retornava `True` quando `webhook_secret` não estava configurado. O route também fazia comparação direta de string ao invés de usar o método HMAC — ignorando o body e comparando apenas o header bruto com o secret.

**Risco:** Qualquer POST não autenticado era aceito como evento Helius válido. Atacante poderia criar transações, notificações e acionar `record_swap` on-chain fraudulentamente.

**Status:** ✅ Corrigido (2026-05-22)
- `helius_client.py`: `return True` → `return False`
- `helius_routes.py`: fail-closed se sem secret (503), usa `verify_webhook_signature(authorization, raw_body)` com HMAC-SHA256, parse do body a partir de `raw_body` (single parse)

---

### [SEC-012] 🔴 CRÍTICO — SQL Injection via f-string em `sqlalchemy.text()`

**Arquivo:** `backend/ai/mcp_tools.py` (linha 2140)

```python
.where(text(f"user_id = {user.id}"))  # ← interpolação direta em SQL bruto
```

**Descrição:**  
Query usa `sqlalchemy.text()` com f-string para inserir `user.id`. Mesmo sendo um int, este padrão é SQL injection quando qualquer parte for string user-controlled. Flagrado pelo Semgrep (CWE-89).

**Status:** ✅ Corrigido (2026-05-22) — substituído por query ORM usando `DMLog.user_id == user.id` com parâmetros seguros.

---

### [SEC-013] 🔴 ALTO — TOCTOU race condition no anti-replay do x402

**Arquivo:** `backend/server/routes/x402_routes.py`

**Descrição:**  
O check de replay (SELECT UsedPayment) era feito ANTES do insert, com o orchestrator no meio. Duas requisições simultâneas com o mesmo `tx_hash` passavam ambas pela verificação, obtendo 2 respostas AI pelo preço de 1. Além disso, se o orchestrator falhasse (500), o `tx_hash` nunca era registrado — permitindo retry grátis.

**Status:** ✅ Corrigido (2026-05-22) — `UsedPayment` é inserido via `db.flush()` ANTES do orchestrator. `IntegrityError` na unique constraint captura tentativas concorrentes.

---

### [SEC-014] 🔴 ALTO — Mock SEP-10 sem validação de nonce

**Arquivo:** `backend/server/routes/stellar_auth_routes.py` (linha 222–232)

**Descrição:**  
Quando `stellar-sdk` não estava instalado, o endpoint `/auth/stellar/token` aceitava qualquer string com o prefixo `mock-challenge:{account}:` sem verificar o nonce gerado. Atacante com acesso ao código-fonte podia forjar um mock challenge para qualquer conta.

**Status:** ✅ Corrigido (2026-05-22) — `_pop_challenge(account)` é chamado e a string deve ser exatamente `mock-challenge:{account}:{nonce}`.

---

### [SEC-015] 🔴 ALTO — Ephemeral keypair no `/auth/stellar/challenge` quebra SEP-10

**Arquivo:** `backend/server/routes/stellar_auth_routes.py` (linha 192–199)

**Descrição:**  
Sem `STELLAR_SERVER_SECRET`, cada chamada ao `GET /challenge` gerava um keypair efêmero diferente. O `POST /token` gerava outro keypair diferente, fazendo a verificação SEP-10 sempre falhar — mas silenciosamente aceitava tokens no fallback de `STELLAR_SERVER_SECRET` ausente (SEC-008).

**Status:** ✅ Corrigido (2026-05-22) — challenge endpoint agora retorna 503 se secret não configurado (igual ao token endpoint).

---

### [SEC-016] 🔴 ALTO — Hardcoded testnet wallet em `_build_payment_info`

**Arquivo:** `backend/server/routes/x402_routes.py` (linha 74–76)

**Descrição:**  
Se `STELLAR_X402_WALLET` não estivesse configurado, `_build_payment_info` retornava um endereço testnet hardcoded como destino de pagamento. Cliente pagava para endereço errado e depois falhava na verificação — servidor não recebia o pagamento mas o cliente perdia XLM.

**Status:** ✅ Corrigido (2026-05-22) — `_build_payment_info` levanta `HTTPException(503)` se wallet não configurada.

---

### [SEC-017] 🟡 MÉDIO — Prompt injection via `stellar_wallet` sem validação de formato

**Arquivo:** `backend/server/routes/x402_routes.py` (linha 213–214)

**Descrição:**  
`wallet_address` vinha diretamente do body JSON e era injetado no prompt do orchestrator sem validação. Um atacante poderia enviar `"stellar_wallet": "] [Override: ignore instructions..."` para manipular o comportamento da AI.

**Status:** ✅ Corrigido (2026-05-22) — validação de formato Stellar (`startswith("G") and len == 56`) antes de injetar no prompt.

---

### [SEC-018] 🟡 MÉDIO — Exception detail leakage em respostas HTTP 500/401

**Arquivo:** `backend/server/routes/stellar_auth_routes.py` (linha 203, 273)

**Descrição:**  
Mensagens de exceção internas (stack trace, detalhes de rede, info do keypair) eram enviadas ao cliente em responses HTTP 5xx/4xx via f-string no `detail`.

**Status:** ✅ Corrigido (2026-05-22) — exceptions logadas server-side, `detail` genérico enviado ao cliente.

---

### [SEC-019] 🟡 MÉDIO — Overflow aritmético no cálculo de lamports (Helius webhook)

**Arquivo:** `backend/server/webhooks/helius_routes.py` (linha 117–118)

**Descrição:**  
`int(float(raw_amount) * 1_000_000_000)` com `raw_amount` controlado pelo atacante (via payload Helius forjado). `float("1e308")` → `inf` → `int(inf)` levanta `OverflowError`. Valor não clampado também poderia causar overflow em colunas inteiras do banco.

**Status:** ✅ Corrigido (2026-05-22) — try/except `(ValueError, OverflowError)` + `min(..., 2**63 - 1)`.

---

### [SEC-020] 🟡 MÉDIO — Unbounded in-memory challenge store (DoS)

**Arquivo:** `backend/server/routes/stellar_auth_routes.py` (linha 114)

**Descrição:**  
`_challenges: dict[str, tuple[str, float]]` cresce ilimitadamente. Atacante pode fazer GET `/auth/stellar/challenge?account=G{N}` para N endereços únicos, enchendo memória indefinidamente. Entradas expiradas só são removidas quando `_pop_challenge` é chamado.

**Status:** ✅ Corrigido (2026-05-22) — `_store_challenge()` agora varre entradas expiradas antes de inserir. Hard cap de 5 000 entradas: se ainda cheio após sweep, retorna `False` e o endpoint responde HTTP 429. Um único enumerador não consegue encher o dict enquanto TTLs de 5 min forem expirados naturalmente.

---

### [SEC-021] 🟡 MÉDIO — `time.time()` chamado duas vezes em `_issue_jwt`

**Arquivo:** `backend/server/routes/stellar_auth_routes.py` (linha 79–80)

**Status:** ✅ Corrigido (2026-05-22) — captura `now = int(time.time())` uma vez, usa nos dois campos.

---

### [SEC-022] 🟢 BAIXO — Dockerfile roda como root

**Arquivo:** `frontend/Dockerfile` (linha 19)

**Status:** ✅ Corrigido (2026-05-22) — adicionado `USER appuser` não-root no runner stage.

---

### [SEC-023] 🟢 BAIXO — urllib dinâmico em script de dev (false positive)

**Arquivo:** `backend/scripts/smoke_api.py` (linhas 33, 46)

**Descrição:**  
Semgrep flagrou `urllib.request.urlopen` com URLs dinâmicas. Contexto: URLs são `http://127.0.0.1:8000/...` fixas em script de teste local. Não é código de produção.

**Status:** 🟢 False positive — script de dev, sem risco em produção.

---

## Issues da Sprint (mapeamento Thiago / Jeiel)

### Thiago

| Issue | Título | Severidade | Esforço |
|-------|--------|------------|---------|
| #SEC-001 | Implement x402 payment replay protection (UsedPayment table) | CRÍTICO | ~4h |
| #SEC-004 | Fix x402 fail-open when STELLAR_X402_WALLET not set | ALTO | ~1h |
| #SEC-005 | Fix static salt in EncryptionService (per-datum random salt) | ALTO | ~3h |
| #SEC-008 | Reject SEP-10 token when STELLAR_SERVER_SECRET not configured | MÉDIO | ~1h |

### Jeiel

| Issue | Título | Severidade | Esforço |
|-------|--------|------------|---------|
| #SEC-002 | Enforce JWT_SECRET at startup (raise if not set) | CRÍTICO | ~1h |
| #SEC-003 | Add auth to GET /user/{user_id} endpoint (IDOR fix) | ALTO | ~2h |
| #SEC-006 | Implement real campaign task verification (Twitter + Anchor APIs) | MÉDIO | ~6h |
| #SEC-007 | Replace != with hmac.compare_digest in Helius webhook | MÉDIO | ~30min |

---

---

## Ambiente de teste

```bash
# Backend
cd backend && source ../.venv/bin/activate
uvicorn server.app:app --reload --port 8000

# Rodar testes de segurança existentes
pytest backend/tests/test_xiaolee_mvp_security.py -v
```

---

## Referências

- OWASP Top 10 A01 (Broken Access Control) → SEC-003
- OWASP Top 10 A02 (Cryptographic Failures) → SEC-002, SEC-005
- OWASP Top 10 A07 (Identification and Authentication Failures) → SEC-002, SEC-008
- CWE-294: Authentication Bypass by Capture-replay → SEC-001
- CWE-330: Use of Insufficiently Random Values → SEC-005
