# ARQUIVADO (2026-07-10) — sem entrypoint, não roda em produção. Ver flask_api/README.md.

import logging
import asyncio
import os
import httpx
import json
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, request, jsonify
from typing import Any, Dict, Optional
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sse_starlette import EventSourceResponse
from user_management.user_service import UserService
from user_management.authentication_service import AuthenticationService
from user_management.campaign_service import CampaignService
from user_management.wallet_service import WalletService
from ai.response_generator import XiaoLeeResponseGenerator
from ai.llm_client import LLMClient
from swaps.balance_manager import BalanceManager
from ai.mcp_tools import MCPToolsManager
from database.models import WebSession, User, AuthToken, DMLog
from swaps.price_manager import PriceManager

logger = logging.getLogger(__name__)


class ChatHandler:

    def __init__(self, db_session_factory: async_sessionmaker[AsyncSession]):
        self.db_session_factory = db_session_factory
        self.response_generator = XiaoLeeResponseGenerator(db_session_factory)
        self.user_service = UserService(self.db_session_factory)
        self.auth_service = AuthenticationService(self.db_session_factory)
        self.campaign_service = CampaignService(self.db_session_factory)
        self.wallet_service = WalletService(self.db_session_factory)
        self.mcp_manager = MCPToolsManager(db_session_factory)
        self.pending_confirmations: Dict[str, Any] = {}
        logger.info("🤖 AI ChatHandler initialized with services.")

    async def _log_chat_message(self, user_id: int, session_id: str,
                                content: str, message_type: str,
                                request_id: str):
        """Helper to log web chat messages to DMLog."""
        try:
            async with self.db_session_factory() as session:
                log_entry = DMLog(user_id=user_id,
                                  content=content,
                                  message_type=message_type,
                                  platform='web',
                                  session_id=session_id,
                                  conversation_id=session_id,
                                  request_id=request_id)
                session.add(log_entry)
                await session.commit()
        except Exception as e:
            logger.error(
                f"Failed to log web chat message (type: {message_type}): {e}",
                exc_info=True)

    async def is_twitter_user_authenticated(self,
                                            twitter_user_id: str) -> bool:
        """
        Checks if a Twitter user is authenticated by looking for an 'active'
        auth token linked to their account. This is the definitive check for DM users.
        """
        async with self.db_session_factory() as session:
            stmt = select(AuthToken).where(
                AuthToken.twitter_user_id == twitter_user_id,
                AuthToken.status == 'active')
            result = await session.execute(stmt)
            active_token = result.first()
            return active_token is not None

    async def get_user_from_session(self) -> Optional[User]:
        """Validates session_id from Authorization header and returns the user.

        Accepts two Bearer token formats:
        1. google_session_* / tg_session_* — looked up via WebSession table
        2. google_* / tg_* / devnet_* — treated directly as twitter_user_id
        """
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ')[1].strip()
        if not token:
            return None

        async with self.db_session_factory() as session:
            # 1. Try WebSession lookup (google_session_*, tg_session_*)
            stmt = select(WebSession).where(WebSession.session_id == token)
            web_session = (await session.execute(stmt)).scalar_one_or_none()

            if web_session:
                if web_session.expires_at < datetime.utcnow():
                    await session.delete(web_session)
                    await session.commit()
                    return None
                return await self.user_service.get_user_by_twitter_id(
                    web_session.twitter_user_id)

            # 2. Fallback: token IS the twitter_user_id (google_*, tg_*, devnet_*)
            user = await self.user_service.get_user_by_twitter_id(token)
            return user

    async def build_user_dossier(self, user: Optional[User],
                                 session_id: str) -> Dict:
        """
        Builds a user dossier.
        --- FIX ---
        Now accepts session_id to check for and include a pending action.
        """
        price_manager = PriceManager(self.db_session_factory)
        all_prices = await price_manager.get_all()
        available_tokens = sorted(list(all_prices.keys()))

        # --- FIX: INJECT PENDING ACTION INTO DOSSIER ---
        # Check if there is a pending action for this session and add it to the dossier.
        # This is the crucial step to link the confirmation back to the AI.
        pending_action_for_dossier = self.pending_confirmations.get(session_id)
        # --- END FIX ---

        if not user:
            return {
                "user_info": {},
                "balances": {},
                "history": {},
                "pending_action": pending_action_for_dossier,
                "pending_campaign": None,
                "available_tokens": available_tokens
            }

        balance_manager = BalanceManager(self.db_session_factory)
        balances = await balance_manager.get_all(user.twitter_user_id)

        # Add pending campaign info
        pending_campaign_obj = await self.campaign_service.get_pending_campaign_by_user(
            user.twitter_user_id)
        pending_campaign_dict = None
        if pending_campaign_obj:
            pending_campaign_dict = {
                "id": pending_campaign_obj.id,
                "name": pending_campaign_obj.name,
                "campaign_type": pending_campaign_obj.campaign_type,
                "creation_step": pending_campaign_obj.creation_step
            }

        # --- ADD DM HISTORY ---
        history_logs = []
        async with self.db_session_factory() as session:
            stmt = select(DMLog).where(DMLog.user_id == user.id).order_by(
                DMLog.created_at.desc()).limit(10)
            result = await session.execute(stmt)
            logs = result.scalars().all()
            for log in logs:
                # Assuming DMLog has 'message_type' (e.g., 'user' or 'ai') and 'content'
                history_logs.append({
                    "role": log.message_type,
                    "content": log.content
                })
        history_logs.reverse(
        )  # Puts the logs in chronological order for the AI
        # --- END DM HISTORY ---

        return {
            "user_info": {
                "twitter_user_id": user.twitter_user_id,
                "twitter_handle": user.twitter_handle,
            },
            "balances": balances,
            "history": history_logs,
            "pending_action": pending_action_for_dossier,
            "pending_campaign": pending_campaign_dict,
            "available_tokens": available_tokens
        }

    async def handle_chat_request(self, user: Optional[User], message: str,
                                  is_authenticated: bool, source: str):
        """
        Main logic for handling a chat request, including confirmation flows.
        """
        session_id = request.headers.get('Authorization', '').split(' ')[-1]
        request_id = f"req_{secrets.token_hex(8)}"

        # Debug logging for all web chat requests
        if source == 'web':
            logger.info(f"🔍 DEBUG: Web chat request - session_id: {session_id}")
            logger.info(f"🔍 DEBUG: User: {user.twitter_handle if user else 'None'} (authenticated: {is_authenticated})")
            logger.info(f"🔍 DEBUG: Message: '{message}'")

        # Log user message for web chat
        if source == 'twitter' and user:
            await self._log_chat_message(user.id, session_id, message, 'user',
                                         request_id)

        # Always proceed with the normal flow. The ResponseGenerator will handle
        # pending actions based on the dossier content.
        dossier = await self.build_user_dossier(user, session_id)

        # --- Inject pending transfer auto-claim and welcome message before balance response ---
        welcome_message = None
        if user and message.strip().lower() in ["balance", "check balance", "wallet", "show balance", "my balance", "check my balance"]:
            # Only trigger on balance-related queries
            logger.info(f"🎁 [AUTO-CLAIM] Balance request detected from {user.twitter_handle}: '{message}'")
            async with self.db_session_factory() as session:
                try:
                    from services.modern_transfer_service import ModernTransferService
                    transfer_service = ModernTransferService()
                    logger.info(f"🎁 [AUTO-CLAIM] Attempting to claim pending transfers for {user.twitter_user_id}")
                    claimed_transfers = await transfer_service.claim_pending_transfers(session, user.twitter_user_id)
                    logger.info(f"🎁 [AUTO-CLAIM] Claimed {len(claimed_transfers) if claimed_transfers else 0} transfers")
                    if claimed_transfers:
                        # Format welcome message using XiaoLeeResponseGenerator
                        context = {
                            "claimed": len(claimed_transfers),
                            "transfers": [
                                {
                                    "token": t.token_symbol,
                                    "amount": float(t.amount),
                                    "from_handle": t.from_twitter_handle,
                                    "claimed_at": t.claimed_at.isoformat() if t.claimed_at else None
                                } for t in claimed_transfers
                            ]
                        }
                        welcome_message = await self.response_generator._generate_pending_transfers_claimed_response(context)
                        logger.info(f"🎁 [AUTO-CLAIM] Generated welcome message: {welcome_message[:100]}...")
                    else:
                        logger.info(f"🎁 [AUTO-CLAIM] No transfers to claim")
                except Exception as e:
                    logger.error(f"Error auto-claiming pending transfers during balance check: {e}", exc_info=True)

        if source == 'web':
            logger.info(f"🔍 DEBUG: Built dossier: {dossier}")
            logger.info(f"🔍 DEBUG: Pending confirmations: {self.pending_confirmations}")

        # Use the actual pending_confirmations to enable proper confirmation flow
        # The MCP system manages its own confirmations, but we need to pass the session-based ones
        result = await self.response_generator.generate_response(
            message=message,
            dossier=dossier,
            pending_confirmations=self.pending_confirmations,
            is_authenticated=is_authenticated,
            auth_service=self.auth_service,
            source=source)

        if source == 'web':
            logger.info(f"🔍 DEBUG: Response generator result: {result}")

        # After generating a response, the generator may return a new pending action.
        # This handler is responsible for persisting it for the current session.
        pending_action = result.pop("pending_action", None)
        if pending_action:
            logger.info(
                f"Saving pending action for session {session_id}: {pending_action}"
            )
            # We now store the pending action directly in the dossier for the next request.
            # This is a conceptual change. The actual implementation of persisting this
            # between requests would require a session storage mechanism (e.g., Redis, DB).
            # For now, we update a local dictionary as was done previously.
            self.pending_confirmations[session_id] = pending_action
        elif session_id in self.pending_confirmations:
            # Clean up the confirmation now that it has been processed
            del self.pending_confirmations[session_id]

        # Log AI response for web chat (normal flow)
        if source == 'web' and user:
            ai_content = result.get("response", [{}])[0].get("content")
            if ai_content:
                await self._log_chat_message(user.id, session_id, ai_content,
                                             'assistant', request_id)

        # If there was a welcome message for auto-claimed transfers, prepend it to the response
        if welcome_message:
            logger.info(f"🎁 [AUTO-CLAIM] Adding welcome message to response")
            # Prepend the welcome message to the AI response with correct format
            if "response" in result and isinstance(result["response"], list) and result["response"]:
                result["response"].insert(0, {"type": "text", "content": welcome_message})
            else:
                result["response"] = [{"type": "text", "content": welcome_message}]
        return jsonify(result)

    async def process(self, dossier: Dict, message: str,
                      is_authenticated: bool, source: str) -> dict:
        """DEPRECATED: Use handle_chat_request instead."""
        return await self.response_generator.generate_response(
            message,
            dossier,
            self.pending_confirmations,
            is_authenticated=is_authenticated,
            auth_service=self.auth_service,
            source=source)


def create_chat_blueprint(
    db_session_factory: async_sessionmaker[AsyncSession]
) -> tuple[Blueprint, ChatHandler]:
    chat_bp = Blueprint('chat', __name__)
    handler = ChatHandler(db_session_factory)

    # ===================================================================
    #                           CAMPAIGN ROUTES
    # ===================================================================

    @chat_bp.route('/campaigns', methods=['GET'])
    async def list_campaigns():
        """
        Lists all active campaigns. Publicly accessible.
        """
        campaigns = await handler.campaign_service.list_campaigns()
        return jsonify({"success": True, "campaigns": campaigns}), 200

    @chat_bp.route('/campaigns', methods=['POST'])
    async def create_campaign():
        """
        Creates a new campaign, funded by the authenticated user.
        Any user can create a campaign as long as they have enough funds.
        """
        user = await handler.get_user_from_session()
        if not user:
            return jsonify({
                "success": False,
                "error": "Authentication required"
            }), 401

        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "Invalid request body"
            }), 400

        # Required fields validation
        required_fields = [
            'title', 'description', 'reward_token', 'reward_per_participant',
            'max_participants'
        ]
        if not all(field in data for field in required_fields):
            return jsonify({
                "success": False,
                "error": "Missing required fields"
            }), 400

        result = await handler.campaign_service.create_funded_campaign(
            user.twitter_user_id, data)

        if result.get("success"):
            return jsonify(
                result), 201  # 201 Created is ideal for successful POSTs
        else:
            return jsonify(result), 400

    @chat_bp.route('/campaigns/create_full', methods=['POST'])
    async def create_full_campaign():
        """Creates and activates a campaign from a single request."""
        user = await handler.get_user_from_session()
        if not user:
            return jsonify({
                "success": False,
                "error": "Authentication required"
            }), 401

        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "Request body must be JSON."
            }), 400

        # Add the authenticated user as creator
        data['creator_twitter_user_id'] = user.twitter_user_id

        result = await handler.campaign_service.create_full_campaign(data)

        if not result.get("success"):
            return jsonify(result), 400

        return jsonify(result), 201

    @chat_bp.route('/campaigns/me', methods=['GET'])
    async def list_my_campaigns():
        """Lists campaigns for the currently authenticated user."""
        user = await handler.get_user_from_session()
        if not user:
            return jsonify({
                "success": False,
                "error": "Authentication required"
            }), 401

        campaigns = await handler.campaign_service.list_participating_campaigns(
            user.id)
            
        # Rename participation_status to status for consistency with the MCP tools
        for campaign in campaigns:
            if "participation_status" in campaign:
                campaign["status"] = campaign.pop("participation_status")

        return jsonify({"success": True, "campaigns": campaigns}), 200

    @chat_bp.route('/campaigns/join', methods=['POST'])
    async def join_campaign():
        """Joins a campaign for the authenticated user."""
        user = await handler.get_user_from_session()
        if not user:
            return jsonify({
                "success": False,
                "error": "Authentication required"
            }), 401

        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "Request body must be JSON."
            }), 400

        campaign_identifier = data.get('campaign_identifier')
        if not campaign_identifier:
            return jsonify({
                "success":
                False,
                "error":
                "Missing required parameter: campaign_identifier."
            }), 400

        campaign_id_to_join = None
        if isinstance(campaign_identifier,
                      int) or str(campaign_identifier).isdigit():
            campaign_id_to_join = int(campaign_identifier)
        else:
            campaign = await handler.campaign_service.get_campaign_by_name(
                campaign_identifier)
            if campaign:
                campaign_id_to_join = campaign.id

        if not campaign_id_to_join:
            return jsonify({
                "success": False,
                "error": "Campaign not found."
            }), 404

        result = await handler.campaign_service.join_campaign(
            user.twitter_user_id, campaign_id_to_join)

        if not result.get("success"):
            return jsonify(result), 400

        return jsonify(result), 200

    @chat_bp.route('/campaigns/verify', methods=['POST'])
    async def verify_campaign_tasks():
        """Verifies campaign tasks for the authenticated user."""
        user = await handler.get_user_from_session()
        if not user:
            return jsonify({
                "success": False,
                "error": "Authentication required"
            }), 401

        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "Request body must be JSON."
            }), 400

        campaign_identifier = data.get('campaign_identifier')
        if not campaign_identifier:
            return jsonify({
                "success":
                False,
                "error":
                "Missing required parameter: campaign_identifier."
            }), 400

        result = await handler.mcp_manager.verify_campaign_tasks_impl(
            user_id=user.twitter_user_id,
            campaign_identifier=campaign_identifier)

        if not result.get("success"):
            return jsonify(result), 400

        return jsonify(result), 200

    @chat_bp.route('/campaigns/claim', methods=['POST'])
    async def claim_campaign_reward():
        """Claims a campaign reward for the authenticated user."""
        user = await handler.get_user_from_session()
        if not user:
            return jsonify({
                "success": False,
                "error": "Authentication required"
            }), 401

        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "Request body must be JSON."
            }), 400

        campaign_identifier = data.get('campaign_identifier')
        if not campaign_identifier:
            return jsonify({
                "success":
                False,
                "error":
                "Missing required parameter: campaign_identifier."
            }), 400

        result = await handler.mcp_manager.claim_campaign_reward_impl(
            user_id=user.twitter_user_id,
            campaign_identifier=campaign_identifier)

        if not result.get("success"):
            return jsonify(result), 400

        return jsonify(result), 200

    # ===================================================================
    #                         AUTH & USER ROUTES
    # ===================================================================

    @chat_bp.route('/auth/status/<string:token>', methods=['GET'])
    async def get_auth_status(token: str):
        """
        Checks the auth token status. If active, creates a new web session
        and returns the session_id to the client.
        """
        async with db_session_factory() as session:
            stmt = select(AuthToken).where(AuthToken.token == token)
            auth_token = (await session.execute(stmt)).scalar_one_or_none()

            if not auth_token:
                return jsonify({"status": "not_found"}), 404

            if auth_token.status == 'active' and auth_token.twitter_user_id:
                user_service = UserService(db_session_factory)
                user = await user_service.get_user_by_twitter_id(
                    auth_token.twitter_user_id)

                if not user:
                    logger.warning(
                        f"Session creation failed for token {token}: User ID {auth_token.twitter_user_id} not found in users table."
                    )
                    return jsonify({"status": "user_not_found"}), 404

                session_id = secrets.token_hex(32)
                expires_at = datetime.utcnow() + timedelta(days=30)

                new_session = WebSession(
                    session_id=session_id,
                    twitter_user_id=auth_token.twitter_user_id,
                    expires_at=expires_at)
                session.add(new_session)
                await session.commit()

                logger.info(
                    f"New web session created for user {auth_token.twitter_user_id}"
                )
                return jsonify({
                    "status": "active",
                    "session_id": session_id,
                    "twitter_user_id": user.twitter_user_id
                }), 200

            if auth_token.status == 'pending' and auth_token.expires_at < datetime.utcnow(
            ):
                return jsonify({"status": "expired"}), 410

            if auth_token.expires_at < datetime.utcnow():
                logger.info(f"Auth token {token} is expired.")
                return jsonify({"status": "expired"}), 410

            return jsonify({"status": "pending"}), 202

    @chat_bp.route('/user/<string:twitter_user_id>', methods=['GET'])
    def get_user_dossier(twitter_user_id: str):
        """
        Retrieves a complete dossier for a user, including profile info,
        wallet balances, and full transaction, swap, and DM history.
        """

        async def get_dossier_async():
            user_service = UserService(db_session_factory)
            balance_manager = BalanceManager(db_session_factory)
            campaign_service = CampaignService(db_session_factory)
            wallet_service = WalletService(db_session_factory)
            mcp_manager = MCPToolsManager(db_session_factory)

            user = await user_service.get_user_by_twitter_id(twitter_user_id)
            if not user:
                return jsonify({
                    "success": False,
                    "error": "User not found"
                }), 404

            user_info = {
                "twitter_user_id":
                user.twitter_user_id,
                "twitter_handle":
                user.twitter_handle,
                "internal_id":
                user.id,
                "created_at":
                user.created_at.isoformat() if user.created_at else None
            }

            balances = await balance_manager.get_all(user.twitter_user_id)

            # Use wallet_service for transaction-related history
            wallet_activity = await wallet_service.get_wallet_activity(user.id, limit=10)
            transaction_history = await wallet_service.get_transaction_history(user.id, limit=10)
            
            # Use MCP manager for chat history
            dm_history_result = await mcp_manager.get_recent_messages_impl(str(user.id), limit=10)
            dm_history = dm_history_result.get("messages", []) if dm_history_result.get("success", False) else []
            
            campaign_history = await campaign_service.list_participating_campaigns(
                user.id)
                
            # Rename participation_status to status for consistency with the MCP tools
            for campaign in campaign_history:
                if "participation_status" in campaign:
                    campaign["status"] = campaign.pop("participation_status")

            dossier_data = {
                "user_info": user_info,
                "balances": balances,
                "history": {
                    "swaps": wallet_activity.get("activity", [])[:10],
                    "transactions": transaction_history[:10],
                    "chat_history": dm_history
                },
                "campaigns": campaign_history
            }

            return jsonify({"success": True, "dossier": dossier_data}), 200

        return asyncio.run(get_dossier_async())

    @chat_bp.route('/user/me', methods=['GET'])
    async def get_current_user_dossier():
        """
        Retrieves a complete dossier for the currently authenticated user,
        identified by their session_id.
        """
        user = await handler.get_user_from_session()
        if not user:
            return jsonify({
                "success":
                False,
                "error":
                "Authentication required or session invalid"
            }), 401

        user_service = UserService(db_session_factory)
        balance_manager = BalanceManager(db_session_factory)
        wallet_service = WalletService(db_session_factory)

        user_info = {
            "twitter_user_id": user.twitter_user_id,
            "twitter_handle": user.twitter_handle,
            "internal_id": user.id,
            "created_at":
            user.created_at.isoformat() if user.created_at else None
        }

        balances = await balance_manager.get_all(user.twitter_user_id)
        
        # Use wallet_service for transaction-related history
        wallet_activity = await wallet_service.get_wallet_activity(user.id, limit=10)
        transaction_history = await wallet_service.get_transaction_history(user.id, limit=10)

        dossier_data = {
            "user_info": user_info,
            "balances": balances,
            "history": {
                "swaps": wallet_activity.get("activity", [])[:10],
                "transactions": transaction_history[:10]
            }
        }

        return jsonify({"success": True, "user": dossier_data}), 200

    @chat_bp.route('/chat', methods=['GET'])
    def chat_info():
        return jsonify({
            "message":
            "Xiao Lee AI Chat API",
            "version":
            "2.0",
            "features": [
                "Real AI with DeepSeek", "MCP Tools Integration",
                "Crypto Operations", "Natural Language Processing"
            ],
            "endpoints": {
                "POST /chat": {
                    "description":
                    "Send chat message to AI. Requires a session_id via Bearer token.",
                    "body": {
                        "message": "string"
                    }
                },
                "POST /chat_twitter": {
                    "description":
                    "Send chat message to AI from Twitter. Requires twitter_user_id.",
                    "body": {
                        "twitter_user_id": "string",
                        "message": "string"
                    }
                },
                "GET /health": "Health check"
            }
        })

    @chat_bp.route('/chat', methods=['POST'])
    async def chat():
        """
        Main chat endpoint. Handles both authenticated and unauthenticated users.
        If unauthenticated, it will initiate the authentication flow.
        """
        data = request.get_json()
        if not data or "message" not in data:
            return jsonify({
                "success": False,
                "error": "Missing 'message' in request body",
                "response_code": "BAD_REQUEST"
            }), 400

        message = data.get("message")

        user = await handler.get_user_from_session()

        is_authenticated = user is not None

        return await handler.handle_chat_request(
            user=user,
            message=message,
            is_authenticated=is_authenticated,
            source='web')

    @chat_bp.route('/chat_twitter', methods=['POST'])
    async def chat_twitter():
        data = request.get_json()
        twitter_user_id = data.get("user_id")
        message = data.get("message")

        if not all([twitter_user_id, message]):
            return jsonify({"error": "user_id and message are required"}), 400

        user = await handler.user_service.get_user_by_twitter_id(
            twitter_user_id)
        print(f"🔍 User found: {user}")

        is_auth = True

        return await handler.handle_chat_request(user,
                                                 message,
                                                 is_authenticated=is_auth,
                                                 source="twitter")

    @chat_bp.route('/sse', methods=['GET'])
    async def sse_endpoint():

        async def event_generator():
            print("🚀 SSE funcao chamada - Connection started")
            connection_count = 0

            try:
                while True:
                    connection_count += 1
                    current_time = datetime.now().strftime("%H:%M:%S")

                    # Diferentes tipos de mensagens para testar
                    messages = [{
                        'type': 'heartbeat',
                        'message': f'Heartbeat #{connection_count}',
                        'timestamp': current_time
                    }, {
                        'type': 'notification',
                        'message': 'Xiaolee says hello! 🌸',
                        'timestamp': current_time
                    }, {
                        'type': 'transaction',
                        'message': 'Mock transaction completed',
                        'amount': 100.50,
                        'timestamp': current_time
                    }, {
                        'type': 'text',
                        'message': 'Just a regular text message',
                        'timestamp': current_time
                    }]

                    # Alternar entre diferentes tipos de mensagem
                    message = messages[connection_count % len(messages)]

                    print(f"📤 Sending SSE: {message}")
                    yield f"data: {json.dumps(message)}\n\n"

                    # Aguardar antes da próxima mensagem
                    await asyncio.sleep(3)

            except Exception as e:
                print(f"❌ SSE Error: {e}")
                error_msg = {
                    'type': 'error',
                    'message': f'SSE Error: {str(e)}',
                    'timestamp': datetime.now().strftime("%H:%M:%S")
                }
                yield f"data: {json.dumps(error_msg)} teve erro tá\n\n"

        return EventSourceResponse(event_generator())

    @chat_bp.route('/health', methods=['GET'])
    def health():
        return jsonify({
            "status": "healthy",
            "service": "xiao-lee-ai-chat-api",
            "version": "2.0",
            "ai_enabled": True,
            "mcp_tools": True
        })

    return chat_bp, handler
