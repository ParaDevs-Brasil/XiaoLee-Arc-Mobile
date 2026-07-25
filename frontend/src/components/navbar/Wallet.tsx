"use client";

import React, { useState, useEffect, useCallback } from "react";
import { WalletProps } from "@/interfaces";
import { useModal } from "@/hooks/useModal";
import { Modal } from "@/components/ui/Modal";
import api from "@/api/api";
import { getStoredConnectedWallet, clearStoredConnectedWallet } from "@/lib/walletProviders";
import { CHAIN_LABEL, type Chain } from "@/lib/chains";
import { clearStoredEvmAddress, getEvmChainName, getStoredEvmAddress, shortEvmAddress } from "@/lib/evmWallet";
import { IconLogout, IconClose } from "@/components/icons";

const Wallet: React.FC<WalletProps> = ({ balance = [], shouldOpen = false, onClose, onRequestConnect }) => {
  const { isOpen, animateIn, closeModal } = useModal(shouldOpen, onClose);

  const [address, setAddress] = useState<string>("");
  const [chain, setChain] = useState<Chain | null>(null);
  const [chainName, setChainName] = useState<string>("");
  const [statusMsg, setStatusMsg] = useState<string>("");
  const [copied, setCopied] = useState(false);
  // Saldo USDC on-chain no Arc (lido pelo backend via RPC) — null = indisponível
  const [arcUsdc, setArcUsdc] = useState<number | null>(null);

  const loadChain = useCallback(async () => {
    setChainName(await getEvmChainName());
  }, []);

  useEffect(() => {
    // Wallet universal (Connect Wallet) tem prioridade e já sabe a chain; chave EVM legada é sempre Arc
    const connected = getStoredConnectedWallet();
    if (connected?.address) {
      setAddress(connected.address);
      setChain(connected.chain);
      return;
    }
    const legacy = getStoredEvmAddress();
    if (legacy) {
      setAddress(legacy);
      setChain("arc");
    }
  }, [isOpen]);

  useEffect(() => {
    // Nome de rede (ex.: "Arc Sepolia") só existe pro trilho EVM — Solana/Stellar usam o rótulo fixo da chain
    if (isOpen && address && chain === "arc") loadChain();
  }, [isOpen, address, chain, loadChain]);

  useEffect(() => {
    if (!isOpen || !address || chain !== "arc") return;
    setArcUsdc(null);
    api
      .get<{ usdc_balance: number }>(`/v1/arc/balance/${address}`)
      .then((resp) => setArcUsdc(resp.data.usdc_balance))
      .catch(() => setArcUsdc(null));
  }, [isOpen, address, chain]);

  const handleRequestConnect = () => {
    // Deixa a animação de saída do próprio modal terminar antes de abrir o fluxo universal
    closeModal();
    setTimeout(() => onRequestConnect?.(), 300);
  };

  const handleDisconnect = () => {
    clearStoredConnectedWallet();
    clearStoredEvmAddress();
    setAddress("");
    setChain(null);
    setChainName("");
    setStatusMsg("Carteira desconectada.");
  };

  const handleCopyAddress = () => {
    if (!address) return;
    navigator.clipboard.writeText(address);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const rewardTokens = Array.isArray(balance) ? balance : [];
  const totalUSD = rewardTokens.reduce((sum, t) => sum + (t.valueUSD ?? 0), 0);
  // Nome de rede real (Arc) ou rótulo fixo da chain (Solana/Stellar não têm "nome de rede" dinâmico)
  const chainLabel = chain === "arc" ? chainName : chain ? CHAIN_LABEL[chain] : "";

  return (
    <Modal
      isOpen={isOpen}
      animateIn={animateIn}
      onBackdropClick={closeModal}
      boxClassName="bg-white rounded-3xl shadow-e3 border border-[var(--border)] max-w-2xl w-full max-h-[90vh] overflow-hidden"
    >
        {/* ── Header ───────────────────────────────────────────────── */}
        <div className="border-b border-[var(--border)]">
          <div className="px-6 pt-6 flex items-center justify-between mb-4">
            <div>
              <h2 className="text-2xl font-bold text-[var(--ink)]">
                💰 XiaoLee <span className="text-grad">Wallet</span>
              </h2>
              <p className="text-sm text-[var(--ink-2)]">XiaoLee · USDC · x402</p>
            </div>
            <div className="flex items-center gap-2">
              {address && (
                <button
                  onClick={handleDisconnect}
                  title="Desconectar"
                  aria-label="Desconectar carteira"
                  className="p-2 hover:bg-black/5 rounded-lg transition-colors"
                >
                  <IconLogout className="w-5 h-5 text-[var(--danger)]" sw={2} />
                </button>
              )}
              <button onClick={closeModal} title="Fechar" aria-label="Fechar" className="p-2 hover:bg-black/5 rounded-lg transition-colors">
                <IconClose className="w-5 h-5 text-[var(--ink-3)]" sw={2} />
              </button>
            </div>
          </div>

          {/* Token strip — trilhos XiaoLee */}
          <div className="flex items-stretch divide-x divide-[var(--border)]">
            {[
              { symbol: "USDC", network: "XiaoLee", icon: "$" },
              { symbol: "Rewards", network: "XiaoLee", icon: "✦" },
            ].map((t) => (
              <div key={t.symbol} className="flex-1 flex items-center gap-2 px-4 py-2 bg-[var(--bg)] hover:bg-[var(--accent-soft)] transition-colors">
                <span className="w-7 h-7 rounded-full bg-[var(--accent)] flex items-center justify-center text-white text-xs font-bold shrink-0">
                  {t.icon}
                </span>
                <div>
                  <p className="text-xs font-bold text-[var(--ink)] leading-none">{t.symbol}</p>
                  <p className="text-[10px] text-[var(--accent)] leading-none mt-0.5">{t.network}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Total Balance */}
          <div className="mx-6 my-4 text-center bg-[var(--bg)] border border-[var(--border)] rounded-xl p-6">
            <p className="text-sm text-[var(--ink-2)] mb-2">Total Balance</p>
            {address ? (
              <>
                <p className="text-5xl font-bold text-[var(--accent)]">
                  ${((arcUsdc ?? 0) + totalUSD).toFixed(2)}
                </p>
                <p className="text-sm text-[var(--ink-2)] mt-1">
                  {arcUsdc != null
                    ? `${arcUsdc.toFixed(2)} USDC no Arc${totalUSD > 0 ? " + recompensas" : ""}`
                    : chain && chain !== "arc"
                    ? `Recompensas XiaoLee · saldo on-chain ${CHAIN_LABEL[chain]} em breve`
                    : `Recompensas XiaoLee${chainLabel ? ` · ${chainLabel}` : ""}`}
                </p>
              </>
            ) : (
              <p className="text-lg text-[var(--ink-2)]">Conecte sua carteira</p>
            )}
          </div>

          {/* Account pill */}
          {address && (
            <div className="mx-6 mb-4 flex items-center justify-between bg-[var(--bg)] border border-[var(--border)] rounded-xl px-4 py-2">
              <div>
                <p className="text-xs font-mono font-semibold text-[var(--ink)]">{shortEvmAddress(address, 8, 6)}</p>
                <p className="text-[10px] text-[var(--ink-2)]">
                  XiaoLee{chainLabel ? ` · ${chainLabel}` : ""}
                </p>
              </div>
              <button onClick={handleCopyAddress} className="text-xs text-[var(--accent)] hover:text-[var(--accent-hover)] transition-colors">
                {copied ? "✓ copiado" : "copiar"}
              </button>
            </div>
          )}
        </div>

        {/* ── Token List ────────────────────────────────────────────── */}
        <div className="p-6 max-h-[55vh] overflow-y-auto space-y-4">
          {!address ? (
            <div className="text-center py-10">
              <div className="text-5xl mb-3">✦</div>
              <p className="text-[var(--ink-2)] text-sm mb-5">
                Conecte sua carteira para ver seus saldos e recompensas XiaoLee
              </p>
              <button
                onClick={handleRequestConnect}
                className="px-8 py-2.5 rounded-xl btn-primary text-white font-semibold transition-all"
              >
                Conectar Carteira
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              <h3 className="text-xl font-semibold text-[var(--ink)] flex items-center gap-2">
                💎 Your Tokens
              </h3>

              {/* USDC on-chain no Arc */}
              {arcUsdc != null && (
                <div className="bg-[var(--bg)] rounded-xl p-4 border border-[var(--border)] hover:border-[var(--accent)]/40 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-[var(--accent-soft)] text-[var(--accent)] rounded-lg flex items-center justify-center text-lg">$</div>
                      <div>
                        <p className="font-semibold text-[var(--ink)]">USDC</p>
                        <p className="text-xs text-[var(--ink-2)]">Arc Testnet · on-chain</p>
                      </div>
                    </div>
                    <p className="font-semibold text-[var(--ink)]">{arcUsdc.toFixed(2)} USDC</p>
                  </div>
                </div>
              )}

              {/* Campaign reward tokens */}
              {rewardTokens.map((tokenData) => (
                <div key={tokenData.token} className="bg-[var(--bg)] rounded-xl p-4 border border-[var(--border)] hover:border-[var(--accent)]/40 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-[var(--accent-soft)] text-[var(--accent)] rounded-lg flex items-center justify-center text-lg">💰</div>
                      <div>
                        <p className="font-semibold text-[var(--ink)]">{tokenData.token}</p>
                        <p className="text-xs text-[var(--ink-2)]">{tokenData.balance.toLocaleString()} tokens</p>
                      </div>
                    </div>
                    <p className="font-semibold text-[var(--ink)]">${tokenData.valueUSD.toFixed(2)}</p>
                  </div>
                </div>
              ))}

              {rewardTokens.length === 0 && (
                <p className="text-xs text-[var(--ink-2)] text-center py-3">
                  Sem recompensas ainda — participe de uma campanha XiaoLee para ganhar tokens.
                </p>
              )}
            </div>
          )}

          {statusMsg && (
            <div className={`p-3 rounded-xl text-sm border ${
              statusMsg.startsWith("Erro") || statusMsg.includes("não encontrada")
                ? "bg-[var(--accent-soft)] border-[var(--danger)]/30 text-[var(--danger)]"
                : "bg-[var(--accent-soft)] border-[var(--border)] text-[var(--ink)]"
            }`}>
              {statusMsg}
            </div>
          )}
        </div>

        {/* ── Footer ───────────────────────────────────────────────── */}
        <div className="px-6 py-3 border-t border-[var(--border)] bg-[var(--bg)]">
          <p className="text-center text-sm text-[var(--ink-2)]">
            Secured by XiaoLee · USDC · x402
          </p>
        </div>
    </Modal>
  );
};

export default Wallet;
