import React from 'react';
import { UserCampaignParticipation } from '@/interfaces';
import { useLanguage } from '@/contexts/LanguageContext';

// ── SVG Icons ──────────────────────────────────────────────────────────────
const IconTarget = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
    <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>
  </svg>
);
const IconCheck = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-3 h-3">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);
const IconReceipt = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" className="w-3 h-3">
    <path d="M14 2H6a2 2 0 0 0-2 2v16l3-2 2 2 2-2 2 2 2-2 3 2V4a2 2 0 0 0-2-2z"/>
  </svg>
);

interface UserCampaignCardProps {
  campaign: UserCampaignParticipation;
  className?: string;
}

const statusConfig: Record<string, { label: string; bg: string; text: string; border: string }> = {
  enrolled:       { label: 'Inscrito',   bg: 'bg-amber-50',   text: 'text-amber-600',   border: 'border-amber-100' },
  tasks_verified: { label: 'Verificado', bg: 'bg-emerald-50',  text: 'text-[var(--success)]',  border: 'border-emerald-100' },
  paid:           { label: 'Claimed',    bg: 'bg-emerald-50', text: 'text-emerald-600', border: 'border-emerald-100' },
};

export const UserCampaignCard: React.FC<UserCampaignCardProps> = ({ campaign, className = '' }) => {
  const { t } = useLanguage();
  const currentStatus = campaign.participation_status;
  const statusLabels: Record<string, string> = {
    enrolled: t('user_campaigns.status_enrolled'),
    tasks_verified: t('user_campaigns.status_verified'),
    paid: t('user_campaigns.status_claimed'),
  };
  const cfg = statusConfig[currentStatus] ?? { label: currentStatus, bg: 'bg-gray-50', text: 'text-gray-500', border: 'border-gray-100' };
  const statusLabel = statusLabels[currentStatus] ?? cfg.label;

  return (
    <div className={`rounded-xl border border-[var(--border)] bg-white p-4 hover:shadow-sm transition-shadow duration-150 ${className}`}>
      <div className="flex items-start justify-between gap-3 mb-2">
        <h3 className="text-base font-bold text-gray-900 leading-tight flex-1 min-w-0">{campaign.name}</h3>
        <span className={`shrink-0 inline-flex items-center gap-1 text-xs font-bold uppercase tracking-wide px-2.5 py-1 rounded-full border ${cfg.bg} ${cfg.text} ${cfg.border}`}>
          {currentStatus === 'paid' && <IconCheck />}
          {statusLabel}
        </span>
      </div>

      <p className="text-sm text-gray-600 mb-3 leading-relaxed line-clamp-2">{campaign.description}</p>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600 font-medium">{t('user_campaigns.reward')}</span>
          <span className="text-base font-black text-[var(--accent)]">{campaign.reward_per_participant}</span>
          <span className="text-xs font-bold text-[var(--accent)] bg-[var(--accent-soft)] px-2 py-0.5 rounded-full">{campaign.reward_token}</span>
        </div>
        {campaign.tasks_verified_at && (
          <div className="flex items-center gap-1 text-xs text-gray-500 font-medium">
            <IconReceipt />
            {new Date(campaign.tasks_verified_at).toLocaleDateString('pt-BR')}
          </div>
        )}
      </div>
    </div>
  );
};

interface UserCampaignsListProps {
  campaigns: UserCampaignParticipation[];
  className?: string;
  title?: string;
}

export const UserCampaignsList: React.FC<UserCampaignsListProps> = ({
  campaigns, className = '', title
}) => {
  const { t } = useLanguage();
  const listTitle = title ?? t('user_campaigns.title');
  if (campaigns.length === 0) {
    return (
      <div className={`rounded-2xl border border-[var(--border)] bg-white p-8 text-center ${className}`}>
        <div className="w-10 h-10 rounded-2xl bg-[var(--accent-soft)] border border-[var(--border)] flex items-center justify-center mx-auto mb-3 text-[var(--accent)]">
          <IconTarget />
        </div>
        <h3 className="text-sm font-bold text-gray-600 mb-1">{t('user_campaigns.empty_title')}</h3>
        <p className="text-xs text-gray-400">{t('user_campaigns.empty_sub')}</p>
      </div>
    );
  }

  return (
    <div className={className}>
      <div className="flex items-center gap-2 mb-3 px-1">
        <span className="text-[var(--accent)]"><IconTarget /></span>
        <h2 className="text-sm font-bold text-gray-700 uppercase tracking-widest">{listTitle}</h2>
      </div>
      <div className="space-y-3">
        {campaigns.map((campaign) => (
          <UserCampaignCard key={campaign.id} campaign={campaign} />
        ))}
      </div>
    </div>
  );
};

export default UserCampaignsList;
