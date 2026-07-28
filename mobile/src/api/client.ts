import { API_URL, REQUEST_TIMEOUT_MS } from '@/lib/config';
import { getSessionToken } from '@/lib/session';

/**
 * Cliente HTTP do backend XiaoLee — mesma responsabilidade de
 * `frontend/src/api/api.tsx` (base URL + Bearer automático + erro
 * normalizado), sobre `fetch` e com SecureStore no lugar do localStorage.
 */

/** Erro de API já normalizado — `message` é sempre exibível ao usuário. */
export class ApiError extends Error {
  readonly status: number | null;
  readonly isNetworkError: boolean;

  constructor(message: string, status: number | null, isNetworkError: boolean) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.isNetworkError = isNetworkError;
  }
}

/**
 * FastAPI responde erro como `{"detail": "..."}` e falha de validação como
 * `{"detail": [{msg, loc, ...}]}` — as duas viram uma string legível.
 */
function messageFromBody(body: unknown): string | null {
  if (typeof body !== 'object' || body === null) return null;

  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === 'string') return detail;

  if (Array.isArray(detail)) {
    const msgs = detail
      .map((item) =>
        typeof item === 'object' && item !== null ? (item as { msg?: unknown }).msg : null,
      )
      .filter((msg): msg is string => typeof msg === 'string');
    if (msgs.length > 0) return msgs.join('; ');
  }

  const message = (body as { message?: unknown }).message;
  return typeof message === 'string' ? message : null;
}

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  /** Serializado como JSON. Use `method: 'POST'` junto. */
  json?: unknown;
  /** Sobrescreve o timeout padrão, em ms. */
  timeoutMs?: number;
  /** `true` pula a injeção do Bearer (rotas públicas). */
  skipAuth?: boolean;
}

/**
 * Faz a chamada e devolve o JSON já tipado, ou lança `ApiError`.
 *
 * `fetch` não tem timeout nativo — sem o AbortController abaixo, um backend
 * inacessível deixaria a tela girando indefinidamente em vez de mostrar erro.
 */
export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { json, timeoutMs = REQUEST_TIMEOUT_MS, skipAuth = false, headers, ...init } = options;

  const requestHeaders = new Headers(headers);
  requestHeaders.set('Accept', 'application/json');
  if (json !== undefined) requestHeaders.set('Content-Type', 'application/json');

  if (!skipAuth && !requestHeaders.has('Authorization')) {
    const token = await getSessionToken();
    if (token) requestHeaders.set('Authorization', `Bearer ${token}`);
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: requestHeaders,
      signal: controller.signal,
      ...(json !== undefined ? { body: JSON.stringify(json) } : {}),
    });
  } catch (error) {
    const aborted = error instanceof Error && error.name === 'AbortError';
    throw new ApiError(
      aborted
        ? `Backend não respondeu em ${timeoutMs / 1000}s (${API_URL})`
        : `Não foi possível alcançar o backend em ${API_URL}`,
      null,
      true,
    );
  } finally {
    clearTimeout(timeoutId);
  }

  const raw = await response.text();
  let body: unknown = null;
  if (raw) {
    try {
      body = JSON.parse(raw);
    } catch {
      // resposta não-JSON — `body` fica null e o texto cru vira a mensagem
    }
  }

  if (!response.ok) {
    const detail = messageFromBody(body) ?? raw.slice(0, 200);
    throw new ApiError(detail || `HTTP ${response.status}`, response.status, false);
  }

  return body as T;
}
