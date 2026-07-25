import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any
from sqlalchemy import text
from database.database import init_db

logger = logging.getLogger(__name__)

class PriceManager:
    def __init__(self, db_session_factory=None):
        self.api_url = "https://piperxdb.piperxprotocol.workers.dev/api/piperxapi/getAllTokenPrices"
        self.headers = {
            "Content-Type": "application/json",
            "Origin": "https://app.piperx.xyz",
            "Referer": "https://app.piperx.xyz/"
        }
        
        self.token_addresses = [
            "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
            "0x1514000000000000000000000000000000000000",
            "0x855bd6a8c5046d97c4e063e90e40f0f010d5423a",
            "0x2f7f07691615188b07ea8198cf47a8bb11a3f2fc",
            "0xf1815bd50389c46847f0bda824ec8da914045d14",
            "0xbab93b7ad7fe8692a878b95a8e689423437cc500",
            "0x5267f7ee069ceb3d8f1c760c215569b79d0685ad",
            "0xd07faed671decf3c5a6cc038dad97c8efdb507c0",
            "0x5a212776066b81e449fe74396cce368dc4b14043",
            "0xa4f5c615f72ddeb2220471694fff1c0c3de051e1",
            "0x1a925792d2dabaddc52fc929a2f1e3225bcfa611",
            "0x79925eb7bafa8d227c4fc0c283d03292d5cadc7e"
        ]
       
        if db_session_factory:
            self.db_session_factory = db_session_factory
        else:
            _, self.db_session_factory = init_db()
    
    def convert_price(self, raw_price: str, symbol: str) -> float:
        """Convert API price string to float value"""
        try:
            # The API already returns decimal prices as strings, just convert to float
            price = float(raw_price)
            return price
                
        except (ValueError, TypeError):
            logger.warning(f"Failed to convert price '{raw_price}' for {symbol}")
            return 0.0
    
    async def fetch_data(self) -> Dict[str, Any]:
        payload = {"addresses": self.token_addresses}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url, 
                    json=payload, 
                    headers=self.headers
                ) as response:
                    
                    if response.status == 200:
                        logger.info("API fetch successful")
                        logger.debug(f"API response: {await response.json()}")
                        return await response.json()
                    else:
                        logger.error(f"API error: {response.status}")
                        return {}
                        
        except Exception as e:
            logger.error(f"Fetch error: {e}")
            return {}
    
    async def process_data(self, api_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        processed = []
        tokens = api_data.get("tokens", {})
        
        for address, token_data in tokens.items():
            symbol = token_data.get("symbol")
            raw_price = token_data.get("now")
            
            if symbol and raw_price:
                usd_price = self.convert_price(raw_price, symbol)
                
                processed.append({
                    "symbol": symbol,
                    "address": address,
                    "price_usd": usd_price,
                    "raw_price": raw_price
                })
        
        return processed
    
    async def update_db(self, records: List[Dict[str, Any]]) -> bool:
        try:
            async with self.db_session_factory() as session:
                # Use a transaction to ensure all or nothing
                async with session.begin():
                    for record in records:
                        # Normalize symbol to uppercase before inserting/updating
                        normalized_symbol = record["symbol"].upper()
                        
                        # Using INSERT ... ON CONFLICT (UPSERT) for atomicity
                        await session.execute(
                            text("""
                                INSERT INTO tokenprices (symbol, name, price_usd, decimals, is_active, created_at, updated_at)
                                VALUES (:symbol, :name, :price_usd, :decimals, :is_active, datetime('now'), datetime('now'))
                                ON CONFLICT(symbol) DO UPDATE SET
                                    price_usd = excluded.price_usd,
                                    updated_at = datetime('now')
                            """),
                            {
                                "symbol": normalized_symbol, 
                                "name": normalized_symbol,
                                "price_usd": record["price_usd"],
                                "decimals": 18,
                                "is_active": True
                            }
                        )
                
                # The commit is handled by the 'async with session.begin()' context manager
                logger.info(f"Upserted {len(records)} prices")
                return True
                
        except Exception as e:
            logger.error(f"DB upsert error: {e}", exc_info=True)
            return False
    
    async def get_price(self, symbol: str) -> Optional[float]:
        try:
            async with self.db_session_factory() as session:
                # Normalize symbol to uppercase for consistent lookup
                normalized_symbol = symbol.upper()
                result = await session.execute(
                    text("SELECT price_usd FROM tokenprices WHERE UPPER(symbol) = :symbol"),
                    {"symbol": normalized_symbol}
                )
                row = result.fetchone()
                
                if row:
                    logger.debug(f"Price found for symbol {normalized_symbol}: {row[0]}")
                    return float(row[0])
                
                logger.warning(f"Price not found in DB for symbol: {symbol} (normalized: {normalized_symbol})")
                return None
                
        except Exception as e:
            logger.error(f"Price error for symbol {symbol}: {e}")
            return None
    
    async def get_all(self) -> Dict[str, float]:
        try:
            async with self.db_session_factory() as session:
                result = await session.execute(
                    text("SELECT symbol, price_usd FROM tokenprices ORDER BY symbol")
                )
                rows = result.fetchall()
                
                return {row[0]: float(row[1]) for row in rows}
                
        except Exception as e:
            logger.error(f"All prices error: {e}")
            return {}
    
    async def get_last_updated(self) -> str:
        """Get the timestamp of when prices were last updated."""
        try:
            async with self.db_session_factory() as session:
                result = await session.execute(
                    text("SELECT MAX(updated_at) FROM tokenprices")
                )
                row = result.fetchone()
                
                if row and row[0]:
                    # Format the timestamp in a human-readable format
                    from datetime import datetime
                    try:
                        # Try to parse the database timestamp
                        dt = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                    except:
                        # Return the raw timestamp if parsing fails
                        return str(row[0])
                
                return None
                
        except Exception as e:
            logger.error(f"Last updated timestamp error: {e}")
            return None
    
    async def refresh(self) -> Dict[str, Any]:
        logger.info("Refreshing prices...")
        
        api_data = await self.fetch_data()
        if not api_data:
            return {"error": "API failed"}
        
        records = await self.process_data(api_data)
        if not records:
            return {"error": "No data"}
        
        success = await self.update_db(records)
        if not success:
            return {"error": "DB failed"}
        
        return {
            "success": True,
            "updated": len(records),
            "timestamp": api_data.get("timestamp"),
            "prices": {r["symbol"]: r["price_usd"] for r in records}
        } 