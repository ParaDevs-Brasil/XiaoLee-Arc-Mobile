// User-related interfaces for Xiaolee project

// User data structure matching the new backend dossier format
export interface UserInfo {
  twitter_handle: string;
  twitter_user_id: string;
  created_at: string;
  internal_id?: number;
  custodial_wallet_address?: string;
}

export interface TokenBalance {
  token: string;
  balance: number;
  priceUSD: number;
  valueUSD: number;
}

// Backend simple swap structure from the actual API response
export interface SwapHistoryItem {
  amount: number;
  status: string;
  timestamp: string;
  to_address: string | null;
  token: string;
  transaction_type: string;
  type: string;
}

// Full swap history item (for detailed swaps)
export interface DetailedSwapHistoryItem {
  id: number;
  user_id: string;
  from_token: string;
  to_token: string;
  from_amount: string;
  to_amount: string;
  exchange_rate: string;
  status: string;
  created_at: string;
  updated_at: string;
  value_usd: string;
}

// Backend transaction structure
export interface TransactionHistoryItem {
  id: number;
  amount: string;
  confirmation_blocks: number;
  created_at: string;
  error_message: string | null;
  gas_price: string | null;
  gas_used: string | null;
  recipient_twitter_handle: string;
  sender_twitter_handle: string;
  status: string;
  to_address: string | null;
  token_symbol: string;
  transaction_type: string;
  tx_hash: string | null;
  updated_at: string;
  user_id: number;
}

export interface ActivityItem {
  type: 'swap' | 'dm' | 'transaction';
  description: string;
  timestamp: string;
  amount?: string;
  token?: string;
  status?: string;
}

export interface History {
  chat_history: import('./chat').ChatHistoryItem[];
  swaps: SwapHistoryItem[];
  transactions: TransactionHistoryItem[];
}

export interface TypeUserData {
  user_info: UserInfo;
  balances: TokenBalance[];
  history: History;
  campaigns?: import('./campaign').UserCampaignParticipation[];
  session_id?: string;
}

// New detailed dossier structure from the backend
export interface DetailedDossier {
  user_info: {
    twitter_handle: string;
    twitter_user_id: string;
    internal_id: number;
    created_at: string;
  };
  balances: TokenBalance[];
  campaigns: import('./campaign').UserCampaignParticipation[];
  history: History;
}

// API Response interfaces
export interface DossierResponse {
  success: boolean;
  dossier: TypeUserData;
}

export interface DetailedDossierResponse {
  success: boolean;
  dossier: DetailedDossier;
}

// Component Props interfaces
export interface WalletProps {
  balance?: TokenBalance[];
  shouldOpen?: boolean;
  onClose?: () => void;
  onRefresh?: () => void;
  /** Sem carteira conectada: abre o fluxo universal (Arc/Solana/Stellar) em vez de conectar por conta própria. */
  onRequestConnect?: () => void;
}

export interface TransacoesProps {
  shouldOpen?: boolean;
  onClose?: () => void;
  transactions?: TransactionHistoryItem[];
  balance?: TokenBalance[];
}
