# modules/settings.py
# NAYA: Aapke plan (Phase 2) ke anusaar User Settings ko manage karne ke liye
import logging
from datetime import datetime
from modules.database import db

logger = logging.getLogger(__name__)

# Aapke plan ke anusaar default settings
def get_default_settings(user_id: int, name: str, username: str) -> dict:
    """Naye user ke liye default settings structure return karein"""
    return {
        "user_id": user_id,
        "name": name,
        "username": username,
        
        # Upload Settings
        "upload_as": "video",  # "video" ya "document"
        
        # Merge Mode
        "mode": "video+video",  # Default mode
        
        # Feature Toggles
        "gofile_enabled": False,
        "metadata_enabled": False, # Default: metadata remove karein
        "thumbnail_enabled": True, # Default: custom thumbnail maangein
        "encode_enabled": False,
        "trim_enabled": False, # Default: trim disabled
        
        # Custom Settings
        "custom_thumbnail": None,  # File path or None
        "trim_settings": {
            "enabled": False,
            "start_time": "00:00:00",
            "end_time": "00:00:00"
        },
        
        # Status
        "ban_status": False,
        "created_at": datetime.utcnow(),
        "last_updated": datetime.utcnow()
    }

async def init_user_settings(user_id: int, name: str, username: str):
    """Naye user ke liye database mein default settings banayein."""
    try:
        existing_settings = await db.user_settings.find_one({"user_id": user_id})
        if not existing_settings:
            default_settings = get_default_settings(user_id, name, username)
            await db.user_settings.insert_one(default_settings)
            logger.info(f"User {user_id} ke liye default settings initialize kiye gaye.")
    except Exception as e:
        logger.error(f"Error init_user_settings({user_id}): {e}")

async def get_user_settings(user_id: int) -> dict:
    """Database se user settings fetch karein, agar nahi hai to default return karein."""
    try:
        settings = await db.user_settings.find_one({"user_id": user_id})
        if settings:
            return settings
        else:
            # Agar user settings mein nahi hai (lekin users table mein hai)
            # To on-the-fly default return karein (lekin save na karein)
            # init_user_settings ko /start mein call karna behtar hai
            logger.warning(f"User {user_id} ke liye settings nahi mile. Default return kar rahe hain.")
            # Note: Aasli user ka naam/username yahaan nahi milega, isliye default use karein
            return get_default_settings(user_id, "Unknown", "unknown")
    except Exception as e:
        logger.error(f"Error get_user_settings({user_id}): {e}")
        return get_default_settings(user_id, "Error", "error")

async def update_user_setting(user_id: int, key: str, value):
    """User ki ek specific setting update karein."""
    try:
        await db.user_settings.update_one(
            {"user_id": user_id},
            {"$set": {key: value, "last_updated": datetime.utcnow()}}
        )
        logger.info(f"User {user_id} ki setting update ki: {key} = {value}")
        return True
    except Exception as e:
        logger.error(f"Error update_user_setting({user_id}, {key}): {e}")
        return False

async def toggle_user_setting(user_id: int, key: str) -> bool | None:
    """User ki boolean (True/False) setting ko toggle (ulta) karein."""
    try:
        # Pehle current value fetch karein
        settings = await get_user_settings(user_id)
        current_value = settings.get(key, False)
        
        # Toggle karein
        new_value = not current_value
        
        # Update karein
        await update_user_setting(user_id, key, new_value)
        return new_value
    except Exception as e:
        logger.error(f"Error toggle_user_setting({user_id}, {key}): {e}")
        return None
