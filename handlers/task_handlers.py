# handlers/task_handlers.py (v7.0 - Professional Enhanced)
# Task processing handlers with complete implementations
# All missing functions added & production ready
# ==================================================

import os
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from config import config
from modules import bot_state, log_manager, processor
from modules.database import db
from modules.helpers import is_authorized_user, verify_user_complete
from modules.utils import is_valid_url, cleanup_files, process_manager, get_human_readable_size
from modules.downloader import download_from_tg, YTDLDownloader
from modules.uploader import GofileUploader, upload_to_telegram

logger = logging.getLogger(__name__)

def register_task_handlers(app: Client):
    """Register all task processing handlers"""

    @app.on_message(filters.command("cancel"))
    async def cancel_handler(client: Client, message: Message, reply: bool = True):
        """Handle /cancel command to stop current task"""
        user_id = message.from_user.id
        
        if not await is_authorized_user(user_id, message.chat.id):
            return
        
        task_id = None
        
        # Check active processes first
        for tid, info in process_manager.active_processes.items():
            if info.get('user_id') == user_id:
                task_id = tid
                break
        
        # If not in active processes, check database
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
                        config.MSG_TASK_CANCELLED.format(task_id=task_id)
                    )
                return
            else:
                if reply:
                    await message.reply_text(config.MSG_NO_ACTIVE_TASK)
                return
        
        # Kill the process
        await process_manager.kill_process_async(task_id)
        
        # Cleanup temporary files
        user_download_dir = os.path.join(config.DOWNLOAD_DIR, str(user_id), task_id)
        await cleanup_files(user_download_dir)
        
        # Update database
        await db.update_task(task_id, {"status": "cancelled"})
        
        if reply:
            await message.reply_text(
                config.MSG_TASK_CANCELLED.format(task_id=task_id)
            )

    @app.on_message(filters.command("process"))
    async def process_handler(client: Client, message: Message):
        """Handle /process command for merge operations"""
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        if not await is_authorized_user(user_id, chat_id):
            return
        
        if not await verify_user_complete(client, message):
            return
        
        # Check if user already has active task
        if await db.is_user_task_running(user_id):
            return await message.reply_text(
                config.MSG_TASK_IN_PROGRESS, 
                quote=True
            )
        
        try:
            settings = await db.get_user_settings(user_id)
            active_tool = settings.get("active_tool")
        except Exception as e:
            logger.error(f"Failed to get settings in process_handler: {e}")
            return await message.reply_text(
                "❌ Could not retrieve your settings."
            )
        
        # Check if merge tool is active
        if active_tool != 'merge':
            return await message.reply_text(
                "❌ Please enable **Merge** tool first!\n\nUse: `/vt` → 🎬 Merge Videos",
                quote=True
            )
        
        # Import queue manager
        from modules.queue_manager import queue_manager
        
        # Check if files in queue
        if not queue_manager.has_queue(user_id) or queue_manager.get_queue_count(user_id) < 2:
            return await message.reply_text(
                "❌ Please add at least 2 files to queue first!\n\nSend files one by one.",
                quote=True
            )
        
        # Check bot state
        if not bot_state.is_bot_active() and user_id not in config.ADMINS:
            return await message.reply_text(
                config.MSG_BOT_ON_HOLD, 
                quote=True
            )
        
        # Check user hold state
        if settings.get("is_on_hold", False):
            return await message.reply_text(
                config.MSG_USER_ON_HOLD, 
                quote=True
            )
        
        # Create task in database
        task_id = await db.create_task(user_id, active_tool, "telegram_files")
        
        if not task_id:
            return await message.reply_text("❌ Error creating task in database.")
        
        # Get queued files
        queue_items = queue_manager.get_queue(user_id)
        messages_to_merge = [item['message'] for item in queue_items]
        
        # Clear queue
        queue_manager.clear_queue(user_id)
        
        # Start merge task
        await start_merge_task(
            client, message, messages_to_merge, user_id, task_id, settings
        )

    @app.on_message(
        (filters.video | filters.document | filters.audio | filters.text)
        & filters.group
        & ~filters.media_group
        & ~filters.regex(r'^/')
    )
    async def file_handler(client: Client, message: Message):
        """Handle file uploads and URL inputs"""
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        if not await is_authorized_user(user_id, chat_id):
            return
        
        if not await verify_user_complete(client, message):
            return
        
        # Check if user already has active task
        if await db.is_user_task_running(user_id):
            return await message.reply_text(
                config.MSG_TASK_IN_PROGRESS, 
                quote=True
            )
        
        try:
            settings = await db.get_user_settings(user_id)
            active_tool = settings.get("active_tool")
            download_mode = settings.get("download_mode")
        except Exception as e:
            logger.error(f"Failed to get settings in file_handler: {e}")
            return await message.reply_text(
                "❌ Could not retrieve your settings."
            )
        
        # Check bot state
        if not bot_state.is_bot_active() and user_id not in config.ADMINS:
            return await message.reply_text(
                config.MSG_BOT_ON_HOLD, 
                quote=True
            )
        
        # Check user hold state
        if settings.get("is_on_hold", False):
            return await message.reply_text(
                config.MSG_USER_ON_HOLD, 
                quote=True
            )
        
        # Check if tool is selected
        if not active_tool or active_tool == "none":
            return await message.reply_text(
                config.MSG_SELECT_TOOL_FIRST, 
                quote=True
            )
        
        # Determine input type
        is_url = bool(message.text and is_valid_url(message.text))
        is_tg_file = bool(message.video or message.document or message.audio)
        
        # Validate input matches download mode
        if download_mode == "url" and is_tg_file:
            return await message.reply_text(
                "❌ Download mode is set to **URL**, but you sent a file.\n\nChange mode in: /us",
                quote=True
            )
        
        if download_mode == "telegram" and is_url:
            return await message.reply_text(
                "❌ Download mode is set to **Telegram**, but you sent a URL.\n\nChange mode in: /us",
                quote=True
            )
        
        # Validate input is valid
        if not is_url and not is_tg_file:
            if message.text:
                return
            return await message.reply_text(
                "❌ Invalid input. Please send a file or a valid URL.",
                quote=True
            )
        
        # Handle merge tool (requires queue)
        if active_tool == 'merge':
            if download_mode == 'url':
                return await message.reply_text(
                    "❌ Merge tool doesn't support URL mode.\n\nChange to **Telegram** mode in: /us",
                    quote=True
                )
            
            from modules.queue_manager import queue_manager
            
            file_info = {
                'message': message,
                'filename': getattr(
                    message.video or message.document or message.audio,
                    'file_name',
                    'Unknown'
                ),
                'file_size': getattr(
                    message.video or message.document or message.audio,
                    'file_size',
                    0
                )
            }
            
            count = queue_manager.add_to_queue(user_id, file_info)
            
            queue_msg = queue_manager.format_queue_message(
                user_id,
                user_name=message.from_user.first_name,
                title="Merge Queue"
            )
            
            keyboard = queue_manager.get_queue_keyboard(user_id)
            
            return await message.reply_text(
                queue_msg,
                reply_markup=keyboard,
                quote=True
            )
        
        # For other tools, create task immediately
        input_source = "url" if is_url else "telegram_file"
        
        task_id = await db.create_task(user_id, active_tool, input_source)
        
        if not task_id:
            return await message.reply_text(
                "❌ Error creating task in database."
            )
        
        # Start processing task
        await start_processing_task(client, message, user_id, task_id, settings)

    logger.info("✅ Task handlers registered successfully")


# ===================================================================
# CORE PROCESSING FUNCTIONS
# ===================================================================

async def start_merge_task(
    client: Client,
    trigger_message: Message,
    messages_to_merge: list,
    user_id: int,
    task_id: str,
    settings: dict
):
    """Manages the merge task lifecycle"""
    
    status_message = None
    log_message_id = None
    user = trigger_message.from_user
    user_download_dir = os.path.join(config.DOWNLOAD_DIR, str(user_id), task_id)
    output_file_path = None
    downloaded_files = []
    
    cancel_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            config.BTN_CANCEL,
            callback_data=f"task_cancel:{task_id}"
        )
    ]])
    
    try:
        # Update task status
        await db.update_task(task_id, {"status": "starting"})
        
        # Send initial message
        status_message = await trigger_message.reply_text(
            config.MSG_TASK_ACCEPTED.format(
                task_id=task_id,
                count=len(messages_to_merge)
            ),
            quote=True,
            reply_markup=cancel_markup
        )
        
        # Create task log
        log_message_id = await log_manager.create_task_log(
            client, user, settings, task_id
        )
        
        # Download files
        await db.update_task(task_id, {"status": "downloading"})
        await log_manager.send_stage_notification(
            client, task_id, "Download Started",
            f"{len(messages_to_merge)} files"
        )
        await log_manager.update_task_log(
            client, log_message_id, "Downloading files..."
        )
        
        for i, msg in enumerate(messages_to_merge):
            file_num = i + 1
            
            await status_message.edit_text(
                f"⏳ **Downloading Files**\n\n"
                f"File: {file_num}/{len(messages_to_merge)}\n"
                f"Task ID: `{task_id}`",
                reply_markup=cancel_markup
            )
            
            download_path = await download_from_tg(
                client, msg, user_id, task_id, status_message,
                log_manager, log_message_id, cancel_markup=cancel_markup
            )
            
            if not download_path:
                raise Exception(f"File {file_num} download failed.")
            
            downloaded_files.append(download_path)
        
        # Process files
        await db.update_task(task_id, {"status": "processing"})
        await log_manager.send_stage_notification(
            client, task_id, "Processing Started"
        )
        await log_manager.update_task_log(
            client, log_message_id, "Processing..."
        )
        
        output_file_path = await processor.process_task(
            client, user_id, task_id, downloaded_files,
            status_message, log_message_id
        )
        
        if not output_file_path:
            raise Exception("Processing failed. Check status message for error.")
        
        # Prepare for upload
        await log_manager.update_task_log(
            client, log_message_id, "Preparing filename"
        )
        
        default_filename = os.path.basename(output_file_path).rsplit('.', 1)[0]
        custom_filename = settings.get('custom_filename', default_filename) or default_filename
        custom_filename = custom_filename.strip().replace('/', '_')
        
        # Upload
        await log_manager.update_task_log(
            client, log_message_id, "Preparing upload"
        )
        
        file_size = os.path.getsize(output_file_path)
        upload_choice = settings.get('upload_mode', 'telegram')
        
        # Force GoFile if file too large
        if upload_choice == 'telegram' and file_size > config.MAX_TG_UPLOAD_SIZE_BYTES:
            await status_message.edit_text(
                f"⚠️ File size ({get_human_readable_size(file_size)}) exceeds Telegram limit.\n\n"
                f"Uploading to **GoFile** instead...",
                reply_markup=cancel_markup
            )
            upload_choice = "gofile"
        
        # Update database
        await db.update_task(
            task_id,
            {"status": "uploading", "upload_target": upload_choice}
        )
        await log_manager.send_stage_notification(
            client, task_id, "Upload Started",
            f"to {upload_choice}"
        )
        await log_manager.update_task_log(
            client, log_message_id,
            f"Uploading to {upload_choice}"
        )
        
        # Upload to selected service
        if upload_choice == "gofile":
            gofile = GofileUploader(
                user_id, task_id, status_message,
                log_manager, log_message_id, client, cancel_markup
            )
            gofile_link = await gofile.upload_file(output_file_path, custom_filename)
            
            await status_message.delete()
            
            final_text = config.MSG_UPLOAD_COMPLETE_GOFILE.format(
                task_id=task_id,
                user_mention=user.mention,
                link=gofile_link
            )
            
            await client.send_message(
                trigger_message.chat.id,
                final_text,
                disable_web_page_preview=True
            )
            
            await log_manager.finish_task_log(
                client, log_message_id, "Complete",
                file_size, gofile_link, task_id
            )
        
        else:  # Telegram upload
            await log_manager.update_task_log(
                client, log_message_id, "Downloading thumbnail"
            )
            
            thumb_path = None
            saved_thumb_id = settings.get("custom_thumbnail")
            
            if saved_thumb_id:
                thumb_path = await client.download_media(
                    saved_thumb_id,
                    file_name=os.path.join(user_download_dir, "thumb.jpg")
                )
            
            success, final_size = await upload_to_telegram(
                client, user, trigger_message.chat.id,
                output_file_path, status_message, thumb_path,
                custom_filename, settings, log_manager,
                log_message_id, task_id, cancel_markup
            )
            
            if not success:
                raise Exception("Telegram upload failed")
            
            await log_manager.finish_task_log(
                client, log_message_id, "Complete",
                final_size, None, task_id
            )
        
        # Mark task as completed
        await db.update_task(task_id, {"status": "completed"})
        
    except Exception as e:
        logger.error(f"Merge task {task_id} error: {e}", exc_info=True)
        
        await db.update_task(
            task_id,
            {"status": "failed", "error_msg": str(e)}
        )
        
        if status_message and "Processing failed" not in str(e):
            try:
                await status_message.edit_text(
                    config.MSG_TASK_FAILED.format(task_id=task_id, error=e),
                    reply_markup=None
                )
            except:
                pass
        
        if log_message_id:
            await log_manager.finish_task_log(
                client, log_message_id,
                f"Failed: {str(e)}", 0, None, task_id
            )
    
    finally:
        await log_manager.cleanup_task_context(task_id)
        await cleanup_files(user_download_dir)


async def start_processing_task(
    client: Client,
    message: Message,
    user_id: int,
    task_id: str,
    settings: dict
):
    """Manages the standard (single file) task lifecycle"""
    
    status_message = None
    log_message_id = None
    user = message.from_user
    user_download_dir = os.path.join(config.DOWNLOAD_DIR, str(user_id), task_id)
    output_file_path = None
    downloaded_files = []
    
    cancel_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            config.BTN_CANCEL,
            callback_data=f"task_cancel:{task_id}"
        )
    ]])
    
    try:
        # Update task status
        await db.update_task(task_id, {"status": "starting"})
        
        # Send initial message
        status_message = await message.reply_text(
            config.MSG_TASK_ACCEPTED_SINGLE.format(
                task_id=task_id,
                tool=settings['active_tool'].upper()
            ),
            quote=True,
            reply_markup=cancel_markup
        )
        
        # Create task log
        log_message_id = await log_manager.create_task_log(
            client, user, settings, task_id
        )
        
        # Download file
        await db.update_task(task_id, {"status": "downloading"})
        await log_manager.send_stage_notification(
            client, task_id, "Download Started"
        )
        await log_manager.update_task_log(
            client, log_message_id, "Initializing download"
        )
        
        downloader = None
        download_path = None
        
        if settings['download_mode'] == 'url':
            downloader = YTDLDownloader(
                user_id, task_id, status_message,
                log_manager, log_message_id, client, cancel_markup
            )
            download_path = await downloader.download(message.text)
        else:
            download_path = await download_from_tg(
                client, message, user_id, task_id, status_message,
                log_manager, log_message_id, cancel_markup=cancel_markup
            )
        
        if not download_path:
            raise Exception("File download failed.")
        
        downloaded_files.append(download_path)
        
        # Process file
        await db.update_task(task_id, {"status": "processing"})
        await log_manager.send_stage_notification(
            client, task_id, "Processing Started"
        )
        await log_manager.update_task_log(
            client, log_message_id, "Processing..."
        )
        
        output_file_path = await processor.process_task(
            client, user_id, task_id, downloaded_files,
            status_message, log_message_id
        )
        
        if not output_file_path:
            if settings['active_tool'] == 'mediainfo':
                await log_manager.finish_task_log(
                    client, log_message_id, "Complete (MediaInfo)",
                    0, None, task_id
                )
                await db.update_task(task_id, {"status": "completed"})
                return
            else:
                raise Exception("Processing failed. Check status message for error.")
        
        # Prepare for upload
        await log_manager.update_task_log(
            client, log_message_id, "Preparing filename"
        )
        
        default_filename = os.path.basename(output_file_path).rsplit('.', 1)[0]
        custom_filename = settings.get('custom_filename', default_filename) or default_filename
        custom_filename = custom_filename.strip().replace('/', '_')
        
        # Add suffix for encode tool
        active_tool = settings.get('active_tool')
        if active_tool == 'encode':
            suffix = settings.get('encode_settings', {}).get('suffix', '')
            if suffix:
                custom_filename = f"{custom_filename} {suffix}"
        
        # Upload
        await log_manager.update_task_log(
            client, log_message_id, "Preparing upload"
        )
        
        file_size = os.path.getsize(output_file_path)
        upload_choice = settings.get('upload_mode', 'telegram')
        
        # Force GoFile if file too large
        if upload_choice == 'telegram' and file_size > config.MAX_TG_UPLOAD_SIZE_BYTES:
            await status_message.edit_text(
                f"⚠️ File size ({get_human_readable_size(file_size)}) exceeds Telegram limit.\n\n"
                f"Uploading to **GoFile** instead...",
                reply_markup=cancel_markup
            )
            upload_choice = "gofile"
        
        # Update database
        await db.update_task(
            task_id,
            {"status": "uploading", "upload_target": upload_choice}
        )
        await log_manager.send_stage_notification(
            client, task_id, "Upload Started",
            f"to {upload_choice}"
        )
        await log_manager.update_task_log(
            client, log_message_id,
            f"Uploading to {upload_choice}"
        )
        
        # Upload to selected service
        if upload_choice == "gofile":
            gofile = GofileUploader(
                user_id, task_id, status_message,
                log_manager, log_message_id, client, cancel_markup
            )
            gofile_link = await gofile.upload_file(output_file_path, custom_filename)
            
            await status_message.delete()
            
            final_text = config.MSG_UPLOAD_COMPLETE_GOFILE.format(
                task_id=task_id,
                user_mention=user.mention,
                link=gofile_link
            )
            
            await client.send_message(
                message.chat.id,
                final_text,
                disable_web_page_preview=True
            )
            
            await log_manager.finish_task_log(
                client, log_message_id, "Complete",
                file_size, gofile_link, task_id
            )
        
        else:  # Telegram upload
            await log_manager.update_task_log(
                client, log_message_id, "Downloading thumbnail"
            )
            
            thumb_path = None
            saved_thumb_id = settings.get("custom_thumbnail")
            
            if saved_thumb_id:
                thumb_path = await client.download_media(
                    saved_thumb_id,
                    file_name=os.path.join(user_download_dir, "thumb.jpg")
                )
            
            success, final_size = await upload_to_telegram(
                client, user, message.chat.id,
                output_file_path, status_message, thumb_path,
                custom_filename, settings, log_manager,
                log_message_id, task_id, cancel_markup
            )
            
            if not success:
                raise Exception("Telegram upload failed")
            
            await log_manager.finish_task_log(
                client, log_message_id, "Complete",
                final_size, None, task_id
            )
        
        # Mark task as completed
        await db.update_task(task_id, {"status": "completed"})
        
    except Exception as e:
        logger.error(f"Processing task {task_id} error: {e}", exc_info=True)
        
        await db.update_task(
            task_id,
            {"status": "failed", "error_msg": str(e)}
        )
        
        if status_message and "Processing failed" not in str(e):
            try:
                await status_message.edit_text(
                    config.MSG_TASK_FAILED.format(task_id=task_id, error=e),
                    reply_markup=None
                )
            except:
                pass
        
        if log_message_id:
            await log_manager.finish_task_log(
                client, log_message_id,
                f"Failed: {str(e)}", 0, None, task_id
            )
    
    finally:
        await log_manager.cleanup_task_context(task_id)
        await cleanup_files(user_download_dir)
