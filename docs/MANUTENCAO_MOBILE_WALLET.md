# Manutenção — Mobile, carteira e assinatura no Arc

> **Status:** levantado em 2026-08-01, durante a validação do fluxo de transferência no celular.
> **Contexto:** a transferência USDC gasless (EIP-3009) foi provada de ponta a ponta — 1 USDC
> transferido, assinatura EIP-712 aceita pela MetaMask, tx confirmada on-chain, usuário sem gastar
> gas. O que está listado aqui é o que ficou pelo caminho.
> **Cada item traz a evidência**, não a impressão: quase tudo aqui custou horas de diagnóstico, e
> repetir a investigação seria desperdício.

---

## 1. Intent de transferência exige endereço na frase

**Prioridade: alta.** É fricção visível numa demo.

O botão de assinar só aparece quando a mensagem contém o endereço `0x…`. Sem ele, o detector
classifica como `help` e o agente devolve ajuda genérica.

| mensagem | intent | botão |
|---|---|---|
| `manda 1 usdc pro 0x4D4c…` | `evm_transfer_prepare` | sim |
| `transfere 0.5 usdc para 0x4D4c…` | `evm_transfer_prepare` | sim |
| `quero enviar 1 USDC` | `help` | **não** |
| `send 1 usdc` | `help` | **não** |

Português ou inglês não muda nada — o que decide é ter o destino.

**O incômodo é que o caminho certo já existe e não é alcançado.** O
`orchestration/service.py:946` trata exatamente esse caso: quando falta valor ou endereço, ele
instrui o agente a *pedir o que falta*. Só que a mensagem nunca chega lá, porque o detector já
classificou como `help` antes.

**Proposta:** reconhecer a intenção de transferir mesmo sem o destino, deixando o
`evm_transfer_missing_info` fazer o trabalho dele — perguntar "para qual endereço?" em vez de
responder com ajuda genérica.

---

## 2. `purgeWalletConnectStorage` está no código e é perigoso

**Prioridade: alta.** Uma linha para remover.

Em `mobile/src/lib/walletconnect.tsx`, o `disconnect` apaga chaves `wc@` do AsyncStorage. Foi
adição nossa para contornar sessão órfã, e **quebrou de duas formas distintas**:

1. Apagando o keychain, eliminou o `client_ed25519_seed` — a identidade que assina o JWT do relay.
   Resultado: `WebSocket connection failed for host: wss://relay.walletconnect.com` em todos os
   sockets, e o app inteiro sem WalletConnect.
2. Preservando o keychain mas limpando `subscription`/`history`, tirou a contabilidade do relayer
   com ele rodando. Resultado: laço infinito de `attemptToReconnect`, e a sessão nunca fecha —
   foi o que impediu a conexão de completar mesmo com o usuário aprovando na carteira.

Só dispara ao tocar em **Disconnect**; passivamente não atrapalha.

**Proposta:** remover a chamada e deixar `provider.disconnect()`, que é o caminho suportado. Se
sobrar sessão órfã, a recuperação honesta é reinstalar o app — não brigar com o armazenamento do
SDK.

---

## 3. Cadastro da rede Arc Testnet não pode ser automatizado

**Prioridade: média.** Não há conserto; é escolha de UX.

Carteira mobile só opera em rede que o usuário registrou nela. Todas as vias foram testadas:

| tentativa | resultado |
|---|---|
| `wallet_addEthereumChain` por WalletConnect | Rabby: `-32601 method does not exist`. MetaMask: recebe e nunca responde |
| Arc em `optionalNamespaces` | carteira ignora; chain fica fora do escopo e assinar dá `-32602` |
| Arc em `namespaces` (obrigatório) | conexão **nunca fecha** — a carteira rejeita a proposta, como manda a especificação |
| Migrar para Reown AppKit | faz o mesmo pedido; conferido no código-fonte dele |

**A diferença com o web é o transporte, não a lógica.** Nosso `ensureArcNetwork` é porte linha a
linha do `frontend/src/lib/evmWallet.ts:117`, incluindo o fallback `4902` e o gas explícito. No web
o provider é injetado pela extensão e o método funciona; por WalletConnect, não.

**É pedágio de testnet, não limitação permanente.** A MetaMask já traz o Arc **mainnet** (chainId
5042) de fábrica — apareceu no escopo da sessão sem nenhuma ação do usuário. Em mainnet a fricção
some sozinha.

**Proposta:** tela guiada com os parâmetros copiáveis e o caminho de menu por carteira. Foi
construída e descartada por qualidade visual; a decisão de produto segue de pé. Não investir em
onboarding elaborado para um problema que o mainnet dissolve.

Parâmetros: `Arc Testnet` · RPC `https://rpc.testnet.arc.network` · chainId `5042002` · símbolo
`USDC` · explorer `https://testnet.arcscan.app`. Cuidado com `5042`, que é a mainnet.

---

## 4. `@walletconnect/modal-react-native` está descontinuado

**Prioridade: média.** Três defeitos já corrigidos com remendo; virão mais.

| defeito | contorno atual |
|---|---|
| `react-native-modal@13` chama `BackHandler.removeEventListener`, API removida do RN | override para `14.0.0-rc.1` |
| Ícones em branco: `image_url` virou objeto e `/getWalletImage/` responde 404 | `patch-package` + `postinstall` |
| Métodos não declarados no handshake são recusados antes de chegar à carteira | `SESSION_PARAMS` explícito |

**Migrar para `@reown/appkit-wagmi-react-native`.** O levantamento já foi feito: todas as
dependências nativas exigidas (`netinfo`, `get-random-values`, `react-native-compat`) **já estão
linkadas no APK**, então é migração de JavaScript puro — sem prebuild, sem APK novo.

Atenção: o AppKit exige `wagmi >=2 <3.0.0` e temos 3.7.5. Nenhum arquivo do `src/` importa wagmi,
então o downgrade é seguro — ou usa-se a variante `ethers`.

**E não espere que resolva o item 3:** ele faz o mesmo pedido de namespace que já fazemos.

---

## 5. Vínculo da carteira no backend exige login

`POST /auth/wallet` responde **401** sem sessão, e o Google Sign-In está quebrado (item 7). O chat
já funciona sem o vínculo — lê a sessão viva do WalletConnect — mas campanhas dependem dele.

Há também uma marca de "endereço já tentado" que **não é limpa quando o usuário entra na conta
depois**, então vincular exige reconectar a carteira. Está registrada como `ponytail:` no código.

---

## 6. Chave do Gemini vaza nos logs

**Prioridade: alta se for para produção.**

O `httpx` grava a URL completa das chamadas, e a `GEMINI_API_KEY` vai na query string. Ela está em
texto puro nos logs do backend.

**Proposta:** silenciar o log de URL do httpx e rotacionar a chave atual.

Registro do que aconteceu na sessão: a chave devolveu `403 PERMISSION_DENIED — Lightning dunning
decision is deny`, que é bloqueio por **faturamento**, não cota. O agente parou de gerar texto,
mas as transações continuaram sendo preparadas corretamente.

---

## 7. Google Sign-In em `DEVELOPER_ERROR`

O `expo prebuild --clean` regenerou o `android/` com o keystore de debug padrão do template, cujo
SHA-1 não está registrado no Firebase.

| | SHA-1 |
|---|---|
| APK atual | `5e8f1606 2ea3cd2c 4a0d5478 76baa6f3 8cabf625` |
| Registrado no `google-services.json` | `326729ea 8b0b3285 0f3215f8 dff9c8f6 3c77956a` |

**Proposta:** adicionar o fingerprint atual no Firebase Console. É aditivo — o APK antigo do EAS
continua funcionando.

---

## 8. `/auth/google/login` aceita endereço sem prova de posse

**Prioridade: alta antes de mainnet.** É falha de autenticação, não de UX.

A rota do web (`campaigns_routes.py:600`) recebe um endereço Solana no corpo e emite sessão a
partir dele — `twitter_user_id = f"google_{address[:20]}"`. **Quem enviar o endereço de outra
pessoa recebe a sessão dela.**

O mobile usa `/auth/session`, que valida a assinatura do token contra o JWKS do Google. É a rota
correta. O próprio `mobile/src/api/backend.ts:76` chama a outra de "o furo que ela substitui".

**Proposta:** migrar o web para `/auth/session` e aposentar a rota antiga.

---

## 9. Ambiente de desenvolvimento no aparelho

Anotações que economizam tempo de quem for retomar:

- **A MIUI bloqueia** `adb install`, `pm clear` e `adb shell input`. Instalação é pelo APK em
  `/sdcard/Download` tocado no gerenciador de arquivos; navegação por deep link
  (`xiaolee://wallet`); toques só na janela do scrcpy.
- **A porta 8000 está ocupada** pelo `solana-test-validator`. O backend sobe na 8010.
- **A carteira precisa de um RPC que ela alcance.** O `chain-config` deriva o `rpcUrls` do host da
  requisição, então `localhost` (via `adb reverse`) serve o XiaoLee mas **não** o app da carteira.
  Use o RPC público do Arc.
- **MetaMask bloqueada engole pedidos.** Quando exige biometria, os pedidos do WalletConnect ficam
  parados sem mostrar nada — parece travamento e não é.
- **Trazer a carteira para a frente é do SDK.** Ele chama `handleDeeplinkRedirect` com `requestId`
  e `sessionTopic` depois de publicar o pedido. Um deep link próprio abre a carteira sem contexto
  e antes do pedido existir; ela mostra a tela inicial e o pedido vence.

---

## 10. Carteiras ainda não testadas

Trust e OKX nunca chegaram a conectar. Phantom foi excluída da lista do mobile por causa do
comentário em `evmWallet.ts:154` (catálogo de chains fechado), **mas o modal do web a lista com
badge ARC** — vale confirmar se o comentário está desatualizado antes de mantê-la fora.
