import asyncio
import logging
import sys
import os

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import select, text
from database.database import init_db
from database.models import User, TokenBalance

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def grant_initial_stip():
    """
    Grants an initial balance of 1000 STIP to all users who do not currently
    have a STIP balance. This script is idempotent and safe to run multiple times.
    """
    logger.info("--- 💰 Starting STIP Airdrop for Existing Users ---")

    db_url, db_session_factory = init_db()

    async with db_session_factory() as session:
        try:
            # 1. Get all user IDs, excluding the system wallet
            user_stmt = select(User.twitter_user_id).where(
                User.twitter_user_id != 'SYSTEM_WALLET_999')
            user_result = await session.execute(user_stmt)
            all_user_ids = user_result.scalars().all()

            if not all_user_ids:
                logger.info("No users found to process. Exiting.")
                return

            logger.info(f"Found {len(all_user_ids)} total users to check.")

            # 2. Get all users who ALREADY have a STIP balance
            balance_stmt = select(TokenBalance.user_id).where(
                TokenBalance.token_symbol == 'STIP')
            balance_result = await session.execute(balance_stmt)
            users_with_stip = set(balance_result.scalars().all())

            logger.info(
                f"{len(users_with_stip)} users already have a STIP balance.")

            # 3. Determine which users need the airdrop
            users_to_airdrop = [
                user_id for user_id in all_user_ids
                if user_id not in users_with_stip
            ]

            if not users_to_airdrop:
                logger.info(
                    "All users already have STIP. No new airdrops needed.")
                await session.commit()
                return

            logger.info(
                f"Found {len(users_to_airdrop)} users who need the STIP airdrop. Processing..."
            )

            # 4. Add the balance for each user who needs it
            new_balances = []
            for user_id in users_to_airdrop:
                new_balances.append(
                    TokenBalance(user_id=user_id,
                                 token_symbol='stIP',
                                 balance=1000.0))

            session.add_all(new_balances)
            await session.commit()

            logger.info(
                f"✅ Successfully granted 1000 STIP to {len(users_to_airdrop)} users."
            )

        except Exception as e:
            logger.error(f"An error occurred during the airdrop process: {e}",
                         exc_info=True)
            await session.rollback()
        finally:
            logger.info("--- 💰 Airdrop Script Finished ---")


if __name__ == "__main__":
    asyncio.run(grant_initial_stip())
