/**
 * Detecção de chain por formato de endereço/tx e links de explorer.
 *
 * Formatos (ROADMAP_INTEGRACAO_FRONTEND.md · Fase 0.1 e 1.1):
 *   arc/EVM  — endereço `0x` + 40 hex · tx `0x` + 64 hex
 *   solana   — endereço base58 32-44 chars · tx assinatura base58 ~87-88 chars
 *   stellar  — endereço strkey `G` + 55 chars · tx hash 64 hex sem `0x`
 */

export type Chain = "arc" | "solana" | "stellar";

const BASE58_RE = /^[1-9A-HJ-NP-Za-km-z]+$/;

export const CHAIN_LABEL: Record<Chain, string> = {
  arc: "Arc",
  solana: "Solana",
  stellar: "Stellar",
};

export function detectChainFromAddress(address: string): Chain | null {
  const addr = address.trim();
  if (/^0x[0-9a-fA-F]{40}$/.test(addr)) return "arc";
  if (/^G[A-Z2-7]{55}$/.test(addr)) return "stellar";
  if (addr.length >= 32 && addr.length <= 44 && BASE58_RE.test(addr)) return "solana";
  return null;
}

export function detectChainFromTx(tx: string): Chain | null {
  const t = tx.trim();
  if (/^0x[0-9a-fA-F]{64}$/.test(t)) return "arc";
  if (/^[0-9a-fA-F]{64}$/.test(t)) return "stellar";
  if (t.length >= 80 && t.length <= 96 && BASE58_RE.test(t)) return "solana";
  return null;
}

export function explorerTxUrl(tx: string, chain?: Chain | null): string | null {
  const resolved = chain ?? detectChainFromTx(tx);
  switch (resolved) {
    case "arc":
      return `https://testnet.arcscan.app/tx/${tx}`;
    case "solana":
      return `https://solscan.io/tx/${tx}?cluster=devnet`;
    case "stellar":
      return `https://stellar.expert/explorer/testnet/tx/${tx}`;
    default:
      return null;
  }
}
