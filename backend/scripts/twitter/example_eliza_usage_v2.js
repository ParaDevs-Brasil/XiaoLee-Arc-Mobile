
// EXEMPLO DE USO COM COOKIES CORRIGIDOS V2
const { Scraper } = require('agent-twitter-client');
const elizaCookies = require('./eliza_cookies_v2.json');

async function useDMsV2() {
    const scraper = new Scraper();
    
    // Define cookies (método string simples)
    const cookieStrings = elizaCookies.map(cookie => 
        `${cookie.key}=${cookie.value}; Domain=${cookie.domain}; Path=${cookie.path}`
    );
    await scraper.setCookies(cookieStrings);
    
    console.log('Testing authentication...');
    const me = await scraper.me();
    console.log('User object:', JSON.stringify(me, null, 2));
    
    if (me) {
        console.log('User ID:', me.id);
        
        // Lista todas as conversas DM
        const conversations = await scraper.getDirectMessageConversations(me.id);
        console.log(`Encontradas ${conversations?.conversations?.length || 0} conversas`);
        console.log('Response:', JSON.stringify(conversations, null, 2));
        
        return conversations;
    } else {
        console.log('Authentication failed');
        return null;
    }
}

// Usar assim:
useDMsV2().then(conversations => console.log('Final result:', conversations)).catch(console.error);
