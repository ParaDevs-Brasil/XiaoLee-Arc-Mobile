#!/usr/bin/env python3
"""
ANALISADOR DE NOTIFICATIONS
Mostra exatamente o que tem dentro das notifications do Twitter
"""

import asyncio
import json
import logging
from pprint import pprint
from twikit import Client

logging.basicConfig(level=logging.WARNING)

async def analyze_notifications():
    """Analisa as notifications em detalhes"""
    
    print("🔬 ANÁLISE DETALHADA DAS NOTIFICATIONS")
    print("="*60)
    
    # Inicializa cliente
    with open("twitter_manual_cookies.json", 'r') as f:
        cookie_data = json.load(f)
    
    cookies = {}
    for name, value in cookie_data.items():
        if not name.startswith('_') and value:
            cookies[name] = value
    
    print("🔧 INICIALIZANDO...")
    client = Client(language='en-US')
    client.set_cookies(cookies)
    
    try:
        # Busca notifications
        print("📬 BUSCANDO NOTIFICATIONS...")
        notifications = await client.get_notifications()
        
        print(f"📊 TOTAL DE NOTIFICATIONS: {len(notifications)}")
        print("="*60)
        
        # Analisa cada notification
        user_ids_found = set()
        notification_types = {}
        
        for i, notif in enumerate(notifications[:10]):  # Primeiras 10
            print(f"\n🔔 NOTIFICATION #{i+1}:")
            print("-" * 40)
            
            # Analisa o tipo
            notif_type = getattr(notif, 'type', 'UNKNOWN')
            notification_types[notif_type] = notification_types.get(notif_type, 0) + 1
            
            print(f"📋 TIPO: {notif_type}")
            
            # Busca user info
            if hasattr(notif, 'user') and notif.user:
                user_id = notif.user.id
                username = notif.user.username
                user_ids_found.add(user_id)
                print(f"👤 USER: @{username} (ID: {user_id})")
            
            # Busca texto/conteúdo
            if hasattr(notif, 'text') and notif.text:
                print(f"💬 TEXTO: {notif.text[:100]}...")
            
            # Mostra timestamp
            if hasattr(notif, 'created_at') and notif.created_at:
                print(f"⏰ DATA: {notif.created_at}")
            
            # Mostra tweet_id se tiver
            if hasattr(notif, 'tweet') and notif.tweet:
                print(f"🐦 TWEET_ID: {notif.tweet.id}")
            
            print("-" * 40)
        
        print(f"\n📊 RESUMO GERAL:")
        print("="*60)
        print(f"🔔 TIPOS DE NOTIFICATIONS ENCONTRADOS:")
        for notif_type, count in notification_types.items():
            print(f"   • {notif_type}: {count}x")
        
        print(f"\n👥 USER_IDs ÚNICOS DESCOBERTOS: {len(user_ids_found)}")
        print(f"📋 Lista: {list(user_ids_found)[:5]}...")  # Primeiros 5
        
        # Mostra atributos disponíveis
        if notifications:
            print(f"\n🔍 ATRIBUTOS DISPONÍVEIS NA NOTIFICATION:")
            sample_notif = notifications[0]
            attributes = [attr for attr in dir(sample_notif) if not attr.startswith('_')]
            for attr in attributes[:10]:  # Primeiros 10
                try:
                    value = getattr(sample_notif, attr)
                    if not callable(value):
                        print(f"   • {attr}: {type(value).__name__}")
                except:
                    pass
        
        return user_ids_found
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        return set()

if __name__ == "__main__":
    asyncio.run(analyze_notifications()) 