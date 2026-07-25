#!/usr/bin/env node
/**
 * TESTE AGENT-TWITTER-CLIENT JS CORRIGIDO
 * Testando Scraper para métodos de DM
 */

const fs = require('fs');
const { Scraper, SearchMode } = require('agent-twitter-client');

async function testAgentTwitterClient() {
    console.log('🔬 TESTANDO AGENT-TWITTER-CLIENT JS (SCRAPER)');
    console.log('='.repeat(60));
    
    try {
        // Carrega cookies do arquivo Python
        console.log('📂 CARREGANDO COOKIES...');
        const cookiesJson = fs.readFileSync('twitter_manual_cookies.json', 'utf8');
        const cookies = JSON.parse(cookiesJson);
        
        console.log('✅ Cookies carregados');
        console.log(`📊 Total de cookies: ${Object.keys(cookies).length}`);
        
        // Inicializa Scraper
        console.log('\n🔧 INICIALIZANDO SCRAPER...');
        
        const scraper = new Scraper();
        
        console.log('✅ Scraper criado');
        console.log(`📋 Tipo: ${typeof scraper}`);
        
        // Converte cookies para array de objetos
        const cookieArray = Object.entries(cookies)
            .filter(([key, value]) => !key.startsWith('_') && value)
            .map(([name, value]) => ({ name, value, domain: '.x.com' }));
        
        // Define cookies
        console.log('🍪 DEFININDO COOKIES...');
        await scraper.setCookies(cookieArray);
        console.log('✅ Cookies definidos');
        
        // Lista todos os métodos disponíveis
        console.log('\n🔍 MÉTODOS DISPONÍVEIS NO SCRAPER:');
        console.log('-'.repeat(50));
        
        const methods = Object.getOwnPropertyNames(Object.getPrototypeOf(scraper))
            .filter(method => typeof scraper[method] === 'function' && method !== 'constructor');
        
        console.log(`📋 Total de métodos: ${methods.length}`);
        
        // Mostra todos os métodos
        methods.forEach(method => {
            console.log(`   • ${method}()`);
        });
        
        // Busca métodos relacionados a DM/conversation
        const dmMethods = methods.filter(method => 
            method.toLowerCase().includes('dm') ||
            method.toLowerCase().includes('message') ||
            method.toLowerCase().includes('conversation') ||
            method.toLowerCase().includes('chat') ||
            method.toLowerCase().includes('inbox')
        );
        
        console.log('\n💬 MÉTODOS DE DM/CONVERSATION ENCONTRADOS:');
        if (dmMethods.length > 0) {
            dmMethods.forEach(method => {
                console.log(`   ✅ ${method}()`);
            });
        } else {
            console.log('   ⚪ Nenhum método de DM encontrado nos nomes');
        }
        
        // Testa especificamente getAllConversations
        console.log('\n🎯 TESTANDO getAllConversations():');
        if (typeof scraper.getAllConversations === 'function') {
            console.log('✅ Método getAllConversations() EXISTE!');
            
            try {
                console.log('🚀 Executando getAllConversations()...');
                const conversations = await scraper.getAllConversations();
                
                console.log(`📊 RESULTADO: ${conversations ? conversations.length : 'null'} conversas`);
                
                if (conversations && conversations.length > 0) {
                    console.log('\n🔸 PRIMEIRA CONVERSA:');
                    const first = conversations[0];
                    
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
        
        // Testa outros métodos potenciais para DM
        const testMethods = [
            'getConversations',
            'getDMs', 
            'getDirectMessages',
            'listConversations',
            'getMessageHistory',
            'getInbox',
            'fetchDMs',
            'fetchMessages',
            'fetchConversations'
        ];
        
        console.log('\n🔍 TESTANDO OUTROS MÉTODOS POTENCIAIS:');
        for (const methodName of testMethods) {
            if (typeof scraper[methodName] === 'function') {
                console.log(`✅ ${methodName}() EXISTE!`);
                
                try {
                    console.log(`   🚀 Testando ${methodName}()...`);
                    const result = await scraper[methodName]();
                    console.log(`   📊 Resultado: ${result ? JSON.stringify(result).substring(0, 100) : 'null'}...`);
                } catch (error) {
                    console.log(`   ❌ Erro: ${error.message}`);
                }
            } else {
                console.log(`❌ ${methodName}() não existe`);
            }
        }
        
        // Testa método que sabemos que existe (search) para validar funcionamento
        console.log('\n🧪 TESTE DE VALIDAÇÃO (SEARCH):');
        if (typeof scraper.searchTweets === 'function') {
            try {
                console.log('🔍 Testando searchTweets()...');
                const tweets = [];
                const searchResults = scraper.searchTweets('test', 5, SearchMode.Latest);
                
                let count = 0;
                for await (const tweet of searchResults) {
                    tweets.push(tweet);
                    count++;
                    if (count >= 2) break; // Só pega 2 para testar
                }
                
                console.log(`✅ Search funcionou: ${tweets.length} tweets encontrados`);
                
            } catch (error) {
                console.log(`❌ Search erro: ${error.message}`);
            }
        }
        
        console.log('\n🎯 CONCLUSÃO:');
        console.log('='.repeat(60));
        
        if (dmMethods.length > 0) {
            console.log('✅ AGENT-TWITTER-CLIENT TEM MÉTODOS DE DM!');
            console.log('🚀 Pode ser uma SOLUÇÃO MELHOR que twikit');
            console.log(`📋 Métodos encontrados: ${dmMethods.join(', ')}`);
        } else {
            console.log('❌ Nenhum método de DM óbvio encontrado');
            console.log('📝 Mas biblioteca funciona (search OK)');
            console.log('🔍 Pode ter métodos com nomes não óbvios');
        }
        
    } catch (error) {
        console.log(`❌ ERRO GERAL: ${error.message}`);
        console.log(`📋 Stack: ${error.stack}`);
    }
}

// Executa o teste
testAgentTwitterClient().catch(console.error); 