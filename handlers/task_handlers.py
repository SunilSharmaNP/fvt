# handlers/task_handlers.py
# Task processing handlers: cancel, process, file handling, and task lifecycle management

import os
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from config import config
from modules import bot_state, log_manager, processor
from modules.database import db
from modules.helpers import is_authorized_user, verify_user_complete
from modules.utils import is_valid_url
from modules.downloader import download_from_tg, YTDLDownloader
from modules.uploader import GofileUploader, upload_to_telegram
from modules.utils import cleanup_files, process_manager, get_human_readable_size

logger = logging.getLogger(__name__)


def register_task_handlers(app: Client):
    """Register all task processing handlers"""

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
        user_download_dir = os.path.join(config.DOWNLOAD_DIR, str(user_id), task_id)
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
            return await message.reply_text(config.MSG_TASK_IN_PROGRESS, quote=True)

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

        if not queue_manager.has_queue(user_id) or queue_manager.get_queue_count(user_id) < 2:
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

        await start_merge_task(client, message, messages_to_merge, user_id, task_id, settings)

    @app.on_message((filters.video | filters.document | filters.audio | filters.text)
                    & filters.group
                    & ~filters.media_group
                    & ~filters.regex(r'^/'))
    async def file_handler(client: Client, message: Message):
        user_id = message.from_user.id
        chat_id = message.chat.id

        if not await is_authorized_user(user_id, chat_id): return
        if not await verify_user_complete(client, message): return

        if await db.is_user_task_running(user_id):
            return await message.reply_text(config.MSG_TASK_IN_PROGRESS, quote=True)

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
            return await message.reply_text(config.MSG_SELECT_TOOL_FIRST, quote=True)

        is_url = bool(message.text and is_valid_url(message.text))
        is_tg_file = bool(message.video or message.document or message.audio)

        if download_mode == "url" and is_tg_file:
            return await message.reply_text(config.MSG_MODE_MISMATCH_FILE, quote=True)
        if download_mode == "telegram" and is_url:
            return await message.reply_text(config.MSG_MODE_MISMATCH_URL, quote=True)

        if not is_url and not is_tg_file:
            if message.text: return
            return await message.reply_text(
                "❌ Invalid input. Please send a file or a valid URL.", quote=True)

        if active_tool == 'merge':
            if download_mode == 'url':
                return await message.reply_text(config.MSG_MERGE_URL_REJECTED, quote=True)

            from modules.queue_manager import queue_manager
            file_info = {
                'message': message,
                'filename': getattr(message.video or message.document or message.audio, 'file_name', 'Unknown'),
                'file_size': getattr(message.video or message.document or message.audio, 'file_size', 0)
            }
            count = queue_manager.add_to_queue(user_id, file_info)
            queue_msg = queue_manager.format_queue_message(
                user_id,
                user_name=message.from_user.first_name,
                title="Testing [Merge]")
            keyboard = queue_manager.get_queue_keyboard(user_id)
            return await message.reply_text(queue_msg, reply_markup=keyboard, quote=True)

        input_source = message.text if is_url else "telegram_file"
        task_id = await db.create_task(user_id, active_tool, input_source)
        if not task_id:
            return await message.reply_text("❌ Error creating task in database.")

        await start_processing_task(client, message, user_id, task_id, settings)

    logger.info("✅ Task handlers registered")


# ===================================================================
# CORE PROCESSING FUNCTIONS
# ===================================================================

async def start_merge_task(client: Client, trigger_message: Message,
                           messages_to_merge: list, user_id: int, task_id: str,
                           settings: dict):
    """Manages the merge task lifecycle."""
    status_message = None
    log_message_id = None
    user = trigger_message.from_user
    user_download_dir = os.path.join(config.DOWNLOAD_DIR, str(user_id), task_id)
    output_file_path = None
    downloaded_files = []

    cancel_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton(config.BTN_CANCEL, callback_data=f"task_cancel:{task_id}")
    ]])

    try:
        await db.update_task(task_id, {"status": "starting"})
        status_message = await trigger_message.reply_text(
            config.MSG_TASK_ACCEPTED.format(task_id=task_id, tool="MERGE", count=len(messages_to_merge)),
            quote=True,
            reply_markup=cancel_markup)

        log_message_id = await log_manager.create_task_log(client, user, settings, task_id)
        await db.update_task(task_id, {"status": "downloading"})
        await log_manager.update_task_log(client, log_message_id, "Downloading files...")

        for i, msg in enumerate(messages_to_merge):
            file_num = i + 1
            await status_message.edit_text(
                config.MSG_DOWNLOAD_MERGE_PROGRESS.format(
                    task_id=task_id,
                    file_num=file_num,
                    total_files=len(messages_to_merge)),
                reply_markup=cancel_markup)

            download_path = await download_from_tg(client, msg, user_id, task_id, status_message,
                                                   log_manager, log_message_id, cancel_markup=cancel_markup)
            if not download_path:
                raise Exception(f"File {file_num} download failed.")
            downloaded_files.append(download_path)

        await db.update_task(task_id, {"status": "processing"})
        await log_manager.update_task_log(client, log_message_id, "Processing")

        # ✅ [CRITICAL FIX v6.3] Calling processor.process_task with 6 arguments (settings not included)
        output_file_path = await processor.process_task(
            client, user_id, task_id, downloaded_files, status_message, log_message_id)

        # ✅ [CRITICAL FIX v6.3] Check if processing was successful
        if not output_file_path:
            raise Exception("Processing failed. Check status message for error.")

        # Upload logic
        await log_manager.update_task_log(client, log_message_id, "Preparing filename")
        default_filename = os.path.basename(output_file_path).rsplit('.', 1)[0]
        custom_filename = settings.get('custom_filename', default_filename)
        if not custom_filename:
            custom_filename = default_filename
        custom_filename = custom_filename.strip().replace('/', '_')

        await log_manager.update_task_log(client, log_message_id, "Waiting for Upload Mode")
        file_size = os.path.getsize(output_file_path)
        upload_choice = settings.get('upload_mode', 'telegram')

        if upload_choice == 'telegram' and file_size > config.MAX_TG_UPLOAD_SIZE_BYTES:
            await status_message.edit_text(
                config.MSG_FORCE_GOFILE.format(size=get_human_readable_size(file_size)),
                reply_markup=cancel_markup)
            upload_choice = "gofile"

        await db.update_task(task_id, {"status": "uploading", "upload_target": upload_choice})
        await log_manager.update_task_log(client, log_message_id, f"Uploading to {upload_choice}")

        if upload_choice == "gofile":
            gofile = GofileUploader(user_id, task_id, status_message, log_manager, log_message_id, client, cancel_markup)
            gofile_link = await gofile.upload_file(output_file_path, custom_filename)
            await status_message.delete()
            final_text = config.MSG_UPLOAD_COMPLETE_GOFILE.format(
                task_id=task_id, user_mention=user.mention, link=gofile_link)
            await client.send_message(trigger_message.chat.id, final_text, disable_web_page_preview=True)
            await log_manager.finish_task_log(client, log_message_id, "Complete", file_size, gofile_link)
        else:
            await log_manager.update_task_log(client, log_message_id, "Waiting for Thumbnail")
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
            if not success:
                raise Exception("Telegram upload failed")
            await log_manager.finish_task_log(client, log_message_id, "Complete", final_size)

        await db.update_task(task_id, {"status": "completed"})

    except Exception as e:
        logger.error(f"Merge task {task_id} error: {e}", exc_info=True)
        await db.update_task(task_id, {"status": "failed", "error_msg": str(e)})
        if status_message and "Processing failed" not in str(e):
            try:
                await status_message.edit_text(
                    config.MSG_TASK_FAILED.format(task_id=task_id, error=e),
                    reply_markup=None)
            except:
                pass
        if log_message_id:
            await log_manager.finish_task_log(client, log_message_id, f"Failed: {str(e)}", 0)
        task_info = await db.get_task(task_id)
        if task_info and task_info.get("status") != "failed":
            await db.update_task(task_id, {"status": "failed", "error_msg": str(e)})

    finally:
        cleanup_files(user_download_dir)


async def start_processing_task(client: Client, message: Message, user_id: int,
                                task_id: str, settings: dict):
    """Manages the standard (single file) task lifecycle"""
    status_message = None
    log_message_id = None
    user = message.from_user
    user_download_dir = os.path.join(config.DOWNLOAD_DIR, str(user_id), task_id)
    output_file_path = None
    downloaded_files = []

    cancel_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton(config.BTN_CANCEL, callback_data=f"task_cancel:{task_id}")
    ]])

    try:
        await db.update_task(task_id, {"status": "starting"})
        status_message = await message.reply_text(
            config.MSG_TASK_ACCEPTED_SINGLE.format(
                task_id=task_id, tool=settings['active_tool'].upper()),
            quote=True,
            reply_markup=cancel_markup)

        log_message_id = await log_manager.create_task_log(client, user, settings, task_id)
        await db.update_task(task_id, {"status": "downloading"})
        await log_manager.update_task_log(client, log_message_id, "Initializing Download")

        downloader = None
        download_path = None
        if settings['download_mode'] == 'url':
            downloader = YTDLDownloader(user_id, task_id, status_message,
                                        log_manager, log_message_id, client, cancel_markup)
            download_path = await downloader.download(message.text)
        else:
            download_path = await download_from_tg(client, message, user_id, task_id, status_message,
                                                   log_manager, log_message_id, cancel_markup=cancel_markup)

        if not download_path:
            raise Exception("File download failed.")
        downloaded_files.append(download_path)
        await db.update_task(task_id, {"status": "processing"})
        await log_manager.update_task_log(client, log_message_id, "Processing")

        # ✅ [CRITICAL FIX v6.3] Calling processor.process_task with 6 arguments (settings not included)
        output_file_path = await processor.process_task(
            client, user_id, task_id, downloaded_files, status_message, log_message_id)

        # ✅ [CRITICAL FIX v6.3] Check if processing was successful
        if not output_file_path:
            if settings['active_tool'] == 'mediainfo':
                await log_manager.finish_task_log(client, log_message_id, "Complete (MediaInfo)", 0)
                await db.update_task(task_id, {"status": "completed"})
                return
            else:
                raise Exception("Processing failed. Check status message for error.")

        # Upload logic
        await log_manager.update_task_log(client, log_message_id, "Preparing filename")
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

        await log_manager.update_task_log(client, log_message_id, "Waiting for Upload Mode")
        file_size = os.path.getsize(output_file_path)
        upload_choice = settings.get('upload_mode', 'telegram')

        if upload_choice == 'telegram' and file_size > config.MAX_TG_UPLOAD_SIZE_BYTES:
            await status_message.edit_text(
                config.MSG_FORCE_GOFILE.format(size=get_human_readable_size(file_size)),
                reply_markup=cancel_markup)
            upload_choice = "gofile"

        await db.update_task(task_id, {"status": "uploading", "upload_target": upload_choice})
        await log_manager.update_task_log(client, log_message_id, f"Uploading to {upload_choice}")

        if upload_choice == "gofile":
            gofile = GofileUploader(user_id, task_id, status_message, log_manager, log_message_id, client, cancel_markup)
            gofile_link = await gofile.upload_file(output_file_path, custom_filename)
            await status_message.delete()
            final_text = config.MSG_UPLOAD_COMPLETE_GOFILE.format(
                task_id=task_id, user_mention=user.mention, link=gofile_link)
            await client.send_message(message.chat.id, final_text, disable_web_page_preview=True)
            await log_manager.finish_task_log(client, log_message_id, "Complete", file_size, gofile_link)
        else:
            await log_manager.update_task_log(client, log_message_id, "Waiting for Thumbnail")
            thumb_path = None
            saved_thumb_id = settings.get("custom_thumbnail")
            if saved_thumb_id:
                thumb_path = await client.download_media(
                    saved_thumb_id,
                    file_name=os.path.join(user_download_dir, "thumb.jpg"))

            success, final_size = await upload_to_telegram(
                client, user, message.chat.id, output_file_path,
                status_message, thumb_path, custom_filename, settings,
                log_manager, log_message_id, task_id, cancel_markup)
            if not success:
                raise Exception("Telegram upload failed")
            await log_manager.finish_task_log(client, log_message_id, "Complete", final_size)

        await db.update_task(task_id, {"status": "completed"})

    except Exception as e:
        logger.error(f"Processing task {task_id} error: {e}", exc_info=True)
        await db.update_task(task_id, {"status": "failed", "error_msg": str(e)})
        if status_message and "Processing failed" not in str(e):
            try:
                await status_message.edit_text(
                    config.MSG_TASK_FAILED.format(task_id=task_id, error=e),
                    reply_markup=None)
            except:
                pass
        if log_message_id:
            await log_manager.finish_task_log(client, log_message_id, f"Failed: {str(e)}", 0)
        task_info = await db.get_task(task_id)
        if task_info and task_info.get("status") != "failed":
            await db.update_task(task_id, {"status": "failed", "error_msg": str(e)})

    finally:
        cleanup_files(user_download_dir)
