import React from 'react';
import { useXiaoLeeProgram } from '../../hooks/useXiaoLeeProgram';
import { useLanguage } from '@/contexts/LanguageContext';
import { IconWallet, IconBarChart } from '@/components/icons';

interface UserStatsCardProps {
  twitterId?: string;
  isConnected: boolean;
}

export default function UserStatsCard({ twitterId, isConnected }: UserStatsCardProps) {
  const { t } = useLanguage();
  const { userState, loading, errorCode } = useXiaoLeeProgram(twitterId || null);

  if (!isConnected) {
    return (
      <div className="rounded-2xl border border-[var(--border)] bg-white shadow-sm p-5">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-[var(--accent)]"><IconBarChart className="w-4 h-4" /></span>
          <h2 className="text-sm font-bold text-gray-700">{t('user_stats.title')}</h2>
        </div>
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <div className="w-12 h-12 rounded-2xl bg-[var(--accent-soft)] border border-[var(--border)] flex items-center justify-center mb-3 text-[var(--accent)]">
            <IconWallet className="w-5 h-5" />
          </div>
          <h3 className="text-sm font-bold text-gray-700 mb-1">{t('user_stats.disconnected_title')}</h3>
          <p className="text-sm text-gray-600 max-w-xs leading-relaxed">
            {t('user_stats.disconnected_sub')}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-[var(--border)] bg-white shadow-sm p-5">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-[var(--accent)]"><IconBarChart className="w-4 h-4" /></span>
        <h2 className="text-sm font-bold text-gray-700">{t('user_stats.title')}</h2>
      </div>

      {loading ? (
        <div className="flex justify-center items-center py-8">
          <div className="animate-spin rounded-full h-7 w-7 border-2 border-[var(--border)] border-t-[var(--accent)]" />
        </div>
      ) : errorCode ? (
        <div className="rounded-xl border border-red-100 bg-red-50 px-4 py-3">
          <p className="text-sm text-[var(--danger)] font-semibold text-center">
            {t(errorCode === 'not_found' ? 'user_stats.no_data' : 'user_stats.connection_error')}
          </p>
        </div>
      ) : userState ? (
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-xl bg-[var(--main-bg)] border border-[var(--border)] p-4 text-center">
            <p className="text-sm text-[var(--text-secondary)] font-semibold mb-1">{t('user_stats.total_swaps')}</p>
            <p className="text-2xl font-black text-[var(--text-primary)]">{userState.swapCount}</p>
          </div>
          <div className="rounded-xl bg-[var(--main-bg)] border border-[var(--border)] p-4 text-center">
            <p className="text-sm text-[var(--text-secondary)] font-semibold mb-1">{t('user_stats.volume_usdc')}</p>
            <p className="text-2xl font-black text-[var(--success)]">
              ${(userState.totalVolume / 1_000_000).toFixed(2)}
            </p>
          </div>
        </div>
      ) : null}
    </div>
  );
}
