import { useState } from 'react';
import api from '@/api/api';
import UserData from '@/components/UserData';
import { VerifyTasksResponse } from '@/interfaces';

interface UseVerifyTasksReturn {
  verifyTasks: (campaignId: number) => Promise<VerifyTasksResponse>;
  loading: boolean;
  error: string | null;
}

export default function useVerifyTasks(): UseVerifyTasksReturn {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const verifyTasks = async (campaignId: number): Promise<VerifyTasksResponse> => {
    setLoading(true);
    setError(null);
    
    try {
      // Verificar se o usuário está autenticado
      if (!UserData.hasData()) {
        throw new Error('Você precisa estar autenticado para verificar tarefas');
      }

      const sessionId = UserData.getSessionId();
      if (!sessionId) {
        throw new Error('Sessão não encontrada. Faça login novamente.');
      }

      console.log(`🔍 Verificando tarefas da campanha ${campaignId}...`);

      const response = await api.post(`/campaigns/verify`, {
        campaign_identifier: campaignId.toString()
      }, {
        headers: {
          'Authorization': `Bearer ${sessionId}`,
          'Content-Type': 'application/json'
        }
      });

      console.log('✅ Resposta da verificação:', response.data);

      return {
        success: response.data.success,
        message: response.data.message
      };

    } catch (error: unknown) {
      console.error('❌ Erro ao verificar tarefas:', error);
      
      let errorMessage = 'Erro ao verificar tarefas';
      
      const apiError = error as { response?: { data?: { error?: string; message?: string } }; message?: string };
      if (apiError.response?.data?.error) {
        errorMessage = apiError.response.data.error;
      } else if (apiError.response?.data?.message) {
        errorMessage = apiError.response.data.message;
      } else if (apiError.message) {
        errorMessage = apiError.message;
      }
      
      setError(errorMessage);
      
      return {
        success: false,
        message: errorMessage
      };
    } finally {
      setLoading(false);
    }
  };

  return {
    verifyTasks,
    loading,
    error
  };
}
