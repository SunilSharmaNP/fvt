# modules/screenshot_tools.py
# Screenshot generation tools from animated-lamp integration

import os
import math
import logging
import tempfile
import datetime
import random
from typing import List, Optional, Tuple
import asyncio

logger = logging.getLogger(__name__)

class ScreenshotGenerator:
    """Generate screenshots from videos"""
    
    @staticmethod
    async def get_duration(file_path: str) -> Optional[int]:
        """Get video duration using ffprobe"""
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            duration = float(stdout.decode().strip())
            return int(duration)
        except Exception as e:
            logger.error(f"Error getting duration: {e}")
            return None
    
    @staticmethod
    async def get_dimensions(file_path: str) -> Tuple[int, int]:
        """Get video dimensions"""
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=s=x:p=0",
                file_path
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            width, height = map(int, stdout.decode().strip().split('x'))
            return width, height
        except Exception as e:
            logger.error(f"Error getting dimensions: {e}")
            return 1920, 1080
    
    @staticmethod
    def get_watermark_coordinates(position: str, width: int, height: int) -> Tuple[str, str]:
        """Calculate watermark position coordinates"""
        positions = {
            "top_left": ("10", "10"),
            "top_right": (f"w-tw-10", "10"),
            "bottom_left": ("10", f"h-th-10"),
            "bottom_right": (f"w-tw-10", f"h-th-10"),
            "center": (f"(w-tw)/2", f"(h-th)/2")
        }
        return positions.get(position, positions["bottom_left"])
    
    @staticmethod
    async def generate_screenshots(
        file_path: str,
        count: int = 5,
        watermark_text: str = "",
        watermark_position: str = "bottom_left",
        watermark_color: str = "white",
        font_size: int = 40,
        mode: str = "equally_spaced"
    ) -> List[str]:
        """
        Generate screenshots from video
        
        Args:
            file_path: Path to video file
            count: Number of screenshots (2-10)
            watermark_text: Watermark text to add
            watermark_position: Position of watermark
            watermark_color: Color of watermark text
            font_size: Font size for watermark
            mode: 'equally_spaced' or 'random'
        
        Returns:
            List of generated screenshot file paths
        """
        try:
            duration = await ScreenshotGenerator.get_duration(file_path)
            if not duration:
                return []
            
            # Calculate safe duration (remove first and last 2%)
            safe_duration = duration - int(duration * 0.04)
            if safe_duration <= 0:
                safe_duration = duration
            
            # Calculate screenshot timestamps
            if mode == "equally_spaced":
                timestamps = [int(safe_duration / count * i) for i in range(1, count + 1)]
            else:  # random
                timestamps = sorted([random.randint(1, safe_duration) for _ in range(count)])
            
            # Prepare FFmpeg watermark filter
            watermark_filter = "scale=1280:-1"
            if watermark_text:
                width, height = await ScreenshotGenerator.get_dimensions(file_path)
                x_pos, y_pos = ScreenshotGenerator.get_watermark_coordinates(
                    watermark_position, width, height
                )
                watermark_filter = (
                    f"drawtext=fontcolor={watermark_color}:fontsize={font_size}:"
                    f"x={x_pos}:y={y_pos}:text='{watermark_text}', scale=1280:-1"
                )
            
            screenshots = []
            output_dir = tempfile.mkdtemp()
            
            for i, timestamp in enumerate(timestamps):
                output_file = os.path.join(output_dir, f"screenshot_{i+1}.png")
                
                cmd = [
                    "ffmpeg",
                    "-ss", str(timestamp),
                    "-i", file_path,
                    "-vf", watermark_filter,
                    "-vframes", "1",
                    "-y",
                    output_file
                ]
                
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await proc.communicate()
                
                if os.path.exists(output_file):
                    screenshots.append(output_file)
                else:
                    logger.warning(f"Screenshot {i+1} not generated")
            
            return screenshots
            
        except Exception as e:
            logger.error(f"Error generating screenshots: {e}")
            return []
    
    @staticmethod
    async def extract_thumbnail(file_path: str, timestamp: int = 0) -> Optional[str]:
        """Extract single thumbnail at specific timestamp"""
        try:
            output_file = os.path.join(tempfile.gettempdir(), f"thumb_{timestamp}.jpg")
            
            cmd = [
                "ffmpeg",
                "-ss", str(timestamp),
                "-i", file_path,
                "-vframes", "1",
                "-q:v", "2",
                "-y",
                output_file
            ]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            
            if os.path.exists(output_file):
                return output_file
            return None
            
        except Exception as e:
            logger.error(f"Error extracting thumbnail: {e}")
            return None
