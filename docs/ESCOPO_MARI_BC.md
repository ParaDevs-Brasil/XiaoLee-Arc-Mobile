
# Escopo Completo — Frontend & Produto (Mari + BC)

Criado em: **2026-07-01**
De: Gustavo (com Claude Code)
Para: **Mari (MariaPereiraTI)** e **BC — BrazillianCare (SkiterH)**, responsáveis a partir de agora pela frente de frontend e produto do XiaoLee.

Este é o **documento único** com todo o escopo: onde estamos, o que muda na documentação existente (arquitetura e design system), e o que precisa acontecer nos próximos dias até a submissão do Lepton. Ele substitui dois rascunhos anteriores (handoff técnico + plano de produto) que foram consolidados aqui.

---

## 1. O prazo real (confirma isso primeiro)

Vários docs no repo (`docs/team/WORKFLOW_SEMANA.md`, `docs/STATUS_HACKATHON.md`, `docs/POSICIONAMENTO_ARC_LEPTON.md`, `docs/workflows/ARC_LEPTON_ARCHITECTURE.md`) ainda falam em **29 jun** como deadline — isso mudou. **A data real de submissão é 6 jul 2026, 23:59 ET** (GitHub público + vídeo <3min + link live + formulário). Hoje é **1 jul** → restam **5 dias**.

Fonte viva de status: [issues `hackathon-lepton` no GitHub](https://github.com/ParaDevs-Brasil/XiaoLee/issues?q=is%3Aissue+is%3Aopen+label%3Ahackathon-lepton) — mais confiável que qualquer doc estático, incluindo este.

---

## 2. O posicionamento (a tese do produto, não só estética)

De `docs/POSICIONAMENTO_ARC_LEPTON.md` (vale ler inteiro):

> **XiaoLee é o agente que paga creators "pela fração" — nanopagamentos USDC em tempo real, conforme o trabalho acontece, sem ninguém apertar botão.**

Tudo que vocês construírem serve pra provar essa frase — se uma feature não prova isso, é "se sobrar tempo".

**Hierarquia de mensagem pro júri:** 1) Autonomia (Agentic 30%, Jeiel) → 2) **Dinheiro real fluindo (Traction 30%, dona Mari)** → 3) Nativo do Arc (Circle Tools 20%, Gustavo) → 4) Recibo/identidade (Innovation 20%, só se o resto estiver verde).

**Regra de ouro:** toda decisão de escopo passa por *"isso prova a frase e move Agentic ou Traction?"* Se não, corta ou adia.

---

## 3. Onde estamos — backlog (snapshot 1 jul, confirmar no GitHub antes de agir)

| Frente | Status | Issue |
|---|---|---|
| Loop agêntico (Jeiel) | ✅ Completo, E2E validado | — |
| USDC real fluindo | 🔴 Bloqueado — `CIRCLE_API_KEY` ainda placeholder (401 na API Circle). Bloqueador do Gustavo, mas **sem ele o dashboard de vocês mostra zero** | — |
| Onboarding de creators reais (Mari) | 🟡 Formulário existe, falta 5+ creators reais com wallet Sepolia | [#40](https://github.com/ParaDevs-Brasil/XiaoLee/issues/40) — **ETA era 1 jul: hoje** |
| Dashboard de traction público (Mari) | 🟡 Página existe com SSE ao vivo, falta validar mobile + deploy público | [#41](https://github.com/ParaDevs-Brasil/XiaoLee/issues/41) — **ETA era 1 jul: hoje** |
| Vídeo demo ≤3min (Mari + Gustavo) | ⬜ Não iniciado | [#45](https://github.com/ParaDevs-Brasil/XiaoLee/issues/45) |
| Consistência de frontend (landing como referência) | 🟡 Fase 1 completa, Fase 2 parcial | [#48](https://github.com/ParaDevs-Brasil/XiaoLee/issues/48) |

**#40 e #41 são a prioridade nº1** — o prazo deles já estourou.

---

## 4. A convergência importante: `/traction` mobile é duas coisas ao mesmo tempo

O critério de aceite do **#41** diz literalmente: *"Funciona em mobile (o júri pode abrir no celular)"*. E o plano de consistência de frontend (seção 6 abaixo, Fase 4) identificou que **nenhuma página fora da landing tem breakpoint responsivo** — `/traction` incluída.

**Não são dois trabalhos, é um só.** Ataquem a responsividade de `/traction` e `/onboarding` primeiro — são as páginas que o júri realmente abre. Generalizar pro resto do app (`dashboard`, `campaigns`, `notifications`) é "se sobrar tempo", não tem critério de aceite do hackathon te cobrando.

---

## 5. Estado técnico exato de onde a Fase 1/2 do frontend pararam

Plano completo (6 fases) em `docs/FRONTEND_CONSISTENCY_PLAN.md` — leiam esse pra entender o *porquê* (a landing page, criada em 31/05, é a versão mais madura e mais recente do design do XiaoLee; o resto do app ficou preso ao padrão de antes dela existir, documentado em `docs/DESIGN_SYSTEM.md` v3 de 09/05).

- ✅ **Fase 1 (tokens de tom)** — `font-display`, `text-ink`, `text-grad`, `text-grad-stellar`, `.glass`, `.ring-soft`, `.reveal*`, `.msg-in`, `.word-in`, `.anim-floaty*` promovidos de `landing.css` (só funcionava em `.xl-landing`) para `globals.css` (funciona em qualquer página agora). Validado com build limpo + comparação visual pixel-a-pixel da landing.
- 🟡 **Fase 2 (ícones unificados)** — `src/components/icons.tsx` criado como arquivo canônico. `src/components/landing/icons.tsx` virou um re-export (`export * from "../icons"`), zero risco pra landing. **Só `dashboard/page.tsx` foi migrado.**

  Falta migrar (mesmo padrão — trocar SVG inline por import de `@/components/icons`, preservando `className="w-N h-N"` e `sw` quando o `strokeWidth` original não era 1.8):

  | Arquivo | Ícones faltando | Observação |
  |---|---|---|
  | `onboarding/page.tsx` | `IconUser`, `IconWallet`, `IconCheck` (`w-8 h-8`, `sw=2.5`), `IconDollar`, `IconArrow`, `IconActivity` | ⚠️ `IconWallet` do onboarding tem desenho **diferente** do `IconWallet` já em `icons.tsx` — decidir se unifica (muda o visual) ou vira export separado (`IconWalletOutline`) |
  | `traction/page.tsx` | `IconDollar`, `IconZap` (alias de `IconBolt`, path idêntico), `IconUsers`, `IconActivity`, `IconCheck` (`w-3 h-3`, `sw=2.5`), `IconInbox`, `IconUserPlus` | — |
  | `dashboard/TokenomicsCard.tsx` | `IconToken` | — |
  | `Navbar.tsx` | usa `@heroicons/react` (4ª fonte de ícone) | decisão em aberto: migrar ou manter como exceção documentada |

  Trade-offs visuais já aceitos ao migrar o dashboard (não são bugs): `IconShield` ganhou um checkmark interno que não tinha, `IconCpu` ficou mais simples (menos "pinos"), `IconTarget` passou a preencher o ponto central. Validado visualmente, ficou bom.

- ⬜ **Fases 3-6** — não iniciadas (primitives compartilhadas, responsividade geral, i18n, Navbar, atualizar `DESIGN_SYSTEM.md` — ver análise abaixo).

**Nada disso foi commitado ainda** no momento em que este doc foi escrito — confirmem com o Gustavo o estado do branch antes de puxar.

---

## 6. Análise: o que precisa mudar na arquitetura e no design system

Pedido explícito do Gustavo: verificar se `docs/ARCHITECTURE.md`, `docs/workflows/ARC_LEPTON_ARCHITECTURE.md` e `docs/DESIGN_SYSTEM.md` têm coisas desatualizadas por causa desse trabalho de frontend.

### Arquitetura — nada a mudar
`docs/workflows/ARC_LEPTON_ARCHITECTURE.md` (fonte da verdade atual, por camadas L0-L4) e `docs/ARCHITECTURE.md` (legado, útil só pra padrões de código per `CLAUDE.md`) não fazem nenhuma afirmação sobre componentização visual, ícones ou tokens de design que contradiga o trabalho de frontend. A seção 9 do `ARCHITECTURE.md` (`UserData` singleton) é sobre gerência de estado, não visual — segue válida. **Conclusão: não precisam de edição por causa deste trabalho.** (Ambos têm datas de deadline desatualizadas — 29 jun — mas isso é um problema geral do repo, não específico de frontend.)

### `docs/DESIGN_SYSTEM.md` — precisa de reescrita (isso é a Fase 6, ainda não fizemos)
Comparei o que o documento afirma com o código real e achei **contradições factuais**, não só coisas desatualizadas:

1. **Tipografia (seção 2) — errado, não só desatualizado.** O doc diz que a fonte principal é **Inter**. O código inteiro usa **Quicksand** (`layout.tsx` carrega `Quicksand` via `next/font/google`, `globals.css` define `--font-sans: 'Quicksand', ...`, e o próprio `landing.css` tem o comentário `/* heavier display weight (Quicksand caps at 700) */`). Não existe uma única referência a "Inter" no código (`grep` deu zero resultados). Isso nunca foi implementado assim, ou mudou sem atualizar o doc.
2. **Princípio 1 (seção 1.1) também contradiz o código.** Diz que o sistema "removeu gradientes pesados e bordas multicoloridas em favor de tons pastéis sutis" — mas `dashboard`, `notifications`, `onboarding` e `traction` usam gradientes fortes o tempo todo (fundo `bg-gradient-to-br from-pink-50 via-purple-50...`, texto `bg-clip-text` com gradiente de 3 cores, botões `from-pink-400 via-fuchsia-500 to-purple-500`). O princípio nunca foi seguido na prática.
3. **"Mobile-first" (seção 1, item 6) está com a definição errada.** Diz que mobile-first é `max-w-2xl mx-auto` fixo. Isso não é mobile-first, é "mobile-only, nunca escala" — a landing (que é a referência agora) mostra o que mobile-first de verdade é: base mobile + breakpoints (`sm:/md:/lg:`) que escalam o layout em telas maiores.
4. **Iconografia (seção 4) não menciona `src/components/icons.tsx`** porque esse arquivo não existia quando a seção foi escrita (documenta "SVG inline por componente" como o padrão, quando agora o padrão é importar do arquivo canônico).
5. **Estrutura de Layout (seção 5) e as seções 7/8 (Notifications/Dashboard)** descrevem o container fixo `max-w-2xl` e os cards de stat reimplementados por página como se fossem o padrão desejado — isso vai ficar desatualizado assim que as Fases 3 (primitives compartilhadas) e 4 (responsividade) rodarem.
6. **O documento inteiro não menciona a landing page** — trata o estilo antigo do app como se fosse o único e completo sistema de design do XiaoLee.

**Recomendação:** não reescrevam isso ainda (é a Fase 6, propositalmente por último, depois que as Fases 2-5 estiverem implementadas — reescrever antes seria documentar um estado que ainda não existe). Mas já sabem, a partir de agora, que a seção 2 (tipografia), 1.1 (gradientes) e 1.6/5 (mobile-first) **não são confiáveis como estão** — não usem como referência de "como as coisas são hoje".

---

## 7. Plano dos próximos 5 dias (1-6 jul)

Sugestão de sequência, ajustem no sync diário:

| Dia | Foco produto (Traction) | Foco frontend |
|---|---|---|
| **1 jul (hoje)** | Fechar #40 (5+ creators reais) e #41 (validar dashboard ao vivo) | Responsividade mobile de **só** `/traction` e `/onboarding` (fatia da Fase 4 que é critério de aceite) |
| **2 jul** | Confirmar deploy público acessível ([#43](https://github.com/ParaDevs-Brasil/XiaoLee/issues/43)) + capturar métricas/prints reais | Terminar Fase 2 (ícones) nas páginas que sobrarem, **se der tempo** |
| **3 jul** | Usuários reais pagando, métricas subindo | — |
| **4 jul** | Roteiro + captura de tela pro vídeo (#45) | — |
| **5 jul** | Gravação/edição do vídeo, revisão final | Fase 6 (`DESIGN_SYSTEM.md`) só se sobrar tempo |
| **6 jul** | Buffer + submissão | — |

**O que NÃO fazer nesses 5 dias:** Fase 3 (primitives) e o resto da Fase 4 (dashboard/campaigns/notifications responsivos) — é debt de consistência, não critério de nota. Só voltem nisso depois do dia 6, ou se sobrar tempo real depois de #40/#41/#45 verdes.

---

## 8. Divisão sugerida Mari / BC

Sugestão de ponto de partida (não sei o quanto BC já conhece de código vs. produto/narrativa — ajustem entre vocês):

- **Mari**: mão na massa técnica — responsividade do `/traction`/`onboarding`, dashboard, dados reais de creators.
- **BC**: captura de métricas/prints, roteiro do vídeo, testar o fluxo como o júri (abrir no celular, achar bugs de UX), validar que a narrativa do posicionamento (seção 2) está sendo cumprida em cada tela.

---

## 9. Onde encontrar tudo

- `docs/POSICIONAMENTO_ARC_LEPTON.md` — tese do produto, ICP, mensagem pro júri
- `docs/FRONTEND_CONSISTENCY_PLAN.md` — as 6 fases completas, landing como referência
- `docs/team/ONBOARDING_MARI.md` — onboarding original de Traction Lead (ainda vale, escopo só ficou maior)
- Issues `hackathon-lepton` no GitHub — status vivo
- Dúvida de produto/traction/creator/frontend → a partir de agora é vocês dois

---

## 10. Ressalva

Fui eu (Claude, com o Gustavo) quem cruzou os docs existentes e o código pra montar isso — não substitui o sync real com o time. Os números de status têm data de referência (1 jul) e podem já estar desatualizados quando vocês lerem. Confirmem no GitHub e no sync antes de agir em cima de qualquer número aqui.
