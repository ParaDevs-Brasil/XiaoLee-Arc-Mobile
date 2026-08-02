import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

/**
 * Token de sessão emitido por `POST /auth/telegram/login` ou
 * `POST /auth/google/login` — vai como `Bearer` em todas as chamadas
 * autenticadas do backend.
 *
 * No web (`expo start --web`) o SecureStore não existe; caímos para
 * localStorage, que é o que o frontend Next.js já usa.
 */
const SESSION_KEY = 'xiaolee_session_id';
const USER_ID_KEY = 'xiaolee_twitter_user_id';
const HANDLE_KEY = 'xiaolee_handle';
const WALLET_KEY = 'xiaolee_wallet_address';
const WALLET_CHAIN_KEY = 'xiaolee_wallet_chain';

const isWeb = Platform.OS === 'web';

async function readItem(key: string): Promise<string | null> {
  if (isWeb) {
    try {
      return globalThis.localStorage?.getItem(key) ?? null;
    } catch {
      return null;
    }
  }
  return SecureStore.getItemAsync(key);
}

async function writeItem(key: string, value: string): Promise<void> {
  if (isWeb) {
    try {
      globalThis.localStorage?.setItem(key, value);
    } catch {
      // storage indisponível (modo privado) — sessão fica só em memória
    }
    return;
  }
  await SecureStore.setItemAsync(key, value);
}

async function removeItem(key: string): Promise<void> {
  if (isWeb) {
    try {
      globalThis.localStorage?.removeItem(key);
    } catch {
      // nada a limpar
    }
    return;
  }
  await SecureStore.deleteItemAsync(key);
}

export interface Session {
  sessionId: string;
  twitterUserId: string;
  /**
   * Nome de exibição — o `username` que `/auth/session` devolve.
   *
   * Guardado separado do `twitterUserId` porque os dois não são a mesma coisa:
   * o id é interno (`firebase_<uid>`) e é o que vai nas requisições; o handle é
   * o nome da conta Google, e é o que o painel de perfil deve mostrar. Sem ele
   * o usuário logado aparecia como `@firebase_9x8s7…`.
   */
  handle?: string;
}

/**
 * Fonte única e reativa da sessão.
 *
 * Antes cada tela lia o storage na montagem e guardava o resultado em estado
 * local. Existiam três cópias da mesma verdade — a do `ScreenShell`, a de cada
 * `useSession()` e a do storage — e nada ligava uma na outra: depois do login o
 * painel de perfil mostrava o usuário e a tela atrás dele seguia dizendo
 * "No session yet" até o app reabrir.
 *
 * Agora quem grava avisa quem estiver ouvindo. O cache síncrono existe porque
 * `useSyncExternalStore` exige um snapshot sem `await`, e o storage é assíncrono.
 */
type Listener = () => void;
const listeners = new Set<Listener>();

/** `undefined` = storage ainda não lido; `null` = lido, e não há sessão. */
let cached: Session | null | undefined;

function emit(): void {
  for (const listener of listeners) listener();
}

export function subscribeSession(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Snapshot síncrono para `useSyncExternalStore`. */
export function getCachedSession(): Session | null | undefined {
  return cached;
}

/**
 * Compara conteúdo, não referência.
 *
 * `useSyncExternalStore` re-renderiza sempre que o snapshot muda de
 * identidade. Como `getSession` monta um objeto novo a cada leitura, publicar
 * sem comparar faria cada releitura repintar todas as telas assinantes.
 */
function sameSession(a: Session | null | undefined, b: Session | null): boolean {
  if (a === undefined) return false;
  if (a === null || b === null) return a === b;
  return (
    a.sessionId === b.sessionId &&
    a.twitterUserId === b.twitterUserId &&
    a.handle === b.handle
  );
}

export async function getSessionToken(): Promise<string | null> {
  const token = await readItem(SESSION_KEY);
  return token?.trim() || null;
}

export async function getSession(): Promise<Session | null> {
  const [sessionId, twitterUserId, handle] = await Promise.all([
    readItem(SESSION_KEY),
    readItem(USER_ID_KEY),
    readItem(HANDLE_KEY),
  ]);
  const next: Session | null = sessionId?.trim()
    ? {
        sessionId: sessionId.trim(),
        twitterUserId: twitterUserId?.trim() ?? '',
        handle: handle?.trim() || undefined,
      }
    : null;

  if (!sameSession(cached, next)) {
    cached = next;
    emit();
  }
  return next;
}

export async function saveSession(session: Session): Promise<void> {
  await Promise.all([
    writeItem(SESSION_KEY, session.sessionId),
    writeItem(USER_ID_KEY, session.twitterUserId),
    session.handle ? writeItem(HANDLE_KEY, session.handle) : removeItem(HANDLE_KEY),
  ]);
  cached = session;
  emit();
}

export async function clearSession(): Promise<void> {
  await Promise.all([
    removeItem(SESSION_KEY),
    removeItem(USER_ID_KEY),
    removeItem(HANDLE_KEY),
    removeItem(WALLET_KEY),
    removeItem(WALLET_CHAIN_KEY),
  ]);
  cached = null;
  emit();
}

/**
 * Carteira de payout do usuário — o endereço para onde o agente manda USDC.
 *
 * Guardada aqui só como cache local do que o backend já tem: o vínculo real é
 * feito por `POST /auth/wallet`, autenticado pela sessão. É o equivalente ao
 * que o web mantém em `localStorage` para mandar em cada `/chat`.
 */
export interface ConnectedWallet {
  address: string;
  chain: string;
}

export async function getWallet(): Promise<ConnectedWallet | null> {
  const [address, chain] = await Promise.all([
    readItem(WALLET_KEY),
    readItem(WALLET_CHAIN_KEY),
  ]);
  if (!address?.trim()) return null;
  return { address: address.trim(), chain: chain?.trim() || 'arc' };
}

export async function saveWallet(wallet: ConnectedWallet): Promise<void> {
  await Promise.all([
    writeItem(WALLET_KEY, wallet.address),
    writeItem(WALLET_CHAIN_KEY, wallet.chain),
  ]);
}

export async function clearWallet(): Promise<void> {
  await Promise.all([removeItem(WALLET_KEY), removeItem(WALLET_CHAIN_KEY)]);
}
