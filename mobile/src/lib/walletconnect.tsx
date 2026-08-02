import '@walletconnect/react-native-compat';

import {
  useWalletConnectModal,
  WalletConnectModal,
} from '@walletconnect/modal-react-native';
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';

import {
  getArcChainConfig,
  getArcGasFees,
  getUsdcAuthorizationDomain,
  linkWallet,
  relayUsdcAuthorization,
} from '@/api/backend';
import { ApiError } from '@/api/client';
import { useSession } from '@/hooks/use-session';
import { clearWallet, getWallet, saveWallet, type ConnectedWallet } from '@/lib/session';

/**
 * Provider de WalletConnect para o app mobile.
 *
 * Abre o modal nativo de seleção de carteira (Metamask, Rainbow, Trust, etc.)
 * e vincula o endereço conectado ao backend via POST /auth/wallet.
 */

const PROJECT_ID = process.env.EXPO_PUBLIC_WC_PROJECT_ID?.trim() || 'CHANGE_ME';
const RELAY_URL = 'wss://relay.walletconnect.com';

const APP_METADATA = {
  name: 'XiaoLee',
  description: 'XiaoLee - AI DeFi Assistant',
  url: 'https://xiaolee.ai',
  icons: ['https://xiaolee.ai/icon.png'],
  redirect: {
    native: 'xiaolee://',
    universal: 'https://xiaolee.ai',
  },
};

/**
 * As carteiras que abrem o picker, na ordem.
 *
 * Sem isto o modal mostra o conjunto padrão do explorer da Reown, que trazia
 * Binance, SafePal, Fireblocks e TokenPocket à frente de Rabby e Phantom —
 * carteiras que ninguém do público do XiaoLee usa. Os IDs vêm do explorer
 * (`explorer-api.walletconnect.com/v3/wallets`) e são estáveis.
 *
 * O critério é **suportar rede EVM customizada**, não popularidade: o Arc é um
 * testnet (chainId 5042002) que nenhuma carteira traz de fábrica — confirmado
 * no explorer da Reown, onde nem MetaMask nem Rabby declaram essa chain. Quem
 * não deixa adicionar rede à mão simplesmente não consegue operar no Arc.
 *
 * Por isso Phantom e Rainbow ficam de fora, apesar de populares: as duas têm
 * catálogo de chains fechado. É a mesma conclusão a que o web já tinha chegado
 * (`frontend/src/lib/evmWallet.ts:154` manda o usuário para MetaMask ou Rabby
 * quando o `wallet_addEthereumChain` é recusado).
 *
 * São quatro porque o modal só mostra cinco antes do "View All", e ainda promove
 * a recente e as instaladas para as primeiras posições — lista maior não amplia
 * o grid, só empurra as últimas para fora dele.
 */
const RECOMMENDED_WALLETS = [
  'c57ca95b47569778a828d19178114f4db188b89b763c899ba0be274e97267d96', // MetaMask
  '18388be9ac2d02726dbac9777c96efaac06d744b2f6d580fccdd4127a6d01fd1', // Rabby
  '4622a2b2d6af1c9844944291e5e7351a6aa24cd7b23099efac1b2fd875da31a0', // Trust Wallet
  '971e689d0a5be527bac79629b4ee9b925e82208e5168b733496a09c0faed0709', // OKX Wallet
];

interface WalletConnectContextValue {
  isConnected: boolean;
  address: string | undefined;
  /**
   * Chain da sessão viva, independente do vínculo no backend.
   *
   * Existe porque `POST /auth/wallet` exige sessão de login, e o chat precisa
   * saber a carteira mesmo sem ela — conectar carteira e entrar na conta são
   * coisas distintas.
   */
  chain: string | undefined;
  /**
   * Se a carteira conhece a rede Arc — lido do escopo da sessão.
   *
   * Falso é o caso comum e não tem conserto pelo app: nenhuma carteira traz o
   * Arc Testnet de fábrica, e cadastrá-la por WalletConnect não é possível (a
   * Rabby avisa "wallet_addEthereumChain not supported"; a MetaMask engole o
   * pedido). Enquanto for falso, assinar qualquer coisa do Arc é recusado com
   * `-32602`, então vale avisar antes em vez de deixar o usuário descobrir no
   * meio de uma transferência.
   */
  hasArcNetwork: boolean;
  isLinking: boolean;
  linkError: string | null;
  openModal: () => void;
  disconnect: () => void;
  /** Assina e envia a tx preparada pelo backend. Devolve o hash. */
  signAndSend: (tx: EvmTxRequest) => Promise<string>;
  /**
   * Transfere USDC no Arc por autorização assinada (EIP-3009), sem exigir que a
   * carteira esteja na rede Arc. Devolve o hash da tx submetida pelo backend.
   */
  signAndRelay: (to: string, amountUsdc: number) => Promise<string>;
}

/**
 * Chain do Arc Testnet, espelho de `ARC_CHAIN_ID` no backend
 * (`server/settings.py:97`, exposto em `GET /v1/arc/chain-config`).
 *
 * Duplicado aqui de propósito, em vez de buscado: serve só para dar nome à
 * chain no rótulo que vai para o agente. Se o id do testnet mudar, o rótulo
 * degrada para `eip155:<id>` — continua verdadeiro, só menos legível.
 */
const ARC_CHAIN_ID = 5042002;

/**
 * RPC público do Arc Testnet — o mesmo que `viem/chains` publica em `arcTestnet`.
 *
 * Existe separado do RPC do backend de propósito: o nosso (`/v1/arc/rpc`) é um
 * proxy que injeta o token do Canteen server-side e, em desenvolvimento, vive
 * atrás de um túnel. Quem precisa deste endereço é o **app da carteira**, que
 * não passa por nada disso.
 */
const ARC_PUBLIC_RPC = 'https://rpc.testnet.arc.network';

/**
 * O que a sessão pede à carteira no handshake.
 *
 * Sem isto a sessão sobe com o conjunto padrão de métodos, que **não inclui**
 * `wallet_addEthereumChain` — a carteira rejeita o pedido de adicionar o Arc, e
 * como nenhuma carteira traz o chainId 5042002 de fábrica, a rede nunca
 * aparece. Foi o que a tela "No Custom Network" da Rabby mostrou.
 *
 * Vai em `optionalNamespaces` e não em `requiredNamespaces`: exigir a chain do
 * Arc no handshake faria carteira nenhuma conseguir conectar, porque nenhuma a
 * declara (confirmado no explorer da Reown).
 */
const SESSION_PARAMS = {
  // `namespaces` é o obrigatório e precisa existir: é ele que registra o
  // rpcProvider do eip155 no universal provider. Passar só `optionalNamespaces`
  // quebra a inicialização com `Provider not found:` de namespace vazio.
  //
  // Fica com `eip155:1` e os métodos que toda carteira implementa. A chain do
  // Arc não entra aqui porque exigi-la no handshake faria a conexão inteira ser
  // recusada — nenhuma carteira a declara (conferido no explorer da Reown).
  namespaces: {
    eip155: {
      // Só o que **toda** carteira implementa. Método obrigatório que a carteira
      // não tem bloqueia a conexão inteira: a Rabby avisa na tela com
      // "Unsupported required WalletConnect request: 1 method
      // (wallet_addEthereumChain) not supported" e não deixa conectar.
      //
      // Os métodos de rede (`wallet_switchEthereumChain`/`wallet_addEthereumChain`)
      // ficam em `optionalNamespaces`: quem tiver, oferece; quem não tiver,
      // conecta do mesmo jeito.
      methods: ['eth_sendTransaction', 'personal_sign', 'eth_signTypedData_v4'],
      chains: ['eip155:1'],
      events: ['chainChanged', 'accountsChanged'],
      rpcMap: {},
    },
  },
  /**
   * O Arc entra como **opcional**, com o RPC público junto.
   *
   * Motivo: a carteira devolveu `-32602 Invalid params` ao assinar um typed data
   * cujo `domain.chainId` é 5042002 enquanto a sessão só tinha `eip155:1` no
   * escopo. Declarar a chain aqui é o que dá à sessão um escopo onde esse
   * domínio faz sentido.
   *
   * Opcional e não obrigatório porque nenhuma carteira declara o Arc (conferido
   * no explorer da Reown): exigi-la faria a conexão inteira ser recusada, em vez
   * de só esta assinatura.
   *
   * O `rpcMap` usa o RPC público oficial (o mesmo que o `viem/chains` publica em
   * `arcTestnet`), não o nosso proxy: quem consulta esse endereço é o app da
   * carteira, que não passa pelo túnel de desenvolvimento.
   */
  optionalNamespaces: {
    eip155: {
      methods: [
        'eth_sendTransaction',
        'personal_sign',
        'eth_signTypedData_v4',
        'wallet_switchEthereumChain',
        'wallet_addEthereumChain',
      ],
      chains: [`eip155:${ARC_CHAIN_ID}`],
      events: ['chainChanged', 'accountsChanged'],
      rpcMap: { [ARC_CHAIN_ID]: ARC_PUBLIC_RPC },
    },
  },
};

/**
 * Em que chain a carteira **está**, lido da sessão do WalletConnect.
 *
 * Antes isto era `'arc'` fixo, o que era uma mentira na maioria das conexões: a
 * MetaMask conecta na rede em que o usuário estiver — quase sempre Ethereum
 * mainnet, não Arc. Esse rótulo vira nota de sistema no prompt do agente
 * (`app.py:442`), então um 'arc' errado faz ele raciocinar sobre a chain errada.
 *
 * O formato é CAIP-2: `accounts` traz `eip155:<chainId>:<address>`.
 */
function chainFromSession(accounts: string[] | undefined): string {
  const [namespace, id] = (accounts?.[0] ?? '').split(':');
  if (!namespace || !id) return 'evm';
  return Number(id) === ARC_CHAIN_ID ? 'arc' : `${namespace}:${id}`;
}

/** Nome da chain a partir do id numérico. */
function labelForChainId(id: number): string {
  return id === ARC_CHAIN_ID ? 'arc' : `eip155:${id}`;
}

/**
 * O provider do WalletConnect fala JSON-RPC; só isto é usado daqui.
 *
 * O segundo argumento é a chain CAIP-2 do pedido. Sem ele o provider usa a
 * default da sessão — e assinar um typed data do Arc no escopo de `eip155:1` foi
 * o que a carteira recusou com `-32602`.
 */
type Requester = {
  request: (args: { method: string; params?: unknown[] }, chain?: string) => Promise<unknown>;
};

/**
 * Pede à carteira para entrar na rede Arc, porta de `frontend/src/lib/evmWallet.ts`.
 *
 * Roda **na hora de assinar**, não ao conectar: é aqui que o Arc passa a ser
 * necessário, e é quando o usuário está esperando uma ação da carteira — pedir
 * o cadastro da rede no meio de uma conexão parece ruído.
 *
 * Toda a assinatura no Arc depende disto. A carteira externa se recusa a assinar
 * (`-32602`) e até a aprovar a chain no escopo da sessão enquanto não conhecer a
 * rede; foi o bloqueio que travou o fluxo inteiro.
 *
 * Não lança: se a carteira recusar, quem decide o que fazer é o chamador, com a
 * checagem de chain que roda logo depois.
 */
async function ensureArcNetwork(provider: Requester): Promise<void> {
  let config;
  try {
    config = await getArcChainConfig();
  } catch {
    return; // sem config o app não tem o que pedir — deixa a carteira decidir
  }

  try {
    const current = (await provider.request({ method: 'eth_chainId' })) as string;
    if (current?.toLowerCase() === config.chainIdHex.toLowerCase()) return;
  } catch {
    // carteira que não responde eth_chainId ainda pode aceitar o switch abaixo
  }

  // Toda requisição daqui pede aprovação humana na carteira, e a carteira fica
  // em SEGUNDO PLANO esperando. Sem trazê-la para a frente, o usuário encara o
  // app parado até o pedido vencer — foi exatamente o `Request expired` que
  // apareceu no log.
  try {
    await provider.request({
      method: 'wallet_switchEthereumChain',
      params: [{ chainId: config.chainIdHex }],
    });
    return;
  } catch (err) {
    // 4902 = chain desconhecida pela carteira, que é o caso esperado do Arc.
    // Qualquer outro código também cai no `add`: carteiras divergem no que
    // devolvem para uma chain que não conhecem, e tentar adicionar é inócuo
    // quando ela já existe.
    console.log('[arc] switch falhou, tentando add:', describeRpcError(err));
  }

  try {
    await provider.request({
      method: 'wallet_addEthereumChain',
      params: [
        {
          chainId: config.chainIdHex,
          chainName: config.chainName,
          // RPC público, e não o `config.rpcUrls` do backend: quem vai consultar
          // este endereço é o app da carteira, que não passa pelo túnel de
          // desenvolvimento nem tem o token do Canteen. Uma rede cadastrada com
          // RPC inalcançável é pior que rede nenhuma — ela é aceita e depois
          // falha em silêncio na hora de estimar gas.
          rpcUrls: [ARC_PUBLIC_RPC],
          blockExplorerUrls: config.blockExplorerUrls,
          nativeCurrency: config.nativeCurrency,
        },
      ],
    });
    console.log('[arc] rede adicionada com RPC', ARC_PUBLIC_RPC);
  } catch (err) {
    // Logado, e não engolido: foi justamente o silêncio aqui que escondeu por
    // que a rede nunca aparecia na carteira.
    console.log('[arc] add falhou:', describeRpcError(err));
  }
}

/** Janela de validade da autorização. Curta: é uma ordem de pagamento assinada. */
const AUTHORIZATION_TTL_S = 3600;

/**
 * Transfere USDC no Arc sem a carteira precisar estar no Arc.
 *
 * O usuário assina um typed data (EIP-3009 `transferWithAuthorization`) e o
 * backend submete on-chain pagando o gas. A diferença que faz isto existir:
 * `eth_signTypedData_v4` funciona em qualquer rede, porque é só uma assinatura,
 * enquanto `eth_sendTransaction` exige a rede cadastrada — e a Rabby mobile não
 * aceita `wallet_addEthereumChain` sobre WalletConnect (responde -32601).
 *
 * O que o usuário assina é exatamente o que acontece: valor, destino e prazo
 * estão na mensagem, e o contrato valida a assinatura contra eles. O backend não
 * consegue alterar nada sem invalidar a assinatura.
 */
async function signAndRelayAuthorization(
  requester: Requester,
  from: string,
  to: string,
  amountUsdc: number,
  approvedChains: string[],
): Promise<string> {
  // Primeiro passo, e o que destrava todo o resto: a carteira precisa conhecer
  // o Arc. Sem isso ela recusa o typed data com -32602, porque o `chainId` do
  // domínio aponta para uma rede que, para ela, não existe.
  await ensureArcNetwork(requester);

  const domain = await getUsdcAuthorizationDomain();
  const validBefore = Math.floor(Date.now() / 1000) + AUTHORIZATION_TTL_S;
  const nonce = randomNonce();
  // USDC tem 6 decimais; `Math.round` evita o 0.1+0.2 do ponto flutuante virar
  // um valor um wei menor que o pedido.
  const value = Math.round(amountUsdc * 1_000_000);

  const typedData = {
    types: {
      EIP712Domain: [
        { name: 'name', type: 'string' },
        { name: 'version', type: 'string' },
        { name: 'chainId', type: 'uint256' },
        { name: 'verifyingContract', type: 'address' },
      ],
      TransferWithAuthorization: [
        { name: 'from', type: 'address' },
        { name: 'to', type: 'address' },
        { name: 'value', type: 'uint256' },
        { name: 'validAfter', type: 'uint256' },
        { name: 'validBefore', type: 'uint256' },
        { name: 'nonce', type: 'bytes32' },
      ],
    },
    primaryType: 'TransferWithAuthorization',
    domain,
    message: {
      from,
      to,
      value: String(value),
      validAfter: '0',
      validBefore: String(validBefore),
      nonce,
    },
  };

  // A ordem dos parâmetros é [endereço, json] — invertida em relação a
  // `personal_sign`, e trocar devolve "invalid params" sem mais explicação.
  //
  // Os logs `[3009]` existem porque cada etapa daqui falha de um jeito diferente
  // e a carteira quase nunca diz qual: a assinatura pode ser recusada pelo
  // chainId do domínio, pelo método não declarado na sessão, ou pelo usuário.
  console.log(`[3009] assinando: ${amountUsdc} USDC → ${to} | chainId ${domain.chainId}`);

  // Manda no escopo do Arc quando a carteira aprovou essa chain; senão deixa o
  // provider usar a default, que é o melhor possível sem ela.
  const arcScope = `eip155:${ARC_CHAIN_ID}`;
  const scope = approvedChains.includes(arcScope) ? arcScope : undefined;
  console.log(`[3009] escopo do pedido: ${scope ?? '(default da sessão)'}`);

  let signature: string;
  try {
    signature = (await requester.request(
      {
        method: 'eth_signTypedData_v4',
        params: [from, JSON.stringify(typedData)],
      },
      scope,
    )) as string;
  } catch (err) {
    console.log('[3009] carteira recusou assinar:', describeRpcError(err));
    // O objeto cru costuma trazer `data` com o motivo real, que a mensagem
    // curta omite — é o que separa "chainId divergente" de "params malformado".
    console.log('[3009] erro completo:', JSON.stringify(err, Object.getOwnPropertyNames(err ?? {})));
    throw err;
  }
  console.log(`[3009] assinatura recebida (${signature?.length ?? 0} chars)`);

  const relayed = await relayUsdcAuthorization({
    from_address: from,
    to_address: to,
    value,
    valid_after: 0,
    valid_before: validBefore,
    nonce,
    signature,
  });
  console.log(`[3009] relay ok: tx=${relayed.tx_hash} confirmada=${relayed.confirmed}`);
  return relayed.tx_hash;
}

/**
 * Nonce de 32 bytes da autorização.
 *
 * É o que impede a mesma assinatura de ser submetida duas vezes — o contrato
 * grava cada nonce gasto. Precisa ser imprevisível, então vem do
 * `crypto.getRandomValues` (polyfill nativo de `react-native-get-random-values`,
 * que o compat do WalletConnect já carrega), nunca de `Math.random`.
 */
function randomNonce(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  return '0x' + [...bytes].map((b) => b.toString(16).padStart(2, '0')).join('');
}

/** O chainId numérico da carteira, ou `undefined` se ela não responder. */
async function currentChainId(requester: Requester): Promise<number | undefined> {
  try {
    const hex = (await requester.request({ method: 'eth_chainId' })) as string;
    const id = Number.parseInt(hex, 16);
    return Number.isFinite(id) ? id : undefined;
  } catch {
    return undefined;
  }
}

/** Erro de carteira vem como `{code, message}` puro, não como `Error`. */
function describeRpcError(err: unknown): string {
  if (err && typeof err === 'object') {
    const { code, message } = err as { code?: number; message?: unknown };
    return `code=${code ?? '?'} ${String(message ?? err)}`;
  }
  return String(err);
}

/**
 * Trazer a carteira para a frente é responsabilidade do **SDK**, não nossa.
 *
 * O sign-client chama `handleDeeplinkRedirect` logo depois de publicar cada
 * pedido no relay, e monta a URL com o contexto que importa:
 *
 *     ${redirect.native}/wc?requestId=<id>&sessionTopic=<topic>
 *
 * Nós tínhamos um `bringWalletToFront` próprio que abria apenas `metamask://`,
 * sem `requestId`, e **antes** de o pedido existir. A carteira abria na tela
 * inicial sem nada para aprovar, e o pedido vencia sozinho em segundo plano
 * (`Request expired`). Deletado: o SDK já fazia isso certo.
 */

/**
 * Apaga o estado que o WalletConnect guarda no AsyncStorage.
 *
 * O `provider.disconnect()` encerra a sessão pelo relay, mas deixa para trás
 * pareamentos e registros de sessão no armazenamento local. Quando esses
 * registros sobrevivem a uma sessão que morreu do outro lado, o app passa a
 * mandar pedidos para um tópico que não existe mais — a carteira recebe algo
 * que não reconhece, ignora, e abre na tela inicial sem nada para aprovar.
 *
 * Foi exatamente o que travou o fluxo: o `sessionTopic` em uso era o mesmo que o
 * SDK já tinha rejeitado com `No matching key. session topic doesn't exist`.
 *
 * Existe porque não há outra saída no aparelho: a MIUI bloqueia `pm clear`, e a
 * alternativa seria reinstalar o APK inteiro.
 *
 * **O keychain fica de fora, e isso não é detalhe.** É lá que vive o
 * `client_ed25519_seed`, a identidade que assina o JWT de autenticação com o
 * relay. Apagá-lo derruba o app inteiro do WalletConnect: sem semente, o
 * cliente não autentica, e todo socket morre com
 * `WebSocket connection failed for host: wss://relay.walletconnect.com`.
 */
async function purgeWalletConnectStorage(): Promise<void> {
  try {
    const AsyncStorage = (await import('@react-native-async-storage/async-storage')).default;
    const keys = await AsyncStorage.getAllKeys();
    const wcKeys = keys.filter(
      (k) => (k.startsWith('wc@') || k.startsWith('WALLETCONNECT')) && !k.includes('keychain'),
    );
    if (wcKeys.length) await AsyncStorage.multiRemove(wcKeys);
    console.log(`[wc] sessões e pareamentos limpos (${wcKeys.length} chaves, keychain preservado)`);
  } catch (err) {
    console.log('[wc] falha ao limpar estado local:', String(err));
  }
}

/** A transação que o backend prepara em `execution.evm_tx`. */
export interface EvmTxRequest {
  to: string;
  data: string;
  value?: string;
}

/**
 * Assina e envia a transação preparada pelo backend, na carteira conectada.
 *
 * Porta `frontend/src/lib/evmWallet.ts::sendEvmTransaction`, inclusive as duas
 * defesas que o web descobriu contra testnet custom — sem elas a carteira abre
 * mas não deixa assinar:
 *
 *  - **gas explícito**: a Rabby desabilita o "Sign" quando não consegue SIMULAR
 *    a tx numa chain que ela não conhece. Com o gas já no payload ela não
 *    depende da simulação.
 *  - **fee EIP-1559 explícito**: a MetaMask mostra "Network fee: Unavailable" e
 *    trava, porque não estima fee sozinha no Arc.
 *
 * A chave privada nunca passa por aqui: quem assina é a carteira, o app só
 * monta o pedido.
 */
async function sendTransaction(
  requester: Requester,
  from: string,
  tx: EvmTxRequest,
): Promise<string> {
  await ensureArcNetwork(requester);

  // Trava dura: assinar fora do Arc é perigoso, não só inútil. O `to` é o
  // contrato USDC do Arc e o `data` é uma chamada ERC-20 — em outra rede aquele
  // endereço é outra coisa, e a mesma calldata pode significar qualquer coisa.
  // A troca de rede falha em silêncio de propósito (ver `ensureArcNetwork`),
  // então a checagem tem que estar aqui, imediatamente antes de assinar.
  const chainId = await currentChainId(requester);
  if (chainId !== ARC_CHAIN_ID) {
    throw new Error(
      `Sua carteira está na chain ${chainId ?? 'desconhecida'}, não no Arc (${ARC_CHAIN_ID}). ` +
        'Adicione a rede Arc Testnet na carteira e selecione-a antes de assinar.',
    );
  }

  const params: Record<string, string> = {
    from,
    to: tx.to,
    data: tx.data,
    value: tx.value ?? '0x0',
  };

  try {
    const estimate = (await requester.request({
      method: 'eth_estimateGas',
      params: [{ from, to: tx.to, data: tx.data, value: params.value }],
    })) as string;
    params.gas = '0x' + Math.ceil(Number.parseInt(estimate, 16) * 1.3).toString(16); // +30% de folga
  } catch {
    // estimativa falhou — segue sem gas explícito, a carteira estima do jeito dela
  }

  let triedEip1559 = false;
  try {
    const fees = await getArcGasFees();
    params.maxFeePerGas = fees.maxFeePerGasHex;
    params.maxPriorityFeePerGas = fees.maxPriorityFeePerGasHex;
    triedEip1559 = true;
  } catch {
    // sem fee explícito — a carteira tenta sozinha
  }

  try {
    return (await requester.request({ method: 'eth_sendTransaction', params: [params] })) as string;
  } catch (err) {
    // Algumas carteiras recusam o tipo EIP-1559 mesmo a chain suportando
    // (-32602). Refaz como transação legada em vez de propagar o erro.
    const code = (err as { code?: number } | null)?.code;
    const message = (err as { message?: string } | null)?.message ?? '';
    if (!triedEip1559 || code !== -32602 || !/EIP-1559/i.test(message)) throw err;

    delete params.maxFeePerGas;
    delete params.maxPriorityFeePerGas;
    try {
      params.gasPrice = (await requester.request({ method: 'eth_gasPrice' })) as string;
    } catch {
      // a carteira estima
    }
    return (await requester.request({ method: 'eth_sendTransaction', params: [params] })) as string;
  }
}

/**
 * A chain em que a carteira está agora.
 *
 * Pergunta direto (`eth_chainId`) porque é a única fonte que reflete uma troca
 * de rede recente; a sessão do WalletConnect só é reescrita no próximo handshake.
 * Cai para a sessão quando a carteira não responde ao método.
 */
async function currentChain(
  requester: Requester | undefined,
  accounts: string[] | undefined,
): Promise<string> {
  const id = requester ? await currentChainId(requester) : undefined;
  // Sem resposta da carteira, a sessão ainda diz algo verdadeiro.
  return id === undefined ? chainFromSession(accounts) : labelForChainId(id);
}

const WCContext = createContext<WalletConnectContextValue | null>(null);

export function WalletConnectProvider({ children }: { children: ReactNode }) {
  const { isConnected, address, open, provider } = useWalletConnectModal();
  const { hasSession } = useSession();
  const [isLinking, setIsLinking] = useState(false);
  const [linkError, setLinkError] = useState<string | null>(null);
  const [storedWallet, setStoredWallet] = useState<ConnectedWallet | null>(null);
  const [liveChain, setLiveChain] = useState<string>();
  /** Endereço cujo vínculo já foi tentado nesta execução — evita repetir o POST. */
  const attempted = useRef<string>(undefined);

  // Restaura wallet do SecureStore na montagem
  useEffect(() => {
    getWallet().then(setStoredWallet);
  }, []);

  // A marca de "já tentei" morre quando a sessão aparece.
  //
  // Conectar a carteira antes de entrar na conta é o caminho comum, e ali o
  // vínculo falha com 401 `Sign in required` — a rota tira o dono do Bearer.
  // Sem zerar a marca, o login não re-tentava nada: a carteira ficava conectada
  // na tela, o erro pendurado embaixo dela, e vincular exigia desconectar e
  // reconectar. Roda antes do efeito de vínculo, que tem `hasSession` nas deps.
  //
  // Só mexe no ref: limpar o erro aqui seria `setState` no corpo do efeito, que
  // o lint barra com razão. Quem limpa é o `link()`, ao recomeçar.
  useEffect(() => {
    if (!hasSession) return;
    attempted.current = undefined;
  }, [hasSession]);

  // Quando conecta via WalletConnect, vincula ao backend.
  //
  // O corpo do efeito não chama `setState` direto (o lint do React barra, e com
  // razão: dispararia render em cascata) — quem chama é a cadeia da promise,
  // que já roda fora do render.
  useEffect(() => {
    if (!isConnected || !address) return;
    if (storedWallet && storedWallet.address.toLowerCase() === address.toLowerCase()) return;

    // Uma tentativa por endereço. Sem isto o vínculo vira laço: `provider` está
    // nas dependências, o `storedWallet` só é gravado quando o POST dá certo, e
    // um 401 (login ausente) deixava a guarda acima sempre aberta — quatro
    // chamadas em sequência foi o que apareceu no log do backend.
    //
    // A marca é zerada quando a sessão aparece (efeito acima), que é o caso em
    // que a tentativa anterior morreu de 401 e merece uma segunda chance.
    if (attempted.current === address.toLowerCase()) return;
    attempted.current = address.toLowerCase();

    const accounts = provider?.session?.namespaces?.eip155?.accounts;
    const requester = provider as Requester | undefined;

    let cancelled = false;
    async function link(wallet: string) {
      setIsLinking(true);
      setLinkError(null);
      try {
        // Sem tentar trocar a rede aqui, de propósito.
        //
        // O fluxo de transferência é gasless (EIP-3009): o usuário assina um
        // typed data, que vale em qualquer rede, e o backend submete no Arc. A
        // carteira nunca precisa estar no Arc.
        //
        // Tentar a troca mesmo assim custava duas requisições condenadas por
        // conexão — `wallet_switchEthereumChain` e `wallet_addEthereumChain` não
        // estão no namespace aprovado da sessão, então o cliente as recusa com
        // "Invalid params" e o usuário vê um LogBox vermelho ao conectar.
        const chain = await currentChain(requester, accounts);

        // Publicada antes de vincular, e de propósito: o vínculo é persistência
        // no backend e exige sessão, mas a carteira já está conectada e o
        // endereço já é conhecido aqui. Guardar isto atrás do login deixaria o
        // chat dizendo "conecte sua carteira" com a carteira conectada ao lado.
        if (!cancelled) setLiveChain(chain);

        const linked = await linkWallet(wallet, chain);
        const connected = { address: linked.address, chain: linked.chain };
        await saveWallet(connected);
        if (!cancelled) setStoredWallet(connected);
      } catch (err) {
        if (!cancelled) setLinkError(err instanceof ApiError ? err.message : String(err));
      } finally {
        if (!cancelled) setIsLinking(false);
      }
    }
    link(address);

    return () => {
      cancelled = true;
    };
    // `provider` entra nas deps porque a chain sai da sessão dele. Reexecutar
    // é barato: a checagem de `storedWallet` acima corta antes de vincular de
    // novo o mesmo endereço. `hasSession` entra para que o login re-dispare a
    // tentativa que falhou deslogada.
  }, [isConnected, address, storedWallet, provider, hasSession]);

  const openModal = () => open();

  /**
   * Encerra a sessão e apaga o rastro local dela.
   *
   * Limpar o estado importa tanto quanto derrubar a sessão: sem zerar
   * `attempted`, reconectar o mesmo endereço não tentaria vincular de novo; sem
   * `clearWallet`, o SecureStore continuaria servindo o endereço antigo ao chat.
   *
   * Também é o único jeito de renegociar a sessão quando os `SESSION_PARAMS`
   * mudam — a carteira guarda os métodos aprovados no handshake, e a Rabby
   * mobile não tem tela de "connected dapps" para desconectar do lado dela.
   */
  const disconnect = async () => {
    if (provider) {
      try {
        await provider.disconnect();
      } catch {
        // sessão já pode ter caído do outro lado — seguir e limpar mesmo assim
      }
    }
    await purgeWalletConnectStorage();
    attempted.current = undefined;
    setLiveChain(undefined);
    setLinkError(null);
    setStoredWallet(null);
    await clearWallet();
  };

  /** Assina e envia pela carteira conectada (caminho direto, exige rede Arc). */
  async function signAndSend(tx: EvmTxRequest): Promise<string> {
    const requester = provider as Requester | undefined;
    if (!requester || !address) throw new Error('Nenhuma carteira conectada.');

    return sendTransaction(requester, address, tx);
  }

  async function signAndRelay(to: string, amountUsdc: number): Promise<string> {
    const requester = provider as Requester | undefined;
    if (!requester || !address) throw new Error('Nenhuma carteira conectada.');

    // Os métodos aprovados são fixados no handshake e não mudam depois. Se
    // `eth_signTypedData_v4` não estiver aqui, a sessão é anterior a ele ter
    // entrado nos SESSION_PARAMS — e o cliente recusa com -32602 antes mesmo de
    // a carteira ver o pedido. Sem este log, isso é indistinguível de a carteira
    // ter recusado a assinatura.
    const ns = provider?.session?.namespaces?.eip155;
    console.log('[3009] métodos aprovados:', (ns?.methods ?? []).join(', ') || '(nenhum)');
    // As chains aprovadas importam tanto quanto os métodos: se a carteira exigir
    // que o `domain.chainId` do typed data bata com a chain da sessão, assinar
    // para o Arc (5042002) numa sessão de `eip155:1` é recusado — e é a hipótese
    // que o -32602 vindo da própria carteira levanta.
    console.log('[3009] chains aprovadas:', (ns?.chains ?? []).join(', ') || '(nenhuma)');
    console.log('[3009] contas:', (ns?.accounts ?? []).join(', ') || '(nenhuma)');

    return signAndRelayAuthorization(requester, address, to, amountUsdc, ns?.chains ?? []);
  }

  const value = useMemo(
    () => ({
      isConnected,
      address,
      chain: liveChain ?? storedWallet?.chain,
      hasArcNetwork: (provider?.session?.namespaces?.eip155?.chains ?? []).includes(
        `eip155:${ARC_CHAIN_ID}`,
      ),
      isLinking,
      linkError,
      openModal,
      disconnect,
      signAndSend,
      signAndRelay,
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [isConnected, address, liveChain, storedWallet, isLinking, linkError, provider],
  );

  return (
    <WCContext.Provider value={value}>
      {children}
      <WalletConnectModal
        projectId={PROJECT_ID}
        providerMetadata={APP_METADATA}
        relayUrl={RELAY_URL}
        sessionParams={SESSION_PARAMS}
        explorerRecommendedWalletIds={RECOMMENDED_WALLETS}
        themeMode="light"
      />
    </WCContext.Provider>
  );
}

export function useWalletConnect(): WalletConnectContextValue {
  const ctx = useContext(WCContext);
  if (!ctx) {
    throw new Error('useWalletConnect deve ser usado dentro de WalletConnectProvider');
  }
  return ctx;
}
