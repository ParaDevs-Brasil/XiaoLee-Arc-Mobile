import logging
import time
from typing import Dict, Optional, Any, List
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
    
    async def _register_logic(self, session: AsyncSession, handle: str, user_id: str) -> Dict[str, Any]:
        """
        Core logic for registering a user. Must be called within an active session.
        """
        # Check if user already exists
        stmt = select(User).where(User.twitter_user_id == user_id)
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            # Update handle if it changed (e.g., user changed their Twitter handle)
            if existing_user.twitter_handle != handle:
                logger.info(f"🔄 Updating handle for user {user_id}: @{existing_user.twitter_handle} → @{handle}")
                
                # Update previous handles history
                from services.twitter_api_service import user_handle_service
                await user_handle_service.sync_user_profile(user_id, session)
            
            # For existing users, auto-claim any pending transfers
            claimed_transfers = await self._auto_claim_pending_transfers(existing_user, session)
            return {
                "success": True, 
                "user": existing_user, 
                "is_new_user": False,
                "claimed_transfers": claimed_transfers
            }

        # Create new user with real Twitter handle
        logger.info(f"✨ Creating new user: @{handle} (ID: {user_id})")
        new_user = User(
            twitter_handle=handle,
            twitter_user_id=user_id,
            display_name=handle,  # Will be updated by profile sync
            verified=False
        )
        session.add(new_user)
        # Flush to ensure new_user object has its ID for subsequent operations
        await session.flush()

        # Auto-claim any pending transfers for new user
        claimed_transfers = await self._auto_claim_pending_transfers(new_user, session)
        logger.info(f"New user registered: {user_id} ({handle})")
        return {
            "success": True, 
            "user": new_user, 
            "is_new_user": True,
            "message": "User registered successfully",
            "claimed_transfers": claimed_transfers
        }

    async def _auto_claim_pending_transfers(self, user: User, session: AsyncSession) -> List[Dict]:
        """
        Modern auto-claim pending transfers using Twitter handle resolution
        
        Returns:
            List of claimed transfer information for notifications
        """
        try:
            # Import the modern transfer service
            from services.modern_transfer_service import ModernTransferService
            
            # Create transfer service instance
            transfer_service = ModernTransferService()
            
            # Use the modern claiming logic
            claimed_transfers = await transfer_service.claim_pending_transfers(session, user.twitter_user_id)
            
            if claimed_transfers:
                logger.info(f"🎉 Auto-claimed {len(claimed_transfers)} pending transfers for @{user.twitter_handle}")
                
                # Format claimed transfers for notification
                claimed_info = []
                for transfer in claimed_transfers:
                    claimed_info.append({
                        "from_handle": transfer.from_twitter_handle,
                        "token": transfer.token_symbol,
                        "amount": float(transfer.amount)
                    })
                return claimed_info
            else:
                logger.info(f"ℹ️ No pending transfers found for @{user.twitter_handle}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Auto-claim failed for user @{user.twitter_handle}: {e}", exc_info=True)
            return []  # Don't re-raise as this shouldn't prevent user registration/login

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
                        # Ensure the user object is accessible after the session closes
                        if result.get("user"):
                            await new_session.refresh(result["user"])
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
            # Normalize handle (remove @ if present)
            handle = twitter_handle.lstrip('@')
            
            async with self.db_session_factory() as session:
                stmt = select(User).where(User.twitter_handle == handle)
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

    async def log_transaction(self, transaction_data: Dict[str, Any]) -> bool:
        """
        Logs a transaction to the database.
        """
        try:
            async with self.db_session_factory() as session:
                async with session.begin():
                    transaction = TransactionHistory(**transaction_data)
                    session.add(transaction)
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
            logger.error(f"Error getting user count: {e}", exc_info=True)
            return 0

import logging
import time
from typing import Dict, Optional, Any
from sqlalchemy import text, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from database.database import init_db
from database.models import User, DMLog, SwapHistory, TransactionHistory, PendingTransfer, TokenBalance
from datetime import datetime
from swaps.balance_manager import BalanceManager
from decimal import Decimala
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
    
    async def _register_logic(self, session: AsyncSession, handle: str, user_id: str) -> Dict[str, Any]:
        """
        Core logic for registering a user. Must be called within an active session.
        """
        # Check if user already exists
        stmt = select(User).where(User.twitter_user_id == user_id)
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            # Update handle if it changed (e.g., user changed their Twitter handle)
            if existing_user.twitter_handle != handle:
                logger.info(f"🔄 Updating handle for user {user_id}: @{existing_user.twitter_handle} → @{handle}")
                
                # Update previous handles history
                from services.twitter_api_service import user_handle_service
                await user_handle_service.sync_user_profile(user_id, session)
            
            # For existing users, auto-claim any pending transfers
            await self._auto_claim_pending_transfers(existing_user, session)
            return {"success": True, "user": existing_user, "is_new_user": False}

        # Create new user with real Twitter handle
        logger.info(f"✨ Creating new user: @{handle} (ID: {user_id})")
        new_user = User(
            twitter_handle=handle,
            twitter_user_id=user_id,
            display_name=handle,  # Will be updated by profile sync
            verified=False
        )
        session.add(new_user)
        # Flush to ensure new_user object has its ID for subsequent operations
        await session.flush()

        # Auto-claim any pending transfers for new user
        await self._auto_claim_pending_transfers(new_user, session)
        logger.info(f"New user registered: {user_id} ({handle})")
        return {
            "success": True, 
            "user": new_user, 
            "is_new_user": True,
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
            claimed_count = await transfer_service.claim_pending_transfers(session, user.twitter_user_id)
            
            if claimed_count > 0:
                logger.info(f"🎉 Auto-claimed {claimed_count} pending transfers for @{user.twitter_handle}")
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
                        # Ensure the user object is accessible after the session closes
                        if result.get("user"):
                            await new_session.refresh(result["user"])
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
            # Normalize handle (remove @ if present)
            handle = twitter_handle.lstrip('@')
            
            async with self.db_session_factory() as session:
                stmt = select(User).where(User.twitter_handle == handle)
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

    async def log_transaction(self, transaction_data: Dict[str, Any]) -> bool:
        """
        Logs a transaction to the database.
        """
        try:
            async with self.db_session_factory() as session:
                async with session.begin():
                    transaction = TransactionHistory(**transaction_data)
                    session.add(transaction)
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
            logger.error(f"Error getting user count: {e}", exc_info=True)
            return 0
