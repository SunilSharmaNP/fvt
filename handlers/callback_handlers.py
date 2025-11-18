# handlers/callback_handlers.py
# Callback query handlers for inline buttons and interactive UI

import os
import sys
import re
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import MessageNotModified, QueryIdInvalid

from config import config
from modules import bot_state
from modules.database import db
from modules.utils import cleanup_files, process_manager, parse_time_input
from modules.ui_menus import (
    get_start_menu, get_user_settings_menu, get_video_tools_menu,
    get_admin_menu
)
from modules.helpers import verify_user_complete, is_authorized_user
from handlers.task_handlers import start_merge_task
from handlers.start_handlers import send_start_menu

logger = logging.getLogger(__name__)


async def refresh_panel(query: CallbackQuery, panel_type: str):
    """Refresh a UI panel with updated data"""
    try:
        user_id = query.from_user.id
        image, caption, keyboard = None, None, None

        if panel_type == "start":
            image, caption, keyboard = await get_start_menu(user_id)
        elif panel_type == "settings":
            image, caption, keyboard = await get_user_settings_menu(user_id)
        elif panel_type == "tools":
            image, caption, keyboard = await get_video_tools_menu(user_id)
        elif panel_type == "admin":
            image, caption, keyboard = await get_admin_menu()
        elif panel_type.startswith("us:"):
            # User settings submenu
            from modules.ui_menus import get_metadata_submenu, get_download_mode_submenu, get_upload_mode_submenu
            if panel_type == "us:metadata":
                image, caption, keyboard = await get_metadata_submenu(user_id)
            elif panel_type == "us:mode:download":
                image, caption, keyboard = await get_download_mode_submenu(user_id)
            elif panel_type == "us:mode:upload":
                image, caption, keyboard = await get_upload_mode_submenu(user_id)
        elif panel_type.startswith("vt:"):
            # Video tools submenu
            parts = panel_type.split(":")
            tool = parts[1] if len(parts) > 1 else None
            submenu = parts[2] if len(parts) > 2 else "main"
            
            from modules.ui_menus import (
                get_vt_merge_menu, get_vt_encode_menu, get_vt_trim_menu,
                get_vt_watermark_menu, get_vt_sample_menu, get_vt_extract_menu,
                get_vt_extra_menu, get_vt_rotate_menu, get_vt_flip_menu,
                get_vt_speed_menu, get_vt_volume_menu, get_vt_crop_menu,
                get_vt_gif_menu, get_vt_reverse_menu
            )
            
            menu_map = {
                "merge": get_vt_merge_menu,
                "encode": get_vt_encode_menu,
                "trim": get_vt_trim_menu,
                "watermark": get_vt_watermark_menu,
                "sample": get_vt_sample_menu,
                "extract": get_vt_extract_menu,
                "extra": get_vt_extra_menu,
                "rotate": get_vt_rotate_menu,
                "flip": get_vt_flip_menu,
                "speed": get_vt_speed_menu,
                "volume": get_vt_volume_menu,
                "crop": get_vt_crop_menu,
                "gif": get_vt_gif_menu,
                "reverse": get_vt_reverse_menu
            }
            
            if tool in menu_map:
                image, caption, keyboard = await menu_map[tool](user_id, submenu)

        if keyboard:
            await query.message.edit_media(
                media=InputMediaPhoto(image, caption=caption),
                reply_markup=keyboard)
            await query.answer()
        else:
            await query.answer("Error: Panel not found.")
    except MessageNotModified:
        await query.answer()
    except QueryIdInvalid:
        pass
    except Exception as e:
        logger.error(f"Error refreshing panel {panel_type}: {e}", exc_info=True)
        await query.answer("An error occurred.", show_alert=True)


def register_callback_handlers(app: Client):
    """Register the main callback query handler"""

    @app.on_callback_query()
    async def callback_handler(client: Client, query: CallbackQuery):
        user_id = query.from_user.id
        data = query.data
        chat_id = query.message.chat.id

        async def safe_answer(msg="", show_alert=False):
            try:
                await query.answer(msg, show_alert=show_alert)
            except Exception:
                pass

        try:
            # Force subscribe check
            if data == "check_subscription":
                if await verify_user_complete(client, query):
                    await query.answer("✅ Subscription verified!", show_alert=True)
                    await query.message.delete()
                    # Create a pseudo-message object to send start menu without quoting
                    dummy_message = query.message
                    dummy_message.from_user = query.from_user
                    await send_start_menu(client, dummy_message, quote=False)
                return

            if not await is_authorized_user(user_id, chat_id):
                return await query.answer("❌ You are not authorized.", show_alert=True)

            # Task cancellation
            if data.startswith("task_cancel:"):
                task_id = data.split(":", 1)[1]
                info = process_manager.get_process_info(task_id)
                if not info:
                    db_task = await db.get_task(task_id)
                    if not db_task or db_task["user_id"] != user_id:
                        return await query.answer("❌ Not your task or already finished.", show_alert=True)
                    if db_task["status"] in ["pending", "downloading", "processing", "uploading"]:
                        await db.update_task(task_id, {"status": "cancelled"})
                    else:
                        return await query.answer("❌ Task already done.", show_alert=True)
                elif info["user_id"] != user_id:
                    return await query.answer("❌ This is not your task.", show_alert=True)
                await process_manager.kill_process_async(task_id)
                cleanup_files(os.path.join(config.DOWNLOAD_DIR, str(user_id), task_id))
                await query.answer("Task Cancelled!", show_alert=True)
                await query.message.edit_text(config.MSG_TASK_CANCELLED.format(task_id=task_id))
                return

            # Queue management
            if data.startswith("queue:"):
                from modules.queue_manager import queue_manager
                action = data.split(":", 1)[1]
                if action == "add_more":
                    await query.answer("👍 Send more videos to add to queue!")
                    return
                elif action == "merge_now":
                    if not queue_manager.has_queue(user_id) or queue_manager.get_queue_count(user_id) < 2:
                        return await query.answer("❌ Need at least 2 videos in queue", show_alert=True)
                    settings = await db.get_user_settings(user_id)
                    if await db.is_user_task_running(user_id):
                        return await query.answer("⏳ You have a task running. Please wait.", show_alert=True)
                    task_id = await db.create_task(user_id, "merge", "telegram_files")
                    if not task_id:
                        return await query.answer("❌ Error creating task", show_alert=True)
                    queue_items = queue_manager.get_queue(user_id)
                    messages_to_merge = [item['message'] for item in queue_items]
                    queue_manager.clear_queue(user_id)
                    await query.answer("🔀 Starting merge process...")
                    await query.message.delete()
                    await start_merge_task(client, query.message, messages_to_merge, user_id, task_id, settings)
                    return
                elif action == "clear":
                    queue_manager.clear_queue(user_id)
                    await query.answer("🗑️ Queue cleared!", show_alert=True)
                    await query.message.delete()
                    return

            # Panel navigation
            if data.startswith("open:"):
                panel = data.split(":", 1)[1]
                if panel in ["start", "settings", "tools", "admin"]:
                    return await refresh_panel(query, panel)
                elif panel == "help":
                    await query.message.edit_media(
                        InputMediaPhoto(config.IMG_START, caption=config.MSG_HELP),
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton(f"🔙 {config.BTN_BACK}", callback_data="open:start")
                        ]]))
                    return await query.answer()
                elif panel == "about":
                    caption = config.MSG_ABOUT.format(bot_name=config.BOT_NAME, developer=config.DEVELOPER)
                    await query.message.edit_media(
                        InputMediaPhoto(config.IMG_START, caption=caption),
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton(f"🔙 {config.BTN_BACK}", callback_data="open:start")
                        ]]))
                    return await query.answer()

            parts = data.split(":")
            prefix = parts[0]

            # User settings callbacks
            if prefix == "us":
                action, *payload = parts[1:]
                payload = ":".join(payload)
                if action == "mode":
                    # Handle mode submenus (download/upload)
                    if len(parts) >= 3 and parts[2] == "open":
                        # us:mode:download:open or us:mode:upload:open
                        return await refresh_panel(query, f"us:mode:{payload.replace(':open', '')}")
                elif action == "set":
                    key, value = payload.split(":", 1) if ":" in payload else (payload, "")
                    if key in ["download_mode", "upload_mode"]:
                        await db.update_user_setting(user_id, key, value)
                        await query.answer(f"{key.replace('_',' ').title()} set to {value.capitalize()}")
                        return await refresh_panel(query, "settings")
                    elif key == "custom_thumbnail" and value == "none":
                        await db.update_user_setting(user_id, "custom_thumbnail", None)
                        await query.answer("Thumbnail cleared.")
                        return await refresh_panel(query, "settings")
                elif action == "toggle":
                    key = payload
                    if key in ["upload_mode", "download_mode"]:
                        settings = await db.get_user_settings(user_id)
                        cur = settings.get(key, "telegram")
                        if isinstance(cur, bool): cur = "telegram"
                        if key == "upload_mode":
                            new = "gofile" if cur == "telegram" else "telegram"
                        else:
                            new = "url" if cur == "telegram" else "telegram"
                        await db.update_user_setting(user_id, key, new)
                        await query.answer(f"{key.replace('_',' ').title()} → {new.capitalize()}")
                    else:
                        new_val = await db.toggle_user_setting(user_id, key)
                        await query.answer(f"{key.replace('_',' ').capitalize()} set to {'ON' if new_val else 'OFF'}")
                    if key == "metadata":
                        return await refresh_panel(query, "us:metadata")
                elif action == "set" and payload == "custom_thumbnail:none":
                    await db.update_user_setting(user_id, "custom_thumbnail", None)
                    await query.answer("Thumbnail cleared.")
                elif action == "metadata":
                    if len(parts) < 3:
                        return await query.answer("Invalid metadata action")
                    metadata_action = parts[2]
                    if metadata_action == "open" and len(parts) > 3 and parts[3] == "main":
                        return await refresh_panel(query, "us:metadata")
                    elif metadata_action == "ask":
                        field = parts[3] if len(parts) > 3 else None
                        if field not in ["title", "artist", "comment"]:
                            return await query.answer("Invalid metadata field")
                        field_name = field.capitalize()
                        await query.answer()
                        try:
                            r = await client.ask(
                                chat_id,
                                f"📝 Enter custom **{field_name}** for your videos:\n\n(Send /cancel to abort)",
                                filters=filters.text,
                                timeout=300)
                            if r.text == "/cancel":
                                return await r.reply_text(config.MSG_SET_CANCELLED)
                            await db.update_user_nested_setting(user_id, f"metadata_custom.{field}", r.text)
                            await r.reply_text(config.MSG_SET_SUCCESS)
                        except asyncio.TimeoutError:
                            return await client.send_message(chat_id, config.MSG_SET_TIMEOUT)
                        return await refresh_panel(query, "us:metadata")
                    elif metadata_action == "clear" and len(parts) > 3 and parts[3] == "all":
                        await db.update_user_setting(user_id, "metadata_custom", {})
                        await query.answer("All custom metadata cleared!")
                        return await refresh_panel(query, "us:metadata")
                elif action == "ask":
                    key = payload
                    try:
                        if key == "custom_filename":
                            await query.answer()
                            r = await client.ask(chat_id, config.MSG_ASK_FILENAME, filters=filters.text, timeout=300)
                            if r.text == "/cancel":
                                return await r.reply_text(config.MSG_SET_CANCELLED)
                            if " " in r.text or "." in r.text:
                                return await r.reply_text(config.MSG_SET_ERROR_FILENAME)
                            await db.update_user_setting(user_id, "custom_filename", r.text)
                            await r.reply_text(config.MSG_SET_SUCCESS)
                        elif key == "custom_thumbnail":
                            await query.answer()
                            r = await client.ask(chat_id, config.MSG_ASK_THUMBNAIL, filters=filters.photo, timeout=300)
                            await db.update_user_setting(user_id, "custom_thumbnail", r.photo.file_id)
                            await r.reply_text(config.MSG_SET_SUCCESS)
                    except asyncio.TimeoutError:
                        return await client.send_message(chat_id, config.MSG_SET_TIMEOUT)
                return await refresh_panel(query, "settings")

            # Video tools callbacks
            if prefix == "vt":
                if len(parts) == 3 and parts[1] == "toggle":
                    action, tool = "toggle", parts[2]
                    payload = ""
                else:
                    tool, action, *payload_parts = parts[1:]
                    payload = ":".join(payload_parts)

                if action == "open":
                    return await refresh_panel(query, f"vt:{tool}:{payload}")
                elif action == "toggle":
                    settings = await db.get_user_settings(user_id)
                    active = settings.get("active_tool", "none")
                    if active == tool:
                        await db.update_user_setting(user_id, "active_tool", "none")
                        await query.answer(f"{tool.capitalize()} tool disabled.")
                    else:
                        await db.update_user_setting(user_id, "active_tool", tool)
                        await query.answer(f"{tool.capitalize()} tool enabled ✅")
                    return await refresh_panel(query, f"vt:{tool}:main")
                elif action == "set":
                    key, value = payload.split(":", 1)
                    if tool == "merge":
                        await db.update_user_setting(user_id, "merge_mode", value)
                        return await refresh_panel(query, "vt:merge:main")
                    db_key = f"{tool}_settings.{key}"
                    if key == "resolution":
                        if value.endswith("_hevc"):
                            base = value.replace("_hevc", "")
                            await db.update_user_nested_setting(user_id, "encode_settings.resolution", base)
                            await db.update_user_nested_setting(user_id, "encode_settings.vcodec", "libx265")
                            await query.answer(f"Set {base.upper()} (HEVC)", show_alert=False)
                        else:
                            await db.update_user_nested_setting(user_id, "encode_settings.resolution", value)
                            await db.update_user_nested_setting(user_id, "encode_settings.vcodec", "libx264")
                            await query.answer(f"Set {value.upper()} (H.264)", show_alert=False)
                        return await refresh_panel(query, f"vt:{tool}:resolution")
                    if key in ["crf", "duration", "angle", "volume", "fps", "scale"]:
                        value = int(value)
                    elif key == "opacity" or key == "speed":
                        value = float(value)
                    await db.update_user_nested_setting(user_id, db_key, value)
                    await query.answer(f"{key.capitalize()} set to {value}")
                    if key in ["vcodec", "crf", "preset", "resolution", "acodec"]:
                        panel = f"vt:encode:{key}"
                    elif key in ["type", "position", "frequency"]:
                        panel = f"vt:watermark:{key}"
                    elif key == "from_point":
                        panel = "vt:sample:from"
                    elif key in ["angle", "direction", "speed", "volume", "aspect_ratio", "quality"]:
                        panel = f"vt:{tool}:main"
                    else:
                        panel = f"vt:{tool}:main"
                    return await refresh_panel(query, panel)
                elif action == "ask":
                    key = payload
                    db_key = f"{tool}_settings.{key}"
                    ask_msg, error_msg = None, None
                    validation = None
                    if tool == "encode":
                        if key == "crf":
                            ask_msg, error_msg = config.MSG_ASK_CUSTOM_CRF, config.MSG_SET_ERROR_CRF
                            validation = lambda x: 0 <= int(x) <= 51
                        elif key == "abitrate":
                            ask_msg, error_msg = config.MSG_ASK_CUSTOM_ABITRATE, config.MSG_SET_ERROR_BITRATE
                            validation = lambda x: x.endswith("k") and x[:-1].isdigit()
                        elif key == "resolution":
                            ask_msg, error_msg = config.MSG_ASK_CUSTOM_RESOLUTION, config.MSG_SET_ERROR_RESOLUTION
                            validation = lambda x: bool(re.match(r"^\d+x\d+$", x))
                            db_key = "encode_settings.custom_resolution"
                        elif key == "suffix":
                            ask_msg = config.MSG_ASK_ENCODE_SUFFIX
                            validation = lambda x: True
                    elif tool == "trim":
                        ask_msg = config.MSG_ASK_TRIM_START if key == "start" else config.MSG_ASK_TRIM_END
                        error_msg = "❌ Invalid time format. Use format like: 10, 1:30, or 01:30:00"
                        validation = lambda x: parse_time_input(x) is not None
                    elif tool == "sample" and key == "duration":
                        ask_msg, error_msg = config.MSG_ASK_SAMPLE_DURATION, config.MSG_SET_ERROR_DURATION
                        validation = lambda x: x.isdigit() and int(x) > 0
                    elif tool == "watermark" and key == "text":
                        ask_msg = config.MSG_ASK_WATERMARK_TEXT
                        validation = lambda x: len(x) > 0
                    if not ask_msg:
                        return await query.answer("⚠️ No input expected for this action.")
                    if not error_msg:
                        error_msg = "❌ Invalid input. Please try again."
                    await query.answer()
                    try:
                        resp = await client.ask(chat_id, ask_msg, filters=filters.text, timeout=300)
                        if resp.text == "/cancel":
                            return await resp.reply_text(config.MSG_SET_CANCELLED)
                        if not validation(resp.text):
                            return await resp.reply_text(error_msg)
                        val = resp.text
                        if key == "resolution":
                            await db.update_user_nested_setting(user_id, "encode_settings.resolution", "custom")
                            await db.update_user_nested_setting(user_id, db_key, val)
                        else:
                            await db.update_user_nested_setting(user_id, db_key, val)
                        await resp.reply_text(config.MSG_SET_SUCCESS)
                        return await refresh_panel(query, f"vt:{tool}:main")
                    except asyncio.TimeoutError:
                        return await client.send_message(chat_id, config.MSG_SET_TIMEOUT)
                elif action == "queue":
                    from modules.queue_manager import queue_manager
                    if tool != "merge":
                        return await query.answer("Queue is only for merge tool!", show_alert=True)
                    queue_action = payload
                    if queue_action == "wait_more":
                        await query.answer("Send more files to add to queue!")
                        return
                    elif queue_action == "clear":
                        queue_manager.clear_queue(user_id)
                        await query.answer("Queue cleared!")
                        return await refresh_panel(query, "vt:merge:main")
                    elif queue_action == "process":
                        queue = queue_manager.get_queue(user_id)
                        if len(queue) < 2:
                            return await query.answer("Need at least 2 files to merge!", show_alert=True)
                        await query.answer("Starting merge process...")
                        queue_manager.clear_queue(user_id)
                        await query.message.reply_text("🔀 Merge processing will be implemented in the merge handler!")
                        return

            # Admin callbacks
            if prefix == "admin":
                if user_id not in config.ADMINS:
                    return await query.answer("❌ You are not an admin.", show_alert=True)
                act, *payload = parts[1:]
                payload = payload[0] if payload else ""
                if act == "toggle" and payload == "mode":
                    cur = bot_state.get_bot_mode()
                    new = "ACTIVE" if cur == "HOLD" else "HOLD"
                    bot_state.set_bot_mode(new)
                    await query.answer(f"Bot mode: {new}")
                    return await refresh_panel(query, "admin")
                elif act == "show" and payload == "tasks":
                    # Show active tasks
                    import time
                    from modules.utils import format_duration
                    status_text = f"**Bot Task Status**\\n\\nTotal Tasks: `{len(process_manager.active_processes)}`\\n\\n"
                    if not process_manager.active_processes:
                        await query.message.reply_text("No active tasks.")
                    else:
                        for task_id, data in process_manager.active_processes.items():
                            elapsed = time.time() - data['start_time']
                            db_task = await db.get_task(task_id)
                            tool = db_task.get('tool', 'N/A') if db_task else 'N/A'
                            status_text += f"**Task:** `{task_id}`\\n"
                            status_text += f" **User:** `{data['user_id']}`\\n"
                            status_text += f" **Tool:** `{tool}`\\n"
                            status_text += f" **PID:** `{data['pid']}` | **PGID:** `{data['pgid']}`\\n"
                            status_text += f" **Running for:** `{format_duration(elapsed)}`\\n"
                            status_text += "------\\n"
                        await query.message.reply_text(status_text)
                    return await query.answer()
                elif act == "show" and payload == "stats":
                    await query.answer("📊 Stats view coming soon.", show_alert=True)
                    logger.info(f"Admin {user_id} requested stats (not yet implemented)")
                    return
                elif act == "broadcast":
                    await query.answer("📣 Broadcast tooling under development.", show_alert=True)
                    logger.info(f"Admin {user_id} requested broadcast (not yet implemented)")
                    return
                elif act == "restart":
                    if user_id not in config.SUDO_USERS:
                        return await query.answer("❌ Only Sudo Users can restart.", show_alert=True)
                    await query.message.edit_text("🔄 Restarting...")
                    await client.stop()
                    os.execl(sys.executable, sys.executable, *sys.argv)

            await query.answer()

        except Exception as e:
            logger.error(f"Callback Error: {e}", exc_info=True)
            await safe_answer("⚠️ An error occurred.", show_alert=True)

    logger.info("✅ Callback handlers registered")
