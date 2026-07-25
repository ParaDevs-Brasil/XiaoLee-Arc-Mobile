import React from 'react';
import ActionButton from '@/components/ActionButton';
import { UserCampaignCardProps } from '@/interfaces/campaignComponents';
import { IconCheck, IconReceipt } from '@/components/icons';

const statusConfig: Record<string, { label: string; bg: string; text: string; border: string }> = {
  enrolled:       { label: 'Inscrito',   bg: 'bg-amber-50',   text: 'text-amber-600',   border: 'border-amber-100' },
  tasks_verified: { label: 'Verificado', bg: 'bg-emerald-50',  text: 'text-[var(--success)]',  border: 'border-emerald-100' },
  paid:           { label: 'Claimed',    bg: 'bg-emerald-50', text: 'text-emerald-600', border: 'border-emerald-100' },
};

export const UserCampaignCard: React.FC<UserCampaignCardProps> = ({
  campaign, onVerify, onClaim, isVerifying, isClaiming
}) => {
  const currentStatus = campaign.participation_status || 'enrolled';
  const cfg = statusConfig[currentStatus] ?? { label: currentStatus, bg: 'bg-gray-50', text: 'text-gray-500', border: 'border-gray-100' };

  return (
    <div className="rounded-xl border border-[var(--border)] bg-white hover:shadow-sm transition-shadow duration-150">

      {/* Header */}
      <div className="flex items-start justify-between gap-3 px-4 py-3 border-b border-[var(--border)]">
        <div className="min-w-0">
          <h3 className="text-sm font-bold text-gray-800 leading-tight truncate">{campaign.name}</h3>
          <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--accent)]">{campaign.campaign_type}</span>
        </div>
        <span className={`shrink-0 inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wide px-2.5 py-1 rounded-full border ${cfg.bg} ${cfg.text} ${cfg.border}`}>
          {currentStatus === 'paid' && <IconCheck className="w-3 h-3" sw={2} />}
          {cfg.label}
        </span>
      </div>

      {/* Body */}
      <div className="px-4 py-3">
        <p className="text-xs text-gray-500 leading-relaxed mb-3 line-clamp-2">{campaign.description}</p>

        {/* Reward */}
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs text-gray-400">Reward</span>
          <div className="flex items-center gap-1">
            <span className="text-sm font-black text-[var(--accent)]">{campaign.reward_per_participant}</span>
            <span className="text-xs font-bold text-[var(--accent)] bg-[var(--accent-soft)] px-1.5 py-0.5 rounded-full">{campaign.reward_token}</span>
          </div>
        </div>

        {/* Meta */}
        {campaign.tasks_verified_at && (
          <p className="text-xs text-gray-400 mb-2">
            Verificado em: <span className="font-medium">{new Date(campaign.tasks_verified_at).toLocaleDateString('pt-BR')}</span>
          </p>
        )}

        {campaign.claim_receipt_id && (
          <div className="flex items-center gap-1.5 mb-3">
            <span className="text-gray-300"><IconReceipt className="w-3 h-3" /></span>
            <p className="text-[10px] text-gray-400 font-mono truncate">{campaign.claim_receipt_id}</p>
          </div>
        )}

        {/* Actions */}
        <div className="space-y-2">
          {currentStatus === 'enrolled' && (
            <ActionButton
              onClick={() => onVerify(campaign.id)}
              disabled={isVerifying(campaign.id)}
              loading={isVerifying(campaign.id)}
              loadingText="Verificando..."
              variant="secondary"
            >
              Verificar Tasks
            </ActionButton>
          )}

          {currentStatus === 'tasks_verified' && (
            <ActionButton
              onClick={() => onClaim(campaign.id)}
              disabled={isClaiming(campaign.id)}
              loading={isClaiming(campaign.id)}
              loadingText="Reivindicando..."
              variant="success"
            >
              Reivindicar {campaign.reward_per_participant} {campaign.reward_token}
            </ActionButton>
          )}

          {currentStatus === 'paid' && (
            <div className="w-full py-2.5 rounded-xl text-xs font-bold text-center bg-emerald-50 text-emerald-600 border border-emerald-100">
              {campaign.reward_per_participant} {campaign.reward_token} {campaign.tasks_claimed ? 'reivindicado' : 'processado'}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default UserCampaignCard;
