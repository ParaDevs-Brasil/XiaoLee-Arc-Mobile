"""
Isolated and comprehensive test script for campaign and swap endpoints.

This script provides end-to-end testing for critical user-facing flows, including
the full campaign lifecycle and the multi-step swap process. It validates not only
API responses but also the underlying database state to ensure financial integrity.

**IMPORTANT**:
1. This script must be run in parallel with the main Flask application.
   Start the server first: `python -m flask_api.chat_app`
2. This script directly manipulates the database. It is destructive and should
   ONLY be run against a local/test database. It will delete and create data.
"""
import asyncio
import logging
import httpx
from decimal import Decimal
from datetime import datetime, timedelta
import secrets
import random

try:
    import pytest
except Exception:
    pytest = None

# --- Test Configuration ---
TEST_USER_ID_1 = "campaign_creator_001"
TEST_USER_HANDLE_1 = "campaign_creator_1"
TEST_USER_ID_2 = "campaign_participant_001"
TEST_USER_HANDLE_2 = "campaign_participant_1"
TEST_USER_ID_3 = "campaign_participant_002"
TEST_USER_HANDLE_3 = "campaign_participant_2"
SYSTEM_WALLET_ID = "SYSTEM_WALLET_999"
API_BASE_URL = "http://127.0.0.1:5000"

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- DB & Test Helpers ---
try:
    from user_management.user_service import UserService
    from database.database import init_db
    from swaps.balance_manager import BalanceManager
    from database.models import WebSession, User, CampaignParticipant
    from sqlalchemy import select, delete
except ModuleNotFoundError as exc:
    if pytest is not None and exc.name in {"solders"}:
        pytest.skip("solders is not installed in this environment", allow_module_level=True)
    raise
except ValueError as exc:
    if pytest is not None and "ENCRYPTION_KEY environment variable is required" in str(exc):
        pytest.skip("ENCRYPTION_KEY is not set in this environment", allow_module_level=True)
    raise

if pytest is not None and __name__ != "__main__":
    pytest.skip("legacy integration script; run directly instead of via pytest", allow_module_level=True)

async def setup_test_environment():
    """
    Connects to the database, cleans up old test data, creates/funds test users, 
    and sets up web sessions.
    This function assumes the database schema (tables) already exists.
    It is designed to be idempotent and ensure a clean slate for test data.
    """
    logging.info("--- Preparing test environment ---")
    
    # Initialize DB connection
    engine, session_factory = init_db()

    user_service = UserService(session_factory)
    balance_manager = BalanceManager(session_factory)
    test_user_ids = [TEST_USER_ID_1, TEST_USER_ID_2, TEST_USER_ID_3]

    async with session_factory() as session:
        # Clean up previous test runs to ensure idempotency
        logging.info("Cleaning up old test data...")
        
        # Correctly get numeric user IDs from string twitter_user_ids
        user_id_stmt = select(User.id).where(User.twitter_user_id.in_(test_user_ids))
        user_numeric_ids_result = await session.execute(user_id_stmt)
        user_numeric_ids = user_numeric_ids_result.scalars().all()

        if user_numeric_ids:
            await session.execute(delete(WebSession).where(WebSession.twitter_user_id.in_(test_user_ids)))
            await session.execute(delete(CampaignParticipant).where(CampaignParticipant.user_id.in_(user_numeric_ids)))
        
        # Do not delete Users or Campaigns to preserve IDs, we will re-use them
        await session.commit()

    # Create and fund users
    for handle, user_id in [(TEST_USER_HANDLE_1, TEST_USER_ID_1), 
                            (TEST_USER_HANDLE_2, TEST_USER_ID_2), 
                            (TEST_USER_HANDLE_3, TEST_USER_ID_3)]:
        user = await user_service.get_user_by_twitter_id(user_id)
        if not user:
            await user_service.register_user(handle, user_id)
            logging.info(f"Created test user: {handle}")
        # Ensure users have a known starting balance for tests
        await balance_manager.set(user_id, "WIP", Decimal("1000000.0"))
        await balance_manager.set(user_id, "ZOO", Decimal("0.0"))

    logging.info("Test users are ready and funded.")
    
    # Ensure system wallet exists
    await balance_manager.set(SYSTEM_WALLET_ID, "WIP", Decimal("0.0"))
    logging.info(f"System wallet '{SYSTEM_WALLET_ID}' is ready.")

    # Create fresh web sessions
    sessions = {}
    async with session_factory() as session:
        for user_id in test_user_ids:
            session_token = secrets.token_hex(32)
            new_session = WebSession(
                session_id=session_token, 
                twitter_user_id=user_id, 
                expires_at=datetime.utcnow() + timedelta(hours=24)
            )
            session.add(new_session)
            sessions[user_id] = session_token
        await session.commit()
    logging.info("Fresh web sessions created for all test users.")

    return True, sessions.get(TEST_USER_ID_1), sessions.get(TEST_USER_ID_2), sessions.get(TEST_USER_ID_3), balance_manager, session_factory

async def run_test(description, method, endpoint, expected_status, session_id=None, json_payload=None):
    """
    A helper function to run a single API test case. It now ALWAYS logs the
    full response body for complete visibility.
    """
    logging.info(f"RUNNING TEST: {description}")
    async with httpx.AsyncClient() as client:
        try:
            headers = {"Authorization": f"Bearer {session_id}"} if session_id else {}
            response = await client.request(method, f"{API_BASE_URL}{endpoint}", headers=headers, json=json_payload, timeout=30.0)
            
            logging.info(f"  -> API Response Status: {response.status_code} (Expected: {expected_status})")
            
            # Always log the full response body
            response_json = None
            try:
                response_json = response.json()
                logging.info(f"  -> Response Body: {response_json}")
            except Exception:
                logging.info(f"  -> Response Body (Not JSON): {response.text}")

            if response.status_code == expected_status:
                logging.info("  -> ✅ API-LEVEL TEST PASSED")
                return response_json if response_json is not None else response.text
            else:
                logging.error(f"  -> ❌ API-LEVEL TEST FAILED: Status code mismatch.")
                return None
        except Exception as e:
            logging.error(f"  -> ❌ API-LEVEL TEST FAILED: An unexpected error occurred: {e}")
            return None

async def assert_and_log(condition, success_msg, failure_msg):
    """Helper to assert a condition and log the result in a standard format."""
    if condition:
        logging.info(f"      ✅ VALIDATION PASSED: {success_msg}")
        return True
    else:
        logging.error(f"      ❌ VALIDATION FAILED: {failure_msg}")
        return False

async def main():
    """Main function to run the automated test suite for campaign and swap endpoints."""
    setup_ok, session_1, session_2, session_3, balance_manager, session_factory = await setup_test_environment()
    if not setup_ok:
        logging.error("Test environment setup failed. Aborting.")
        return

    # --- Test Data Generation ---
    def get_campaign_payload(name_suffix, reward=100, participants=10):
        return {
          "campaign_type": "airdrop",
          "name": f"Test Campaign {name_suffix} {random.randint(1000, 9999)}",
          "description": "A test airdrop campaign.",
          "reward_token": "WIP",
          "reward_per_participant": reward,
          "max_participants": participants
        }

    # =================================================================================
    # GROUP 1: CAMPAIGN CREATION AND FINANCIAL INTEGRITY TESTS
    # =================================================================================
    logging.info("\n\n--- GROUP 1: CAMPAIGN CREATION & FINANCIAL INTEGRITY ---\n")

    # Test 1.1: Successful Creation & Funds Transfer to Escrow
    logging.info("--- Test 1.1: Create Campaign (Success) and Validate Escrow ---")
    payload_1 = get_campaign_payload("Financial-OK")
    reward_pool = payload_1['reward_per_participant'] * payload_1['max_participants']
    
    creator_balance_before = await balance_manager.get(TEST_USER_ID_1, "WIP")
    system_balance_before = await balance_manager.get(SYSTEM_WALLET_ID, "WIP")

    created_campaign_1 = await run_test(
        "Create campaign with sufficient funds", "POST", "/campaigns/create_full", 201, 
        session_id=session_1, json_payload=payload_1
    )
    if created_campaign_1:
        creator_balance_after = await balance_manager.get(TEST_USER_ID_1, "WIP")
        system_balance_after = await balance_manager.get(SYSTEM_WALLET_ID, "WIP")

        await assert_and_log(
            creator_balance_after == creator_balance_before - Decimal(reward_pool),
            "Creator's balance was correctly debited.",
            f"Expected creator balance: {creator_balance_before - Decimal(reward_pool)}, Got: {creator_balance_after}"
        )
        await assert_and_log(
            system_balance_after == system_balance_before + Decimal(reward_pool),
            "System wallet was correctly credited.",
            f"Expected system wallet balance: {system_balance_before + Decimal(reward_pool)}, Got: {system_balance_after}"
        )
    
    # Test 1.2: Creation Failure due to Insufficient Funds
    logging.info("\n--- Test 1.2: Create Campaign (Failure) - Insufficient Funds ---")
    payload_2 = get_campaign_payload("Financial-FAIL", reward=50000, participants=100) # 5M reward pool
    
    creator_balance_before = await balance_manager.get(TEST_USER_ID_1, "WIP")
    system_balance_before = await balance_manager.get(SYSTEM_WALLET_ID, "WIP")

    await run_test(
        "Attempt to create campaign with insufficient funds", "POST", "/campaigns/create_full", 400,
        session_id=session_1, json_payload=payload_2
    )
    
    creator_balance_after = await balance_manager.get(TEST_USER_ID_1, "WIP")
    system_balance_after = await balance_manager.get(SYSTEM_WALLET_ID, "WIP")
    
    await assert_and_log(
        creator_balance_after == creator_balance_before,
        "Creator's balance remained unchanged after failed transaction.",
        "Creator's balance should not have changed."
    )
    await assert_and_log(
        system_balance_after == system_balance_before,
        "System wallet balance remained unchanged after failed transaction.",
        "System wallet balance should not have changed."
    )

    # =================================================================================
    # GROUP 2: CAMPAIGN JOIN & VERIFY FLOW
    # =================================================================================
    logging.info("\n\n--- GROUP 2: CAMPAIGN JOIN & VERIFY FLOW ---\n")
    
    # Test 2.1: Join campaign (Failure) - Campaign is full
    logging.info("\n--- Test 2.1: Join Campaign (Failure) - Campaign Full ---")
    payload_3 = get_campaign_payload("Full-Campaign", participants=1)
    campaign_full = await run_test("Create campaign with 1 slot", "POST", "/campaigns/create_full", 201, session_1, payload_3)
    
    if campaign_full:
        campaign_full_id = campaign_full.get("campaign_id")
        # User 2 successfully joins
        await run_test("User 2 joins the 1-slot campaign", "POST", "/campaigns/join", 200, session_2, {"campaign_identifier": campaign_full_id})
        # User 3 fails to join
        await run_test("User 3 fails to join the full campaign", "POST", "/campaigns/join", 400, session_3, {"campaign_identifier": campaign_full_id})

    # Test 2.2: Verify campaign state change
    logging.info("\n--- Test 2.2: Verify Campaign and check DB state change ---")
    payload_4 = get_campaign_payload("Verify-Test")
    campaign_verify = await run_test("Create campaign for verification test", "POST", "/campaigns/create_full", 201, session_1, payload_4)
    if campaign_verify:
        campaign_verify_id = campaign_verify.get("campaign_id")
        await run_test("User 2 joins campaign for verification", "POST", "/campaigns/join", 200, session_2, {"campaign_identifier": campaign_verify_id})

        async with session_factory() as db_session:
            # Get the numeric ID for the test user to perform a correct lookup
            user_2_id_stmt = select(User.id).where(User.twitter_user_id == TEST_USER_ID_2)
            user_2_numeric_id = (await db_session.execute(user_2_id_stmt)).scalar_one()

            stmt = select(CampaignParticipant).where(CampaignParticipant.campaign_id == campaign_verify_id, CampaignParticipant.user_id == user_2_numeric_id)
            result = await db_session.execute(stmt)
            participant_entry = result.scalar_one_or_none()
            await assert_and_log(participant_entry.tasks_verified_at is None, "tasks_verified_at is NULL before verification.", "tasks_verified_at should be NULL initially.")
        
        await run_test("User 2 verifies tasks for airdrop", "POST", "/campaigns/verify", 200, session_2, {"campaign_identifier": campaign_verify_id})
        
        async with session_factory() as db_session:
            # Re-fetch the numeric ID in this new session context
            user_2_id_stmt = select(User.id).where(User.twitter_user_id == TEST_USER_ID_2)
            user_2_numeric_id = (await db_session.execute(user_2_id_stmt)).scalar_one()

            stmt = select(CampaignParticipant).where(CampaignParticipant.campaign_id == campaign_verify_id, CampaignParticipant.user_id == user_2_numeric_id)
            result = await db_session.execute(stmt)
            participant_entry = result.scalar_one()
            await assert_and_log(participant_entry.tasks_verified_at is not None, "tasks_verified_at is populated after verification.", "tasks_verified_at should not be NULL.")


    # =================================================================================
    # GROUP 3: CLAIM REWARD FLOW AND FINANCIAL INTEGRITY
    # =================================================================================
    logging.info("\n\n--- GROUP 3: CLAIM REWARD FLOW & FINANCIAL INTEGRITY ---\n")

    logging.info("--- Test 3.1: Claim Reward (Success) and Validate Payout ---")
    payload_5 = get_campaign_payload("Claim-Test", reward=150, participants=5)
    campaign_claim = await run_test("Create campaign for claim test", "POST", "/campaigns/create_full", 201, session_1, payload_5)
    
    if campaign_claim:
        campaign_claim_id = campaign_claim.get("campaign_id")
        reward_amount = payload_5['reward_per_participant']
        await run_test("User 2 joins campaign to claim", "POST", "/campaigns/join", 200, session_2, {"campaign_identifier": campaign_claim_id})
        
        participant_balance_before = await balance_manager.get(TEST_USER_ID_2, "WIP")
        system_balance_before = await balance_manager.get(SYSTEM_WALLET_ID, "WIP")

        await run_test("User 2 claims reward", "POST", "/campaigns/claim", 200, session_2, {"campaign_identifier": campaign_claim_id})

        participant_balance_after = await balance_manager.get(TEST_USER_ID_2, "WIP")
        system_balance_after = await balance_manager.get(SYSTEM_WALLET_ID, "WIP")
        
        await assert_and_log(
            participant_balance_after == participant_balance_before + Decimal(reward_amount),
            "Participant's balance was correctly credited.",
            f"Expected participant balance: {participant_balance_before + Decimal(reward_amount)}, Got: {participant_balance_after}"
        )
        await assert_and_log(
            system_balance_after == system_balance_before - Decimal(reward_amount),
            "System wallet was correctly debited for the payout.",
            f"Expected system wallet balance: {system_balance_before - Decimal(reward_amount)}, Got: {system_balance_after}"
        )

        # Test 3.2: Double Claim Failure
        logging.info("\n--- Test 3.2: Claim Reward (Failure) - Double Claim ---")
        await run_test("User 2 attempts to claim reward again", "POST", "/campaigns/claim", 400, session_2, {"campaign_identifier": campaign_claim_id})
        participant_balance_final = await balance_manager.get(TEST_USER_ID_2, "WIP")
        await assert_and_log(
            participant_balance_final == participant_balance_after,
            "Participant's balance remained unchanged after double claim attempt.",
            "Balance should not change on a failed double claim."
        )

    # =================================================================================
    # GROUP 4: SWAP FLOW (VIA CHAT)
    # =================================================================================
    logging.info("\n\n--- GROUP 4: SWAP FLOW (VIA CHAT) ---\n")
    
    # Test 4.1: Full Swap Flow (Success)
    logging.info("--- Test 4.1: Full Swap Flow (Success) ---")
    user1_wip_before = await balance_manager.get(TEST_USER_ID_1, "WIP")
    user1_zoo_before = await balance_manager.get(TEST_USER_ID_1, "ZOO")
    
    # Step 1: Initiate swap
    swap_quote_response = await run_test(
        "Step 1: Initiate swap for quote", "POST", "/chat", 200,
        session_id=session_1, json_payload={"message": "swap 1000 WIP for ZOO"}
    )
    # This part is tricky as we need to parse the quote, for now we assume it continues
    if swap_quote_response:
        # Step 2: Confirm swap
        await run_test(
            "Step 2: Confirm the swap", "POST", "/chat", 200,
            session_id=session_1, json_payload={"message": "yes"}
        )
        
        user1_wip_after = await balance_manager.get(TEST_USER_ID_1, "WIP")
        user1_zoo_after = await balance_manager.get(TEST_USER_ID_1, "ZOO")

        await assert_and_log(
            user1_wip_after < user1_wip_before, "User WIP balance decreased after swap.", "WIP balance should have decreased."
        )
        await assert_and_log(
            user1_zoo_after > user1_zoo_before, "User ZOO balance increased after swap.", "ZOO balance should have increased."
        )
        logging.info(f"Swap result: WIP {user1_wip_before} -> {user1_wip_after}, ZOO {user1_zoo_before} -> {user1_zoo_after}")


    # Test 4.2: Swap Flow (Failure - Insufficient Funds)
    logging.info("\n--- Test 4.2: Swap Flow (Failure) - Insufficient Funds ---")
    user1_wip_before_fail = await balance_manager.get(TEST_USER_ID_1, "WIP")
    
    await run_test(
        "Attempt to swap more WIP than available", "POST", "/chat", 200, # The API returns 200 but the message contains the error
        session_id=session_1, json_payload={"message": "swap 999999999 WIP for ZOO"}
    )
    
    user1_wip_after_fail = await balance_manager.get(TEST_USER_ID_1, "WIP")
    await assert_and_log(
        user1_wip_after_fail == user1_wip_before_fail,
        "User WIP balance is unchanged after insufficient funds swap attempt.",
        "WIP balance should not change on a failed swap."
    )


    # =================================================================================
    # GROUP 5: ADVANCED USER SIMULATION VIA /CHAT
    # =================================================================================
    logging.info("\n\n--- GROUP 5: ADVANCED USER SIMULATION VIA /CHAT ---\n")

    # Test 5.1: Multiple, chained swaps with validation
    logging.info("--- Test 5.1: Chained Swaps with Full Validation ---")
    
    # Swap 1: WIP to ZOO
    user_wip_before_1 = await balance_manager.get(TEST_USER_ID_2, "WIP")
    user_zoo_before_1 = await balance_manager.get(TEST_USER_ID_2, "ZOO")
    
    logging.info("  Sub-test 5.1.1: Swapping 500 WIP for ZOO")
    await run_test("Step 1: Initiate WIP->ZOO swap", "POST", "/chat", 200, session_2, {"message": "swap 500 WIP for ZOO"})
    swap_1_response = await run_test("Step 2: Confirm WIP->ZOO swap", "POST", "/chat", 200, session_2, {"message": "yes"})
    
    if swap_1_response and swap_1_response.get('response'):
        await assert_and_log('animations' in swap_1_response, "Swap response contains 'animations' key.", "Swap response is missing 'animations' key.")
        
        user_wip_after_1 = await balance_manager.get(TEST_USER_ID_2, "WIP")
        user_zoo_after_1 = await balance_manager.get(TEST_USER_ID_2, "ZOO")
        await assert_and_log(user_wip_after_1 < user_wip_before_1, "User WIP balance decreased correctly.", "WIP balance did not decrease.")
        await assert_and_log(user_zoo_after_1 > user_zoo_before_1, "User ZOO balance increased correctly.", "ZOO balance did not increase.")

    # Swap 2: ZOO back to WIP
    logging.info("\n  Sub-test 5.1.2: Swapping 100000 ZOO back to WIP")
    user_wip_before_2 = await balance_manager.get(TEST_USER_ID_2, "WIP")
    user_zoo_before_2 = await balance_manager.get(TEST_USER_ID_2, "ZOO")
    await run_test("Step 1: Initiate ZOO->WIP swap", "POST", "/chat", 200, session_2, {"message": "swap 100000 ZOO for WIP"})
    await run_test("Step 2: Confirm ZOO->WIP swap", "POST", "/chat", 200, session_2, {"message": "yes"})
    
    user_wip_after_2 = await balance_manager.get(TEST_USER_ID_2, "WIP")
    user_zoo_after_2 = await balance_manager.get(TEST_USER_ID_2, "ZOO")
    await assert_and_log(user_wip_after_2 > user_wip_before_2, "User WIP balance increased correctly on reverse swap.", "WIP balance did not increase on reverse swap.")
    await assert_and_log(user_zoo_after_2 < user_zoo_before_2, "User ZOO balance decreased correctly on reverse swap.", "ZOO balance did not decrease on reverse swap.")

    # Test 5.2: Proving campaign management does NOT work via chat
    logging.info("\n--- Test 5.2: Prove Campaign Management via Chat is Not Supported ---")
    
    # Setup: Create a campaign directly via API to try and join it
    campaign_for_chat_test = get_campaign_payload("Chat-Join-Test")
    created_chat_campaign = await run_test("Setup: Create a campaign via API", "POST", "/campaigns/create_full", 201, session_id=session_1, json_payload=campaign_for_chat_test)

    # Attempt to join via chat
    logging.info("  Sub-test 5.2.1: Attempting to join a campaign via chat")
    join_attempt_response = await run_test(
        "Attempt to join campaign via chat", "POST", "/chat", 200, 
        session_id=session_2, json_payload={"message": f"I want to join the campaign '{campaign_for_chat_test['name']}'"}
    )
    # A sophisticated check would analyze the text, but for now, we just ensure it doesn't crash
    # and we can manually observe the 'I don't know how' response.
    await assert_and_log(join_attempt_response is not None, "Chatbot responded to join command without error.", "Chatbot crashed on join command.")

    # Attempt to create via chat
    logging.info("\n  Sub-test 5.2.2: Attempting to create a campaign via chat")
    create_attempt_response = await run_test(
        "Attempt to create campaign via chat", "POST", "/chat", 200,
        session_id=session_1, json_payload={"message": "create a new campaign"}
    )
    await assert_and_log(create_attempt_response is not None, "Chatbot responded to create command without error.", "Chatbot crashed on create command.")

    # Test 5.3: General Chat Functions
    logging.info("\n--- Test 5.3: Test General Chat Functions (Balance Check) ---")
    balance_check_response = await run_test(
        "Ask chatbot for balance", "POST", "/chat", 200,
        session_id=session_1, json_payload={"message": "what is my balance?"}
    )
    if balance_check_response and balance_check_response.get('response'):
        response_text = balance_check_response['response'][0].get('content', '').lower()
        await assert_and_log("wip" in response_text and "zoo" in response_text, "Balance check response contains token symbols.", "Balance check response seems incorrect.")


    logging.info("\n\n--- ALL TESTS COMPLETED ---\n")

if __name__ == "__main__":
    asyncio.run(main()) 