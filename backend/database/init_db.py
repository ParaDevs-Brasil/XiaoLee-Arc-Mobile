import asyncio
from sqlalchemy import text
from .database import init_db, create_tables, get_session
from .models import TokenPrice


async def populate_tokens():
    tokens = [
        {"symbol": "ETH", "name": "Ethereum", "price_usd": 2000.0, "decimals": 18},
        {"symbol": "USDC", "name": "USD Coin", "price_usd": 1.0, "decimals": 6},
        {"symbol": "USDT", "name": "Tether", "price_usd": 1.0, "decimals": 6},
        {"symbol": "BTC", "name": "Bitcoin", "price_usd": 45000.0, "decimals": 8},
        {"symbol": "STORY", "name": "Story Protocol", "price_usd": 0.5, "decimals": 18},
    ]
    
    async for session in get_session():
        result = await session.execute(text("SELECT COUNT(*) FROM tokenprices"))
        if result.scalar() > 0:
            print("Tokens already exist")
            return
        
        for token_data in tokens:
            token = TokenPrice(**token_data)
            session.add(token)
        
        await session.commit()
        print(f"Added {len(tokens)} tokens")


async def main():
    print("Setting up database...")
    
    init_db()
    await create_tables()
    await populate_tokens()
    
    print("Database ready!")


if __name__ == "__main__":
    asyncio.run(main()) 