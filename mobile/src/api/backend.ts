import { ApiError, apiFetch } from '@/api/client';

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

/** `POST /chat` — `backend/server/app.py::chat_compat` */
export interface ChatResponse {
  /** O backend devolve uma lista de blocos; hoje só `type: "text"` é usado. */
  response: { type: string; content: string }[];
  intent: { action: string; confidence: number; entities: Record<string, unknown> };
  execution: Record<string, unknown>;
  code: string | null;
  /** Nome da animação a tocar — ver `animationFromBackend`. Pode vir null. */
  animations: string | null;
}

export interface ChatRequest {
  message: string;
  /** Endereço de payout, quando há carteira conectada. */
  wallet_address?: string;
  wallet_chain?: string;
}

/**
 * Manda a mensagem para o agente.
 *
 * Funciona sem sessão — o backend trata como `web_anonymous`. Com sessão, o
 * `Bearer` é injetado pelo `apiFetch` e o agente responde no contexto do
 * usuário (saldo, campanhas, histórico).
 */
export function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
  return apiFetch<ChatResponse>('/chat', {
    method: 'POST',
    // `platform: "web"` de propósito, e não "mobile": o backend ramifica em
    // `platform` para montar o prompt (`_wallet_ctx`, `_build_agentic_system_prompt`),
    // e só "web", "telegram" e "x" têm caminho escrito e testado. Mandar um
    // valor novo daqui criaria um comportamento que ninguém validou — o mobile
    // é a mesma experiência do app web, então usa o mesmo contexto.
    // Trocar para "mobile" só depois que o backend tratar o valor explicitamente.
    json: { ...request, platform: 'web' },
    // Timeout maior: a resposta depende de uma chamada a LLM.
    timeoutMs: 60_000,
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

/** `POST /campaigns/create` — `backend/server/campaigns_routes.py::create_campaign` */
export interface CreateCampaignRequest {
  title: string;
  description: string;
  /** `airdrop` | `engagement` | `referral` — os valores do select do web. */
  campaign_type: string;
  profile_to_follow?: string;
  tweet_id_to_engage?: string;
  reward_token: string;
  reward_per_participant: number;
  max_participants: number;
}

export interface CreateCampaignResponse {
  success: boolean;
  message: string;
  campaign: Campaign;
}

/**
 * Cria uma campanha. **Exige sessão**: a rota resolve o criador a partir do
 * `Bearer` (`_resolve_user`), então esta é a única chamada de campanha sem
 * `skipAuth`.
 *
 * `reward_pool` não vai no corpo de propósito — o backend o calcula como
 * `reward_per_participant * max_participants`, e mandar daqui abriria espaço
 * para os dois valores discordarem.
 */
export function createCampaign(request: CreateCampaignRequest): Promise<CreateCampaignResponse> {
  return apiFetch<CreateCampaignResponse>('/campaigns/create', {
    method: 'POST',
    json: request,
  });
}

/**
 * Item de `GET /v1/notifications/me` — `backend/server/notifications_routes.py::NotificationResponse`
 *
 * Repare que **não há timestamp**: o schema do backend não expõe `created_at`,
 * mesmo o modelo tendo a coluna. O tipo do web declara o campo, mas ele nunca
 * chega — então esta tela ordena por `id` (o backend já devolve desc) e não
 * mostra "há quanto tempo".
 */
export interface NotificationItem {
  id: number;
  channel: string;
  title: string;
  body: string;
  /** `delivered` depois do ack; qualquer outro valor conta como pendente. */
  status: string;
  related_signature: string | null;
  metadata: Record<string, unknown>;
}

interface NotificationsResponse {
  success: boolean;
  notifications: NotificationItem[];
}

export interface AckResponse {
  success: boolean;
  notification_id: number;
  status: string;
}

/**
 * `GET /v1/notifications/me` — **exige sessão**: a rota resolve o usuário pelo
 * `Bearer` e responde 401 sem ele.
 */
export async function listNotifications(): Promise<NotificationItem[]> {
  const response = await apiFetch<NotificationsResponse>('/v1/notifications/me');

  // O corpo traz um `success` além do status HTTP. Hoje o backend sempre manda
  // `true`, mas tratar `false` como lista vazia esconderia uma falha atrás de
  // um estado vazio legítimo — melhor errar alto, como o web faz.
  if (!response.success) {
    throw new ApiError('The backend could not read your notifications', null, false);
  }

  return response.notifications ?? [];
}

/** `POST /v1/notifications/{id}/ack` — marca como `delivered`. */
export function ackNotification(id: number): Promise<AckResponse> {
  return apiFetch<AckResponse>(`/v1/notifications/${id}/ack`, { method: 'POST' });
}

/**
 * Tesouraria por chain, com o Arc como hub — `frontend/src/hooks/useTreasury.ts`.
 *
 *   GET /v1/arc/wallet/balance            (`server/routes/arc_routes.py:99`)
 *   GET /v1/cctp/treasury/{chain}/balance (`server/routes/cctp_routes.py:44`)
 */
export type TreasuryChain = 'arc' | 'solana' | 'stellar';

/** `disabled` não é falha: é a flag da chain desligada no backend. */
export type TreasuryStatus = 'ok' | 'disabled' | 'error';

export interface TreasuryBalance {
  chain: TreasuryChain;
  status: TreasuryStatus;
  /** Stellar não expõe saldo no client, então vem `null` mesmo com status ok. */
  usdc: number | null;
  address?: string;
  sandbox?: boolean;
}

interface BalancePayload {
  usdc_balance?: number;
  sandbox?: boolean;
  address?: string;
}

const TREASURY_CHAINS: TreasuryChain[] = ['arc', 'solana', 'stellar'];

async function fetchChainBalance(chain: TreasuryChain): Promise<TreasuryBalance> {
  const path = chain === 'arc' ? '/v1/arc/wallet/balance' : `/v1/cctp/treasury/${chain}/balance`;

  try {
    const payload = await apiFetch<BalancePayload>(path);
    return {
      chain,
      status: 'ok',
      usdc: payload.usdc_balance ?? null,
      address: payload.address,
      sandbox: payload.sandbox,
    };
  } catch (err) {
    // 503 é a chain desligada por flag (`SOLANA_CCTP_ENABLED` etc.), não uma
    // falha — vira badge na tela em vez de derrubar o cartão inteiro.
    const disabled = err instanceof ApiError && err.status === 503;
    return { chain, status: disabled ? 'disabled' : 'error', usdc: null };
  }
}

/**
 * As três chains em paralelo. Cada uma resolve o próprio status, então uma
 * chain fora do ar não apaga o saldo das outras.
 */
export function getTreasury(): Promise<TreasuryBalance[]> {
  return Promise.all(TREASURY_CHAINS.map(fetchChainBalance));
}

/** `GET /campaigns/me` — `campaigns_routes.py::UserCampaignParticipation` */
export interface UserCampaignParticipation {
  id: number;
  name: string;
  description: string;
  reward_token: string;
  reward_per_participant: number;
  campaign_type: string;
  /** `tasks_verified` é o estado que libera o resgate. */
  participation_status: string;
  tasks_verified_at: string | null;
  tasks_claimed: boolean;
  claim_receipt_id: string | null;
}

interface UserCampaignsResponse {
  success: boolean;
  campaigns: UserCampaignParticipation[];
}

/** **Exige sessão**: a rota resolve o participante pelo `Bearer`. */
export async function listMyCampaigns(): Promise<UserCampaignParticipation[]> {
  const response = await apiFetch<UserCampaignsResponse>('/campaigns/me');

  if (!response.success) {
    throw new ApiError('The backend could not read your campaigns', null, false);
  }

  return response.campaigns ?? [];
}
