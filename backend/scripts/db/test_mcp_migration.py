#!/usr/bin/env python3
"""
Test script for MCP Real Migration
Tests DeepSeek tool calling vs old pattern matching
"""

import asyncio
import os
import sys
from datetime import datetime
import json

try:
    import pytest
except Exception:
    pytest = None

# Add project root to path
sys.path.append('.')

# Load .env file
from dotenv import load_dotenv
load_dotenv()

try:
    from ai.response_generator import XiaoLeeResponseGenerator
    from ai.mcp_tools import get_mcp_tools
    from database.database import init_db
except ModuleNotFoundError as exc:
    if pytest is not None and exc.name in {"openai"}:
        pytest.skip("openai is not installed in this environment", allow_module_level=True)
    raise

if pytest is not None and __name__ != "__main__":
    pytest.skip("legacy integration script; run directly instead of via pytest", allow_module_level=True)

class MCPMigrationTester:
    def __init__(self):
        self.generator = XiaoLeeResponseGenerator(provider="deepseek")
        self.test_user_id = "test_user_12345"
        
    async def test_create_wallet(self):
        """Test wallet creation with natural language"""
        print("\n🧪 Testing Wallet Creation...")
        
        test_messages = [
            "I need a new wallet",
            "Can you create a wallet for me?",
            "I want to start trading, help me set up",
            "create wallet please"
        ]
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n--- Test {i}: '{message}' ---")
            try:
                response = await self.generator.generate_response(message, self.test_user_id)
                print(f"Response: {response}")
            except Exception as e:
                print(f"❌ Error: {e}")
            
    async def test_balance_check(self):
        """Test balance checking with natural language"""
        print("\n💰 Testing Balance Check...")
        
        test_messages = [
            "What's my balance?",
            "How much do I have?",
            "Show me my tokens",
            "check balance"
        ]
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n--- Test {i}: '{message}' ---")
            try:
                response = await self.generator.generate_response(message, self.test_user_id)
                print(f"Response: {response}")
            except Exception as e:
                print(f"❌ Error: {e}")
            
    async def test_swap_requests(self):
        """Test swap requests with natural language"""
        print("\n🔄 Testing Swap Requests...")
        
        test_messages = [
            "I want to swap 100 USDC for ETH",
            "Trade 50 USDC to BTC please",
            "Exchange 0.1 ETH for USDC",
            "Can you swap 10 USDC to ETH?"
        ]
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n--- Test {i}: '{message}' ---")
            try:
                response = await self.generator.generate_response(message, self.test_user_id)
                print(f"Response: {response}")
            except Exception as e:
                print(f"❌ Error: {e}")
            
    async def test_general_conversation(self):
        """Test general conversation handling"""
        print("\n💬 Testing General Conversation...")
        
        test_messages = [
            "Hello there!",
            "What can you help me with?",
            "I'm new to crypto",
            "How does this work?"
        ]
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n--- Test {i}: '{message}' ---")
            try:
                response = await self.generator.generate_response(message, self.test_user_id)
                print(f"Response: {response}")
            except Exception as e:
                print(f"❌ Error: {e}")
            
    async def test_mcp_tools_format(self):
        """Test MCP tools format"""
        print("\n🔧 Testing MCP Tools Format...")
        
        tools = get_mcp_tools()
        print(f"Number of tools: {len(tools)}")
        
        for tool in tools:
            print(f"\n✅ Tool: {tool['function']['name']}")
            print(f"   Description: {tool['function']['description']}")
            print(f"   Parameters: {list(tool['function']['parameters']['properties'].keys())}")
            
    async def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting MCP Migration Tests...")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Test User ID: {self.test_user_id}")
        
        # Check API key
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            print("❌ DEEPSEEK_API_KEY not found in .env file")
            return
        print(f"✅ API Key found: {api_key[:10]}...")
        
        # Test tools format first
        await self.test_mcp_tools_format()
        
        # Test each functionality
        await self.test_create_wallet()
        await self.test_balance_check()
        await self.test_swap_requests()
        await self.test_general_conversation()
        
        print("\n🎉 All tests completed!")

async def main():
    """Main test runner"""
    try:
        tester = MCPMigrationTester()
        await tester.run_all_tests()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 