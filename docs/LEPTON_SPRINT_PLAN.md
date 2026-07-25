# XiaoLee — Lepton Hackathon Sprint Plan
> Deadline real: **6 jul 2026, 23:59 ET** | Hoje: 30 jun | Dias restantes: **6**
> Scoring: Agentic 30% · Traction 30% · Circle Tools 20% · Innovation 20%
> Score atual estimado: **~68/100** → meta: **85+/100**

---

## Diagnóstico (30 jun — checagem 360° pós-sessão de infra)

| Critério | Peso | Estado real hoje | Score |
|----------|------|-----------------|-------|
| Agentic | 30% | Loop Claude completo, 4 tools, background task — mas o loop autônomo (`run-campaign`) ainda não rodou ponta a ponta com dinheiro real, só pagamentos avulsos | ~22/30 |
| Traction | 30% | **16 tx USDC reais confirmadas on-chain (29/jun), $3.55, 7 creators** — feed agora persistido em DB (`settled_payments`) e sobrevive a restart; `/traction` page consome `/v1/traction/stats` + SSE | ~16/30 |
| Circle Tools | 20% | W3S ArcClient, CCTP, circle_crypto, arc_x402 registrado e **`ARC_X402_WALLET_ADDRESS` agora configurado** (30/jun) — endpoint de recebimento desbloqueado, falta validar fluxo 402→paga→200 ponta a ponta | ~18/20 |
| Innovation | 20% | PQC ML-DSA-87 **integrado ao fluxo do agente** (`creator_pay_tools.py` chama `sign_receipt` e retorna `receipt_pqc`) — não aparece no demo/vídeo ainda | ~14/20 |
| **TOTAL** | | | **~68/100** |

**O que nos separa do Grand Prize:** loop agêntico completo rodando com dinheiro real (não só pagamentos avulsos) + validar x402 ponta a ponta com a wallet configurada + deploy público + vídeo forte.

---

## P0 — Fix urgente (bloqueantes de nota)

### P0-01 — ~~Registrar `arc_x402_routes.py` no `app.py`~~ DONE (28/jun)
`arc_x402_router` adicionado em `app.py` linhas 45 e 133.
`POST /v1/arc/ai/query` sem X-Payment → retorna 402 com `"network":"arc","asset":"USDC"`.
Verificado: import OK, payment info builder OK, sandbox verify OK.

---

### P0-02 — ~~Configurar Circle credentials reais~~ DONE (30/jun)
**Owner: f0ntz**

`.env` atual: `ARC_SANDBOX=false`, `CIRCLE_API_KEY` setada (formato sandbox real `TEST_API_KEY:uuid:hex`), `CIRCLE_WALLET_ID` setada, `ANTHROPIC_API_KEY` setada.

`ARC_X402_WALLET_ADDRESS` estava ausente, causando `503 "Payment service not configured"` em
`POST /v1/arc/ai/query` (`server/routes/arc_x402_routes.py:99`). Resolvido sem criar wallet nova
(que orfanaria o `CIRCLE_WALLET_ID` já em uso pelas 16 tx reais do P1-01): consultamos o endereço
EVM da wallet já existente e LIVE em `ARC-TESTNET` via `ArcClient.get_wallet_info()` e gravamos em
`.env`. Verificado: `server.routes.arc_x402_routes._arc_x402_wallet()` agora retorna o endereço.

Próximo passo: fundar a wallet com USDC de teste em [faucet.circle.com](https://faucet.circle.com)
e validar `POST /v1/arc/ai/query` ponta a ponta (402 → paga → 200).

> ATENÇÃO SEGURANÇA: durante a checagem de 30/jun um comando de diagnóstico imprimiu `ANTHROPIC_API_KEY` e `CIRCLE_API_KEY` em texto plano numa sessão de terminal. Rotacionar as duas chaves antes da submissão pública do repositório.

---

### P0-03 — ~~Corrigir pytest-asyncio~~ DONE (29/jun)
`pytest-asyncio==1.3.0` já instalado no venv. 198 testes coletam OK.
Único erro de coleta pré-existente: `scripts/db/test_mcp_migration.py` (módulo `mcp` não instalado — não bloqueia os testes de Arc/x402).

---

## P1 — Traction real (30% da nota — o que decide o pódio)

### P1-01 — ~~Primeira transação USDC real na Arc testnet~~ FEITO (29/jun, 20:31–21:50 BRT)
**Owner: f0ntz + Jeiel**

**16 transações USDC reais confirmadas on-chain na Arc testnet, $3.55 total, 7 creators**
(hashes em `scripts/backfill_real_payments.py`, conferíveis em testnet.arcscan.app). PQC
receipt (ML-DSA-87) já está implementado em `creator_pay_tools.pay_creator_nanopayment`.

Ressalva importante: essas 16 tx foram disparadas manualmente contra
`POST /v1/payments/settled` (estilo `seed_demo_payments.py`, mas com hashes reais), não
pelo loop agêntico completo (`POST /v1/agent/run-campaign` → discover→evaluate→pay). O
banco `payment_intents` (usado pelo loop autônomo) segue zerado — falta provar o agente
rodando sozinho com dinheiro real, ainda não só pagamentos avulsos confirmados.

**Bug crítico encontrado e corrigido (30/jun):** o feed de tração (`server/metrics.py`)
era 100% in-memory — qualquer restart do backend zerava o dashboard que o júri vê, mesmo
com USDC real on-chain. Corrigido: nova tabela `settled_payments` (migração
`20260630_add_settled_payments`), `POST /v1/payments/settled` agora persiste antes de
atualizar memória/SSE, e o `lifespan` do `app.py` hidrata o estado no boot. As 16 tx reais
de ontem foram backfilladas via `scripts/backfill_real_payments.py` (idempotente, tx hash
como `intent_id` — seguro rodar de novo). Cobertura nova: `test_settled_payments_repository.py`,
`test_metrics_hydrate.py`, `test_traction_routes.py`.

Também corrigido en passant: `tests/test_agent_engine.py::test_live_mode_requires_api_key`
disparava uma chamada HTTP real pra `api.circle.com` durante a suíte (o construtor do
`ArcClient` faz `api_key or os.getenv("CIRCLE_API_KEY", "")`, e com a key real configurada
no `.env` desde o P0-02, `api_key=""` explícito não bloqueava mais o fallback). Só não
houve transferência real porque o `idempotencyKey` do fixture não era um UUID válido.

Próximo passo real: rodar `POST /v1/agent/run-campaign` ponta a ponta com dinheiro real
pra provar o loop agêntico (não só pagamentos avulsos) — isso ainda não foi feito.

**Gap arquitetural encontrado e corrigido (01/jul):** mesmo com wallet e credenciais
configuradas, o loop agêntico não conseguia pagar ninguém de verdade. `discover_creators`/
`evaluate_creator` leem de `campaign_participants` (0 linhas, e sem nenhuma coluna de wallet
EVM/Circle — só `stellar_wallet`, campo legado da era Stellar), e `pay_creator_nanopayment`
chamava `ArcClient.send_usdc(to_address=to)`, que exige um endereço EVM cru — não havia
nenhum caminho para resolver esse endereço a partir de um creator enrolado na campanha.

Corrigido em `ai/agents/creator_pay_tools.py::pay_creator_nanopayment`: quando `to` é um
handle já registrado via `POST /v1/creator/register`, o executor agora resolve o
`circle_wallet_id` via `get_registered_creator_wallet()` (mesmo registro usado pela trilha
manual) e paga via `transfer_usdc()` — a mesma trilha Circle já usada nas 16 tx reais. Se
`to` não é um handle registrado, cai no `arc_client.send_usdc` (endereço EVM direto),
mantendo o contrato da tool (`pay_creator_nanopayment(intent_id, to, amount_usdc)`)
inalterado. Validado: import limpo + suíte completa roda sem regressão
(320 passed, as 2 falhas restantes são pré-existentes em `test_security_regression.py`,
Stellar-era, sem relação com esta mudança).

**Ainda falta para rodar de verdade:** `_registered_creators` (`server/metrics.py`) é
in-memory — zera a cada restart do backend, então é preciso (1) subir o backend, (2)
registrar um creator real via `/v1/creator/register` com um `circle_wallet_id` de
destino real, (3) inserir 1 linha em `campaign_participants` com tasks verificadas
(score ≥ 50) pra esse creator, e só então (4) disparar `POST /v1/agent/run-campaign`
com budget pequeno. Ainda não executado — envolve mover USDC real, feito sob confirmação.

---

### P1-02 — Onboarding de creators reais no testnet
**Owner: Mari | ETA: D29-D01**

O júri vai olhar o dashboard ao vivo. Precisa de criadores reais, não seeds.

- Objetivo: **5 creators registrados** via `POST /v1/creator/register` com wallet Sepolia real
- Mari usa `seed_demo_payments.py` como referência para o fluxo, mas com wallets reais
- Compartilhar link de onboarding no Discord do hackathon — pede para outros builders testarem

```bash
# Registrar creator (já tem endpoint)
curl -X POST http://<staging>/v1/creator/register \
  -H "Content-Type: application/json" \
  -d '{"handle": "@testcreator", "circle_wallet_id": "<uuid>"}'
```

---

### P1-03 — Dashboard ao vivo com USDC-flow visível
**Owner: Mari | ETA: D30-D01**

O júri abre o link e precisa ver USDC saindo em tempo real.

- **Atualização 30/jun:** `frontend/src/app/traction/page.tsx` já existe, chama
  `GET /v1/traction/stats` e abre `EventSource` no SSE `/v1/traction/feed`. Página pública pronta.
- Falta validar: métricas mínimas visíveis (total USDC pago, nº creators, latência, feed) renderizando
  com dados reais — hoje só há infra, sem pagamentos reais para popular a tela.

---

### P0-04 — ~~`.venv` deste checkout tinha scripts (`pip`, `pytest`...) apontando pra OUTRO repo~~ CORRIGIDO (01/jul)

`Documents/ParaDevs-XIAOLEE-StellarAdapt/XiaoLee/.venv/bin/{pip,pytest,locust,flask,httpx,...}`
tinham shebang `#!/home/f0ntz/ParaDevs-XIAOLEE/XiaoLee/.venv/bin/python3` — um checkout
totalmente diferente na máquina. Rodar `pytest`/`pip install` aqui sempre executava
silenciosamente no OUTRO venv. `.venv/bin/uvicorn` (o que `make dev` usa de verdade)
sempre esteve correto — só os scripts de dev/test estavam trocados.

**Efeito real:** `dilithium-py` (assina `receipt_pqc` ML-DSA-87) nunca foi instalada
NESTE venv — `sign_receipt()` no servidor real caía em `except ImportError` e devolvia
`intent_id` puro como "receipt", sem assinatura criptográfica nenhuma, mesmo com os
testes "passando" (porque os testes rodavam no outro venv, que tinha a lib). Ou seja:
o diferencial de Innovation (PQC) parecia pronto mas não funcionava de verdade.

Corrigido: shebangs reescritos pra apontar pro python3 correto deste `.venv`,
`dilithium-py` instalada aqui, suíte inteira revalidada (322 passed, mesmo resultado
de antes — confirma que os testes já testavam o código certo, só com libs erradas).
PQC real testado manualmente: assinatura + verificação ML-DSA-87 válidas,
`PQC_SECRET_KEY`/`PQC_PUBLIC_KEY` do `.env` carregam corretamente via `server.settings`.

---

### P0-05 — Cobertura de testes ampliada (segurança, spending, fuzzing, métricas) — 01/jul

Suíte foi de 206 → **371 testes passando** (mesmas 5 falhas pré-existentes não
relacionadas em `test_security_regression.py`/`test_xiaolee_mvp_orchestration.py`).
Novos arquivos:

- `test_security_injection.py` + `test_spending_guardrails.py` — payloads maliciosos
  (SQLi-shaped, XSS, unicode, CRLF) tratados como dado inerte; **2 bugs reais achados
  e corrigidos**: (1) `amount_usdc` negativo em `pay_creator_nanopayment` inflava o
  orçamento restante ao invés de ser rejeitado; (2) `amount=Infinity` passava
  `Field(gt=0)` e corrompia `_usdc_total` pra sempre, e `NaN`/`Infinity`/`-Infinity`
  faziam o handler de erro 422 do FastAPI quebrar com **500 não tratado** (Starlette
  serializa JSON em modo estrito) — corrigido com `allow_inf_nan=False` no schema +
  exception handler global que sanitiza floats não-finitos.
- `test_fuzz_traction.py` — Hypothesis sobre o endpoint de settlement e o recibo PQC:
  tamper detection (flip de byte na assinatura/payload sempre invalida), verify_receipt
  nunca crasha com lixo arbitrário, `_canonical` sempre formata 6 casas decimais.
- `test_traction_metrics_correctness.py` — avg/p95 de latência batem com a fórmula de
  referência sob 100-500 pagamentos, feed capado em 20 (snapshot)/`_MAX_FEED` (buffer
  interno) mesmo com 600 eventos, `hydrate_traction` de 1000 linhas roda em <5s.
- `test_agent_routes_and_register_fuzzing.py` — validação de `POST /v1/agent/run-campaign`
  e `POST /v1/creator/register`, `discover_creators` sob 200 participantes. **3º bug real**:
  `RunCampaignRequest.budget_usdc`/`reward_per_creator_usdc` não tinham `Field(gt=0,
  allow_inf_nan=False)` — `budget_usdc=Infinity` passava o guard manual `<= 0` (inf <= 0
  é False) e o agente rodaria com orçamento **efetivamente ilimitado**. Corrigido.
  **Incidente durante o próprio teste**: um payload com `campaign_id=1.0` (coagido pra
  `1` pelo pydantic) escapou da validação e o `BackgroundTasks` do FastAPI — que o
  `TestClient` executa síncrono dentro da mesma chamada — disparou o `ClaudeAgentEngine`
  de verdade contra a API real da Anthropic + Circle live. Pagamentos falharam
  ("Invalid destination address", a Circle rejeitou antes de mover fundos), mas
  consumiu chamadas reais de API sem necessidade. Corrigido isolando o teste com
  `monkeypatch` no `_run_agent_task` — nenhum teste futuro nesse arquivo toca rede real.

- `test_payment_intent_security_and_scoring.py` — mesma resiliência a payload malicioso
  agora em `payment_intents` (a tabela de anti-replay do loop autônomo, não só
  `settled_payments`); limites exatos do score de `evaluate_creator` (30/30/25/15,
  elegível ⟺ score ≥ 50); `ArcClient` sandbox nunca abre conexão de rede real
  (`httpx.AsyncClient` mockado pra falhar se for chamado).

**Também corrigidas as 5 falhas pré-existentes** (não eram bugs de app, eram falhas de
isolamento de teste):
- `test_security_regression.py` (2 testes) — usavam `asyncio.get_event_loop().run_until_complete()`,
  um padrão legado que reaproveita/fecha o event loop do processo; ao rodar depois de
  centenas de outros testes async na suíte completa, o loop já estava fechado.
  Convertidos pra `@pytest.mark.asyncio async def` + `await`, como o resto do projeto.
- `test_xiaolee_mvp_orchestration.py` (3 testes) — `OrchestrationService()` não tinha
  como desligar o `ClaudeAgentEngine` nos testes; com `ANTHROPIC_API_KEY` real
  configurada (desde o P0-02), os testes **chamavam a API real da Anthropic** a cada
  run, ignorando os fakes injetados (`FakeGemini`/`FakeSolana`) — por isso o resultado
  mudava (`action` virava "help" com respostas reais da Xiao). Adicionado parâmetro
  `claude_engine` no construtor (default preserva o comportamento atual em produção;
  testes passam `claude_engine=None` pra forçar o caminho legado Gemini/regras).
  Suíte completa ficou ~2x mais rápida (136s → 72s) sem essas chamadas de rede.

**Total: 206 → 411 testes passando, 0 falhas — meta de 200 testes novos batida
(batches 1-5).**

---

### P1-04 — Deploy staging acessível publicamente
**Owner: f0ntz | ETA: D30**

O hackathon pede "live deployed link (strongly encouraged)".
Sem link, o júri não testa.

```bash
# Railway (já tem config)
railway up --detach

# Ou Docker Compose na VPS
docker-compose up -d
```

Variáveis de ambiente precisam estar no Railway/VPS antes do deploy.

---

## P2 — Innovation (20%) — diferencial de pódio

### P2-01 — ~~PQC na resposta do agente (ML-DSA-87)~~ DONE (verificado 30/jun)
`receipt_pqc` já existe em `PaymentIntent` (`database/models.py:199`) e `creator_pay_tools.py:306`
chama `sign_receipt()` após a transferência, populando `receipt_pqc` na resposta.

**Falta só para o vídeo:** confirmar que `receipt_pqc` aparece no JSON de
`GET /v1/agent/run-campaign/{run_id}/status` durante a gravação e narrar
"pagamento com assinatura pós-quântica ML-DSA-87".

---

### P2-02 — CCTP no vídeo de demo
**Owner: f0ntz | ETA: D02**

`cctp_client.py` é completo e funcional com sandbox. No vídeo: mostrar
`POST /v1/arc/cctp/bridge` bridgeando USDC de Sepolia para Arc.
Não precisa ser transação live — sandbox com log bonito no terminal resolve.

---

### P2-03 — ERC-8004 agent identity (stretch)
**Owner: f0ntz | ETA: D03, só se P0+P1 estiverem verdes**

Se houver tempo: registrar o agente XiaoLee na rede Arc com identidade ERC-8004.
Só adiciona ao Innovation 20% — não bloqueia nada.

---

## P3 — Submissão (D05-D06)

### P3-01 — Vídeo demo ≤ 3min
**Owner: f0ntz + Mari | ETA: D04-D05**

Roteiro (story board):
1. **0:00–0:20** — problema: creators não recebem pelo conteúdo
2. **0:20–0:50** — XiaoLee: agente descobre creators → avalia → paga USDC sem fricção
3. **0:50–1:40** — demo ao vivo: `Run Agent` → 3 pagamentos USDC na tela → feed SSE atualiza
4. **1:40–2:10** — inovação: PQC receipt no JSON + CCTP bridge
5. **2:10–2:40** — tração: X creators, Y USDC pagos, dashboard ao vivo
6. **2:40–3:00** — call to action: GitHub + link live

Gravar no Loom (gratuito, link público imediato).

---

### P3-02 — README público mapeado aos critérios do hackathon
**Owner: Jeiel | ETA: D05**

O README precisa ter uma seção "How XiaoLee scores on Lepton criteria" **no topo**
(logo abaixo do título/tagline) — é o primeiro contato do júri, e se não for óbvio
em segundos como o XiaoLee mapeia os 4 critérios, o júri passa para o próximo projeto.

Bloco pronto para colar no README (paths já verificados contra o código em 01/jul):

```markdown
> **Live on Arc testnet:** X creators paid · $Y.YY USDC settled · avg latency Zms
> [Live demo](<URL>) · [Video demo](<LOOM_URL>) · [Submit form](https://forms.gle/SMqLaw2pMGDe58LFA)

## How XiaoLee scores on Lepton criteria

| Criterion | Weight | How XiaoLee addresses it | Evidence |
|---|---|---|---|
| **Agentic** | 30% | `ClaudeAgentEngine`: autonomous discover → evaluate → pay loop. No human in the loop — the agent decides which creators to pay and how much, within budget constraints. | `backend/claude_agent.py`, `POST /v1/agent/run-campaign` |
| **Traction** | 30% | Creators onboarded and USDC settled on Arc testnet during the event window, exposed live via a stats/feed API and Grafana dashboard. | `GET /v1/traction/stats`, `GET /v1/traction/feed` (SSE), `backend/server/traction_routes.py` |
| **Circle Tools** | 20% | Circle W3S developer wallets for USDC payouts, x402 HTTP 402 nanopayments on Arc, CCTP bridge to move USDC from Sepolia to Arc, App Kit for the frontend wallet. | `backend/server/integrations/arc_client.py`, `backend/server/routes/arc_x402_routes.py`, `backend/server/integrations/cctp_client.py` |
| **Innovation** | 20% | ML-DSA-87 (NIST FIPS 204) post-quantum signatures on every payment receipt, plus CCTP cross-chain funding and agent-to-agent identity (ERC-8004, stretch). | `backend/services/pqc_receipt.py`, `backend/server/routes/trust_routes.py` |

### Quick start for judges

\`\`\`bash
# x402 on Arc — should return HTTP 402 with "network":"arc","asset":"USDC"
curl -X POST https://<URL>/v1/arc/ai/query \
  -H "Content-Type: application/json" \
  -d '{"message":"hello"}'

# Traction stats — creators paid, USDC settled, latency
curl https://<URL>/v1/traction/stats
\`\`\`
```

**Antes de colar no README:**
1. Preencher `<URL>` (link do deploy — depende de P1-04) e `<LOOM_URL>` (depende de P3-01)
2. Preencher X (creators) e $Y.YY (USDC settled) no banner — depende de P1-01/P1-02
3. Rodar os dois `curl` contra o staging real para confirmar que retornam o esperado antes de publicar

**Critério de aceite:**
- [ ] Seção "How XiaoLee scores on Lepton criteria" no topo do README
- [ ] Banner de tração com números reais (preencher após P1-01)
- [ ] Quick start com comandos curl que o júri pode executar
- [ ] Link para vídeo demo (preencher após P3-01)
- [ ] Link para formulário de submissão

---

### P3-03 — Submissão
**Owner: f0ntz | ETA: 6 jul antes das 20h ET**

- [ ] Repo GitHub público (sem secrets no histórico)
- [ ] Vídeo no Loom/YouTube (link público)
- [ ] Link live deployado
- [ ] Formulário: `forms.gle/SMqLaw2pMGDe58LFA`
- [ ] Métricas de traction capturadas (screenshots do dashboard + total USDC)

---

## Responsabilidades por pessoa

| Task | f0ntz | Jeiel | Mari |
|------|-------|-------|------|
| P0-01: Registrar arc_x402 | X | | |
| P0-02: Circle credentials | X | | |
| P0-03: Fix pytest env | X | | |
| P1-01: Primeira tx USDC real | X | X | |
| P1-02: Onboarding creators | | | X |
| P1-03: Dashboard ao vivo | | | X |
| P1-04: Deploy staging | X | | |
| P2-01: PQC no fluxo do agente | X | | |
| P2-02: CCTP no vídeo | X | | |
| P3-01: Vídeo demo | X | | X |
| P3-02: README público | | X | |
| P3-03: Submissão | X | | |

---

## Timeline comprimida (8 dias)

```
D29 (hoje dom)  f0ntz: P0-02 Circle credentials reais + P1-04 deploy staging
D30 (seg)       f0ntz+Jeiel: P1-01 primeira tx USDC real | Mari: P1-02 onboarding
D01 (ter)       Mari: P1-03 dashboard | f0ntz: P2-01 PQC no fluxo
D02 (qua)       Jeiel: loop a2a | f0ntz: P2-02 CCTP demo prep
D03 (qui)       integration freeze — tudo rodando junto no staging
D04 (sex)       buffer traction — mais creators, mais USDC fluindo
D05 (sáb)       f0ntz+Mari: vídeo roteiro + gravação | Jeiel: README
D06 (dom 5 jul) edição vídeo + dry-run submissão
D07 (seg 6 jul) SUBMISSÃO até 20h ET
```

---

## Critérios de sucesso (o que o júri precisa ver)

Para Grand Prize (1st — $10k):
- [x] Agente autônomo com loop real de decisão (não chatbot)
- [x] 10+ transações USDC reais no testnet Arc durante o evento (16 tx, $3.55, 29/jun)
- [ ] Dashboard ao vivo mostrando USDC fluindo (feed agora persiste — falta validar visualmente em staging)
- [ ] x402 on Arc respondendo 402 → pagamento → 200
- [x] PQC receipt no JSON de resposta (`creator_pay_tools.py` → `receipt_pqc`)
- [ ] CCTP demonstrado (mesmo em sandbox)
- [ ] Vídeo ≤ 3min com demo ao vivo
- [ ] README mapeado aos critérios

Para Standout ($650–750, mínimo aceitável):
- [x] Código funcionando com Circle tools
- [x] Pelo menos 1 transação USDC real
- [ ] Vídeo demonstrando o loop
