# bot.py (v6.3 - Final Fix)
# ✅ [CRITICAL FIX] `processor.process_task` को कॉल करते समय `settings` आर्ग्युमेंट हटा दिया गया।
# ✅ यह `processor.py` (v6.12) के 6-आर्ग्युमेंट वाले सिग्नेचर से मेल खाता है।
# ✅ यह रेस कंडीशन (Race Condition) को ठीक करने के लिए `await` का सही उपयोग करता है।

import os
import shutil
import asyncio
import logging
from pyrogram import types, Client
from pyrogram.types import CallbackQuery
import time
import re
import sys
import signal
from datetime import datetime
from pyrogram import Client, filters, idle, ContinuePropagation
from pyrogram.types import (Message, InlineKeyboardMarkup,
                            InlineKeyboardButton, CallbackQuery, ForceReply,
                            InputMediaPhoto, BotCommand, BotCommandScopeChat)
from pyrogram.errors import (FloodWait, UserNotParticipant, MessageNotModified,
                             QueryIdInvalid)

# --- Module Imports ---
from config import config
from modules.database import db
from modules import bot_state, log_manager, processor, media_info
from modules.downloader import download_from_tg, YTDLDownloader
from modules.uploader import GofileUploader, upload_to_telegram
from modules.helpers import force_subscribe_check, is_authorized_user, verify_user_complete
from modules.utils import (cleanup_files, is_valid_url,
                           get_human_readable_size, format_duration,
                           process_manager, parse_time_input)
from modules.ui_menus import (
    get_start_menu, get_user_settings_menu, get_video_tools_menu,
    get_admin_menu, get_metadata_submenu, get_vt_merge_menu,
    get_vt_encode_menu, get_vt_trim_menu, get_vt_watermark_menu,
    get_vt_sample_menu, get_vt_extract_menu, get_vt_extra_menu,
    get_vt_rotate_menu, get_vt_flip_menu, get_vt_speed_menu,
    get_vt_volume_menu, get_vt_crop_menu, get_vt_gif_menu, get_vt_reverse_menu)
from pyromod import listen

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Config Check ---
if not config.API_ID or not config.API_HASH or not config.BOT_TOKEN:
    logger.critical(
        "❌ Configuration not set! Missing API_ID, API_HASH, or BOT_TOKEN.")
    sys.exit(1)
if not isinstance(config.API_ID, int):
    logger.critical("❌ API_ID must be an integer.")
    sys.exit(1)

# --- Pyrogram Client (with Pyromod) ---
try:
    app = Client("SS_Video_Workstation_Bot_v5",
                 api_id=config.API_ID,
                 api_hash=config.API_HASH,
                 bot_token=config.BOT_TOKEN)
except Exception as e:
    logger.critical(f"Failed to initialize bot client: {e}")
    sys.exit(1)


# ===================================================================
# 1. START & UI COMMANDS
# ===================================================================
@app.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    try:
        if not await is_authorized_user(user_id, chat_id):
            if chat_id == user_id:
                return await message.reply_text(
                    config.MSG_PRIVATE_CHAT_RESTRICTED)
            else:
                return await message.reply_text(config.MSG_GROUP_NOT_AUTHORIZED
                                                )
        if not await verify_user_complete(client, message): return
        image, caption, keyboard = await get_start_menu(user_id)
        await message.reply_photo(photo=image,
                                  caption=caption,
                                  reply_markup=keyboard,
                                  quote=True)
    except Exception as e:
        logger.error(f"Start handler error: {e}", exc_info=True)
        try:
            await message.reply_text("❌ Error: Bot could not be started.")
        except:
            pass


@app.on_message(filters.command(["help", f"help@{config.BOT_USERNAME}"]))
async def help_handler(client: Client, message: Message):
    if not await is_authorized_user(message.from_user.id, message.chat.id):
        return
    await message.reply_text(config.MSG_HELP,
                             reply_markup=InlineKeyboardMarkup([[
                                 InlineKeyboardButton(
                                     f"🔙 {config.BTN_BACK}",
                                     callback_data="open:start")
                             ]]))


@app.on_message(filters.command(["about", f"about@{config.BOT_USERNAME}"]))
async def about_handler(client: Client, message: Message):
    if not await is_authorized_user(message.from_user.id, message.chat.id):
        return
    caption = config.MSG_ABOUT.format(bot_name=config.BOT_NAME,
                                      developer=config.DEVELOPER)
    await message.reply_text(caption,
                             reply_markup=InlineKeyboardMarkup([[
                                 InlineKeyboardButton(
                                     f"🔙 {config.BTN_BACK}",
                                     callback_data="open:start")
                             ]]))


@app.on_message(filters.command(["us", "settings", "usersettings"]))
async def user_settings_handler(client: Client, message: Message):
    user_id = message.from_user.id
    if not await is_authorized_user(user_id, message.chat.id): return
    if not await verify_user_complete(client, message): return
    try:
        image, caption, keyboard = await get_user_settings_menu(user_id)
        await message.reply_photo(photo=image,
                                  caption=caption,
                                  reply_markup=keyboard,
                                  quote=True)
    except Exception as e:
        logger.error(f"User Settings handler error: {e}", exc_info=True)
        await message.reply_text(f"❌ Error loading settings: {e}")


@app.on_message(filters.command(["vt", "tools", "videotools"]))
async def video_tools_handler(client: Client, message: Message):
    user_id = message.from_user.id
    if not await is_authorized_user(user_id, message.chat.id): return
    if not await verify_user_complete(client, message): return
    try:
        image, caption, keyboard = await get_video_tools_menu(user_id)
        await message.reply_photo(photo=image,
                                  caption=caption,
                                  reply_markup=keyboard,
                                  quote=True)
    except Exception as e:
        logger.error(f"Video Tools handler error: {e}", exc_info=True)
        await message.reply_text(f"❌ Error loading tools: {e}")


# ===================================================================
# 2. ADMIN & BOT MODE COMMANDS
# ===================================================================
@app.on_message(filters.command("admin") & filters.user(config.ADMINS))
async def admin_handler(client: Client, message: Message):
    image, caption, keyboard = await get_admin_menu()
    await message.reply_photo(photo=image,
                              caption=caption,
                              reply_markup=keyboard,
                              quote=True)


@app.on_message(filters.command("botmode") & filters.user(config.ADMINS))
async def get_mode_handler(client: Client, message: Message):
    mode = bot_state.get_bot_mode()
    emoji = "✅" if mode == "ACTIVE" else "HOLD ⏸️"
    await message.reply_text(f"Global Bot Status: **{mode} {emoji}**")


@app.on_message(filters.command("activate") & filters.user(config.ADMINS))
async def activate_handler(client: Client, message: Message):
    bot_state.set_bot_mode("ACTIVE")
    await message.reply_text("✅ **Bot Activated!**\nNow processing new tasks.")


@app.on_message(filters.command("deactivate") & filters.user(config.ADMINS))
async def deactivate_handler(client: Client, message: Message):
    bot_state.set_bot_mode("HOLD")
    await message.reply_text("⏸️ **Bot on Hold!**\nWill not process new tasks."
                             )


@app.on_message(filters.command("hold"))
async def hold_handler(client: Client, message: Message):
    user_id = message.from_user.id
    if not await is_authorized_user(user_id, message.chat.id): return
    try:
        new_status = await db.toggle_user_setting(user_id, "is_on_hold")
        if new_status:
            await message.reply_text(config.MSG_USER_HOLD_ENABLED)
        else:
            await message.reply_text(config.MSG_USER_HOLD_DISABLED)
    except Exception as e:
        logger.error(f"Per-user hold handler error: {e}", exc_info=True)
        await message.reply_text("❌ Error changing your hold status.")


@app.on_message(filters.command(["s", "status"]) & filters.user(config.ADMINS))
async def status_handler(client: Client, message: Message):
    status_text = f"**Bot Task Status**\n\nTotal Tasks: `{len(process_manager.active_processes)}`\n\n"
    if not process_manager.active_processes:
        return await message.reply_text("No active tasks.")
    for task_id, data in process_manager.active_processes.items():
        elapsed = time.time() - data['start_time']
        db_task = await db.get_task(task_id)
        tool = db_task.get('tool', 'N/A') if db_task else 'N/A'
        status_text += f"**Task:** `{task_id}`\n"
        status_text += f"  **User:** `{data['user_id']}`\n"
        status_text += f"  **Tool:** `{tool}`\n"
        status_text += f"  **PID:** `{data['pid']}` | **PGID:** `{data['pgid']}`\n"
        status_text += f"  **Running for:** `{format_duration(elapsed)}`\n"
        status_text += "------\n"
    await message.reply_text(status_text)


@app.on_message(filters.command("restart") & filters.user(config.SUDO_USERS))
async def restart_handler(client: Client, message: Message):
    try:
        await message.reply_text("🔄 **Restarting...**")
        logger.info(
            f"Bot restart initiated by SUDO user {message.from_user.id}")
        await client.stop()
        os.execl(sys.executable, sys.executable, *sys.argv)
    except Exception as e:
        logger.error(f"Restart failed: {e}")


@app.on_message(filters.command("addauth") & filters.user(config.ADMINS))
async def add_auth_chat(client: Client, message: Message):
    chat_id = message.chat.id
    if message.reply_to_message:
        chat_id = message.reply_to_message.chat.id
    elif len(message.command) > 1:
        try:
            chat_id = int(message.command[1])
        except ValueError:
            return await message.reply_text("Invalid Chat ID.")
    if await db.is_authorized_chat(chat_id):
        return await message.reply_text("✅ Chat is already authorized.")
    if await db.add_authorized_chat(chat_id):
        await message.reply_text(f"✅ Chat `{chat_id}` has been authorized.")
    else:
        await message.reply_text("❌ Failed to authorize chat.")


@app.on_message(filters.command("removeauth") & filters.user(config.ADMINS))
async def remove_auth_chat(client: Client, message: Message):
    chat_id = message.chat.id
    if message.reply_to_message:
        chat_id = message.reply_to_message.chat.id
    elif len(message.command) > 1:
        try:
            chat_id = int(message.command[1])
        except ValueError:
            return await message.reply_text("Invalid Chat ID.")
    if not await db.is_authorized_chat(chat_id):
        return await message.reply_text("❌ Chat is not authorized.")
    if await db.remove_authorized_chat(chat_id):
        await message.reply_text(f"✅ Chat `{chat_id}` has been de-authorized.")
    else:
        await message.reply_text("❌ Failed to de-authorize chat.")


# ===================================================================
# 3. TASK & FILE HANDLERS
# ===================================================================
@app.on_message(filters.command("cancel"))
async def cancel_handler(client: Client, message: Message, reply: bool = True):
    user_id = message.from_user.id
    if not await is_authorized_user(user_id, message.chat.id): return

    task_id = None
    for tid, info in process_manager.active_processes.items():
        if info['user_id'] == user_id:
            task_id = tid
            break

    if not task_id:
        running_task = await db.tasks.find_one({
            "user_id": user_id,
            "status": {
                "$in": ["pending", "downloading", "processing", "uploading"]
            }
        })
        if running_task:
            task_id = running_task['task_id']
            logger.warning(f"Task {task_id} in DB (stuck). Cleaning up.")
            await db.update_task(task_id, {"status": "cancelled"})
            if reply:
                await message.reply_text(
                    config.MSG_TASK_CANCELLED.format(task_id=task_id))
            return
        else:
            if reply: await message.reply_text(config.MSG_NO_ACTIVE_TASK)
            return

    await process_manager.kill_process_async(task_id)
    user_download_dir = os.path.join(config.DOWNLOAD_DIR, str(user_id),
                                     task_id)
    cleanup_files(user_download_dir)

    if reply:
        await message.reply_text(
            config.MSG_TASK_CANCELLED.format(task_id=task_id))


@app.on_message(filters.command("process"))
async def process_handler(client: Client, message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if not await is_authorized_user(user_id, chat_id): return
    if not await verify_user_complete(client, message): return

    if await db.is_user_task_running(user_id):
        return await message.reply_text(config.MSG_TASK_IN_PROGRESS,
                                        quote=True)

    try:
        settings = await db.get_user_settings(user_id)
        active_tool = settings.get("active_tool")
    except Exception as e:
        logger.error(f"Failed to get settings in process_handler: {e}")
        return await message.reply_text("❌ Could not retrieve your settings.")

    if active_tool != 'merge':
        return await message.reply_text(
            config.MSG_PROCESS_FOR_MERGE_ONLY.format(active_tool=active_tool),
            quote=True)

    from modules.queue_manager import queue_manager

    if not queue_manager.has_queue(user_id) or queue_manager.get_queue_count(
            user_id) < 2:
        return await message.reply_text(config.MSG_MERGE_NO_FILES, quote=True)

    if not bot_state.is_bot_active() and user_id not in config.ADMINS:
        return await message.reply_text(config.MSG_BOT_ON_HOLD, quote=True)
    if settings.get("is_on_hold", False):
        return await message.reply_text(config.MSG_USER_ON_HOLD, quote=True)

    task_id = await db.create_task(user_id, active_tool, "telegram_files")
    if not task_id:
        return await message.reply_text("❌ Error creating task in database.")

    queue_items = queue_manager.get_queue(user_id)
    messages_to_merge = [item['message'] for item in queue_items]
    queue_manager.clear_queue(user_id)

    await start_merge_task(client, message, messages_to_merge, user_id,
                           task_id, settings)


@app.on_message((filters.video | filters.document | filters.audio
                 | filters.text)
                & filters.group
                & ~filters.media_group
                & ~filters.regex(r'^/'))
async def file_handler(client: Client, message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if not await is_authorized_user(user_id, chat_id): return
    if not await verify_user_complete(client, message): return

    if await db.is_user_task_running(user_id):
        return await message.reply_text(config.MSG_TASK_IN_PROGRESS,
                                        quote=True)

    try:
        settings = await db.get_user_settings(user_id)
        active_tool = settings.get("active_tool")
        download_mode = settings.get("download_mode")
    except Exception as e:
        logger.error(f"Failed to get settings in file_handler: {e}")
        return await message.reply_text("❌ Could not retrieve your settings.")

    if not bot_state.is_bot_active() and user_id not in config.ADMINS:
        return await message.reply_text(config.MSG_BOT_ON_HOLD, quote=True)
    if settings.get("is_on_hold", False):
        return await message.reply_text(config.MSG_USER_ON_HOLD, quote=True)

    if not active_tool or active_tool == "none":
        return await message.reply_text(config.MSG_SELECT_TOOL_FIRST,
                                        quote=True)

    is_url = bool(message.text and is_valid_url(message.text))
    is_tg_file = bool(message.video or message.document or message.audio)

    if download_mode == "url" and is_tg_file:
        return await message.reply_text(config.MSG_MODE_MISMATCH_FILE,
                                        quote=True)
    if download_mode == "telegram" and is_url:
        return await message.reply_text(config.MSG_MODE_MISMATCH_URL,
                                        quote=True)

    if not is_url and not is_tg_file:
        if message.text: return
        return await message.reply_text(
            "❌ Invalid input. Please send a file or a valid URL.", quote=True)

    if active_tool == 'merge':
        if download_mode == 'url':
            return await message.reply_text(config.MSG_MERGE_URL_REJECTED,
                                            quote=True)

        from modules.queue_manager import queue_manager
        file_info = {
            'message':
            message,
            'filename':
            getattr(message.video or message.document or message.audio,
                    'file_name', 'Unknown'),
            'file_size':
            getattr(message.video or message.document or message.audio,
                    'file_size', 0)
        }
        count = queue_manager.add_to_queue(user_id, file_info)
        queue_msg = queue_manager.format_queue_message(
            user_id,
            user_name=message.from_user.first_name,
            title="Testing [Merge]")
        keyboard = queue_manager.get_queue_keyboard(user_id)
        return await message.reply_text(queue_msg,
                                        reply_markup=keyboard,
                                        quote=True)

    input_source = message.text if is_url else "telegram_file"
    task_id = await db.create_task(user_id, active_tool, input_source)
    if not task_id:
        return await message.reply_text("❌ Error creating task in database.")

    await start_processing_task(client, message, user_id, task_id, settings)


# ===================================================================
# 5. CORE PROCESSING FUNCTIONS
# ===================================================================


async def start_merge_task(client: Client, trigger_message: Message,
                           messages_to_merge: list, user_id: int, task_id: str,
                           settings: dict):
    """Manages the merge task lifecycle."""
    status_message = None
    log_message_id = None
    user = trigger_message.from_user
    user_download_dir = os.path.join(config.DOWNLOAD_DIR, str(user_id),
                                     task_id)
    output_file_path = None
    downloaded_files = []

    cancel_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton(config.BTN_CANCEL,
                             callback_data=f"task_cancel:{task_id}")
    ]])

    try:
        await db.update_task(task_id, {"status": "starting"})
        status_message = await trigger_message.reply_text(
            config.MSG_TASK_ACCEPTED.format(task_id=task_id,
                                            tool="MERGE",
                                            count=len(messages_to_merge)),
            quote=True,
            reply_markup=cancel_markup)

        log_message_id = await log_manager.create_task_log(
            client, user, settings, task_id)
        await db.update_task(task_id, {"status": "downloading"})
        await log_manager.update_task_log(client, log_message_id,
                                          "Downloading files...")

        for i, msg in enumerate(messages_to_merge):
            file_num = i + 1
            await status_message.edit_text(
                config.MSG_DOWNLOAD_MERGE_PROGRESS.format(
                    task_id=task_id,
                    file_num=file_num,
                    total_files=len(messages_to_merge)),
                reply_markup=cancel_markup)

            download_path = await download_from_tg(client,
                                                   msg,
                                                   user_id,
                                                   task_id,
                                                   status_message,
                                                   log_manager,
                                                   log_message_id,
                                                   cancel_markup=cancel_markup)
            if not download_path:
                raise Exception(f"File {file_num} download failed.")
            downloaded_files.append(download_path)

        await db.update_task(task_id, {"status": "processing"})
        await log_manager.update_task_log(client, log_message_id, "Processing")

        # ✅ [CRITICAL FIX v6.3] `processor.process_task` को कॉल करें
        # यह अब 6 आर्ग्युमेंट्स लेता है (settings नहीं)
        output_file_path = await processor.process_task(
            client, user_id, task_id, downloaded_files, status_message,
            log_message_id)

        # ✅ [CRITICAL FIX v6.3] जाँचें कि क्या प्रोसेस सफल हुआ
        if not output_file_path:
            # `processor.py` (v6.12) ने पहले ही status_message को एरर के साथ अपडेट कर दिया है
            raise Exception(
                "Processing failed. Check status message for error.")

        # --- Rest of upload logic unchanged ---
        await log_manager.update_task_log(client, log_message_id,
                                          "Preparing filename")
        default_filename = os.path.basename(output_file_path).rsplit('.', 1)[0]
        custom_filename = settings.get('custom_filename', default_filename)
        if not custom_filename:
            custom_filename = default_filename
        custom_filename = custom_filename.strip().replace('/', '_')

        await log_manager.update_task_log(client, log_message_id,
                                          "Waiting for Upload Mode")
        file_size = os.path.getsize(output_file_path)
        upload_choice = settings.get('upload_mode', 'telegram')

        if upload_choice == 'telegram' and file_size > config.MAX_TG_UPLOAD_SIZE_BYTES:
            await status_message.edit_text(config.MSG_FORCE_GOFILE.format(
                size=get_human_readable_size(file_size)),
                                           reply_markup=cancel_markup)
            upload_choice = "gofile"

        await db.update_task(task_id, {
            "status": "uploading",
            "upload_target": upload_choice
        })
        await log_manager.update_task_log(client, log_message_id,
                                          f"Uploading to {upload_choice}")

        if upload_choice == "gofile":
            gofile = GofileUploader(user_id, task_id, status_message,
                                    log_manager, log_message_id, client,
                                    cancel_markup)
            gofile_link = await gofile.upload_file(output_file_path,
                                                   custom_filename)
            await status_message.delete()
            final_text = config.MSG_UPLOAD_COMPLETE_GOFILE.format(
                task_id=task_id, user_mention=user.mention, link=gofile_link)
            await client.send_message(trigger_message.chat.id,
                                      final_text,
                                      disable_web_page_preview=True)
            await log_manager.finish_task_log(client, log_message_id,
                                              "Complete", file_size,
                                              gofile_link)
        else:
            await log_manager.update_task_log(client, log_message_id,
                                              "Waiting for Thumbnail")
            thumb_path = None
            saved_thumb_id = settings.get("custom_thumbnail")
            if saved_thumb_id:
                thumb_path = await client.download_media(
                    saved_thumb_id,
                    file_name=os.path.join(user_download_dir, "thumb.jpg"))

            success, final_size = await upload_to_telegram(
                client, user, trigger_message.chat.id, output_file_path,
                status_message, thumb_path, custom_filename, settings,
                log_manager, log_message_id, task_id, cancel_markup)
            if success:
                await log_manager.finish_task_log(client, log_message_id,
                                                  "Complete", final_size)
            else:
                raise Exception("Telegram upload failed.")

        await db.update_task(task_id, {"status": "completed"})

    except asyncio.CancelledError:
        logger.warning(
            f"Task {task_id} (merge) received a CancelledError. Checking source..."
        )
        task_info = await db.get_task(task_id)
        is_user_cancel = (task_info and task_info.get("status") == "cancelled")

        if is_user_cancel:
            logger.info(
                f"Task {task_id} (merge) was confirmed cancelled by user.")
            if status_message:
                await status_message.edit_text(
                    config.MSG_TASK_CANCELLED.format(task_id=task_id),
                    reply_markup=None)
            if log_message_id:
                await log_manager.finish_task_log(client, log_message_id,
                                                  "Cancelled", 0)
        else:
            error_msg = "Upload failed (connection lost or system interrupt)"
            logger.error(
                f"Task {task_id} (merge) failed with a system interrupt (misreported as CancelledError).",
                exc_info=False)
            if status_message:
                await status_message.edit_text(config.MSG_TASK_FAILED.format(
                    task_id=task_id, error=error_msg),
                                               reply_markup=None)
            if log_message_id:
                await log_manager.finish_task_log(client, log_message_id,
                                                  f"Failed: {error_msg}", 0)
            await db.update_task(task_id, {
                "status": "failed",
                "error_msg": error_msg
            })

    except Exception as e:
        logger.error(f"Task {task_id} (merge) failed: {e}", exc_info=True)
        # ✅ [FIX v6.3] `processor.py` एरर को दोबारा न भेजें
        if status_message and "Processing failed" not in str(e):
            try:
                await status_message.edit_text(config.MSG_TASK_FAILED.format(
                    task_id=task_id, error=e),
                                               reply_markup=None)
            except:
                pass
        if log_message_id:
            await log_manager.finish_task_log(client, log_message_id,
                                              f"Failed: {str(e)}", 0)
        # सुनिश्चित करें कि DB "failed" पर सेट है
        task_info = await db.get_task(task_id)
        if task_info and task_info.get("status") != "failed":
            await db.update_task(task_id, {
                "status": "failed",
                "error_msg": str(e)
            })

    finally:
        cleanup_files(user_download_dir)


# --- END OF FUNCTION 1 ---


async def start_processing_task(client: Client, message: Message, user_id: int,
                                task_id: str, settings: dict):
    """Manages the standard (single file) task lifecycle"""
    status_message = None
    log_message_id = None
    user = message.from_user
    user_download_dir = os.path.join(config.DOWNLOAD_DIR, str(user_id),
                                     task_id)
    output_file_path = None
    downloaded_files = []

    cancel_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton(config.BTN_CANCEL,
                             callback_data=f"task_cancel:{task_id}")
    ]])

    try:
        await db.update_task(task_id, {"status": "starting"})
        status_message = await message.reply_text(
            config.MSG_TASK_ACCEPTED_SINGLE.format(
                task_id=task_id, tool=settings['active_tool'].upper()),
            quote=True,
            reply_markup=cancel_markup)

        log_message_id = await log_manager.create_task_log(
            client, user, settings, task_id)
        await db.update_task(task_id, {"status": "downloading"})
        await log_manager.update_task_log(client, log_message_id,
                                          "Initializing Download")

        downloader = None
        download_path = None
        if settings['download_mode'] == 'url':
            downloader = YTDLDownloader(user_id, task_id, status_message,
                                        log_manager, log_message_id, client,
                                        cancel_markup)
            download_path = await downloader.download(message.text)
        else:
            download_path = await download_from_tg(client,
                                                   message,
                                                   user_id,
                                                   task_id,
                                                   status_message,
                                                   log_manager,
                                                   log_message_id,
                                                   cancel_markup=cancel_markup)

        if not download_path:
            raise Exception("File download failed.")
        downloaded_files.append(download_path)
        await db.update_task(task_id, {"status": "processing"})
        await log_manager.update_task_log(client, log_message_id, "Processing")

        # ✅ [CRITICAL FIX v6.3] `processor.process_task` को कॉल करें
        # यह अब 6 आर्ग्युमेंट्स लेता है (settings नहीं)
        output_file_path = await processor.process_task(
            client, user_id, task_id, downloaded_files, status_message,
            log_message_id)

        # ✅ [CRITICAL FIX v6.3] जाँचें कि क्या प्रोसेस सफल हुआ
        if not output_file_path:
            if settings['active_tool'] == 'mediainfo':
                await log_manager.finish_task_log(client, log_message_id,
                                                  "Complete (MediaInfo)", 0)
                await db.update_task(task_id, {"status": "completed"})
                return
            else:
                raise Exception(
                    "Processing failed. Check status message for error.")

        # --- Rest of upload logic unchanged ---
        await log_manager.update_task_log(client, log_message_id,
                                          "Preparing filename")
        default_filename = os.path.basename(output_file_path).rsplit('.', 1)[0]
        custom_filename = settings.get('custom_filename', default_filename)
        if not custom_filename:
            custom_filename = default_filename
        custom_filename = custom_filename.strip().replace('/', '_')

        active_tool = settings.get('active_tool')
        if active_tool == 'encode':
            suffix = settings.get('encode_settings', {}).get('suffix', '')
            if suffix:
                custom_filename = f"{custom_filename} {suffix}"

        await log_manager.update_task_log(client, log_message_id,
                                          "Waiting for Upload Mode")
        file_size = os.path.getsize(output_file_path)
        upload_choice = settings.get('upload_mode', 'telegram')

        if upload_choice == 'telegram' and file_size > config.MAX_TG_UPLOAD_SIZE_BYTES:
            await status_message.edit_text(config.MSG_FORCE_GOFILE.format(
                size=get_human_readable_size(file_size)),
                                           reply_markup=cancel_markup)
            upload_choice = "gofile"

        await db.update_task(task_id, {
            "status": "uploading",
            "upload_target": upload_choice
        })
        await log_manager.update_task_log(client, log_message_id,
                                          f"Uploading to {upload_choice}")

        if upload_choice == "gofile":
            gofile = GofileUploader(user_id, task_id, status_message,
                                    log_manager, log_message_id, client,
                                    cancel_markup)
            gofile_link = await gofile.upload_file(output_file_path,
                                                   custom_filename)
            await status_message.delete()
            final_text = config.MSG_UPLOAD_COMPLETE_GOFILE.format(
                task_id=task_id, user_mention=user.mention, link=gofile_link)
            await client.send_message(message.chat.id,
                                      final_text,
                                      disable_web_page_preview=True)
            await log_manager.finish_task_log(client, log_message_id,
                                              "Complete", file_size,
                                              gofile_link)
        else:
            await log_manager.update_task_log(client, log_message_id,
                                              "Waiting for Thumbnail")
            thumb_path = None
            saved_thumb_id = settings.get("custom_thumbnail")
            if saved_thumb_id:
                thumb_path = await client.download_media(
                    saved_thumb_id,
                    file_name=os.path.join(user_download_dir, "thumb.jpg"))

            if active_tool == 'extract_thumb' and output_file_path.endswith(
                    ".jpg"):
                thumb_path = output_file_path

            success, final_size = await upload_to_telegram(
                client, user, message.chat.id, output_file_path,
                status_message, thumb_path, custom_filename, settings,
                log_manager, log_message_id, task_id, cancel_markup)
            if success:
                await log_manager.finish_task_log(client, log_message_id,
                                                  "Complete", final_size)
            else:
                raise Exception("Telegram upload failed.")

        await db.update_task(task_id, {"status": "completed"})

    except asyncio.CancelledError:
        logger.warning(
            f"Task {task_id} received a CancelledError. Checking source...")
        task_info = await db.get_task(task_id)
        is_user_cancel = (task_info and task_info.get("status") == "cancelled")

        if is_user_cancel:
            logger.info(f"Task {task_id} was confirmed cancelled by user.")
            if status_message:
                await status_message.edit_text(
                    config.MSG_TASK_CANCELLED.format(task_id=task_id),
                    reply_markup=None)
            if log_message_id:
                await log_manager.finish_task_log(client, log_message_id,
                                                  "Cancelled", 0)
        else:
            error_msg = "Upload failed (connection lost or system interrupt)"
            logger.error(
                f"Task {task_id} failed with a system interrupt (misreported as CancelledError).",
                exc_info=False)
            if status_message:
                await status_message.edit_text(config.MSG_TASK_FAILED.format(
                    task_id=task_id, error=error_msg),
                                               reply_markup=None)
            if log_message_id:
                await log_manager.finish_task_log(client, log_message_id,
                                                  f"Failed: {error_msg}", 0)
            await db.update_task(task_id, {
                "status": "failed",
                "error_msg": error_msg
            })

    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}", exc_info=True)
        if status_message and "Processing failed" not in str(e):
            try:
                await status_message.edit_text(config.MSG_TASK_FAILED.format(
                    task_id=task_id, error=e),
                                               reply_markup=None)
            except:
                pass
        if log_message_id:
            await log_manager.finish_task_log(client, log_message_id,
                                              f"Failed: {str(e)}", 0)
        task_info = await db.get_task(task_id)
        if task_info and task_info.get("status") != "failed":
            await db.update_task(task_id, {
                "status": "failed",
                "error_msg": str(e)
            })

    finally:
        cleanup_files(user_download_dir)


# --- END OF FUNCTION 2 ---

# ===================================================================
# 6. CALLBACK HANDLER (v6.0 - Granular UI Logic)
# ===================================================================


async def refresh_panel(query: CallbackQuery, panel_type: str):
    user_id = query.from_user.id
    try:
        image, caption, keyboard = None, None, None
        if panel_type.startswith("vt:"):
            tool, menu = panel_type.split(":", 2)[1:]
            if tool == "merge":
                image, caption, keyboard = await get_vt_merge_menu(user_id)
            elif tool == "encode":
                image, caption, keyboard = await get_vt_encode_menu(
                    user_id, menu_type=menu)
            elif tool == "trim":
                image, caption, keyboard = await get_vt_trim_menu(user_id)
            elif tool == "watermark":
                image, caption, keyboard = await get_vt_watermark_menu(
                    user_id, menu_type=menu)
            elif tool == "sample":
                image, caption, keyboard = await get_vt_sample_menu(
                    user_id, menu_type=menu)
            elif tool == "extract":
                image, caption, keyboard = await get_vt_extract_menu(user_id)
            elif tool == "extra":
                image, caption, keyboard = await get_vt_extra_menu(user_id)
            elif tool == "rotate":
                image, caption, keyboard = await get_vt_rotate_menu(
                    user_id, menu_type=menu)
            elif tool == "flip":
                image, caption, keyboard = await get_vt_flip_menu(
                    user_id, menu_type=menu)
            elif tool == "speed":
                image, caption, keyboard = await get_vt_speed_menu(
                    user_id, menu_type=menu)
            elif tool == "volume":
                image, caption, keyboard = await get_vt_volume_menu(
                    user_id, menu_type=menu)
            elif tool == "crop":
                image, caption, keyboard = await get_vt_crop_menu(
                    user_id, menu_type=menu)
            elif tool == "gif":
                image, caption, keyboard = await get_vt_gif_menu(
                    user_id, menu_type=menu)
            elif tool == "reverse":
                image, caption, keyboard = await get_vt_reverse_menu(
                    user_id, menu_type=menu)
            else:
                image, caption, keyboard = await get_video_tools_menu(user_id)
        elif panel_type.startswith("us:metadata"):
            image, caption, keyboard = await get_metadata_submenu(user_id)
        elif panel_type == "start":
            image, caption, keyboard = await get_start_menu(user_id)
        elif panel_type == "settings":
            image, caption, keyboard = await get_user_settings_menu(user_id)
        elif panel_type == "tools":
            image, caption, keyboard = await get_video_tools_menu(user_id)
        elif panel_type == "admin":
            image, caption, keyboard = await get_admin_menu()

        if keyboard:
            await query.message.edit_media(media=InputMediaPhoto(
                image, caption=caption),
                                           reply_markup=keyboard)
            await query.answer()
        else:
            await query.answer("Error: Panel not found.")
    except MessageNotModified:
        await query.answer()
    except QueryIdInvalid:
        pass
    except Exception as e:
        logger.error(f"Error refreshing panel {panel_type}: {e}",
                     exc_info=True)
        await query.answer("An error occurred.", show_alert=True)


@app.on_callback_query()
async def callback_handler(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    data = query.data
    chat_id = query.message.chat.id

    def safe_answer(msg="", show_alert=False):
        try:
            return query.answer(msg, show_alert=show_alert)
        except Exception:
            return None

    try:
        if data == "check_subscription":
            if await verify_user_complete(client, query):
                await query.answer("✅ Subscription verified!", show_alert=True)
                await query.message.delete()
                dummy_message = query.message
                dummy_message.from_user = query.from_user
                await start_handler(client, dummy_message)
            return

        if not await is_authorized_user(user_id, chat_id):
            return await query.answer("❌ You are not authorized.",
                                      show_alert=True)

        if data.startswith("task_cancel:"):
            task_id = data.split(":", 1)[1]
            info = process_manager.get_process_info(task_id)
            if not info:
                db_task = await db.get_task(task_id)
                if not db_task or db_task["user_id"] != user_id:
                    return await query.answer(
                        "❌ Not your task or already finished.",
                        show_alert=True)
                if db_task["status"] in [
                        "pending", "downloading", "processing", "uploading"
                ]:
                    await db.update_task(task_id, {"status": "cancelled"})
                else:
                    return await query.answer("❌ Task already done.",
                                              show_alert=True)
            elif info["user_id"] != user_id:
                return await query.answer("❌ This is not your task.",
                                          show_alert=True)
            await process_manager.kill_process_async(task_id)
            cleanup_files(
                os.path.join(config.DOWNLOAD_DIR, str(user_id), task_id))
            await query.answer("Task Cancelled!", show_alert=True)
            await query.message.edit_text(
                config.MSG_TASK_CANCELLED.format(task_id=task_id))
            return

        if data.startswith("queue:"):
            from modules.queue_manager import queue_manager
            action = data.split(":", 1)[1]
            if action == "add_more":
                await query.answer("👍 Send more videos to add to queue!")
                return
            elif action == "merge_now":
                if not queue_manager.has_queue(
                        user_id) or queue_manager.get_queue_count(user_id) < 2:
                    return await query.answer(
                        "❌ Need at least 2 videos in queue", show_alert=True)
                settings = await db.get_user_settings(user_id)
                if await db.is_user_task_running(user_id):
                    return await query.answer(
                        "⏳ You have a task running. Please wait.",
                        show_alert=True)
                task_id = await db.create_task(user_id, "merge",
                                               "telegram_files")
                if not task_id:
                    return await query.answer("❌ Error creating task",
                                              show_alert=True)
                queue_items = queue_manager.get_queue(user_id)
                messages_to_merge = [item['message'] for item in queue_items]
                queue_manager.clear_queue(user_id)
                await query.answer("🔀 Starting merge process...")
                await query.message.delete()
                await start_merge_task(client, query.message,
                                       messages_to_merge, user_id, task_id,
                                       settings)
                return
            elif action == "clear":
                queue_manager.clear_queue(user_id)
                await query.answer("🗑️ Queue cleared!", show_alert=True)
                await query.message.delete()
                return

        if data.startswith("open:"):
            panel = data.split(":", 1)[1]
            if panel in ["start", "settings", "tools", "admin"]:
                return await refresh_panel(query, panel)
            elif panel == "help":
                await query.message.edit_media(
                    InputMediaPhoto(config.IMG_START, caption=config.MSG_HELP),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(f"🔙 {config.BTN_BACK}",
                                             callback_data="open:start")
                    ]]))
                return await query.answer()
            elif panel == "about":
                caption = config.MSG_ABOUT.format(bot_name=config.BOT_NAME,
                                                  developer=config.DEVELOPER)
                await query.message.edit_media(
                    InputMediaPhoto(config.IMG_START, caption=caption),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(f"🔙 {config.BTN_BACK}",
                                             callback_data="open:start")
                    ]]))
                return await query.answer()

        parts = data.split(":")
        prefix = parts[0]

        if prefix == "us":
            action, *payload = parts[1:]
            payload = ":".join(payload)
            if action == "toggle":
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
                    await query.answer(
                        f"{key.replace('_',' ').title()} → {new.capitalize()}")
                else:
                    new_val = await db.toggle_user_setting(user_id, key)
                    await query.answer(
                        f"{key.replace('_',' ').capitalize()} set to {'ON' if new_val else 'OFF'}"
                    )
                if key == "metadata":
                    return await refresh_panel(query, "us:metadata")
            elif action == "set" and payload == "custom_thumbnail:none":
                await db.update_user_setting(user_id, "custom_thumbnail", None)
                await query.answer("Thumbnail cleared.")
            elif action == "metadata":
                if len(parts) < 3:
                    return await query.answer("Invalid metadata action")
                metadata_action = parts[2]
                if metadata_action == "open" and len(
                        parts) > 3 and parts[3] == "main":
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
                        await db.update_user_nested_setting(
                            user_id, f"metadata_custom.{field}", r.text)
                        await r.reply_text(config.MSG_SET_SUCCESS)
                    except asyncio.TimeoutError:
                        return await client.send_message(
                            chat_id, config.MSG_SET_TIMEOUT)
                    return await refresh_panel(query, "us:metadata")
                elif metadata_action == "clear" and len(
                        parts) > 3 and parts[3] == "all":
                    await db.update_user_setting(user_id, "metadata_custom",
                                                 {})
                    await query.answer("All custom metadata cleared!")
                    return await refresh_panel(query, "us:metadata")
            elif action == "ask":
                key = payload
                try:
                    if key == "custom_filename":
                        await query.answer()
                        r = await client.ask(chat_id,
                                             config.MSG_ASK_FILENAME,
                                             filters=filters.text,
                                             timeout=300)
                        if r.text == "/cancel":
                            return await r.reply_text(config.MSG_SET_CANCELLED)
                        if " " in r.text or "." in r.text:
                            return await r.reply_text(
                                config.MSG_SET_ERROR_FILENAME)
                        await db.update_user_setting(user_id,
                                                     "custom_filename", r.text)
                        await r.reply_text(config.MSG_SET_SUCCESS)
                    elif key == "custom_thumbnail":
                        await query.answer()
                        r = await client.ask(chat_id,
                                             config.MSG_ASK_THUMBNAIL,
                                             filters=filters.photo,
                                             timeout=300)
                        await db.update_user_setting(user_id,
                                                     "custom_thumbnail",
                                                     r.photo.file_id)
                        await r.reply_text(config.MSG_SET_SUCCESS)
                except asyncio.TimeoutError:
                    return await client.send_message(chat_id,
                                                     config.MSG_SET_TIMEOUT)
            return await refresh_panel(query, "settings")

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
                    await db.update_user_setting(user_id, "active_tool",
                                                 "none")
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
                        await db.update_user_nested_setting(
                            user_id, "encode_settings.resolution", base)
                        await db.update_user_nested_setting(
                            user_id, "encode_settings.vcodec", "libx265")
                        await query.answer(f"Set {base.upper()} (HEVC)",
                                           show_alert=False)
                    else:
                        await db.update_user_nested_setting(
                            user_id, "encode_settings.resolution", value)
                        await db.update_user_nested_setting(
                            user_id, "encode_settings.vcodec", "libx264")
                        await query.answer(f"Set {value.upper()} (H.264)",
                                           show_alert=False)
                    return await refresh_panel(query, f"vt:{tool}:resolution")
                if key in [
                        "crf", "duration", "angle", "volume", "fps", "scale"
                ]:
                    value = int(value)
                elif key == "opacity" or key == "speed":
                    value = float(value)
                await db.update_user_nested_setting(user_id, db_key, value)
                await query.answer(f"{key.capitalize()} set to {value}")
                if key in ["vcodec", "crf", "preset", "resolution", "acodec"]:
                    panel = f"vt:encode:{key}"
                elif key in ["type", "position"]:
                    panel = f"vt:watermark:{key}"
                elif key == "from_point":
                    panel = "vt:sample:from"
                elif key in [
                        "angle", "direction", "speed", "volume",
                        "aspect_ratio", "quality"
                ]:
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
                        validation = lambda x: x.endswith(
                            "k") and x[:-1].isdigit()
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
                    return await query.answer(
                        "⚠️ No input expected for this action.")
                if not error_msg:
                    error_msg = "❌ Invalid input. Please try again."
                await query.answer()
                try:
                    resp = await client.ask(chat_id,
                                            ask_msg,
                                            filters=filters.text,
                                            timeout=300)
                    if resp.text == "/cancel":
                        return await resp.reply_text(config.MSG_SET_CANCELLED)
                    if not validation(resp.text):
                        return await resp.reply_text(error_msg)
                    val = resp.text
                    if key == "resolution":
                        await db.update_user_nested_setting(
                            user_id, "encode_settings.resolution", "custom")
                        await db.update_user_nested_setting(
                            user_id, db_key, val)
                    else:
                        await db.update_user_nested_setting(
                            user_id, db_key, val)
                    await resp.reply_text(config.MSG_SET_SUCCESS)
                    return await refresh_panel(query, f"vt:{tool}:main")
                except asyncio.TimeoutError:
                    return await client.send_message(chat_id,
                                                     config.MSG_SET_TIMEOUT)
            elif action == "queue":
                from modules.queue_manager import queue_manager
                if tool != "merge":
                    return await query.answer("Queue is only for merge tool!",
                                              show_alert=True)
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
                        return await query.answer(
                            "Need at least 2 files to merge!", show_alert=True)
                    await query.answer("Starting merge process...")
                    queue_manager.clear_queue(user_id)
                    await query.message.reply_text(
                        "🔀 Merge processing will be implemented in the merge handler!"
                    )
                    return

        if prefix == "admin":
            if user_id not in config.ADMINS:
                return await query.answer("❌ You are not an admin.",
                                          show_alert=True)
            act, *payload = parts[1:]
            payload = payload[0] if payload else ""
            if act == "toggle" and payload == "mode":
                cur = bot_state.get_bot_mode()
                new = "ACTIVE" if cur == "HOLD" else "HOLD"
                bot_state.set_bot_mode(new)
                await query.answer(f"Bot mode: {new}")
                return await refresh_panel(query, "admin")
            elif act == "show" and payload == "tasks":
                await status_handler(client, query.message)
                return await query.answer()
            elif act == "show" and payload == "stats":
                await query.answer("📊 Stats view coming soon.",
                                   show_alert=True)
                logger.info(
                    f"Admin {user_id} requested stats (not yet implemented)")
                return
            elif act == "broadcast":
                await query.answer("📣 Broadcast tooling under development.",
                                   show_alert=True)
                logger.info(
                    f"Admin {user_id} requested broadcast (not yet implemented)"
                )
                return
            elif act == "restart":
                if user_id not in config.SUDO_USERS:
                    return await query.answer("❌ Only Sudo Users can restart.",
                                              show_alert=True)
                await query.message.edit_text("🔄 Restarting...")
                await app.stop()
                os.execl(sys.executable, sys.executable, *sys.argv)

        await query.answer()

    except Exception as e:
        logger.error(f"Callback Error: {e}", exc_info=True)
        safe_answer("⚠️ An error occurred.", show_alert=True)


# ===================================================================
# BOT STARTUP
# ===================================================================
if __name__ == "__main__":

    async def main():
        logger.info(f"🚀 Starting {config.BOT_NAME} (v6.3)...")  # v6.3
        logger.info(f"👑 Owner ID: {config.OWNER_ID}")
        logger.info(f"📡 Task Log Channel: {config.TASK_LOG_CHANNEL}")
        logger.info(f"🤖 Default Mode: {bot_state.get_bot_mode()}")

        logger.info("Connecting to MongoDB...")
        db.connect(config.MONGO_URI, config.DATABASE_NAME)

        await app.start()

        base_commands = [
            BotCommand("start", "Start the bot"),
            BotCommand("us", "User Settings"),
            BotCommand("vt", "Video Tools"),
            BotCommand("cancel", "Cancel current task"),
            BotCommand("help", "Get help"),
            BotCommand("hold", "Pause/Resume your tasks"),
            BotCommand("process", "Process queued merge files")
        ]
        await app.set_bot_commands(base_commands)

        admin_commands = [
            BotCommand("admin", "Open Admin Panel"),
            BotCommand("botmode", "Check global bot mode"),
            BotCommand("activate", "Activate task processing (Global)"),
            BotCommand("deactivate", "Hold task processing (Global)"),
            BotCommand("s", "Check bot status (Admin)"),
            BotCommand("addauth", "Authorize a chat"),
            BotCommand("removeauth", "De-authorize a chat"),
            BotCommand("restart", "Restart the bot (Sudo)")
        ]
        full_admin_commands = base_commands + admin_commands
        for admin_id in config.ADMINS:
            try:
                await app.set_bot_commands(full_admin_commands,
                                           scope=BotCommandScopeChat(admin_id))
            except Exception:
                pass

        await idle()
        await app.stop()
        logger.info("Bot stopped.")

    try:
        app.run(main())
    except Exception as e:
        logger.critical(f"Bot exited with a critical error: {e}",
                        exc_info=True)
