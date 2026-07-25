"use client";

/**
 * Minimal EIP-1193 injected-wallet helpers (MetaMask, Rabby, Coinbase, …).
 * No SDK dependency — the payment rail itself lives in the backend
 * (Circle W3S / arc_native); the frontend only needs the user's address.
 */

export type Eip1193Provider = {
  request: (args: { method: string; params?: unknown[] }) => Promise<unknown>;
  on?: (event: string, listener: (...args: unknown[]) => void) => void;
  removeListener?: (event: string, listener: (...args: unknown[]) => void) => void;
  isMetaMask?: boolean;
};

const STORAGE_KEY = "xiaolee_evm_address";

// Friendly names for the chains XiaoLee touches (CCTP path: Sepolia ↔ Arc)
const CHAIN_NAMES: Record<string, string> = {
  "0x1": "Ethereum",
  "0xaa36a7": "Ethereum Sepolia",
  "0x66eee": "Arbitrum Sepolia",
  "0x14a34": "Base Sepolia",
  "0x2105": "Base",
  "0xa4b1": "Arbitrum One",
};

export function getInjectedProvider(): Eip1193Provider | null {
  if (typeof window === "undefined") return null;
  const eth = (window as Window & { ethereum?: Eip1193Provider }).ethereum;
  return eth ?? null;
}

export function isEvmWalletInstalled(): boolean {
  return getInjectedProvider() !== null;
}

export async function connectEvmWallet(): Promise<string> {
  const provider = getInjectedProvider();
  if (!provider) throw new Error("no_wallet");
  const accounts = (await provider.request({ method: "eth_requestAccounts" })) as string[];
  const address = accounts?.[0];
  if (!address) throw new Error("no_account");
  if (typeof window !== "undefined") {
    window.localStorage.setItem(STORAGE_KEY, address);
  }
  return address;
}

export async function getEvmChainName(): Promise<string> {
  const provider = getInjectedProvider();
  if (!provider) return "";
  try {
    const chainId = (await provider.request({ method: "eth_chainId" })) as string;
    return CHAIN_NAMES[chainId?.toLowerCase()] ?? `Chain ${parseInt(chainId, 16)}`;
  } catch {
    return "";
  }
}

export function getStoredEvmAddress(): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(STORAGE_KEY) ?? "";
}

export function clearStoredEvmAddress(): void {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(STORAGE_KEY);
  }
}

/**
 * Assina uma mensagem UTF-8 via EIP-191 personal_sign — retorna a assinatura 0x… (65 bytes hex).
 * Resolve o provider da wallet que CONECTOU (não o window.ethereum genérico, que com
 * várias extensões pode ser outra wallet) e pede autorização do site antes de assinar.
 */
export async function signEvmMessage(address: string, message: string): Promise<string> {
  const { resolveEvmProvider } = await import("./walletProviders");
  const provider = (await resolveEvmProvider(address)) ?? getInjectedProvider();
  if (!provider) throw new Error("no_wallet");

  // personal_sign falha com "not authorized" se o site não está conectado nessa wallet
  const accounts = (await provider.request({ method: "eth_accounts" })) as string[];
  if (!accounts?.some((a) => a.toLowerCase() === address.toLowerCase())) {
    await provider.request({ method: "eth_requestAccounts" });
  }

  const hexMessage =
    "0x" + Array.from(new TextEncoder().encode(message), (b) => b.toString(16).padStart(2, "0")).join("");
  return (await provider.request({
    method: "personal_sign",
    params: [hexMessage, address],
  })) as string;
}

export interface EvmTxRequest {
  to: string;
  data: string;
  value?: string;
}

interface ArcChainConfig {
  chainIdHex: string;
  chainName: string;
  rpcUrls: string[];
  blockExplorerUrls: string[];
  nativeCurrency: { name: string; symbol: string; decimals: number };
}

const API_BASE = process.env.NEXT_PUBLIC_CORE_API_URL || "http://localhost:8000";

/**
 * Garante que a wallet esteja na rede Arc antes de assinar — sem isso o
 * eth_sendTransaction vai para a rede ativa da wallet (ex: Ethereum) e a
 * simulação falha porque o contrato USDC do Arc não existe lá.
 */
async function ensureArcNetwork(provider: Eip1193Provider): Promise<void> {
  let cfg: ArcChainConfig;
  try {
    const resp = await fetch(`${API_BASE}/v1/arc/chain-config`);
    if (!resp.ok) return; // sem config → segue e deixa a wallet decidir
    cfg = (await resp.json()) as ArcChainConfig;
  } catch {
    return;
  }

  const current = (await provider.request({ method: "eth_chainId" })) as string;
  if (current?.toLowerCase() === cfg.chainIdHex.toLowerCase()) return;

  try {
    await provider.request({
      method: "wallet_switchEthereumChain",
      params: [{ chainId: cfg.chainIdHex }],
    });
  } catch (err) {
    // 4902 = chain desconhecida na wallet → tenta adicionar e o switch é implícito
    const code = (err as { code?: number })?.code;
    if (code === 4902 || code === -32603) {
      try {
        await provider.request({
          method: "wallet_addEthereumChain",
          params: [{
            chainId: cfg.chainIdHex,
            chainName: cfg.chainName,
            rpcUrls: cfg.rpcUrls,
            blockExplorerUrls: cfg.blockExplorerUrls,
            nativeCurrency: cfg.nativeCurrency,
          }],
        });
      } catch {
        // Wallets como a Phantom recusam redes EVM customizadas (só suportam as
        // chains grandes). Erro claro apontando para MetaMask/Rabby.
        throw new Error(
          "Sua wallet não suporta a rede Arc testnet (a Phantom só aceita chains grandes). " +
          "Conecte a MetaMask ou a Rabby pelo Connect Wallet para transferir USDC no Arc."
        );
      }
    } else {
      throw new Error(
        "Sua wallet não suporta a rede Arc testnet. Conecte a MetaMask ou a Rabby pelo Connect Wallet."
      );
    }
  }
}

/**
 * Envia uma transação pela wallet EVM conectada (eth_sendTransaction) — mesmo
 * resolver de provider do signEvmMessage. Retorna o tx hash.
 */
export async function sendEvmTransaction(tx: EvmTxRequest): Promise<string> {
  const { resolveEvmProvider, getStoredConnectedWallet } = await import("./walletProviders");
  const connected = getStoredConnectedWallet();
  const from = connected?.address ?? getStoredEvmAddress();
  if (!from) throw new Error("no_wallet_connected");

  const provider = (await resolveEvmProvider(from)) ?? getInjectedProvider();
  if (!provider) throw new Error("no_wallet");

  const accounts = (await provider.request({ method: "eth_accounts" })) as string[];
  if (!accounts?.some((a) => a.toLowerCase() === from.toLowerCase())) {
    await provider.request({ method: "eth_requestAccounts" });
  }

  await ensureArcNetwork(provider);

  const params: Record<string, string> = {
    from,
    to: tx.to,
    data: tx.data,
    value: tx.value ?? "0x0",
  };

  // Estima o gas nós mesmos e envia explícito: wallets como a Rabby desabilitam o
  // "Sign" quando não conseguem SIMULAR numa testnet custom (Arc). Com o gas já no
  // payload, elas não dependem da simulação para liberar a assinatura.
  try {
    const est = (await provider.request({
      method: "eth_estimateGas",
      params: [{ from, to: tx.to, data: tx.data, value: tx.value ?? "0x0" }],
    })) as string;
    const withBuffer = Math.ceil(parseInt(est, 16) * 1.3); // +30% de folga
    params.gas = "0x" + withBuffer.toString(16);
  } catch {
    // estimativa falhou — segue sem gas explícito (wallet estima do jeito dela)
  }

  // Fee EIP-1559 explícito: sem isso a MetaMask mostra "Network fee: Unavailable"
  // e não deixa assinar na testnet custom (não consegue estimar o fee sozinha).
  let triedEip1559 = false;
  try {
    const resp = await fetch(`${API_BASE}/v1/arc/gas-fees`);
    if (resp.ok) {
      const fees = (await resp.json()) as {
        maxFeePerGasHex: string;
        maxPriorityFeePerGasHex: string;
      };
      params.maxFeePerGas = fees.maxFeePerGasHex;
      params.maxPriorityFeePerGas = fees.maxPriorityFeePerGasHex;
      triedEip1559 = true;
    }
  } catch {
    // sem fee explícito — a wallet tenta estimar do jeito dela
  }

  try {
    return (await provider.request({
      method: "eth_sendTransaction",
      params: [params],
    })) as string;
  } catch (err) {
    // Algumas wallets (ex: MetaMask com o chain Arc já cacheado de uma sessão
    // anterior/instável) recusam o tipo EIP-1559 mesmo a chain suportando —
    // erro -32602 "does not support EIP-1559". Refaz como tx legada (gasPrice)
    // em vez de propagar o erro pro usuário.
    const code = (err as { code?: number } | null)?.code;
    const message = (err as { message?: string } | null)?.message ?? "";
    const rejectedEip1559 = code === -32602 && /EIP-1559/i.test(message);
    if (!rejectedEip1559 || !triedEip1559) throw err;

    delete params.maxFeePerGas;
    delete params.maxPriorityFeePerGas;
    try {
      params.gasPrice = (await provider.request({ method: "eth_gasPrice" })) as string;
    } catch {
      // sem gasPrice explícito — a wallet estima do jeito dela
    }
    return (await provider.request({
      method: "eth_sendTransaction",
      params: [params],
    })) as string;
  }
}

/**
 * Provider errors from injected wallets (MetaMask/Rabby) are plain
 * `{code, message}` objects, not `Error` instances — `instanceof Error`
 * misses them and `String(err)` collapses to "[object Object]".
 */
export function getErrorMessage(err: unknown): string {
  if (err && typeof err === "object" && "message" in err) {
    return String((err as { message: unknown }).message);
  }
  return String(err);
}

export function shortEvmAddress(address: string, front = 6, back = 4): string {
  if (!address || address.length <= front + back + 2) return address;
  return `${address.slice(0, front)}…${address.slice(-back)}`;
}
