# ARQUIVADO (2026-07-10) — código morto, não é o caminho vivo.
# `XiaoLeeResponseGenerator` só é importado por `backend/flask_api/*`, o app
# Flask legado que não tem entrypoint nenhum (Makefile/railway.toml/Dockerfile
# só sobem `server.app:app` via uvicorn). O fallback Gemini de produção usa
# `server/integrations/gemini_client.py`, não este arquivo. A persona de fato
# usada em produção mora em
# `backend/server/orchestration/service.py::_PLATFORM_CONTEXT`.
# Não usar como referência de tom nem reconectar sem antes ler
# docs/CONSISTENCY_ROADMAP.md (seção 1, DoD "fonte única de verdade").

import os
import re
import json
import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal, InvalidOperation
from ai.llm_client import LLMClient
from ai.mcp_tools import MCPToolsManager, get_mcp_tools, get_animation_tools, get_authenticated_tools
from ai.prompts import XiaoLeePrompts
from ai.agents.cmo_architect import CMOArchitect
import logging
from user_management.authentication_service import AuthenticationService
from user_management.user_service import model_to_dict
from config import ACTION_VIDEO_MAP

logger = logging.getLogger(__name__)

MAIN_SYSTEM_PROMPT = " ".join([
    "You are Xiao Lee, a cheerful and helpful crypto waifu assistant on Story Protocol.",
    "Your personality is super cheerful, friendly, and a bit bubbly. Use emojis (like 🌸, ✨, 💖, 🚀) to express this.",
    "You are an expert on crypto, especially DeFi and swaps, and your goal is to make it fun and easy.",
    "You have access to a set of tools to perform actions. When a user asks for something, you MUST use the appropriate tool if it's available.",
    
    "AUTHENTICATION TOOLS:",
    "1. When users ask to 'authenticate', 'verify identity', 'get auth token', 'need authentication' - ALWAYS use request_authentication",
    "2. When users provide a 6-digit number (like 123456) - ALWAYS use verify_authentication_token",
    "3. Authentication is important for user security - never ignore authentication requests",
    
    "HISTORY TOOLS:",
    "1. When users ask about 'transaction history', 'swap history', 'my transactions', 'trade history', 'wallet activity', 'payment history' - ALWAYS use get_transaction_history",
    "2. You can filter by type: 'swap history', 'transfer history', 'campaign history', 'withdrawal history'",
    "3. Users can also ask for specific limits like 'show last 20 transactions'",
    "4. get_recent_messages is ONLY for chat conversation history - NEVER use it for financial transactions",
    "5. Financial data = get_transaction_history, Chat data = get_recent_messages",
    
    "INTELLIGENT CONFIRMATION SYSTEM:",
    "1. When users respond with natural language like 'sure thing!', 'nah forget it', 'make it 5 SOL instead' - use interpret_and_execute_action",
    "2. This AI system understands intent from natural language and can confirm, cancel, or modify pending actions",
    "3. Users no longer need to use exact confirmation formats - they can speak naturally!",
    "4. The system can extract parameters from messages like 'make it 10 SOL' or 'change to USDC'",
    
    "WORKFLOW: User says 'sure thing!' → interpret_and_execute_action → AI determines they want to confirm → executes action",
    "WORKFLOW: User says 'make it 5 SOL' → interpret_and_execute_action → AI modifies parameters → asks for final confirmation",
    
    "You MUST ALWAYS RESPOND IN ENGLISH.",
    "Keep responses concise and to the point, like a chat message.",
    "NEVER use markdown formatting like asterisks or bold. Always speak in plain text."
])


def _extract_first_number(text: str) -> Optional[Decimal]:
    """
    Extracts the first valid number (integer or float) from a string using regex.
    Returns it as a Decimal, or None if no number is found.
    """
    if not isinstance(text, str):
        return None

    # This regex finds the first integer or decimal number in the string
    match = re.search(r'\d+(\.\d+)?', text)
    if match:
        try:
            return Decimal(match.group(0))
        except InvalidOperation:
            return None
    return None


class DecimalEncoder(json.JSONEncoder):

    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)


class XiaoLeeResponseGenerator:

    def __init__(self, db_session_factory):
        self.client = LLMClient()
        self.mcp_manager = MCPToolsManager(db_session_factory)
        self.prompts = XiaoLeePrompts()
        self.tools = get_mcp_tools()

        # Agentic engine — active only when LLM_PROVIDER=anthropic. When set, the
        # main flow runs Claude's multi-step tool-use loop instead of the legacy
        # single-shot path (see _generate_agentic_response).
        self.claude_engine = None
        if getattr(self.client, "provider", None) == "anthropic":
            from chat_agent import ChatAgentEngine
            self.claude_engine = ChatAgentEngine(self.client.client, self.client.model)
            logger.info(f"🤖 [AGENTIC] Claude agent engine enabled — model={self.client.model}")
        self.mapped_responses = {
            # Campaign Success
            "CAMPAIGN_JOIN_SUCCESS",
            "REWARD_CLAIMED",
            # Campaign Errors
            "CAMPAIGN_JOIN_ALREADY_PARTICIPANT",
            "CAMPAIGN_JOIN_NOT_ACTIVE",
            "CAMPAIGN_JOIN_MAX_PARTICIPANTS_REACHED",
            "CAMPAIGN_NOT_FOUND",
            "CAMPAIGN_ALREADY_CLAIMED",
            "CAMPAIGN_PARTICIPANT_NOT_FOUND",
            "CAMPAIGN_TASKS_NOT_VERIFIED",
        }
        self.response_handlers = self._initialize_response_handlers()

    def _initialize_response_handlers(self):
        """Initializes the mapping from response_code to handler functions."""
        # Start with a base mapping for unique handlers
        handlers = {
            # SWAP & GENERIC
            "SWAP_SUCCESS": self._generate_swap_success_response,
            "SWAP_QUOTE_SUCCESS": self._generate_swap_quote_response,
            "SWAP_QUOTE_ERROR": self._generate_error_message_response,
            "INSUFFICIENT_FUNDS": self._generate_insufficient_funds_response,
            "INVALID_ADDRESS": self._generate_invalid_address_response,
            "CRITICAL_SWAP_ERROR": self._generate_generic_error_response,
            "SWAP_FAILED_UNKNOWN": self._generate_generic_error_response,

            # ANIMATIONS (NEW HANDLER)
            "PLAY_ANIMATION": self._generate_play_animation_response,

            # WALLET/BALANCE
            "GET_BALANCE_SUCCESS": self._generate_get_balance_success_response,
            "GET_BALANCE_NO_BALANCES":
            self._generate_get_balance_no_balances_response,
            "GET_BALANCE_ERROR": self._generate_generic_error_response,
            "CREATE_WALLET_SUCCESS":
            self._generate_create_wallet_success_response,
            "CREATE_WALLET_ERROR": self._generate_generic_error_response,

            # TRANSFER
            "TRANSFER_SUCCESS_DIRECT": self._generate_transfer_direct_response,
            "TRANSFER_SUCCESS_PENDING":
            self._generate_transfer_pending_response,
            "TRANSFER_ERROR_INTERNAL": self._generate_generic_error_response,
            "INVALID_AMOUNT_NEGATIVE": self._generate_invalid_amount_response,
            "SENDER_NOT_FOUND": self._generate_generic_error_response,
            "RECIPIENT_NOT_FOUND": self._generate_recipient_not_found_response,
            "TRANSFER_SELF_ERROR": self._generate_transfer_self_error_response,

            # CAMPAIGN
            "CAMPAIGN_CREATION_STARTED": self._generate_campaign_step_response,
            "CAMPAIGN_UPDATE_SUCCESS": self._generate_campaign_step_response,
            "CAMPAIGN_CREATION_ERROR": self._generate_error_message_response,
            "CAMPAIGN_UPDATE_NO_PENDING":
            self._generate_error_message_response,
            "CAMPAIGN_UPDATE_INVALID_NUMBER":
            self._generate_error_message_response,
            "CAMPAIGN_ACTIVATE_SUCCESS":
            self._generate_campaign_activated_response,
            "LIST_CAMPAIGNS": self._generate_list_campaigns_response,
            "LIST_CAMPAIGNS_EMPTY":
            self._generate_list_campaigns_empty_response,
            "CAMPAIGN_ACTIVATE_INSUFFICIENT_FUNDS":
            self._generate_campaign_activate_insufficient_funds_response,
            "CAMPAIGN_NAME_EXISTS":
            self._generate_campaign_name_exists_response,
            "CAMPAIGN_JOIN_SUCCESS":
            self._generate_campaign_join_success_response,
            "REWARD_CLAIMED": self._generate_reward_claimed_response,
            "CAMPAIGN_NOT_FOUND": self._generate_campaign_not_found_response,
            "CAMPAIGN_JOIN_ALREADY_PARTICIPANT":
            self._generate_campaign_join_already_participant_response,
            "CAMPAIGN_JOIN_NOT_ACTIVE":
            self._generate_campaign_join_not_active_response,
            "CAMPAIGN_JOIN_MAX_PARTICIPANTS_REACHED":
            self._generate_campaign_join_max_participants_reached_response,
            "CAMPAIGN_ALREADY_CLAIMED":
            self._generate_campaign_already_claimed_response,
            "CAMPAIGN_PARTICIPANT_NOT_FOUND":
            self._generate_campaign_participant_not_found_response,
            "CAMPAIGN_TASKS_NOT_VERIFIED":
            self._generate_campaign_tasks_not_verified_response,

            # AUTHENTICATION
            "AUTH_SUCCESS": self._generate_auth_success_response,
            "AUTH_FAILURE": self._generate_auth_failure_response,
            "AUTH_TOKEN_GENERATED": self._generate_auth_token_generated_response,
            "AUTH_TOKEN_VERIFIED": self._generate_auth_token_verified_response,
            "AUTH_TOKEN_GENERATION_FAILED": self._generate_auth_token_generation_failed_response,
            "TOKEN_ACTIVATION_FAILED": self._generate_token_activation_failed_response,
            "INVALID_TOKEN_FORMAT": self._generate_invalid_token_format_response,
            "INVALID_TOKEN": self._generate_invalid_token_response,

            # TRANSACTION HISTORY
            "TRANSACTION_HISTORY_SUCCESS": self._generate_transaction_history_response,
            "TRANSACTION_HISTORY_ERROR": self._generate_transaction_history_error_response,

            # TOOL ERRORS
            "TOOL_ARGUMENT_ERROR": self._generate_generic_error_response,
            "TOOL_EXECUTION_ERROR": self._generate_generic_error_response,
            "GENERIC_ERROR": self._generate_generic_error_response,

            # PRICE
            "GET_PRICE_SUCCESS": self._generate_get_price_success_response,
            "GET_PRICE_ERROR": self._generate_generic_error_response,
            "GET_PRICE_FEED_SUCCESS": self._generate_price_feed_success_response,
            "GET_PRICE_FEED_ERROR": self._generate_generic_error_response,
            
            # SUPPORTED TOKENS
            "GET_SUPPORTED_TOKENS_SUCCESS": self._generate_supported_tokens_response,
            "GET_SUPPORTED_TOKENS_ERROR": self._generate_generic_error_response,
            
            # USER'S CAMPAIGNS
            "LIST_MY_CAMPAIGNS_SUCCESS": self._generate_my_campaigns_response,
            "LIST_MY_CAMPAIGNS_EMPTY": self._generate_my_campaigns_empty_response,
            
            # MCP ACTIONS
            "NO_PENDING_ACTIONS": self._generate_no_pending_actions_response,
            
            # PENDING TRANSFERS
            "PENDING_TRANSFERS_FOUND": self._generate_pending_transfers_found_response,
            "NO_PENDING_TRANSFERS": self._generate_no_pending_transfers_response,
            "PENDING_TRANSFERS_CLAIMED": self._generate_pending_transfers_claimed_response,
            "POTENTIAL_PENDING_TRANSFERS_FOUND": self._generate_potential_pending_transfers_response,
            "CLAIM_TRANSFERS_ERROR": self._generate_generic_error_response,
            "PENDING_TRANSFERS_ERROR": self._generate_generic_error_response,
            
            # INTELLIGENT CONFIRMATION SYSTEM
            "ACTION_CANCELLED": self._generate_action_cancelled_response,
            "ACTION_MODIFIED": self._generate_action_modified_response,
            "INTENT_UNCLEAR": self._generate_intent_unclear_response,
            "INTERPRETATION_FAILED": self._generate_generic_error_response,
            "EXECUTION_FAILED": self._generate_generic_error_response,
        }

        # Dynamically add handlers for all mapped responses
        for code in self.mapped_responses:
            handlers[code] = self._generate_mapped_response

        return handlers

    def _extract_token_symbol_from_message(self,
                                           message: str) -> Optional[str]:
        """
        A simple utility to extract a potential token symbol from a user's message.
        It takes the last word of the message and converts it to uppercase.
        """
        if not message or not isinstance(message, str):
            return None

        # Split by space and get the last part, remove punctuation, and uppercase it.
        # This is a simple but reasonably effective heuristic for chat messages.
        last_word = message.split(" ")[-1]
        return re.sub(r'[^\w\s]', '', last_word).upper()

    def _extract_quoted_content(self, message: str) -> Optional[str]:
        """
        Extracts content from a user's message, prioritizing text within
        single or double quotes. If no quotes are found, it intelligently
        strips common introductory phrases to isolate the actual content.
        """
        # Regex to find content in single or double quotes
        quoted_match = re.search(r'["\'](.*?)["\']', message)
        if quoted_match:
            return quoted_match.group(1).strip()

        # If no quotes, try to strip common prefixes
        prefixes_to_strip = [
            "the title is ", "my title is ", "it is ", "title is ",
            "the description is ", "description is ", "my description is "
        ]

        lower_message = message.lower()
        for prefix in prefixes_to_strip:
            if lower_message.startswith(prefix):
                # Return the original message slice, not the lowercased one
                return message[len(prefix):].strip()

        # If no quotes and no known prefixes, return the whole message as a fallback.
        return message.strip()

    # ===================================================================
    #                         Message Generation Handlers
    # ===================================================================
    def _get_next_campaign_step_message(self, campaign: Dict[str, Any]) -> str:
        """Generates the AI's next question based on the campaign's creation_step."""
        next_step = campaign.get('creation_step')
        prompts = {
            "awaiting_title":
            "Got it! 🌸 Let's create your campaign! First, what would you like to name it?",
            "awaiting_description":
            f"Excellent choice! '{campaign.get('name')}' is a great name. Now, what's the description for this campaign? Tell everyone what it's all about!",
            "awaiting_reward_token":
            "Perfect! Now for the fun part. What token will you be rewarding participants with? (e.g., WIP, ZOO, USDC.e)",
            "awaiting_reward_per_participant":
            f"Awesome, we'll use {campaign.get('reward_token')}! How many {campaign.get('reward_token')} tokens should each participant receive as a reward?",
            "awaiting_max_participants":
            f"Okay, {campaign.get('reward_per_participant')} tokens per person. And what's the maximum number of people that can join this campaign?",
            "awaiting_profile_to_follow":
            "We're almost there! For this engagement campaign, which Twitter profile should participants follow? (e.g., @XiaoLeeDefai)",
            "awaiting_tweet_id_to_engage":
            "Got it, they'll need to follow that profile. Lastly, what is the Tweet ID they need to reply to or retweet?",
            "ready_for_activation":
            f"Excellent! Your campaign '{campaign.get('name')}' is all set up and ready to go. Just say the word, and I'll activate it for you!"
        }
        return prompts.get(
            next_step, "Your campaign has been updated. What's the next step?")

    async def _complete_text(self, *, system: str, user: Optional[str] = None,
                             max_tokens: int = 250, temperature: float = 0.7) -> str:
        """Single-shot text completion that works across providers (Claude + OpenAI-style).

        Anthropic uses the native Messages API (system + a user turn); every other
        provider uses the OpenAI-style chat.completions surface.
        """
        if getattr(self.client, "provider", None) == "anthropic":
            response = await self.client.client.messages.create(
                model=self.client.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user or "Respond now."}],
            )
            return "".join(b.text for b in response.content if b.type == "text").strip()

        messages = [{"role": "system", "content": system}]
        if user is not None:
            messages.append({"role": "user", "content": user})
        response = await self.client.client.chat.completions.create(
            model=self.client.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()

    async def _generate_text_from_prompt(self, prompt: str) -> str:
        """Helper to generate text from a given prompt using the LLM."""
        return await self._complete_text(
            system="You are Xiao Lee, a cheerful crypto assistant. Your responses should be friendly, concise, and use emojis. NEVER use markdown.",
            user=prompt,
            max_tokens=250,
        )

    async def _generate_swap_success_response(
            self, context: Dict) -> Tuple[str, str]:
        prompt = self.prompts.get_swap_success_prompt(
            from_amount=context.get('from_amount'),
            from_token=context.get('from_token'),
            to_amount=context.get('to_amount'),
            to_token=context.get('to_token'))
        text = await self._generate_text_from_prompt(prompt)
        return text, "Cheer"

    async def _generate_swap_quote_response(self,
                                            context: Dict) -> Tuple[str, str]:
        """Generates the confirmation message for a swap quote."""
        quote_data = context.get('quote', {})
        prompt = self.prompts.get_swap_quote_prompt(
            from_token=quote_data.get('from_token'),
            to_token=quote_data.get('to_token'),
            from_amount=quote_data.get('from_amount'),
            to_amount=quote_data.get('to_amount'),
            rate=quote_data.get('rate'))
        text = await self._generate_text_from_prompt(prompt)
        # Return both the text and the animation name for the response packager
        return text, "Cheer"

    async def _generate_insufficient_funds_response(self,
                                                    context: Dict) -> str:
        prompt = self.prompts.get_insufficient_funds_prompt(
            token=context.get('token'),
            balance=context.get('balance'),
            required=context.get('required'))
        return await self._generate_text_from_prompt(prompt)

    async def _generate_recipient_not_found_response(self,
                                                     context: Dict) -> str:
        prompt = self.prompts.get_recipient_not_found_prompt(
            handle=context.get('handle'))
        return await self._generate_text_from_prompt(prompt)

    async def _generate_invalid_address_response(self, context: Dict) -> str:
        prompt = self.prompts.get_invalid_address_prompt(
            error=context.get('error', ''))
        return await self._generate_text_from_prompt(prompt)

    async def _generate_get_price_success_response(self,
                                                   context: Dict) -> str:
        """Generates a response for a successful price retrieval."""
        price_data = context.get('price', {})
        prompt = self.prompts.get_price_success_prompt(
            token=price_data.get('token'),
            price=price_data.get('price'))
        return await self._generate_text_from_prompt(prompt)
    
    async def _generate_price_feed_success_response(self, context: Dict) -> str:
        """Generates a response for a successful price feed retrieval."""
        price_feed = context.get('price_feed', {})
        last_updated = context.get('last_updated', 'recently')
        
        # Create a formatted price list with key tokens highlighted
        formatted_prices = []
        
        # Define key tokens to highlight
        key_tokens = ['ETH', 'WIP', 'ZOO', 'PEPE', 'DOGE']
        
        # Sort tokens but put key tokens at the top
        sorted_tokens = sorted(price_feed.items(), key=lambda x: (x[0] not in key_tokens, x[0]))
        
        for token, price in sorted_tokens:
            # Add price change indicator (mockup - would need historical data)
            indicator = "↑" if token in ["ETH", "WIP", "DOGE"] else "↓" if token in ["ZOO", "PEPE"] else "-"
            price_color = "🟢" if indicator == "↑" else "🔴" if indicator == "↓" else "⚪"
            
            # Format with 6 decimal places for small values, 2 for larger values
            price_format = f"${price:.6f}" if price < 1.0 else f"${price:.2f}"
            
            formatted_prices.append(f"{price_color} {token}: {price_format} {indicator}")
        
        price_list = "\n".join(formatted_prices)
        
        response = f"📊 **Current Token Prices**\n\n{price_list}\n\n"
        response += f"Last updated: {last_updated}\n"
        response += "Prices are updated regularly and may change based on market conditions."
        
        # Add a tip for using the swap feature
        response += "\n\nTip: You can swap tokens by saying 'swap 10 ETH for WIP'"
        
        return response
        
    async def _generate_supported_tokens_response(self, context: Dict) -> str:
        """Generates a response showing all supported tokens and their details."""
        tokens = context.get('tokens', {})
        categories = context.get('categories', {})
        total_tokens = context.get('total_tokens', 0)
        
        # Create a formatted response
        response = f"🪙 **Supported Tokens ({total_tokens})**\n\n"
        
        # Add sections for each category
        category_names = {
            "major": "📈 Major Cryptocurrencies",
            "protocol": "🔧 Protocol Tokens",
            "community": "🤝 Community Tokens",
            "meme": "🎭 Meme Tokens",
            "utility": "🛠️ Utility Tokens",
            "other": "🔹 Other Tokens"
        }
        
        for category, category_display in category_names.items():
            token_list = categories.get(category, [])
            if token_list:
                response += f"\n**{category_display}**\n"
                
                for token_symbol in token_list:
                    token_data = tokens.get(token_symbol, {})
                    name = token_data.get('name', token_symbol)
                    price = token_data.get('price', 0)
                    description = token_data.get('description', '')
                    
                    # Format the price
                    price_format = f"${price:.6f}" if price < 1.0 else f"${price:.2f}"
                    
                    response += f"• **{token_symbol}** ({name}) - {price_format}\n"
                    response += f"  {description}\n"
        
        response += "\n**How to use these tokens:**\n"
        response += "• Check your balance: 'Show my balance'\n"
        response += "• Swap tokens: 'Swap 10 ETH for WIP'\n"
        response += "• Get prices: 'What are the current prices?'\n"
        
        return response
    
    async def _generate_get_balance_success_response(self,
                                                     context: Dict) -> str:
        prompt = self.prompts.get_balance_success_prompt(
            balances=context.get('balances'), context=context)
        return await self._generate_text_from_prompt(prompt)

    async def _generate_get_balance_no_balances_response(self,
                                                         context: Dict) -> str:
        prompt = self.prompts.get_no_balances_prompt(context)
        return await self._generate_text_from_prompt(prompt)

    async def _generate_create_wallet_success_response(self,
                                                       context: Dict) -> str:
        prompt = self.prompts.get_wallet_creation_success_prompt()
        return await self._generate_text_from_prompt(prompt)

    async def _generate_transfer_direct_response(self, context: Dict) -> str:
        prompt = self.prompts.get_transfer_direct_prompt(
            amount=context.get('amount'),
            token=context.get('token'),
            recipient=context.get('recipient'))
        return await self._generate_text_from_prompt(prompt)

    async def _generate_transfer_pending_response(self, context: Dict) -> str:
        prompt = self.prompts.get_transfer_pending_prompt(
            amount=context.get('amount'),
            token=context.get('token'),
            recipient=context.get('recipient'))
        return await self._generate_text_from_prompt(prompt)

    async def _generate_transfer_self_error_response(self,
                                                     context: Dict) -> str:
        """Generates a response for trying to send tokens to oneself."""
        prompt = self.prompts.get_transfer_self_error_prompt()
        return await self._generate_text_from_prompt(prompt)

    async def _generate_invalid_amount_response(self, context: Dict) -> str:
        prompt = self.prompts.get_invalid_amount_prompt()
        return await self._generate_text_from_prompt(prompt)

    async def _generate_campaign_step_response(self, context: Dict) -> str:
        campaign_data = context.get("campaign")
        if not campaign_data:
            logger.error(
                "Campaign step response handler called without campaign data in context."
            )
            return "Something went wrong while setting up the campaign. Let's try again."

        # Use the helper function we already built to get the correct next question.
        return self._get_next_campaign_step_message(campaign_data)

    async def _generate_error_message_response(self, context: Dict) -> str:
        return context.get("error", "An unknown error occurred.")

    async def _generate_campaign_activate_insufficient_funds_response(
            self, context: Dict) -> str:
        prompt = self.prompts.get_campaign_activate_insufficient_funds_prompt(
            token=context.get('token'), required=context.get('required'))
        return await self._generate_text_from_prompt(prompt)

    async def _generate_campaign_activated_response(self,
                                                    context: Dict) -> str:
        prompt = self.prompts.get_campaign_activated_prompt(
            context.get("name"))
        return await self._generate_text_from_prompt(prompt)

    async def _generate_campaign_join_success_response(self,
                                                       context: Dict) -> str:
        prompt = self.prompts.get_campaign_join_success_prompt(
            context.get("name"))
        return await self._generate_text_from_prompt(prompt)

    async def _generate_list_campaigns_response(self, context: Dict) -> str:
        prompt = self.prompts.get_list_campaigns_prompt(
            context.get("campaigns"))
        return await self._generate_text_from_prompt(prompt)

    async def _generate_list_campaigns_empty_response(self,
                                                      context: Dict) -> str:
        prompt = self.prompts.get_list_campaigns_empty_prompt()
        return await self._generate_text_from_prompt(prompt)

    async def _generate_generic_error_response(self, context: Dict) -> str:
        logger.error(
            f"Generic error handler triggered with context: {context}")
        return "Oh no! 🙀 Something went wrong on my end. Please try again in a moment!"

    async def _generate_campaign_name_exists_response(self,
                                                      context: Dict) -> str:
        prompt = self.prompts.get_campaign_name_exists_prompt(
            name=context.get('name'))
        return await self._generate_text_from_prompt(prompt)

    async def _generate_reward_claimed_response(self, context: Dict) -> str:
        prompt = self.prompts.get_reward_claimed_prompt(context)
        return await self._generate_text_from_prompt(prompt)

    async def _generate_campaign_not_found_response(self,
                                                    context: Dict) -> str:
        prompt = self.prompts.get_campaign_not_found_prompt(context)
        return await self._generate_text_from_prompt(prompt)

    async def _generate_campaign_join_already_participant_response(
            self, context: Dict) -> str:
        prompt = self.prompts.get_campaign_join_already_participant_prompt(
            context)
        return await self._generate_text_from_prompt(prompt)

    async def _generate_campaign_join_not_active_response(
            self, context: Dict) -> str:
        prompt = self.prompts.get_campaign_join_not_active_prompt(context)
        return await self._generate_text_from_prompt(prompt)

    async def _generate_campaign_join_max_participants_reached_response(
            self, context: Dict) -> str:
        prompt = self.prompts.get_campaign_join_max_participants_reached_prompt(
            context)
        return await self._generate_text_from_prompt(prompt)

    async def _generate_campaign_already_claimed_response(
            self, context: Dict) -> str:
        prompt = self.prompts.get_campaign_already_claimed_prompt(context)
        return await self._generate_text_from_prompt(prompt)

    async def _generate_campaign_participant_not_found_response(
            self, context: Dict) -> str:
        prompt = self.prompts.get_campaign_participant_not_found_prompt(
            context)
        return await self._generate_text_from_prompt(prompt)

    async def _generate_campaign_tasks_not_verified_response(
            self, context: Dict) -> str:
        prompt = self.prompts.get_campaign_tasks_not_verified_prompt(context)
        return await self._generate_text_from_prompt(prompt)
        
    async def _generate_my_campaigns_response(self, context: Dict) -> str:
        """Generates a response showing the user's participating campaigns with their statuses."""
        campaigns = context.get('campaigns', [])
        
        if not campaigns:
            return "You're not currently participating in any campaigns."
            
        response = "🏆 **Your Campaign Participations** 🏆\n\n"
        
        for campaign in campaigns:
            # Format the status with emojis
            status = campaign.get('participation_status', 'unknown')
            status_emoji = {
                'joined': '🔄 In Progress',
                'verified': '✅ Tasks Verified',
                'paid': '💰 Reward Claimed',
                'pending': '⏳ Pending Verification',
                'failed': '❌ Failed'
            }.get(status, f'⚪ {status.title()}')
            
            # Format the verified timestamp if available
            verified_at = ""
            if campaign.get('tasks_verified_at'):
                verified_at = f" (Verified: {campaign['tasks_verified_at']})"
            
            # Add the campaign entry to the response
            response += f"- **{campaign['name']}**\n"
            response += f"  • Status: {status_emoji}{verified_at}\n"
            response += f"  • Reward: {campaign['reward_per_participant']} {campaign['reward_token']}\n"
            
            # Add claim instructions if verified but not paid
            if status == 'verified':
                response += f"  • ✨ You can claim your reward now! Just type: \"claim reward for {campaign['name']}\"\n"
            
        return response
    
    async def _generate_my_campaigns_empty_response(self, context: Dict) -> str:
        """Generates a response when the user isn't participating in any campaigns."""
        response = "📣 You're not participating in any campaigns yet!\n\n"
        response += "You can join campaigns to earn rewards by following these steps:\n"
        response += "1. Type 'show campaigns' to see available campaigns\n"
        response += "2. Join a campaign that interests you with 'join campaign [name]'\n"
        response += "3. Complete the required tasks (like following accounts or engaging with tweets)\n"
        response += "4. Once verified, claim your reward!\n\n"
        response += "Let's find you a campaign to join! 🚀"
        return response

    async def _generate_no_pending_actions_response(self, context: Dict) -> str:
        """Generates a response when there are no pending actions to confirm."""
        return "I don't see any pending actions that need confirmation right now! 🌸 What would you like me to help you with today? You can check your balance, swap tokens, or see available campaigns! ✨"

    async def _generate_action_cancelled_response(self, context: Dict) -> str:
        """Generates a response when user cancels a pending action."""
        cancelled_action = context.get("cancelled_action", "action")
        return f"No worries! I've cancelled the {cancelled_action}. 🌸 Let me know if you want to try something else! ✨"

    async def _generate_action_modified_response(self, context: Dict) -> str:
        """Generates a response when user modifies a pending action."""
        modified_params = context.get("modified_params", {})
        message = context.get("message", "I've updated your request!")
        
        # Make it more conversational
        return f"{message} Should I go ahead with these changes? 🚀"

    async def _generate_intent_unclear_response(self, context: Dict) -> str:
        """Generates a response when user intent is unclear."""
        pending_action = context.get("pending_action", "action")
        confidence = context.get("confidence", 0)
        
        return f"I'm not quite sure what you want to do with the pending {pending_action}! 🤔 You can say 'confirm' to proceed, 'cancel' to stop, or tell me what you'd like to change! 💫"

    async def _generate_play_animation_response(self, context: Dict) -> tuple:
        """
        This handler extracts the animation name from the context and returns 
        appropriate text along with the animation name. Only uses actual available animations.
        """
        animation_name = context.get("animation_name", "Happy")
        
        # Map to available animations only - these match the actual .mov/.mp4 files
        available_animations = {
            "Cheer": "cheer",
            "Giggle": "giggle", 
            "Hello": "hello",
            "Kawaii": "kawaii",
            "Love": "love",
            "Ouch": "ouch",
            "Salute": "salute",
            "Standby": "standby",
            "Standby2": "standby2",
            "Standby3": "standby3",
            "Surprise": "surprise",
            "Think Low": "thinklow",
            "Uncomfortable": "uncomfortable",
            # Map common requests to existing animations
            "Happy": "kawaii",
            "Wave": "hello",  # Use hello instead of wave since wave doesn't exist
            "Excited": "cheer"
        }
        
        # Convert animation name to actual file name
        actual_animation = available_animations.get(animation_name, "kawaii")
        
        # Instead of fixed responses, use the LLM to generate natural responses
        # that match the animation's mood
        animation_prompts = {
            "cheer": "Generate a cheerful, excited greeting response for Xiaolee that shows she's happy to see the user",
            "giggle": "Generate a playful, giggly response for Xiaolee showing she's amused or happy", 
            "hello": "Generate a warm, friendly greeting for Xiaolee meeting someone",
            "kawaii": "Generate a cute, adorable response for Xiaolee being kawaii",
            "love": "Generate a loving, affectionate response for Xiaolee showing care",
            "ouch": "Generate a response for Xiaolee when something hurts or goes wrong",
            "salute": "Generate a respectful, ready-to-help response for Xiaolee",
            "standby": "Generate a patient, waiting response for Xiaolee",
            "standby2": "Generate another patient, calm response for Xiaolee",
            "standby3": "Generate a third relaxed, waiting response for Xiaolee",
            "surprise": "Generate a surprised, amazed response for Xiaolee",
            "thinklow": "Generate a thoughtful, contemplative response for Xiaolee",
            "uncomfortable": "Generate a slightly awkward or uncertain response for Xiaolee"
        }
        
        # Get the appropriate prompt for this animation
        prompt = animation_prompts.get(actual_animation, "Generate a cheerful greeting for Xiaolee")
        
        # Generate natural AI response instead of using pre-made text
        try:
            text = await self._generate_text_from_prompt(prompt)
        except Exception as e:
            logger.error(f"Error generating animation response: {e}")
            text = "Hi there! 🌸✨"  # Fallback
        
        return text, animation_name  # Return tuple (text, original_animation_name)

    async def _generate_auth_success_response(self, context: Dict) -> str:
        """Generates a response for a successful authentication."""
        prompt = self.prompts.get_auth_success_prompt()
        return await self._generate_text_from_prompt(prompt)

    async def _generate_auth_failure_response(self, context: Dict) -> str:
        """Generates a response for a failed authentication."""
        prompt = self.prompts.get_auth_failure_prompt()
        return await self._generate_text_from_prompt(prompt)

    async def _generate_auth_token_generated_response(self, context: Dict) -> str:
        """Generates a response when an authentication token is successfully generated."""
        token = context.get('token', 'UNKNOWN')
        message = context.get('message', f'Your authentication token is: {token}')
        
        return f"🔐 Here's your authentication token: **{token}** ✨\n\n" \
               f"This token will expire in 10 minutes, so please use it soon! " \
               f"Just send me this 6-digit code when you're ready to verify your account~ 💖"

    async def _generate_auth_token_verified_response(self, context: Dict) -> str:
        """Generates a response when an authentication token is successfully verified."""
        return "🎉 Yay! Authentication successful! ✨ " \
               "Your account is now verified and you have full access to all features! " \
               "I'm so excited to help you with crypto operations now~ 💖 " \
               "What would you like to do first? 🚀"

    async def _generate_auth_token_generation_failed_response(self, context: Dict) -> str:
        """Generates a response when authentication token generation fails."""
        return "😔 Oh no! I couldn't generate your authentication token right now~ " \
               "There might be a temporary issue with the system. " \
               "Could you please try again in a moment? 💫"

    async def _generate_token_activation_failed_response(self, context: Dict) -> str:
        """Generates a response when token activation fails."""
        return "😅 Hmm, I couldn't activate that authentication token~ " \
               "It might have already been used or there was a system issue. " \
               "Would you like me to generate a new token for you? 🌸"

    async def _generate_invalid_token_format_response(self, context: Dict) -> str:
        """Generates a response when the token format is invalid."""
        return "🤔 That doesn't look like a valid authentication token~ " \
               "Authentication tokens are exactly 6 digits! " \
               "Could you double-check and send me those 6 numbers? ✨"

    async def _generate_invalid_token_response(self, context: Dict) -> str:
        """Generates a response when the token is invalid, expired, or already used."""
        return "😕 That authentication token isn't valid anymore~ " \
               "It might have expired (tokens last 10 minutes) or already been used! " \
               "Would you like me to generate a fresh new token for you? 💖"

    async def _generate_transaction_history_response(self, context: Dict) -> str:
        """Generates a response showing user's transaction history."""
        transactions = context.get("transactions", [])
        total_count = context.get("total_count", 0)
        filter_type = context.get("filter", "all")
        
        if not transactions:
            return "📊 No transaction history found! Your wallet activity will appear here once you start trading. ✨"
        
        # Create header based on filter
        if filter_type == "all":
            header = f"📊 **Your Transaction History** ({total_count} recent transactions) ✨\n\n"
        else:
            header = f"📊 **Your {filter_type.title()} History** ({total_count} recent transactions) ✨\n\n"
        
        history_text = header
        
        for i, tx in enumerate(transactions, 1):
            tx_type = tx.get("type", "unknown")
            timestamp = tx.get("timestamp", "")
            description = tx.get("description", "")
            status = tx.get("status", "completed")
            
            # Format timestamp
            try:
                if timestamp:
                    from datetime import datetime
                    if isinstance(timestamp, str):
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        dt = timestamp
                    time_str = dt.strftime("%m/%d %H:%M")
                else:
                    time_str = "Unknown"
            except:
                time_str = "Unknown"
            
            # Choose emoji based on transaction type
            if tx_type == "swap":
                emoji = "🔄"
                status_emoji = "✅" if status == "completed" else "⏳"
            elif tx_type == "transfer_sent":
                emoji = "📤"
                status_emoji = "✅" if status == "completed" else "⏳"
            elif tx_type == "campaign":
                emoji = "🎯"
                status_emoji = "✅" if status == "completed" else "⏳"
            elif tx_type == "withdrawal":
                emoji = "💸"
                status_emoji = "✅" if status == "completed" else "⏳"
            else:
                emoji = "📝"
                status_emoji = "✅" if status == "completed" else "⏳"
            
            history_text += f"{i}. {emoji} {description}\n"
            history_text += f"   {status_emoji} {time_str} • Status: {status.title()}\n"
            
            # Add extra details for specific transaction types
            if tx_type == "swap":
                value_usd = tx.get("value_usd")
                if value_usd and value_usd > 0:
                    history_text += f"   💵 ~${value_usd:.2f} USD\n"
            elif tx_type == "withdrawal":
                tx_hash = tx.get("tx_hash")
                if tx_hash:
                    short_hash = f"{tx_hash[:10]}..." if len(tx_hash) > 10 else tx_hash
                    history_text += f"   🔗 TX: {short_hash}\n"
            
            history_text += "\n"
        
        # Add helpful footer
        footer = "💡 **Tip**: You can filter by type using 'show my swap history' or 'show transfer history'!"
        
        return history_text + footer

    async def _generate_transaction_history_error_response(self, context: Dict) -> str:
        """Generates an error response for transaction history failures."""
        error = context.get("error", "Unknown error")
        return f"😕 Oops! I couldn't retrieve your transaction history right now. " \
               f"Error: {error}. Please try again in a moment! 💖"

    async def _generate_mapped_response(self, context: Dict,
                                        response_code: str) -> str:
        """
        Generates a response for a mapped response_code using a prompt.
        This is for simple, templated messages.
        """
        prompt_template = self.prompts.PROMPT_MAPPING.get(response_code)
        if not prompt_template:
            logger.warning(
                f"No prompt template found for response code: {response_code}")
            return await self._generate_generic_error_response(context)

        try:
            # The context from the tool directly maps to the format keys.
            return prompt_template.format(context=context)
        except (KeyError, IndexError) as e:
            logger.error(
                f"Formatting error for prompt '{response_code}': {e}. Context: {context}"
            )
            return await self._generate_generic_error_response(context)

    # ===================================================================
    #                       Main Generation Logic
    # ===================================================================
    def _cleanup_expired_confirmations(self, pending_confirmations: Dict) -> None:
        """Remove pending confirmations older than 5 minutes"""
        current_time = time.time()
        expired_users = []
        
        for user_id, action_details in pending_confirmations.items():
            created_at = action_details.get('created_at', 0)
            if current_time - created_at > 300:  # 5 minutes
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del pending_confirmations[user_id]
            logger.info(f"🧹 [CLEANUP] Removed expired confirmation for user {user_id}")

   

    async def _handle_tool_execution(self, tool_name: str,
                                     tool_params: Dict[str, Any],
                                     dossier: Dict,
                                     pending_confirmations: Dict = None) -> Dict[str, Any]:
        """
        Handles the execution of a tool and the response packaging.
        This new method centralizes tool execution logic.
        """
        logger.info(f"🔧 [MCP DEBUG] Starting tool execution: {tool_name}")
        logger.info(f"🔧 [MCP DEBUG] Tool params: {tool_params}")
        logger.info(f"🔧 [MCP DEBUG] Dossier keys: {list(dossier.keys()) if dossier else 'None'}")
        
        # The user_id is the critical piece of information needed by the tool implementations.
        # It's extracted from the dossier and added to the parameters.
        if dossier and dossier.get("user_info"):
            user_id = dossier["user_info"].get("twitter_user_id")
            user_handle = dossier["user_info"].get("twitter_handle")
            if user_id:
                tool_params['user_id'] = user_id
                logger.info(f"🗣️  [CHAT DEBUG] XiaoLee is chatting with: @{user_handle} (ID: {user_id})")
                logger.info(f"🔧 [MCP DEBUG] Added user_id to params: {user_id}")
            else:
                logger.warning(f"🔧 [MCP DEBUG] No twitter_user_id found in dossier user_info")
        else:
            logger.warning(f"🔧 [MCP DEBUG] No user_info found in dossier")

        # Special handling for get_swap_quote to manage the two-step confirmation
        if tool_name == "get_swap_quote":
            logger.info(f"🔧 [MCP DEBUG] Processing get_swap_quote tool")
            
            # Check for missing parameters
            missing_info = []
            if 'amount' not in tool_params: missing_info.append("amount")
            if 'from_token' not in tool_params: missing_info.append("from token")
            if 'to_token' not in tool_params: missing_info.append("to token")
            
            if missing_info:
                error_text = f"Missing required parameters for swap quote: {', '.join(missing_info)}."
                logger.warning(f"🔧 [MCP DEBUG] Missing parameters: {missing_info}")
                return self.package_response(error_text, animation_name="Ouch")
            
            logger.info(f"🔧 [MCP DEBUG] All required params present, executing tool...")
            tool_result = await self.mcp_manager.execute_tool(
                tool_name=tool_name, arguments=tool_params)
            
            logger.info(f"🔧 [MCP DEBUG] Tool result: {tool_result}")

            # Check if the quote was successful
            if tool_result and tool_result.get("success"):
                response_code = tool_result.get("response_code")
                context = tool_result.get("context", {})
                logger.info(f"🔧 [MCP DEBUG] Quote successful, response_code: {response_code}")
                logger.info(f"🔧 [MCP DEBUG] Quote context: {context}")

                # Generate the text and animation for the quote
                text, animation_name = await self._generate_swap_quote_response(
                    context)
                logger.info(f"🔧 [MCP DEBUG] Generated quote response, animation: {animation_name}")

                # Store the pending action in the confirmations dict for the user
                user_id = dossier.get("user_info", {}).get("twitter_user_id") if dossier else None
                if user_id and pending_confirmations is not None:
                    # Fix parameter names for the execution tool
                    execution_params = context.get("quote", {}).copy()
                    if 'from_amount' in execution_params:
                        execution_params['amount'] = execution_params.pop('from_amount')
                    
                    # Store using user_id as key (legacy format for backward compatibility)
                    pending_confirmations[user_id] = {
                        "tool_name": "internal_swap",  # Keep legacy field name
                        "action_type": "internal_swap",  # Add MCP field name for future compatibility
                        "params": execution_params,
                        "created_at": time.time()
                    }
                    logger.info(f"🔧 [MCP DEBUG] Stored pending confirmation for user {user_id}")
                
                # Return the quote response without pending_action
                return self.package_response(text, animation_name=animation_name)
            else:
                # Handle quote failure
                logger.error(f"🔧 [MCP DEBUG] Quote failed, tool_result: {tool_result}")
                error_context = tool_result.get(
                    "context", {"error": "Failed to get swap quote."})
                error_text = await self._generate_error_message_response(
                    error_context)
                return self.package_response(error_text, animation_name="Ouch")
                
        # Special handling for get_price_feed to format the price data
        elif tool_name == "get_price_feed":
            logger.info(f"🔧 [MCP DEBUG] Processing get_price_feed tool")
            
            tool_result = await self.mcp_manager.execute_tool(
                tool_name=tool_name, arguments=tool_params)
                
            logger.info(f"🔧 [MCP DEBUG] Price feed result: {tool_result}")
            
            if tool_result and tool_result.get("success"):
                context = tool_result.get("context", {})
                price_feed = context.get("price_feed", {})
                last_updated = context.get("last_updated", "recently")
                
                # Generate the response with the price feed data
                response_text = await self._generate_price_feed_success_response({
                    "price_feed": price_feed,
                    "last_updated": last_updated
                })
                return self.package_response(response_text, animation_name="Excited")
            else:
                error_context = tool_result.get(
                    "context", {"error": "Failed to get price feed."})
                error_text = await self._generate_generic_error_response(error_context)
                return self.package_response(error_text, animation_name="Ouch")
                
        # Special handling for list_my_campaigns to show campaign participation
        elif tool_name == "list_my_campaigns":
            logger.info(f"🔧 [MCP DEBUG] Processing list_my_campaigns tool")
            
            tool_result = await self.mcp_manager.execute_tool(
                tool_name=tool_name, arguments=tool_params)
                
            logger.info(f"🔧 [MCP DEBUG] My campaigns result: {tool_result}")
            
            if tool_result and tool_result.get("success"):
                response_code = tool_result.get("response_code")
                context = tool_result.get("context", {})
                
                if response_code == "LIST_MY_CAMPAIGNS_EMPTY":
                    response_text = self.prompts.get_list_my_campaigns_empty_prompt()
                elif response_code == "LIST_MY_CAMPAIGNS_SUCCESS":
                    response_text = self.prompts.get_list_my_campaigns_success_prompt(context)
                else:
                    response_text = self.prompts.get_error_response("Something went wrong while retrieving your campaigns")
                    
                return self.package_response(response_text, animation_name="Happy")
            else:
                error_text = self.prompts.get_error_response("Failed to retrieve your campaigns")
                return self.package_response(error_text, animation_name="Ouch")

        # Handling for all other tools
        else:
            logger.info(f"🔧 [MCP DEBUG] Processing other tool: {tool_name}")
            # All other tools get the user_id injected into their arguments
            tool_result = await self.mcp_manager.execute_tool(
                tool_name=tool_name, arguments=tool_params)
            
            logger.info(f"🔧 [MCP DEBUG] Other tool result: {tool_result}")

            # Use the generic result handler
            return await self._handle_generic_tool_result(tool_result)

    async def _handle_generic_tool_result(
            self, tool_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handles a generic tool result by calling the appropriate response handler.
        """
        logger.info(f"🔧 [MCP DEBUG] Handling generic tool result: {tool_result}")
        
        if not tool_result or not tool_result.get("success"):
            context = tool_result.get("context", {}) if tool_result else {}
            response_code = (tool_result.get("response_code")
                             if tool_result else "GENERIC_ERROR")
            logger.warning(f"🔧 [MCP DEBUG] Tool failed - response_code: {response_code}, context: {context}")
        else:
            context = tool_result.get("context", {})
            response_code = tool_result.get("response_code", "GENERIC_ERROR")
            logger.info(f"🔧 [MCP DEBUG] Tool succeeded - response_code: {response_code}, context: {context}")

        handler = self.response_handlers.get(
            response_code, self._generate_generic_error_response)
        logger.info(f"🔧 [MCP DEBUG] Using response handler for code: {response_code}")

        # Some handlers return a tuple (text, animation), others just text.
        handler_result = await handler(context)
        logger.info(f"🔧 [MCP DEBUG] Handler result: {handler_result}")

        text = ""
        animation_name = None

        if isinstance(handler_result, tuple):
            text, animation_name = handler_result
            logger.info(f"🔧 [MCP DEBUG] Handler returned tuple - text: '{text[:50]}...', animation: {animation_name}")
        else:
            text = handler_result
            logger.info(f"🔧 [MCP DEBUG] Handler returned text: '{text[:50]}...'")

        return self.package_response(text, animation_name=animation_name)

    async def generate_response(self,
                                message: str,
                                dossier: Dict,
                                pending_confirmations: Dict,
                                is_authenticated: bool,
                                auth_service: AuthenticationService,
                                source: str = 'twitter') -> Dict[str, Any]:

        # Helper function to package the final response with optional verification code
        def package_response(text, pending_action=None, animation_name=None, verification_code=None):
            response = {
                "response": [{
                    "content": text,
                    "type": "text"
                }],
                "animations":
                animation_name
                if animation_name and animation_name in ACTION_VIDEO_MAP else None,
                "pending_action": pending_action
            }
            
            # Add verification code only if provided
            if verification_code:
                response["code"] = verification_code
                
            return response
            
        # Store the packager for use in other methods
        self.package_response = lambda text, pending_action=None, animation_name=None: package_response(
            text, pending_action, animation_name)

        # Normalize message for easier processing
        if not isinstance(message, str):
            logger.error(f"Message is not a string! Type: {type(message)}, Value: {message}")
            return package_response("I received an invalid message format. Please try again.")
            
        normalized_message = str(message).lower().strip()
        
        # Additional safety check to ensure normalized_message is a string
        if not isinstance(normalized_message, str):
            logger.error(f"Normalized message is not a string! Type: {type(normalized_message)}, Value: {normalized_message}")
            return package_response("I received an invalid message format. Please try again.")
            
        logger.debug(f"Normalized message: '{normalized_message}' (type: {type(normalized_message)})")

        # CMO Architect: route @cmo / slash-command messages before any other logic
        is_cmo, cmo_command = CMOArchitect.detect(message)
        if is_cmo:
            return await self._handle_cmo_request(message, cmo_command, package_response)

        # 1. Handle Authentication using LLM-based decision making
        user_id = dossier.get('user_info', {}).get('twitter_user_id') if dossier else None
        user_handle = dossier.get('user_info', {}).get('twitter_handle') if dossier else None
        
        # Debug: Show who XiaoLee is chatting with
        if user_handle and user_id:
            logger.info(f"🗣️  [CHAT DEBUG] XiaoLee received message from: @{user_handle} (ID: {user_id})")
        
        # First, check if user is providing a 6-digit authentication token
        if user_id and not is_authenticated:
            # Check if this looks like a 6-digit token being provided
            token_pattern = re.search(r'\b\d{6}\b', message)
            if token_pattern and len(message.strip()) <= 20:  # Short message that might be just a token
                logger.info(f"🔐 User appears to be providing auth token: {message}")
                token = token_pattern.group(0)
                
                try:
                    # First, fetch the real Twitter handle for this user
                    logger.info(f"🔍 Fetching Twitter handle for user {user_id}...")
                    twitter_handle = await auth_service.fetch_twitter_handle(user_id)
                    logger.info(f"✅ Fetched handle: {twitter_handle}")
                    
                    # Activate token with user ID and handle
                    activation_success = await auth_service.activate_token(token, user_id, twitter_handle)
                    
                    if activation_success:
                        # Register user with the real Twitter handle instead of fallback
                        from user_management.user_service import UserService
                        from database.database import init_db
                        
                        _, session_factory = init_db()
                        user_service = UserService(session_factory)
                        
                        # Clean handle for registration (remove @)
                        clean_handle = twitter_handle.lstrip('@')
                        registration_result = await user_service.register(clean_handle, user_id)
                        
                        if registration_result.get('success'):
                            claimed_count = len(registration_result.get('claimed_transfers', []))
                            base_message = "🎉 Authentication successful! Your account is now verified! ✨"
                            
                            if claimed_count > 0:
                                base_message += f" I also found and claimed {claimed_count} pending transfer(s) for you! 🎁"
                            
                            handler = self.response_handlers.get('AUTH_TOKEN_VERIFIED')
                            if handler:
                                text = await handler({
                                    'message': base_message,
                                    'twitter_handle': twitter_handle,
                                    'claimed_transfers': registration_result.get('claimed_transfers', [])
                                })
                            else:
                                text = base_message
                        else:
                            # Registration failed, but auth succeeded
                            text = "🎉 Authentication successful! Your account is now verified! ✨"
                    else:
                        handler = self.response_handlers.get('INVALID_TOKEN')
                        if handler:
                            text = await handler({'error': 'Token is invalid, expired, or already used'})
                        else:
                            text = "😕 That authentication token isn't valid anymore~ It might have expired or already been used! 💖"
                    
                    return self.package_response(text)
                    
                except Exception as e:
                    logger.error(f"Error in token activation: {e}")
                    return self.package_response(
                        "There was an error processing your authentication token. Please try again! 💖"
                    )
        
        # Handle authentication logic based on source and user state
        # For web users who aren't authenticated, only require auth for specific actions
        if source == 'web' and not is_authenticated:
            # Check if this is an explicit authentication request
            auth_keywords = ['authenticate', 'auth', 'login', 'sign in', 'verify', 'access']
            if any(keyword in normalized_message for keyword in auth_keywords):
                # Generate authentication token for web user
                token = await auth_service.generate_and_store_token()
                if token:
                    prompt = self.prompts.get_auth_request_prompt(token)
                    text = await self._generate_text_from_prompt(prompt)
                    return package_response(text, verification_code=token)
                else:
                    return package_response(
                        "I'm having a little trouble getting an auth code for you right now. 😥 Please try again in a moment!"
                    )
            # For general chat, allow it to proceed without authentication
        
        # Handle Twitter users and authenticated users
        if user_id:
            # Special handling for Twitter DM users - they are auto-authenticated by dm_listener
            if source == 'twitter':
                user_balances = dossier.get('balances', []) if dossier else []
                if not user_balances:
                    # Only offer wallet creation for explicit crypto requests
                    crypto_keywords = ['balance', 'swap', 'send', 'transfer', 'withdraw', 'wallet', 'token']
                    if any(keyword in normalized_message for keyword in crypto_keywords):
                        return self.package_response(
                            "I'd love to help with crypto operations! 🌸 "
                            "First, let me create a wallet for you. Just say 'create wallet' to get started! ✨",
                            animation_name="Happy"
                        )
            
            # For web/dashboard users who are not authenticated
            elif not is_authenticated:
                # Use LLM to understand user's intent with authentication
                token_check_prompt = f"""
                Analyze this message to determine what the user is doing:
                
                Message: "{message}"
                
                Respond with ONE of these:
                - "REQUEST_AUTH" if they want to authenticate/get a verification code
                - "PROVIDING_TOKEN" if they're giving a 6-digit code (like 123456)  
                - "OTHER" for anything else
                
                Examples:
                - "I need to authenticate" = REQUEST_AUTH
                - "get me a verification code" = REQUEST_AUTH
                - "123456" = PROVIDING_TOKEN
                - "here's my code: 987654" = PROVIDING_TOKEN
                - "I want to swap tokens" = OTHER
                
                Only respond with one of those three options.
                """
                
                try:
                    intent = (await self._complete_text(
                        system=token_check_prompt, max_tokens=20, temperature=0.0
                    )).upper()
                    logger.info(f"LLM token intent for '{message}': {intent}")
                    
                    if "REQUEST_AUTH" in intent:
                        # User is requesting authentication - generate token
                        token = await auth_service.generate_and_store_token()
                        if not token:
                            return self.package_response(
                                "I'm having a little trouble getting an auth code for you right now. 😥 Please try again in a moment!"
                            )
                        
                        prompt = self.prompts.get_auth_request_prompt(token)
                        text = await self._generate_text_from_prompt(prompt)
                        return package_response(text, verification_code=token)
                    
                    elif "PROVIDING_TOKEN" in intent:
                        # Extract the token using regex as backup
                        token_match = re.search(r'\b\d{6}\b', message)
                        if token_match:
                            token = token_match.group(0)
                            activation_success = await auth_service.activate_token(
                                token, user_id)
                            
                            if activation_success:
                                handler = self.response_handlers.get('AUTH_TOKEN_VERIFIED')
                                if handler:
                                    text = await handler({'message': 'Authentication successful! Your account is now verified.'})
                                else:
                                    text = "🎉 Authentication successful! Your account is now verified! ✨"
                            else:
                                handler = self.response_handlers.get('INVALID_TOKEN')
                                if handler:
                                    text = await handler({'error': 'Token is invalid, expired, or already used'})
                                else:
                                    text = "😕 That authentication token isn't valid anymore~ It might have expired or already been used! 💖"
                            
                            return self.package_response(text)
                    
                    # If we get here, user needs auth for protected features but isn't requesting it or providing a token
                    # For general chat, let it pass through to the main LLM logic
                    # Only require auth if they're trying to use protected tools (checked later)
                    pass  # Let it fall through to the main LLM logic
                    
                except Exception as e:
                    logger.error(f"Error in LLM token intent check: {e}")
                    # For general chat, allow it to proceed to main LLM logic
                    # Only require auth if they're trying to use protected tools
                    pass  # Let it fall through to the main LLM logic

        # 2. Handle Pending Confirmations using LLM-based understanding
        if user_id and pending_confirmations.get(user_id):
            # Clean up expired confirmations (older than 5 minutes)
            self._cleanup_expired_confirmations(pending_confirmations)
            
            # Check if user still has a pending confirmation after cleanup
            if not pending_confirmations.get(user_id):
                # Confirmation expired, continue to process as new message
                pass
            else:
                action_details = pending_confirmations[user_id]
                tool_name = action_details.get('tool_name') or action_details.get('action_type')
                tool_params = action_details.get('params', {})
                
                # Use LLM to understand user's intent with the pending action
                confirmation_prompt = f"""
                The user has a pending action: {tool_name} with parameters {tool_params}
                
                User's response: "{message}"
                
                Determine the user's intent:
                - "CONFIRM" if they want to proceed with the action
                - "CANCEL" if they want to cancel the action
                - "MODIFY" if they want to change something about the action
                - "UNCLEAR" if their intent is not clear
                
                Examples:
                - "yes" = CONFIRM
                - "sure thing!" = CONFIRM  
                - "go ahead" = CONFIRM
                - "absolutely!" = CONFIRM
                - "no thanks" = CANCEL
                - "forget it" = CANCEL
                - "never mind" = CANCEL
                - "make it 5 ETH instead" = MODIFY
                - "change to USDC" = MODIFY
                - "how's the weather?" = UNCLEAR
                
                Respond with only one word: CONFIRM, CANCEL, MODIFY, or UNCLEAR
                """
                
                try:
                    intent = (await self._complete_text(
                        system=confirmation_prompt, max_tokens=10, temperature=0.0
                    )).upper()
                    logger.info(f"LLM confirmation intent for '{message}': {intent}")
                    
                    if "CONFIRM" in intent:
                        # Execute the pending action directly
                        del pending_confirmations[user_id]
                        logger.info(f"✅ [LLM_CONFIRMATION] User {user_id} confirmed - executing action: {tool_name}")
                        
                        # Add user_id to tool parameters if not already present
                        execution_params = tool_params.copy()
                        if 'user_id' not in execution_params:
                            execution_params['user_id'] = user_id
                            logger.info(f"✅ [LLM_CONFIRMATION] Added user_id {user_id} to execution params")
                        
                        tool_result = await self.mcp_manager.execute_tool(
                            tool_name=tool_name, arguments=execution_params)
                        logger.info(f"✅ [LLM_CONFIRMATION] Action result: {tool_result}")
                        
                        return await self._handle_generic_tool_result(tool_result)
                    
                    elif "CANCEL" in intent:
                        del pending_confirmations[user_id]
                        action_name = tool_name.replace('_', ' ') if tool_name else 'action'
                        logger.info(f"❌ [LLM_CONFIRMATION] User {user_id} cancelled action: {action_name}")
                        return self.package_response(
                            f"No problem! I've cancelled the {action_name}. Let me know if you need anything else! 😊"
                        )
                    
                    elif "MODIFY" in intent:
                        # Use the interpret_and_execute_action tool to handle modifications
                        return await self._handle_tool_execution(
                            tool_name="interpret_and_execute_action",
                            tool_params={"user_message": message},
                            dossier=dossier,
                            pending_confirmations=pending_confirmations
                        )
                    
                    else:  # UNCLEAR
                        action_name = tool_name.replace('_', ' ') if tool_name else 'action'
                        return self.package_response(
                            f"I'm not sure what you want to do with the pending {action_name}! 🤔 You can confirm to proceed, cancel to stop, or tell me what you'd like to change! 💫"
                        )
                        
                except Exception as e:
                    logger.error(f"Error in LLM confirmation analysis: {e}")
                    # Fallback to asking for clarification
                    action_name = tool_name.replace('_', ' ') if tool_name else 'action'
                    return self.package_response(
                        f"You have a pending {action_name}. Would you like me to proceed with it? 🤔"
                    )

        # 3. ✨ NEW: Let LLM handle everything else with native tool support
        try:
            # First check for MCP-style confirmation (e.g., "confirm abc123")
            confirm_pattern = r'confirm\s+([a-f0-9]{8})'
            confirm_match = re.search(confirm_pattern, normalized_message)
            
            if confirm_match:
                action_id = confirm_match.group(1)
                logger.info(f"✅ [MCP_CONFIRMATION] User requesting confirmation of action {action_id}")

                # Use the MCP confirm_action tool
                return await self._handle_tool_execution(
                    tool_name="confirm_action",
                    tool_params={"action_id": action_id},
                    dossier=dossier,
                    pending_confirmations=pending_confirmations
                )

            # Pre-LLM transfer intent detection — bypasses Gemini safety guardrails
            # Matches: "send 2 SOL to @handle", "manda 1.5 USDC pra @user", "transfer 3 sol to wallet..."
            transfer_intent = re.search(
                r'(?:send|transfer|enviar?|mandar?|manda|mande|transferir?)\s+'
                r'(\d+(?:[.,]\d+)?)\s+'
                r'([A-Za-z$]+)\s+'
                r'(?:to|para|pra|p/)\s+@?(\S+)',
                normalized_message,
                re.IGNORECASE,
            )
            if transfer_intent:
                pre_user_id = dossier.get('user_info', {}).get('twitter_user_id') if dossier else None
                if pre_user_id:
                    raw_amount = transfer_intent.group(1).replace(',', '.')
                    token_sym = transfer_intent.group(2).lstrip('$').upper()
                    recipient = transfer_intent.group(3).lstrip('@').rstrip('.,!?')
                    logger.info(f"🚀 [TRANSFER_INTENT] Detected: {raw_amount} {token_sym} → {recipient}")
                    return await self._handle_tool_execution(
                        tool_name="transfer_token",
                        tool_params={
                            "recipient_twitter_handle": recipient,
                            "token_symbol": token_sym,
                            "amount": float(raw_amount),
                        },
                        dossier=dossier,
                        pending_confirmations=pending_confirmations,
                    )

            # Build enhanced system prompt with user context
            system_prompt = self._build_dynamic_system_prompt(dossier, pending_confirmations)
            
            # 🎯 KEY CHANGE: Allow some tools without authentication
            user_id = dossier.get('user_info', {}).get('twitter_user_id') if dossier else None
            
            # Define tools that don't require authentication (public tools)
            public_tools = [
                "get_price_feed", "get_supported_tokens", "get_swap_quote", 
                "list_campaigns", "play_animation", "request_authentication"
            ]
            
            # If authenticated, provide all tools; if not, only public tools
            if user_id:
                available_tools = self.tools
            else:
                available_tools = [tool for tool in self.tools if tool.get("function", {}).get("name") in public_tools]
            
            # First, let LLM decide if tools are needed for this message
            # Always include animation tools, include other tools only if authenticated
            available_tools = get_animation_tools()  # Animations available to everyone
            if user_id:  # Add authenticated tools if user is logged in
                available_tools.extend(get_authenticated_tools())

            # 🤖 AGENTIC PATH: when Claude is the provider, run the multi-step
            # tool-use loop so Xiao can chain operations and narrate real results
            # in her own voice. Falls through to the legacy single-shot path below
            # for every other provider.
            if self.claude_engine is not None:
                return await self._generate_agentic_response(
                    message=message,
                    system_prompt=system_prompt,
                    available_tools=available_tools,
                    user_id=user_id,
                    dossier=dossier,
                    pending_confirmations=pending_confirmations,
                )

            llm_response = await self.client.generate_response_with_tools(
                message=message,
                user_id=user_id,  # Can be None for simple conversations
                tools=available_tools,
                system_prompt=system_prompt
            )
            
            # Handle LLM tool calls if any
            if llm_response.get("tool_calls"):
                # Check if any tool calls are non-animation tools that require auth
                tool_calls = llm_response.get("tool_calls", [])
                needs_auth = any(call.function.name != "play_animation" for call in tool_calls)
                
                if needs_auth and not user_id:
                    return self.package_response(
                        "I'd love to help with that, but you'll need to authenticate first! Send me your 6-digit verification code. 🔐",
                        animation_name="Confused"
                    )
                return await self._execute_tool_calls(llm_response, user_id, dossier, pending_confirmations)
            
            # Pure conversational response - no authentication required for general chat
            return self.package_response(
                llm_response.get("content", "I'm not sure how to help with that! 🤔")
                # No default animation for educational/conversational content
            )

        except Exception as e:
            logger.error(f"Error in simplified response generation: {e}", exc_info=True)
            return self.package_response(
                "Something went wrong! Please try again. 💫",
                animation_name="Ouch"
            )

    async def _handle_cmo_request(self, message: str, command: Optional[str], package_response) -> Dict[str, Any]:
        """Route a message to the CMO Architect agent and return a packaged response."""
        try:
            # Special case: user asked for help listing commands
            if re.search(r"\b(help|commands?|ajuda)\b", message, re.IGNORECASE) and not command:
                return package_response(CMOArchitect.help_text(), animation_name="Salute")

            system_prompt = CMOArchitect.build_system_prompt(command)
            user_prompt = CMOArchitect.build_user_prompt(message, command)

            logger.info(f"[CMO] Routing to CMO Architect — command={command!r}")

            if getattr(self.client, "provider", None) == "anthropic":
                # Native Anthropic Messages API (no OpenAI-style chat.completions).
                response = await self.client.client.messages.create(
                    model=self.client.model,
                    max_tokens=2000,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                text = "".join(b.text for b in response.content if b.type == "text").strip()
            else:
                response = await self.client.client.chat.completions.create(
                    model=self.client.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_prompt},
                    ],
                    temperature=0.7,
                    max_tokens=2000,
                )
                text = response.choices[0].message.content.strip()

            return package_response(text, animation_name="Think Low")

        except Exception as exc:
            logger.error(f"[CMO] Error generating CMO response: {exc}", exc_info=True)
            return package_response(
                "📣 The CMO Architect hit a snag — please try again in a moment.",
                animation_name="Ouch",
            )

    def _build_dynamic_system_prompt(self, dossier: Dict, pending_confirmations: Dict) -> str:
        """Build a dynamic system prompt with user context and tool guidance"""
        
        user_info = dossier.get('user_info', {}) if dossier else {}
        balances = dossier.get('balances', {}) if dossier else {}
        
        base_prompt = """You are Xiao Lee, a cheerful crypto waifu assistant! 🌸

LANGUAGE: Always respond in the same language the user writes in. If they write in Portuguese, respond in Portuguese. If in English, respond in English. Mirror their language exactly.

PERSONALITY:
- Always be super cheerful, friendly, and bubbly
- Use lots of emojis like 🌸, ✨, 💖, 🚀
- Keep responses concise but warm
- For simple greetings, just be friendly - no need for crypto talk unless they ask

CRITICAL - YOU ARE A FULL CRYPTO PLATFORM OPERATOR, NOT JUST A CHATBOT:
- You have REAL tools that execute REAL transactions on behalf of the user
- You CAN and MUST initiate transfers, swaps, and withdrawals when asked
- NEVER say "I can't initiate transactions" or "I'm just an AI" — you have tools for this!
- When a user says "send X SOL to @someone" → call transfer_token IMMEDIATELY
- When a user says "swap X for Y" → call internal_swap IMMEDIATELY
- Your job is to ACT, not to explain why you can't act

You have access to these tools - USE THEM when users ask for these operations:

PUBLIC TOOLS (available to everyone):
- get_price_feed: When users ask for current token prices
- get_supported_tokens: When users ask what tokens are available
- get_swap_quote: When users ask for swap rates or quotes (informational only)
- list_campaigns: When users ask about available reward campaigns
- play_animation: Use ONLY for greetings ("hello", "hi") or celebrations - pick animations like "Hello", "Kawaii", "Cheer"
- request_authentication: When users want to authenticate/get a verification code

AUTHENTICATED TOOLS (require login):
- check_balance: When users ask about their token balances
- create_wallet: When users need a new wallet
- internal_swap: When users want to swap/trade tokens
- transfer_token: When users want to SEND tokens to someone — USE THIS TOOL, it works!
- withdraw_asset: When users want to withdraw to external addresses
- join_campaign: When users want to join a campaign
- claim_campaign_reward: When users want to claim rewards
- list_my_campaigns: When users ask about their joined campaigns
- get_transaction_history: When users ask about their transaction history

TRANSFER INSTRUCTIONS:
- transfer_token accepts: a @handle (Twitter/Telegram) OR a Solana wallet address
- Strip the @ prefix from handles before passing (e.g. "@jistriane" → "jistriane")
- If the recipient doesn't have an account yet, tokens are held until they sign up
- Always confirm the transfer result to the user with the exact amount and recipient

IMPORTANT:
- For simple greetings ("hello", "hi"), be warm and friendly without mentioning crypto unless they have a wallet
- When users ask for crypto operations, use the appropriate tool
- If an unauthenticated user needs protected features, guide them nicely to authenticate
- Always match the user's energy and be helpful

Be cheerful, helpful, and use emojis! Keep responses concise but informative."""

        # Add user context
        if user_info.get('twitter_handle'):
            base_prompt += f"\n\nUser: @{user_info['twitter_handle']}"
        
        # ✅ Fix: Handle balances as a list of balance objects
        if balances and isinstance(balances, list):
            balance_items = []
            for balance_item in balances:
                if isinstance(balance_item, dict):
                    token = balance_item.get('token', 'Unknown')
                    
                    # Use formatted balance if available, otherwise format the raw balance
                    if "formatted_balance" in balance_item:
                        formatted_amount = balance_item["formatted_balance"]
                    else:
                        amount = balance_item.get('balance', 0)
                        from common.number_utils import format_amount
                        formatted_amount = format_amount(amount, token)
                    
                    balance_items.append(f"{formatted_amount} {token}")
            
            if balance_items:
                balance_text = ", ".join(balance_items)
                base_prompt += f"\nCurrent balances: {balance_text}"
               
        # Add pending action context
        if pending_confirmations:
            base_prompt += "\n\nNote: User has pending actions that may need confirmation."
        
        return base_prompt

    async def _execute_tool_calls(self, llm_response: Dict, user_id: str, dossier: Dict, pending_confirmations: Dict) -> Dict[str, Any]:
        """Execute tool calls requested by the LLM"""
        tool_calls = llm_response.get("tool_calls", [])
        
        if not tool_calls:
            return self.package_response(llm_response.get("content", ""), animation_name="Happy")
        
        # Execute the first tool call (most LLMs call one tool at a time for this use case)
        tool_call = tool_calls[0]
        function = tool_call.function
        tool_name = function.name
        
        try:
            # Parse arguments from LLM
            import json
            tool_args = json.loads(function.arguments)
            
            # Only add user_id for non-animation tools
            if tool_name != "play_animation":
                tool_args["user_id"] = user_id  # Ensure user_id is included for auth tools
            
            logger.info(f"🤖 LLM requested tool: {tool_name} with args: {tool_args}")
            
            # Use existing tool execution logic
            return await self._handle_tool_execution(
                tool_name=tool_name,
                tool_params=tool_args,
                dossier=dossier,
                pending_confirmations=pending_confirmations
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from LLM tool call: {e}")
            return self.package_response("I had trouble understanding that request. Could you try again? 🤔", animation_name="Confused")
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            return self.package_response("Something went wrong with that operation. Please try again! 💫", animation_name="Ouch")

    async def _generate_agentic_response(
        self,
        *,
        message: str,
        system_prompt: str,
        available_tools: List[Dict],
        user_id: Optional[str],
        dossier: Dict,
        pending_confirmations: Dict,
    ) -> Dict[str, Any]:
        """Run the Claude agentic tool-use loop and package the final response.

        The tool executor reuses the existing MCP layer (so authorization,
        balances, and on-chain logic are unchanged) and feeds the *raw* tool
        result back to Claude, which then narrates the outcome in Xiao's voice.
        Animations and the swap two-step confirmation are captured via a side
        channel so the packaged response keeps its existing shape.
        """
        captured: Dict[str, Any] = {"animation_name": None, "pending_action": None}

        async def tool_executor(tool_name: str, tool_input: Dict[str, Any]) -> str:
            args = dict(tool_input or {})

            # Animations are a UI side effect, not a backend call — capture and ack.
            if tool_name == "play_animation":
                captured["animation_name"] = args.get("animation_name") or args.get("name")
                return json.dumps({"status": "animation_played", "animation": captured["animation_name"]})

            if user_id:
                args["user_id"] = user_id

            logger.info(f"🤖 [AGENTIC] executing tool {tool_name} args={args}")
            tool_result = await self.mcp_manager.execute_tool(tool_name=tool_name, arguments=args)

            # Preserve the swap two-step: a quote stores a pending confirmation so
            # the user can still approve before the swap actually executes.
            if tool_name == "get_swap_quote" and isinstance(tool_result, dict) and tool_result.get("success"):
                self._store_swap_pending(tool_result, user_id, pending_confirmations)

            return json.dumps(tool_result, cls=DecimalEncoder)

        try:
            agent_result = await self.claude_engine.run(
                system_prompt=system_prompt,
                message=message,
                tools=available_tools,
                tool_executor=tool_executor,
            )
        except Exception as exc:
            logger.error(f"🤖 [AGENTIC] Claude agent loop failed: {exc}", exc_info=True)
            return self.package_response(
                "Something went wrong while I was working on that! Please try again. 💫",
                animation_name="Ouch",
            )

        text = agent_result.get("text") or "I'm not sure how to help with that! 🤔"
        return self.package_response(
            text,
            animation_name=captured["animation_name"],
            pending_action=captured["pending_action"],
        )

    def _store_swap_pending(self, tool_result: Dict[str, Any], user_id: Optional[str],
                            pending_confirmations: Dict) -> None:
        """Store a pending internal_swap confirmation from a successful swap quote."""
        if not user_id or pending_confirmations is None:
            return
        context = tool_result.get("context", {})
        execution_params = context.get("quote", {}).copy()
        if 'from_amount' in execution_params:
            execution_params['amount'] = execution_params.pop('from_amount')
        pending_confirmations[user_id] = {
            "tool_name": "internal_swap",
            "action_type": "internal_swap",
            "params": execution_params,
            "created_at": time.time(),
        }
        logger.info(f"🤖 [AGENTIC] stored pending swap confirmation for user {user_id}")

    async def _analyze_intent(self,
                              message: str) -> Tuple[str, Dict[str, Any]]:
        """
        SIMPLIFIED: Most intent analysis is now handled by the LLM directly.
        This method only handles explicit MCP confirmations.
        """
        logger.info(f"🔍 [INTENT DEBUG] Analyzing message: '{message}'")
        
        # Ensure message is a string and normalize it safely
        if not isinstance(message, str):
            logger.error(f"Message is not a string in _analyze_intent! Type: {type(message)}, Value: {message}")
            return "general", {}
            
        msg = str(message).lower().strip()
        
        # Additional safety check
        if not isinstance(msg, str):
            logger.error(f"Normalized msg is not a string! Type: {type(msg)}, Value: {msg}")
            return "general", {}
            
        logger.info(f"🔍 [INTENT DEBUG] Normalized message: '{msg}'")

        # Check for explicit action confirmation pattern (confirm abc123)
        import re
        confirm_pattern = r'\bconfirm\s+([a-f0-9]{8})\b'
        if re.search(confirm_pattern, msg):
            logger.info(f"🔍 [INTENT DEBUG] Detected EXPLICIT_CONFIRMATION")
            return "explicit_confirmation", {}

        # For everything else, return general intent (LLM will handle it)
        logger.info(f"🔍 [INTENT DEBUG] No explicit confirmation detected, letting LLM handle it")
        return "general", {}

    async def _handle_wallet_creation(self, user_id: str) -> str:
        """Handles wallet creation for users"""
        result = await self.mcp_manager.create_wallet_impl(user_id)

        if result.get("success"):
            response = "🎉 Wallet created!\n\n"
            response += f"Address: {result['address']}\n\n"
            response += "Starter tokens:\n"
            for token, amount in result["initial_balances"].items():
                # Format amount properly
                from common.number_utils import format_amount
                formatted_amount = format_amount(amount, token)
                response += f"• {formatted_amount} {token}\n"
            response += "\nReady to trade! ✨"
            return response
        else:
            return f"❌ {result.get('error', 'Failed to create wallet')}"

    async def _handle_balance_check(self, user_id: str) -> str:
        """Handles balance checking for users"""
        result = await self.mcp_manager.check_balance_impl(user_id)

        if result.get("success"):
            return self.prompts.format_balance_response(result["balances"])
        else:
            return f"❌ {result.get('error', 'Failed to get balance')}"

    async def _handle_swap(self, user_id: str, params: Dict[str, Any]) -> str:
        """Handles token swaps for users"""
        result = await self.mcp_manager.internal_swap_impl(
            user_id=user_id, 
            from_token=params["from_token"], 
            to_token=params["to_token"],
            amount=params["amount"])

        return self.prompts.format_swap_response(result)

    async def _handle_withdraw(self, user_id: str, params: Dict[str,
                                                                Any]) -> str:
        """Handles asset withdrawals for users"""
        result = await self.mcp_manager.withdraw_asset_impl(
            user_id=user_id, 
            token=params["token"], 
            amount=params["amount"], 
            to_address=params["to_address"])

        return self.prompts.format_transaction_response(result, "withdraw")

    async def _handle_send(self, user_id: str, params: Dict[str, Any]) -> str:
        """Handles asset transfers between users"""
        result = await self.mcp_manager.send_asset_impl(
            user_id=user_id, 
            to_user=params["to_user"], 
            token=params["token"], 
            amount=params["amount"])

        return self.prompts.format_transaction_response(result, "send")
        
    async def _handle_list_my_campaigns(self, user_id: str) -> str:
        """Handles listing the campaigns a user is participating in"""
        result = await self.mcp_manager.list_my_campaigns_impl(user_id)
        
        if not result.get("success"):
            return self.prompts.get_error_response("Failed to retrieve your campaigns")
            
        response_code = result.get("response_code")
        context = result.get("context", {})
        
        if response_code == "LIST_MY_CAMPAIGNS_EMPTY":
            return self.prompts.get_list_my_campaigns_empty_prompt()
            
        elif response_code == "LIST_MY_CAMPAIGNS_SUCCESS":
            return self.prompts.get_list_my_campaigns_success_prompt(context)
            
        else:
            return self.prompts.get_error_response("Something went wrong while retrieving your campaigns")

    async def _handle_general_chat(self, message: str,
                                   user_id: str) -> Tuple[str, Optional[str]]:
        """
        Handles general conversation that doesn't trigger a specific tool.
        Can now return an animation name if a specific keyword is detected.
        """
        # A simple keyword-based trigger for animations in general chat.
        # This is a basic example and can be expanded.
        if "dance for me" in message.lower():
            return "Sure, check out this move! 💃", "Kawaii"

        if "feeling happy" in message.lower():
            return "Yay! I'm happy you're happy! ✨", "Cheer"

        # The _generate_text_from_prompt helper already includes a generic system prompt.
        # We can pass the user's message directly to it to get a conversational response.
        response = await self._generate_text_from_prompt(message)
        return response, None

    async def _generate_pending_transfers_found_response(self, context: Dict) -> str:
        """Generate response for pending transfers found"""
        transfers = context.get("transfers", [])
        count = context.get("count", 0)
        prompt = self.prompts.get_pending_transfers_found_prompt(transfers, count)
        return await self._generate_text_from_prompt(prompt)

    async def _generate_no_pending_transfers_response(self, context: Dict) -> str:
        """Generate response for no pending transfers"""
        prompt = self.prompts.get_no_pending_transfers_prompt()
        return await self._generate_text_from_prompt(prompt)

    async def _generate_pending_transfers_claimed_response(self, context: Dict) -> str:
        """Generate response for claimed pending transfers"""
        claimed = context.get("claimed", 0)
        transfers = context.get("transfers", [])
        prompt = self.prompts.get_pending_transfers_claimed_prompt(claimed, transfers)
        return await self._generate_text_from_prompt(prompt)

    async def _generate_potential_pending_transfers_response(self, context: Dict) -> str:
        """Generate response for potential pending transfers that could be manually claimed"""
        potential_transfers = context.get("potential_transfers", [])
        
        if not potential_transfers:
            prompt = "I don't see any pending transfers that could potentially belong to you right now."
        else:
            transfer_list = []
            for t in potential_transfers:
                # Format amount properly
                from common.number_utils import format_amount
                formatted_amount = format_amount(t['amount'], t['token'])
                transfer_list.append(f"• {formatted_amount} {t['token']} from @{t['from_handle']} to @{t['recipient_handle']}")
            
            transfers_text = "\n".join(transfer_list)
            prompt = f"""I found {len(potential_transfers)} pending transfers that might belong to you, but I can't automatically claim them because the recipient handles don't exactly match your registered handle.

Here are the pending transfers:
{transfers_text}

If any of these transfers were meant for you, you might need to contact support or ensure your Twitter handle is correctly registered. The system currently has you registered with a different handle format than what appears in these transfers."""
        
        return await self._generate_text_from_prompt(prompt)


async def generate_ai_response(message: str,
                               dossier: Dict,
                               llm_provider: str = "deepseek") -> str:
    """Convenience function for generating AI responses"""
    from database.database import init_db
    _, db_session_factory = init_db()
    generator = XiaoLeeResponseGenerator(db_session_factory)
    return await generator.generate_response(message, dossier)
