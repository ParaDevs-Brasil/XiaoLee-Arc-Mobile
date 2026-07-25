#!/usr/bin/env python3
"""
BUSCA DMs NOVAS - Encontra conversas recém-criadas
Otimizado para contas que acabaram de seguir/enviar mensagens
"""

import asyncio
import json
import logging
from pprint import pprint
from twikit import Client

# Disable verbose logging
logging.basicConfig(level=logging.WARNING)

class NewDMFinder:
    """Encontrador de DMs recém-criadas"""
    
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

    async def scan_following_for_dms(self):
        """Busca DMs com TODOS que você está seguindo (nova conta)"""
        print("\n🔍 BUSCANDO DMs - FOLLOWING COMPLETO")
        print("-" * 50)
        
        try:
            user = await self.client.user()
            following = await user.get_following(count=100)  # Mais usuários
            
            print(f"📋 Testando {len(following)} usuários que você segue...")
            
            found_conversations = []
            
            for i, followed_user in enumerate(following):
                try:
                    print(f"   {i+1:3d}. Testando @{followed_user.screen_name}...", end=" ")
                    
                    # Busca histórico DM
                    dm_history = await self.client.get_dm_history(followed_user.id)
                    messages = list(dm_history)
                    
                    if messages:
                        # Separa mensagens próprias vs recebidas
                        sent_by_you = [m for m in messages if m.sender_id == self.user_id]
                        received_from_them = [m for m in messages if m.sender_id != self.user_id]
                        
                        total = len(messages)
                        sent = len(sent_by_you)
                        received = len(received_from_them)
                        
                        print(f"✅ {total} msgs (Enviadas:{sent}, Recebidas:{received})")
                        
                        # Salva conversa
                        found_conversations.append({
                            'user_id': followed_user.id,
                            'screen_name': followed_user.screen_name,
                            'name': followed_user.name,
                            'total_messages': total,
                            'sent_by_you': sent_by_you,
                            'received_from_them': received_from_them,
                            'all_messages': messages
                        })
                        
                        # Mostra última mensagem
                        last_msg = messages[0]  # Mais recente
                        sender = "VOCÊ" if last_msg.sender_id == self.user_id else "ELES"
                        print(f"       📨 Última ({sender}): \"{last_msg.text[:50]}...\"")
                        
                    else:
                        print("⚪ Sem mensagens")
                        
                except Exception as e:
                    print(f"❌ Erro: {str(e)[:20]}...")
                    
            return found_conversations
            
        except Exception as e:
            print(f"❌ Erro geral: {e}")
            return []

    async def analyze_conversation(self, conv):
        """Analisa conversa completa"""
        print(f"\n📋 CONVERSA: @{conv['screen_name']} ({conv['name']})")
        print("=" * 60)
        
        print(f"🔸 USER_ID: {conv['user_id']}")
        print(f"🔸 TOTAL MENSAGENS: {conv['total_messages']}")
        print(f"🔸 ENVIADAS POR VOCÊ: {len(conv['sent_by_you'])}")
        print(f"🔸 RECEBIDAS DELES: {len(conv['received_from_them'])}")
        
        print(f"\n📨 TODAS AS MENSAGENS (cronológica):")
        print("-" * 40)
        
        # Ordena por timestamp (mais antigas primeiro)
        all_msgs = sorted(conv['all_messages'], key=lambda m: m.time)
        
        for i, msg in enumerate(all_msgs, 1):
            sender = "VOCÊ" if msg.sender_id == self.user_id else f"@{conv['screen_name']}"
            timestamp = msg.time
            
            print(f"\n{i:2d}. [{sender}] {timestamp}")
            print(f"    ID: {msg.id}")
            print(f"    Texto: \"{msg.text}\"")
            
            if msg.attachment:
                print(f"    Anexo: {msg.attachment}")
        
        # Se tem mensagens recebidas, analisa estrutura RAW
        if conv['received_from_them']:
            print(f"\n🔬 ANÁLISE RAW - MENSAGEM RECEBIDA:")
            print("-" * 40)
            received_msg = conv['received_from_them'][0]
            
            print("🔸 PROPRIEDADES:")
            attrs = ['id', 'text', 'time', 'sender_id', 'recipient_id', 'attachment']
            for attr in attrs:
                if hasattr(received_msg, attr):
                    value = getattr(received_msg, attr)
                    print(f"   {attr}: {value}")
            
            print("\n🔸 ESTRUTURA COMPLETA:")
            pprint(received_msg.__dict__, width=50, depth=2)
            
            print("\n🔸 MÉTODOS DISPONÍVEIS:")
            methods = [attr for attr in dir(received_msg) 
                      if not attr.startswith('_') and callable(getattr(received_msg, attr))]
            for method in methods:
                print(f"   {method}()")

    async def run_scan(self):
        """Executa scan completo"""
        print("🚀 BUSCA DMs RECÉM-CRIADAS")
        print("="*50)
        
        if not await self.initialize():
            return
        
        # Busca conversas
        conversations = await self.scan_following_for_dms()
        
        # Resumo
        print("\n" + "="*60)
        print("📊 RESUMO FINAL")
        print("="*60)
        print(f"✅ Conversas encontradas: {len(conversations)}")
        
        if conversations:
            print(f"\n📋 LISTA DE CONVERSAS:")
            for i, conv in enumerate(conversations, 1):
                print(f"\n{i}. @{conv['screen_name']} - {conv['total_messages']} mensagens")
                print(f"   Enviadas: {len(conv['sent_by_you'])}, Recebidas: {len(conv['received_from_them'])}")
            
            print(f"\n💡 Escolha uma conversa para análise detalhada (1-{len(conversations)}):")
            try:
                choice = input("Número: ").strip()
                if choice and choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(conversations):
                        await self.analyze_conversation(conversations[idx])
                    else:
                        print("❌ Número inválido")
                else:
                    print("📋 Pulando análise detalhada...")
            except:
                print("📋 Entrada inválida, pulando...")
        else:
            print("\n⚠️ NENHUMA CONVERSA ENCONTRADA")
            print("💡 Certifique-se de:")
            print("   - Ter seguido alguns usuários")
            print("   - Ter enviado DMs para eles")
            print("   - Aguardar alguns minutos para sincronização")

async def main():
    finder = NewDMFinder()
    await finder.run_scan()

if __name__ == "__main__":
    print("""
    🔍 BUSCA DMs NOVAS
    ==================
    
    Este script busca conversas DM que você acabou de criar:
    - Verifica todos os usuários que você segue
    - Encontra mensagens enviadas e recebidas
    - Analisa estrutura completa das mensagens
    
    Iniciando busca...
    """)
    
    asyncio.run(main()) 