# modules/ffmpeg_tools.py (v6.0 - VE-ported encoding)
# Integrated encoding best-practices from `ve` repo into your bot.
# - CRF/preset controls
# - libx264 / libx265 support
# - audio copy when possible, re-encode otherwise
# - two-pass optional mode for constrained bitrate
# - scaling that preserves aspect and ensures even width/height
# - uses run_ffmpeg_with_progress from modules.utils for progress reporting

import os
import logging
from typing import Optional, Dict, Any, Tuple, List

from modules.utils import (
    run_ffmpeg_with_progress,
    get_video_info,
    get_temp_filename,
    validate_video_file,
    format_duration
)

logger = logging.getLogger(__name__)


# ------------------------
# Encoding presets (can be extended)
# ------------------------
ENCODE_PRESETS = {
    "default_h264": {
        "vcodec": "libx264",
        "crf": 26,
        "preset": "slow",
        "tune": None,
        "profile": "high",
        "pix_fmt": "yuv420p",
        "acodec": "aac",
        "abitrate": "128k",
        "movflags": "+faststart",
    },
    "h265_medium": {
        "vcodec": "libx265",
        "crf": 28,
        "preset": "medium",
        "tune": None,
        "profile": None,
        "pix_fmt": "yuv420p",
        "acodec": "aac",
        "abitrate": "128k",
        "movflags": "+faststart",
    },
    "mobile_480p": {
        "vcodec": "libx264",
        "crf": 28,
        "preset": "fast",
        "tune": "film",
        "profile": "baseline",
        "pix_fmt": "yuv420p",
        "acodec": "aac",
        "abitrate": "96k",
        "movflags": "+faststart",
    }
}


def _scale_filter_for_resolution(resolution: str, custom: Optional[str] = None) -> Optional[str]:
    """
    returns an ffmpeg -vf scale filter string for common resolutions.
    Use scale=-2:HEIGHT to keep aspect and even width
    """
    if not resolution or resolution == "source":
        return None
    if resolution == "1080p":
        return "scale=-2:1080"
    if resolution == "720p":
        return "scale=-2:720"
    if resolution == "480p":
        return "scale=-2:480"
    if resolution == "360p":
        return "scale=-2:360"
    if resolution == "custom" and custom:
        # custom expected like "1280x720"
        try:
            w, h = custom.split("x")
            # use pad to keep even dims and preserve aspect ratio
            return f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"
        except Exception:
            return None
    return None


async def encode_video(
    input_file: str,
    output_file: str,
    preset_name: str = "default_h264",
    task_id: str = "encode",
    user_id: int = 0,
    progress_callback=None,
    custom_settings: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str]:
    """
    High-level encode function. Returns (success, stderr_or_msg).

    Preset keys supported:
      - vcodec, crf, preset, tune, profile, pix_fmt, acodec, abitrate, movflags

    Also supports:
      - resolution: 'source'|'720p'|'480p'|'custom'
      - custom_resolution: '1280x720'
      - two_pass: bool
      - maxrate/bufsize for constrained bitrate workflows
      - copy_audio: bool (prefer -c:a copy if True and input audio compatible)
    """
    try:
        ok, ferr = validate_video_file(input_file)
        if not ok:
            return False, ferr

        preset = ENCODE_PRESETS.get(preset_name, {}).copy()
        if not preset:
            preset = ENCODE_PRESETS["default_h264"].copy()

        if custom_settings:
            preset.update(custom_settings)

        # Build base command (we may run 1 or 2 ffmpeg passes)
        vcodec = preset.get("vcodec", "libx264")
        crf = preset.get("crf", 26)
        preset_flag = preset.get("preset", "slow")
        tune = preset.get("tune")
        profile = preset.get("profile")
        pix_fmt = preset.get("pix_fmt", "yuv420p")
        acodec = preset.get("acodec", "aac")
        abitrate = preset.get("abitrate", "128k")
        movflags = preset.get("movflags", "+faststart")
        copy_audio = bool(preset.get("copy_audio", False))

        # Resolution handling
        resolution = preset.get("resolution", "source")
        custom_res = preset.get("custom_resolution", None)
        scale_filter = _scale_filter_for_resolution(resolution, custom_res)

        # Constrained bitrate option (two-pass) - optional
        two_pass = bool(preset.get("two_pass", False))
        maxrate = preset.get("maxrate")  # e.g. '1500k'
        bufsize = preset.get("bufsize")  # e.g. '3000k'

        # Try to decide whether we can copy audio stream
        can_copy_audio = False
        try:
            info = get_video_info(input_file)
            if info and info.get("audio_codec"):
                # If user's requested acodec equals input, copy is possible
                if copy_audio or (acodec == info.get("audio_codec")):
                    can_copy_audio = True
        except Exception:
            can_copy_audio = False

        # Build video codec part
        base_vparams = ["-c:v", vcodec, "-crf", str(crf), "-preset", preset_flag]
        if tune:
            base_vparams += ["-tune", tune]
        # Only apply profile for libx264 (libx265 doesn't support -profile:v flag)
        if profile and vcodec == "libx264":
            base_vparams += ["-profile:v", profile]
        elif profile and vcodec == "libx265":
            # libx265 doesn't use -profile:v, skip it (profile is controlled via x265-params)
            logger.debug(f"Skipping profile '{profile}' for libx265 codec (not supported)")

        # pix_fmt explicitly for compatibility
        base_vparams += ["-pix_fmt", pix_fmt]

        # scale filter
        vf_args = []
        if scale_filter:
            vf_args.append(scale_filter)

        # combine vf if any
        vf_full = None
        if vf_args:
            vf_full = ",".join(vf_args)

        # audio params
        if can_copy_audio:
            audio_params = ["-c:a", "copy"]
        else:
            audio_params = ["-c:a", acodec, "-b:a", abitrate]

        # add movflags
        final_common = ["-movflags", movflags, "-y"]

        # two-pass workflow
        if two_pass and maxrate and bufsize:
            # First pass
            passlog = get_temp_filename(task_id, ".log")
            first_cmd = ["ffmpeg", "-y"]
            if vf_full:
                first_cmd += ["-i", input_file, "-vf", vf_full]
            else:
                first_cmd += ["-i", input_file]
            first_cmd += base_vparams + ["-b:v", maxrate, "-maxrate", maxrate, "-bufsize", bufsize,
                                        "-pass", "1", "-an", "-f", "mp4", os.devnull]
            logger.info(f"Encoding two-pass first pass: {' '.join(first_cmd[:10])} ...")
            ok1, stderr1 = await run_ffmpeg_with_progress(first_cmd, task_id + "_pass1", user_id, progress_callback)
            # proceed even if first pass had warnings — check ok1
            if not ok1:
                logger.warning(f"First pass failed for {task_id}: {stderr1}")

            # Second pass
            second_cmd = ["ffmpeg", "-y"]
            if vf_full:
                second_cmd += ["-i", input_file, "-vf", vf_full]
            else:
                second_cmd += ["-i", input_file]
            second_cmd += base_vparams + ["-b:v", maxrate, "-maxrate", maxrate, "-bufsize", bufsize,
                                         "-pass", "2"] + audio_params + final_common + [output_file]
            logger.info(f"Encoding two-pass second pass: {' '.join(second_cmd[:10])} ...")
            ok2, stderr2 = await run_ffmpeg_with_progress(second_cmd, task_id + "_pass2", user_id, progress_callback)
            # cleanup pass logs may be created by ffmpeg in CWD; we won't rely on passlog variable
            return ok2, (stderr2 if not ok2 else "Encoded (two-pass)")
        else:
            # single-pass encode (recommended)
            cmd = ["ffmpeg", "-i", input_file]
            if vf_full:
                cmd += ["-vf", vf_full]
            cmd += base_vparams
            # If maxrate/bufsize provided without two-pass, apply constrained params (CBR-ish)
            if maxrate:
                cmd += ["-maxrate", str(maxrate)]
            if bufsize:
                cmd += ["-bufsize", str(bufsize)]

            # audio
            cmd += audio_params
            # finalize
            cmd += final_common + [output_file]

            logger.info(f"Encoding single-pass: {' '.join(cmd[:10])} ... -> {output_file}")

            ok, stderr = await run_ffmpeg_with_progress(cmd, task_id, user_id, progress_callback)
            if ok:
                return True, "Encoded"
            return False, stderr

    except FileNotFoundError:
        return False, "FFmpeg not found on system"
    except Exception as e:
        logger.exception("encode_video error")
        return False, str(e)


# ------------------------
# Watermark: text & image
# ------------------------
async def add_text_watermark(
    input_file: str,
    output_file: str,
    text: str,
    task_id: str,
    user_id: int,
    position: str = "bottom_right",
    font_size: int = 24,
    font_color: str = "white",
    progress_callback=None
) -> Tuple[bool, str, Optional[str]]:
    try:
        positions = {
            "top_left": "x=10:y=10",
            "top_right": "x=w-tw-10:y=10",
            "bottom_left": "x=10:y=h-th-10",
            "bottom_right": "x=w-tw-10:y=h-th-10",
            "center": "x=(w-tw)/2:y=(h-th)/2",
        }
        pos = positions.get(position, positions["bottom_right"])
        # escape single quotes in text
        safe_text = text.replace("'", r"\'")
        draw = f"drawtext=text='{safe_text}':fontsize={font_size}:fontcolor={font_color}:{pos}:box=1:boxcolor=black@0.5:boxborderw=5"
        cmd = ["ffmpeg", "-i", input_file, "-vf", draw, "-c:v", "libx264", "-crf", "23", "-preset", "medium", "-c:a", "copy", "-y", output_file]
        ok, stderr = await run_ffmpeg_with_progress(cmd, task_id, user_id, progress_callback)
        if ok:
            return True, "Watermark added", output_file
        return False, stderr, None
    except Exception as e:
        logger.exception("add_text_watermark error")
        return False, str(e), None


async def add_image_watermark(
    input_file: str,
    output_file: str,
    watermark_image: str,
    task_id: str,
    user_id: int,
    position: str = "bottom_right",
    opacity: float = 0.7,
    progress_callback=None
) -> Tuple[bool, str, Optional[str]]:
    try:
        if not os.path.exists(watermark_image):
            return False, "Watermark image missing", None
        positions = {
            "top_left": "10:10",
            "top_right": "W-w-10:10",
            "bottom_left": "10:H-h-10",
            "bottom_right": "W-w-10:H-h-10",
            "center": "(W-w)/2:(H-h)/2",
        }
        pos = positions.get(position, positions["bottom_right"])
        filter_complex = f"[1:v]format=rgba,colorchannelmixer=aa={opacity}[wm];[0:v][wm]overlay={pos}:format=auto[outv]"
        cmd = ["ffmpeg", "-i", input_file, "-i", watermark_image, "-filter_complex", filter_complex, "-map", "[outv]", "-map", "0:a?", "-c:v", "libx264", "-crf", "23", "-preset", "medium", "-c:a", "copy", "-y", output_file]
        ok, stderr = await run_ffmpeg_with_progress(cmd, task_id, user_id, progress_callback)
        if ok:
            return True, "Watermark added", output_file
        return False, stderr, None
    except Exception as e:
        logger.exception("add_image_watermark error")
        return False, str(e), None


# ------------------------
# Trim / Sample (re-use ffmpeg trim patterns)
# ------------------------
async def trim_video(
    input_file: str,
    output_file: str,
    start_time: float,
    end_time: float,
    task_id: str,
    user_id: int,
    progress_callback=None
) -> Tuple[bool, str]:
    try:
        ok, ferr = validate_video_file(input_file)
        if not ok:
            return False, ferr
        duration = get_video_info(input_file).get("duration", 0)
        if start_time < 0:
            start_time = 0
        if end_time > duration:
            end_time = duration
        if start_time >= end_time:
            return False, "Start must be before end"
        tdur = end_time - start_time
        # fast copy trim
        cmd = ["ffmpeg", "-ss", str(start_time), "-i", input_file, "-t", str(tdur), "-c", "copy", "-avoid_negative_ts", "1", "-movflags", "+faststart", "-y", output_file]
        ok, stderr = await run_ffmpeg_with_progress(cmd, task_id, user_id, progress_callback)
        if ok and os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            return True, f"Trimmed {format_duration(tdur)}"
        # fallback re-encode
        cmd = ["ffmpeg", "-ss", str(start_time), "-i", input_file, "-t", str(tdur), "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-y", output_file]
        ok2, stderr2 = await run_ffmpeg_with_progress(cmd, task_id + "_reencode", user_id, progress_callback)
        if ok2:
            return True, f"Trimmed (re-encoded) {format_duration(tdur)}"
        return False, stderr2
    except Exception as e:
        logger.exception("trim_video error")
        return False, str(e)


async def generate_sample(
    input_file: str,
    output_file: str,
    duration: int,
    task_id: str,
    user_id: int,
    from_point: str = "start",
    progress_callback=None
) -> Tuple[bool, str]:
    try:
        info = get_video_info(input_file)
        if not info:
            return False, "Unable to read input info"
        total = info.get("duration", 0)
        if duration >= total:
            return False, "Sample duration too long"
        if from_point == "start":
            start = 0
        elif from_point == "middle":
            start = max(0, (total - duration) / 2)
        elif from_point == "end":
            start = max(0, total - duration)
        elif from_point == "random":
            import random
            start = random.uniform(0, max(0, total - duration))
        else:
            start = 0
        return await trim_video(input_file, output_file, start, start + duration, task_id, user_id, progress_callback)
    except Exception as e:
        logger.exception("generate_sample error")
        return False, str(e)


# ------------------------
# Convert / Copy helpers
# ------------------------
async def convert_to_video(input_file: str, output_file: str, task_id: str, user_id: int, progress_callback=None) -> Tuple[bool, str]:
    try:
        cmd = ["ffmpeg", "-i", input_file, "-c", "copy", "-movflags", "+faststart", "-y", output_file]
        ok, stderr = await run_ffmpeg_with_progress(cmd, task_id, user_id, progress_callback)
        return ok, stderr
    except Exception as e:
        logger.exception("convert_to_video error")
        return False, str(e)


async def convert_to_document(input_file: str, output_file: str, task_id: str, user_id: int, progress_callback=None) -> Tuple[bool, str]:
    try:
        import shutil
        shutil.copy2(input_file, output_file)
        return True, "Prepared as document"
    except Exception as e:
        logger.exception("convert_to_document error")
        return False, str(e)


# ------------------------
# Merge functions
# ------------------------
async def merge_videos_simple(input_files: List[str], output_file: str, task_id: str, user_id: int, progress_callback=None) -> Tuple[bool, str]:
    try:
        if len(input_files) < 2:
            return False, "Need at least 2 videos"
        concat_file = get_temp_filename(task_id, ".txt")
        with open(concat_file, "w", encoding="utf-8") as f:
            for p in input_files:
                f.write(f"file '{os.path.abspath(p)}'\n")
        cmd = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_file, "-c", "copy", "-movflags", "+faststart", "-y", output_file]
        ok, stderr = await run_ffmpeg_with_progress(cmd, task_id, user_id, progress_callback)
        try:
            if os.path.exists(concat_file):
                os.remove(concat_file)
        except Exception:
            pass
        return ok, stderr
    except Exception as e:
        logger.exception("merge_videos_simple error")
        return False, str(e)


async def merge_videos_complex(input_files: List[str], output_file: str, task_id: str, user_id: int, progress_callback=None) -> Tuple[bool, str]:
    """
    Re-encode concat for incompatible files using concat filter.
    """
    try:
        if len(input_files) < 2:
            return False, "Need at least 2 videos"
        cmd = ["ffmpeg"]
        # add inputs
        for fp in input_files:
            cmd += ["-i", fp]
        # build filter_complex: [0:v:0][0:a:0?][1:v:0][1:a:0?]concat=n=X:v=1:a=1[v][a]
        fc_parts = []
        for i in range(len(input_files)):
            fc_parts.append(f"[{i}:v:0][{i}:a:0?]")
        fc = "".join(fc_parts) + f"concat=n={len(input_files)}:v=1:a=1[v][a]"
        cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-y", output_file]
        ok, stderr = await run_ffmpeg_with_progress(cmd, task_id, user_id, progress_callback)
        return ok, stderr
    except Exception as e:
        logger.exception("merge_videos_complex error")
        return False, str(e)


async def merge_video_audio(video_file: str, audio_file: str, output_file: str, task_id: str, user_id: int, progress_callback=None) -> Tuple[bool, str]:
    try:
        cmd = ["ffmpeg", "-i", video_file, "-i", audio_file, "-c:v", "copy", "-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", "-y", output_file]
        ok, stderr = await run_ffmpeg_with_progress(cmd, task_id, user_id, progress_callback)
        return ok, stderr
    except Exception as e:
        logger.exception("merge_video_audio error")
        return False, str(e)


async def merge_video_subtitle(video_file: str, subtitle_file: str, output_file: str, task_id: str, user_id: int, progress_callback=None) -> Tuple[bool, str]:
    try:
        sub_codec = "mov_text" if output_file.endswith(".mp4") else "srt"
        cmd = ["ffmpeg", "-i", video_file, "-i", subtitle_file, "-c", "copy", "-map", "0", "-map", "1", "-c:s", sub_codec, "-metadata:s:s:0", "language=eng", "-movflags", "+faststart", "-y", output_file]
        ok, stderr = await run_ffmpeg_with_progress(cmd, task_id, user_id, progress_callback)
        return ok, stderr
    except Exception as e:
        logger.exception("merge_video_subtitle error")
        return False, str(e)


# ------------------------
# New Tools: Rotate, Flip, Speed, Volume, Crop, GIF, Reverse, Extract Thumbnail
# ------------------------
async def rotate_video(
    input_file: str,
    output_file: str,
    angle: int,
    task_id: str,
    user_id: int,
    progress_callback=None
) -> Tuple[bool, str]:
    """Rotate video by 90, 180, or 270 degrees."""
    try:
        ok, ferr = validate_video_file(input_file)
        if not ok:
            return False, ferr or "Invalid video file"
        
        transpose_map = {
            90: "1",
            180: "2,transpose=2",
            270: "2"
        }
        
        if angle not in transpose_map:
            return False, f"Invalid rotation angle: {angle}. Must be 90, 180, or 270."
        
        transpose_filter = f"transpose={transpose_map[angle]}"
        
        cmd = ["ffmpeg", "-i", input_file, "-vf", transpose_filter, "-c:a", "copy", "-movflags", "+faststart", "-y", output_file]
        ok, stderr = await run_ffmpeg_with_progress(cmd, task_id, user_id, progress_callback)
        return (True, f"Rotated {angle}°") if ok else (False, stderr or "Rotation failed")
    except Exception as e:
        logger.exception("rotate_video error")
        return False, str(e)


async def flip_video(
    input_file: str,
    output_file: str,
    direction: str,
    task_id: str,
    user_id: int,
    progress_callback=None
) -> Tuple[bool, str]:
    """Flip video horizontally or vertically."""
    try:
        ok, ferr = validate_video_file(input_file)
        if not ok:
            return False, ferr or "Invalid video file"
        
        flip_filters = {
            "horizontal": "hflip",
            "vertical": "vflip"
        }
        
        if direction not in flip_filters:
            return False, f"Invalid flip direction: {direction}. Must be 'horizontal' or 'vertical'."
        
        vf = flip_filters[direction]
        cmd = ["ffmpeg", "-i", input_file, "-vf", vf, "-c:a", "copy", "-movflags", "+faststart", "-y", output_file]
        ok, stderr = await run_ffmpeg_with_progress(cmd, task_id, user_id, progress_callback)
        return (True, f"Flipped {direction}") if ok else (False, stderr or "Flip failed")
    except Exception as e:
        logger.exception("flip_video error")
        return False, str(e)


async def adjust_video_speed(
    input_file: str,
    output_file: str,
    speed: float,
    task_id: str,
    user_id: int,
    progress_callback=None
) -> Tuple[bool, str]:
    """Adjust video playback speed. Speed range: 0.5 to 2.0."""
    try:
        ok, ferr = validate_video_file(input_file)
        if not ok:
            return False, ferr or "Invalid video file"
        
        if speed < 0.5 or speed > 2.0:
            return False, "Speed must be between 0.5 and 2.0"
        
        video_speed = 1.0 / speed
        audio_speed = speed
        
        if audio_speed < 0.5:
            audio_speed = 0.5
        elif audio_speed > 2.0:
            audio_speed = 2.0
        
        vf = f"setpts={video_speed}*PTS"
        af = f"atempo={audio_speed}"
        
        if audio_speed > 2.0 or audio_speed < 0.5:
            af = f"atempo=2.0,atempo={audio_speed/2.0}" if audio_speed > 2.0 else f"atempo=0.5,atempo={audio_speed*2.0}"
        
        cmd = ["ffmpeg", "-i", input_file, "-vf", vf, "-af", af, "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-y", output_file]
        ok, stderr = await run_ffmpeg_with_progress(cmd, task_id, user_id, progress_callback)
        return (True, f"Speed adjusted to {speed}x") if ok else (False, stderr or "Speed adjustment failed")
    except Exception as e:
        logger.exception("adjust_video_speed error")
        return False, str(e)


async def adjust_audio_volume(
    input_file: str,
    output_file: str,
    volume_percent: int,
    task_id: str,
    user_id: int,
    progress_callback=None
) -> Tuple[bool, str]:
    """Adjust audio volume. Volume is percentage (50 = 50%, 200 = 200%)."""
    try:
        ok, ferr = validate_video_file(input_file)
        if not ok:
            return False, ferr or "Invalid video file"
        
        if volume_percent < 0 or volume_percent > 500:
            return False, "Volume must be between 0 and 500%"
        
        volume_factor = volume_percent / 100.0
        af = f"volume={volume_factor}"
        
        cmd = ["ffmpeg", "-i", input_file, "-af", af, "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-y", output_file]
        ok, stderr = await run_ffmpeg_with_progress(cmd, task_id, user_id, progress_callback)
        return (True, f"Volume adjusted to {volume_percent}%") if ok else (False, stderr or "Volume adjustment failed")
    except Exception as e:
        logger.exception("adjust_audio_volume error")
        return False, str(e)


async def crop_video(
    input_file: str,
    output_file: str,
    aspect_ratio: str,
    task_id: str,
    user_id: int,
    progress_callback=None
) -> Tuple[bool, str]:
    """Crop video to specified aspect ratio."""
    try:
        ok, ferr = validate_video_file(input_file)
        if not ok:
            return False, ferr or "Invalid video file"
        
        info = get_video_info(input_file)
        if not info or "width" not in info or "height" not in info:
            return False, "Cannot get video dimensions"
        
        width = info.get("width", 1920)
        height = info.get("height", 1080)
        
        aspect_ratios = {
            "16:9": (16, 9),
            "4:3": (4, 3),
            "1:1": (1, 1),
            "9:16": (9, 16)
        }
        
        if aspect_ratio not in aspect_ratios:
            return False, f"Invalid aspect ratio: {aspect_ratio}"
        
        ar_w, ar_h = aspect_ratios[aspect_ratio]
        target_aspect = ar_w / ar_h
        current_aspect = width / height
        
        if abs(target_aspect - current_aspect) < 0.01:
            return False, "Video already has this aspect ratio"
        
        if current_aspect > target_aspect:
            new_width = int(height * target_aspect)
            new_height = height
            x_offset = (width - new_width) // 2
            y_offset = 0
        else:
            new_width = width
            new_height = int(width / target_aspect)
            x_offset = 0
            y_offset = (height - new_height) // 2
        
        new_width = new_width - (new_width % 2)
        new_height = new_height - (new_height % 2)
        
        crop_filter = f"crop={new_width}:{new_height}:{x_offset}:{y_offset}"
        cmd = ["ffmpeg", "-i", input_file, "-vf", crop_filter, "-c:a", "copy", "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-movflags", "+faststart", "-y", output_file]
        ok, stderr = await run_ffmpeg_with_progress(cmd, task_id, user_id, progress_callback)
        return (True, f"Cropped to {aspect_ratio}") if ok else (False, stderr or "Crop failed")
    except Exception as e:
        logger.exception("crop_video error")
        return False, str(e)


async def convert_to_gif(
    input_file: str,
    output_file: str,
    fps: int,
    scale: int,
    quality: str,
    task_id: str,
    user_id: int,
    progress_callback=None
) -> Tuple[bool, str]:
    """Convert video to GIF with palette generation for better quality."""
    try:
        ok, ferr = validate_video_file(input_file)
        if not ok:
            return False, ferr or "Invalid video file"
        
        if fps < 5 or fps > 30:
            return False, "FPS must be between 5 and 30"
        
        if scale < 240 or scale > 1080:
            return False, "Scale must be between 240 and 1080"
        
        quality_map = {
            "low": 128,
            "medium": 64,
            "high": 32
        }
        
        max_colors = quality_map.get(quality, 64)
        palette_file = get_temp_filename(task_id, "_palette.png")
        
        filters = f"fps={fps},scale={scale}:-1:flags=lanczos"
        palette_cmd = ["ffmpeg", "-i", input_file, "-vf", f"{filters},palettegen=max_colors={max_colors}", "-y", palette_file]
        
        ok1, stderr1 = await run_ffmpeg_with_progress(palette_cmd, task_id + "_palette", user_id, None)
        if not ok1:
            return False, f"Palette generation failed: {stderr1}"
        
        gif_cmd = ["ffmpeg", "-i", input_file, "-i", palette_file, "-filter_complex", f"{filters}[x];[x][1:v]paletteuse", "-y", output_file]
        ok2, stderr2 = await run_ffmpeg_with_progress(gif_cmd, task_id, user_id, progress_callback)
        
        try:
            if os.path.exists(palette_file):
                os.remove(palette_file)
        except Exception:
            pass
        
        return (True, "Converted to GIF") if ok2 else (False, stderr2 or "GIF conversion failed")
    except Exception as e:
        logger.exception("convert_to_gif error")
        return False, str(e)


async def reverse_video(
    input_file: str,
    output_file: str,
    task_id: str,
    user_id: int,
    progress_callback=None
) -> Tuple[bool, str]:
    """Reverse video playback (both video and audio)."""
    try:
        ok, ferr = validate_video_file(input_file)
        if not ok:
            return False, ferr or "Invalid video file"
        
        cmd = ["ffmpeg", "-i", input_file, "-vf", "reverse", "-af", "areverse", "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-c:a", "aac", "-b:a", "128k", "-avoid_negative_ts", "make_zero", "-movflags", "+faststart", "-y", output_file]
        ok, stderr = await run_ffmpeg_with_progress(cmd, task_id, user_id, progress_callback)
        return (True, "Video reversed") if ok else (False, stderr or "Reverse failed")
    except Exception as e:
        logger.exception("reverse_video error")
        return False, str(e)


async def extract_thumbnails(
    input_file: str,
    output_dir: str,
    mode: str,
    timestamp: str,
    count: int,
    task_id: str,
    user_id: int,
    progress_callback=None
) -> Tuple[bool, str]:
    """Extract thumbnail images from video."""
    try:
        ok, ferr = validate_video_file(input_file)
        if not ok:
            return False, ferr or "Invalid video file"
        
        info = get_video_info(input_file)
        if not info or "duration" not in info:
            return False, "Cannot get video duration"
        
        duration = info.get("duration", 0.0)
        if duration <= 0:
            duration = 10.0
        
        if mode == "single":
            from modules.utils import parse_time_input
            ts = parse_time_input(timestamp)
            if ts > duration:
                ts = duration / 2
            
            output_file = os.path.join(output_dir, f"thumb_{task_id}.jpg")
            cmd = ["ffmpeg", "-ss", str(ts), "-i", input_file, "-vframes", "1", "-q:v", "2", "-y", output_file]
            ok, stderr = await run_ffmpeg_with_progress(cmd, task_id, user_id, progress_callback)
            return (True, f"Extracted thumbnail at {format_duration(ts)}") if ok else (False, stderr or "Thumbnail extraction failed")
        
        elif mode == "interval":
            if count < 1 or count > 20:
                return False, "Count must be between 1 and 20"
            
            interval = duration / (count + 1)
            output_pattern = os.path.join(output_dir, f"thumb_{task_id}_%03d.jpg")
            
            cmd = ["ffmpeg", "-i", input_file, "-vf", f"fps=1/{interval}", "-vframes", str(count), "-q:v", "2", "-y", output_pattern]
            ok, stderr = await run_ffmpeg_with_progress(cmd, task_id, user_id, progress_callback)
            return (True, f"Extracted {count} thumbnails") if ok else (False, stderr or "Thumbnail extraction failed")
        
        else:
            return False, f"Invalid mode: {mode}"
    
    except Exception as e:
        logger.exception("extract_thumbnails error")
        return False, str(e)


# ------------------------
# Extract streams (audio, video, subtitles, thumbnails)
# ------------------------
async def extract_video_stream(
    input_file: str,
    output_file: str,
    task_id: str,
    user_id: int,
    progress_callback=None
) -> Tuple[bool, str]:
    """Extract only video stream (no audio)."""
    try:
        ok, ferr = validate_video_file(input_file)
        if not ok:
            return False, ferr or "Invalid video file"
        
        cmd = ["ffmpeg", "-i", input_file, "-an", "-c:v", "copy", "-y", output_file]
        ok, stderr = await run_ffmpeg_with_progress(cmd, task_id, user_id, progress_callback)
        return (True, "Video stream extracted") if ok else (False, stderr or "Video extraction failed")
    except Exception as e:
        logger.exception("extract_video_stream error")
        return False, str(e)


async def extract_audio_stream(
    input_file: str,
    output_file: str,
    task_id: str,
    user_id: int,
    progress_callback=None
) -> Tuple[bool, str]:
    """Extract only audio stream."""
    try:
        ok, ferr = validate_video_file(input_file)
        if not ok:
            return False, ferr or "Invalid video file"
        
        cmd = ["ffmpeg", "-i", input_file, "-vn", "-c:a", "libmp3lame", "-b:a", "192k", "-y", output_file]
        ok, stderr = await run_ffmpeg_with_progress(cmd, task_id, user_id, progress_callback)
        return (True, "Audio stream extracted") if ok else (False, stderr or "Audio extraction failed")
    except Exception as e:
        logger.exception("extract_audio_stream error")
        return False, str(e)


async def extract_subtitles(
    input_file: str,
    output_file: str,
    task_id: str,
    user_id: int,
    progress_callback=None
) -> Tuple[bool, str]:
    """Extract subtitle streams."""
    try:
        ok, ferr = validate_video_file(input_file)
        if not ok:
            return False, ferr or "Invalid video file"
        
        cmd = ["ffmpeg", "-i", input_file, "-map", "0:s:0", "-c:s", "srt", "-y", output_file]
        ok, stderr = await run_ffmpeg_with_progress(cmd, task_id, user_id, progress_callback)
        return (True, "Subtitles extracted") if ok else (False, stderr or "Subtitle extraction failed (no subtitles found)")
    except Exception as e:
        logger.exception("extract_subtitles error")
        return False, str(e)


async def extract_thumbnail(
    input_file: str,
    output_file: str,
    task_id: str,
    user_id: int,
    progress_callback=None
) -> Tuple[bool, str]:
    """Extract thumbnail/cover image from video."""
    try:
        ok, ferr = validate_video_file(input_file)
        if not ok:
            return False, ferr or "Invalid video file"
        
        cmd = ["ffmpeg", "-i", input_file, "-vframes", "1", "-q:v", "2", "-y", output_file]
        ok, stderr = await run_ffmpeg_with_progress(cmd, task_id, user_id, progress_callback)
        return (True, "Thumbnail extracted") if ok else (False, stderr or "Thumbnail extraction failed")
    except Exception as e:
        logger.exception("extract_thumbnail error")
        return False, str(e)


# ------------------------
# exports
# ------------------------
__all__ = [
    "ENCODE_PRESETS",
    "encode_video",
    "add_text_watermark",
    "add_image_watermark",
    "trim_video",
    "generate_sample",
    "convert_to_video",
    "convert_to_document",
    "merge_videos_simple",
    "merge_videos_complex",
    "merge_video_audio",
    "merge_video_subtitle",
    "rotate_video",
    "flip_video",
    "extract_video_stream",
    "extract_audio_stream",
    "extract_subtitles",
    "extract_thumbnail",
    "adjust_video_speed",
    "adjust_audio_volume",
    "crop_video",
    "convert_to_gif",
    "reverse_video",
    "extract_thumbnails",
]
