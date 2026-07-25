import sqlalchemy

# Define the database path, ensuring it's relative to the project root
DB_URL = "sqlite:///xiao_lee.db"

def verify_tables():
    """Connects to the database and lists all table names."""
    try:
        engine = sqlalchemy.create_engine(DB_URL)
        with engine.connect() as connection:
            inspector = sqlalchemy.inspect(engine)
            table_names = inspector.get_table_names()
            
            print("--- Database Table Verification ---")
            if table_names:
                print("Tables found:")
                for name in sorted(table_names):
                    print(f"- {name}")
            else:
                print("No tables found in the database.")
            
            # Check for the specific tables from Phase 2
            expected_tables = {
                'auth_tokens',
                'pending_transfers',
                'campaigns',
                'campaign_participants'
            }
            found_tables = set(table_names)
            missing_tables = expected_tables - found_tables
            
            print("\n--- Phase 2 Verification ---")
            if not missing_tables:
                print("✅ SUCCESS: All new tables from Phase 2 were created correctly.")
            else:
                print(f"❌ FAILED: The following tables are missing: {', '.join(sorted(missing_tables))}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    verify_tables() 