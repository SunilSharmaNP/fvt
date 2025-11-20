# modules/progress_ui.py (v8.0 - Refactored for SSTheme)
# Professional progress UI - Now a thin wrapper around centralized SSTheme
# All formatting logic delegated to modules/ui_core.SSTheme

from typing import Optional, Dict
from modules.ui_core import SSTheme
from modules.utils import format_duration

class ProgressUI:
    """
    Professional progress display for tasks
    Thin orchestrator that uses SSTheme for all formatting
    """
    
    @staticmethod
    def get_progress_bar(percentage: float) -> str:
        """
        Generate progress bar - delegates to SSTheme
        DEPRECATED: Use SSTheme.get_progress_bar() directly
        """
        return SSTheme.get_progress_bar(percentage)
    
    @staticmethod
    def format_progress_message(
        title: str,
        status: str,
        processed: int,
        total: int,
        percentage: float,
        speed: int,
        eta: int,
        elapsed: int,
        engine: str = "FFmpeg",
        mode: str = "#Leech",
        user_name: str = "User",
        user_id: int = 0,
        cancel_data: str = "cancel"
    ) -> str:
        """
        Format professional progress message using SSTheme
        
        Args:
            title: Video title/filename
            status: Current status (Download/Encoding/Upload/etc)
            processed: Bytes processed
            total: Total bytes
            percentage: Progress percentage (0-100)
            speed: Current speed in bytes/sec
            eta: Estimated time remaining in seconds
            elapsed: Elapsed time in seconds
            engine: Processing engine name (FFmpeg/yt-dlp/Aria2)
            mode: Processing mode (#Leech | #Tool)
            user_name: User's name
            user_id: User's telegram ID
            cancel_data: Callback data for cancel button
        
        Returns:
            Complete formatted message with decorative borders and stats footer
        """
        from modules.utils import get_human_readable_size
        
        # Convert numeric speed/eta to strings
        speed_str = f"{get_human_readable_size(speed)}/s" if speed > 0 else "0B/s"
        eta_str = format_duration(eta) if eta > 0 else "Calculating..."
        elapsed_str = format_duration(int(elapsed))
        
        # Delegate to SSTheme formatter
        return SSTheme.format_progress_message(
            title=title,
            status=status,
            processed=processed,
            total=total,
            percentage=percentage,
            speed=speed_str,
            eta=eta_str,
            elapsed=elapsed_str,
            engine=engine,
            mode=mode,
            user_name=user_name,
            user_id=user_id,
            cancel_data=cancel_data
        )
    
    @staticmethod
    def get_bot_stats() -> str:
        """
        Get system statistics - delegates to SSTheme
        DEPRECATED: Use SSTheme.get_bot_stats() directly
        """
        return SSTheme.get_bot_stats(show_speeds=False)
    
    @staticmethod
    def format_queue_message(
        queue_items: list,
        title: str = "Testing [Merge]",
        admin_name: str = "admin"
    ) -> str:
        """
        Format queue display message
        Simple queue notification for merge operations
        """
        count = len(queue_items)
        
        msg = f"<b>{title}</b> <i>{admin_name}</i>\n"
        msg += f"✅ <b>Video Added to Queue!</b>\n"
        msg += f"📊 <b>Queue: {count} item(s)</b>\n"
        
        return msg
    
    @staticmethod
    def format_upload_complete_message(
        title: str,
        file_size: int,
        upload_time: int,
        user_name: str,
        mode: str = "Telegram"
    ) -> str:
        """
        Format upload completion message with decorative styling
        """
        from modules.utils import get_human_readable_size
        
        body_lines = [
            f"{SSTheme.BORDER_LINE}✅ <b>𝐔ᴘʟᴏᴀᴅ 𝐂ᴏᴍᴘʟᴇᴛᴇ</b>",
            f"{SSTheme.BORDER_LINE}",
            SSTheme.format_field('processed', '𝐒ɪᴢᴇ', get_human_readable_size(file_size)),
            SSTheme.format_field('elapsed', '𝐓ɪᴍᴇ', format_duration(upload_time)),
            SSTheme.format_field('mode', '𝐌ᴏᴅᴇ', mode),
            SSTheme.format_field('user', '𝐔ᴘʟᴏᴀᴅᴇᴅ 𝐁ʏ', user_name),
        ]
        
        footer_lines = [
            f"{SSTheme.BORDER_LINE}✦ |̲̅̅●̲̅̅|̲̅̅=̲̅̅|̲̅̅●̲̅̅| <b>𝐏ᴏᴡᴇʀᴇᴅ 𝐁ʏ : 𝐒𝐒 𝐁ᴏᴛs</b> ✌️|̲̅̅●̲̅̅|̲̅̅=̲̅̅|̲̅̅●̲̅̅|",
        ]
        
        return SSTheme.render_panel(
            title=title,
            body_lines=body_lines,
            footer_lines=footer_lines,
            include_stats=False
        )
    
    @staticmethod
    def format_task_complete_message(
        title: str,
        task_type: str,
        duration: int,
        file_size: int,
        user_name: str
    ) -> str:
        """
        Format task completion message with professional styling
        """
        from modules.utils import get_human_readable_size
        
        body_lines = [
            f"{SSTheme.BORDER_LINE}🎉 <b>𝐓ᴀsᴋ 𝐂ᴏᴍᴘʟᴇᴛᴇᴅ 𝐒ᴜᴄᴄᴇssꜰᴜʟʟʏ</b>",
            f"{SSTheme.BORDER_LINE}",
            SSTheme.format_field('engine', '𝐓ᴏᴏʟ', task_type.upper()),
            SSTheme.format_field('processed', '𝐎ᴜᴛᴘᴜᴛ 𝐒ɪᴢᴇ', get_human_readable_size(file_size)),
            SSTheme.format_field('elapsed', '𝐓ᴏᴛᴀʟ 𝐓ɪᴍᴇ', format_duration(duration)),
            SSTheme.format_field('user', '𝐏ʀᴏᴄᴇssᴇᴅ 𝐁ʏ', user_name),
        ]
        
        footer_lines = [
            f"{SSTheme.BORDER_LINE}✦ |̲̅̅●̲̅̅|̲̅̅=̲̅̅|̲̅̅●̲̅̅| <b>𝐏ᴏᴡᴇʀᴇᴅ 𝐁ʏ : 𝐒𝐒 𝐁ᴏᴛs</b> ✌️|̲̅̅●̲̅̅|̲̅̅=̲̅̅|̲̅̅●̲̅̅|",
        ]
        
        return SSTheme.render_panel(
            title=title,
            body_lines=body_lines,
            footer_lines=footer_lines,
            include_stats=True
        )
