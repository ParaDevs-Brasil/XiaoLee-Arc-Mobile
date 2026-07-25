const fs = require('fs');

// Cookies loaded from env — REDACTED_ROTATE_BEFORE_USE, never hardcode a live session here
const newCookieString = process.env.TWITTER_COOKIE_STRING || '';

// Parse cookies
const cookies = newCookieString.split(';').map(cookie => {
    const [key, value] = cookie.trim().split('=');
    return {
        key: key,
        value: value.replace(/"/g, ''), // Remove quotes
        domain: 'twitter.com',
        path: '/',
        secure: true,
        httpOnly: false,
        sameSite: 'None'
    };
});

// Save to eliza format
fs.writeFileSync('eliza_cookies_v2.json', JSON.stringify(cookies, null, 2));
console.log('✅ Cookies updated successfully!');
console.log(`   Updated ${cookies.length} cookies`); 