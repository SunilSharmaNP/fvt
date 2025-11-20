# modules/database.py (v6.9 - enhanced)
# Complete, ready-to-run stable database helper for SS Video Workstation
import motor.motor_asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)


class Database:

    def __init__(self):
        self.client = None
        self.db = None
        self.settings = None
        self.authorized_chats = None
        self.tasks = None
        self.temp_covers = None  # collection for temporary covers (HD cover tool)
        self._connected = False

    # ----------------------
    # Connection / Lifecycle
    # ----------------------
    def connect(self, mongo_uri: str, database_name: str, **kwargs):
        """
        Initialize motor AsyncIOMotorClient.
        Returns True on success; raises on failure.
        Extra kwargs forwarded to AsyncIOMotorClient if needed.
        """
        if self._connected:
            return True
        try:
            self.client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri, **kwargs)
            self.db = self.client[database_name]
            self.settings = self.db.user_settings
            self.authorized_chats = self.db.authorized_chats
            self.tasks = self.db.tasks
            self.temp_covers = self.db.temp_covers
            self._connected = True

            # Ensure indexes for quick lookups
            try:
                self.ensure_indexes()
            except Exception as ie:
                logger.warning(f"Index creation warning: {ie}")

            logger.info("✅ Successfully connected to the database.")
            return True
        except Exception as e:
            logger.error(f"❌ Could not connect to database: {e}", exc_info=True)
            raise

    def close(self):
        """Close motor client connection."""
        try:
            if self.client:
                self.client.close()
            self._connected = False
            logger.info("🛑 Database connection closed.")
        except Exception as e:
            logger.warning(f"Error closing DB client: {e}")

    async def ping(self) -> bool:
        """Async ping to check DB responsiveness."""
        try:
            # 'ping' command is supported by pymongo/motor
            await self.db.command("ping")
            return True
        except Exception as e:
            logger.error(f"Database ping failed: {e}")
            return False

    def ensure_indexes(self):
        """Create common indexes (synchronous calls on motor collection objects are fine)."""
        try:
            # settings: unique user_id
            self.settings.create_index("user_id", unique=True)
            # tasks: index by task_id and user_id
            self.tasks.create_index("task_id", unique=True)
            self.tasks.create_index("user_id")
            self.tasks.create_index("status")
            # authorized chats
            self.authorized_chats.create_index("chat_id", unique=True)
            # temp covers
            self.temp_covers.create_index("user_id", unique=True)
            logger.debug("Created/ensured database indexes.")
        except Exception as e:
            logger.warning(f"Could not create indexes: {e}")

    def ensure_collections(self):
        """
        Optionally call to ensure collections exist (touch them).
        This is helpful in initial setup scripts.
        """
        try:
            # touch/ensure by creating if not exists an index call
            _ = self.settings.name
            _ = self.tasks.name
            _ = self.authorized_chats.name
            _ = self.temp_covers.name
            logger.debug("Collections checked.")
        except Exception as e:
            logger.warning(f"Error ensuring collections: {e}")

    # ----------------------
    # Default settings
    # ----------------------
    def get_default_settings(self, user_id: int) -> Dict[str, Any]:
        """Returns the default settings dictionary for a new user."""
        try:
            from config import config
            bot_name = config.BOT_NAME if hasattr(config, "BOT_NAME") else "SSVideoWorkstation"
        except Exception:
            bot_name = "SSVideoWorkstation"

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
            "metadata_custom": {},
            "custom_filename": bot_name.replace(" ", "_"),
            "custom_thumbnail": None,

            # --- Video Tools (/vt) ---
            "active_tool": "none",
            "merge_mode": "video+video",

            "encode_settings": {
                "vcodec": "libx264",
                "crf": 23,
                "preset": "medium",
                "resolution": "source",
                "custom_resolution": "1280x720",
                "acodec": "aac",
                "abitrate": "128k",
                "suffix": "[ENC]"
            },
            "trim_settings": {
                "start": "00:00:00",
                "end": "00:00:30"
            },
            "watermark_settings": {
                "type": "none",
                "text": f"@{bot_name}",
                "image_id": None,
                "position": "bottom_right",
                "opacity": 0.7
            },
            "sample_settings": {
                "duration": 30,
                "from_point": "start"
            },

            # --- New Tools Settings ---
            "rotate_settings": {
                "angle": 90
            },
            "flip_settings": {
                "direction": "horizontal"
            },
            "speed_settings": {
                "speed": 1.0
            },
            "volume_settings": {
                "volume": 100
            },
            "crop_settings": {
                "aspect_ratio": "16:9"
            },
            "gif_settings": {
                "fps": 10,
                "quality": "medium",
                "scale": 480
            },
            "reverse_settings": {},
            "extract_thumb_settings": {
                "mode": "single",
                "timestamp": "00:00:05",
                "count": 5
            },
            "extract_settings": {
                "mode": "video"
            },
            # New Screenshot settings
            "screenshot_settings": {
                "count": 5
            },
            # New Audio Remover settings
            "audioremover_settings": {
                "mode": "remove"
            }
        }

    # ----------------------
    # User lifecycle helpers
    # ----------------------
    async def add_user(self, user_id: int, name: str = "", username: str = "") -> bool:
        """
        Insert or update a user. Ensures default settings are set on first insert.
        """
        try:
            update_doc = {
                "name": name or "",
                "username": username or "",
                "last_active": datetime.utcnow()
            }
            default_settings = self.get_default_settings(user_id)

            # Remove fields that are set by update_doc
            default_settings_insert = {
                k: v
                for k, v in default_settings.items()
                if k not in ["name", "username", "last_active"]
            }

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
            logger.error(f"Error adding/updating user {user_id}: {e}", exc_info=True)
            return False

    async def get_user_settings(self, user_id: int) -> Dict[str, Any]:
        """
        Gets user settings, ensuring all new keys (and nested subkeys) are present.
        Returns a plain dict (motor returns dict-like).
        """
        try:
            settings = await self.settings.find_one({"user_id": user_id})
            if not settings:
                logger.warning(f"No settings found for {user_id}. Creating defaults.")
                default_settings = self.get_default_settings(user_id)
                await self.settings.insert_one(default_settings)
                return default_settings

            # Add missing top-level keys
            default_data = self.get_default_settings(user_id)
            missing_keys = [k for k in default_data.keys() if k not in settings]
            if missing_keys:
                logger.info(f"Adding missing keys {missing_keys} for user {user_id}")
                update_doc = {k: default_data[k] for k in missing_keys}
                await self.settings.update_one({"user_id": user_id}, {"$set": update_doc})
                settings.update(update_doc)

            # Ensure nested keys for dictionaries
            needs_sub_update = False
            update_doc = {}
            keys_to_check = [
                'encode_settings', 'trim_settings', 'watermark_settings',
                'sample_settings', 'rotate_settings', 'flip_settings',
                'speed_settings', 'volume_settings', 'crop_settings',
                'gif_settings', 'reverse_settings', 'extract_thumb_settings',
                'extract_settings', 'screenshot_settings', 'audioremover_settings',
                'metadata_custom'
            ]

            for main_key in keys_to_check:
                default_sub = default_data.get(main_key, {})
                # If default_sub is not a dict, skip
                if not isinstance(default_sub, dict):
                    continue

                # If main key missing in settings add the whole dict
                if main_key not in settings:
                    update_doc[main_key] = default_sub
                    needs_sub_update = True
                else:
                    # Ensure sub keys exist
                    current_sub = settings.get(main_key) or {}
                    if not isinstance(current_sub, dict):
                        current_sub = {}
                    for sub_key, sub_val in default_sub.items():
                        if sub_key not in current_sub:
                            nested_key = f"{main_key}.{sub_key}"
                            update_doc[nested_key] = sub_val
                            needs_sub_update = True

            if needs_sub_update:
                logger.info(f"Adding missing sub-keys {list(update_doc.keys())} for user {user_id}")
                await self.settings.update_one({"user_id": user_id}, {"$set": update_doc})
                settings = await self.settings.find_one({"user_id": user_id})

            # Always return a dict (not a Motor cursor)
            return settings
        except Exception as e:
            logger.error(f"Error getting settings for {user_id}: {e}", exc_info=True)
            return self.get_default_settings(user_id)

    async def update_user_setting(self, user_id: int, key: str, value: Any) -> bool:
        """Updates a TOP-LEVEL setting for a user."""
        try:
            await self.settings.update_one(
                {"user_id": user_id},
                {"$set": {key: value, "last_active": datetime.utcnow()}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error updating setting '{key}' for {user_id}: {e}", exc_info=True)
            return False

    async def update_user_nested_setting(self, user_id: int, key: str, value: Any) -> bool:
        """Updates a NESTED setting using dot notation (e.g. 'encode_settings.crf')."""
        try:
            await self.settings.update_one(
                {"user_id": user_id},
                {"$set": {key: value, "last_active": datetime.utcnow()}}
            )
            logger.info(f"Updated nested setting for {user_id}: {key} = {value}")
            return True
        except Exception as e:
            logger.error(f"Error updating nested setting '{key}' for {user_id}: {e}", exc_info=True)
            return False

    async def toggle_user_setting(self, user_id: int, key: str) -> bool:
        """Flip a boolean top-level setting (returns new value)."""
        try:
            current_settings = await self.get_user_settings(user_id)
            current = current_settings.get(key, False)
            new_value = not bool(current)
            await self.update_user_setting(user_id, key, new_value)
            return new_value
        except Exception as e:
            logger.error(f"Error toggling setting '{key}' for {user_id}: {e}", exc_info=True)
            return False

    async def update_user_last_active(self, user_id: int) -> bool:
        """Update last_active timestamp for a user."""
        try:
            await self.settings.update_one({"user_id": user_id}, {"$set": {"last_active": datetime.utcnow()}})
            return True
        except Exception as e:
            logger.error(f"Error updating last_active for {user_id}: {e}", exc_info=True)
            return False

    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Lookup user settings by username (if stored)."""
        try:
            return await self.settings.find_one({"username": username})
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {e}", exc_info=True)
            return None

    # ----------------------
    # Temp cover / HD cover helpers
    # ----------------------
    async def save_temp_cover(self, user_id: int, file_id: str) -> bool:
        """Saves the file_id of the cover image sent by user."""
        try:
            await self.temp_covers.update_one({"user_id": user_id}, {"$set": {"file_id": file_id, "created_at": datetime.utcnow()}}, upsert=True)
            return True
        except Exception as e:
            logger.error(f"Error saving temp cover for {user_id}: {e}", exc_info=True)
            return False

    async def get_temp_cover(self, user_id: int) -> Optional[str]:
        """Gets the saved cover file_id."""
        try:
            doc = await self.temp_covers.find_one({"user_id": user_id})
            return doc.get("file_id") if doc else None
        except Exception as e:
            logger.error(f"Error getting temp cover for {user_id}: {e}", exc_info=True)
            return None

    async def delete_temp_cover(self, user_id: int) -> bool:
        """Deletes the saved cover."""
        try:
            await self.temp_covers.delete_one({"user_id": user_id})
            return True
        except Exception as e:
            logger.error(f"Error deleting temp cover for {user_id}: {e}", exc_info=True)
            return False

    # ----------------------
    # Ban / Unban / Check Methods
    # ----------------------
    async def is_user_banned(self, user_id: int) -> bool:
        """Checks if the user is banned."""
        try:
            user = await self.settings.find_one({"user_id": user_id}, {"is_banned": 1})
            return bool(user and user.get("is_banned", False))
        except Exception as e:
            logger.error(f"Error checking ban status for {user_id}: {e}", exc_info=True)
            return False

    async def ban_user(self, user_id: int) -> bool:
        """Ban a user."""
        try:
            await self.settings.update_one({"user_id": user_id}, {"$set": {"is_banned": True}})
            return True
        except Exception as e:
            logger.error(f"Error banning user {user_id}: {e}", exc_info=True)
            return False

    async def unban_user(self, user_id: int) -> bool:
        """Unban a user."""
        try:
            await self.settings.update_one({"user_id": user_id}, {"$set": {"is_banned": False}})
            return True
        except Exception as e:
            logger.error(f"Error unbanning user {user_id}: {e}", exc_info=True)
            return False

    # ----------------------
    # Task collection methods
    # ----------------------
    async def create_task(self, user_id: int, tool: str, input_source: str) -> Optional[str]:
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
            logger.error(f"Error creating task for user {user_id}: {e}", exc_info=True)
            return None

    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        try:
            updates["updated_at"] = datetime.utcnow()
            await self.tasks.update_one({"task_id": task_id}, {"$set": updates})
            return True
        except Exception as e:
            logger.error(f"Error updating task {task_id}: {e}", exc_info=True)
            return False

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        try:
            return await self.tasks.find_one({"task_id": task_id})
        except Exception as e:
            logger.error(f"Error getting task {task_id}: {e}", exc_info=True)
            return None

    async def delete_task(self, task_id: str) -> bool:
        try:
            await self.tasks.delete_one({"task_id": task_id})
            return True
        except Exception as e:
            logger.error(f"Error deleting task {task_id}: {e}", exc_info=True)
            return False

    async def is_user_task_running(self, user_id: int) -> bool:
        try:
            running_task = await self.tasks.find_one({
                "user_id": user_id,
                "status": {"$in": ["pending", "downloading", "processing", "uploading"]}
            })
            return bool(running_task)
        except Exception as e:
            logger.error(f"Error checking user task status for {user_id}: {e}", exc_info=True)
            return False

    async def list_tasks_for_user(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent tasks for a user (most recent first)."""
        try:
            cursor = self.tasks.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as e:
            logger.error(f"Error listing tasks for user {user_id}: {e}", exc_info=True)
            return []

    async def find_tasks(self, filter_doc: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        try:
            cursor = self.tasks.find(filter_doc).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as e:
            logger.error(f"Error finding tasks: {e}", exc_info=True)
            return []

    # ----------------------
    # Misc helpers / stats
    # ----------------------
    async def get_all_user_ids(self) -> List[int]:
        try:
            users = await self.settings.find({}, {"user_id": 1}).to_list(length=None)
            return [user["user_id"] for user in users]
        except Exception as e:
            logger.error(f"Error getting user IDs: {e}", exc_info=True)
            return []

    async def get_total_users_count(self) -> int:
        try:
            return await self.settings.count_documents({})
        except Exception as e:
            logger.error(f"Error counting users: {e}", exc_info=True)
            return 0

    async def get_total_tasks_count(self) -> int:
        try:
            return await self.tasks.count_documents({})
        except Exception as e:
            logger.error(f"Error counting tasks: {e}", exc_info=True)
            return 0

    async def get_completed_tasks_count(self) -> int:
        try:
            return await self.tasks.count_documents({"status": "completed"})
        except Exception as e:
            logger.error(f"Error counting completed tasks: {e}", exc_info=True)
            return 0

    # ----------------------
    # Authorized chats helpers
    # ----------------------
    async def add_authorized_chat(self, chat_id: int) -> bool:
        try:
            await self.authorized_chats.update_one({"chat_id": chat_id}, {"$set": {"added_at": datetime.utcnow()}}, upsert=True)
            return True
        except Exception as e:
            logger.error(f"Error adding authorized chat {chat_id}: {e}", exc_info=True)
            return False

    async def remove_authorized_chat(self, chat_id: int) -> bool:
        try:
            await self.authorized_chats.delete_one({"chat_id": chat_id})
            return True
        except Exception as e:
            logger.error(f"Error removing authorized chat {chat_id}: {e}", exc_info=True)
            return False

    async def is_authorized_chat(self, chat_id: int) -> bool:
        try:
            chat = await self.authorized_chats.find_one({"chat_id": chat_id})
            return bool(chat)
        except Exception as e:
            logger.error(f"Error checking authorized chat {chat_id}: {e}", exc_info=True)
            return False

    # ----------------------
    # Broadcast / utility helpers
    # ----------------------
    async def get_users_for_broadcast(self, batch: int = 100, exclude_banned: bool = True) -> List[List[int]]:
        """
        Return list of user_id batches for broadcast.
        Each item is a list with up to `batch` user ids.
        """
        try:
            query = {}
            if exclude_banned:
                query["is_banned"] = {"$ne": True}
            cursor = self.settings.find(query, {"user_id": 1})
            user_docs = await cursor.to_list(length=None)
            user_ids = [d["user_id"] for d in user_docs]
            # split into chunks
            chunks = [user_ids[i:i + batch] for i in range(0, len(user_ids), batch)]
            return chunks
        except Exception as e:
            logger.error(f"Error getting users for broadcast: {e}", exc_info=True)
            return []

    async def get_users_active_since(self, since_ts: datetime) -> List[int]:
        """Return users whose last_active >= since_ts."""
        try:
            cursor = self.settings.find({"last_active": {"$gte": since_ts}}, {"user_id": 1})
            docs = await cursor.to_list(length=None)
            return [d["user_id"] for d in docs]
        except Exception as e:
            logger.error(f"Error getting active users since {since_ts}: {e}", exc_info=True)
            return []


# Create database instance
db = Database()
