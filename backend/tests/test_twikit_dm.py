#!/usr/bin/env python3
"""
Teste do Twikit Direct - Envio de DM
"""

import asyncio
import logging

try:
    import pytest
except Exception:
    pytest = None

try:
    from twitter.twikit_direct import TwikitDirectManager
except ModuleNotFoundError as exc:
    if pytest is not None and exc.name in {"twitter"}:
        pytest.skip("twitter package is not installed in this environment", allow_module_level=True)
    raise

if pytest is not None and __name__ != "__main__":
    pytest.skip("legacy integration script; run directly instead of via pytest", allow_module_level=True)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_send_dm():
    """Testa envio de DM"""
    manager = TwikitDirectManager()
    
    try:
        # Inicializa
        await manager.initialize("twitter_manual_cookies.json")
        
        # Status
        status = manager.get_status()
        print(f"✅ Status: {status}")
        
        # Pede user_id de destino
        target_user_id = input("Digite o user_id para testar DM: ")
        
        if not target_user_id:
            print("❌ User ID obrigatório")
            return
        
        # Envia DM de teste
        message = "Oi! Teste do bot Xiao Lee funcionando! 💖"
        success = await manager.send_dm(target_user_id, message)
        
        if success:
            print("✅ DM enviado com sucesso!")
        else:
            print("❌ Falha ao enviar DM")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_send_dm()) 