"""
Xiao Lee AI Module - Phase 4: AI + MCP Tools Integration

This module provides:
- LLM integration (OpenAI/Ollama)
- Multiple MCP tools for crypto operations, campaigns, and user interaction
- Waifu personality prompts
- Complete response generation pipeline
"""

from .prompts import XiaoLeePrompts

# Heavy imports depend on 'mcp', 'web3', and other packages only present in the full server
# environment.  Unit tests that only need ai.agents.* (creator_pay_tools, etc.) can load the
# package without these optional deps installed.
try:
    from .llm_client import LLMClient
    from .mcp_tools import (MCPToolsManager, get_mcp_tools_manager, create_wallet_impl,
                            check_balance_impl, internal_swap_impl,
                            withdraw_asset_impl, request_authentication_impl,
                            verify_authentication_token_impl, get_transaction_history_impl,
                            get_pending_transfers_impl, claim_pending_transfers_impl,
                            login_user_impl, mcp_server, get_mcp_tools)
    from .response_generator import XiaoLeeResponseGenerator, generate_ai_response
except ImportError:
    LLMClient = None  # type: ignore[assignment,misc]
    MCPToolsManager = None  # type: ignore[assignment,misc]
    get_mcp_tools_manager = None  # type: ignore[assignment]
    get_mcp_tools = None  # type: ignore[assignment]
    mcp_server = None  # type: ignore[assignment]
    create_wallet_impl = check_balance_impl = internal_swap_impl = None  # type: ignore[assignment]
    withdraw_asset_impl = request_authentication_impl = None  # type: ignore[assignment]
    verify_authentication_token_impl = get_transaction_history_impl = None  # type: ignore[assignment]
    get_pending_transfers_impl = claim_pending_transfers_impl = None  # type: ignore[assignment]
    login_user_impl = None  # type: ignore[assignment]
    XiaoLeeResponseGenerator = None  # type: ignore[assignment,misc]
    generate_ai_response = None  # type: ignore[assignment]

__all__ = [
    # Main classes
    'LLMClient',
    'XiaoLeePrompts',
    'XiaoLeeResponseGenerator',

    # MCP Tools Manager
    'MCPToolsManager',
    'get_mcp_tools_manager',
    'get_mcp_tools',

    # MCP Tools (backward compatibility)
    'create_wallet_impl',
    'check_balance_impl',
    'internal_swap_impl',
    'withdraw_asset_impl',
    'request_authentication_impl',
    'verify_authentication_token_impl',
    'get_transaction_history_impl',
    'get_pending_transfers_impl',
    'claim_pending_transfers_impl',
    'login_user_impl',
    'mcp_server',

    # Convenience function
    'generate_ai_response'
]
