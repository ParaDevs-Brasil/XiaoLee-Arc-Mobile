import asyncio
import sys
import os
from pathlib import Path

# Add project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from database.models import Base
from database import models # Import models to ensure they are registered with Base
from sqlalchemy.ext.asyncio import create_async_engine

async def create_all_tables():
    """Connects to the database and creates all tables defined in models.py."""
    # This logic is self-contained to avoid breaking other parts of the app.
    db_path = project_root / "xiao_lee.db"
    default_url = f"sqlite+aiosqlite:///{db_path}"
    db_url = os.getenv("DATABASE_URL", default_url)

    print(f"Connecting to database at {db_url}...")
    engine = create_async_engine(db_url)

    async with engine.begin() as conn:
        print("--- Creating all tables from models ---")
        await conn.run_sync(Base.metadata.create_all)
        print("✅ SUCCESS: All tables created successfully.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_all_tables()) 