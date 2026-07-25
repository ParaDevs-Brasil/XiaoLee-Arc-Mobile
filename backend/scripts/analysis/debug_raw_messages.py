#!/usr/bin/env python3
"""
DEBUG RAW MESSAGES - Análise completa do que o twikit retorna
Mostra TODOS os parâmetros e estrutura das mensagens DM
"""

import asyncio
import json
import logging
from pathlib import Path
from pprint import pprint
from twikit import Client

# Setup logging detalhado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RawMessageAnalyzer:
    """Analisador de mensagens RAW do twikit"""
    
    def __init__(self):
        self.client = None
        self.user_id = None
        
    async def initialize(self):
        """Inicializa cliente twikit"""
        try:
            # Carrega cookies
            with open("twitter_manual_cookies.json", 'r') as f:
                cookie_data = json.load(f)
            
            # Filtra cookies
            cookies = {}
            for name, value in cookie_data.items():
                if not name.startswith('_') and value:
                    cookies[name] = value
            
            print(f"🔧 COOKIES CARREGADOS: {list(cookies.keys())}")
            
            # Inicializa twikit
            self.client = Client(language='en-US')
            self.client.set_cookies(cookies)
            
            # Extrai user_id
            if 'twid' in cookies:
                twid = cookies['twid']
                if 'u%3D' in twid:
                    self.user_id = twid.split('u%3D')[1]
                    print(f"✅ USER_ID: {self.user_id}")
            
            print("✅ TWIKIT INICIALIZADO")
            return True
            
        except Exception as e:
            print(f"❌ ERRO: {e}")
            return False

    async def analyze_user_method(self):
        """Tenta diferentes métodos para obter user info"""
        print("\n" + "="*50)
        print("🔍 TESTANDO MÉTODOS DE USER")
        print("="*50)
        
        # Método 1: user_id()
        try:
            user_id = await self.client.user_id()
            print(f"✅ client.user_id(): {user_id}")
            self.user_id = user_id
        except Exception as e:
            print(f"❌ client.user_id() falhou: {e}")
        
        # Método 2: user()
        try:
            user = await self.client.user()
            print(f"✅ client.user(): {user}")
            print(f"   - ID: {user.id}")
            print(f"   - Screen Name: {user.screen_name}")
            print(f"   - Name: {user.name}")
            
            # RAW data do user
            print(f"\n📋 USER RAW DATA:")
            if hasattr(user, '_data'):
                pprint(user._data)
            else:
                print("   Sem _data disponível")
                
        except Exception as e:
            print(f"❌ client.user() falhou: {e}")

    async def find_dm_conversations(self):
        """Busca conversas DM usando diferentes métodos"""
        print("\n" + "="*50)
        print("🔍 BUSCANDO CONVERSAS DM")
        print("="*50)
        
        if not self.user_id:
            print("❌ USER_ID necessário")
            return []
        
        # Método: tentar get_dm_history com IDs conhecidos
        # Primeiro, vamos tentar alguns user_ids comuns ou conhecidos
        
        test_user_ids = []
        
        # Pede user_id para testar
        print("💡 Para testar, digite um user_id conhecido (ou Enter para pular):")
        test_id = input("User ID: ").strip()
        if test_id:
            test_user_ids.append(test_id)
        
        conversations = []
        
        for user_id in test_user_ids:
            try:
                print(f"\n🔍 Testando conversa com user_id: {user_id}")
                
                # Busca histórico DM
                dm_result = await self.client.get_dm_history(user_id)
                
                print(f"✅ RESULTADO get_dm_history({user_id}):")
                print(f"   Tipo: {type(dm_result)}")
                
                # Analisa estrutura do resultado
                if hasattr(dm_result, '__iter__'):
                    messages = list(dm_result)
                    print(f"   Total mensagens: {len(messages)}")
                    
                    for i, message in enumerate(messages[:3]):  # Primeiras 3
                        await self.analyze_message_raw(message, f"Msg {i+1}")
                        
                    conversations.append({
                        'user_id': user_id,
                        'message_count': len(messages),
                        'messages': messages[:5]  # Salva primeiras 5
                    })
                else:
                    print(f"   Resultado não iterável: {dm_result}")
                
            except Exception as e:
                print(f"❌ Erro com user_id {user_id}: {e}")
        
        return conversations

    async def analyze_message_raw(self, message, label="Message"):
        """Analisa uma mensagem em modo RAW"""
        print(f"\n📨 {label.upper()}:")
        print("-" * 30)
        
        # Atributos básicos
        try:
            print(f"   ID: {message.id}")
            print(f"   Text: {message.text}")
            print(f"   Time: {message.time}")
            print(f"   Sender ID: {message.sender_id}")
            print(f"   Recipient ID: {message.recipient_id}")
            
            if hasattr(message, 'attachment') and message.attachment:
                print(f"   Attachment: {message.attachment}")
            
        except Exception as e:
            print(f"   ❌ Erro nos atributos básicos: {e}")
        
        # Dados RAW completos
        try:
            print(f"\n📋 RAW DATA ({label}):")
            if hasattr(message, '_data'):
                pprint(message._data, width=80, depth=3)
            elif hasattr(message, '__dict__'):
                pprint(message.__dict__, width=80, depth=3)
            else:
                print(f"   Tipo: {type(message)}")
                print(f"   Repr: {repr(message)}")
                
        except Exception as e:
            print(f"   ❌ Erro nos dados RAW: {e}")
        
        # Métodos disponíveis
        try:
            methods = [attr for attr in dir(message) 
                      if not attr.startswith('_') and callable(getattr(message, attr))]
            print(f"\n🔧 MÉTODOS DISPONÍVEIS ({label}):")
            for method in methods[:10]:  # Primeiros 10
                print(f"   - {method}()")
                
        except Exception as e:
            print(f"   ❌ Erro listando métodos: {e}")

    async def test_streaming_setup(self):
        """Testa setup de streaming para ver estrutura"""
        print("\n" + "="*50)
        print("🔍 TESTANDO STREAMING SETUP")
        print("="*50)
        
        try:
            from twikit.streaming import Topic
            
            # Cria topic de teste
            if self.user_id:
                # Tenta criar conversation_id
                test_conv_id = f"test_user-{self.user_id}"
                
                topic_dm_update = Topic.dm_update(test_conv_id)
                topic_dm_typing = Topic.dm_typing(test_conv_id)
                
                print(f"✅ TOPIC DM UPDATE: {topic_dm_update}")
                print(f"✅ TOPIC DM TYPING: {topic_dm_typing}")
                
                # Tenta criar sessão (sem conectar)
                topics = {topic_dm_update, topic_dm_typing}
                print(f"✅ TOPICS SET: {topics}")
                
                # NÃO vamos conectar agora, só mostrar estrutura
                print("💡 Estrutura de streaming preparada (não conectada)")
                
        except Exception as e:
            print(f"❌ Erro no streaming setup: {e}")

    async def run_full_analysis(self):
        """Executa análise completa"""
        print("🚀 INICIANDO ANÁLISE RAW COMPLETA")
        print("="*60)
        
        # 1. Inicializa
        if not await self.initialize():
            return
        
        # 2. Analisa user methods
        await self.analyze_user_method()
        
        # 3. Busca conversas
        conversations = await self.find_dm_conversations()
        
        # 4. Testa streaming setup
        await self.test_streaming_setup()
        
        # 5. Resumo final
        print("\n" + "="*50)
        print("📊 RESUMO FINAL")
        print("="*50)
        print(f"✅ User ID: {self.user_id}")
        print(f"✅ Conversas encontradas: {len(conversations)}")
        print(f"✅ Cliente inicializado: {self.client is not None}")
        
        for conv in conversations:
            print(f"   📂 Conversa {conv['user_id']}: {conv['message_count']} mensagens")

async def main():
    """Função principal"""
    analyzer = RawMessageAnalyzer()
    await analyzer.run_full_analysis()

if __name__ == "__main__":
    print("""
    🔍 ANALISADOR RAW DE MENSAGENS TWIKIT
    ====================================
    
    Este script vai mostrar:
    - Estrutura RAW das mensagens DM
    - Todos os parâmetros disponíveis
    - Métodos do twikit Client
    - Setup de streaming
    
    Preparado para análise completa...
    """)
    
    asyncio.run(main()) 