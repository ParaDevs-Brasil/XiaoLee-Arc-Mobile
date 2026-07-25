import { useState, useEffect, useCallback } from 'react';
import api from "../api/api"
import { Campaign, CampaignsResponse, CampaignError } from "../interfaces";

export interface UseCampaignsReturn {
  campaigns: Campaign[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export const useCampaigns = (): UseCampaignsReturn => {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCampaigns = useCallback(async (): Promise<void> => {
    try {
      setLoading(true);
      setError(null);
      
      console.log("🚀 Buscando campanhas...");
      
      const response = await api.get<CampaignsResponse>("/campaigns");
      
      console.log("📋 Campanhas recebidas:", response.data);
      
      if (response.data.success) {
        setCampaigns(response.data.campaigns);
      } else {
        const errorResponse = response.data as CampaignError;
        setError(errorResponse.message || "Erro ao buscar campanhas");
      }
    } catch (err: unknown) {
      console.error("❌ Erro ao buscar campanhas:", err);
      
      // Verificar se é um erro de resposta da API
      const apiError = err as { response?: { data?: { message?: string } }; message?: string };
      if (apiError.response?.data?.message) {
        setError(apiError.response.data.message);
      } else if (apiError.message) {
        setError(apiError.message);
      } else {
        setError("Erro desconhecido ao buscar campanhas");
      }
      
      setCampaigns([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const refetch = useCallback(async (): Promise<void> => {
    await fetchCampaigns();
  }, [fetchCampaigns]);

  useEffect(() => {
    fetchCampaigns();
  }, [fetchCampaigns]);

  return {
    campaigns,
    loading,
    error,
    refetch
  };
};

export default useCampaigns;
