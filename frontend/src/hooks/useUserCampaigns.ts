import { useState, useEffect, useCallback } from 'react';
import api from '@/api/api';
import UserData from '@/components/UserData';
import { UserCampaignsResponse, UserCampaignParticipation } from '@/interfaces';

interface UseUserCampaignsReturn {
  campaigns: UserCampaignParticipation[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export const useUserCampaigns = (): UseUserCampaignsReturn => {
  const [campaigns, setCampaigns] = useState<UserCampaignParticipation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUserCampaigns = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const sessionId = UserData.getOrCreateDevnetSession();
      if (!sessionId) {
        throw new Error('Nao foi possivel iniciar sessao Devnet');
      }

      console.log('🔍 Buscando campanhas do usuário (Devnet session):', sessionId);

      const response = await api.get<UserCampaignsResponse>('/campaigns/me', {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${sessionId}`
        }
      });

      console.log('📬 Campanhas do usuário recebidas:', response.data);

      if (response.data.success) {
        setCampaigns(response.data.campaigns);
      } else {
        setError('Falha ao buscar campanhas do usuário');
        setCampaigns([]);
      }
    } catch (err) {
      console.error('❌ Erro ao buscar campanhas do usuário:', err);
      setError(err instanceof Error ? err.message : 'Erro desconhecido');
      setCampaigns([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUserCampaigns();
  }, [fetchUserCampaigns]);

  return {
    campaigns,
    loading,
    error,
    refetch: fetchUserCampaigns
  };
};

export default useUserCampaigns;
