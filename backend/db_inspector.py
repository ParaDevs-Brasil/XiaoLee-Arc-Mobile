import sqlite3
import pandas as pd
import json
from typing import List, Dict, Any, Optional

DB_FILE = "xiao_lee.db"

def get_recent_user_messages(user_id: int, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Get the most recent messages exchanged with a specific user.
    
    Args:
        user_id: The user's ID to retrieve messages for
        limit: Maximum number of messages to retrieve (default: 3)
        
    Returns:
        List of message objects containing content, type, and timestamp
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Query to get recent messages for the user, both from user and bot
        cursor.execute("""
            SELECT 
                content, 
                message_type, 
                created_at,
                platform,
                conversation_id
            FROM dmlogs 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (user_id, limit))
        
        messages = cursor.fetchall()
        
        # Format the results
        result = []
        for msg in reversed(messages):  # Reverse to get chronological order
            result.append({
                "content": msg[0],
                "role": "assistant" if msg[1] == "bot" else "user",
                "timestamp": msg[2],
                "platform": msg[3],
                "conversation_id": msg[4]
            })
        
        conn.close()
        return result
    
    except sqlite3.Error as e:
        print(f"❌ Error fetching user messages: {e}")
        return []

def inspect_database():
    """
    Connects to the SQLite database and inspects its schema and content.
    """
    print(f"--- 🕵️‍♂️ Starting inspection of {DB_FILE} 🕵️‍♂️ ---\n")
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # 1. List all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        
        print("📊 Found Tables:")
        if not table_names:
            print("   - No tables found in the database.")
            return
            
        for name in table_names:
            print(f"   - {name}")
        print("-" * 40)

        # 2. Inspect key tables
        key_tables = [
            'users', 'auth_tokens', 'web_sessions', 'tokenprices', 
            'tokenbalances', 'swaps', 'transactions', 'processed_dms',
            'campaigns', 'campaign_participants', 'dmlogs', 'transactionhistorys',
            'wallets', 'pending_transfers', 'swaphistorys', 
        ]
        
        for table_name in key_tables:
            if table_name in table_names:
                print(f"\n🔍 Inspecting Table: {table_name}")
                
                # Use pandas for pretty printing
                try:
                    df = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT 500;", conn)
                    
                    if df.empty:
                        print("   - Table is empty.")
                    else:
                        print("   Schema and First 5 Rows:")
                        print(df.to_string())

                except Exception as e:
                    print(f"   - Could not read table {table_name}: {e}")
            else:
                print(f"\n⚠️ Table '{table_name}' not found.")

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
        print("\n--- ✅ Inspection Complete ✅ ---")

if __name__ == "__main__":
    inspect_database() 