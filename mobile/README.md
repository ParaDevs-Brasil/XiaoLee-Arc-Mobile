# XiaoLee Mobile

App React Native (Expo SDK 57) que consome o backend FastAPI em `../backend`.

## Rodar

O app precisa do backend no ar — ele é a fonte de tudo (chat, campanhas, agente, traction).

```bash
# terminal 1 — na raiz do repositório
make dev-backend          # uvicorn em 0.0.0.0:8000

# terminal 2
make init-mobile          # só na primeira vez: cria .env + npm install
make dev-mobile           # Metro; leia o QR code com o app Expo Go
```

Atalhos: `make dev-mobile-android`, `make dev-mobile-ios`, `make dev-mobile-web`.

A primeira tela é um diagnóstico de conexão: mostra qual `API_URL` foi resolvida, se o
backend respondeu e os números de traction ao vivo. Se aparecer "SEM CONEXÃO", o
problema é de rede/URL, não do app.

## Como a URL do backend é resolvida

`localhost` dentro do app **não** é a sua máquina — é o próprio aparelho. Por isso
[`src/lib/config.ts`](src/lib/config.ts) resolve o host nesta ordem:

1. `EXPO_PUBLIC_API_URL` do `.env`, se preenchida — use para staging/produção
2. host do Metro (`Constants.expoConfig.hostUri`) + porta 8000 — o caso comum em dev,
   funciona tanto no emulador quanto em aparelho físico na mesma rede
3. fallback por plataforma (`10.0.2.2` no Android, `localhost` no resto)

Variáveis `EXPO_PUBLIC_*` são embutidas no bundle em build time e ficam legíveis por
qualquer um que baixe o app — **nunca coloque segredo nelas**.

## Estrutura

| Caminho | Responsabilidade |
|---|---|
| `src/api/client.ts` | `fetch` com base URL, `Bearer` automático, timeout e `ApiError` normalizado |
| `src/api/backend.ts` | Chamadas tipadas do backend — os tipos espelham os response models do FastAPI |
| `src/lib/config.ts` | Resolução da URL do backend |
| `src/lib/session.ts` | Token de sessão em SecureStore (localStorage no web) |
| `src/app/` | Rotas (expo-router, file-based) |

## O que ainda não existe

Este é o setup inicial. Antes de portar as telas do frontend web, três decisões
estão em aberto:

- **Auth** — `_resolve_user` no backend aceita qualquer string como `Bearer` e cria o
  usuário na hora. Precisa virar JWT assinado antes de qualquer build de loja.
- **Wallet** — Phantom, Freighter e o modal do Web3Auth são extensão de browser e não
  funcionam aqui. O caminho é custodial via Circle W3S ou WalletConnect.
- **SSE** — `/v1/traction/feed` usa `EventSource`, que não existe em React Native.
  Ou `react-native-sse`, ou polling em `/v1/traction/stats`.
