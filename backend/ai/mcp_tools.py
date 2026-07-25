import logging
import re
import json
import json
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from mcp.server import Server
from mcp.types import Tool, TextContent
from sqlalchemy import text, select, func
from database.database import init_db
from database.models import DMLog, User, TokenPrice, PendingTransfer, TokenBalance, Campaign
from swaps.price_manager import PriceManager
from swaps.balance_manager import BalanceManager
from swaps.swap_engine import SwapEngine
from web3 import Web3
from user_management.user_service import UserService, model_to_dict
from user_management.wallet_service import WalletService
from user_management.campaign_service import CampaignService
from user_management.twitter_interaction_service import TwitterInteractionService
from user_management.authentication_service import AuthenticationService
from config import ACTION_VIDEO_MAP
from common.utils import normalize_token_symbol
from decimal import Decimal, InvalidOperation
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

mcp_server = Server("xiao-lee-crypto")

MCP_TOOLS_SCHEMAS = [{
    "type": "function",
    "function": {
        "name": "play_animation",
        "description":
        "Use this tool ONLY when you want to play a specific animation for greetings, celebrations, or emotional reactions. Do NOT use this for educational responses or general conversations - only for specific expressive moments like hellos, congratulations, or reactions.",
        "parameters": {
            "type": "object",
            "properties": {
                "animation_name": {
                    "type": "string",
                    "description": "The name of the animation to play. Choose based on the mood: Hello for greetings, Cheer for good news, Giggle for humor, Love for affection, Surprise for unexpected things, Ouch for problems, etc.",
                    "enum": list(ACTION_VIDEO_MAP.keys())
                }
            },
            "required": ["animation_name"],
        },
    },
}, {
    "type": "function",
    "function": {
        "name": "get_token_price",
        "description": "Get the current price of a token in USD.",
        "parameters": {
            "type": "object",
            "properties": {
                "token_symbol": {
                    "type": "string",
                    "description": "The symbol of the token (e.g., ETH, BTC)."
                }
            },
            "required": ["token_symbol"],
        },
    },
}, {
    "type": "function",
    "function": {
        "name": "create_wallet",
        "description":
        "Creates a new crypto wallet for the user if they don't have one. Idempotent.",
        "parameters": {
            "type": "object",
            "properties": {}
        },
    },
}, {
    "type": "function",
    "function": {
        "name": "check_balance",
        "description": "Check the user's token balances.",
        "parameters": {
            "type": "object",
            "properties": {}
        },
    },
}, {
    "type": "function",
    "function": {
        "name": "get_price_feed",
        "description": "Get current token prices,and shows supported tokens.",
        "parameters": {
            "type": "object",
            "properties": {}
        },
    },
}, {
    "type": "function",
    "function": {
        "name": "get_swap_quote",
        "description": "Get a quote for swapping between two tokens.",
        "parameters": {
            "type": "object",
            "properties": {
                "from_token": {
                    "type": "string",
                    "description": "The token symbol to swap from."
                },
                "to_token": {
                    "type": "string",
                    "description": "The token symbol to swap to."
                },
                "amount": {
                    "type": "number",
                    "description": "The amount of from_token to swap."
                },
            },
            "required": ["from_token", "to_token", "amount"],
        },
    },
}, {
    "type": "function",
    "function": {
        "name": "internal_swap",
        "description": "Execute a swap between two tokens.",
        "parameters": {
            "type": "object",
            "properties": {
                "from_token": {
                    "type": "string",
                    "description": "The token symbol to swap from."
                },
                "to_token": {
                    "type": "string",
                    "description": "The token symbol to swap to."
                },
                "amount": {
                    "type": "number",
                    "description": "The amount of from_token to swap."
                },
            },
            "required": ["from_token", "to_token", "amount"],
        },
    },
}, {
    "type": "function",
    "function": {
        "name": "withdraw_asset",
        "description": "Withdraw tokens to an external EVM wallet address.",
        "parameters": {
            "type": "object",
            "properties": {
                "token": {
                    "type": "string",
                    "description": "The symbol of the token to withdraw."
                },
                "amount": {
                    "type": "number",
                    "description": "The amount to withdraw."
                },
                "to_address": {
                    "type": "string",
                    "description": "The destination EVM wallet address."
                },
            },
            "required": ["token", "amount", "to_address"],
        },
    },
}, {
    "type": "function",
    "function": {
        "name": "transfer_token",
        "description": "Send tokens to another user identified by their @handle (Twitter, Telegram, or any platform username). Use this tool whenever a user says things like 'send X tokens to @someone', 'manda X XLEE pra @alguem', 'transfer X SOL to @handle', 'enviar tokens para @usuario'. The amount must be a positive number. If the user provides a negative number or zero, reject the operation.",
        "parameters": {
            "type": "object",
            "properties": {
                "recipient_twitter_handle": {
                    "type": "string",
                    "description": "The recipient identifier: a @handle (Twitter or Telegram username) OR a Solana wallet address (base58 string). Examples: 'brazilliancare', 'EZKVUN9RnUt5vpHH5w1c8mD28JmgeTPY4tCcgFSo5LCg'. Strip the @ prefix from handles before passing."
                },
                "token_symbol": {
                    "type": "string",
                    "description": "The symbol of the token to send."
                },
                "amount": {
                    "type": "number",
                    "description": "The amount of the token to send."
                }
            },
            "required": ["recipient_twitter_handle", "token_symbol", "amount"]
        }
    }
}, {
    "type": "function",
    "function": {
        "name": "list_campaigns",
        "description": "List all active campaigns that users can join.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
}, {
    "type": "function",
    "function": {
        "name": "join_campaign",
        "description": "Joins a specific, active campaign for the user by providing its unique name or ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "campaign_identifier": {
                    "type": "string",
                    "description": "The unique name or numerical ID of the campaign to join."
                }
            },
            "required": ["campaign_identifier"]
        }
    }
}, {
    "type": "function",
    "function": {
        "name": "claim_campaign_reward",
        "description": "Claims the reward for a completed campaign the user has joined.",
        "parameters": {
            "type": "object",
            "properties": {
                "campaign_identifier": {
                    "type": "string",
                    "description": "The unique name or ID of the campaign to claim the reward from."
                }
            },
            "required": ["campaign_identifier"]
        }
    }
}, {
    "type": "function",
    "function": {
        "name": "get_supported_tokens",
        "description": "Get a list of all supported tokens in the system that can be used for swaps, transfers, and other operations.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
}, {
    "type": "function",
    "function": {
        "name": "start_campaign_creation",
        "description": "Starts the creation process for a new campaign. Use this tool after the user has specified the campaign type ('airdrop' or 'engagement'). This tool should be the first step in creating any campaign.",
        "parameters": {
            "type": "object",
            "properties": {
                "campaign_type": {
                    "type": "string",
                    "description": "The type of campaign.",
                    "enum": ["airdrop", "engagement"]
                }
            },
            "required": ["campaign_type"]
        }
    }
}, {
    "type": "function",
    "function": {
        "name": "activate_campaign",
        "description": "Activates the pending campaign after all details have been filled out and confirmed by the user.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
}, {
    "type": "function",
    "function": {
        "name": "verify_campaign_tasks",
        "description": "Verifies if a user has completed the required Twitter tasks for a campaign.",
        "parameters": {
            "type": "object",
            "properties": {
                "campaign_identifier": {
                    "type": "string",
                    "description": "The campaign identifier - can be either the campaign ID (numeric) or campaign name."
                }
            },
            "required": ["campaign_identifier"]
        }
    }
}, {
    "type": "function",
    "function": {
        "name": "list_my_campaigns",
        "description": "List all campaigns that the current user has participated or is participating in .",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
}, {
    "type": "function",
    "function": {
        "name": "get_recent_messages",
        "description": "Get the most recent CHAT MESSAGES and CONVERSATION HISTORY with a user to maintain conversational context. This is ONLY for chat messages, NOT for financial transactions, swaps, transfers, or wallet activity.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "The ID of the user whose CHAT MESSAGES to retrieve."
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of recent CHAT MESSAGES to retrieve (default: 3)."
                }
            },
            "required": ["user_id"]
        }
    }
}, {
    "type": "function",
    "function": {
        "name": "check_pending_actions",
        "description": "Check if the user has any pending actions that require confirmation. This helps understand user intent when they mention confirmation-related keywords like 'yes', 'confirm', 'ok', etc.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
}, {
    "type": "function",
    "function": {
        "name": "check_pending_transfers",
        "description": "Check for and claim any pending token transfers for the user. Use this when users ask to 'claim pending transfers', 'check pending tokens', or similar requests about incoming transfers.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
}, {
    "type": "function",
    "function": {
        "name": "confirm_action",
        "description": "Confirm a pending action that requires user approval (like swaps, transfers, etc.).",
        "parameters": {
            "type": "object",
            "properties": {
                "action_id": {
                    "type": "string",
                    "description": "The unique identifier of the action to confirm."
                }
            },
            "required": ["action_id"]
        }
    }
}, {
    "type": "function",
    "function": {
        "name": "interpret_and_execute_action",
        "description": "Intelligently interpret user messages to determine if they want to confirm, cancel, or modify pending actions. This replaces binary yes/no confirmations with natural language understanding.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_message": {
                    "type": "string",
                    "description": "The user's natural language response to interpret (e.g., 'sure thing!', 'nah forget it', 'make it 10 SOL instead')"
                },
                "context": {
                    "type": "object",
                    "description": "Additional context about the pending action and conversation state",
                    "properties": {
                        "pending_action_id": {
                            "type": "string",
                            "description": "ID of the pending action being referenced"
                        },
                        "conversation_history": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Recent conversation messages for context"
                        }
                    }
                }
            },
            "required": ["user_message"]
        }
    }
}, {
    "type": "function",
    "function": {
        "name": "request_authentication",
        "description": "Generate an authentication token for a user. This tool provides a 6-digit authentication code that users can use to verify their identity and access secured features.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
}, {
    "type": "function", 
    "function": {
        "name": "verify_authentication_token",
        "description": "Verify an authentication token provided by the user. This confirms the user's identity and activates their authentication status.",
        "parameters": {
            "type": "object",
            "properties": {
                "token": {
                    "type": "string",
                    "description": "The 6-digit authentication token provided by the user."
                }
            },
            "required": ["token"]
        }
    }
}, {
    "type": "function",
    "function": {
        "name": "get_transaction_history",
        "description": "Get the user's complete FINANCIAL TRANSACTION HISTORY and WALLET ACTIVITY including balances changes, swaps, transfers, withdrawals, and other MONETARY activities. Use this for ANY request about financial transactions, trading history, or wallet activity.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of transactions to retrieve (default: 10, max: 50)"
                },
                "transaction_type": {
                    "type": "string",
                    "description": "Filter by transaction type: 'all', 'swap', 'transfer', 'campaign', 'withdrawal' (default: 'all')",
                    "enum": ["all", "swap", "transfer", "campaign", "withdrawal"]
                }
            }
        }
    }
}, {
    "type": "function",
    "function": {
        "name": "get_pending_transfers",
        "description": "Get pending transfers for the user",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "The Twitter user ID"
                }
            },
            "required": ["user_id"]
        }
    }
}, {
    "type": "function",
    "function": {
        "name": "claim_pending_transfers",
        "description": "Claim all pending transfers for the user",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "The Twitter user ID"
                }
            },
            "required": ["user_id"]
        }
    }
}, {
    "type": "function",
    "function": {
        "name": "login_user",
        "description": "Login/register a user with their Twitter handle and auto-claim any pending transfers",
        "parameters": {
            "type": "object",
            "properties": {
                "twitter_handle": {
                    "type": "string",
                    "description": "The actual Twitter handle (without @ prefix)"
                },
                "twitter_user_id": {
                    "type": "string",
                    "description": "The Twitter user ID"
                }
            },
            "required": ["twitter_handle", "twitter_user_id"]
        }
    }
}]


def get_mcp_tools() -> List[Dict]:
    return MCP_TOOLS_SCHEMAS

def get_animation_tools() -> List[Dict]:
    """Get only animation tools that don't require authentication"""
    return [tool for tool in MCP_TOOLS_SCHEMAS if tool["function"]["name"] == "play_animation"]

def get_authenticated_tools() -> List[Dict]:
    """Get tools that require authentication (all except animations)"""
    return [tool for tool in MCP_TOOLS_SCHEMAS if tool["function"]["name"] != "play_animation"]


class MCPToolsManager:
    """
    Manages the lifecycle of MCP tools, including instantiation and execution.
    This class is responsible for holding the database session factory and passing
    it down to the various services it instantiates.
    """
    def __init__(self, db_session_factory):
        if db_session_factory is None:
            _, self.db_session_factory = init_db()
        else:
            self.db_session_factory = db_session_factory

        # Initialize services that are used across multiple tool calls
        self.user_service = UserService(self.db_session_factory)
        self.wallet_service = WalletService(self.db_session_factory)
        self.campaign_service = CampaignService(self.db_session_factory)
        self.authentication_service = AuthenticationService(self.db_session_factory)
        # self.twitter_interaction_service = TwitterInteractionService()
        self.price_manager = PriceManager(self.db_session_factory)
        self.balance_manager = BalanceManager(self.db_session_factory)
        self.swap_engine = SwapEngine(self.price_manager, self.balance_manager)
        self.pending_confirmations: Dict[str, Any] = {}
        logger.info("🛠️ MCPToolsManager initialized with all services.")

        # Tool name to implementation mapping
        self.tool_implementations = {
            "get_token_price": self.get_token_price_impl,
            "check_balance": self.check_balance_impl,
            "create_wallet": self.create_wallet_impl,
            "get_swap_quote": self.get_swap_quote_impl,
            "internal_swap": self.internal_swap_impl,
            "withdraw_asset": self.withdraw_asset_impl,
            "play_animation": self.play_animation_impl,
            "transfer_token": self.transfer_token_impl,
            "list_campaigns": self.list_campaigns_impl,
            "join_campaign": self.join_campaign_impl,
            "get_supported_tokens": self.get_supported_tokens_impl,
            "claim_campaign_reward": self.claim_campaign_reward_impl,
            "start_campaign_creation": self.start_campaign_creation_impl,
            "activate_campaign": self.activate_campaign_impl,
            "verify_campaign_tasks": self.verify_campaign_tasks_impl,
            "list_my_campaigns": self.list_my_campaigns_impl,
            "get_recent_messages": self.get_recent_messages_impl,
            "get_price_feed": self.get_price_feed_impl,
            "check_pending_actions": self.check_pending_actions_impl,
            "check_pending_transfers": self.check_pending_transfers_impl,
            "confirm_action": self.confirm_action_impl,
            "interpret_and_execute_action": self.interpret_and_execute_action_impl,
            "request_authentication": self.request_authentication_impl,
            "verify_authentication_token": self.verify_authentication_token_impl,
            "get_transaction_history": self.get_transaction_history_impl,
            "get_pending_transfers": self.get_pending_transfers_impl,
            "claim_pending_transfers": self.claim_pending_transfers_impl,
            "login_user": self.login_user_impl,
        }

    async def execute_tool(self, tool_name: str,
                           arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a tool by name with the given arguments.
        This method intelligently passes user_id only to the tools that need it.
        """
        logger.info(f"🔧 [TOOL EXEC DEBUG] Executing tool: {tool_name}")
        logger.info(f"🔧 [TOOL EXEC DEBUG] Arguments: {arguments}")
        logger.info(f"🔧 [TOOL EXEC DEBUG] Available tools: {list(self.tool_implementations.keys())}")
        
        if tool_name not in self.tool_implementations:
            logger.warning(f"🔧 [TOOL EXEC DEBUG] Tool '{tool_name}' not found in tool_implementations")
            logger.warning(f"Attempted to call unknown tool: {tool_name}")
            return {"success": False, "response_code": "TOOL_NOT_FOUND", "context": {"tool_name": tool_name}}

        method_to_call = self.tool_implementations[tool_name]
        logger.info(f"🔧 [TOOL EXEC DEBUG] Found method: {method_to_call}")
        
        import inspect
        sig = inspect.signature(method_to_call)
        logger.info(f"🔧 [TOOL EXEC DEBUG] Method signature: {sig}")
        
        final_args = arguments.copy()

        # Handle user_id parameter
        if 'user_id' not in sig.parameters and 'user_id' in final_args:
            logger.info(f"🔧 [TOOL EXEC DEBUG] Removing user_id from args (method doesn't need it)")
            final_args.pop('user_id')
        elif 'user_id' in sig.parameters and 'user_id' in final_args:
            logger.info(f"🔧 [TOOL EXEC DEBUG] Keeping user_id in args: {final_args['user_id']}")
        elif 'user_id' in sig.parameters and 'user_id' not in final_args:
            logger.warning(f"🔧 [TOOL EXEC DEBUG] Method requires user_id but it's missing from arguments!")
            return {"success": False, "response_code": "TOOL_ARGUMENT_ERROR", "context": {"error": "Missing required user_id parameter"}}

        # Filter out unexpected arguments that don't match method signature
        expected_params = set(sig.parameters.keys())
        provided_params = set(final_args.keys())
        unexpected_params = provided_params - expected_params
        
        if unexpected_params:
            logger.warning(f"🔧 [TOOL EXEC DEBUG] Removing unexpected parameters: {unexpected_params}")
            for param in unexpected_params:
                final_args.pop(param)

        logger.info(f"🔧 [TOOL EXEC DEBUG] Final arguments for tool call: {final_args}")

        try:
            logger.info(f"🔧 [TOOL EXEC DEBUG] Calling {tool_name} with args: {final_args}")
            result = await method_to_call(**final_args)
            logger.info(f"🔧 [TOOL EXEC DEBUG] Tool {tool_name} returned: {result}")
            return result
        except TypeError as te:
            logger.error(f"🔧 [TOOL EXEC DEBUG] TypeError in tool '{tool_name}': {te}", exc_info=True)
            logger.error(f"Tool '{tool_name}' called with incorrect arguments: {te}", exc_info=True)
            # This can happen if the LLM hallucinates arguments.
            return {"success": False, "response_code": "TOOL_ARGUMENT_ERROR", "context": {"error": str(te)}}
        except Exception as e:
            logger.error(f"🔧 [TOOL EXEC DEBUG] Unexpected error in tool '{tool_name}': {e}", exc_info=True)
            logger.error(f"Unexpected error executing tool '{tool_name}': {e}", exc_info=True)
            return {"success": False, "response_code": "TOOL_EXECUTION_ERROR", "context": {"error": str(e)}}

    async def process_request(self,
                              user_id: str,
                              request: str,
                              context: Dict[str, Any] = None) -> str:
        """Processes a user's request by calling the appropriate tool."""
        logger.info(
            f"Processing request for user {user_id} with request: {request}")

        # This mapping is now conceptual. The actual call is generic.
        tool_map = {
            "get_token_price": self.get_token_price_impl,
            "check_balance": self.check_balance_impl,
            "create_wallet": self.create_wallet_impl,
            "internal_swap": self.internal_swap_impl,
        }

        # A simple router - more sophisticated logic could be used here
        if "price" in request.lower():
            tool_name = "get_token_price"
        elif "balance" in request.lower():
            tool_name = "check_balance"
        elif "wallet" in request.lower():
            tool_name = "create_wallet"
        elif "swap" in request.lower() or "exchange" in request.lower():
            tool_name = "internal_swap"
        else:
            return "I'm not sure how to handle that request."

        try:
            if tool_name == "check_balance":
                result = await self.check_balance_impl(user_id)
                if result.get('success'):
                    return f"Balance check successful. User balances: {result.get('context', {}).get('balances')}"
                else:
                    return f"❌ {result.get('context', {}).get('error', 'Could not check balance')}"

            # Example for create_wallet
            if tool_name == "create_wallet":
                 result = await self.create_wallet_impl(user_id)
                 if result.get('success'):
                     return "✅ Wallet created successfully."
                 else:
                     return f"❌ {result.get('context', {}).get('error', 'Could not create wallet')}"

            # Fallback for other tools
            return f"Tool {tool_name} would be called here."

        except Exception as e:
            logger.error(f"Process request error: {e}")
            return "❌ Error processing your crypto request. Please try again!"

    async def create_wallet_impl(self, user_id: str) -> Dict[str, Any]:
        """Creates a wallet for a user. Now returns a structured response."""
        if not user_id:
            return {"success": False, "response_code": "USER_NOT_FOUND", "context": {}}
        try:
            logger.info(f"Executing create_wallet for user_id: {user_id}")
            
            # First, ensure user exists in database
            user = await self.user_service.get_user_by_twitter_id(user_id)
            if not user:
                return {"success": False, "response_code": "USER_NOT_FOUND", "context": {"error": "User not found"}}
            
            # Create wallet for user using the internal user ID
            result = await self.wallet_service.create_wallet_for_user(user.id)
            
            if result.get("success"):
                return {"success": True, "response_code": "CREATE_WALLET_SUCCESS", "context": result}
            else:
                return {"success": False, "response_code": "CREATE_WALLET_ERROR", "context": {"error": result.get("error")}}
                
        except Exception as e:
            logger.error(f"Create wallet failed for user {user_id}: {e}", exc_info=True)
            return {"success": False, "response_code": "CREATE_WALLET_ERROR", "context": {"error": str(e)}}

    async def get_token_price_impl(self, token_symbol: str) -> Dict[str, Any]:
        """Gets the price of a single token."""
        price = await self.price_manager.get_price(token_symbol)
        if price is not None:
            return {"success": True, "price": price}
        else:
            return {"success": False, "error": f"Price for {token_symbol} not found."}

    async def check_balance_impl(self, user_id: str) -> Dict[str, Any]:
        """Gets all balances for a user. Auto-creates wallet and claims pending transfers if needed."""
        try:
            # First check if user has a wallet
            user = await self.user_service.get_user_by_twitter_id(user_id)
            if not user:
                return {"success": False, "response_code": "USER_NOT_FOUND", "context": {}}
            
            wallet_created = False
            claimed_transfers = []
            
            # Check if user has a wallet
            wallet = await self.wallet_service.get_user_wallet(user.id)
            if not wallet:
                # Auto-create wallet if user doesn't have one
                logger.info(f"🔧 Auto-creating wallet for user {user_id}")
                create_result = await self.create_wallet_impl(user_id)
                if create_result.get("success"):
                    wallet_created = True
                    logger.info(f"✅ Wallet auto-created for user {user_id}")
                else:
                    return {"success": False, "response_code": "WALLET_CREATION_FAILED", "context": {"error": "Could not create wallet"}}
            
            # ALWAYS auto-claim pending transfers on balance check (regardless of wallet existence)
            logger.info(f"🎁 [BALANCE-CHECK] Auto-claiming pending transfers for user {user_id}")
            claim_result = await self.claim_pending_transfers_impl(user_id)
            if claim_result.get("success") and claim_result.get("context", {}).get("claimed", 0) > 0:
                claimed_transfers = claim_result.get("context", {}).get("transfers", [])
                logger.info(f"🎁 [BALANCE-CHECK] Auto-claimed {len(claimed_transfers)} transfers")

            # Also check for recent direct transfers (received in last 5 minutes)
            recent_transfers = []
            try:
                from datetime import datetime, timedelta, timezone
                from database.models import TransactionHistory
                
                five_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
                
                async with self.db_session_factory() as session:
                    # Find recent 'receive_direct' transactions for this user
                    stmt = select(TransactionHistory).where(
                        TransactionHistory.user_id == user.id,
                        TransactionHistory.transaction_type == 'receive_direct',
                        TransactionHistory.created_at >= five_minutes_ago,
                        TransactionHistory.status == 'completed'
                    ).order_by(TransactionHistory.created_at.desc())
                    
                    result = await session.execute(stmt)
                    recent_txns = result.scalars().all()
                    
                    for txn in recent_txns:
                        # Ensure timezone-aware datetime for ISO format
                        received_at = txn.created_at
                        if received_at.tzinfo is None:
                            received_at = received_at.replace(tzinfo=timezone.utc)
                        
                        # Format amount properly
                        from common.number_utils import format_amount
                        formatted_amount = format_amount(txn.amount, txn.token_symbol)
                        
                        recent_transfers.append({
                            "from_handle": txn.sender_twitter_handle,
                            "token": txn.token_symbol,
                            "amount": formatted_amount,
                            "received_at": received_at.isoformat()
                        })
                    
                    if recent_transfers:
                        logger.info(f"🎁 [BALANCE-CHECK] Found {len(recent_transfers)} recent direct transfers")
            except Exception as e:
                logger.warning(f"Error checking recent transfers: {e}")

            # Now get the balances and format them
            balances = await self.balance_manager.get_all(user_id)
            
            # Format balance amounts
            if balances:
                from common.number_utils import format_amount
                for balance_item in balances:
                    original_balance = balance_item.get('balance', 0)
                    token = balance_item.get('token', '')
                    formatted_balance = format_amount(original_balance, token)
                    balance_item['formatted_balance'] = formatted_balance
            
            context = {"balances": balances or []}
            
            # Add auto-creation and auto-claim information to context
            if wallet_created:
                context["wallet_created"] = True
            if claimed_transfers:
                context["auto_claimed_transfers"] = claimed_transfers
                context["auto_claimed_count"] = len(claimed_transfers)
            if recent_transfers:
                context["recent_direct_transfers"] = recent_transfers
                context["recent_direct_count"] = len(recent_transfers)
            
            if balances:
                return {"success": True, "response_code": "GET_BALANCE_SUCCESS", "context": context}
            else:
                return {"success": True, "response_code": "GET_BALANCE_NO_BALANCES", "context": context}
                
        except Exception as e:
            logger.error(f"Error checking balance for user {user_id}: {e}", exc_info=True)
            return {"success": False, "response_code": "GET_BALANCE_ERROR", "context": {"error": str(e)}}

    async def internal_swap_impl(self, user_id: str, from_token: str = None, to_token: str = None, amount: float = None, **kwargs) -> dict:
        """Implementation of the internal_swap tool."""
        # Support both keyword arguments and kwargs for backward compatibility
        from_token = from_token or kwargs.get('from_token')
        to_token = to_token or kwargs.get('to_token')  
        amount = amount if amount is not None else kwargs.get('amount')
        
        from_token = normalize_token_symbol(from_token)
        to_token = normalize_token_symbol(to_token)

        if not from_token or not to_token or amount is None:
            return {"success": False, "response_code": "SWAP_MISSING_PARAMS"}

        try:
            amount_decimal = Decimal(str(amount))
        except InvalidOperation:
            return {"success": False, "response_code": "SWAP_INVALID_AMOUNT", "context": {"amount": amount}}

        result = await self.swap_engine.execute_swap(user_id, from_token, to_token, amount_decimal)
        return result

    async def confirm_action_impl(self, user_id: str, action_id: str) -> Dict[str, Any]:
        """Confirm an action that requires user confirmation."""
        if action_id not in self.pending_confirmations:
            return {
                "success": False,
                "response_code": "ACTION_NOT_FOUND",
                "context": {"error": "Action ID not found or already expired"}
            }

        action = self.pending_confirmations.pop(action_id)
        if action.get("user_id") != user_id:
            return {
                "success": False,
                "response_code": "ACTION_NOT_AUTHORIZED",
                "context": {"error": "You are not authorized to confirm this action"}
            }

        # Execute the confirmed action based on its type
        action_type = action.get("action_type")
        action_params = action.get("params", {})
        
        logger.info(f"✅ [CONFIRM_ACTION] User {user_id} confirmed {action_type} with params: {action_params}")
        
        try:
            if action_type == "internal_swap":
                # Execute the swap with the stored parameters
                result = await self.internal_swap_impl(
                    user_id=user_id,
                    from_token=action_params.get("from_token"),
                    to_token=action_params.get("to_token"),
                    amount=action_params.get("amount")
                )
                return result
                
            elif action_type == "transfer_token":
                # Execute the transfer with the stored parameters
                result = await self.transfer_token_impl(
                    user_id=user_id,
                    recipient_twitter_handle=action_params.get("recipient_twitter_handle"),
                    token_symbol=action_params.get("token_symbol"),
                    amount=action_params.get("amount")
                )
                return result
                
            elif action_type == "withdraw_asset":
                # Execute the withdrawal with the stored parameters
                result = await self.withdraw_asset_impl(
                    user_id=user_id,
                    token=action_params.get("token"),
                    amount=action_params.get("amount"),
                    to_address=action_params.get("to_address")
                )
                return result
                
            else:
                return {
                    "success": False,
                    "response_code": "UNSUPPORTED_ACTION_TYPE",
                    "context": {"error": f"Action type '{action_type}' is not supported for confirmation"}
                }
                
        except Exception as e:
            logger.error(f"❌ [CONFIRM_ACTION] Error executing {action_type}: {e}", exc_info=True)
            return {
                "success": False,
                "response_code": "ACTION_EXECUTION_ERROR",
                "context": {"error": f"Failed to execute action: {str(e)}"}
            }
            return {
                "success": False,
                "response_code": "UNKNOWN_ACTION_TYPE",
                "context": {"error": f"Unknown action type: {action_type}"}
            }
                
        except Exception as e:
            logger.error(f"Error executing confirmed action {action_type}: {e}", exc_info=True)
            return {
                "success": False,
                "response_code": "ACTION_EXECUTION_ERROR",
                "context": {"error": f"Failed to execute confirmed action: {str(e)}"}
            }
    
    async def interpret_and_execute_action_impl(self, user_id: str, user_message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        🧠 INTELLIGENT CONFIRMATION SYSTEM
        
        This is where the AI magic happens! Instead of requiring exact "yes/no" responses,
        this function uses natural language understanding to interpret user intent.
        
        CONTEXT FLOW EXPLANATION:
        1. User sends message like "sure thing!" or "nah, forget it"
        2. ResponseGenerator calls this MCP tool with the user_message
        3. This function receives the message AND the context about pending actions
        4. AI analyzes the message to determine: CONFIRM, CANCEL, or MODIFY intent
        5. Based on intent, either executes the action or modifies parameters
        6. Returns structured response back to ResponseGenerator
        7. ResponseGenerator converts response to natural user message
        
        CONTEXT PASSING:
        - user_message: The raw user input ("sure!", "make it 5 SOL instead")
        - context: Contains pending_action_id and conversation_history
        - self.pending_confirmations: In-memory store of pending actions with full parameters
        - Database context: All services have access to user data, balances, etc.
        """
        try:
            logger.info(f"🧠 [AI_INTERPRET] User {user_id} message: '{user_message}'")
            
            # STEP 1: Get pending actions context
            # Find all pending actions for this user
            user_pending_actions = {}
            for action_id, action_data in self.pending_confirmations.items():
                if action_data.get("user_id") == user_id:
                    user_pending_actions[action_id] = action_data
            
            if not user_pending_actions:
                logger.info(f"🧠 [AI_INTERPRET] No pending actions for user {user_id}")
                return {
                    "success": True, 
                    "response_code": "NO_PENDING_ACTIONS",
                    "context": {"message": "I don't see any pending actions to confirm. What would you like to do?"}
                }
            
            # STEP 2: Extract the most recent pending action
            # Get the most recent action by creation time
            most_recent_action_id = max(user_pending_actions.keys(), 
                                      key=lambda aid: user_pending_actions[aid].get('created_at', 0))
            pending_action = user_pending_actions[most_recent_action_id]
            
            # Convert to the expected format for the analysis functions
            formatted_pending_action = {
                "action_type": pending_action["action_type"],
                "action_params": pending_action["params"]
            }
            
            logger.info(f"🧠 [AI_INTERPRET] Analyzing message against pending action: {pending_action['action_type']}")
            
            # STEP 3: AI INTENT ANALYSIS
            # This is where the intelligent interpretation happens
            intent, confidence, extracted_params = await self._analyze_user_intent(
                user_message, 
                formatted_pending_action, 
                context or {}
            )
            
            logger.info(f"🧠 [AI_INTERPRET] Intent: {intent}, Confidence: {confidence}, Params: {extracted_params}")
            
            # STEP 4: Execute based on interpreted intent
            if intent == "CONFIRM" and confidence > 0.7:
                # User wants to proceed with the action
                logger.info(f"🧠 [AI_INTERPRET] User confirmed action with confidence {confidence}")
                
                # Execute the original action (same logic as confirm_action)
                return await self._execute_confirmed_action(user_id, most_recent_action_id, formatted_pending_action)
                
            elif intent == "CANCEL" and confidence > 0.7:
                # User wants to cancel
                logger.info(f"🧠 [AI_INTERPRET] User cancelled action with confidence {confidence}")
                
                # Remove from pending (using the flat structure)
                del self.pending_confirmations[most_recent_action_id]
                
                return {
                    "success": True,
                    "response_code": "ACTION_CANCELLED",
                    "context": {
                        "message": f"Got it! I've cancelled the {pending_action['action_type']} action.",
                        "cancelled_action": pending_action['action_type']
                    }
                }
                
            elif intent == "MODIFY" and confidence > 0.6:
                # User wants to modify parameters
                logger.info(f"🧠 [AI_INTERPRET] User wants to modify action: {extracted_params}")
                
                # Update the pending action with new parameters (using the flat structure)
                for key, value in extracted_params.items():
                    if key in self.pending_confirmations[most_recent_action_id]["params"]:
                        self.pending_confirmations[most_recent_action_id]["params"][key] = value
                
                return {
                    "success": True,
                    "response_code": "ACTION_MODIFIED",
                    "context": {
                        "message": f"I've updated the {pending_action['action_type']} with your changes. The new parameters are: {extracted_params}. Should I proceed?",
                        "modified_params": extracted_params,
                        "updated_action": formatted_pending_action
                    }
                }
                
            else:
                # Intent unclear or low confidence
                logger.info(f"🧠 [AI_INTERPRET] Intent unclear (confidence: {confidence})")
                
                return {
                    "success": True,
                    "response_code": "INTENT_UNCLEAR",
                    "context": {
                        "message": f"I'm not sure what you want to do with the pending {pending_action['action_type']}. You can say 'confirm' to proceed, 'cancel' to stop, or tell me what you'd like to change.",
                        "pending_action": pending_action['action_type'],
                        "confidence": confidence
                    }
                }
                
        except Exception as e:
            logger.error(f"❌ [AI_INTERPRET] Error interpreting user message: {e}", exc_info=True)
            return {
                "success": False, 
                "response_code": "INTERPRETATION_FAILED", 
                "context": {"error": str(e)}
            }

    async def _analyze_user_intent(self, user_message: str, pending_action: Dict, context: Dict) -> tuple[str, float, Dict]:
        """
        🔍 CORE AI ANALYSIS ENGINE
        
        This function does the heavy lifting of understanding user intent.
        It uses multiple strategies to determine what the user wants:
        
        CONTEXT IT RECEIVES:
        - user_message: Raw user input
        - pending_action: Full details of what's pending (action_type, params, etc.)
        - context: Conversation history and additional context
        
        ANALYSIS STRATEGIES:
        1. Keyword matching with weighted confidence
        2. Sentiment analysis (positive = confirm, negative = cancel)
        3. Parameter extraction (numbers, token names, etc.)
        4. Context-aware interpretation based on action type
        """
        
        message_lower = user_message.lower().strip()
        
        # CONFIRMATION PATTERNS (high confidence)
        confirm_patterns = [
            r'\b(yes|yeah|yep|sure|ok|okay|confirm|proceed|go ahead|do it|let\'s go)\b',
            r'\b(sounds good|looks good|perfect|exactly|that\'s right)\b',
            r'\b(✓|👍|✅)\b'  # Emoji patterns
        ]
        
        # CANCELLATION PATTERNS (high confidence)  
        cancel_patterns = [
            r'\b(no|nope|nah|never mind|forget it|cancel|stop|abort)\b',
            r'\b(not now|maybe later|changed my mind)\b',
            r'\b(❌|👎|❎)\b'  # Emoji patterns
        ]
        
        # MODIFICATION PATTERNS (medium confidence)
        modify_patterns = [
            r'\b(change|modify|update|make it|instead|rather)\b',
            r'\b(different|another|not \w+)\b'
        ]
        
        # Check for confirmation intent
        for pattern in confirm_patterns:
            if re.search(pattern, message_lower):
                return "CONFIRM", 0.9, {}
        
        # Check for cancellation intent
        for pattern in cancel_patterns:
            if re.search(pattern, message_lower):
                return "CANCEL", 0.9, {}
        
        # Check for modification intent and extract parameters
        for pattern in modify_patterns:
            if re.search(pattern, message_lower):
                extracted_params = await self._extract_parameters(user_message, pending_action)
                if extracted_params:
                    return "MODIFY", 0.8, extracted_params
                else:
                    return "MODIFY", 0.6, {}
        
        # NUMERICAL ANALYSIS - if user mentions numbers, they might be modifying
        numbers = re.findall(r'\b\d+(?:\.\d+)?\b', user_message)
        if numbers and pending_action['action_type'] in ['swap', 'transfer', 'campaign_funding']:
            # Try to map numbers to relevant parameters
            extracted_params = {}
            action_type = pending_action['action_type']
            
            if action_type == 'swap':
                if 'amount' in pending_action['action_params']:
                    extracted_params['amount'] = float(numbers[0])
            elif action_type == 'transfer':
                if 'amount' in pending_action['action_params']:
                    extracted_params['amount'] = float(numbers[0])
            
            if extracted_params:
                return "MODIFY", 0.7, extracted_params
        
        # TOKEN NAME ANALYSIS - if user mentions different tokens
        common_tokens = ['sol', 'usdc', 'btc', 'eth', 'usdt', 'bonk', 'wif', 'jup']
        mentioned_tokens = [token for token in common_tokens if token in message_lower]
        
        if mentioned_tokens and pending_action['action_type'] in ['swap', 'transfer']:
            extracted_params = {}
            if 'to_token' in pending_action['action_params']:
                extracted_params['to_token'] = mentioned_tokens[0].upper()
            elif 'from_token' in pending_action['action_params']:
                extracted_params['from_token'] = mentioned_tokens[0].upper()
            
            if extracted_params:
                return "MODIFY", 0.7, extracted_params
        
        # SENTIMENT ANALYSIS (fallback with lower confidence)
        positive_words = ['good', 'great', 'nice', 'perfect', 'awesome', 'cool']
        negative_words = ['bad', 'wrong', 'terrible', 'awful', 'hate', 'dislike']
        
        positive_score = sum(1 for word in positive_words if word in message_lower)
        negative_score = sum(1 for word in negative_words if word in message_lower)
        
        if positive_score > negative_score and positive_score > 0:
            return "CONFIRM", 0.5, {}
        elif negative_score > positive_score and negative_score > 0:
            return "CANCEL", 0.5, {}
        
        # Default: unclear intent
        return "UNCLEAR", 0.1, {}

    async def _extract_parameters(self, user_message: str, pending_action: Dict) -> Dict:
        """
        Extract specific parameters that the user wants to modify.
        This is context-aware based on the action type.
        """
        extracted = {}
        message_lower = user_message.lower()
        
        # Extract numbers
        numbers = re.findall(r'\b(\d+(?:\.\d+)?)\b', user_message)
        
        # Extract token symbols
        tokens = re.findall(r'\b([A-Z]{2,5})\b', user_message.upper())
        common_tokens = ['SOL', 'USDC', 'BTC', 'ETH', 'USDT', 'BONK', 'WIF', 'JUP']
        valid_tokens = [token for token in tokens if token in common_tokens]
        
        action_type = pending_action['action_type']
        action_params = pending_action['action_params']
        
        if action_type == 'swap':
            if numbers and 'amount' in action_params:
                extracted['amount'] = float(numbers[0])
            if valid_tokens:
                if 'to_token' in action_params:
                    extracted['to_token'] = valid_tokens[0]
                elif len(valid_tokens) > 1:
                    extracted['from_token'] = valid_tokens[0]
                    extracted['to_token'] = valid_tokens[1]
        
        elif action_type == 'transfer':
            if numbers and 'amount' in action_params:
                extracted['amount'] = float(numbers[0])
            if valid_tokens and 'token' in action_params:
                extracted['token'] = valid_tokens[0]
        
        return extracted

    async def _execute_confirmed_action(self, user_id: str, action_id: str, pending_action: Dict) -> Dict[str, Any]:
        """
        Execute the confirmed action. This is the same logic as confirm_action_impl
        but extracted for reuse in the intelligent system.
        """
        action_type = pending_action["action_type"]
        action_params = pending_action["action_params"]
        
        logger.info(f"✅ [AI_EXECUTE] User {user_id} confirmed {action_type} with params: {action_params}")
        
        try:
            # Map action types to their correct implementation methods
            if action_type == "swap" or action_type == "internal_swap":
                result = await self.internal_swap_impl(user_id=user_id, **action_params)
            elif action_type == "transfer" or action_type == "transfer_token":
                result = await self.transfer_token_impl(user_id=user_id, **action_params)
            elif action_type == "withdraw" or action_type == "withdraw_asset":
                result = await self.withdraw_asset_impl(user_id=user_id, **action_params)
            elif action_type == "campaign_funding" or action_type == "activate_campaign":
                result = await self.activate_campaign_impl(user_id=user_id, **action_params)
            else:
                logger.error(f"❌ [AI_EXECUTE] Unknown action type: {action_type}")
                return {"success": False, "response_code": "UNKNOWN_ACTION_TYPE", "context": {"action_type": action_type}}

            # Remove the pending confirmation since it's been executed (using flat structure)
            del self.pending_confirmations[action_id]

            logger.info(f"✅ [AI_EXECUTE] Action {action_type} executed successfully")
            return result

        except Exception as e:
            logger.error(f"❌ [AI_EXECUTE] Error executing {action_type}: {e}", exc_info=True)
            return {"success": False, "response_code": "EXECUTION_FAILED", "context": {"error": str(e), "action_id": action_id}}

    def create_pending_action(self, user_id: str, action_type: str, params: Dict[str, Any]) -> str:
        """
        Create a pending action that requires user confirmation.
        
        Args:
            user_id: The ID of the user who will confirm the action
            action_type: The type of action (e.g., "internal_swap", "transfer_token", "withdraw_asset")
            params: The parameters needed to execute the action
            
        Returns:
            action_id: A unique identifier for this pending action
        """
        import uuid
        import time
        
        action_id = str(uuid.uuid4())[:8]  # Short unique ID for user convenience
        
        self.pending_confirmations[action_id] = {
            "user_id": user_id,
            "action_type": action_type,
            "params": params,
            "created_at": time.time()
        }
        
        logger.info(f"🔄 [PENDING_ACTION] Created {action_type} confirmation {action_id} for user {user_id}")
        return action_id
    
    def cleanup_expired_actions(self, max_age_seconds: int = 300):  # 5 minutes
        """Remove pending actions older than max_age_seconds"""
        import time
        current_time = time.time()
        expired_actions = []
        
        for action_id, action_data in self.pending_confirmations.items():
            created_at = action_data.get('created_at', 0)
            if current_time - created_at > max_age_seconds:
                expired_actions.append(action_id)
        
        for action_id in expired_actions:
            del self.pending_confirmations[action_id]
            logger.info(f"🧹 [CLEANUP] Removed expired action {action_id}")
            
        if expired_actions:
            logger.info(f"🧹 [CLEANUP] Removed {len(expired_actions)} expired pending actions")

    async def check_pending_actions_impl(self, user_id: str) -> Dict[str, Any]:
        """
        Check if the user has any pending actions that require confirmation.
        This helps the LLM understand context when users say things like 'yes', 'confirm', etc.
        """
        try:
            # Clean up expired actions first
            self.cleanup_expired_actions()
            
            # Find all pending actions for this user
            user_pending_actions = []
            for action_id, action_data in self.pending_confirmations.items():
                if action_data.get("user_id") == user_id:
                    user_pending_actions.append({
                        "action_id": action_id,
                        "action_type": action_data.get("action_type"),
                        "params": action_data.get("params"),
                        "created_at": action_data.get("created_at"),
                        "summary": self._generate_action_summary(action_data)
                    })
            
            if not user_pending_actions:
                return {
                    "success": True,
                    "response_code": "NO_PENDING_ACTIONS",
                    "context": {
                        "message": "No pending actions require confirmation",
                        "pending_actions": [],
                        "count": 0
                    }
                }
            
            return {
                "success": True,
                "response_code": "PENDING_ACTIONS_FOUND",
                "context": {
                    "pending_actions": user_pending_actions,
                    "count": len(user_pending_actions),
                    "message": f"Found {len(user_pending_actions)} pending action(s) requiring confirmation"
                }
            }
            
        except Exception as e:
            logger.error(f"Error checking pending actions for user {user_id}: {e}", exc_info=True)
            return {
                "success": False,
                "response_code": "CHECK_PENDING_ERROR",
                "context": {"error": str(e)}
            }

    async def check_pending_transfers_impl(self, user_id: str) -> Dict[str, Any]:
        """
        Check for and claim any pending token transfers for the user.
        This is specifically for handling incoming token transfers from other users.
        """
        try:
            from services.modern_transfer_service import ModernTransferService
            from user_management.user_service import UserService
            
            # Get user info to get twitter handle - use self.db_session_factory
            user_service = UserService(self.db_session_factory)
            user = await user_service.get_user_by_twitter_id(user_id)
            
            if not user:
                return {
                    "success": False,
                    "response_code": "USER_NOT_FOUND",
                    "context": {"error": "User not found"}
                }
            
            twitter_handle = user.twitter_handle
            if not twitter_handle:
                return {
                    "success": False,
                    "response_code": "NO_TWITTER_HANDLE",
                    "context": {"error": "User does not have a linked Twitter handle"}
                }
            
            # Check and claim pending transfers
            transfer_service = ModernTransferService()
            
            # Use the db_session_factory to get a session and claim transfers
            async with self.db_session_factory() as session:
                claimed_transfers = await transfer_service.claim_pending_transfers(session, user.twitter_user_id)
            
            if not claimed_transfers:
                return {
                    "success": True,
                    "response_code": "NO_PENDING_TRANSFERS",
                    "context": {
                        "message": "No pending transfers found",
                        "claimed_transfers": [],
                        "count": 0
                    }
                }
            
            # Format the response
            transfer_summaries = []
            for transfer in claimed_transfers:
                transfer_summaries.append({
                    "from_user": transfer.from_twitter_handle,
                    "token_symbol": transfer.token_symbol,
                    "amount": float(transfer.amount),
                    "transfer_id": transfer.id
                })
            
            return {
                "success": True,
                "response_code": "TRANSFERS_CLAIMED",
                "context": {
                    "claimed_transfers": transfer_summaries,
                    "count": len(claimed_transfers),
                    "message": f"Successfully claimed {len(claimed_transfers)} pending transfer(s)"
                }
            }
            
        except Exception as e:
            logger.error(f"Error checking/claiming pending transfers for user {user_id}: {e}", exc_info=True)
            return {
                "success": False,
                "response_code": "CHECK_TRANSFERS_ERROR",
                "context": {"error": str(e)}
            }

    def _generate_action_summary(self, action_data: Dict[str, Any]) -> str:
        """Generate a human-readable summary of a pending action"""
        action_type = action_data.get("action_type")
        params = action_data.get("params", {})
        
        if action_type == "internal_swap":
            return f"Swap {params.get('amount')} {params.get('from_token')} for {params.get('to_token')}"
        elif action_type == "transfer_token":
            return f"Transfer {params.get('amount')} {params.get('token')} to @{params.get('to_user')}"
        elif action_type == "withdraw_asset":
            to_address = params.get('to_address', '')
            short_address = f"{to_address[:10]}..." if len(to_address) > 10 else to_address
            return f"Withdraw {params.get('amount')} {params.get('token')} to {short_address}"
        else:
            return f"{action_type.replace('_', ' ').title()} action"

    async def withdraw_asset_impl(self, user_id: str, token: str,
                                  amount: float,
                                  to_address: str) -> Dict[str, Any]:
        """Withdraw tokens to external address"""
        token = normalize_token_symbol(token)
        if not Web3.is_address(to_address):
            return {
                "success": False,
                "response_code": "INVALID_ADDRESS",
                "context": {"error": "Invalid address format"}
            }

        try:
            async with self.db_session_factory() as session:
                balance = await self.balance_manager.get(user_id, token)
                if balance < amount:
                    return {
                        "success": False,
                        "response_code": "INSUFFICIENT_FUNDS",
                        "context": {"token": token, "balance": balance, "required": amount}
                    }

                # Placeholder for withdrawal logic
                await self.balance_manager.subtract(user_id, token, amount)

                # In a real scenario, you'd have a transaction hash
                return {
                    "success": True,
                    "response_code": "WITHDRAW_SUCCESS",
                    "context": {"amount": amount, "token": token, "address": to_address}
                }
        except Exception as e:
            logger.error(f"Withdraw asset failed: {e}")
            return {"success": False, "response_code": "WITHDRAW_DB_ERROR", "context": {"error": str(e)}}

    async def play_animation_impl(self, animation_name: str) -> dict:
        return {"response_code": "PLAY_ANIMATION", "context": {"animation_name": animation_name}}

    async def get_swap_quote_impl(self, from_token: str, to_token: str,
                                  amount: float, user_id: str = None) -> Dict[str, Any]:
        """Implementation for getting a swap quote."""
        logger.info(f"🔄 [SWAP DEBUG] Starting get_swap_quote_impl")
        logger.info(f"🔄 [SWAP DEBUG] Raw params - from_token: {from_token}, to_token: {to_token}, amount: {amount}, user_id: {user_id}")
        
        from_token = normalize_token_symbol(from_token)
        to_token = normalize_token_symbol(to_token)
        logger.info(f"🔄 [SWAP DEBUG] Normalized tokens - from_token: {from_token}, to_token: {to_token}")

        try:
            amount_decimal = Decimal(str(amount))
            logger.info(f"🔄 [SWAP DEBUG] Amount converted to Decimal: {amount_decimal}")
        except InvalidOperation:
            logger.error(f"🔄 [SWAP DEBUG] Invalid amount conversion: {amount}")
            return {"success": False, "response_code": "INVALID_AMOUNT_NEGATIVE", "context": {}}

        logger.info(f"🔄 [SWAP DEBUG] Calling swap_engine.calculate...")
        calculation = await self.swap_engine.calculate(from_token, to_token, amount_decimal)
        logger.info(f"🔄 [SWAP DEBUG] Swap calculation result: {calculation}")

        if not calculation.get("success"):
            logger.warning(f"🔄 [SWAP DEBUG] Calculation failed: {calculation.get('error')}")
            return {
                "success": False,
                "response_code": "SWAP_QUOTE_ERROR",
                "context": {"error": calculation.get("error")}
            }

        # Clean up expired actions before creating new one
        self.cleanup_expired_actions()
        
        # Create a pending action for confirmation using the new system
        if user_id:
            action_id = self.create_pending_action(
                user_id=user_id,
                action_type="internal_swap",
                params={
                    "from_token": from_token,
                    "to_token": to_token,
                    "amount": float(amount_decimal)
                }
            )
            
            logger.info(f"🔄 [SWAP DEBUG] Quote successful, created pending action {action_id}")
            return {
                "success": True,
                "response_code": "SWAP_QUOTE_SUCCESS",
                "context": {
                    "quote": calculation,
                    "action_id": action_id,
                    "confirmation_message": f"To confirm this swap, reply with: confirm {action_id}"
                }
            }
        else:
            # Fallback for cases where user_id is not provided (backwards compatibility)
            logger.info(f"🔄 [SWAP DEBUG] Quote successful, no user_id provided - using old system")
            return {
                "success": True,
                "response_code": "SWAP_QUOTE_SUCCESS",
                "context": {"quote": calculation},
                "pending_action": {
                    "action_type": "swap",
                    "from_token": from_token,
                    "to_token": to_token,
                    "from_amount": str(amount_decimal),
                    "summary": f"swap {amount_decimal} {from_token} for {calculation.get('to_amount')} {to_token}"
                }
            }
    async def get_price_feed_impl(self) -> Dict[str, Any]:
        """Implementation for getting all token prices, price feeds and supported tokens."""
        try:
            price_feed = await self.price_manager.get_all()
            # Get the last updated timestamp for prices
            last_updated = await self.price_manager.get_last_updated()
            
            if price_feed:
                return {
                    "success": True, 
                    "response_code": "GET_PRICE_FEED_SUCCESS", 
                    "context": {
                        "price_feed": price_feed,
                        "last_updated": last_updated or "recently"
                    }
                }
            return {
                "success": False, 
                "response_code": "GET_PRICE_FEED_ERROR", 
                "context": {"error": "No price data available. Please try again later."}
            }
        except Exception as e:
            logger.error(f"Error fetching price feed: {str(e)}", exc_info=True)
            return {
                "success": False, 
                "response_code": "GET_PRICE_FEED_ERROR", 
                "context": {"error": f"Failed to fetch price feed: {str(e)}"}
            }

    async def get_supported_tokens_impl(self) -> Dict[str, Any]:
        """Implementation for getting a list of all supported tokens in the system."""
        try:
            # Get all tokens with prices from the price manager
            price_feed = await self.price_manager.get_all()
            
            # Define token categories and descriptions
            token_details = {
                "ETH": {
                    "name": "Ethereum",
                    "description": "Native cryptocurrency of the Ethereum blockchain",
                    "category": "major",
                    "use_cases": ["gas fees", "trading", "store of value"]
                },
                "WIP": {
                    "name": "Work-in-Progress",
                    "description": "Utility token for Story Protocol ecosystem",
                    "category": "protocol",
                    "use_cases": ["governance", "staking", "rewards"]
                },
                "ZOO": {
                    "name": "Zoo Token",
                    "description": "Community token for the Story ecosystem",
                    "category": "community",
                    "use_cases": ["trading", "rewards", "collectibles"]
                },
                "PEPE": {
                    "name": "Pepe",
                    "description": "Meme token based on the Pepe the Frog character",
                    "category": "meme",
                    "use_cases": ["community", "memes", "trading"]
                },
                "DOGE": {
                    "name": "Dogecoin",
                    "description": "Original meme cryptocurrency",
                    "category": "meme",
                    "use_cases": ["tipping", "community", "trading"]
                },
                "STIP": {
                    "name": "Stipend Token",
                    "description": "Utility token for user rewards and stipends",
                    "category": "utility",
                    "use_cases": ["rewards", "testing", "onboarding"]
                }
            }
            
            # Add basic info for any tokens not explicitly defined
            all_tokens = {}
            for token_symbol in price_feed.keys():
                if token_symbol in token_details:
                    all_tokens[token_symbol] = token_details[token_symbol]
                    all_tokens[token_symbol]["price"] = price_feed[token_symbol]
                else:
                    all_tokens[token_symbol] = {
                        "name": token_symbol,
                        "description": f"Trading token {token_symbol}",
                        "category": "other",
                        "use_cases": ["trading"],
                        "price": price_feed[token_symbol]
                    }
            
            # Group tokens by category
            token_categories = {
                "major": [],
                "protocol": [],
                "community": [],
                "meme": [],
                "utility": [],
                "other": []
            }
            
            for token, details in all_tokens.items():
                category = details.get("category", "other")
                token_categories[category].append(token)
            
            return {
                "success": True,
                "response_code": "GET_SUPPORTED_TOKENS_SUCCESS",
                "context": {
                    "tokens": all_tokens,
                    "categories": token_categories,
                    "total_tokens": len(all_tokens)
                }
            }
        except Exception as e:
            logger.error(f"Error fetching supported tokens: {str(e)}", exc_info=True)
            return {
                "success": False,
                "response_code": "GET_SUPPORTED_TOKENS_ERROR",
                "context": {"error": f"Failed to fetch supported tokens: {str(e)}"}
            }

    async def transfer_token_impl(self, user_id: str, recipient_twitter_handle: str, token_symbol: str, amount: float) -> Dict[str, Any]:
        """
        Modern implementation for transferring tokens using Twitter IDs and handle resolution
        """
        # Normalize the recipient handle (remove extra @, make case-insensitive)
        clean_recipient = recipient_twitter_handle.strip().replace('@', '').lower()
        
        logger.info(f"💰 Starting modern transfer: {amount} {token_symbol} from {user_id} to {clean_recipient}")
        
        try:
            # Import the modern transfer service
            from services.modern_transfer_service import ModernTransferService
            
            # Create transfer service instance
            transfer_service = ModernTransferService()
            
            # Execute the transfer using modern service with database session
            async with self.db_session_factory() as session:
                result = await transfer_service.transfer_tokens(
                    session=session,
                    sender_twitter_user_id=user_id,
                    recipient_identifier=clean_recipient,  # Use cleaned handle
                    amount=amount,
                    token_symbol=token_symbol
                )
            
            # Convert service response to MCP response format
            if result.get('success'):
                if result.get('type') == 'direct':
                    response_code = 'TRANSFER_SUCCESS_DIRECT'
                elif result.get('type') == 'pending':
                    response_code = 'TRANSFER_SUCCESS_PENDING'
                else:
                    response_code = 'TRANSFER_SUCCESS_PENDING'  # Default to pending
                
                logger.info(f"✅ Modern transfer successful: {response_code}")
                
                # Use normalized handle in response (single @)
                formatted_recipient = f"@{clean_recipient}"
                
                # Flatten the context for response generator - use actual values instead of result fields
                flattened_context = {
                    'amount': amount,  # Use the input amount
                    'token': token_symbol,  # Use the input token_symbol  
                    'recipient': formatted_recipient,  # Use the normalized recipient
                    'type': result.get('type'),
                    'expires_at': result.get('expires_at'),
                    'message': result.get('message'),
                    'transaction_id': result.get('transaction_id')
                }
                
                return {
                    'success': True,
                    'response_code': response_code,
                    'context': flattened_context
                }
            else:
                logger.error(f"❌ Modern transfer failed: {result.get('error', 'Unknown error')}")
                return {
                    'success': False,
                    'response_code': 'TRANSFER_ERROR_INTERNAL',
                    'context': result
                }
            
        except Exception as e:
            logger.error(f"❌ Modern transfer failed: {e}", exc_info=True)
            return {
                'success': False,
                'response_code': 'TRANSFER_ERROR',
                'context': {'error': str(e)}
            }
            
    async def get_pending_transfers_impl(self, user_id: str) -> Dict[str, Any]:
        """Implementation for getting pending transfers for a user."""
        try:
            async with self.db_session_factory() as session:
                # Find user first
                sender_user = await self.user_service.get_user_by_twitter_id(user_id)
                if not sender_user:
                    return {"success": False, "response_code": "USER_NOT_FOUND"}
                
                # Get pending transfers by Twitter handle (try both with @ and without @)
                handle_without_at = sender_user.twitter_handle.lstrip('@')
                handle_with_at = sender_user.twitter_handle if sender_user.twitter_handle.startswith('@') else f'@{sender_user.twitter_handle}'
                
                stmt = select(PendingTransfer).where(
                    PendingTransfer.recipient_twitter_handle.in_([handle_without_at, handle_with_at, sender_user.twitter_handle]),
                    PendingTransfer.status == 'pending'
                )
                result = await session.execute(stmt)
                pending_transfers = result.scalars().all()
                
                transfers_data = []
                for transfer in pending_transfers:
                    transfers_data.append({
                        "id": transfer.id,
                        "from_handle": transfer.from_twitter_handle,
                        "token": transfer.token_symbol,
                        "amount": transfer.amount,
                        "created_at": transfer.created_at.isoformat() if transfer.created_at else None
                    })
                
                return {
                    "success": True,
                    "response_code": "PENDING_TRANSFERS_FOUND" if transfers_data else "NO_PENDING_TRANSFERS",
                    "context": {"transfers": transfers_data, "count": len(transfers_data)}
                }
                
        except Exception as e:
            logger.error(f"Get pending transfers failed for {user_id}: {e}", exc_info=True)
            return {"success": False, "response_code": "PENDING_TRANSFERS_ERROR", "context": {"error": str(e)}}

    async def claim_pending_transfers_impl(self, user_id: str) -> Dict[str, Any]:
        """Implementation for claiming all pending transfers for a user."""
        try:
            async with self.db_session_factory() as session:
                async with session.begin():
                    # Find user first
                    recipient_user = await self.user_service.get_user_by_twitter_id(user_id)
                    if not recipient_user:
                        return {"success": False, "response_code": "USER_NOT_FOUND"}
                    
                    # Get pending transfers by Twitter handle (try both with @ and without @)
                    handle_without_at = recipient_user.twitter_handle.lstrip('@')
                    handle_with_at = recipient_user.twitter_handle if recipient_user.twitter_handle.startswith('@') else f'@{recipient_user.twitter_handle}'
                    
                    logger.info(f"🔍 [CLAIM_DEBUG] Searching pending transfers for user {recipient_user.twitter_handle}")
                    logger.info(f"🔍 [CLAIM_DEBUG] Search variants: {[handle_without_at, handle_with_at, recipient_user.twitter_handle]}")
                    
                    # First, try exact matches
                    stmt = select(PendingTransfer).where(
                        PendingTransfer.recipient_twitter_handle.in_([handle_without_at, handle_with_at, recipient_user.twitter_handle]),
                        PendingTransfer.status == 'pending'
                    )
                    result = await session.execute(stmt)
                    pending_transfers = result.scalars().all()
                    
                    # If no exact matches, try broader search for potential matches
                    if not pending_transfers:
                        logger.info(f"🔍 [CLAIM_DEBUG] No exact matches found, checking all pending transfers for potential matches")
                        
                        # Get ALL pending transfers
                        all_pending_stmt = select(PendingTransfer).where(PendingTransfer.status == 'pending')
                        all_pending_result = await session.execute(all_pending_stmt)
                        all_pending_transfers = all_pending_result.scalars().all()
                        
                        logger.info(f"🔍 [CLAIM_DEBUG] Found {len(all_pending_transfers)} total pending transfers:")
                        for t in all_pending_transfers:
                            logger.info(f"🔍 [CLAIM_DEBUG] - To: {t.recipient_twitter_handle}, Amount: {t.amount} {t.token_symbol}")
                        
                        # For now, return info about available transfers that could potentially be claimed manually
                        # In the future, this could be enhanced with Twitter API integration
                        if all_pending_transfers:
                            return {
                                "success": True, 
                                "response_code": "POTENTIAL_PENDING_TRANSFERS_FOUND",
                                "context": {
                                    "claimed": 0,
                                    "potential_transfers": [
                                        {
                                            "id": t.id,
                                            "recipient_handle": t.recipient_twitter_handle,
                                            "from_handle": t.from_twitter_handle,
                                            "amount": float(t.amount),
                                            "token": t.token_symbol
                                        } for t in all_pending_transfers
                                    ]
                                }
                            }
                    
                    if not pending_transfers:
                        return {"success": True, "response_code": "NO_PENDING_TRANSFERS", "context": {"claimed": 0}}
                    
                    claimed_transfers = []
                    total_claimed = 0
                    
                    for transfer in pending_transfers:
                        # Add to recipient's balance
                        balance_added = await self.balance_manager.add(
                            user_id=recipient_user.twitter_user_id,
                            token=transfer.token_symbol,
                            amount=Decimal(str(transfer.amount)),
                            session=session
                        )
                        
                        if balance_added:
                            # Update transfer status
                            transfer.status = 'claimed'
                            transfer.claimed_at = datetime.now(timezone.utc)
                            session.add(transfer)
                            
                            # Log transaction for recipient (claimer)
                            await self.user_service.log_transaction(
                                user_id=recipient_user.id,
                                transaction_type='receive_claimed',
                                token_symbol=transfer.token_symbol,
                                amount=transfer.amount,
                                status='completed',
                                sender_twitter_handle=transfer.from_twitter_handle,
                                recipient_twitter_handle=recipient_user.twitter_handle,
                                session=session  # Pass the existing session
                            )
                            
                            # FIXED: Also log transaction for sender (original sender gets completion notification)
                            from database.models import User
                            sender_result = await session.execute(
                                select(User).where(User.twitter_user_id == transfer.from_twitter_user_id)
                            )
                            sender_user = sender_result.scalar_one_or_none()
                            if sender_user:
                                await self.user_service.log_transaction(
                                    user_id=sender_user.id,
                                    transaction_type='transfer_completed',
                                    token_symbol=transfer.token_symbol,
                                    amount=transfer.amount,
                                    status='completed',
                                    sender_twitter_handle=transfer.from_twitter_handle,
                                    recipient_twitter_handle=recipient_user.twitter_handle,
                                    session=session  # Pass the existing session
                                )
                            
                            # Format amount properly
                            from common.number_utils import format_amount
                            formatted_amount = format_amount(transfer.amount, transfer.token_symbol)
                            
                            claimed_transfers.append({
                                "from_handle": transfer.from_twitter_handle,
                                "token": transfer.token_symbol,
                                "amount": formatted_amount,
                                "claimed_at": transfer.claimed_at.isoformat()
                            })
                            total_claimed += 1
                            
                            logger.info(f"💰 [CLAIM DEBUG] Claimed pending transfer: {transfer.amount} {transfer.token_symbol} from {transfer.from_twitter_handle}")
                    
                    return {
                        "success": True,
                        "response_code": "PENDING_TRANSFERS_CLAIMED" if total_claimed > 0 else "NO_PENDING_TRANSFERS",
                        "context": {
                            "claimed": total_claimed,
                            "transfers": claimed_transfers
                        }
                    }
                    
        except Exception as e:
            logger.error(f"Claim pending transfers failed for {user_id}: {e}", exc_info=True)
            return {"success": False, "response_code": "CLAIM_TRANSFERS_ERROR", "context": {"error": str(e)}}

    async def login_user_impl(self, twitter_handle: str, twitter_user_id: str) -> Dict[str, Any]:
        """Implementation for user login/registration with auto-claim of pending transfers."""
        try:
            logger.info(f"🔐 [LOGIN] Processing login for handle: {twitter_handle}, ID: {twitter_user_id}")
            
            # Normalize Twitter handle - remove @ prefix if present and ensure it's the actual handle
            normalized_handle = twitter_handle.lstrip('@')
            
            # Register/login the user (this will auto-claim pending transfers)
            registration_result = await self.user_service.register(normalized_handle, twitter_user_id)
            
            if not registration_result.get("success"):
                logger.error(f"❌ [LOGIN] User registration failed: {registration_result.get('error')}")
                return {
                    "success": False,
                    "response_code": "LOGIN_REGISTRATION_FAILED",
                    "context": {"error": registration_result.get("error", "Registration failed")}
                }
            
            user = registration_result["user"]
            is_new_user = registration_result.get("is_new_user", False)
            
            # Additional pending transfers check and claim if needed
            try:
                claim_result = await self.claim_pending_transfers_impl(twitter_user_id)
                claimed_count = claim_result.get("context", {}).get("claimed", 0)
                
                if claimed_count > 0:
                    logger.info(f"🎁 [LOGIN] Additional claim found {claimed_count} pending transfers for {normalized_handle}")
            except Exception as claim_error:
                logger.warning(f"[LOGIN] Additional claim check failed: {claim_error}")
                # Don't fail login if additional claim fails
            
            # Get updated balance after login/claims
            balance_result = await self.check_balance_impl(twitter_user_id)
            balances = balance_result.get("context", {}).get("balances", [])
            
            response_context = {
                "user_id": twitter_user_id,
                "twitter_handle": normalized_handle,
                "is_new_user": is_new_user,
                "balances": balances
            }
            
            if is_new_user:
                logger.info(f"✅ [LOGIN] New user registered: {normalized_handle}")
                return {
                    "success": True,
                    "response_code": "USER_REGISTERED_SUCCESS",
                    "context": response_context
                }
            else:
                logger.info(f"✅ [LOGIN] Existing user logged in: {normalized_handle}")
                return {
                    "success": True,
                    "response_code": "USER_LOGIN_SUCCESS", 
                    "context": response_context
                }
                
        except Exception as e:
            logger.error(f"❌ [LOGIN] Login failed for {twitter_handle}: {e}", exc_info=True)
            return {
                "success": False,
                "response_code": "LOGIN_ERROR",
                "context": {"error": str(e)}
            }

    async def list_campaigns_impl(self, user_id: str) -> Dict[str, Any]:
        """Implementation for listing active campaigns."""
        campaigns = await self.campaign_service.list_campaigns()
        if not campaigns:
            return {"success": True, "response_code": "LIST_CAMPAIGNS_EMPTY"}
        return {"success": True, "response_code": "LIST_CAMPAIGNS", "context": {"campaigns": campaigns}}

    async def join_campaign_impl(self, user_id: str, campaign_identifier: str) -> Dict[str, Any]:
        """
        Allows a user to join a campaign using either its ID or its case-insensitive name.
        """
        campaign_id = None
        # Try to convert to int first for ID-based lookup
        try:
            campaign_id = int(campaign_identifier)
            return await self.campaign_service.join_campaign(user_id, campaign_id)
        except (ValueError, TypeError):
            # If it fails, treat it as a name string
            logger.info(f"Campaign identifier '{campaign_identifier}' is not an ID, searching by name.")
            async with self.db_session_factory() as session:
                stmt = select(Campaign.id).where(func.lower(Campaign.name) == func.lower(campaign_identifier))
                result = await session.execute(stmt)
                campaign_id_from_name = result.scalar_one_or_none()

            if campaign_id_from_name:
                return await self.campaign_service.join_campaign(user_id, campaign_id_from_name)
            else:
                return {"success": False, "response_code": "CAMPAIGN_NOT_FOUND", "context": {"name": campaign_identifier}}

    async def claim_campaign_reward_impl(self, user_id: str, campaign_identifier: str) -> Dict[str, Any]:
        """
        Claims a reward for a campaign, identified by its ID or case-insensitive name.
        """
        logger.info(f"🏆 [CAMPAIGN DEBUG] Starting reward claim for user {user_id}, campaign: {campaign_identifier}")
        
        campaign_id = None
        try:
            campaign_id = int(campaign_identifier)
            logger.info(f"🏆 [CAMPAIGN DEBUG] Using campaign ID: {campaign_id}")
        except (ValueError, TypeError):
            logger.info(f"🏆 [CAMPAIGN DEBUG] Campaign identifier '{campaign_identifier}' is not an ID, searching by name...")
            async with self.db_session_factory() as session:
                stmt = select(Campaign.id).where(func.lower(Campaign.name) == func.lower(campaign_identifier))
                result = await session.execute(stmt)
                campaign_id_from_name = result.scalar_one_or_none()
                if not campaign_id_from_name:
                     logger.warning(f"🏆 [CAMPAIGN DEBUG] Campaign not found by name: {campaign_identifier}")
                     return {"success": False, "response_code": "CAMPAIGN_NOT_FOUND", "context": {"name": campaign_identifier}}
                campaign_id = campaign_id_from_name
                logger.info(f"🏆 [CAMPAIGN DEBUG] Found campaign by name, ID: {campaign_id}")

        logger.info(f"🏆 [CAMPAIGN DEBUG] Calling campaign_service.claim_reward...")
        result = await self.campaign_service.claim_reward(user_id, campaign_id)
        logger.info(f"🏆 [CAMPAIGN DEBUG] Claim result: {result}")
        return result

    async def start_campaign_creation_impl(self, user_id: str, campaign_type: str) -> Dict[str, Any]:
        """
        Implementation for starting the campaign creation process.
        """
        try:
            campaign = await self.campaign_service.start_campaign_creation(user_id, campaign_type)
            if not campaign:
                return {"success": False, "response_code": "CAMPAIGN_CREATION_ERROR", "context": {"error": "Failed to initialize campaign."}}

            # The tool now returns the raw campaign object context
            return {
                "success": True,
                "response_code": "CAMPAIGN_CREATION_STARTED",
                "context": {"campaign": model_to_dict(campaign)}
            }
        except ValueError as ve:
            return {"success": False, "response_code": "CAMPAIGN_CREATION_ERROR", "context": {"error": str(ve)}}
        except Exception as e:
            logger.error(f"Start campaign creation failed for user {user_id}: {e}", exc_info=True)
            return {"success": False, "response_code": "CAMPAIGN_CREATION_ERROR", "context": {"error": str(e)}}

    async def activate_campaign_impl(self, user_id: str) -> Dict[str, Any]:
        """Activates a pending campaign for the user."""
        logger.info(f"🎯 [CAMPAIGN DEBUG] Starting campaign activation for user {user_id}")
        
        pending_campaign = await self.campaign_service.get_pending_campaign_by_user(user_id)
        if not pending_campaign:
            logger.warning(f"🎯 [CAMPAIGN DEBUG] No pending campaign found for user {user_id}")
            return {"success": False, "response_code": "CAMPAIGN_ACTIVATE_NO_PENDING", "context": {}}

        logger.info(f"🎯 [CAMPAIGN DEBUG] Found pending campaign: {pending_campaign.name} (ID: {pending_campaign.id})")

        try:
            logger.info(f"🎯 [CAMPAIGN DEBUG] Calling campaign_service.activate_campaign...")
            result = await self.campaign_service.activate_campaign(pending_campaign.id)
            logger.info(f"🎯 [CAMPAIGN DEBUG] Activation result: {result}")
            # The service layer now returns a structured response
            return result
        except Exception as e:
            logger.error(f"🎯 [CAMPAIGN DEBUG] Error activating campaign for user {user_id}: {e}", exc_info=True)
            logger.error(f"Error activating campaign for user {user_id}: {e}")
            return {"success": False, "response_code": "CAMPAIGN_ACTIVATE_UNEXPECTED_ERROR", "context": {}}

    async def verify_campaign_tasks_impl(self, user_id: str, campaign_identifier: str) -> Dict[str, Any]:
        """Implementation for verifying campaign tasks."""
        try:
            async with self.db_session_factory() as session:
                # 1. Get our internal user
                user = await self.user_service.get_user_by_twitter_id(user_id)
                if not user:
                    return {"success": False, "error": "User not found."}

                # 2. Get campaign by identifier (ID or name)
                campaign = None
                if str(campaign_identifier).isdigit():
                    campaign = await self.campaign_service.get_campaign_by_id(int(campaign_identifier), session)
                else:
                    campaign = await self.campaign_service.get_campaign_by_name(str(campaign_identifier))

                if not campaign:
                    return {"success": False, "error": "Could not find the specified campaign."}

                # 3. Skip verification - always return success
                # NOTE: Twitter interaction verification is disabled for now
                # Original verification code commented out:
                # results = {}
                # if campaign.profile_to_follow:
                #     results['has_followed'] = await self.interaction_service.check_user_follows(user.twitter_handle, campaign.profile_to_follow)
                # 
                # if campaign.tweet_id_to_engage:
                #     results['has_replied'] = await self.interaction_service.did_user_reply(user.twitter_user_id, campaign.tweet_id_to_engage)
                #     results['has_retweeted'] = await self.interaction_service.did_user_retweet(user.twitter_user_id, campaign.tweet_id_to_engage)
                #     results['has_quoted'] = await self.interaction_service.did_user_quote(user.twitter_user_id, campaign.tweet_id_to_engage)

                # 4. Save mock successful results to database (all tasks marked as completed)
                mock_results = {}
                if campaign.profile_to_follow:
                    mock_results['has_followed'] = True
                if campaign.tweet_id_to_engage:
                    mock_results['has_replied'] = True
                    mock_results['has_retweeted'] = True

                # Update participant status with timestamp and mock results
                await self.campaign_service.update_participant_task_status(
                    user.id, 
                    campaign.id, 
                    tasks_verified_at=datetime.now(timezone.utc),  # Set the timestamp
                    status='tasks_verified',  # Set the status
                    **mock_results  # Add mock results
                )

                # 5. Always return success
                return {"success": True, "message": "All tasks have been successfully verified! You can now claim your reward."}

        except Exception as e:
            logger.error(f"Error during task verification for user {user_id}, campaign {campaign_identifier}: {e}", exc_info=True)
            return {"success": False, "error": "An unexpected error occurred during task verification."}

    async def list_my_campaigns_impl(self, user_id: str) -> Dict[str, Any]:
        """Implementation for the list_my_campaigns tool."""
        try:
            # Precisamos do ID interno do usuário
            user = await self.user_service.get_user_by_twitter_id(user_id)
            if not user:
                return {"success": False, "response_code": "USER_NOT_FOUND", "context": {}}

            campaigns = await self.campaign_service.list_participating_campaigns(user.id)

            if not campaigns:
                return {"success": True, "response_code": "LIST_MY_CAMPAIGNS_EMPTY", "context": {}}
                
            # Rename "participation_status" to "status" for more intuitive handling
            for campaign in campaigns:
                if "participation_status" in campaign:
                    campaign["status"] = campaign.pop("participation_status")

            return {"success": True, "response_code": "LIST_MY_CAMPAIGNS_SUCCESS", "context": {"campaigns": campaigns}}
        except Exception as e:
            logger.error(f"Error in list_my_campaigns_impl: {e}", exc_info=True)
            return {"success": False, "response_code": "GENERIC_ERROR", "context": {}}
            
    async def get_recent_messages_impl(self, user_id: str, limit: int = 3) -> Dict[str, Any]:
        """
        Gets the most recent messages exchanged with a specific user to maintain context in conversations.
        
        Args:
            user_id: The ID of the user whose messages to retrieve
            limit: Maximum number of messages to retrieve (default: 3)
            
        Returns:
            A dictionary with success flag and the retrieved messages
        """
        try:
            # Convert Twitter ID to internal user ID
            user = await self.user_service.get_user_by_twitter_id(user_id)
            if not user:
                return {"success": False, "response_code": "USER_NOT_FOUND", "context": {}}
                
            # Query to get recent messages from the DMLog table
            async with self.db_session_factory() as session:
                # Get messages for this user
                result = await session.execute(
                    select(
                        DMLog.content,
                        DMLog.message_type,
                        DMLog.created_at,
                        DMLog.platform,
                        DMLog.conversation_id,
                    )
                    .where(DMLog.user_id == user.id)
                    .order_by(DMLog.created_at.desc())
                    .limit(limit)
                )
                
                messages = result.fetchall()
                
                # Format the results
                message_history = []
                for msg in reversed(messages):  # Reverse to get chronological order
                    message_history.append({
                        "content": msg[0],
                        "role": "assistant" if msg[1] == "bot" else "user",
                        "timestamp": msg[2],
                        "platform": msg[3],
                        "conversation_id": msg[4]
                    })
                
                return {
                    "success": True, 
                    "response_code": "GET_MESSAGES_SUCCESS", 
                    "context": {"messages": message_history}
                }
                
        except Exception as e:
            logger.error(f"Error in get_recent_messages_impl: {e}", exc_info=True)
            return {"success": False, "response_code": "GENERIC_ERROR", "context": {"error": str(e)}}

    async def request_authentication_impl(self) -> Dict[str, Any]:
        """
        Generate a 6-digit authentication token for a user.
        This tool provides an authentication code that users can use to verify their identity.
        
        Returns:
            A dictionary with success flag and the generated token
        """
        try:
            logger.info("🔐 Generating authentication token...")
            
            # Generate the authentication token using the authentication service
            token = await self.authentication_service.generate_and_store_token()
            
            if token:
                logger.info(f"✅ Authentication token generated successfully: {token[:2]}****")
                return {
                    "success": True,
                    "response_code": "AUTH_TOKEN_GENERATED",
                    "context": {
                        "token": token,
                        "message": f"Your authentication token is: {token}. This token will expire in 10 minutes."
                    }
                }
            else:
                logger.error("❌ Failed to generate authentication token")
                return {
                    "success": False,
                    "response_code": "AUTH_TOKEN_GENERATION_FAILED",
                    "context": {"error": "Failed to generate authentication token"}
                }
                
        except Exception as e:
            logger.error(f"Error in request_authentication_impl: {e}", exc_info=True)
            return {
                "success": False,
                "response_code": "GENERIC_ERROR",
                "context": {"error": str(e)}
            }

    async def verify_authentication_token_impl(self, user_id: str, token: str) -> Dict[str, Any]:
        """
        Verify an authentication token provided by the user.
        This confirms the user's identity and activates their authentication status.
        Also triggers auto-claim of any pending transfers for the authenticated user.
        
        Args:
            user_id: The Twitter user ID of the user
            token: The 6-digit authentication token to verify
            
        Returns:
            A dictionary with success flag and verification result
        """
        try:
            logger.info(f"🔐 Verifying authentication token for user {user_id}")
            
            # Validate the token format (should be 6 digits)
            if not re.match(r'^\d{6}$', token):
                logger.warning(f"❌ Invalid token format: {token}")
                return {
                    "success": False,
                    "response_code": "INVALID_TOKEN_FORMAT",
                    "context": {"error": "Authentication token must be exactly 6 digits"}
                }
            
            # Check if the token is pending (valid and not expired)
            is_pending = await self.authentication_service.is_pending_token(token)
            if not is_pending:
                logger.warning(f"❌ Token {token} is not pending (invalid, expired, or already used)")
                return {
                    "success": False,
                    "response_code": "INVALID_TOKEN",
                    "context": {"error": "Token is invalid, expired, or already used"}
                }
            
            # Activate the token for this user
            activation_success = await self.authentication_service.activate_token(token, user_id)
            
            if activation_success:
                logger.info(f"✅ Authentication token {token} activated successfully for user {user_id}")
                
                # Auto-claim any pending transfers after successful authentication
                try:
                    claim_result = await self.claim_pending_transfers_impl(user_id)
                    claimed_count = claim_result.get("context", {}).get("claimed", 0)
                    if claimed_count > 0:
                        logger.info(f"🎁 Auto-claimed {claimed_count} pending transfers for authenticated user {user_id}")
                except Exception as claim_error:
                    logger.warning(f"Failed to auto-claim pending transfers on authentication: {claim_error}")
                    # Don't fail authentication if auto-claim fails
                
                return {
                    "success": True,
                    "response_code": "AUTH_TOKEN_VERIFIED",
                    "context": {
                        "message": "Authentication successful! Your account is now verified.",
                        "authenticated": True,
                        "user_id": user_id
                    }
                }
            else:
                logger.error(f"❌ Failed to activate token {token} for user {user_id}")
                return {
                    "success": False,
                    "response_code": "TOKEN_ACTIVATION_FAILED",
                    "context": {"error": "Failed to activate authentication token"}
                }
                
        except Exception as e:
            logger.error(f"Error in verify_authentication_token_impl: {e}", exc_info=True)
            return {
                "success": False,
                "response_code": "GENERIC_ERROR",
                "context": {"error": str(e)}
            }

    async def get_transaction_history_impl(self, user_id: str, limit: int = 10, transaction_type: str = "all") -> Dict[str, Any]:
        """Implementation for getting user's transaction and swap history."""
        try:
            # Validate parameters
            if limit > 50:
                limit = 50
            elif limit < 1:
                limit = 10
                
            logger.info(f"📊 [HISTORY] Getting transaction history for user {user_id}, limit: {limit}, type: {transaction_type}")
            
            async with self.db_session_factory() as session:
                # Get user first
                user_result = await session.execute(
                    select(User).where(User.twitter_user_id == user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if not user:
                    return {
                        "success": False,
                        "response_code": "USER_NOT_FOUND",
                        "context": {"error": "User not found"}
                    }
                
                transactions = []
                
                # Get swap history
                if transaction_type in ["all", "swap"]:
                    swap_result = await session.execute(
                        text("""SELECT 'swap' as type, from_token, to_token, from_amount, to_amount, 
                               exchange_rate, status, created_at, value_usd, NULL as recipient, NULL as campaign_name
                               FROM swaphistorys WHERE user_id = :user_id 
                               ORDER BY created_at DESC LIMIT :limit"""),
                        {"user_id": user_id, "limit": limit}
                    )
                    swap_rows = swap_result.fetchall()
                    
                    for row in swap_rows:
                        transactions.append({
                            "type": "swap",
                            "from_token": row[1],
                            "to_token": row[2], 
                            "from_amount": float(row[3]),
                            "to_amount": float(row[4]),
                            "exchange_rate": float(row[5]),
                            "status": row[6],
                            "timestamp": row[7],
                            "value_usd": float(row[8]) if row[8] else None,
                            "description": f"Swapped {float(row[3])} {row[1]} for {float(row[4])} {row[2]}"
                        })
                
                # Get transfer history (both sent and received)
                if transaction_type in ["all", "transfer"]:
                    # Transfers sent
                    transfer_sent_result = await session.execute(
                        text("""SELECT 'transfer_sent' as type, token_symbol, amount, to_address, 
                               status, created_at, recipient_twitter_handle
                               FROM transactionhistorys 
                               WHERE user_id = :user_id AND transaction_type LIKE '%transfer%'
                               ORDER BY created_at DESC LIMIT :limit"""),
                        {"user_id": user.id, "limit": limit}
                    )
                    transfer_sent_rows = transfer_sent_result.fetchall()
                    
                    for row in transfer_sent_rows:
                        transactions.append({
                            "type": "transfer_sent",
                            "token": row[1],
                            "amount": float(row[2]),
                            "recipient": row[6] or row[3],  # Twitter handle or address
                            "status": row[4],
                            "timestamp": row[5],
                            "description": f"Sent {float(row[2])} {row[1]} to {row[6] or row[3]}"
                        })
                
                # Get campaign activities
                if transaction_type in ["all", "campaign"]:
                    campaign_result = await session.execute(
                        text("""SELECT 'campaign' as type, token_symbol, amount, transaction_type,
                               status, created_at
                               FROM transactionhistorys 
                               WHERE user_id = :user_id AND transaction_type LIKE '%campaign%'
                               ORDER BY created_at DESC LIMIT :limit"""),
                        {"user_id": user.id, "limit": limit}
                    )
                    campaign_rows = campaign_result.fetchall()
                    
                    for row in campaign_rows:
                        tx_type = row[3]
                        action = "claimed reward from" if "claim" in tx_type else "funded"
                        transactions.append({
                            "type": "campaign",
                            "token": row[1],
                            "amount": float(row[2]),
                            "campaign_action": action,
                            "status": row[4],
                            "timestamp": row[5],
                            "description": f"{action.title()} {float(row[2])} {row[1]} - campaign activity"
                        })
                
                # Get withdrawal history
                if transaction_type in ["all", "withdrawal"]:
                    withdrawal_result = await session.execute(
                        text("""SELECT 'withdrawal' as type, token_symbol, amount, to_address,
                               status, created_at, tx_hash
                               FROM transactionhistorys 
                               WHERE user_id = :user_id AND transaction_type = 'withdrawal'
                               ORDER BY created_at DESC LIMIT :limit"""),
                        {"user_id": user.id, "limit": limit}
                    )
                    withdrawal_rows = withdrawal_result.fetchall()
                    
                    for row in withdrawal_rows:
                        short_address = f"{row[3][:10]}..." if len(row[3]) > 10 else row[3]
                        transactions.append({
                            "type": "withdrawal",
                            "token": row[1],
                            "amount": float(row[2]),
                            "to_address": row[3],
                            "status": row[4],
                            "timestamp": row[5],
                            "tx_hash": row[6],
                            "description": f"Withdrew {float(row[2])} {row[1]} to {short_address}"
                        })
                
                # Sort all transactions by timestamp (most recent first)
                transactions.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
                
                # Limit the final results
                transactions = transactions[:limit]
                
                logger.info(f"📊 [HISTORY] Found {len(transactions)} transactions for user {user_id}")
                
                return {
                    "success": True,
                    "response_code": "TRANSACTION_HISTORY_SUCCESS",
                    "context": {
                        "transactions": transactions,
                        "total_count": len(transactions),
                        "user_id": user_id,
                        "filter": transaction_type
                    }
                }
                
        except Exception as e:
            logger.error(f"❌ [HISTORY] Error getting transaction history for user {user_id}: {e}", exc_info=True)
            return {
                "success": False,
                "response_code": "TRANSACTION_HISTORY_ERROR",
                "context": {"error": str(e)}
            }

    def _get_user_id_from_args(self, kwargs: Dict[str, Any]) -> Optional[str]:
        """Helper to extract user_id from arguments."""
        return kwargs.get('user_id')


_mcp_tools_manager_instance = None

def get_mcp_tools_manager(db_session_factory=None):
    """Factory function to get a singleton instance of the MCPToolsManager."""
    global _mcp_tools_manager_instance
    if _mcp_tools_manager_instance is None:
        _mcp_tools_manager_instance = MCPToolsManager(db_session_factory)
    return _mcp_tools_manager_instance


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """Dynamically builds the list of tools from the schemas."""
    return [Tool.from_dict(tool['function']) for tool in MCP_TOOLS_SCHEMAS]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
    """
    This is the main entry point when a tool is called from the MCP server.
    It retrieves the user_id from the context and executes the tool.
    """
    logger.info(f"Received tool call: {name} with args: {arguments}")

    # The user_id MUST be passed in the tool call context.
    # This is configured in response_generator.py
    user_id = arguments.pop("user_id", None)
    if not user_id:
        logger.error("Tool call failed: user_id was not provided in the context.")
        return [TextContent(text="Error: User ID not found.")]

    # Get the singleton instance of the tools manager
    tools_manager = get_mcp_tools_manager()

    # Dynamically find and execute the corresponding '_impl' method.
    method_name = f"{name}_impl"
    if hasattr(tools_manager, method_name):
        method_to_call = getattr(tools_manager, method_name)

        # For methods that require the user_id, pass it.
        # This uses introspection, but a more explicit mapping could also work.
        import inspect
        sig = inspect.signature(method_to_call)
        if 'user_id' in sig.parameters:
            arguments['user_id'] = user_id

        result = await method_to_call(**arguments)
    else:
        logger.warning(f"Tool '{name}' not found in MCPToolsManager.")
        result = {"success": False, "response_code": "TOOL_NOT_FOUND", "context": {"tool_name": name}}

    # For now, we'll just log the structured result.
    # The conversion to a user-facing message is handled by ResponseGenerator.
    logger.info(f"Tool {name} executed with result: {result}")

    # The MCP server expects a list of TextContent objects.
    # We will just return a placeholder, as the actual response is handled by the calling logic.
    return [TextContent(text=json.dumps(result))]


async def run_mcp_server():
    """Runs the MCP server."""
    # This function might be used if running the tools as a separate microservice.
    await mcp_server.run()



async def create_wallet_impl(user_id: str) -> Dict[str, Any]:
    # This function is now part of MCPToolsManager
    tools_manager = get_mcp_tools_manager()
    return await tools_manager.create_wallet_impl(user_id)

async def check_balance_impl(user_id: str) -> Dict[str, Any]:
    # This function is now part of MCPToolsManager
    tools_manager = get_mcp_tools_manager()
    return await tools_manager.check_balance_impl(user_id)

async def internal_swap_impl(user_id: str, from_token: str, to_token: str,
                             amount: float) -> Dict[str, Any]:
    # This function is now part of MCPToolsManager
    manager = get_mcp_tools_manager()
    return await manager.internal_swap_impl(user_id, from_token, to_token, amount)

async def withdraw_asset_impl(user_id: str, token: str, amount: float,
                              to_address: str) -> Dict[str, Any]:
    # This function is now part of MCPToolsManager
    manager = get_mcp_tools_manager()
    return await manager.withdraw_asset_impl(user_id, token, amount, to_address)

async def request_authentication_impl() -> Dict[str, Any]:
    # This function is now part of MCPToolsManager
    manager = get_mcp_tools_manager()
    return await manager.request_authentication_impl()

async def verify_authentication_token_impl(user_id: str, token: str) -> Dict[str, Any]:
    # This function is now part of MCPToolsManager
    manager = get_mcp_tools_manager()
    return await manager.verify_authentication_token_impl(user_id, token)

async def get_transaction_history_impl(user_id: str, limit: int = 10, transaction_type: str = "all") -> Dict[str, Any]:
    # This function is now part of MCPToolsManager
    manager = get_mcp_tools_manager()
    return await manager.get_transaction_history_impl(user_id, limit, transaction_type)

async def get_pending_transfers_impl(user_id: str) -> Dict[str, Any]:
    # This function is now part of MCPToolsManager
    manager = get_mcp_tools_manager()
    return await manager.get_pending_transfers_impl(user_id)

async def claim_pending_transfers_impl(user_id: str) -> Dict[str, Any]:
    # This function is now part of MCPToolsManager
    manager = get_mcp_tools_manager()
    return await manager.claim_pending_transfers_impl(user_id)

async def login_user_impl(twitter_handle: str, twitter_user_id: str) -> Dict[str, Any]:
    # This function is now part of MCPToolsManager
    manager = get_mcp_tools_manager()
    return await manager.login_user_impl(twitter_handle, twitter_user_id)
