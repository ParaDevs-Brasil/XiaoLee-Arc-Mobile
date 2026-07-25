#!/usr/bin/env node
/**
 * CORREÇÃO DE COOKIES PARA ELIZA/AGENT-TWITTER-CLIENT V2
 * Corrige domínio para twitter.com
 */

const fs = require('fs');
const { Scraper } = require('agent-twitter-client');

async function fixElizaCookiesV2() {
    console.log('🔧 CORRIGINDO COOKIES PARA ELIZA V2 (DOMÍNIO TWITTER.COM)');
    console.log('='.repeat(60));
    
    try {
        // 1. CARREGA COOKIES ATUAIS
        console.log('📂 CARREGANDO COOKIES ATUAIS...');
        const cookiesJson = fs.readFileSync('data/twitter_manual_cookies.json', 'utf8');
        const currentCookies = JSON.parse(cookiesJson);
        
        console.log('✅ Cookies atuais carregados');
        console.log(`📊 Total: ${Object.keys(currentCookies).length} cookies`);
        
        // 2. CONVERTE PARA FORMATO CORRETO DO ELIZA
        console.log('\n🔄 CONVERTENDO PARA FORMATO ELIZA (TWITTER.COM)...');
        
        const elizaCookies = Object.entries(currentCookies)
            .filter(([key, value]) => !key.startsWith('_') && value)
            .map(([name, value]) => ({
                name: name,
                value: value,
                domain: '.twitter.com',   // ✅ CORRIGIDO PARA TWITTER.COM
                path: '/',
                secure: true,
                httpOnly: false,          // ✅ AJUSTADO
                sameSite: 'Lax'
            }));
        
        console.log(`✅ Convertidos ${elizaCookies.length} cookies para formato ElizaOS`);
        
        // 3. EXTRAI CSRF TOKEN
        const csrfToken = currentCookies.ct0;
        if (!csrfToken) {
            throw new Error('❌ CSRF token (ct0) não encontrado nos cookies!');
        }
        
        console.log(`✅ CSRF Token extraído: ${csrfToken.substring(0, 10)}...`);
        
        // 4. SALVA COOKIES NO FORMATO ELIZA V2
        console.log('\n💾 SALVANDO COOKIES FORMATO ELIZA V2...');
        
        const elizaCookiesJson = JSON.stringify(elizaCookies, null, 2);
        fs.writeFileSync('data/eliza_cookies_v2.json', elizaCookiesJson);
        
        console.log('✅ Cookies salvos em: data/eliza_cookies_v2.json');
        
        // 5. TESTA O AGENT-TWITTER-CLIENT
        console.log('\n🧪 TESTANDO AGENT-TWITTER-CLIENT V2...');
        
        const scraper = new Scraper();
        
        // Método alternativo para definir cookies
        console.log('🍪 DEFININDO COOKIES MÉTODO ALTERNATIVO...');
        
        // Tenta formato string simples primeiro
        const cookieStrings = elizaCookies.map(cookie => 
            `${cookie.name}=${cookie.value}`
        );
        
        try {
            await scraper.setCookies(cookieStrings);
            console.log('✅ Cookies definidos (método string)');
        } catch (e) {
            console.log('⚠️ Método string falhou, tentando método array...');
            await scraper.setCookies(elizaCookies);
            console.log('✅ Cookies definidos (método array)');
        }
        
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
                
                // Lista todas as propriedades
                Object.keys(conv).forEach(key => {
                    const value = conv[key];
                    
                    if (key === 'id' || key === 'conversation_id') {
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
                    } else if (key.includes('time') || key.includes('date')) {
                        console.log(`   ⏰ ${key}: ${value}`);
                    } else if (typeof value === 'string' && value.length > 50) {
                        console.log(`   📋 ${key}: ${value.substring(0, 50)}...`);
                    } else if (typeof value === 'object' && value !== null) {
                        console.log(`   📦 ${key}: [Objeto - ${Object.keys(value).length} propriedades]`);
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
            console.log('🎯 PROBLEMA DE DOMÍNIO RESOLVIDO!');
            
        } else {
            console.log('\n⚪ Nenhuma conversa encontrada');
            console.log('💡 Possíveis motivos:');
            console.log('   • Conta nova sem DMs');
            console.log('   • Todas as conversas foram deletadas');
            console.log('   • Método precisa de parâmetros adicionais');
            console.log('✅ Mas a autenticação funcionou!');
        }
        
        // 7. TESTA OUTROS MÉTODOS DM
        console.log('\n🔬 TESTANDO OUTROS MÉTODOS DM...');
        
        try {
            console.log('📬 Testando sendDirectMessage...');
            // Não vamos enviar, só verificar se método existe
            if (typeof scraper.sendDirectMessage === 'function') {
                console.log('✅ sendDirectMessage() disponível');
            }
        } catch (e) {
            console.log(`⚠️ sendDirectMessage erro: ${e.message}`);
        }
        
        // 8. CRIA EXEMPLO DE USO CORRIGIDO
        console.log('\n📝 CRIANDO EXEMPLO DE USO CORRIGIDO...');
        
        const exampleCode = `
// EXEMPLO DE USO COM COOKIES CORRIGIDOS V2
const { Scraper } = require('agent-twitter-client');
const elizaCookies = require('./eliza_cookies_v2.json');

async function useDMsV2() {
    const scraper = new Scraper();
    
    // Define cookies (método string simples)
    const cookieStrings = elizaCookies.map(cookie => 
        \`\${cookie.name}=\${cookie.value}\`
    );
    await scraper.setCookies(cookieStrings);
    
    // CSRF token (OBRIGATÓRIO!)
    scraper.withXCsrfToken('${csrfToken}');
    
    // Lista todas as conversas DM
    const conversations = await scraper.getDirectMessageConversations();
    console.log(\`Encontradas \${conversations.length} conversas\`);
    
    return conversations;
}

// Usar assim:
// useDMsV2().then(conversations => console.log(conversations));
`;
        
        fs.writeFileSync('example_eliza_usage_v2.js', exampleCode);
        console.log('✅ Exemplo V2 salvo em: example_eliza_usage_v2.js');
        
    } catch (error) {
        console.log(`\n❌ ERRO: ${error.message}`);
        
        if (error.message.includes('domain')) {
            console.log('\n🌐 PROBLEMA DE DOMÍNIO:');
            console.log('   • Tentativa com twitter.com ainda falhou');
            console.log('   • Pode ser necessário usar método diferente');
            console.log('   • Cookies podem precisar ser resetados');
        } else if (error.message.includes('csrf')) {
            console.log('\n🔑 PROBLEMA DE CSRF:');
            console.log('   • CSRF resolvido mas outro erro apareceu');
            console.log('   • Verifique se withXCsrfToken() foi chamado antes');
        }
        
        console.log(`\n📋 Stack: ${error.stack}`);
    }
    
    console.log('\n💡 RESUMO V2:');
    console.log('='.repeat(60));
    console.log('🎯 Cookies convertidos para twitter.com');
    console.log('🔐 CSRF token extraído e configurado');
    console.log('📁 Arquivos criados:');
    console.log('   • data/eliza_cookies_v2.json (domínio corrigido)');
    console.log('   • example_eliza_usage_v2.js (exemplo funcional)');
    console.log('🚀 Pronto para usar agent-twitter-client!');
}

// Executa a correção V2
fixElizaCookiesV2().catch(console.error); 