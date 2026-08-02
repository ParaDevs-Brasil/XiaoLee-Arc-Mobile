# XiaoLee Mobile — status da branch `feature/frontend-ui`



Este documento resume o que existe hoje no app mobile, de onde vem o dado de
cada tela, e o que falta para fechar a paridade com o web ou para o produto
funcionar de ponta a ponta.

---

## 1. Telas — o que existe

| Tela | Rota | Fonte de dado | Sessão? |
|---|---|---|---|
| Chat | `/` (index) | `POST /chat` | Não exige — backend trata como `web_anonymous` |
| Traction | `/traction` | `GET /v1/traction/stats` + SSE `GET /v1/traction/feed` | Pública |
| Dashboard | `/dashboard` | `GET /v1/arc/wallet/balance`, `GET /v1/cctp/treasury/{chain}/balance`, `GET /v1/traction/stats`, `GET /campaigns/me` | Parcial — bloco pessoal exige sessão, resto é público |
| Notifications | `/notifications` | `GET /v1/notifications/me`, `POST /v1/notifications/{id}/ack` | Exige sessão (vazio sem ela) |
| Campaigns | `/campaigns` | `GET /campaigns` (pública) + `GET /campaigns/me` | Parcial — listar é público, entrar/verificar/resgatar exigem sessão |
| New Campaign | `/campaigns/new` (modal) | `POST /campaigns/create` | Exige sessão |
| Wallet | `/wallet` | `GET /campaigns/me`, agregado por token | Exige sessão (vazio sem ela) |
| Transactions | `/transactions` | `GET /campaigns/me` + `GET /v1/notifications/me`, cruzados e deduplicados por `related_signature` | Exige sessão (vazio sem ela) |
| History | `/history` | `AsyncStorage` local (`lib/chat-history.ts`) — **não é o backend** | Não exige — é dado do aparelho |
| Diagnostics | `/diagnostics` | `GET /health` | Pública — ferramenta de desenvolvimento, sem entrada no menu |

**Total: 10 telas.** Todas com `tsc --noEmit`, `expo lint` e `npm test` passando a cada commit.

### Divergências deliberadas do web (não são bugs)

- **Dashboard** não usa os números fixos do web (`$1,240,500` de TVL etc.) — usa o recorte real de `/v1/traction/stats`.
- **Wallet** não lê `GET /v1/arc/balance/{address}` como o web: não há endereço, porque o mobile não tem conector de carteira. Em vez disso, agrega recompensas de campanha por token.
- **Transactions** não lê o dossiê (`swaps`/`transactions` do `GET /user/{id}`) porque o backend devolve essas listas vazias por contrato (`campaigns_routes.py:557`). Constrói o extrato cruzando resgates de campanha com notificações assinadas.
- **History** não lê do backend porque o backend nunca grava conversa em lugar nenhum — nem para o web. Replica a solução do próprio web: gravar cada troca no armazenamento do cliente (`localStorage` lá, `AsyncStorage` aqui).

---

## 2. Conexão com o backend

### Rotas do backend em uso pelo mobile

```
POST /chat
GET  /health
GET  /v1/traction/stats
GET  /v1/traction/feed              (SSE)
GET  /v1/arc/wallet/balance
GET  /v1/cctp/treasury/{chain}/balance
GET  /campaigns
GET  /campaigns/me
POST /campaigns/create
GET  /v1/notifications/me
POST /v1/notifications/{id}/ack
POST /auth/session                  (cliente pronto — ver seção 3)
```

### Rotas do backend que o mobile não usa (existem, ~60 no total)

Notáveis para o roadmap:

- `POST /v1/agent/run-campaign` + `GET /v1/agent/run-campaign/{id}/status` — o loop agêntico (critério **Agentic**, 30% da nota do hackathon). **Rota pública, sem `Authorization`.** Nenhuma tela do mobile aciona isso hoje.
- `POST /v1/creator/register` — onboarding de creator (funil de entrada da **Traction**, 30% da nota). Exige assinatura de wallet.
- `GET /v1/arc/balance/{address}` — saldo on-chain de um endereço específico. Só é útil com conector de carteira.
- `POST /auth/google/login`, `POST /auth/telegram/login` — login por outros canais.
- Rotas Stellar/Solana (`stellar_routes.py`, `webhooks/helius_routes.py`) — da era pré-pivô para Arc; não fazem sentido para o mobile hoje.

---

## 3. Autenticação — o maior item pendente

O fluxo existe **e está testado**, só não está ligado a nenhum botão.

- `mobile/src/lib/auth.ts` — `signInAndStartSession()`: Google Sign-In → credencial Firebase → `POST /auth/session` (o backend valida o ID token contra o JWKS do Google) → grava sessão via `SecureStore`.
- `mobile/src/lib/session.ts` — leitura/escrita da sessão, com fallback pra `localStorage` no web.
- `mobile/src/hooks/use-session.ts` — **devolve `null` sempre**, porque nada chama `signInAndStartSession`.
- `mobile/src/components/profile-menu.tsx` — o botão "Sign in with Google" já existe visualmente e recebe `onSignIn?: () => void`, mas **`ScreenShell` nunca passa esse prop** (`screen-shell.tsx:55`).

### Efeito em cascata de não estar ligado

Toda tela que faz `if (!hasSession)` mostra o estado de convidado permanentemente:

- Campaigns: não dá pra entrar, verificar tarefas nem resgatar recompensa.
- New Campaign: formulário existe, mas toda submissão falharia (a rota exige `Bearer`).
- Wallet, Transactions, Notifications: sempre vazias.
- Dashboard: bloco "Your campaigns" sempre no estado de convidado.

### O que falta, concretamente

1. Em `screen-shell.tsx`, passar `onSignIn={() => signInAndStartSession().then(...)}` para `ProfileMenu`.
2. Tratar erro do fluxo (`GoogleSignInCancelled` é esperado e não deve virar toast de erro).
3. Depois do login, as telas já reagem sozinhas — `useSession`/`useBackendData` releem o storage.
4. Testar no dev client (Expo Go **não** carrega os módulos nativos do Firebase — só funciona em build nativo).

---

## 4. O que falta por tela/área

| Item | Bloqueio | Esforço estimado |
|---|---|---|
| **Ligar o login** (seção 3) | Nenhum — só falta o fio | Pequeno |
| **Onboarding de creator** (`/onboarding` no web) | Backend exige assinatura EIP-191/Ed25519 de posse da wallet — mobile não tem conector | Médio/grande (depende de WalletConnect) |
| **Painel do agente** (`AgentStatus`/`useAgentStatus` no web) | Nenhum — rota é pública | Médio — não existe nenhuma tela ainda |
| **Connect Wallet / Withdraw / Deposit** (linhas do `ProfileMenu`) | Sem conector de carteira no mobile | Grande — mesmo bloqueio do Onboarding |
| **Contador de caracteres no composer do chat** | Nenhum | Pequeno |
| **Animação do teclado em `campaigns/new.tsx`** | Perdida ao trocar `KeyboardAvoidingView` por medida direta (layout correto, transição seca) | Pequeno/médio (`LayoutAnimation`, não testável sem aparelho) |
| **Rebuild do dev client** | Mudanças nativas pendentes: plugin da status bar (`app.json`) e `@react-native-async-storage/async-storage` (módulo nativo novo) | Trivial, só rodar `npx expo run:android` |
| **`mobile/AGENTS.md`** não documenta a decisão de storage (`AsyncStorage` vs. memória) | — | Trivial |
| **Verificação visual em aparelho/simulador real** | Nenhuma tela desta sessão (Wallet, Transactions, History, correções de teclado/status bar) foi confirmada rodando — só validada por `tsc`/`lint`/`test` | — |

### Sem dono ainda (não avaliado nesta branch)

- Loop agêntico como tela mobile — o maior gap de pontuação do hackathon (Agentic 30%) sem superfície nenhuma no app.
- PQC receipt (Innovation 20%) — não tem componente de UI previsto em lugar nenhum ainda, mobile ou web.
- Modo escuro — suspenso por decisão de design (`constants/theme.ts`), não é falta, é escolha.

---

## 5. Dívida técnica notada mas não corrigida

- `campaigns/new.tsx`: teclado corrige a posição certa, mas sem a animação suave que o `KeyboardAvoidingView` dava de graça no chat.
- `mobile/src/app/diagnostics.tsx`: ferramenta de dev sem entrada no menu — permanece acessível só por navegação direta, de propósito.
- Nenhuma tela nova tem teste automatizado de UI (só os módulos puros em `lib/` têm `*.test.ts`, rodados via `node --experimental-strip-types`).
