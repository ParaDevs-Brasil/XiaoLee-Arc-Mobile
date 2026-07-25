"use client";

import React, { useEffect, useState } from "react";
import { toast } from "react-toastify";
import { useModal } from "@/hooks/useModal";
import { useLanguage } from "@/contexts/LanguageContext";
import UserData from "../UserData";
import {
  connectEvmWallet,
  clearStoredEvmAddress,
  getEvmChainName,
  getStoredEvmAddress,
  isEvmWalletInstalled,
  shortEvmAddress,
} from "@/lib/evmWallet";

interface EvmWalletProps {
  shouldOpen?: boolean;
  onClose?: () => void;
}

const EvmWallet: React.FC<EvmWalletProps> = ({ shouldOpen = false, onClose }) => {
  const { isOpen, animateIn, closeModal } = useModal(shouldOpen, onClose);
  const { t } = useLanguage();

  const [installed, setInstalled] = useState(false);
  const [address, setAddress] = useState("");
  const [chainName, setChainName] = useState("");
  const [connecting, setConnecting] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    setInstalled(isEvmWalletInstalled());
    const stored = getStoredEvmAddress();
    if (stored) {
      setAddress(stored);
      getEvmChainName().then(setChainName);
    }
  }, [isOpen]);

  const handleConnect = async () => {
    setConnecting(true);
    try {
      const addr = await connectEvmWallet();
      setAddress(addr);
      setChainName(await getEvmChainName());
      UserData.setDevnetWalletSession(addr);
      toast.success(t("evm_wallet.session_linked"));
    } catch {
      toast.error(t("evm_wallet.connect_error"));
    } finally {
      setConnecting(false);
    }
  };

  const handleCopy = async () => {
    await navigator.clipboard.writeText(address);
    toast.success(t("evm_wallet.copied"));
  };

  const handleDisconnect = () => {
    clearStoredEvmAddress();
    setAddress("");
    setChainName("");
  };

  if (!isOpen) return null;

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center p-4 transition-all duration-300 ${
        animateIn ? "bg-black/30 backdrop-blur-sm" : "bg-black/0"
      }`}
      onClick={closeModal}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className={`bg-gradient-to-br from-[var(--modal-bg-start)] via-[var(--modal-bg-middle)] to-[var(--modal-bg-end)] rounded-3xl shadow-2xl border-2 border-[var(--modal-border)] max-w-md w-full overflow-hidden transition-all duration-300 transform ${
          animateIn ? "scale-100 opacity-100" : "scale-95 opacity-0"
        }`}
      >
        {/* Header */}
        <div className="flex items-start justify-between px-6 pt-6 pb-4 border-b border-[var(--modal-border)]/40">
          <div>
            <h2 className="text-lg font-extrabold text-[var(--text-primary)]">{t("evm_wallet.title")}</h2>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">{t("evm_wallet.subtitle")}</p>
          </div>
          <button
            onClick={closeModal}
            aria-label={t("common.close")}
            className="w-8 h-8 grid place-items-center rounded-full text-[var(--text-secondary)] hover:bg-black/5 transition-colors"
          >
            ✕
          </button>
        </div>

        <div className="p-6 flex flex-col gap-4">
          {!installed ? (
            <div className="flex flex-col items-center gap-4 text-center py-4">
              <div className="w-14 h-14 rounded-2xl bg-amber-50 border border-amber-100 text-amber-500 grid place-items-center text-2xl">
                Ξ
              </div>
              <p className="text-sm text-[var(--text-secondary)] leading-relaxed max-w-xs">
                {t("evm_wallet.not_installed")}
              </p>
              <a
                href="https://metamask.io/download/"
                target="_blank"
                rel="noopener noreferrer"
                className="px-5 py-2.5 rounded-xl btn-primary text-white text-sm font-bold transition-all"
              >
                {t("evm_wallet.install")} ↗
              </a>
            </div>
          ) : !address ? (
            <div className="flex flex-col items-center gap-4 text-center py-4">
              <div className="w-14 h-14 rounded-2xl bg-[var(--accent-soft)] border border-[var(--border)] text-[var(--accent)] grid place-items-center text-2xl">
                Ξ
              </div>
              <p className="text-sm text-[var(--text-secondary)] leading-relaxed max-w-xs">
                {t("evm_wallet.hint")}
              </p>
              <button
                onClick={handleConnect}
                disabled={connecting}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-xl btn-primary text-white text-sm font-bold disabled:opacity-50 transition-all"
              >
                {connecting && <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />}
                {connecting ? t("evm_wallet.connecting") : t("evm_wallet.connect")}
              </button>
            </div>
          ) : (
            <>
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-[var(--success)]">
                <span className="w-2 h-2 rounded-full bg-[var(--success)] animate-pulse" />
                {t("evm_wallet.connected")}
              </div>

              <div className="rounded-2xl border border-[var(--modal-border)]/50 bg-white/40 p-4 flex flex-col gap-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs text-[var(--text-secondary)]">{t("evm_wallet.address")}</span>
                  <button
                    onClick={handleCopy}
                    title={t("evm_wallet.copy")}
                    className="font-mono text-sm font-semibold text-[var(--text-primary)] hover:text-[var(--accent)] transition-colors"
                  >
                    {shortEvmAddress(address, 8, 6)} ⧉
                  </button>
                </div>
                {chainName && (
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs text-[var(--text-secondary)]">{t("evm_wallet.network")}</span>
                    <span className="text-xs font-bold text-[var(--accent)] bg-[var(--accent-soft)] border border-[var(--border)] rounded-lg px-2 py-1">
                      {chainName}
                    </span>
                  </div>
                )}
              </div>

              <p className="text-xs text-[var(--text-secondary)] leading-relaxed">{t("evm_wallet.hint")}</p>

              <button
                onClick={handleDisconnect}
                className="self-start text-xs font-semibold text-[var(--danger)] hover:opacity-80 transition-colors"
              >
                {t("evm_wallet.disconnect")}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default EvmWallet;
