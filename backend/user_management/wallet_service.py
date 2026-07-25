import logging
import time
from typing import Dict, Optional, Any, List
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
import nacl.signing

from database.models import User, Wallet, TokenBalance
from config import ENCRYPTION_KEY
from .encryption_service import EncryptionService
from swaps.balance_manager import BalanceManager
from database.database import init_db

logger = logging.getLogger(__name__)

_B58_ALPHABET = b'123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


def _b58encode(data: bytes) -> str:
    n = int.from_bytes(data, 'big')
    result = []
    while n:
        n, r = divmod(n, 58)
        result.append(_B58_ALPHABET[r:r + 1])
    for byte in data:
        if byte == 0:
            result.append(b'1')
        else:
            break
    return b''.join(reversed(result)).decode()


class WalletService:
    def __init__(self, db_session_factory: async_sessionmaker[AsyncSession]):
        self.db_session_factory = db_session_factory
        self.encryption_service = EncryptionService(ENCRYPTION_KEY)
        self.balance_manager = BalanceManager(self.db_session_factory)

    def _create_solana_keypair(self) -> Dict[str, str]:
        signing_key = nacl.signing.SigningKey.generate()
        private_bytes = bytes(signing_key)           # 32-byte seed
        public_bytes = bytes(signing_key.verify_key)  # 32-byte Ed25519 pubkey
        secret_64 = private_bytes + public_bytes      # Solana 64-byte wire format
        return {
            "address": _b58encode(public_bytes),
            "private_key": secret_64.hex(),
        }
    
    async def create_wallet_for_user(self, user_id: int) -> Dict[str, Any]:
        """Create and link a new wallet to user"""
        try:
            async with self.db_session_factory() as session:
                result = await session.execute(
                    select(Wallet).where(Wallet.user_id == user_id)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    return {
                        "success": True,
                        "address": existing.address,
                        "message": "User already has wallet",
                        "new_wallet": False
                    }
                
                wallet_data = self._create_solana_keypair()
                encrypted_private_key = self.encryption_service.encrypt(wallet_data["private_key"])
                
                new_wallet = Wallet(
                    user_id=user_id,
                    address=wallet_data["address"],
                    private_key_encrypted=encrypted_private_key
                )
                session.add(new_wallet)
                await session.commit()
                
                # Get the user to find their Twitter user ID for claiming transfers
                user_result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if user and user.twitter_user_id:
                    # Auto-claim pending transfers after wallet creation
                    try:
                        from services.modern_transfer_service import ModernTransferService
                        transfer_service = ModernTransferService()
                        claimed_transfers = await transfer_service.claim_pending_transfers(session, user.twitter_user_id)
                        
                        if claimed_transfers:
                            logger.info(f"🎉 Auto-claimed {len(claimed_transfers)} pending transfers after wallet creation for user {user_id}")
                    except Exception as e:
                        logger.error(f"❌ Failed to auto-claim transfers after wallet creation: {e}")
                        # Don't fail wallet creation if claiming fails
                
                await self.initialize_user_balances(user_id)
                
                logger.info(f"Created Solana wallet for user {user_id}: {wallet_data['address']}")
                
                return {
                    "success": True,
                    "address": wallet_data["address"],
                    "message": "Solana wallet created successfully",
                    "new_wallet": True
                }
                
        except Exception as e:
            logger.error(f"Create wallet failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_user_wallet(self, user_id: int) -> Optional[Wallet]:
        """Get user's wallet information"""
        try:
            async with self.db_session_factory() as session:
                result = await session.execute(select(Wallet).where(Wallet.user_id == user_id))
                wallet = result.scalar_one_or_none()
                
                if wallet:
                    return wallet
                return None
                
        except Exception as e:
            logger.error(f"Get user wallet failed: {e}")
            return None
    
    async def get_wallet_balances(self, user_id: int) -> Dict[str, Any]:
        """Get complete wallet balances (internal + blockchain)"""
        try:
            internal_balances = await self.balance_manager.get_all(str(user_id))
            
            wallet = await self.get_user_wallet(user_id)
            
            result = {
                "internal_balances": internal_balances,
                "blockchain_balances": {},
                "total_balances": internal_balances.copy(),
                "wallet_address": wallet.address if wallet else None
            }
            
            if wallet:
                try:
                    blockchain_balances = await self.get_blockchain_balances(wallet.address)
                    result["blockchain_balances"] = blockchain_balances
                    
                    for token, amount in blockchain_balances.items():
                        if token in result["total_balances"]:
                            result["total_balances"][token] += amount
                        else:
                            result["total_balances"][token] = amount
                            
                except Exception as e:
                    logger.warning(f"Failed to get blockchain balances: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Get wallet balances failed: {e}")
            return {
                "internal_balances": {},
                "blockchain_balances": {},
                "total_balances": {},
                "wallet_address": None
            }
    
    async def get_blockchain_balances(self, address: str) -> Dict[str, float]:
        """Get token balances from blockchain"""
        try:
            return {}
            
        except Exception as e:
            logger.error(f"Get blockchain balances failed: {e}")
            return {}
    
    async def initialize_user_balances(self, user_id: int) -> bool:
        """Initialize new user with some test tokens"""
        try:
            starter_tokens = {
                
            }
            
            for token, amount in starter_tokens.items():
                await self.balance_manager.set(str(user_id), token, amount)
            
            logger.info(f"Initialized starter balances for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Initialize user balances failed: {e}")
            return False
    
    async def link_wallet_to_user(self, user_id: int, wallet_address: str, private_key_encrypted: str) -> bool:
        """Link an existing wallet to user"""
        try:
            async with self.db_session_factory() as session:
                result = await session.execute(
                    select(Wallet).where(Wallet.user_id == user_id)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    await session.execute(
                        text("""UPDATE wallets SET address = :address, private_key_encrypted = :private_key, 
                               updated_at = datetime('now') WHERE user_id = :user_id"""),
                        {
                            "address": wallet_address,
                            "private_key": private_key_encrypted,
                            "user_id": user_id
                        }
                    )
                else:
                    await session.execute(
                        text("""INSERT INTO wallets (user_id, address, private_key_encrypted, created_at, updated_at)
                               VALUES (:user_id, :address, :private_key, datetime('now'), datetime('now'))"""),
                        {
                            "user_id": user_id,
                            "address": wallet_address,
                            "private_key": private_key_encrypted
                        }
                    )
                
                await session.commit()
                logger.info(f"Linked wallet {wallet_address} to user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Link wallet failed: {e}")
            return False
    
    async def backup_wallet_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Create backup of user wallet data"""
        try:
            async with self.db_session_factory() as session:
                result = await session.execute(
                    select(Wallet).where(Wallet.user_id == user_id)
                )
                wallet = result.scalar_one_or_none()
                
                if not wallet:
                    return None
                
                result = await session.execute(
                    select(User.twitter_handle, User.twitter_user_id).where(User.id == user_id)
                )
                user = result.fetchone()
                
                balances = await self.balance_manager.get_all(str(user_id))
                
                return {
                    "user_id": user_id,
                    "twitter_handle": user[0] if user else None,
                    "twitter_user_id": user[1] if user else None,
                    "wallet_address": wallet.address,
                    "wallet_created": wallet.created_at,
                    "balances": balances,
                    "backup_timestamp": int(time.time())
                }
                
        except Exception as e:
            logger.error(f"Backup wallet data failed: {e}")
            return None
    
    async def recover_wallet_by_twitter(self, twitter_handle: str) -> Optional[Dict[str, Any]]:
        """Recover wallet by Twitter handle"""
        try:
            async with self.db_session_factory() as session:
                result = await session.execute(
                    select(User.id).where(User.twitter_handle == twitter_handle)
                )
                user = result.fetchone()
                
                if not user:
                    return None
                
                user_id = user[0]
                
                wallet = await self.get_user_wallet(user_id)
                if not wallet:
                    return None
                
                balances = await self.get_wallet_balances(user_id)
                
                return {
                    "user_id": user_id,
                    "twitter_handle": twitter_handle,
                    "wallet_address": wallet.address,
                    "balances": balances["total_balances"],
                    "recovery_successful": True
                }
                
        except Exception as e:
            logger.error(f"Recover wallet failed: {e}")
            return None
    
    async def get_wallet_activity(self, user_id: int, limit: int = 20) -> Dict[str, Any]:
        """Get wallet activity history"""
        try:
            async with self.db_session_factory() as session:
                result = await session.execute(
                    text("""SELECT transaction_type, token_symbol, amount, to_address, status, created_at
                           FROM transactionhistorys WHERE user_id = :user_id 
                           ORDER BY created_at DESC LIMIT :limit"""),
                    {"user_id": user_id, "limit": limit}
                )
                transactions = result.fetchall()
                
                activity = []
                for tx in transactions:
                    activity.append({
                        "type": "transaction",
                        "transaction_type": tx[0],
                        "token": tx[1],
                        "amount": float(tx[2]),
                        "to_address": tx[3],
                        "status": tx[4],
                        "timestamp": tx[5]
                    })
                
                return {
                    "activity": activity,
                    "total_transactions": len(activity)
                }
                
        except Exception as e:
            logger.error(f"Get wallet activity failed: {e}")
            return {"activity": [], "total_transactions": 0}

    async def get_or_create_wallet_for_user(self, user_id: int) -> Dict[str, Any]:
        """Gets a user's wallet or creates one if it doesn't exist."""
        wallet = await self.get_user_wallet(user_id)
        if wallet:
            return {"success": True, "address": wallet.address, "is_new": False}
        
        return await self.create_wallet_for_user(user_id)

    async def get_wallet_address(self, user_id: int) -> Optional[str]:
        """Gets a user's wallet address."""
        wallet = await self.get_user_wallet(user_id)
        return wallet.address if wallet else None

    async def get_decrypted_private_key(self, user_id: int) -> Optional[str]:
        """Get the decrypted private key for a user's wallet."""
        try:
            wallet = await self.get_user_wallet(user_id)
            if not wallet or not wallet.private_key_encrypted:
                return None
            return self.encryption_service.decrypt(wallet.private_key_encrypted)
        except Exception as e:
            logger.error(f"Failed to decrypt private key for user {user_id}: {e}")
            return None

    async def get_wallet_balances(self, user_id: int) -> Dict[str, Any]:
        """
        Retrieves all token balances for a user's wallet.
        This version uses the database as the source of truth, updated by a separate process.
        """
        try:
            async with self.db_session_factory() as session:
                result = await session.execute(
                    select(TokenBalance.token_symbol, TokenBalance.balance).where(TokenBalance.user_id == str(user_id))
                )
                balances = {row[0]: float(row[1]) for row in result.fetchall()}
                
                return {
                    "success": True,
                    "total_balances": balances
                }
        except Exception as e:
            logger.error(f"Failed to get database balances for user {user_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e), "total_balances": {}}

    async def update_token_balance(self, user_id: int, token_symbol: str, new_balance: float) -> bool:
        """Updates a user's token balance in the database."""
        try:
            async with self.db_session_factory() as session:
                # Use an upsert-like operation
                stmt = text("""
                    INSERT INTO tokenbalances (user_id, token_symbol, balance, created_at, updated_at)
                    VALUES (:user_id, :token_symbol, :balance, :now, :now)
                    ON CONFLICT(user_id, token_symbol) DO UPDATE SET
                        balance = excluded.balance,
                        updated_at = excluded.updated_at
                """)
                await session.execute(stmt, {
                    "user_id": str(user_id),
                    "token_symbol": token_symbol,
                    "balance": new_balance,
                    "now": time.time()
                })
                await session.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to update balance for user {user_id}, token {token_symbol}: {e}")
            return False

    async def get_total_system_liquidity(self) -> Dict[str, float]:
        """Calculates the total amount of each token held across all user wallets."""
        try:
            async with self.db_session_factory() as session:
                result = await session.execute(
                    text("SELECT token_symbol, SUM(balance) FROM tokenbalances GROUP BY token_symbol")
                )
                return {row[0]: float(row[1]) for row in result.fetchall()}
        except Exception as e:
            logger.error(f"Failed to get total system liquidity: {e}")
            return {}
            
    async def get_user_id_from_address(self, address: str) -> Optional[int]:
        """Finds a user's internal ID from their wallet address."""
        try:
            async with self.db_session_factory() as session:
                result = await session.execute(select(Wallet.user_id).where(Wallet.address == address))
                user_id = result.scalar_one_or_none()
                return user_id
        except Exception as e:
            logger.error(f"Could not get user_id from address {address}: {e}")
            return None
            
    async def transfer_between_users(self, from_user_id: int, to_user_id: int, token: str, amount: float) -> Dict[str, Any]:
        """
        Transfers tokens between two users by adjusting their database balances.
        This is an internal, off-chain operation.
        """
        if from_user_id == to_user_id:
            return {"success": False, "error": "Cannot send to yourself."}
        if amount <= 0:
            return {"success": False, "error": "Amount must be positive."}
            
        try:
            async with self.db_session_factory() as session:
                async with session.begin():
                    sender_balance_result = await session.execute(
                        select(TokenBalance.balance)
                        .where(TokenBalance.user_id == str(from_user_id))
                        .where(TokenBalance.token_symbol == token)
                    )
                    sender_balance = sender_balance_result.scalar_one_or_none()
                    
                    if sender_balance is None or sender_balance < amount:
                        return {"success": False, "error": f"Insufficient {token} balance."}
                        
                    await session.execute(
                        text("""
                            UPDATE tokenbalances SET balance = balance - :amount, updated_at = :now
                            WHERE user_id = :user_id AND token_symbol = :token
                        """),
                        {"amount": amount, "now": time.time(), "user_id": str(from_user_id), "token": token}
                    )
                    
                    await session.execute(
                        text("""
                            INSERT INTO tokenbalances (user_id, token_symbol, balance, created_at, updated_at)
                            VALUES (:user_id, :token, :amount, :now, :now)
                            ON CONFLICT(user_id, token_symbol) DO UPDATE SET
                                balance = tokenbalances.balance + excluded.balance,
                                updated_at = excluded.updated_at
                        """),
                        {"user_id": str(to_user_id), "token": token, "amount": amount, "now": time.time()}
                    )
                
                logger.info(f"Transferred {amount} {token} from user {from_user_id} to {to_user_id}")
                return {"success": True, "message": "Transfer successful."}
                
        except Exception as e:
            logger.error(f"Internal transfer failed: {e}", exc_info=True)
            return {"success": False, "error": "An internal error occurred during the transfer."}
            
    async def log_transaction(self, user_id: int, tx_type: str, token: str, amount: float, to_address: str, status: str, tx_hash: Optional[str] = None, error: Optional[str] = None):
        """Logs a transaction to the database."""
        pass

    async def get_transaction_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Gets a user's transaction history."""
        return [] # Implementation for getting transaction history 