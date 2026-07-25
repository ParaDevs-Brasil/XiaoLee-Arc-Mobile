import sqlite3

def fix_database():
    # Fix test database
    conn = sqlite3.connect('test_xiao_lee.db')
    
    try:
        # Add platform column if it doesn't exist
        conn.execute('ALTER TABLE dmlogs ADD COLUMN platform TEXT DEFAULT "twitter"')
        print("✅ Added platform column to dmlogs")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("✅ Platform column already exists")
        else:
            print(f"⚠️  Error: {e}")
    
    conn.commit()
    conn.close()
    
    # Fix main database
    try:
        conn = sqlite3.connect('data/xiao_lee.db')
        
        try:
            conn.execute('ALTER TABLE dmlogs ADD COLUMN platform TEXT DEFAULT "twitter"')
            print("✅ Added platform column to main dmlogs")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("✅ Platform column already exists in main DB")
            else:
                print(f"⚠️  Error in main DB: {e}")
        
        conn.commit()
        conn.close()
    except:
        print("ℹ️  Main database doesn't exist yet")

def fix_db_paths():
    # Connect to the database in the new 'data' directory
    conn = sqlite3.connect('data/xiao_lee.db')
    cursor = conn.cursor()

    # Example of a fix - this part would need to be adapted
    # For now, just connecting is the main test
    print("Successfully connected to data/xiao_lee.db")
    
    # Close connection
    conn.close()

if __name__ == "__main__":
    fix_database()
    fix_db_paths() 