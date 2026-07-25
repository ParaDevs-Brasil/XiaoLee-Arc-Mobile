#!/usr/bin/env python3
"""
RAW DM Analysis Test - Twikit Structure Investigation
Testa estrutura real de DMs e métodos de discovery
"""

import asyncio
import json
import logging
from datetime import datetime

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

# Configure simple logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class DMRawAnalyzer:
    """Analisador RAW de DMs do twikit"""
    
    def __init__(self):
        self.client = Client('en-US')
        self.authenticated = False
    
    async def connect(self):
        """Conectar usando cookies"""
        try:
            print("🔄 Carregando cookies...")
            self.client.load_cookies("twitter_manual_cookies.json")
            
            # Verificar autenticação
            user = await self.client.user()
            self.authenticated = True
            
            print(f"✅ Conectado como: @{user.screen_name} (ID: {user.id})")
            return True
            
        except Exception as e:
            print(f"❌ Erro na conexão: {e}")
            return False
    
    async def test_dm_with_known_user(self, user_id: str):
        """Testar DMs com user_id conhecido"""
        print(f"\n=== TESTE DM COM USER_ID: {user_id} ===")
        
        try:
            # Pegar histórico de DMs
            dm_result = await self.client.get_dm_history(user_id)
            
            print(f"📊 RESULTADO TYPE: {type(dm_result)}")
            print(f"📊 RESULTADO LENGTH: {len(dm_result) if dm_result else 0}")
            
            if dm_result:
                print(f"📊 PRIMEIRO ITEM TYPE: {type(dm_result[0])}")
                
                # Analisar primeiro DM
                first_dm = dm_result[0]
                print(f"\n📨 PRIMEIRA MENSAGEM:")
                print(f"   ID: {getattr(first_dm, 'id', 'N/A')}")
                print(f"   Text: {getattr(first_dm, 'text', 'N/A')}")
                print(f"   Time: {getattr(first_dm, 'time', 'N/A')}")
                print(f"   Sender ID: {getattr(first_dm, 'sender_id', 'N/A')}")
                print(f"   Recipient ID: {getattr(first_dm, 'recipient_id', 'N/A')}")
                
                # Mostrar todos os atributos
                print(f"\n🔍 TODOS OS ATRIBUTOS:")
                for attr in dir(first_dm):
                    if not attr.startswith('_'):
                        try:
                            value = getattr(first_dm, attr)
                            if not callable(value):
                                print(f"   {attr}: {value}")
                        except:
                            print(f"   {attr}: <erro ao acessar>")
                
                # Mostrar estrutura de mais mensagens
                print(f"\n📋 OVERVIEW DE TODAS AS MENSAGENS:")
                for i, dm in enumerate(dm_result[:5]):  # Primeiras 5
                    sender = getattr(dm, 'sender_id', 'N/A')
                    text = getattr(dm, 'text', 'N/A')[:50]
                    time = getattr(dm, 'time', 'N/A')
                    print(f"   {i+1}. Sender: {sender} | Text: {text}... | Time: {time}")
            
            else:
                print("❌ Nenhuma mensagem encontrada")
                
        except Exception as e:
            print(f"❌ Erro ao testar DMs: {e}")
            import traceback
            traceback.print_exc()
    
    async def test_discovery_methods(self):
        """Testar métodos alternativos de discovery"""
        print(f"\n=== TESTE DE DISCOVERY METHODS ===")
        
        # Método 1: Tentar buscar notificações
        try:
            print("🔍 Testando notifications...")
            notifications = await self.client.get_notifications('All', count=10)
            print(f"📊 Notifications encontradas: {len(notifications)}")
            
            for i, notif in enumerate(notifications[:3]):
                print(f"   {i+1}. Type: {type(notif)} | {getattr(notif, 'id', 'N/A')}")
                
        except Exception as e:
            print(f"❌ Erro nas notifications: {e}")
        
        # Método 2: Investigar métodos do client
        print(f"\n🔍 MÉTODOS DISPONÍVEIS NO CLIENT:")
        dm_methods = [method for method in dir(self.client) if 'dm' in method.lower()]
        for method in dm_methods:
            print(f"   {method}")
        
        message_methods = [method for method in dir(self.client) if 'message' in method.lower()]
        for method in message_methods:
            print(f"   {method}")
    
    async def test_user_discovery(self):
        """Tentar descobrir user_ids de DMs recentes"""
        print(f"\n=== TESTE USER DISCOVERY ===")
        
        try:
            # Testar busca por conversas (pode não existir)
            print("🔍 Procurando métodos de conversation...")
            
            conv_methods = [method for method in dir(self.client) if 'conv' in method.lower()]
            print(f"📋 Métodos com 'conv': {conv_methods}")
            
            chat_methods = [method for method in dir(self.client) if 'chat' in method.lower()]
            print(f"📋 Métodos com 'chat': {chat_methods}")
            
            # Verificar se existe algum método útil
            if hasattr(self.client, 'get_conversations'):
                print("🎯 Encontrou get_conversations! Testando...")
                conversations = await self.client.get_conversations()
                print(f"📊 Conversations: {conversations}")
            
        except Exception as e:
            print(f"❌ Erro no user discovery: {e}")
    
    async def run_full_analysis(self):
        """Executar análise completa"""
        print("🧪 INICIANDO ANÁLISE RAW DE DMs")
        print("=" * 50)
        
        # Conectar
        if not await self.connect():
            return
        
        # Testar discovery methods primeiro
        await self.test_discovery_methods()
        await self.test_user_discovery()
        
        # Perguntar por user_id para testar
        print(f"\n" + "=" * 50)
        print("📝 PARA TESTAR DMs, PRECISO DE UM USER_ID VÁLIDO")
        print("💡 Opções para obter user_id:")
        print("   1. Usar client.get_user_by_screen_name('@username')")
        print("   2. Manualmente de quem te mandou DM")
        print("   3. Procurar no DevTools do browser")
        
        # Testar com user_id conhecidos (se especificado)
        test_user_ids = [
            # "USER_ID_AQUI",  # Substituir por IDs reais
        ]
        
        for user_id in test_user_ids:
            await self.test_dm_with_known_user(user_id)
        
        if not test_user_ids:
            print("\n⚠️ Nenhum user_id especificado para teste")
            print("💡 Edite o arquivo e adicione user_ids na lista test_user_ids")

async def main():
    """Função principal"""
    analyzer = DMRawAnalyzer()
    await analyzer.run_full_analysis()

if __name__ == "__main__":
    print("""
    🧪 RAW DM ANALYSIS TEST
    =======================
    
    Este teste vai investigar:
    ✅ Como twikit estrutura DMs
    ✅ Que dados estão disponíveis  
    ✅ Métodos de discovery
    ✅ Como identificar conversas ativas
    
    """)
    
    asyncio.run(main()) 