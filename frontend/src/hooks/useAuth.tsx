import api from "@/api/api";
import UserData from "@/components/UserData";
import { DetailedDossier } from "@/interfaces";

export interface AuthStatus {
    status: "active" | "expired" | "pending";
    session_id?: string;
}

interface AuthContextLike {
    setUserData: (data: DetailedDossier | null) => void;
    setAuthenticated: (authenticated: boolean) => void;
    setLoading: (loading: boolean) => void;
}

export default async function handleAuth(
    token: string,
    authContext?: AuthContextLike
): Promise<AuthStatus> {
    try {        
        console.log("🔐 Checking auth status with token:", token);
        
        const response = await api.get("/auth/status/"+token);
        console.log("🔐 Auth response:", response.data);
        
        if (response.data.status === "active") {
            // Set the twitter_user_id for future API calls
            UserData.setTwitterUserId(response.data.twitter_user_id);
            
            // Set the session_id if provided
            if (response.data.session_id) {
                UserData.setSessionId(response.data.session_id);
            }
            
            const user = await api.get(`/user/` + response.data.twitter_user_id);
           
            // Set user data in UserData singleton
            if (user.data.dossier) {
                // The backend provides DetailedDossier format
                const dossierData: DetailedDossier & { session_id?: string } = {
                    ...user.data.dossier,
                    session_id: response.data.session_id
                };
                UserData.setUserData(dossierData);
                
                // Update auth context
                if (authContext) {
                    authContext.setUserData(user.data.dossier);
                    authContext.setAuthenticated(true);
                }
            }
        } else {
            // Auth failed or expired - clear data
            UserData.clearData();
            
            // Update auth context
            if (authContext) {
                authContext.setAuthenticated(false);
                authContext.setUserData(null);
            }
        }
        
        if (authContext) {
            authContext.setLoading(false);
        }

        return {
            status: response.data.status,
            session_id: response.data.session_id
        };
    } catch (error) {
        console.error("❌ Error in useAuth:", error);
        throw error;
    }
}
