#!/usr/bin/env python3
"""
ANALISADOR DE NOTIFICATIONS CORRIGIDO
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
    
    # Tipos de notifications do twikit
    notification_types = ['All', 'Verified', 'Mentions']
    
    try:
        for notif_type in notification_types:
            print(f"\n📬 BUSCANDO NOTIFICATIONS TIPO: {notif_type}")
            print("-" * 50)
            
            try:
                notifications = await client.get_notifications(notif_type)
                print(f"📊 TOTAL ENCONTRADAS: {len(notifications)}")
                
                if not notifications:
                    print("   ⚪ Nenhuma notification encontrada")
                    continue
                
                # Analisa primeiras 5 notifications
                user_ids_found = set()
                
                for i, notif in enumerate(notifications[:5]):
                    print(f"\n🔔 NOTIFICATION #{i+1}:")
                    print("   " + "-" * 35)
                    
                    # Mostra todos os atributos disponíveis
                    print(f"   📋 ATRIBUTOS:")
                    attributes = [attr for attr in dir(notif) if not attr.startswith('_')]
                    
                    for attr in attributes:
                        try:
                            value = getattr(notif, attr)
                            if not callable(value) and value is not None:
                                if isinstance(value, str) and len(value) > 50:
                                    print(f"      • {attr}: {value[:50]}...")
                                else:
                                    print(f"      • {attr}: {value}")
                                    
                                # Se é user, pega o ID
                                if attr == 'user' and hasattr(value, 'id'):
                                    user_ids_found.add(value.id)
                                    print(f"         └─ USER_ID: {value.id}")
                                    
                        except Exception as e:
                            print(f"      • {attr}: <erro: {e}>")
                
                print(f"\n   👥 USER_IDs DESCOBERTOS: {user_ids_found}")
                print(f"   📋 Total único: {len(user_ids_found)}")
                
            except Exception as e:
                print(f"   ❌ ERRO ao buscar {notif_type}: {e}")
        
        print("\n🎯 TENTANDO OUTROS MÉTODOS...")
        print("="*60)
        
        # Tenta outros métodos do twikit
        try:
            print("📱 Tentando get_timeline()...")
            timeline = await client.get_timeline()
            print(f"   ✅ Timeline: {len(timeline)} tweets")
            
            # Analisa users da timeline
            timeline_users = set()
            for tweet in timeline[:5]:
                if hasattr(tweet, 'user') and tweet.user:
                    timeline_users.add(tweet.user.id)
            print(f"   👥 Users na timeline: {timeline_users}")
            
        except Exception as e:
            print(f"   ❌ Timeline erro: {e}")
        
        try:
            print("🔍 Tentando search('notifications')...")
            search_results = await client.search('notifications', count=5)
            print(f"   ✅ Search: {len(search_results)} resultados")
            
        except Exception as e:
            print(f"   ❌ Search erro: {e}")
        
        print(f"\n💡 CONCLUSÃO:")
        print("="*60)
        print("📬 NOTIFICATIONS contêm:")
        print("   • User IDs de quem interagiu com você")
        print("   • Tipos: menções, likes, retweets, follows")
        print("   • Timestamps das interações")
        print("   • Links para tweets/conteúdo")
        print("\n🎯 USO PARA DMs:")
        print("   • Se alguém te menciona/segue → pode ter mandado DM")
        print("   • Pegamos user_id das notifications")
        print("   • Testamos get_dm_history(user_id)")
        print("   • = Descobrimos conversas DM!")
        
    except Exception as e:
        print(f"❌ ERRO GERAL: {e}")

if __name__ == "__main__":
    asyncio.run(analyze_notifications()) 