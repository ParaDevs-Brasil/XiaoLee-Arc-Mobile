#!/usr/bin/env python3
"""
Xiao Lee DM Monitor
Integrates agent-twitter-client with Python system for real-time DM monitoring
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set

import httpx
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy import select

# Load environment variables
load_dotenv()

# Setup paths and logging
from database.database import init_db
from database.models import DMLog, ProcessedDM
from user_management.user_service import UserService
from user_management.authentication_service import AuthenticationService
from .twitter_client import TwitterClient

logger = logging.getLogger(__name__)

class DMListenerService:
    """The main service for listening to and processing Twitter DMs."""
    
    def __init__(self, poll_interval: int = 15):
        self.poll_interval = poll_interval
        self.db_session_factory = init_db()
        self.user_service = UserService(self.db_session_factory)
        self.auth_service = AuthenticationService(self.db_session_factory)
        self.twitter_client = TwitterClient()
        self.bot_user_id: Optional[str] = None
        self.user_message_batches: Dict[str, List[str]] = {}
        self.batch_timers: Dict[str, asyncio.Task] = {}
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def start_monitoring(self):
        """Main loop to start polling for DMs."""
        logger.info("🤖 Starting DM Listener Service...")
        self.bot_user_id = await self.twitter_client.get_bot_user_id()
        
        if not self.bot_user_id:
            logger.critical("❌ Could not get bot user ID. DM listener cannot start.")
            return

        while True:
            try:
                await self._poll_and_process_dms()
            except Exception as e:
                logger.error(f"❌ Unhandled error in monitoring loop: {e}", exc_info=True)
            
            logger.info(f"Waiting for {self.poll_interval} seconds until next poll.")
            await asyncio.sleep(self.poll_interval)

    async def _poll_and_process_dms(self):
        """Fetches DMs and processes them."""
        logger.info("🔍 Polling for new DMs...")
        conversations = await self.twitter_client.get_dms()
        
        if not conversations:
            logger.info("No new DM conversations found.")
            return
            
        logger.info(f"Found {len(conversations)} conversations to process.")
        for conv in conversations:
            await self._process_conversation(conv)

    async def _process_conversation(self, conversation: Dict[str, Any]):
        """Processes all new messages in a single conversation."""
        conversation_id = conversation.get("conversation_id")
        if not conversation_id:
            return

        # The other participant's ID is the conversation ID minus our bot's ID and the hyphen
        participants = conversation_id.split('-')
        sender_id = next((p for p in participants if p != self.bot_user_id), None)

        if not sender_id:
            logger.warning(f"Could not determine sender in conversation {conversation_id}")
            return

        sorted_messages = sorted(conversation.get("messages", []), key=lambda m: m.get("created_at", 0))

        for message in sorted_messages:
            message_id = message.get("id")
            if not message_id:
                continue

            async with self.db_session_factory() as session:
                stmt = select(ProcessedDM).where(ProcessedDM.twitter_message_id == message_id)
                result = await session.execute(stmt)
                if result.scalar_one_or_none() is not None:
                    continue # Skip already processed messages

            if message.get("sender_id") == self.bot_user_id:
                async with self.db_session_factory() as session:
                    async with session.begin():
                        session.add(ProcessedDM(twitter_message_id=message_id))
                continue

            message_text = message.get("text", "").strip()
            if message_text:
                await self._process_dm(conversation_id, message_text, sender_id)
            
            async with self.db_session_factory() as session:
                async with session.begin():
                    session.add(ProcessedDM(twitter_message_id=message_id))

    async def _process_dm(self, conversation_id: str, message_text: str, sender_id: str):
        """
        Processes a single DM. Checks for an auth token first, otherwise batches the message.
        """
        # Step 1: Check if the message is a 6-digit authentication token
        if re.fullmatch(r'\d{6}', message_text):
            logger.info(f"Potential auth token '{message_text}' received from user {sender_id}.")
            token_activated = await self.auth_service.activate_token(message_text, sender_id)
            
            if token_activated:
                logger.info(f"Token activation successful for user {sender_id}.")
                try:
                    await self.twitter_client.send_dm(
                        conversation_id=conversation_id,
                        text="✅ Sua conta foi autenticada com sucesso! Você já pode usar todos os nossos recursos no chat."
                    )
                except Exception as e:
                    logger.error(f"Failed to send auth confirmation DM to {sender_id}: {e}")
                return # Stop processing this message further
            else:
                logger.warning(f"Token-like message from {sender_id} failed activation. Treating as regular chat.")

        # Step 2: If not an auth token, proceed with message batching logic
        if sender_id not in self.user_message_batches:
            self.user_message_batches[sender_id] = []

        self.user_message_batches[sender_id].append(message_text)
        
        # If a timer is already running for this user, cancel it to reset the countdown
        if sender_id in self.batch_timers:
            self.batch_timers[sender_id].cancel()
        
        # Start a new timer to process the batch after a short delay
        self.batch_timers[sender_id] = asyncio.create_task(
            self._schedule_batch_processing(conversation_id, sender_id)
        )

    async def _schedule_batch_processing(self, conversation_id: str, sender_id: str):
        """Waits for a short period before processing a user's batched messages."""
        await asyncio.sleep(5) # Wait 5 seconds for more messages
        
        if sender_id in self.user_message_batches:
            message_batch = self.user_message_batches.pop(sender_id, [])
            if message_batch:
                await self._process_batch(conversation_id, sender_id, message_batch)
        
        self.batch_timers.pop(sender_id, None)

    async def _process_batch(self, conversation_id: str, sender_id: str, messages: List[str]):
        """Combines batched messages and sends them to the chat API."""
        full_message = "\n".join(messages)
        logger.info(f"Processing batch of {len(messages)} messages for user {sender_id}: '{full_message[:100]}...'")
        
        # --- LOGGING TO DMLog TABLE ---
        try:
            async with self.db_session_factory() as session:
                user = await self.user_service.get_user_by_twitter_id(sender_id, session=session)
                if user:
                    new_log = DMLog(
                        user_id=user.id,
                        content=full_message,
                        conversation_id=conversation_id,
                        message_type="user" 
                    )
                    session.add(new_log)
                    await session.commit()
                    logger.info(f"Saved user message for user {user.id} to DMLog.")
                else:
                    logger.warning(f"Could not log DM for twitter_user_id {sender_id}: User not found.")
        except Exception as e:
            logger.error(f"Failed to save message to DMLog for user {sender_id}: {e}", exc_info=True)
        # --- END LOGGING ---

        try:
            # The /chat_twitter endpoint is designed for this purpose (no animations)
            api_url = f"{os.getenv('API_BASE_URL', 'http://127.0.0.1:5000')}/chat_twitter"
            
            response = await self.http_client.post(api_url, json={
                "twitter_user_id": sender_id,
                "message": full_message
            })
            response.raise_for_status()
            
            api_data = response.json()
            ai_response = api_data.get("response", [{}])[0].get("content")

            if ai_response:
                await self.twitter_client.send_dm(conversation_id, ai_response)
            else:
                logger.error(f"Received empty AI response from API for user {sender_id}")

        except httpx.RequestError as e:
            logger.error(f"Could not connect to chat API at {e.request.url}: {e}")
        except Exception as e:
            logger.error(f"Failed to process message batch for user {sender_id}: {e}", exc_info=True)

    async def close(self):
        """Gracefully closes open connections."""
        await self.http_client.aclose()
        await self.twitter_client.close()

async def main():
    """Main function to configure logging and start the DM listener service."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/dm_monitor.log', encoding='utf-8')
        ]
    )
    
    service = DMListenerService(poll_interval=15)
    
    try:
        await service.start_monitoring()
    except KeyboardInterrupt:
        logger.info("DM Listener stopped by user.")
    finally:
        await service.close()
        logger.info("DM Listener shut down gracefully.")


if __name__ == "__main__":
    asyncio.run(main()) 