#!/usr/bin/env python3
"""
TESTE DM ESPECÍFICO - Testa conversa DM com user_id conhecido
"""

import asyncio
import json
import logging
from pprint import pprint

try:
    import pytest
except Exception:
    pytest = None

try:
    from twikit import Client
except ModuleNotFoundError as exc:
    if pytest is not None and exc.name in {"twikit"}:
        pytest.skip("twikit is not installed in this environment", allow_module_level=True)
    raise

if pytest is not None and __name__ != "__main__":
    pytest.skip("legacy integration script; run directly instead of via pytest", allow_module_level=True)

# Disable verbose logging
logging.basicConfig(level=logging.WARNING)

async def test_specific_dm():
    """Testa DM com user_id específico"""
    try:
        # Carrega cookies
        with open("twitter_manual_cookies.json", 'r') as f:
            cookie_data = json.load(f)
        
        cookies = {}
        for name, value in cookie_data.items():
            if not name.startswith('_') and value:
                cookies[name] = value
        
        print("🔧 INICIALIZANDO...")
        
        client = Client(language='en-US')
        client.set_cookies(cookies)
        user_id = await client.user_id()
        
        print(f"✅ USER_ID: {user_id}")
        
        # Pede user_id para testar
        print("\n💡 Digite o USER_ID de alguém que você enviou DM:")
        target_user_id = input("User ID: ").strip()
        
        if not target_user_id:
            print("❌ User ID necessário!")
            return
        
        print(f"\n🔍 TESTANDO DM COM: {target_user_id}")
        print("-" * 40)
        
        # Busca histórico DM
        dm_history = await client.get_dm_history(target_user_id)
        messages = list(dm_history)
        
        if not messages:
            print("❌ Nenhuma mensagem encontrada")
            return
        
        print(f"✅ ENCONTROU {len(messages)} MENSAGENS!")
        
        # Separa mensagens
        sent_by_you = [m for m in messages if m.sender_id == user_id]
        received_from_them = [m for m in messages if m.sender_id != user_id]
        
        print(f"📤 ENVIADAS POR VOCÊ: {len(sent_by_you)}")
        print(f"📥 RECEBIDAS DELES: {len(received_from_them)}")
        
        # Mostra todas as mensagens
        print(f"\n📨 TODAS AS MENSAGENS:")
        print("=" * 60)
        
        # Ordena por timestamp (mais antigas primeiro)
        all_msgs = sorted(messages, key=lambda m: m.time)
        
        for i, msg in enumerate(all_msgs, 1):
            sender = "VOCÊ" if msg.sender_id == user_id else "ELES"
            
            print(f"\n{i:2d}. [{sender}] Timestamp: {msg.time}")
            print(f"    ID: {msg.id}")
            print(f"    Sender: {msg.sender_id}")
            print(f"    Recipient: {msg.recipient_id}")
            print(f"    Texto: \"{msg.text}\"")
            
            if hasattr(msg, 'attachment') and msg.attachment:
                print(f"    Anexo: {msg.attachment}")
        
        # Análise RAW se tem mensagem recebida
        if received_from_them:
            print(f"\n🔬 ANÁLISE RAW - MENSAGEM RECEBIDA:")
            print("=" * 60)
            received_msg = received_from_them[0]
            
            print("🔸 TODAS AS PROPRIEDADES:")
            attrs = dir(received_msg)
            for attr in sorted(attrs):
                if not attr.startswith('_'):
                    try:
                        value = getattr(received_msg, attr)
                        if not callable(value):
                            print(f"   {attr}: {value}")
                    except:
                        pass
            
            print("\n🔸 ESTRUTURA COMPLETA (__dict__):")
            pprint(received_msg.__dict__, width=50, depth=3)
            
            print("\n🔸 MÉTODOS DISPONÍVEIS:")
            methods = [attr for attr in dir(received_msg) 
                      if not attr.startswith('_') and callable(getattr(received_msg, attr))]
            for method in methods:
                print(f"   {method}()")
                
            print(f"\n✅ SUCESSO! Mensagem de outro usuário analisada:")
            print(f"   ID: {received_msg.id}")
            print(f"   Texto: '{received_msg.text}'")
            print(f"   De: {received_msg.sender_id}")
            print(f"   Para: {received_msg.recipient_id}")
        
    except Exception as e:
        print(f"❌ ERRO: {e}")

if __name__ == "__main__":
    print("""
    🎯 TESTE DM ESPECÍFICO
    ======================
    
    Este script testa DM com user_id conhecido.
    Útil quando você sabe o ID de quem conversou.
    
    """)
    
    asyncio.run(test_specific_dm()) 