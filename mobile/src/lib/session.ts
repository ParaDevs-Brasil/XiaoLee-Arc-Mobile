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
}

export async function getSessionToken(): Promise<string | null> {
  const token = await readItem(SESSION_KEY);
  return token?.trim() || null;
}

export async function getSession(): Promise<Session | null> {
  const [sessionId, twitterUserId] = await Promise.all([
    readItem(SESSION_KEY),
    readItem(USER_ID_KEY),
  ]);
  if (!sessionId?.trim()) return null;
  return { sessionId: sessionId.trim(), twitterUserId: twitterUserId?.trim() ?? '' };
}

export async function saveSession(session: Session): Promise<void> {
  await Promise.all([
    writeItem(SESSION_KEY, session.sessionId),
    writeItem(USER_ID_KEY, session.twitterUserId),
  ]);
}

export async function clearSession(): Promise<void> {
  await Promise.all([
    removeItem(SESSION_KEY),
    removeItem(USER_ID_KEY),
    removeItem(WALLET_KEY),
    removeItem(WALLET_CHAIN_KEY),
  ]);
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
