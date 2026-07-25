import logging
from typing import Dict, Optional
from decimal import Decimal, InvalidOperation
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from contextlib import asynccontextmanager
from database.database import init_db

logger = logging.getLogger(__name__)

class BalanceManager:
    def __init__(self, db_session_factory: async_sessionmaker[AsyncSession]):
        self.db_session_factory = db_session_factory
        # Initialize transaction history service lazily to avoid circular imports
        self._transaction_history = None

    @property
    def transaction_history(self):
        if self._transaction_history is None:
            from user_management.transaction_history_service import TransactionHistoryService
            self._transaction_history = TransactionHistoryService(self.db_session_factory)
        return self._transaction_history

    @asynccontextmanager
    async def _session_scope(self, session: Optional[AsyncSession] = None):
        """Provide a transactional scope around a series of operations."""
        if session:
            yield session
        else:
            async with self.db_session_factory() as new_session:
                async with new_session.begin():
                    yield new_session

    async def get(self, user_id: str, token: str, session: Optional[AsyncSession] = None) -> Decimal:
        try:
            async with self._session_scope(session) as s:
                result = await s.execute(
                    text("SELECT balance FROM tokenbalances WHERE user_id = :user_id AND token_symbol = :token"),
                    {"user_id": user_id, "token": token}
                )
                row = result.fetchone()
                return Decimal(row[0]) if row else Decimal('0.0')
        except Exception as e:
            logger.error(f"Get balance failed: {e}")
            return Decimal('0.0')
    
    async def set(self, user_id: str, token: str, amount: Decimal, session: Optional[AsyncSession] = None) -> bool:
        try:
            # Convert Decimal to float for DB compatibility
            balance_float = float(amount)
            async with self._session_scope(session) as s:
                result = await s.execute(
                    text("SELECT id FROM tokenbalances WHERE user_id = :user_id AND token_symbol = :token"),
                    {"user_id": user_id, "token": token}
                )
                existing = result.fetchone()
                
                if existing:
                    await s.execute(
                        text("UPDATE tokenbalances SET balance = :balance, updated_at = datetime('now') WHERE user_id = :user_id AND token_symbol = :token"),
                        {"user_id": user_id, "token": token, "balance": balance_float}
                    )
                else:
                    await s.execute(
                        text("""INSERT INTO tokenbalances 
                               (user_id, token_symbol, balance, created_at, updated_at) 
                               VALUES (:user_id, :token, :balance, datetime('now'), datetime('now'))"""),
                        {"user_id": user_id, "token": token, "balance": balance_float}
                    )
                return True
        except Exception as e:
            logger.error(f"Set balance failed: {e}")
            return False

    async def add(self, user_id: str, token: str, amount: Decimal, session: Optional[AsyncSession] = None) -> bool:
        try:
            async with self._session_scope(session) as s:
                current = await self.get(user_id, token, session=s)
                return await self.set(user_id, token, current + amount, session=s)
        except InvalidOperation:
            logger.error(f"Invalid amount '{amount}' for add operation.")
            return False

    async def subtract(self, user_id: str, token: str, amount: Decimal, session: Optional[AsyncSession] = None) -> bool:
        try:
            logger.debug(f"🔄 [SUBTRACT DEBUG] Starting subtract: {amount} {token} from user {user_id}")
            async with self._session_scope(session) as s:
                current = await self.get(user_id, token, session=s)
                logger.debug(f"🔄 [SUBTRACT DEBUG] Current balance: {current} {token}")
                
                if current < amount:
                    logger.warning(f"🔄 [SUBTRACT DEBUG] Insufficient funds: has {current}, needs {amount}")
                    return False
                
                new_balance = current - amount
                logger.debug(f"🔄 [SUBTRACT DEBUG] New balance will be: {new_balance} {token}")
                
                result = await self.set(user_id, token, new_balance, session=s)
                logger.debug(f"🔄 [SUBTRACT DEBUG] Set balance result: {result}")
                
                return result
        except InvalidOperation:
            logger.error(f"🔄 [SUBTRACT DEBUG] Invalid amount '{amount}' for subtract operation.")
            return False

    async def transfer(self, from_user: str, to_user: str, token: str, amount: Decimal, session: Optional[AsyncSession] = None) -> bool:
        try:
            print(f"🔄 [TRANSFER DEBUG] Initiating transfer of {amount} {token} from {from_user} to {to_user}")
            logger.info(f"🔄 [TRANSFER DEBUG] Starting transfer: {amount} {token} from {from_user} to {to_user}")
            
            async with self._session_scope(session) as s:
                # Check sender's balance first
                
                from_balance = await self.get(from_user, token, session=s)
                logger.info(f"🔄 [TRANSFER DEBUG] Sender {from_user} current balance: {from_balance} {token}")
                
                if from_balance < amount:
                    logger.warning(f"🔄 [TRANSFER DEBUG] Transfer failed: Insufficient funds for {from_user}. Has {from_balance}, needs {amount}")
                    return False
                
                logger.info(f"🔄 [TRANSFER DEBUG] Sufficient funds confirmed. Proceeding with balance operations...")
                #Check recipient's balance before transfer
                to_balance = await self.get(to_user, token, session=s)
                if to_balance is None:
                    #Create a wallet for the recipient if it doesn't exist
                    logger.info(f"🔄 [TRANSFER DEBUG] Recipient {to_user} does not have a balance record. Creating one...")
                    await self.set(to_user, token, Decimal('0.0'), session=s)
                

                # Subtract from sender
                ok1 = await self.subtract(from_user, token, amount, session=s)
                logger.info(f"🔄 [TRANSFER DEBUG] Subtract from sender result: {ok1}")
                
                if ok1:
                    # Check sender balance after subtraction
                    new_from_balance = await self.get(from_user, token, session=s)
                    logger.info(f"🔄 [TRANSFER DEBUG] Sender {from_user} balance after subtract: {new_from_balance} {token}")
                
                # Add to recipient
                ok2 = await self.add(to_user, token, amount, session=s)
                logger.info(f"🔄 [TRANSFER DEBUG] Add to recipient result: {ok2}")
                
                if ok2:
                    # Check recipient balance after addition
                    to_balance = await self.get(to_user, token, session=s)
                    logger.info(f"🔄 [TRANSFER DEBUG] Recipient {to_user} balance after add: {to_balance} {token}")
                
                # Log transfer transaction if both operations succeeded
                if ok1 and ok2:
                    logger.info(f"🔄 [TRANSFER DEBUG] Both balance operations successful. Logging transaction...")
                    
                    try:
                        await self.transaction_history.log_transfer(
                            from_user_id=from_user,
                            to_user_id=to_user,
                            token=token,
                            amount=amount,
                            session=s
                        )
                        logger.info(f"🔄 [TRANSFER DEBUG] Transaction logged successfully")
                    except Exception as log_error:
                        logger.error(f"🔄 [TRANSFER DEBUG] Failed to log transaction: {log_error}")
                        # Note: We don't return False here as the transfer itself succeeded
                else:
                    logger.error(f"🔄 [TRANSFER DEBUG] Transfer failed - subtract: {ok1}, add: {ok2}")
                
                final_result = ok1 and ok2
                logger.info(f"🔄 [TRANSFER DEBUG] Transfer completed. Final result: {final_result}")
                
                return final_result
                
        except InvalidOperation as e:
            logger.error(f"🔄 [TRANSFER DEBUG] Invalid amount '{amount}' for transfer operation: {e}")
            return False
        except Exception as e:
            logger.error(f"🔄 [TRANSFER DEBUG] Transfer failed with exception: {e}", exc_info=True)
            return False

    async def get_all(self, user_id: str, session: Optional[AsyncSession] = None) -> list[dict[str, any]]:
        try:
            async with self._session_scope(session) as s:
                query = text("""
                    SELECT
                        tb.token_symbol,
                        tb.balance,
                        tp.price_usd
                    FROM
                        tokenbalances tb
                    LEFT JOIN
                        tokenprices tp ON UPPER(tb.token_symbol) = UPPER(tp.symbol)
                    WHERE
                        tb.user_id = :user_id AND tb.balance > 0
                """)
                result = await s.execute(query, {"user_id": user_id})
                rows = result.fetchall()
                
                balances = []
                for row in rows:
                    balance = Decimal(str(row[1]))
                    price_usd = Decimal(str(row[2])) if row[2] is not None else Decimal('0')
                    value_usd = balance * price_usd
                    balances.append({
                        "token": row[0],
                        "balance": float(balance),
                        "priceUSD": float(price_usd),
                        "valueUSD": float(value_usd)
                    })
                return balances
        except Exception as e:
            logger.error(f"Get all failed: {e}")
            return []

    async def has_balance(self, user_id: str, token: str, amount: Decimal, session: Optional[AsyncSession] = None) -> bool:
        try:
            balance = await self.get(user_id, token, session=session)
            return balance >= amount
        except InvalidOperation:
            logger.error(f"Invalid amount '{amount}' for has_balance check.")
            return False