#!/usr/bin/env python3
"""
Simple DM Test - Just test if we can get DMs from Twitter
"""

import asyncio
import json
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class SimpleDMTest:
    def __init__(self):
        self.bot_user_id = None
    
    async def test_get_user_id(self):
        """Test getting our bot's user ID"""
        try:
            logger.info("🔍 Testing authentication...")
            
            script_content = """
const { Scraper } = require('agent-twitter-client');
const fs = require('fs');

async function getBotUserId() {
    try {
        console.error('Loading cookies...');
        const cookiesData = JSON.parse(fs.readFileSync('eliza_cookies_v2.json', 'utf8'));
        
        console.error('Creating scraper...');
        const scraper = new Scraper();
        await scraper.setCookies(cookiesData.map(cookie => 
            `${cookie.key}=${cookie.value}; Domain=${cookie.domain}; Path=${cookie.path}`
        ));
        
        console.error('Getting user info...');
        const me = await scraper.me();
        if (!me) {
            throw new Error('Failed to get authenticated user info');
        }
        
        console.log(JSON.stringify({ 
            userId: me.id, 
            screenName: me.screenName, 
            name: me.name,
            verified: me.verified || false,
            profileImageUrl: me.profileImageUrl || ""
        }));
        
    } catch (error) {
        console.error('Error:', error.message);
        process.exit(1);
    }
}

getBotUserId();
"""
            
            script_path = Path("temp_test_auth.js")
            script_path.write_text(script_content)
            
            result = subprocess.run(
                ["node", str(script_path)],
                capture_output=True,
                text=True,
                timeout=20
            )
            
            script_path.unlink(missing_ok=True)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                self.bot_user_id = data["userId"]
                logger.info(f"✅ Authentication successful!")
                logger.info(f"   Name: {data['name']}")
                logger.info(f"   Handle: @{data['screenName']}")
                logger.info(f"   ID: {data['userId']}")
                logger.info(f"   Verified: {data.get('verified', False)}")
                return True
            else:
                logger.error(f"❌ Authentication failed:")
                logger.error(f"   stdout: {result.stdout}")
                logger.error(f"   stderr: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error testing auth: {e}")
            return False
    
    async def test_get_dms(self):
        """Test getting DM conversations"""
        if not self.bot_user_id:
            logger.error("❌ No bot user ID available")
            return False
        
        try:
            logger.info("🔍 Testing DM retrieval...")
            
            script_content = f"""
const {{ Scraper }} = require('agent-twitter-client');
const fs = require('fs');

async function getDMs() {{
    try {{
        console.error('Loading cookies...');
        const cookiesData = JSON.parse(fs.readFileSync('eliza_cookies_v2.json', 'utf8'));
        
        console.error('Creating scraper...');
        const scraper = new Scraper();
        await scraper.setCookies(cookiesData.map(cookie => 
            `${{cookie.key}}=${{cookie.value}}; Domain=${{cookie.domain}}; Path=${{cookie.path}}`
        ));
        
        console.error('Getting DM conversations...');
        const dmResponse = await scraper.getDirectMessageConversations('{self.bot_user_id}');
        
        console.error(`Got response with ${{dmResponse?.conversations?.length || 0}} conversations`);
        console.log(JSON.stringify(dmResponse, null, 2));
        
    }} catch (error) {{
        console.error('Error:', error.message);
        console.error('Stack:', error.stack);
        process.exit(1);
    }}
}}

getDMs();
"""
            
            script_path = Path("temp_test_dms.js")
            script_path.write_text(script_content)
            
            result = subprocess.run(
                ["node", str(script_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            script_path.unlink(missing_ok=True)
            
            if result.returncode == 0:
                dm_data = json.loads(result.stdout)
                conversations = dm_data.get("conversations", [])
                
                logger.info(f"✅ DM retrieval successful!")
                logger.info(f"   Found {len(conversations)} conversations")
                
                # Log details of each conversation
                for i, conv in enumerate(conversations):
                    conv_id = conv["conversationId"]
                    messages = conv.get("messages", [])
                    participants = conv.get("participants", [])
                    
                    logger.info(f"   📝 Conversation {i+1}: {conv_id}")
                    logger.info(f"      Messages: {len(messages)}")
                    
                    for p in participants:
                        screen_name = p.get("screenName", p.get("id", "unknown"))
                        logger.info(f"      Participant: @{screen_name}")
                    
                    # Show recent messages
                    if messages:
                        recent_messages = sorted(messages, key=lambda m: int(m["createdAt"]))[-3:]
                        logger.info(f"      Recent messages:")
                        for msg in recent_messages:
                            sender = msg.get("senderScreenName", msg.get("senderId", "unknown"))
                            text = msg.get("text", "")[:50] + ("..." if len(msg.get("text", "")) > 50 else "")
                            logger.info(f"        @{sender}: {text}")
                
                return True
            else:
                logger.error(f"❌ DM retrieval failed:")
                logger.error(f"   stdout: {result.stdout}")
                logger.error(f"   stderr: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error testing DMs: {e}")
            return False
    
    async def run_tests(self):
        """Run all tests"""
        logger.info("🚀 Starting Simple DM Tests")
        logger.info("="*50)
        
        # Test 1: Authentication
        auth_success = await self.test_get_user_id()
        if not auth_success:
            logger.error("❌ Authentication test failed - stopping")
            return False
        
        # Test 2: DM retrieval
        dm_success = await self.test_get_dms()
        if not dm_success:
            logger.error("❌ DM retrieval test failed")
            return False
        
        logger.info("🎉 All tests passed successfully!")
        return True

async def main():
    """Main test function"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    tester = SimpleDMTest()
    success = await tester.run_tests()
    
    if success:
        logger.info("✅ DM system is working correctly!")
    else:
        logger.error("❌ DM system has issues!")

if __name__ == "__main__":
    asyncio.run(main()) 