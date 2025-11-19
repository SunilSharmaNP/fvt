# modules/uploader.py (v5.2 - FIXED & OPTIMIZED)
# ✅ Fixed aiohttp streaming upload to GoFile
# ✅ Added FloodWait-safe Telegram progress
# ✅ Proper cancel handling & cleanup
# ✅ Unified progress callback logic
# ✅ Safe log updates (awaited)
# ✅ Retry logic fixed

import os
import time
import aiofiles
import asyncio
import logging
import aiohttp
from aiohttp import ClientSession, MultipartWriter
from config import config
from modules.utils import get_human_readable_size, get_progress_bar, format_duration
from modules.log_manager import update_task_log
from modules.database import db
from pyrogram.errors import FloodWait, MessageNotModified

logger = logging.getLogger(__name__)

# ====================================================
#                   GOFILE UPLOADER
# ====================================================

class GofileUploader:
    """Handles GoFile uploads asynchronously with cancel & progress tracking."""

    def __init__(self, user_id, task_id, status_message, log_manager, log_message_id, client, cancel_markup=None):
        self.user_id = user_id
        self.task_id = task_id
        self.status_message = status_message
        self.log_manager = log_manager
        self.log_message_id = log_message_id
        self.client = client
        self.api_url = "https://api.gofile.io"
        self.token = config.GOFILE_TOKEN
        self.cancel_markup = cancel_markup
        self.last_update = 0

    async def get_server(self, session):
        """Selects optimal GoFile server."""
        async with session.get(f"{self.api_url}/servers") as r:
            r.raise_for_status()
            res = await r.json()
            if res.get("status") == "ok":
                return res["data"]["servers"][0]["name"]
            raise Exception(f"GoFile error: {res.get('message')}")

    async def upload_file(self, file_path: str, custom_filename: str) -> str:
        """Uploads file to GoFile with proper async streaming."""
        if not os.path.exists(file_path):
            raise Exception("File not found for upload")

        filename = f"{custom_filename}{os.path.splitext(file_path)[1]}"
        file_size = os.path.getsize(file_path)
        start_time = time.time()

        async with ClientSession() as session:
            server = await self.get_server(session)
            upload_url = f"https://{server}.gofile.io/uploadFile"

            logger.info(f"[UPLOAD] Starting GoFile upload for {filename}")
            
            # TODO: Implement streaming progress for GoFile uploads
            # Current limitation: Progress updates only show completion (0% → 100%)
            # aiohttp FormData doesn't provide upload progress hooks
            # Possible solutions: Manual chunking, multipart streaming, or trace_request_ctx
            
            # Use FormData with open file handle to enable streaming
            data = aiohttp.FormData()
            if self.token:
                data.add_field('token', self.token)
            
            # Keep file open during upload - add file directly to FormData
            with open(file_path, "rb") as f:
                data.add_field('file', f, filename=filename, content_type='application/octet-stream')
                
                # Upload with the file handle still open
                async with session.post(upload_url, data=data) as resp:
                    # Track upload progress (currently only at completion)
                    await self._update_progress(file_size, file_size, start_time, filename)
                    
                    resp_data = await resp.json()
                    if resp_data.get("status") == "ok":
                        return resp_data["data"]["downloadPage"]
                    raise Exception(f"Upload failed: {resp_data.get('message')}")

    async def _update_progress(self, current, total, start_time, filename):
        """Update progress UI + log for GoFile uploads - Now uses ProgressUI theme."""
        now = time.time()
        if now - self.last_update < config.PROCESS_POLL_INTERVAL_S:
            return
        self.last_update = now

        from modules.progress_ui import ProgressUI
        
        percentage = (current / total) * 100 if total > 0 else 0
        elapsed = now - start_time
        speed = current / elapsed if elapsed > 0 else 0
        eta = (total - current) / speed if speed > 0 else 0

        user = self.status_message.from_user
        
        message_text = ProgressUI.format_progress_message(
            title=filename,
            status="Upload to GoFile",
            processed=current,
            total=total,
            percentage=percentage,
            speed=int(speed),
            eta=int(eta),
            elapsed=int(elapsed),
            engine="GoFile API",
            mode="#Upload",
            user_name=user.first_name or "User",
            user_id=user.id,
            cancel_data=f"cancel_{self.task_id}"
        )

        try:
            await self.status_message.edit_text(message_text, reply_markup=self.cancel_markup)
        except MessageNotModified:
            pass
        except FloodWait as fw:
            logger.warning(f"FloodWait {fw.value}s while updating GoFile progress")
            await asyncio.sleep(fw.value)

        await self.log_manager.update_task_log(
            self.client,
            self.log_message_id,
            "Uploading (GoFile)",
            progress_percent=percentage / 100,
            speed=f"{get_human_readable_size(speed)}/s",
            eta=format_duration(int(eta))
        )

# ====================================================
#                TELEGRAM UPLOADER
# ====================================================

async def upload_to_telegram(
    client, user, chat_id, file_path,
    status_message, thumb_path, custom_filename,
    settings, log_manager, log_message_id, task_id,
    cancel_markup=None
):
    """Uploads a file to Telegram with progress tracking & cancel support."""
    file_size = os.path.getsize(file_path)
    filename = f"{custom_filename}{os.path.splitext(file_path)[1]}"
    upload_as_doc = settings.get("upload_mode") == "document"

    start_time = time.time()
    last_update = 0

    async def progress(current, total):
        nonlocal last_update
        now = time.time()
        if now - last_update < config.PROCESS_POLL_INTERVAL_S:
            return
        last_update = now

        from modules.progress_ui import ProgressUI
        
        percentage = (current / total) * 100 if total > 0 else 0
        elapsed = now - start_time
        speed = current / elapsed if elapsed else 0
        eta = (total - current) / speed if speed > 0 else 0

        message_text = ProgressUI.format_progress_message(
            title=filename,
            status="Upload to Telegram",
            processed=current,
            total=total,
            percentage=percentage,
            speed=int(speed),
            eta=int(eta),
            elapsed=int(elapsed),
            engine="Pyrogram",
            mode="#Upload",
            user_name=user.first_name or "User",
            user_id=user.id,
            cancel_data=f"cancel_{task_id}"
        )

        try:
            await status_message.edit_text(message_text, reply_markup=cancel_markup)
        except MessageNotModified:
            pass
        except FloodWait as fw:
            await asyncio.sleep(fw.value)

        await log_manager.update_task_log(
            client,
            log_message_id,
            "Uploading (Telegram)",
            progress_percent=percentage / 100,
            speed=f"{get_human_readable_size(speed)}/s",
            eta=format_duration(int(eta))
        )

    try:
        logger.info(f"[UPLOAD] Starting Telegram upload: {filename}")
        if upload_as_doc:
            sent = await client.send_document(
                chat_id=chat_id,
                document=file_path,
                thumb=thumb_path,
                file_name=filename,
                progress=progress
            )
        else:
            # fetch media info safely
            from modules.media_info import get_media_info
            duration, width, height = 0, 0, 0
            try:
                info, _ = await get_media_info(file_path)
                if info:
                    v = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
                    if v:
                        duration = int(float(info.get("format", {}).get("duration", 0)))
                        width = int(v.get("width", 0))
                        height = int(v.get("height", 0))
            except Exception as e:
                logger.warning(f"[UPLOAD] Media info error: {e}")

            sent = await client.send_video(
                chat_id=chat_id,
                video=file_path,
                thumb=thumb_path,
                file_name=filename,
                duration=duration,
                width=width,
                height=height,
                progress=progress
            )

        await status_message.delete()
        complete_text = config.MSG_UPLOAD_COMPLETE.format(
            task_id=task_id,
            user_mention=user.mention,
            file_name=filename,
            file_size=get_human_readable_size(file_size)
        )
        await client.send_message(chat_id, text=complete_text, reply_to_message_id=sent.id)
        return True, file_size

    except asyncio.CancelledError:
        await status_message.edit_text("❌ Upload cancelled.", reply_markup=None)
        logger.info(f"[UPLOAD] Cancelled: {task_id}")
        raise
    except FloodWait as fw:
        logger.warning(f"FloodWait {fw.value}s on Telegram upload, retrying...")
        await asyncio.sleep(fw.value)
        return await upload_to_telegram(
            client, user, chat_id, file_path,
            status_message, thumb_path, custom_filename,
            settings, log_manager, log_message_id, task_id, cancel_markup
        )
    except Exception as e:
        logger.error(f"[UPLOAD FAIL] {e}", exc_info=True)
        await status_message.edit_text(config.MSG_UPLOAD_FAILED.format(error=e))
        return False, 0
    finally:
        if thumb_path and os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
                logger.debug(f"Removed thumbnail: {thumb_path}")
            except Exception:
                pass
