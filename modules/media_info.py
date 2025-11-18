# modules/media_info.py (v5.1)
# MODIFIED based on user's 24-point plan and CHANGELOG.md:
# 1. Added `generate_media_info_graph` function (Plan Point 8.7).
# 2. Uses `matplotlib` to create a professional-looking graph image of the media info.
# 3. Uses `asyncio.to_thread` to run blocking `matplotlib` code non-blockingly.
# 4. Added `MATPLOTLIB_INSTALLED` check to handle missing dependency gracefully.
# 5. Kept existing `get_media_info` and `format_media_info` for text-based output.

import os
import json
import asyncio
import logging
import time
from typing import Optional, Dict, Any
from modules.utils import get_human_readable_size, format_duration

# Try to import matplotlib for graph generation
try:
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend
    import matplotlib.pyplot as plt
    MATPLOTLIB_INSTALLED = True
except ImportError:
    MATPLOTLIB_INSTALLED = False
    plt = None

logger = logging.getLogger(__name__)

if not MATPLOTLIB_INSTALLED:
    logger.warning("matplotlib not found. MediaInfo graph generation will be disabled.")
    logger.warning("Please run 'pip install matplotlib' to enable it.")


async def get_media_info(file_path: str) -> (Optional[Dict], Optional[str]):
    """
    Runs ffprobe to get detailed media info.
    Returns (info_dict, formatted_string)
    """
    try:
        command = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path,
        ]

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"ffprobe failed: {stderr.decode()}")
            return None, None
            
        data = json.loads(stdout)
        formatted_info = await format_media_info(data)
        
        return data, formatted_info
        
    except Exception as e:
        logger.error(f"Error getting media info: {e}", exc_info=True)
        return None, None

async def format_media_info(data: dict) -> str:
    """Formats the ffprobe JSON output into a professional string."""
    try:
        format_data = data.get("format", {})
        video_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
        audio_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
        subtitle_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "subtitle"]

        filename = os.path.basename(format_data.get("filename", "N/A"))
        size = int(format_data.get("size", 0))
        duration_sec = float(format_data.get("duration", 0))
        duration = format_duration(duration_sec) # Use util function
        bitrate = int(format_data.get("bit_rate", 0))

        info = f"**File:** `{filename}`\n"
        info += f"**Size:** `{get_human_readable_size(size)}`\n"
        info += f"**Duration:** `{duration}`\n"
        info += f"**Overall Bitrate:** `{get_human_readable_size(bitrate)}/s`\n"
        info += f"**Format:** `{format_data.get('format_long_name', 'N/A')}`\n\n"

        if video_streams:
            info += "**Video Stream**\n"
            vs = video_streams[0]
            width = vs.get('width', 'N/A')
            height = vs.get('height', 'N/A')
            codec = vs.get('codec_name', 'N/A')
            profile = vs.get('profile', 'N/A')
            fps_str = vs.get('r_frame_rate', 'N/A')
            
            fps_num = 0.0
            if '/' in fps_str:
                try:
                    num, den = fps_str.split('/')
                    if int(den) == 0: 
                        fps_num = 0
                    else:
                        fps_num = int(num) / int(den)
                    fps = f"{fps_num:.2f}"
                except ValueError:
                    fps = "N/A" # Handle invalid format
            else:
                fps = fps_str
            
            info += f"  `Codec:` {codec} ({profile})\n"
            info += f"  `Resolution:` {width}x{height}\n"
            info += f"  `Frame Rate:` {fps} fps\n"

        if audio_streams:
            info += f"\n**Audio Stream(s):** `{len(audio_streams)}`\n"
            for i, aus in enumerate(audio_streams):
                lang = aus.get('tags', {}).get('language', 'N/A')
                codec = aus.get('codec_name', 'N/A')
                channels = aus.get('channels', 'N/A')
                layout = aus.get('channel_layout', 'N/A')
                info += f"  `Stream {i+1}:` {codec} ({lang}, {channels}ch, {layout})\n"

        if subtitle_streams:
            info += f"\n**Subtitle Stream(s):** `{len(subtitle_streams)}`\n"
            for i, sus in enumerate(subtitle_streams):
                lang = sus.get('tags', {}).get('language', 'N/A')
                title = sus.get('tags', {}).get('title', 'N/A')
                codec = sus.get('codec_name', 'N/A')
                info += f"  `Stream {i+1}:` {codec} ({lang}, {title})\n"

        return info.strip()
    except Exception as e:
        logger.error(f"Error formatting media info: {e}")
        return "Could not format media info."


# --- NAYA: Graph Generation (Plan Point 8.7) ---

def _run_graph_generation(info_dict: Dict, output_path: str) -> Optional[str]:
    """
    Internal blocking function to create the graph image.
    Run this in a thread.
    """
    if not MATPLOTLIB_INSTALLED:
        logger.warning("Skipping graph generation: matplotlib not installed.")
        return None
        
    try:
        # --- 1. Extract Data ---
        format_data = info_dict.get("format", {})
        video_stream = next((s for s in info_dict.get("streams", []) if s.get("codec_type") == "video"), None)
        audio_streams = [s for s in info_dict.get("streams", []) if s.get("codec_type") == "audio"]
        
        if not video_stream:
            logger.error("Cannot generate graph: No video stream found.")
            return None

        filename = os.path.basename(format_data.get("filename", "N/A"))
        size = get_human_readable_size(int(format_data.get("size", 0)))
        duration = format_duration(float(format_data.get("duration", 0)))
        bitrate = f"{int(format_data.get('bit_rate', 0)) // 1000} kb/s"
        
        v_codec = video_stream.get('codec_name', 'N/A')
        v_profile = video_stream.get('profile', '')
        v_res = f"{video_stream.get('width', 0)}x{video_stream.get('height', 0)}"
        v_bitrate = f"{int(video_stream.get('bit_rate', 0)) // 1000} kb/s"
        v_fps_str = video_stream.get('r_frame_rate', 'N/A')
        if '/' in v_fps_str:
             num, den = v_fps_str.split('/')
             v_fps = f"{int(num) / int(den):.2f}" if int(den) > 0 else "N/A"
        else:
             v_fps = v_fps_str

        # --- 2. Build Text ---
        text = f"**General**\n"
        text += f"{'File:':<12} {filename}\n"
        text += f"{'Size:':<12} {size}\n"
        text += f"{'Duration:':<12} {duration}\n"
        text += f"{'Bitrate:':<12} {bitrate}\n\n"
        
        text += f"**Video**\n"
        text += f"{'Codec:':<12} {v_codec} ({v_profile})\n"
        text += f"{'Resolution:':<12} {v_res}\n"
        text += f"{'Bitrate:':<12} {v_bitrate}\n"
        text += f"{'Framerate:':<12} {v_fps} fps\n\n"
        
        text += f"**Audio ({len(audio_streams)})**\n"
        if not audio_streams:
            text += "  None\n"
        for i, aus in enumerate(audio_streams):
            a_codec = aus.get('codec_name', 'N/A')
            a_lang = aus.get('tags', {}).get('language', 'und')
            a_ch = aus.get('channels', 'N/A')
            a_layout = aus.get('channel_layout', 'N/A')
            a_bitrate = f"{int(aus.get('bit_rate', 0)) // 1000} kb/s"
            text += f"  `Track {i+1}:` {a_codec} ({a_lang}) | {a_layout} ({a_ch}ch) | {a_bitrate}\n"

        # --- 3. Create Plot ---
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(10, 6), facecolor='#1A1A1A')
        ax.set_facecolor('#1A1A1A')
        plt.axis('off')
        
        # Draw the text
        fig.text(
            0.05, 0.95, text, 
            ha='left', va='top', 
            fontsize=12, color='white', 
            fontfamily='monospace',
            wrap=True
        )
        
        # Add a title
        fig.text(
            0.5, 0.97, "Media Information", 
            ha='center', va='top', 
            fontsize=16, color='#4A90E2', 
            fontweight='bold'
        )

        # Save the figure
        plt.savefig(
            output_path, 
            bbox_inches='tight', 
            pad_inches=0.5, 
            facecolor=fig.get_facecolor(),
            dpi=100
        )
        plt.close(fig)
        
        logger.info(f"MediaInfo graph generated at {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Error generating MediaInfo graph: {e}", exc_info=True)
        # Ensure plot is closed on error
        try:
            plt.close(fig)
        except:
            pass
        return None

async def generate_media_info_graph(
    info_dict: Dict, 
    output_dir: str, 
    task_id: str
) -> Optional[str]:
    """
    Asynchronously generates a MediaInfo graph image.
    Returns the path to the generated PNG file or None.
    """
    if not MATPLOTLIB_INSTALLED:
        return None
        
    output_path = os.path.join(output_dir, f"mediainfo_{task_id}.png")
    
    try:
        # Run the blocking matplotlib code in a separate thread
        path = await asyncio.to_thread(_run_graph_generation, info_dict, output_path)
        return path
    except Exception as e:
        logger.error(f"Failed to run graph generation in thread: {e}")
        return None
