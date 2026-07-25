"use client";

import React, { useEffect, useState } from 'react';
import Navbar from '../../components/navbar/Navbar';
import TokenomicsCard from '../../components/dashboard/TokenomicsCard';
import TreasuryCard from '../../components/dashboard/TreasuryCard';
import UserStatsCard from '../../components/dashboard/UserStatsCard';
import ActivityFeed from '../../components/dashboard/ActivityFeed';
import { TypeUserData } from "@/interfaces";
import { ThemeProviderWrapper } from '@/providers/ThemeProvider';
import { useUserCampaigns } from '@/hooks/useUserCampaigns';
import { useLanguage } from '@/contexts/LanguageContext';
import UserData from '@/components/UserData';
import {
  IconTarget, IconCheck, IconAward, IconLock, IconUsers, IconGift,
  IconTrendingUp, IconActivity, IconCpu, IconZap, IconWifi, IconShield,
  type IconProps,
} from '@/components/icons';

// ── Campaign Summary Bar ───────────────────────────────────────────────────
function CampaignSummaryBar() {
  const { campaigns, loading } = useUserCampaigns();
  const { t } = useLanguage();

  const joined   = campaigns.length;
  const verified = campaigns.filter(c => c.participation_status === 'tasks_verified').length;
  const claimed  = campaigns.filter(c => c.tasks_claimed).length;

  const stats = [
    { label: t('dashboard.stat_campaigns'), value: joined,   Icon: IconTarget, accent: "text-[var(--accent)]", bg: "bg-white", border: "border-[var(--border)]" },
    { label: t('dashboard.stat_verified'),  value: verified, Icon: IconCheck,  accent: "text-[var(--success)]", bg: "bg-white", border: "border-[var(--border)]" },
    { label: t('dashboard.stat_rewarded'),  value: claimed,  Icon: IconAward,  accent: "text-[var(--accent)]", bg: "bg-white", border: "border-[var(--border)]" },
  ];

  if (loading) {
    return (
      <div className="grid grid-cols-3 gap-3 mb-6 animate-pulse">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-20 bg-white/40 rounded-2xl border border-[var(--border)]" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-3 gap-3 mb-6">
      {stats.map(({ label, value, Icon, accent, bg, border }) => (
        <div
          key={label}
          className={`rounded-2xl border ${border} ${bg} p-4 text-center hover:shadow-sm transition-shadow duration-200`}
        >
          <div className={`flex justify-center mb-2 ${accent}`}>
            <Icon className="w-4 h-4" />
          </div>
          <div className="text-2xl font-black text-gray-800 leading-none">{value}</div>
          <div className="text-sm text-gray-600 mt-1 font-semibold">{label}</div>
        </div>
      ))}
    </div>
  );
}

// ── Global Economy Stat ────────────────────────────────────────────────────
function EconomyStat({ Icon, value, label, accent }: {
  Icon: (p: IconProps) => React.ReactNode;
  value: string;
  label: string;
  accent: string;
}) {
  return (
    <div className="flex items-center gap-3 bg-white rounded-2xl border border-[var(--border)] p-4 hover:shadow-sm transition-shadow duration-200">
      <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${accent} bg-white border border-current/10 shadow-sm`}>
        <Icon className="w-5 h-5" />
      </div>
      <div className="min-w-0">
        <div className="text-base font-bold text-gray-800 leading-tight">{value}</div>
        <div className="text-sm text-gray-600 font-semibold mt-0.5">{label}</div>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const { t } = useLanguage();
  const [userData, setUserData] = useState<TypeUserData | null>(null);

  useEffect(() => {
    // Navbar calls restoreSession() before this effect runs — read whatever is already set
    const existing = UserData.getUserData();
    if (existing?.user_info?.twitter_user_id) {
      setUserData(existing);
    }

    const handler = (e: Event) => {
      setUserData((e as CustomEvent<TypeUserData>).detail);
    };
    window.addEventListener('userDataLoaded', handler);
    return () => window.removeEventListener('userDataLoaded', handler);
  }, []);

  const twitterId = userData?.user_info?.twitter_user_id;

  return (
    <ThemeProviderWrapper>
      <div className="min-h-screen bg-[var(--main-bg)] transition-colors duration-500">
        <Navbar />

        <main className="container mx-auto px-4 py-10 max-w-2xl">

          {/* ── Header ─────────────────────────────────────────────────── */}
          <div className="text-center mb-8">
            <h1 className="text-3xl font-extrabold text-[var(--text-primary)] mb-2 leading-tight">
              {t('dashboard.title')}
            </h1>
            <p className="text-base text-gray-600 max-w-xs mx-auto leading-relaxed">
              {t('dashboard.subtitle')}
            </p>
          </div>

          {/* ── Campaign Stats ─────────────────────────────────────────── */}
          <CampaignSummaryBar />

          {/* ── Tokenomics + User Stats ────────────────────────────────── */}
          <div className="grid grid-cols-1 gap-4 mb-4">
            <TreasuryCard />
            <TokenomicsCard />
            <UserStatsCard isConnected={!!userData} twitterId={twitterId} />
          </div>

          {/* ── Global Economy ─────────────────────────────────────────── */}
          <div className="mb-4">
            <div className="flex items-center gap-2 mb-3 px-1">
              <span className="text-[var(--accent)]"><IconTrendingUp /></span>
              <h2 className="text-sm font-bold text-gray-600 uppercase tracking-widest">{t('dashboard.global_economy')}</h2>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <EconomyStat Icon={IconLock}      value="$1,240,500"  label={t('dashboard.tvl')}                  accent="text-[var(--success)]" />
              <EconomyStat Icon={IconUsers}     value="12,450"      label={t('dashboard.active_users')}         accent="text-[var(--text-secondary)]" />
              <EconomyStat Icon={IconGift}      value="45,200 USDC" label={t('dashboard.rewards_distributed')}  accent="text-[var(--success)]" />
              <EconomyStat Icon={IconTrendingUp} value="1,120"      label={t('dashboard.campaigns_created')}    accent="text-[var(--text-secondary)]" />
            </div>
          </div>

          {/* ── Activity + Architecture ────────────────────────────────── */}
          <div className="grid grid-cols-1 gap-4">
            {/* Activity Feed */}
            <div className="rounded-2xl border border-[var(--border)] bg-white shadow-sm overflow-hidden">
              <div className="flex items-center gap-2 px-5 py-4 border-b border-[var(--border)]">
                <span className="text-[var(--accent)]"><IconActivity /></span>
                <div>
                  <h2 className="text-sm font-bold text-gray-700">{t('dashboard.recent_activity')}</h2>
                  <p className="text-sm text-gray-600">{t('dashboard.recent_activity_sub')}</p>
                </div>
              </div>
              <div className="p-4">
                <ActivityFeed maxItems={5} />
              </div>
            </div>

            {/* Architecture */}
            <div className="rounded-2xl border border-[var(--border)] bg-white shadow-sm p-5">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-[var(--accent)]"><IconCpu /></span>
                <h2 className="text-sm font-bold text-gray-700">{t('dashboard.architecture')}</h2>
              </div>
              <p className="text-sm text-gray-600 leading-relaxed mb-4">
                {t('dashboard.architecture_desc')}
              </p>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { Icon: IconShield, label: "Wallet-first" },
                  { Icon: IconCpu,    label: "Claude Agent" },
                  { Icon: IconZap,    label: "x402" },
                  { Icon: IconWifi,   label: "Circle W3S" },
                ].map(({ Icon, label }) => (
                  <div key={label} className="flex items-center gap-2 px-3 py-2 rounded-xl bg-[var(--main-bg)] border border-[var(--border)]">
                    <span className="text-[var(--text-secondary)] shrink-0"><Icon /></span>
                    <span className="text-xs font-semibold text-gray-600">{label}</span>
                  </div>
                ))}
              </div>
              <p className="text-center text-xs text-gray-500 font-medium uppercase tracking-widest mt-4 pt-3 border-t border-[var(--border)]">
                {t('dashboard.footer')}
              </p>
            </div>
          </div>

        </main>
      </div>
    </ThemeProviderWrapper>
  );
}
