#!/usr/bin/env python3
"""
SCANNER DM AVANÇADO - Usa TODOS os parâmetros do twikit
Implementa flags e técnicas avançadas para encontrar DMs reais
"""

import asyncio
import json
import logging
from pprint import pprint
from twikit import Client

# Disable verbose logging
logging.basicConfig(level=logging.WARNING)

class AdvancedDMScanner:
    """Scanner DM com parâmetros avançados do twikit"""
    
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
            
            print(f"🔧 INICIALIZANDO COM PARÂMETROS AVANÇADOS...")
            
            self.client = Client(language='en-US')
            self.client.set_cookies(cookies)
            self.user_id = await self.client.user_id()
            
            print(f"✅ USER_ID: {self.user_id}")
            return True
            
        except Exception as e:
            print(f"❌ ERRO: {e}")
            return False

    async def advanced_dm_search(self, user_id: str):
        """Busca avançada de DMs com TODOS os parâmetros"""
        print(f"\n🔍 BUSCA AVANÇADA DM - USER {user_id}")
        print("=" * 60)
        
        try:
            # MÉTODO 1: get_dm_history SEM max_id (padrão)
            print("\n📋 MÉTODO 1: get_dm_history() padrão")
            print("-" * 40)
            
            dm_history_1 = await self.client.get_dm_history(user_id)
            messages_1 = list(dm_history_1)
            
            print(f"   Mensagens encontradas: {len(messages_1)}")
            if messages_1:
                for i, msg in enumerate(messages_1[:3], 1):
                    print(f"   {i}. ID: {msg.id}, Texto: '{msg.text[:30]}...', Sender: {msg.sender_id}")
            
            # MÉTODO 2: get_dm_history COM max_id=None explícito  
            print("\n📋 MÉTODO 2: get_dm_history(max_id=None)")
            print("-" * 40)
            
            dm_history_2 = await self.client.get_dm_history(user_id, max_id=None)
            messages_2 = list(dm_history_2)
            
            print(f"   Mensagens encontradas: {len(messages_2)}")
            if messages_2:
                for i, msg in enumerate(messages_2[:3], 1):
                    print(f"   {i}. ID: {msg.id}, Texto: '{msg.text[:30]}...', Sender: {msg.sender_id}")
            
            # MÉTODO 3: Usar Result.next() para buscar mais mensagens
            print("\n📋 MÉTODO 3: Usando Result.next() para mais mensagens")
            print("-" * 40)
            
            dm_result = await self.client.get_dm_history(user_id)
            all_messages = []
            
            # Coleta mensagens da primeira página
            for msg in dm_result:
                all_messages.append(msg)
            
            print(f"   Primeira página: {len(all_messages)} mensagens")
            
            # Tenta próxima página
            try:
                next_result = await dm_result.next()
                if next_result:
                    more_messages = list(next_result)
                    all_messages.extend(more_messages)
                    print(f"   Segunda página: {len(more_messages)} mensagens")
                else:
                    print("   Não há segunda página")
            except Exception as e:
                print(f"   Erro ao buscar próxima página: {e}")
            
            print(f"   📊 TOTAL COLETADO: {len(all_messages)} mensagens")
            
            # MÉTODO 4: Busca por chunks usando max_id
            print("\n📋 MÉTODO 4: Busca por chunks com max_id")
            print("-" * 40)
            
            await self._chunk_search(user_id)
            
            # MÉTODO 5: Análise completa das mensagens encontradas
            if all_messages:
                print("\n🔬 ANÁLISE COMPLETA DAS MENSAGENS")
                print("=" * 60)
                await self._analyze_messages(all_messages, user_id)
            else:
                print("\n⚠️ NENHUMA MENSAGEM ENCONTRADA COM MÉTODOS AVANÇADOS")
                print("💡 Isso pode indicar:")
                print("   - DMs foram enviadas por outro app/cliente")
                print("   - Configurações de privacidade bloqueiam acesso")
                print("   - Rate limits ou problemas de autenticação")
                print("   - Mensagens muito antigas")
            
        except Exception as e:
            print(f"❌ Erro na busca avançada: {e}")

    async def _chunk_search(self, user_id: str):
        """Busca DMs em chunks usando max_id"""
        try:
            max_id = None
            total_found = 0
            
            for chunk in range(1, 6):  # Até 5 chunks
                print(f"   Chunk {chunk}: ", end="")
                
                dm_history = await self.client.get_dm_history(user_id, max_id=max_id)
                messages = list(dm_history)
                
                if not messages:
                    print("Vazio")
                    break
                
                print(f"{len(messages)} mensagens")
                total_found += len(messages)
                
                # Última mensagem como próximo max_id
                max_id = messages[-1].id
                
                # Mostra algumas mensagens
                for i, msg in enumerate(messages[:2], 1):
                    print(f"      {i}. '{msg.text[:25]}...' ({msg.sender_id})")
                    
            print(f"   📈 Total em chunks: {total_found} mensagens")
            
        except Exception as e:
            print(f"   ❌ Erro no chunk search: {e}")

    async def _analyze_messages(self, messages, target_user_id):
        """Análise detalhada das mensagens encontradas"""
        try:
            print(f"📊 ESTATÍSTICAS:")
            print(f"   Total de mensagens: {len(messages)}")
            
            # Separar por remetente
            from_you = [m for m in messages if m.sender_id == self.user_id]
            from_them = [m for m in messages if m.sender_id == target_user_id]
            others = [m for m in messages if m.sender_id not in [self.user_id, target_user_id]]
            
            print(f"   Enviadas por você: {len(from_you)}")
            print(f"   Enviadas por {target_user_id}: {len(from_them)}")
            print(f"   De outros usuários: {len(others)}")
            
            # Análise temporal
            if messages:
                timestamps = [msg.time for msg in messages if hasattr(msg, 'time')]
                if timestamps:
                    print(f"   Timestamp mais antigo: {min(timestamps)}")
                    print(f"   Timestamp mais recente: {max(timestamps)}")
            
            # Mostra as mensagens mais recentes de OUTROS usuários
            if from_them:
                print(f"\n📨 MENSAGENS RECEBIDAS DE {target_user_id}:")
                print("-" * 50)
                for i, msg in enumerate(from_them[:5], 1):
                    print(f"{i:2d}. [{msg.time}] \"{msg.text}\"")
                    print(f"     ID: {msg.id}, Sender: {msg.sender_id} → {msg.recipient_id}")
                    
                    # Análise RAW da primeira mensagem recebida
                    if i == 1:
                        print(f"\n🔬 ANÁLISE RAW DA MENSAGEM:")
                        print(f"     Propriedades disponíveis:")
                        attrs = [attr for attr in dir(msg) if not attr.startswith('_')]
                        for attr in sorted(attrs):
                            try:
                                value = getattr(msg, attr)
                                if not callable(value):
                                    print(f"       {attr}: {value}")
                            except:
                                pass
            
            # Mostra mensagens de outros usuários (se houver)
            if others:
                print(f"\n👥 MENSAGENS DE OUTROS USUÁRIOS:")
                print("-" * 50)
                user_counts = {}
                for msg in others:
                    if msg.sender_id not in user_counts:
                        user_counts[msg.sender_id] = 0
                    user_counts[msg.sender_id] += 1
                
                for user, count in user_counts.items():
                    print(f"   User {user}: {count} mensagens")
            
        except Exception as e:
            print(f"❌ Erro na análise: {e}")

    async def test_multiple_users(self, user_ids: list):
        """Testa múltiplos user_ids"""
        print(f"\n🎯 TESTE MÚLTIPLOS USUÁRIOS")
        print("=" * 60)
        
        results = {}
        
        for user_id in user_ids:
            print(f"\n🔄 Testando User ID: {user_id}")
            try:
                dm_history = await self.client.get_dm_history(user_id)
                messages = list(dm_history)
                results[user_id] = len(messages)
                print(f"   ✅ {len(messages)} mensagens encontradas")
            except Exception as e:
                results[user_id] = f"ERRO: {e}"
                print(f"   ❌ Erro: {e}")
        
        print(f"\n📋 RESUMO DOS TESTES:")
        for user_id, result in results.items():
            print(f"   {user_id}: {result}")

    async def interactive_user_test(self):
        """Teste interativo onde você especifica user_ids"""
        print(f"\n💬 TESTE INTERATIVO")
        print("=" * 60)
        
        while True:
            user_id = input("\n💡 Digite um USER_ID para testar (ou 'quit' para sair): ").strip()
            
            if user_id.lower() in ['quit', 'exit', 'q']:
                break
            
            if not user_id:
                continue
                
            if not user_id.isdigit():
                print("❌ USER_ID deve ser numérico")
                continue
            
            await self.advanced_dm_search(user_id)

async def main():
    """Executa scanner avançado"""
    scanner = AdvancedDMScanner()
    
    if not await scanner.initialize():
        return
    
    print("""
    🔍 SCANNER DM AVANÇADO
    ======================
    
    Este scanner usa TODOS os parâmetros e métodos do twikit:
    - get_dm_history() com diferentes parâmetros
    - Result.next() para paginação
    - max_id para busca por chunks
    - Análise completa das mensagens
    
    """)
    
    # Opções de teste
    print("📋 OPÇÕES:")
    print("1. Teste interativo (você escolhe user_ids)")
    print("2. Teste com user_ids conhecidos")
    print("3. Teste com seu próprio user_id")
    
    choice = input("\nEscolha (1-3): ").strip()
    
    if choice == "1":
        await scanner.interactive_user_test()
    elif choice == "2":
        # User IDs comuns para teste
        test_users = [
            "783214",      # Twitter oficial
            "50393960",    # TwitterDev
            "17874544",    # TwitterSupport
        ]
        await scanner.test_multiple_users(test_users)
    elif choice == "3":
        print(f"\n🔄 Testando com seu próprio user_id: {scanner.user_id}")
        await scanner.advanced_dm_search(scanner.user_id)
    else:
        print("❌ Opção inválida")

if __name__ == "__main__":
    print("""
    🚀 SCANNER DM AVANÇADO - TWIKIT
    ===============================
    
    Usa parâmetros avançados do twikit para encontrar DMs:
    - max_id para busca histórica
    - Result.next() para paginação
    - Análise detalhada de mensagens
    - Suporte a múltiplos user_ids
    
    """)
    
    asyncio.run(main()) 