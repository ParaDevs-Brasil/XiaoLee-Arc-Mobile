#!/usr/bin/env python3
"""
DEBUG RAW AUTO - Busca todas as mensagens DM existentes automaticamente
Mostra TUDO em modo RAW sem precisar de input manual
"""

import asyncio
import json
import logging
from pprint import pprint
from twikit import Client

# Disable verbose logging
logging.basicConfig(level=logging.WARNING)

class AutoRawAnalyzer:
    """Analisador automático de mensagens RAW"""
    
    def __init__(self):
        self.client = None
        self.user_id = None
        
    async def initialize(self):
        """Inicializa cliente twikit automaticamente"""
        try:
            # Carrega cookies
            with open("twitter_manual_cookies.json", 'r') as f:
                cookie_data = json.load(f)
            
            # Filtra cookies
            cookies = {}
            for name, value in cookie_data.items():
                if not name.startswith('_') and value:
                    cookies[name] = value
            
            print(f"🔧 COOKIES: {list(cookies.keys())}")
            
            # Inicializa twikit
            self.client = Client(language='en-US')
            self.client.set_cookies(cookies)
            
            # Obtém user_id automaticamente
            self.user_id = await self.client.user_id()
            
            print(f"✅ USER_ID: {self.user_id}")
            print(f"✅ TWIKIT READY")
            return True
            
        except Exception as e:
            print(f"❌ ERRO: {e}")
            return False

    async def get_all_dm_conversations(self):
        """Tenta descobrir TODAS as conversas DM automaticamente"""
        print("\n" + "="*60)
        print("🔍 DESCOBRINDO CONVERSAS DM EXISTENTES")
        print("="*60)
        
        conversations = []
        
        # MÉTODO 1: Tentar com followers recentes
        try:
            print("📋 MÉTODO 1: Buscando followers...")
            user = await self.client.user()
            followers = await user.get_followers(count=20)
            
            print(f"   Testando {len(followers)} followers...")
            
            for i, follower in enumerate(followers[:5]):  # Testa primeiros 5
                try:
                    print(f"   📨 Testando DM com: {follower.screen_name} ({follower.id})")
                    
                    dm_history = await self.client.get_dm_history(follower.id)
                    messages = list(dm_history)
                    
                    if messages:
                        print(f"   ✅ ENCONTROU {len(messages)} mensagens!")
                        conversations.append({
                            'user_id': follower.id,
                            'screen_name': follower.screen_name,
                            'message_count': len(messages),
                            'messages': messages
                        })
                        
                        # Analisa primeira mensagem
                        await self.analyze_message_detailed(messages[0], f"Conversa {follower.screen_name}")
                    
                except Exception as e:
                    print(f"   ⚪ Sem mensagens com {follower.screen_name}: {e}")
                    
        except Exception as e:
            print(f"❌ Erro no método followers: {e}")
        
        # MÉTODO 2: Tentar com following
        try:
            print("\n📋 MÉTODO 2: Buscando following...")
            user = await self.client.user()
            following = await user.get_following(count=20)
            
            print(f"   Testando {len(following)} following...")
            
            for follower in following[:5]:  # Testa primeiros 5
                try:
                    # Pula se já testado
                    if any(c['user_id'] == follower.id for c in conversations):
                        continue
                        
                    print(f"   📨 Testando DM com: {follower.screen_name} ({follower.id})")
                    
                    dm_history = await self.client.get_dm_history(follower.id)
                    messages = list(dm_history)
                    
                    if messages:
                        print(f"   ✅ ENCONTROU {len(messages)} mensagens!")
                        conversations.append({
                            'user_id': follower.id,
                            'screen_name': follower.screen_name,
                            'message_count': len(messages),
                            'messages': messages
                        })
                        
                        # Analisa primeira mensagem
                        await self.analyze_message_detailed(messages[0], f"Conversa {follower.screen_name}")
                    
                except Exception as e:
                    print(f"   ⚪ Sem mensagens com {follower.screen_name}: {e}")
                    
        except Exception as e:
            print(f"❌ Erro no método following: {e}")
        
        # MÉTODO 3: Tentar IDs conhecidos/comuns
        print("\n📋 MÉTODO 3: Testando IDs conhecidos...")
        
        # IDs de teste (Twitter oficial, etc)
        test_ids = [
            "783214",     # Twitter
            "50393960",   # Twitter Dev
            "17874544",   # Twitter Support
            self.user_id  # Próprio ID (mensagens salvas)
        ]
        
        for test_id in test_ids:
            try:
                if test_id == self.user_id:
                    print(f"   📨 Testando mensagens próprias...")
                else:
                    print(f"   📨 Testando ID: {test_id}")
                
                dm_history = await self.client.get_dm_history(test_id)
                messages = list(dm_history)
                
                if messages:
                    print(f"   ✅ ENCONTROU {len(messages)} mensagens!")
                    conversations.append({
                        'user_id': test_id,
                        'screen_name': f"ID_{test_id}",
                        'message_count': len(messages),
                        'messages': messages
                    })
                    
                    # Analisa primeira mensagem
                    await self.analyze_message_detailed(messages[0], f"ID {test_id}")
                
            except Exception as e:
                print(f"   ⚪ Sem mensagens com ID {test_id}: {e}")
        
        return conversations

    async def analyze_message_detailed(self, message, label):
        """Análise COMPLETA de uma mensagem"""
        print(f"\n📨 MENSAGEM RAW - {label.upper()}")
        print("=" * 50)
        
        # ATRIBUTOS BÁSICOS
        print("🔸 ATRIBUTOS BÁSICOS:")
        try:
            print(f"   ID: {message.id}")
            print(f"   Text: '{message.text}'")
            print(f"   Time: {message.time}")
            print(f"   Sender ID: {message.sender_id}")
            print(f"   Recipient ID: {message.recipient_id}")
            
            if hasattr(message, 'attachment') and message.attachment:
                print(f"   Attachment: {message.attachment}")
            else:
                print("   Attachment: None")
                
        except Exception as e:
            print(f"   ❌ Erro: {e}")
        
        # TODOS OS ATRIBUTOS
        print("\n🔸 TODOS OS ATRIBUTOS:")
        try:
            attrs = [attr for attr in dir(message) if not attr.startswith('_')]
            for attr in attrs:
                try:
                    value = getattr(message, attr)
                    if not callable(value):
                        print(f"   {attr}: {value}")
                except:
                    print(f"   {attr}: <erro ao acessar>")
        except Exception as e:
            print(f"   ❌ Erro: {e}")
        
        # MÉTODOS DISPONÍVEIS
        print("\n🔸 MÉTODOS DISPONÍVEIS:")
        try:
            methods = [attr for attr in dir(message) 
                      if not attr.startswith('_') and callable(getattr(message, attr))]
            for method in methods:
                print(f"   {method}()")
        except Exception as e:
            print(f"   ❌ Erro: {e}")
        
        # DADOS RAW INTERNOS
        print("\n🔸 DADOS RAW INTERNOS:")
        try:
            if hasattr(message, '_data'):
                print("   _data encontrado:")
                pprint(message._data, width=60, depth=2)
            elif hasattr(message, '__dict__'):
                print("   __dict__:")
                pprint(message.__dict__, width=60, depth=2)
            else:
                print(f"   Tipo: {type(message)}")
                print(f"   Repr: {repr(message)}")
        except Exception as e:
            print(f"   ❌ Erro: {e}")

    async def run_analysis(self):
        """Executa análise completa automática"""
        print("🚀 ANÁLISE RAW AUTOMÁTICA - TODAS AS MENSAGENS")
        print("="*70)
        
        # 1. Inicializa
        if not await self.initialize():
            return
        
        # 2. Busca todas as conversas
        conversations = await self.get_all_dm_conversations()
        
        # 3. Resumo final
        print("\n" + "="*60)
        print("📊 RESUMO FINAL")
        print("="*60)
        print(f"✅ User ID: {self.user_id}")
        print(f"✅ Conversas encontradas: {len(conversations)}")
        
        for i, conv in enumerate(conversations, 1):
            print(f"\n📂 CONVERSA {i}:")
            print(f"   User ID: {conv['user_id']}")
            print(f"   Screen Name: {conv['screen_name']}")
            print(f"   Total Mensagens: {conv['message_count']}")
            
            # Mostra primeiras 3 mensagens de cada conversa
            print(f"   📋 MENSAGENS (primeiras 3):")
            for j, msg in enumerate(conv['messages'][:3], 1):
                print(f"      {j}. [{msg.sender_id}] {msg.text[:50]}...")

async def main():
    analyzer = AutoRawAnalyzer()
    await analyzer.run_analysis()

if __name__ == "__main__":
    print("""
    🔍 AUTO RAW ANALYZER - MENSAGENS DM
    ===================================
    
    Busca AUTOMATICAMENTE todas as conversas DM
    e mostra dados RAW completos SEM interação.
    
    Iniciando...
    """)
    
    asyncio.run(main()) 