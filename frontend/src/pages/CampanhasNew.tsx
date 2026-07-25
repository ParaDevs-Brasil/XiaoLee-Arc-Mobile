import React, { useState, useEffect, useRef } from 'react';
import Link from "next/link";
import { toast } from 'react-toastify';
import useCampaigns from '@/hooks/useCampaigns';
import { useCampaignActions } from '@/hooks/useCampaignActions';
import useUserCampaigns from '@/hooks/useUserCampaigns';
import useNotifications from '@/hooks/useNotifications';
import { useModal } from '@/hooks/useModal';
import { Modal } from '@/components/ui/Modal';

import UserData from '@/components/UserData';
import { connectEvmWallet, getStoredEvmAddress, isEvmWalletInstalled } from '@/lib/evmWallet';
import { useLanguage } from '@/contexts/LanguageContext';
import { CampaignCard } from '@/components/campaigns/CampaignCard';
import CreateCampaignForm from '@/components/campaigns/CreateCampaignForm';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { UserCampaignsList } from '@/components/campaigns/UserCampaignsList';
import {
  IconPlus,
  IconRefresh,
  IconCheck,
  IconClock,
  IconAlert,
  IconTarget,
  IconBell,
  IconChevronLeft,
  IconChevronRight,
  IconChevronDown,
  IconClose,
  IconMegaphone,
  IconReceipt,
} from '@/components/icons';

export default function Campaigns() {
  const { campaigns, loading, error, refetch } = useCampaigns();
  const { campaigns: userCampaigns, refetch: refetchUserCampaigns } = useUserCampaigns();
  const { notifications, loading: notificationsLoading, error: notificationsError, refetch: refetchNotifications, ackNotification, isAckLoading } = useNotifications();
  const { joinCampaign, verifyTasks, claimReward, isJoinLoading, isVerifyLoading, isClaimLoading } = useCampaignActions();
  const { t } = useLanguage();
  const [isCampaignReady, setIsCampaignReady] = useState(UserData.hasCampaignIdentity());
  const [walletAddress, setWalletAddress] = useState<string>("");
  const [showCreateForm, setShowCreateForm] = useState(false);
  const { isOpen: isCreateModalOpen, animateIn: createModalAnimateIn, closeModal: closeCreateModal } = useModal(
    showCreateForm,
    () => setShowCreateForm(false)
  );
  const [refreshing, setRefreshing] = useState(false);
  // Aba ativa — organiza o conteúdo em views para cortar o scroll (sobretudo no mobile)
  const [tab, setTab] = useState<'explore' | 'mine' | 'rewards'>('explore');
  // Carrossel horizontal das campanhas ativas (um card por vez, com setas + swipe)
  const scrollerRef = useRef<HTMLDivElement>(null);
  const [carIdx, setCarIdx] = useState(0);
  // "Como funciona" recolhível no topo — acessível sem custar scroll
  const [howOpen, setHowOpen] = useState(false);
  const currentUserId = UserData.getSessionId();

  const scrollToCard = (i: number) => {
    const el = scrollerRef.current;
    if (!el) return;
    const clamped = Math.max(0, Math.min(i, el.children.length - 1));
    const child = el.children[clamped] as HTMLElement | undefined;
    if (child) el.scrollTo({ left: child.offsetLeft - el.offsetLeft, behavior: 'smooth' });
    setCarIdx(clamped);
  };

  const onScrollerScroll = () => {
    const el = scrollerRef.current;
    if (!el) return;
    // card ativo = aquele cujo início está mais próximo da borda esquerda do scroller
    let best = 0, bestDist = Infinity;
    for (let i = 0; i < el.children.length; i++) {
      const c = el.children[i] as HTMLElement;
      const dist = Math.abs(c.offsetLeft - el.offsetLeft - el.scrollLeft);
      if (dist < bestDist) { bestDist = dist; best = i; }
    }
    setCarIdx(best);
  };

  useEffect(() => {
    if (userCampaigns) UserData.updateCampaigns(userCampaigns);
  }, [userCampaigns]);

  useEffect(() => {
    const sessionId = UserData.getOrCreateDevnetSession();
    setIsCampaignReady(!!sessionId);
    // Only auto-sync a previously connected EVM wallet if no authenticated session exists
    const hasAuth = sessionId?.startsWith('tg_session_') || sessionId?.startsWith('google_session_');
    if (!hasAuth) {
      const maybeWallet = getStoredEvmAddress();
      if (maybeWallet) {
        setWalletAddress(maybeWallet);
        UserData.setDevnetWalletSession(maybeWallet);
      }
    }
    refetchUserCampaigns();
  }, [refetchUserCampaigns]);

  const handleConnectDevnetWallet = async () => {
    // If already authenticated via Telegram or Google, just confirm the session
    const currentSession = UserData.getSessionId();
    if (currentSession?.startsWith('tg_session_') || currentSession?.startsWith('google_session_')) {
      setIsCampaignReady(true);
      await refetchUserCampaigns();
      toast.success('Sessão autenticada sincronizada.');
      return;
    }
    // Otherwise try an injected EVM wallet (MetaMask etc.) for on-chain identity
    if (!isEvmWalletInstalled()) {
      toast.info('Sem carteira detectada. Continuando com sessão local.');
      const fallback = UserData.getOrCreateDevnetSession();
      setIsCampaignReady(!!fallback);
      return;
    }
    try {
      const address = await connectEvmWallet();
      UserData.setDevnetWalletSession(address);
      setWalletAddress(address);
      setIsCampaignReady(true);
      await refetchUserCampaigns();
      toast.success('Wallet conectada para campanhas.');
    } catch {
      toast.error('Não foi possível conectar a wallet.');
    }
  };

  useEffect(() => {
    const handler = () => { setIsCampaignReady(UserData.hasCampaignIdentity()); refetchUserCampaigns(); };
    window.addEventListener('userDataLoaded', handler);
    return () => window.removeEventListener('userDataLoaded', handler);
  }, [refetchUserCampaigns]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await refetch();
      await refetchUserCampaigns();
      await refetchNotifications();
      await UserData.fetchData();
    } finally {
      setRefreshing(false);
    }
  };

  const handleJoinCampaign = async (campaignId: number) => {
    if (!isCampaignReady) { toast.error('Sessão Testnet não inicializada. Atualize e tente novamente.'); return; }
    const result = await joinCampaign(campaignId);
    if (result.success) { toast.success(result.message); handleRefresh(); await refetchUserCampaigns(); await UserData.fetchData(); }
    else { toast.error(result.error); }
  };

  const handleVerifyTasks = async (campaignId: number) => {
    if (!isCampaignReady) { toast.error('Sessão Testnet não inicializada. Atualize e tente novamente.'); return; }
    const result = await verifyTasks(campaignId);
    if (result.success) { toast.success(result.message); await refetchUserCampaigns(); await UserData.fetchData(); }
    else { toast.warning(result.message); }
  };

  const handleClaimReward = async (campaignId: number) => {
    if (!isCampaignReady) { toast.error('Sessão Testnet não inicializada. Atualize e tente novamente.'); return; }
    const result = await claimReward(campaignId);
    if (result.success) {
      const receiptSuffix = result.claim_receipt_id ? ` Receipt: ${result.claim_receipt_id}` : '';
      toast.success(`${result.message}${receiptSuffix}`, { autoClose: 5000 });
      await refetchUserCampaigns();
      await refetchNotifications();
      await UserData.fetchData();
    } else { toast.error(result.error); }
  };

  const handleCreateSuccess = () => {
    closeCreateModal();
    toast.success('Campanha criada com sucesso!');
    handleRefresh();
    UserData.fetchData();
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="xl" text="Loading campaigns..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8">
        <div className="text-center bg-white border border-red-200 rounded-2xl p-8 max-w-sm w-full shadow-sm">
          <div className="w-12 h-12 rounded-2xl bg-red-50 border border-red-100 flex items-center justify-center mx-auto mb-4 text-red-400">
            <IconAlert className="w-3.5 h-3.5" />
          </div>
          <h2 className="text-base font-bold text-gray-700 mb-2">Erro ao carregar campanhas</h2>
          <p className="text-sm text-gray-400 mb-5">{error}</p>
          <button onClick={handleRefresh} className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white text-sm font-semibold shadow-sm hover:shadow-md hover:scale-105 active:scale-95 transition-all">
            <IconRefresh className="w-3.5 h-3.5" /> Tentar novamente
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen px-4 py-10">
      <div className="max-w-2xl mx-auto">

        {/* ── Header ──────────────────────────────────────────────────── */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-extrabold text-[var(--text-primary)] mb-2 leading-tight">
            {t('campaigns.title')}
          </h1>
          <p className="text-base text-gray-600 max-w-xs mx-auto leading-relaxed">
            {t('campaigns.subtitle')}
          </p>
        </div>

        {/* ── Session Status Banner ────────────────────────────────────── */}
        <div className={`flex items-center gap-3 rounded-2xl border px-4 py-3 mb-6 ${
          isCampaignReady
            ? 'bg-emerald-50 border-emerald-100'
            : 'bg-amber-50 border-amber-100'
        }`}>
          <div className={`w-7 h-7 rounded-xl flex items-center justify-center shrink-0 ${
            isCampaignReady ? 'bg-emerald-100 text-emerald-500' : 'bg-amber-100 text-amber-500'
          }`}>
            {isCampaignReady ? <IconCheck className="w-3.5 h-3.5" sw={2} /> : <IconClock className="w-3.5 h-3.5" />}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-bold text-gray-800">
              {isCampaignReady ? t('campaigns.session_active') : t('campaigns.guest_mode')}
            </p>
            <p className="text-sm text-gray-600 mt-0.5">
              {isCampaignReady
                ? t('campaigns.session_ready')
                : t('campaigns.session_connect')}
            </p>
          </div>
          {!isCampaignReady ? (
            <Link href="/" className="shrink-0 px-3 py-1.5 rounded-xl bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold transition-colors">
              Login
            </Link>
          ) : (
            <button onClick={handleConnectDevnetWallet} className="shrink-0 px-4 py-2 rounded-xl bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white text-sm font-bold transition-colors">
              Sync Wallet
            </button>
          )}
        </div>

        {/* ── Tab bar (segmented pills) — uma seção por vez, sem scroll infinito ── */}
        <div className="sticky top-2 z-10 mb-6 flex items-center gap-2 rounded-2xl border border-[var(--border)] bg-white/85 backdrop-blur px-1.5 py-1.5 shadow-sm">
          <div className="flex flex-1 items-center gap-1 overflow-x-auto no-scrollbar">
            {([
              { id: 'explore', label: t('campaigns.tab_explore'), count: campaigns.length },
              { id: 'mine', label: t('campaigns.tab_mine'), count: userCampaigns?.length ?? 0 },
              { id: 'rewards', label: t('campaigns.tab_rewards'), count: notifications.length },
            ] as const).map((tItem) => {
              const active = tab === tItem.id;
              return (
                <button
                  key={tItem.id}
                  onClick={() => setTab(tItem.id)}
                  aria-pressed={active}
                  className={`flex shrink-0 items-center gap-1.5 rounded-xl px-3.5 py-2 text-sm font-bold transition-all ${
                    active
                      ? 'bg-[var(--accent)] text-white shadow-sm'
                      : 'text-gray-500 hover:bg-[var(--accent-soft)] hover:text-[var(--accent)]'
                  }`}
                >
                  {tItem.label}
                  {tItem.count > 0 && (
                    <span className={`rounded-full px-1.5 py-0.5 text-[11px] font-extrabold leading-none ${
                      active ? 'bg-white/25 text-white' : 'bg-[var(--accent-soft)] text-[var(--accent)]'
                    }`}>
                      {tItem.count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
          <button
            onClick={() => setShowCreateForm(true)}
            title={t('campaigns.create_campaign')}
            className="flex shrink-0 items-center gap-1.5 rounded-xl bg-[var(--accent)] hover:bg-[var(--accent-hover)] px-3 py-2 text-sm font-bold text-white shadow-sm active:scale-95 transition-all"
          >
            <IconPlus className="w-4 h-4" /><span className="hidden sm:inline">{t('campaigns.create_campaign')}</span>
          </button>
        </div>

        {/* ── Como funciona (recolhível) ─────────────────────────────── */}
        <div className="mb-6 rounded-2xl border border-[var(--border)] bg-white shadow-sm overflow-hidden">
          <button
            onClick={() => setHowOpen((v) => !v)}
            aria-expanded={howOpen}
            className="flex w-full items-center gap-2 px-4 py-3 text-left hover:bg-[var(--accent-soft)]/50 transition-colors"
          >
            <span className="text-[var(--accent)]"><IconTarget className="w-4 h-4" /></span>
            <h3 className="flex-1 text-xs font-bold text-gray-500 uppercase tracking-widest">{t('campaigns.how_title')}</h3>
            <span className={`text-gray-400 transition-transform duration-300 ${howOpen ? 'rotate-180' : ''}`}><IconChevronDown className="w-4 h-4" sw={2.2} /></span>
          </button>
          <div className={`grid transition-all duration-300 ease-out ${howOpen ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'}`}>
            <div className="overflow-hidden">
              <ol className="space-y-2 px-4 pb-4">
                {[t('campaigns.how_1'), t('campaigns.how_2'), t('campaigns.how_3'), t('campaigns.how_4')].map((step, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-sm text-gray-600">
                    <span className="w-4 h-4 rounded-full bg-[var(--accent-soft)] border border-[var(--border)] text-[var(--accent)] font-bold flex items-center justify-center shrink-0 text-[10px]">
                      {i + 1}
                    </span>
                    {step}
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </div>

        {/* ── My Campaigns ────────────────────────────────────────────── */}
        {tab === 'mine' && (
          userCampaigns && userCampaigns.length > 0 ? (
            <div className="mb-6">
              <UserCampaignsList campaigns={userCampaigns} title="My Campaigns" />
            </div>
          ) : (
            <div className="rounded-2xl border border-[var(--border)] bg-white shadow-sm p-12 text-center mb-6">
              <div className="w-12 h-12 rounded-2xl bg-[var(--accent-soft)] border border-[var(--border)] flex items-center justify-center mx-auto mb-4 text-[var(--accent)]">
                <IconTarget className="w-4 h-4" />
              </div>
              <h2 className="text-sm font-bold text-gray-600 mb-1">{t('campaigns.mine_empty_title')}</h2>
              <p className="text-xs text-gray-400 mb-5 leading-relaxed">{t('campaigns.mine_empty_sub')}</p>
              <button onClick={() => setTab('explore')} className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white text-sm font-semibold shadow-sm active:scale-95 transition-all">
                {t('campaigns.tab_explore')}
              </button>
            </div>
          )
        )}

        {/* ── Recent Rewards (Notifications) ──────────────────────────── */}
        {tab === 'rewards' && (notifications.length > 0 || notificationsLoading || notificationsError) && (
          <div className="rounded-2xl border border-[var(--border)] bg-white shadow-sm mb-6 overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--border)]">
              <div className="flex items-center gap-2">
                <span className="text-[var(--accent)]"><IconBell className="w-4 h-4" /></span>
                <h2 className="text-sm font-bold text-gray-700">{t('campaigns.recent_rewards')}</h2>
              </div>
              <button onClick={refetchNotifications} className="text-xs font-semibold text-[var(--accent)] hover:text-[var(--accent-hover)] transition-colors">
                Atualizar
              </button>
            </div>

            <div className="p-4">
              {notificationsError && (
                <p className="text-xs text-red-500 mb-3">{notificationsError}</p>
              )}
              {notificationsLoading ? (
                <p className="text-xs text-gray-400 py-4 text-center">{t('campaigns.loading_notifications')}</p>
              ) : (
                <div className="space-y-2">
                  {notifications.slice(0, 3).map((notification) => (
                    <div key={notification.id} className={`rounded-xl border px-4 py-3 ${
                      notification.status === 'delivered'
                        ? 'border-emerald-100 bg-emerald-50/50'
                        : 'border-[var(--border)] bg-white'
                    }`}>
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${notification.status === 'delivered' ? 'bg-emerald-400' : 'bg-amber-400 animate-pulse'}`} />
                            <p className="text-sm font-bold text-gray-800 truncate">{notification.title}</p>
                          </div>
                          <p className="text-sm text-gray-600 line-clamp-1">{notification.body}</p>
                          {notification.related_signature && (
                            <div className="flex items-center gap-1 mt-1.5">
                              <span className="text-gray-300"><IconReceipt className="w-3 h-3" /></span>
                              <p className="text-[10px] text-gray-400 font-mono truncate">{notification.related_signature}</p>
                            </div>
                          )}
                        </div>
                        <div className="flex flex-col items-end gap-1.5 shrink-0">
                          <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                            notification.status === 'delivered'
                              ? 'bg-emerald-100 text-emerald-600'
                              : 'bg-amber-100 text-amber-600'
                          }`}>
                            {notification.status}
                          </span>
                          {notification.status !== 'delivered' && (
                            <button
                              onClick={async () => {
                                try { await ackNotification(notification.id); toast.success('Notificação confirmada.'); }
                                catch { toast.error('Erro ao confirmar notificação.'); }
                              }}
                              disabled={isAckLoading(notification.id)}
                              className="text-[10px] font-semibold text-white bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed px-2.5 py-1 rounded-lg transition-colors"
                            >
                              {isAckLoading(notification.id) ? '...' : 'Confirmar'}
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Rewards vazio ────────────────────────────────────────────── */}
        {tab === 'rewards' && notifications.length === 0 && !notificationsLoading && !notificationsError && (
          <div className="rounded-2xl border border-[var(--border)] bg-white shadow-sm p-12 text-center mb-6">
            <div className="w-12 h-12 rounded-2xl bg-[var(--accent-soft)] border border-[var(--border)] flex items-center justify-center mx-auto mb-4 text-[var(--accent)]">
              <IconBell className="w-4 h-4" />
            </div>
            <h2 className="text-sm font-bold text-gray-600 mb-1">{t('campaigns.rewards_empty_title')}</h2>
            <p className="text-xs text-gray-400 leading-relaxed">{t('campaigns.rewards_empty_sub')}</p>
          </div>
        )}

        {/* ── Campaign List ────────────────────────────────────────────── */}
        {tab === 'explore' && (campaigns.length === 0 ? (
          <div className="rounded-2xl border border-[var(--border)] bg-white shadow-sm p-12 text-center">
            <div className="w-12 h-12 rounded-2xl bg-[var(--accent-soft)] border border-[var(--border)] flex items-center justify-center mx-auto mb-4 text-[var(--accent)]">
              <IconMegaphone className="w-5 h-5" />
            </div>
            <h2 className="text-sm font-bold text-gray-600 mb-1">Nenhuma campanha ativa</h2>
            <p className="text-xs text-gray-400 mb-5 leading-relaxed">Novas campanhas em breve. Verifique novamente em alguns instantes.</p>
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white text-sm font-semibold shadow-sm hover:shadow-md hover:scale-105 active:scale-95 disabled:opacity-50 transition-all"
            >
              {refreshing ? <LoadingSpinner size="sm" /> : <IconRefresh className="w-3.5 h-3.5" />}
              {refreshing ? t('campaigns.refreshing') : t('campaigns.refresh')}
            </button>
          </div>
        ) : (
          <>
            {/* List header + navegação do carrossel */}
            <div className="flex items-center justify-between mb-4 px-1">
              <p className="text-sm font-bold text-gray-600 uppercase tracking-widest">
                <span className="text-[var(--accent)]">{carIdx + 1}</span>
                <span className="text-gray-400">/{campaigns.length}</span> ativa{campaigns.length !== 1 ? 's' : ''}
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleRefresh}
                  disabled={refreshing}
                  className="inline-flex items-center gap-1.5 text-xs text-gray-400 hover:text-[var(--accent)] font-semibold transition-colors disabled:opacity-50 mr-1"
                >
                  <IconRefresh className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">{refreshing ? t('campaigns.refreshing') : t('campaigns.refresh')}</span>
                </button>
                <button
                  onClick={() => scrollToCard(carIdx - 1)}
                  disabled={carIdx <= 0}
                  aria-label={t('campaigns.prev')}
                  className="grid h-8 w-8 place-items-center rounded-xl border border-[var(--border)] bg-white text-[var(--accent)] shadow-sm hover:bg-[var(--accent-soft)] disabled:opacity-40 disabled:cursor-not-allowed transition-all"
                >
                  <IconChevronLeft className="w-4 h-4" sw={2.2} />
                </button>
                <button
                  onClick={() => scrollToCard(carIdx + 1)}
                  disabled={carIdx >= campaigns.length - 1}
                  aria-label={t('campaigns.next')}
                  className="grid h-8 w-8 place-items-center rounded-xl border border-[var(--border)] bg-white text-[var(--accent)] shadow-sm hover:bg-[var(--accent-soft)] disabled:opacity-40 disabled:cursor-not-allowed transition-all"
                >
                  <IconChevronRight className="w-4 h-4" sw={2.2} />
                </button>
              </div>
            </div>

            {/* Carrossel horizontal — um card por vez, swipe no mobile, snap */}
            <div
              ref={scrollerRef}
              onScroll={onScrollerScroll}
              className="flex snap-x snap-mandatory gap-4 overflow-x-auto no-scrollbar -mx-1 px-1 pb-1"
            >
              {campaigns.map((campaign) => (
                <div key={campaign.id} className="w-full shrink-0 snap-start">
                  <CampaignCard
                    campaign={campaign}
                    userCampaigns={userCampaigns ?? []}
                    onJoin={handleJoinCampaign}
                    onVerify={handleVerifyTasks}
                    onClaim={handleClaimReward}
                    isJoining={isJoinLoading}
                    isVerifying={isVerifyLoading}
                    isClaiming={isClaimLoading}
                    isCreator={!!currentUserId && currentUserId === campaign.creator_twitter_user_id}
                  />
                </div>
              ))}
            </div>

            {/* Bolinhas de posição */}
            {campaigns.length > 1 && (
              <div className="mt-4 flex items-center justify-center gap-1.5">
                {campaigns.map((c, i) => (
                  <button
                    key={c.id}
                    onClick={() => scrollToCard(i)}
                    aria-label={`${t('campaigns.go_to')} ${i + 1}`}
                    className={`h-2 rounded-full transition-all ${
                      i === carIdx ? 'w-6 bg-[var(--accent)]' : 'w-2 bg-[var(--border)] hover:bg-[var(--accent-soft)]'
                    }`}
                  />
                ))}
              </div>
            )}
          </>
        ))}

      </div>

      {/* ── Create Campaign Modal ────────────────────────────────────── */}
      <Modal
        isOpen={isCreateModalOpen}
        animateIn={createModalAnimateIn}
        onBackdropClick={closeCreateModal}
        boxClassName="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl"
      >
            <div className="flex items-center justify-between p-5 border-b border-gray-100">
              <h2 className="text-base font-bold text-gray-800">Nova Campanha</h2>
              <button onClick={closeCreateModal} aria-label={t('common.close')} className="text-gray-400 hover:text-gray-600 transition-colors">
                <IconClose className="w-5 h-5" sw={2} />
              </button>
            </div>
            <div className="p-5">
              <CreateCampaignForm
                onSuccess={handleCreateSuccess}
                onCancel={closeCreateModal}
                onError={(message) => toast.error(message)}
              />
            </div>
      </Modal>
    </div>
  );
}
