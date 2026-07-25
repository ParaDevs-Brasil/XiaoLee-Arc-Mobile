import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import text, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from database.models import AuthToken

logger = logging.getLogger(__name__)

class AuthenticationService:
    def __init__(self, db_session_factory: async_sessionmaker[AsyncSession]):
        self.db_session_factory = db_session_factory

    async def generate_and_store_token(self) -> str:
        """
        Generates a secure, unique 6-digit token, stores it in the database
        with a 10-minute expiry, and returns the token.
        This now uses the SQLAlchemy ORM model to ensure all defaults are applied.
        """
        try:
            async with self.db_session_factory() as session:
                async with session.begin():
                    while True:
                        token = str(secrets.randbelow(1_000_000)).zfill(6)
                        
                        # Check if token already exists and is not expired using the ORM
                        stmt = select(AuthToken).where(
                            AuthToken.token == token,
                            AuthToken.expires_at > datetime.utcnow()
                        )
                        result = await session.execute(stmt)
                        if result.scalar_one_or_none() is None:
                            break
                    
                    # Create an instance of the AuthToken model
                    new_auth_token = AuthToken(
                        token=token,
                        status='pending',
                        expires_at=datetime.utcnow() + timedelta(minutes=10)
                        # created_at and updated_at are now handled automatically by the Base model
                    )
                    
                    session.add(new_auth_token)
                    # The commit happens automatically when the `async with session.begin()` block exits
                    
                    logger.info(f"Generated new auth token (ORM): {token}")
                    return token
        except Exception as e:
            logger.error(f"Failed to generate and store auth token: {e}", exc_info=True)
            return None 

    async def is_pending_token(self, token: str) -> bool:
        """Checks if a given token exists and has a 'pending' status."""
        try:
            async with self.db_session_factory() as session:
                stmt = select(AuthToken).where(
                    AuthToken.token == token,
                    AuthToken.status == 'pending'
                )
                result = await session.execute(stmt)
                return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error(f"Database error during token check for token {token}: {e}", exc_info=True)
            return False

    async def activate_token(self, token: str, twitter_user_id: str, twitter_handle: str = None) -> bool:
        """
        Activates a 'pending' token if it exists and is not expired,
        linking it to the user's Twitter ID and optionally storing the Twitter handle.
        This now uses the SQLAlchemy ORM to ensure all model defaults/updates are applied.
        """
        try:
            async with self.db_session_factory() as session:
                async with session.begin():
                    # 1. Select the token object using the ORM
                    stmt = select(AuthToken).where(AuthToken.token == token)
                    result = await session.execute(stmt)
                    token_to_activate = result.scalar_one_or_none()

                    # 2. Check if the token is valid for activation
                    if (token_to_activate and 
                        token_to_activate.status == 'pending' and
                        token_to_activate.expires_at > datetime.utcnow()):

                        # 3. Update the object's attributes in Python
                        token_to_activate.status = 'active'
                        token_to_activate.twitter_user_id = twitter_user_id
                        if twitter_handle:
                            token_to_activate.twitter_handle = twitter_handle
                        # The 'updated_at' field will be handled automatically by the ORM on commit

                        logger.info(f"Token {token} successfully activated for user {twitter_user_id} (@{twitter_handle or 'unknown'}).")
                        return True
                    else:
                        logger.warning(f"Failed to activate token {token} for user {twitter_user_id}. It might be invalid, expired, or already used.")
                        return False
        except Exception as e:
            logger.error(f"Database error during token activation for token {token}: {e}", exc_info=True)
            return False

    async def get_token_info(self, token: str) -> Optional[dict]:
        """
        Get information about a token including twitter_handle if available
        """
        try:
            async with self.db_session_factory() as session:
                stmt = select(AuthToken).where(AuthToken.token == token)
                result = await session.execute(stmt)
                token_obj = result.scalar_one_or_none()
                
                if token_obj:
                    return {
                        'token': token_obj.token,
                        'twitter_user_id': token_obj.twitter_user_id,
                        'twitter_handle': token_obj.twitter_handle,
                        'status': token_obj.status,
                        'expires_at': token_obj.expires_at,
                        'created_at': token_obj.created_at,
                        'updated_at': token_obj.updated_at
                    }
                return None
                
        except Exception as e:
            logger.error(f"Error getting token info for {token}: {e}")
            return None

    async def fetch_twitter_handle(self, twitter_user_id: str) -> str:
        """
        Fetch Twitter handle for a given user ID using the existing Twitter scraper system.
        Falls back to user_{id} format if handle cannot be fetched.
        """
        try:
            import subprocess
            import json
            import tempfile
            import os
            
            # Create a Node.js script to fetch user handle
            script_content = f"""
const {{ Scraper }} = require('agent-twitter-client');
const fs = require('fs');

async function getUserHandle() {{
    try {{
        // Load cookies from the same file used by dm_listener
        let cookies;
        try {{
            cookies = JSON.parse(fs.readFileSync('eliza_cookies_v2.json', 'utf8'));
        }} catch (e) {{
            try {{
                cookies = JSON.parse(fs.readFileSync('eliza_cookies.json', 'utf8'));
            }} catch (e2) {{
                console.error('No valid cookies file found');
                return null;
            }}
        }}
        
        const scraper = new Scraper();
        
        // Set cookies
        await scraper.setCookies(cookies.map(c => `${{c.key || c.name}}=${{c.value}}`));
        
        // Get user by ID
        const user = await scraper.getProfile('{twitter_user_id}');
        
        if (user && user.username) {{
            console.log(JSON.stringify({{
                success: true,
                handle: user.username,
                display_name: user.name
            }}));
        }} else {{
            console.log(JSON.stringify({{
                success: false,
                error: 'User not found'
            }}));
        }}
        
    }} catch (error) {{
        console.log(JSON.stringify({{
            success: false,
            error: error.message
        }}));
    }}
}}

getUserHandle();
"""
            
            # Write script to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
                f.write(script_content)
                script_path = f.name
            
            try:
                # Run the script
                result = subprocess.run(
                    ['node', script_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    try:
                        data = json.loads(result.stdout.strip())
                        if data.get('success') and data.get('handle'):
                            handle = data['handle']
                            logger.info(f"✅ Fetched Twitter handle for {twitter_user_id}: @{handle}")
                            return f"@{handle}"
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON response when fetching handle for {twitter_user_id}")
                
                logger.warning(f"Failed to fetch handle for {twitter_user_id}: {result.stderr}")
                
            finally:
                # Clean up temp file
                try:
                    os.unlink(script_path)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Error fetching Twitter handle for {twitter_user_id}: {e}")
        
        # Fallback to user_id format
        fallback_handle = f"@user_{twitter_user_id}"
        logger.info(f"Using fallback handle for {twitter_user_id}: {fallback_handle}")
        return fallback_handle 