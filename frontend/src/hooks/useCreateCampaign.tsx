import { useState } from 'react';
import api from '@/api/api';
import { CreateCampaignRequest, CreateCampaignResponse } from '@/interfaces';
import UserData from '@/components/UserData';

interface UseCreateCampaignReturn {
  createCampaign: (campaignData: CreateCampaignRequest) => Promise<CreateCampaignResponse>;
  isCreating: boolean;
  error: string | null;
  success: boolean;
  reset: () => void;
}

export default function useCreateCampaign(): UseCreateCampaignReturn {
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const createCampaign = async (campaignData: CreateCampaignRequest): Promise<CreateCampaignResponse> => {
    setIsCreating(true);
    setError(null);
    setSuccess(false);
    
    try {
      const sessionId = UserData.getOrCreateDevnetSession();
      if (!sessionId) {
        throw new Error('Nao foi possivel iniciar sessao Devnet para criar campanha.');
      }

      console.log('🚀 Criando campanha:', campaignData);

      const response = await api.post('/campaigns/create', campaignData, {
        headers: {
          'Authorization': `Bearer ${sessionId}`,
          'Content-Type': 'application/json'
        }
      });

      console.log('✅ Campanha criada com sucesso:', response.data);
      setSuccess(true);
      return response.data;

    } catch (err: unknown) {
      const apiError = err as { response?: { data?: { message?: string } }; message?: string };
      const errorMessage = apiError.response?.data?.message || apiError.message || 'Erro ao criar campanha';
      console.error('❌ Erro ao criar campanha:', errorMessage);
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsCreating(false);
    }
  };

  const reset = () => {
    setError(null);
    setSuccess(false);
  };

  return {
    createCampaign,
    isCreating,
    error,
    success,
    reset
  };
}
