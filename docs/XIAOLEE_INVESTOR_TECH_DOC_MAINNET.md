<!--
╔══════════════════════════════════════════════════════════════════════════╗
║  NÃO PUBLICAR ENQUANTO HOUVER PLACEHOLDER <<...>> NO DOCUMENTO.            ║
║  Esta versão só se torna verdadeira APÓS o deploy real em mainnet.        ║
║  Antes de enviar a qualquer investidor:                                   ║
║    1. Fazer o deploy do contrato Soroban + SAC $XLEE em mainnet.          ║
║    2. Preencher TODOS os <<...>> com IDs/hashes reais (StellarExpert).    ║
║    3. Conferir cada hash clicável abrindo no explorer.                    ║
║    4. Remover este bloco de comentário e o banner abaixo.                 ║
║  Enquanto (1)–(3) não estiverem feitos, use XIAOLEE_INVESTOR_TECH_DOC.md  ║
║  (versão honesta: MVP + prova em testnet).                                ║
╚══════════════════════════════════════════════════════════════════════════╝
-->

> ⚠️ **RASCUNHO — PENDENTE DE DEPLOY.** Este documento contém placeholders `<<...>>` que só podem ser preenchidos após o deploy real em mainnet. Não enviar a investidores antes de preencher e verificar cada hash on-chain. (Remover este aviso na publicação.)

---

# XiaoLee — Documentação Técnica para Investidores

### AI Ops Layer não-custodial para a economia de criadores sobre Stellar

> Versão 1.0 — 2026-06-__ · Programa 37 Graus (NearX/SDF), Track A · Stellar Mainnet (beta)
> Builder: Gustavo Fontes (`f0ntz`) · fontzweb3@gmail.com · ParaDevs (Brazil) · Embaixador Stellar
> Repositório: `github.com/ParaDevs-Brasil/XiaoLee`

---

## Sumário

- [1. Executive Summary](#1-executive-summary)
- [2. Produto e Estado Atual](#2-produto-e-estado-atual)
- [3. Mainnet — Prova On-Chain](#3-mainnet--prova-on-chain)
- [4. Arquitetura e Fluxos Críticos](#4-arquitetura-e-fluxos-críticos)
- [5. Segurança e Modelo de Custódia](#5-segurança-e-modelo-de-custódia)
- [6. Modelo de Negócio e GTM](#6-modelo-de-negócio-e-gtm)
- [7. Roadmap e Investimento Pleiteado](#7-roadmap-e-investimento-pleiteado)
- [8. Riscos e Mitigações](#8-riscos-e-mitigações)
- [Anexo A — Decisões de Produto (PDRs)](#anexo-a--decisões-de-produto-pdrs)
- [Anexo B — Decisões de Arquitetura (ADRs)](#anexo-b--decisões-de-arquitetura-adrs)
- [Anexo C — Referência de Endpoints e Configuração](#anexo-c--referência-de-endpoints-e-configuração)

---

## 1. Executive Summary

A XiaoLee é uma **AI ops layer não-custodial** para a economia de criadores: uma camada de inteligência conversacional que senta entre o usuário e a infraestrutura Stellar e orquestra operações on-chain — swaps, campanhas sociais, distribuição de recompensas e pagamentos — em linguagem natural, via Twitter DM, Telegram ou web. O usuário nunca precisa entender carteiras, slippage, trustlines ou contratos: descreve a intenção, a XiaoLee prepara a transação e a assinatura permanece sempre na carteira do usuário.

**Problema.** A economia de criadores cresce sobre rails de pagamento que não a servem: cartão e plataformas centralizadas bloqueiam contas sem aviso, aplicam chargebacks que destroem margem e cobram 20–50% de comissão. No Brasil e na LATAM, o fã sem cartão internacional simplesmente não consegue pagar. As soluções on-chain endereçam parte disso, mas exigem que o usuário aprenda DeFi — uma barreira que o criador e o seu público não absorvem.

**Solução.** A XiaoLee transforma a interface do DeFi Stellar em uma conversa. Três pilares — engine de campanhas sociais, DeFi conversacional (swaps e pagamentos via Stellar DEX) e gateway de entrada/saída em Pix para a LATAM — operam sobre um princípio único: **wallet-first e non-custodial**. O backend orquestra, prepara e roteia; a chave privada nunca toca o servidor. A camada blockchain permanece transparente para o usuário, e o vínculo social-financeiro (Twitter ID como identidade) é o que diferencia o protocolo de uma carteira genérica.

**Estado em 2026-06-__.** O produto opera em **mainnet (beta)**. O contrato Soroban `xiaolee_core` e o Stellar Asset Contract (SAC) de $XLEE estão implantados (§3.1); a camada Stellar off-chain — autenticação SEP-10, micropagamentos x402, cotação e montagem de swaps via Stellar DEX, âncora SEP-24 e integração Freighter — está implementada e passou por auditoria de segurança interna (23 findings corrigidos, §3.3). A track Solana (Anchor) segue como rail multi-chain paralelo. O rollout é controlado, com TVL limitado e auditoria externa em andamento (§5).

| | |
|---|---|
| Categoria | AI ops layer não-custodial para economia de criadores (campanhas + DeFi conversacional + on/off ramp) |
| Blockchain | Stellar (mainnet) + Soroban; track Solana/Anchor (rail multi-chain paralelo) |
| Estágio | Beta público em mainnet · camada off-chain auditada internamente · auditoria externa em andamento · Track A 37 Graus |
| Prova on-chain | Contrato Soroban + SAC $XLEE em mainnet (§3.1); fluxo x402 em mainnet (§3.2); auditoria interna com 23 findings corrigidos e 61 testes passando (§3.3) |
| Diferencial | Interface em linguagem natural · non-custodial · Pix nativo via EtherFuse · micropagamentos agentic x402 · identidade social (Twitter ID) |
| Modelo de receita | Fee de swap (0,3%) + fee de campanha (0,5%) + x402 premium por query de AI (§6.1) |
| Investimento pleiteado | Aplicação ao SCF Build Award (Stellar Community Fund); montante detalhado em documento SCF dedicado (§7.3) |

---

## 2. Produto e Estado Atual

### 2.1 O que a XiaoLee entrega

Uma interface de AI conversacional para o DeFi Stellar, construída sobre três pilares. Cada pilar endereça uma fricção concreta que hoje limita a adoção de cripto por criadores e pelo seu público.

**1. Engine de Campanhas sociais com recompensa on-chain.** Criadores publicam campanhas com tarefas sociais (seguir, repostar, comentar) e definem recompensas em $XLEE, XLM ou USDC. O usuário completa as tarefas, a XiaoLee verifica e a recompensa é distribuída diretamente na carteira Freighter — sem código e sem custódia.

*Impacto:* o criador monta um programa de engajamento pago em minutos, sem desenvolver contrato próprio, e constrói uma audiência on-chain que nenhuma plataforma centralizada pode remover ou bloquear.

**2. DeFi conversacional non-custodial.** Swaps, consultas de saldo e envio de pagamentos por mensagem. *"Troca 50 USDC por XLM"* → a XiaoLee consulta o melhor caminho no Stellar DEX, apresenta o quote, o usuário confirma e o Freighter assina. O backend monta a transação não assinada (XDR); a chave nunca sai da carteira.

*Impacto:* elimina a curva técnica do DeFi. O usuário opera a liquidez nativa da camada-1 da Stellar sem aprender interface de DEX, sem aprovar contrato de terceiro e sem expor a chave privada.

**3. Gateway de pagamentos Pix/LATAM.** On/off ramp via **EtherFuse** (parceiro oficial do programa 37 Graus): o usuário entra com Pix, opera no DeFi Stellar e sai quando quiser, sem comprar cripto em exchange. A EtherFuse abstrai SEP-24, KYC e a conversão fiat ↔ Stellar.

*Impacto:* desloca a barreira de entrada do DeFi do "tenha uma exchange e um cartão internacional" para "tenha um celular e um CPF". É o caminho Pix → DeFi que hoje não existe de forma conversacional no Brasil.

### 2.2 Diferenciais e impacto gerado

| Capacidade | Impacto gerado |
|---|---|
| Linguagem natural como única interface | Remove a curva técnica do DeFi: o criador e o fã operam por conversa, encurtando o onboarding a uma mensagem. |
| Non-custodial por design (chave nunca toca o backend) | Um eventual comprometimento do servidor não movimenta fundos — superfície de ataque substancialmente menor e *due diligence* mais simples. |
| Identidade social (Twitter ID como âncora) | A campanha recompensa "um criador com audiência verificada", não "uma carteira" — a wallet pode ser trocada; a identidade social, não (PDR-001). |
| Pix nativo via EtherFuse | Único caminho conversacional Pix ↔ DeFi para a LATAM — abre o funil para o público sem cartão internacional. |
| Micropagamentos agentic via x402 | A própria AI cobra por query premium em XLM (HTTP 402), criando um modelo de receita on-chain nativo para a economia de agentes. |
| Multi-chain isolado (Solana + Stellar) | A camada de orquestração e o DB são compartilhados (coluna `chain`); a integração Stellar não regride os rails Solana. |
| Custo de rede em frações de centavo (Stellar L1) | Viabiliza recompensa pequena e micropagamento de AI sem erosão de margem por gás. |

### 2.3 Público-alvo

| Segmento | Dor central | Solução da XiaoLee |
|---|---|---|
| Criadores LATAM e globais (Twitter/X, streamers, artistas) | Sem ferramenta para monetizar engajamento on-chain sem exigir que o fã configure carteira do zero | Engine de campanhas: tarefa social → recompensa na carteira, sem código e sem custódia |
| Fãs / usuários crypto-nativos (18–35) | Cada protocolo tem uma UX diferente; querem uma conversa só, em qualquer língua | Interface única em linguagem natural sobre o DeFi Stellar |
| Usuários não-crypto (LATAM, Pix) | Barreira de entrada ao DeFi via rail de pagamento local | Pix nativo via EtherFuse — entra com R$ e opera no DeFi sem exchange |
| Projetos Web3 globais | Custo alto de desenvolvimento de campanhas com recompensa on-chain | Plataforma escalável de campanhas como serviço, independente de região |

### 2.4 Estado de produto

A XiaoLee opera em mainnet (beta), com a fundação técnica auditada internamente e rollout controlado. A tração de usuários é reportada à medida que o beta público avança; este documento prioriza a prova on-chain verificável (§3) sobre projeções.

| Dimensão | Estado | Track |
|---|---|---|
| Camada Stellar off-chain (SEP-10, x402, swap DEX, SEP-24, Freighter) | Implementada e auditada | Stellar |
| Contrato on-chain | Soroban + SAC $XLEE em mainnet (§3.1); Anchor em devnet (rail paralelo) | Stellar / Solana |
| Backend API + DB multi-chain | Funcional; 61 testes passando; auditoria interna feita | Compartilhado |
| Canal conversacional | Telegram operacional; X/Twitter DM pendente de API paga | Compartilhado |
| Auditoria externa | Em andamento (rollout com TVL limitado até a conclusão) | Ambas |

---

## 3. Mainnet — Prova On-Chain

> **[PREENCHER NO DEPLOY]** Todos os campos `<<...>>` abaixo devem ser substituídos pelos identificadores e hashes reais gerados no deploy em mainnet, e cada link verificado no StellarExpert antes da publicação.

### 3.1 Contratos em mainnet (Stellar)

O contrato Soroban `xiaolee_core` e o SAC de $XLEE estão implantados na mainnet pública da Stellar.

| Item | Valor (mainnet) |
|---|---|
| Rede | `STELLAR_NETWORK=mainnet` |
| Horizon | `https://horizon.stellar.org` |
| Soroban RPC | `https://mainnet.sorobanrpc.com` |
| Contrato `xiaolee_core` | `<<SOROBAN_CONTRACT_ID>>` |
| SAC $XLEE | `<<XLEE_SAC_CONTRACT_ID>>` |
| Asset $XLEE | `XLEE:<<XLEE_ISSUER_G_ADDRESS>>` |
| Admin do contrato | `<<ADMIN_G_ADDRESS>>` (migração para multisig — ver §5) |
| Deploy tx (`initialize`) | [StellarExpert](https://stellar.expert/explorer/public/tx/<<INITIALIZE_TX_HASH>>) |

### 3.2 Operações reais em mainnet

| Fluxo | Prova on-chain |
|---|---|
| Emissão do asset $XLEE + deploy do SAC | [StellarExpert](https://stellar.expert/explorer/public/tx/<<XLEE_ISSUE_TX_HASH>>) |
| `record_reward` — distribuição de $XLEE em campanha | [StellarExpert](https://stellar.expert/explorer/public/tx/<<RECORD_REWARD_TX_HASH>>) |
| Swap via Stellar DEX (path payment) | [StellarExpert](https://stellar.expert/explorer/public/tx/<<SWAP_TX_HASH>>) |
| Micropagamento x402 (0,5 XLM por query de AI) | [StellarExpert](https://stellar.expert/explorer/public/tx/<<X402_TX_HASH>>) |

> Caso, na data de publicação, algum fluxo ainda não tenha sido exercido em mainnet, **remova a linha correspondente** em vez de deixar um placeholder ou um valor não verificado.

### 3.3 Auditoria de segurança interna (Sprint 2026-05)

Auditoria de segurança interna sobre a branch `develop`, cobrindo backend (FastAPI), frontend (Next.js) e infraestrutura. **23 findings corrigidos**, com metodologia equivalente à de uma pré-auditoria de produção. **Não substitui** a auditoria externa independente, que segue em andamento para o rollout de mainnet com TVL crescente (§5).

| Severidade | Qtd | Status |
|---|---|---|
| Crítico | 4 | Corrigidos (SEC-001 replay x402, SEC-002 `JWT_SECRET` obrigatório, SEC-011, SEC-012) |
| Alto | 9 | Corrigidos (inclui SEP-10 SEC-014/015, Helius HMAC SEC-007/011) |
| Médio | 7 | Corrigidos |
| Baixo | 3 | Avaliados (1 corrigido, 1 false positive, 1 aceito por UX) |

| Frente | Cobertura |
|---|---|
| SAST | Semgrep 1.163.0 OSS — Python (security-audit, secrets, fastapi, OWASP Top 10, CWE Top 25, Trail of Bits), JS/TS (react, nextjs), Docker |
| Cripto / timing | Análise (metodologia Trail of Bits) em `encryption_service.py`, `stellar_auth_routes.py`, `helius_routes.py`, `x402_routes.py` |
| Supply chain | 11 dependências flagradas (5 de alto risco); dependências mortas removidas; Dependabot configurado |
| Fuzzing | Hypothesis property-based — 15 testes, ~2.500 exemplos; encontrou e corrigiu 2 bugs reais |
| Carga | `load_tests/locustfile.py` — 5 classes, incluindo `XiaoLeeStellarAuth` (stress SEP-10) e replay/SQLi |
| Suíte | 61 testes passando, 6 skipped |

---

## 4. Arquitetura e Fluxos Críticos

### 4.1 Arquitetura de alto nível

```
┌─────────────────────────────────────────────────────────┐
│                      Clientes                           │
│  Next.js Frontend    Telegram Bot    X/Twitter DM       │
│  Freighter (Stellar) · Wallet Adapter (Solana, paralelo)│
└──────────────┬──────────────────────────────────────────┘
               │ HTTPS + JWT (SEP-10)
┌──────────────▼──────────────────────────────────────────┐
│                  Backend FastAPI                         │
│  ┌─────────────┐  ┌────────────────┐  ┌─────────────┐   │
│  │  SEP-10     │  │ Orchestration  │  │  Campaigns  │   │
│  │  Auth (JWT) │  │ Service + LLM  │  │  Router     │   │
│  └─────────────┘  └───────┬────────┘  └──────┬──────┘   │
│  ┌──────────────┐         │                  │          │
│  │ x402 (HTTP   │         │                  │          │
│  │ 402) /v1/ai  │         │                  │          │
│  └──────────────┘ ┌───────▼──────────────────▼──────┐   │
│                   │        StellarAdapter            │   │
│                   │  get_balance · prepare_swap      │   │
│                   │  build_swap_xdr · verify_payment │   │
│                   │  record_reward (→ Soroban)       │   │
│                   └──────────────────────────────────┘   │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────┐ │
│  │ PostgreSQL │  │   Redis    │  │  Horizon (Stellar) │ │
│  │ (coluna    │  │ Rate Limit │  │  + Solana RPC      │ │
│  │  `chain`)  │  │ + fallback │  │                    │ │
│  └────────────┘  └────────────┘  └────────────────────┘ │
└─────────────────────────────┬───────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────┐
│                    Redes On-chain                        │
│  Stellar: Horizon · DEX (path payments) · SEP-24 anchor  │
│           Soroban xiaolee_core + SAC $XLEE  (mainnet)    │
│  Solana:  Anchor xiaolee_core (rail multi-chain paralelo)│
└─────────────────────────────────────────────────────────┘
```

### 4.2 Ciclo de vida de uma campanha

`CREATED` → `ENROLLED` → `TASKS_VERIFIED` → { `REWARDED` | `EXPIRED` }

O participante entra (`enrolled`), completa as tarefas sociais, a XiaoLee verifica (`tasks_verified`) e, na claim, a recompensa é distribuída e registrada (`rewarded`). Idempotência garantida por constraint única (`uq_participant_campaign_user`) — uma segunda inscrição retorna `409 Conflict`.

### 4.3 Fluxo 1 — Autenticação SEP-10 (não-custodial)

```
1. Frontend: GET /auth/stellar/challenge?account=G...ABC
2. Backend: gera challenge XDR (sequence=0, manage_data op, nonce, TTL 5min)
3. Frontend: Freighter.sign(XDR) -> signed_xdr
4. Frontend: POST /auth/stellar/token { account, transaction: signed_xdr }
5. Backend: valida a assinatura com stellar-sdk e extrai a public key
6. Backend: emite JWT { sub: twitter_id, stellar_wallet: G...ABC, chain: "stellar" }
7. Frontend: armazena o JWT — todas as requests subsequentes o incluem
```

O backend mantém um keypair dedicado exclusivamente ao challenge SEP-10, nunca usado para fundos. A chave privada do usuário nunca toca o servidor (ADR-002).

### 4.4 Fluxo 2 — Swap conversacional via Stellar DEX

```
Usuário: "troca 50 USDC por XLM"
1. OrchestrationService: intent = stellar_swap
2. StellarAdapter.prepare_swap(USDC, XLM, 50)
   - GET /paths/strict-send (Horizon) -> melhor caminho + destination_amount
3. XiaoLee: "Você receberá ~142.3 XLM. Confirma?"
4. Usuário confirma
5. Backend: build_swap_xdr -> XDR unsigned (pathPaymentStrictSend)
6. Freighter: o usuário assina
7. Frontend submete via Horizon -> Backend persiste swap_record (chain="stellar")
```

A liquidez é a nativa da camada-1 da Stellar — sem contrato de DEX de terceiro e sem aprovação de token (ADR-003).

### 4.5 Fluxo 3 — Micropagamento de AI (x402)

```
1. Cliente: POST /v1/ai/query  (sem pagamento)
2. Backend: HTTP 402 Payment Required + payment-info { asset: XLM, amount: 0.5, pay_to }
3. Cliente: paga 0.5 XLM na Stellar (Freighter) -> tx_hash
4. Cliente: POST /v1/ai/query  com header X-Payment { tx_hash, network: mainnet }
5. Backend: verify_payment(tx_hash, pay_to, 0.5) via Horizon
   - rejeita se o hash já foi usado (anti-replay, SEC-001)
6. Backend: processa a query e retorna a resposta da AI
```

É o caso de uso *agentic*: a própria AI cobra por uso premium, em XLM, de forma nativa ao protocolo HTTP — modelo de receita on-chain sem intermediário (PDR-007).

### 4.6 Fluxo 4 — Campanha: join / verify / claim (Stellar)

```
POST /campaigns/join { campaign_id, stellar_wallet, chain: "stellar" }
   -> participant enrolled (409 se já inscrito)
Usuário completa as tarefas sociais (follow, RT, comment)
POST /campaigns/verify { campaign_id, twitter_id, proof }
   -> Backend verifica via API Twitter/X -> tasks_verified
POST /campaigns/claim { campaign_id, stellar_wallet }
   -> Backend valida o JWT (SEP-10)
   -> StellarAdapter.record_reward(twitter_id, wallet, amount)
        -> invoca record_reward no contrato Soroban + transfere $XLEE via SAC
   -> persiste o receipt com tx_hash -> usuário recebe $XLEE no Freighter
```

### 4.7 Contrato Soroban `xiaolee_core`

| Instrução | Descrição |
|---|---|
| `initialize(admin, xlee_sac)` | Inicializa o `GlobalConfig` (instance storage); `require_auth` |
| `initialize_user(twitter_id)` | Registra o usuário (persistent storage + bump de TTL) |
| `record_reward(admin, twitter_id, amount)` | Distribui $XLEE via SAC; `require_auth` + `checked_add` (anti-overflow) |
| `pause_protocol` / `unpause_protocol` | Emergency pause |
| `transfer_admin(admin, new_admin)` | Migração de autoridade |

Storage `instance` para config global e `persistent` por usuário; auth por `Address::require_auth()`; token via SAC (`token::Client`). Eventos `reward_recorded`, `protocol_paused`, `admin_transferred`. Implantado em mainnet (§3.1).

---

## 5. Segurança e Modelo de Custódia

A segurança é o núcleo do produto, não uma camada acessória. O princípio é abstrair a complexidade cripto do usuário sem nunca assumir o controle dos seus fundos. A tabela associa cada mecanismo ao risco concreto que ele elimina; o status reflete o estado real verificado no código.

| Mecanismo | Risco eliminado | Status |
|---|---|---|
| Non-custodial — XDR montado no backend, assinado no Freighter | Um vazamento do servidor não move fundos: a chave do usuário nunca está sob a plataforma (ADR-002) | Implementado |
| Autenticação SEP-10 (challenge/response → JWT) | Sessão sem senha e sem custódia de chave; padrão Stellar compatível com âncoras | Implementado e auditado |
| Anti-replay no x402 (`tx_hash` registrado após uso) | Reuso de um pagamento para obter respostas de AI de graça (SEC-001) | Corrigido |
| `JWT_SECRET` obrigatório no startup (raise se ausente) | Segredo de assinatura fraco/default em produção (SEC-002) | Corrigido |
| Webhook Helius com HMAC SHA-256 validado | Injeção de eventos on-chain forjados (SEC-007/011) | Corrigido |
| Rate limiting por usuário (Redis + fallback in-memory) | Abuso e exaustão de recursos (ex.: flood de challenge SEP-10) | Implementado |
| Idempotência (constraint única → 409) | Inscrição/recompensa duplicada em campanha | Implementado |
| Verificação on-chain antes de creditar (Horizon) | Crédito baseado em estado local divergente do ledger | Implementado (x402/swap) |
| `require_auth()` + `checked_add` no contrato Soroban | Operação não autorizada e overflow no total de recompensas | No contrato |
| Emergency pause no contrato | Continuidade de operação durante incidente on-chain | No contrato |

**Rollout controlado de mainnet.** O beta opera com **TVL limitado** enquanto a **auditoria externa independente** (contratos + backend) está em andamento — pré-requisito para ampliar limites. Hardening em curso: migração do admin EOA para **multisig nativo** (Stellar / Squads na Solana), **secrets em vault** (keypairs, DB, Redis, JWT), **HTTPS + HSTS** e **bug bounty** em testnet pública. O detalhamento dos gates está em `MAINNET_READINESS.md`.

---

## 6. Modelo de Negócio e GTM

### 6.1 Modelo de receita

| Fonte | Mecanismo | Status |
|---|---|---|
| Fee de swap | 0,3% sobre o volume de swaps executados via XiaoLee | Ativo em mainnet |
| Fee de campanha | 0,5% sobre o volume de recompensas distribuídas | Ativo em mainnet |
| x402 premium | Micropagamento em XLM por query de AI avançada | Ativo em mainnet |

A XiaoLee abraça o x402 como receita nativa: o caso de uso *agentic* (a AI cobra por uso premium) é compatível com o produto e opera em mainnet — um vetor de monetização on-chain que não depende de intermediário de pagamento.

### 6.2 Canais de aquisição

| Canal | Tática | Meta |
|---|---|---|
| Twitter/X (dogfooding) | Campanha self-referencial na própria plataforma: "complete tarefas → ganhe $XLEE" | Primeiros usuários e prova de produto |
| Telegram | Bot XiaoLee com onboarding Stellar na comunidade (canal já operacional) | Base inicial conversacional |
| Criadores BR | Parceria com 3–5 influenciadores crypto BR para campanhas pagas | Liquidez de oferta nas campanhas |
| Comunidade Stellar BR | Presença em Telegram/Discord Stellar BR | Awareness |
| Build in public | Thread semanal com progresso e métricas reais | Credibilidade |
| Rede 37 Graus | Mentoria SDF e introduções no Rio; status de embaixador Stellar | Pipeline e parceria EtherFuse |

### 6.3 Síntese de posicionamento

Configure uma campanha em poucos minutos: seus fãs completam tarefas sociais e recebem a recompensa direto na carteira, sem código e sem custódia. Swaps e pagamentos por conversa, com a chave sempre no usuário. E, para a LATAM, o fã entra via Pix — sem exchange e sem cartão internacional. **A XiaoLee é a interface de AI para o DeFi Stellar, com Pix nativo.**

---

## 7. Roadmap e Investimento Pleiteado

### 7.1 Status por fase (37 Graus, Track A)

> Programa NearX/SDF: 04/05–11/06/2026 · 5 Sprints · Residência no Rio 08–11/06.

| Fase | Período | Status | Entregáveis-chave |
|---|---|---|---|
| 1 — Infra Stellar + primeiros usuários | 04–11/05 | Concluído | `StellarAdapter`, SEP-10, Freighter no frontend, migração multi-chain (DB) |
| 2 — Pagamentos: Pix, stablecoins, x402 | 11–18/05 | Concluído | x402 (HTTP 402); swap DEX; integração EtherFuse |
| 3 — DeFi e protocolo | 18–25/05 | Concluído | Contrato Soroban + SAC $XLEE; `record_reward` on-chain; campanhas verificáveis |
| 4 — GTM e narrativa de investidor | 25/05–01/06 | Em curso | Deck, one-pager, este documento, vídeo demo |
| 5 — Pitch Rio | 08–11/06 | Planejado | Apresentação presencial + demo ao vivo |

### 7.2 Marcos críticos (gates)

| Gate | Descrição | Status |
|---|---|---|
| Contrato Soroban + SAC $XLEE | Implantar `xiaolee_core` (auth, overflow check, eventos) + asset $XLEE | Concluído em mainnet (§3.1) |
| Integração on-chain | `StellarAdapter.record_reward` ligado ao contrato real | Concluído |
| Auditoria externa | 2 auditorias independentes por track + backend | Em andamento (TVL limitado até concluir) |
| Secrets / vault + HTTPS/HSTS + multisig | Hardening de produção | Em andamento |

### 7.3 Investimento pleiteado

Aplicação ao **SCF Build Award** (Stellar Community Fund) para concluir a auditoria externa, ampliar os limites de mainnet, integrar o EtherFuse (Pix) em escala e acelerar a aquisição de criadores. Montante e uso de recursos detalhados em documento SCF dedicado; submissão pendente.

Uso de recursos previsto:

- **Segurança:** auditoria externa por track + backend; migração de admin para multisig; secrets em vault; bug bounty.
- **Engenharia:** escala do contrato e da integração on-chain; integração EtherFuse em produção.
- **Infraestrutura:** Horizon/Soroban RPC dedicados; PostgreSQL gerenciado e Redis em produção.
- **Comercial:** ativação dos primeiros criadores BR e dos canais Telegram/X.

---

## 8. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Auditoria externa pendente durante o beta | Alta | Crítico | Rollout com **TVL limitado** até a conclusão; auditoria interna (23 findings) como pré-auditoria; candidatos mapeados (OtterSec, Veridise, Trail of Bits) |
| Admin EOA antes da migração para multisig | Média | Crítico | Migração para multisig nativo no hardening; emergency pause no contrato |
| Dependência da API EtherFuse (Pix) | Média | Médio | Parceria oficial do 37 Graus; swap DEX nativo funciona sem o on/off ramp; integração isolada no `StellarAdapter` |
| X/Twitter DM exige API paga | Alta | Baixo | Telegram cobre 100% do fluxo conversacional; X é incremental |
| Complexidade do híbrido multi-chain (Solana + Stellar) | Média | Médio | Camada de orquestração e DB compartilhados (coluna `chain`); tracks isoladas, sem regressão mútua |
| Trustline $XLEE como atrito de UX | Média | Médio | XiaoLee detecta a ausência e guia o usuário; o Freighter assina o trustline com um clique (ADR-005) |

---

## Anexo A — Decisões de Produto (PDRs)

**PDR-001 — Twitter ID como identidade primária.** A wallet Freighter é vinculada ao Twitter ID, não o contrário. *Justificativa:* o vínculo social-financeiro é o diferencial; uma campanha recompensa um criador com audiência verificada, não uma carteira. A wallet pode ser trocada; a identidade social, não.

**PDR-002 — Freighter como wallet principal.** Mantida pela SDF, com SDK TypeScript oficial e suporte nativo a Soroban. *Futuro:* xBull e LOBSTR via abstração `WalletAdapter`, sem quebrar a interface.

**PDR-003 — On/off ramp via EtherFuse.** A EtherFuse (parceiro oficial do 37 Graus) abstrai SEP-24, KYC e a conversão fiat ↔ Stellar. *Justificativa:* reduz o escopo de implementação e entrega o diferenciador Pix sem integrar âncora diretamente.

**PDR-004 — $XLEE como Stellar Asset (SAC), não token Soroban puro.** Liquidez nativa no Stellar DEX imediata; o SAC provê a interface para o contrato distribuir $XLEE. Complexidade extra (vesting/locks) via wrapper Soroban quando necessário.

**PDR-005 — SEP-10 para autenticação não-custodial.** Padrão Stellar de challenge/response → JWT. *Justificativa:* compatibilidade com âncoras e integradores; suportado nativamente pelo Freighter.

**PDR-006 — Soroban para o contrato XiaoLee Core.** O registro on-chain de recompensa é diferencial de produto (auditabilidade sem confiar no backend). Rust/WASM com `require_auth()` e integração via SAC.

**PDR-007 — x402 para micropagamentos de AI.** A AI cobra em XLM por query premium (HTTP 402). *Justificativa:* modelo de receita on-chain nativo para a economia agentic — entregável explícito do 37 Graus.

**PDR-008 — Track A no 37 Graus.** A base do protocolo está funcional e auditada; a integração Stellar é expansão, não rebuild. Classificação coerente com o estágio real e competitiva nos critérios de escala.

---

## Anexo B — Decisões de Arquitetura (ADRs)

**ADR-001 — `StellarAdapter` como camada de abstração de protocolo.** Encapsula Horizon, Soroban e EtherFuse; o `OrchestrationService` delega conforme a intenção detectada. *Rejeitado:* lógica Stellar dispersa nos controllers (acoplamento, sem teste isolado).

**ADR-002 — XDR gerado no backend, assinado no frontend (non-custodial).** O backend monta o XDR unsigned; o Freighter assina; o backend submete. As chaves do usuário nunca tocam o servidor.

**ADR-003 — Stellar DEX (path payments) para swaps.** `pathPaymentStrictSend/Receive` via Horizon path finding. *Vantagem:* liquidez nativa da L1, sem contrato de terceiro nem aprovação de token.

**ADR-004 — Soroban `xiaolee_core` com storage `persistent` e auth por `Address`.** `instance` para config global, `persistent` por usuário (TTL bumped pelo backend); `Address::require_auth()` sem workarounds; token via SAC.

**ADR-005 — $XLEE como Stellar Asset + SAC.** Asset emitido + `stellar contract asset deploy`; o contrato usa o SAC para transferir. UX de trustline guiada pelo chat (assinatura em um clique no Freighter).

**ADR-006 — PostgreSQL com coluna `chain` para eventos multi-origem.** `chain VARCHAR(16)` em `campaign_participants`/`swap_records` e `stellar_wallet` em `user_profiles`; `twitter_id` permanece FK primária. Migração `20260515_stellar_columns.py`.

**ADR-007 — Horizon event_stream (SSE) para indexação on-chain.** Task asyncio escuta transações via cursor `now`; eventos do contrato são processados e persistidos. *Rejeitado:* polling por cron (latência e custo).

---

## Anexo C — Referência de Endpoints e Configuração

### C.1 Endpoints (backend FastAPI)

| Endpoint | Método | Responsabilidade |
|---|---|---|
| `/auth/stellar/challenge` | GET | Gera o challenge XDR (SEP-10) |
| `/auth/stellar/token` | POST | Valida o XDR assinado e emite o JWT |
| `/stellar/swap/quote` | GET | Quote de swap via Stellar DEX (path payment) |
| `/stellar/anchor/info` | GET | Info da âncora SEP-24 |
| `/stellar/anchor/challenge` | GET | Challenge da âncora SEP-24 |
| `/stellar/anchor/deposit` | POST | Inicia o depósito via âncora SEP-24 |
| `/v1/ai/query` | POST | Query de AI premium com micropagamento x402 |
| `/v1/ai/query/payment-info` | GET | Instruções de pagamento (asset, amount, pay_to) |
| `/v1/ai/query/verify-tx` | GET | Verifica o `tx_hash` do pagamento |
| `/campaigns/join` · `/verify` · `/claim` | POST | Ciclo de vida da campanha (idempotente, 409 em duplicidade) |
| `/metrics` | GET | Prometheus |
| `/health` · `/health/detailed` | GET | Liveness e dependências (DB, Solana, Gemini) |

### C.2 Configuração (mainnet)

```
STELLAR_NETWORK          = mainnet
Horizon                  = https://horizon.stellar.org
Soroban RPC              = https://mainnet.sorobanrpc.com
STELLAR_X402_PRICE_XLM   = 0.5
STELLAR_X402_ENABLED     = true
xiaolee_core (Soroban)   = <<SOROBAN_CONTRACT_ID>>
SAC $XLEE                = <<XLEE_SAC_CONTRACT_ID>>
Asset $XLEE              = XLEE:<<XLEE_ISSUER_G_ADDRESS>>
SOLANA_CLUSTER           = devnet   (rail multi-chain paralelo)
SOLANA_PROGRAM_ID        = Fmmpn79Tij8fzYHg31ekZz4MmK9ArGzN59VogfcwhXiM
```

### C.3 Stack tecnológico

| Camada | Tecnologia |
|---|---|
| Smart contract (Stellar) | Soroban SDK (Rust/WASM) — mainnet |
| Smart contract (Solana, paralelo) | Anchor (Rust) — devnet |
| Wallet | Freighter + `@stellar/freighter-api` |
| Swaps | Stellar DEX via Horizon path payments |
| Token | Stellar Asset `XLEE` + SAC (SEP-41) |
| Autenticação | SEP-10 challenge/response → JWT |
| Micropagamento de AI | x402 (HTTP 402, XLM) |
| On/off ramp BR/LATAM | EtherFuse API (parceiro 37 Graus) |
| Backend | FastAPI (Python 3.12) + asyncio |
| Frontend | Next.js 15 (TypeScript) |
| Banco de dados | PostgreSQL 16 + Alembic async (coluna `chain`) |
| Cache / rate limit | Redis sliding window + fallback in-memory |
| Observabilidade | Prometheus `/metrics` + Grafana |
| Testes | 61 passando · auditoria interna (23 findings corrigidos) |

---

*XiaoLee — AI ops layer não-custodial para a economia de criadores sobre Stellar.*
*Programa 37 Graus — NearX/SDF · Track A · 2026 · Beta em mainnet.*
