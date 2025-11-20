# modules/log_manager.py (v5.1)
# MODIFIED based on user's 24-point plan and processor.py (v5.1):
# 1. Changed `update_task_log` signature to accept `stage`, `progress_percent`, `speed`, `eta`.
#    This makes it compatible with the new `processor.py` and `utils.py` progress callbacks.
# 2. Upgraded `create_task_log` to include `Start Time:`.
# 3. Upgraded `finish_task_log` to parse Start Time and calculate `Total Time:` for a professional log.
# 4. Added `import re` for time parsing.

import logging
import re
from datetime import datetime
from config import config
from pyrogram.errors import MessageNotModified
from modules.utils import get_human_readable_size, format_duration, get_progress_bar

logger = logging.getLogger(__name__)

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
        return log_message.id
    except Exception as e:
        # TASK_LOG_CHANNEL is optional, so log as warning not error
        logger.warning(f"Could not create task log (optional feature): {e}")
        return None

async def update_task_log(
    client, 
    log_message_id, 
    stage: str, 
    progress_percent = None, 
    speed: str = "", 
    eta: str = ""
):
    """Updates the log message with progress. (MODIFIED Signature)"""
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

async def finish_task_log(client, log_message_id, status: str, final_size: int = None, gofile_link: str = None):
    """Updates the log message on completion or failure."""
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
    except Exception as e:
        logger.warning(f"Error finishing task log: {e}")


# Simple log helpers for screenshot, HD cover, and audio remover tools
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
