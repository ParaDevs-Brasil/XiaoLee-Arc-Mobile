# XiaoLee — Plano de Go-to-Market

### Foco: tração pré-mainnet e narrativa de grant (SCF / Instawards)

> **Atualizado em:** 30/05/2026
> **Escopo deste documento:** GTM da Fase 0 — provar demanda **agora**, com o produto em MVP/testnet, e converter essa prova em funding (SCF Build Award / Instawards) e em pipeline de criadores. O lançamento de aquisição em mainnet é tratado como Fase 1 (esboçado em §9), mas **não** é o foco aqui.
> **Documentos relacionados:** `XIAOLEE_INVESTOR_TECH_DOC.md` (§6 modelo de receita e canais), `posicionamento_xiaolee.html` (framework de posicionamento), `INSTAWARDS_DRAFT.md` (plano de execução 30 dias), `MAINNET_READINESS.md` (gates).

---

## 1. Princípio do GTM nesta fase

A XiaoLee **ainda não está em mainnet** e este plano não promete tração de usuário que não existe. O objetivo da Fase 0 não é volume — é **prova de demanda verificável** e **credibilidade técnica em público**, que são os dois ativos que destravam o funding e as parcerias de criador.

Tudo aqui é desenhado para ser executável com o que já existe hoje: backend auditado internamente, fluxo x402 em testnet, programa Solana em devnet, e os canais Telegram/X já operacionais. Nenhuma tática depende do contrato Soroban estar pronto — quando ele entrar (gate 1B, P0), vira combustível de narrativa, não pré-requisito.

**Três metas mensuráveis da Fase 0:**

| Meta | Métrica de saída | Janela |
|---|---|---|
| Provar demanda | ≥ 1 campanha real rodando com participantes reais em testnet; lista de espera de criadores | Até pitch Rio (08–11/06) |
| Ganhar funding | Submissão SCF Build Award + Instawards aprovados | Junho/2026 |
| Construir audiência | Build-in-public com cadência semanal; base de seguidores qualificados em X + Telegram | Contínuo |

---

## 2. ICP — Perfil de Cliente Ideal

GTM nesta fase mira **um único ICP primário** (criador). Os demais segmentos são consequência, não foco de aquisição agora.

### 2.1 ICP primário — Criador BR/LATAM crypto-curioso

| Atributo | Definição |
|---|---|
| Quem é | Criador de conteúdo BR/LATAM (Twitter/X, streamer, artista, comunidade Web3) com 5k–100k seguidores engajados |
| Dor central | Quer recompensar/engajar a audiência on-chain, mas não tem ferramenta sem exigir que o fã configure carteira do zero; rails de cartão cobram 20–50% e bloqueiam conta |
| Por que agora | Curioso sobre cripto mas sem stack técnico; o Pix nativo (EtherFuse) remove a barreira do fã sem cartão internacional |
| Gatilho de adoção | "Configuro uma campanha em minutos, meus fãs completam tarefa social e recebem na carteira — sem código, sem custódia" |
| Onde encontrar | Telegram/Discord de comunidades Web3 BR, X cripto-BR, eventos Stellar/Solana BR, rede 37 Graus |

### 2.2 Segmentos secundários (não são alvo de aquisição na Fase 0)

| Segmento | Papel no GTM atual |
|---|---|
| Fã / usuário cripto-nativo (18–35) | Participante das campanhas dos criadores — entra puxado pelo criador, não por aquisição direta |
| Usuário não-cripto LATAM (Pix) | Prova do diferencial Pix; alvo real só pós-EtherFuse em produção |
| Projetos Web3 globais (campanhas como serviço) | Pipeline B2B futuro; coletar interesse, não vender ainda |

### 2.3 Anti-ICP (para quem NÃO vender agora)

- Criador sem audiência engajada (campanha sem participante não vira prova).
- Projeto que exige mainnet/produção imediata — não temos, e prometer destrói credibilidade.
- Usuário que quer trading avançado/DeFi pesado — não é a proposta de valor.

---

## 3. Posicionamento e mensagem

**Statement central:** *A XiaoLee é a interface de AI para o DeFi Stellar, com Pix nativo.* O usuário descreve a intenção em linguagem natural; a XiaoLee prepara a transação e a assinatura permanece sempre na carteira do usuário (wallet-first, non-custodial).

### 3.1 Matriz de mensagem por audiência

| Audiência | Dor que abrimos | Mensagem de uma linha | Prova que mostramos |
|---|---|---|---|
| Criador BR/LATAM | "Monetizar engajamento on-chain é técnico demais pro meu público" | "Campanha social com recompensa na carteira do fã, sem código e sem custódia" | Demo de campanha join→verify→claim |
| Comunidade Stellar/SDF | "Falta UX de massa sobre Stellar" | "Camada de AI conversacional que esconde trustline/slippage/SEP-10 do usuário final" | x402 em testnet (§3.2 do investor doc), SEP-10 |
| Avaliador de grant (SCF/Instawards) | "Projetos prometem e não entregam" | "Base off-chain auditada (23 findings corrigidos), x402 em testnet, Solana em devnet — funding só pra fechar o contrato Soroban + mainnet" | AUDIT.md, tx hashes, commit history |
| Fã / participante | "Cada protocolo tem uma UX diferente" | "Uma conversa só, em qualquer língua — e entra com Pix" | Onboarding via Telegram bot |

### 3.2 Pilares de prova (o que sempre acompanha a mensagem)

1. **Non-custodial / wallet-first** — a chave privada nunca toca o servidor.
2. **Auditado internamente** — Sprint de segurança 2026-05, 23 findings corrigidos.
3. **Verificável on-chain hoje** — Solana devnet + x402 Stellar testnet (tx hashes públicos).
4. **Pix nativo (LATAM)** — diferencial que nenhum concorrente cripto-nativo cobre.

> Honestidade é parte da mensagem: comunicamos abertamente que estamos pré-mainnet. Em GTM de grant, transparência sobre o estágio **aumenta** a credibilidade — ver tom do Executive Summary do investor doc.

---

## 4. Estratégia de canais (Fase 0)

Prioridade por ordem de impacto na prova de demanda + funding. Cada canal tem dono, tática e KPI.

| # | Canal | Tática | KPI primário | Custo |
|---|---|---|---|---|
| 1 | **Dogfooding em X** | Campanha self-referencial na própria plataforma: "complete tarefas → ganhe $XLEE" (testnet). A XiaoLee usando a XiaoLee. | Nº de participantes reais na campanha | ~0 |
| 2 | **Build in public (X + Telegram)** | Thread semanal: progresso técnico + métricas reais + tx hashes. Documenta o caminho até o gate Soroban. | Crescimento de seguidores qualificados; impressões/thread | ~0 |
| 3 | **Telegram bot** | Onboarding conversacional Stellar na comunidade (canal já operacional). | Nº de usuários ativos no bot | ~0 |
| 4 | **Criadores BR (parceria)** | 3–5 influenciadores cripto-BR rodam uma campanha-piloto cada. | Nº de criadores ativos com campanha rodando | Baixo (recompensa testnet/simbólica) |
| 5 | **Comunidade Stellar BR + rede 37 Graus** | Presença em Telegram/Discord Stellar BR; mentoria SDF; intro EtherFuse; pitch presencial no Rio (08–11/06). | Intros qualificadas; avanço do pipeline de parceria | ~0 |
| 6 | **Grant motion (SCF + Instawards)** | Submissão com evidências verificáveis; documento SCF dedicado. | Grant aprovado | Tempo |

### 4.1 O canal-âncora: dogfooding + build-in-public

O motor de tudo é **usar o produto pra divulgar o produto**. Uma campanha real em testnet onde o prêmio é entrar cedo na XiaoLee resolve duas coisas ao mesmo tempo: gera os primeiros participantes reais (prova de demanda) e produz o conteúdo do build-in-public (tx hashes, prints, métricas). Custo marginal zero, e cada execução vira material de grant.

---

## 5. Funil e métricas (Fase 0)

Funil enxuto, adaptado a um produto pré-mainnet — o objetivo é **demanda e credibilidade**, não receita.

```
Awareness        → build-in-public, comunidade Stellar BR, dogfooding em X
   ↓ (impressões, seguidores qualificados)
Interesse        → entra no Telegram bot / segue threads / curte demo
   ↓ (usuários no bot, lista de espera de criadores)
Ativação         → completa 1 tarefa numa campanha testnet (join→verify→claim)
   ↓ (participantes reais, tx on-chain)
Prova/advocacy   → criador roda a própria campanha-piloto
   ↓ (criadores ativos)
Funding          → evidência vira submissão SCF/Instawards aprovada
```

### 5.1 KPIs do tabuleiro (revisão semanal)

| Métrica | Baseline (30/05) | Meta até pitch Rio (11/06) |
|---|---|---|
| Participantes reais em campanha testnet | a medir | ≥ 1 campanha com participantes |
| Criadores com campanha-piloto rodando | 0 | 3–5 |
| Usuários ativos no Telegram bot | a medir | crescimento mensurável vs. baseline |
| Threads de build-in-public publicadas | — | 1/semana, sem furo |
| Submissões de grant | 0 | SCF submetido + Instawards submetido |

> **Ação imediata:** instrumentar a baseline (participantes, usuários no bot, seguidores) antes de 06/06 — sem baseline não há narrativa de crescimento.

---

## 6. Motor de conteúdo (build-in-public)

A cadência semanal é o ativo de marca. Formato fixo reduz custo de produção.

| Dia | Peça | Conteúdo |
|---|---|---|
| Semanal | **Thread de progresso (X)** | O que foi feito na semana + um tx hash/print verificável + próximo marco (rumo ao gate Soroban) |
| Ad hoc | **Demo curto (vídeo)** | Fluxo de campanha join→verify→claim; swap conversacional; x402 em ação |
| Marco | **Post de gate** | Quando um gate fecha (ex.: contrato Soroban em testnet) — antes/depois, com evidência on-chain |
| Recorrente | **Onboarding no Telegram** | Conteúdo que leva o curioso a completar a primeira tarefa |

**Linha editorial:** técnico mas acessível, honesto sobre o estágio, sempre com prova verificável. Sem emoji em comunicação técnica/infra; persona da XiaoLee mantém o tom dela nos canais de produto/AI.

---

## 7. Parcerias

| Parceiro | Status | Objetivo no GTM | Próximo passo |
|---|---|---|---|
| **37 Graus / SDF (NearX)** | Em curso (programa 04/05–11/06) | Mentoria, intros, palco no pitch Rio | Demo ao vivo 08–11/06 |
| **EtherFuse (Pix on/off-ramp)** | A integrar | Destrava o diferencial Pix LATAM | Intro via rede 37 Graus; integração pós-grant |
| **Criadores BR (3–5)** | A recrutar | Liquidez de oferta nas campanhas; prova de demanda | Recrutar via X/Telegram; piloto em testnet |
| **Comunidade Stellar BR** | Acessível | Awareness e primeiros usuários | Presença ativa em Telegram/Discord |

---

## 8. Alinhamento GTM ↔ funding

O GTM da Fase 0 **é** a narrativa do grant. Cada tática produz uma evidência exigida na submissão.

| Tática de GTM | Evidência gerada | Onde entra no grant |
|---|---|---|
| Campanha dogfooding em testnet | tx hashes de `record_reward` / claim on-chain | Prova técnica verificável |
| Build-in-public | Commit history + threads = trilha de execução | Evidence of completion (Instawards §6) |
| Criadores-piloto | Demanda real demonstrada | Tração / validação de mercado |
| Auditoria interna | AUDIT.md, 23 findings corrigidos | Segurança e maturidade |

**Pedido de funding (resumo — detalhe no doc SCF dedicado):** recursos para escrever e auditar o contrato Soroban `xiaolee_core` (gate 1B, P0), emitir o SAC $XLEE, integrar EtherFuse (Pix) e levar a track Stellar a mainnet com auditoria externa. Instawards: $5.000 (cap), foco em fechar contrato Soroban + verificação x402. Ver `INSTAWARDS_DRAFT.md` §4.2 e investor doc §7.3.

---

## 9. Fase 1 (prévia) — Lançamento em mainnet

Fora do escopo de execução agora; registrado para continuidade. Destrava só após os gates de mainnet: contrato Soroban em produção, **auditoria externa** (bloqueador), SAC $XLEE emitido, secrets/vault + HTTPS/HSTS + multisig.

Quando habilitada, a Fase 1 ativa o modelo de receita (swap 0,3%, campanha 0,5%, x402 premium — investor doc §6.1), aquisição paga com criadores, e o on-ramp Pix em produção como motor de aquisição de não-cripto na LATAM. Funil passa a incluir retenção e LTV; KPIs migram de "prova de demanda" para volume, GMV de campanha e receita.

---

## 10. Plano de 90 dias (visão de execução)

| Janela | Foco | Resultado esperado |
|---|---|---|
| **Agora → 11/06** | Dogfooding + build-in-public + submissões de grant + pitch Rio | 1 campanha real, 3–5 criadores-piloto, SCF/Instawards submetidos, demo ao vivo no Rio |
| **Jun–Jul** (pós-grant) | Fechar gate Soroban (P0) + integrar EtherFuse; manter cadência de conteúdo | Contrato em testnet com tx verificável; Pix em piloto; base de criadores crescendo |
| **Jul–Ago** | Preparar Fase 1: auditoria externa + hardening; recrutar coorte maior de criadores | Caminho de mainnet destravado; pipeline de lançamento pronto |

---

## 11. Riscos de GTM e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| Campanha testnet sem participantes | Sem prova de demanda → enfraquece grant | Começar pelo dogfooding (custo zero) + recrutar criadores com audiência já engajada (anti-ICP filtra os sem audiência) |
| Atraso no gate Soroban | Narrativa "ainda pré-mainnet" se arrasta | Build-in-public foca no caminho, não no destino; cada gate fechado é um post; honestidade sobre estágio é parte da mensagem |
| Dependência de EtherFuse para o diferencial Pix | Diferencial não demonstrável até integrar | Posicionar Pix como roadmap próximo, não como entregue; provar os outros 3 pilares hoje |
| Build-in-public sem baseline | Não dá pra mostrar crescimento | Instrumentar métricas antes de 06/06 |
| Mensagem prometer mainnet | Destrói credibilidade com avaliador | Disciplina de comunicação: sempre marcar testnet/devnet e estágio MVP |
