# modules/screenshot_tool.py
# Screenshot Generator Tool - Extract screenshots from video
# Based on attached screenshot_generator feature

import os
import random
import logging
import tempfile
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

logger = logging.getLogger(__name__)

# User session storage
screenshot_sessions = {}


async def handle_screenshot_command(client: Client, message: Message):
    """Handle /ss command - ask for screenshot count"""
    try:
        from modules.database import db
        
        user_id = message.from_user.id
        
        # Check if tool is enabled
        settings = await db.get_user_settings(user_id)
        active_tool = settings.get("active_tool", "none")
        
        if active_tool != "screenshot":
            return await message.reply_text(
                "⚠️ **Screenshot tool is not enabled!**\n\n"
                "Please enable it from:\n"
                "**Video Tools → 📸 Screenshot**"
            )
        
        # Check if replying to video
        if not message.reply_to_message or not message.reply_to_message.video:
            return await message.reply_text(
                "⚠️ **Please reply to a video with /ss command**\n\n"
                "Usage: Reply to video → `/ss`"
            )
        
        video_msg = message.reply_to_message
        
        # Store session
        screenshot_sessions[user_id] = {
            "video_msg": video_msg,
            "message_id": message.id
        }
        
        # Ask for count
        await message.reply_text(
            "📸 **How many screenshots do you want?**\n\n"
            "Select below:",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("1", callback_data="ss_1"),
                    InlineKeyboardButton("3", callback_data="ss_3"),
                    InlineKeyboardButton("5", callback_data="ss_5"),
                ],
                [
                    InlineKeyboardButton("10", callback_data="ss_10"),
                    InlineKeyboardButton("15", callback_data="ss_15"),
                    InlineKeyboardButton("20", callback_data="ss_20"),
                ]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error in screenshot command: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")


async def handle_screenshot_callback(client: Client, callback_query):
    """Handle screenshot count selection"""
    try:
        from modules.database import db
        
        user_id = callback_query.from_user.id
        
        # Re-check if tool is still enabled (prevent mid-session disable bypass)
        settings = await db.get_user_settings(user_id)
        active_tool = settings.get("active_tool", "none")
        
        if active_tool != "screenshot":
            return await callback_query.answer(
                "⚠️ Screenshot tool was disabled!",
                show_alert=True
            )
        
        ss_count = int(callback_query.data.split("_")[1])
        
        # Check session
        if user_id not in screenshot_sessions:
            return await callback_query.answer(
                "⚠️ Session expired. Use /ss again!",
                show_alert=True
            )
        
        session = screenshot_sessions[user_id]
        video_msg = session["video_msg"]
        
        # Update message
        msg = await callback_query.message.edit_text(
            f"📥 **Downloading video...**\n\n"
            f"Screenshots: `{ss_count}`"
        )
        
        # Download video
        file_path = await video_msg.download()
        
        await msg.edit_text(
            f"🎲 **Generating {ss_count} random timestamps...**"
        )
        
        # Get video duration
        from modules.utils import get_video_info
        info = get_video_info(file_path)
        
        if not info or not info.get('duration'):
            os.remove(file_path)
            return await msg.edit_text("❌ Could not read video duration")
        
        total_seconds = int(info['duration'])
        
        # Generate random timestamps (avoid first/last 2 seconds)
        safe_start = 2
        safe_end = max(safe_start + 1, total_seconds - 2)
        
        if safe_end <= safe_start:
            os.remove(file_path)
            return await msg.edit_text("❌ Video too short for screenshots")
        
        timestamps = sorted(random.sample(range(safe_start, safe_end), min(ss_count, safe_end - safe_start)))
        
        await msg.edit_text(
            f"📸 **Taking {len(timestamps)} screenshots...**"
        )
        
        # Extract screenshots using FFmpeg
        import subprocess
        output_files = []
        temp_dir = tempfile.mkdtemp()
        
        for i, ts in enumerate(timestamps):
            out_file = os.path.join(temp_dir, f"screenshot_{i+1}.jpg")
            
            cmd = [
                "ffmpeg", "-ss", str(ts),
                "-i", file_path,
                "-frames:v", "1",
                "-q:v", "3",
                "-y", out_file
            ]
            
            result = subprocess.run(cmd, capture_output=True)
            
            if result.returncode == 0 and os.path.exists(out_file):
                hours = ts // 3600
                minutes = (ts % 3600) // 60
                seconds = ts % 60
                timestamp_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                output_files.append((out_file, timestamp_str))
        
        # Send screenshots
        await msg.edit_text(
            f"📤 **Sending {len(output_files)} screenshots...**"
        )
        
        for img, tstamp in output_files:
            await callback_query.message.reply_photo(
                img,
                caption=f"🕒 **Time:** `{tstamp}`"
            )
            os.remove(img)
        
        # Cleanup
        os.remove(file_path)
        os.rmdir(temp_dir)
        screenshot_sessions.pop(user_id, None)
        
        await msg.edit_text(
            f"🎉 **{len(output_files)} screenshots sent successfully!** 📸"
        )
        
    except Exception as e:
        logger.error(f"Error generating screenshots: {e}")
        await callback_query.message.edit_text(f"❌ Error: {str(e)}")
        
        # Cleanup on error
        if user_id in screenshot_sessions:
            screenshot_sessions.pop(user_id)


# Handler registration function
def register_screenshot_handlers(app: Client):
    """Register screenshot tool handlers"""
    
    @app.on_message(filters.command("ss") & filters.private & filters.reply)
    async def ss_command_handler(client, message):
        await handle_screenshot_command(client, message)
    
    @app.on_callback_query(filters.regex("^ss_\\d+$"))
    async def ss_callback_handler(client, callback_query):
        await handle_screenshot_callback(client, callback_query)
    
    logger.info("✅ Screenshot tool handlers registered")
