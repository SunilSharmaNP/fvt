# modules/downloader.py (v5.2)
# MODIFIED based on user's 24-point plan and downloader (12).py:
# 1. Integrated Gofile.io logic from `downloader (12).py` (Plan Point 10).
# 2. Added imports: requests, sha256, json, urlparse.
# 3. Added helper functions for Gofile: `handle_gofile_url`, `__get_token`, `__fetch_links`.
# 4. Modified `YTDLDownloader.download` to:
#    - Detect 'gofile.io' links.
#    - Run `handle_gofile_url` in a thread to get direct link & headers.
#    - Pass the direct link and headers to yt-dlp for downloading.
#    - Fallback to normal yt-dlp for all other links.
# 5. Kept existing `download_from_tg` and inline cancel button support.

import os
import time
import logging
import asyncio
from config import config
from modules.utils import get_human_readable_size, get_progress_bar, cleanup_files
from modules.log_manager import update_task_log
from modules.database import db
from pyrogram.errors import FloodWait, MessageNotModified
from yt_dlp import YoutubeDL, DownloadError

# --- Imports for Gofile (from downloader (12).py) ---
import requests
import json
from hashlib import sha256
from urllib.parse import urlparse
from functools import partial

logger = logging.getLogger(__name__)

# --- Gofile.io Configuration (from downloader (12).py) ---
GOFILE_API_URL = "https://api.gofile.io"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
PASSWORD_ERROR_MESSAGE = "ERROR: Password is required for this link\n\nUse: {link} password"

class DirectDownloadLinkException(Exception):
    pass

# --- Gofile Helper Functions (from downloader (12).py) ---
# NOTE: These are SYNCHRONOUS and must be run in a thread

def __get_token(session):
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "*/*",
        "Connection": "keep-alive",
    }
    __url = f"{GOFILE_API_URL}/accounts"
    try:
        __res = session.post(__url, headers=headers).json()
        if __res["status"] != "ok":
            raise DirectDownloadLinkException("ERROR: Failed to get token.")
        return __res["data"]["token"]
    except Exception as e:
        raise e

def __fetch_links(session, _id, token, _password, details, folderPath=""):
    _url = f"{GOFILE_API_URL}/contents/{_id}?wt=4fd6sg89d7s6&cache=true"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "*/*",
        "Connection": "keep-alive",
        "Authorization": "Bearer" + " " + token,
    }
    if _password:
        _url += f"&password={_password}"
    try:
        _json = session.get(_url, headers=headers).json()
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")
    
    if _json["status"] == "error-passwordRequired":
        raise DirectDownloadLinkException("ERROR: Password is required for this link.")
    if _json["status"] == "error-passwordWrong":
        raise DirectDownloadLinkException("ERROR: This password is wrong!")
    if _json["status"] == "error-notFound":
        raise DirectDownloadLinkException("ERROR: File not found on gofile's server")
    if _json["status"] == "error-notPublic":
        raise DirectDownloadLinkException("ERROR: This folder is not public")
    if _json["status"] != "ok":
         raise DirectDownloadLinkException(f"ERROR: Unknown Gofile error ({_json['status']})")

    data = _json["data"]

    if not details["title"]:
        details["title"] = data["name"] if data["type"] == "folder" else _id

    contents = data.get("children", {})
    if not contents and data.get("type") == "file": # Handle direct file link
        contents = {_id: data}
    elif not contents and data.get("type") == "folder": # Empty folder
        return

    for content in contents.values():
        if content["type"] == "folder":
            if not content.get("public", True): # Assume public if key missing
                continue
            newFolderPath = os.path.join(folderPath, content["name"])
            __fetch_links(session, content["id"], token, _password, details, newFolderPath)
        else:
            item = {
                "filename": content["name"],
                "url": content["link"],
            }
            if "size" in content:
                size = content["size"]
                if isinstance(size, str) and size.isdigit():
                    size = float(size)
                details["total_size"] += size
            details["contents"].append(item)

def handle_gofile_url(url: str, password: str = None) -> tuple:
    """
    Handle gofile.io URLs and return (direct_download_link, headers_string).
    Based on the provided gofile function.
    """
    try:
        _password = sha256(password.encode("utf-8")).hexdigest() if password else ""
        _id = url.split("/")[-1]
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: Invalid Gofile URL format. {e.__class__.__name__}")

    details = {"contents": [], "title": "", "total_size": 0}
    with requests.Session() as session:
        try:
            token = __get_token(session)
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: Failed to get Gofile token: {e.__class__.__name__}")
        
        details["header"] = f"Cookie: accountToken={token}"
        
        try:
            __fetch_links(session, _id, token, _password, details)
        except Exception as e:
            raise e # Re-raise error from __fetch_links

    if len(details["contents"]) == 1:
        return (details["contents"][0]["url"], details["header"])
    elif len(details["contents"]) > 1:
        logger.warning(f"Gofile link has multiple files. Downloading the first one: {details['contents'][0]['filename']}")
        return (details["contents"][0]["url"], details["header"])
    else:
        raise DirectDownloadLinkException("No downloadable content found in gofile link")


# --- Telegram Downloader (v5.1) ---

async def download_from_tg(
    client, 
    message, 
    user_id: int,
    task_id: str,
    status_message,
    log_manager,
    log_message_id,
    cancel_markup=None
):
    """
    Downloads a file from Telegram with real-time progress.
    """
    file_obj = message.video or message.document or message.audio
    if not file_obj:
        raise ValueError("This message does not contain a downloadable file.")
        
    file_name = file_obj.file_name or "file.mkv"
    file_size = file_obj.file_size
    
    user_download_dir = os.path.join(config.DOWNLOAD_DIR, str(user_id), task_id)
    os.makedirs(user_download_dir, exist_ok=True)
    dest_path = os.path.join(user_download_dir, file_name)
    
    start_time = time.time()
    last_update_time = 0

    async def progress_callback(current, total):
        nonlocal last_update_time
        
        if not await db.is_user_task_running(user_id):
            logger.warning(f"Task {task_id} not found, cancelling TG download.")
            raise asyncio.CancelledError("Task cancelled by user.")
            
        now = time.time()
        if (now - last_update_time) < config.PROCESS_POLL_INTERVAL_S:
            return
            
        last_update_time = now
        
        percentage = (current / total) * 100 if total > 0 else 0
        elapsed = now - start_time
        speed = current / elapsed if elapsed > 0 else 0
        eta = ((total - current) / speed) if speed > 0 else 0
        
        from modules.progress_ui import ProgressUI
        user = message.from_user
        
        message_text = ProgressUI.format_progress_message(
            title=file_name,
            status="Download from Telegram",
            processed=current,
            total=total,
            percentage=percentage,
            speed=int(speed),
            eta=int(eta),
            elapsed=int(elapsed),
            engine="Pyrogram",
            mode="#Leech",
            user_name=user.first_name or "User",
            user_id=user_id,
            cancel_data=f"cancel_{task_id}"
        )
        
        progress_data = {
            "progress": percentage / 100,
            "downloaded": get_human_readable_size(current),
            "total_size": get_human_readable_size(total),
            "speed": f"{get_human_readable_size(speed)}/s",
            "eta": time.strftime('%H:%M:%S', time.gmtime(eta))
        }
        
        try:
            await status_message.edit_text(
                message_text,
                reply_markup=cancel_markup
            )
        except MessageNotModified:
            pass
            
        await log_manager.update_task_log(
            client, 
            log_message_id, 
            "Downloading (TG)",
            progress_data
        )

    try:
        logger.info(f"Downloading {file_name} from Telegram for task {task_id}")
        
        file_path = await client.download_media(
            message=message,
            file_name=dest_path,
            progress=progress_callback
        )
        
        if not file_path or not os.path.exists(dest_path):
            raise Exception("File not found after download.")
            
        return dest_path

    except asyncio.CancelledError:
        logger.info(f"TG Download cancelled for {task_id}")
        cleanup_files(user_download_dir)
        raise
    except FloodWait as e:
        logger.warning(f"FloodWait of {e.value}s during TG download.")
        await asyncio.sleep(e.value)
        return await download_from_tg(client, message, user_id, task_id, status_message, log_manager, log_message_id, cancel_markup)
    except Exception as e:
        logger.error(f"Failed to download from TG: {e}", exc_info=True)
        cleanup_files(user_download_dir)
        raise

# --- URL Downloader (yt-dlp) - MODIFIED for Gofile ---

class YTDLDownloader:
    def __init__(self, user_id: int, task_id: str, status_message, log_manager, log_message_id, client, cancel_markup=None):
        self.user_id = user_id
        self.task_id = task_id
        self.status_message = status_message
        self.log_manager = log_manager
        self.log_message_id = log_message_id
        self.client = client
        self.start_time = time.time()
        self.last_update_time = 0
        self.user_download_dir = os.path.join(config.DOWNLOAD_DIR, str(user_id), task_id)
        self.cancel_markup = cancel_markup
        os.makedirs(self.user_download_dir, exist_ok=True)

    def progress_hook(self, d):
        """yt-dlp progress hook."""
        
        # Check if task is still running (sync version - will use db check in async context)
        # For now, we'll skip this check since it needs async context
        # The task cancellation will be handled by the main task management system
            
        if d['status'] == 'downloading':
            now = time.time()
            if (now - self.last_update_time) < config.PROCESS_POLL_INTERVAL_S:
                return
            
            self.last_update_time = now
            
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)
            speed = d.get('speed', 0) or 0
            eta = d.get('eta', 0) or 0
            
            progress = downloaded / total if total > 0 else 0
            filename = d.get('filename', 'file').split(os.sep)[-1]
            
            progress_data = {
                "progress": progress,
                "downloaded": get_human_readable_size(downloaded),
                "total_size": get_human_readable_size(total),
                "speed": f"{get_human_readable_size(speed)}/s",
                "eta": time.strftime('%H:%M:%S', time.gmtime(eta)),
                "downloaded_bytes": downloaded,
                "total_bytes": total,
                "speed_numeric": speed,
                "eta_seconds": eta,
                "elapsed": now - self.start_time
            }
            
            asyncio.run_coroutine_threadsafe(
                self.update_progress_messages(filename, progress_data),
                self.client.loop
            )
            
        elif d['status'] == 'finished':
            logger.info(f"Finished downloading for task {self.task_id}. Now post-processing...")
            
    async def update_progress_messages(self, filename: str, data: dict):
        """Async helper to edit messages from sync hook - Now uses ProgressUI theme."""
        from modules.progress_ui import ProgressUI
        
        user = self.status_message.from_user
        percentage = data['progress'] * 100
        
        message_text = ProgressUI.format_progress_message(
            title=filename,
            status="Download from URL",
            processed=data.get('downloaded_bytes', 0),
            total=data.get('total_bytes', 1),
            percentage=percentage,
            speed=int(data.get('speed_numeric', 0)),
            eta=int(data.get('eta_seconds', 0)),
            elapsed=int(data.get('elapsed', 0)),
            engine="yt-dlp",
            mode="#Leech",
            user_name=user.first_name or "User",
            user_id=user.id,
            cancel_data=f"cancel_{self.task_id}"
        )
        
        try:
            await self.status_message.edit_text(
                message_text,
                reply_markup=self.cancel_markup
            )
        except MessageNotModified:
            pass
            
        await self.log_manager.update_task_log(
            self.client, 
            self.log_message_id, 
            "Downloading (URL)",
            data
        )

    async def download(self, url: str) -> str:
        """
        Runs the yt-dlp download in a separate thread.
        MODIFIED: Now handles Gofile links before falling back to yt-dlp.
        """
        
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': os.path.join(self.user_download_dir, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'nocheckcertificate': True,
            'logtostderr': False,
            'quiet': True,
            'progress_hooks': [self.progress_hook],
            'postprocessor_args': [
                '-movflags', 'faststart'
            ],
            'retries': 5,
            'fragment_retries': 5,
        }
        
        download_url = url
        
        # --- MODIFIED: Gofile Logic ---
        try:
            parsed_url = urlparse(url)
            if 'gofile.io' in parsed_url.netloc:
                await self.status_message.edit_text(
                    "🔍 **Processing Gofile.io link...**\n\n"
                    f"Task ID: `{self.task_id}`",
                    reply_markup=self.cancel_markup
                )
                
                loop = asyncio.get_event_loop()
                # Run synchronous `handle_gofile_url` in a thread
                gofile_func = partial(handle_gofile_url, url, None) # No password support for now
                direct_url, headers_str = await loop.run_in_executor(None, gofile_func)
                
                download_url = direct_url # Use the direct link
                
                # Add headers to ydl_opts for Gofile
                # yt-dlp http_headers option
                ydl_opts['http_headers'] = {
                    "User-Agent": USER_AGENT,
                    "Cookie": headers_str.split(": ")[1] # Extract cookie value
                }
                
                await self.status_message.edit_text(
                    f"✅ **Gofile.io link processed!**\n\n"
                    f"Starting download...\nTask ID: `{self.task_id}`",
                    reply_markup=self.cancel_markup
                )
        except Exception as e:
            logger.error(f"Failed to process Gofile link: {e}", exc_info=True)
            raise Exception(f"Gofile.io Error: {str(e)}")
        # --- End Gofile Logic ---

        try:
            logger.info(f"Downloading from URL: {download_url} for task {self.task_id}")
            
            loop = asyncio.get_event_loop()
            with YoutubeDL(ydl_opts) as ydl:
                info = await loop.run_in_executor(
                    None,
                    lambda: ydl.extract_info(download_url, download=False)
                )
                
                filename = ydl.prepare_filename(info)
                
                await loop.run_in_executor(
                    None,
                    lambda: ydl.download([download_url])
                )
            
            if not os.path.exists(filename):
                # Handle cases where yt-dlp merges and creates a different extension
                base_fn = os.path.splitext(filename)[0]
                possible_files = [f for f in os.listdir(self.user_download_dir) if f.startswith(os.path.basename(base_fn))]
                if possible_files:
                    filename = os.path.join(self.user_download_dir, possible_files[0])
                    logger.warning(f"yt-dlp output file was {filename}")
                else:
                    raise Exception(f"File not found after yt-dlp download: {filename}")
            
            return filename

        except DownloadError as e:
            logger.info(f"URL Download cancelled or failed for {self.task_id}: {e}")
            cleanup_files(self.user_download_dir)
            if "Task cancelled" in str(e):
                raise asyncio.CancelledError("Task cancelled by user.")
            raise Exception(f"Failed to download from URL: {e}")
        except Exception as e:
            logger.error(f"Failed to download from URL: {e}", exc_info=True)
            cleanup_files(self.user_download_dir)
            raise
