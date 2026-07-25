#!/usr/bin/env python3
"""
ANALISAR CONVERSA ENCONTRADA
Análise detalhada da conversa DM real que foi descoberta
"""

import asyncio
import json
import logging
from pprint import pprint
from twikit import Client
import time

logging.basicConfig(level=logging.WARNING)

async def analyze_conversation():
    """Analisa a conversa encontrada em detalhes"""
    
    # User ID encontrado
    FOUND_USER_ID = "1735029448339009536"  # @QQuanteBuild
    
    print("🔬 ANÁLISE DETALHADA DA CONVERSA ENCONTRADA")
    print("="*60)
    print(f"🎯 User ID: {FOUND_USER_ID} (@QQuanteBuild)")
    print(f"📊 19 mensagens recebidas + 1 enviada = 20 total")
    
    # Inicializa cliente
    with open("../../data/twitter_manual_cookies.json", 'r') as f:
        cookie_data = json.load(f)
    
    cookies = {}
    
    client = Client(language='en-US')
    client.set_cookies(cookies)
    my_user_id = await client.user_id()
    
    print(f"✅ Seu user_id: {my_user_id}")
    print(f"✅ Cliente inicializado")
    
    # Busca todas as mensagens
    print(f"\n📨 BUSCANDO TODAS AS MENSAGENS...")
    dm_history = await client.get_dm_history(FOUND_USER_ID)
    all_messages = list(dm_history)
    
    print(f"✅ Coletadas {len(all_messages)} mensagens")
    
    # Separa mensagens
    from_them = [m for m in all_messages if m.sender_id == FOUND_USER_ID]
    from_you = [m for m in all_messages if m.sender_id == my_user_id]
    
    print(f"\n📊 ESTATÍSTICAS:")
    print(f"   📥 Recebidas de @QQuanteBuild: {len(from_them)}")
    print(f"   📤 Enviadas por você: {len(from_you)}")
    print(f"   📋 Total: {len(all_messages)}")
    
    # Ordena mensagens por timestamp (cronológica)
    all_messages_sorted = sorted(all_messages, key=lambda m: m.time)
    
    print(f"\n💬 CONVERSA COMPLETA (CRONOLÓGICA):")
    print("-" * 60)
    
    for i, msg in enumerate(all_messages_sorted, 1):
        sender = "VOCÊ" if msg.sender_id == my_user_id else "@QQuanteBuild"
        timestamp = msg.time
        
        print(f"\n{i:2d}. [{sender}] {timestamp}")
        print(f"    ID: {msg.id}")
        print(f"    Texto: \"{msg.text}\"")
        print(f"    Sender: {msg.sender_id} → Recipient: {msg.recipient_id}")
        
        if hasattr(msg, 'attachment') and msg.attachment:
            print(f"    Anexo: {msg.attachment}")
    
    # Análise RAW da primeira mensagem RECEBIDA
    if from_them:
        print(f"\n🔬 ANÁLISE RAW - PRIMEIRA MENSAGEM RECEBIDA:")
        print("="*60)
        first_received = from_them[0]
        
        print("🔸 PROPRIEDADES:")
        attrs = ['id', 'text', 'time', 'sender_id', 'recipient_id', 'attachment']
        for attr in attrs:
            if hasattr(first_received, attr):
                value = getattr(first_received, attr)
                print(f"   {attr}: {value}")
        
        print("\n🔸 ESTRUTURA COMPLETA:")
        pprint(first_received.__dict__, width=60, depth=2)
        
        print("\n🔸 MÉTODOS DISPONÍVEIS:")
        methods = [attr for attr in dir(first_received) 
                  if not attr.startswith('_') and callable(getattr(first_received, attr))]
        for method in methods:
            print(f"   {method}()")
        
        print(f"\n✅ MENSAGEM REAL DE OUTRO USUÁRIO ANALISADA!")
        print(f"   ID: {first_received.id}")
        print(f"   Texto: '{first_received.text}'")
        print(f"   De: {first_received.sender_id} (@QQuanteBuild)")
        print(f"   Para: {first_received.recipient_id} (você)")
        print(f"   Timestamp: {first_received.time}")

def get_cookies():
    try:
        with open("../../data/twitter_manual_cookies.json", 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Cookie file not found.")

async def main():
    await analyze_conversation()

if __name__ == "__main__":
    print("""
    🎉 ANÁLISE DA CONVERSA REAL ENCONTRADA
    ======================================
    
    Vamos analisar detalhadamente a conversa DM real
    que foi descoberta via notificações/menções:
    
    User: @QQuanteBuild (1735029448339009536)
    Mensagens: 19 recebidas + 1 enviada
    
    """)
    
    asyncio.run(main()) 