import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_CORE_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// SEC-003: endpoints como /user/{id} exigem Bearer da própria sessão. Lê o
// localStorage direto (não importa UserData — evitaria ciclo api→UserData→useUser→api)
// com a mesma prioridade de UserData.getSessionId(): auth real > sessão devnet.
function getSessionToken(): string {
  if (typeof window === "undefined") return "";
  try {
    const info = window.localStorage.getItem("xiaolee_user_info");
    if (info) {
      const parsed = JSON.parse(info) as { twitter_user_id?: string };
      if (parsed.twitter_user_id?.trim()) return parsed.twitter_user_id.trim();
    }
  } catch {
    // user_info corrompido — cai para a sessão devnet
  }
  return window.localStorage.getItem("xiaolee_devnet_session")?.trim() ?? "";
}

api.interceptors.request.use((config) => {
  if (!config.headers.Authorization) {
    const token = getSessionToken();
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response) {
      console.error('API Error:', error.response.status, error.response.data);
    } else if (error.request) {
      console.error('API Error: no response received', error.message, error.request);
    } else {
      console.error('API Error:', error.message);
    }
    return Promise.reject(error);
  }
);

export interface CreatorRegisterResult {
  ok: boolean;
  creator: string;
  circle_wallet_id: string;
  eligible: boolean;
  already_registered: boolean;
  registered_at: string;
  message: string;
}

export type CreatorChain = "arc" | "solana" | "stellar";

/**
 * Registra um creator com endereço nativo + chain (ROADMAP F0.1).
 * `circle_wallet_id` segue no payload por compatibilidade com o contrato
 * anterior; o backend novo lê `wallet_address` + `chain`.
 */
export interface CreatorRegisterProof {
  signed_message: string;
  signature: string;
  proof_encoding: "eip191" | "base64";
}

export async function registerCreator(
  twitterHandle: string,
  walletAddress: string,
  chain: CreatorChain,
  proof: CreatorRegisterProof,
): Promise<CreatorRegisterResult> {
  const res = await api.post<CreatorRegisterResult>("/v1/creator/register", {
    twitter_handle: twitterHandle,
    wallet_address: walletAddress,
    chain,
    circle_wallet_id: walletAddress,
    ...proof,
  });
  return res.data;
}

export default api;
