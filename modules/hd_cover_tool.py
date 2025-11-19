# modules/hd_cover_tool.py
# HD Cover/Thumbnail Tool - Add custom cover to videos
# Based on attached hdcoverset feature

import logging
from pyrogram import Client, filters
from pyrogram.types import InputMediaVideo, Message
from modules.database import db

logger = logging.getLogger(__name__)

# User thumbnail storage (in-memory cache)
user_thumbnails = {}


async def handle_thumbnail_photo(client: Client, message: Message):
    """Handle photo sent by user - save as thumbnail"""
    try:
        user_id = message.from_user.id
        
        # Check if tool is enabled
        settings = await db.get_user_settings(user_id)
        active_tool = settings.get("active_tool", "none")
        
        if active_tool != "hdcover":
            return
        
        photo_file_id = message.photo[-1].file_id
        
        # Store in cache
        user_thumbnails[user_id] = photo_file_id
        
        # Also save to database for persistence
        await db.user_settings.update_one(
            {"user_id": user_id},
            {"$set": {"custom_thumbnail": photo_file_id}},
            upsert=True
        )
        
        await message.reply_text(
            "✅ **Thumbnail Saved Successfully!**\n\n"
            "Ab video bhejiye to yahi thumbnail lagega.",
            reply_to_message_id=message.id
        )
        logger.info(f"User {user_id} saved thumbnail: {photo_file_id}")
        
    except Exception as e:
        logger.error(f"Error saving thumbnail: {e}")
        await message.reply_text("❌ Thumbnail save nahi hua, phir se try karein.")


async def handle_video_with_cover(client: Client, message: Message):
    """Add saved thumbnail as HD cover to video"""
    try:
        user_id = message.from_user.id
        
        # Check if tool is enabled
        settings = await db.get_user_settings(user_id)
        active_tool = settings.get("active_tool", "none")
        
        if active_tool != "hdcover":
            return
        
        # Check if user has saved thumbnail
        thumbnail = user_thumbnails.get(user_id)
        
        if not thumbnail:
            # Check database
            settings = await db.user_settings.find_one({"user_id": user_id})
            if settings and settings.get("custom_thumbnail"):
                thumbnail = settings["custom_thumbnail"]
                user_thumbnails[user_id] = thumbnail
        
        if not thumbnail:
            return await message.reply_text(
                "❌ **Pehle thumbnail bhejiye!**\n\n"
                "Photo bhejiye jise aap video cover banana chahte hain.",
                reply_to_message_id=message.id
            )
        
        # Send processing message
        msg = await message.reply_text(
            "🔄 **Adding HD Cover...**\n\n"
            "Please wait...",
            reply_to_message_id=message.id
        )
        
        video_file_id = message.video.file_id
        caption = message.caption or "✅ **HD Cover Added**"
        
        # Create InputMediaVideo with custom cover
        media = InputMediaVideo(
            media=video_file_id,
            caption=caption,
            supports_streaming=True,
            thumb=thumbnail
        )
        
        # Edit message with video + cover
        await client.edit_message_media(
            chat_id=message.chat.id,
            message_id=msg.id,
            media=media
        )
        
        logger.info(f"User {user_id} added HD cover to video")
        
    except Exception as e:
        logger.error(f"Error adding video cover: {e}")
        await message.reply_text(
            f"❌ **Cover add karne mein error:**\n\n`{str(e)}`"
        )


async def handle_remove_thumbnail(client: Client, message: Message):
    """Remove saved thumbnail"""
    try:
        user_id = message.from_user.id
        
        # Check if tool is enabled
        settings = await db.get_user_settings(user_id)
        active_tool = settings.get("active_tool", "none")
        
        if active_tool != "hdcover":
            return await message.reply_text(
                "⚠️ **HD Cover tool is not enabled!**\n\n"
                "Please enable it from:\n"
                "**Video Tools → 🖼️ HD Cover**"
            )
        
        # Remove from cache
        if user_id in user_thumbnails:
            user_thumbnails.pop(user_id)
        
        # Remove from database
        await db.user_settings.update_one(
            {"user_id": user_id},
            {"$unset": {"custom_thumbnail": ""}}
        )
        
        await message.reply_text(
            "✅ **Thumbnail Removed Successfully!**",
            reply_to_message_id=message.id
        )
        logger.info(f"User {user_id} removed thumbnail")
        
    except Exception as e:
        logger.error(f"Error removing thumbnail: {e}")
        await message.reply_text("⚠️ Pehle thumbnail add karein.")


# Handler registration function
def register_hd_cover_handlers(app: Client):
    """Register HD Cover tool handlers"""
    
    # Photo handler - save thumbnail
    @app.on_message(filters.photo & filters.private)
    async def photo_handler(client, message):
        await handle_thumbnail_photo(client, message)
    
    # Video handler - add cover (only if thumbnail exists)
    @app.on_message(filters.video & filters.private)
    async def video_handler(client, message):
        # Check if this is a video processing command
        # If yes, skip HD cover and let other handlers process it
        if message.caption and message.caption.startswith('/'):
            return
        await handle_video_with_cover(client, message)
    
    # Command to remove thumbnail
    @app.on_message(filters.command("removethumb") & filters.private)
    async def remove_handler(client, message):
        await handle_remove_thumbnail(client, message)
    
    logger.info("✅ HD Cover tool handlers registered")
