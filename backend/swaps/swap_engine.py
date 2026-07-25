import logging
import time
from typing import Dict, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from database.database import init_db
from .price_manager import PriceManager
from .balance_manager import BalanceManager
from user_management.transaction_history_service import TransactionHistoryService
from decimal import Decimal

logger = logging.getLogger(__name__)

class SwapEngine:
    def __init__(self, price_manager: PriceManager, balance_manager: BalanceManager):
        self.prices = price_manager
        self.balances = balance_manager
        self.transaction_history = TransactionHistoryService(balance_manager.db_session_factory)
    
    async def rate(self, from_token: str, to_token: str) -> Optional[Decimal]:
        try:
            # Refresh prices from API before calculating rate
            logger.info(f"🔄 [SWAP ENGINE] Refreshing prices before rate calculation")
            refresh_result = await self.prices.refresh()
            if not refresh_result.get("success"):
                logger.warning(f"⚠️ [SWAP ENGINE] Price refresh failed: {refresh_result.get('error')}")
            else:
                logger.info(f"✅ [SWAP ENGINE] Prices refreshed successfully")
            
            from_price = await self.prices.get_price(from_token)
            to_price = await self.prices.get_price(to_token)
            
            if from_price is None or to_price is None or to_price == 0:
                return None
            
            # Use Decimal for precision
            return Decimal(str(from_price)) / Decimal(str(to_price))
        except Exception as e:
            logger.error(f"Rate calc failed: {e}")
            return None
    
    async def calculate(self, from_token: str, to_token: str, amount: Decimal) -> Dict:
        exchange_rate = await self.rate(from_token, to_token)
        print(f"Exchange rate for {from_token} to {to_token}: {exchange_rate}")
        if exchange_rate is None:
            return {"error": "Price unavailable"}
        
        to_amount = amount * exchange_rate
        to_amount = to_amount.quantize(Decimal('1.000'))  # Adjust precision as needed
        
        return {
            "success": True,
            "from_token": from_token,
            "to_token": to_token,
            "from_amount": amount,
            "to_amount": to_amount,
            "rate": exchange_rate
        }
    
    async def validate(self, user_id: str, from_token: str, to_token: str, amount: Decimal) -> Dict:
        """Validates a swap request, checking balance and prices for both tokens."""
        if amount <= Decimal('0'):
            return {"success": False, "error": "Invalid amount. Must be positive."}
        
        if not await self.balances.has_balance(user_id, from_token, amount):
            current_balance = await self.balances.get(user_id, from_token)
            return {"success": False, "error": f"Insufficient balance. You have {current_balance} {from_token} but need {amount}."}
        
        # Refresh prices before validation
        logger.info(f"🔄 [SWAP ENGINE] Refreshing prices before validation")
        refresh_result = await self.prices.refresh()
        if not refresh_result.get("success"):
            logger.warning(f"⚠️ [SWAP ENGINE] Price refresh failed during validation: {refresh_result.get('error')}")
        
        from_price = await self.prices.get_price(from_token)
        if from_price is None:
            return {"success": False, "error": f"The token '{from_token}' is not supported for swaps at this time."}
            
        to_price = await self.prices.get_price(to_token)
        if to_price is None:
            return {"success": False, "error": f"The token '{to_token}' is not supported for swaps at this time."}
        
        return {"success": True}
    
    async def execute_swap(self, user_id: str, from_token: str, to_token: str, amount: Decimal) -> Dict:
        try:
            async with self.balances.db_session_factory() as session:
                async with session.begin():
                    validation = await self.validate(user_id, from_token, to_token, amount)
                    if not validation.get("success"):
                        return {"success": False, "response_code": "SWAP_VALIDATION_FAILED", "context": {"error": validation.get("error")}}

                    calculation = await self.calculate(from_token, to_token, amount)
                    if not calculation.get("success"):
                        return {"success": False, "response_code": "SWAP_QUOTE_FAILED", "context": {"error": calculation.get("error")}}

                    to_amount = calculation["to_amount"]

                    # Perform the swap within the transaction
                    subtract_ok = await self.balances.subtract(user_id, from_token, amount, session=session)
                    if not subtract_ok:
                        raise Exception("Subtract balance failed during swap.") # This will trigger a rollback

                    add_ok = await self.balances.add(user_id, to_token, to_amount, session=session)
                    if not add_ok:
                        raise Exception("Add balance failed during swap.") # This will trigger a rollback

                    # Log the swap within the same transaction
                    await self.log(user_id, calculation, session=session)
                    
                    # **FIX: Log transaction history for audit trail**
                    await self.transaction_history.log_swap(
                        user_id=user_id,
                        from_token=from_token,
                        to_token=to_token,
                        from_amount=amount,
                        to_amount=to_amount,
                        session=session
                    )
                    
                    await session.flush()

            # If we reach here, the transaction was committed successfully.
            return {
                "success": True,
                "response_code": "SWAP_SUCCESS",
                "context": {
                    "from_amount": amount,
                    "from_token": from_token,
                    "to_amount": to_amount,
                    "to_token": to_token
                }
            }
        except Exception as e:
            logger.error(f"Swap execution failed for user {user_id}: {e}", exc_info=True)
            return {"success": False, "response_code": "CRITICAL_SWAP_ERROR", "context": {"error": str(e)}}
    
    async def log(self, user_id: str, swap_data: Dict, session: AsyncSession) -> str:
        """Logs a completed swap to the database within a provided session."""
        swap_id = f"swap_{int(time.time())}_{user_id[:8]}"
        
        # Refresh prices before logging to get the most current USD value
        logger.info(f"🔄 [SWAP ENGINE] Refreshing prices before logging swap")
        refresh_result = await self.prices.refresh()
        if not refresh_result.get("success"):
            logger.warning(f"⚠️ [SWAP ENGINE] Price refresh failed during logging: {refresh_result.get('error')}")
        
        from_token_price = await self.prices.get_price(swap_data["from_token"])
        value_usd = 0.0
        if from_token_price:
            value_usd = float(swap_data["from_amount"]) * from_token_price

        await session.execute(
            text("""INSERT INTO swaphistorys 
                   (user_id, from_token, to_token, from_amount, to_amount, exchange_rate, value_usd, status, created_at, updated_at) 
                   VALUES (:user_id, :from_token, :to_token, :from_amount, :to_amount, :rate, :value_usd, :status, datetime('now'), datetime('now'))"""),
            {
                "user_id": user_id,
                "from_token": swap_data["from_token"],
                "to_token": swap_data["to_token"],
                "from_amount": float(swap_data["from_amount"]), # Convert Decimal for DB
                "to_amount": float(swap_data["to_amount"]),     # Convert Decimal for DB
                "rate": float(swap_data["rate"]),               # Convert Decimal for DB
                "value_usd": value_usd,
                "status": "completed"
            }
        )
        logger.info(f"Swap {swap_id} logged for user {user_id}")
        return swap_id
    
    async def history(self, user_id: str, limit: int = 10) -> list:
        try:
            async with self.balances.db_session_factory() as session:
                result = await session.execute(
                    text("""SELECT from_token, to_token, from_amount, to_amount, exchange_rate, status, created_at, value_usd 
                           FROM swaphistorys WHERE user_id = :user_id 
                           ORDER BY created_at DESC LIMIT :limit"""),
                    {"user_id": user_id, "limit": limit}
                )
                rows = result.fetchall()
                
                return [
                    {
                        "from_token": row[0],
                        "to_token": row[1],
                        "from_amount": float(row[2]),
                        "to_amount": float(row[3]),
                        "rate": float(row[4]),
                        "status": row[5],
                        "timestamp": row[6],
                        "valueUSD": float(row[7]) if row[7] is not None else None
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"History failed: {e}")
            return [] 