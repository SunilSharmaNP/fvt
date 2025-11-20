# modules/audio_remover_tool.py
# Audio Track Remover Tool - Remove specific audio tracks from video
# Based on attached removestream feature

import os
import json
import logging
import subprocess
import tempfile
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

logger = logging.getLogger(__name__)

# User session storage
audio_remover_sessions = {}


async def handle_tracks_command(client: Client, message: Message):
    """Handle /tracks command - show audio tracks"""
    try:
        from modules.database import db
        
        user_id = message.from_user.id
        
        # Check if tool is enabled
        settings = await db.get_user_settings(user_id)
        active_tool = settings.get("active_tool", "none")
        
        if active_tool != "audioremover":
            return await message.reply_text(
                "⚠️ **Audio Remover tool is not enabled!**\n\n"
                "Please enable it from:\n"
                "**Video Tools → 🎧 Audio Remover**"
            )
        
        # Check if replying to video
        if not message.reply_to_message or not message.reply_to_message.video:
            return await message.reply_text(
                "⚠️ **Please reply to a video with /tracks command**\n\n"
                "Usage: Reply to video → `/tracks`"
            )
        
        video_msg = message.reply_to_message
        
        msg = await message.reply_text("📥 **Downloading video...**")
        
        # Download video
        file_path = await video_msg.download()
        
        await msg.edit_text("🔍 **Extracting track list...**")
        
        # Get audio tracks using ffprobe
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "a",
            "-show_entries", "stream=index,codec_name,channels,channel_layout",
            "-of", "json",
            file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            os.remove(file_path)
            return await msg.edit_text("❌ Error reading video tracks")
        
        data = json.loads(result.stdout)
        streams = data.get('streams', [])
        
        if not streams:
            os.remove(file_path)
            return await msg.edit_text("❌ No audio tracks found in this video")
        
        # Store session
        audio_remover_sessions[user_id] = {
            "file_path": file_path,
            "streams": streams,
            "original_message": video_msg
        }
        
        # Create buttons for each track
        buttons = []
        for stream in streams:
            index = stream.get('index', 'N/A')
            codec = stream.get('codec_name', 'unknown')
            channels = stream.get('channels', 'N/A')
            layout = stream.get('channel_layout', 'N/A')
            
            button_text = f"🎧 Track {index} | {codec} | {channels}ch ({layout})"
            buttons.append([
                InlineKeyboardButton(
                    button_text,
                    callback_data=f"selecttrack_{index}"
                )
            ])
        
        await msg.edit_text(
            "🎧 **Audio Tracks Found:**\n\n"
            "Select the track you want to **REMOVE**:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    except Exception as e:
        logger.error(f"Error in tracks command: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")


async def handle_track_selection(client: Client, callback_query):
    """Handle track selection - show confirmation"""
    try:
        from modules.database import db
        
        user_id = callback_query.from_user.id
        
        # Re-check if tool is still enabled (prevent mid-session disable bypass)
        settings = await db.get_user_settings(user_id)
        active_tool = settings.get("active_tool", "none")
        
        if active_tool != "audioremover":
            return await callback_query.answer(
                "⚠️ Audio Remover tool was disabled!",
                show_alert=True
            )
        
        track_id = callback_query.data.split("_")[1]
        
        # Check session
        if user_id not in audio_remover_sessions:
            return await callback_query.answer(
                "⚠️ Session expired. Use /tracks again!",
                show_alert=True
            )
        
        # Store selected track
        audio_remover_sessions[user_id]["selected_track"] = track_id
        
        # Ask for confirmation
        await callback_query.message.edit_text(
            f"⚠️ **Are you sure?**\n\n"
            f"You want to **REMOVE** audio track `{track_id}`?\n\n"
            f"⚠️ **Note:** Subtitles will also be removed.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ YES", callback_data="confirm_yes"),
                    InlineKeyboardButton("❌ NO", callback_data="confirm_no")
                ]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error in track selection: {e}")
        await callback_query.message.edit_text(f"❌ Error: {str(e)}")


async def handle_confirmation(client: Client, callback_query):
    """Handle user confirmation"""
    log_id = None
    try:
        from modules.database import db
        from modules.log_manager import log_simple_task, log_simple_complete
        
        user_id = callback_query.from_user.id
        user = callback_query.from_user
        action = callback_query.data
        
        # Re-check if tool is still enabled (prevent mid-session disable bypass)
        settings = await db.get_user_settings(user_id)
        active_tool = settings.get("active_tool", "none")
        
        if active_tool != "audioremover":
            # Clean up session
            if user_id in audio_remover_sessions:
                file_path = audio_remover_sessions[user_id].get("file_path")
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                audio_remover_sessions.pop(user_id)
            
            return await callback_query.answer(
                "⚠️ Audio Remover tool was disabled!",
                show_alert=True
            )
        
        if action == "confirm_no":
            # Cancel operation
            if user_id in audio_remover_sessions:
                file_path = audio_remover_sessions[user_id].get("file_path")
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                audio_remover_sessions.pop(user_id)
            
            return await callback_query.message.edit_text("❌ **Action cancelled.**")
        
        # Proceed with removal
        if user_id not in audio_remover_sessions:
            return await callback_query.answer("⚠️ Session expired!", show_alert=True)
        
        session = audio_remover_sessions[user_id]
        input_video = session["file_path"]
        track_id = session["selected_track"]
        original_message = session.get("original_message")
        
        # Create task log
        log_id = await log_simple_task(client, user, "Audio Remover", f"Removing track {track_id}")
        
        await callback_query.message.edit_text(
            "🛠 **Removing selected audio track & subtitles...**\n\n"
            "Please wait..."
        )
        
        # Create output file
        output_video = tempfile.mktemp(suffix=".mp4")
        
        # FFmpeg command to remove specific audio track and all subtitles
        cmd = [
            "ffmpeg", "-i", input_video,
            "-map", "0",  # Map all streams
            "-map", f"-0:a:{track_id}",  # Remove specific audio track
            "-map", "-0:s?",  # Remove all subtitles
            "-c", "copy",  # Copy codec (no re-encoding)
            "-y", output_video
        ]
        
        result = subprocess.run(cmd, capture_output=True)
        
        if result.returncode != 0 or not os.path.exists(output_video):
            os.remove(input_video)
            error_msg = result.stderr.decode('utf-8', 'ignore')[-200:] if result.stderr else "Unknown error"
            await log_simple_complete(client, log_id, False, error_msg)
            return await callback_query.message.edit_text(
                "❌ **Failed to process video**\n\n"
                f"Error: {error_msg}"
            )
        
        await callback_query.message.edit_text("📤 **Uploading processed video...**")
        
        # Get original caption if available
        original_caption = ""
        if original_message and hasattr(original_message, 'caption') and original_message.caption:
            original_caption = original_message.caption + "\n\n"
        
        # Upload processed video with caption
        caption = f"{original_caption}🎉 **Audio Track Removed!**\n\n🎧 Track `{track_id}` removed\n✅ All subtitles removed"
        await callback_query.message.reply_video(
            output_video,
            caption=caption
        )
        
        # Complete log
        await log_simple_complete(client, log_id, True)
        
        # Cleanup
        os.remove(input_video)
        os.remove(output_video)
        audio_remover_sessions.pop(user_id, None)
        
        await callback_query.message.edit_text("✅ **Done!**")
        
    except Exception as e:
        logger.error(f"Error in confirmation: {e}")
        
        # Log error
        if log_id:
            from modules.log_manager import log_simple_complete
            await log_simple_complete(client, log_id, False, str(e))
        
        await callback_query.message.edit_text(f"❌ Error: {str(e)}")
        
        # Cleanup on error
        if user_id in audio_remover_sessions:
            file_path = audio_remover_sessions[user_id].get("file_path")
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            audio_remover_sessions.pop(user_id)


# Handler registration function
def register_audio_remover_handlers(app: Client):
    """Register audio remover tool handlers"""
    
    @app.on_message(filters.command("tracks") & filters.private & filters.reply)
    async def tracks_command_handler(client, message):
        await handle_tracks_command(client, message)
    
    @app.on_callback_query(filters.regex("^selecttrack_"))
    async def track_selection_handler(client, callback_query):
        await handle_track_selection(client, callback_query)
    
    @app.on_callback_query(filters.regex("^confirm_(yes|no)$"))
    async def confirmation_handler(client, callback_query):
        await handle_confirmation(client, callback_query)
    
    logger.info("✅ Audio Remover tool handlers registered")
