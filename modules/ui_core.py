# modules/ui_core.py (v8.0 - Professional SS Bots Theme)
# Complete theming system for consistent, beautiful UI across the bot
# Centralized borders, emojis, typography, and message formatters

import time
import psutil
from typing import List, Dict, Optional, Any
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# ═══════════════════════════════════════════════════════════════
#                    SS BOTS THEME CONSTANTS
# ═══════════════════════════════════════════════════════════════

class SSTheme:
    """Professional SS Bots theming constants and helpers"""
    
    # Decorative Borders
    BORDER_TOP = "┏━━༻« ★彡 𝐒𝐒 𝐁ᴏᴛs 彡★ »༺━━┓"
    BORDER_BOTTOM = "┗━━༻« ★彡 𝐒𝐒 𝐁ᴏᴛs 彡★ »༺━━┛"
    BORDER_LINE = "┠"
    BORDER_STATS_TOP = "┎⌬ 📊 <b>𝐒𝐒 𝐁ᴏᴛs 𝐒ᴛᴀᴛs</b> ⋆｡°✩₊˚.༄"
    BORDER_STATS_BOTTOM = "┖"
    
    # Typography
    BOLD_START = "<b>𝐒"
    BOLD_END = "</b>"
    
    # Emoji Sets
    EMOJIS = {
        'title': '🎥',
        'processed': '⚡',
        'status': '🪄',
        'eta': '⏳',
        'speed': '☘️',
        'elapsed': '🕓',
        'engine': '🪩',
        'mode': '🌐',
        'user': '👤',
        'user_id': '🆔',
        'cpu': '🖥️',
        'disk': '💿',
        'ram': '🧠',
        'uptime': '⏳',
        'download': '🔻',
        'upload': '🔺',
    }
    
    # Progress Bar Characters
    PROGRESS_FILLED = "■"
    PROGRESS_CURRENT = "▩"
    PROGRESS_EMPTY = "□"
    
    @staticmethod
    def get_progress_bar(percentage: float, length: int = 13) -> str:
        """
        Generate beautiful progress bar
        Example: [■■■■■■▩□□□□□□] 54.02%
        """
        if percentage < 0:
            percentage = 0
        elif percentage > 100:
            percentage = 100
        
        filled = int(percentage / 100 * length)
        
        if filled == 0:
            bar = SSTheme.PROGRESS_EMPTY * length
        elif filled >= length:
            bar = SSTheme.PROGRESS_FILLED * length
        else:
            bar = SSTheme.PROGRESS_FILLED * filled + SSTheme.PROGRESS_CURRENT + SSTheme.PROGRESS_EMPTY * (length - filled - 1)
        
        return f"[{bar}] {percentage:.2f}%"
    
    @staticmethod
    def format_field(emoji_key: str, label: str, value: str, bold_label: bool = True) -> str:
        """
        Format a single field with emoji and label
        Example: ┠⚡ 𝐏ʀᴏᴄᴇssᴇᴅ : 414.95 MiB of 768.17 MiB
        """
        emoji = SSTheme.EMOJIS.get(emoji_key, '')
        if bold_label:
            return f"{SSTheme.BORDER_LINE}{emoji} <b>{label}</b> : {value}"
        return f"{SSTheme.BORDER_LINE}{emoji} {label} : {value}"
    
    @staticmethod
    def get_bot_stats(show_speeds: bool = False) -> str:
        """
        Get system statistics with decorative formatting
        Matches screenshot: CPU, Free Space, RAM, Uptime, DL/UL speeds
        """
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        disk_free_gb = psutil.disk_usage('/').free / (1024**3)
        
        try:
            from modules.utils import format_duration
            boot_time = psutil.boot_time()
            uptime_seconds = int(time.time() - boot_time)
            uptime_str = format_duration(uptime_seconds)
        except:
            uptime_str = "N/A"
        
        msg = f"\n{SSTheme.BORDER_STATS_TOP}\n"
        msg += f"{SSTheme.BORDER_LINE}{SSTheme.EMOJIS['cpu']} <b>𝐂ᴘᴜ</b>: {cpu:.1f}% | {SSTheme.EMOJIS['disk']} <b>𝐅</b>: {disk_free_gb:.2f}GB [{100-disk:.1f}%]\n"
        msg += f"{SSTheme.BORDER_LINE} {SSTheme.EMOJIS['ram']} <b>𝐑ᴀᴍ</b>: {ram:.1f}% | {SSTheme.EMOJIS['uptime']} <b>𝐔ᴘᴛɪᴍᴇ</b>: {uptime_str}\n"
        
        if show_speeds:
            from modules.utils import get_human_readable_size
            net_io = psutil.net_io_counters()
            msg += f"{SSTheme.BORDER_STATS_BOTTOM} {SSTheme.EMOJIS['download']} <b>𝐃ʟ</b>: {get_human_readable_size(net_io.bytes_recv)}/s | {SSTheme.EMOJIS['upload']} <b>𝐔ʟ</b>: {get_human_readable_size(net_io.bytes_sent)}/s\n"
        else:
            msg += f"{SSTheme.BORDER_STATS_BOTTOM} {SSTheme.EMOJIS['download']} <b>𝐃ʟ</b>: 0B/s | {SSTheme.EMOJIS['upload']} <b>𝐔ʟ</b>: 0B/s\n"
        
        return msg
    
    @staticmethod
    def render_panel(
        title: str,
        body_lines: List[str],
        footer_lines: Optional[List[str]] = None,
        include_stats: bool = True
    ) -> str:
        """
        Render a complete panel with borders, body, and optional footer/stats
        
        Args:
            title: Panel title (e.g., video filename)
            body_lines: List of formatted body lines
            footer_lines: Optional additional footer lines
            include_stats: Whether to include bot stats footer
        
        Returns:
            Complete formatted message
        """
        msg = f"{SSTheme.EMOJIS['title']} <b>𝐓ɪᴛᴛʟᴇ</b> : {title}\n\n"
        msg += f"{SSTheme.BORDER_TOP}\n"
        
        for line in body_lines:
            msg += f"{line}\n"
        
        if footer_lines:
            for line in footer_lines:
                msg += f"{line}\n"
        
        msg += f"{SSTheme.BORDER_BOTTOM}"
        
        if include_stats:
            msg += SSTheme.get_bot_stats()
        
        return msg
    
    @staticmethod
    def format_progress_message(
        title: str,
        status: str,
        processed: int,
        total: int,
        percentage: float,
        speed: str,
        eta: str,
        elapsed: str,
        engine: str = "FFmpeg",
        mode: str = "#Leech",
        user_name: str = "User",
        user_id: int = 0,
        cancel_data: str = "cancel"
    ) -> str:
        """
        Format complete progress message matching screenshot design
        
        Example output:
        🎥 𝐓ɪᴛᴛʟᴇ : Wild.Bloom.2022.EP32.1080p.WEB-DL.Golchindl.DUBLE.mkv
        
        ┏━━༻« ★彡 𝐒𝐒 𝐁ᴏᴛs 彡★ »༺━━┓
        ┠ [■■■■■■▩□□□□□□] 54.02%
        ┠⚡ 𝐏ʀᴏᴄᴇssᴇᴅ : 414.95 MiB of 768.17 MiB
        ┠ 🪄 𝐒ᴛᴀᴛᴜs : Download
        ┠⏳ 𝐄ᴛᴀ : 23m4s
        ┠☘️ 𝐒ᴘᴇᴇᴅ : 261.22 KiB/s
        ┠ 🕓 𝐄ʟᴀᴘsᴇᴅ : 25m53s
        ┠ 🪩 𝐄ɴɢɪɴᴇ : FFmpeg v1.36.0
        ┠ 🌐 𝐌ᴏᴅᴇ : #Leech | #Tool
        ┠ 👤 𝐔sᴇʀ : John
        ┠ 🆔 𝐈𝐃 : 123456789
        ┠ /cancel_xyz123
        ┗━━༻« ★彡 𝐒𝐒 𝐁ᴏᴛs 彡★ »༺━━┛
        
        ┎⌬ 📊 𝐒𝐒 𝐁ᴏᴛs 𝐒ᴛᴀᴛs ⋆｡°✩₊˚.༄
        ┠🖥️ 𝐂ᴘᴜ: 1.4% | 💿 𝐅: 163.94GB [68.2%]
        ┠ 🧠 𝐑ᴀᴍ: 32.4% | ⏳ 𝐔ᴘᴛɪᴍᴇ: 1d11h6m39s
        ┖ 🔻 𝐃ʟ: 261.13KB/s | 🔺 𝐔ʟ: 0B/s
        """
        from modules.utils import get_human_readable_size
        
        progress_bar = SSTheme.get_progress_bar(percentage)
        
        body_lines = [
            f"{SSTheme.BORDER_LINE} {progress_bar}",
            SSTheme.format_field('processed', '𝐏ʀᴏᴄᴇssᴇᴅ', f"{get_human_readable_size(processed)} of {get_human_readable_size(total)}"),
            SSTheme.format_field('status', '𝐒ᴛᴀᴛᴜs', status),
            SSTheme.format_field('eta', '𝐄ᴛᴀ', eta if eta else "Calculating..."),
            SSTheme.format_field('speed', '𝐒ᴘᴇᴇᴅ', speed if speed else "0B/s"),
            SSTheme.format_field('elapsed', '𝐄ʟᴀᴘsᴇᴅ', elapsed),
            SSTheme.format_field('engine', '𝐄ɴɢɪɴᴇ', engine),
            SSTheme.format_field('mode', '𝐌ᴏᴅᴇ', mode),
            SSTheme.format_field('user', '𝐔sᴇʀ', user_name),
            SSTheme.format_field('user_id', '𝐈𝐃', str(user_id)),
            f"{SSTheme.BORDER_LINE} /{cancel_data}",
        ]
        
        return SSTheme.render_panel(
            title=title,
            body_lines=body_lines,
            include_stats=True
        )
    
    @staticmethod
    def format_user_settings_card(
        user_name: str,
        user_id: int,
        upload_mode: str,
        download_mode: str,
        active_tool: str = "None",
        metadata: str = "Enabled",
        thumbnail: str = "Not Set"
    ) -> str:
        """
        Format user settings display card with decorative styling
        """
        body_lines = [
            f"{SSTheme.BORDER_LINE}━━ <b>⚙️ 𝐔sᴇʀ 𝐒ᴇᴛᴛɪɴɢs</b> ━━",
            f"{SSTheme.BORDER_LINE}",
            f"{SSTheme.BORDER_LINE} <b>𝐍ᴀᴍᴇ</b> : {user_name}",
            f"{SSTheme.BORDER_LINE} <b>𝐈𝐃</b>: {user_id}",
            f"{SSTheme.BORDER_LINE} <b>𝐓ᴇʟᴇɢʀᴀᴍ 𝐃𝐂</b> : 5",
            f"{SSTheme.BORDER_LINE}",
            f"{SSTheme.BORDER_LINE}➲ <b>𝐀ᴠᴀɪʟᴀʙʟᴇ 𝐀ʀɢs:</b>",
            f"{SSTheme.BORDER_LINE} ✦ ➪ Upload Mode: <b>{upload_mode}</b>",
            f"{SSTheme.BORDER_LINE} ✦ ➪ Download Mode: <b>{download_mode}</b>",
            f"{SSTheme.BORDER_LINE} ✦ ➪ Active Tool: <b>{active_tool}</b>",
            f"{SSTheme.BORDER_LINE} ✦ ➪ Metadata: <b>{metadata}</b>",
            f"{SSTheme.BORDER_LINE} ✦ ➪ Thumbnail: <b>{thumbnail}</b>",
        ]
        
        footer_lines = [
            f"{SSTheme.BORDER_LINE}✦ |̲̅̅●̲̅̅|̲̅̅=̲̅̅|̲̅̅●̲̅̅| <b>𝐏ᴏᴡᴇʀᴇᴅ 𝐁ʏ : 𝐒𝐒 𝐁ᴏᴛs</b> ✌️|̲̅̅●̲̅̅|̲̅̅=̲̅̅|̲̅̅●̲̅̅|",
        ]
        
        msg = f"{SSTheme.BORDER_TOP}\n"
        for line in body_lines:
            msg += f"{line}\n"
        for line in footer_lines:
            msg += f"{line}\n"
        msg += f"{SSTheme.BORDER_BOTTOM}"
        
        return msg

# ═══════════════════════════════════════════════════════════════
#                    KEYBOARD HELPERS (Original)
# ═══════════════════════════════════════════════════════════════

def create_keyboard(buttons: list, columns: int = 2) -> InlineKeyboardMarkup:
    """
    Creates a flexible InlineKeyboardMarkup with a set number of columns.
    Fixes the 2-column layout bug.
    """
    # Filter out any None buttons (e.g., if a channel is not set)
    valid_buttons = [b for b in buttons if b is not None]
    
    # Build the keyboard row by row
    keyboard = []
    row = []
    
    for button in valid_buttons:
        # If button text starts with '---', give it its own row (1 column)
        if isinstance(button, InlineKeyboardButton) and button.text.startswith("---"):
            if row: # Add the previous row first
                keyboard.append(row)
                row = []
            keyboard.append([button]) # Add this button as its own row
        else:
            row.append(button)
            if len(row) == columns:
                keyboard.append(row)
                row = []
    
    # Add any remaining buttons in the last row
    if row:
        keyboard.append(row)
        
    return InlineKeyboardMarkup(keyboard)
