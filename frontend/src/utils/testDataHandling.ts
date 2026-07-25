// Test utility to verify data handling with the provided JSON format

import UserData from "@/components/UserData";

// Your example JSON data
const testData = {
    "user_info": {
        "created_at": "2025-08-17T18:46:58",
        "internal_id": 3,
        "twitter_handle": "justaweb3farmer",
        "twitter_user_id": "1922442598297264128"
    },
    "balances": [
        {
            "balance": 1080,
            "priceUSD": 10.693157,
            "token": "STIP",
            "valueUSD": 11548.60956
        }
    ],
    "campaigns": [],
    "history": {
        "chat_history": [],
        "swaps": [
            {
                "amount": 30,
                "status": "completed",
                "timestamp": "2025-09-11 19:33:35",
                "to_address": null,
                "token": "STIP",
                "transaction_type": "receive_claimed",
                "type": "transaction"
            },
            {
                "amount": 10,
                "status": "completed",
                "timestamp": "2025-09-11 19:33:35",
                "to_address": null,
                "token": "STIP",
                "transaction_type": "receive_claimed",
                "type": "transaction"
            },
            {
                "amount": 10,
                "status": "completed",
                "timestamp": "2025-08-17 18:46:58",
                "to_address": null,
                "token": "STIP",
                "transaction_type": "pending_claim",
                "type": "transaction"
            }
        ],
        "transactions": []
    },
    "session_id": "d8bc169cf46b7f90f177599b49c9450766415a9a55be656f36040b22098fe896"
};

export function testDataHandling() {
    console.log("🧪 Testing data handling with provided JSON...");
    
    // Set the data
    UserData.setUserData(testData);
    
    // Verify data was set correctly
    const userData = UserData.getUserData();
    console.log("📊 User Data:", userData);
    
    // Test chat history (should be empty initially)
    const chatHistory = UserData.getChatHistory();
    console.log("💬 Chat History:", chatHistory);
    
    // Test swap history 
    const swapHistory = UserData.getSwapHistory();
    console.log("🔄 Swap History:", swapHistory);
    
    // Test transaction history
    const transactionHistory = UserData.getTransactionHistory();
    console.log("💸 Transaction History:", transactionHistory);
    
    // Test balances
    const balances = UserData.getBalances();
    console.log("💰 Balances:", balances);
    
    // Test user info
    const userInfo = UserData.getUserInfo();
    console.log("👤 User Info:", userInfo);
    
    // Test adding a local chat message
    UserData.addLocalChatMessage("Hello Xiaolee!", "Hello! How can I help you today? 😊");
    
    // Verify chat history now has messages
    const updatedChatHistory = UserData.getChatHistory();
    console.log("💬 Updated Chat History:", updatedChatHistory);
    
    // Test all activity items
    const allActivity = UserData.getAllActivityItems();
    console.log("📋 All Activity:", allActivity);
    
    return {
        userData,
        chatHistory: updatedChatHistory,
        swapHistory,
        transactionHistory,
        balances,
        userInfo,
        allActivity
    };
}

export default testDataHandling;
