# main.py (v7.0 - Professional Enhanced)
# SS Video Workstation Bot - Main Entry Point
# All Bugs Fixed & Production Ready
# ==================================================

import os
import sys
import logging
from pyrogram import Client
from pyrogram.types import BotCommand, BotCommandScopeChat

# ✅ CRITICAL FIX: Import pyromod and initialize it properly
from pyromod import listen

from config import config
from modules import bot_state
from modules.database import db

# Import handler registration functions
from handlers.start_handlers import register_start_handlers
from handlers.admin_handlers import register_admin_handlers
from handlers.task_handlers import register_task_handlers
from handlers.callback_handlers import register_callback_handlers

# Import new video tool handlers
from modules.screenshot_tool import register_screenshot_handlers
from modules.audio_remover_tool import register_audio_remover_handlers
from modules.hd_cover_tool import register_hd_cover_handlers

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== PYROGRAM CLIENT CONFIGURATION ====================

class BotClient:
    """Main Bot Client Manager"""
    
    def __init__(self):
        self.app = None
        self.session_name = "ss_video_workstation"
        
    async def init_bot(self):
        """Initialize Pyrogram bot client"""
        try:
            logger.info("🔧 Initializing Pyrogram bot client...")
            
            self.app = Client(
                name=self.session_name,
                api_id=config.API_ID,
                api_hash=config.API_HASH,
                bot_token=config.BOT_TOKEN,
                workers=32,
                max_concurrent_transmissions=10
            )
            
            # ✅ CRITICAL FIX: Initialize pyromod listener for client.ask() functionality
            listen(self.app)
            logger.info("✅ pyromod listener initialized successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize bot client: {e}", exc_info=True)
            return False

    async def register_all_handlers(self):
        """Register all command and callback handlers"""
        try:
            logger.info("📋 Registering all handlers...")
            
            # Register handlers in correct order
            register_start_handlers(self.app)
            logger.info("✅ Start handlers registered")
            
            register_admin_handlers(self.app)
            logger.info("✅ Admin handlers registered")
            
            register_task_handlers(self.app)
            logger.info("✅ Task handlers registered")
            
            register_callback_handlers(self.app)
            logger.info("✅ Callback handlers registered")
            
            # Register tool-specific handlers
            register_screenshot_handlers(self.app)
            logger.info("✅ Screenshot tool handlers registered")
            
            register_audio_remover_handlers(self.app)
            logger.info("✅ Audio remover tool handlers registered")
            
            register_hd_cover_handlers(self.app)
            logger.info("✅ HD cover tool handlers registered")
            
            logger.info("✅ All handlers registered successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to register handlers: {e}", exc_info=True)
            return False

    async def set_commands(self):
        """Set bot commands for better UX"""
        try:
            logger.info("⚙️ Setting bot commands...")
            
            commands = [
                BotCommand(command="start", description="🚀 Start the bot"),
                BotCommand(command="help", description="📚 Show help guide"),
                BotCommand(command="about", description="ℹ️ About the bot"),
                BotCommand(command="vt", description="🛠️ Video Tools"),
                BotCommand(command="us", description="⚙️ User Settings"),
                BotCommand(command="cancel", description="❌ Cancel task"),
                BotCommand(command="hold", description="⏸️ Hold/Resume tasks"),
                BotCommand(command="admin", description="🤖 Admin Panel"),
            ]
            
            await self.app.set_bot_commands(commands)
            logger.info("✅ Bot commands set successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to set bot commands: {e}", exc_info=True)
            return False

    async def on_startup(self):
        """Handle bot startup"""
        try:
            logger.info("\n" + "="*60)
            logger.info("🚀 SS Video Workstation Bot - Startup Sequence")
            logger.info("="*60)
            
            # Get bot info
            me = await self.app.get_me()
            logger.info(f"✅ Bot Account: @{me.username} (ID: {me.id})")
            logger.info(f"✅ Bot Name: {me.first_name}")
            
            # Initialize database
            logger.info("🔗 Connecting to MongoDB...")
            try:
                db.connect(config.MONGO_URI, config.DATABASE_NAME)
                logger.info(f"✅ MongoDB Connected: {config.DATABASE_NAME}")
            except Exception as db_error:
                logger.error(f"❌ MongoDB Connection Failed: {db_error}")
                logger.warning("⚠️ Bot will continue without database (limited functionality)")
            
            # Initialize bot state
            bot_state.bot_active = True
            bot_state.processing_active = True
            logger.info("✅ Bot State Initialized")
            
            # Set commands
            await self.set_commands()
            
            # Check configuration
            logger.info("\n📋 Configuration Check:")
            logger.info(f"  • Owner ID: {config.OWNER_ID}")
            logger.info(f"  • Admin Count: {len(config.ADMINS)}")
            logger.info(f"  • Sudo Users: {len(config.SUDO_USERS)}")
            logger.info(f"  • Download Dir: {config.DOWNLOAD_DIR}")
            logger.info(f"  • Log Channel: {config.LOG_CHANNEL if config.LOG_CHANNEL else 'Not configured'}")
            
            logger.info("\n" + "="*60)
            logger.info("🎉 Bot Started Successfully!")
            logger.info(f"📞 Bot: @{me.username}")
            logger.info("="*60 + "\n")
            
        except Exception as e:
            logger.error(f"❌ Startup error: {e}", exc_info=True)

    async def on_shutdown(self):
        """Handle bot shutdown gracefully"""
        try:
            logger.info("\n" + "="*60)
            logger.info("⏹️  Shutting down bot gracefully...")
            logger.info("="*60)
            
            # Stop processing
            bot_state.bot_active = False
            bot_state.processing_active = False
            logger.info("✅ Bot state set to inactive")
            
            # Cleanup database connections
            if db._connected:
                db.disconnect()
                logger.info("✅ Database disconnected")
            
            # Cleanup temporary files
            try:
                from modules.utils import cleanup_files
                await cleanup_files(config.DOWNLOAD_DIR)
                logger.info("✅ Temporary files cleaned")
            except Exception as cleanup_error:
                logger.warning(f"⚠️ Cleanup error: {cleanup_error}")
            
            logger.info("✅ Shutdown complete")
            logger.info("="*60 + "\n")
            
        except Exception as e:
            logger.error(f"❌ Shutdown error: {e}", exc_info=True)

# ==================== MAIN EXECUTION ====================

async def main():
    """Main execution function"""
    
    try:
        # Create bot client
        bot = BotClient()
        
        # Initialize bot
        if not await bot.init_bot():
            logger.critical("❌ Failed to initialize bot. Exiting...")
            sys.exit(1)
        
        # Register all handlers
        if not await bot.register_all_handlers():
            logger.critical("❌ Failed to register handlers. Exiting...")
            sys.exit(1)
        
        # Setup startup/shutdown handlers
        @bot.app.on_start()
        async def on_start():
            await bot.on_startup()
        
        @bot.app.on_stop()
        async def on_stop():
            await bot.on_shutdown()
        
        # Start bot
        logger.info("▶️  Starting bot polling...")
        await bot.app.start()
        logger.info("✅ Bot is running! Press Ctrl+C to stop...")
        
        # Keep bot running
        await bot.app.idle()
        
    except KeyboardInterrupt:
        logger.info("\n⚠️  Received keyboard interrupt (Ctrl+C)")
    except Exception as e:
        logger.critical(f"❌ Critical error: {e}", exc_info=True)
        sys.exit(1)

# ==================== ENTRY POINT ====================

if __name__ == "__main__":
    try:
        import asyncio
        
        # Check Python version
        if sys.version_info < (3, 8):
            logger.critical("❌ Python 3.8+ required")
            sys.exit(1)
        
        # Check required environment variables
        required_vars = ["API_ID", "API_HASH", "BOT_TOKEN", "OWNER_ID"]
        missing = [var for var in required_vars if not os.environ.get(var)]
        
        if missing:
            logger.critical(f"❌ Missing environment variables: {', '.join(missing)}")
            logger.critical("❌ Please configure config.env with all required variables")
            sys.exit(1)
        
        # Run bot
        asyncio.run(main())
        
    except Exception as e:
        logger.critical(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
