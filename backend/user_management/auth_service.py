import logging
import time
import hashlib
import secrets
from typing import Dict, Optional, Any, List
from sqlalchemy import text
from database.database import init_db
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

logger = logging.getLogger(__name__)


class AuthService:

    def __init__(self, db_session_factory: async_sessionmaker[AsyncSession]):
        self.db = db_session_factory
        self.active_sessions = {}
        self.session_timeout = 10800

    async def create_session(self,
                             user_id: int,
                             platform: str = "twitter") -> Dict[str, Any]:
        """Create authentication session for user"""
        try:
            session_token = secrets.token_urlsafe(32)
            session_id = hashlib.sha256(
                f"{user_id}_{session_token}_{time.time()}".encode()).hexdigest(
                )

            session_data = {
                "user_id": user_id,
                "platform": platform,
                "created_at": int(time.time()),
                "expires_at": int(time.time()) + self.session_timeout,
                "token": session_token,
                "active": True
            }

            self.active_sessions[session_id] = session_data

            await self.log_auth_event(user_id, "session_created", platform)

            logger.info(f"Created session for user {user_id} on {platform}")

            return {
                "success": True,
                "session_id": session_id,
                "token": session_token,
                "expires_at": session_data["expires_at"]
            }

        except Exception as e:
            logger.error(f"Create session failed: {e}")
            return {"success": False, "error": str(e)}

    async def validate_session(self,
                               session_id: str) -> Optional[Dict[str, Any]]:
        """Validate and refresh session if valid"""
        try:
            session_data = self.active_sessions.get(session_id)

            if not session_data:
                return None

            current_time = int(time.time())
            if current_time > session_data["expires_at"]:
                await self.invalidate_session(session_id)
                return None

            session_data["expires_at"] = current_time + self.session_timeout
            session_data["last_activity"] = current_time

            return session_data

        except Exception as e:
            logger.error(f"Validate session failed: {e}")
            return None

    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a session"""
        try:
            session_data = self.active_sessions.get(session_id)

            if session_data:
                await self.log_auth_event(session_data["user_id"],
                                          "session_ended",
                                          session_data["platform"])

                del self.active_sessions[session_id]

                logger.info(
                    f"Invalidated session for user {session_data['user_id']}")
                return True

            return False

        except Exception as e:
            logger.error(f"Invalidate session failed: {e}")
            return False

    async def authenticate_user(self, twitter_handle: str,
                                twitter_user_id: str) -> Dict[str, Any]:
        """Authenticate user and create session"""
        try:
            async with self.db() as session:
                result = await session.execute(
                    text(
                        "SELECT id, twitter_handle FROM users WHERE twitter_user_id = :twitter_user_id"
                    ), {"twitter_user_id": twitter_user_id})
                user = result.fetchone()

                if not user:
                    return {
                        "success": False,
                        "error": "User not found",
                        "needs_registration": True
                    }

                user_id = user[0]

                session_result = await self.create_session(user_id, "twitter")

                if not session_result["success"]:
                    return session_result

                await self.log_auth_event(user_id, "authenticated", "twitter")

                return {
                    "success": True,
                    "user_id": user_id,
                    "twitter_handle": user[1],
                    "session_id": session_result["session_id"],
                    "token": session_result["token"],
                    "expires_at": session_result["expires_at"]
                }

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return {"success": False, "error": str(e)}

    async def get_user_sessions(self, user_id: int) -> list:
        """Get all active sessions for user"""
        try:
            user_sessions = []
            current_time = int(time.time())

            for session_id, session_data in self.active_sessions.items():
                if session_data["user_id"] == user_id:
                    if current_time > session_data["expires_at"]:
                        continue

                    user_sessions.append({
                        "session_id":
                        session_id,
                        "platform":
                        session_data["platform"],
                        "created_at":
                        session_data["created_at"],
                        "expires_at":
                        session_data["expires_at"],
                        "last_activity":
                        session_data.get("last_activity",
                                         session_data["created_at"])
                    })

            return user_sessions

        except Exception as e:
            logger.error(f"Get user sessions failed: {e}")
            return []

    async def log_auth_event(self,
                             user_id: int,
                             event_type: str,
                             platform: str,
                             details: str = None):
        """Log authentication events"""
        try:
            async with self.db() as session:
                await session.execute(
                    text(
                        """INSERT INTO dmlogs (user_id, message_type, content, platform, error_occurred, created_at, updated_at)
                           VALUES (:user_id, :event_type, :content, :platform, :error_occurred, datetime('now'), datetime('now'))"""
                    ), {
                        "user_id": user_id,
                        "event_type": f"auth_{event_type}",
                        "content": details or f"Auth event: {event_type}",
                        "platform": platform,
                        "error_occurred": False
                    })
                await session.commit()

        except Exception as e:
            logger.error(f"Log auth event failed: {e}")

    async def log_dm(self,
                     user_id: int,
                     content: str,
                     message_type: str,
                     platform: str = "twitter",
                     conversation_id: str = None):
        """Log DM message to database with optional conversation_id"""
        try:
            async with self.db() as session:
                await session.execute(
                    text(
                        """INSERT INTO dmlogs (user_id, message_type, content, platform, conversation_id, error_occurred, created_at, updated_at)
                           VALUES (:user_id, :message_type, :content, :platform, :conversation_id, :error_occurred, datetime('now'), datetime('now'))"""
                    ), {
                        "user_id": user_id,
                        "message_type": message_type,
                        "content": content,
                        "platform": platform,
                        "conversation_id": conversation_id,
                        "error_occurred": False
                    })
                await session.commit()

        except Exception as e:
            logger.error(f"Log DM failed: {e}")
            raise

    async def get_saved_conversation_ids(self,
                                         platform: str = "twitter"
                                         ) -> List[str]:
        """Get all unique conversation IDs from database"""
        try:
            async with self.db() as session:
                result = await session.execute(
                    text("""SELECT DISTINCT conversation_id FROM dmlogs 
                           WHERE conversation_id IS NOT NULL AND platform = :platform
                           ORDER BY created_at DESC"""),
                    {"platform": platform})
                conversation_ids = [row[0] for row in result.fetchall()]
                logger.info(
                    f"📊 Found {len(conversation_ids)} saved conversations")
                return conversation_ids

        except Exception as e:
            logger.error(f"Get saved conversation IDs failed: {e}")
            return []

    async def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        try:
            current_time = int(time.time())
            expired_sessions = []

            for session_id, session_data in self.active_sessions.items():
                if current_time > session_data["expires_at"]:
                    expired_sessions.append(session_id)

            for session_id in expired_sessions:
                await self.invalidate_session(session_id)

            if expired_sessions:
                logger.info(
                    f"Cleaned up {len(expired_sessions)} expired sessions")

        except Exception as e:
            logger.error(f"Session cleanup failed: {e}")

    async def get_session_stats(self) -> Dict[str, Any]:
        """Get authentication statistics"""
        try:
            current_time = int(time.time())
            active_count = 0
            expired_count = 0
            platforms = {}

            for session_data in self.active_sessions.values():
                if current_time > session_data["expires_at"]:
                    expired_count += 1
                else:
                    active_count += 1
                    platform = session_data["platform"]
                    platforms[platform] = platforms.get(platform, 0) + 1

            return {
                "active_sessions": active_count,
                "expired_sessions": expired_count,
                "total_sessions": len(self.active_sessions),
                "platforms": platforms,
                "session_timeout": self.session_timeout
            }

        except Exception as e:
            logger.error(f"Get session stats failed: {e}")
            return {
                "active_sessions": 0,
                "expired_sessions": 0,
                "total_sessions": 0,
                "platforms": {},
                "session_timeout": self.session_timeout
            }

    async def require_auth(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Decorator-like function to require authentication"""
        session_data = await self.validate_session(session_id)

        if not session_data:
            return None

        # Get user data
        try:
            async with self.db() as db_session:
                result = await db_session.execute(
                    text(
                        "SELECT id, twitter_handle, twitter_user_id FROM users WHERE id = :user_id"
                    ), {"user_id": session_data["user_id"]})
                user = result.fetchone()

                if user:
                    return {
                        "user_id": user[0],
                        "twitter_handle": user[1],
                        "twitter_user_id": user[2],
                        "session_id": session_id,
                        "platform": session_data["platform"]
                    }

        except Exception as e:
            logger.error(f"Require auth failed: {e}")

        return None

    async def logout_user(self, user_id: int) -> bool:
        """Logout user from all sessions"""
        try:
            user_sessions = await self.get_user_sessions(user_id)

            for session in user_sessions:
                await self.invalidate_session(session["session_id"])

            await self.log_auth_event(user_id, "logout_all", "system")
            logger.info(f"Logged out user {user_id} from all sessions")

            return True

        except Exception as e:
            logger.error(f"Logout user failed: {e}")
            return False

    async def refresh_session(self,
                              session_id: str) -> Optional[Dict[str, Any]]:
        """Refresh session expiration"""
        try:
            session_data = await self.validate_session(session_id)

            if session_data:
                return {
                    "success": True,
                    "expires_at": session_data["expires_at"],
                    "remaining_time":
                    session_data["expires_at"] - int(time.time())
                }

            return None

        except Exception as e:
            logger.error(f"Refresh session failed: {e}")
            return None
