# modules/queue_manager.py
# Enhanced queue management for merge operations with visual display

import logging
from typing import Dict, List, Optional
from datetime import datetime
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

class QueueManager:
    """Manage user file queues for merge operations with visual display"""
    
    def __init__(self):
        self.user_queues: Dict[int, List[dict]] = {}
    
    def add_to_queue(self, user_id: int, file_info: dict) -> int:
        """Add file to user's queue"""
        if user_id not in self.user_queues:
            self.user_queues[user_id] = []
        
        file_info['added_at'] = datetime.now()
        self.user_queues[user_id].append(file_info)
        
        return len(self.user_queues[user_id])
    
    def get_queue(self, user_id: int) -> List[dict]:
        """Get user's current queue"""
        return self.user_queues.get(user_id, [])
    
    def get_queue_count(self, user_id: int) -> int:
        """Get number of items in user's queue"""
        return len(self.user_queues.get(user_id, []))
    
    def clear_queue(self, user_id: int):
        """Clear user's queue"""
        if user_id in self.user_queues:
            del self.user_queues[user_id]
    
    def has_queue(self, user_id: int) -> bool:
        """Check if user has items in queue"""
        return user_id in self.user_queues and len(self.user_queues[user_id]) > 0
    
    def format_queue_message(self, user_id: int, user_name: str = "admin", title: str = "Testing [Merge]") -> str:
        """
        Format queue message matching the screenshot design with real queue data
        Returns formatted message for queue display
        """
        count = self.get_queue_count(user_id)
        queue_items = self.get_queue(user_id)
        
        msg = f"<b>{title}</b>  <i>{user_name}</i>\n"
        msg += f"✅ <b>Video Added to Queue!</b>\n"
        msg += f"📊 <b>Queue: {count} item(s)</b>\n"
        
        # Show queue items with real file data
        if queue_items:
            msg += "\n<b>Files in queue:</b>\n"
            for i, item in enumerate(queue_items, 1):
                filename = item.get('filename', 'Unknown')
                file_size = item.get('file_size', 0)
                
                # Format file size
                if file_size > 0:
                    if file_size < 1024:
                        size_str = f"{file_size}B"
                    elif file_size < 1024 * 1024:
                        size_str = f"{file_size / 1024:.1f}KB"
                    elif file_size < 1024 * 1024 * 1024:
                        size_str = f"{file_size / (1024 * 1024):.1f}MB"
                    else:
                        size_str = f"{file_size / (1024 * 1024 * 1024):.2f}GB"
                else:
                    size_str = "Unknown"
                
                msg += f"{i}. {filename} ({size_str})\n"
        
        return msg
    
    def get_queue_keyboard(self, user_id: int) -> Optional[InlineKeyboardMarkup]:
        """
        Get inline keyboard for queue operations matching screenshot design
        Shows: Add More | Merge Now (if >= 2 items) | Clear
        """
        count = self.get_queue_count(user_id)
        
        if count == 0:
            return None
        
        buttons = []
        
        if count >= 2:
            buttons.append([
                InlineKeyboardButton("➕ Add More", callback_data="queue:add_more"),
                InlineKeyboardButton("🔀 Merge Now", callback_data="queue:merge_now")
            ])
            buttons.append([
                InlineKeyboardButton("🗑️ Clear", callback_data="queue:clear")
            ])
        else:
            buttons.append([
                InlineKeyboardButton("➕ Add More", callback_data="queue:add_more"),
                InlineKeyboardButton("🗑️ Clear", callback_data="queue:clear")
            ])
        
        return InlineKeyboardMarkup(buttons)

# Global queue manager instance
queue_manager = QueueManager()
