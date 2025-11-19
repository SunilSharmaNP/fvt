# main.py
# Main entry point for the SS Video Workstation Telegram Bot
# Refactored into modular handlers for better organization and maintainability

import os
import sys
import logging
from pyrogram import Client
from pyrogram.types import BotCommand, BotCommandScopeChat

# Import pyromod to enable client.ask() functionality
from pyromod import listen

from config import config
from modules import bot_state
from modules.database import db

# Import handler registration functions
from handlers.start_handlers import register_start_handlers
from handlers.admin_handlers import register_admin_handlers
from handlers.task_handlers import register_task_handlers
from handlers.callback_handlers import register_callback_handlers

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration validation
if not config.API_ID or not config.API_HASH or not config.BOT_TOKEN:
    logger.critical("❌ Configuration not set! Missing API_ID, API_HASH, or BOT_TOKEN.")
    sys.exit(1)
if not isinstance(config.API_ID, int):
    logger.critical("❌ API_ID must be an integer.")
    sys.exit(1)

# Initialize Pyrogram Client
try:
    app = Client("SS_Video_Workstation_Bot_v5",
                 api_id=config.API_ID,
                 api_hash=config.API_HASH,
                 bot_token=config.BOT_TOKEN)
except Exception as e:
    logger.critical(f"Failed to initialize bot client: {e}")
    sys.exit(1)

# Register all handlers
logger.info("📦 Registering handlers...")
register_start_handlers(app)
register_admin_handlers(app)
register_task_handlers(app)
register_callback_handlers(app)
logger.info("✅ All handlers registered successfully!")


# Bot startup and command registration
async def startup():
    """Initialize and start the bot"""
    logger.info(f"🚀 Starting {config.BOT_NAME}...")
    logger.info(f"👑 Owner ID: {config.OWNER_ID}")
    logger.info(f"📡 Task Log Channel: {config.TASK_LOG_CHANNEL}")
    logger.info(f"🤖 Default Mode: {bot_state.get_bot_mode()}")

    # Connect to MongoDB
    logger.info("Connecting to MongoDB...")
    db.connect(config.MONGO_URI, config.DATABASE_NAME)

    # Start the bot
    await app.start()

    # Set bot commands for regular users
    base_commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("us", "User Settings"),
        BotCommand("vt", "Video Tools"),
        BotCommand("cancel", "Cancel current task"),
        BotCommand("help", "Get help"),
        BotCommand("hold", "Pause/Resume your tasks"),
        BotCommand("process", "Process queued merge files")
    ]
    await app.set_bot_commands(base_commands)

    # Set additional commands for admins
    admin_commands = [
        BotCommand("admin", "Open Admin Panel"),
        BotCommand("botmode", "Check global bot mode"),
        BotCommand("activate", "Activate task processing (Global)"),
        BotCommand("deactivate", "Hold task processing (Global)"),
        BotCommand("s", "Check bot status (Admin)"),
        BotCommand("addauth", "Authorize a chat"),
        BotCommand("removeauth", "De-authorize a chat"),
        BotCommand("restart", "Restart the bot (Sudo)")
    ]
    full_admin_commands = base_commands + admin_commands
    for admin_id in config.ADMINS:
        try:
            await app.set_bot_commands(full_admin_commands, scope=BotCommandScopeChat(admin_id))
        except Exception:
            pass

    logger.info(f"✅ {config.BOT_NAME} is running!")
    logger.info("Press Ctrl+C to stop the bot.")

    # Keep the bot running
    from pyrogram import idle
    await idle()
    
    # Cleanup on shutdown
    await app.stop()
    logger.info("Bot stopped.")


# Main execution
if __name__ == "__main__":
    try:
        app.run(startup())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.critical(f"Bot exited with a critical error: {e}", exc_info=True)
