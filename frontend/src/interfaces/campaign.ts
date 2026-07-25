// Campaign-related interfaces for Xiaolee project

export interface Campaign {
  id: number;
  name: string;
  description: string;
  campaign_type: string;
  completed_participants: number;
  created_at: string;
  creator_twitter_user_id: string;
  max_participants: number;
  profile_to_follow?: string | null;
  reward_per_participant: number;
  reward_pool: number;
  reward_token: string;
  status: string;
  tweet_id_to_engage?: string | null;
}

export interface CreateCampaignData {
  title: string;
  description: string;
  campaign_type: string;
  profile_to_follow?: string;
  tweet_id_to_engage?: string;
  reward_token: string;
  reward_per_participant: number;
  max_participants: number;
}

export interface UserCampaignParticipation {
  id: number;
  name: string;
  description: string;
  reward_token: string;
  reward_per_participant: number;
  campaign_type: string;
  /**
   * Estados de participação — alinhados com o backend:
   *   'enrolled'       — participante inscrito, tarefas pendentes
   *   'tasks_verified' — tarefas verificadas pelo backend, aguardando claim
   *   'paid'           — recompensa claimed e paga (estado final)
   *
   * Nota: o estado 'reward_claimed' foi removido — era legado apenas no frontend.
   * O equivalente canônico no backend e no banco de dados é 'paid'.
   */
  participation_status: 'enrolled' | 'tasks_verified' | 'paid';
  tasks_verified_at: string | null;
  tasks_claimed: boolean;
  claim_receipt_id?: string | null;
}

export interface CampaignsResponse {
  success: boolean;
  campaigns: Campaign[];
  message?: string;
}

export interface CampaignError {
  success: false;
  message: string;
  error?: string;
}

export interface CreateCampaignRequest {
  title: string;
  description: string;
  campaign_type: string;
  profile_to_follow?: string;
  tweet_id_to_engage?: string;
  reward_token: string;
  reward_per_participant: number;
  max_participants: number;
}

export interface UserCampaignsResponse {
  success: boolean;
  campaigns: UserCampaignParticipation[];
  message?: string;
}

export interface CreateCampaignResponse {
  success: boolean;
  message: string;
}

// Campaign action interfaces
export interface JoinCampaignResponse {
  success: boolean;
  message?: string;
  error?: string;
}

export interface ClaimRewardResponse {
  success: boolean;
  message?: string;
  error?: string;
  transaction_id?: string;
  claim_receipt_id?: string;
  reward_amount?: number;
  reward_token?: string;
  wallet_public_key?: string;
  proof_submitted?: boolean;
}

// Response interfaces
export interface VerifyTasksResponse {
  success: boolean;
  message: string;
}

// Hook interface
export interface UseCampaignsReturn {
  // Data
  campaigns: Campaign[];
  userCampaigns: UserCampaignParticipation[];
  
  // Loading states
  loading: boolean;
  userCampaignsLoading: boolean;
  joinLoading: boolean;
  verifyLoading: boolean;
  claimLoading: boolean;
  createLoading: boolean;
  
  // Error states
  error: string | null;
  userCampaignsError: string | null;
  
  // Actions
  fetchCampaigns: () => Promise<void>;
  fetchUserCampaigns: () => Promise<void>;
  joinCampaign: (campaignId: number) => Promise<JoinCampaignResponse>;
  verifyTasks: (campaignId: number) => Promise<VerifyTasksResponse>;
  claimReward: (campaignId: number) => Promise<ClaimRewardResponse>;
  createCampaign: (data: CreateCampaignData) => Promise<CreateCampaignResponse>;
}
