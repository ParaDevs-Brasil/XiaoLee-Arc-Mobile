import '@walletconnect/react-native-compat';

import {
  AppKit,
  AppKitProvider,
  createAppKit,
  useAccount,
  useAppKit,
  useProvider,
} from '@reown/appkit-react-native';
import { WagmiAdapter } from '@reown/appkit-wagmi-react-native';
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { defineChain } from 'viem';
import { mainnet } from 'viem/chains';

import {
  getArcChainConfig,
  getArcGasFees,
  getUsdcAuthorizationDomain,
  relayUsdcAuthorization,
} from '@/api/backend';
import { appKitStorage } from '@/lib/appkit-storage';
import { shortHash } from '@/lib/format';
import { clearSession, clearWallet, getWallet, saveSession, saveWallet, type ConnectedWallet } from '@/lib/session';

/**
 * Provider de WalletConnect para o app mobile.
 *
 * Migrado de `@walletconnect/modal-react-native` (descontinuado, ver git log)
 * para `@reown/appkit-wagmi-react-native` — SDK atual, mantido pela mesma
 * Reown que roda o relay. `@walletconnect/modal-react-native@1.1.0` era o
 * suspeito nº 1 quando a MetaMask 8.5 parou de mostrar qualquer tela de
 * aprovação de conexão: lib abandonada não acompanha mudança de protocolo do
 * lado da carteira.
 *
 * A carteira conectada **é** a sessão do app: não há login separado (ver
 * `lib/auth.ts`, removido) — `saveSession` grava o endereço como identidade
 * assim que a carteira conecta, e é essa identidade que vai como `Bearer` em
 * toda chamada autenticada (`api/client.ts::apiFetch`).
 */

const PROJECT_ID = process.env.EXPO_PUBLIC_WC_PROJECT_ID?.trim() || 'CHANGE_ME';

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
 * O critério é **suportar rede EVM customizada**, não popularidade — mesma
 * lógica de antes da migração, ver histórico do arquivo.
 */
const RECOMMENDED_WALLETS = [
  'c57ca95b47569778a828d19178114f4db188b89b763c899ba0be274e97267d96', // MetaMask
  '18388be9ac2d02726dbac9777c96efaac06d744b2f6d580fccdd4127a6d01fd1', // Rabby
  '4622a2b2d6af1c9844944291e5e7351a6aa24cd7b23099efac1b2fd875da31a0', // Trust Wallet
  '971e689d0a5be527bac79629b4ee9b925e82208e5168b733496a09c0faed0709', // OKX Wallet
];

/**
 * Chain do Arc Testnet, espelho de `ARC_CHAIN_ID` no backend
 * (`server/settings.py:97`, exposto em `GET /v1/arc/chain-config`).
 */
const ARC_CHAIN_ID = 5042002;

/**
 * RPC público do Arc Testnet — o mesmo que estava em uso antes da migração.
 * Quem consulta este endereço é o app da carteira, não o nosso backend.
 */
const ARC_PUBLIC_RPC = 'https://rpc.testnet.arc.network';

/**
 * Declaração da chain Arc no formato que `WagmiAdapter`/`createAppKit` esperam
 * (`viem.Chain`, que é estruturalmente o mesmo `Network` do AppKit).
 *
 * Entra como chain suportada igual ao Ethereum mainnet — não há mais a
 * separação required/optional manual que o `SESSION_PARAMS` da lib antiga
 * precisava: o AppKit decide sozinho como negociar isso com a carteira.
 */
const arcTestnet = defineChain({
  id: ARC_CHAIN_ID,
  name: 'Arc Testnet',
  nativeCurrency: { name: 'USDC', symbol: 'USDC', decimals: 6 },
  rpcUrls: { default: { http: [ARC_PUBLIC_RPC] } },
  blockExplorers: { default: { name: 'Arc Explorer', url: 'https://testnet.arcscan.app' } },
  testnet: true,
});

/**
 * Mainnet entra junto: é a chain que garante que a conexão inicial funcione
 * com qualquer carteira, mesmo uma que nunca vai ouvir falar do Arc — mesmo
 * raciocínio do `eip155:1` que já estava no `SESSION_PARAMS` antigo.
 */
const wagmiAdapter = new WagmiAdapter({
  projectId: PROJECT_ID,
  networks: [mainnet, arcTestnet],
});

/**
 * Singleton — `createAppKit` avisa que uma segunda chamada com config
 * diferente é ignorada, então isto só pode rodar uma vez, em module scope.
 */
let appKit: ReturnType<typeof createAppKit>;
try {
  appKit = createAppKit({
    projectId: PROJECT_ID,
    metadata: APP_METADATA,
    adapters: [wagmiAdapter],
    networks: [mainnet, arcTestnet],
    storage: appKitStorage,
    includeWalletIds: RECOMMENDED_WALLETS,
    themeMode: 'light',
  });
} catch (err) {
  console.log('[appkit] createAppKit falhou:', (err as Error)?.stack ?? String(err));
  throw err;
}

interface WalletConnectContextValue {
  isConnected: boolean;
  address: string | undefined;
  /** Chain da sessão viva do WalletConnect. */
  chain: string | undefined;
  /**
   * Se a carteira tem uma conta ativa na rede Arc — lido das contas da sessão.
   *
   * Falso é o caso comum e não tem conserto pelo app: nenhuma carteira traz o
   * Arc Testnet de fábrica. Enquanto for falso, assinar qualquer coisa do Arc
   * pode ser recusado, então vale avisar antes em vez de deixar o usuário
   * descobrir no meio de uma transferência.
   */
  hasArcNetwork: boolean;
  openModal: () => void;
  disconnect: () => void;
  /** Assina e envia a tx preparada pelo backend. Devolve o hash. */
  signAndSend: (tx: EvmTxRequest) => Promise<string>;
  /**
   * Transfere USDC no Arc por autorização assinada (EIP-3009), sem exigir que a
   * carteira esteja na rede Arc. Devolve o hash da tx submetida pelo backend.
   */
  signAndRelay: (to: string, amountUsdc: number) => Promise<string>;
  /**
   * Assinatura EIP-191 (`personal_sign`) sobre uma mensagem UTF-8 qualquer —
   * devolve a assinatura hex de 65 bytes. É a prova de posse da carteira que o
   * backend confere em `_verify_claim_proof` (`campaigns_routes.py`) para
   * resgates de campanha sem sessão custodial.
   */
  signMessage: (message: string) => Promise<string>;
}

/**
 * Rótulo de chain a partir do chainId ativo — `'arc'`, `eip155:<id>` para
 * qualquer outra, ou `'evm'` sem conexão nenhuma ainda. Vira nota de sistema
 * no prompt do agente (`app.py:442`), então precisa ser verdade, não um
 * `'arc'` fixo torcendo para o usuário estar na chain certa.
 */
function chainLabel(chainId: string | undefined): string {
  if (!chainId) return 'evm';
  return Number(chainId) === ARC_CHAIN_ID ? 'arc' : `eip155:${chainId}`;
}

/**
 * O provider fala JSON-RPC; só isto é usado daqui. Mesmo formato que
 * `@reown/appkit-react-native`'s `Provider.request` — compatível de propósito,
 * para as funções abaixo não precisarem saber qual SDK está por trás.
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

  try {
    await provider.request({
      method: 'wallet_switchEthereumChain',
      params: [{ chainId: config.chainIdHex }],
    });
    return;
  } catch (err) {
    console.log('[arc] switch falhou, tentando add:', describeRpcError(err));
  }

  try {
    await provider.request({
      method: 'wallet_addEthereumChain',
      params: [
        {
          chainId: config.chainIdHex,
          chainName: config.chainName,
          rpcUrls: [ARC_PUBLIC_RPC],
          blockExplorerUrls: config.blockExplorerUrls,
          nativeCurrency: config.nativeCurrency,
        },
      ],
    });
    console.log('[arc] rede adicionada com RPC', ARC_PUBLIC_RPC);
  } catch (err) {
    console.log('[arc] add falhou:', describeRpcError(err));
  }
}

/** Janela de validade da autorização. Curta: é uma ordem de pagamento assinada. */
const AUTHORIZATION_TTL_S = 3600;

/**
 * Transfere USDC no Arc sem a carteira precisar estar no Arc.
 *
 * O usuário assina um typed data (EIP-3009 `transferWithAuthorization`) e o
 * backend submete on-chain pagando o gas. `eth_signTypedData_v4` funciona em
 * qualquer rede, porque é só uma assinatura, enquanto `eth_sendTransaction`
 * exige a rede cadastrada.
 */
async function signAndRelayAuthorization(
  requester: Requester,
  from: string,
  to: string,
  amountUsdc: number,
): Promise<string> {
  await ensureArcNetwork(requester);

  const domain = await getUsdcAuthorizationDomain();
  const validBefore = Math.floor(Date.now() / 1000) + AUTHORIZATION_TTL_S;
  const nonce = randomNonce();
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

  console.log(`[3009] assinando: ${amountUsdc} USDC → ${to} | chainId ${domain.chainId}`);

  // Sempre no escopo do Arc — lição da migração anterior: cair no default da
  // sessão deixava o pedido implicitamente noutra chain enquanto o
  // domain.chainId dizia Arc, descompasso que MetaMask 8.5 não tolerava.
  const scope = `eip155:${ARC_CHAIN_ID}`;

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
 * Assina uma mensagem UTF-8 via EIP-191 `personal_sign` — porta de
 * `frontend/src/lib/evmWallet.ts::signEvmMessage`. Não passa por
 * `ensureArcNetwork`: assinar uma mensagem não depende de rede.
 */
async function personalSign(requester: Requester, address: string, message: string): Promise<string> {
  const hex =
    '0x' + Array.from(new TextEncoder().encode(message), (b) => b.toString(16).padStart(2, '0')).join('');
  return (await requester.request({ method: 'personal_sign', params: [hex, address] })) as string;
}

/** Nonce de 32 bytes da autorização — imprevisível, então `crypto.getRandomValues`, nunca `Math.random`. */
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
 * Apaga o estado que o WalletConnect guarda no AsyncStorage.
 *
 * `appKit.disconnect()` encerra a sessão pelo relay, mas deixa para trás
 * pareamentos e registros de sessão. Quando esses registros sobrevivem a uma
 * sessão que morreu do outro lado, o app manda pedidos para um tópico que não
 * existe mais — a carteira recebe algo que não reconhece, ignora, e abre na
 * tela inicial sem nada para aprovar.
 *
 * O keychain fica de fora, e isso não é detalhe: é lá que vive a identidade
 * que assina o JWT de autenticação com o relay. Apagá-lo derruba o app
 * inteiro do WalletConnect.
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
 * defesas que o web descobriu contra testnet custom:
 *
 *  - **gas explícito**: a Rabby desabilita o "Sign" quando não consegue SIMULAR
 *    a tx numa chain que ela não conhece. Com o gas já no payload ela não
 *    depende da simulação.
 *  - **fee EIP-1559 explícito**: a MetaMask mostra "Network fee: Unavailable" e
 *    trava, porque não estima fee sozinha no Arc.
 */
async function sendTransaction(
  requester: Requester,
  from: string,
  tx: EvmTxRequest,
): Promise<string> {
  await ensureArcNetwork(requester);

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
    params.gas = '0x' + Math.ceil(Number.parseInt(estimate, 16) * 1.3).toString(16);
  } catch {
    // estimativa falhou — segue sem gas explícito
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

const WCContext = createContext<WalletConnectContextValue | null>(null);

export function WalletConnectProvider({ children }: { children: ReactNode }) {
  return (
    <AppKitProvider instance={appKit}>
      <WalletConnectInner>{children}</WalletConnectInner>
      <AppKit />
    </AppKitProvider>
  );
}

function WalletConnectInner({ children }: { children: ReactNode }) {
  const { isConnected, address, chainId, allAccounts } = useAccount();
  const { provider } = useProvider();
  const { open, disconnect: appKitDisconnect } = useAppKit();
  const [storedWallet, setStoredWallet] = useState<ConnectedWallet | null>(null);
  /** Endereço já gravado como sessão nesta execução — evita regravar a cada render. */
  const established = useRef<string>(undefined);

  useEffect(() => {
    getWallet().then(setStoredWallet);
  }, []);

  // Quando conecta via WalletConnect, a carteira vira a sessão do app — não há
  // login separado: `saveSession` grava o endereço como identidade assim que a
  // carteira conecta, e é essa identidade que vai como `Bearer` em toda
  // chamada autenticada (`api/client.ts::apiFetch`).
  useEffect(() => {
    if (!isConnected || !address) return;
    if (established.current === address.toLowerCase()) return;
    established.current = address.toLowerCase();

    const id = address.toLowerCase();
    const chain = chainLabel(chainId);
    let cancelled = false;
    Promise.all([
      saveSession({ sessionId: id, twitterUserId: id, handle: shortHash(address) }),
      saveWallet({ address, chain }),
    ]).then(() => {
      if (!cancelled) setStoredWallet({ address, chain });
    });

    return () => {
      cancelled = true;
    };
  }, [isConnected, address, chainId]);

  const openModal = () => open();

  /**
   * Encerra a sessão e apaga o rastro local dela — desconectar a carteira é o
   * único "logout" que existe no app. Também é o único jeito de renegociar a
   * sessão quando a config muda: a carteira guarda o que aprovou no handshake.
   */
  const disconnect = async () => {
    try {
      await appKitDisconnect();
    } catch {
      // sessão já pode ter caído do outro lado — seguir e limpar mesmo assim
    }
    await purgeWalletConnectStorage();
    established.current = undefined;
    setStoredWallet(null);
    await Promise.all([clearWallet(), clearSession()]);
  };

  async function signAndSend(tx: EvmTxRequest): Promise<string> {
    const requester = provider as Requester | undefined;
    if (!requester || !address) throw new Error('Nenhuma carteira conectada.');
    return sendTransaction(requester, address, tx);
  }

  async function signAndRelay(to: string, amountUsdc: number): Promise<string> {
    const requester = provider as Requester | undefined;
    if (!requester || !address) throw new Error('Nenhuma carteira conectada.');
    console.log('[3009] chainId ativo:', chainId, '| contas:', allAccounts.length);
    return signAndRelayAuthorization(requester, address, to, amountUsdc);
  }

  async function signMessage(message: string): Promise<string> {
    const requester = provider as Requester | undefined;
    if (!requester || !address) throw new Error('Nenhuma carteira conectada.');
    return personalSign(requester, address, message);
  }

  const value = useMemo(
    () => ({
      isConnected,
      address,
      chain: isConnected ? chainLabel(chainId) : storedWallet?.chain,
      hasArcNetwork: allAccounts.some((a) => a.chainId === String(ARC_CHAIN_ID)),
      openModal,
      disconnect,
      signAndSend,
      signAndRelay,
      signMessage,
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [isConnected, address, chainId, allAccounts, storedWallet, provider],
  );

  return <WCContext.Provider value={value}>{children}</WCContext.Provider>;
}

export function useWalletConnect(): WalletConnectContextValue {
  const ctx = useContext(WCContext);
  if (!ctx) {
    throw new Error('useWalletConnect deve ser usado dentro de WalletConnectProvider');
  }
  return ctx;
}
