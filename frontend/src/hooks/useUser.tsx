import api from "@/api/api";

export default async function fetchUserData(id: string) {
    try {
        const response = await api.get("/user/" + id);
        console.log("👤 User data fetched:", response.data);
        return response.data;
    } catch (error) {
        console.error("Error in useChat:", error);
        throw error;
    }
}
