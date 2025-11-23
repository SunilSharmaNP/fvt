# modules/bot_state.py
# Manages the global ACTIVE/HOLD state of the bot
import logging

logger = logging.getLogger(__name__)

# Default mode is HOLD
# Admin must use /activate to start processing
CURRENT_BOT_MODE = "HOLD"

def set_bot_mode(mode: str):
    """Sets the bot mode to ACTIVE or HOLD."""
    global CURRENT_BOT_MODE
    if mode in ["ACTIVE", "HOLD"]:
        CURRENT_BOT_MODE = mode
        logger.info(f"Bot mode set to: {CURRENT_BOT_MODE}")
    else:
        logger.warning(f"Invalid mode attempted: {mode}")

def get_bot_mode() -> str:
    """Returns the current bot mode."""
    return CURRENT_BOT_MODE

def is_bot_active() -> bool:
    """Checks if the bot mode is ACTIVE."""
    return CURRENT_BOT_MODE == "ACTIVE"

