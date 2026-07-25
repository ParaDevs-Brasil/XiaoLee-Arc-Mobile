/**
 * stellar.ts — Utilitários para integração com Freighter e Stellar testnet.
 *
 * Encapsula toda interação com @stellar/freighter-api para que os componentes
 * não chamem a biblioteca diretamente (PDR-002 / ADR-002).
 */

const CORE_API_URL =
  process.env.NEXT_PUBLIC_CORE_API_URL || "http://localhost:8000";

const STELLAR_NETWORK = "TESTNET";

// ---------------------------------------------------------------------------
// Freighter detection
// ---------------------------------------------------------------------------

export async function isFreighterInstalled(): Promise<boolean> {
  if (typeof window === "undefined") return false;
  try {
    const { isConnected } = await import("@stellar/freighter-api");
    const result = await isConnected();
    // freighter-api v3+ returns { isConnected: boolean }
    return typeof result === "object" ? result.isConnected : Boolean(result);
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// Connect / get public key
// ---------------------------------------------------------------------------

export async function connectFreighter(): Promise<string> {
  const { requestAccess } = await import("@stellar/freighter-api");
  const result = await requestAccess();
  if (result.error) throw new Error(`Freighter: ${result.error.message}`);
  const address = result.address;
  if (!address || !address.startsWith("G")) {
    throw new Error("Freighter retornou uma chave pública inválida.");
  }
  return address;
}

// ---------------------------------------------------------------------------
// Sign a transaction XDR (SEP-10 or path payment)
// ---------------------------------------------------------------------------

export async function signTransactionXdr(xdr: string, networkPassphrase?: string): Promise<string> {
  const { signTransaction } = await import("@stellar/freighter-api");
  const result = await signTransaction(xdr, {
    networkPassphrase: networkPassphrase ?? "Test SDF Network ; September 2015",
  });
  if ((result as { error?: { message: string } }).error) {
    const msg = (result as { error: { message: string } }).error.message;
    throw new Error(`Freighter: ${msg || "usuário cancelou ou extensão indisponível"}`);
  }
  const signed = (result as { signedTxXdr: string }).signedTxXdr;
  if (!signed) throw new Error("Freighter não retornou transação assinada.");
  return signed;
}

// ---------------------------------------------------------------------------
// SEP-10 — challenge / token flow
// ---------------------------------------------------------------------------

export interface StellarAuthResult {
  token: string;
  account: string;
}

export async function stellarSEP10Auth(account: string): Promise<StellarAuthResult> {
  // Step 1: get challenge XDR from backend
  const challengeResp = await fetch(
    `${CORE_API_URL}/auth/stellar/challenge?account=${account}`
  );
  if (!challengeResp.ok) {
    const err = await challengeResp.text();
    throw new Error(`Challenge falhou: ${err}`);
  }
  const { transaction: challengeXdr } = await challengeResp.json();

  // Step 2: sign with Freighter
  const signedXdr = await signTransactionXdr(challengeXdr);

  // Step 3: exchange for JWT
  const tokenResp = await fetch(`${CORE_API_URL}/auth/stellar/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ account, transaction: signedXdr }),
  });
  if (!tokenResp.ok) {
    const err = await tokenResp.text();
    throw new Error(`Token falhou: ${err}`);
  }
  const data = await tokenResp.json();
  return { token: data.token, account: data.account };
}

// ---------------------------------------------------------------------------
// Horizon balance query
// ---------------------------------------------------------------------------

export interface StellarBalance {
  xlm: number;
  assets: Array<{ asset_code: string; asset_issuer: string; balance: number }>;
}

export async function getStellarBalance(account: string): Promise<StellarBalance> {
  const HORIZON = "https://horizon-testnet.stellar.org";
  const resp = await fetch(`${HORIZON}/accounts/${account}`);
  if (!resp.ok) throw new Error(`Conta não encontrada no testnet: ${account}`);
  const data = await resp.json();
  let xlm = 0;
  const assets: StellarBalance["assets"] = [];
  for (const b of data.balances ?? []) {
    if (b.asset_type === "native") {
      xlm = parseFloat(b.balance);
    } else {
      assets.push({
        asset_code: b.asset_code,
        asset_issuer: b.asset_issuer,
        balance: parseFloat(b.balance),
      });
    }
  }
  return { xlm, assets };
}

// ---------------------------------------------------------------------------
// x402 — AI query with micropayment
// ---------------------------------------------------------------------------

export interface X402PaymentInfo {
  version: string;
  network: string;
  asset: string;
  amount: string;
  pay_to: string;
  memo: string;
  expires: number;
}

export interface X402QueryResult {
  reply: string;
  intent: unknown;
  x402_verified: boolean;
  execution?: {
    chain?: string;
    swap_xdr?: string | null;
    network_passphrase?: string;
    swap_quote?: {
      from: string;
      to: string;
      source_amount: number;
      destination_amount: number;
    };
    [key: string]: unknown;
  };
}

// ---------------------------------------------------------------------------
// x402 auto-pay: backend gera XDR → Freighter assina → Horizon submete
// ---------------------------------------------------------------------------

export async function buildPaymentXdr(account: string): Promise<{
  xdr: string;
  network_passphrase: string;
  pay_to: string;
  amount: string;
  memo: string;
}> {
  const resp = await fetch(
    `${CORE_API_URL}/v1/ai/query/payment-tx?account=${encodeURIComponent(account)}`
  );
  if (!resp.ok) throw new Error(`Falha ao construir transação: HTTP ${resp.status}`);
  return resp.json();
}

export async function submitToHorizon(
  signedXdr: string,
  network: "testnet" | "mainnet" = "testnet"
): Promise<string> {
  const HORIZON =
    network === "testnet"
      ? "https://horizon-testnet.stellar.org"
      : "https://horizon.stellar.org";
  const resp = await fetch(`${HORIZON}/transactions`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ tx: signedXdr }),
  });
  const data = await resp.json();
  if (!resp.ok) {
    const codes = data?.extras?.result_codes;
    throw new Error(`Horizon rejeitou: ${JSON.stringify(codes ?? data.detail ?? data)}`);
  }
  return data.hash as string;
}

export async function autoPayX402(account: string): Promise<string> {
  const { xdr, network_passphrase } = await buildPaymentXdr(account);
  const signedXdr = await signTransactionXdr(xdr, network_passphrase);
  return submitToHorizon(signedXdr, "testnet");
}

// ---------------------------------------------------------------------------
// Direct DEX swap quote + XDR (sem AI, sem x402)
// ---------------------------------------------------------------------------

export interface SwapQuoteResult {
  quote: {
    from: string;
    to: string;
    source_amount: number;
    destination_amount: number;
    fee_xlm: number;
    path: string[];
  };
  xdr: string | null;
  network_passphrase: string;
  has_liquidity: boolean;
}

export async function getStellarSwapQuote(
  wallet: string,
  fromAsset: string,
  toAsset: string,
  amount: number
): Promise<SwapQuoteResult> {
  const url = `${CORE_API_URL}/stellar/swap/quote?wallet=${encodeURIComponent(wallet)}&from_asset=${fromAsset}&to_asset=${toAsset}&amount=${amount}`;
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`Quote failed: HTTP ${resp.status}`);
  return resp.json();
}

export async function x402AiQuery(
  message: string,
  stellarWallet: string,
  txHash?: string
): Promise<{ status: 402; payment: X402PaymentInfo } | { status: 200; data: X402QueryResult }> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (txHash) {
    headers["X-Payment"] = JSON.stringify({ tx_hash: txHash, network: "testnet" });
  }

  const resp = await fetch(`${CORE_API_URL}/v1/ai/query`, {
    method: "POST",
    headers,
    body: JSON.stringify({ message, stellar_wallet: stellarWallet }),
  });

  if (resp.status === 402) {
    const body = await resp.json();
    return { status: 402, payment: body.payment as X402PaymentInfo };
  }

  if (!resp.ok) {
    const err = await resp.text();
    throw new Error(`AI query error: ${err}`);
  }

  const data = await resp.json();
  return { status: 200, data: data as X402QueryResult };
}

// ---------------------------------------------------------------------------
// Anchor SEP-24 — testanchor.stellar.org (âncora oficial SDF no testnet)
// ---------------------------------------------------------------------------

export interface AnchorDepositResult {
  url: string;
  id: string;
  type: string;
  anchor: string;
  asset_code: string;
}

export async function getAnchorChallenge(
  account: string
): Promise<{ transaction: string; network_passphrase: string }> {
  const resp = await fetch(
    `${CORE_API_URL}/stellar/anchor/challenge?account=${encodeURIComponent(account)}`
  );
  if (!resp.ok) throw new Error(`Anchor challenge falhou: HTTP ${resp.status}`);
  return resp.json();
}

export async function initiateAnchorDeposit(
  account: string,
  signedXdr: string,
  assetCode: string = "USDC"
): Promise<AnchorDepositResult> {
  const resp = await fetch(`${CORE_API_URL}/stellar/anchor/deposit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ account, signed_xdr: signedXdr, asset_code: assetCode }),
  });
  if (!resp.ok) {
    const err = await resp.text();
    throw new Error(`Anchor deposit falhou: ${err}`);
  }
  return resp.json();
}
