# handlers/start_handlers.py
# Handlers for start, help, about, settings, and video tools commands

import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from config import config
from modules.helpers import is_authorized_user, verify_user_complete
from modules.ui_menus import get_start_menu, get_user_settings_menu, get_video_tools_menu

logger = logging.getLogger(__name__)


async def send_start_menu(client: Client, message: Message, quote: bool = True):
    """Shared helper to send the start menu to a user"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    try:
        image, caption, keyboard = await get_start_menu(user_id)
        if quote:
            await message.reply_photo(photo=image, caption=caption, reply_markup=keyboard, quote=True)
        else:
            # Send as new message without quoting (for force-subscribe flow after message deletion)
            await client.send_photo(chat_id=chat_id, photo=image, caption=caption, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error sending start menu: {e}", exc_info=True)
        try:
            if quote:
                await message.reply_text("❌ Error: Bot could not be started.")
            else:
                await client.send_message(chat_id, "❌ Error: Bot could not be started.")
        except:
            pass


def register_start_handlers(app: Client):
    """Register all start-related command handlers"""

    @app.on_message(filters.command("start"))
    async def start_handler(client: Client, message: Message):
        user_id = message.from_user.id
        chat_id = message.chat.id
        if not await is_authorized_user(user_id, chat_id):
            if chat_id == user_id:
                return await message.reply_text(config.MSG_PRIVATE_CHAT_RESTRICTED)
            else:
                return await message.reply_text(config.MSG_GROUP_NOT_AUTHORIZED)
        if not await verify_user_complete(client, message): return
        await send_start_menu(client, message)

    @app.on_message(filters.command(["help", f"help@{config.BOT_USERNAME}"]))
    async def help_handler(client: Client, message: Message):
        if not await is_authorized_user(message.from_user.id, message.chat.id):
            return
        await message.reply_text(config.MSG_HELP,
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton(f"🔙 {config.BTN_BACK}", callback_data="open:start")
                                ]]))

    @app.on_message(filters.command(["about", f"about@{config.BOT_USERNAME}"]))
    async def about_handler(client: Client, message: Message):
        if not await is_authorized_user(message.from_user.id, message.chat.id):
            return
        caption = config.MSG_ABOUT.format(bot_name=config.BOT_NAME, developer=config.DEVELOPER)
        await message.reply_text(caption,
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton(f"🔙 {config.BTN_BACK}", callback_data="open:start")
                                ]]))

    @app.on_message(filters.command(["us", "settings", "usersettings"]))
    async def user_settings_handler(client: Client, message: Message):
        user_id = message.from_user.id
        if not await is_authorized_user(user_id, message.chat.id): return
        if not await verify_user_complete(client, message): return
        try:
            image, caption, keyboard = await get_user_settings_menu(user_id)
            await message.reply_photo(photo=image, caption=caption, reply_markup=keyboard, quote=True)
        except Exception as e:
            logger.error(f"User Settings handler error: {e}", exc_info=True)
            await message.reply_text(f"❌ Error loading settings: {e}")

    @app.on_message(filters.command(["vt", "tools", "videotools"]))
    async def video_tools_handler(client: Client, message: Message):
        user_id = message.from_user.id
        if not await is_authorized_user(user_id, message.chat.id): return
        if not await verify_user_complete(client, message): return
        try:
            image, caption, keyboard = await get_video_tools_menu(user_id)
            await message.reply_photo(photo=image, caption=caption, reply_markup=keyboard, quote=True)
        except Exception as e:
            logger.error(f"Video Tools handler error: {e}", exc_info=True)
            await message.reply_text(f"❌ Error loading tools: {e}")

    logger.info("✅ Start handlers registered")
