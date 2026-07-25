#!/usr/bin/env python3
"""
DESCOBRIR USER_IDs VIA MENÇÕES/NOTIFICAÇÕES
Usa menções e notificações para descobrir quem pode ter enviado DMs
"""

import asyncio
import json
import logging
from pprint import pprint
from twikit import Client

logging.basicConfig(level=logging.WARNING)

class DMDiscoveryViaMentions:
    def __init__(self):
        self.client = None
        self.user_id = None
        
    async def initialize(self):
        with open("twitter_manual_cookies.json", 'r') as f:
            cookie_data = json.load(f)
        
        cookies = {}
        for name, value in cookie_data.items():
            if not name.startswith('_') and value:
                cookies[name] = value
        
        print("🔧 INICIALIZANDO...")
        self.client = Client(language='en-US')
        self.client.set_cookies(cookies)
        self.user_id = await self.client.user_id()
        print(f"✅ USER_ID: {self.user_id}")
        return True
        
    async def discover_potential_dm_users(self):
        """Descobre user_ids via menções e notificações"""
        potential_users = set()
        
        print("\n🔍 DESCOBRINDO USUÁRIOS VIA MENÇÕES...")
        
        # 1. Via notificações
        try:
            notifications = await self.client.get_notifications('All', count=50)
            for notif in notifications:
                if hasattr(notif, 'from_user') and notif.from_user:
                    potential_users.add(notif.from_user.id)
                    print(f"   📬 @{notif.from_user.screen_name} ({notif.from_user.id})")
        except Exception as e:
            print(f"   ❌ Erro nas notificações: {e}")
        
        # 2. Via timeline (quem você segue)
        try:
            timeline = await self.client.get_timeline(count=50)
            for tweet in timeline:
                if hasattr(tweet, 'user') and tweet.user:
                    potential_users.add(tweet.user.id)
        except Exception as e:
            print(f"   ❌ Erro na timeline: {e}")
        
        # 3. Via followers recentes
        try:
            user = await self.client.user()
            followers = await user.get_followers(count=50)
            for follower in followers:
                potential_users.add(follower.id)
                print(f"   👥 @{follower.screen_name} ({follower.id})")
        except Exception as e:
            print(f"   ❌ Erro nos followers: {e}")
        
        return list(potential_users)
    
    async def test_dms_with_users(self, user_ids):
        """Testa DMs com lista de user_ids descobertos"""
        print(f"\n🎯 TESTANDO DMs COM {len(user_ids)} USUÁRIOS...")
        
        found_conversations = []
        
        for i, user_id in enumerate(user_ids, 1):
            try:
                print(f"   {i:2d}. Testando {user_id}...", end=" ")
                
                dm_history = await self.client.get_dm_history(user_id)
                messages = list(dm_history)
                
                if messages:
                    from_them = [m for m in messages if m.sender_id == user_id]
                    total = len(messages)
                    received = len(from_them)
                    
                    print(f"✅ {total} msgs ({received} recebidas)")
                    
                    if from_them:
                        found_conversations.append({
                            'user_id': user_id,
                            'total_messages': total,
                            'received_from_them': from_them,
                            'latest_received': from_them[0]
                        })
                else:
                    print("⚪ Sem mensagens")
                    
            except Exception as e:
                print(f"❌ Erro: {str(e)[:30]}...")
        
        return found_conversations
    
    async def run_full_discovery(self):
        """Executa descoberta completa"""
        print("🚀 DESCOBERTA VIA MENÇÕES/NOTIFICAÇÕES")
        print("="*50)
        
        if not await self.initialize():
            return
        
        # Descobre user_ids
        user_ids = await self.discover_potential_dm_users()
        print(f"\n📋 DESCOBERTOS: {len(user_ids)} user_ids únicos")
        
        if not user_ids:
            print("❌ Nenhum user_id descoberto")
            return
        
        # Testa DMs
        conversations = await self.test_dms_with_users(user_ids)
        
        # Resultado
        print(f"\n📊 RESULTADO FINAL:")
        print(f"✅ Conversas DM encontradas: {len(conversations)}")
        
        if conversations:
            print(f"\n💬 CONVERSAS COM MENSAGENS RECEBIDAS:")
            for conv in conversations:
                latest = conv['latest_received']
                print(f"\n🔸 User {conv['user_id']}:")
                print(f"   Total: {conv['total_messages']} msgs")
                print(f"   Recebidas: {len(conv['received_from_them'])} msgs")
                print(f"   Última: \"{latest.text[:50]}...\"")
                print(f"   Timestamp: {latest.time}")

async def main():
    discovery = DMDiscoveryViaMentions()
    await discovery.run_full_discovery()

if __name__ == "__main__":
    print("""
    🔍 DESCOBERTA DM VIA MENÇÕES
    ============================
    
    Estratégia:
    1. Busca notificações/menções para descobrir user_ids
    2. Testa DMs com cada user_id descoberto  
    3. Encontra conversas DM existentes
    
    """)
    
    asyncio.run(main()) 