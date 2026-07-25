#!/usr/bin/env python3
"""
Temporary configuration for testing MCP migration
Replace with your actual API keys
"""

import os

# Set environment variables for testing
def setup_test_env():
    """Setup test environment variables"""
    
    # DeepSeek API Key - REPLACE WITH YOUR ACTUAL KEY
    os.environ["DEEPSEEK_API_KEY"] = "sk-your-deepseek-api-key-here"
    
    # Optional: Other API keys for testing
    # os.environ["OPENAI_API_KEY"] = "your-openai-key"
    # os.environ["PIPER_X_API_KEY"] = "your-piperx-key"
    
    print("✅ Test environment configured")
    print("⚠️  Using placeholder API keys - replace with real ones to test!")

if __name__ == "__main__":
    setup_test_env() 