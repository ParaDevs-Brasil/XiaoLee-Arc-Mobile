# LEIA PRIMEIRO — Time XiaoLee · Sprint Lepton (Arc)

> Mari e Jeiel: bem-vindos ao sprint. **Não leiam os 25 docs.** A maioria é da fase Stellar
> (pré-pivot). Abaixo está o que importa AGORA, na ordem, + o que ignorar.

## Contexto em 30 segundos
XiaoLee = agente conversacional que **descobre creators, avalia e PAGA por fração** via
nanopagamento **USDC no Arc (Circle)**. Estamos no **Lepton Agents Hackathon** (15–29 jun,
pool $50k). Pivotamos de Stellar → Arc. A base de código (loop agêntico + x402 + anti-replay)
**reaproveita ~70%**; só o backend de chain é novo.

**Régua de nota (decora isso):** Agentic 30% · Traction 30% · Circle Tools 20% · Innovation 20%.
Tudo que a gente faz tem que cair numa dessas. O juiz quer ver **USDC saindo de verdade, ao vivo.**

## Ordem de leitura (todos)
1. **`docs/ARC_LEPTON_ARCHITECTURE.md`** ← a fonte da verdade do sprint. Leiam INTEIRO.
2. **`docs/team/WORKFLOW_SEMANA.md`** ← como a semana vai rodar.
3. Seu onboarding: **`ONBOARDING_JEIEL.md`** ou **`ONBOARDING_MARI.md`**.

## Mapa de TODOS os docs (o que é vivo vs arquivo morto)

| Doc | Status | Pra quem |
|---|---|---|
| `ARC_LEPTON_ARCHITECTURE.md` | 🟢 **VIVO — fonte da verdade** | TODOS |
| `team/WORKFLOW_SEMANA.md` | 🟢 VIVO | TODOS |
| `ARCHITECTURE.md` | 🟡 base técnica (era Stellar, padrões valem) | Jeiel |
| `API_REFERENCE.md` | 🟡 endpoints atuais (x402, orchestration) | Jeiel |
| `GTM_XIAOLEE.md` | 🟡 narrativa de produto/creators | Mari |
| `INSTAWARDS_DRAFT.md` | 🟡 modelo de campanha de creator | Mari |
| `XIAOLEE_INVESTOR_TECH_DOC.md` | 🟡 pitch/visão (útil pro vídeo) | Mari (vídeo) |
| `DESIGN_SYSTEM.md` | 🟡 UI/tokens visuais | Mari (dashboard) |
| `RT_XIAOLEE_STELLAR.md` (1090 linhas) | 🔴 era-Stellar, NÃO leiam inteiro | só consulta pontual |
| `MAINNET_READINESS.md`, `SMART_CONTRACT.md` | 🔴 era-Stellar | ignorar no sprint |
| `*.pdf`, `*.docx`, `legacy/`, `qa/` | 🔴 arquivo | ignorar |

### Docs fora de `docs/` (achados na varredura — valem!)

| Doc | Status | Pra quem |
|---|---|---|
| `backend/memory-bank/systemPatterns.md` | 🟡 padrões de arquitetura/código | Jeiel |
| `backend/memory-bank/techContext.md` | 🟡 stack técnica | Jeiel |
| `backend/memory-bank/projectbrief.md` | 🟡 brief do projeto | TODOS (contexto) |
| `backend/memory-bank/productContext.md` | 🟡 contexto de produto | Mari |
| `AUDIT.md` | 🟡 23 findings de segurança corrigidos | Jeiel |
| `README.md` · `CONTRIBUTING.md` | 🟡 setup + convenções | TODOS |
| `Instawards - Bounties (1).docx` | 🟡 versão de bounties | Mari |
| `backend/memory-bank/activeContext.md` · `progress.md` | 🔴 era-Stellar, confunde | ignorar |
| `ops/DEPLOY_MAINNET.md` · `docs/qa/` | 🔴 era-Stellar | ignorar |

> ⚠️ O `memory-bank/` e o `README.md` são **era-Stellar**: servem pra entender *padrões e
> estrutura do código*, mas a verdade do sprint é sempre o `ARC_LEPTON_ARCHITECTURE.md`.

> Regra de ouro: se um doc fala de **XLM / Soroban / Freighter / SEP-10**, é da fase antiga.
> O equivalente no Arc está no `ARC_LEPTON_ARCHITECTURE.md`. Em dúvida, perguntem no sync.
