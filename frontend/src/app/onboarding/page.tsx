"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import Navbar from "../../components/navbar/Navbar";
import { ThemeProviderWrapper } from "@/providers/ThemeProvider";
import { useLanguage } from "@/contexts/LanguageContext";
import { registerCreator, CreatorRegisterResult, CreatorChain } from "@/api/api";
import { detectWallets, type DetectedWallet } from "@/lib/walletProviders";
import { CHAIN_LABEL, type Chain } from "@/lib/chains";
import { shortEvmAddress } from "@/lib/evmWallet";
import { IconUser, IconWallet, IconCheck, IconDollar, IconArrow, IconActivity } from "@/components/icons";

type Step = "form" | "loading" | "success" | "error";

export default function OnboardingPage() {
  const { t } = useLanguage();
  const [step, setStep] = useState<Step>("form");
  const [handle, setHandle] = useState("");
  const [result, setResult] = useState<CreatorRegisterResult | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [connecting, setConnecting] = useState<string | null>(null);
  const [wallets, setWallets] = useState<DetectedWallet[]>([]);
  // Wallet CONECTADA (endereço + chain + como assinar) — a única fonte de endereço.
  // Não há mais campo de texto livre: só entra endereço provado por assinatura.
  const [connected, setConnected] = useState<{ address: string; chain: Chain; wallet: DetectedWallet } | null>(null);

  // Detecta todas as wallets instaladas: EVM (EIP-6963), Phantom/Solflare, Freighter
  useEffect(() => {
    detectWallets().then(setWallets);
  }, []);

  const handleConnectWallet = async (wallet: DetectedWallet) => {
    setConnecting(wallet.id);
    setErrorMsg("");
    try {
      const address = await wallet.connect();
      setConnected({ address, chain: wallet.chain, wallet });
    } catch {
      setErrorMsg(t("onboarding.error_wallet"));
    } finally {
      setConnecting(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const h = handle.trim().replace(/^@/, "");
    if (!h || !connected) return;

    setStep("loading");
    try {
      // Prova de posse: a wallet conectada assina um desafio vinculado ao endereço + handle.
      const challenge = `XiaoLee creator registration|wallet:${connected.address}|handle:@${h}|ts:${Date.now()}`;
      const proof = await connected.wallet.sign(challenge);
      const data = await registerCreator(h, connected.address, connected.chain as CreatorChain, {
        signed_message: challenge,
        signature: proof.signature,
        proof_encoding: proof.encoding,
      });
      setResult(data);
      setStep("success");
    } catch (err: unknown) {
      const httpStatus = (err as { response?: { status?: number } })?.response?.status;
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      // Rejeição da assinatura pela wallet (usuário cancelou / sem suporte)
      const rejected = (err as { code?: number })?.code === 4001 || /sign|reject|denied|no_sign/i.test(String((err as Error)?.message));
      const msg = rejected
        ? t("onboarding.error_signature")
        : httpStatus === 422 || httpStatus === 400
          ? (detail ?? t("onboarding.error_invalid_wallet"))
          : t("onboarding.error_wallet");
      setErrorMsg(msg);
      setStep("error");
    }
  };

  return (
    <ThemeProviderWrapper>
      <div className="min-h-screen bg-[var(--main-bg)] transition-colors duration-500">
        <Navbar />

        <main className="container mx-auto px-4 py-12 max-w-md">

          {/* ── Header ──────────────────────────────────────────────── */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-[var(--accent)] text-white shadow-lg mb-4">
              <IconDollar className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-extrabold text-[var(--text-primary)] leading-tight mb-2">
              {t("onboarding.title")}
            </h1>
            <p className="text-sm text-gray-500 max-w-xs mx-auto leading-relaxed">
              {t("onboarding.subtitle")}
            </p>
          </div>

          {/* ── Form state ──────────────────────────────────────────── */}
          {(step === "form" || step === "loading") && (
            <form onSubmit={handleSubmit} className="rounded-2xl border border-[var(--border)] bg-white shadow-sm p-6 flex flex-col gap-5">

              {/* Handle */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-gray-500 uppercase tracking-widest flex items-center gap-1.5">
                  <span className="text-[var(--accent)]"><IconUser className="w-5 h-5" /></span>
                  {t("onboarding.handle_label")}
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 font-semibold text-sm select-none">@</span>
                  <input
                    type="text"
                    value={handle}
                    onChange={(e) => setHandle(e.target.value.replace(/^@/, ""))}
                    placeholder={t("onboarding.handle_placeholder")}
                    required
                    disabled={step === "loading"}
                    className="w-full pl-8 pr-4 py-3 rounded-xl border border-gray-200 bg-gray-50 text-sm font-semibold text-gray-800 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-[rgba(216,27,120,0.35)] focus:border-[rgba(216,27,120,0.45)] disabled:opacity-60 transition"
                  />
                </div>
              </div>

              {/* Connect wallet — sem campo de texto: só endereço provado por assinatura */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-gray-500 uppercase tracking-widest flex items-center gap-1.5">
                  <span className="text-[var(--accent)]"><IconWallet className="w-5 h-5" /></span>
                  {t("onboarding.wallet_label")}
                </label>

                {connected ? (
                  /* Wallet conectada — endereço + chain + botão trocar */
                  <div className="flex items-center gap-3 rounded-xl border border-emerald-100 bg-emerald-50 px-4 py-3">
                    <span className="w-8 h-8 rounded-lg bg-emerald-500 text-white flex items-center justify-center shrink-0">
                      <IconCheck className="w-4 h-4" />
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-sm font-bold text-gray-800 truncate">{shortEvmAddress(connected.address, 8, 6)}</span>
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-[var(--accent-soft)] text-[var(--accent)] font-bold text-[10px] uppercase shrink-0">
                          {CHAIN_LABEL[connected.chain]}
                        </span>
                      </div>
                      <p className="text-[11px] text-emerald-600 font-semibold mt-0.5">{t("onboarding.wallet_connected")}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setConnected(null)}
                      disabled={step === "loading"}
                      className="shrink-0 text-xs font-bold text-gray-400 hover:text-[var(--accent)] disabled:opacity-50 transition-colors"
                    >
                      {t("onboarding.wallet_change")}
                    </button>
                  </div>
                ) : wallets.length > 0 ? (
                  /* Wallets instaladas — clicar conecta (a assinatura é pedida no submit) */
                  <div className="flex flex-wrap gap-1.5">
                    {wallets.map((w) => (
                      <button
                        key={w.id}
                        type="button"
                        onClick={() => handleConnectWallet(w)}
                        disabled={connecting !== null || step === "loading"}
                        title={`${w.name} · ${CHAIN_LABEL[w.chain]}`}
                        className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-[var(--border)] bg-[var(--accent-soft)] text-[var(--accent)] text-xs font-bold hover:bg-[#fbe3ef] disabled:opacity-50 transition"
                      >
                        {w.icon && (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={w.icon} alt="" className="w-4 h-4 rounded" />
                        )}
                        {connecting === w.id ? t("onboarding.connecting") : w.name}
                        <span className="text-[9px] font-bold uppercase text-[var(--accent)]/60">
                          {CHAIN_LABEL[w.chain]}
                        </span>
                      </button>
                    ))}
                  </div>
                ) : (
                  /* Nenhuma wallet instalada */
                  <div className="rounded-xl border border-dashed border-[var(--border)] bg-gray-50 px-4 py-3 text-center">
                    <p className="text-xs text-gray-500 font-medium">{t("onboarding.wallet_none_installed")}</p>
                  </div>
                )}

                <p className="text-xs text-gray-400 mt-0.5">{t("onboarding.wallet_ownership_hint")}</p>
              </div>

              {/* Submit */}
              <button
                type="submit"
                disabled={step === "loading" || !handle.trim() || !connected}
                className="w-full flex items-center justify-center gap-2 py-3.5 rounded-xl bg-[var(--accent)] text-white text-sm font-bold shadow-lg hover:bg-[var(--accent-hover)] focus:outline-none focus:ring-4 focus:ring-[rgba(216,27,120,0.25)] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 hover:scale-[1.02] active:scale-[0.98]"
              >
                {step === "loading" ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                    {t("onboarding.submitting")}
                  </>
                ) : (
                  <>
                    {t("onboarding.submit")}
                    <IconArrow className="w-4 h-4" />
                  </>
                )}
              </button>

              {/* What happens next */}
              <div className="border-t border-gray-100 pt-4 flex flex-col gap-2">
                <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">{t("onboarding.what_next")}</p>
                {[t("onboarding.next_1"), t("onboarding.next_2"), t("onboarding.next_3")].map((s, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs text-gray-500">
                    <span className="w-4 h-4 rounded-full bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center font-bold shrink-0 mt-0.5 text-[10px]">
                      {i + 1}
                    </span>
                    {s}
                  </div>
                ))}
              </div>
            </form>
          )}

          {/* ── Success state ────────────────────────────────────────── */}
          {step === "success" && result && (
            <div className="rounded-2xl border border-emerald-100 bg-emerald-50 shadow-sm p-8 flex flex-col items-center gap-5 text-center">
              <div className="w-16 h-16 rounded-2xl bg-emerald-500 text-white flex items-center justify-center shadow-lg">
                <IconCheck className="w-8 h-8" />
              </div>
              <div>
                <h2 className="text-xl font-extrabold text-emerald-800 mb-1">
                  {result.already_registered ? t("onboarding.success_existing") : t("onboarding.success_new")}
                </h2>
                <p className="text-sm text-emerald-700 font-semibold">{result.creator}</p>
                <p className="text-sm text-emerald-600 mt-1">{t("onboarding.success_eligible")}</p>
              </div>

              <div className="w-full rounded-xl bg-white border border-emerald-100 p-4 text-left flex flex-col gap-2">
                <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">{t("onboarding.success_details")}</p>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-500">{t("onboarding.success_handle")}</span>
                  <span className="font-bold text-gray-800">{result.creator}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-500">{t("onboarding.success_wallet")}</span>
                  <span className="font-mono text-gray-600 truncate max-w-[160px]">{result.circle_wallet_id.slice(0, 20)}…</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-500">{t("onboarding.success_at")}</span>
                  <span className="text-gray-600">{new Date(result.registered_at).toLocaleTimeString()}</span>
                </div>
              </div>

              <Link
                href="/traction"
                className="w-full flex items-center justify-center gap-2 py-3.5 rounded-xl bg-[var(--accent)] text-white text-sm font-bold shadow-lg hover:bg-[var(--accent-hover)] transition-all duration-200 hover:scale-[1.02]"
              >
                <IconActivity className="w-4 h-4" />
                {t("onboarding.success_cta")}
              </Link>

              <button
                onClick={() => { setStep("form"); setHandle(""); setConnected(null); setResult(null); }}
                className="text-xs text-gray-400 hover:text-[var(--accent)] transition-colors"
              >
                {t("onboarding.register_another")}
              </button>
            </div>
          )}

          {/* ── Error state ──────────────────────────────────────────── */}
          {step === "error" && (
            <div className="rounded-2xl border border-red-100 bg-red-50 shadow-sm p-8 flex flex-col items-center gap-4 text-center">
              <div className="w-12 h-12 rounded-2xl bg-red-100 text-red-500 flex items-center justify-center">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6">
                  <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
              </div>
              <div>
                <h2 className="text-base font-bold text-red-700 mb-1">{t("onboarding.error_title")}</h2>
                <p className="text-sm text-red-600">{errorMsg}</p>
              </div>
              <button
                onClick={() => setStep("form")}
                className="px-6 py-2.5 rounded-xl bg-red-500 text-white text-sm font-bold hover:bg-red-600 transition"
              >
                {t("onboarding.error_retry")}
              </button>
            </div>
          )}

          {/* ── Footer ──────────────────────────────────────────────── */}
          <p className="text-center text-xs text-gray-400 font-medium uppercase tracking-widest mt-8">
            Arc Lepton · RFB-06 · XiaoLee Core
          </p>

        </main>
      </div>
    </ThemeProviderWrapper>
  );
}
