"""
Configuration module for XiaoLee bot
Loads configuration from environment variables
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Encryption key for wallet services
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    raise ValueError("ENCRYPTION_KEY environment variable is required")

# Other configuration variables can be added here as needed
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///xiao_lee.db")
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:5000")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# AI Provider settings
AI_PROVIDER = os.getenv("AI_PROVIDER", "deepseek")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Twitter API settings
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

# Ollama settings
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")

# Animation/Video mapping for UI animations
# XiaoLee's animation set for personality expression
ACTION_VIDEO_MAP = {
    # Map to actual xiaolee animation files
    "Cheer": "xiaolee_cheer.mov",
    "Giggle": "xiaolee_giggle.mp4", 
    "Kawaii": "xiaolee_kawaii.mov",
    "Love": "xiaolee_love.mp4",
    "Hello": "xiaolee_hello.mov",
    "Surprise": "xiaolee_surprise.mov",
    "Uncomfortable": "xiaolee_uncomfortable.mov",
    "Ouch": "xiaolee_ouch.mov",
    "Think Low": "xiaolee_thinklow.mov",
    "Salute": "xiaolee_salute.mov",
    
    # Map common animation names to available files
    "Happy": "xiaolee_kawaii.mov",  # Use kawaii for happy
    "Excited": "xiaolee_cheer.mov",  # Use cheer for excited
    "Confused": "xiaolee_thinklow.mov",  # Use thinklow for confused
    "Thinking": "xiaolee_thinklow.mov",  # Direct mapping
    
    # Standby animations for general use
    "Standby": "xiaolee_standby.mov",
    "Standby2": "xiaolee_standby2.mov", 
    "Standby3": "xiaolee_standby3.mov",
    
    # Legacy mappings - fix wave to use a friendly animation
    "wave": "xiaolee_hello.mov",  # Use hello for wave greeting
    "celebration": "xiaolee_cheer.mov",
    "success": "xiaolee_cheer.mov",
    "error": "xiaolee_ouch.mov",
}
