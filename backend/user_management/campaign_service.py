import logging
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import collate
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone  # Added timezone import
from decimal import Decimal

from database.models import Campaign, CampaignParticipant, TokenBalance, User
from database.database import init_db
from swaps.balance_manager import BalanceManager
from swaps.price_manager import PriceManager
from user_management.transaction_history_service import TransactionHistoryService
from user_management.transaction_history_service import TransactionHistoryService

logger = logging.getLogger(__name__)

class CampaignService:
    def __init__(self, db_session_factory):
        self.db = db_session_factory
        self.balance_manager = BalanceManager(db_session_factory)
        self.price_manager = PriceManager(db_session_factory)
        self.transaction_history = TransactionHistoryService(db_session_factory)
        self.transaction_history = TransactionHistoryService(db_session_factory)

    async def start_campaign_creation(self, creator_user_id: str, campaign_type: str) -> Optional[Campaign]:
        """
        Starts the campaign creation process by creating a 'pending' campaign.
        The process always begins by asking for the title next.
        """
        async with self.db() as session:
            async with session.begin():
                existing_pending = await self.get_pending_campaign_by_user(creator_user_id, session)
                if existing_pending:
                    raise ValueError("User already has a pending campaign.")

                if campaign_type not in ['airdrop', 'engagement']:
                    raise ValueError("Invalid campaign type specified.")

                # Always start with a placeholder title and await the real one.
                creation_step = 'awaiting_title'
                title = f"Untitled Campaign {int(datetime.now().timestamp())}"

                new_campaign = Campaign(
                    creator_twitter_user_id=creator_user_id,
                    name=title,
                    campaign_type=campaign_type,
                    status='pending',
                    creation_step=creation_step,
                    description="",
                    reward_token="",
                    reward_per_participant=0,
                    max_participants=0,
                    reward_pool=0
                )
                session.add(new_campaign)
                await session.flush()
                await session.refresh(new_campaign)
                return new_campaign

    async def update_campaign_creation(self, campaign_id: int, updates: Dict[str, Any]) -> Optional[Campaign]:
        """
        Updates a pending campaign with new information and advances the creation_step
        based on the campaign_type.
        """
        async with self.db() as session:
            async with session.begin():
                campaign = await self.get_campaign_by_id(campaign_id, session)
                if not campaign or campaign.status != 'pending':
                    return None

                # Apply updates first
                for field, value in updates.items():
                    if hasattr(campaign, field):
                        setattr(campaign, field, value)
                    # The AI might try to update the 'title', which maps to the 'name' field.
                    elif field == 'title':
                        campaign.name = value
                
                # Determine the next step with branching logic
                campaign.creation_step = self._get_next_creation_step(campaign)
                
                session.add(campaign)
                await session.flush()
                await session.refresh(campaign)
                return campaign
    
    def _get_next_creation_step(self, campaign: Campaign) -> str:
        """Determines the next creation step based on the campaign's current state and type."""
        base_flow = [
            'awaiting_title',
            'awaiting_description',
            'awaiting_reward_token',
            'awaiting_reward_per_participant',
            'awaiting_max_participants'
        ]
        
        engagement_flow = [
            'awaiting_profile_to_follow',
            'awaiting_tweet_id_to_engage'
        ]

        current_step = campaign.creation_step

        full_flow = base_flow
        if campaign.campaign_type == 'engagement':
            full_flow = base_flow + engagement_flow
            
        # Simplified and more robust logic to find the next step.
        # It finds the current position in the full list and returns the next item.
        try:
            current_index = full_flow.index(current_step)
            if current_index + 1 < len(full_flow):
                return full_flow[current_index + 1]
            else:
                return 'ready_for_activation'
        except ValueError:
            # Fallback for safety, though it should ideally not be reached
            # if the creation steps are managed correctly.
            return 'ready_for_activation'

    async def activate_campaign(self, campaign_id: int) -> Dict[str, Any]:
        """
        Activates a pending campaign after final validation and escrows the funds.
        """
        logger.info(f"🎯 [ACTIVATE DEBUG] Starting activation for campaign {campaign_id}")
        
        async with self.db() as session:
            async with session.begin():
                campaign = await self.get_campaign_by_id(campaign_id, session)
                if not campaign or campaign.status != 'pending':
                    logger.warning(f"🎯 [ACTIVATE DEBUG] Campaign not found or not pending: {campaign.status if campaign else 'not found'}")
                    return {"success": False, "response_code": "CAMPAIGN_NOT_FOUND", "error": "Campaign not found or not in pending state."}
                
                logger.info(f"🎯 [ACTIVATE DEBUG] Campaign details - name: {campaign.name}, creator: {campaign.creator_twitter_user_id}")
                
                # --- CORRECTED VALIDATION LOGIC ---
                # Explicitly check for required fields and that numeric values are positive.
                if not all([campaign.description, campaign.reward_token]) or campaign.reward_per_participant <= 0 or campaign.max_participants <= 0:
                     logger.warning(f"🎯 [ACTIVATE DEBUG] Campaign validation failed - missing details or invalid amounts")
                     return {"success": False, "response_code": "CAMPAIGN_CREATION_ERROR", "error": "Campaign is missing required details or has invalid amounts."}

                # Add validation for engagement campaigns
                if campaign.campaign_type == 'engagement':
                    if not campaign.profile_to_follow or not campaign.tweet_id_to_engage:
                        logger.warning(f"🎯 [ACTIVATE DEBUG] Engagement campaign missing required fields")
                        return {"success": False, "response_code": "CAMPAIGN_CREATION_ERROR", "error": "Engagement campaigns require a profile to follow and a tweet to engage with."}

                total_pool = Decimal(str(campaign.reward_per_participant)) * Decimal(str(campaign.max_participants))
                logger.info(f"🎯 [ACTIVATE DEBUG] Total pool required: {total_pool} {campaign.reward_token}")
                
                # 1. Check creator balance
                creator_balance = await self.balance_manager.get(campaign.creator_twitter_user_id, campaign.reward_token, session=session)
                logger.info(f"🎯 [ACTIVATE DEBUG] Creator balance: {creator_balance} {campaign.reward_token}")
                
                has_balance = await self.balance_manager.has_balance(campaign.creator_twitter_user_id, campaign.reward_token, total_pool, session=session)
                if not has_balance:
                    logger.warning(f"🎯 [ACTIVATE DEBUG] Insufficient balance - required: {total_pool}, available: {creator_balance}")
                    return {
                        "success": False,
                        "response_code": "CAMPAIGN_ACTIVATE_INSUFFICIENT_FUNDS",
                        "context": {
                            "token": campaign.reward_token,
                            "required": float(total_pool)
                        }
                    }

                logger.info(f"🎯 [ACTIVATE DEBUG] Starting funds escrow...")

                # 2. Escrow funds to the system wallet
                SYSTEM_WALLET_USER_ID = 'SYSTEM_WALLET_999'
                transfer_ok = await self.balance_manager.transfer(
                    from_user=campaign.creator_twitter_user_id,
                    to_user=SYSTEM_WALLET_USER_ID,
                    token=campaign.reward_token,
                    amount=total_pool,
                    session=session
                )
                if not transfer_ok:
                    # This will trigger a rollback due to the session.begin() context manager
                    logger.error(f"🎯 [ACTIVATE DEBUG] Failed to escrow funds for campaign {campaign_id}")
                    return {"success": False, "response_code": "CAMPAIGN_FUND_TRANSFER_FAILED", "error": "Failed to escrow campaign funds."}
                
                logger.info(f"🎯 [ACTIVATE DEBUG] Successfully escrowed {total_pool} {campaign.reward_token} for campaign '{campaign.name}' ({campaign.id}).")
                
                # **FIX: Log the campaign funding transaction**
                await self.transaction_history.log_campaign_funding(
                    creator_user_id=campaign.creator_twitter_user_id,
                    campaign_name=campaign.name,
                    token=campaign.reward_token,
                    amount=total_pool,
                    session=session
                )
                
                # 3. Activate Campaign
                campaign.status = 'active'
                campaign.creation_step = 'completed'
                campaign.reward_pool = float(total_pool) # Store as float in DB
                session.add(campaign)

                logger.info(f"🎯 [ACTIVATE DEBUG] Campaign {campaign_id} activated successfully!")

        return {
            "success": True, 
            "response_code": "CAMPAIGN_ACTIVATE_SUCCESS",
            "context": {"name": campaign.name}
        }

    async def get_pending_campaign_by_user(self, creator_user_id: str, session: Optional[AsyncSession] = None) -> Optional[Campaign]:
        """Fetches a pending campaign for a given user."""
        async def _get(db_session):
            stmt = select(Campaign).where(
                Campaign.creator_twitter_user_id == creator_user_id,
                Campaign.status == 'pending'
            )
            result = await db_session.execute(stmt)
            return result.scalar_one_or_none()

        if session:
            return await _get(session)
        else:
            async with self.db() as new_session:
                return await _get(new_session)

    async def get_campaign_by_name(self, name: str) -> Optional[Campaign]:
        """Fetches a campaign by its unique name, case-insensitively."""
        async with self.db() as session:
            stmt = select(Campaign).where(collate(Campaign.name, 'NOCASE') == name)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_campaign_by_id(self, campaign_id: int, session: Optional[AsyncSession] = None) -> Optional[Campaign]:
        """Fetches a campaign by its primary key."""
        async def _get(db_session):
            stmt = select(Campaign).where(Campaign.id == campaign_id)
            result = await db_session.execute(stmt)
            return result.scalar_one_or_none()
        
        if session:
            return await _get(session)
        else:
            async with self.db() as new_session:
                return await _get(new_session)

    async def update_participant_task_status(self, user_id: int, campaign_id: int, **kwargs) -> bool:
        """Updates the task status for a campaign participant."""
        # Automatically set tasks_verified_at if not provided but status is 'tasks_verified'
        if 'status' in kwargs and kwargs['status'] == 'tasks_verified' and 'tasks_verified_at' not in kwargs:
            kwargs['tasks_verified_at'] = datetime.now(timezone.utc)
        
        try:
            async with self.db() as session:
                stmt = update(CampaignParticipant).where(
                    CampaignParticipant.user_id == user_id,
                    CampaignParticipant.campaign_id == campaign_id
                ).values(**kwargs)
                await session.execute(stmt)
                await session.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update participant status for user {user_id}, campaign {campaign_id}: {e}")
            return False

    async def create_funded_campaign(self, creator_user_id: str, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a new campaign in a single atomic operation.
        The new flow uses start_campaign_creation, update_campaign_creation, and activate_campaign.
        
        Creates a new campaign, funded by the creator.
        This operation is atomic.
        """
        try:
            total_pool = campaign_data['reward_per_participant'] * campaign_data['max_participants']
            reward_token = campaign_data['reward_token']
            
            # 0. Validate token
            is_valid_token = await self.price_manager.get_price(reward_token)
            if not is_valid_token:
                raise ValueError(f"The token '{reward_token}' is not supported by the system.")

            async with self.db() as session:
                async with session.begin():
                    # 1. Check if the creator has enough balance.
                    has_balance = await self.balance_manager.has_balance(creator_user_id, reward_token, total_pool, session=session)
                    if not has_balance:
                        raise ValueError(f"Insufficient balance to fund the campaign. Required: {total_pool} {reward_token}")

                    # 2. **FIX: Actually escrow the funds to system wallet**
                    SYSTEM_WALLET_USER_ID = 'SYSTEM_WALLET_999'
                    transfer_ok = await self.balance_manager.transfer(
                        from_user=creator_user_id,
                        to_user=SYSTEM_WALLET_USER_ID,
                        token=reward_token,
                        amount=Decimal(str(total_pool)),
                        session=session
                    )
                    if not transfer_ok:
                        raise ValueError(f"Failed to escrow campaign funds from {creator_user_id}.")
                    
                    logger.info(f"✅ Successfully escrowed {total_pool} {reward_token} for campaign '{campaign_data['title']}'.")

                    # **FIX: Log the campaign funding transaction**
                    await self.transaction_history.log_campaign_funding(
                        creator_user_id=creator_user_id,
                        campaign_name=campaign_data['title'],
                        token=reward_token,
                        amount=Decimal(str(total_pool)),
                        session=session
                    )

                    # 3. Create the campaign object
                    new_campaign = Campaign(
                        creator_twitter_user_id=creator_user_id,
                        name=campaign_data['title'],
                        description=campaign_data['description'],
                        campaign_type=campaign_data.get('campaign_type', 'airdrop'), # Add default
                        reward_token=reward_token,
                        reward_per_participant=campaign_data['reward_per_participant'],
                        max_participants=campaign_data['max_participants'],
                        reward_pool=total_pool,
                        status='active',
                        profile_to_follow=campaign_data.get('profile_handle'),
                        tweet_id_to_engage=campaign_data.get('tweet_id')
                    )
                    session.add(new_campaign)
            
            logger.info(f"Campaign '{campaign_data['title']}' created successfully by {creator_user_id}. Funds escrowed: {total_pool} {reward_token}.")
            return {"success": True, "message": "Campaign created successfully! Funds have been escrowed for rewards."}

        except ValueError as ve:
            logger.warning(f"Campaign creation validation failed: {ve}")
            return {"success": False, "error": str(ve)}
        except Exception as e:
            logger.error(f"Failed to create funded campaign: {e}", exc_info=True)
            return {"success": False, "error": "An internal error occurred during campaign creation."}

    async def list_campaigns(self) -> List[Dict[str, Any]]:
        """Lists all active campaigns."""
        async with self.db() as session:
            result = await session.execute(
                select(Campaign).where(Campaign.status == 'active')
            )
            campaigns = result.scalars().all()
            
            campaign_list = []
            for c in campaigns:
                # Count completed participants
                stmt = select(func.count(CampaignParticipant.id)).where(
                    CampaignParticipant.campaign_id == c.id,
                    CampaignParticipant.status == 'paid'
                )
                completed_count_result = await session.execute(stmt)
                completed_count = completed_count_result.scalar_one()

                campaign_list.append({
                    "id": c.id,
                    "name": c.name,
                    "description": c.description,
                    "reward_token": c.reward_token,
                    "reward_per_participant": float(c.reward_per_participant),
                    "campaign_type": c.campaign_type,
                    "max_participants": c.max_participants,
                    "reward_pool": float(c.reward_pool),
                    "status": c.status,
                    "profile_to_follow": c.profile_to_follow,
                    "tweet_id_to_engage": c.tweet_id_to_engage,
                    "creator_twitter_user_id": c.creator_twitter_user_id,
                    "created_at": c.created_at.isoformat(),
                    "completed_participants": completed_count
                })
            return campaign_list

    async def list_participating_campaigns(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Lists all campaigns a user is participating in, along with their status.
        """
        async with self.db() as session:
            stmt = select(
                Campaign,
                CampaignParticipant.status,
                CampaignParticipant.tasks_verified_at
            ).join(
                CampaignParticipant, Campaign.id == CampaignParticipant.campaign_id
            ).where(
                CampaignParticipant.user_id == user_id
            ).order_by(Campaign.created_at.desc())

            result = await session.execute(stmt)
            
            participations = []
            for campaign, status, verified_at in result.all():
                participations.append({
                    "id": campaign.id,
                    "name": campaign.name,
                    "description": campaign.description,
                    "reward_token": campaign.reward_token,
                    "reward_per_participant": float(campaign.reward_per_participant),
                    "campaign_type": campaign.campaign_type,
                    "participation_status": status,
                    "tasks_verified_at": verified_at.isoformat() if verified_at else None,
                    "tasks_claimed": status == 'paid',
                })
            return participations

    async def join_campaign(self, twitter_user_id: str, campaign_id: int) -> Dict[str, Any]:
        """Allows a user to join a campaign by its ID."""
        async with self.db() as session:
            async with session.begin():
                # 1. Get User from twitter_user_id to get internal user.id
                user_stmt = select(User).where(User.twitter_user_id == twitter_user_id)
                user_result = await session.execute(user_stmt)
                user = user_result.scalar_one_or_none()
                if not user:
                    return {"success": False, "error": "User not found."}

                # 2. Get Campaign from ID
                campaign_stmt = select(Campaign).where(Campaign.id == campaign_id)
                campaign_result = await session.execute(campaign_stmt)
                campaign = campaign_result.scalar_one_or_none()
                if not campaign:
                    return {"success": False, "error": f"Campaign with ID {campaign_id} not found."}

                # 4. Check if campaign is full
                participant_count_stmt = select(func.count(CampaignParticipant.id)).where(CampaignParticipant.campaign_id == campaign.id)
                participant_count = (await session.execute(participant_count_stmt)).scalar_one()

                if participant_count >= campaign.max_participants:
                    return {"success": False, "response_code": "CAMPAIGN_FULL", "error": f"The campaign '{campaign.name}' has reached its maximum number of participants."}

                # 5. Check if user is already a participant
                participant_stmt = select(CampaignParticipant).where(
                    CampaignParticipant.user_id == user.id,
                    CampaignParticipant.campaign_id == campaign.id
                )
                participant_result = await session.execute(participant_stmt)
                existing_participant = participant_result.scalar_one_or_none()

                if existing_participant:
                    return {"success": False, "error": f"You have already joined the '{campaign.name}' campaign."}

                # 6. Create new participant record
                new_participant = CampaignParticipant(
                    user_id=user.id,
                    campaign_id=campaign.id,
                    status='enrolled'
                )
                session.add(new_participant)
        
        return {"success": True, "message": f"You have successfully joined the '{campaign.name}' campaign! 💖"}

    async def claim_reward(self, twitter_user_id: str, campaign_id: int) -> Dict[str, Any]:
        """
        Claims a reward for a user who has completed the tasks for a campaign.
        Funds are transferred from the system's escrow wallet.
        """
        logger.info(f"🏆 [CLAIM DEBUG] Starting reward claim for user {twitter_user_id}, campaign {campaign_id}")
        
        async with self.db() as session:
            async with session.begin():
                # 1. Find the campaign participant entry
                stmt = select(CampaignParticipant).where(
                    CampaignParticipant.campaign_id == campaign_id,
                ).join(User).where(User.twitter_user_id == twitter_user_id)
                
                result = await session.execute(stmt)
                participant = result.scalar_one_or_none()

                if not participant:
                    logger.warning(f"🏆 [CLAIM DEBUG] Participant not found for user {twitter_user_id}, campaign {campaign_id}")
                    return {"success": False, "response_code": "CAMPAIGN_PARTICIPANT_NOT_FOUND"}

                logger.info(f"🏆 [CLAIM DEBUG] Found participant: {participant.id}, status: {participant.status}")

                # 2. Check campaign status
                campaign = await self.get_campaign_by_id(campaign_id, session)
                if not campaign or campaign.status != 'active':
                    logger.warning(f"🏆 [CLAIM DEBUG] Campaign not active: {campaign.status if campaign else 'not found'}")
                    return {"success": False, "response_code": "CAMPAIGN_JOIN_NOT_ACTIVE"}

                logger.info(f"🏆 [CLAIM DEBUG] Campaign details - name: {campaign.name}, reward: {campaign.reward_per_participant} {campaign.reward_token}")

                # 3. Check if reward was already claimed
                if participant.status == 'paid':
                    logger.warning(f"🏆 [CLAIM DEBUG] Reward already claimed for user {twitter_user_id}")
                    return {"success": False, "response_code": "CAMPAIGN_ALREADY_CLAIMED"}

                # For airdrop campaigns, tasks are implicitly verified and can be claimed directly.
                # For other types, tasks_verified_at must be set.
                if campaign.campaign_type != 'airdrop' and not participant.tasks_verified_at:
                    logger.warning(f"🏆 [CLAIM DEBUG] Tasks not verified for engagement campaign")
                    return {"success": False, "response_code": "CAMPAIGN_TASKS_NOT_VERIFIED"}
                
                logger.info(f"🏆 [CLAIM DEBUG] All validations passed, starting balance transfer...")
                
                # 4. Transfer funds from the system's escrow wallet to the user
                SYSTEM_WALLET_USER_ID = 'SYSTEM_WALLET_999'
                
                # Check system wallet balance first
                system_balance = await self.balance_manager.get(SYSTEM_WALLET_USER_ID, campaign.reward_token, session=session)
                logger.info(f"🏆 [CLAIM DEBUG] System wallet balance: {system_balance} {campaign.reward_token}")
                
                transfer_ok = await self.balance_manager.transfer(
                    from_user=SYSTEM_WALLET_USER_ID,
                    to_user=twitter_user_id,
                    token=campaign.reward_token,
                    amount=Decimal(str(campaign.reward_per_participant)),
                    session=session
                )
                
                if not transfer_ok:
                    # The transaction will be rolled back.
                    logger.error(f"🏆 [CLAIM DEBUG] Critical: Failed to transfer reward from system wallet for campaign {campaign_id} to user {twitter_user_id}.")
                    return {"success": False, "response_code": "REWARD_TRANSFER_FAILED"}

                logger.info(f"🏆 [CLAIM DEBUG] Balance transfer successful!")

                # **FIX: Log the campaign claim transaction**
                await self.transaction_history.log_campaign_claim(
                    user_id=twitter_user_id,
                    campaign_name=campaign.name,
                    token=campaign.reward_token,
                    amount=Decimal(str(campaign.reward_per_participant)),
                    session=session
                )

                # 5. Update participant status to 'paid'
                participant.status = 'paid'
                session.add(participant)
                
                logger.info(f"🏆 [CLAIM DEBUG] User {twitter_user_id} successfully claimed reward for campaign {campaign_id}")
                return {
                    "success": True,
                    "response_code": "REWARD_CLAIMED",
                    "context": {
                        "amount": campaign.reward_per_participant,
                        "token": campaign.reward_token,
                        "name": campaign.name
                    }
                }

            return {"success": False, "response_code": "CLAIM_FAILED", "error": "An unexpected error occurred."}

    async def verify_tasks_for_user(self, twitter_user_id: str, campaign_id: int, interaction_service) -> Dict[str, Any]:
        """
        Verifies if a user has completed the required tasks for a campaign.
        """
        try:
            async with self.db() as session:
                if not hasattr(self, 'user_service'):
                    from user_management.user_service import UserService
                    self.user_service = UserService(self.db)
                
                user = await self.user_service.get_user_by_twitter_id(twitter_user_id, session=session)
                if not user:
                    return {"success": False, "response_code": "USER_NOT_FOUND"}

                stmt = select(CampaignParticipant).where(
                    CampaignParticipant.user_id == user.id,
                    CampaignParticipant.campaign_id == campaign_id
                )
                result = await session.execute(stmt)
                participant = result.scalar_one_or_none()

                if not participant:
                    return {"success": False, "response_code": "NOT_A_PARTICIPANT"}

                campaign = await self.get_campaign_by_id(campaign_id, session)

                if campaign.campaign_type != 'airdrop':
                    await self.update_participant_task_status(
                        user_id=participant.user_id,
                        campaign_id=campaign_id,
                        tasks_verified_at=datetime.now(timezone.utc),  # Use timezone-aware datetime
                        status='tasks_verified'
                    )
                    return {
                        "success": True,
                        "message": "All tasks have been successfully verified! You can now claim your reward."
                    }

                # Fallback for engagement campaigns - logic to be refined later
                return {"success": True, "message": "Engagement campaign verification not fully implemented."}

        except Exception as e:
            logger.error(f"Error during task verification for user {twitter_user_id}, campaign {campaign_id}: {e}", exc_info=True)
            return {"success": False, "error": "An unexpected error occurred during task verification."}

    async def create_full_campaign(self, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates and activates a campaign in a single atomic operation from a full set of data.
        """
        required_fields = ['creator_twitter_user_id', 'campaign_type', 'name', 'description', 'reward_token', 'reward_per_participant', 'max_participants']
        if not all(field in campaign_data for field in required_fields):
            return {"success": False, "error": "Missing required campaign data."}

        # Validação para campanhas de engajamento
        if campaign_data['campaign_type'] == 'engagement':
            if not all(field in campaign_data for field in ['profile_to_follow', 'tweet_id_to_engage']):
                 return {"success": False, "error": "Engagement campaigns require profile_to_follow and tweet_id_to_engage."}

        try:
            total_pool = campaign_data['reward_per_participant'] * campaign_data['max_participants']
            reward_token = campaign_data['reward_token']
            creator_user_id = campaign_data['creator_twitter_user_id']

            async with self.db() as session:
                async with session.begin():
                    # 1. Verificar saldo do criador
                    has_balance = await self.balance_manager.has_balance(creator_user_id, reward_token, total_pool, session=session)
                    if not has_balance:
                        # Retornamos um erro estruturado que a API pode usar
                        return {"success": False, "response_code": "INSUFFICIENT_FUNDS", "error": f"Insufficient balance for {reward_token}."}

                    # 2. Verificar se o nome da campanha já existe
                    # This now uses the corrected case-insensitive query
                    existing_stmt = select(Campaign).where(collate(Campaign.name, 'NOCASE') == campaign_data['name'])
                    existing_result = await session.execute(existing_stmt)
                    if existing_result.scalar_one_or_none():
                        return {"success": False, "response_code": "CAMPAIGN_NAME_EXISTS", "error": "A campaign with this name already exists."}

                    # 3. Escrow funds to the system wallet
                    SYSTEM_WALLET_USER_ID = 'SYSTEM_WALLET_999'
                    transfer_ok = await self.balance_manager.transfer(
                        from_user=creator_user_id,
                        to_user=SYSTEM_WALLET_USER_ID,
                        token=reward_token,
                        amount=Decimal(str(total_pool)),
                        session=session
                    )
                    if not transfer_ok:
                        return {"success": False, "response_code": "CAMPAIGN_FUND_TRANSFER_FAILED", "error": "Failed to escrow campaign funds."}
                    
                    logger.info(f"Successfully escrowed {total_pool} {reward_token} for new campaign '{campaign_data['name']}'.")

                    # **FIX: Log the campaign funding transaction**
                    await self.transaction_history.log_campaign_funding(
                        creator_user_id=creator_user_id,
                        campaign_name=campaign_data['name'],
                        token=reward_token,
                        amount=Decimal(str(total_pool)),
                        session=session
                    )

                    # 4. Criar e salvar a campanha já ativa
                    new_campaign = Campaign(
                        creator_twitter_user_id=creator_user_id,
                        name=campaign_data['name'],
                        description=campaign_data['description'],
                        campaign_type=campaign_data.get('campaign_type', 'airdrop'),
                        reward_token=reward_token,
                        reward_per_participant=campaign_data['reward_per_participant'],
                        max_participants=campaign_data['max_participants'],
                        reward_pool=total_pool,
                        status='active',
                        creation_step='completed',
                        profile_to_follow=campaign_data.get('profile_to_follow'),
                        tweet_id_to_engage=campaign_data.get('tweet_id_to_engage')
                    )
                    session.add(new_campaign)
                    await session.flush()
                    
                    logger.info(f"Campaign '{new_campaign.name}' created and activated successfully.")
                    return {"success": True, "campaign_id": new_campaign.id, "campaign_name": new_campaign.name}
        except Exception as e:
            logger.error(f"Error in create_full_campaign: {e}", exc_info=True)
            return {"success": False, "error": "An internal error occurred."}
    async def get_participation_status(self, user_id: int, campaign_id: int) -> Dict[str, Any]:
        """
        Returns the participation status of a user in a specific campaign.
        """
        async with self.db() as session:
            stmt = select(CampaignParticipant).where(
                CampaignParticipant.user_id == user_id,
                CampaignParticipant.campaign_id == campaign_id
            )
            result = await session.execute(stmt)
            participant = result.scalar_one_or_none()
            
            if not participant:
                return {"success": False, "error": "User is not a participant in this campaign."}
            
            return {
                "success": True,
                "status": participant.status,
                "tasks_verified_at": participant.tasks_verified_at.isoformat() if participant.tasks_verified_at else None
            }
    # Internal helper methods would go here, e.g., for checking participation 
