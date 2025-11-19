# handlers/admin_handlers.py
# Admin-only command handlers for bot management

import os
import sys
import time
import logging
import asyncio
import psutil
import platform
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait

from config import config
from modules import bot_state
from modules.database import db
from modules.ui_menus import get_admin_menu
from modules.utils import format_duration, process_manager

logger = logging.getLogger(__name__)

bot_start_time = time.time()


def register_admin_handlers(app: Client):
    """Register all admin command handlers"""

    @app.on_message(filters.command("admin") & filters.user(config.ADMINS))
    async def admin_handler(client: Client, message: Message):
        image, caption, keyboard = await get_admin_menu()
        await message.reply_photo(photo=image, caption=caption, reply_markup=keyboard, quote=True)

    @app.on_message(filters.command("botmode") & filters.user(config.ADMINS))
    async def get_mode_handler(client: Client, message: Message):
        mode = bot_state.get_bot_mode()
        emoji = "✅" if mode == "ACTIVE" else "HOLD ⏸️"
        await message.reply_text(f"Global Bot Status: **{mode} {emoji}**")

    @app.on_message(filters.command("activate") & filters.user(config.ADMINS))
    async def activate_handler(client: Client, message: Message):
        bot_state.set_bot_mode("ACTIVE")
        await message.reply_text("✅ **Bot Activated!**\\nNow processing new tasks.")

    @app.on_message(filters.command("deactivate") & filters.user(config.ADMINS))
    async def deactivate_handler(client: Client, message: Message):
        bot_state.set_bot_mode("HOLD")
        await message.reply_text("⏸️ **Bot on Hold!**\\nWill not process new tasks.")

    @app.on_message(filters.command("hold"))
    async def hold_handler(client: Client, message: Message):
        user_id = message.from_user.id
        from modules.helpers import is_authorized_user
        if not await is_authorized_user(user_id, message.chat.id): return
        try:
            new_status = await db.toggle_user_setting(user_id, "is_on_hold")
            if new_status:
                await message.reply_text(config.MSG_USER_HOLD_ENABLED)
            else:
                await message.reply_text(config.MSG_USER_HOLD_DISABLED)
        except Exception as e:
            logger.error(f"Per-user hold handler error: {e}", exc_info=True)
            await message.reply_text("❌ Error changing your hold status.")

    @app.on_message(filters.command(["s", "status"]) & filters.user(config.ADMINS))
    async def status_handler(client: Client, message: Message):
        status_text = f"**Bot Task Status**\\n\\nTotal Tasks: `{len(process_manager.active_processes)}`\\n\\n"
        if not process_manager.active_processes:
            return await message.reply_text("No active tasks.")
        for task_id, data in process_manager.active_processes.items():
            elapsed = time.time() - data['start_time']
            db_task = await db.get_task(task_id)
            tool = db_task.get('tool', 'N/A') if db_task else 'N/A'
            status_text += f"**Task:** `{task_id}`\\n"
            status_text += f" **User:** `{data['user_id']}`\\n"
            status_text += f" **Tool:** `{tool}`\\n"
            status_text += f" **PID:** `{data['pid']}` | **PGID:** `{data['pgid']}`\\n"
            status_text += f" **Running for:** `{format_duration(elapsed)}`\\n"
            status_text += "------\\n"
        await message.reply_text(status_text)

    @app.on_message(filters.command("restart") & filters.user(config.SUDO_USERS))
    async def restart_handler(client: Client, message: Message):
        try:
            await message.reply_text("🔄 **Restarting...**")
            logger.info(f"Bot restart initiated by SUDO user {message.from_user.id}")
            await client.stop()
            os.execl(sys.executable, sys.executable, *sys.argv)
        except Exception as e:
            logger.error(f"Restart failed: {e}")

    @app.on_message(filters.command("addauth") & filters.user(config.ADMINS))
    async def add_auth_chat(client: Client, message: Message):
        chat_id = message.chat.id
        if message.reply_to_message:
            chat_id = message.reply_to_message.chat.id
        elif len(message.command) > 1:
            try:
                chat_id = int(message.command[1])
            except ValueError:
                return await message.reply_text("Invalid Chat ID.")
        if await db.is_authorized_chat(chat_id):
            return await message.reply_text("✅ Chat is already authorized.")
        if await db.add_authorized_chat(chat_id):
            await message.reply_text(f"✅ Chat `{chat_id}` has been authorized.")
        else:
            await message.reply_text("❌ Failed to authorize chat.")

    @app.on_message(filters.command("removeauth") & filters.user(config.ADMINS))
    async def remove_auth_chat(client: Client, message: Message):
        chat_id = message.chat.id
        if message.reply_to_message:
            chat_id = message.reply_to_message.chat.id
        elif len(message.command) > 1:
            try:
                chat_id = int(message.command[1])
            except ValueError:
                return await message.reply_text("Invalid Chat ID.")
        if not await db.is_authorized_chat(chat_id):
            return await message.reply_text("❌ Chat is not authorized.")
        if await db.remove_authorized_chat(chat_id):
            await message.reply_text(f"✅ Chat `{chat_id}` has been de-authorized.")
        else:
            await message.reply_text("❌ Failed to de-authorize chat.")

    @app.on_message(filters.command("broadcast") & filters.user(config.SUDO_USERS))
    async def broadcast_handler(client: Client, message: Message):
        """Broadcast message to all bot users"""
        if not message.reply_to_message:
            return await message.reply_text(
                "**📣 Broadcast Command**\n\n"
                "Reply to a message to broadcast it to all users.\n\n"
                "**Usage:** `/broadcast` (reply to message)\n\n"
                "⚠️ This will send the message to all bot users!"
            )
        
        broadcast_msg = message.reply_to_message
        all_users = await db.get_all_user_ids()
        
        if not all_users:
            return await message.reply_text("❌ No users found in database.")
        
        success = 0
        failed = 0
        blocked = 0
        
        status_msg = await message.reply_text(
            f"📣 **Broadcasting...**\n\n"
            f"Total Users: {len(all_users)}\n"
            f"✅ Success: {success}\n"
            f"❌ Failed: {failed}\n"
            f"🚫 Blocked: {blocked}"
        )
        
        for user_id in all_users:
            try:
                await broadcast_msg.copy(user_id)
                success += 1
            except FloodWait as fw:
                logger.warning(f"FloodWait: sleeping for {fw.value} seconds")
                await asyncio.sleep(fw.value)
                try:
                    await broadcast_msg.copy(user_id)
                    success += 1
                except Exception as retry_err:
                    error_str = str(retry_err).lower()
                    if "blocked" in error_str or "user is deactivated" in error_str:
                        blocked += 1
                    else:
                        failed += 1
                        logger.debug(f"Broadcast retry failed for {user_id}: {retry_err}")
            except Exception as e:
                error_str = str(e).lower()
                if "blocked" in error_str or "user is deactivated" in error_str:
                    blocked += 1
                else:
                    failed += 1
                    logger.debug(f"Broadcast failed for {user_id}: {e}")
            
            if (success + failed + blocked) % 20 == 0:
                try:
                    await status_msg.edit_text(
                        f"📣 **Broadcasting...**\n\n"
                        f"Total Users: {len(all_users)}\n"
                        f"✅ Success: {success}\n"
                        f"❌ Failed: {failed}\n"
                        f"🚫 Blocked: {blocked}"
                    )
                except:
                    pass
            
            await asyncio.sleep(0.05)
        
        await status_msg.edit_text(
            f"📣 **Broadcast Complete!**\n\n"
            f"Total Users: {len(all_users)}\n"
            f"✅ Success: {success}\n"
            f"❌ Failed: {failed}\n"
            f"🚫 Blocked: {blocked}\n\n"
            f"**Success Rate:** {(success/len(all_users)*100):.1f}%"
        )

    @app.on_message(filters.command("stats") & filters.user(config.ADMINS))
    async def stats_handler(client: Client, message: Message):
        """Show detailed bot statistics"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        uptime_seconds = time.time() - bot_start_time
        uptime = format_duration(uptime_seconds)
        
        total_users = await db.get_total_users_count()
        total_tasks = await db.get_total_tasks_count()
        completed_tasks = await db.get_completed_tasks_count()
        
        success_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        stats_text = f"""
**🤖 Bot Statistics**

**📊 System Resources:**
• CPU Usage: `{cpu_percent}%`
• RAM: `{memory.percent}%` ({memory.used // (1024**3)}GB / {memory.total // (1024**3)}GB)
• Disk: `{disk.percent}%` ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)
• Platform: `{platform.system()} {platform.release()}`
• Uptime: `{uptime}`

**👥 User Statistics:**
• Total Users: `{total_users}`

**📈 Task Statistics:**
• Total Tasks: `{total_tasks}`
• Completed: `{completed_tasks}`
• Success Rate: `{success_rate:.1f}%`
• Active Now: `{len(process_manager.active_processes)}`

**🕐 Last Updated:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`
"""
        
        await message.reply_text(stats_text)

    logger.info("✅ Admin handlers registered")
