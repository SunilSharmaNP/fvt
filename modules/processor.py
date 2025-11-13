# modules/processor.py (v6.5 — VE Encoding Integrated)
# ✅ Integrated VE repo encoding engine
# ✅ Uses ffmpeg.encode_video() instead of hardcoded command
# ✅ Retains all original tools and progress callbacks
# ✅ Compatible with ffmpeg_tools v6.0 + utils v5.4
# ✅ Async-safe and 100% functional

import os
import asyncio
import logging
import json
from typing import Dict, List
from pyrogram.types import Message
from pyrogram.errors import MessageNotModified

from config import config
from modules.database import db
from modules.utils import (run_ffmpeg_with_progress, get_video_info,
                           parse_time_input, get_temp_filename,
                           check_video_compatibility)
import modules.ffmpeg_tools as ffmpeg
import modules.log_manager as log_manager
import modules.media_info as media_info  # <-- ADD THIS
import modules.mediainfo_graph as mediainfo_graph
import shlex  # <-- यह जोड़ें
import os  # <-- यह पहले से होना चाहिए, सुनिश्चित करें
from telegraph.aio import Telegraph  # <-- यह जोड़ें
from telegraph.exceptions import TelegraphException  # <-- Error handling के लिए

logger = logging.getLogger(__name__)

section_dict = {
    "General": "嵐",
    "Video": "時",
    "Audio": "矧",
    "Text": "箱",
    "Menu": "翼"
}


def parseinfo(out, size):
    tc, trigger = "", False
    size_line = (
        f"File size                                 : {size / (1024 * 1024):.2f} MiB"
    )
    for line in out.split("\n"):
        for section, emoji in section_dict.items():
            if line.startswith(section):
                trigger = True
                if not line.startswith("General"):
                    tc += "</pre><br>"
                # 'Text' को 'Subtitle' से बदलें जैसा कि WZML-X करता है
                tc += f"<h4>{emoji} {line.replace('Text', 'Subtitle')}</h4>"
                break
        if line.startswith("File size"):
            line = size_line
        if trigger:
            tc += "<br><pre>"
            trigger = False
        else:
            tc += line + "\n"
    tc += "</pre><br>"
    return tc


# --- एंड WZML-X लॉजिक ---


# ---------------------- PROGRESS CALLBACK ---------------------- #
async def _progress_callback(task_id: str, status_message: Message,
                             log_message_id: int, client, stage: str,
                             **kwargs):
    try:
        progress = kwargs.get('progress', 0)
        speed = kwargs.get('speed', 'N/A')
        eta = kwargs.get('eta', 'N/A')
        text = (f"**⏳ Task `{task_id}`: {stage}...**\n\n"
                f"**Progress:** {int(progress*100)}%\n"
                f"**Speed:** `{speed}` | **ETA:** `{eta}`")
        await status_message.edit_text(text)
        await log_manager.update_task_log(client, log_message_id, stage, {
            "progress": progress,
            "speed": speed,
            "eta": eta
        })
    except MessageNotModified:
        pass
    except Exception as e:
        logger.warning(f"Error updating progress for {task_id}: {e}")


# ---------------------- MERGE ---------------------- #
async def _process_merge(user_id, task_id, downloaded_files, settings,
                         progress_cb):
    output_file = get_temp_filename(task_id, ".mp4")
    mode = settings.get("merge_mode", "video+video")
    logger.info(f"Task {task_id}: Starting merge mode '{mode}'")
    await progress_cb(stage="Merging")

    if mode == "video+video":
        infos = [get_video_info(f) for f in downloaded_files]
        compatible, reason = check_video_compatibility(infos)
        if compatible:
            success, msg = await ffmpeg.merge_videos_simple(
                downloaded_files, output_file, task_id, user_id, progress_cb)
        else:
            logger.warning(f"Incompatible ({reason}), using re-encode.")
            success, msg = await ffmpeg.merge_videos_complex(
                downloaded_files, output_file, task_id, user_id, progress_cb)
        return success, msg, output_file if success else None

    elif mode == "video+audio":
        success, msg = await ffmpeg.merge_video_audio(downloaded_files[0],
                                                      downloaded_files[1],
                                                      output_file, task_id,
                                                      user_id, progress_cb)
        return success, msg, output_file if success else None

    elif mode == "video+subtitle":
        success, msg = await ffmpeg.merge_video_subtitle(
            downloaded_files[0], downloaded_files[1], output_file, task_id,
            user_id, progress_cb)
        return success, msg, output_file if success else None

    else:
        return False, f"Unknown merge mode: {mode}", None


# ---------------------- ENCODE ---------------------- #
async def _process_encode(user_id, task_id, downloaded_files, settings,
                          progress_cb):
    """
    Modern VE-based encoding pipeline
    Uses ffmpeg.encode_video() for consistent CRF, preset, resolution logic.
    """
    input_file = downloaded_files[0]
    output_file = get_temp_filename(task_id, ".mp4")

    # Load user or default encoding settings
    user_defaults = db.get_default_settings(user_id) if hasattr(
        db, "get_default_settings") else {}
    encode_settings = settings.get("encode_settings",
                                   user_defaults.get('encode_settings', {}))

    preset_name = encode_settings.get("preset_name", "default_h264")

    custom_settings = {
        "vcodec": encode_settings.get("vcodec", "libx264"),
        "crf": int(encode_settings.get("crf", 26)),
        "preset": encode_settings.get("preset", "slow"),
        "acodec": encode_settings.get("acodec", "aac"),
        "abitrate": encode_settings.get("abitrate", "128k"),
        "resolution": encode_settings.get("resolution", "source"),
        "custom_resolution": encode_settings.get("custom_resolution", None),
        "two_pass": encode_settings.get("two_pass", False),
        "copy_audio": encode_settings.get("copy_audio", True),
        "maxrate": encode_settings.get("maxrate"),
        "bufsize": encode_settings.get("bufsize")
    }

    logger.info(
        f"[ENCODE] Task {task_id}: Using preset={preset_name} custom={custom_settings}"
    )
    await progress_cb(stage="Encoding")

    try:
        success, msg = await ffmpeg.encode_video(
            input_file=input_file,
            output_file=output_file,
            preset_name=preset_name,
            task_id=task_id,
            user_id=user_id,
            progress_callback=progress_cb,
            custom_settings=custom_settings)
        return success, msg, output_file if success else None
    except FileNotFoundError:
        return False, "FFmpeg not found on system", None
    except Exception as e:
        logger.error(f"Encoding error ({task_id}): {e}", exc_info=True)
        return False, str(e), None


# ---------------------- TRIM ---------------------- #
async def _process_trim(user_id, task_id, downloaded_files, settings,
                        progress_cb):
    input_file = downloaded_files[0]
    output_file = get_temp_filename(task_id, ".mp4")
    trim = settings.get("trim_settings",
                        db.get_default_settings(user_id)['trim_settings'])
    start = parse_time_input(trim.get('start', '00:00:00'))
    end = parse_time_input(trim.get('end', '00:00:30'))
    await progress_cb(stage="Trimming")
    success, msg = await ffmpeg.trim_video(input_file, output_file, start, end,
                                           task_id, user_id, progress_cb)
    return success, msg, output_file if success else None


# ---------------------- SAMPLE ---------------------- #
async def _process_sample(user_id, task_id, downloaded_files, settings,
                          progress_cb):
    input_file = downloaded_files[0]
    output_file = get_temp_filename(task_id, ".mp4")
    sample = settings.get("sample_settings",
                          db.get_default_settings(user_id)['sample_settings'])
    duration = sample.get('duration', 30)
    if isinstance(duration, str):
        try:
            duration = int(duration)
        except:
            duration = 30
    await progress_cb(stage="Generating Sample")
    success, msg = await ffmpeg.generate_sample(
        input_file, output_file, duration, task_id, user_id,
        sample.get('from_point', 'start'), progress_cb)
    return success, msg, output_file if success else None


# ---------------------- MEDIA INFO ---------------------- #
# ---------------------- MEDIA INFO ---------------------- #
async def _process_mediainfo(status_message, task_id, downloaded_files):
    input_file = downloaded_files[0]
    await status_message.edit_text(f"📊 Generating MediaInfo for `{task_id}`..."
                                   )

    try:
        # 1. 'mediainfo' कमांड-लाइन टूल चलाएँ
        command = ['mediainfo', input_file]
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            logger.error(f"MediaInfo CLI failed: {stderr.decode()}")
            raise Exception(f"MediaInfo CLI Error: {stderr.decode()}")

        stdout = stdout.decode().strip()
        if not stdout:
            raise Exception("MediaInfo returned empty output.")

        # 2. फ़ाइल साइज़ प्राप्त करें (WZML-X की तरह)
        file_size = os.path.getsize(input_file)

        # 3. WZML-X के पार्सर का उपयोग करके HTML कंटेंट बनाएँ
        file_name = os.path.basename(input_file)
        html_content = f"<h4>東 {file_name}</h4><br><br>"
        html_content += parseinfo(stdout, file_size)  #

        # 4. Telegraph पेज बनाएँ (telegraph_helper.py की तरह)
        telegraph_obj = Telegraph(domain="graph.org")

        # एक रैंडम अकाउंट बनाएँ, जैसा WZML-X करता है
        try:
            await telegraph_obj.create_account(
                short_name=f"task-{task_id[:8]}", author_name="MediaInfo Bot")
        except Exception as e:
            logger.warning(
                f"Failed to create telegraph account, proceeding: {e}")

        # पेज बनाएँ
        page = await telegraph_obj.create_page(title="MediaInfo X",
                                               html_content=html_content)
        page_url = page['url']

        # 5. यूज़र को फ़ाइनल लिंक भेजें (WZML-X फॉर्मेट)
        final_text = (f"**MediaInfo:**\n\n"
                      f"筐ｲ **Link :** {page_url}")
        await status_message.edit_text(final_text,
                                       disable_web_page_preview=False)

        # यह ज़रूरी है
        return True, "Displayed", None

    except TelegraphException as e:
        logger.error(f"Telegraph error: {e}")
        await status_message.edit_text(f"❌ Telegraph Error: {e}")
        return False, f"Telegraph error: {e}", None
    except Exception as e:
        logger.error(f"MediaInfo error: {e}", exc_info=True)
        await status_message.edit_text(f"❌ MediaInfo (Graph) failed: {e}")
        return False, f"MediaInfo failed: {e}", None


# ---------------------- WATERMARK ---------------------- #
async def _process_watermark(user_id, task_id, downloaded_files, settings,
                             progress_cb):
    input_file = downloaded_files[0]
    output_file = get_temp_filename(task_id, ".mp4")
    wm_settings = settings.get("watermark_settings", {})
    wtype = wm_settings.get("type", "none")
    await progress_cb(stage="Adding Watermark")

    if wtype == "text":
        text = wm_settings.get("text", "")
        position = wm_settings.get("position", "bottom_right")
        return await ffmpeg.add_text_watermark(input_file,
                                               output_file,
                                               text,
                                               task_id,
                                               user_id,
                                               position,
                                               progress_callback=progress_cb)
    elif wtype == "image":
        image_path = wm_settings.get("image_id")
        if not image_path:
            return False, "No watermark image set", None
        position = wm_settings.get("position", "bottom_right")
        opacity = wm_settings.get("opacity", 0.7)
        return await ffmpeg.add_image_watermark(input_file,
                                                output_file,
                                                image_path,
                                                task_id,
                                                user_id,
                                                position,
                                                opacity,
                                                progress_callback=progress_cb)
    else:
        return False, "Watermark type not set or is 'none'", None


# ---------------------- CONVERT ---------------------- #
async def _process_convert(user_id, task_id, downloaded_files, settings,
                           progress_cb):
    input_file = downloaded_files[0]
    output_file = get_temp_filename(task_id, ".mp4")
    upload_mode = settings.get("upload_mode", "telegram")
    await progress_cb(stage="Converting")

    if upload_mode == "telegram":
        success, msg = await ffmpeg.convert_to_video(input_file, output_file,
                                                     task_id, user_id,
                                                     progress_cb)
    else:
        success, msg = await ffmpeg.convert_to_document(
            input_file, output_file, task_id, user_id, progress_cb)
    return success, msg, output_file if success else None


# ---------------------- RENAME ---------------------- #
async def _process_rename(user_id, task_id, downloaded_files, settings,
                          progress_cb):
    import shutil
    input_file = downloaded_files[0]
    new_name = settings.get("custom_filename",
                            "renamed").strip().replace('/',
                                                       '_').replace('\\', '_')
    ext = os.path.splitext(input_file)[1]
    temp_dir = os.path.dirname(get_temp_filename(task_id, ext))
    output_file = os.path.join(temp_dir, f"{new_name}{ext}")
    try:
        shutil.copy2(input_file, output_file)
        return True, f"File renamed to {new_name}{ext}", output_file
    except Exception as e:
        logger.error(f"Rename error: {e}")
        return False, f"Rename failed: {e}", None


# ---------------------- NEW TOOLS ---------------------- #


async def _process_rotate(user_id, task_id, downloaded_files, settings,
                          progress_cb):
    """Rotate video by specified angle."""
    input_file = downloaded_files[0]
    output_file = get_temp_filename(task_id, ".mp4")
    rotate_settings = settings.get(
        "rotate_settings",
        db.get_default_settings(user_id)['rotate_settings'])
    angle = rotate_settings.get('angle', 90)

    await progress_cb(stage="Rotating Video")
    success, msg = await ffmpeg.rotate_video(input_file, output_file, angle,
                                             task_id, user_id, progress_cb)
    return success, msg, output_file if success else None


async def _process_flip(user_id, task_id, downloaded_files, settings,
                        progress_cb):
    """Flip video horizontally or vertically."""
    input_file = downloaded_files[0]
    output_file = get_temp_filename(task_id, ".mp4")
    flip_settings = settings.get(
        "flip_settings",
        db.get_default_settings(user_id)['flip_settings'])
    direction = flip_settings.get('direction', 'horizontal')

    await progress_cb(stage="Flipping Video")
    success, msg = await ffmpeg.flip_video(input_file, output_file, direction,
                                           task_id, user_id, progress_cb)
    return success, msg, output_file if success else None


async def _process_speed(user_id, task_id, downloaded_files, settings,
                         progress_cb):
    """Adjust video playback speed."""
    input_file = downloaded_files[0]
    output_file = get_temp_filename(task_id, ".mp4")
    speed_settings = settings.get(
        "speed_settings",
        db.get_default_settings(user_id)['speed_settings'])
    speed = float(speed_settings.get('speed', 1.0))

    await progress_cb(stage="Adjusting Speed")
    success, msg = await ffmpeg.adjust_video_speed(input_file, output_file,
                                                   speed, task_id, user_id,
                                                   progress_cb)
    return success, msg, output_file if success else None


async def _process_volume(user_id, task_id, downloaded_files, settings,
                          progress_cb):
    """Adjust audio volume."""
    input_file = downloaded_files[0]
    output_file = get_temp_filename(task_id, ".mp4")
    volume_settings = settings.get(
        "volume_settings",
        db.get_default_settings(user_id)['volume_settings'])
    volume = int(volume_settings.get('volume', 100))

    await progress_cb(stage="Adjusting Volume")
    success, msg = await ffmpeg.adjust_audio_volume(input_file, output_file,
                                                    volume, task_id, user_id,
                                                    progress_cb)
    return success, msg, output_file if success else None


async def _process_crop(user_id, task_id, downloaded_files, settings,
                        progress_cb):
    """Crop video to specified aspect ratio."""
    input_file = downloaded_files[0]
    output_file = get_temp_filename(task_id, ".mp4")
    crop_settings = settings.get(
        "crop_settings",
        db.get_default_settings(user_id)['crop_settings'])
    aspect_ratio = crop_settings.get('aspect_ratio', '16:9')

    await progress_cb(stage="Cropping Video")
    success, msg = await ffmpeg.crop_video(input_file, output_file,
                                           aspect_ratio, task_id, user_id,
                                           progress_cb)
    return success, msg, output_file if success else None


async def _process_gif(user_id, task_id, downloaded_files, settings,
                       progress_cb):
    """Convert video to GIF."""
    input_file = downloaded_files[0]
    output_file = get_temp_filename(task_id, ".gif")
    gif_settings = settings.get(
        "gif_settings",
        db.get_default_settings(user_id)['gif_settings'])
    fps = int(gif_settings.get('fps', 10))
    scale = int(gif_settings.get('scale', 480))
    quality = gif_settings.get('quality', 'medium')

    await progress_cb(stage="Converting to GIF")
    success, msg = await ffmpeg.convert_to_gif(input_file, output_file, fps,
                                               scale, quality, task_id,
                                               user_id, progress_cb)
    return success, msg, output_file if success else None


async def _process_reverse(user_id, task_id, downloaded_files, settings,
                           progress_cb):
    """Reverse video playback."""
    input_file = downloaded_files[0]
    output_file = get_temp_filename(task_id, ".mp4")

    await progress_cb(stage="Reversing Video")
    success, msg = await ffmpeg.reverse_video(input_file, output_file, task_id,
                                              user_id, progress_cb)
    return success, msg, output_file if success else None


async def _process_extract_thumb(user_id, task_id, downloaded_files, settings,
                                 progress_cb):
    """Extract thumbnail(s) from video."""
    input_file = downloaded_files[0]
    output_dir = os.path.dirname(get_temp_filename(task_id, ""))
    thumb_settings = settings.get(
        "extract_thumb_settings",
        db.get_default_settings(user_id)['extract_thumb_settings'])
    mode = thumb_settings.get('mode', 'single')
    timestamp = thumb_settings.get('timestamp', '00:00:05')
    count = int(thumb_settings.get('count', 5))

    await progress_cb(stage="Extracting Thumbnails")
    success, msg = await ffmpeg.extract_thumbnails(input_file, output_dir,
                                                   mode, timestamp, count,
                                                   task_id, user_id,
                                                   progress_cb)

    if success and mode == "single":
        output_file = os.path.join(output_dir, f"thumb_{task_id}.jpg")
        return success, msg, output_file
    elif success and mode == "interval":
        output_file = os.path.join(output_dir, f"thumb_{task_id}_001.jpg")
        return success, msg, output_file
    else:
        return success, msg, None


# ---------------------- MAIN ROUTER ---------------------- #
async def process_task(client, user_id, task_id, downloaded_files,
                       status_message, log_message_id):
    try:
        settings = await db.get_user_settings(user_id)
        tool = settings.get("active_tool", "none")
        logger.info(f"Task {task_id}: Processing tool '{tool}'")

        from functools import partial
        cb = partial(_progress_callback, task_id, status_message,
                     log_message_id, client)

        if tool == "merge":
            success, msg, out = await _process_merge(user_id, task_id,
                                                     downloaded_files,
                                                     settings, cb)
        elif tool == "encode":
            success, msg, out = await _process_encode(user_id, task_id,
                                                      downloaded_files,
                                                      settings, cb)
        elif tool == "trim":
            success, msg, out = await _process_trim(user_id, task_id,
                                                    downloaded_files, settings,
                                                    cb)
        elif tool == "sample":
            success, msg, out = await _process_sample(user_id, task_id,
                                                      downloaded_files,
                                                      settings, cb)
        elif tool == "mediainfo":
            success, msg, out = await _process_mediainfo(
                status_message, task_id, downloaded_files)
        elif tool == "watermark":
            success, msg, out = await _process_watermark(
                user_id, task_id, downloaded_files, settings, cb)
        elif tool == "convert":
            success, msg, out = await _process_convert(user_id, task_id,
                                                       downloaded_files,
                                                       settings, cb)
        elif tool == "rename":
            success, msg, out = await _process_rename(user_id, task_id,
                                                      downloaded_files,
                                                      settings, cb)
        elif tool == "rotate":
            success, msg, out = await _process_rotate(user_id, task_id,
                                                      downloaded_files,
                                                      settings, cb)
        elif tool == "flip":
            success, msg, out = await _process_flip(user_id, task_id,
                                                    downloaded_files, settings,
                                                    cb)
        elif tool == "speed":
            success, msg, out = await _process_speed(user_id, task_id,
                                                     downloaded_files,
                                                     settings, cb)
        elif tool == "volume":
            success, msg, out = await _process_volume(user_id, task_id,
                                                      downloaded_files,
                                                      settings, cb)
        elif tool == "crop":
            success, msg, out = await _process_crop(user_id, task_id,
                                                    downloaded_files, settings,
                                                    cb)
        elif tool == "gif":
            success, msg, out = await _process_gif(user_id, task_id,
                                                   downloaded_files, settings,
                                                   cb)
        elif tool == "reverse":
            success, msg, out = await _process_reverse(user_id, task_id,
                                                       downloaded_files,
                                                       settings, cb)
        elif tool == "extract_thumb":
            success, msg, out = await _process_extract_thumb(
                user_id, task_id, downloaded_files, settings, cb)
        else:
            return None

        # ✅ FIX SECTION
        if not success:
            raise Exception(msg)
        elif out is None and tool == "mediainfo":
            logger.info(
                f"Task {task_id}: MediaInfo displayed successfully (no output file)."
            )
            return None
        elif not out:
            raise Exception(msg)

        return out

    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}", exc_info=True)
        # Truncate error message to avoid MESSAGE_TOO_LONG error (Telegram limit: 4096 chars)
        error_msg = str(e)
        if len(error_msg) > 3500:
            error_msg = error_msg[:3500] + "\n\n... (error message truncated)"
        await status_message.edit_text(f"❌ Error: {error_msg}")
        return None
