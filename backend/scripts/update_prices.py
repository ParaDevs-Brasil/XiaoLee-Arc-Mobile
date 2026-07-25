import asyncio
import logging
import sys
import os

# Add project root to path to allow for local module imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from swaps.price_manager import PriceManager
from database.database import init_db
from database.base import Base

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def main():
    """
    Initializes the PriceManager and calls the refresh method to update
    token prices from an external API.
    """
    # --- Create tables if they don't exist ---
    engine, session_factory = init_db()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # -----------------------------------------

    logging.info("--- Iniciando a atualização de preços dos tokens ---")
    
    price_manager = PriceManager()
    
    result = await price_manager.refresh()
    
    if result.get("success"):
        logging.info(f"✅ Sucesso! {result.get('updated', 0)} tokens foram atualizados.")
        logging.info("Preços atualizados:")
        prices = result.get('prices', {})
        for symbol, price in prices.items():
            print(f"  - {symbol}: ${price:.4f}")
    else:
        logging.error(f"❌ Falha na atualização de preços: {result.get('error', 'Erro desconhecido')}")
        
    logging.info("--- Atualização de preços concluída ---")

if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(main()) 