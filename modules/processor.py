# modules/processor.py (v7.0 - Professional Enhanced)
# Video Processing Task Manager - All Tools Integrated
# All Bugs Fixed & Production Ready
# ==================================================

import os
import asyncio
import logging
import json
import shlex
import shutil
import functools
from typing import Dict, List, Optional, Tuple, Any
from pyrogram.types import Message
from pyrogram.errors import MessageNotModified

from config import config
from modules.database import db
from modules.utils import (
    run_ffmpeg_with_progress, get_video_info,
    parse_time_input, get_temp_filename,
    check_video_compatibility, cleanup_files
)
import modules.ffmpeg_tools as ffmpeg
import modules.log_manager as log_manager
from telegraph.aio import Telegraph
from telegraph.exceptions import TelegraphException

logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================

section_dict = {
    "General": "🎬",
    "Video": "🎥",
    "Audio": "🎵",
    "Text": "📝",
    "Menu": "📋"
}

# ==================== HELPER FUNCTIONS ====================

def parse_mediainfo_output(output: str, file_size: int) -> str:
    """Parse mediainfo output into readable format"""
    try:
        text_content = ""
        size_line = f"📦 **File Size:** {file_size / (1024 * 1024):.2f} MiB\n"
        text_content += size_line
        
        current_section = None
        
        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue
            
            # Check if this is a section header
            for section, emoji in section_dict.items():
                if line.startswith(section):
                    if current_section:
                        text_content += "\n"
                    text_content += f"\n**{emoji} {section}:**\n"
                    current_section = section
                    break
            else:
                # It's a detail line
                if current_section and ":" in line:
                    text_content += f"• {line}\n"
        
        return text_content
    except Exception as e:
        logger.error(f"Error parsing mediainfo: {e}")
        return f"📊 **Media Information:**\n```\n{output[:500]}\n```"

# ==================== MAIN PROCESSOR CLASS ====================

class VideoProcessor:
    """Main video processing orchestrator"""
    
    def __init__(self):
        self.telegraph = None
        
    async def init_telegraph(self):
        """Initialize Telegraph client for media uploads"""
        try:
            if not self.telegraph:
                self.telegraph = Telegraph()
                await self.telegraph.create_account(
                    short_name="VideoBot",
                    author_name="SS Video Workstation"
                )
            return True
        except Exception as e:
            logger.warning(f"Telegraph initialization failed: {e}")
            self.telegraph = None
            return False

    async def process_task(
        self,
        client,
        user_id: int,
        task_id: str,
        input_files: List[str],
        status_message: Optional[Message] = None,
        log_message_id: Optional[int] = None
    ) -> Optional[str]:
        """
        Main task processing orchestrator
        Returns: output_file_path on success, None on failure
        """
        
        try:
            # Get user settings (WITHOUT await - CRITICAL FIX)
            settings = db.get_default_settings(user_id)
            active_tool = settings.get('active_tool', 'none')
            
            logger.info(f"Processing task {task_id}: tool={active_tool}, files={len(input_files)}")
            
            # Route to appropriate processor
            if active_tool == 'merge':
                return await self._process_merge(
                    client, user_id, task_id, input_files,
                    status_message, log_message_id, settings
                )
            
            elif active_tool == 'encode':
                return await self._process_encode(
                    client, user_id, task_id, input_files[0],
                    status_message, log_message_id, settings
                )
            
            elif active_tool == 'trim':
                return await self._process_trim(
                    client, user_id, task_id, input_files[0],
                    status_message, log_message_id, settings
                )
            
            elif active_tool == 'watermark':
                return await self._process_watermark(
                    client, user_id, task_id, input_files[0],
                    status_message, log_message_id, settings
                )
            
            elif active_tool == 'sample':
                return await self._process_sample(
                    client, user_id, task_id, input_files[0],
                    status_message, log_message_id, settings
                )
            
            elif active_tool == 'mediainfo':
                return await self._process_mediainfo(
                    client, user_id, task_id, input_files[0],
                    status_message, log_message_id
                )
            
            elif active_tool == 'rotate':
                return await self._process_rotate(
                    client, user_id, task_id, input_files[0],
                    status_message, log_message_id, settings
                )
            
            elif active_tool == 'flip':
                return await self._process_flip(
                    client, user_id, task_id, input_files[0],
                    status_message, log_message_id, settings
                )
            
            elif active_tool == 'speed':
                return await self._process_speed(
                    client, user_id, task_id, input_files[0],
                    status_message, log_message_id, settings
                )
            
            elif active_tool == 'volume':
                return await self._process_volume(
                    client, user_id, task_id, input_files[0],
                    status_message, log_message_id, settings
                )
            
            elif active_tool == 'crop':
                return await self._process_crop(
                    client, user_id, task_id, input_files[0],
                    status_message, log_message_id, settings
                )
            
            elif active_tool == 'gif':
                return await self._process_gif(
                    client, user_id, task_id, input_files[0],
                    status_message, log_message_id, settings
                )
            
            elif active_tool == 'reverse':
                return await self._process_reverse(
                    client, user_id, task_id, input_files[0],
                    status_message, log_message_id, settings
                )
            
            elif active_tool == 'extract':
                return await self._process_extract(
                    client, user_id, task_id, input_files[0],
                    status_message, log_message_id, settings
                )
            
            elif active_tool == 'audioremover':
                return await self._process_audio_remover(
                    client, user_id, task_id, input_files[0],
                    status_message, log_message_id, settings
                )
            
            elif active_tool == 'hdcover':
                return await self._process_hd_cover(
                    client, user_id, task_id, input_files[0],
                    status_message, log_message_id, settings
                )
            
            elif active_tool == 'screenshot':
                return await self._process_screenshot(
                    client, user_id, task_id, input_files[0],
                    status_message, log_message_id, settings
                )
            
            else:
                raise ValueError(f"Unknown tool: {active_tool}")
        
        except Exception as e:
            logger.error(f"Task {task_id} error: {e}", exc_info=True)
            if status_message:
                try:
                    await status_message.edit_text(
                        f"❌ **Processing Error:**\n\n`{str(e)[:200]}`"
                    )
                except MessageNotModified:
                    pass
            return None

    # ==================== TOOL-SPECIFIC PROCESSORS ====================

    async def _process_merge(
        self, client, user_id: int, task_id: str,
        input_files: List[str], status_msg, log_msg_id, settings: dict
    ) -> Optional[str]:
        """Process merge operation"""
        try:
            output = get_temp_filename(task_id, "mp4")
            
            if status_msg:
                await status_msg.edit_text(
                    f"⏳ **Merging Videos**\n\nTask ID: `{task_id}`"
                )
            
            # Use ffmpeg_tools for merging
            result = await ffmpeg.merge_videos(
                input_files, output, status_msg, task_id
            )
            
            return output if result else None
        
        except Exception as e:
            logger.error(f"Merge error: {e}")
            return None

    async def _process_encode(
        self, client, user_id: int, task_id: str,
        input_file: str, status_msg, log_msg_id, settings: dict
    ) -> Optional[str]:
        """Process encoding operation"""
        try:
            output = get_temp_filename(task_id, "mp4")
            
            if status_msg:
                await status_msg.edit_text(
                    f"⚡ **Encoding Video**\n\nTask ID: `{task_id}`"
                )
            
            # Get encoding settings
            encode_settings = settings.get('encode_settings', {})
            
            result = await ffmpeg.encode_video(
                input_file, output, encode_settings, status_msg, task_id
            )
            
            return output if result else None
        
        except Exception as e:
            logger.error(f"Encode error: {e}")
            return None

    async def _process_trim(
        self, client, user_id: int, task_id: str,
        input_file: str, status_msg, log_msg_id, settings: dict
    ) -> Optional[str]:
        """Process trim operation"""
        try:
            output = get_temp_filename(task_id, "mp4")
            
            if status_msg:
                await status_msg.edit_text(
                    f"✂️ **Trimming Video**\n\nTask ID: `{task_id}`"
                )
            
            trim_settings = settings.get('trim_settings', {})
            start_time = trim_settings.get('start', '00:00:00')
            end_time = trim_settings.get('end', '00:00:00')
            
            result = await ffmpeg.trim_video(
                input_file, output, start_time, end_time, status_msg, task_id
            )
            
            return output if result else None
        
        except Exception as e:
            logger.error(f"Trim error: {e}")
            return None

    async def _process_watermark(
        self, client, user_id: int, task_id: str,
        input_file: str, status_msg, log_msg_id, settings: dict
    ) -> Optional[str]:
        """Process watermark operation"""
        try:
            output = get_temp_filename(task_id, "mp4")
            
            if status_msg:
                await status_msg.edit_text(
                    f"🖼️ **Adding Watermark**\n\nTask ID: `{task_id}`"
                )
            
            watermark_settings = settings.get('watermark_settings', {})
            
            result = await ffmpeg.add_watermark(
                input_file, output, watermark_settings, status_msg, task_id
            )
            
            return output if result else None
        
        except Exception as e:
            logger.error(f"Watermark error: {e}")
            return None

    async def _process_sample(
        self, client, user_id: int, task_id: str,
        input_file: str, status_msg, log_msg_id, settings: dict
    ) -> Optional[str]:
        """Process sample creation"""
        try:
            output = get_temp_filename(task_id, "mp4")
            
            if status_msg:
                await status_msg.edit_text(
                    f"🎞️ **Creating Sample**\n\nTask ID: `{task_id}`"
                )
            
            sample_settings = settings.get('sample_settings', {})
            
            result = await ffmpeg.create_sample(
                input_file, output, sample_settings, status_msg, task_id
            )
            
            return output if result else None
        
        except Exception as e:
            logger.error(f"Sample error: {e}")
            return None

    async def _process_mediainfo(
        self, client, user_id: int, task_id: str,
        input_file: str, status_msg, log_msg_id
    ) -> Optional[str]:
        """Process mediainfo extraction"""
        try:
            if status_msg:
                await status_msg.edit_text(
                    f"📊 **Extracting Media Info**\n\nTask ID: `{task_id}`"
                )
            
            # Get media info
            info = await get_video_info(input_file)
            file_size = os.path.getsize(input_file)
            
            # Parse and send info
            parsed_info = parse_mediainfo_output(info, file_size)
            
            # Send as telegraph page
            try:
                await self.init_telegraph()
                if self.telegraph:
                    page = await self.telegraph.create_page(
                        title=f"Media Info - {task_id}",
                        html_content=f"<pre>{parsed_info}</pre>"
                    )
                    media_url = page['url']
                else:
                    media_url = None
            except:
                media_url = None
            
            # Send to user
            if status_msg:
                await status_msg.edit_text(parsed_info)
                if media_url:
                    await status_msg.reply_text(
                        f"📄 **Full Info:** [View on Telegraph]({media_url})",
                        disable_web_page_preview=True
                    )
            
            # Return dummy file for tracking
            return get_temp_filename(task_id, "txt")
        
        except Exception as e:
            logger.error(f"MediaInfo error: {e}")
            return None

    async def _process_rotate(
        self, client, user_id: int, task_id: str,
        input_file: str, status_msg, log_msg_id, settings: dict
    ) -> Optional[str]:
        """Process video rotation"""
        try:
            output = get_temp_filename(task_id, "mp4")
            
            if status_msg:
                await status_msg.edit_text(
                    f"🔄 **Rotating Video**\n\nTask ID: `{task_id}`"
                )
            
            rotate_settings = settings.get('rotate_settings', {})
            angle = rotate_settings.get('angle', 90)
            
            result = await ffmpeg.rotate_video(
                input_file, output, angle, status_msg, task_id
            )
            
            return output if result else None
        
        except Exception as e:
            logger.error(f"Rotate error: {e}")
            return None

    async def _process_flip(
        self, client, user_id: int, task_id: str,
        input_file: str, status_msg, log_msg_id, settings: dict
    ) -> Optional[str]:
        """Process video flipping"""
        try:
            output = get_temp_filename(task_id, "mp4")
            
            if status_msg:
                await status_msg.edit_text(
                    f"🔃 **Flipping Video**\n\nTask ID: `{task_id}`"
                )
            
            flip_settings = settings.get('flip_settings', {})
            direction = flip_settings.get('direction', 'horizontal')
            
            result = await ffmpeg.flip_video(
                input_file, output, direction, status_msg, task_id
            )
            
            return output if result else None
        
        except Exception as e:
            logger.error(f"Flip error: {e}")
            return None

    async def _process_speed(
        self, client, user_id: int, task_id: str,
        input_file: str, status_msg, log_msg_id, settings: dict
    ) -> Optional[str]:
        """Process speed adjustment"""
        try:
            output = get_temp_filename(task_id, "mp4")
            
            if status_msg:
                await status_msg.edit_text(
                    f"⚡ **Adjusting Speed**\n\nTask ID: `{task_id}`"
                )
            
            speed_settings = settings.get('speed_settings', {})
            multiplier = speed_settings.get('multiplier', 1.0)
            
            result = await ffmpeg.adjust_video_speed(
                input_file, output, multiplier, status_msg, task_id
            )
            
            return output if result else None
        
        except Exception as e:
            logger.error(f"Speed error: {e}")
            return None

    async def _process_volume(
        self, client, user_id: int, task_id: str,
        input_file: str, status_msg, log_msg_id, settings: dict
    ) -> Optional[str]:
        """Process volume adjustment"""
        try:
            output = get_temp_filename(task_id, "mp4")
            
            if status_msg:
                await status_msg.edit_text(
                    f"🔊 **Adjusting Volume**\n\nTask ID: `{task_id}`"
                )
            
            volume_settings = settings.get('volume_settings', {})
            level = volume_settings.get('level', 1.0)
            
            result = await ffmpeg.adjust_audio_volume(
                input_file, output, level, status_msg, task_id
            )
            
            return output if result else None
        
        except Exception as e:
            logger.error(f"Volume error: {e}")
            return None

    async def _process_crop(
        self, client, user_id: int, task_id: str,
        input_file: str, status_msg, log_msg_id, settings: dict
    ) -> Optional[str]:
        """Process video cropping"""
        try:
            output = get_temp_filename(task_id, "mp4")
            
            if status_msg:
                await status_msg.edit_text(
                    f"✂️ **Cropping Video**\n\nTask ID: `{task_id}`"
                )
            
            crop_settings = settings.get('crop_settings', {})
            
            result = await ffmpeg.crop_video(
                input_file, output, crop_settings, status_msg, task_id
            )
            
            return output if result else None
        
        except Exception as e:
            logger.error(f"Crop error: {e}")
            return None

    async def _process_gif(
        self, client, user_id: int, task_id: str,
        input_file: str, status_msg, log_msg_id, settings: dict
    ) -> Optional[str]:
        """Process GIF conversion"""
        try:
            output = get_temp_filename(task_id, "gif")
            
            if status_msg:
                await status_msg.edit_text(
                    f"🎞️ **Creating GIF**\n\nTask ID: `{task_id}`"
                )
            
            gif_settings = settings.get('gif_settings', {})
            
            result = await ffmpeg.convert_to_gif(
                input_file, output, gif_settings, status_msg, task_id
            )
            
            return output if result else None
        
        except Exception as e:
            logger.error(f"GIF error: {e}")
            return None

    async def _process_reverse(
        self, client, user_id: int, task_id: str,
        input_file: str, status_msg, log_msg_id, settings: dict
    ) -> Optional[str]:
        """Process video reversal"""
        try:
            output = get_temp_filename(task_id, "mp4")
            
            if status_msg:
                await status_msg.edit_text(
                    f"⏪ **Reversing Video**\n\nTask ID: `{task_id}`"
                )
            
            result = await ffmpeg.reverse_video(
                input_file, output, status_msg, task_id
            )
            
            return output if result else None
        
        except Exception as e:
            logger.error(f"Reverse error: {e}")
            return None

    async def _process_extract(
        self, client, user_id: int, task_id: str,
        input_file: str, status_msg, log_msg_id, settings: dict
    ) -> Optional[str]:
        """Process stream extraction"""
        try:
            extract_settings = settings.get('extract_settings', {})
            extract_type = extract_settings.get('type', 'video')
            
            if extract_type == 'video':
                output = get_temp_filename(task_id, "mp4")
                msg = f"📹 **Extracting Video Stream**\n\nTask ID: `{task_id}`"
            elif extract_type == 'audio':
                output = get_temp_filename(task_id, "mp3")
                msg = f"🎵 **Extracting Audio Track**\n\nTask ID: `{task_id}`"
            else:
                output = get_temp_filename(task_id, "srt")
                msg = f"💬 **Extracting Subtitles**\n\nTask ID: `{task_id}`"
            
            if status_msg:
                await status_msg.edit_text(msg)
            
            result = await ffmpeg.extract_stream(
                input_file, output, extract_type, status_msg, task_id
            )
            
            return output if result else None
        
        except Exception as e:
            logger.error(f"Extract error: {e}")
            return None

    async def _process_audio_remover(
        self, client, user_id: int, task_id: str,
        input_file: str, status_msg, log_msg_id, settings: dict
    ) -> Optional[str]:
        """Process audio removal"""
        try:
            output = get_temp_filename(task_id, "mp4")
            
            if status_msg:
                await status_msg.edit_text(
                    f"🔇 **Removing Audio**\n\nTask ID: `{task_id}`"
                )
            
            result = await ffmpeg.remove_audio(
                input_file, output, status_msg, task_id
            )
            
            return output if result else None
        
        except Exception as e:
            logger.error(f"Audio remover error: {e}")
            return None

    async def _process_hd_cover(
        self, client, user_id: int, task_id: str,
        input_file: str, status_msg, log_msg_id, settings: dict
    ) -> Optional[str]:
        """Process HD cover addition"""
        try:
            output = get_temp_filename(task_id, "mp4")
            
            if status_msg:
                await status_msg.edit_text(
                    f"🎨 **Adding HD Cover**\n\nTask ID: `{task_id}`"
                )
            
            # Get cover from settings
            cover_file = settings.get('hd_cover_file')
            
            if not cover_file:
                raise ValueError("No cover image provided")
            
            result = await ffmpeg.add_hd_cover(
                input_file, output, cover_file, status_msg, task_id
            )
            
            return output if result else None
        
        except Exception as e:
            logger.error(f"HD cover error: {e}")
            return None

    async def _process_screenshot(
        self, client, user_id: int, task_id: str,
        input_file: str, status_msg, log_msg_id, settings: dict
    ) -> Optional[str]:
        """Process screenshot extraction"""
        try:
            output_dir = get_temp_filename(task_id, "")
            os.makedirs(output_dir, exist_ok=True)
            
            if status_msg:
                await status_msg.edit_text(
                    f"📸 **Extracting Screenshots**\n\nTask ID: `{task_id}`"
                )
            
            screenshot_settings = settings.get('screenshot_settings', {})
            
            result = await ffmpeg.extract_screenshots(
                input_file, output_dir, screenshot_settings, status_msg, task_id
            )
            
            return output_dir if result else None
        
        except Exception as e:
            logger.error(f"Screenshot error: {e}")
            return None

# ==================== GLOBAL INSTANCE ====================

# Create singleton processor instance
processor = VideoProcessor()
