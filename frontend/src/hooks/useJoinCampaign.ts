import { useState } from 'react';
import api from '@/api/api';
import UserData from '@/components/UserData';
import { detectChainFromAddress } from '@/lib/chains';

// ─── Tipos alinhados com o backend ─────────────────────────────────────────────

interface JoinCampaignResponse {
  success: boolean;
  message?: string;
  /** Presente em erros de negócio (success=false) */
  error?: string;
  /** true quando o usuário já estava inscrito (HTTP 409 Conflict) */
  alreadyJoined?: boolean;
}

interface ClaimRewardResponse {
  success: boolean;
  message?: string;
  error?: string;
  transaction_id?: string;
  claim_receipt_id?: string;
  reward_amount?: number;
  reward_token?: string;
}

interface UseJoinCampaignReturn {
  joinCampaign: (campaignId: number) => Promise<JoinCampaignResponse>;
  claimReward: (campaignId: number) => Promise<ClaimRewardResponse>;
  loading: boolean;
  claimLoading: boolean;
  error: string | null;
  claimError: string | null;
}

// ─── Helper: extrai mensagem de erro da resposta Axios/FastAPI ─────────────────

type AxiosLikeError = {
  response?: {
    status?: number;
    data?: { detail?: string; error?: string; message?: string };
  };
  message?: string;
};

function extractErrorMessage(error: unknown, fallback: string): string {
  const e = error as AxiosLikeError;
  // FastAPI HTTPException retorna { detail: "..." }
  if (e?.response?.data?.detail) return e.response.data.detail;
  // Outros erros retornam { error: "..." } ou { message: "..." }
  if (e?.response?.data?.error) return e.response.data.error;
  if (e?.response?.data?.message) return e.response.data.message;
  if (e instanceof Error && e.message) return e.message;
  return fallback;
}

// ─── Hook ──────────────────────────────────────────────────────────────────────

export default function useJoinCampaign(): UseJoinCampaignReturn {
  const [loading, setLoading] = useState(false);
  const [claimLoading, setClaimLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [claimError, setClaimError] = useState<string | null>(null);

  const joinCampaign = async (campaignId: number): Promise<JoinCampaignResponse> => {
    setLoading(true);
    setError(null);

    try {
      if (!UserData.hasData()) {
        throw new Error('Você precisa estar autenticado para participar de campanhas');
      }

      const sessionId = UserData.getSessionId();
      if (!sessionId) {
        throw new Error('Sessão não encontrada. Faça login novamente.');
      }

      console.log(`🚀 Tentando participar da campanha ${campaignId}...`);

      // Wallet + chain detectada — o agente precisa saber o trilho de payout
      // de quem entra pela UI (ROADMAP F0.2 / ADR-006)
      const joinWallet = UserData.getDevnetWalletPublicKey?.();
      const response = await api.post(
        `/campaigns/join`,
        {
          campaign_identifier: campaignId.toString(),
          ...(joinWallet && {
            wallet_public_key: joinWallet,
            chain: detectChainFromAddress(joinWallet),
          }),
        },
        { headers: { Authorization: `Bearer ${sessionId}` } }
      );

      console.log('✅ Resposta do servidor:', response.data);

      return {
        success: true,
        message: response.data.message,
      };

    } catch (err: unknown) {
      const e = err as AxiosLikeError;
      const httpStatus = e?.response?.status;

      // 409 Conflict — usuário já está inscrito nesta campanha
      if (httpStatus === 409) {
        const msg = extractErrorMessage(err, 'Você já está inscrito nesta campanha.');
        console.info(`ℹ️ Join duplicado detectado (409): ${msg}`);
        setError(msg);
        return { success: false, error: msg, alreadyJoined: true };
      }

      // 404 — campanha não encontrada
      if (httpStatus === 404) {
        const msg = 'Campanha não encontrada. Ela pode ter sido encerrada.';
        setError(msg);
        return { success: false, error: msg };
      }

      // 403 — campanha cheia ou usuário não elegível
      if (httpStatus === 403) {
        const msg = extractErrorMessage(err, 'Você não é elegível para esta campanha.');
        setError(msg);
        return { success: false, error: msg };
      }

      const errorMessage = extractErrorMessage(err, 'Erro ao participar da campanha');
      console.error('❌ Erro ao participar da campanha:', err);
      setError(errorMessage);
      return { success: false, error: errorMessage };

    } finally {
      setLoading(false);
    }
  };

  const claimReward = async (campaignId: number): Promise<ClaimRewardResponse> => {
    setClaimLoading(true);
    setClaimError(null);

    try {
      if (!UserData.hasData()) {
        throw new Error('Você precisa estar autenticado para coletar recompensas');
      }

      const sessionId = UserData.getSessionId();
      if (!sessionId) {
        throw new Error('Sessão não encontrada. Faça login novamente.');
      }

      // Wallet público necessário para prova de claim
      const walletPublicKey = UserData.getDevnetWalletPublicKey?.();

      console.log(`🎁 Tentando coletar recompensa da campanha ${campaignId}...`);

      const response = await api.post(
        `/campaigns/claim`,
        {
          campaign_identifier: campaignId.toString(),
          ...(walletPublicKey && {
            wallet_public_key: walletPublicKey,
            chain: detectChainFromAddress(walletPublicKey),
          }),
        },
        { headers: { Authorization: `Bearer ${sessionId}` } }
      );

      console.log('✅ Resposta do servidor:', response.data);

      if (response.data.success) {
        return {
          success: true,
          message: response.data.message,
          transaction_id: response.data.transaction_id,
          claim_receipt_id: response.data.claim_receipt_id,
          reward_amount: response.data.reward_amount,
          reward_token: response.data.reward_token,
        };
      }

      throw new Error(response.data.error || 'Erro desconhecido ao coletar recompensa');

    } catch (err: unknown) {
      const errorMessage = extractErrorMessage(err, 'Erro ao coletar recompensa');
      console.error('❌ Erro ao coletar recompensa:', err);
      setClaimError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setClaimLoading(false);
    }
  };

  return {
    joinCampaign,
    claimReward,
    loading,
    claimLoading,
    error,
    claimError,
  };
}
