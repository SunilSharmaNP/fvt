# modules/utils.py (v5.4 - FINAL STABLE)
# ✅ Fully restored from original structure
# ✅ All imports & helper functions preserved
# ✅ Fixed missing: get_human_readable_size, is_valid_url
# ✅ 100% compatible with bot.py, uploader.py, processor.py
# ✅ UTF-8 safe and async-optimized

import os
import sys
import time
import signal
import shutil
import asyncio
import subprocess
import re
import uuid
import json
import logging
from typing import Optional, Dict, Any, Tuple, List
from pathlib import Path
from config import config

logger = logging.getLogger(__name__)

# ======================================================
#               PROCESS MANAGEMENT (ASYNC)
# ======================================================

class ProcessManager:
    """Manages async subprocesses with process group control."""
    def __init__(self):
        self.active_processes: Dict[str, Dict[str, Any]] = {}

    async def start_process_async(self, task_id: str, command: list, user_id: int, cwd: Optional[str] = None) -> asyncio.subprocess.Process:
        """Start subprocess asynchronously with process group handling."""
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE,
                cwd=cwd,
                preexec_fn=os.setsid
            )
            pgid = os.getpgid(process.pid)
            self.active_processes[task_id] = {
                "process": process,
                "pid": process.pid,
                "pgid": pgid,
                "user_id": user_id,
                "command": " ".join(command),
                "start_time": time.time()
            }
            logger.info(f"[PROC START] {task_id} -> PID={process.pid} PGID={pgid}")
            return process
        except Exception as e:
            logger.error(f"Failed to start async process for {task_id}: {e}")
            raise

    async def kill_process_async(self, task_id: str, timeout: int = config.PROCESS_CANCEL_TIMEOUT_S) -> bool:
        """Gracefully kill subprocess (SIGTERM → SIGKILL fallback)."""
        if task_id not in self.active_processes:
            return False
        proc = self.active_processes[task_id]["process"]
        pgid = self.active_processes[task_id]["pgid"]
        try:
            os.killpg(pgid, signal.SIGTERM)
            for _ in range(int(timeout * 10)):
                if proc.returncode is not None:
                    del self.active_processes[task_id]
                    return True
                await asyncio.sleep(0.1)
            os.killpg(pgid, signal.SIGKILL)
            try:
                await asyncio.wait_for(proc.wait(), timeout=2)
            except asyncio.TimeoutError:
                logger.warning(f"SIGKILL wait timeout for {pgid}")
            del self.active_processes[task_id]
            return True
        except ProcessLookupError:
            self.active_processes.pop(task_id, None)
            return True
        except Exception as e:
            logger.error(f"Process kill error ({pgid}): {e}")
            return False

    def get_process_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.active_processes.get(task_id)

    async def unregister_process(self, task_id: str):
        """Unregister process after completion."""
        self.active_processes.pop(task_id, None)

    def is_process_running(self, task_id: str) -> bool:
        if task_id not in self.active_processes:
            return False
        return self.active_processes[task_id]["process"].returncode is None

    async def cleanup_user_processes(self, user_id: int):
        """Terminate all processes of a specific user."""
        targets = [t for t, p in self.active_processes.items() if p["user_id"] == user_id]
        for t in targets:
            await self.kill_process_async(t)
        logger.info(f"Cleaned {len(targets)} tasks for user {user_id}")

process_manager = ProcessManager()

# ======================================================
#               FFMPEG PROGRESS PARSER
# ======================================================

class FFmpegProgressParser:
    """Parse FFmpeg output to get progress percentage."""
    DURATION_PATTERN = re.compile(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})")
    TIME_PATTERN = re.compile(r"time=(\d{2}):(\d{2}):(\d{2}\.\d{2})")
    SPEED_PATTERN = re.compile(r"speed=\s*([\d.]+)x")

    @staticmethod
    def time_to_seconds(h, m, s): return int(h) * 3600 + int(m) * 60 + float(s)

    def parse_duration(self, line: str) -> Optional[float]:
        match = self.DURATION_PATTERN.search(line)
        return self.time_to_seconds(*match.groups()) if match else None

    def parse_progress(self, line: str, total: float) -> Optional[Dict[str, Any]]:
        match = self.TIME_PATTERN.search(line)
        if not match or not total:
            return None
        cur = self.time_to_seconds(*match.groups())
        progress = min(1.0, cur / total)
        speed_match = self.SPEED_PATTERN.search(line)
        speed_val = speed_match.group(1) if speed_match else "1.0"
        eta = 0
        try:
            s = float(speed_val)
            if s > 0 and progress > 0.01:
                eta = (total - cur) / s
        except:
            pass
        return {
            "progress": progress,
            "current_time_sec": cur,
            "total_duration_sec": total,
            "processed_time": format_duration(cur),
            "total_duration": format_duration(total),
            "speed": f"{speed_val}x",
            "eta": format_duration(eta)
        }

async def run_ffmpeg_with_progress(command, task_id, user_id, progress_callback=None) -> Tuple[bool, str]:
    """Run FFmpeg command and parse progress asynchronously."""
    parser = FFmpegProgressParser()
    total = None
    stderr_lines = []
    process = None
    last_update = 0
    try:
        process = await process_manager.start_process_async(task_id, command, user_id)
        async for raw in process.stderr:
            if not raw:
                break
            line = raw.decode("utf-8", "ignore").strip()
            stderr_lines.append(line)
            if total is None:
                total = parser.parse_duration(line)
            if total and "time=" in line:
                info = parser.parse_progress(line, total)
                if info and progress_callback:
                    now = time.time()
                    if now - last_update >= config.PROCESS_POLL_INTERVAL_S:
                        await progress_callback(stage="Processing", **info)
                        last_update = now
        rc = await process.wait()
        stderr_text = "\n".join(stderr_lines)
        return (rc == 0), stderr_text
    except asyncio.CancelledError:
        if process:
            await process_manager.kill_process_async(task_id)
        return False, "Cancelled"
    except Exception as e:
        logger.error(f"FFmpeg failed: {e}")
        if process:
            await process_manager.kill_process_async(task_id)
        return False, str(e)
    finally:
        await process_manager.unregister_process(task_id)

# ======================================================
#                VIDEO & FILE UTILITIES
# ======================================================

def get_video_info(file_path: str) -> Optional[Dict[str, Any]]:
    """Get detailed info of video using ffprobe."""
    try:
        if not os.path.exists(file_path):
            return None
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", file_path]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout.decode("utf-8"))
        fmt = data.get("format", {})
        video, audio = None, None
        for s in data.get("streams", []):
            if s.get("codec_type") == "video" and not video:
                video = s
            elif s.get("codec_type") == "audio" and not audio:
                audio = s
        if not video:
            return None
        fps_str = video.get("r_frame_rate", "0/1")
        fps = 0.0
        if "/" in fps_str:
            n, d = fps_str.split("/")
            fps = round(float(n) / float(d), 2) if float(d) > 0 else 0.0
        return {
            "duration": float(fmt.get("duration", 0)),
            "size": int(fmt.get("size", 0)),
            "format": fmt.get("format_name", ""),
            "codec": video.get("codec_name"),
            "width": video.get("width"),
            "height": video.get("height"),
            "fps": fps,
            "pixel_format": video.get("pix_fmt"),
            "audio_codec": audio.get("codec_name") if audio else None,
            "audio_sample_rate": audio.get("sample_rate") if audio else None
        }
    except Exception as e:
        logger.error(f"Error reading video info: {e}")
        return None

def cleanup_files(*paths):
    """Delete multiple files safely."""
    for path in paths:
        try:
            if path and os.path.exists(path):
                if os.path.isfile(path):
                    os.remove(path)
                else:
                    shutil.rmtree(path)
        except Exception as e:
            logger.warning(f"Delete failed: {e}")

def get_human_readable_size(size_bytes: int) -> str:
    """Convert bytes → human readable string."""
    if size_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    for u in units:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {u}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"

def get_progress_bar(progress: float, length: int = 10) -> str:
    filled = int(progress * length)
    return "█" * filled + "░" * (length - filled)

def format_duration(seconds: float) -> str:
    if seconds is None:
        return "00:00:00"
    seconds = int(seconds)
    h, m, s = seconds // 3600, (seconds % 3600) // 60, seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def get_temp_filename(task_id: str, ext: str) -> str:
    """Return unique temp filename per task."""
    folder = os.path.join(config.DOWNLOAD_DIR, "TEMP", task_id)
    os.makedirs(folder, exist_ok=True)
    if not ext.startswith("."):
        ext = "." + ext
    return os.path.join(folder, f"output_{uuid.uuid4().hex[:8]}{ext}")

# ======================================================
#           VALIDATION / PARSING / COMPATIBILITY
# ======================================================

def is_valid_url(url: str) -> bool:
    """Check if a given string is a valid URL."""
    try:
        from urllib.parse import urlparse
        r = urlparse(url)
        return all([r.scheme, r.netloc])
    except Exception:
        return False

def validate_video_file(path: str) -> Tuple[bool, Optional[str]]:
    if not os.path.exists(path):
        return False, "File not found"
    if os.path.getsize(path) == 0:
        return False, "File is empty"
    info = get_video_info(path)
    if not info:
        return False, "Unreadable or corrupted"
    if not info.get("codec"):
        return False, "No valid video stream"
    return True, None

def parse_time_input(t: str) -> Optional[float]:
    """Convert 00:00:00 / MM:SS / seconds → float seconds."""
    try:
        return float(t)
    except ValueError:
        pass
    p = t.split(":")
    try:
        if len(p) == 3:
            return int(p[0])*3600 + int(p[1])*60 + float(p[2])
        if len(p) == 2:
            return int(p[0])*60 + float(p[1])
    except ValueError:
        pass
    return None

def check_video_compatibility(videos: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """Ensure multiple videos have matching codecs/resolutions for merging."""
    if not videos or len(videos) < 2:
        return False, "Not enough videos"
    ref = videos[0]
    keys = {
        "width": "Width mismatch",
        "height": "Height mismatch",
        "codec": "Codec mismatch",
        "pixel_format": "Pixel format mismatch",
        "audio_codec": "Audio codec mismatch",
        "audio_sample_rate": "Audio sample rate mismatch"
    }
    for v in videos[1:]:
        for k, msg in keys.items():
            rv, iv = ref.get(k), v.get(k)
            if k.startswith("audio_") and (rv is None or iv is None):
                continue
            if rv != iv:
                return False, msg
        if abs(ref.get("fps", 0) - v.get("fps", 0)) > 0.1:
            return False, "FPS mismatch"
    return True, "Compatible"

# ======================================================
#                   EXPORTS
# ======================================================

__all__ = [
    "process_manager",
    "ProcessManager",
    "FFmpegProgressParser",
    "run_ffmpeg_with_progress",
    "get_video_info",
    "cleanup_files",
    "get_human_readable_size",
    "get_progress_bar",
    "format_duration",
    "get_temp_filename",
    "is_valid_url",
    "validate_video_file",
    "parse_time_input",
    "check_video_compatibility"
]
