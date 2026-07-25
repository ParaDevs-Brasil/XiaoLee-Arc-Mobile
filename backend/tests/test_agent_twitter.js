#!/usr/bin/env node
/**
 * TESTE AGENT-TWITTER-CLIENT JS
 * Verificando métodos de DM e getAllConversations()
 */

const fs = require('fs');

async function testAgentTwitterClient() {
    console.log('🔬 TESTANDO AGENT-TWITTER-CLIENT JS');
    console.log('='.repeat(60));
    
    try {
        // Carrega cookies do arquivo Python
        console.log('📂 CARREGANDO COOKIES...');
        const cookiesJson = fs.readFileSync('twitter_manual_cookies.json', 'utf8');
        const cookies = JSON.parse(cookiesJson);
        
        console.log('✅ Cookies carregados');
        console.log(`📊 Total de cookies: ${Object.keys(cookies).length}`);
        
        // Tenta importar agent-twitter-client
        console.log('\n📦 TENTANDO IMPORTAR AGENT-TWITTER-CLIENT...');
        
        let TwitterClient;
        try {
            // Tenta import moderno
            const module = await import('agent-twitter-client');
            TwitterClient = module.TwitterClient || module.default || module.Client;
        } catch (e1) {
            try {
                // Tenta require comum
                TwitterClient = require('agent-twitter-client');
            } catch (e2) {
                throw new Error(`Não conseguiu importar: ${e1.message} | ${e2.message}`);
            }
        }
        
        if (!TwitterClient) {
            throw new Error('TwitterClient não encontrado no módulo');
        }
        
        console.log('✅ Agent-twitter-client importado com sucesso');
        console.log(`📋 Tipo: ${typeof TwitterClient}`);
        
        // Inicializa cliente
        console.log('\n🔧 INICIALIZANDO CLIENTE...');
        
        // Converte cookies para formato adequado
        const cookieString = Object.entries(cookies)
            .filter(([key, value]) => !key.startsWith('_') && value)
            .map(([key, value]) => `${key}=${value}`)
            .join('; ');
        
        const client = new TwitterClient({
            username: 'XiaoLeeDefai',
            cookies: cookieString,
            // Outras opções possíveis
        });
        
        console.log('✅ Cliente inicializado');
        
        // Lista todos os métodos disponíveis
        console.log('\n🔍 MÉTODOS DISPONÍVEIS:');
        console.log('-'.repeat(50));
        
        const methods = Object.getOwnPropertyNames(Object.getPrototypeOf(client))
            .filter(method => typeof client[method] === 'function' && method !== 'constructor');
        
        console.log(`📋 Total de métodos: ${methods.length}`);
        
        // Busca métodos relacionados a DM/conversation
        const dmMethods = methods.filter(method => 
            method.toLowerCase().includes('dm') ||
            method.toLowerCase().includes('message') ||
            method.toLowerCase().includes('conversation') ||
            method.toLowerCase().includes('chat')
        );
        
        console.log('\n💬 MÉTODOS DE DM/CONVERSATION ENCONTRADOS:');
        dmMethods.forEach(method => {
            console.log(`   • ${method}()`);
        });
        
        if (dmMethods.length === 0) {
            console.log('   ⚪ Nenhum método de DM encontrado nos nomes');
        }
        
        // Testa especificamente getAllConversations
        console.log('\n🎯 TESTANDO getAllConversations():');
        if (typeof client.getAllConversations === 'function') {
            console.log('✅ Método getAllConversations() EXISTE!');
            
            try {
                console.log('🚀 Executando getAllConversations()...');
                const conversations = await client.getAllConversations();
                
                console.log(`📊 RESULTADO: ${conversations ? conversations.length : 'null'} conversas`);
                
                if (conversations && conversations.length > 0) {
                    console.log('\n🔸 PRIMEIRA CONVERSA:');
                    const first = conversations[0];
                    
                    // Mostra estrutura da conversa
                    Object.keys(first).forEach(key => {
                        const value = first[key];
                        if (typeof value === 'string' && value.length > 50) {
                            console.log(`   • ${key}: ${value.substring(0, 50)}...`);
                        } else {
                            console.log(`   • ${key}: ${JSON.stringify(value)}`);
                        }
                    });
                }
                
            } catch (error) {
                console.log(`❌ Erro ao executar: ${error.message}`);
            }
            
        } else {
            console.log('❌ Método getAllConversations() NÃO EXISTE');
        }
        
        // Testa outros métodos potenciais
        const testMethods = [
            'getConversations',
            'getDMs',
            'getDirectMessages',
            'listConversations',
            'getMessageHistory',
            'getInbox'
        ];
        
        console.log('\n🔍 TESTANDO OUTROS MÉTODOS POTENCIAIS:');
        for (const methodName of testMethods) {
            if (typeof client[methodName] === 'function') {
                console.log(`✅ ${methodName}() EXISTE!`);
                
                try {
                    console.log(`   🚀 Testando ${methodName}()...`);
                    const result = await client[methodName]();
                    console.log(`   📊 Resultado: ${result ? JSON.stringify(result).substring(0, 100) : 'null'}...`);
                } catch (error) {
                    console.log(`   ❌ Erro: ${error.message}`);
                }
            } else {
                console.log(`❌ ${methodName}() não existe`);
            }
        }
        
        console.log('\n🎯 CONCLUSÃO:');
        console.log('='.repeat(60));
        
        if (dmMethods.length > 0) {
            console.log('✅ AGENT-TWITTER-CLIENT TEM MÉTODOS DE DM!');
            console.log('🚀 Pode ser uma SOLUÇÃO MELHOR que twikit');
        } else {
            console.log('❌ Nenhum método de DM óbvio encontrado');
            console.log('📝 Mas pode ter métodos com nomes diferentes');
        }
        
    } catch (error) {
        console.log(`❌ ERRO GERAL: ${error.message}`);
        console.log(`📋 Stack: ${error.stack}`);
        
        // Se não conseguiu importar, tenta instalar
        if (error.message.includes('Cannot find module')) {
            console.log('\n📦 TENTANDO INSTALAR AGENT-TWITTER-CLIENT...');
            console.log('Execute: npm install agent-twitter-client');
        }
    }
}

// Executa o teste
testAgentTwitterClient().catch(console.error); 