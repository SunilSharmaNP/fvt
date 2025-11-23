# modules/hd_cover_tool.py
# HD Cover/Thumbnail Tool - Add custom cover to videos instantly without downloading
# Based on Pyrogram's InputMediaVideo with cover parameter

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
        await db.update_user_setting(user_id, "hd_cover_thumbnail", photo_file_id)
        
        await message.reply_text(
            "✅ **Cover Image Saved Successfully!**\n\n"
            "Now send any video, I will instantly add this cover without downloading.\n\n"
            "💡 **No re-encoding required** - instant processing!",
            reply_to_message_id=message.id
        )
        logger.info(f"User {user_id} saved HD cover thumbnail: {photo_file_id}")
        
    except Exception as e:
        logger.error(f"Error saving thumbnail: {e}")
        await message.reply_text("❌ Error saving cover image. Please try again.")


async def handle_video_with_cover(client: Client, message: Message):
    """Add saved thumbnail as HD cover to video instantly (no download required)"""
    log_id = None
    try:
        from modules.log_manager import log_simple_task, log_simple_complete
        
        user_id = message.from_user.id
        user = message.from_user
        
        # Check if tool is enabled
        settings = await db.get_user_settings(user_id)
        active_tool = settings.get("active_tool", "none")
        
        if active_tool != "hdcover":
            return
        
        # Check if user has saved thumbnail
        thumbnail = user_thumbnails.get(user_id)
        
        if not thumbnail:
            # Check database
            thumbnail = settings.get("hd_cover_thumbnail")
            if thumbnail:
                user_thumbnails[user_id] = thumbnail
        
        if not thumbnail:
            return await message.reply_text(
                "❌ **First send a cover image!**\n\n"
                "Send a photo that you want to use as the video cover/thumbnail.",
                reply_to_message_id=message.id
            )
        
        # Create task log
        log_id = await log_simple_task(client, user, "HD Cover", "Instant cover addition")
        
        # Send processing message
        msg = await message.reply_text(
            "🔄 **Adding HD Cover...**\n\nThis is instant - no download needed!",
            reply_to_message_id=message.id
        )
        
        video_file_id = message.video.file_id
        
        # Preserve original caption or use default
        caption = message.caption if message.caption else "✅ **HD Cover Added Successfully!**"
        
        # Create InputMediaVideo with custom cover (no download - instant processing)
        media = InputMediaVideo(
            media=video_file_id,
            caption=caption,
            supports_streaming=True,
            thumb=thumbnail  # This adds the cover without downloading the video
        )
        
        # Edit message with video + cover (instant operation)
        await client.edit_message_media(
            chat_id=message.chat.id,
            message_id=msg.id,
            media=media
        )
        
        # Complete log
        await log_simple_complete(client, log_id, True)
        
        logger.info(f"User {user_id} added HD cover to video instantly")
        
    except Exception as e:
        logger.error(f"Error adding video cover: {e}")
        
        # Log error
        if log_id:
            from modules.log_manager import log_simple_complete
            await log_simple_complete(client, log_id, False, str(e))
        
        await message.reply_text(
            f"❌ **Error adding cover:**\n\n`{str(e)}`"
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
