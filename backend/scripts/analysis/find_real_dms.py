#!/usr/bin/env python3
"""
BUSCA DMs REAIS - Encontra mensagens de OUTROS usuários
Métodos avançados para descobrir conversas DM existentes
"""

import asyncio
import json
import logging
from pprint import pprint
from twikit import Client

# Disable verbose logging
logging.basicConfig(level=logging.WARNING)

class RealDMFinder:
    """Encontrador de DMs reais de outros usuários"""
    
    def __init__(self):
        self.client = None
        self.user_id = None
        
    async def initialize(self):
        """Inicializa cliente twikit"""
        try:
            with open("twitter_manual_cookies.json", 'r') as f:
                cookie_data = json.load(f)
            
            cookies = {}
            for name, value in cookie_data.items():
                if not name.startswith('_') and value:
                    cookies[name] = value
            
            print(f"🔧 INICIALIZANDO...")
            
            self.client = Client(language='en-US')
            self.client.set_cookies(cookies)
            self.user_id = await self.client.user_id()
            
            print(f"✅ USER_ID: {self.user_id}")
            return True
            
        except Exception as e:
            print(f"❌ ERRO: {e}")
            return False

    async def method_1_recent_followers(self):
        """MÉTODO 1: Busca DMs com followers recentes"""
        print("\n🔍 MÉTODO 1: FOLLOWERS RECENTES")
        print("-" * 40)
        
        try:
            user = await self.client.user()
            followers = await user.get_followers(count=50)  # Mais followers
            
            print(f"📋 Testando {len(followers)} followers...")
            
            found_convs = []
            
            for i, follower in enumerate(followers):
                try:
                    print(f"   {i+1:2d}. Testando @{follower.screen_name}...")
                    
                    dm_history = await self.client.get_dm_history(follower.id)
                    messages = list(dm_history)
                    
                    if messages:
                        # Filtra mensagens de OUTROS (não próprias)
                        other_messages = [m for m in messages if m.sender_id != self.user_id]
                        
                        if other_messages:
                            print(f"       ✅ {len(other_messages)} mensagens de @{follower.screen_name}!")
                            found_convs.append({
                                'user_id': follower.id,
                                'screen_name': follower.screen_name,
                                'other_messages': other_messages,
                                'total_messages': len(messages)
                            })
                            
                            # Mostra primeira mensagem do outro usuário
                            first_msg = other_messages[0]
                            print(f"       📨 \"{first_msg.text[:40]}...\"")
                        else:
                            print(f"       ⚪ Só mensagens próprias")
                    else:
                        print(f"       ⚪ Sem mensagens")
                        
                except Exception as e:
                    print(f"       ❌ Erro: {str(e)[:30]}...")
                    
            return found_convs
            
        except Exception as e:
            print(f"❌ Erro no método 1: {e}")
            return []

    async def method_2_recent_following(self):
        """MÉTODO 2: Busca DMs com quem você segue"""
        print("\n🔍 MÉTODO 2: FOLLOWING RECENTES")
        print("-" * 40)
        
        try:
            user = await self.client.user()
            following = await user.get_following(count=50)
            
            print(f"📋 Testando {len(following)} following...")
            
            found_convs = []
            
            for i, followed in enumerate(following):
                try:
                    print(f"   {i+1:2d}. Testando @{followed.screen_name}...")
                    
                    dm_history = await self.client.get_dm_history(followed.id)
                    messages = list(dm_history)
                    
                    if messages:
                        other_messages = [m for m in messages if m.sender_id != self.user_id]
                        
                        if other_messages:
                            print(f"       ✅ {len(other_messages)} mensagens de @{followed.screen_name}!")
                            found_convs.append({
                                'user_id': followed.id,
                                'screen_name': followed.screen_name,
                                'other_messages': other_messages,
                                'total_messages': len(messages)
                            })
                            
                            first_msg = other_messages[0]
                            print(f"       📨 \"{first_msg.text[:40]}...\"")
                        else:
                            print(f"       ⚪ Só mensagens próprias")
                    else:
                        print(f"       ⚪ Sem mensagens")
                        
                except Exception as e:
                    print(f"       ❌ Erro: {str(e)[:30]}...")
                    
            return found_convs
            
        except Exception as e:
            print(f"❌ Erro no método 2: {e}")
            return []

    async def method_3_notification_scan(self):
        """MÉTODO 3: Busca via notificações (usuários que interagiram)"""
        print("\n🔍 MÉTODO 3: SCAN DE NOTIFICAÇÕES")
        print("-" * 40)
        
        try:
            notifications = await self.client.get_notifications('All', count=50)
            
            print(f"📋 Analisando {len(notifications)} notificações...")
            
            found_convs = []
            tested_users = set()
            
            for i, notif in enumerate(notifications):
                try:
                    from_user = notif.from_user
                    
                    if from_user.id in tested_users or from_user.id == self.user_id:
                        continue
                        
                    tested_users.add(from_user.id)
                    
                    print(f"   {i+1:2d}. Testando @{from_user.screen_name} (via notificação)...")
                    
                    dm_history = await self.client.get_dm_history(from_user.id)
                    messages = list(dm_history)
                    
                    if messages:
                        other_messages = [m for m in messages if m.sender_id != self.user_id]
                        
                        if other_messages:
                            print(f"       ✅ {len(other_messages)} mensagens de @{from_user.screen_name}!")
                            found_convs.append({
                                'user_id': from_user.id,
                                'screen_name': from_user.screen_name,
                                'other_messages': other_messages,
                                'total_messages': len(messages)
                            })
                            
                            first_msg = other_messages[0]
                            print(f"       📨 \"{first_msg.text[:40]}...\"")
                        
                except Exception as e:
                    print(f"       ❌ Erro: {str(e)[:30]}...")
                    
            return found_convs
            
        except Exception as e:
            print(f"❌ Erro no método 3: {e}")
            return []

    async def method_4_search_common_users(self):
        """MÉTODO 4: Testa usuários comuns do Twitter"""
        print("\n🔍 MÉTODO 4: USUÁRIOS COMUNS/CONHECIDOS")
        print("-" * 40)
        
        # Lista de usuários conhecidos para testar
        common_users = [
            ("783214", "Twitter"),
            ("50393960", "TwitterDev"),
            ("17874544", "TwitterSupport"),
            ("6253282", "Twitter"),
            ("1526228120", "TwitterSafety"),
        ]
        
        found_convs = []
        
        for user_id, username in common_users:
            try:
                print(f"   Testando @{username} ({user_id})...")
                
                dm_history = await self.client.get_dm_history(user_id)
                messages = list(dm_history)
                
                if messages:
                    other_messages = [m for m in messages if m.sender_id != self.user_id]
                    
                    if other_messages:
                        print(f"       ✅ {len(other_messages)} mensagens de @{username}!")
                        found_convs.append({
                            'user_id': user_id,
                            'screen_name': username,
                            'other_messages': other_messages,
                            'total_messages': len(messages)
                        })
                        
                        first_msg = other_messages[0]
                        print(f"       📨 \"{first_msg.text[:40]}...\"")
                    
            except Exception as e:
                print(f"       ❌ Erro com @{username}: {str(e)[:30]}...")
                
        return found_convs

    async def analyze_real_message(self, message, sender_info):
        """Analisa mensagem REAL de outro usuário"""
        print(f"\n📨 MENSAGEM REAL - @{sender_info['screen_name']}")
        print("=" * 60)
        
        print("🔸 DADOS DA MENSAGEM:")
        print(f"   ID: {message.id}")
        print(f"   Texto: '{message.text}'")
        print(f"   Timestamp: {message.time}")
        print(f"   De: {message.sender_id} (@{sender_info['screen_name']})")
        print(f"   Para: {message.recipient_id} (você)")
        
        if message.attachment:
            print(f"   Anexo: {message.attachment}")
        
        print("\n🔸 ESTRUTURA RAW:")
        pprint(message.__dict__, width=60, depth=2)
        
        print("\n🔸 MÉTODOS DISPONÍVEIS:")
        methods = [attr for attr in dir(message) 
                  if not attr.startswith('_') and callable(getattr(message, attr))]
        for method in methods:
            print(f"   {method}()")

    async def run_full_search(self):
        """Executa busca completa por DMs reais"""
        print("🚀 BUSCA COMPLETA POR DMs REAIS DE OUTROS USUÁRIOS")
        print("="*70)
        
        if not await self.initialize():
            return
        
        all_conversations = []
        
        # Executa todos os métodos
        methods = [
            ("FOLLOWERS", self.method_1_recent_followers),
            ("FOLLOWING", self.method_2_recent_following), 
            ("NOTIFICAÇÕES", self.method_3_notification_scan),
            ("USUÁRIOS COMUNS", self.method_4_search_common_users)
        ]
        
        for method_name, method_func in methods:
            try:
                print(f"\n🔄 EXECUTANDO: {method_name}")
                convs = await method_func()
                all_conversations.extend(convs)
                print(f"✅ {method_name}: {len(convs)} conversas encontradas")
                
            except Exception as e:
                print(f"❌ {method_name} falhou: {e}")
        
        # Remove duplicatas
        unique_convs = {}
        for conv in all_conversations:
            unique_convs[conv['user_id']] = conv
        
        final_convs = list(unique_convs.values())
        
        # Resumo final
        print("\n" + "="*60)
        print("📊 RESUMO FINAL - DMs REAIS ENCONTRADAS")
        print("="*60)
        print(f"✅ Total de conversas com outros usuários: {len(final_convs)}")
        
        if final_convs:
            print("\n📋 CONVERSAS ENCONTRADAS:")
            for i, conv in enumerate(final_convs, 1):
                print(f"\n{i}. @{conv['screen_name']} ({conv['user_id']})")
                print(f"   💬 {len(conv['other_messages'])} mensagens recebidas")
                print(f"   📊 {conv['total_messages']} mensagens total")
                
                # Analisa primeira mensagem
                if conv['other_messages']:
                    await self.analyze_real_message(conv['other_messages'][0], conv)
        else:
            print("\n⚠️ NENHUMA CONVERSA COM OUTROS USUÁRIOS ENCONTRADA")
            print("💡 Possíveis razões:")
            print("   - Conta nova sem DMs recebidas")
            print("   - DMs em configuração privada")
            print("   - Rate limits do Twitter")
            print("   - Conversas muito antigas")

async def main():
    finder = RealDMFinder()
    await finder.run_full_search()

if __name__ == "__main__":
    print("""
    🔍 BUSCA DMs REAIS - OUTROS USUÁRIOS
    ====================================
    
    Este script busca especificamente mensagens DM
    enviadas por OUTROS usuários para você.
    
    Métodos usados:
    1. Followers recentes
    2. Following recentes  
    3. Usuários de notificações
    4. Usuários comuns/conhecidos
    
    Iniciando busca avançada...
    """)
    
    asyncio.run(main()) 