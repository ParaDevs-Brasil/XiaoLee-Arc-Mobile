"use client";
// Landing copy (EN/PT). Reuses the global language from useLanguage() but keeps
// landing strings local so you don't have to touch src/locales/*.json.
import { useLanguage } from "@/contexts/LanguageContext";

type Dict = Record<string, string>;

export const LANDING_STRINGS: Record<"en" | "pt", Dict> = {
  en: {
    "nav.product": "Product",
    "nav.how": "How it works",
    "nav.token": "$XLEE",
    "nav.dev": "Developers",
    "nav.launch": "Launch app",

    "hero.badge": "AI ops layer · built on Arc",
    "hero.head.pre": "Just talk. Xiaolee handles the",
    "hero.sub": "Xiaolee is a conversational AI agent for the USDC economy on Arc. Swap, send, earn and cash in via Pix — in plain language. No wallets to configure, no slippage to learn. You confirm, your keys sign.",
    "hero.cta1": "Launch app",
    "hero.cta2": "See it talk",
    "hero.trust": "Non-custodial · Arc · Circle · x402",

    "cta.eyebrow": "Ready when you are",
    "cta.head": "Talk to your money.",
    "cta.sub": "Connect your wallet and say hi. Xiaolee speaks your language — literally — and never touches your keys.",
    "cta.btn": "Launch Xiaolee",

    "footer.tag": "The conversational interface for USDC on Arc — with native Pix for the creator economy.",
    "footer.rights": "Devnet · Testnet demo · Not investment advice. Xiaolee is non-custodial: your keys never touch our servers.",
  },
  pt: {
    "nav.product": "Produto",
    "nav.how": "Como funciona",
    "nav.token": "$XLEE",
    "nav.dev": "Desenvolvedores",
    "nav.launch": "Abrir app",

    "hero.badge": "camada de IA · feito no Arc",
    "hero.head.pre": "É só falar. A Xiaolee cuida dos",
    "hero.sub": "A Xiaolee é uma agente de IA conversacional para a economia USDC no Arc. Faça swap, envie, ganhe e saque por Pix — em linguagem natural. Sem configurar carteira, sem entender slippage. Você confirma, sua chave assina.",
    "hero.cta1": "Abrir app",
    "hero.cta2": "Ver conversando",
    "hero.trust": "Não-custodial · Arc · Circle · x402",

    "cta.eyebrow": "Quando você quiser",
    "cta.head": "Converse com seu dinheiro.",
    "cta.sub": "Conecte sua carteira e diga oi. A Xiaolee fala a sua língua — de verdade — e nunca toca nas suas chaves.",
    "cta.btn": "Abrir a Xiaolee",

    "footer.tag": "A interface conversacional para USDC no Arc — com Pix nativo para a economia de criadores.",
    "footer.rights": "Devnet · Demo testnet · Não é recomendação de investimento. A Xiaolee é não-custodial: suas chaves nunca tocam nossos servidores.",
  },
};

export const ROTATE: Record<"en" | "pt", string[]> = {
  en: ["swaps.", "campaigns.", "Pix deposits.", "payouts.", "trustlines."],
  pt: ["swaps.", "campanhas.", "depósitos Pix.", "pagamentos.", "trustlines."],
};

export const APP_URL = "https://xiaolee-frontend-production-96d7.up.railway.app";

export function useLandingT() {
  const { lang } = useLanguage();
  return (key: string): string =>
    LANDING_STRINGS[lang]?.[key] ?? LANDING_STRINGS.en[key] ?? key;
}
