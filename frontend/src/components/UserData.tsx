import fetchUserData from "@/hooks/useUser";
import { 
  TypeUserData, 
  UserInfo, 
  History, 
  DetailedDossier,
  ActivityItem, 
  SwapHistoryItem, 
  ChatHistoryItem,
  TransactionHistoryItem,
  TokenBalance,
  UserCampaignParticipation
} from "@/interfaces";

type UserDataPayload = TypeUserData | DetailedDossier;


export default class UserData {
  private static user_info: UserInfo;
  private static balances: TokenBalance[] = [];
  private static campaigns: UserCampaignParticipation[] = [];
  private static history: History = { 
    chat_history: [], 
    swaps: [], 
    transactions: [] 
  };
  private static twitter_user_id: string = "";
  private static session_id: string = "";
  private static devnet_wallet_public_key: string = "";
  private static rawSwapData: SwapHistoryItem[] = [];
  private static rawChatHistory: ChatHistoryItem[] = [];
  private static rawTransactionData: TransactionHistoryItem[] = [];

  static getUserData(): TypeUserData {
    return {
      user_info: this.user_info,
      balances: this.balances,
      campaigns: this.campaigns,
      history: this.history,
      session_id: this.session_id,
    };
  }
  
  static getHistory(): History {
    return this.history;
  }
  
  // Get specific history sections
  static getChatHistory(): ChatHistoryItem[] {
    const inMemory = this.history?.chat_history || [];
    if (typeof window === 'undefined') return inMemory;
    try {
      const stored = localStorage.getItem('xiaolee_chat_history');
      if (!stored) return inMemory;
      const fromStorage: ChatHistoryItem[] = JSON.parse(stored);
      const inMemoryTs = new Set(inMemory.map(h => h.user_message.timestamp));
      const unique = fromStorage.filter(h => !inMemoryTs.has(h.user_message.timestamp));
      return [...unique, ...inMemory].sort(
        (a, b) => new Date(a.user_message.timestamp).getTime() - new Date(b.user_message.timestamp).getTime()
      );
    } catch {
      return inMemory;
    }
  }
  
  static getSwapHistory(): SwapHistoryItem[] {
    return this.history.swaps || [];
  }
  
  static getTransactionHistory(): TransactionHistoryItem[] {
    return this.history.transactions || [];
  }
  
  // Get combined activity items from all history sources
  static getAllActivityItems(): ActivityItem[] {
    const items: ActivityItem[] = [];
    
    // Add transaction history converted to activity items
    items.push(...this.getTransactionHistory().map(tx => ({
      type: 'transaction' as const,
      description: `${tx.transaction_type}: ${tx.amount} ${tx.token_symbol}`,
      timestamp: tx.created_at,
      amount: tx.amount,
      token: tx.token_symbol,
      status: tx.status
    })));
    
    // Add swaps as activity items (handle new format)
    items.push(...this.getSwapHistory().map(swap => ({
      type: 'swap' as const,
      description: `${swap.transaction_type}: ${swap.amount} ${swap.token}`,
      timestamp: swap.timestamp,
      amount: swap.amount.toString(),
      token: swap.token,
      status: swap.status
    })));
    
    // Add chat history as activity items
    items.push(...this.getChatHistory().map(chat => ({
      type: 'dm' as const,
      description: `Chat: ${chat.user_message.content.slice(0, 50)}...`,
      timestamp: chat.user_message.timestamp
    })));
    
    // Sort by timestamp (most recent first)
    return items.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  }
  
  static getUserInfo(): UserInfo {
    return this.user_info;
  }  
  
  static getBalances(): TokenBalance[] {
    return this.balances;
  }
  
  static getUserCampaigns(): UserCampaignParticipation[] {
    return this.campaigns;
  }

  static getDevnetWalletPublicKey(): string {
    return this.devnet_wallet_public_key;
  }
  
  static getSessionId(): string {
    // Prefer twitter_user_id (set after real auth) over guest session token
    if (this.user_info?.twitter_user_id && this.user_info.twitter_user_id.trim()) {
      return this.user_info.twitter_user_id;
    }
    if (!this.session_id && typeof window !== 'undefined') {
      const stored = window.localStorage.getItem('xiaolee_devnet_session');
      if (stored && stored.trim()) {
        this.session_id = stored.trim();
      }
    }
    return this.session_id;
  }

  static hasCampaignIdentity(): boolean {
    if (this.session_id && this.session_id.trim()) {
      return true;
    }

    if (typeof window === 'undefined') {
      return false;
    }

    const stored = window.localStorage.getItem('xiaolee_devnet_session');
    return !!stored && stored.trim().length > 0;
  }

  static getOrCreateDevnetSession(): string {
    const existing = this.getSessionId();
    if (existing) {
      // Ensure user_info is populated even when returning an existing session
      if (!this.user_info || !this.user_info.twitter_user_id) {
        this.user_info = {
          twitter_user_id: existing,
          twitter_handle: existing.slice(0, 20),
          created_at: new Date().toISOString(),
        };
      }
      return existing;
    }

    if (typeof window === 'undefined') {
      return "";
    }

    // Always create a guest session — Phantom/wallet connect must be explicit
    const token = `devnet_guest_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;

    window.localStorage.setItem('xiaolee_devnet_session', token);
    this.session_id = token;

    if (!this.twitter_user_id || this.twitter_user_id.trim() === "") {
      this.twitter_user_id = token;
    }

    if (!this.user_info || !this.user_info.twitter_user_id) {
      this.user_info = {
        twitter_user_id: token,
        twitter_handle: token.slice(0, 20),
        created_at: new Date().toISOString(),
      };
    }

    return token;
  }

  static setDevnetWalletSession(publicKey: string): string {
    const sanitized = publicKey.trim();
    if (!sanitized) {
      return this.getOrCreateDevnetSession();
    }

    const token = `devnet_wallet_${sanitized}`;
    this.session_id = token;
    this.twitter_user_id = token;
    this.devnet_wallet_public_key = sanitized;

    if (typeof window !== 'undefined') {
      window.localStorage.setItem('xiaolee_devnet_session', token);
    }

    this.user_info = {
      twitter_user_id: token,
      twitter_handle: `wallet_${sanitized.slice(0, 8)}`,
      created_at: new Date().toISOString(),
    };

    return token;
  }
  
  static setSessionId(session_id: string): void {
    this.session_id = session_id;
    console.log("🔐 Session ID set:", session_id);
  }
  
  static setUserData(data: UserDataPayload): void {    
    console.log("📊 Setting user data:", data);
    
    // Handle the actual backend response format (based on your JSON)
    if (data.user_info && data.balances && Array.isArray(data.balances) && data.history) {
      this.user_info = data.user_info;
      this.balances = data.balances;
      this.campaigns = data.campaigns || [];
      
      // Handle the backend history format
      this.history = { 
        chat_history: data.history.chat_history || [],
        swaps: data.history.swaps || [],
        transactions: data.history.transactions || []
      };
      
      // Store raw data for components that need it
      this.rawSwapData = data.history.swaps || [];
      this.rawChatHistory = data.history.chat_history || [];
      this.rawTransactionData = data.history.transactions || [];
      
    } else if ('balances' in data && Array.isArray(data.balances)) {
      // Backend DetailedDossier format (legacy)
      this.user_info = data.user_info;
      this.balances = data.balances;
      this.campaigns = data.campaigns || [];
      
      // Store raw data for components that need it
      this.rawSwapData = (data as DetailedDossier).history.swaps || [];
      this.rawChatHistory = (data as DetailedDossier).history.chat_history || [];
      this.rawTransactionData = (data as DetailedDossier).history.transactions || [];
      
      // Store the backend history structure directly
      this.history = { 
        chat_history: (data as DetailedDossier).history?.chat_history || [],
        swaps: (data as DetailedDossier).history?.swaps || [],
        transactions: (data as DetailedDossier).history?.transactions || []
      };
    } else {
      // Frontend TypeUserData format (legacy)
      this.user_info = data.user_info || { twitter_user_id: "", twitter_handle: "", created_at: new Date().toISOString() };
      this.balances = data.balances || [];
      this.campaigns = data.campaigns || [];
      this.history = {
        chat_history: data.history?.chat_history || [],
        swaps: data.history?.swaps || [],
        transactions: data.history?.transactions || []
      };
    }
    
    // Set session_id if provided
    if ('session_id' in data && data.session_id) {
      this.session_id = data.session_id;
    }
    
    console.log("🔍 Processed user data:", {
      user_info: this.user_info,
      balances_count: this.balances?.length || 0,
      chat_history_count: this.history?.chat_history?.length || 0,
      swaps_count: this.history?.swaps?.length || 0,
      transactions_count: this.history?.transactions?.length || 0
    });
    
    // Persist user_info to localStorage so it survives page refresh
    if (typeof window !== 'undefined' && this.user_info?.twitter_user_id) {
      window.localStorage.setItem('xiaolee_user_info', JSON.stringify(this.user_info));
    }

    // Dispatch custom event when data is loaded (only on client side)
    console.log("🎉 User data loaded, dispatching event");
    if (typeof window !== 'undefined') {
      const event = new CustomEvent('userDataLoaded', {
        detail: this.getUserData()
      });
      window.dispatchEvent(event);
    }
  }
  
  static async fetchData(): Promise<boolean> {
    try {
      // Guard: do not call API with an empty user ID
      if (!this.twitter_user_id || this.twitter_user_id.trim() === "") {
        console.log("⏭ fetchData skipped — no twitter_user_id set");
        return false;
      }
      const data = await fetchUserData(this.twitter_user_id);
      console.log("📊 Data fetched successfully:", data);
      this.setUserData(data.dossier);
      return true;
    } catch (error) {
      console.error("❌ Error fetching data:", error);
      return false;
    }
  }  
  
  static setTwitterUserId(twitter_user_id: string): void {
    this.twitter_user_id = twitter_user_id;
  }

  // Method to check if data is loaded
  static hasData(): boolean {
    return this.user_info && this.user_info.twitter_user_id !== undefined;
  }
  
  // Method to add a local chat message to history
  static addLocalChatMessage(userMessage: string, assistantResponse: string): void {
    const timestamp = new Date().toISOString();
    const newChatItem = {
      user_message: { content: userMessage, timestamp },
      assistant_response: { content: assistantResponse, timestamp: new Date(Date.now() + 1000).toISOString() }
    };

    if (!this.history) this.history = { chat_history: [], swaps: [], transactions: [] };
    if (!this.history.chat_history) this.history.chat_history = [];
    this.history.chat_history.push(newChatItem);

    // Persist to localStorage so fetchData() overwrites don't erase local messages
    if (typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem('xiaolee_chat_history');
        const existing: ChatHistoryItem[] = stored ? JSON.parse(stored) : [];
        existing.push(newChatItem);
        localStorage.setItem('xiaolee_chat_history', JSON.stringify(existing.slice(-200)));
      } catch { /* ignore */ }
    }
  }

  // Restore session + user_info from localStorage on page load (works for all auth types)
  static restoreSession(): boolean {
    if (typeof window === 'undefined') return false;

    const sessionId = window.localStorage.getItem('xiaolee_devnet_session');
    if (!sessionId) return false;

    this.session_id = sessionId;

    const cached = window.localStorage.getItem('xiaolee_user_info');
    if (cached) {
      try {
        const info = JSON.parse(cached);
        if (info?.twitter_user_id) {
          this.twitter_user_id = info.twitter_user_id;
          this.user_info = info;
          return true;
        }
      } catch { /* ignore */ }
    }

    return false;
  }

  // Method to clear all data (useful for logout)
  static clearData(): void {
    this.history = { 
      chat_history: [], 
      swaps: [], 
      transactions: [] 
    };
    this.user_info = {} as UserInfo;
    this.balances = [];
    this.campaigns = [];
    this.twitter_user_id = "";
    this.session_id = "";
    this.devnet_wallet_public_key = "";
    
    // Clear raw data
    this.rawSwapData = [];
    this.rawChatHistory = [];
    this.rawTransactionData = [];
    
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem('xiaolee_devnet_session');
      window.localStorage.removeItem('xiaolee_user_info');
      window.localStorage.removeItem('connected_wallet');
      window.localStorage.removeItem('xiaolee_google_user');
      window.localStorage.removeItem('xiaolee_chat_history');
    }

    console.log("🧹 User data cleared");
  }
  
  static verifyCampaignParticipation(campaignId: number): boolean {
    // Check if the user is participating in the campaign
    return this.campaigns.some(campaign => campaign.id === campaignId);
  }

  // Method to update campaigns data from useUserCampaigns hook
  static updateCampaigns(campaigns: UserCampaignParticipation[]): void {
    this.campaigns = campaigns;
    console.log("📊 Campaigns updated:", campaigns);
  }
}
