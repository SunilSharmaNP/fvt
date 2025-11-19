import asyncio
import logging
import os
import tempfile
from pymediainfo import MediaInfo
from telegraph import Telegraph
import aiohttp
from pyrogram import Client
from pyrogram.types import Message

logger = logging.getLogger(__name__)

async def get_instant_mediainfo_from_telegram(client: Client, message: Message) -> str:
    """
    Stream first few MB from Telegram file to generate instant mediainfo
    """
    temp_file_path = None
    try:
        file = message.video or message.document
        if not file:
            return None
        
        temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        temp_file_path = temp_file.name
        temp_file.close()
        
        downloaded = 0
        max_bytes = 5 * 1024 * 1024
        
        logger.info(f"Downloading first {max_bytes/1024/1024}MB for instant mediainfo...")
        
        async for chunk in client.stream_media(message, limit=6):
            with open(temp_file_path, 'ab') as f:
                f.write(chunk)
            downloaded += len(chunk)
            if downloaded >= max_bytes:
                break
        
        logger.info(f"Downloaded {downloaded} bytes, parsing mediainfo...")
        media_info = MediaInfo.parse(temp_file_path)
        formatted_info = format_mediainfo_output(media_info, file.file_name)
        
        try:
            os.remove(temp_file_path)
        except:
            pass
        
        return formatted_info
    except Exception as e:
        logger.error(f"Telegram instant mediainfo error: {e}", exc_info=True)
        if temp_file_path:
            try:
                os.remove(temp_file_path)
            except:
                pass
        return None


async def get_instant_mediainfo_from_url(url: str) -> str:
    """
    Download first 5MB of video from URL and generate mediainfo
    """
    temp_file_path = None
    try:
        temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        temp_file_path = temp_file.name
        temp_file.close()
        
        max_bytes = 5 * 1024 * 1024
        
        logger.info(f"Downloading first {max_bytes/1024/1024}MB from URL for instant mediainfo...")
        
        async with aiohttp.ClientSession() as session:
            headers = {'Range': f'bytes=0-{max_bytes}'}
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                with open(temp_file_path, 'wb') as f:
                    f.write(await resp.read())
        
        media_info = MediaInfo.parse(temp_file_path)
        formatted_info = format_mediainfo_output(media_info, url.split('/')[-1])
        
        try:
            os.remove(temp_file_path)
        except:
            pass
        
        return formatted_info
    except Exception as e:
        logger.error(f"URL instant mediainfo error: {e}", exc_info=True)
        if temp_file_path:
            try:
                os.remove(temp_file_path)
            except:
                pass
        return None


def format_mediainfo_output(media_info, filename: str = "Unknown") -> str:
    """Format pymediainfo output professionally"""
    output = []
    output.append(f"**📄 File:** `{filename}`\n")
    
    for track in media_info.tracks:
        if track.track_type == "General":
            output.append(f"**📊 General Information**")
            if track.format:
                output.append(f"• Format: `{track.format}`")
            if track.file_size:
                size_mb = int(track.file_size) / (1024 * 1024)
                output.append(f"• File Size: `{size_mb:.2f} MB`")
            if track.duration:
                duration_sec = int(track.duration) / 1000
                mins, secs = divmod(duration_sec, 60)
                hours, mins = divmod(mins, 60)
                if hours > 0:
                    output.append(f"• Duration: `{int(hours):02d}:{int(mins):02d}:{int(secs):02d}`")
                else:
                    output.append(f"• Duration: `{int(mins):02d}:{int(secs):02d}`")
            if track.overall_bit_rate:
                bitrate_kbps = int(track.overall_bit_rate) / 1000
                output.append(f"• Overall Bitrate: `{bitrate_kbps:.0f} kbps`")
            output.append("")
        
        elif track.track_type == "Video":
            output.append(f"**🎬 Video Track**")
            if track.codec_id or track.format:
                codec = track.codec_id or track.format
                output.append(f"• Codec: `{codec}`")
            if track.width and track.height:
                output.append(f"• Resolution: `{track.width}x{track.height}`")
            if track.display_aspect_ratio:
                output.append(f"• Aspect Ratio: `{track.display_aspect_ratio}`")
            if track.frame_rate:
                output.append(f"• Frame Rate: `{track.frame_rate} fps`")
            if track.bit_rate:
                bitrate_kbps = int(track.bit_rate) / 1000
                output.append(f"• Bitrate: `{bitrate_kbps:.0f} kbps`")
            if track.bit_depth:
                output.append(f"• Bit Depth: `{track.bit_depth} bits`")
            output.append("")
        
        elif track.track_type == "Audio":
            output.append(f"**🎵 Audio Track**")
            if track.codec_id or track.format:
                codec = track.codec_id or track.format
                output.append(f"• Codec: `{codec}`")
            if track.channel_s:
                output.append(f"• Channels: `{track.channel_s}`")
            if track.sampling_rate:
                sample_rate_khz = int(track.sampling_rate) / 1000
                output.append(f"• Sample Rate: `{sample_rate_khz:.1f} kHz`")
            if track.bit_rate:
                bitrate_kbps = int(track.bit_rate) / 1000
                output.append(f"• Bitrate: `{bitrate_kbps:.0f} kbps`")
            if track.language:
                output.append(f"• Language: `{track.language}`")
            output.append("")
    
    if not any(track.track_type == "Video" for track in media_info.tracks):
        output.append("⚠️ No video track found")
    
    return "\n".join(output)


async def upload_mediainfo_to_telegraph(mediainfo_text: str, title: str = "MediaInfo") -> str:
    """Upload mediainfo to telegraph and return URL"""
    try:
        telegraph = Telegraph()
        telegraph.create_account(short_name='VideoBot')
        
        html_content = f"<pre>{mediainfo_text}</pre>"
        
        response = telegraph.create_page(
            title=title,
            html_content=html_content
        )
        
        telegraph_url = f"https://telegra.ph/{response['path']}"
        logger.info(f"MediaInfo uploaded to Telegraph: {telegraph_url}")
        return telegraph_url
    except Exception as e:
        logger.error(f"Telegraph upload error: {e}", exc_info=True)
        return None
