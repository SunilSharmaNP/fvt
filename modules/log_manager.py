# modules/log_manager.py (v6.0)
# MODIFIED: Sends SEPARATE messages for each processing stage instead of editing one message.
# Each stage (download started, processing started, upload started, completed) gets its own notification.

import logging
import re
from datetime import datetime
from config import config
from pyrogram.errors import MessageNotModified
from modules.utils import get_human_readable_size, format_duration, get_progress_bar

logger = logging.getLogger(__name__)

# Store task context for generating stage messages
_task_contexts = {}

async def create_task_log(client, user, settings, task_id):
    """Creates the initial log message in the log channel."""
    if not config.TASK_LOG_CHANNEL:
        return None
    
    try:
        active_tool = settings.get("active_tool", "N/A")
        mode_text = ""
        
        if active_tool == "merge":
            mode_text = f"**Merge Mode:** `{settings.get('merge_mode')}`"
        elif active_tool == "encode":
            mode_text = f"**Encode Preset:** `{settings.get('encode_preset')}`"
        elif active_tool == "trim":
            mode_text = f"**Trim Time:** `{settings.get('trim_time')}`"
        
        start_time_dt = datetime.utcnow()
        start_time_str = start_time_dt.strftime('%Y-%m-%d %H:%M:%S')

        log_text = f"""
**New Task Started** 🚀

**Task ID:** `{task_id}`
**User:** {user.mention} (`{user.id}`)
**Tool:** `{active_tool.upper()}`
{mode_text}
**Start Time:** `{start_time_str} UTC`

**Status:** `Initializing...`
"""
        
        # Convert channel ID to int if it's a string
        channel_id = config.TASK_LOG_CHANNEL
        if isinstance(channel_id, str):
            channel_id = int(channel_id)
        
        log_message = await client.send_message(
            chat_id=channel_id,
            text=log_text
        )
        
        # Store task context for stage notifications
        _task_contexts[task_id] = {
            "user": user,
            "tool": active_tool,
            "start_time": start_time_str,
            "mode_text": mode_text,
            "initial_message_id": log_message.id
        }
        
        return log_message.id
    except Exception as e:
        # TASK_LOG_CHANNEL is optional, so log as warning not error
        logger.warning(f"Could not create task log (optional feature): {e}")
        return None


async def send_stage_notification(client, task_id: str, stage: str, details: str = ""):
    """
    Sends a SEPARATE message for each processing stage.
    Stages: "Download Started", "Processing Started", "Upload Started", etc.
    """
    if not config.TASK_LOG_CHANNEL or task_id not in _task_contexts:
        return
    
    try:
        context = _task_contexts[task_id]
        user = context["user"]
        tool = context["tool"]
        
        emoji_map = {
            "Download Started": "⬇️",
            "Processing Started": "⚙️",
            "Upload Started": "⬆️",
            "Completed": "✅",
            "Failed": "❌"
        }
        
        emoji = emoji_map.get(stage, "📋")
        detail_text = f"\n**Details:** `{details}`" if details else ""
        
        log_text = f"""
**Stage Update** {emoji}

**Task ID:** `{task_id}`
**User:** {user.mention} (`{user.id}`)
**Tool:** `{tool.upper()}`
**Stage:** `{stage}`{detail_text}
**Time:** `{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC`
"""
        
        channel_id = config.TASK_LOG_CHANNEL
        if isinstance(channel_id, str):
            channel_id = int(channel_id)
        
        await client.send_message(
            chat_id=channel_id,
            text=log_text
        )
    except Exception as e:
        logger.warning(f"Error sending stage notification: {e}")


async def update_task_log(
    client, 
    log_message_id, 
    stage: str, 
    progress_percent = None, 
    speed: str = "", 
    eta: str = ""
):
    """
    Updates the INITIAL log message with progress (for real-time updates during download/upload).
    For stage transitions, use send_stage_notification instead.
    """
    if not config.TASK_LOG_CHANNEL or not log_message_id:
        return
        
    try:
        # Get the original text to preserve user info
        original_message = await client.get_messages(config.TASK_LOG_CHANNEL, log_message_id)
        if not original_message.text:
            return
            
        base_text = original_message.text.split("\n\n**Status:**")[0]
        
        progress_text = ""
        # MODIFIED: Handle both dict (old format) and float (new format)
        if progress_percent is not None:
            if isinstance(progress_percent, dict):
                # Old format: progress_data dict from downloader/uploader
                progress_val = progress_percent.get("progress", 0)
                speed_val = progress_percent.get("speed", "")
                eta_val = progress_percent.get("eta", "")
                progress_bar = get_progress_bar(progress_val)
                progress_text = f"""
**Progress:** {progress_bar} {progress_val:.1%}
**Speed:** `{speed_val}` | **ETA:** `{eta_val}`
"""
            else:
                # New format: separate float and strings
                progress_bar = get_progress_bar(progress_percent)
                progress_text = f"""
**Progress:** {progress_bar} {progress_percent:.1%}
**Speed:** `{speed}` | **ETA:** `{eta}`
"""

        log_text = f"""
{base_text}

**Status:** `{stage}`
{progress_text}
"""
        
        await client.edit_message_text(
            chat_id=config.TASK_LOG_CHANNEL,
            message_id=log_message_id,
            text=log_text
        )
    except MessageNotModified:
        pass
    except Exception as e:
        logger.warning(f"Error updating task log: {e}")

async def finish_task_log(client, log_message_id, status: str, final_size: int = None, gofile_link: str = None, task_id: str = None):
    """Updates the INITIAL log message on completion or failure, and sends final stage notification."""
    if not config.TASK_LOG_CHANNEL or not log_message_id:
        return

    try:
        original_message = await client.get_messages(config.TASK_LOG_CHANNEL, log_message_id)
        if not original_message.text:
            return
            
        base_text = original_message.text.split("\n\n**Status:**")[0]
        
        # MODIFIED: Calculate total elapsed time
        total_elapsed = "N/A"
        start_time_match = re.search(r"Start Time:\*\* `(.*?) UTC`", base_text)
        if start_time_match:
            try:
                start_time = datetime.strptime(start_time_match.group(1), '%Y-%m-%d %H:%M:%S')
                elapsed = datetime.utcnow() - start_time
                total_elapsed = format_duration(elapsed.total_seconds())
            except Exception as e:
                logger.warning(f"Could not parse start time for log: {e}")

        emoji = "✅" if status == "Complete" else "🚫"
        
        final_text = ""
        if final_size:
            final_text += f"**Output Size:** `{get_human_readable_size(final_size)}`\n"
        if gofile_link:
            final_text += f"**Link:** {gofile_link}\n"
        
        # MODIFIED: Added Total Time
        final_text += f"**Total Time:** `{total_elapsed}`\n"
            
        log_text = f"""
{base_text}

**Status:** `{status}` {emoji}
{final_text}
"""
        
        await client.edit_message_text(
            chat_id=config.TASK_LOG_CHANNEL,
            message_id=log_message_id,
            text=log_text,
            disable_web_page_preview=True
        )
        
        # Send final stage notification
        if task_id:
            stage = "Completed" if status == "Complete" else "Failed"
            details = f"Output: {get_human_readable_size(final_size)}" if final_size else ""
            await send_stage_notification(client, task_id, stage, details)
            
            # Clean up task context
            if task_id in _task_contexts:
                del _task_contexts[task_id]
                
    except Exception as e:
        logger.warning(f"Error finishing task log: {e}")


# Simple log helpers for screenshot, HD cover, and audio remover tools
async def cleanup_task_context(task_id: str):
    """
    Emergency cleanup for task context. Use in finally blocks to prevent memory leaks.
    Safe to call even if task_id doesn't exist in _task_contexts.
    """
    if task_id in _task_contexts:
        del _task_contexts[task_id]
        logger.info(f"Cleaned up task context for {task_id}")


async def log_simple_task(client, user, tool_name: str, details: str = ""):
    """Create a simple task log for lightweight tools"""
    if not config.TASK_LOG_CHANNEL:
        return None
    
    try:
        start_time_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        detail_text = f"\n**Details:** `{details}`" if details else ""
        
        log_text = f"""
**Task Started** 🚀

**User:** {user.mention} (`{user.id}`)
**Tool:** `{tool_name.upper()}`{detail_text}
**Start Time:** `{start_time_str} UTC`

**Status:** `Processing...`
"""
        
        channel_id = config.TASK_LOG_CHANNEL
        if isinstance(channel_id, str):
            channel_id = int(channel_id)
        
        log_message = await client.send_message(
            chat_id=channel_id,
            text=log_text
        )
        return log_message.id
    except Exception as e:
        logger.warning(f"Could not create simple task log: {e}")
        return None


async def log_simple_complete(client, log_message_id, success: bool = True, error_msg: str = None):
    """Complete a simple task log"""
    if not config.TASK_LOG_CHANNEL or not log_message_id:
        return
    
    try:
        original_message = await client.get_messages(config.TASK_LOG_CHANNEL, log_message_id)
        if not original_message.text:
            return
        
        base_text = original_message.text.split("\n\n**Status:**")[0]
        
        # Calculate elapsed time
        total_elapsed = "N/A"
        start_time_match = re.search(r"Start Time:\*\* `(.*?) UTC`", base_text)
        if start_time_match:
            try:
                start_time = datetime.strptime(start_time_match.group(1), '%Y-%m-%d %H:%M:%S')
                elapsed = datetime.utcnow() - start_time
                total_elapsed = format_duration(elapsed.total_seconds())
            except:
                pass
        
        if success:
            status = "Complete ✅"
            final_text = f"**Total Time:** `{total_elapsed}`"
        else:
            status = "Failed ❌"
            final_text = f"**Error:** `{error_msg or 'Unknown error'}`\n**Total Time:** `{total_elapsed}`"
        
        log_text = f"""
{base_text}

**Status:** `{status}`
{final_text}
"""
        
        await client.edit_message_text(
            chat_id=config.TASK_LOG_CHANNEL,
            message_id=log_message_id,
            text=log_text
        )
    except Exception as e:
        logger.warning(f"Error completing simple task log: {e}")
