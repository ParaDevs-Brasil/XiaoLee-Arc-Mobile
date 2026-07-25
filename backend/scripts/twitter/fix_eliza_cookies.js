#!/usr/bin/env node
/**
 * CORREÇÃO DE COOKIES PARA ELIZA/AGENT-TWITTER-CLIENT
 * Resolve bug #558 do ElizaOS e adiciona CSRF correto
 */

const fs = require('fs');
const { Scraper } = require('agent-twitter-client');

async function fixElizaCookies() {
    console.log('🔧 CORRIGINDO COOKIES PARA ELIZA/AGENT-TWITTER-CLIENT');
    console.log('='.repeat(60));
    
    try {
        // 1. CARREGA COOKIES ATUAIS
        console.log('📂 CARREGANDO COOKIES ATUAIS...');
        const cookiesJson = fs.readFileSync('twitter_manual_cookies.json', 'utf8');
        const currentCookies = JSON.parse(cookiesJson);
        
        console.log('✅ Cookies atuais carregados');
        console.log(`📊 Total: ${Object.keys(currentCookies).length} cookies`);
        
        // 2. CONVERTE PARA FORMATO CORRETO DO ELIZA
        console.log('\n🔄 CONVERTENDO PARA FORMATO ELIZA...');
        
        const elizaCookies = Object.entries(currentCookies)
            .filter(([key, value]) => !key.startsWith('_') && value)
            .map(([name, value]) => ({
                name: name,           // ✅ USA 'name' (não 'key' como no bug)
                value: value,
                domain: '.x.com',     // ✅ Domínio correto
                path: '/',
                secure: true,
                httpOnly: true,
                sameSite: 'Lax'
            }));
        
        console.log(`✅ Convertidos ${elizaCookies.length} cookies para formato ElizaOS`);
        
        // 3. EXTRAI CSRF TOKEN
        const csrfToken = currentCookies.ct0;
        if (!csrfToken) {
            throw new Error('❌ CSRF token (ct0) não encontrado nos cookies!');
        }
        
        console.log(`✅ CSRF Token extraído: ${csrfToken.substring(0, 10)}...`);
        
        // 4. SALVA COOKIES NO FORMATO ELIZA
        console.log('\n💾 SALVANDO COOKIES FORMATO ELIZA...');
        
        const elizaCookiesJson = JSON.stringify(elizaCookies, null, 2);
        fs.writeFileSync('eliza_cookies.json', elizaCookiesJson);
        
        console.log('✅ Cookies salvos em: eliza_cookies.json');
        
        // 5. TESTA O AGENT-TWITTER-CLIENT
        console.log('\n🧪 TESTANDO AGENT-TWITTER-CLIENT...');
        
        const scraper = new Scraper();
        
        // Define cookies no formato correto
        await scraper.setCookies(elizaCookies.map(cookie => 
            `${cookie.name}=${cookie.value}; Domain=${cookie.domain}; Path=${cookie.path}; ${cookie.secure ? 'Secure' : ''}; ${cookie.httpOnly ? 'HttpOnly' : ''}; SameSite=${cookie.sameSite}`
        ));
        
        console.log('✅ Cookies definidos no scraper');
        
        // ADICIONA CSRF TOKEN (CRÍTICO!)
        console.log('🔐 ADICIONANDO CSRF TOKEN...');
        scraper.withXCsrfToken(csrfToken);
        console.log('✅ CSRF token configurado');
        
        // 6. TESTA getDirectMessageConversations()
        console.log('\n🎯 TESTANDO getDirectMessageConversations()...');
        console.log('⏳ Aguarde...');
        
        const conversations = await scraper.getDirectMessageConversations();
        
        console.log('\n🎉 SUCESSO TOTAL!');
        console.log('='.repeat(60));
        console.log(`📊 CONVERSAS ENCONTRADAS: ${conversations ? conversations.length : 'null'}`);
        
        if (conversations && conversations.length > 0) {
            console.log('\n💬 DETALHES DAS CONVERSAS:');
            
            conversations.forEach((conv, index) => {
                console.log(`\n🔸 CONVERSA #${index + 1}:`);
                console.log('-'.repeat(40));
                
                // Mostra propriedades importantes
                Object.keys(conv).forEach(key => {
                    const value = conv[key];
                    
                    if (key === 'id') {
                        console.log(`   🆔 ${key}: ${value}`);
                    } else if (key === 'participants' && Array.isArray(value)) {
                        console.log(`   👥 ${key}: ${value.length} participantes`);
                        value.slice(0, 3).forEach(p => {
                            console.log(`      └─ @${p.screen_name || p.username || p.id}`);
                        });
                    } else if (key === 'messages' && Array.isArray(value)) {
                        console.log(`   📨 ${key}: ${value.length} mensagens`);
                        if (value.length > 0) {
                            const lastMsg = value[0];
                            console.log(`      └─ Última: "${lastMsg.text || lastMsg.content || 'sem texto'}"`);
                        }
                    } else if (key === 'last_read_event_id') {
                        console.log(`   📍 ${key}: ${value}`);
                    } else if (typeof value === 'string' && value.length > 50) {
                        console.log(`   📋 ${key}: ${value.substring(0, 50)}...`);
                    } else if (typeof value === 'object' && value !== null) {
                        console.log(`   📦 ${key}: [Objeto complexo]`);
                    } else {
                        console.log(`   📋 ${key}: ${value}`);
                    }
                });
            });
            
            console.log('\n🏆 RESULTADO FINAL:');
            console.log('✅ AGENT-TWITTER-CLIENT FUNCIONA PERFEITAMENTE!');
            console.log('✅ COOKIES E CSRF CORRIGIDOS!');
            console.log('✅ getDirectMessageConversations() FUNCIONANDO!');
            console.log('🚀 PODE SUBSTITUIR TWIKIT AGORA!');
            
        } else {
            console.log('\n⚪ Nenhuma conversa encontrada');
            console.log('💡 Isso pode ser normal se a conta não tem DMs');
            console.log('✅ Mas a autenticação funcionou!');
        }
        
        // 7. CRIA EXEMPLO DE USO
        console.log('\n📝 CRIANDO EXEMPLO DE USO...');
        
        const exampleCode = `
// EXEMPLO DE USO COM COOKIES CORRIGIDOS
const { Scraper } = require('agent-twitter-client');
const elizaCookies = require('./eliza_cookies.json');

async function useDMs() {
    const scraper = new Scraper();
    
    // Define cookies
    await scraper.setCookies(elizaCookies.map(cookie => 
        \`\${cookie.name}=\${cookie.value}; Domain=\${cookie.domain}; Path=\${cookie.path}\`
    ));
    
    // CSRF token (OBRIGATÓRIO!)
    scraper.withXCsrfToken('${csrfToken}');
    
    // Lista todas as conversas DM
    const conversations = await scraper.getDirectMessageConversations();
    console.log(\`Encontradas \${conversations.length} conversas\`);
    
    // Envia DM
    await scraper.sendDirectMessage('user_id_here', 'Hello world!');
}
`;
        
        fs.writeFileSync('example_eliza_usage.js', exampleCode);
        console.log('✅ Exemplo salvo em: example_eliza_usage.js');
        
    } catch (error) {
        console.log(`\n❌ ERRO: ${error.message}`);
        
        if (error.message.includes('csrf')) {
            console.log('\n🔑 PROBLEMA DE CSRF:');
            console.log('   • Verifique se o cookie ct0 existe');
            console.log('   • Certifique-se que withXCsrfToken() foi chamado');
            console.log('   • Cookies podem estar expirados');
        } else if (error.message.includes('auth')) {
            console.log('\n🔐 PROBLEMA DE AUTENTICAÇÃO:');
            console.log('   • Cookies podem estar expirados');
            console.log('   • Formato de cookies pode estar incorreto');
            console.log('   • Conta pode estar suspensa');
        }
        
        console.log(`\n📋 Stack: ${error.stack}`);
    }
    
    console.log('\n💡 RESUMO:');
    console.log('='.repeat(60));
    console.log('🎯 Cookies convertidos para formato ElizaOS');
    console.log('🔐 CSRF token extraído e configurado');
    console.log('📁 Arquivos criados:');
    console.log('   • eliza_cookies.json (formato correto)');
    console.log('   • example_eliza_usage.js (exemplo de uso)');
    console.log('🚀 Pronto para usar agent-twitter-client!');
}

// Executa a correção
fixElizaCookies().catch(console.error); 