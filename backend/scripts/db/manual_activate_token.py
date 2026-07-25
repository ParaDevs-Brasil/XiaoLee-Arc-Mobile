import asyncio
import logging
from user_management.authentication_service import AuthenticationService
from database.database import init_db

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    """
    Manually activates an authentication token for a given user.
    This script simulates the action of the DMListenerService.
    """
    # --- CONFIGURATION ---
    TOKEN_TO_ACTIVATE = "726529"
    TWITTER_USER_ID = "1735029448339009536"
    # -------------------

    logging.info("--- Manual Token Activation Script ---")
    logging.info(f"Attempting to activate token '{TOKEN_TO_ACTIVATE}' for user ID '{TWITTER_USER_ID}'...")

    try:
        # Initialize the database session factory
        db_session_factory = init_db()
        
        # Instantiate the authentication service
        auth_service = AuthenticationService(db_session_factory)
        
        # Call the activation method
        success = await auth_service.activate_token(TOKEN_TO_ACTIVATE, TWITTER_USER_ID)
        
        if success:
            logging.info("✅ SUCCESS: Token has been successfully activated in the database.")
        else:
            logging.error("❌ FAILURE: Token could not be activated. It might be expired, invalid, or already used.")

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)

    logging.info("--- Script finished ---")


if __name__ == "__main__":
    asyncio.run(main()) 