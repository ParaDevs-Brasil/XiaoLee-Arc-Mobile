import React from 'react';
import UserData from '@/components/UserData';
import ActionButton from '@/components/ActionButton';
import AgentStatus from './AgentStatus';
import { CampaignCardProps } from '@/interfaces/campaignComponents';
import { useLanguage } from '@/contexts/LanguageContext';
import { IconCheck, IconList, IconAlert } from '@/components/icons';

export const CampaignCard: React.FC<CampaignCardProps> = ({
  campaign, userCampaigns, onJoin, onVerify, onClaim, isJoining, isVerifying, isClaiming, isCreator = false
}) => {
  const { t } = useLanguage();
  const hasCampaignIdentity = UserData.hasCampaignIdentity();
  // Prefer reactive prop (updated after actions) over static UserData cache
  const userCampaignParticipation = hasCampaignIdentity
    ? (userCampaigns ?? UserData.getUserCampaigns()).find(uc => uc.id === campaign.id)
    : null;

  const isEnrolled      = userCampaignParticipation?.participation_status === 'enrolled';
  const isTasksVerified = userCampaignParticipation?.participation_status === 'tasks_verified';
  const isPaid          = userCampaignParticipation?.participation_status === 'paid';
  const isTasksClaimed  = userCampaignParticipation?.tasks_claimed === true;

  // Progress bar
  const pct = campaign.max_participants > 0
    ? Math.min(100, Math.round((campaign.completed_participants / campaign.max_participants) * 100))
    : 0;
  const barColor = pct >= 90 ? 'bg-rose-400' : pct >= 60 ? 'bg-amber-400' : 'bg-emerald-400';
  const spotsLeft = campaign.max_participants - (campaign.completed_participants || 0);

  return (
    <div className="rounded-2xl border border-[var(--border)] bg-white shadow-sm hover:shadow-md transition-shadow duration-200">

      {/* Card Header */}
      <div className="px-5 py-4 border-b border-[var(--border)]">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="text-base font-bold text-gray-900 leading-tight mb-1.5">{campaign.name}</h3>
            <span className="text-xs font-bold uppercase tracking-widest text-[var(--accent)] bg-[var(--accent-soft)] border border-[var(--border)] px-2.5 py-0.5 rounded-full">
              {campaign.campaign_type}
            </span>
          </div>
          {(isPaid || isTasksClaimed) && (
            <span className="shrink-0 inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide px-3 py-1.5 rounded-full bg-emerald-100 text-emerald-700 border border-emerald-200">
              <IconCheck className="w-3.5 h-3.5" sw={2} /> {t('campaign_card.claimed_badge')}
            </span>
          )}
        </div>
      </div>

      {/* Description */}
      <div className="px-5 py-3">
        <p className="text-sm text-gray-600 leading-relaxed line-clamp-3">{campaign.description}</p>
      </div>

      {/* Stats + Progress */}
      <div className="px-5 pb-3">
        <div className="rounded-xl bg-gray-50/80 border border-gray-100 p-3">
          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm mb-3">
            <div className="flex justify-between">
              <span className="text-gray-500 font-medium">{t('campaign_card.max')}</span>
              <span className="font-bold text-gray-800">{campaign.max_participants}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500 font-medium">{t('campaign_card.pool')}</span>
              <span className="font-bold text-gray-800">{campaign.reward_pool} {campaign.reward_token}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500 font-medium">{t('campaign_card.enrolled')}</span>
              <span className="font-bold text-gray-800">{campaign.completed_participants || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500 font-medium">{t('campaign_card.spots')}</span>
              <span className={`font-bold ${spotsLeft === 0 ? 'text-rose-500' : 'text-gray-800'}`}>
                {spotsLeft === 0 ? t('campaign_card.sold_out') : spotsLeft}
              </span>
            </div>
          </div>
          {/* Progress bar */}
          <div>
            <div className="flex justify-between text-xs text-gray-500 font-medium mb-1">
              <span>{t('campaign_card.spots_filled')}</span>
              <span className="font-bold">{pct}%</span>
            </div>
            <div className="w-full h-1.5 bg-gray-200 rounded-full overflow-hidden">
              <div className={`h-full ${barColor} rounded-full transition-all duration-700`} style={{ width: `${pct}%` }} />
            </div>
          </div>
        </div>
      </div>

      {/* Reward */}
      <div className="px-5 pb-3">
        <div className="flex items-center justify-between rounded-xl border border-[var(--border)] bg-[var(--accent-soft)] px-4 py-2.5">
          <span className="text-sm text-gray-600 font-semibold">{t('campaign_card.reward_per_participant')}</span>
          <div className="flex items-center gap-2">
            <span className="text-xl font-black text-[var(--accent)]">{campaign.reward_per_participant}</span>
            <span className="text-sm font-bold text-[var(--accent)] bg-[var(--accent-soft)] px-2.5 py-0.5 rounded-full">{campaign.reward_token}</span>
          </div>
        </div>
      </div>

      {/* Tasks required */}
      {(campaign.profile_to_follow || campaign.tweet_id_to_engage) && (
        <div className="px-5 pb-3">
          <div className="rounded-xl border border-[var(--border)] bg-[var(--main-bg)] p-3">
            <div className="flex items-center gap-1.5 mb-2">
              <span className="text-[var(--text-secondary)]"><IconList className="w-3.5 h-3.5" /></span>
              <span className="text-sm font-bold text-[var(--text-secondary)] uppercase tracking-wider">{t('campaign_card.required_tasks')}</span>
            </div>
            <div className="space-y-1 text-sm text-[var(--text-secondary)]">
              {campaign.profile_to_follow && (
                <div>{t('campaign_card.follow')} <a className="underline font-medium" target="_blank" rel="noreferrer" href={`https://x.com/${campaign.profile_to_follow.replace(/^@/, '')}`}>{campaign.profile_to_follow}</a></div>
              )}
              {campaign.tweet_id_to_engage && (
                <div className="break-all">{t('campaign_card.engage')} <a className="underline font-medium" target="_blank" rel="noreferrer" href={campaign.tweet_id_to_engage}>{campaign.tweet_id_to_engage}</a></div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* No identity warning */}
      {!hasCampaignIdentity && (
        <div className="px-5 pb-3">
          <div className="flex items-center gap-2 rounded-xl border border-amber-100 bg-amber-50 px-3 py-2 text-amber-600">
            <IconAlert className="w-3.5 h-3.5" />
            <span className="text-sm font-semibold">{t('campaign_card.no_session')}</span>
          </div>
        </div>
      )}

      {/* Status info when already participating */}
      {!!userCampaignParticipation && (
        <div className="px-5 pb-3">
          <div className="flex items-center gap-2 rounded-xl border border-emerald-100 bg-emerald-50 px-3 py-2 text-emerald-600">
            <IconCheck className="w-3.5 h-3.5" sw={2} />
            <span className="text-sm font-semibold">
              {isPaid ? t('campaign_card.status_paid') :
               isTasksVerified ? t('campaign_card.status_verified') :
               t('campaign_card.status_enrolled')}
            </span>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="px-5 pb-5 space-y-2">
        {/* Join */}
        {!userCampaignParticipation && (
          <ActionButton
            onClick={() => onJoin(campaign.id)}
            disabled={isJoining(campaign.id)}
            loading={isJoining(campaign.id)}
            loadingText={t('campaign_card.btn_joining')}
            variant="primary"
            isLocked={!hasCampaignIdentity}
          >
            {!hasCampaignIdentity ? t('campaign_card.btn_waiting') : t('campaign_card.btn_join')}
          </ActionButton>
        )}

        {/* Verify */}
        <ActionButton
          onClick={() => onVerify(campaign.id)}
          disabled={isVerifying(campaign.id) || !isEnrolled || isTasksVerified || isPaid}
          loading={isVerifying(campaign.id)}
          loadingText={t('campaign_card.btn_verifying')}
          variant="secondary"
          isLocked={!hasCampaignIdentity}
        >
          {!hasCampaignIdentity ? t('campaign_card.btn_waiting') :
           isTasksVerified || isPaid ? t('campaign_card.btn_verified') :
           !isEnrolled ? t('campaign_card.btn_join_first') :
           t('campaign_card.btn_verify')}
        </ActionButton>

        {/* Claim */}
        <ActionButton
          onClick={() => onClaim(campaign.id)}
          disabled={isClaiming(campaign.id) || !isTasksVerified || isPaid || isTasksClaimed}
          loading={isClaiming(campaign.id)}
          loadingText={t('campaign_card.btn_claiming')}
          variant="success"
          isLocked={!hasCampaignIdentity}
        >
          {!hasCampaignIdentity ? t('campaign_card.btn_waiting') :
           isPaid || isTasksClaimed ? t('campaign_card.btn_claimed') :
           !isTasksVerified ? t('campaign_card.btn_verify_first') :
           t('campaign_card.btn_claim')}
        </ActionButton>
      </div>

      {/* Agent panel — only visible to the campaign creator */}
      {isCreator && (
        <div className="px-5 pb-3">
          <AgentStatus
            campaignId={campaign.id}
            campaignBudget={campaign.reward_pool}
            rewardPerCreator={campaign.reward_per_participant}
            isCreator={isCreator}
          />
        </div>
      )}

      {/* Footer meta */}
      <div className="px-5 pb-4 pt-0">
        <div className="flex justify-between items-center text-xs text-gray-500 font-medium border-t border-[var(--border)] pt-3">
          <span>@{campaign.creator_twitter_user_id}</span>
          <span>{new Date(campaign.created_at).toLocaleDateString()}</span>
        </div>
      </div>

    </div>
  );
};

export default CampaignCard;
