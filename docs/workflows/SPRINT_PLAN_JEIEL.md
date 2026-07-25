# Plano de Sprint — Jeiel (Agent Brain Lead)
> Criado em: 2026-06-21 | Hackathon Lepton (Arc/Circle) — deadline: 29 jun
> Critério de nota: **Agentic 30% · Traction 30% · Circle Tools 20% · Innovation 20%**

---

## Contexto Rápido

XiaoLee = agente conversacional que **descobre creators, avalia e PAGA por fração** via
nanopagamento **USDC no Arc (Circle)**. O juiz quer ver USDC saindo de verdade, ao vivo.

**Sua fatia:** Agentic 30% + metade do Innovation (agent-to-agent) = maior fatia de nota.

Branch atual: `feature/agent-brain-lead`

---

## O Que Ainda NÃO Existe (gaps críticos detectados)

| Componente | Status | Prioridade |
|---|---|---|
| `backend/claude_agent.py` (`ClaudeAgentEngine`) | **Não existe** | P0 — é o motor |
| Tools: `discover_creators`, `evaluate_creator`, `check_budget`, `pay_creator_nanopayment` | **Não existem** | P0 |
| Adapter Arc/Circle (USDC payment rail) | **Não existe** | P0 (costura c/ chain) |
| Tabela `payment_intents` (intent log durável, anti-replay) | **Não existe** | P0 |
| Loop autônomo: discover → evaluate → check_budget → pay | **Não existe** | P0 |
| Rota FastAPI para disparar campanha agêntica | **Não existe** | P1 |
| Frontend: painel de status do agente (ao vivo) | **Não existe** | P1 |
| Migração Alembic para `payment_intents` | **Não existe** | P1 |
| Modelos de intenção (intent detection) robustos | **Frágil — dois sistemas desconexos** | P1 |

### O Que Já Existe e Reaproveita

| Componente | Arquivo | O que você usa |
|---|---|---|
| Loop multi-step com tools | `backend/ai/llm_client.py` | `generate_response_with_tools`, `continue_conversation_with_tool_results` |
| Orquestração de tools | `backend/server/orchestration/service.py` | padrão de injeção de wallet/contexto |
| Modelo de campanhas | `backend/database/models.py` (`Campaign`, `CampaignParticipant`) | query de creators inscritos |
| Anti-replay via DB | `backend/database/models.py` (`ProcessedDM`) | mesmo padrão p/ `UsedPayment` |
| Rate limiter Redis | `backend/server/rate_limiter.py` | limitar chamadas ao agente |
| x402 (estrutura de pagamento) | `backend/server/routes/x402_routes.py` | padrão de verificação de tx |
| CMO Architect (agent especializado) | `backend/ai/agents/cmo_architect.py` | padrão de agent com detect/build_prompt |

---

## Cronograma (D = dia do hackathon)

| Dia | Data | Entrega |
|---|---|---|
| **D2** | **Dom 21 (HOJE)** | `ClaudeAgentEngine` + stub das 4 tools (mock `pay_`) + plugar no FastAPI |
| **D3** | Seg 22 | Loop discover→evaluate→pay v1 real (Arc sandbox) |
| **D4** | Ter 23 | Loop a2a autônomo dentro de budget; intent log durável |
| **D5** | Qua 24 | Polir, casos de erro; painel frontend de status |
| **D6** | Qui 25 | Roteiro do vídeo (parte agêntica); ajudar Mari |
| **D7-D8** | Sex-Sáb 26-27 | Buffer + ensaio da demo ao vivo |
| **D9** | Dom 28 | Freeze de código; apenas hot-fixes |
| **D10** | Seg 29 | **SUBMISSÃO** |

---

## Tarefas Detalhadas por Dia

### D2 — Dom 21 (HOJE): Motor + Stubs

#### 1. Criar `backend/claude_agent.py` — ClaudeAgentEngine

Motor do loop agêntico. Padrão:

```python
class ClaudeAgentEngine:
    """Loop nativo Anthropic: chama modelo → executa tool → devolve resultado → repete."""

    def __init__(self, llm: LLMClient, tools: list[dict], max_steps: int = 10):
        self.llm = llm
        self.tools = tools          # formato OpenAI — o engine converte
        self.max_steps = max_steps  # trava de segurança

    async def run(self, prompt: str, context: dict) -> AgentResult:
        """Executa o loop até finish_reason == 'stop' ou max_steps."""
        ...
```

**Regra de ouro:** wallet/budget NUNCA são parâmetros do modelo — vêm injetados pelo executor.

#### 2. Criar `backend/ai/agents/creator_pay_tools.py` — As 4 Tools

```python
# Formato OpenAI (o ClaudeAgentEngine converte para Anthropic)

discover_creators(criteria: dict) -> list[Creator]
# Consulta Campaign + CampaignParticipant (já existem no DB)
# Filtra por engajamento, followers, nicho

evaluate_creator(creator_id: str) -> CreatorScore
# Score 0-100 contra critério RFB-06 da campanha
# Retorna: { score, followers, engagement_rate, niche_match }

check_budget() -> BudgetStatus
# Lê saldo USDC restante na campanha (DB ou Arc API)
# Retorna: { remaining_usdc, max_per_creator, can_pay: bool }

pay_creator_nanopayment(intent_id: str, to: str, amount_usdc: float) -> PaymentReceipt
# COSTURA Agent↔Chain (contrato congelado com f0ntz)
# Escreve intent ANTES de executar (anti-replay)
# Retorna: { tx, receipt_pqc }
```

> `pay_creator_nanopayment` — comece com mock. O f0ntz implementa o rail Arc.
> O contrato do parâmetro é fixo: `intent_id` + `to` + `amount_usdc`. Não mude.

#### 3. Criar rota `/v1/agent/run-campaign` no FastAPI

```python
POST /v1/agent/run-campaign
Body: { campaign_id: int, budget_usdc: float, criteria: dict }
Response: { agent_run_id, steps: [...], payments: [...], status }
```

Adicionar em `backend/server/app.py`.

---

### D3 — Seg 22: Loop Real (Arc Sandbox)

#### 4. Adapter Arc/Circle USDC

Criar `backend/server/integrations/arc_client.py`:

```python
class ArcClient:
    """Wrapper para o Circle Payments API (Arc)."""

    async def send_usdc(self, to_address: str, amount_usdc: float, idempotency_key: str) -> str:
        """Retorna transaction hash. Usa idempotency_key = intent_id para anti-replay."""
        ...

    async def get_balance(self, wallet_id: str) -> float:
        """Saldo USDC disponível na campanha."""
        ...
```

Variáveis de ambiente necessárias: `CIRCLE_API_KEY`, `CIRCLE_WALLET_ID`, `ARC_SANDBOX=true`.

#### 5. Migração Alembic — Tabela `payment_intents`

```python
# backend/alembic/versions/YYYYMMDD_payment_intents.py
class PaymentIntent(Base):
    __tablename__ = 'payment_intents'

    intent_id: str          # UUID, PK, único (anti-replay)
    campaign_id: int        # FK campaigns.id
    creator_id: str         # twitter_handle ou endereço
    amount_usdc: float
    status: str             # pending | submitted | confirmed | failed
    arc_tx_hash: str        # preenchido após submit
    created_at: datetime
    executed_at: datetime   # null até submit
```

Executar: `make db-new-migration MSG="add_payment_intents"` + `make db-migrate`.

#### 6. Ligar `pay_creator_nanopayment` ao ArcClient real

```python
async def pay_creator_nanopayment(intent_id, to, amount_usdc):
    # 1. Gravar intent ANTES (durável)
    await repo.create_payment_intent(intent_id, to, amount_usdc, status="pending")
    # 2. Chamar ArcClient
    tx_hash = await arc_client.send_usdc(to, amount_usdc, idempotency_key=intent_id)
    # 3. Atualizar status
    await repo.update_payment_intent(intent_id, status="submitted", tx_hash=tx_hash)
    return { "tx": tx_hash, "receipt_pqc": intent_id }
```

---

### D4 — Ter 23: Loop Autônomo + Intent Log

#### 7. Loop a2a com trava de budget

O agente deve, em uma única execução, encadear:
```
discover → evaluate → check_budget → pay
```
...repetindo até o budget acabar ou não ter mais creators elegíveis.

```python
async def run_campaign_agent(campaign_id: int, budget_usdc: float) -> AgentResult:
    engine = ClaudeAgentEngine(
        llm=llm_client,
        tools=[discover_creators, evaluate_creator, check_budget, pay_creator_nanopayment],
        max_steps=50,  # trava absoluta
    )
    prompt = f"""
    Você é um agente de marketing que gerencia a campanha #{campaign_id}.
    Budget disponível: ${budget_usdc} USDC.
    Sua missão: descobrir creators elegíveis, avaliá-los, e pagar os melhores dentro do budget.
    Pare quando o budget acabar ou não houver mais creators elegíveis.
    """
    return await engine.run(prompt, context={ "campaign_id": campaign_id, "budget": budget_usdc })
```

#### 8. Durabilidade: restart sem reprocessar

- Ao iniciar, verificar `payment_intents` com `status = "pending"` → tentar resubmit.
- Se a chain cair, enfileirar e responder `"status": "queued"` — não travar o loop.
- Estado sempre no DB, nunca em memória.

---

### D5 — Qua 24: Polimento + Frontend

#### 9. Casos de erro a cobrir

- [ ] Creator já pago nesta campanha (verificar `payment_intents` pelo `creator_id`)
- [ ] Budget insuficiente para o próximo pagamento (check_budget retorna `can_pay: false`)
- [ ] ArcClient timeout → enfileirar, não falhar
- [ ] `max_steps` atingido → log + retornar parcial
- [ ] Intent duplicado (`intent_id` já existe) → idempotente, retornar receipt existente

#### 10. Frontend: Painel de Status do Agente

Em `frontend/src/pages/` ou `frontend/src/components/`, criar `AgentStatus.tsx`:

```tsx
// Mostra ao vivo:
// - Steps executados (discover → evaluate → pay)
// - Lista de pagamentos realizados (creator, amount, tx_hash)
// - Budget restante
// - Status geral: running | completed | failed
```

Conectar ao endpoint `GET /v1/agent/run-campaign/{run_id}/status`.

---

### D6 — Qui 25: Vídeo + Stretch

#### 11. Roteiro do Vídeo (parte agêntica — o que impressiona o juiz)

Cena recomendada:
1. Mostrar campanha criada no dashboard
2. Disparar o agente via `/v1/agent/run-campaign`
3. Mostrar no terminal o loop passo a passo: discover → evaluate → check_budget → pay
4. Mostrar USDC saindo na dashboard do Circle/Arc
5. Mostrar receipt no frontend

#### 12. Stretch — Innovation: Agent-to-Agent (ERC-8004)

Só fazer DEPOIS do core verde:
- Agente A (campanha) negocia com Agente B (creator) via protocolo ERC-8004
- Identidade on-chain para cada agente
- B aceita ou rejeita o pagamento automaticamente

---

## Contratos de Interface (não mudar sem avisar)

### Tool `pay_creator_nanopayment` (congelada)
```python
pay_creator_nanopayment(
    intent_id: str,   # UUID v4, gerado pelo agente
    to: str,          # endereço Arc/Circle do creator
    amount_usdc: float
) -> { "tx": str, "receipt_pqc": str }
```

### Rota de campanha agêntica
```
POST /v1/agent/run-campaign
GET  /v1/agent/run-campaign/{run_id}/status
```

### Tabela `payment_intents` (schema fixo)
Colunas: `intent_id`, `campaign_id`, `creator_id`, `amount_usdc`, `status`, `arc_tx_hash`, `created_at`, `executed_at`

---

## Variáveis de Ambiente Novas

Adicionar ao `.env` e ao Railway:

```bash
CIRCLE_API_KEY=          # Arc/Circle API Key (sandbox)
CIRCLE_WALLET_ID=        # ID da wallet de pagamento USDC
ARC_SANDBOX=true         # false em produção
ANTHROPIC_API_KEY=       # para o ClaudeAgentEngine (se usar Claude nativo)
AGENT_MAX_STEPS=50       # trava de segurança do loop
```

---

## Tarefa: Modelos de Intenção Robustos

> Prioridade P1 — ideal fazer no **D3/D4** junto com o loop, porque o agente depende de
> intenção correta para acionar as ferramentas certas.

### Diagnóstico: O Que Está Frágil Hoje

O projeto tem **dois sistemas de intenção desconexos** que não se falam:

| Sistema | Arquivo | Problema |
|---|---|---|
| `OrchestrationService.detect_intent()` | `server/orchestration/service.py:116` | Keywords hardcoded em inglês + threshold 0.65 arbitrário; sem intents para Arc/USDC/agente |
| `XiaoLeePrompts.get_intent_classification_prompt()` | `ai/prompts.py:38` | Só retorna YES/NO — sem tipo de intenção, sem score, sem contexto |
| `ResponseGenerator` (MAIN_SYSTEM_PROMPT) | `ai/response_generator.py:19` | Terceiro sistema paralelo — deixa o LLM escolher tool sem classificação prévia |

**Bugs concretos encontrados:**

1. **Falso positivo de swap** — a palavra "swap" em "me explica como funciona um swap" dispara intent `swap_quote` (linha `orchestration/service.py:153`).
2. **PT-BR ignorado no fallback** — o fallback regex tem "saldo/balance/quanto tenho" mas a maioria dos sinônimos em português falta.
3. **Sem intents para o sprint Arc** — nenhum dos dois sistemas reconhece `discover_creators`, `run_campaign`, `check_budget`, `pay_creator`. O agente nunca vai ser acionado pelo chat.
4. **`_extract_amount()` frágil** — regex `(\d+(?:[\.,]\d+)?)` captura datas, IDs e qualquer número no texto.
5. **Multi-intenção ignorada** — "checa meu saldo e entra na campanha" produz só uma intenção; a segunda é silenciosamente descartada.
6. **Negação invisível** — "não quero fazer swap" ainda dispara `swap_quote` porque só verifica keywords positivas.
7. **Sem logging de misses** — quando o Gemini retorna confidence < 0.65 e o fallback também falha, cai em `help` sem log. Impossível melhorar sem dados.

---

### O Que Fazer (por ordem de impacto)

#### 13. Adicionar intents Arc/agente ao `OrchestrationService`

Em `backend/server/orchestration/service.py`, dentro de `detect_intent()`, adicionar após o bloco Stellar:

```python
# --- intents do agente Arc (sprint Lepton) ---
arc_keywords_run = ("run campaign", "executar campanha", "disparar agente", "start campaign agent")
arc_keywords_pay = ("pay creator", "pagar creator", "nanopayment", "usdc creator")
arc_keywords_discover = ("discover creators", "buscar creators", "find creators", "encontrar creators")

if any(w in lowered for w in arc_keywords_run):
    campaign_id = self._extract_amount(clean)  # reutiliza extrator de número
    return IntentResponse(action="run_campaign_agent", confidence=0.85,
                          entities={"campaign_id": int(campaign_id) if campaign_id else None})

if any(w in lowered for w in arc_keywords_pay):
    return IntentResponse(action="pay_creator", confidence=0.80, entities={})

if any(w in lowered for w in arc_keywords_discover):
    return IntentResponse(action="discover_creators", confidence=0.80, entities={})
```

#### 14. Corrigir falso positivo de "swap educacional"

Antes de disparar `swap_quote`, verificar se há **verbos de ação** junto com a keyword:

```python
# Só é swap_quote se vier com verbo de ação — não se for pergunta educacional
_SWAP_ACTION_VERBS = re.compile(
    r"\b(quero|queria|faz|faze|faça|make|do|execute|swap|trocar|exchange|convert)\b",
    re.IGNORECASE,
)
_SWAP_QUESTION = re.compile(
    r"\b(o que é|what is|como funciona|how does|me explica|explain)\b",
    re.IGNORECASE,
)

if swap_keyword_found:
    is_question = bool(_SWAP_QUESTION.search(clean))
    has_action = bool(_SWAP_ACTION_VERBS.search(clean))
    if is_question and not has_action:
        # É pergunta educacional → cai no fallback geral
        pass
    else:
        # É intenção de swap real
        return IntentResponse(action="swap_quote", ...)
```

#### 15. Adicionar negação básica

Antes de qualquer match de keyword, checar negação:

```python
_NEGATION_RE = re.compile(
    r"\b(não|nao|no|not|nunca|never|cancel|cancelar|cancela)\b",
    re.IGNORECASE,
)

def _has_negation(self, text: str) -> bool:
    return bool(_NEGATION_RE.search(text))
```

Usar: se `_has_negation(clean)` E a intenção for ação destrutiva (swap, pay), retornar `cancel` em vez de executar.

#### 16. Melhorar `_extract_amount()` — distinguir valores de ruído

```python
def _extract_amount(self, text: str) -> float | None:
    # Prioriza padrões com unidade monetária próxima: "100 USDC", "$50", "5 SOL"
    monetary = re.search(
        r"(\d+(?:[.,]\d+)?)\s*(?:usdc|sol|xlm|usd|\$|reais|brl)",
        text, re.IGNORECASE
    )
    if monetary:
        return float(monetary.group(1).replace(",", "."))
    # Fallback: primeiro número isolado (não precedido por # / data)
    plain = re.search(r"(?<![\#\/\-])\b(\d{1,10}(?:[.,]\d{1,8})?)\b(?![\-\/\#])", text)
    if plain:
        return float(plain.group(1).replace(",", "."))
    return None
```

#### 17. Logging de intent miss para melhoria contínua

Em `detect_intent()`, antes do `return` final de `help`:

```python
logger.warning(
    "intent_miss user=%s confidence=%.2f gemini_action=%s text_preview=%s",
    user_id,
    ai_intent.get("confidence", 0.0),
    ai_intent.get("action", "none"),
    clean[:80],
)
```

Isso permite ver no Grafana/logs quais mensagens estão caindo no `help` sem intenção detectada.

#### 18. Unificar os dois sistemas (refactor leve — só se sobrar tempo)

O ideal seria ter um único `IntentClassifier` que:
1. Tenta Gemini com structured output (JSON schema fixo)
2. Se confidence < threshold → aplica regras deterministas
3. Retorna sempre `IntentResponse` tipado

Mas **não é bloqueador para o hackathon** — fazer D5/D6 se sobrar tempo. O que bloqueia o demo é o item 13 (intents Arc).

---

### Prioridade dos itens desta tarefa

| Item | Impacto no hackathon | Quando fazer |
|---|---|---|
| #13 — Intents Arc/agente | **CRÍTICO** — sem isso o agente não é acionado pelo chat | D3 |
| #14 — Falso positivo swap | Médio — melhora UX do chat | D4 |
| #15 — Negação | Médio — previne execuções não intencionais | D4 |
| #16 — `_extract_amount` | Baixo — edge case | D5 se sobrar |
| #17 — Logging de miss | Alto para melhoria — baixo custo de implementação | D3 junto c/ #13 |
| #18 — Unificação | Refactor longo — não é P0 | D6/stretch |

---

## Checklist Final (antes da submissão)

### Agentic (30%)
- [ ] Loop autônomo: discover → evaluate → check_budget → pay, sem intervenção humana
- [ ] `max_steps` como trava de segurança documentado
- [ ] Agente para sozinho quando budget acaba

### Circle Tools (20%)
- [ ] USDC saindo via Circle/Arc API (não simulado)
- [ ] `idempotency_key` em todos os pagamentos
- [ ] Saldo da carteira Arc lido em tempo real

### Traction (30%)
- [ ] Pelo menos 1 campanha real criada e executada na demo
- [ ] Pagamentos visíveis no dashboard do Circle
- [ ] Frontend mostrando status ao vivo

### Innovation (20%)
- [ ] Intent log durável (restart sem reprocessar)
- [ ] Anti-replay via `UsedPayment` / `payment_intents`
- [ ] [stretch] Agent-to-Agent via ERC-8004

---

## Arquivos a Criar/Modificar

```
backend/
  claude_agent.py                        ← CRIAR (ClaudeAgentEngine)
  ai/agents/creator_pay_tools.py         ← CRIAR (4 tools)
  server/integrations/arc_client.py      ← CRIAR (Circle USDC adapter)
  server/routes/agent_routes.py          ← CRIAR (rota /v1/agent/)
  alembic/versions/YYYYMMDD_payment_intents.py  ← CRIAR (migração)
  database/models.py                     ← MODIFICAR (adicionar PaymentIntent)
  server/app.py                          ← MODIFICAR (incluir agent_router)

frontend/
  src/components/AgentStatus.tsx         ← CRIAR (painel ao vivo)
  src/hooks/useAgentStatus.ts            ← CRIAR (polling/SSE do status)
```

---

## Riscos e Mitigações

| Risco | Probabilidade | Mitigação |
|---|---|---|
| Arc/Circle sandbox instável | Médio | Mock local com flag `ARC_SANDBOX=true`; demo com sandbox |
| Loop infinito / custo LLM | Alto | `max_steps=50` + timeout por step (30s) |
| Creator já pago | Médio | Verificar `payment_intents` antes de pagar |
| Demo ao vivo trava | Médio | Gravar demo prévia; mostrar vídeo se ao vivo falhar |
| Tempo insuficiente p/ frontend | Alto | Priorizar backend; frontend é bonus — logs no terminal já convencem |

---

> **Regra de ouro:** se sobrar dúvida entre features, a prioridade é: **USDC saindo de verdade** > loop autônomo > frontend bonito.
