"use client";
import type { CSSProperties, ReactNode } from "react";

export type IconProps = {
  size?: number;
  sw?: number;
  className?: string;
  style?: CSSProperties;
  fill?: string;
};

function Svg({ children, size = 24, sw = 1.8, fill = "none", className, style }: IconProps & { children: ReactNode }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill={fill} stroke="currentColor"
      strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" className={className} style={style}>
      {children}
    </svg>
  );
}

// ── Landing icons (original) ─────────────────────────────────────────────────
export const IconChat    = (p: IconProps) => <Svg {...p}><path d="M21 11.5a8.38 8.38 0 0 1-8.5 8.5 8.5 8.5 0 0 1-3.8-.9L3 21l1.9-5.7a8.5 8.5 0 0 1-.9-3.8A8.38 8.38 0 0 1 12.5 3 8.38 8.38 0 0 1 21 11.5z"/></Svg>;
export const IconSwap    = (p: IconProps) => <Svg {...p}><path d="M7 10l-3 3 3 3"/><path d="M4 13h13a3 3 0 0 0 3-3V7"/><path d="M17 14l3-3-3-3"/><path d="M20 11H7a3 3 0 0 0-3 3v3"/></Svg>;
export const IconSend    = (p: IconProps) => <Svg {...p}><path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4 20-7z"/></Svg>;
export const IconGift    = (p: IconProps) => <Svg {...p}><path d="M20 12v9H4v-9"/><path d="M2 7h20v5H2z"/><path d="M12 22V7"/><path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z"/><path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"/></Svg>;
export const IconBolt    = (p: IconProps) => <Svg {...p}><path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/></Svg>;
export const IconShield  = (p: IconProps) => <Svg {...p}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></Svg>;
export const IconSpark   = (p: IconProps) => <Svg {...p} fill="currentColor" sw={0}><path d="M12 2l1.6 5.6L19 9.2l-5.4 1.6L12 16l-1.6-5.2L5 9.2l5.4-1.6L12 2z"/></Svg>;
export const IconGlobe   = (p: IconProps) => <Svg {...p}><circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3c2.5 2.6 2.5 15.4 0 18-2.5-2.6-2.5-15.4 0-18z"/></Svg>;
export const IconTarget  = (p: IconProps) => <Svg {...p}><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none"/></Svg>;
export const IconCheck   = (p: IconProps) => <Svg {...p}><path d="M20 6 9 17l-5-5"/></Svg>;
export const IconWallet  = (p: IconProps) => <Svg {...p}><path d="M3 7a2 2 0 0 1 2-2h13v4"/><path d="M3 7v10a2 2 0 0 0 2 2h15V9H5a2 2 0 0 1-2-2z"/><circle cx="16.5" cy="14" r="1.2" fill="currentColor" stroke="none"/></Svg>;
export const IconCoin    = (p: IconProps) => <Svg {...p}><circle cx="12" cy="12" r="9"/><path d="M12 7v10M9.5 9.2c0-1.2 1.1-1.9 2.5-1.9s2.5.7 2.5 1.9-1.1 1.7-2.5 1.7-2.5.6-2.5 1.8 1.1 1.9 2.5 1.9 2.5-.7 2.5-1.9"/></Svg>;
export const IconLock    = (p: IconProps) => <Svg {...p}><rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></Svg>;
export const IconCpu     = (p: IconProps) => <Svg {...p}><rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 1v3M15 1v3M9 20v3M15 20v3M1 9h3M1 15h3M20 9h3M20 15h3"/><rect x="10" y="10" width="4" height="4" rx="1"/></Svg>;
export const IconStar    = (p: IconProps) => <Svg {...p} fill="currentColor" sw={0}><path d="M12 2l2.6 6.9L22 9.6l-5.5 4.7L18.2 22 12 18.1 5.8 22l1.7-7.7L2 9.6l7.4-.7L12 2z"/></Svg>;
export const IconRoute   = (p: IconProps) => <Svg {...p}><circle cx="6" cy="19" r="2.5"/><circle cx="18" cy="5" r="2.5"/><path d="M8.5 19H14a4 4 0 0 0 0-8H9a4 4 0 0 1 0-8h6.5"/></Svg>;
export const IconArrow   = (p: IconProps) => <Svg {...p}><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></Svg>;
export const IconPlay    = (p: IconProps) => <Svg {...p}><path d="M7 5l12 7-12 7V5z" fill="currentColor" stroke="none"/></Svg>;
export const IconLayers  = (p: IconProps) => <Svg {...p}><path d="m12 2 9 5-9 5-9-5 9-5z"/><path d="m3 12 9 5 9-5"/><path d="m3 17 9 5 9-5"/></Svg>;
export const IconX       = ({ size = 20 }: IconProps) => <svg viewBox="0 0 24 24" width={size} height={size} fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24h-6.66l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231 5.45-6.231zm-1.161 17.52h1.833L7.084 4.126H5.117l11.966 15.644z"/></svg>;
export const IconTelegram = ({ size = 20 }: IconProps) => <svg viewBox="0 0 24 24" width={size} height={size} fill="currentColor"><path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/></svg>;
export const IconGithub  = ({ size = 20 }: IconProps) => <svg viewBox="0 0 24 24" width={size} height={size} fill="currentColor"><path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/></svg>;
export const IconDiscord = ({ size = 20 }: IconProps) => <svg viewBox="0 0 24 24" width={size} height={size} fill="currentColor"><path d="M20.317 4.369a19.79 19.79 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.1 13.1 0 0 1-1.872-.892.077.077 0 0 1-.008-.128c.126-.094.252-.192.372-.291a.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.009c.12.099.246.198.373.292a.077.077 0 0 1-.006.127 12.3 12.3 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.84 19.84 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.06.06 0 0 0-.031-.028zM8.02 15.331c-1.182 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/></svg>;

// ── App icons ────────────────────────────────────────────────────────────────
export const IconUser      = (p: IconProps) => <Svg {...p}><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></Svg>;
export const IconUsers     = (p: IconProps) => <Svg {...p}><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></Svg>;
export const IconUserPlus  = (p: IconProps) => <Svg {...p}><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/></Svg>;
export const IconDollar    = (p: IconProps) => <Svg {...p}><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></Svg>;
export const IconZap       = (p: IconProps) => <Svg {...p}><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></Svg>;
export const IconActivity  = (p: IconProps) => <Svg {...p}><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></Svg>;
export const IconTrendingUp = (p: IconProps) => <Svg {...p}><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></Svg>;
export const IconAward     = (p: IconProps) => <Svg {...p}><circle cx="12" cy="8" r="6"/><path d="M15.477 12.89L17 22l-5-3-5 3 1.523-9.11"/></Svg>;
export const IconWifi      = (p: IconProps) => <Svg {...p}><path d="M5 12.55a11 11 0 0 1 14.08 0"/><path d="M1.42 9a16 16 0 0 1 21.16 0"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><line x1="12" y1="20" x2="12.01" y2="20"/></Svg>;
export const IconInbox     = (p: IconProps) => <Svg {...p}><polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/></Svg>;

// ── Navbar + Campaigns (consolidado 2026-07 — substitui Heroicons/SVG inline/emoji duplicados) ──
export const IconClipboard = (p: IconProps) => <Svg {...p}><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><path d="M9 5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2 2 2 0 0 1-2 2H11a2 2 0 0 1-2-2z"/><path d="M9 12h6M9 16h6M9 9h.01"/></Svg>;
export const IconClock     = (p: IconProps) => <Svg {...p}><circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15.5 14"/></Svg>;
export const IconLink      = (p: IconProps) => <Svg {...p}><path d="M10 14a5 5 0 0 0 7.07 0l2.83-2.83a5 5 0 1 0-7.07-7.07L11.5 5.5"/><path d="M14 10a5 5 0 0 0-7.07 0L4.1 12.83a5 5 0 1 0 7.07 7.07L12.5 18.5"/></Svg>;
export const IconDownload  = (p: IconProps) => <Svg {...p}><path d="M4 16v1a3 3 0 0 0 3 3h10a3 3 0 0 0 3-3v-1"/><path d="M12 4v12m0 0-4-4m4 4 4-4"/></Svg>;
export const IconUpload    = (p: IconProps) => <Svg {...p}><path d="M4 16v1a3 3 0 0 0 3 3h10a3 3 0 0 0 3-3v-1"/><path d="M12 16V4m0 0 4 4m-4-4-4 4"/></Svg>;
export const IconLogout    = (p: IconProps) => <Svg {...p}><path d="M17 16l4-4m0 0-4-4m4 4H7"/><path d="M13 20v1a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3V7a3 3 0 0 1 3-3h4a3 3 0 0 1 3 3v1"/></Svg>;
export const IconRocket    = (p: IconProps) => <Svg {...p}><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="M12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 19 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/></Svg>;
export const IconBarChart  = (p: IconProps) => <Svg {...p}><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></Svg>;
export const IconChevronDown  = (p: IconProps) => <Svg {...p}><polyline points="6 9 12 15 18 9"/></Svg>;
export const IconChevronLeft  = (p: IconProps) => <Svg {...p}><polyline points="15 18 9 12 15 6"/></Svg>;
export const IconChevronRight = (p: IconProps) => <Svg {...p}><polyline points="9 18 15 12 9 6"/></Svg>;
export const IconBell      = (p: IconProps) => <Svg {...p}><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></Svg>;
export const IconClose     = (p: IconProps) => <Svg {...p}><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></Svg>;
export const IconPlus      = (p: IconProps) => <Svg {...p}><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></Svg>;
export const IconAlert     = (p: IconProps) => <Svg {...p}><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></Svg>;
export const IconMegaphone = (p: IconProps) => <Svg {...p}><path d="M3 11l19-9-9 19-2-8-8-2z"/></Svg>;
export const IconReceipt   = (p: IconProps) => <Svg {...p}><path d="M14 2H6a2 2 0 0 0-2 2v16l3-2 2 2 2-2 2 2 2-2 3 2V4a2 2 0 0 0-2-2z"/></Svg>;
export const IconRefresh   = (p: IconProps) => <Svg {...p}><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></Svg>;
export const IconList      = (p: IconProps) => <Svg {...p}><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></Svg>;
