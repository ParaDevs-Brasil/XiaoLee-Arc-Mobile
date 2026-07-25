#!/usr/bin/env python3
"""
Xiao Lee Twitter Bot - Windows Optimized Runner
Integra Twitter DM monitoring com AI response generation usando twikit direto
"""

import asyncio
import logging
import signal
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to Python path
sys.path.append(str(Path(__file__).parent))

# Usar implementação twikit direta
from twitter.twikit_direct import CookieBasedTwitterManager

# Configure logging without emojis for Windows compatibility
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()

# Windows-friendly logging (no emojis)
class WindowsLogFormatter(logging.Formatter):
    """Logging formatter que remove emojis para compatibilidade Windows"""
    
    def format(self, record):
        # Replace common emojis with text equivalents
        emoji_replacements = {
            '🔧': '[CONFIG]',
            '✅': '[OK]',
            '❌': '[ERROR]',
            '⚠️': '[WARN]',
            '🚀': '[START]',
            '🔍': '[SEARCH]',
            '📨': '[MSG]',
            '💡': '[INFO]',
            '🛑': '[STOP]',
            '🎯': '[TARGET]',
            '📡': '[SYSTEM]',
            '🔄': '[PROCESS]',
            '📱': '[BOT]',
            '📋': '[LIST]',
            '📤': '[SEND]',
            '💖': '[LOVE]',
            '⌨️': '[TYPING]',
            '➕': '[ADD]'
        }
        
        # Get the original message
        original_msg = super().format(record)
        
        # Replace emojis with text
        for emoji, replacement in emoji_replacements.items():
            original_msg = original_msg.replace(emoji, replacement)
        
        return original_msg

# Setup Windows-compatible logging
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('xiao_lee_bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Apply Windows formatter to all handlers
for handler in logging.getLogger().handlers:
    handler.setFormatter(WindowsLogFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

logger = logging.getLogger(__name__)

class XiaoLeeTwitterBot:
    """Main Twitter bot controller usando twikit direto"""
    
    def __init__(self):
        self.twitter_manager = CookieBasedTwitterManager()
        self.running = False
        
    async def start(self):
        """Start the Twitter bot com twikit direto"""
        try:
            logger.info("[START] Iniciando Xiao Lee Twitter Bot (Twikit Direto)...")
            
            # Initialize Twitter manager com cookies
            await self.twitter_manager.initialize("twitter_manual_cookies.json")
            
            # Check status
            status = self.twitter_manager.get_status()
            logger.info(f"[CONFIG] Status: {status}")
            
            if not status['authenticated']:
                raise Exception("Falha na autenticação com cookies")
            
            logger.info("[OK] Bot inicializado com sucesso!")
            logger.info(f"[CONFIG] User ID: {status.get('user_id', 'Extraindo...')}")
            
            # Start monitoring usando streaming do twikit
            self.running = True
            logger.info("[PROCESS] Iniciando monitoramento de DMs via streaming...")
            await self.twitter_manager.start_monitoring()
            
        except Exception as e:
            logger.error(f"[ERROR] Falha ao iniciar bot: {e}")
            raise

    async def stop(self):
        """Stop the Twitter bot"""
        logger.info("[STOP] Parando Xiao Lee Twitter Bot...")
        self.running = False
        
        if self.twitter_manager:
            await self.twitter_manager.stop()
        
        logger.info("[STOP] Bot parado")

    async def send_test_message(self, user_handle: str, message: str = None):
        """Send a test message para verificar funcionalidade"""
        if not self.twitter_manager:
            raise Exception("Bot não inicializado")
            
        return await self.twitter_manager.send_test_dm(user_handle, message)

# Global bot instance para signal handling
bot = None

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"[SYSTEM] Received signal {signum}")
    if bot and bot.running:
        asyncio.create_task(bot.stop())

async def main():
    """Main function usando twikit direto"""
    global bot
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    bot = XiaoLeeTwitterBot()
    
    # Check se cookies file existe
    if not Path("twitter_manual_cookies.json").exists():
        logger.error("[ERROR] Cookie file não encontrado!")
        logger.error("[CONFIG] Por favor extraia cookies do Twitter manualmente:")
        logger.error("[CONFIG]    1. Abra Twitter no navegador e faça login")
        logger.error("[CONFIG]    2. Pressione F12 para abrir Developer Tools")
        logger.error("[CONFIG]    3. Vá em Application > Cookies > https://twitter.com")
        logger.error("[CONFIG]    4. Copie valores de 'auth_token' e 'ct0'")
        logger.error("[CONFIG]    5. Cole no arquivo twitter_manual_cookies.json")
        return
    
    # Validate API key
    deepseek_key = os.getenv('DEEPSEEK_API_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')
    
    if not (deepseek_key or openai_key):
        logger.error("[ERROR] Chave de API AI ausente!")
        logger.error("[CONFIG] Defina DEEPSEEK_API_KEY ou OPENAI_API_KEY")
        logger.error("[CONFIG] em variáveis de ambiente ou arquivo .env")
        return
    
    try:
        logger.info("[START] Inicializando Xiao Lee Twitter Bot...")
        logger.info(f"[CONFIG] AI Provider: {os.getenv('AI_PROVIDER', 'deepseek')}")
        logger.info("[CONFIG] Usando autenticação via cookies twikit direto")
        
        # Start the bot
        await bot.start()
        
        # Keep running
        logger.info("[SYSTEM] Bot em execução. Ctrl+C para parar.")
        while bot.running:
            await asyncio.sleep(1)
        
    except KeyboardInterrupt:
        logger.info("[SYSTEM] Interrupção de teclado recebida")
    except Exception as e:
        logger.error(f"[ERROR] Bot crashou: {e}")
        import traceback
        logger.error(f"[ERROR] Traceback: {traceback.format_exc()}")
    finally:
        if bot:
            await bot.stop()

if __name__ == "__main__":
    print("""
    ========================================
    Xiao Lee AI Twitter Bot (Twikit Direto)
    ========================================
    
    [OK] Configuração carregada do arquivo .env
    [OK] Credenciais Twitter via cookies
    [OK] Chave de API AI configurada
    [OK] Configurações do bot
    
    O bot irá:
    [OK] Login no Twitter usando cookies (sessão persistente)
    [OK] Monitorar DMs com streaming em tempo real
    [OK] Gerar respostas AI usando personalidade XiaoLee
    [OK] Processar operações crypto usando MCP tools
    
    Pressione Ctrl+C para parar o bot.
    ========================================
    """)
    
    # Run the bot
    asyncio.run(main()) 