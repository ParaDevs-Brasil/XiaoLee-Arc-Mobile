import logging
import time
from typing import Dict, Optional, Any, List
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from user_management.user_service import UserService
from user_management.wallet_service import WalletService
from .auth_service import AuthService
from database.models import User, DMLog

logger = logging.getLogger(__name__)

class UserManager:
    """Central user management system integrating all Phase 8 components"""
    
    def __init__(self, db_session_factory: async_sessionmaker[AsyncSession]):
        self.db_session_factory = db_session_factory
        self.user_service = UserService(self.db_session_factory)
        self.wallet_service = WalletService(self.db_session_factory)
        self.auth_service = AuthService(self.db_session_factory)
    
    async def handle_new_user_interaction(
        self, twitter_handle: str, twitter_user_id: str, platform: str = "twitter"
    ) -> Dict[str, Any]:
        """
        Handles the logic for a new user interaction.
        This is the primary entry point when a user interacts for the first time.
        """
        logger.info(f"Handling new interaction for Twitter ID: {twitter_user_id}")
        
        # We don't need to check for the user here, `register` handles it.
        # This simplifies the logic flow.
        registration_result = await self.user_service.register(
            handle=twitter_handle,
            user_id=twitter_user_id
        )

        if not registration_result.get("success"):
            return {"success": False, "error": "User registration failed."}

        user = registration_result["user"]
        is_new_user = registration_result["is_new"]

        # If it's a new user, create a wallet.
        if is_new_user:
            logger.info(f"New user registration detected for {twitter_handle}. Creating wallet.")
            wallet_result = await self.wallet_service.create_wallet(user.id)
            if not wallet_result.get("success"):
                logger.error(f"Failed to create wallet for new user {user.id}. This is a critical error.")
                # We might want to decide on a rollback strategy here in a real-world scenario.
                return {"success": False, "error": "Wallet creation failed for new user."}
        
        logger.info(f"User interaction handled successfully for user_id: {user.id}")
        return {"success": True, "user": user, "is_new": is_new_user}
    
    async def get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get complete user profile with all data"""
        try:
            user_info = await self.user_service.get_user_by_id(user_id)
            if not user_info:
                return None
            
            wallet_info = await self.wallet_service.get_user_wallet(user_id)
            
            balances = await self.wallet_service.get_wallet_balances(user_id)
            
            stats = await self.user_service.get_user_stats(user_id)
            
            sessions = await self.auth_service.get_user_sessions(user_id)
            
            activity = await self.user_service.get_user_activity(user_id, 10)
            
            return {
                "user_info": user_info.to_dict(),
                "wallet": wallet_info.to_dict() if wallet_info else None,
                "balances": balances,
                "stats": stats,
                "active_sessions": len(sessions),
                "recent_activity": activity.get("activity", [])
            }
            
        except Exception as e:
            logger.error(f"Get user profile failed: {e}", exc_info=True)
            return None
    
    async def get_user_dossier(self, twitter_user_id: str) -> Optional[Dict[str, Any]]:
        """
        Compiles a complete dossier for a user, including their profile, wallet, and DM history.
        This is used to provide context to the AI.
        """
        logger.info(f"Compiling dossier for Twitter user: {twitter_user_id}")
        
        user = await self.user_service.get_user_by_twitter_id(twitter_user_id)
        if not user:
            logger.warning(f"No user found for Twitter ID {twitter_user_id} when compiling dossier.")
            return None

        wallet = await self.wallet_service.get_wallet_by_user_id(user.id)
        dm_history = await self.user_service.get_dm_history(user.id, limit=50) # Get last 50 DMs for context

        dossier = {
            "user_profile": {
                "db_id": user.id,
                "twitter_handle": user.twitter_handle,
                "twitter_user_id": user.twitter_user_id,
                "created_at": user.created_at,
                "last_seen": user.last_seen,
            },
            "wallet": {
                "address": wallet.address if wallet else "Not Available",
                "balance": wallet.balance if wallet else "0.0",
            },
            "dm_history": [
                {
                    "type": dm.message_type,
                    "content": dm.content,
                    "timestamp": dm.timestamp,
                }
                for dm in dm_history
            ],
        }
        
        logger.info(f"Dossier successfully compiled for {user.twitter_handle}.")
        return dossier
    
    async def authenticate_twitter_user(self, twitter_handle: str, twitter_user_id: str) -> Dict[str, Any]:
        """Authenticate Twitter user and return session"""
        try:
            user_info = await self.user_service.get_user_by_twitter_id(twitter_user_id)
            
            if not user_info:
                return {
                    "success": False,
                    "needs_registration": True,
                    "message": "User not registered"
                }
            
            auth_result = await self.auth_service.authenticate_user(twitter_handle, twitter_user_id)
            
            if not auth_result["success"]:
                return auth_result
            
            profile = await self.get_user_profile(auth_result["user_id"])
            
            return {
                "success": True,
                "authentication": auth_result,
                "profile": profile
            }
            
        except Exception as e:
            logger.error(f"Twitter authentication failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def process_user_command(self, session_id: str, command: str, args: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process user command with authentication"""
        try:
            auth_data = await self.auth_service.require_auth(session_id)
            
            if not auth_data:
                return {
                    "success": False,
                    "error": "Authentication required",
                    "needs_auth": True
                }
            
            user_id = auth_data["user_id"]
            
            if command == "balance":
                balances = await self.wallet_service.get_wallet_balances(user_id)
                return {
                    "success": True,
                    "command": "balance",
                    "data": balances["total_balances"]
                }
            
            elif command == "profile":
                profile = await self.get_user_profile(user_id)
                return {
                    "success": True,
                    "command": "profile",
                    "data": profile
                }
            
            elif command == "stats":
                stats = await self.user_service.get_user_stats(user_id)
                return {
                    "success": True,
                    "command": "stats",
                    "data": stats
                }
            
            elif command == "activity":
                limit = args.get("limit", 10) if args else 10
                activity = await self.user_service.get_user_activity(user_id, limit)
                return {
                    "success": True,
                    "command": "activity",
                    "data": activity
                }
            
            elif command == "logout":
                logout_result = await self.auth_service.logout_user(user_id)
                return {
                    "success": logout_result,
                    "command": "logout",
                    "message": "Logged out successfully" if logout_result else "Logout failed"
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown command: {command}"
                }
            
        except Exception as e:
            logger.error(f"Process user command failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def backup_user_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Create complete backup of user data"""
        try:
            user_info = await self.user_service.get_user_by_id(user_id)
            wallet_backup = await self.wallet_service.backup_wallet_data(user_id)
            stats = await self.user_service.get_user_stats(user_id)
            activity = await self.user_service.get_user_activity(user_id, 50)
            
            return {
                "user_info": user_info,
                "wallet_data": wallet_backup,
                "stats": stats,
                "activity_history": activity,
                "backup_type": "complete",
                "backup_timestamp": int(time.time())
            }
            
        except Exception as e:
            logger.error(f"Backup user data failed: {e}")
            return None
    
    async def recover_user_account(self, twitter_handle: str) -> Optional[Dict[str, Any]]:
        """Recover user account by Twitter handle"""
        try:
            recovery_result = await self.wallet_service.recover_wallet_by_twitter(twitter_handle)
            
            if not recovery_result:
                return None
            
            user_id = recovery_result["user_id"]
            
            session_result = await self.auth_service.create_session(user_id, "recovery")
            
            profile = await self.get_user_profile(user_id)
            
            return {
                "recovery_successful": True,
                "user_id": user_id,
                "twitter_handle": twitter_handle,
                "wallet_address": recovery_result["wallet_address"],
                "balances": recovery_result["balances"],
                "session": session_result if session_result["success"] else None,
                "profile": profile
            }
            
        except Exception as e:
            logger.error(f"Account recovery failed: {e}")
            return None
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get overall system statistics"""
        try:
            recent_users = await self.user_service.list_recent_users(20)
            
            session_stats = await self.auth_service.get_session_stats()
            
            await self.auth_service.cleanup_expired_sessions()
            
            return {
                "total_users": len(recent_users),
                "recent_users": recent_users[:5],
                "session_stats": session_stats,
                "system_health": "operational"
            }
            
        except Exception as e:
            logger.error(f"Get system stats failed: {e}")
            return {
                "total_users": 0,
                "recent_users": [],
                "session_stats": {},
                "system_health": "error"
            }
    
    async def get_or_create_user(self, twitter_handle: str, twitter_user_id: str) -> tuple:
        """Get existing user or create new one, returns (user, created)"""
        try:
            user_info = await self.user_service.get_user_by_twitter_id(twitter_user_id)
            
            if user_info:
                return user_info, False
                
            user_result = await self.user_service.register(twitter_handle, twitter_user_id)
            
            if user_result["success"]:
                user_data = {
                    "id": user_result["user_id"],
                    "user_id": user_result["user_id"],
                    "twitter_handle": user_result["twitter_handle"],
                    "twitter_user_id": twitter_user_id
                }
                return user_data, True
            else:
                logger.error(f"Failed to create user: {user_result.get('error')}")
                return None, False
                
        except Exception as e:
            logger.error(f"Error in get_or_create_user: {e}")
            return None, False
    
    async def log_dm(self, user_id: int, content: str, message_type: str, conversation_id: str, twitter_message_id: Optional[str] = None) -> bool:
        """
        Logs a direct message to the database using the UserService.
        This is a convenience wrapper around the low-level service.
        """
        return await self.user_service.log_dm(
            user_id=user_id,
            content=content,
            message_type=message_type,
            conversation_id=conversation_id,
            twitter_message_id=twitter_message_id
        )

    async def get_saved_conversation_ids(self, platform: str = "twitter") -> List[str]:
        """Get all saved conversation IDs from database"""
        try:
            return await self.auth_service.get_saved_conversation_ids(platform)
        except Exception as e:
            logger.error(f"Error getting saved conversation IDs: {e}")
            return []

    async def health_check(self) -> Dict[str, Any]:
        """Health check for user management system"""
        try:
            test_user = await self.user_service.get_user_by_id(1)
            db_healthy = True
            
            session_stats = await self.auth_service.get_session_stats()
            sessions_healthy = isinstance(session_stats, dict)
            
            wallet_healthy = hasattr(self.wallet_service, 'balance_manager')
            
            overall_health = db_healthy and sessions_healthy and wallet_healthy
            
            return {
                "healthy": overall_health,
                "components": {
                    "database": db_healthy,
                    "sessions": sessions_healthy,
                    "wallet_service": wallet_healthy
                },
                "active_sessions": session_stats.get("active_sessions", 0),
                "system_status": "operational" if overall_health else "degraded"
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "system_status": "error"
            }

    async def get_user_context_dossier(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Gathers a complete user data dossier, formatted for AI context.
        This includes user identity, wallet, balances, and recent activity.
        """
        try:
            user_info = await self.user_service.get_user_by_id(user_id)
            if not user_info:
                logger.warning(f"No user found for ID {user_id} when building dossier.")
                return None

            wallet_info = await self.wallet_service.get_user_wallet(user_id)
            balances_data = await self.wallet_service.get_wallet_balances(user_id)
            activity_data = await self.user_service.get_user_activity(user_id, limit=5)
            conversation_history = await self.user_service.get_dm_history(user_id, limit=10)

            dossier = {
                "user_id": user_info.id,
                "twitter_handle": user_info.twitter_handle,
                "twitter_user_id": user_info.twitter_user_id,
                "user_since": user_info.created_at.strftime("%Y-%m-%d"),
                "wallet_address": wallet_info.get("address") if wallet_info else "N/A",
                "balances": balances_data.get("total_balances", []),
                "recent_activity": activity_data.get("activity", []),
                "conversation_history": conversation_history
            }
            
            return {"success": True, "dossier": dossier}

        except Exception as e:
            logger.error(f"Failed to build user context dossier for user_id {user_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)} 