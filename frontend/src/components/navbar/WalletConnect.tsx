"use client";

import React, { useEffect, useState } from "react";
import Image from "next/image";
import { toast } from "react-toastify";
import { useModal } from "@/hooks/useModal";
import { Modal } from "@/components/ui/Modal";
import { IconClose } from "@/components/icons";
import { useLanguage } from "@/contexts/LanguageContext";
import UserData from "../UserData";
import {
  detectWallets,
  getStoredConnectedWallet,
  storeConnectedWallet,
  clearStoredConnectedWallet,
  type ConnectedWallet,
  type DetectedWallet,
} from "@/lib/walletProviders";
import { CHAIN_LABEL, detectChainFromAddress } from "@/lib/chains";
import { getEvmChainName, shortEvmAddress } from "@/lib/evmWallet";

interface WalletConnectProps {
  shouldOpen?: boolean;
  onClose?: () => void;
}

const CHAIN_BADGE: Record<string, string> = {
  arc: "text-[var(--accent)] bg-[var(--accent-soft)] border-[var(--border)]",
  solana: "text-violet-600 bg-violet-50 border-violet-100",
  stellar: "text-sky-600 bg-sky-50 border-sky-100",
};

const WalletConnect: React.FC<WalletConnectProps> = ({ shouldOpen = false, onClose }) => {
  const { isOpen, animateIn, closeModal } = useModal(shouldOpen, onClose);
  const { t } = useLanguage();

  const [wallets, setWallets] = useState<DetectedWallet[]>([]);
  const [detecting, setDetecting] = useState(true);
  const [connected, setConnected] = useState<ConnectedWallet | null>(null);
  const [networkName, setNetworkName] = useState("");
  const [connecting, setConnecting] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    setDetecting(true);
    detectWallets()
      .then(setWallets)
      .finally(() => setDetecting(false));
    const stored = getStoredConnectedWallet();
    setConnected(stored);
    if (stored?.chain === "arc") getEvmChainName().then(setNetworkName);
  }, [isOpen]);

  const handleConnect = async (wallet: DetectedWallet) => {
    setConnecting(wallet.id);
    try {
      const address = await wallet.connect();
      const chain = detectChainFromAddress(address) ?? wallet.chain;
      const next: ConnectedWallet = { address, chain, walletName: wallet.name, providerId: wallet.id };
      storeConnectedWallet(next);
      setConnected(next);
      setNetworkName(chain === "arc" ? await getEvmChainName() : "");
      // Sessão custodial (Google/Telegram) NÃO é sobrescrita — a wallet vira só a
      // identidade de payout; sem ela, a wallet também assume a sessão de campanhas.
      const sessionId = UserData.getSessionId();
      if (!/^(google_|tg_)/.test(sessionId)) {
        UserData.setDevnetWalletSession(address);
      }
      toast.success(t("wallet_connect.session_linked"));
    } catch {
      toast.error(t("wallet_connect.connect_error"));
    } finally {
      setConnecting(null);
    }
  };

  const handleCopy = async () => {
    if (!connected) return;
    await navigator.clipboard.writeText(connected.address);
    toast.success(t("wallet_connect.copied"));
  };

  const handleDisconnect = () => {
    clearStoredConnectedWallet();
    setConnected(null);
    setNetworkName("");
  };

  return (
    <Modal
      isOpen={isOpen}
      animateIn={animateIn}
      onBackdropClick={closeModal}
      boxClassName="bg-gradient-to-br from-[var(--modal-bg-start)] via-[var(--modal-bg-middle)] to-[var(--modal-bg-end)] rounded-3xl shadow-2xl border-2 border-[var(--modal-border)] max-w-md w-full overflow-hidden"
    >
        {/* Header */}
        <div className="flex items-start justify-between px-6 pt-6 pb-4 border-b border-[var(--modal-border)]/40">
          <div>
            <h2 className="text-lg font-extrabold text-[var(--text-primary)]">{t("wallet_connect.title")}</h2>
            <p className="text-xs text-[var(--text-secondary)] mt-0.5">{t("wallet_connect.subtitle")}</p>
          </div>
          <button
            onClick={closeModal}
            aria-label={t("common.close")}
            className="w-8 h-8 grid place-items-center rounded-full text-[var(--text-secondary)] hover:bg-black/5 transition-colors"
          >
            <IconClose className="w-4 h-4" sw={2} />
          </button>
        </div>

        <div className="p-6 flex flex-col gap-4">
          {connected ? (
            <>
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-[var(--success)]">
                <span className="w-2 h-2 rounded-full bg-[var(--success)] animate-pulse" />
                {t("wallet_connect.connected")} · {connected.walletName}
              </div>

              <div className="rounded-2xl border border-[var(--modal-border)]/50 bg-white/40 p-4 flex flex-col gap-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs text-[var(--text-secondary)]">{t("wallet_connect.address")}</span>
                  <button
                    onClick={handleCopy}
                    title={t("wallet_connect.copy")}
                    className="font-mono text-sm font-semibold text-[var(--text-primary)] hover:text-[var(--accent)] transition-colors"
                  >
                    {shortEvmAddress(connected.address, 8, 6)} ⧉
                  </button>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs text-[var(--text-secondary)]">{t("wallet_connect.network")}</span>
                  <span
                    className={`text-xs font-bold border rounded-lg px-2 py-1 ${CHAIN_BADGE[connected.chain]}`}
                  >
                    {CHAIN_LABEL[connected.chain]}
                    {networkName && ` · ${networkName}`}
                  </span>
                </div>
              </div>

              <p className="text-xs text-[var(--text-secondary)] leading-relaxed">{t("wallet_connect.hint")}</p>

              <button
                onClick={handleDisconnect}
                className="self-start text-xs font-semibold text-[var(--danger)] hover:opacity-80 transition-colors"
              >
                {t("wallet_connect.disconnect")}
              </button>
            </>
          ) : detecting ? (
            <div className="flex items-center justify-center gap-3 py-8 text-sm text-[var(--text-secondary)]">
              <span className="w-4 h-4 border-2 border-[var(--accent)]/30 border-t-[var(--accent)] rounded-full animate-spin" />
              {t("wallet_connect.detecting")}
            </div>
          ) : wallets.length === 0 ? (
            <div className="flex flex-col items-center gap-4 text-center py-4">
              <div className="w-14 h-14 rounded-2xl bg-amber-50 border border-amber-100 text-amber-500 grid place-items-center text-2xl">
                ◈
              </div>
              <p className="text-sm text-[var(--text-secondary)] leading-relaxed max-w-xs">
                {t("wallet_connect.none_installed")}
              </p>
              <a
                href="https://metamask.io/download/"
                target="_blank"
                rel="noopener noreferrer"
                className="px-5 py-2.5 rounded-xl btn-primary text-white text-sm font-bold transition-all"
              >
                {t("wallet_connect.install")} ↗
              </a>
            </div>
          ) : (
            <>
              <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
                {t("wallet_connect.pick_hint")}
              </p>
              <div className="flex flex-col gap-2">
                {wallets.map((wallet) => (
                  <button
                    key={wallet.id}
                    onClick={() => handleConnect(wallet)}
                    disabled={connecting !== null}
                    className="flex items-center gap-3 w-full p-3 rounded-2xl border border-[var(--modal-border)]/50 bg-white/40 hover:border-[var(--accent)] hover:bg-[var(--accent-soft)]/40 disabled:opacity-50 transition-all text-left"
                  >
                    {wallet.icon ? (
                      <Image
                        src={wallet.icon}
                        alt={wallet.name}
                        width={36}
                        height={36}
                        className="w-9 h-9 rounded-xl"
                        unoptimized
                      />
                    ) : (
                      <span className="w-9 h-9 rounded-xl bg-[var(--accent-soft)] text-[var(--accent)] grid place-items-center text-lg font-bold">
                        {wallet.name.charAt(0)}
                      </span>
                    )}
                    <span className="flex-1 text-sm font-bold text-[var(--text-primary)]">{wallet.name}</span>
                    {connecting === wallet.id ? (
                      <span className="w-4 h-4 border-2 border-[var(--accent)]/30 border-t-[var(--accent)] rounded-full animate-spin" />
                    ) : (
                      <span
                        className={`text-[10px] font-bold uppercase tracking-wider border rounded-lg px-2 py-1 ${CHAIN_BADGE[wallet.chain]}`}
                      >
                        {CHAIN_LABEL[wallet.chain]}
                      </span>
                    )}
                  </button>
                ))}
              </div>
              <p className="text-xs text-[var(--text-secondary)] leading-relaxed">{t("wallet_connect.hint")}</p>
            </>
          )}
        </div>
    </Modal>
  );
};

export default WalletConnect;
