#!/usr/bin/env node
/**
 * TESTE ESPECÍFICO: getDirectMessageConversations()
 * O MOMENTO DA VERDADE!
 */

const fs = require('fs');
const { Scraper } = require('agent-twitter-client');

async function testDMConversations() {
    console.log('🎯 TESTE CRÍTICO: getDirectMessageConversations()');
    console.log('='.repeat(60));
    
    try {
        // Carrega cookies
        const cookiesJson = fs.readFileSync('twitter_manual_cookies.json', 'utf8');
        const cookies = JSON.parse(cookiesJson);
        
        // Inicializa Scraper
        const scraper = new Scraper();
        
        console.log('🔧 Preparando scraper...');
        
        // Define cookies em formato string simples
        const cookieString = Object.entries(cookies)
            .filter(([key, value]) => !key.startsWith('_') && value)
            .map(([name, value]) => `${name}=${value}`)
            .join('; ');
        
        // Tenta definir cookies de forma simples
        try {
            await scraper.setCookies([cookieString]);
        } catch (e) {
            console.log('⚠️ Erro cookies, continuando...');
        }
        
        console.log('🎯 EXECUTANDO getDirectMessageConversations()...');
        console.log('⏳ Aguarde...');
        
        // O MOMENTO DA VERDADE
        const conversations = await scraper.getDirectMessageConversations();
        
        console.log('\n🎉 SUCESSO!');
        console.log('='.repeat(60));
        console.log(`📊 TOTAL DE CONVERSAS: ${conversations ? conversations.length : 'null'}`);
        
        if (conversations && conversations.length > 0) {
            console.log('\n✅ CONVERSAS ENCONTRADAS!');
            console.log('💬 DETALHES DAS CONVERSAS:');
            
            conversations.forEach((conv, index) => {
                console.log(`\n🔸 CONVERSA #${index + 1}:`);
                console.log('-'.repeat(40));
                
                // Mostra todas as propriedades da conversa
                Object.keys(conv).forEach(key => {
                    const value = conv[key];
                    
                    if (key === 'messages' && Array.isArray(value)) {
                        console.log(`   📨 ${key}: ${value.length} mensagens`);
                        
                        // Mostra primeira mensagem como exemplo
                        if (value.length > 0) {
                            const firstMsg = value[0];
                            console.log(`      └─ Primeira: "${firstMsg.text || firstMsg.message || 'sem texto'}"`);
                        }
                        
                    } else if (key === 'participants' && Array.isArray(value)) {
                        console.log(`   👥 ${key}: ${value.length} participantes`);
                        value.forEach(p => {
                            console.log(`      └─ @${p.username || p.screen_name || p.id}`);
                        });
                        
                    } else if (typeof value === 'string' && value.length > 50) {
                        console.log(`   📋 ${key}: ${value.substring(0, 50)}...`);
                    } else if (typeof value === 'object' && value !== null) {
                        console.log(`   📦 ${key}: [Objeto]`);
                    } else {
                        console.log(`   📋 ${key}: ${value}`);
                    }
                });
            });
            
            console.log('\n🚀 RESULTADO FINAL:');
            console.log('✅ AGENT-TWITTER-CLIENT FUNCIONA PARA DMs!');
            console.log('🏆 SOLUÇÃO ENCONTRADA!');
            console.log('📈 UPGRADE RECOMENDADO DO TWIKIT');
            
        } else {
            console.log('\n⚪ Nenhuma conversa encontrada');
            console.log('🤔 Possíveis causas:');
            console.log('   • Cookies não autenticados corretamente');
            console.log('   • Conta nova sem DMs');
            console.log('   • Método precisa de parâmetros');
        }
        
    } catch (error) {
        console.log('\n❌ ERRO AO EXECUTAR:');
        console.log(`📋 Mensagem: ${error.message}`);
        console.log(`📋 Stack: ${error.stack}`);
        
        if (error.message.includes('auth') || error.message.includes('login')) {
            console.log('\n🔑 PROBLEMA DE AUTENTICAÇÃO:');
            console.log('   • Cookies podem estar expirados');
            console.log('   • Formato de cookies incorreto');
            console.log('   • Precisa login com username/password');
        }
    }
    
    console.log('\n💡 CONCLUSÃO:');
    console.log('='.repeat(60));
    console.log('🎯 getDirectMessageConversations() EXISTE!');
    console.log('🔄 Próximo: Resolver autenticação se necessário');
    console.log('📈 Potencial para substituir twikit completamente');
}

// Executa o teste
testDMConversations().catch(console.error); 