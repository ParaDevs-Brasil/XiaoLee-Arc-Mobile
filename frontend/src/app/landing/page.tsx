import type { Metadata } from "next";
import "./landing.css";
import { Nav, Hero, Metrics } from "@/components/landing/Hero";
import { Pillars, SayItGrid, HowItWorks, Campaigns, Token, Channels, FinalCTA, Footer } from "@/components/landing/Sections";

export const metadata: Metadata = {
  title: "Xiaolee — Talk to your money on Arc",
  description:
    "Xiaolee is a conversational AI agent for Arc, Circle's USDC-native chain. Swap, send, earn and pay by chatting — non-custodial, no wallets to configure, no slippage to learn.",
};

export default function LandingPage() {
  return (
    <div className="xl-landing font-sans antialiased overflow-x-hidden">
      <Nav />
      <main>
        <Hero />
        <Metrics />
        <Pillars />
        <SayItGrid />
        <HowItWorks />
        <Campaigns />
        <Token />
        <Channels />
        <FinalCTA />
      </main>
      <Footer />
    </div>
  );
}
