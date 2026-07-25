"use client";
import { useLandingT, APP_URL } from "./strings";
import { Reveal, SectionHead, Eyebrow, XiaoleeBubble } from "./primitives";
import {
  IconGift, IconChat, IconBolt, IconShield, IconCheck, IconCoin, IconLock, IconCpu,
  IconStar, IconRoute, IconWallet, IconGlobe, IconTarget, IconLayers, IconSend,
  IconArrow, IconSwap, IconSpark, IconX, IconTelegram, IconGithub, IconDiscord,
} from "./icons";
import type { IconProps } from "./icons";
import type { ComponentType } from "react";

type IC = ComponentType<IconProps>;

/* ------------------------------- PILLARS --------------------------------- */
export function Pillars() {
  const pillars: { icon: IC; tone: "fuchsia" | "purple" | "sky"; title: string; body: string; tags: string[] }[] = [
    { icon: IconChat, tone: "fuchsia", title: "Conversational DeFi",
      body: "Swaps, balances and sends — all by message. “Trade 50 USDC for EURC” and Xiaolee quotes the best route on Arc. You confirm, your wallet signs.",
      tags: ["x402 payments", "Live quotes", "@handle sends"] },
    { icon: IconTarget, tone: "purple", title: "Creator campaigns",
      body: "Creators post social tasks; fans complete them; Xiaolee verifies and pays out $XLEE or USDC straight to the wallet — no code, no custody, auditable on-chain.",
      tags: ["x402 receipts", "Join · Verify · Claim", "0.5% fee"] },
    { icon: IconBolt, tone: "sky", title: "Pix & LATAM gateway",
      body: "On/off-ramp via EtherFuse. Enter with Pix, operate in USDC on Arc, and cash out whenever — no exchange account, no international card.",
      tags: ["Pix in/out", "Stablecoins", "No card needed"] },
  ];
  const tones: Record<string, string> = {
    fuchsia: "from-pink-400 to-fuchsia-500",
    purple: "from-fuchsia-500 to-purple-600",
    sky: "from-sky-400 to-blue-500",
  };
  return (
    <section id="product" className="mx-auto max-w-[1180px] scroll-mt-24 px-4 py-16 sm:px-6">
      <SectionHead eyebrow={<><IconSpark size={13} /> What Xiaolee does</>} tone="pink"
        title={<>One chat. The whole <span className="text-grad">USDC economy.</span></>}
        sub="No dashboards to decode, no twelve tabs. Three things Xiaolee does the moment you say hello." />
      <div className="mt-12 grid gap-5 md:grid-cols-3">
        {pillars.map((p, i) => {
          const Ic = p.icon;
          return (
            <Reveal key={i} delay={(i + 1) as 1 | 2 | 3}>
              <div className="lift glass h-full rounded-3xl border border-white/70 p-6 shadow-sm ring-soft">
                <div className={`grid h-12 w-12 place-items-center rounded-2xl bg-gradient-to-br ${tones[p.tone]} text-white shadow-md`}><Ic size={24} /></div>
                <h3 className="mt-5 font-display text-[21px] font-bold text-ink">{p.title}</h3>
                <p className="mt-2.5 text-[15px] leading-relaxed text-gray-500">{p.body}</p>
                <div className="mt-5 flex flex-wrap gap-2">
                  {p.tags.map((t) => <span key={t} className="rounded-full border border-fuchsia-100 bg-white/60 px-2.5 py-1 text-[12px] font-semibold text-fuchsia-500">{t}</span>)}
                </div>
              </div>
            </Reveal>
          );
        })}
      </div>
    </section>
  );
}

/* --------------------------- CONVERSATIONAL GRID ------------------------- */
export function SayItGrid() {
  const rows: { icon: IC; say: string; get: string }[] = [
    { icon: IconWallet, say: "What's in my wallet?", get: "120 USDC · 45 EURC · 0 XLEE" },
    { icon: IconSwap, say: "Swap 50 USDC → EURC", get: "Best route on Arc, you confirm" },
    { icon: IconSend, say: "Send 10 USDC to @maria", get: "By @handle or 0x-address" },
    { icon: IconBolt, say: "Deposit R$100 via Pix", get: "EtherFuse on-ramp, instant" },
    { icon: IconTarget, say: "Join @artist's campaign", get: "Tasks tracked, reward queued" },
    { icon: IconGlobe, say: "What's USDC in BRL?", get: "Live price, no app-switching" },
  ];
  return (
    <section className="relative overflow-hidden py-16">
      <div className="mx-auto max-w-[1180px] px-4 sm:px-6">
        <SectionHead eyebrow={<><IconChat size={13} /> Just say it</>} tone="pink"
          title={<>If you can text it, <span className="text-grad-stellar">Xiaolee can do it.</span></>}
          sub="Gemini reads your intent and mirrors your language. Here's the kind of thing people type all day." />
        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {rows.map((r, i) => {
            const Ic = r.icon;
            return (
              <Reveal key={i} delay={((i % 3) + 1) as 1 | 2 | 3}>
                <div className="lift glass h-full rounded-2xl border border-white/70 p-5 shadow-sm">
                  <div className="flex items-start gap-3">
                    <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-fuchsia-50 text-fuchsia-500"><Ic size={18} /></div>
                    <div className="min-w-0">
                      <div className="rounded-2xl rounded-tl-sm btn-primary px-3 py-2 text-[14px] font-semibold text-white shadow-sm">{r.say}</div>
                      <div className="mt-2 flex items-center gap-1.5 pl-1 text-[13.5px] text-gray-500"><IconArrow size={13} className="shrink-0 text-fuchsia-300" /><span>{r.get}</span></div>
                    </div>
                  </div>
                </div>
              </Reveal>
            );
          })}
        </div>
      </div>
    </section>
  );
}

/* ------------------------------ HOW IT WORKS ----------------------------- */
export function HowItWorks() {
  const steps: { n: string; icon: IC; title: string; body: string }[] = [
    { n: "01", icon: IconWallet, title: "Connect your wallet", body: "A one-tap signature proves the wallet is yours. No private key ever reaches our backend." },
    { n: "02", icon: IconChat, title: "Just talk", body: "Ask in plain language — EN or PT, auto-detected. Xiaolee figures out the intent and the route." },
    { n: "03", icon: IconShield, title: "Confirm in-wallet", body: "Xiaolee shows the quote, fee and path. Nothing moves until you sign it in your wallet yourself." },
    { n: "04", icon: IconCheck, title: "Done, on-chain", body: "Settled on Arc in seconds for fractions of a cent. A receipt lands in your in-app inbox." },
  ];
  return (
    <section id="how" className="mx-auto max-w-[1180px] scroll-mt-24 px-4 py-16 sm:px-6">
      <SectionHead eyebrow={<><IconRoute size={13} /> How it works</>} tone="stellar"
        title={<>Four steps. <span className="text-grad">You stay in control.</span></>}
        sub="Wallet-first and non-custodial from end to end — the backend orchestrates, your keys decide." />
      <div className="relative mt-14 grid gap-6 md:grid-cols-4">
        <div className="pointer-events-none absolute left-0 right-0 top-7 hidden h-px bg-gradient-to-r from-transparent via-fuchsia-200 to-transparent md:block" />
        {steps.map((s, i) => {
          const Ic = s.icon;
          return (
            <Reveal key={i} delay={(i + 1) as 1 | 2 | 3 | 4}>
              <div className="relative text-center md:text-left">
                <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl border border-white/70 glass text-fuchsia-500 shadow-md ring-soft md:mx-0"><Ic size={24} /></div>
                <div className="mt-4 font-mono text-[12px] font-bold tracking-widest text-fuchsia-400">{s.n}</div>
                <h3 className="mt-1 font-display text-[18px] font-bold text-ink">{s.title}</h3>
                <p className="mt-2 text-[14px] leading-relaxed text-gray-500">{s.body}</p>
              </div>
            </Reveal>
          );
        })}
      </div>
    </section>
  );
}

/* ------------------------------- CAMPAIGNS ------------------------------- */
function CampaignCardMock() {
  const tasks = [
    { t: "Follow @xiaolee_ai on X", done: true },
    { t: "Repost the launch thread", done: true },
    { t: "Comment your favorite feature", done: false },
  ];
  const stats = [
    { v: "10", l: "Reward", u: "$XLEE" },
    { v: "5,000", l: "Pool", u: "$XLEE" },
    { v: "312", l: "Spots", u: "of 500" },
  ];
  return (
    <div className="glass ring-soft rounded-3xl border border-white/70 p-5 shadow-xl">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-fuchsia-500 to-purple-600 text-white"><IconTarget size={20} /></div>
          <div>
            <div className="text-[15px] font-bold text-ink">Launch week boost</div>
            <div className="text-[12px] font-semibold text-gray-400">by @xiaolee_ai · active</div>
          </div>
        </div>
        <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-bold text-emerald-600">Live</span>
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2.5 text-center">
        {stats.map((x) => (
          <div key={x.l} className="rounded-2xl border border-fuchsia-100 bg-white/60 py-3">
            <div className="font-display text-[20px] font-extrabold leading-none text-grad">{x.v}</div>
            <div className="mt-1 text-[11px] font-semibold text-gray-400">{x.l} · {x.u}</div>
          </div>
        ))}
      </div>
      <div className="mt-4 space-y-2">
        {tasks.map((t, i) => (
          <div key={i} className="flex items-center gap-2.5 rounded-xl border border-gray-100 bg-white/60 px-3 py-2.5">
            <span className={`grid h-5 w-5 place-items-center rounded-full ${t.done ? "bg-emerald-500 text-white" : "border-2 border-fuchsia-200 text-transparent"}`}><IconCheck size={13} /></span>
            <span className={`text-[13.5px] ${t.done ? "text-gray-400 line-through" : "font-semibold text-gray-600"}`}>{t.t}</span>
          </div>
        ))}
      </div>
      <button className="btn-primary mt-4 flex w-full items-center justify-center gap-2 rounded-2xl py-3 text-[14.5px] font-bold text-white"><IconGift size={17} /> Claim 10 $XLEE</button>
      <div className="mt-2.5 flex items-center justify-center gap-1.5 text-[11.5px] font-medium text-gray-400"><IconCpu size={13} className="text-fuchsia-300" /> Settled on-chain via x402</div>
    </div>
  );
}

export function Campaigns() {
  const bullets: { icon: IC; t: string; b: string }[] = [
    { icon: IconGift, t: "Pay for verified engagement", b: "Fans follow, repost and comment — Xiaolee verifies, then releases the reward. You pay only when tasks check out." },
    { icon: IconLock, t: "Custodial-free for your fans", b: "No seed phrases to onboard. Custodial sessions via Google or Telegram let anyone claim, then graduate to self-custody." },
    { icon: IconCpu, t: "Auditable on-chain", b: "Every distribution is recorded on-chain by the XiaoLee payment contract. Creators and fans can verify without trusting us." },
  ];
  return (
    <section className="relative py-16">
      <div className="mx-auto grid max-w-[1180px] items-center gap-12 px-4 sm:px-6 lg:grid-cols-[1fr_0.85fr]">
        <div>
          <Reveal><Eyebrow tone="pink"><IconGift size={13} /> Campaign engine</Eyebrow></Reveal>
          <Reveal delay={1}>
            <h2 className="mt-5 font-display text-[clamp(28px,4.4vw,46px)] font-extrabold leading-[1.08] tracking-[-0.02em] text-ink">Creator campaigns,<br /><span className="text-grad">real on-chain rewards.</span></h2>
          </Reveal>
          <Reveal delay={2}><p className="mt-4 max-w-lg text-[17px] leading-relaxed text-gray-500">Set up a campaign in ten minutes. Your audience completes social tasks and gets paid in $XLEE or USDC — straight to the wallet, 40× cheaper than legacy creator platforms.</p></Reveal>
          <div className="mt-8 space-y-5">
            {bullets.map((x, i) => {
              const Ic = x.icon;
              return (
                <Reveal key={i} delay={(i + 2) as 2 | 3 | 4}>
                  <div className="flex gap-3.5">
                    <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-fuchsia-50 text-fuchsia-500"><Ic size={19} /></div>
                    <div><h4 className="text-[16px] font-bold text-ink">{x.t}</h4><p className="mt-1 text-[14.5px] leading-relaxed text-gray-500">{x.b}</p></div>
                  </div>
                </Reveal>
              );
            })}
          </div>
        </div>
        <Reveal delay={2}><CampaignCardMock /></Reveal>
      </div>
    </section>
  );
}

/* --------------------------------- TOKEN --------------------------------- */
export function Token() {
  const rows = [
    { k: "Standard", v: "ERC-20 on Arc" },
    { k: "Network", v: "Arc · Circle" },
    { k: "Transfer fee (burn)", v: "0.5% native" },
    { k: "Rewards", v: "Distributed via x402" },
    { k: "Contract (mint)", v: "Awaiting mainnet deploy", mono: true },
  ];
  const feats: { icon: IC; t: string; b: string }[] = [
    { icon: IconLock, t: "Chargeback-proof", b: "Blockchain settlement is irreversible — zero chargebacks, ever." },
    { icon: IconShield, t: "Pseudonymous", b: "A wallet, not a bank statement. Discreet by default." },
    { icon: IconCoin, t: "40× cheaper", b: "0.5% campaign fee vs. the 20–50% legacy platforms take." },
  ];
  return (
    <section id="token" className="mx-auto max-w-[1180px] scroll-mt-24 px-4 py-16 sm:px-6">
      <div className="grid items-center gap-12 lg:grid-cols-[0.85fr_1fr]">
        <Reveal delay={1}>
          <div className="glass ring-soft rounded-3xl border border-white/70 p-6 shadow-xl">
            <div className="flex items-center gap-3">
              <div className="grid h-12 w-12 place-items-center rounded-2xl bg-gradient-to-br from-amber-300 to-fuchsia-500 text-white shadow-md"><IconCoin size={24} /></div>
              <div><div className="font-display text-[22px] font-extrabold text-ink">$XLEE</div><div className="text-[12.5px] font-semibold text-gray-400">Tokenomics</div></div>
            </div>
            <div className="mt-5 divide-y divide-gray-100">
              {rows.map((r) => (
                <div key={r.k} className="flex items-center justify-between py-3">
                  <span className="text-[14px] text-gray-500">{r.k}</span>
                  <span className={`text-[14px] font-bold text-ink ${r.mono ? "font-mono text-[12.5px] text-gray-400" : ""}`}>{r.v}</span>
                </div>
              ))}
            </div>
          </div>
        </Reveal>
        <div>
          <Reveal><Eyebrow tone="pink"><IconCoin size={13} /> Built for creators</Eyebrow></Reveal>
          <Reveal delay={1}><h2 className="mt-5 font-display text-[clamp(28px,4.4vw,46px)] font-extrabold leading-[1.08] tracking-[-0.02em] text-ink">Money that <span className="text-grad">can&apos;t be blocked.</span></h2></Reveal>
          <Reveal delay={2}><p className="mt-4 max-w-lg text-[17px] leading-relaxed text-gray-500">$XLEE is a standard ERC-20 on Arc, so it plugs into the USDC economy from day one and distributes through audited x402 nanopayments — no custom token risk.</p></Reveal>
          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            {feats.map((f, i) => {
              const Ic = f.icon;
              return (
                <Reveal key={i} delay={(i + 2) as 2 | 3 | 4}>
                  <div className="lift glass h-full rounded-2xl border border-white/70 p-4 shadow-sm">
                    <div className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-50 text-emerald-500"><Ic size={19} /></div>
                    <h4 className="mt-3 text-[15px] font-bold text-ink">{f.t}</h4>
                    <p className="mt-1 text-[13px] leading-relaxed text-gray-500">{f.b}</p>
                  </div>
                </Reveal>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}

/* ------------------------------- CHANNELS -------------------------------- */
export function Channels() {
  const chans: { icon: IC; t: string; b: string; tag: string }[] = [
    { icon: IconX, t: "X / Twitter DM", b: "Where the creator economy already lives. DM Xiaolee and operate without leaving the timeline.", tag: "social-native" },
    { icon: IconTelegram, t: "Telegram", b: "Full conversational ops in your group or DMs — 100% operational today, onboarding and all.", tag: "live" },
    { icon: IconChat, t: "Web app", b: "The full glass UI: chat, campaigns, dashboard and notifications — with wallet connect built in.", tag: "wallet" },
  ];
  const stack = ["Arc", "Circle", "USDC", "EURC", "CCTP", "x402", "ERC-20", "EtherFuse"];
  return (
    <section id="dev" className="relative scroll-mt-24 py-16">
      <div className="mx-auto max-w-[1180px] px-4 sm:px-6">
        <SectionHead eyebrow={<><IconLayers size={13} /> Omnichannel</>} tone="stellar"
          title={<>Meet Xiaolee where <span className="text-grad-stellar">you already are.</span></>}
          sub="One agent, one identity anchored to your social handle — across every surface you talk on." />
        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {chans.map((c, i) => {
            const Ic = c.icon;
            return (
              <Reveal key={i} delay={(i + 1) as 1 | 2 | 3}>
                <div className="lift glass h-full rounded-3xl border border-white/70 p-6 shadow-sm ring-soft">
                  <div className="flex items-center justify-between">
                    <div className="grid h-12 w-12 place-items-center rounded-2xl bg-ink text-white shadow-md"><Ic size={22} /></div>
                    <span className="rounded-full border border-fuchsia-100 bg-white/60 px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider text-fuchsia-400">{c.tag}</span>
                  </div>
                  <h3 className="mt-5 font-display text-[19px] font-bold text-ink">{c.t}</h3>
                  <p className="mt-2 text-[14.5px] leading-relaxed text-gray-500">{c.b}</p>
                </div>
              </Reveal>
            );
          })}
        </div>
        <Reveal delay={2}>
          <div className="mt-10 flex flex-col items-center gap-4 rounded-3xl border border-white/70 glass px-6 py-6 shadow-sm sm:flex-row sm:justify-between">
            <div className="flex items-center gap-2.5">
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-sky-400 to-blue-600 text-white"><IconStar size={18} /></span>
              <span className="font-display text-[16px] font-bold text-ink">Built on Arc</span>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-2">
              {stack.map((s) => <span key={s} className="rounded-full border border-sky-100 bg-white/60 px-3 py-1.5 text-[12.5px] font-semibold text-sky-600">{s}</span>)}
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

/* ------------------------------- FINAL CTA ------------------------------- */
export function FinalCTA() {
  const t = useLandingT();
  return (
    <section className="mx-auto max-w-[1180px] px-4 py-16 sm:px-6">
      <Reveal>
        <div className="relative overflow-hidden rounded-[36px] border border-white/70 px-6 py-16 text-center shadow-2xl ring-soft" style={{ background: "linear-gradient(135deg,#fff0fa 0%,#f6ecff 55%,#eaf4ff 100%)" }}>
          <div className="pointer-events-none absolute inset-0 opacity-70">
            <IconSpark size={28} className="absolute left-[12%] top-[20%] text-fuchsia-300 anim-floaty" />
            <IconSpark size={18} className="absolute right-[14%] top-[30%] text-sky-300 anim-floatySlow" />
            <IconSpark size={22} className="absolute bottom-[16%] left-[20%] text-purple-300 anim-floaty" style={{ animationDelay: "1s" }} />
          </div>
          <div className="relative">
            <div className="mx-auto mb-6 w-fit"><XiaoleeBubble size={64} /></div>
            <div className="text-[12.5px] font-bold uppercase tracking-[0.16em] text-fuchsia-500">{t("cta.eyebrow")}</div>
            <h2 className="mx-auto mt-3 max-w-3xl font-display text-[clamp(34px,6vw,60px)] font-extrabold leading-[1.05] tracking-[-0.025em] text-ink">{t("cta.head")}</h2>
            <p className="mx-auto mt-5 max-w-xl text-[17px] leading-relaxed text-gray-500">{t("cta.sub")}</p>
            <a href={APP_URL} target="_blank" rel="noopener noreferrer" className="btn-primary mt-8 inline-flex items-center gap-2 rounded-full px-7 py-4 text-[17px] font-bold text-white">{t("cta.btn")} <IconArrow size={19} /></a>
          </div>
        </div>
      </Reveal>
    </section>
  );
}

/* -------------------------------- FOOTER --------------------------------- */
export function Footer() {
  const t = useLandingT();
  const cols = [
    { h: "Product", links: ["Conversational DeFi", "Campaigns", "$XLEE", "Pix on-ramp"] },
    { h: "Developers", links: ["Payment contract", "API reference", "Agent API", "x402 payments"] },
    { h: "Community", links: ["X / Twitter", "Telegram", "Discord", "GitHub"] },
  ];
  const socials: IC[] = [IconX, IconTelegram, IconDiscord, IconGithub];
  return (
    <footer className="border-t border-fuchsia-100/70 bg-white/40">
      <div className="mx-auto max-w-[1180px] px-4 py-14 sm:px-6">
        <div className="grid gap-10 md:grid-cols-[1.4fr_1fr_1fr_1fr]">
          <div>
            <div className="flex items-center gap-2.5">
              <XiaoleeBubble size={34} />
              <span className="font-display text-[19px] font-extrabold tracking-tight text-ink">Xiao<span className="text-grad">lee</span></span>
              <IconSpark size={13} className="text-fuchsia-400" />
            </div>
            <p className="mt-4 max-w-xs text-[14px] leading-relaxed text-gray-500">{t("footer.tag")}</p>
            <div className="mt-5 flex items-center gap-2.5">
              {socials.map((S, i) => (
                <a key={i} href={APP_URL} target="_blank" rel="noopener noreferrer" className="grid h-9 w-9 place-items-center rounded-full border border-fuchsia-100 bg-white/70 text-gray-400 transition hover:text-fuchsia-500 hover:shadow-md"><S size={17} /></a>
              ))}
            </div>
          </div>
          {cols.map((c) => (
            <div key={c.h}>
              <h4 className="text-[13px] font-bold uppercase tracking-wider text-ink">{c.h}</h4>
              <ul className="mt-4 space-y-2.5">
                {c.links.map((l) => <li key={l}><a href={APP_URL} target="_blank" rel="noopener noreferrer" className="text-[14px] text-gray-500 transition hover:text-fuchsia-600">{l}</a></li>)}
              </ul>
            </div>
          ))}
        </div>
        <div className="mt-12 flex flex-col items-start justify-between gap-4 border-t border-fuchsia-100/70 pt-6 sm:flex-row sm:items-center">
          <p className="max-w-2xl text-[12.5px] leading-relaxed text-gray-400">{t("footer.rights")}</p>
          <span className="inline-flex shrink-0 items-center gap-2 rounded-full border border-sky-100 bg-white/70 px-3.5 py-1.5 text-[12.5px] font-bold text-sky-600 shadow-sm"><IconStar size={13} /> Built on Arc</span>
        </div>
      </div>
    </footer>
  );
}
