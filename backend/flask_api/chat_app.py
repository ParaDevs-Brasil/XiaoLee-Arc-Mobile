# ARQUIVADO (2026-07-10) — sem entrypoint, não roda em produção. Ver flask_api/README.md.

import logging
import asyncio
from flask import Flask
from hypercorn.asyncio import serve
from hypercorn.config import Config
from datetime import datetime
import json
from sse_starlette.sse import EventSourceResponse

from database.database import init_db
from database.base import Base
from swaps.price_manager import PriceManager
from .cors_config import setup_cors
from .chat_routes import create_chat_blueprint, ChatHandler
from .dm_listener import DMListenerService
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession, AsyncEngine
from user_management.user_service import UserService
from user_management.campaign_service import CampaignService
from ai.response_generator import XiaoLeeResponseGenerator
from ai.mcp_tools import MCPToolsManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app(
) -> tuple[Flask, ChatHandler, async_sessionmaker[AsyncSession], AsyncEngine]:
    """Initializes and returns the Flask app, services, and database engine."""
    app = Flask(__name__)
    setup_cors(app)

    # 1. Initialize Database
    engine, db_session_factory = init_db()
    logger.info("Database connection initialized for Flask app")

    # 2. Create Blueprints and Services
    chat_bp, chat_handler = create_chat_blueprint(db_session_factory)

    # 3. Register Blueprints
    app.register_blueprint(chat_bp)

    @app.route('/')
    def index():
        return {
            "message": "Xiao Lee Chat API Server",
            "version": "1.2",
            "status": "running",
            "endpoints": {
                "GET /": "API info",
                "GET /chat": "Chat interface info",
                "POST /chat": "Send chat message",
                "GET /health": "Health check",
                "GET /prices": "Get all token prices"
            }
        }

    @app.route('/prices')
    async def get_prices():
        """Public endpoint to get all available token prices."""
        try:
            price_manager = PriceManager(db_session_factory)
            prices = await price_manager.get_all()
            return {"success": True, "prices": prices}
        except Exception as e:
            logger.error(f"Error fetching prices for /prices endpoint: {e}",
                         exc_info=True)
            return {
                "success": False,
                "error": "Could not retrieve token prices."
            }, 500

    return app, chat_handler, db_session_factory, engine


async def create_db_and_tables(engine: AsyncEngine):
    """Connects to the DB and creates all tables based on the SQLAlchemy models."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully.")


async def ensure_system_user_exists(
        db_session_factory: async_sessionmaker[AsyncSession]):
    """Ensures the special 'system_wallet' user exists for campaign fund custody."""
    user_service = UserService(db_session_factory)
    system_user_id = 'SYSTEM_WALLET_999'

    try:
        user = await user_service.get_user_by_twitter_id(system_user_id)
        if not user:
            logger.info(
                f"System user {system_user_id} not found, creating it...")
            await user_service.register(handle="@SystemWallet",
                                        user_id=system_user_id)
            logger.info(
                f"System user {system_user_id} created successfully.")
        else:
            logger.info(f"System user {system_user_id} already exists.")
    except Exception as e:
        logger.error(f"Failed to ensure system user exists: {e}",
                     exc_info=True)


async def main(host='0.0.0.0', port=5000, debug=True):
    app, chat_handler, db_session_factory, engine = create_app()

    await create_db_and_tables(engine)
    await ensure_system_user_exists(db_session_factory)

    logger.info("Initializing price update...")
    try:
        price_manager = PriceManager(db_session_factory)
        await price_manager.refresh()
        logger.info("Price update completed successfully.")
    except Exception as e:
        logger.error(f"Failed to update prices on startup: {e}",
                     exc_info=True)

    dm_listener_service = DMListenerService(db_session_factory)

    config = Config()
    config.bind = [f"{host}:{port}"]
    config.debug = debug

    logger.info(f"Starting Xiao Lee Chat Server on {host}:{port}")

    try:
        dm_task = asyncio.create_task(dm_listener_service.start_monitoring())
        await serve(app, config)
    except KeyboardInterrupt:
        logger.info("Server stopped by user.")
    finally:
        if not dm_task.done():
            dm_task.cancel()
            try:
                await dm_task
            except asyncio.CancelledError:
                pass
        await dm_listener_service.close()
        logger.info("All services shut down gracefully.")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Main loop interrupted.")
