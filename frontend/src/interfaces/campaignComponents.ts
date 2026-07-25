import type { ReactNode } from 'react';
import { Campaign, UserCampaignParticipation } from './campaign';

// Props para botões de ação
export interface ActionButtonProps {
  onClick: () => void;
  disabled: boolean;
  loading: boolean;
  loadingText: string;
  children: ReactNode;
  variant: 'primary' | 'secondary' | 'success';
  isLocked?: boolean;
}

// Props para card de campanha pública
export interface CampaignCardProps {
  campaign: Campaign;
  userCampaigns?: UserCampaignParticipation[];
  onJoin: (campaignId: number) => void;
  onVerify: (campaignId: number) => void;
  onClaim: (campaignId: number) => void;
  isJoining: (campaignId: number) => boolean;
  isVerifying: (campaignId: number) => boolean;
  isClaiming: (campaignId: number) => boolean;
  isCreator?: boolean;
}

// Props para card de campanha do usuário
export interface UserCampaignCardProps {
  campaign: UserCampaignParticipation;
  onVerify: (campaignId: number) => void;
  onClaim: (campaignId: number) => void;
  isVerifying: (campaignId: number) => boolean;
  isClaiming: (campaignId: number) => boolean;
}

// Props para formulário de criação
export interface CreateCampaignFormProps {
  onSuccess: () => void;
  onCancel: () => void;
}
