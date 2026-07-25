"use client";

import React from "react";
import { useNotifications, NotificationItem } from "@/hooks/useNotifications";
import { useUserCampaigns } from "@/hooks/useUserCampaigns";
import { useLanguage } from "@/contexts/LanguageContext";

// ── SVG icons ──────────────────────────────────────────────────────────────
const IconTrophy = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
    <polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-1a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v1a2 2 0 0 1-2 2h-2"/><rect x="6" y="18" width="12" height="4"/>
  </svg>
);
const IconRefresh = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
    <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
  </svg>
);
const IconTarget = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
    <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>
  </svg>
);
const IconBell = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5">
    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>
  </svg>
);
const IconCheck = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" className="w-3 h-3">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);
const IconInbox = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6">
    <polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>
  </svg>
);
const IconAlert = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
    <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
  </svg>
);
const IconReceipt = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" className="w-3 h-3">
    <path d="M14 2H6a2 2 0 0 0-2 2v16l3-2 2 2 2-2 2 2 2-2 3 2V4a2 2 0 0 0-2-2z"/>
  </svg>
);

// ── Unified activity item ──────────────────────────────────────────────────
interface ActivityItem {
  key: string;
  title: string;
  body: string;
  status: 'pending' | 'delivered';
  related_signature?: string | null;
  created_at?: string;
  isPending: boolean;
  notifId?: number;
}

function getEventMeta(title: string): {
  Icon: () => React.ReactNode;
  accent: string;
  label: string;
} {
  const t = title.toLowerCase();
  if (t.includes("claim") || t.includes("reward"))
    return { Icon: IconTrophy,  accent: "text-amber-500 bg-amber-50 border-amber-100",       label: "Reward" };
  if (t.includes("swap"))
    return { Icon: IconRefresh, accent: "text-blue-500 bg-blue-50 border-blue-100",           label: "Swap" };
  if (t.includes("campaign") || t.includes("campanha"))
    return { Icon: IconTarget,  accent: "text-[var(--accent)] bg-[var(--accent-soft)] border-[var(--border)]",  label: "Campaign" };
  return   { Icon: IconBell,    accent: "text-gray-400 bg-gray-50 border-gray-100",           label: "Info" };
}

function useTimeAgo() {
  const { t } = useLanguage();
  return (isoDate?: string): string => {
    if (!isoDate) return "";
    const diff = Date.now() - new Date(isoDate).getTime();
    const minutes = Math.floor(diff / 60_000);
    if (minutes < 1) return t('activity_feed.just_now');
    if (minutes < 60) return `${minutes} ${t('activity_feed.min_ago')}`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}${t('activity_feed.h_ago')}`;
    return `${Math.floor(hours / 24)}${t('activity_feed.d_ago')}`;
  };
}

interface ActivityFeedProps {
  maxItems?: number;
}

export default function ActivityFeed({ maxItems = 5 }: ActivityFeedProps) {
  const { t } = useLanguage();
  const timeAgo = useTimeAgo();
  const { notifications, loading: notifLoading, error, ackNotification, isAckLoading, refetch } = useNotifications();
  const { campaigns: userCampaigns, loading: campaignsLoading } = useUserCampaigns();

  const loading = notifLoading || campaignsLoading;

  // Build unified activity list
  const notifItems: ActivityItem[] = notifications.map((n: NotificationItem) => ({
    key: `notif-${n.id}`,
    title: n.title,
    body: n.body,
    status: n.status as 'pending' | 'delivered',
    related_signature: n.related_signature,
    created_at: n.created_at,
    isPending: n.status === 'pending',
    notifId: n.id,
  }));

  // Campaign claim items — deduplicate against notifications by receipt
  const notifReceipts = new Set(
    notifications.map((n: NotificationItem) => n.related_signature).filter(Boolean)
  );
  const claimItems: ActivityItem[] = (userCampaigns ?? [])
    .filter(c => c.tasks_claimed || c.participation_status === 'paid')
    .filter(c => !c.claim_receipt_id || !notifReceipts.has(c.claim_receipt_id))
    .map(c => ({
      key: `campaign-${c.id}`,
      title: `Claim: ${c.name}`,
      body: `+${c.reward_per_participant} ${c.reward_token}`,
      status: 'delivered' as const,
      related_signature: c.claim_receipt_id ?? null,
      created_at: c.tasks_verified_at ?? undefined,
      isPending: false,
    }));

  const allItems = [...notifItems, ...claimItems].slice(0, maxItems);

  // Loading skeleton
  if (loading) {
    return (
      <div className="flex flex-col gap-2.5 animate-pulse">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-14 rounded-xl bg-[var(--main-bg)] border border-[var(--border)]" />
        ))}
      </div>
    );
  }

  // Error state
  if (error && allItems.length === 0) {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-orange-100 bg-orange-50 px-4 py-3">
        <span className="text-orange-400 shrink-0"><IconAlert /></span>
        <div className="flex-1 min-w-0">
          <p className="text-xs text-orange-600">{error}</p>
        </div>
        <button
          onClick={refetch}
          className="text-xs text-orange-500 font-semibold underline hover:text-orange-700 transition-colors shrink-0"
        >
          {t('activity_feed.retry')}
        </button>
      </div>
    );
  }

  // Empty state
  if (allItems.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-center">
        <div className="text-[var(--text-placeholder)] mb-3"><IconInbox /></div>
        <p className="text-xs font-semibold text-gray-500">{t('activity_feed.empty_title')}</p>
        <p className="text-xs text-gray-400 mt-1 max-w-xs leading-relaxed">
          {t('activity_feed.empty_sub')}
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {allItems.map((item) => {
        const { Icon, accent, label } = getEventMeta(item.title);

        return (
          <div
            key={item.key}
            className={`
              relative rounded-xl border transition-colors duration-150
              hover:bg-[var(--main-bg)]
              ${item.isPending ? "border-[var(--border)] bg-white" : "border-emerald-100 bg-emerald-50/30"}
            `}
          >
            <div className="flex items-start gap-3 p-3">
              {/* Icon */}
              <div className={`w-8 h-8 rounded-xl border flex items-center justify-center shrink-0 ${accent}`}>
                <Icon />
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <span className={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-md border ${accent}`}>
                    {label}
                  </span>
                  <span className="text-[10px] text-gray-300 shrink-0">
                    {timeAgo(item.created_at)}
                  </span>
                </div>

                <p className="text-xs font-semibold text-gray-700 mt-1 truncate">{item.title}</p>
                <p className="text-xs text-gray-400 mt-0.5 line-clamp-1">{item.body}</p>

                {/* ACK button — only for real pending notifications */}
                {item.isPending && item.notifId !== undefined && (
                  <button
                    onClick={() => ackNotification(item.notifId!)}
                    disabled={isAckLoading(item.notifId!)}
                    className="mt-2 inline-flex items-center gap-1 text-[10px] px-2.5 py-1 rounded-lg font-semibold bg-emerald-500 text-white hover:bg-emerald-600 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-150"
                  >
                    <IconCheck />
                    {isAckLoading(item.notifId!) ? t('activity_feed.confirming') : t('activity_feed.confirm')}
                  </button>
                )}

                {/* Receipt hash */}
                {item.related_signature && (
                  <div className="mt-1.5 flex items-center gap-1.5">
                    <span className="text-gray-300"><IconReceipt /></span>
                    <p className="text-[10px] text-gray-400 font-mono truncate">{item.related_signature}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })}

      {(notifications.length + claimItems.length) > maxItems && (
        <p className="text-center text-xs text-gray-400 pt-1">
          {t('activity_feed.more_notifications', { count: (notifications.length + claimItems.length) - maxItems })}
        </p>
      )}
    </div>
  );
}
