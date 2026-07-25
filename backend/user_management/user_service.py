import logging
import time
from typing import Dict, Optional, Any
from sqlalchemy import text, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from database.database import init_db
from database.models import User, DMLog, SwapHistory, TransactionHistory, PendingTransfer, TokenBalance
from datetime import datetime
from swaps.balance_manager import BalanceManager
from decimal import Decimal
from collections import defaultdict
from sqlalchemy import func

logger = logging.getLogger(__name__)

def model_to_dict(model_instance):
    """Converts a SQLAlchemy model instance into a dictionary."""
    if not model_instance:
        return None
    d = {c.key: getattr(model_instance, c.key) for c in model_instance.__table__.columns}
    for k, v in d.items():
        if isinstance(v, Decimal):
            d[k] = float(v)
    return d

class UserService:
    def __init__(self, db_session_factory: async_sessionmaker[AsyncSession]):
        self.db_session_factory = db_session_factory
        self.balance_manager = BalanceManager(db_session_factory)
    
    async def _process_pending_transfers(self, session: AsyncSession, new_user: User):
        """Checks for and processes any transfers pending for a new user. Returns list of claimed transfers."""
        claimed_transfers = []
        try:
            twitter_handle_normalized = new_user.twitter_handle.lstrip('@')
            
            # Find pending transfers for this user's handle
            stmt = select(PendingTransfer).where(
                PendingTransfer.recipient_twitter_handle == twitter_handle_normalized,
                PendingTransfer.status == 'pending'
            )
            result = await session.execute(stmt)
            pending_transfers = result.scalars().all()

            if not pending_transfers:
                return claimed_transfers  # Return empty list instead of None

            logger.info(f"Found {len(pending_transfers)} pending transfers for user {new_user.twitter_handle}")

            for transfer in pending_transfers:
                # 1. Add balance to the new user
                await self.balance_manager.add(
                    user_id=new_user.twitter_user_id,
                    token=transfer.token_symbol,
                    amount=Decimal(str(transfer.amount)),
                    session=session # Ensure operation is part of the same transaction
                )
                
                # 2. Mark the transfer as claimed
                transfer.status = 'claimed'
                transfer.claimed_at = datetime.utcnow()
                
                # 3. Add to claimed transfers list
                claimed_transfers.append({
                    "token": transfer.token_symbol,
                    "amount": float(transfer.amount),
                    "from_handle": transfer.from_twitter_handle,
                    "claimed_at": transfer.claimed_at.isoformat() if transfer.claimed_at else None
                })

            logger.info(f"Successfully processed {len(pending_transfers)} pending transfers for {new_user.twitter_handle}.")
            return claimed_transfers

        except Exception as e:
            logger.error(f"Error processing pending transfers for {new_user.twitter_handle}: {e}", exc_info=True)
            # We don't re-raise the exception to not fail the entire registration process
            return claimed_transfers
    
    async def _register_logic(self, session: AsyncSession, handle: str, user_id: str) -> Dict[str, Any]:
        """
        Core logic for registering a user. Must be called within an active session.
        """
        # Normalize handle - remove @ symbol and lowercase for consistent storage
        normalized_handle = handle.strip().replace('@', '').lower()
        
        # Check if user already exists
        stmt = select(User).where(User.twitter_user_id == user_id)
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            return {"success": True, "user": existing_user, "is_new_user": False, "claimed_transfers": []}

        # Create new user with normalized Twitter handle
        logger.info(f"✨ Creating new user: @{normalized_handle} (ID: {user_id})")
        new_user = User(
            twitter_handle=normalized_handle,
            twitter_user_id=user_id
            # ✅ Removed display_name and verified - they don't exist in the model
        )
        session.add(new_user)
        # Flush to ensure new_user object has its ID for subsequent operations
        await session.flush()

        # Auto-claim any pending transfers for new user
        await self._auto_claim_pending_transfers(new_user, session)

        # Airdrop for new users
        try:
            logger.info(f"Processing welcome airdrop for new user {user_id} ({handle}).")
            airdrop_success = await self.balance_manager.add(
                user_id=user_id, 
                token="STIP", 
                amount=Decimal("1000"), 
                session=session
            )
            
            if airdrop_success:
                logger.info(f"✅ Successfully airdropped 1000 STIP to {user_id}.")
            else:
                logger.error(f"❌ Failed to airdrop 1000 STIP to {user_id}.")
                
        except Exception as e:
            logger.error(f"❌ Failed to process airdrop for user {user_id}: {e}", exc_info=True)
            # Re-raise to ensure the entire transaction is rolled back
            raise

        # Process pending transfers for the new user
        claimed_transfers = await self._process_pending_transfers(session, new_user)

        logger.info(f"New user registered: {handle} ({user_id})")

        return {
            "success": True, 
            "user": new_user, 
            "is_new_user": True,
            "claimed_transfers": claimed_transfers,
            "message": "User registered successfully"
        }

    async def _auto_claim_pending_transfers(self, user: User, session: AsyncSession):
        """
        Modern auto-claim pending transfers using Twitter handle resolution
        """
        try:
            # Import the modern transfer service
            from services.modern_transfer_service import ModernTransferService
            
            # Create transfer service instance
            transfer_service = ModernTransferService()
            
            # Use the modern claiming logic
            claimed_transfers = await transfer_service.claim_pending_transfers(session, user.twitter_user_id)
            
            if len(claimed_transfers) > 0:
                logger.info(f"🎉 Auto-claimed {len(claimed_transfers)} pending transfers for @{user.twitter_handle}")
            else:
                logger.info(f"ℹ️ No pending transfers found for @{user.twitter_handle}")
                
        except Exception as e:
            logger.error(f"❌ Auto-claim failed for user @{user.twitter_handle}: {e}", exc_info=True)
            # Don't re-raise as this shouldn't prevent user registration/login

    async def register(self, handle: str, user_id: str, session: Optional[AsyncSession] = None) -> Dict[str, Any]:
        """
        Registers a new user. If a session is provided, it uses it; otherwise,
        it creates a new session and transaction. This ensures atomicity.
        """
        if session:
            # Caller is managing the session, just run the logic.
            return await self._register_logic(session, handle, user_id)
        else:
            # This method manages the session and transaction.
            try:
                async with self.db_session_factory() as new_session:
                    async with new_session.begin():
                        result = await self._register_logic(new_session, handle, user_id)
                        # No need to refresh - the result already contains the user data
                        return result
            except Exception as e:
                logger.error(f"❌ User registration failed for {handle} ({user_id}): {e}", exc_info=True)
                return {"success": False, "message": f"Registration failed: {str(e)}"}

    async def register_user(self, twitter_user_id: str, twitter_handle: str) -> Dict[str, Any]:
        """
        Public method to register a user with their Twitter ID and handle
        """
        return await self.register(twitter_handle, twitter_user_id)

    async def get_user_by_twitter_id(self, twitter_user_id: str) -> Optional[User]:
        """
        Retrieves a user by their Twitter user ID.
        """
        try:
            async with self.db_session_factory() as session:
                stmt = select(User).where(User.twitter_user_id == twitter_user_id)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
                return user
        except Exception as e:
            logger.error(f"Error retrieving user by Twitter ID {twitter_user_id}: {e}", exc_info=True)
            return None

    async def get_user_by_twitter_handle(self, twitter_handle: str) -> Optional[User]:
        """
        Retrieves a user by their Twitter handle.
        """
        try:
            # Normalize handle (remove @ if present and make lowercase for case-insensitive search)
            handle = twitter_handle.strip().replace('@', '').lower()
            
            async with self.db_session_factory() as session:
                # Use case-insensitive search with func.lower()
                from sqlalchemy import func
                stmt = select(User).where(func.lower(User.twitter_handle) == handle)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()
                return user
        except Exception as e:
            logger.error(f"Error retrieving user by handle @{twitter_handle}: {e}", exc_info=True)
            return None

    async def user_exists(self, twitter_user_id: str) -> bool:
        """
        Checks if a user exists by Twitter user ID.
        """
        user = await self.get_user_by_twitter_id(twitter_user_id)
        return user is not None

    async def sync_user_profile(self, twitter_user_id: str) -> bool:
        """
        Synchronize user profile with current Twitter data
        """
        try:
            from services.twitter_api_service import user_handle_service
            async with self.db_session_factory() as session:
                updated = await user_handle_service.sync_user_profile(twitter_user_id, session)
                if updated:
                    await session.commit()
                return updated
        except Exception as e:
            logger.error(f"❌ Profile sync failed for user {twitter_user_id}: {e}")
            return False

    async def log_transaction(self, user_id: int, transaction_type: str, token_symbol: str, 
                           amount: float, status: str, sender_twitter_handle: str = None, 
                           recipient_twitter_handle: str = None, session: Optional[AsyncSession] = None, **kwargs) -> bool:
        """
        Logs a transaction to the database.
        If session is provided, uses it; otherwise creates a new session.
        """
        try:
            transaction_data = {
                'user_id': user_id,
                'transaction_type': transaction_type,
                'token_symbol': token_symbol,
                'amount': amount,
                'status': status,
                'sender_twitter_handle': sender_twitter_handle,
                'recipient_twitter_handle': recipient_twitter_handle,
                **kwargs
            }
            
            if session:
                # Use existing session (no commit - let caller handle it)
                transaction = TransactionHistory(**transaction_data)
                session.add(transaction)
                return True
            else:
                # Create new session and commit
                async with self.db_session_factory() as new_session:
                    async with new_session.begin():
                        transaction = TransactionHistory(**transaction_data)
                        new_session.add(transaction)
                        return True
        except Exception as e:
            logger.error(f"Failed to log transaction with data {transaction_data}: {e}", exc_info=True)
            return False

    # Additional methods for compatibility...
    
    async def get_all_users(self) -> list[Dict[str, Any]]:
        """Get all users as dictionaries"""
        try:
            async with self.db_session_factory() as session:
                stmt = select(User)
                result = await session.execute(stmt)
                users = result.scalars().all()
                return [model_to_dict(user) for user in users]
        except Exception as e:
            logger.error(f"Error getting all users: {e}", exc_info=True)
            return []

    async def get_user_count(self) -> int:
        """Get total number of users"""
        try:
            async with self.db_session_factory() as session:
                stmt = select(func.count(User.id))
                result = await session.execute(stmt)
                return result.scalar() or 0
        except Exception as e:
            logger.error(f"Failed to get user count: {e}", exc_info=True)
            return 0
    
    async def log_transaction(self, session: Optional[AsyncSession] = None, **kwargs) -> bool:
        """
        Logs a transaction to the database using keyword arguments for flexibility.
        If session is provided, uses it; otherwise creates a new session.
        """
        try:
            if session:
                # Use existing session (no commit - let caller handle it)
                tx_log = TransactionHistory(**kwargs)
                session.add(tx_log)
                return True
            else:
                # Create new session and commit
                async with self.db_session_factory() as new_session:
                    async with new_session.begin():
                        # The kwargs directly map to the TransactionHistory model fields.
                        # This is flexible for different transaction types (e.g., internal vs. external).
                        tx_log = TransactionHistory(**kwargs)
                        new_session.add(tx_log)
                    return True
        except Exception as e:
            logger.error(f"Failed to log transaction with data {kwargs}: {e}", exc_info=True)
            return False

    async def get_user_activity(self, user_id: int, limit: int = 20) -> Dict[str, Any]:
        """Get recent user activity across all systems"""
        try:
            async with self.db_session_factory() as session:
                result = await session.execute(
                    text("""SELECT from_token, to_token, from_amount, to_amount, created_at, 'swap' as type
                           FROM swaphistorys WHERE user_id = :user_id 
                           ORDER BY created_at DESC LIMIT :limit"""),
                    {"user_id": user_id, "limit": limit}
                )
                swaps = result.fetchall()
                
                result = await session.execute(
                    text("""SELECT content, message_type, created_at, 'dm' as type
                           FROM dmlogs WHERE user_id = :user_id 
                           ORDER BY created_at DESC LIMIT :limit"""),
                    {"user_id": user_id, "limit": limit}
                )
                dms = result.fetchall()
                
                activity = []
                
                for swap in swaps:
                    activity.append({
                        "type": "swap",
                        "description": f"Swapped {swap[2]} {swap[0]} → {swap[3]} {swap[1]}",
                        "timestamp": swap[4]
                    })
                
                for dm in dms:
                    activity.append({
                        "type": "dm",
                        "description": f"DM ({dm[1]}): {dm[0][:50]}...",
                        "timestamp": dm[2]
                    })
                
                activity.sort(key=lambda x: x['timestamp'], reverse=True)
                
                return {"activity": activity[:limit]}
                
        except Exception as e:
            logger.error(f"Get user activity failed for {user_id}: {e}", exc_info=True)
            return {"activity": []}

    async def log_dm(self, user_id: int, content: str, message_type: str, platform: str = "twitter", conversation_id: str = None) -> bool:
        """Logs a single DM to the database."""
        try:
            async with self.db_session_factory() as session:
                log_entry = DMLog(
                    user_id=user_id,
                    content=content,
                    message_type=message_type,
                    platform=platform,
                    conversation_id=conversation_id
                )
                session.add(log_entry)
                await session.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to log DM for user {user_id}: {e}", exc_info=True)
            return False

    async def list_users(self) -> list:
        """List all users in the system."""
        try:
            async with self.db_session_factory() as session:
                result = await session.execute(select(User))
                users = result.scalars().all()
                return [model_to_dict(user) for user in users]
        except Exception as e:
            logger.error(f"Failed to list users: {e}", exc_info=True)
            return []