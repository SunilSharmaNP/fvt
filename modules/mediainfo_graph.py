# modules/mediainfo_graph.py
# MediaInfo extraction with graph generation

import os
import logging
import asyncio
import tempfile
import json
from typing import Optional, Dict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pymediainfo import MediaInfo

logger = logging.getLogger(__name__)

class MediaInfoGraphGenerator:
    """Generate mediainfo and create graphs"""
    
    @staticmethod
    async def get_mediainfo(file_path: str) -> Optional[str]:
        """Get mediainfo using pymediainfo"""
        try:
            media_info = MediaInfo.parse(file_path)
            info_text = ""
            
            for track in media_info.tracks:
                info_text += f"\n{'='*50}\n"
                info_text += f"Track type: {track.track_type}\n"
                info_text += f"{'='*50}\n"
                
                for key, value in track.to_data().items():
                    if value and key not in ['track_type']:
                        info_text += f"{key}: {value}\n"
            
            return info_text
        except Exception as e:
            logger.error(f"Error getting mediainfo: {e}")
            return None
    
    @staticmethod
    async def get_mediainfo_instant(file_url: str) -> Optional[str]:
        """
        Get mediainfo without downloading full file
        Uses ffprobe for instant analysis
        """
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                file_url
            ]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            
            if proc.returncode != 0:
                return None
            
            data = json.loads(stdout.decode())
            
            # Format output
            info_text = "\n" + "="*50 + "\n"
            info_text += "MEDIA INFORMATION (Instant Analysis)\n"
            info_text += "="*50 + "\n\n"
            
            # Format info
            if 'format' in data:
                fmt = data['format']
                info_text += "📦 CONTAINER\n"
                info_text += f"Format: {fmt.get('format_name', 'N/A')}\n"
                info_text += f"Duration: {float(fmt.get('duration', 0)):.2f}s\n"
                info_text += f"Size: {int(fmt.get('size', 0)) / (1024*1024):.2f} MB\n"
                info_text += f"Bitrate: {int(fmt.get('bit_rate', 0)) / 1000:.2f} kbps\n\n"
            
            if 'streams' in data:
                for stream in data['streams']:
                    stype = stream.get('codec_type', 'unknown')
                    if stype == 'video':
                        info_text += "🎥 VIDEO STREAM\n"
                        info_text += f"Codec: {stream.get('codec_name', 'N/A')}\n"
                        info_text += f"Resolution: {stream.get('width', 'N/A')}x{stream.get('height', 'N/A')}\n"
                        # Safe FPS parsing (no eval for security)
                        fps_str = stream.get('r_frame_rate', '0/1')
                        try:
                            if '/' in fps_str:
                                num, den = map(float, fps_str.split('/'))
                                fps = num / den if den != 0 else 0.0
                            else:
                                fps = float(fps_str)
                            info_text += f"FPS: {fps:.2f}\n"
                        except:
                            info_text += f"FPS: N/A\n"
                        info_text += f"Bitrate: {int(stream.get('bit_rate', 0)) / 1000:.2f} kbps\n\n"
                    elif stype == 'audio':
                        info_text += "🎵 AUDIO STREAM\n"
                        info_text += f"Codec: {stream.get('codec_name', 'N/A')}\n"
                        info_text += f"Sample Rate: {stream.get('sample_rate', 'N/A')} Hz\n"
                        info_text += f"Channels: {stream.get('channels', 'N/A')}\n"
                        info_text += f"Bitrate: {int(stream.get('bit_rate', 0)) / 1000:.2f} kbps\n\n"
            
            return info_text
            
        except Exception as e:
            logger.error(f"Error getting instant mediainfo: {e}")
            return None
    
    @staticmethod
    async def generate_bitrate_graph(file_path: str) -> Optional[str]:
        """Generate bitrate graph from video"""
        try:
            output_graph = os.path.join(tempfile.gettempdir(), f"bitrate_graph_{os.getpid()}.png")
            
            # Get frame bitrate data
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-select_streams", "v:0",
                "-show_entries", "packet=pts_time,size",
                "-of", "json",
                file_path
            ]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            
            data = json.loads(stdout.decode())
            packets = data.get('packets', [])
            
            if len(packets) < 10:
                return None
            
            # Sample packets for visualization
            sample_size = min(len(packets), 500)
            step = len(packets) // sample_size
            sampled_packets = packets[::step]
            
            times = [float(p.get('pts_time', 0)) for p in sampled_packets if 'pts_time' in p]
            sizes = [int(p.get('size', 0)) * 8 / 1000 for p in sampled_packets if 'size' in p]  # Convert to kbps
            
            if not times or not sizes:
                return None
            
            # Create graph
            plt.figure(figsize=(12, 6))
            plt.plot(times, sizes, linewidth=0.8, color='#2E86DE')
            plt.fill_between(times, sizes, alpha=0.3, color='#54A0FF')
            plt.xlabel('Time (seconds)', fontsize=10)
            plt.ylabel('Bitrate (kbps)', fontsize=10)
            plt.title('Video Bitrate Over Time', fontsize=12, fontweight='bold')
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(output_graph, dpi=150, bbox_inches='tight')
            plt.close()
            
            if os.path.exists(output_graph):
                return output_graph
            return None
            
        except Exception as e:
            logger.error(f"Error generating bitrate graph: {e}")
            return None

# Global instance
mediainfo_generator = MediaInfoGraphGenerator()
