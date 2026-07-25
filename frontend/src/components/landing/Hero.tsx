"use client";
import { useState, useEffect, useRef } from "react";
import { useLanguage } from "@/contexts/LanguageContext";
import { useLandingT, ROTATE, APP_URL } from "./strings";
import { Reveal, CountUp, useReducedMotion, Eyebrow, XiaoleeBubble } from "./primitives";
import {
  IconSpark, IconArrow, IconPlay, IconSwap, IconRoute, IconCheck, IconShield, IconStar,
} from "./icons";

/* ---------------------------------- NAV ---------------------------------- */
export function LangToggle() {
  const { lang, setLang } = useLanguage();
  return (
    <div className="flex items-center gap-0.5 rounded-full border border-fuchsia-200/80 bg-white/70 p-0.5 shadow-sm">
      {(["en", "pt"] as const).map((l) => (
        <button key={l} onClick={() => setLang(l)} aria-pressed={lang === l}
          className={`rounded-full px-2.5 py-1 text-[12px] font-bold tracking-wide transition-all ${
            lang === l ? "btn-primary text-white" : "text-fuchsia-500/80 hover:text-fuchsia-600"
          }`}>
          {l === "en" ? "EN" : "PT"}
        </button>
      ))}
    </div>
  );
}

export function Nav() {
  const t = useLandingT();
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 12);
    fn(); window.addEventListener("scroll", fn, { passive: true });
    return () => window.removeEventListener("scroll", fn);
  }, []);
  const links = [
    { k: "nav.product", href: "#product" },
    { k: "nav.how", href: "#how" },
    { k: "nav.token", href: "#token" },
    { k: "nav.dev", href: "#dev" },
  ];
  return (
    <header className={`sticky top-0 z-50 transition-all duration-300 ${scrolled ? "py-2" : "py-3.5"}`}>
      <div className="mx-auto max-w-[1180px] px-4 sm:px-6">
        <div className={`flex items-center justify-between rounded-2xl px-3 sm:px-4 transition-all duration-300 ${scrolled ? "glass ring-soft border border-white/60 py-2" : "py-1.5"}`}>
          <a href="#top" className="flex items-center gap-2.5">
            <XiaoleeBubble size={34} />
            <span className="font-display text-[19px] font-extrabold tracking-tight text-ink">Xiao<span className="text-grad">lee</span></span>
            <IconSpark size={14} className="text-fuchsia-400 anim-floaty" />
          </a>
          <nav className="hidden items-center gap-7 md:flex">
            {links.map((l) => (
              <a key={l.k} href={l.href} className="text-[15px] font-semibold text-gray-500 transition-colors hover:text-fuchsia-600">{t(l.k)}</a>
            ))}
          </nav>
          <div className="flex items-center gap-2.5">
            <LangToggle />
            <a href={APP_URL} target="_blank" rel="noopener noreferrer"
              className="btn-primary inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-[14px] font-bold text-white">
              {t("nav.launch")} <IconArrow size={15} />
            </a>
          </div>
        </div>
      </div>
    </header>
  );
}

/* ----------------------------- HERO CHAT SIM ----------------------------- */
function TypingDots() {
  return (
    <div className="flex items-center gap-1 px-1 py-0.5">
      {[0, 1, 2].map((i) => (
        <span key={i} className="h-2 w-2 rounded-full bg-fuchsia-300"
          style={{ animation: "xlDot 1.2s infinite", animationDelay: `${i * 0.18}s` }} />
      ))}
    </div>
  );
}

function QuoteCard() {
  return (
    <div className="msg-in mt-2 rounded-2xl border border-fuchsia-100 bg-white p-3.5 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-[12px] font-bold uppercase tracking-wider text-fuchsia-500">
          <IconRoute size={15} /> Arc swap route
        </div>
        <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-bold text-emerald-600">best path</span>
      </div>
      <div className="mt-3 flex items-center justify-between gap-2">
        <div className="text-center">
          <div className="font-display text-[22px] font-extrabold leading-none text-ink">50</div>
          <div className="mt-1 text-[12px] font-semibold text-gray-400">USDC</div>
        </div>
        <div className="flex flex-1 items-center justify-center text-fuchsia-300">
          <span className="h-px flex-1 bg-fuchsia-100" /><IconSwap size={16} className="mx-1.5" /><span className="h-px flex-1 bg-fuchsia-100" />
        </div>
        <div className="text-center">
          <div className="font-display text-[22px] font-extrabold leading-none text-grad-stellar">45.90</div>
          <div className="mt-1 text-[12px] font-semibold text-gray-400">EURC</div>
        </div>
      </div>
      <div className="mt-3 flex items-center justify-between border-t border-gray-100 pt-2.5 text-[12px] text-gray-500">
        <span>Network fee</span><span className="font-mono font-semibold text-gray-700">&lt; $0.01 USDC</span>
      </div>
    </div>
  );
}

type Msg = { who: "user" | "bot"; kind: "text" | "typing" | "quote" | "confirm" | "success"; text?: string; _i?: number };

function Bubble({ m }: { m: Msg }) {
  if (m.who === "user") {
    return (
      <div className="msg-in flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-md btn-primary px-3.5 py-2.5 text-[14.5px] font-medium text-white shadow">{m.text}</div>
      </div>
    );
  }
  return (
    <div className="msg-in flex items-end gap-2">
      <XiaoleeBubble size={28} />
      <div className="max-w-[86%]">
        {m.kind === "typing" && <div className="rounded-2xl rounded-bl-md border border-fuchsia-100 bg-white px-2.5 py-2 shadow-sm"><TypingDots /></div>}
        {m.kind === "text" && <div className="rounded-2xl rounded-bl-md border border-fuchsia-100 bg-white px-3.5 py-2.5 text-[14.5px] leading-snug text-gray-700 shadow-sm">{m.text}</div>}
        {m.kind === "quote" && <QuoteCard />}
        {m.kind === "confirm" && (
          <button className="msg-in mt-2 flex w-full items-center justify-center gap-2 rounded-2xl border border-fuchsia-200 bg-fuchsia-50 px-3.5 py-2.5 text-[13.5px] font-bold text-fuchsia-600 shadow-sm transition hover:bg-fuchsia-100">
            <IconShield size={15} /> Confirm in your wallet
          </button>
        )}
        {m.kind === "success" && (
          <div className="msg-in mt-2 flex items-center gap-2 rounded-2xl rounded-bl-md border border-emerald-100 bg-emerald-50 px-3.5 py-2.5 text-[13.5px] font-semibold text-emerald-700 shadow-sm">
            <IconCheck size={16} className="shrink-0" /> Sent · 45.90 EURC landed · tx <span className="font-mono">0x3f…9b2</span>
          </div>
        )}
      </div>
    </div>
  );
}

const SCRIPT: Msg[] = [
  { who: "user", kind: "text", text: "swap 50 USDC for EURC ✨" },
  { who: "bot", kind: "typing" },
  { who: "bot", kind: "text", text: "On it! Here's your best route on Arc 💫" },
  { who: "bot", kind: "quote" },
  { who: "bot", kind: "confirm" },
  { who: "bot", kind: "typing" },
  { who: "bot", kind: "success" },
];
const DELAYS = [700, 900, 850, 700, 950, 1100, 700];

function ChatSim() {
  const reduced = useReducedMotion();
  const [n, setN] = useState(0);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (reduced) { setN(SCRIPT.length); return; }
    let timers: ReturnType<typeof setTimeout>[] = [];
    const schedule = () => {
      timers.forEach(clearTimeout); timers = [];
      let acc = 500;
      setN(0);
      SCRIPT.forEach((_, i) => { acc += DELAYS[i]; timers.push(setTimeout(() => setN(i + 1), acc)); });
      timers.push(setTimeout(() => schedule(), acc + 4200));
    };
    schedule();
    return () => timers.forEach(clearTimeout);
  }, [reduced]);

  const msgs: Msg[] = [];
  for (let i = 0; i < n; i++) {
    const m = SCRIPT[i];
    if (m.kind === "typing" && i < n - 1) continue;
    msgs.push({ ...m, _i: i });
  }
  useEffect(() => { const el = scrollRef.current; if (el) el.scrollTop = el.scrollHeight; }, [n]);

  return (
    <div className="relative">
      <div className="glass ring-soft overflow-hidden rounded-[28px] border border-white/70 shadow-2xl">
        <div className="flex items-center justify-between border-b border-fuchsia-100/70 bg-white/55 px-4 py-3">
          <div className="flex items-center gap-2.5">
            <span className="relative"><XiaoleeBubble size={36} /><span className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-white bg-emerald-400" /></span>
            <div>
              <div className="flex items-center gap-1 text-[14px] font-bold text-ink">Xiaolee <IconSpark size={11} className="text-fuchsia-400" /></div>
              <div className="text-[11px] font-medium text-emerald-500">online · Arc testnet</div>
            </div>
          </div>
          <div className="flex items-center gap-1 rounded-full bg-sky-50 px-2.5 py-1 text-[11px] font-bold text-sky-500"><IconStar size={11} /> USDC</div>
        </div>
        <div ref={scrollRef} className="flex h-[360px] flex-col justify-end gap-2.5 overflow-hidden px-4 py-4">
          {msgs.map((m) => <Bubble key={m._i} m={m} />)}
        </div>
        <div className="border-t border-fuchsia-100/70 bg-white/55 px-3 py-3">
          <div className="flex items-center gap-2 rounded-full border border-fuchsia-100 bg-white px-4 py-2.5 shadow-inner">
            <span className="flex-1 text-[14px] text-gray-400">Ask Xiaolee anything… ( ˶ˆ ꒳ ˆ˵ )</span>
            <button className="btn-primary grid h-8 w-8 place-items-center rounded-full text-white"><IconArrow size={15} /></button>
          </div>
        </div>
      </div>
      <div className="pointer-events-none absolute -right-5 -top-6 anim-floatySlow rounded-2xl border border-white/70 glass px-3 py-2 text-[12px] font-bold text-fuchsia-500 shadow-lg">no slippage math 💕</div>
      <div className="pointer-events-none absolute -bottom-5 -left-5 anim-floaty rounded-2xl border border-white/70 glass px-3 py-2 text-[12px] font-bold text-sky-500 shadow-lg" style={{ animationDelay: "1.2s" }}>keys stay with you 🔐</div>
    </div>
  );
}

/* -------------------------------- ROTATOR -------------------------------- */
function Rotator() {
  const { lang } = useLanguage();
  const reduced = useReducedMotion();
  const words = ROTATE[lang];
  const [i, setI] = useState(0);
  useEffect(() => {
    if (reduced) return;
    const id = setInterval(() => setI((x) => (x + 1) % words.length), 2200);
    return () => clearInterval(id);
  }, [reduced, words.length]);
  return <span key={`${lang}-${i}`} className="word-in inline-block text-grad">{words[i % words.length]}</span>;
}

/* --------------------------------- HERO ---------------------------------- */
export function Hero() {
  const t = useLandingT();
  return (
    <section id="top" className="relative">
      <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <IconSpark size={26} className="absolute left-[8%] top-[22%] text-fuchsia-300/70 anim-floaty" />
        <IconSpark size={16} className="absolute left-[22%] top-[64%] text-purple-300/60 anim-floatySlow" />
        <IconSpark size={20} className="absolute right-[6%] top-[58%] text-sky-300/60 anim-floaty" style={{ animationDelay: "1.5s" }} />
      </div>
      <div className="mx-auto grid max-w-[1180px] items-center gap-12 px-4 pb-8 pt-10 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:gap-8 lg:pt-16">
        <div>
          <Reveal><Eyebrow tone="stellar"><IconStar size={13} /> {t("hero.badge")}</Eyebrow></Reveal>
          <Reveal delay={1}>
            <h1 className="mt-6 font-display text-[clamp(36px,6vw,62px)] font-extrabold leading-[1.04] tracking-[-0.025em] text-ink">
              {t("hero.head.pre")}{" "}<span className="relative inline-block min-w-[5ch]"><Rotator /></span>
            </h1>
          </Reveal>
          <Reveal delay={2}><p className="mt-6 max-w-xl text-[18px] leading-relaxed text-gray-500">{t("hero.sub")}</p></Reveal>
          <Reveal delay={3}>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <a href={APP_URL} target="_blank" rel="noopener noreferrer" className="btn-primary inline-flex items-center gap-2 rounded-full px-6 py-3.5 text-[16px] font-bold text-white">{t("hero.cta1")} <IconArrow size={18} /></a>
              <a href="#product" className="inline-flex items-center gap-2 rounded-full border border-fuchsia-200 bg-white/70 px-5 py-3.5 text-[15px] font-bold text-fuchsia-600 shadow-sm transition hover:bg-white"><IconPlay size={15} /> {t("hero.cta2")}</a>
            </div>
          </Reveal>
          <Reveal delay={4}>
            <div className="mt-7 flex items-center gap-2 text-[13.5px] font-semibold text-gray-400"><IconShield size={16} className="text-emerald-500" /> {t("hero.trust")}</div>
          </Reveal>
        </div>
        <Reveal delay={2}><ChatSim /></Reveal>
      </div>
    </section>
  );
}

/* ----------------------------- METRICS STRIP ----------------------------- */
export function Metrics() {
  const stats = [
    { to: 100, suffix: "%", label: "Non-custodial by design", sub: "your keys sign every tx" },
    { to: 40, suffix: "×", label: "Lower fees", sub: "vs. legacy creator payouts" },
    { to: 3, suffix: "", label: "Channels", sub: "X · Telegram · Web" },
    { to: 2, suffix: "", label: "Languages", sub: "EN & PT, auto-detected" },
  ];
  return (
    <section className="mx-auto max-w-[1180px] px-4 py-10 sm:px-6">
      <Reveal>
        <div className="glass ring-soft grid grid-cols-2 gap-y-7 rounded-3xl border border-white/70 px-6 py-8 md:grid-cols-4 md:gap-0">
          {stats.map((s, i) => (
            <div key={i} className={`px-2 text-center ${i ? "md:border-l md:border-fuchsia-100" : ""}`}>
              <div className="font-display text-[clamp(30px,4vw,44px)] font-extrabold leading-none text-grad"><CountUp to={s.to} suffix={s.suffix} /></div>
              <div className="mt-2 text-[14px] font-bold text-ink">{s.label}</div>
              <div className="mt-0.5 text-[12.5px] text-gray-400">{s.sub}</div>
            </div>
          ))}
        </div>
      </Reveal>
    </section>
  );
}
