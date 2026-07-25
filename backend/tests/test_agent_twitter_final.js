#!/usr/bin/env node
/**
 * TESTE AGENT-TWITTER-CLIENT JS FINAL
 * Testando Scraper com formato correto de cookies
 */

const fs = require('fs');
const { Scraper, SearchMode } = require('agent-twitter-client');

async function testAgentTwitterClient() {
    console.log('🔬 TESTANDO AGENT-TWITTER-CLIENT JS (VERSÃO FINAL)');
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
        
        // Converte cookies para string formato correto
        const cookieStrings = Object.entries(cookies)
            .filter(([key, value]) => !key.startsWith('_') && value)
            .map(([name, value]) => `${name}=${value}; Domain=.x.com; Path=/`);
        
        // Define cookies um por um
        console.log('🍪 DEFININDO COOKIES...');
        for (const cookieString of cookieStrings) {
            try {
                await scraper.setCookies([cookieString]);
            } catch (e) {
                // Ignora erros de cookie individual
                console.log(`   ⚠️ Cookie ignorado: ${cookieString.split('=')[0]}`);
            }
        }
        console.log('✅ Cookies processados');
        
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
                    
                    return; // Se funcionou, para aqui!
                }
                
            } catch (error) {
                console.log(`❌ Erro ao executar getAllConversations: ${error.message}`);
            }
            
        } else {
            console.log('❌ Método getAllConversations() NÃO EXISTE');
        }
        
        // Se não achou getAllConversations, procura alternativas
        console.log('\n🔍 BUSCANDO ALTERNATIVAS...');
        
        // Lista métodos que podem ter DMs
        const possibleDmMethods = methods.filter(method => {
            const methodLower = method.toLowerCase();
            return methodLower.includes('get') || 
                   methodLower.includes('fetch') ||
                   methodLower.includes('search') ||
                   methodLower.includes('find');
        });
        
        console.log(`📋 MÉTODOS INTERESSANTES (${possibleDmMethods.length}):`);
        possibleDmMethods.forEach(method => {
            console.log(`   • ${method}()`);
        });
        
        // Testa alguns métodos específicos
        const testMethods = [
            'getConversations',
            'getDMs', 
            'getDirectMessages',
            'fetchDMs',
            'fetchMessages',
            'fetchConversations'
        ];
        
        console.log('\n🧪 TESTANDO MÉTODOS ESPECÍFICOS:');
        for (const methodName of testMethods) {
            if (typeof scraper[methodName] === 'function') {
                console.log(`✅ ${methodName}() EXISTE!`);
                
                try {
                    console.log(`   🚀 Testando ${methodName}()...`);
                    const result = await scraper[methodName]();
                    console.log(`   📊 Resultado: ${result ? 'Dados retornados' : 'null'}`);
                    if (result) {
                        console.log(`   📋 Tipo: ${typeof result}, Length: ${result.length || 'N/A'}`);
                    }
                } catch (error) {
                    console.log(`   ❌ Erro: ${error.message}`);
                }
            } else {
                console.log(`❌ ${methodName}() não existe`);
            }
        }
        
        console.log('\n🎯 CONCLUSÃO SOBRE AGENT-TWITTER-CLIENT:');
        console.log('='.repeat(60));
        
        if (dmMethods.length > 0) {
            console.log('✅ MÉTODOS DE DM ENCONTRADOS!');
            console.log(`📋 Lista: ${dmMethods.join(', ')}`);
            console.log('🚀 PODE SER SOLUÇÃO MELHOR QUE TWIKIT!');
        } else {
            console.log('❌ Nenhum método de DM óbvio encontrado');
            console.log('📝 Agent-twitter-client pode não ter DM support');
            console.log('🎯 Focado em tweets/posts, não DMs');
        }
        
        console.log('\n💡 RECOMENDAÇÃO:');
        if (dmMethods.length > 0) {
            console.log('📈 CONTINUAR COM AGENT-TWITTER-CLIENT');
            console.log('🔄 Implementar integração JS+Python');
        } else {
            console.log('📉 MANTER TWIKIT COMO SOLUÇÃO PRINCIPAL');
            console.log('✅ Sua estratégia atual já funciona perfeitamente');
        }
        
    } catch (error) {
        console.log(`❌ ERRO GERAL: ${error.message}`);
        console.log(`📋 Stack: ${error.stack}`);
    }
}

// Executa o teste
testAgentTwitterClient().catch(console.error); 