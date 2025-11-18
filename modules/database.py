# modules/database.py (v6.0)
# MODIFIED for Granular 've' Repo UI (Step 1)
# 1. `get_default_settings` poori tarah rewrite kiya gaya hai.
#    - "encode_preset", "trim_time" etc. ko hata kar.
#    - Naye dictionaries: `encode_settings`, `trim_settings`, `watermark_settings`, `sample_settings` add kiye gaye hain.
# 2. NAYA Function: `update_user_nested_setting(user_id, key, value)` add kiya gaya hai.
#    Yeh nested keys (jaise "encode_settings.vcodec") ko update karne ke liye zaroori hai.

import motor.motor_asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import asyncio

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client = None
        self.db = None
        self.settings = None
        self.authorized_chats = None
        self.tasks = None
        self._connected = False
    
    def connect(self, mongo_uri: str, database_name: str):
        if self._connected:
            return True
        try:
            self.client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
            self.db = self.client[database_name]
            self.settings = self.db.user_settings 
            self.authorized_chats = self.db.authorized_chats
            self.tasks = self.db.tasks
            self._connected = True
            logger.info("✅ Successfully connected to the database.")
            return True
        except Exception as e:
            logger.error(f"❌ Could not connect to database: {e}")
            raise
    
    # MODIFIED: (v6.0) - Granular Settings Structure
    def get_default_settings(self, user_id: int):
        """Returns the default settings dictionary for a new user (Granular v6.0)."""
        from config import config
        bot_name = config.BOT_NAME if hasattr(config, 'BOT_NAME') else "SSVideoWorkstation"
        
        return {
            "user_id": user_id,
            "name": "",
            "username": "",
            "join_date": datetime.utcnow(),
            "last_active": datetime.utcnow(),
            "is_banned": False,
            "is_on_hold": False,
            
            # --- User Settings (/us) ---
            "upload_mode": "telegram",
            "download_mode": "telegram",
            "metadata": False,
            "custom_filename": bot_name.replace(" ", "_"),
            "custom_thumbnail": None,
            
            # --- Video Tools (/vt) ---
            "active_tool": "none",
            
            # (Simple tool, no dict needed)
            "merge_mode": "video+video",
            
            # (Granular Settings Dictionary)
            "encode_settings": {
                "vcodec": "libx264",
                "crf": 23,
                "preset": "medium",
                "resolution": "source", # 'source', '720p', '1080p', 'custom'
                "custom_resolution": "1280x720",
                "acodec": "aac",
                "abitrate": "128k",
                "suffix": "[ENC]"
            },
            
            # (Granular Settings Dictionary)
            "trim_settings": {
                "start": "00:00:00",
                "end": "00:00:30"
            },
            
            # (Granular Settings Dictionary)
            "watermark_settings": {
                "type": "none", # 'none', 'text', 'image'
                "text": f"@{bot_name}",
                "image_id": None,
                "position": "bottom_right", # 'top_left', 'top_right', 'bottom_left', 'bottom_right', 'center'
                "opacity": 0.7
            },
            
            # (Granular Settings Dictionary)
            "sample_settings": {
                "duration": 30, # in seconds
                "from_point": "start" # 'start', 'middle', 'end'
            },
            
            # --- New Tools Settings ---
            "rotate_settings": {
                "angle": 90 # 90, 180, 270
            },
            
            "flip_settings": {
                "direction": "horizontal" # 'horizontal', 'vertical'
            },
            
            "speed_settings": {
                "speed": 1.0 # 0.5, 0.75, 1.0, 1.25, 1.5, 2.0
            },
            
            "volume_settings": {
                "volume": 100 # percentage: 50, 100, 150, 200
            },
            
            "crop_settings": {
                "aspect_ratio": "16:9" # '16:9', '4:3', '1:1', '9:16', 'custom'
            },
            
            "gif_settings": {
                "fps": 10,
                "quality": "medium", # 'low', 'medium', 'high'
                "scale": 480 # width in pixels
            },
            
            "reverse_settings": {
                # Reverse tool has no configurable parameters
            },
            
            "extract_thumb_settings": {
                "mode": "single", # 'single', 'interval'
                "timestamp": "00:00:05",
                "count": 5
            },
            
            # --- NEW: Extract Tool Settings ---
            "extract_settings": {
                "mode": "video" # 'video', 'audio', 'subtitles', 'thumbnails'
            }
        }

    async def add_user(self, user_id: int, name: str, username: str):
        try:
            update_doc = {
                "name": name,
                "username": username,
                "last_active": datetime.utcnow()
            }
            default_settings = self.get_default_settings(user_id)
            
            # Remove fields from default_settings that will be set by $set to avoid conflict
            default_settings_insert = {k: v for k, v in default_settings.items() 
                                     if k not in ["name", "username", "last_active"]}
            
            await self.settings.update_one(
                {"user_id": user_id},
                {
                    "$set": update_doc,
                    "$setOnInsert": default_settings_insert
                },
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error adding/updating user {user_id}: {e}")
            return False

    async def update_user_activity(self, user_id: int):
        # ... (No Change)
        pass

    async def ban_user(self, user_id: int, status: bool = True):
        # ... (No Change)
        pass

    async def is_user_banned(self, user_id: int) -> bool:
        # ... (No Change)
        pass
            
    async def add_authorized_chat(self, chat_id: int):
        # ... (No Change)
        pass

    async def remove_authorized_chat(self, chat_id: int):
        # ... (No Change)
        pass

    async def is_authorized_chat(self, chat_id: int) -> bool:
        # ... (No Change)
        pass

    async def get_user_settings(self, user_id: int) -> dict:
        """Gets user settings, ensuring all new keys (like dicts) are present."""
        try:
            settings = await self.settings.find_one({"user_id": user_id})
            if not settings:
                logger.warning(f"No settings found for {user_id}. Creating defaults.")
                default_settings = self.get_default_settings(user_id)
                await self.settings.insert_one(default_settings)
                return default_settings
            
            # CRITICAL: Check for missing granular keys (e.g., 'encode_settings')
            default_data = self.get_default_settings(user_id)
            missing_keys = [k for k in default_data.keys() if k not in settings]
            
            if missing_keys:
                logger.info(f"Adding missing keys {missing_keys} for user {user_id}")
                update_doc = {k: default_data[k] for k in missing_keys}
                await self.settings.update_one(
                    {"user_id": user_id},
                    {"$set": update_doc}
                )
                settings.update(update_doc)
                
            # Check for missing SUB-keys (e.g., encode_settings.suffix)
            needs_sub_update = False
            update_doc = {}
            for main_key in ['encode_settings', 'trim_settings', 'watermark_settings', 'sample_settings',
                            'rotate_settings', 'flip_settings', 'speed_settings', 'volume_settings',
                            'crop_settings', 'gif_settings', 'reverse_settings', 'extract_thumb_settings',
                            'extract_settings']:
                if main_key in settings:
                    for sub_key in default_data[main_key].keys():
                        if sub_key not in settings[main_key]:
                            nested_key = f"{main_key}.{sub_key}"
                            update_doc[nested_key] = default_data[main_key][sub_key]
                            needs_sub_update = True
            
            if needs_sub_update:
                logger.info(f"Adding missing sub-keys {update_doc.keys()} for user {user_id}")
                await self.settings.update_one(
                    {"user_id": user_id},
                    {"$set": update_doc}
                )
                settings = await self.settings.find_one({"user_id": user_id}) # Re-fetch

            return settings
        except Exception as e:
            logger.error(f"Error getting settings for {user_id}: {e}")
            return self.get_default_settings(user_id)

    async def update_user_setting(self, user_id: int, key: str, value: any):
        """Updates a TOP-LEVEL setting for a user (e.g., 'active_tool')."""
        try:
            await self.settings.update_one(
                {"user_id": user_id},
                {"$set": {key: value, "last_active": datetime.utcnow()}},
                upsert=True # Just in case
            )
            return True
        except Exception as e:
            logger.error(f"Error updating setting '{key}' for {user_id}: {e}")
            return False
            
    # NAYA: (v6.0) - Granular Settings
    async def update_user_nested_setting(self, user_id: int, key: str, value: any):
        """
        Updates a NESTED setting using dot notation (e.g., "encode_settings.vcodec").
        """
        try:
            await self.settings.update_one(
                {"user_id": user_id},
                {"$set": {key: value, "last_active": datetime.utcnow()}}
                # $set with dot notation updates only that field
            )
            logger.info(f"Updated nested setting for {user_id}: {key} = {value}")
            return True
        except Exception as e:
            logger.error(f"Error updating nested setting '{key}' for {user_id}: {e}")
            return False

    async def toggle_user_setting(self, user_id: int, key: str) -> bool:
        """Toggles a TOP-LEVEL boolean setting for a user."""
        try:
            current_settings = await self.get_user_settings(user_id)
            new_value = not current_settings.get(key, False)
            await self.update_user_setting(user_id, key, new_value)
            return new_value
        except Exception as e:
            logger.error(f"Error toggling setting '{key}' for {user_id}: {e}")
            return False
    
    # --- Task Collection Methods ---
    
    async def create_task(self, user_id: int, tool: str, input_source: str) -> Optional[str]:
        # ... (No Change)
        try:
            task_id = str(uuid.uuid4())[:8]
            task_doc = {
                "task_id": task_id,
                "user_id": user_id,
                "tool": tool,
                "input_source": input_source,
                "status": "pending",
                "progress_percent": 0,
                "process_group_id": None,
                "output_name": None,
                "upload_target": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "error_msg": None
            }
            await self.tasks.insert_one(task_doc)
            logger.info(f"Task {task_id} created for user {user_id}")
            return task_id
        except Exception as e:
            logger.error(f"Error creating task for user {user_id}: {e}")
            return None
    
    async def update_task(self, task_id: str, updates: dict) -> bool:
        # ... (No Change)
        try:
            updates["updated_at"] = datetime.utcnow()
            await self.tasks.update_one(
                {"task_id": task_id},
                {"$set": updates}
            )
            return True
        except Exception as e:
            logger.error(f"Error updating task {task_id}: {e}")
            return False
    
    async def get_task(self, task_id: str) -> Optional[Dict]:
        try:
            return await self.tasks.find_one({"task_id": task_id})
        except Exception as e:
            logger.error(f"Error getting task {task_id}: {e}")
            return None
    
    async def delete_task(self, task_id: str) -> bool:
        # ... (No Change)
        try:
            await self.tasks.delete_one({"task_id": task_id})
            return True
        except Exception as e:
            logger.error(f"Error deleting task {task_id}: {e}")
            return False
            
    async def is_user_task_running(self, user_id: int) -> bool:
        # ... (No Change)
        try:
            running_task = await self.tasks.find_one({
                "user_id": user_id,
                "status": {"$in": ["pending", "downloading", "processing", "uploading"]}
            })
            return bool(running_task)
        except Exception as e:
            logger.error(f"Error checking user task status for {user_id}: {e}")
            return False

# Create database instance
db = Database()
