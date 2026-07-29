import { apiFetch } from '@/api/client';

/**
 * Chamadas tipadas do backend. Os tipos espelham os response models do
 * FastAPI — ver `backend/server/app.py`, `backend/server/schemas.py` e
 * `backend/server/campaigns_routes.py`.
 *
 * Só o que a tela de diagnóstico precisa está aqui; chat, agente e
 * notificações entram conforme as telas forem construídas.
 */

/** `GET /health` — `backend/server/app.py` */
export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  environment: string;
  solana_cluster: string;
  gemini_enabled: boolean;
}

/** Item do feed de traction — `backend/server/metrics.py::record_payment_settled` */
export interface PaymentEvent {
  intent_id: string;
  amount: number;
  creator: string;
  tx: string;
  ts: string;
  latency_ms: number;
}

/** `GET /v1/traction/stats` — `backend/server/schemas.py::TractionSnapshot` */
export interface TractionSnapshot {
  total_usdc: number;
  total_payments: number;
  active_creators: number;
  registered_creators: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  feed: PaymentEvent[];
}

/** `GET /campaigns` — `backend/server/campaigns_routes.py` */
export interface Campaign {
  id: number;
  name: string;
  description: string;
  campaign_type: string;
  completed_participants: number;
  created_at: string;
  creator_twitter_user_id: string;
  max_participants: number;
  profile_to_follow: string | null;
  reward_per_participant: number;
  reward_pool: number;
  reward_token: string;
  status: string;
  tweet_id_to_engage: string | null;
}

export interface CampaignsResponse {
  success: boolean;
  campaigns: Campaign[];
}

/** `POST /auth/session` — `backend/server/campaigns_routes.py::auth_session` */
export interface SessionResponse {
  session_id: string;
  twitter_user_id: string;
  username: string;
  address: string;
}

/**
 * Troca o ID token do Firebase por uma sessão do backend.
 *
 * O backend confere a assinatura do token contra o JWKS do Google antes de
 * emitir a sessão — por isso só o token vai no corpo. Mandar `address`/`email`
 * daqui não teria efeito: a rota ignora o corpo como fonte de identidade
 * (é o furo que ela substitui, ver `/auth/google/login`).
 */
export function loginWithFirebase(idToken: string): Promise<SessionResponse> {
  return apiFetch<SessionResponse>('/auth/session', {
    method: 'POST',
    json: { provider: 'firebase', id_token: idToken },
    skipAuth: true,
  });
}

/** Rota pública — não exige sessão. */
export function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>('/health', { skipAuth: true });
}

/** Rota pública — é o painel que o júri abre. */
export function getTractionStats(): Promise<TractionSnapshot> {
  return apiFetch<TractionSnapshot>('/v1/traction/stats', { skipAuth: true });
}

/** Rota pública — a lista de campanhas não filtra por usuário. */
export function listCampaigns(): Promise<CampaignsResponse> {
  return apiFetch<CampaignsResponse>('/campaigns', { skipAuth: true });
}
