"use client";
import { useState, useEffect, useRef } from "react";
import type { ReactNode, CSSProperties } from "react";
import avatar from "@/assets/animeGirl.png";
import { IconSpark } from "./icons";

export function useReducedMotion(): boolean {
  const [r, setR] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const fn = () => setR(mq.matches);
    fn();
    mq.addEventListener("change", fn);
    return () => mq.removeEventListener("change", fn);
  }, []);
  return r;
}

type RevealProps = {
  children: ReactNode;
  delay?: 0 | 1 | 2 | 3 | 4 | 5;
  className?: string;
};
export function Reveal({ children, delay = 0, className = "" }: RevealProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => { if (e.isIntersecting) { el.classList.add("is-in"); io.unobserve(el); } }),
      { threshold: 0.14, rootMargin: "0px 0px -8% 0px" }
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);
  const d = delay ? ` reveal-d${delay}` : "";
  return <div ref={ref} className={`reveal${d} ${className}`}>{children}</div>;
}

type CountUpProps = { to: number; duration?: number; decimals?: number; prefix?: string; suffix?: string; className?: string };
export function CountUp({ to, duration = 1600, decimals = 0, prefix = "", suffix = "", className = "" }: CountUpProps) {
  const reduced = useReducedMotion();
  const ref = useRef<HTMLSpanElement | null>(null);
  const [val, setVal] = useState(0);
  useEffect(() => {
    if (reduced) { setVal(to); return; }
    const el = ref.current;
    if (!el) return;
    let raf = 0; let started = false;
    const ease = (t: number) => 1 - Math.pow(1 - t, 3);
    const run = () => {
      const t0 = performance.now();
      const tick = (now: number) => {
        const p = Math.min(1, (now - t0) / duration);
        setVal(to * ease(p));
        if (p < 1) raf = requestAnimationFrame(tick);
      };
      raf = requestAnimationFrame(tick);
    };
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (e.isIntersecting && !started) { started = true; run(); io.unobserve(el); } });
    }, { threshold: 0.4 });
    io.observe(el);
    return () => { io.disconnect(); cancelAnimationFrame(raf); };
  }, [to, duration, reduced]);
  const shown = val.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  return <span ref={ref} className={className}>{prefix}{shown}{suffix}</span>;
}

export function Eyebrow({ children, tone = "pink" }: { children: ReactNode; tone?: "pink" | "stellar" }) {
  const tones: Record<string, string> = {
    pink: "text-fuchsia-600 bg-white/70 border-fuchsia-200/80",
    stellar: "text-sky-600 bg-white/70 border-sky-200/80",
  };
  return (
    <span className={`inline-flex items-center gap-2 rounded-full border ${tones[tone]} px-3.5 py-1.5 text-[12.5px] font-semibold uppercase tracking-[0.14em] shadow-sm`}>
      {children}
    </span>
  );
}

type SectionHeadProps = { eyebrow?: ReactNode; tone?: "pink" | "stellar"; title: ReactNode; sub?: ReactNode; center?: boolean };
export function SectionHead({ eyebrow, tone, title, sub, center = true }: SectionHeadProps) {
  return (
    <div className={center ? "mx-auto max-w-2xl text-center" : "max-w-2xl"}>
      {eyebrow && <Reveal><Eyebrow tone={tone}>{eyebrow}</Eyebrow></Reveal>}
      <Reveal delay={1}>
        <h2 className="mt-5 font-display text-[clamp(28px,4.4vw,46px)] font-extrabold leading-[1.08] tracking-[-0.02em] text-ink">{title}</h2>
      </Reveal>
      {sub && <Reveal delay={2}><p className="mt-4 text-[17px] leading-relaxed text-gray-500">{sub}</p></Reveal>}
    </div>
  );
}

export function XiaoleeBubble({ size = 40, ring = true }: { size?: number; ring?: boolean }) {
  const style: CSSProperties = { width: size, height: size };
  return (
    <span className={`relative inline-block shrink-0 overflow-hidden rounded-full ${ring ? "ring-2 ring-white shadow-md" : ""}`} style={style}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={avatar.src} alt="Xiaolee" className="h-full w-full object-cover"
        style={{ objectPosition: "50% 18%", transform: "scale(1.35)" }} />
    </span>
  );
}
