# Consistência & Melhoria — XiaoLee

Criado em: **2026-07-09**
Status: vivo — este doc é reverificado contra o código a cada rodada, não é uma foto única
Escopo: personalidade da IA (eixo 1) + consistência de produto/UX (eixo 2)

---

## 0. Como este documento funciona

Isso não é um plano estático — é o rastreador de consistência do XiaoLee. Regras de uso:

1. **Cada item tem um DoD (Definition of Done) checável.** Nada de "melhorar a personalidade" solto — cada linha do checklist tem que dar pra marcar sim/não olhando o código ou testando na mão.
2. **Toda vez que alguém (Gustavo, Claude, o time) reabrir este doc para trabalhar em um item, revalida contra o código atual antes de confiar no status** — memórias e docs anteriores no repo já provaram que ficam obsoletos rápido (ver `SPRINT_STATUS.md`).
3. **Tabela de status (seção 1 e 2) usa RAG:** 🔴 não iniciado / 🟡 em andamento ou parcialmente verificado / 🟢 DoD cumprido e verificado.
4. **Todo update relevante vai para o Log (seção 5)** — data, o que mudou, quem/o que verificou.
5. Este doc **não duplica** planos de UX já existentes (`FRONTEND_CONSISTENCY_PLAN.md`, `ROADMAP_INTEGRACAO_FRONTEND.md`) — ele referencia e adiciona uma camada de DoD/rastreamento por cima.

---

## 1. Eixo 1 — Personalidade da IA (a "waifu fofa e esperta")

### 1.1 Diagnóstico (verificado em 2026-07-09, direto no código)

O motivo da personalidade ter "sumido" não é impressão — é rastreável. Existem **três definições de persona diferentes no código, e a única que está de fato no ar não define personalidade nenhuma**:

| Arquivo | Conteúdo | Está no ar? |
|---|---|---|
| `backend/ai/prompts.py::get_base_system_prompt()` | Versão mais rica: flerte leve, "degen culture" (bags/moon/wagmi), `play_animation` obrigatório em quase toda resposta | **Não.** `grep` não encontra nenhum caller — código morto desde o commit inicial. |
| `backend/ai/response_generator.py::_build_dynamic_system_prompt()` (+ toda a classe `ResponseGenerator`) | Versão intermediária: "cheerful crypto waifu", emojis, mas sem flerte/degen; `play_animation` restrito a "hello/celebration only" | **Não.** `ResponseGenerator` só é importado por `backend/flask_api/*`, que é o app Flask legado — não roda em nenhum lugar (`Makefile`, `railway.toml`, Dockerfile só sobem `server.app:app` via uvicorn). |
| `backend/server/orchestration/service.py::_build_agentic_system_prompt()` + `_PLATFORM_CONTEXT` | Descreve capacidades técnicas (Arc, CCTP, x402, PQC) em tom neutro. Diz literalmente "responda com sua personalidade" **sem nunca definir essa personalidade** — zero menção a tom, emojis, cheerful, flerte, nada. | **Sim.** `app.py:270` instancia `OrchestrationService`, e `/chat` (endpoint que o frontend usa), o webhook do Telegram e o poller do Twitter passam todos por `_process_inbound → orchestrator.execute()`. Esse é o único caminho vivo. |

**Conclusão:** a persona rica foi escrita duas vezes (com força decrescente) e nenhuma das duas versões acompanhou o pivot pra arquitetura Arc/multi-chain (commit `6fa44c0`, "persona por wallet"). O prompt que está de fato respondendo hoje não tem nenhuma instrução de tom — o "cheerful bubbly waifu" que sobrou é só o que o modelo infere do nome "XiaoLee" sozinho, sem reforço. Prova extra encontrada no próprio código: o handler de `greeting` (linha ~938) já dizia "Dê as boas-vindas **com a personalidade completa da XiaoLee**" — uma referência a uma personalidade que, até esta correção, nunca tinha sido de fato definida em nenhum prompt vivo.

Achados secundários:
- **Não é um só modelo — são dois, mas não em partes iguais.** Correção sobre uma nota anterior deste doc: `execute()` tenta o loop agentic do Claude (`_execute_agentic`/`ChatAgentEngine`, Claude Sonnet 4.6) **primeiro, por padrão**, para qualquer mensagem — só desvia pra Gemini quando `_detect_arc_intent()` reconhece um dos poucos padrões determinísticos bem específicos (pagar creator, descobrir creators, rodar campanha do agente, "check budget"/orçamento) **ou** quando a chamada ao Claude lança exceção (fallback de erro). Ou seja: `self.gemini.generate_reply()` não é "a maioria das conversas" — é uma rota estreita para um punhado de intents do agente Arc/Circle mais um fallback de indisponibilidade. Na prática, saudação, perguntas gerais, saldo e swap (o grosso do volume de chat) passam pelo Claude. Isso foi confirmado testando as 5 mensagens do DoD: todas bateram no mesmo caminho (`_execute_agentic`). A base `_PLATFORM_CONTEXT` é compartilhada pelos dois (17 pontos de uso no arquivo), então mesmo a fatia menor que usa Gemini já herda a correção de tom.
- **O sistema de animação visual está 100% desconectado, não só subutilizado.** `play_animation` (`backend/ai/mcp_tools.py`) tem descrição restritiva (*"Do NOT use for educational responses or general conversations"*) **e nem está na lista de tools do caminho vivo** (`STELLAR_AGENT_TOOLS` em `orchestration/service.py` só tem `arc_get_usdc_balance`, `stellar_get_balance`, `stellar_swap_quote`). Pior: o endpoint `/chat` (`app.py`) retorna `"animations": None` **hardcoded**, sempre — mesmo que o backend algum dia chame a tool. O frontend (`ChatPanel.tsx:229`, `Video.tsx`, `MiniAvatar.tsx`) já tem toda a lógica pronta pra tocar os vídeos (`response.animations !== null` → `Video.setPfp(...)`), só nunca recebe o sinal. Os 13 assets (`frontend/public/xiaolee_*.mov|mp4`: Hello, Kawaii, Love, Cheer, Giggle, Salute, Ouch, Uncomfortable, Surprise, ThinkLow + standbys) estão intactos, esperando. **Isso é um item separado do DoD (1.2), ainda não corrigido nesta rodada** — é sobre expressão visual, não sobre o texto do prompt.
- Não há fragmentação entre canais (web/Telegram/Twitter) — todos passam pelo mesmo `OrchestrationService`, então corrigir o prompt ali corrige os três de uma vez.

### 1.1.1 Correção aplicada em 2026-07-09

Editado `_PLATFORM_CONTEXT` em `backend/server/orchestration/service.py` — adicionado um bloco `PERSONALITY:` fundindo o tom da versão rica (`prompts.py`, código morto): cheerful, bubbly, flerte leve, degen culture opcional (bags/moon/wagmi), emojis com moderação, sem markdown/asteriscos, respostas concisas. O restante do bloco (capacidades técnicas Arc/CCTP/x402/PQC, regras de wallet/chain) foi mantido palavra por palavra — só a camada de tom foi adicionada por cima.

**Validado manualmente** (backend local, 5 mensagens variadas via `/chat`): saudação casual, pergunta sobre campanhas/$XLEE, pergunta técnica sobre CCTP em inglês, saldo sem wallet conectada, saldo com wallet conectada (aciona o loop agentic do Claude). Tom cheerful/warm consistente nas 5, em PT-BR e EN, sem exagero de emoji, explicações técnicas mantidas precisas. Suite completa do backend rodada (`pytest tests/`): **450 passed, 6 skipped**, zero regressão.

Único ponto observado sem ser bloqueante: a resposta do caminho Claude/agentic (saldo com wallet conectada) usou `**negrito**` markdown apesar da instrução de evitar — o texto de `_PLATFORM_CONTEXT` chega no Claude, mas o hábito de bold pode precisar de reforço extra nesse caminho especificamente. Não corrigido ainda, fica registrado para não perder o achado.

### 1.1.2 Animações reconectadas (2026-07-09)

Antes de reconectar, validado com o Gustavo que isso não afeta o layout responsivo do front (feito pela Mari): `AnimePanel` (painel grande, só desktop — `hidden lg:flex`) e `MiniAvatar` (avatar pequeno no header, só abaixo de `lg`) são componentes visuais diferentes, mas **os dois escutam o mesmo serviço singleton `Video`** (`frontend/src/components/Video.tsx`, via `Video.subscribe`/`Video.setPfp`). Reconectar o sinal do backend não toca nenhum arquivo de layout/breakpoint — só faz `Video.setPfp(...)` receber chamadas reais em vez de nunca ser invocado por esse caminho.

Achados que precisaram de correção antes de religar (a razão de checar antes de agir):
1. **Bug de typo no front:** `ChatPanel.tsx` mapeava `Uncomfortable` para o arquivo `xiaolee_unconfortable.mov`, mas o arquivo real é `xiaolee_uncomfortable.mov`. Corrigido (1 linha).
2. **Catálogo do backend maior que o suportado pelo front:** `config.py::ACTION_VIDEO_MAP` tem aliases (`Happy`, `Excited`, `Confused`, `Thinking`, `Standby*`, `wave`) que o front não tem no seu mapa `actions`. Em vez de inflar o front pra cobrir tudo, restringi o enum exposto ao modelo no caminho vivo a exatamente os 10 nomes que o front já suporta corretamente (`_ANIMATION_NAMES` em `orchestration/service.py`) — menor superfície, sem inventar cobertura nova.

Mudanças feitas:
- `backend/server/orchestration/service.py`: adicionada a tool `play_animation` a `STELLAR_AGENT_TOOLS` (antes só tinha `arc_get_usdc_balance`, `stellar_get_balance`, `stellar_swap_quote` — a tool nem estava disponível no caminho vivo); executor captura `animation_name` e injeta em `execution["animation"]`; `_build_agentic_system_prompt` ganhou uma linha descrevendo quando usar a tool.
- `backend/server/app.py`: `/chat` não retorna mais `"animations": None` hardcoded — agora lê `result.execution.get("animation")`.
- `frontend/src/components/ChatPanel.tsx`: typo corrigido (`Uncomfortable`).

**Validado**: suite completa (`pytest tests/`, 450 passed / 6 skipped) + teste manual real via `/chat` local (backend rodando, chamada de verdade ao Claude):
- Saudação ("oii, bom dia!") → `execution.animation = "Hello"`, `animations: "Hello"` na resposta.
- Saldo com wallet conectada → `execution.animation = "Cheer"`, `animations: "Cheer"` na resposta.

Ambos os nomes batem com chaves existentes no `actions` do front, então `Video.setPfp` resolve para um arquivo real dos dois lados (`AnimePanel` e `MiniAvatar`).

**Escopo intencionalmente não coberto nesta rodada:** a fatia de conversa que passa pelo Gemini (`generate_reply`, ver 1.1.1) não tem tool-calling — não recebe sinal de animação. Como essa fatia é pequena (intents específicas do agente Arc/Circle + fallback de erro, não o grosso do chat), ficou de fora por ora; se quiser cobertura ali também, precisa de uma abordagem diferente (heurística por intent, já que `generate_reply` não suporta tools hoje).

### 1.1.3 Reconciliação com `origin/main` (2026-07-09, antes do commit)

Antes de commitar, descoberto que a branch local (`feature/f0ntz-trust-arc-live`) estava **5 commits atrás** de `origin/main` — e 3 deles no mesmo `_PLATFORM_CONTEXT`/`STELLAR_AGENT_TOOLS` que esta sessão editou:

- `8df6c69` (6 jul, Gustavo) — **já tinha corrigido o mesmo problema de tom**, e de forma mais completa que a edição inicial desta sessão: bane `##`/`---`/tabelas/menu de bullet points, regra explícita de anti-alucinação de saldo/tx hash, respostas curtas (1-4 frases). Confirma o diagnóstico de 1.1 (o prompt vivo não tinha tom) e mostra que já tinha sido identificado e corrigido de forma independente 3 dias antes desta sessão.
- `78e6340` + `bdc0bf8` — tool `list_campaigns` cabeada no agente Claude, com regra anti-catálogo (respostas de lista viram prosa corrida, não bullet list).

**Reconciliação feita:** `git merge --ff-only origin/main` pra trazer os 5 commits, depois reaplicado o trabalho desta sessão (stash) por cima. Na versão de `_PLATFORM_CONTEXT`, a base de `8df6c69` foi mantida (é mais completa e já testada) e só a camada flerte/degen (`"A little flirty and degen at heart..."`) foi inserida por cima, sem remover nenhuma das regras anti-markdown/anti-alucinação já existentes. A tool `play_animation` (trabalho novo, sem equivalente em `origin/main`) foi adicionada à lista já existente (que agora também tem `list_campaigns`). `ChatPanel.tsx` também tinha uma mudança de outro commit (`e250a33`, fallback de gas EIP-1559) em linhas diferentes — sem conflito real, mesclou limpo.

Revalidado depois da reconciliação: suite completa (450 passed / 6 skipped) + teste manual via `/chat` (saudação → tom curto/caloroso + animação Hello; pergunta sobre campanhas → `list_campaigns` respondendo em prosa corrida, não catálogo).

### 1.1.4 Código morto arquivado (2026-07-10)

Confirmado por `grep` que os 3 alvos não têm nenhum caller vivo:
- `backend/ai/prompts.py::XiaoLeePrompts` (toda a classe, não só `get_base_system_prompt`) — único consumidor era `response_generator.py`.
- `backend/ai/response_generator.py` (`XiaoLeeResponseGenerator` inteiro) — único consumidor era `flask_api/*`. O fallback Gemini de produção usa `server/integrations/gemini_client.py`, um arquivo diferente — confirma que `response_generator.py` não é "o Gemini" que roda hoje.
- `backend/flask_api/` (`chat_app.py`, `chat_routes.py`, `dm_listener.py`, `cors_config.py`) — sem entrypoint (`Makefile`, `railway.toml`, `Dockerfile` só sobem `server.app:app` via uvicorn).

Decisão do Gustavo: **arquivar, não deletar** (recuperar depois se precisar, com mais tempo pra revisar). Adicionado header de 6-8 linhas no topo de cada arquivo (`prompts.py`, `response_generator.py`) e um `README.md` + header de 1 linha em cada arquivo de `flask_api/`, todos apontando pra este doc. Nada foi deletado, nenhum import foi alterado — mudança é só de comentário, então não roda suite pra validar (não há comportamento novo).

Nota: `backend/chat_agent.py` (`ChatAgentEngine`) é **diferente** e está **vivo** — é o loop agêntico do Claude usado por `orchestration/service.py:187`. Não confundir com `claude_agent.py`/`ClaudeAgentEngine` (loop de pagamento do rail Arc, ainda não existe) nem com o `response_generator.py` arquivado acima, mesmo que o docstring de `chat_agent.py` mencione `response_generator` como "fallback" — essa menção está desatualizada, o fallback real é `gemini_client.py`.

Pendências que ficaram fora desta rodada (não pedidas): decidir se `flask_api/` vira de fato exclusão depois de mais tempo pra revisar, script órfão `backend/scripts/db/test_mcp_migration.py` que ainda importa `response_generator` (não é coletado pelo pytest — `testpaths = tests` — mas quebra se rodado direto).

### 1.1.5 Telegram e Twitter/X testados (2026-07-10)

Mapeado antes de testar: Telegram roda hoje via **poller** (long-polling, `server/integrations/telegram_poller.py`, ativo por padrão via `TELEGRAM_POLLER_ENABLED`), não webhook puro — mas a rota `POST /v1/integrations/telegram/webhook` também existe e é funcional. X/Twitter roda via **poller** de scraping (`server/integrations/x_poller.py`, lib Node não-oficial), mas está **desativado neste ambiente** por falta de credenciais (`TWITTER_USERNAME`/`PASSWORD` ou cookies não configurados) — só loga aviso e não faz nada. Os dois pollers e as duas rotas de webhook convergem no mesmo hub `_process_inbound` → `orchestrator.execute(..., platform=...)` (`server/app.py`), então testar via webhook é fiel ao caminho real.

**Teste executado:** backend local (`TELEGRAM_POLLER_ENABLED=false` só nesta sessão de teste, pra não interferir), 3 mensagens por canal batendo direto em `/v1/integrations/telegram/webhook` (header `X-Telegram-Bot-Api-Secret-Token` real) e `/v1/integrations/x/webhook` (HMAC-SHA256 real com `X_WEBHOOK_SECRET`) — saudação casual, pergunta sobre campanhas, frustração de transação.

Resultado: tom idêntico ao já validado no web/produção nos dois canais — cheerful/warm, emoji moderado, empatia genuína na frustração (`animation: "Ouch"` disparando certo), saudação com `animation: "Hello"`. Confirmado também que a validação de segurança bloqueia de verdade: Telegram sem secret → `401`, X com assinatura inválida → `401` (não é `_validate_*` decorativo).

Achado não-bloqueante repetido (já visto em 1.1.1): a resposta sobre campanhas usou `**negrito**` markdown apesar da instrução de evitar — mesmo padrão observado antes no caminho Claude/agentic, não é regressão nova, fica registrado.

Suite completa revalidada depois do teste: `pytest tests/` → **450 passed, 6 skipped**, zero regressão (inclui os headers de arquivamento do item 1.1.4).

Verificado: **Claude — leitura de `telegram_poller.py`, `x_poller.py`, `app.py` (rotas de webhook), `.env`; backend local real com `TELEGRAM_POLLER_ENABLED=false`; 6 chamadas via `curl` direto nos webhooks reais (secret/HMAC do `.env`) + 2 chamadas de rejeição (401); `pytest tests/` completo.**

### 1.1.6 Animação coberta no caminho Gemini (2026-07-10)

**Motivo de ser diferente do caminho Claude:** `self.gemini.generate_reply()` é geração de texto puro — sem function calling. O Gemini nunca teve como "decidir" chamar `play_animation` do jeito que o Claude decide, porque essa chamada nunca expõe tools pra ele. Solução: mapeamento **determinístico** por branch em `execute()` (`orchestration/service.py`) — cada `if intent.action == ...` já sabe em código se foi sucesso, erro, saudação etc. (é o que já vira `execution["status"]`), então a animação é decidida pela lógica, não pelo modelo.

**Achado que mudou o escopo do trabalho:** ao investigar quais branches são de fato alcançáveis, ficou claro que a maior parte do caminho Gemini (`stellar_balance`, `check_balance`, `swap_quote`, `campaign_info`, `greeting`, help fallback) só é alcançada quando o Claude lança exceção (fallback de erro) ou `claude_engine is None` — no dia a dia com `LLM_PROVIDER=anthropic` configurado, essas mensagens vão pro Claude primeiro. Os branches **realmente exercitados em operação normal** são os de `_detect_arc_intent` (`evm_transfer_prepare`, `check_budget`, `pay_creator`, `discover_creators`, `run_campaign_agent`), que desviam do Claude ANTES dele rodar. Cobri os dois grupos:

Mapeamento aplicado (restrição: só em sucesso/erro/saudação claros, igual à régua do Claude — "não para toda resposta"):
- `stellar_balance` sucesso → `Cheer` · erro RPC → `Ouch` · sem wallet → sem animação (pedido neutro)
- `stellar_swap` sucesso (quote encontrado) → `Cheer` · sem liquidez → sem animação · exceção → `Ouch`
- `check_balance` (Solana) sucesso → `Cheer` · sem wallet → sem animação
- `swap_quote` (Jupiter) sucesso → `Cheer`
- `evm_transfer_prepare` tx pronta → `Cheer` · `ARC_USDC_ADDRESS` não configurado → `Ouch` · info faltando/bridge indisponível → sem animação (pedido neutro)
- `check_budget` com saldo real da treasury buscado com sucesso → `Cheer` (reveal positivo, mesma lógica do saldo) · `run_campaign_agent`/`discover_creators`/`pay_creator`/explicação genérica → sem animação (são explicativos, não um resultado)
- `campaign_info` → `Cheer` (a própria instrução já pede entusiasmo) · `greeting` → `Hello` · help/fallback genérico → sem animação

**Validado:**
- Os 2 branches realmente alcançáveis em operação normal (`check_budget` com treasury real, `evm_transfer_prepare` sucesso) testados via `curl` em `/v1/messages/inbound` no backend local — `animation: "Cheer"` nos dois, confirmado.
- Os branches só alcançáveis via fallback de erro/`claude_engine=None` (`check_balance`, `swap_quote`, `campaign_info`, `greeting`, help) testados com um script Python usando o mesmo padrão dos testes existentes (`OrchestrationService(..., claude_engine=None)`, replicando `tests/test_xiaolee_mvp_orchestration.py`) — resultado bateu 100% com o mapeamento: `Cheer`/`Cheer`/`Cheer`/`Hello`/`None` respectivamente.
- Suite completa revalidada: `pytest tests/` → **450 passed, 6 skipped**, zero regressão (inclui os testes existentes `test_detect_balance_intent_with_wallet` e `test_detect_swap_quote_intent`, que já cobriam 2 desses branches e continuaram passando com a chave `animation` nova no dict).

Verificado: **Claude — edição em `server/orchestration/service.py` (10 pontos de retorno), leitura de `_detect_arc_intent`/`execute()` pra mapear alcançabilidade real de cada branch, backend local real + `curl`, script Python ad-hoc reaproveitando o fixture `FakeGemini`/`FakeSolana` dos testes existentes, `pytest tests/` completo.**

### 1.2 DoD — Eixo 1

- [x] **Fonte única de verdade.** Existe um só lugar no código que define a personalidade do Xiao Lee (tom, emojis, limites do flerte, vocabulário): `_PLATFORM_CONTEXT` em `orchestration/service.py`. As outras definições (`prompts.py::get_base_system_prompt` + resto de `XiaoLeePrompts`, `response_generator.py` inteiro, `flask_api/` inteiro) foram **arquivadas com header/README explícito** apontando pra este doc — decisão: arquivar, não deletar (ver 1.1.4), pra ajustar/remover com calma depois. Feito em 2026-07-10.
- [x] **`_PLATFORM_CONTEXT`/`_build_agentic_system_prompt` (o caminho vivo) inclui definição explícita de tom** — cheerful, bubbly, emojis, flerte leve e degen culture opcional. Feito em 2026-07-09 (ver 1.1.1).
- [x] **`play_animation` reconectado no caminho vivo** — tool adicionada a `STELLAR_AGENT_TOOLS`, executor capturando `animation_name`, `/chat` não zera mais `animations`. Validado com 2 chamadas reais (Hello/Cheer). Feito em 2026-07-09, ver 1.1.2. **Cobertura completa desde 2026-07-10**: caminho Gemini também cobre animação via mapeamento determinístico por branch (ver 1.1.6) — não fica mais restrito ao Claude.
- [x] **Teste manual de consistência**: 5 mensagens variadas testadas em 2026-07-09 (saudação casual, campanhas/$XLEE, pergunta técnica CCTP em EN, saldo sem wallet, saldo com wallet via loop agentic) — tom consistente nas 5. Ver 1.1.1.
- [x] **Persona idêntica nos 3 canais** (web chat, Telegram, Twitter). Testado em 2026-07-10 batendo direto nos endpoints reais `/v1/integrations/telegram/webhook` e `/v1/integrations/x/webhook` (secret/HMAC reais do `.env`, mesmo caminho que poller/produção usam — `platform` flui até `orchestrator.execute()` sem diferença de tom por canal, só contexto de wallet). Ver 1.1.5.
- [ ] `flask_api/` (app Flask legado morto) — decisão explícita: deletar do repo ou deixar documentado como arquivado, para não confundir a próxima pessoa que fizer `grep` por "personality" e cair nele achando que é o caminho vivo (foi exatamente o que aconteceu nesta análise).

**Status:** 🟢 DoD cumprido — tom principal corrigido e validado nos 3 canais (web/Telegram/X), animações cobrindo os dois caminhos (Claude e Gemini), código morto arquivado. Pendências fora do DoD original: decidir se o código arquivado (1.1.4) vira exclusão de vez, e o achado não-bloqueante de markdown (`**negrito**`) ainda aparecendo ocasionalmente no caminho Claude/agentic (ver 1.1.1, 1.1.5).

---

## 2. Eixo 2 — UX / Consistência de produto

Este eixo **não recomeça do zero** — já existem dois planos no repo:

- `docs/FRONTEND_CONSISTENCY_PLAN.md` (30 jun) — consistência visual (landing como referência de design system, ícones, breakpoints, i18n). 6 fases definidas, status "proposta / aguardando execução" na última verificação.
- `docs/ROADMAP_INTEGRACAO_FRONTEND.md` (4 jul, pós c8bf280) — o que o front ainda não consome do backend novo (Arc x402, treasury CCTP, recibos PQC) e o legado Stellar/Phantom a aposentar. Escrito com o deadline do Lepton (6 jul) em mente — **esse deadline já passou (hoje é 9 jul)**, então a priorização por "o que o juiz precisa ver" desse doc está desatualizada; os gaps técnicos listados nele continuam válidos, só a urgência/ordem muda.

Este eixo aqui serve pra **rastrear o DoD** desses dois planos e registrar o que muda depois da última verificação registrada neles (5-6 jul), incluindo o fato de que agora **frontend deixou de ser só domínio da Mari** — o time inteiro (Gustavo incluso) pode mexer, então esse doc para de tratar frontend como "só flag leve".

### 2.1 Estado na última verificação (herdado da memória de sessões anteriores, 4-6 jul — precisa revalidação)

- [x] **Gaps de contrato front↔backend revalidados em 2026-07-10** (ver 2.1.1) — ambos continuam corretos em HEAD (`30d31f0`), sem regressão desde os commits de origem. Duas ressalvas encontradas no processo: a atribuição de commit do fix de `register` na memória estava errada (era `caa3819`/`b8f8bc8`, na verdade é `518206a`), e existe um gap de **cobertura de teste** (não de código) no claim EVM — ver 2.1.1.

#### 2.1.1 Revalidação dos 2 gaps de contrato (2026-07-10)

**Gap 1 — `POST /v1/creator/register` 422 com endereço `0x…`.**
Confirmado resolvido em HEAD, mas **a atribuição de commit na memória estava errada**: o fix real não é `caa3819`/`b8f8bc8` (que tocaram chat/wallet-navbar e o claim, não o register) — é `518206a` (6 jul, "prova de posse no register"), um commit que a memória de sessões anteriores não tinha registrado. Esse commit não só aceitou `0x…` como **endureceu** o endpoint: removeu o campo de texto livre e passou a exigir prova de posse — `_verify_wallet_ownership()` (`backend/server/traction_routes.py:147`) recupera a assinatura EIP-191 (`eth_account.Account.recover_message` + `encode_defunct`) e compara com `wallet_address`; sem `signed_message`/`signature`, retorna **400** (não mais 422) com mensagem clara. `git diff 518206a..HEAD` nos arquivos relevantes (`schemas.py`, `traction_routes.py`) está vazio — zero regressão desde então.
Frontend (`frontend/src/app/onboarding/page.tsx:54`) monta a mensagem assinada no formato exato que o backend espera (`wallet:{address}` presente na string) e usa `connected.wallet.sign()` com `encoding: "eip191"` para wallets EVM — sem drift.

**Gap 2 — `POST /campaigns/claim` sem verificação EVM.**
Confirmado resolvido, integralmente atribuível a `b8f8bc8` como já registrado — `git log`/`git diff b8f8bc8..HEAD -- backend/server/campaigns_routes.py` mostra zero mudança no arquivo desde então. `_verify_claim_proof()` (`campaigns_routes.py:224`) detecta `wallet_public_key` começando com `0x` e valida via `eth_account.Account.recover_message` (EIP-191/`personal_sign`), com Solana (Ed25519) e sessões custodiais (`google_`/`tg_`) continuando a funcionar em paralelo. Frontend (`useCampaignActions.tsx:83` + `evmWallet.ts:77`) monta a mesma string esperada pelo backend e chama `personal_sign` — contrato bate.
**Achado que fica registrado (gap de teste, não de código):** `tests/test_campaign_claim_proof.py` só cobre o ramo Solana/Ed25519 — nenhum teste automatizado exercita o ramo `0x…`/EIP-191 do claim (diferente do `register`, que tem cobertura completa em `test_agent_routes_and_register_fuzzing.py::TestCreatorRegisterEndpoint`, 8 testes incluindo fuzzing). A validação em produção foi feita manualmente (commit menciona "receipt 8e78e073"), mas sem teste de regressão. Recomendação: espelhar `test_claim_reward_accepts_valid_wallet_signature` usando `eth_account.Account.create()` + `personal_sign`, mesmo padrão já usado em `test_agent_routes_and_register_fuzzing.py`. **Não implementado nesta rodada** — fica como item aberto.

**Validado:** os 11 testes relevantes (`TestCreatorRegisterEndpoint` × 8 + `test_campaign_claim_proof.py` × 3) rodados diretamente — todos passando. `git diff` confirmado vazio nos dois casos (sem regressão desde os commits de origem).

Verificado: **Claude — leitura de `traction_routes.py`, `schemas.py`, `campaigns_routes.py`, `useCampaignActions.tsx`, `onboarding/page.tsx`, `evmWallet.ts`; `git log`/`git diff` nos 3 commits (`caa3819`, `b8f8bc8`, `518206a`); `pytest` nos 11 testes relevantes.**

- [x] **Rotas novas do backend ainda não consumidas pelo front — revalidado em 2026-07-10** (ver 2.1.2). Lista original tinha 2 itens obsoletos (já consumidos desde poucas horas após o doc de 4 jul) e 1 premissa imprecisa (item do x402). Lista corrigida abaixo:
  1. `/v1/arc/ai/query` + `/query/payment-info` + `/query/verify-transfer` — x402 na Arc. **Ainda não consumida.** Premissa corrigida: o `/chat` de produção **não usa x402 em nenhuma chain** hoje (nem Stellar nem Arc) — o único código que fala x402 Stellar (`utils/stellar.ts`) só é chamado por `StellarWallet.tsx`, componente **órfão** (confirmado: zero import em qualquer outro arquivo do front).
  2. ~~`/v1/arc/wallet/balance`~~ **já consumida** (`useTreasury.ts` → `TreasuryCard.tsx`, montado em `dashboard/page.tsx`, desde commit `ee30fb1`, 04/jul). `/v1/arc/wallet` (info completa, sem `/balance`) **segue não consumida**. `/v1/arc/cctp/bridge` e `/v1/arc/cctp/status/{hash}` **seguem não consumidas** — atenção ao path real: vivem sob `/v1/arc/cctp/*` (`arc_routes.py`), não `/v1/cctp/*`.
  3. ~~`/v1/cctp/treasury/{chain}/balance`~~ **já consumida** (mesmo `useTreasury.ts`/`TreasuryCard.tsx`, mesmo commit `ee30fb1`). `/v1/cctp/healthcheck` **segue não consumida**.
  4. `/v1/trust/public-key` + `/v1/trust/verify-receipt` (recibos PQC ML-DSA-87) — **ainda não consumida**, confirmado. Nuance nova: `AgentStatus.tsx` já mostra um badge visual "🔐 PQC" quando `receipt_pqc` vem preenchido no status do run, mas é só indicador de presença — não chama `verify-receipt` pra validar a assinatura de fato. "Badge verificado" de `ROADMAP_INTEGRACAO_FRONTEND.md` §2.3 está pela metade.
  5. `/v1/agent/runs` (listagem) — **ainda não consumida**, confirmado idêntico. `useAgentStatus.ts` só usa a consulta individual (`/run-campaign/{id}/status`) e o disparo (`POST /run-campaign`).
- Legado a aposentar: `utils/stellar.ts` inteiro, `StellarWallet.tsx` sem referência, `useXiaoLeeProgram.ts` (Solana), claim via Phantom `signMessage` (substituído por EIP-191 conforme os gaps acima).

#### 2.1.2 Revalidação das rotas não consumidas (2026-07-10)

Achado principal: 2 dos 5 itens da lista ficaram desatualizados **no mesmo dia em que foram escritos** — `ROADMAP_INTEGRACAO_FRONTEND.md` foi commitado às 18:01 de 4/jul (`e48af65`) listando `/v1/arc/wallet/balance` e `/v1/cctp/treasury/{chain}/balance` como "três endpoints prontos que ninguém consome ainda" (§1.4); às 19:59 do mesmo dia (`ee30fb1`, "cockpit cross-chain, treasury...") o front passou a consumir os dois via `frontend/src/hooks/useTreasury.ts` → `TreasuryCard.tsx`, montado em `dashboard/page.tsx`. O doc nunca foi atualizado depois disso — é o tipo de obsolescência rápida que a seção 0 deste doc já avisa que acontece.

Também corrigido um path impreciso: bridge/status CCTP não vivem em `/v1/cctp/*` como a lista sugeria — vivem em `/v1/arc/cctp/*` (`backend/server/routes/arc_routes.py`, `prefix="/v1/arc"`, linhas 299 e 343). `/v1/cctp/*` (sem `/arc/`) é outro router (`cctp_routes.py`) que só tem `/treasury/{chain}/balance` e `/healthcheck`.

Confirmado por spot-check independente (não só o agente de exploração): `grep` direto em `useTreasury.ts` (paths batem), `TreasuryCard` importado e renderizado em `dashboard/page.tsx:6,126`, `StellarWallet.tsx` sem nenhum import em outro arquivo do front (o único hit de "StellarWallet" fora do próprio componente era a função `detectStellarWallets` em `walletProviders.ts` — nome parecido, não relação real), paths dos 3 routers (`arc_x402_routes.py`, `arc_routes.py`, `cctp_routes.py`) conferidos linha a linha.

Verificado: **Claude — leitura de `useTreasury.ts`, `TreasuryCard.tsx`, `dashboard/page.tsx`, `AgentStatus.tsx`, `useAgentStatus.ts`, `arc_x402_routes.py`, `arc_routes.py`, `cctp_routes.py`, `agent_routes.py`; `git log`/`git blame` em `ee30fb1`/`e48af65`; `grep` completo no front pra cada rota.**

#### 2.1.3 Decisão por rota — expor agora / depois / não expor (2026-07-10)

**Premissa da decisão:** o deadline de submissão do Lepton era 6 jul 23:59 ET (`docs/LEPTON_SPRINT_PLAN.md`) — já passou, hoje é 10 jul. Tratando isso como hardening de produto contínuo, não mais urgência de júri/demo. Se a submissão ainda estiver em janela de reavaliação ou houver um re-pitch marcado, a prioridade de 4 e 5 (Innovation/Circle Tools, os dois critérios que essas rotas endereçam) sobe — revisitar se for o caso.

| Rota | Decisão | Por quê |
|---|---|---|
| `/v1/trust/public-key` + `/v1/trust/verify-receipt` | **Agora** | Já existe UI parcial (`AgentStatus.tsx` mostra badge "🔐 PQC" quando `receipt_pqc` está presente) — falta só o último passo, chamar `verify-receipt` pra validar de verdade em vez de só checar presença do campo. Baixo esforço (completar trabalho já começado, não começar do zero) e é o diferencial de Innovation que "nenhum outro time do hackathon vai ter" (`ROADMAP_INTEGRACAO_FRONTEND.md` §2.3). |
| `/v1/cctp/healthcheck` | **Agora** | `TreasuryCard.tsx` já existe e já consome as 2 rotas de saldo do mesmo grupo (`arc/wallet/balance`, `cctp/treasury/*`). Adicionar um badge "disabled" quando a flag da chain está off é extensão barata de um componente já construído, não uma feature nova — o `ROADMAP_INTEGRACAO_FRONTEND.md` §1.4 já avisa que essas rotas retornam 503 quando a flag está off e pede tratamento gracioso, que hoje não existe. |
| `/v1/arc/wallet` (info completa, sem `/balance`) | **Não expor por ora** | `/balance` já cobre o que o `TreasuryCard` precisa mostrar. Expor o payload completo sem um caso de uso concreto puxando é acumular superfície sem necessidade — revisitar só se aparecer uma tela que precise de mais que o saldo (ex: metadata da wallet, histórico). |
| `/v1/agent/runs` (listagem) | **Depois** | Nice-to-have de histórico no cockpit — hoje não há nenhuma tela nem user story pedindo "ver todos os runs passados", só o run individual em andamento. Sem urgência, mas vale quando o cockpit crescer. |
| `/v1/arc/cctp/bridge` + `/v1/arc/cctp/status/{hash}` | **Depois** | É a narrativa CCTP (Circle Tools), mas expor no front é uma feature de verdade — usuário escolhe chain de origem, valor, acompanha status — não um fetch a mais num card existente. `P2-02` do sprint plan já tratava isso como "mostrar no vídeo" via terminal/sandbox, não como requisito de UI. Escopo maior que os outros itens, sem bloqueio hoje. |
| `/v1/arc/ai/query` (x402 na Arc) | **Depois — decisão de produto, não só técnica** | Antes de expor isso no front, é preciso decidir *o que* está sendo exposto: hoje o `/chat` de produção não cobra nada do usuário (nem Stellar nem Arc) — ligar x402 nesse fluxo significa paywall em cima do chat principal, uma mudança de UX que muda a experiência central do produto. Alternativa: tratar como API pública pra outros agentes pagarem por query (o uso mais comum de x402 no ecossistema Circle), o que não é uma tela de frontend, é documentação/API surface. Não decidir sozinho qual dos dois caminhos — fica registrado como pendência de decisão de produto, não de esforço técnico. |

Atualiza o DoD do eixo 2: cada rota da lista de 2.1.2 agora tem decisão registrada (nenhuma fica indefinida).

### 2.2 DoD — Eixo 2

- [ ] `FRONTEND_CONSISTENCY_PLAN.md` fases 1-6 com status individual atualizado (o doc original não tem checklist de status por fase — adicionar).
- [x] Cada rota nova listada em 2.1 tem uma decisão registrada: expor no front agora / depois / não expor — não fica indefinida. Feito em 2026-07-10, ver 2.1.3: `agora` (trust/PQC verify, cctp/healthcheck), `depois` (agent/runs, cctp/bridge+status, x402 Arc — este último com nota de que é decisão de produto, não só técnica), `não expor por ora` (`/v1/arc/wallet` sem `/balance`).
- [ ] Legado Stellar/Phantom com decisão explícita por item (manter como fallback, migrar, remover) — não deixar código morto acumulando como aconteceu no eixo 1.
- [ ] Golden path manual sem quebra: login → conectar wallet → chat → ver saldo → participar de campanha → claim/payout. Rodado depois de qualquer mudança de UX, não só no fim.
- [ ] Nenhuma mudança de consistência introduz trade-off que quebre um fluxo existente sem aviso prévio registrado no Log (seção 5) — essa é a régua que Gustavo pediu: consistência sim, quebra não.

**Status:** 🟡 em andamento — gaps de contrato (2.1.1) e rotas não consumidas (2.1.2) revalidados em 2026-07-10; falta decisão por rota (expor/não expor), decisão de legado, `FRONTEND_CONSISTENCY_PLAN.md` com status por fase, e golden path manual.

---

## 3. Modelo de DoD reutilizável

Para qualquer item novo que entrar neste doc, seguir este template:

```
### <nome do item>
- Contexto: <por que isso importa, 1-2 frases>
- Critérios de DoD:
  - [ ] <critério verificável 1>
  - [ ] <critério verificável 2>
- Esforço: baixo / médio / alto
- Risco se não fizer: <consequência concreta>
- Última verificação: <data> — <quem/o que verificou, ex: "Claude, grep + leitura de código">
```

Critério de bom DoD: se alguém sem contexto nenhum consegue olhar o item e checar sim/não sem perguntar "o que isso quer dizer", o critério está bom. Se depende de opinião ("ficou mais bonito"), reescrever.

---

## 4. Riscos / o que não fazer

- **Não** apagar código sem antes confirmar que é mesmo morto (o próprio eixo 1 é prova de que "parece não usado" merece um `grep` antes de decidir — mas depois de confirmado morto, apagar, não deixar acumulando).
- **Não** tratar este doc como substituto do `FRONTEND_CONSISTENCY_PLAN.md`/`ROADMAP_INTEGRACAO_FRONTEND.md` — ele referencia, não duplica. Se um DoD de UX exigir detalhe de execução, o detalhe mora nos docs originais.
- **Não** prometer que a correção do eixo 1 (personalidade) é só "editar um texto" — é editar um texto, mas em um lugar que serve três canais de produção (web/Telegram/Twitter), então qualquer mudança de tom pede o teste manual do DoD antes de dar como pronto.
- **Não** reintroduzir uma quarta fonte de verdade pro prompt de personalidade ao "só adicionar uma variação rápida" em algum lugar novo — se motivo for específico de canal, resolver com contexto injetado, não com um novo bloco de tom paralelo.

---

## 5. Log de atualizações

| Data | O que mudou | Verificado por |
|---|---|---|
| 2026-07-09 | Doc criado. Diagnóstico completo do eixo 1 (3 prompts concorrentes, só 1 vivo e sem persona definida). Eixo 2 herdado de memória de sessões anteriores (4-6 jul), ainda não revalidado nesta sessão. | Claude — leitura direta de `backend/ai/prompts.py`, `backend/ai/response_generator.py`, `backend/server/orchestration/service.py`, `backend/server/app.py`, `backend/ai/mcp_tools.py`, `frontend/public/`, `.env`, `Makefile`/`railway.toml` |
| 2026-07-09 | Persona fundida em `_PLATFORM_CONTEXT` (`orchestration/service.py`). Achado adicional grave: sistema de animação 100% desconectado (`animations: None` hardcoded em `/chat`, tool fora do `STELLAR_AGENT_TOOLS`), não só "subutilizado" como o diagnóstico inicial sugeria. Suite completa rodada: 450 passed / 6 skipped. Teste manual com 5 mensagens variadas confirmou tom consistente. | Claude — edição em `backend/server/orchestration/service.py`, `pytest tests/` completo, `curl /chat` local com 5 mensagens (PT-BR + EN, com e sem wallet) |
| 2026-07-09 | Correção de rota: `execute()` usa o loop Claude por padrão pra quase tudo — Gemini só entra em intents Arc/Circle bem específicas (pagar/descobrir creator, rodar agente, budget) ou como fallback de erro. Nota anterior ("2 modelos, Gemini na maioria") estava imprecisa, corrigida. | Claude — leitura de `_detect_arc_intent`/`execute()`, confirmado testando as 5 mensagens do DoD (todas bateram em `_execute_agentic`) |
| 2026-07-09 | Animações reconectadas no caminho Claude: `play_animation` adicionada a `STELLAR_AGENT_TOOLS`, executor capturando `animation_name` → `execution["animation"]`, `/chat` parou de zerar `animations`. Corrigido também um typo pré-existente no front (`ChatPanel.tsx`: `xiaolee_unconfortable.mov` → `xiaolee_uncomfortable.mov`) e restringido o enum exposto ao modelo aos 10 nomes que o front já suporta (evita expor aliases do backend sem cobertura no front). Validado: suite completa (450 passed) + 2 chamadas reais via `/chat` (saudação → Hello, saldo → Cheer). Confirmado antes de mexer que `AnimePanel` (desktop) e `MiniAvatar` (mobile) escutam o mesmo singleton `Video`, então a mudança de backend não toca o layout responsivo da Mari. | Claude — edição em `orchestration/service.py`, `app.py`, `ChatPanel.tsx`; `pytest tests/` completo; `curl /chat` local com backend real |
| 2026-07-09 | Reconciliado com `origin/main` (5 commits à frente, incluindo o fix de tom de 6 jul e o `list_campaigns`), commitado (`30d31f0`) e deployado: push em `feature/f0ntz-trust-arc-live` e fast-forward + push em `main` → Railway auto-deploy do backend e frontend. Validado **em produção** (não só local): saudação → tom caloroso + `animations: "Hello"`; campanhas → prosa corrida via `list_campaigns` (sem virar catálogo); frustração de transação → empatia genuína + `animations: "Ouch"`; frontend 200 OK. | Claude — `git merge --ff-only`, resolução de conflito, `git push` (branch + main), `railway logs`, `curl` direto em `xiaolee-production-12b3.up.railway.app/chat` (3 mensagens) |
| 2026-07-10 | Fechado o item "fonte única de verdade" do DoD do eixo 1: `prompts.py` (`XiaoLeePrompts`), `response_generator.py` (`XiaoLeeResponseGenerator`) e `flask_api/` inteiro confirmados sem nenhum caller vivo (`grep`) e **arquivados** (não deletados, por decisão do Gustavo — ajustar com mais tempo depois) com header/README apontando pra este doc. Nenhum comportamento mudou (só comentários), não roda suite. | Claude — `grep` completo dos 3 alvos + `Makefile`/`railway.toml`/`Dockerfile`, edição de headers em 6 arquivos + `flask_api/README.md`, ver 1.1.4 |
| 2026-07-10 | Fechado o item "persona idêntica nos 3 canais": Telegram e X/Twitter testados batendo direto nos webhooks reais (secret/HMAC do `.env`), mesmo tom validado no web em 3 mensagens por canal (saudação, campanhas, frustração), animações disparando certo (Hello/Ouch), validação de segurança confirmada (401 em request inválido nos dois). Suite completa revalidada: 450 passed / 6 skipped. | Claude — leitura de `telegram_poller.py`/`x_poller.py`/rotas de webhook em `app.py`, backend local real, `curl` nos 2 webhooks (6 chamadas válidas + 2 de rejeição), `pytest tests/` completo, ver 1.1.5 |
| 2026-07-10 | **Eixo 1 fechado (DoD cumprido).** Animação coberta no caminho Gemini com mapeamento determinístico por branch (10 pontos de retorno em `execute()`) — Gemini não tem function calling, então quem decide a animação é a lógica de código (sucesso/erro/saudação), não o modelo. Achado no processo: a maior parte dos branches Gemini só roda em fallback de erro do Claude, não em operação normal — só os branches de `_detect_arc_intent` (`check_budget`, `evm_transfer_prepare` etc.) são de fato exercitados hoje. Testado via curl (branches reais) e script Python com `claude_engine=None` (branches de fallback, mesmo padrão dos testes existentes). Suite completa: 450 passed / 6 skipped. | Claude — edição em `orchestration/service.py`, `curl` local + script Python ad-hoc, `pytest tests/` completo, ver 1.1.6 |
| 2026-07-10 | Início do eixo 2 (UX). Revalidados os 2 gaps de contrato front↔backend (`register` 422 com 0x, `claim` sem verificação EVM) — ambos continuam corretos em HEAD, zero regressão desde os commits de origem. Corrigida uma atribuição errada na memória (o fix do `register` é `518206a`, não `caa3819`/`b8f8bc8`) e registrado um gap de cobertura de teste real: `/campaigns/claim` com EIP-191 não tem teste unitário dedicado (só Solana/Ed25519 é testado), diferente do `register` que tem 8 testes incluindo fuzzing. 11 testes relevantes rodados, todos passando. | Claude — leitura de `traction_routes.py`/`campaigns_routes.py`/`schemas.py`/hooks do front, `git log`/`git diff` nos 3 commits, `pytest` nos 11 testes relevantes, ver 2.1.1 |
| 2026-07-10 | Revalidadas as 5 rotas "não consumidas pelo front" de 2.1. 2 delas (`/v1/arc/wallet/balance`, `/v1/cctp/treasury/{chain}/balance`) já tinham virado consumidas — `useTreasury.ts`/`TreasuryCard.tsx` no dashboard, desde `ee30fb1` (04/jul, ~2h depois do `ROADMAP_INTEGRACAO_FRONTEND.md` ser escrito). Corrigido também um path impreciso (bridge/status CCTP vivem em `/v1/arc/cctp/*`, não `/v1/cctp/*`) e a premissa do item x402 (chat de produção não usa x402 em nenhuma chain — o código Stellar x402 é órfão). As outras 3 rotas (`arc/ai/query`, `trust/*`, `agent/runs`) seguem confirmadas não consumidas, sem mudança. | Claude — leitura de `useTreasury.ts`, `TreasuryCard.tsx`, `AgentStatus.tsx`, 3 routers de backend, `git log`/`git blame`, `grep` completo no front, ver 2.1.2 |
| 2026-07-10 | Decisão registrada rota a rota (agora/depois/não expor) pra cada item da lista de 2.1.2 — item do DoD do eixo 2 fechado. Premissa: deadline do Lepton (6 jul) já passou, tratado como hardening de produto, não urgência de júri. `Agora`: trust/verify-receipt (UI já parcial em `AgentStatus.tsx`, falta só o wire-up) e cctp/healthcheck (extensão barata do `TreasuryCard` já existente). `Depois`: agent/runs (sem user story hoje), cctp/bridge+status (feature de UI real, não um fetch a mais), x402 Arc (decisão de produto — paywall no chat principal vs. API pública pra outros agentes, não decidido sozinho). `Não expor por ora`: `/v1/arc/wallet` completo (`/balance` já cobre o caso de uso atual). | Claude — leitura de `LEPTON_SPRINT_PLAN.md` pra calibrar prioridade pós-deadline, ver 2.1.3 |

---

## 6. Resumo executivo

A personalidade "sumiu" porque o prompt que está de fato no ar (`_PLATFORM_CONTEXT`, base do loop agentic do Claude, que responde à maioria das mensagens) nunca ganhou definição de tom depois do pivot pra Arc — as duas versões ricas da persona (`prompts.py`, `response_generator.py`) ficaram presas em código morto (a segunda inteira dentro de um app Flask legado que não roda mais). Não é regressão de modelo, é prompt que não acompanhou a arquitetura. **Corrigido em 2026-07-09**: tom fundido em `_PLATFORM_CONTEXT`, validado com 5 mensagens variadas e suite completa (450 passed). **Também em 2026-07-09**: sistema de animação reconectado (estava 100% desligado, não só subutilizado) — `play_animation` agora disponível no loop vivo, `/chat` para de zerar `animations`, validado com chamadas reais (Hello/Cheer). Confirmado que isso não afeta o layout responsivo que a Mari construiu (`AnimePanel`/`MiniAvatar` já compartilhavam o mesmo serviço `Video`) — mas 2 bugs pré-existentes no front (typo de arquivo, catálogo maior que o suportado) precisaram ser corrigidos antes, prova de que valeu a pena checar antes de religar o sinal.

**Em 2026-07-10**: código morto (`prompts.py`, `response_generator.py`, `flask_api/`) arquivado com header/README apontando pra este doc (decisão: arquivar, não deletar ainda). Persona testada e confirmada idêntica nos 3 canais — Telegram e X/Twitter batendo direto nos webhooks reais, mesmo tom do web, animações e validação de segurança funcionando. Suite completa seguiu em 450 passed / 6 skipped o tempo todo.

**Também em 2026-07-10**: caminho Gemini agora cobre animação via mapeamento determinístico por branch (não pode ser o modelo decidindo, já que `generate_reply` não tem function calling) — `Cheer` em sucessos/reveals, `Ouch` em erros, `Hello` na saudação, nada nos branches puramente informativos. **Eixo 1 está com o DoD cumprido** 🟢. Ficam só pendências fora do DoD original: decidir com mais calma se o código arquivado (1.1.4) vira exclusão de vez, e o achado não-bloqueante de `**negrito**` markdown ocasional no caminho Claude/agentic. O eixo 2 (UX) já tem dois planos escritos e ainda não foi tocado — o trabalho ali é dar DoD e revalidação, não recriar.
