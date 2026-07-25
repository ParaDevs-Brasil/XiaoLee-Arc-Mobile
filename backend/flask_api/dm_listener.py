# ARQUIVADO (2026-07-10) — sem entrypoint, não roda em produção. Ver flask_api/README.md.

import asyncio
import json
import httpx
import logging
import re
from typing import Dict, Any, Set, List
from pathlib import Path
from collections import defaultdict
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import select

from user_management.user_service import UserService
from user_management.authentication_service import AuthenticationService
from services.twitter_api_service import twitter_api_service
from database.models import ProcessedDM
from ai.response_generator import XiaoLeeResponseGenerator

logger = logging.getLogger(__name__)


class DBStateManager:
    def __init__(self, db_session_factory: async_sessionmaker[AsyncSession]):
        self.db_session_factory = db_session_factory

    async def add_processed_id(self, message_id: str):
        """Adds a new message ID to the processed_dms table."""
        try:
            # Check if already processed first to avoid unnecessary DB operations
            if await self.is_processed(message_id):
                logger.debug(f"✅ Message {message_id} already processed, skipping insert")
                return
                
            async with self.db_session_factory() as session:
                async with session.begin():
                    session.add(ProcessedDM(twitter_message_id=message_id))
                    logger.debug(f"✅ Marked message {message_id} as processed")
        except Exception as e:
            # Handle different types of errors appropriately
            error_str = str(e).lower()
            if "unique constraint failed" in error_str or "integrity" in error_str:
                # This is expected - message was already processed (race condition)
                logger.debug(f"✅ Message {message_id} already processed (race condition handled)")
            else:
                # This is an unexpected error that should be logged as an error
                logger.error(f"❌ Unexpected error saving processed DM ID {message_id} to DB: {e}", exc_info=True)

    async def is_processed(self, message_id: str) -> bool:
        """Checks if a message ID has already been processed by querying the DB."""
        try:
            async with self.db_session_factory() as session:
                stmt = select(ProcessedDM).where(ProcessedDM.twitter_message_id == message_id)
                result = await session.execute(stmt)
                return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error(f"Error checking if DM ID {message_id} is processed: {e}", exc_info=True)
            # On error, we default to assuming it's processed to avoid double-sends.
            return True


class DMListenerService:
    """
    A service that runs in the background of the Flask app,
    polling Twitter DMs and processing them by calling the app's own API.
    """

    def __init__(self,
                 db_session_factory: async_sessionmaker[AsyncSession],
                 poll_interval: int = 60,
                 api_base_url: str = "http://127.0.0.1:5000"):
        self.poll_interval = poll_interval
        self.bot_user_id = None
        self.db_session_factory = db_session_factory
        self.user_service = UserService(self.db_session_factory)
        self.auth_service = AuthenticationService(self.db_session_factory)
        self.response_generator = XiaoLeeResponseGenerator(self.db_session_factory)
        self.state_manager = DBStateManager(self.db_session_factory)
        self.api_base_url = api_base_url
        self.http_client = httpx.AsyncClient()
        self.is_first_run = True
        logger.info(
            f"DMListenerService initialized with DB-based State Manager.")

    async def close(self):
        """Closes the HTTP client."""
        await self.http_client.aclose()

    async def start_monitoring(self):
        """Starts the main monitoring loop."""
        logger.info("🤖 Starting DM Listener Service...")

        # Initial delay to allow the main app to start
        await asyncio.sleep(5)

        await self._get_bot_user_id()
        if not self.bot_user_id:
            logger.error(
                "Could not get bot user ID. DM monitoring will not start.")
            return

        while True:
            try:
                logger.info("DM Listener: Polling for new DMs...")
                await self._poll_and_process_dms()
            except Exception as e:
                logger.error(f"❌ Unhandled error in DM monitoring loop: {e}",
                             exc_info=True)
            finally:
                await asyncio.sleep(self.poll_interval)

    async def _run_node_script(self, script_content: str,
                               timeout: int) -> Dict:
        """
        Executes a temporary Node.js script and returns the JSON output.
        Adds robust error handling and logging.
        """
        script_path = Path(
            f"temp_node_script_{asyncio.current_task().get_name()}.js")
        try:
            script_path.write_text(script_content, encoding='utf-8')

            # The command needs to be a list of arguments
            proc = await asyncio.create_subprocess_exec(
                'node',
                str(script_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)

            stdout, stderr = await asyncio.wait_for(proc.communicate(),
                                                    timeout=timeout)

            if proc.returncode != 0:
                error_message = stderr.decode('utf-8').strip()
                logger.error(
                    f"Node.js script failed with code {proc.returncode}: {error_message}"
                )
                return {}

            return json.loads(stdout.decode('utf-8'))

        except asyncio.TimeoutError:
            logger.error(f"Node.js script timed out after {timeout} seconds.")
            proc.kill()
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from Node.js script: {e}")
            return {}
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while running Node.js script: {e}",
                exc_info=True)
            return {}
        finally:
            if script_path.exists():
                script_path.unlink()

    async def _get_bot_user_id(self):
        """Gets the bot's own Twitter user ID."""
        logger.info("Attempting to get bot user ID...")
        script = """
            const { Scraper } = require('agent-twitter-client');
            const fs = require('fs');

            async function getBotUserId() {
                try {
                    const cookiesData = JSON.parse(fs.readFileSync('data/eliza_cookies_v2.json', 'utf8'));
                    const scraper = new Scraper();
                    const csrfToken = cookiesData.find(c => c.name === 'ct0')?.value;
                    if (!csrfToken) {
                        throw new Error('CSRF token (ct0) not found in cookies');
                    }
                    await scraper.setCookies(cookiesData.map(c => `${c.key || c.name}=${c.value}`));
                    scraper.withXCsrfToken(csrfToken);

                    const me = await scraper.me();
                    if (!me) throw new Error('Failed to get authenticated user info');
                    console.log(JSON.stringify({ userId: me.userId, screenName: me.username }));
                } catch (error) {
                    console.error('Error:', error.message);
                    process.exit(1);
                }
            }
            getBotUserId();
        """
        data = await self._run_node_script(script, timeout=20)
        if data and data.get("userId"):
            self.bot_user_id = data["userId"]
            logger.info(
                f"🤖 Bot authenticated as @{data.get('screenName', 'unknown')} (ID: {self.bot_user_id})"
            )
        else:
            logger.error("Failed to retrieve bot user ID.")

    async def _poll_and_process_dms(self):
        """
        Fetches DMs. On the first run, it populates the state manager with all
        existing message IDs without replying. On subsequent runs, it processes
        each new message individually and serially.
        """
        dm_data = await self._fetch_dms_from_twitter()
        if not dm_data:
            return

        conversations = dm_data.get("conversations", [])
        if not conversations:
            logger.info("📭 No conversations found in DM data.")
            return

        if self.is_first_run:
            logger.info("Performing initial DM sync. All existing messages will be marked as processed without sending replies.")
            all_message_ids = [msg.get("id") for conv in conversations for msg in conv.get("messages", []) if msg.get("id")]
            async with self.db_session_factory() as session:
                async with session.begin():
                    for msg_id in all_message_ids:
                        if not await self.state_manager.is_processed(msg_id):
                            session.add(ProcessedDM(twitter_message_id=msg_id))
                await session.commit()
            self.is_first_run = False
            logger.info(f"✅ Initial sync complete. Marked {len(all_message_ids)} messages as processed.")
            return

        logger.info(f"📬 Found {len(conversations)} conversations. Processing new messages...")

        for conv in conversations:
            # Determine the other participant in the conversation
            other_participant = next((p for p in conv.get('participants', []) if p['id'] != self.bot_user_id), None)
            if not other_participant or not other_participant.get('id'):
                continue

            
            twitter_user_id = other_participant['id']
            
            # FIXED: Properly resolve Twitter handle instead of using fallback
            twitter_handle = await self._resolve_twitter_handle(other_participant)
            
            conversation_id = conv.get("conversationId")

            if not conversation_id:
                logger.warning(f"Conversation with {twitter_handle} is missing a conversationId. Skipping.")
                continue

            # Sort messages chronologically to process them in the order they were received
            sorted_messages = sorted(conv.get("messages", []), key=lambda m: int(m["createdAt"]))

            for msg in sorted_messages:
                # Core processing logic for each individual message
                await self._process_single_message(msg, twitter_user_id, twitter_handle, conversation_id)


    async def _fetch_dms_from_twitter(self) -> Dict:
        """Runs the Node.js script to fetch all DM conversations."""
        script = f"""
            const {{ Scraper }} = require('agent-twitter-client');
            const fs = require('fs');

            async function getDMs() {{
                try {{
                    const cookiesData = JSON.parse(fs.readFileSync('data/eliza_cookies_v2.json', 'utf8'));
                    const scraper = new Scraper();
                    const csrfToken = cookiesData.find(c => c.name === 'ct0')?.value;
                    if (!csrfToken) {{
                        throw new Error('CSRF token (ct0) not found in cookies');
                    }}
                    await scraper.setCookies(cookiesData.map(c => `${{c.key || c.name}}=${{c.value}}`));
                    scraper.withXCsrfToken(csrfToken);

                    const dmResponse = await scraper.getDirectMessageConversations();
                    
                    // Enhance participant data by fetching user profiles
                    if (dmResponse && Array.isArray(dmResponse)) {{
                        for (let conversation of dmResponse) {{
                            if (conversation.participants && Array.isArray(conversation.participants)) {{
                                for (let participant of conversation.participants) {{
                                    if (participant.id && !participant.username && !participant.screen_name && !participant.screenName) {{
                                        try {{
                                            console.log(`Fetching profile for user ID: ${{participant.id}}`);
                                            const profile = await scraper.getProfile(participant.id);
                                            if (profile && profile.username) {{
                                                participant.username = profile.username;
                                                participant.name = profile.name;
                                                participant.verified = profile.verified || false;
                                                console.log(`Enhanced participant ${{participant.id}} with handle @${{profile.username}}`);
                                            }}
                                        }} catch (profileError) {{
                                            console.warn(`Could not fetch profile for user ${{participant.id}}: ${{profileError.message}}`);
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }}
                    
                    // DEBUG: Log the structure of the first conversation to see participant data
                    if (dmResponse && dmResponse.length > 0) {{
                        console.log('=== DEBUG: First conversation with enhanced participant data ===');
                        console.log(JSON.stringify(dmResponse[0], null, 2));
                        console.log('=== END DEBUG ===');
                    }}
                    
                    console.log(JSON.stringify(dmResponse, null, 2));
                }} catch (error) {{
                    console.error('Error getting DMs:', error.message);
                    process.exit(1);
                }}
            }}
            getDMs();
        """
        dm_data = await self._run_node_script(script, timeout=45)
        if not dm_data:
            logger.warning("Did not receive any data from the DM fetching script.")
        return dm_data


    async def _process_single_message(self, msg: Dict, twitter_user_id: str, twitter_handle: str, conversation_id: str):
        """
        Processes one message. Checks if it's new, if it's from the user,
        then routes it to token activation or standard chat processing.
        """
        message_id = msg.get("id")
        sender_id = msg.get("senderId")

        # 1. Skip if message is already processed or is from our bot
        if await self.state_manager.is_processed(message_id) or sender_id == self.bot_user_id:
            return
        
        message_text = msg.get("text", "").strip()

        # 2. Skip if the message has no text content
        if not message_text:
            await self.state_manager.add_processed_id(message_id)
            return

        logger.info(f"📩 Processing new message {message_id} from user {twitter_user_id}...")

        # 3. HIGH-PRIORITY: Check if the message is a 6-digit auth token AND is pending in the DB.
        is_potential_token = re.fullmatch(r'\d{6}', message_text)
        
        if is_potential_token and await self.auth_service.is_pending_token(message_text):
            logger.info(f"Received valid, pending auth token '{message_text}' from user {twitter_user_id}.")
            await self._handle_token_activation(message_text, twitter_user_id, twitter_handle, conversation_id)
        else:
            # 4. If not a valid & pending token, process as a standard chat message
            if is_potential_token:
                 logger.info(f"Message '{message_text}' looks like a token, but is not pending in DB. Treating as chat.")
            await self._handle_chat_message(twitter_user_id, twitter_handle, message_text, conversation_id)

        # 5. Mark as processed AFTER handling is complete to ensure atomicity
        await self.state_manager.add_processed_id(message_id)


    async def _handle_token_activation(self, token: str, twitter_user_id: str, twitter_handle: str, conversation_id: str):
        """
        Ensures the user is registered, then attempts to activate a token
        and sends a DM response.
        """
        logger.info(f"Ensuring user {twitter_handle} ({twitter_user_id}) is registered before token activation.")
        await self.user_service.register(handle=twitter_handle, user_id=twitter_user_id)

        token_activated = await self.auth_service.activate_token(token, twitter_user_id)
        
        if token_activated:
            logger.info(f"✅ Token activation successful for user {twitter_user_id}.")
            handler = self.response_generator.response_handlers.get("AUTH_SUCCESS")
            reply_text = await handler({})
        else:
            logger.warning(f"⚠️ Token-like message from {twitter_user_id} activation failed for {twitter_user_id}.")
            reply_text = "❌ Hmm, that token doesn't seem to be valid or has expired. Please request a new authentication token and try again! 🔄"
        try:
            await self._send_dm_response(twitter_user_id, reply_text, conversation_id)
        except Exception as e:
            logger.error(f"Failed to send token activation result DM to {twitter_user_id}: {e}")
            

    async def _handle_chat_message(self, twitter_user_id: str, twitter_handle: str, message_text: str, conversation_id: str):
        """Registers user, auto-authenticates for Twitter DMs, calls the internal chat API, and sends the response."""
        logger.info(f"🔍 DEBUG: Starting _handle_chat_message for user {twitter_user_id} ({twitter_handle})")
        logger.info(f"🔍 DEBUG: Message text: '{message_text}' (length: {len(message_text)})")
        logger.info(f"🔍 DEBUG: Conversation ID: {conversation_id}")
        logger.info(f"🔍 DEBUG: API base URL: {self.api_base_url}")
        
        try:
            # 1. Ensure the user is registered. This is idempotent.
            logger.info(f"🔍 DEBUG: Step 1 - Attempting to register user {twitter_handle} ({twitter_user_id})")
            registration_result = await self.user_service.register(handle=twitter_handle, user_id=twitter_user_id)
            logger.info(f"🔍 DEBUG: Registration result: {registration_result}")
            
            if not registration_result.get("success"):
                logger.error(f"Failed to register user {twitter_handle} ({twitter_user_id}). Aborting message processing.")
                logger.info(f"🔍 DEBUG: Registration failed, returning early")
                return
            
            is_new_user = registration_result.get("is_new_user", False)
            claimed_transfers = registration_result.get("claimed_transfers", [])
            
            # FIXED: Send auto-claim notification if transfers were claimed
            if claimed_transfers:
                # Normalize twitter_handle to avoid double @ symbols
                clean_handle = twitter_handle.strip().replace('@', '')
                logger.info(f"🎉 Auto-claimed {len(claimed_transfers)} transfers during registration for @{clean_handle}")
                
                # Create detailed summary with sender information
                transfer_details = []
                total_tokens = {}
                for transfer in claimed_transfers:
                    token = transfer["token"]
                    amount = transfer["amount"]
                    sender_handle = transfer.get("from_handle", "unknown")
                    claimed_at = transfer.get("claimed_at")
                    
                    # Normalize sender handle to avoid double @ symbols
                    clean_sender = sender_handle.strip().replace('@', '') if sender_handle != "unknown" else "unknown"
                    formatted_sender = f"@{clean_sender}" if clean_sender != "unknown" else "unknown"
                    
                    # Format transfer detail (with date if available)
                    if claimed_at:
                        # Parse and format the date nicely
                        try:
                            from datetime import datetime
                            dt = datetime.fromisoformat(claimed_at.replace('Z', '+00:00'))
                            date_str = dt.strftime("%m/%d %H:%M")
                            detail = f"{amount} {token} from {formatted_sender} (on {date_str})"
                        except:
                            detail = f"{amount} {token} from {formatted_sender}"
                    else:
                        detail = f"{amount} {token} from {formatted_sender}"
                    
                    transfer_details.append(detail)
                    
                    # Add to totals
                    if token in total_tokens:
                        total_tokens[token] += amount
                    else:
                        total_tokens[token] = amount
                
                # Create both detailed and summary formats
                detailed_list = ", ".join(transfer_details)
                
                if len(claimed_transfers) == 1:
                    # Single transfer - use detailed format
                    notification_text = f"🎉 Welcome! I automatically claimed 1 pending transfer for you: {detailed_list}! Your wallet is ready to use."
                else:
                    # Multiple transfers - show count and details
                    token_summary = []
                    for token, amount in total_tokens.items():
                        token_summary.append(f"{amount} {token}")
                    summary_text = ", ".join(token_summary)
                    notification_text = f"🎉 Welcome! I automatically claimed {len(claimed_transfers)} pending transfers for you: {summary_text} (Details: {detailed_list})! Your wallet is ready to use."
                
                # Send the auto-claim notification
                logger.info(f"📤 Sending auto-claim notification to {twitter_user_id}: {notification_text}")
                await self._send_dm_response(twitter_user_id, notification_text, conversation_id)
            
            # 2. For Twitter DMs, auto-authenticate the user to enable seamless onboarding
            logger.info(f"🔍 DEBUG: Step 2 - Auto-authenticating user for Twitter DM")
            
            # Check if user already has an active auth token
            async with self.auth_service.db_session_factory() as session:
                from sqlalchemy import select
                from database.models import AuthToken
                stmt = select(AuthToken).where(
                    AuthToken.twitter_user_id == twitter_user_id,
                    AuthToken.status == 'active'
                )
                result = await session.execute(stmt)
                is_authenticated = result.first() is not None
            
            if not is_authenticated:
                # Create an auto-authentication token for Twitter DM users
                auth_token = await self.auth_service.generate_and_store_token()
                if auth_token:
                    # Auto-activate the token for seamless DM experience
                    activated = await self.auth_service.activate_token(auth_token, twitter_user_id)
                    if activated:
                        logger.info(f"✅ Auto-authenticated user {twitter_user_id} for Twitter DM")
                    else:
                        logger.warning(f"⚠️ Auto-authentication failed for user {twitter_user_id}")
                else:
                    logger.warning(f"⚠️ Failed to generate auth token for user {twitter_user_id}")
            
            # 3. For new users, auto-create a wallet using MCP tools
            if is_new_user:
                try:
                    from ai.mcp_tools import MCPToolsManager
                    mcp_manager = MCPToolsManager(self.user_service.db_session_factory)
                    wallet_result = await mcp_manager.create_wallet_impl(twitter_user_id)
                    if wallet_result.get("success"):
                        logger.info(f"✅ Auto-created wallet for new user {twitter_user_id}")
                    else:
                        logger.warning(f"⚠️ Failed to auto-create wallet for user {twitter_user_id}: {wallet_result}")
                except Exception as wallet_error:
                    logger.error(f"❌ Error during wallet auto-creation for user {twitter_user_id}: {wallet_error}", exc_info=True)
            
            logger.info(f"🔍 DEBUG: User registration successful, proceeding to chat API call")

            # 2. Call the internal /chat_twitter endpoint which now supports confirmation handling
            logger.info(f"Calling /chat_twitter for user {twitter_user_id} ({twitter_handle})...")
            chat_payload = {"user_id": twitter_user_id, "message": message_text}  # ✅ Correct parameter name
            logger.info(f"🔍 DEBUG: Step 2 - Chat API payload: {chat_payload}")
            logger.info(f"🔍 DEBUG: Step 2 - API endpoint: {self.api_base_url}/chat_twitter")
            
            response = await self.http_client.post(
                f"{self.api_base_url}/chat_twitter",
                json=chat_payload,
                timeout=60.0
            )
            logger.info(f"🔍 DEBUG: Chat API response status: {response.status_code}")
            logger.info(f"🔍 DEBUG: Chat API response headers: {dict(response.headers)}")
            
            response.raise_for_status()

            # Add debug for the response structure
            result = response.json()
            logger.info(f"🔍 DEBUG: Chat API full response structure: {result}")
            logger.info(f"🔍 DEBUG: Response keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")

            # Try to extract response more safely
            ai_response = None
            if isinstance(result, dict):
                # Check multiple possible response formats
                ai_response = (result.get("response") or 
                              result.get("message") or 
                              result.get("content") or
                              result.get("text"))
                
                # If response is a list, get the first item
                if isinstance(ai_response, list) and len(ai_response) > 0:
                    if isinstance(ai_response[0], dict):
                        ai_response = ai_response[0].get("content", "")
                    else:
                        ai_response = str(ai_response[0])

            logger.info(f"🔍 DEBUG: Final extracted AI response: '{ai_response}' (type: {type(ai_response)})")

            if not ai_response or (isinstance(ai_response, str) and not ai_response.strip()):
                logger.warning(f"AI returned empty or invalid response for user {twitter_user_id}. Full result: {result}")
                logger.info(f"🔍 DEBUG: No valid AI response, returning early")
                return

            logger.info(f"🔍 DEBUG: Step 3 - Sending DM response to user {twitter_user_id}")
            # 3. Send the AI's reply via DM
            logger.info(f"🔍 DEBUG: _handle_chat_message completed successfully for user {twitter_user_id}")
            # Around lines 370-374, add the missing DM sending call:

            logger.info(f"🔍 DEBUG: Step 3 - Sending DM response to user {twitter_user_id}")
            # 3. Send the AI's reply via DM
            try:
                dm_sent = await self._send_dm_response(twitter_user_id, ai_response, conversation_id)
                if dm_sent:
                    logger.info(f"🔍 DEBUG: DM successfully sent to user {twitter_user_id}")
                else:
                    logger.warning(f"🔍 DEBUG: Failed to send DM to user {twitter_user_id}")
            except Exception as dm_error:
                logger.error(f"🔍 DEBUG: Error sending DM to user {twitter_user_id}: {dm_error}", exc_info=True)

            logger.info(f"🔍 DEBUG: _handle_chat_message completed successfully for user {twitter_user_id}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Error calling chat API for user {twitter_user_id}: {e.response.status_code} {e.response.text}", exc_info=True)
            logger.info(f"🔍 DEBUG: HTTPStatusError details - Status: {e.response.status_code}, URL: {e.request.url}, Method: {e.request.method}")
            logger.info(f"🔍 DEBUG: Request headers: {dict(e.request.headers)}")
            try:
                logger.info(f"🔍 DEBUG: Response content: {e.response.text}")
            except Exception:
                logger.info(f"🔍 DEBUG: Could not read response content")
        except Exception as e:
            logger.error(f"Error handling chat message from user {twitter_user_id}: {e}", exc_info=True)
            logger.info(f"🔍 DEBUG: Unexpected error in _handle_chat_message: {type(e).__name__}: {str(e)}")
            logger.info(f"🔍 DEBUG: Error occurred for user {twitter_user_id}, message: '{message_text}', conversation: {conversation_id}")


    async def _send_dm_response(self, recipient_id: str, text: str,
                                conversation_id: str) -> bool:
        """Sends a DM response to a user with proper text escaping."""
        logger.info(f"Replying to {recipient_id}: '{text[:50]}...'")
        
        # Properly escape the text for JavaScript to avoid injection and escaping issues
        # Replace problematic characters that could break the JavaScript string
        escaped_text = (text.replace('\\', '\\\\')  # Escape backslashes first
                           .replace('`', '\\`')      # Escape template literal backticks
                           .replace('${', '\\${')    # Escape template literal interpolation
                           .replace('\n', '\\n')     # Escape newlines
                           .replace('\r', '\\r')     # Escape carriage returns
                           .replace('\t', '\\t'))    # Escape tabs
        
        script = f"""
            const {{ Scraper }} = require('agent-twitter-client');
            const fs = require('fs');

            async function sendDM() {{
                try {{
                    const cookiesData = JSON.parse(fs.readFileSync('data/eliza_cookies_v2.json', 'utf8'));
                    const scraper = new Scraper();
                    const csrfToken = cookiesData.find(c => c.name === 'ct0')?.value;
                    if (!csrfToken) {{
                        throw new Error('CSRF token (ct0) not found in cookies');
                    }}
                    await scraper.setCookies(cookiesData.map(c => `${{c.key || c.name}}=${{c.value}}`));
                    scraper.withXCsrfToken(csrfToken);
                    
                    // Use the escaped text directly in template literal
                    await scraper.sendDirectMessage(
                        '{conversation_id}',
                        `{escaped_text}`
                    );
                    console.log(JSON.stringify({{ success: true }}));
                }} catch (error) {{
                    console.error('Error sending DM:', error.message);
                    process.exit(1);
                }}
            }}
            sendDM();
        """
        result = await self._run_node_script(script, timeout=30)
        if result.get("success"):
            logger.info(f"✅ Successfully sent DM to {recipient_id}")
            return True
        else:
            logger.error(f"❌ Failed to send DM to {recipient_id}")
            return False

    async def _resolve_twitter_handle(self, participant: Dict[str, Any]) -> str:
        """
        Resolve Twitter handle with proper fallback logic
        
        This method tries multiple approaches to get the real Twitter handle:
        1. Use the username from the API response
        2. Make additional API calls if needed
        3. Only fall back to user_{id} if absolutely necessary
        """
        user_id = participant.get('id')
        
        # First try: Get username from the participant data
        username = participant.get('username')
        if username:
            return username
        
        # Try alternative field names that might contain the handle
        screen_name = participant.get('screen_name') or participant.get('screenName')
        if screen_name:
            return screen_name
        
        # Second try: Check if we have this user in our database with a real handle
        try:
            async with self.db_session_factory() as session:
                from database.models import User
                stmt = select(User).where(User.twitter_user_id == user_id)
                result = await session.execute(stmt)
                existing_user = result.scalar_one_or_none()
                
                if existing_user and not existing_user.twitter_handle.startswith('user_'):
                    # Normalize handle to avoid double @ symbols
                    clean_handle = existing_user.twitter_handle.strip().replace('@', '')
                    logger.info(f"🗃️ Found real handle in database: @{clean_handle} (ID: {user_id})")
                    return clean_handle
        except Exception as e:
            logger.warning(f"⚠️ Database lookup failed for user {user_id}: {e}")
        
        # Third try: Make an API call to resolve the handle
        # TODO: Implement actual Twitter API lookup here
        # For now, we'll use the mock data from our Twitter service
        try:
            from services.twitter_api_service import twitter_api_service
            twitter_info = await twitter_api_service.get_user_by_id(user_id)
            if twitter_info:
                logger.info(f"🐦 Resolved handle via Twitter API: @{twitter_info.username} (ID: {user_id})")
                return twitter_info.username
        except Exception as e:
            logger.warning(f"⚠️ Twitter API lookup failed for user {user_id}: {e}")
        
        # Last resort: Use fallback format (this should be rare now)
        fallback_handle = f"user_{user_id}"
        logger.warning(f"⚠️ Using fallback handle: @{fallback_handle} (ID: {user_id})")
        logger.warning(f"   This may prevent the user from claiming pending transfers!")
        logger.warning(f"   Consider improving Twitter API integration to resolve real handles.")
        
        return fallback_handle
