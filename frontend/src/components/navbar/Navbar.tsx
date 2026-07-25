import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { toast } from 'react-toastify';
import {
  IconSpark,
  IconChevronDown,
  IconUser,
  IconRocket,
  IconBell,
  IconBarChart,
  IconDollar,
  IconWallet,
  IconClipboard,
  IconClock,
  IconLink,
  IconDownload,
  IconUpload,
  IconLogout,
} from "@/components/icons";
import Transacoes from "./Transacoes";
import Historico from "./Historico";
import Wallet from "./Wallet";
import WalletConnect from "./WalletConnect";
import { TypeUserData } from "@/interfaces";
import UserData from "../UserData";
import dynamic from "next/dynamic";
import TelegramLoginButton from "../TelegramLoginButton";
import { useLanguage, Language } from "@/contexts/LanguageContext";
import { clearWeb3AuthProvider } from "@/lib/web3authProvider";

const Web3AuthButton = dynamic(() => import("../Web3AuthButton"), { ssr: false });

function LangToggle() {
  const { lang, setLang } = useLanguage();
  return (
    <>
      {/* Very narrow screens: single button showing the current language; tap switches */}
      <button
        onClick={() => setLang(lang === "en" ? "pt" : "en")}
        aria-label="Switch language"
        className="min-[400px]:hidden shrink-0 px-2 py-1 rounded-lg text-xs font-bold uppercase tracking-wider bg-[var(--accent)] text-white shadow-sm transition-all duration-200 active:scale-95"
      >
        {lang === "en" ? "EN" : "PT"}
      </button>

      <div className="hidden min-[400px]:flex items-center gap-0.5 bg-black/5 border border-[var(--navbar-border)] rounded-xl p-0.5 shrink-0">
        {(["en", "pt"] as Language[]).map((l) => (
          <button
            key={l}
            onClick={() => setLang(l)}
            className={`px-1.5 sm:px-2.5 py-1 rounded-lg text-xs font-bold uppercase tracking-wider transition-all duration-200 ${
              lang === l
                ? "bg-[var(--accent)] text-white shadow-sm"
                : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-black/5"
            }`}
          >
            {l === "en" ? "EN" : "PT"}
          </button>
        ))}
      </div>
    </>
  );
}

export default function Navbar() {
  const { t } = useLanguage();
  const [userData, setUserData] = useState<TypeUserData | null>(null);
  const [isUserDataLoaded, setIsUserDataLoaded] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [showTelegramLogin, setShowTelegramLogin] = useState(false);
  const [shouldOpenTransactions, setShouldOpenTransactions] = useState(false);
  const [shouldOpenHistory, setShouldOpenHistory] = useState(false);
  const [shouldOpenWallet, setShouldOpenWallet] = useState(false);
  const [shouldOpenEvmWallet, setShouldOpenEvmWallet] = useState(false);
  const pathname = usePathname();

  
  const handleTransactionClick = () => {
    console.log("🔍 Transaction button clicked");
    setShouldOpenTransactions(true);
    setIsDropdownOpen(false);
  };

  const handleHistoryClick = () => {
    console.log("🔍 History button clicked");
    setShouldOpenHistory(true);
    setIsDropdownOpen(false);
  };

  const handleWalletClick = () => {
    console.log("💰 Wallet button clicked");
    setShouldOpenWallet(true);
    setIsDropdownOpen(false);
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    // Verificar se estamos no lado do cliente
    if (typeof window === 'undefined' || typeof document === 'undefined') return;
    
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Element;
      if (target && !target.closest('[data-dropdown]')) {
        setIsDropdownOpen(false);
      }
    };

    if (isDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isDropdownOpen]);
 

  const handleLogout = () => {
    clearWeb3AuthProvider();
    UserData.clearData();
    UserData.getOrCreateDevnetSession();
    const freshData = UserData.getUserData();
    setUserData(freshData);
    setIsDropdownOpen(false);
    toast.success(t('navbar.logged_out'));
  };

  useEffect(() => {
    if (typeof window === 'undefined') return;

    // Try to restore full session (user_info + wallet) from localStorage first
    const restored = UserData.restoreSession();
    if (!restored) {
      // No saved session — create or load existing guest/wallet session
      UserData.getOrCreateDevnetSession();
    }

    const currentData = UserData.getUserData();
    if (currentData?.user_info?.twitter_user_id) {
      setUserData(currentData);
      setIsUserDataLoaded(true);
    }

    const handleUserDataLoaded = (event: Event) => {
      const customEvent = event as CustomEvent<TypeUserData>;
      setUserData(customEvent.detail);
      setIsUserDataLoaded(true);
    };

    window.addEventListener('userDataLoaded', handleUserDataLoaded);
    return () => window.removeEventListener('userDataLoaded', handleUserDataLoaded);
  }, []);

  return (
    <>
      <nav className="bg-gradient-to-r from-[var(--navbar-bg-start)] via-[var(--navbar-bg-middle)] to-[var(--navbar-bg-end)] backdrop-blur-sm border-b border-[var(--navbar-border)] shadow-sm px-2 py-2.5 sm:p-3 md:p-4 sticky top-0 z-20 overflow-visible">
        <div className="container mx-auto flex justify-between items-center relative z-[10000] gap-1.5 sm:gap-2">
          <div className="flex items-center shrink-0">
            {/* Logo — mesmo da landing: "Xiao" escuro + "lee" no acento + faísca */}
            <Link href="/" className="flex items-center gap-1 hover:scale-105 transition-transform whitespace-nowrap">
              <span
                className="text-2xl md:text-[32px] text-[var(--text-primary)]"
                style={{ fontFamily: "var(--font-candice), cursive" }}
              >
                Xiao<span style={{ color: "#d81b78" }}>lee</span>
              </span>
              <IconSpark size={13} className="text-[var(--accent)] -translate-y-1.5" />
            </Link>
          </div>
          
          <div className="flex items-center justify-end flex-1 gap-0.5 sm:gap-1 md:gap-3">
            {/* Navigation — quiet links with palette accents; Dashboard is the single primary CTA */}
            <div className="flex items-center gap-0.5 sm:gap-1 md:gap-1.5">
              <Link
                href="/campaigns"
                className={`inline-flex items-center justify-center gap-x-0 sm:gap-x-1.5 rounded-lg md:rounded-xl px-0 sm:px-3 md:px-4 text-[11px] md:text-sm font-semibold transition-colors duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(216,27,120,0.4)] active:scale-95 w-7 h-7 min-[360px]:w-8 min-[360px]:h-8 sm:w-auto sm:h-10 md:h-11 ${
                  pathname === '/campaigns'
                    ? 'bg-white text-[var(--text-primary)] shadow-e1'
                    : 'text-[var(--text-secondary)] hover:bg-black/5 hover:text-[var(--text-primary)]'
                }`}
              >
                <IconRocket className="w-4 h-4 md:w-[18px] md:h-[18px] shrink-0" />
                <span className="hidden lg:inline">{t('navbar.campaigns')}</span>
              </Link>

              <Link
                href="/traction"
                className={`inline-flex items-center justify-center gap-x-0 sm:gap-x-1.5 rounded-lg md:rounded-xl px-0 sm:px-3 md:px-4 text-[11px] md:text-sm font-semibold transition-colors duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(216,27,120,0.4)] active:scale-95 w-7 h-7 min-[360px]:w-8 min-[360px]:h-8 sm:w-auto sm:h-10 md:h-11 ${
                  pathname === '/traction'
                    ? 'bg-white text-[var(--text-primary)] shadow-e1'
                    : 'text-[var(--text-secondary)] hover:bg-black/5 hover:text-[var(--text-primary)]'
                }`}
              >
                <IconDollar className="w-4 h-4 md:w-[18px] md:h-[18px] shrink-0" />
                <span className="hidden lg:inline">Traction</span>
              </Link>

              <Link
                href="/notifications"
                title={t('navbar.notifications')}
                aria-label={t('navbar.notifications')}
                className={`inline-flex items-center justify-center rounded-lg md:rounded-xl transition-colors duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(216,27,120,0.4)] active:scale-95 w-7 h-7 min-[360px]:w-8 min-[360px]:h-8 sm:h-10 sm:w-10 md:h-11 md:w-11 ${
                  pathname === '/notifications'
                    ? 'bg-white text-[var(--text-primary)] shadow-e1'
                    : 'text-[var(--text-secondary)] hover:bg-black/5 hover:text-[var(--text-primary)]'
                }`}
              >
                <IconBell className="w-4 h-4 md:w-5 md:h-5 shrink-0" />
              </Link>

              <Link
                href="/dashboard"
                className={`inline-flex items-center justify-center gap-x-0 sm:gap-x-1.5 md:gap-x-2 rounded-lg md:rounded-xl btn-primary px-0 sm:px-3 md:px-5 text-[11px] md:text-sm font-bold text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(216,27,120,0.4)] active:scale-95 w-7 h-7 min-[360px]:w-8 min-[360px]:h-8 sm:w-auto sm:h-10 md:h-11 ${pathname === '/dashboard' ? 'ring-2 ring-[rgba(216,27,120,0.3)]' : ''}`}
              >
                <IconBarChart className="w-4 h-4 md:w-[18px] md:h-[18px] shrink-0" />
                <span className="hidden sm:inline lg:hidden whitespace-nowrap">{t('navbar.dashboard').slice(0,4)}</span>
                <span className="hidden lg:inline">{t('navbar.dashboard')}</span>
              </Link>
            </div>

            {/* Show user dropdown only when data is loaded */}
            {isUserDataLoaded && userData ? (
              <div className="relative" data-dropdown>
                <button
                  onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                  className="inline-flex items-center justify-center gap-x-0 sm:gap-x-1.5 md:gap-x-2 rounded-lg md:rounded-xl bg-white border border-[var(--navbar-border)] px-0 sm:px-3 md:px-4 text-[11px] md:text-sm font-semibold text-[var(--text-primary)] hover:bg-black/5 transition-colors duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(216,27,120,0.4)] backdrop-blur-sm active:scale-95 w-7 h-7 min-[360px]:w-8 min-[360px]:h-8 sm:w-auto sm:h-10 md:h-11"
                >
                  <div className="w-5 h-5 md:w-6 md:h-6 bg-[var(--accent)] text-white rounded-full flex items-center justify-center shrink-0">
                    <IconUser className="h-3 w-3 md:h-3.5 md:w-3.5" sw={2.2} />
                  </div>
                  <span className="hidden lg:inline">
                    {userData.session_id?.startsWith('devnet_guest_')
                      ? 'Guest'
                      : userData.user_info?.twitter_handle
                        ? `@${userData.user_info.twitter_handle.slice(0, 12)}`
                        : 'User'}
                  </span>
                  <IconChevronDown
                    sw={2.2}
                    className={`hidden sm:block h-3 w-3 md:h-4 md:w-4 shrink-0 transition-transform duration-200 ${
                      isDropdownOpen ? 'rotate-180' : ''
                    }`}
                  />
                </button>
                    
                {/* Dropdown Menu */}
                {isDropdownOpen && (
                <div className="absolute z-50 right-0 mt-2 w-56 md:w-64 origin-top-right rounded-2xl bg-white border border-[var(--border)] shadow-e3 overflow-hidden transition-all duration-200 animate-in fade-in-0 zoom-in-95">                    
                    {/* User Info Section */}
                    <div className="px-4 py-3 border-b border-[var(--navbar-border)]/30 backdrop-blur-sm">
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-[var(--accent)] rounded-full flex items-center justify-center text-white font-bold">
                          {userData.user_info?.twitter_handle?.charAt(0).toUpperCase() || 'U'}
                        </div>
                        <div>
                          <div className="font-semibold text-[var(--navbar-text-gradient-start)] text-sm">
                            @{userData.user_info?.twitter_handle || 'Usuario'}
                          </div>
                          <div className="text-xs text-[var(--navbar-text-gradient-middle)]/80">
                            ID: {userData.user_info?.twitter_user_id?.slice(0, 8)}...
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Menu Items */}
                    <div className="py-2">
                      <div
                        onClick={() => {
                          handleWalletClick();
                        }}
                        className="group flex w-full items-center px-4 py-3 text-sm font-medium text-[var(--navbar-text-gradient-start)] hover:bg-[var(--accent-soft)] transition-all duration-200 cursor-pointer"
                      >
                        <div className="mr-3 text-lg bg-[var(--accent-soft)] text-[var(--accent)] w-7 h-7 min-[360px]:w-8 min-[360px]:h-8 rounded-lg flex items-center justify-center">
                          <IconWallet className="w-5 h-5" />
                        </div>
                        <div className="text-left">
                          <div className="font-semibold">Wallet</div>
                          <div className="text-xs text-[var(--navbar-text-gradient-middle)]/70">View token balance</div>
                        </div>
                      </div>

                      <div
                        onClick={() => {
                          handleTransactionClick();
                        }}
                        className="group flex w-full items-center px-4 py-3 text-sm font-medium text-[var(--navbar-text-gradient-start)] hover:bg-[var(--accent-soft)] transition-all duration-200 cursor-pointer"
                      >
                        <div className="mr-3 text-lg bg-[var(--accent-soft)] text-[var(--accent)] w-7 h-7 min-[360px]:w-8 min-[360px]:h-8 rounded-lg flex items-center justify-center">
                          <IconClipboard className="w-5 h-5" />
                        </div>
                        <div className="text-left">
                          <div className="font-semibold">Transactions</div>
                          <div className="text-xs text-[var(--navbar-text-gradient-middle)]/70">View swap history</div>
                        </div>
                      </div>
                      
                      <div
                        onClick={() => {
                          handleHistoryClick();
                        }}
                        className="group flex w-full items-center px-4 py-3 text-sm font-medium text-[var(--navbar-text-gradient-start)] hover:bg-[var(--accent-soft)] transition-all duration-200 cursor-pointer"
                      >
                        <div className="mr-3 text-lg bg-[var(--accent-soft)] text-[var(--accent)] w-7 h-7 min-[360px]:w-8 min-[360px]:h-8 rounded-lg flex items-center justify-center">
                          <IconClock className="w-5 h-5" />
                        </div>
                        <div className="text-left">
                          <div className="font-semibold">History</div>
                          <div className="text-xs text-[var(--navbar-text-gradient-middle)]/70">View conversations and activities</div>
                        </div>
                      </div>

                      {/* Wallet Connect — qualquer wallet compatível (EVM/Solana/Stellar) */}
                      <div
                        onClick={() => {
                          setShouldOpenEvmWallet(true);
                          setIsDropdownOpen(false);
                        }}
                        className="group flex w-full items-center px-4 py-3 text-sm font-medium text-[var(--navbar-text-gradient-start)] hover:bg-[var(--accent-soft)] transition-all duration-200 cursor-pointer"
                      >
                        <div className="mr-3 text-lg bg-[var(--accent-soft)] text-[var(--accent)] w-7 h-7 min-[360px]:w-8 min-[360px]:h-8 rounded-lg flex items-center justify-center">
                          <IconLink className="w-5 h-5" />
                        </div>
                        <div className="text-left">
                          <div className="font-semibold">Connect Wallet</div>
                          <div className="text-xs text-[var(--navbar-text-gradient-middle)]/70">Arc · Solana · Stellar · USDC</div>
                        </div>
                      </div>

                      {/* Separator */}
                      <div className="border-t border-[var(--navbar-border)]/30 my-2"></div>

                      {/* Login options — shown for non-Telegram and non-Google sessions */}
                      {!userData.session_id?.startsWith('tg_session_') && !userData.session_id?.startsWith('google_session_') && (
                        <div className="px-4 py-3 flex flex-col gap-2">
                          {/* Telegram login */}
                          {showTelegramLogin ? (
                            <div className="flex flex-col items-center gap-2">
                              <p className="text-xs text-[var(--navbar-text-gradient-middle)]/80 text-center">
                                Authorize in Telegram to link your account
                              </p>
                              <TelegramLoginButton
                                onSuccess={() => {
                                  setShowTelegramLogin(false);
                                  setIsDropdownOpen(false);
                                  toast.success("Telegram account linked!");
                                }}
                                onError={() => toast.error("Telegram login failed")}
                              />
                            </div>
                          ) : (
                            <button
                              onClick={() => setShowTelegramLogin(true)}
                              className="w-full flex items-center gap-3 px-3 py-2 rounded-xl bg-[#2AABEE] text-white text-sm font-semibold shadow hover:bg-[#229ED9] transition-all"
                            >
                              <svg className="w-5 h-5 shrink-0" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.894 8.221-1.97 9.28c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12l-6.871 4.326-2.962-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.833.941z"/>
                              </svg>
                              Login com Telegram
                            </button>
                          )}

                          {/* Google / Web3Auth login */}
                          <Web3AuthButton
                            onSuccess={() => {
                              setIsDropdownOpen(false);
                              toast.success("Google account linked!");
                            }}
                            onError={() => toast.error("Google login failed")}
                          />
                        </div>
                      )}

                      {/* Separator before financial actions */}
                      <div className="border-t border-[var(--navbar-border)]/30 my-2"></div>

                      {/* Withdraw Button */}
                      <div
                        onClick={(e) => {
                          e.preventDefault();
                          handleWalletClick();
                        }}
                        className="group flex w-full items-center px-4 py-3 text-sm font-medium text-[var(--navbar-text-gradient-start)] hover:bg-[var(--accent-soft)] transition-all duration-200 cursor-pointer"
                      >
                        <div className="mr-3 text-lg bg-[var(--accent-soft)] text-[var(--accent)] w-7 h-7 min-[360px]:w-8 min-[360px]:h-8 rounded-lg flex items-center justify-center">
                          <IconDownload className="w-5 h-5" />
                        </div>
                        <div className="text-left">
                          <div className="font-semibold">Withdraw</div>
                          <div className="text-xs text-[var(--navbar-text-gradient-middle)]/70">Withdraw funds to wallet</div>
                        </div>
                      </div>

                      {/* Deposit Button */}
                      <div
                        onClick={(e) => {
                          e.preventDefault();
                          handleWalletClick();
                        }}
                        className="group flex w-full items-center px-4 py-3 text-sm font-medium text-[var(--navbar-text-gradient-start)] hover:bg-[var(--accent-soft)] transition-all duration-200 cursor-pointer"
                      >
                        <div className="mr-3 text-lg bg-[var(--accent-soft)] text-[var(--accent)] w-7 h-7 min-[360px]:w-8 min-[360px]:h-8 rounded-lg flex items-center justify-center">
                          <IconUpload className="w-5 h-5" />
                        </div>
                        <div className="text-left">
                          <div className="font-semibold">Deposit</div>
                          <div className="text-xs text-[var(--navbar-text-gradient-middle)]/70">Add funds to account</div>
                        </div>
                      </div>
                    </div>

                    {/* Logout — only for authenticated (non-guest) sessions */}
                    {userData.session_id && !userData.session_id.startsWith('devnet_guest_') && (
                      <>
                        <div className="border-t border-[var(--navbar-border)]/30 my-2" />
                        <div
                          onClick={handleLogout}
                          className="group flex w-full items-center px-4 py-3 text-sm font-medium text-red-500 hover:bg-red-50/30 backdrop-blur-sm transition-all duration-200 cursor-pointer"
                        >
                          <div className="mr-3 bg-red-100 dark:bg-red-900/50 text-red-500 w-7 h-7 min-[360px]:w-8 min-[360px]:h-8 rounded-lg flex items-center justify-center">
                            <IconLogout className="w-4 h-4" />
                          </div>
                          <div className="text-left">
                            <div className="font-semibold">{t('navbar.logout')}</div>
                            <div className="text-xs text-red-400/70">{t('navbar.logout_sub')}</div>
                          </div>
                        </div>
                      </>
                    )}

                    {/* Footer with session info */}
                    <div className="px-4 py-2 border-t border-[var(--navbar-border)]/30 backdrop-blur-sm">
                      <div className="flex items-center justify-between text-xs text-[var(--navbar-text-gradient-middle)]/80">
                        <span>✨ Online</span>
                        {userData.session_id && (
                          <span>Session: {userData.session_id.slice(0, 6)}...</span>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <></>
            )}
            
            <LangToggle />
            {/* ThemeToggle suspenso — só tema claro até a paleta escura ficar pronta */}
          </div>
        </div>

      </nav>
      
     
        <>
          {shouldOpenTransactions ? (
            <Transacoes
              transactions={UserData.getTransactionHistory()}
              balance={userData?.balances}
              shouldOpen={shouldOpenTransactions}
              onClose={() => setShouldOpenTransactions(false)}
            />
          ): null }
        
          {shouldOpenHistory ?
            <Historico 
              shouldOpen={shouldOpenHistory}
              onClose={() => setShouldOpenHistory(false)}
            />
          : null}

          {shouldOpenWallet ?
            <Wallet
              balance={userData?.balances}
              shouldOpen={shouldOpenWallet}
              onClose={() => setShouldOpenWallet(false)}
              onRequestConnect={() => setShouldOpenEvmWallet(true)}
            />
          : null}

          {shouldOpenEvmWallet ?
            <WalletConnect
              shouldOpen={shouldOpenEvmWallet}
              onClose={() => setShouldOpenEvmWallet(false)}
            />
          : null}
        </>
      
    </>
  );
}
