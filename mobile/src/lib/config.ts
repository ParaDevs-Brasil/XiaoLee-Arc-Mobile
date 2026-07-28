import Constants from 'expo-constants';
import { Platform } from 'react-native';

/**
 * Porta do backend FastAPI (`make dev-backend` sobe em 0.0.0.0:8000).
 */
const BACKEND_PORT = 8000;

/**
 * `localhost` no app não é o `localhost` da máquina de desenvolvimento:
 * no emulador Android o host é `10.0.2.2`, e num aparelho físico é o IP da
 * máquina na LAN. O Metro já sabe esse endereço — ele está em `hostUri`
 * (ex.: `192.168.0.10:8081`), então derivamos o host do backend dele.
 */
function apiUrlFromPackager(): string | null {
  const hostUri = Constants.expoConfig?.hostUri;
  if (!hostUri) return null;

  const host = hostUri.split(':')[0];
  if (!host) return null;

  // `expo start` com adb reverse reporta localhost; nesse caso o emulador
  // Android ainda precisa do alias 10.0.2.2 para alcançar a máquina host.
  if (Platform.OS === 'android' && (host === 'localhost' || host === '127.0.0.1')) {
    return `http://10.0.2.2:${BACKEND_PORT}`;
  }

  return `http://${host}:${BACKEND_PORT}`;
}

function fallbackApiUrl(): string {
  if (Platform.OS === 'android') return `http://10.0.2.2:${BACKEND_PORT}`;
  return `http://localhost:${BACKEND_PORT}`;
}

/**
 * Base URL do backend, em ordem de precedência:
 *  1. `EXPO_PUBLIC_API_URL` no .env — use para apontar para staging/produção
 *  2. host do Metro + porta 8000 — o caso comum em desenvolvimento
 *  3. fallback por plataforma
 *
 * Atenção: variáveis `EXPO_PUBLIC_*` são embutidas no bundle em build time.
 * Nunca coloque segredo nelas.
 */
export const API_URL: string =
  process.env.EXPO_PUBLIC_API_URL?.trim() || apiUrlFromPackager() || fallbackApiUrl();

/** De onde a URL veio — exibido na tela de diagnóstico. */
export const API_URL_SOURCE: 'env' | 'packager' | 'fallback' = process.env
  .EXPO_PUBLIC_API_URL?.trim()
  ? 'env'
  : apiUrlFromPackager()
    ? 'packager'
    : 'fallback';

/** Timeout das chamadas HTTP, em ms. */
export const REQUEST_TIMEOUT_MS = 15_000;
