# handlers/admin_handlers.py
# Admin-only command handlers for bot management

import os
import sys
import time
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

from config import config
from modules import bot_state
from modules.database import db
from modules.ui_menus import get_admin_menu
from modules.utils import format_duration, process_manager

logger = logging.getLogger(__name__)


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

    @app.on_message(filters.command("broadcast") & filters.user(config.ADMINS))
    async def broadcast_handler(client: Client, message: Message):
        try:
            from pyrogram.filters import text as text_filter
            await message.reply_text("📣 **Broadcast Message**\n\nSend the message you want to broadcast to all users.\n\nSend /cancel to abort.")
            try:
                resp = await client.ask(message.chat.id, "Send your broadcast message:", filters=text_filter, timeout=300)
                
                if not resp.text or not isinstance(resp.text, str):
                    return await message.reply_text("❌ Please send a text message only.")
                
                if resp.text == "/cancel":
                    return await resp.reply_text("❌ Broadcast cancelled.")
                
                broadcast_msg = resp.text
                await resp.reply_text("🔄 Broadcasting message to all users...")
                
                all_users = await db.settings.find({}, {"user_id": 1}).to_list(length=None)
                success_count = 0
                fail_count = 0
                
                for user_doc in all_users:
                    try:
                        await client.send_message(user_doc["user_id"], broadcast_msg)
                        success_count += 1
                        await asyncio.sleep(0.05)
                    except Exception:
                        fail_count += 1
                
                await message.reply_text(f"✅ Broadcast completed!\n\n📊 **Statistics:**\n✅ Successful: {success_count}\n❌ Failed: {fail_count}")
            except asyncio.TimeoutError:
                await message.reply_text("⏱️ Timeout! Broadcast cancelled.")
        except Exception as e:
            logger.error(f"Broadcast error: {e}", exc_info=True)
            await message.reply_text(f"❌ Broadcast failed: {str(e)}")

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

    logger.info("✅ Admin handlers registered")
