"use client";

import React from 'react';
import Link from 'next/link';
import { toast } from 'react-toastify';
import Navbar from '../../components/navbar/Navbar';
import useNotifications from '@/hooks/useNotifications';
import { ThemeProviderWrapper } from '@/providers/ThemeProvider';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import UserData from '@/components/UserData';
import { useLanguage } from '@/contexts/LanguageContext';

export default function NotificationsPage() {
  const { t } = useLanguage();
  const { notifications, loading, error, refetch, ackNotification, isAckLoading } = useNotifications();
  // Sessão/wallet vêm do localStorage — ler só após o mount evita hydration mismatch
  // (SSR renderiza vazio e o cliente renderiza o valor real).
  const [sessionId, setSessionId] = React.useState('');
  const [walletPublicKey, setWalletPublicKey] = React.useState('');
  React.useEffect(() => {
    setSessionId(UserData.getSessionId());
    setWalletPublicKey(UserData.getDevnetWalletPublicKey());
  }, []);

  const deliveredCount = notifications.filter((n) => n.status === 'delivered').length;
  const pendingCount = notifications.length - deliveredCount;

  const truncate = (str: string, maxLen = 16) =>
    str ? `${str.slice(0, 6)}...${str.slice(-6)}` : '—';

  return (
    <ThemeProviderWrapper>
      <div className="min-h-screen bg-[var(--main-bg)] transition-colors duration-500">
        <Navbar />

        <main className="container mx-auto px-4 py-10 max-w-2xl">

          {/* ── Header ── */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-[var(--accent)] shadow-lg mb-4">
              <span className="text-2xl">🔔</span>
            </div>
            <h1 className="text-3xl font-extrabold text-[var(--text-primary)] mb-2 leading-tight">
              {t('notifications.title')}
            </h1>
            <p className="text-base text-gray-600 max-w-sm mx-auto leading-relaxed">
              {t('notifications.subtitle')}
            </p>
          </div>

          {/* ── Stats Row ── */}
          <div className="grid grid-cols-3 gap-3 mb-6">
            {[
              { label: t('notifications.total'),     value: notifications.length, color: 'text-[var(--text-primary)]', solid: true, bg: 'from-white to-white', border: 'border-[var(--border)]' },
              { label: t('notifications.delivered'), value: deliveredCount, color: 'text-[var(--success)]', solid: true, bg: 'from-white to-white', border: 'border-[var(--border)]' },
              { label: t('notifications.pending'),   value: pendingCount, color: 'text-amber-600', solid: true, bg: 'from-white to-white', border: 'border-[var(--border)]' },
            ].map(({ label, value, color, solid, bg, border }) => (
              <div
                key={label}
                className={`rounded-2xl bg-gradient-to-br ${bg} border ${border} p-4 text-center shadow-sm`}
              >
                <div className={`text-3xl font-black leading-none ${solid ? color : `bg-gradient-to-r ${color} bg-clip-text text-transparent`}`}>
                  {value}
                </div>
                <div className="text-sm text-gray-600 mt-1 font-semibold">{label}</div>
              </div>
            ))}
          </div>

          {/* ── Session Context ── */}
          <div className="rounded-2xl border border-[var(--border)] bg-white p-4 mb-6 shadow-sm">
            <div className="text-xs font-bold uppercase tracking-widest text-[var(--accent)] mb-3">
              {t('notifications.devnet_context')}
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm text-gray-600 font-semibold shrink-0">{t('notifications.session')}</span>
                <span className="text-xs font-mono text-gray-700 bg-[var(--main-bg)] border border-[var(--border)] rounded-lg px-2 py-1 truncate max-w-[200px]" title={sessionId || ''}>
                  {sessionId ? truncate(sessionId, 12) : <span className="text-gray-400 italic">{t('notifications.not_initialized')}</span>}
                </span>
              </div>
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm text-gray-600 font-semibold shrink-0">{t('notifications.wallet')}</span>
                <span className="text-xs font-mono text-gray-700 bg-[var(--main-bg)] border border-[var(--border)] rounded-lg px-2 py-1 truncate max-w-[200px]" title={walletPublicKey || ''}>
                  {walletPublicKey ? truncate(walletPublicKey, 12) : <span className="text-gray-400 italic">{t('notifications.phantom_not_connected')}</span>}
                </span>
              </div>
            </div>
          </div>

          {/* ── List Section ── */}
          <div className="rounded-2xl border border-[var(--border)] bg-white shadow-lg overflow-hidden">
            {/* List Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--border)]">
              <div>
                <h2 className="text-lg font-bold text-gray-800">{t('notifications.receipts_title')}</h2>
                <p className="text-sm text-gray-600">{t('notifications.receipts_sub')}</p>
              </div>
              <button
                onClick={refetch}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white text-xs font-semibold shadow-md hover:scale-105 active:scale-95 transition-all duration-200"
              >
                <span>↺</span>
                Refresh
              </button>
            </div>

            {/* Loading */}
            {loading && (
              <div className="py-16 flex justify-center">
                <LoadingSpinner size="lg" text={t('notifications.loading')} />
              </div>
            )}

            {/* Error */}
            {!loading && error && (
              <div className="m-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
                {error}
              </div>
            )}

            {/* Empty State */}
            {!loading && !error && notifications.length === 0 && (
              <div className="px-6 py-16 flex flex-col items-center text-center">
                <div className="w-16 h-16 rounded-2xl bg-[var(--accent-soft)] flex items-center justify-center mb-5">
                  <span className="text-3xl">🔕</span>
                </div>
                <h3 className="text-lg font-bold text-gray-800 mb-1">{t('notifications.empty_title')}</h3>
                <p className="text-base text-gray-600 max-w-xs mb-6 leading-relaxed">
                  {t('notifications.empty_sub')}
                </p>
                <Link
                  href="/campaigns"
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white text-sm font-bold shadow-md hover:shadow-lg hover:scale-105 active:scale-95 transition-all duration-200"
                >
                  {t('notifications.explore_campaigns')} 🚀
                </Link>
              </div>
            )}

            {/* Notification List */}
            {!loading && notifications.length > 0 && (
              <div className="divide-y divide-[var(--border)]">
                {notifications.map((notification) => (
                  <div
                    key={notification.id}
                    className="px-5 py-4 hover:bg-[var(--main-bg)] transition-colors duration-150"
                  >
                    <div className="flex items-start gap-3">
                      {/* Status dot */}
                      <div className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${
                        notification.status === 'delivered'
                          ? 'bg-emerald-400'
                          : 'bg-amber-400 animate-pulse'
                      }`} />

                      <div className="flex-1 min-w-0">
                        {/* Title + badge */}
                        <div className="flex items-center gap-2 flex-wrap mb-1">
                          <h3 className="text-base font-bold text-gray-800 leading-tight">
                            {notification.title}
                          </h3>
                          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                            notification.status === 'delivered'
                              ? 'bg-emerald-100 text-emerald-600'
                              : 'bg-amber-100 text-amber-600'
                          }`}>
                            {notification.status}
                          </span>
                        </div>

                        {/* Body */}
                        <p className="text-sm text-gray-700 leading-relaxed mb-2">
                          {notification.body}
                        </p>

                        {/* Receipt signature */}
                        {notification.related_signature && (
                          <div className="rounded-lg bg-[var(--accent-soft)] border border-[var(--border)] px-3 py-2 mb-2">
                            <div className="text-xs text-[var(--accent)] font-bold uppercase tracking-wider mb-0.5">Receipt</div>
                            <div className="text-xs font-mono text-[var(--text-secondary)] break-all">{notification.related_signature}</div>
                          </div>
                        )}

                        {/* Metadata */}
                        {notification.metadata && Object.keys(notification.metadata).length > 0 && (
                          <div className="text-xs text-gray-400 bg-gray-50 rounded-lg px-3 py-1.5 font-mono break-all">
                            {JSON.stringify(notification.metadata)}
                          </div>
                        )}
                      </div>

                      {/* Action */}
                      <div className="shrink-0 mt-0.5">
                        {notification.status !== 'delivered' ? (
                          <button
                            onClick={async () => {
                              try {
                                await ackNotification(notification.id);
                                toast.success('✅ Notification acknowledged.');
                              } catch {
                                toast.error('❌ Failed to acknowledge notification.');
                              }
                            }}
                            disabled={isAckLoading(notification.id)}
                            className="inline-flex items-center px-3 py-1.5 rounded-xl bg-[var(--success)] text-white text-xs font-bold shadow-sm hover:shadow-md hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                          >
                            {isAckLoading(notification.id) ? '...' : t('notifications.ack')}
                          </button>
                        ) : (
                          <span className="inline-flex items-center px-3 py-1.5 rounded-xl bg-emerald-50 text-emerald-500 text-xs font-bold border border-emerald-100">
                            {t('notifications.done')}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* ── Footer note ── */}
          <p className="text-center text-xs text-gray-500 mt-6">
            {t('notifications.footer')}
          </p>

        </main>
      </div>
    </ThemeProviderWrapper>
  );
}