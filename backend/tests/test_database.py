"""
Tests for database functionality (Phase 1).

Tests SQLAlchemy 2.0 models, CRUD operations, and database connectivity.
Ensures all models work correctly with modern async patterns.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Wallet, TokenPrice, SwapHistory, TransactionHistory, DMLog


class TestDatabaseConnection:
    """Test basic database connectivity and setup."""
    
    @pytest.mark.asyncio
    async def test_database_connection(self, db_session: AsyncSession):
        """Test that database connection works."""
        # Simple query to test connection
        result = await db_session.execute(select(1))
        assert result.scalar() == 1
    
    @pytest.mark.asyncio
    async def test_tables_exist(self, db_session: AsyncSession):
        """Test that all required tables exist."""
        # Test that we can query each table (will fail if table doesn't exist)
        tables_to_test = [User, Wallet, TokenPrice, SwapHistory, TransactionHistory, DMLog]
        
        for model in tables_to_test:
            result = await db_session.execute(select(model).limit(1))
            # Should not raise an exception
            result.scalars().all()


class TestUserModel:
    """Test User model CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_user(self, db_session: AsyncSession, sample_user_data):
        """Test creating a new user."""
        user = User(**sample_user_data)
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.id is not None
        assert user.twitter_handle == sample_user_data["twitter_handle"]
        assert user.twitter_user_id == sample_user_data["twitter_user_id"]
        assert user.created_at is not None
        assert user.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_user_unique_constraints(self, db_session: AsyncSession, sample_user_data):
        """Test that user unique constraints work."""
        # Create first user
        user1 = User(**sample_user_data)
        db_session.add(user1)
        await db_session.commit()
        
        # Try to create second user with same twitter_handle
        user2 = User(
            twitter_handle=sample_user_data["twitter_handle"],
            twitter_user_id="different_id"
        )
        db_session.add(user2)
        
        # Should raise integrity error
        with pytest.raises(Exception):  # SQLAlchemy will wrap the DB integrity error
            await db_session.commit()
    
    @pytest.mark.asyncio
    async def test_query_user(self, db_session: AsyncSession, sample_user_data):
        """Test querying users."""
        # Create user
        user = User(**sample_user_data)
        db_session.add(user)
        await db_session.commit()
        
        # Query by twitter_handle
        result = await db_session.execute(
            select(User).where(User.twitter_handle == sample_user_data["twitter_handle"])
        )
        found_user = result.scalar_one()
        
        assert found_user.twitter_handle == sample_user_data["twitter_handle"]
        assert found_user.twitter_user_id == sample_user_data["twitter_user_id"]


class TestWalletModel:
    """Test Wallet model and user relationship."""
    
    @pytest.mark.asyncio
    async def test_create_wallet(self, db_session: AsyncSession, sample_user_data, sample_wallet_data):
        """Test creating a wallet linked to a user."""
        # Create user first
        user = User(**sample_user_data)
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create wallet for user
        wallet_data = {**sample_wallet_data, "user_id": user.id}
        wallet = Wallet(**wallet_data)
        db_session.add(wallet)
        await db_session.commit()
        await db_session.refresh(wallet)
        
        assert wallet.id is not None
        assert wallet.user_id == user.id
        assert wallet.address == sample_wallet_data["address"]
        assert wallet.private_key_encrypted == sample_wallet_data["private_key_encrypted"]
    
    @pytest.mark.asyncio
    async def test_wallet_user_unique_constraint(self, db_session: AsyncSession, sample_user_data, sample_wallet_data):
        """Test that one user can only have one wallet."""
        # Create user
        user = User(**sample_user_data)
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create first wallet
        wallet1 = Wallet(**sample_wallet_data, user_id=user.id)
        db_session.add(wallet1)
        await db_session.commit()
        
        # Try to create second wallet for same user
        wallet2 = Wallet(
            user_id=user.id,
            address="0xdifferentaddress1234567890abcdef12345678",
            private_key_encrypted="different_encrypted_key"
        )
        db_session.add(wallet2)
        
        # Should raise integrity error due to unique constraint on user_id
        with pytest.raises(Exception):
            await db_session.commit()


class TestTokenPriceModel:
    """Test TokenPrice model functionality."""
    
    @pytest.mark.asyncio
    async def test_create_token_price(self, db_session: AsyncSession, sample_token_data):
        """Test creating token price entry."""
        token = TokenPrice(**sample_token_data)
        db_session.add(token)
        await db_session.commit()
        await db_session.refresh(token)
        
        assert token.id is not None
        assert token.symbol == sample_token_data["symbol"]
        assert token.name == sample_token_data["name"]
        assert float(token.price_usd) == sample_token_data["price_usd"]
        assert token.decimals == sample_token_data["decimals"]
        assert token.is_active == sample_token_data["is_active"]
    
    @pytest.mark.asyncio
    async def test_token_symbol_unique(self, db_session: AsyncSession, sample_token_data):
        """Test that token symbols must be unique."""
        # Create first token
        token1 = TokenPrice(**sample_token_data)
        db_session.add(token1)
        await db_session.commit()
        
        # Try to create another token with same symbol
        token2_data = {**sample_token_data, "name": "Different Name"}
        token2 = TokenPrice(**token2_data)
        db_session.add(token2)
        
        # Should raise integrity error
        with pytest.raises(Exception):
            await db_session.commit()
    
    @pytest.mark.asyncio
    async def test_query_active_tokens(self, db_session: AsyncSession):
        """Test querying active tokens only."""
        # Create active and inactive tokens
        active_token = TokenPrice(symbol="ETH", name="Ethereum", price_usd=2000.0, is_active=True)
        inactive_token = TokenPrice(symbol="OLD", name="Old Token", price_usd=1.0, is_active=False)
        
        db_session.add_all([active_token, inactive_token])
        await db_session.commit()
        
        # Query only active tokens
        result = await db_session.execute(
            select(TokenPrice).where(TokenPrice.is_active == True)
        )
        active_tokens = result.scalars().all()
        
        assert len(active_tokens) == 1
        assert active_tokens[0].symbol == "ETH"


class TestSwapHistoryModel:
    """Test SwapHistory model functionality."""
    
    @pytest.mark.asyncio
    async def test_create_swap_history(self, db_session: AsyncSession, sample_user_data, sample_swap_data):
        """Test creating swap history entry."""
        # Create user first
        user = User(**sample_user_data)
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create swap history
        swap_data = {**sample_swap_data, "user_id": user.id}
        swap = SwapHistory(**swap_data)
        db_session.add(swap)
        await db_session.commit()
        await db_session.refresh(swap)
        
        assert swap.id is not None
        assert swap.user_id == str(user.id)
        assert swap.from_token == sample_swap_data["from_token"]
        assert swap.to_token == sample_swap_data["to_token"]
        assert float(swap.from_amount) == sample_swap_data["from_amount"]
        assert float(swap.to_amount) == sample_swap_data["to_amount"]
        assert swap.status == sample_swap_data["status"]


class TestTransactionHistoryModel:
    """Test TransactionHistory model functionality."""
    
    @pytest.mark.asyncio
    async def test_create_transaction_history(self, db_session: AsyncSession, sample_user_data, sample_transaction_data):
        """Test creating transaction history entry."""
        # Create user first
        user = User(**sample_user_data)
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create transaction history
        tx_data = {**sample_transaction_data, "user_id": user.id}
        transaction = TransactionHistory(**tx_data)
        db_session.add(transaction)
        await db_session.commit()
        await db_session.refresh(transaction)
        
        assert transaction.id is not None
        assert transaction.user_id == user.id
        assert transaction.transaction_type == sample_transaction_data["transaction_type"]
        assert transaction.token_symbol == sample_transaction_data["token_symbol"]
        assert float(transaction.amount) == sample_transaction_data["amount"]
        assert transaction.to_address == sample_transaction_data["to_address"]
        assert transaction.status == sample_transaction_data["status"]


class TestDMLogModel:
    """Test DMLog model functionality."""
    
    @pytest.mark.asyncio
    async def test_create_dm_log(self, db_session: AsyncSession, sample_user_data, sample_dm_log_data):
        """Test creating DM log entry."""
        # Create user first
        user = User(**sample_user_data)
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create DM log
        dm_data = {**sample_dm_log_data, "user_id": user.id}
        dm_log = DMLog(**dm_data)
        db_session.add(dm_log)
        await db_session.commit()
        await db_session.refresh(dm_log)
        
        assert dm_log.id is not None
        assert dm_log.user_id == user.id
        assert dm_log.message_type == sample_dm_log_data["message_type"]
        assert dm_log.content == sample_dm_log_data["content"]
        assert dm_log.session_id == sample_dm_log_data["session_id"]
        assert dm_log.error_occurred == sample_dm_log_data["error_occurred"]


class TestModelRepr:
    """Test model string representations."""
    
    @pytest.mark.asyncio
    async def test_user_repr(self, db_session: AsyncSession, sample_user_data):
        """Test User model __repr__ method."""
        user = User(**sample_user_data)
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        repr_str = repr(user)
        assert "User" in repr_str
        assert str(user.id) in repr_str
    
    @pytest.mark.asyncio
    async def test_token_repr(self, db_session: AsyncSession, sample_token_data):
        """Test TokenPrice model __repr__ method."""
        token = TokenPrice(**sample_token_data)
        db_session.add(token)
        await db_session.commit()
        await db_session.refresh(token)
        
        repr_str = repr(token)
        assert "TokenPrice" in repr_str
        assert str(token.id) in repr_str 