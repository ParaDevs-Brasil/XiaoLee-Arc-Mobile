"use client";

import React, { useEffect, useState } from "react";
import { useModal } from "@/hooks/useModal";
import {
  autoPayX402,
  connectFreighter,
  getAnchorChallenge,
  getStellarBalance,
  getStellarSwapQuote,
  initiateAnchorDeposit,
  isFreighterInstalled,
  signTransactionXdr,
  stellarSEP10Auth,
  submitToHorizon,
  x402AiQuery,
  type AnchorDepositResult,
  type StellarBalance,
  type SwapQuoteResult,
  type X402PaymentInfo,
} from "@/utils/stellar";

interface StellarWalletProps {
  shouldOpen?: boolean;
  onClose?: () => void;
}

type AuthState = "idle" | "connecting" | "authenticating" | "authenticated" | "error";

// All chains XiaoLee integrates — shown in the header strip
const INTEGRATED_TOKENS = [
  { symbol: "SOL",  name: "Solana",         network: "Solana",  icon: "◎", bg: "from-purple-500 to-violet-500", networkColor: "text-purple-400" },
  { symbol: "USDC", name: "USD Coin",        network: "Solana",  icon: "$",  bg: "from-blue-500 to-cyan-500",    networkColor: "text-purple-400" },
  { symbol: "XLM",  name: "Stellar Lumens",  network: "Stellar", icon: "★", bg: "from-sky-400 to-blue-500",     networkColor: "text-sky-400" },
  { symbol: "USDC", name: "USD Coin",        network: "Stellar", icon: "$",  bg: "from-indigo-400 to-violet-400", networkColor: "text-sky-400" },
];

function truncate(addr: string, front = 8, back = 8) {
  if (addr.length <= front + back + 3) return addr;
  return `${addr.slice(0, front)}...${addr.slice(-back)}`;
}

const StellarWallet: React.FC<StellarWalletProps> = ({ shouldOpen = false, onClose }) => {
  const { isOpen, animateIn, closeModal } = useModal(shouldOpen, onClose);

  const [authState, setAuthState] = useState<AuthState>("idle");
  const [account, setAccount] = useState<string>("");
  const [jwt, setJwt] = useState<string>("");
  const [balance, setBalance] = useState<StellarBalance | null>(null);
  const [statusMsg, setStatusMsg] = useState<string>("");
  const [isLoadingBalance, setIsLoadingBalance] = useState(false);

  // Swap state
  const [swapFrom, setSwapFrom] = useState<"XLM" | "USDC">("XLM");
  const [swapTo, setSwapTo] = useState<"XLM" | "USDC">("USDC");
  const [swapAmount, setSwapAmount] = useState<string>("10");
  const [swapQuote, setSwapQuote] = useState<SwapQuoteResult["quote"] | null>(null);
  const [swapXdr, setSwapXdr] = useState<string | null>(null);
  const [swapNetworkPassphrase, setSwapNetworkPassphrase] = useState<string>("");
  const [isSigningSwap, setIsSigningSwap] = useState(false);
  const [isLoadingQuote, setIsLoadingQuote] = useState(false);
  const [swapMsg, setSwapMsg] = useState<string>("");

  // Anchor SEP-24 state
  const [anchorAsset, setAnchorAsset] = useState<"SRT" | "native">("SRT");
  const [anchorLoading, setAnchorLoading] = useState(false);
  const [anchorMsg, setAnchorMsg] = useState("");
  const [anchorResult, setAnchorResult] = useState<AnchorDepositResult | null>(null);

  // x402 state
  const [x402PaymentInfo, setX402PaymentInfo] = useState<X402PaymentInfo | null>(null);
  const [x402TxHash, setX402TxHash] = useState<string>("");
  const [x402SwapTxHash, setX402SwapTxHash] = useState<string>("");
  const [x402Query, setX402Query] = useState<string>("");
  const [x402Reply, setX402Reply] = useState<string>("");
  const [x402Step, setX402Step] = useState<string>("");
  const [x402SwapXdr, setX402SwapXdr] = useState<string | null>(null);
  const [x402SwapPassphrase, setX402SwapPassphrase] = useState<string>("");
  const [isSigningX402Swap, setIsSigningX402Swap] = useState(false);
  const [isX402Loading, setIsX402Loading] = useState(false);

  useEffect(() => {
    const savedAccount = localStorage.getItem("stellar_account");
    const savedJwt = localStorage.getItem("stellar_jwt");
    if (savedAccount && savedJwt) {
      setAccount(savedAccount);
      setJwt(savedJwt);
      setAuthState("authenticated");
    }
  }, []);

  useEffect(() => {
    if (isOpen && account && authState === "authenticated") loadBalance(account);
  }, [isOpen, account]);

  // ---------------------------------------------------------------------------

  const handleConnect = async () => {
    setStatusMsg("");
    const installed = await isFreighterInstalled();
    if (!installed) {
      setStatusMsg("Freighter não encontrado. Instale a extensão em freighter.app e recarregue.");
      return;
    }
    try {
      setAuthState("connecting");
      setStatusMsg("Conectando ao Freighter...");
      const publicKey = await connectFreighter();
      setAccount(publicKey);
      setAuthState("authenticating");
      setStatusMsg("Autenticando com SEP-10... Assine o challenge no Freighter.");
      const { token } = await stellarSEP10Auth(publicKey);
      setJwt(token);
      localStorage.setItem("stellar_account", publicKey);
      localStorage.setItem("stellar_jwt", token);
      setAuthState("authenticated");
      setStatusMsg("Conectado e autenticado na Stellar Testnet!");
      await loadBalance(publicKey);
    } catch (err) {
      setAuthState("error");
      setStatusMsg(`Erro: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const handleDisconnect = () => {
    setAccount(""); setJwt(""); setBalance(null);
    setAuthState("idle");
    localStorage.removeItem("stellar_account");
    localStorage.removeItem("stellar_jwt");
    setStatusMsg("Carteira desconectada.");
  };

  const loadBalance = async (addr: string) => {
    setIsLoadingBalance(true);
    try {
      setBalance(await getStellarBalance(addr));
    } catch (err) {
      setStatusMsg(`Erro ao carregar saldo: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsLoadingBalance(false);
    }
  };

  const handleGetQuote = async () => {
    if (!account) { setSwapMsg("Conecte a carteira Freighter primeiro."); return; }
    const amount = parseFloat(swapAmount);
    if (!Number.isFinite(amount) || amount <= 0) { setSwapMsg("Informe um valor válido."); return; }
    setIsLoadingQuote(true);
    setSwapQuote(null); setSwapXdr(null); setSwapMsg("");
    try {
      const result = await getStellarSwapQuote(account, swapFrom, swapTo, amount);
      setSwapQuote(result.quote);
      setSwapNetworkPassphrase(result.network_passphrase);
      if (result.has_liquidity && result.xdr) {
        setSwapXdr(result.xdr);
        setSwapMsg(`Quote via Stellar DEX. Clique em "Assinar no Freighter" para executar.`);
      } else {
        setSwapMsg("Sem liquidez para esse par no testnet. Tente outro par ou quantidade.");
      }
    } catch (err) {
      setSwapMsg(`Erro: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsLoadingQuote(false);
    }
  };

  const handleSignSwap = async () => {
    if (!swapXdr) return;
    setIsSigningSwap(true);
    setSwapMsg("Assine a transação no Freighter...");
    try {
      const signed = await signTransactionXdr(swapXdr, swapNetworkPassphrase);
      setSwapMsg("Enviando ao Horizon Testnet...");
      const txHash = await submitToHorizon(signed, "testnet");
      setSwapMsg(`✓ Swap executado! tx: ${txHash.slice(0, 16)}...`);
      setSwapXdr(null);
      await loadBalance(account);
    } catch (err) {
      setSwapMsg(`Erro ao assinar: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsSigningSwap(false);
    }
  };

  const handleAnchorDeposit = async () => {
    if (!account) { setAnchorMsg("Conecte a carteira Freighter primeiro."); return; }
    setAnchorLoading(true);
    setAnchorMsg("Obtendo challenge SEP-10 da âncora testanchor.stellar.org...");
    setAnchorResult(null);
    try {
      const { transaction: challengeXdr, network_passphrase } = await getAnchorChallenge(account);
      setAnchorMsg("Assine o challenge da âncora no Freighter...");
      const signedXdr = await signTransactionXdr(challengeXdr, network_passphrase);
      setAnchorMsg(`Iniciando depósito SEP-24 (${anchorAsset})...`);
      const result = await initiateAnchorDeposit(account, signedXdr, anchorAsset);
      setAnchorResult(result);
      setAnchorMsg(`Depósito iniciado! ID: ${result.id.slice(0, 16)}...`);
      window.open(result.url, "_blank", "noopener,noreferrer");
    } catch (err) {
      setAnchorMsg(`Erro: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setAnchorLoading(false);
    }
  };

  const handleX402Query = async () => {
    if (!x402Query.trim()) { setStatusMsg("Digite uma pergunta para a AI."); return; }
    if (!account) { setStatusMsg("Conecte a carteira Freighter primeiro."); return; }
    setIsX402Loading(true);
    setX402Reply(""); setX402PaymentInfo(null); setX402TxHash("");
    setX402Step(""); setStatusMsg("");
    try {
      const first = await x402AiQuery(x402Query, account);
      if (first.status === 200) {
        setX402Reply(first.data.reply);
        setStatusMsg("Query processada via x402.");
        return;
      }
      setX402PaymentInfo(first.payment);
      setX402Step(`Construindo transação de ${first.payment.amount} XLM...`);
      setX402Step("Assine o pagamento no Freighter...");
      const txHash = await autoPayX402(account);
      setX402TxHash(txHash);
      setX402Step(`Tx confirmado · ${txHash.slice(0, 10)}... — consultando AI...`);
      const second = await x402AiQuery(x402Query, account, txHash);
      if (second.status === 200) {
        setX402Reply(second.data.reply);
        setX402Step("");
        setStatusMsg(`✓ Pago e processado · tx: ${txHash.slice(0, 14)}...`);
        const exec = second.data.execution;
        if (exec?.swap_xdr) {
          setX402SwapXdr(exec.swap_xdr as string);
          setX402SwapPassphrase((exec.network_passphrase as string) ?? "Test SDF Network ; September 2015");
        }
      } else {
        setStatusMsg("Pagamento enviado mas o servidor retornou 402 novamente.");
      }
    } catch (err) {
      setStatusMsg(`Erro x402: ${err instanceof Error ? err.message : String(err)}`);
      setX402Step("");
    } finally {
      setIsX402Loading(false);
    }
  };

  const handleSignX402Swap = async () => {
    if (!x402SwapXdr) return;
    setIsSigningX402Swap(true);
    setStatusMsg("Assine o swap no Freighter...");
    try {
      const signed = await signTransactionXdr(x402SwapXdr, x402SwapPassphrase);
      setStatusMsg("Enviando swap ao Horizon Testnet...");
      const txHash = await submitToHorizon(signed, "testnet");
      setX402SwapXdr(null);
      setX402SwapTxHash(txHash);
      setStatusMsg("✓ Swap executado!");
      await loadBalance(account);
    } catch (err) {
      setStatusMsg(`Erro no swap: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsSigningX402Swap(false);
    }
  };

  if (!isOpen) return null;

  const isAuthenticated = authState === "authenticated";
  const isConnecting = authState === "connecting" || authState === "authenticating";

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center p-4 transition-all duration-300 ${
        animateIn ? "bg-black/30 backdrop-blur-sm" : "bg-black/0"
      }`}
      onClick={closeModal}
    >
      <div
        className={`bg-gradient-to-br from-[var(--modal-bg-start)] via-[var(--modal-bg-middle)] to-[var(--modal-bg-end)] rounded-3xl shadow-2xl border-2 border-[var(--modal-border)] max-w-2xl w-full max-h-[92vh] overflow-hidden transition-all duration-300 transform ${
          animateIn ? "scale-100 opacity-100 translate-y-0" : "scale-95 opacity-0 translate-y-4"
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── Header ─────────────────────────────────────────────────── */}
        <div className="border-b border-[var(--modal-footer-border)]">
          {/* Title row */}
          <div className="px-6 pt-6 flex items-center justify-between mb-4">
            <div>
              <h2 className="text-2xl font-bold bg-gradient-to-r from-[var(--modal-header-title-start)] via-[var(--modal-header-title-middle)] to-[var(--modal-header-title-end)] bg-clip-text text-transparent">
                ✦ Stellar Wallet
              </h2>
              <p className="text-sm text-[var(--modal-header-subtitle)]">Testnet · Freighter · SEP-10 · SEP-24</p>
            </div>

            <div className="flex items-center gap-2">
              {isAuthenticated && (
                <button
                  onClick={() => loadBalance(account)}
                  disabled={isLoadingBalance}
                  title="Atualizar saldo"
                  className="p-2 hover:bg-[var(--modal-close-button-bg-hover)] rounded-lg transition-colors disabled:opacity-50"
                >
                  <svg
                    className={`w-5 h-5 text-blue-400 ${isLoadingBalance ? "animate-spin" : ""}`}
                    fill="none" stroke="currentColor" viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                </button>
              )}
              <button
                onClick={closeModal}
                className="p-2 hover:bg-[var(--modal-close-button-bg-hover)] rounded-lg transition-colors"
              >
                <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Account pill (authenticated) */}
          {isAuthenticated && account && (
            <div className="mx-6 my-3 flex items-center justify-between bg-gradient-to-r from-[var(--token-card-bg-start)] to-[var(--token-card-bg-end)] border border-[var(--token-card-border)] rounded-xl px-4 py-2">
              <div>
                <p className="text-xs font-mono font-semibold text-[var(--token-card-title)]">
                  {truncate(account)}
                </p>
                <p className="text-[10px] text-[var(--modal-header-subtitle)]">SEP-10 autenticado · Testnet</p>
              </div>
              <button
                onClick={handleDisconnect}
                className="text-xs text-red-400 hover:text-red-600 transition-colors font-medium"
              >
                Desconectar
              </button>
            </div>
          )}
        </div>

        {/* ── Body ───────────────────────────────────────────────────── */}
        <div className="p-6 overflow-y-auto max-h-[68vh] space-y-4">

          {/* Connect / Balance section */}
          <div>
            {!isAuthenticated ? (
              <div className="bg-gradient-to-r from-[var(--token-card-bg-start)] to-[var(--token-card-bg-end)] border border-[var(--token-card-border)] rounded-2xl p-6 text-center">
                <p className="text-sm text-[var(--modal-header-subtitle)] mb-5">
                  Conecte sua carteira Freighter para interagir com a Stellar Testnet.
                  A autenticação usa SEP-10 — nenhuma chave privada toca o backend.
                </p>
                <button
                  onClick={handleConnect}
                  disabled={isConnecting}
                  className="px-8 py-2.5 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 text-white font-semibold hover:opacity-90 disabled:opacity-50 transition-all"
                >
                  {isConnecting ? "Conectando..." : "Conectar Freighter"}
                </button>
              </div>
            ) : (
              /* Token rows — same style as My Wallet */
              <div>
                <h3 className="text-xl font-semibold text-[var(--modal-section-title)] mb-3 flex items-center gap-2">
                  💎 Your Tokens
                </h3>
                <div className="space-y-2">
                  {/* XLM row */}
                  <div className="bg-gradient-to-r from-[var(--token-card-bg-start)] to-[var(--token-card-bg-end)] rounded-xl p-4 border border-[var(--token-card-border)] hover:border-[var(--token-card-border-hover)] transition-colors">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className="w-10 h-10 rounded-lg bg-gradient-to-br from-sky-400 to-blue-500 flex items-center justify-center text-white text-base font-bold shrink-0">
                          ★
                        </span>
                        <div>
                          <p className="font-semibold text-[var(--token-card-title)]">XLM</p>
                          <p className="text-xs text-[var(--token-balance-label)]">Stellar Lumens</p>
                        </div>
                      </div>
                      <p className="font-semibold text-[var(--token-value-amount)]">
                        {isLoadingBalance
                          ? <span className="text-xs animate-pulse text-[var(--modal-header-subtitle)]">carregando...</span>
                          : balance ? `${balance.xlm.toFixed(4)}` : "—"}
                      </p>
                    </div>
                  </div>

                  {/* Asset rows (USDC, etc.) */}
                  {balance?.assets.map((asset) => (
                    <div
                      key={asset.asset_code}
                      className="bg-gradient-to-r from-[var(--token-card-bg-start)] to-[var(--token-card-bg-end)] rounded-xl p-4 border border-[var(--token-card-border)] hover:border-[var(--token-card-border-hover)] transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <span className="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-400 to-violet-400 flex items-center justify-center text-white text-xs font-bold shrink-0">
                            {asset.asset_code.slice(0, 2)}
                          </span>
                          <div>
                            <p className="font-semibold text-[var(--token-card-title)]">{asset.asset_code}</p>
                            <p className="text-xs text-[var(--token-balance-label)] font-mono">{asset.asset_issuer.slice(0, 10)}...</p>
                          </div>
                        </div>
                        <p className="font-semibold text-[var(--token-value-amount)]">{asset.balance.toFixed(4)}</p>
                      </div>
                    </div>
                  ))}

                  {balance && balance.assets.length === 0 && !isLoadingBalance && (
                    <p className="text-xs text-[var(--modal-header-subtitle)] text-center py-1">
                      Sem assets adicionais na testnet.
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* ── Swap section ─────────────────────────────────────────── */}
          {isAuthenticated && (
            <div className="bg-gradient-to-r from-[var(--token-card-bg-start)] to-[var(--token-card-bg-end)] border border-[var(--token-card-border)] rounded-2xl p-5">
              <h3 className="text-base font-semibold text-[var(--modal-section-title)] mb-3">
                Swap · Stellar DEX (Path Payments)
              </h3>

              <div className="grid grid-cols-3 gap-2 mb-3">
                <div>
                  <label className="text-xs text-[var(--token-info-label)]">De</label>
                  <select
                    value={swapFrom}
                    onChange={(e) => setSwapFrom(e.target.value as "XLM" | "USDC")}
                    className="mt-1 w-full px-2 py-1.5 rounded-lg border border-[var(--token-card-border)] bg-white/70 text-sm text-[var(--token-card-title)]"
                  >
                    <option value="XLM">XLM</option>
                    <option value="USDC">USDC</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-[var(--token-info-label)]">Quantidade</label>
                  <input
                    value={swapAmount}
                    onChange={(e) => setSwapAmount(e.target.value)}
                    className="mt-1 w-full px-2 py-1.5 rounded-lg border border-[var(--token-card-border)] bg-white/70 text-sm text-[var(--token-card-title)]"
                    placeholder="10"
                  />
                </div>
                <div>
                  <label className="text-xs text-[var(--token-info-label)]">Para</label>
                  <select
                    value={swapTo}
                    onChange={(e) => setSwapTo(e.target.value as "XLM" | "USDC")}
                    className="mt-1 w-full px-2 py-1.5 rounded-lg border border-[var(--token-card-border)] bg-white/70 text-sm text-[var(--token-card-title)]"
                  >
                    <option value="USDC">USDC</option>
                    <option value="XLM">XLM</option>
                  </select>
                </div>
              </div>

              <button
                onClick={handleGetQuote}
                disabled={isLoadingQuote}
                className="w-full py-2.5 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 hover:opacity-90 text-white font-semibold text-sm disabled:opacity-50 transition-all"
              >
                {isLoadingQuote ? "Consultando DEX..." : "Obter Quote via Stellar DEX"}
              </button>

              {swapQuote && swapQuote.destination_amount > 0 && (
                <div className="mt-3 p-3 bg-white/60 border border-[var(--token-card-border)] rounded-xl text-sm space-y-2">
                  <p className="font-semibold text-[var(--modal-section-title)]">Quote Stellar DEX</p>
                  <p className="text-[var(--token-card-title)]">
                    {swapQuote.source_amount} {swapQuote.from} →{" "}
                    <span className="font-bold">~{swapQuote.destination_amount.toFixed(4)} {swapQuote.to}</span>
                  </p>
                  <p className="text-xs text-[var(--token-info-label)]">slippage 1% · pathPaymentStrictSend</p>
                  {swapXdr && (
                    <button
                      onClick={handleSignSwap}
                      disabled={isSigningSwap}
                      className="w-full py-2 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:opacity-90 text-white font-semibold text-sm disabled:opacity-50 transition-all"
                    >
                      {isSigningSwap ? "Aguardando Freighter..." : "✦ Assinar e Executar no Freighter"}
                    </button>
                  )}
                </div>
              )}

              {swapMsg && (
                <div className={`mt-3 p-3 rounded-xl text-xs break-words ${
                  swapMsg.startsWith("Erro")
                    ? "bg-red-50 border border-red-200 text-red-700"
                    : "bg-blue-50 border border-blue-200 text-blue-700"
                }`}>
                  {swapMsg}
                </div>
              )}
            </div>
          )}

          {/* ── x402 AI Query ────────────────────────────────────────── */}
          {isAuthenticated && (
            <div className="bg-gradient-to-r from-[var(--token-card-bg-start)] to-[var(--token-card-bg-end)] border border-[var(--token-card-border)] rounded-2xl p-5">
              <h3 className="text-base font-semibold text-gray-900 mb-1">
                AI Premium · Protocolo x402
              </h3>
              <p className="text-xs text-gray-700 mb-3">
                Queries avançadas requerem micropagamento em XLM. Sem pagamento → 402 Payment Required.
              </p>

              <textarea
                value={x402Query}
                onChange={(e) => setX402Query(e.target.value)}
                placeholder="Ex: Analise meu portfólio Stellar e sugira estratégia DeFi..."
                className="w-full px-3 py-2 rounded-xl border border-[var(--token-card-border)] bg-white/70 text-sm resize-none h-20 mb-2 text-gray-900 placeholder:text-gray-500"
              />

              {x402Step && (
                <div className="mb-3 p-3 bg-indigo-50 border border-indigo-200 rounded-xl text-xs text-indigo-700 flex items-center gap-2">
                  <svg className="w-3.5 h-3.5 animate-spin text-indigo-500 shrink-0" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                  </svg>
                  <span>{x402Step}</span>
                </div>
              )}

              {x402TxHash && !x402Step && (
                <div className="mb-3 p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-700 space-y-1">
                  <p className="font-semibold">✓ Pagamento confirmado</p>
                  <p className="font-mono break-all">{x402TxHash}</p>
                </div>
              )}

              <button
                onClick={handleX402Query}
                disabled={isX402Loading}
                className="w-full py-2.5 rounded-xl bg-gradient-to-r from-purple-500 to-pink-500 hover:opacity-90 text-white font-semibold text-sm disabled:opacity-50 transition-all"
              >
                {isX402Loading ? "Aguarde..." : "Consultar AI (x402)"}
              </button>

              {x402Reply && (
                <div className="mt-3 p-3 bg-white/70 border border-[var(--token-card-border)] rounded-xl text-sm text-[var(--token-card-title)] leading-relaxed break-words">
                  {x402Reply}
                </div>
              )}

              {x402SwapXdr && (
                <button
                  onClick={handleSignX402Swap}
                  disabled={isSigningX402Swap}
                  className="mt-3 w-full py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:opacity-90 text-white font-semibold text-sm disabled:opacity-50 transition-all"
                >
                  {isSigningX402Swap ? "Aguardando Freighter..." : "✦ Assinar e Executar Swap no Freighter"}
                </button>
              )}

              {x402SwapTxHash && (
                <div className="mt-3 p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs space-y-1">
                  <p className="font-semibold text-emerald-700">✓ Swap executado na Stellar Testnet</p>
                  <p className="font-mono text-emerald-600 break-all">{x402SwapTxHash}</p>
                  <a
                    href={`https://stellar.expert/explorer/testnet/tx/${x402SwapTxHash}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-block mt-1 text-blue-600 hover:underline font-medium"
                  >
                    ↗ Ver no Stellar Expert
                  </a>
                </div>
              )}
            </div>
          )}

          {/* ── Anchor Deposit SEP-24 ────────────────────────────── */}
          {isAuthenticated && (
            <div className="bg-gradient-to-r from-[var(--token-card-bg-start)] to-[var(--token-card-bg-end)] border border-[var(--token-card-border)] rounded-2xl p-5">
              <h3 className="text-base font-semibold text-[var(--modal-section-title)] mb-1">
                Âncora · Depósito SEP-24
              </h3>
              <p className="text-xs text-[var(--modal-header-subtitle)] mb-3">
                Depósito interativo via{" "}
                <span className="font-mono font-semibold">testanchor.stellar.org</span>{" "}
                — âncora oficial SDF no testnet
              </p>

              <div className="mb-3">
                <label className="text-xs text-[var(--token-info-label)]">Asset</label>
                <select
                  value={anchorAsset}
                  onChange={(e) => setAnchorAsset(e.target.value as "SRT" | "native")}
                  className="mt-1 w-full px-2 py-1.5 rounded-lg border border-[var(--token-card-border)] bg-white/70 text-sm text-[var(--token-card-title)]"
                >
                  <option value="SRT">SRT — Stellar Reference Token</option>
                  <option value="native">XLM — Stellar Lumens</option>
                </select>
              </div>

              <button
                onClick={handleAnchorDeposit}
                disabled={anchorLoading}
                className="w-full py-2.5 rounded-xl bg-gradient-to-r from-sky-500 to-blue-600 hover:opacity-90 text-white font-semibold text-sm disabled:opacity-50 transition-all"
              >
                {anchorLoading ? "Aguardando Freighter..." : "Depositar via Âncora (SEP-24)"}
              </button>

              {anchorMsg && (
                <div className={`mt-3 p-3 rounded-xl text-xs break-words ${
                  anchorMsg.startsWith("Erro")
                    ? "bg-red-50 border border-red-200 text-red-700"
                    : "bg-blue-50 border border-blue-200 text-blue-700"
                }`}>
                  {anchorMsg}
                </div>
              )}

              {anchorResult?.url && (
                <a
                  href={anchorResult.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 flex items-center justify-center gap-2 w-full py-2 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-white text-center font-semibold text-sm transition-all"
                >
                  ↗ Abrir UI da Âncora
                </a>
              )}
            </div>
          )}

          {/* Status message */}
          {statusMsg && (
            <div className={`p-3 rounded-xl text-sm ${
              statusMsg.startsWith("Erro")
                ? "bg-red-50 border border-red-200 text-red-700"
                : "bg-blue-50 border border-blue-200 text-blue-700"
            }`}>
              {statusMsg}
            </div>
          )}
        </div>

        {/* ── Footer ─────────────────────────────────────────────────── */}
        <div className="px-6 py-3 border-t border-[var(--modal-footer-border)] bg-gradient-to-r from-[var(--modal-footer-bg-start)] to-[var(--modal-footer-bg-end)]">
          <p className="text-center text-sm text-[var(--modal-footer-text)]">
            Secured by XiaoLee · Stellar Testnet · SEP-10 · SEP-24 · x402
          </p>
        </div>
      </div>
    </div>
  );
};

export default StellarWallet;
