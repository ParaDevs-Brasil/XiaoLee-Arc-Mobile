import api from "@/api/api";
import UserData from "@/components/UserData";

export default async function sendChatMessage(
    msg: string
    
   
) {
    
    try {        

        // Wallet universal do Connect Wallet (navbar) — xiaolee_wallet: {address, chain, walletName}
        let connectedWallet: string | null = null;
        let connectedChain: string | null = null;
        if (typeof window !== "undefined") {
            try {
                const stored = localStorage.getItem("xiaolee_wallet");
                if (stored) {
                    const parsed = JSON.parse(stored) as { address?: string; chain?: string };
                    connectedWallet = parsed.address ?? null;
                    connectedChain = parsed.chain ?? null;
                }
            } catch { /* storage corrompido — segue sem wallet */ }
            // legado: chave antiga usada pelo fluxo Phantom
            connectedWallet = connectedWallet ?? localStorage.getItem("connected_wallet");
        }
        const stellarAccount = typeof window !== "undefined" ? localStorage.getItem("stellar_account") : null;
        // Prefer custodial/Web3Auth wallet over injected wallet for authenticated users
        const walletAddress = UserData.getUserInfo()?.custodial_wallet_address || connectedWallet || undefined;
        const walletChain = connectedChain ?? undefined;

        if (!UserData.hasData()) {
            console.log("🔍 Enviando como usuário anônimo (sem dados no UserData)");
            const response = await api.post("/chat", {
                message: msg,
                ...(walletAddress && { wallet_address: walletAddress }),
                ...(walletChain && { wallet_chain: walletChain }),
                ...(stellarAccount && { stellar_wallet: stellarAccount }),
            });
            console.log("📬 Mensagem anônima enviada:", response.data);
            return response.data;
        } else {
            console.log("🔍 Enviando como usuário autenticado:", UserData.getSessionId());

            const response = await api.post("/chat", {
                message: msg,
                ...(walletAddress && { wallet_address: walletAddress }),
                ...(walletChain && { wallet_chain: walletChain }),
                ...(stellarAccount && { stellar_wallet: stellarAccount }),
            },
            {
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${UserData.getSessionId()}` // Usando o twitter_user_id como token de autenticação
                },
            });

            console.log("📬 Mensagem autenticada enviada:", response.data);
            return response.data;
        }
    } catch (error) {
        console.error("❌ Error in useChat:", error);
        throw error;
    }
}
