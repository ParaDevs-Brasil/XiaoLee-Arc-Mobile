import asyncio
import logging
from datetime import datetime
from sqlalchemy import select, text
from database.database import init_db
from database.models import User, AuthToken, WebSession

TWITTER_USER_ID = "1735029448339009536"
TOKEN = "818787"

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


async def main():
    """
    Checks the database for the complete authentication status of a specific user.
    """
    logging.info("--- Database Auth Status Check ---")
    logging.info(
        f"Checking status for User ID: {TWITTER_USER_ID} and Token: {TOKEN}")
    print("-" * 30)

    db_session_factory = init_db()
    async with db_session_factory() as session:
        # 1. Check if the user exists in the 'users' table
        logging.info("1. Checking 'users' table...")
        user_stmt = select(User).where(User.twitter_user_id == TWITTER_USER_ID)
        user_result = (await session.execute(user_stmt)).scalar_one_or_none()

        if user_result:
            logging.info(
                f"✅ FOUND: User '@{user_result.twitter_handle}' (ID: {user_result.twitter_user_id}) is registered."
            )
            is_user_registered = True
        else:
            logging.error(
                f"❌ NOT FOUND: No user with ID '{TWITTER_USER_ID}' is registered in the 'users' table."
            )
            is_user_registered = False

        print("-" * 30)

        # 2. Check the status of the specific auth token
        logging.info("2. Checking 'auth_tokens' table...")
        token_stmt = select(AuthToken).where(AuthToken.token == TOKEN)
        token_result = (await session.execute(token_stmt)).scalar_one_or_none()

        if token_result:
            logging.info(f"✅ FOUND: Token '{TOKEN}' exists.")
            logging.info(f"   - Status: {token_result.status.upper()}")
            logging.info(
                f"   - Linked to User ID: {token_result.twitter_user_id}")
            logging.info(f"   - Expires at: {token_result.expires_at}")
            is_token_active = token_result.status == 'active'
        else:
            logging.error(f"❌ NOT FOUND: Token '{TOKEN}' does not exist.")
            is_token_active = False

        print("-" * 30)

        # 3. Check for any web sessions for this user
        logging.info("3. Checking 'web_sessions' table...")
        session_stmt = select(WebSession).where(
            WebSession.twitter_user_id == TWITTER_USER_ID)
        session_results = (await session.execute(session_stmt)).scalars().all()

        if session_results:
            logging.info(
                f"✅ FOUND: {len(session_results)} web session(s) for this user."
            )
            for i, web_session in enumerate(session_results):
                logging.info(f"   - Session {i+1}: {web_session.session_id}")
                logging.info(f"   - Expires at: {web_session.expires_at}")
            has_web_session = True
        else:
            logging.warning(
                "⚠️ NOT FOUND: No web sessions currently exist for this user.")
            has_web_session = False

        print("-" * 30)

        # Final Summary
        logging.info("--- Final Status Summary ---")
        if is_user_registered and is_token_active and not has_web_session:
            logging.info(
                "CONCLUSION: The user is registered and the token is active. Ready for Phase 3 (getting a web session)."
            )
        elif is_user_registered and is_token_active and has_web_session:
            logging.info(
                "CONCLUSION: The user is fully authenticated. Ready for Phase 4 (making authenticated API calls)."
            )
        else:
            logging.error(
                "CONCLUSION: The user is NOT fully authenticated. Please review the steps above."
            )


if __name__ == "__main__":
    # Suppress unnecessary warnings from eth_utils
    logging.getLogger("eth_utils.network").setLevel(logging.CRITICAL)
    asyncio.run(main())
