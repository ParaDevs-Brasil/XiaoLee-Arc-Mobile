#!/usr/bin/env python3
"""
Xiao Lee CLI Chat Client
Test the complete flow: User Input → AI → MCP Tools → Database → Response
"""

import asyncio
import aiohttp
import json
import sys
import os
from datetime import datetime

class XiaoLeeChatCLI:
    def __init__(self, base_url="http://127.0.0.1:5000"):
        self.base_url = base_url
        self.session = None
        self.user_id = "cli_user_001"
        
    async def start_session(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession()
        print("🤖 Connecting to Xiao Lee Chat Server...")
        
        try:
            # Test server connection
            async with self.session.get(f"{self.base_url}/") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Connected! Server: {data.get('message', 'Unknown')}")
                    return True
                else:
                    print(f"❌ Server responded with status {response.status}")
                    return False
                    
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    async def send_message(self, message: str) -> str:
        """Send message to Xiao Lee and get response"""
        try:
            payload = {
                "user_id": self.user_id,
                "message": message,
                "platform": "cli"
            }
            
            print(f"📤 Sending: {message}")
            
            async with self.session.post(
                f"{self.base_url}/chat", 
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    ai_response = data.get("response", "No response")
                    print(f"🌸 Xiao Lee: {ai_response}")
                    return ai_response
                else:
                    error_text = await response.text()
                    print(f"❌ Server error ({response.status}): {error_text}")
                    return f"Error: {response.status}"
                    
        except Exception as e:
            print(f"❌ Request failed: {e}")
            return f"Error: {e}"
    
    async def run_interactive(self):
        """Interactive chat mode"""
        print("\n" + "="*60)
        print("🌸 XIAO LEE INTERACTIVE CHAT")
        print("="*60)
        print("Type your messages and press Enter")
        print("Special commands:")
        print("  'test all' - Run comprehensive test suite")
        print("  'quit' or 'exit' - End session")
        print("  'help' - Show Xiao Lee's help menu")
        print("="*60)
        
        while True:
            try:
                user_input = input("\n💬 You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye! Thanks for chatting with Xiao Lee!")
                    break
                    
                elif user_input.lower() == 'test all':
                    await self.run_test_suite()
                    continue
                    
                elif not user_input:
                    continue
                
                # Send to Xiao Lee
                await self.send_message(user_input)
                
            except KeyboardInterrupt:
                print("\n👋 Session ended!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    async def run_test_suite(self):
        """Run comprehensive test of all MCP tools"""
        print("\n🧪 RUNNING COMPREHENSIVE TEST SUITE")
        print("="*50)
        
        tests = [
            # Basic interaction
            ("Hello Xiao Lee!", "Basic greeting"),
            
            # Wallet creation
            ("create wallet", "Wallet creation"),
            
            # Balance check
            ("check my balance", "Balance check"),
            ("what are my bags?", "Balance check (slang)"),
            
            # Swap operations
            ("swap 100 USDC to ETH", "Token swap"),
            ("trade 0.1 ETH for BTC", "Another swap"),
            
            # Help and info
            ("help", "Help menu"),
            ("what can you do?", "Capabilities"),
            
            # Crypto slang
            ("wen moon?", "Crypto slang test"),
            ("are we gonna make it?", "WAGMI test"),
            
            # Error handling
            ("swap 999999 BTC to ETH", "Insufficient balance test"),
        ]
        
        successful_tests = 0
        
        for i, (message, description) in enumerate(tests, 1):
            print(f"\n📋 Test {i}/{len(tests)}: {description}")
            print(f"📨 Input: '{message}'")
            
            try:
                response = await self.send_message(message)
                
                # Basic validation
                if "error" not in response.lower() and len(response) > 10:
                    print("✅ Test passed!")
                    successful_tests += 1
                else:
                    print("⚠️  Test completed (check response quality)")
                    
            except Exception as e:
                print(f"❌ Test failed: {e}")
            
            # Small delay between tests
            await asyncio.sleep(0.5)
        
        print(f"\n📊 TEST SUMMARY")
        print(f"Successful tests: {successful_tests}/{len(tests)}")
        print(f"Success rate: {(successful_tests/len(tests)*100):.1f}%")
        
        if successful_tests >= len(tests) * 0.8:  # 80% success rate
            print("🎉 EXCELLENT! System working well!")
        elif successful_tests >= len(tests) * 0.6:  # 60% success rate
            print("👍 GOOD! Some issues but mostly functional")
        else:
            print("⚠️  NEEDS WORK! Multiple issues detected")
    
    async def close_session(self):
        """Clean up HTTP session"""
        if self.session:
            await self.session.close()

async def main():
    """Main CLI function"""
    print("🚀 XIAO LEE CLI CHAT CLIENT")
    print("Testing complete AI + MCP Tools + Database flow")
    
    cli = XiaoLeeChatCLI()
    
    try:
        # Start session
        if not await cli.start_session():
            print("❌ Failed to connect to server. Is it running?")
            print("💡 Try: python run_chat_server.py")
            return
        
        # Check if user wants auto-test or interactive
        if len(sys.argv) > 1 and sys.argv[1] == 'test':
            await cli.run_test_suite()
        else:
            await cli.run_interactive()
        
    except Exception as e:
        print(f"❌ CLI error: {e}")
    finally:
        await cli.close_session()

if __name__ == "__main__":
    asyncio.run(main()) 