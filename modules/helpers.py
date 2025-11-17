# modules/helpers.py (v5.1)
# MODIFIED based on user's 24-point plan and config.py (v5.1):
# 1. Replaced hardcoded F-Sub message with `config.MSG_FSUB_REQUIRED` (Plan Point 16).
# 2. Replaced hardcoded Banned message with `config.MSG_BANNED` (Plan Point 16).
# 3. Replaced hardcoded F-Sub error message with `config.MSG_FSUB_ERROR`.
# 4. All core logic remains unchanged as it was correct.

import logging
from pyrogram import Client
from pyrogram.errors import UserNotParticipant
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import config
from modules.database import db

logger = logging.getLogger(__name__)

async def is_user_member(client: Client, user_id: int) -> bool:
    """Check if user is member of force subscribe channel."""
    if not config.FORCE_SUB_CHANNEL:
        return True # F-Sub is disabled
        
    try:
        chat_id = config.FORCE_SUB_CHANNEL
        member = await client.get_chat_member(chat_id, user_id)
        return member.status not in ["left", "kicked"]
    except UserNotParticipant:
        return False
    except Exception as e:
        logger.error(f"Error checking membership for {user_id} in {config.FORCE_SUB_CHANNEL}: {e}")
        return False # Default to False on error

async def force_subscribe_check(client: Client, message):
    """
    Checks for F-Sub. If user is not member, sends join message and returns False.
    Returns True if user is member or F-Sub is disabled.
    """
    # Use query.from_user if it's a callback, else message.from_user
    user = getattr(message, 'from_user', None)
    if not user:
        logger.error("Could not get user from message/query in force_subscribe_check")
        return False
        
    user_id = user.id
    
    # Skip check for admins
    if user_id in config.ADMINS:
        return True
    
    if await is_user_member(client, user_id):
        return True
    
    # User is not a member
    try:
        chat_id = config.FORCE_SUB_CHANNEL
        chat = await client.get_chat(chat_id)
        invite_link = chat.invite_link or f"https://t.me/{chat.username}"
        title = chat.title
        
        # MODIFIED: Use text from config.py
        text = config.MSG_FSUB_REQUIRED.format(title=title)
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📢 Join {title}", url=invite_link)],
            [InlineKeyboardButton("🔄 Check Again", callback_data="check_subscription")]
        ])
        
        # Handle both message and callback query
        reply_func = getattr(message, 'reply_photo', getattr(message, 'reply_text', None))
        if 'reply_photo' in getattr(reply_func, '__name__', ''):
             await message.reply_photo(
                photo=config.IMG_FSUB,
                caption=text,
                reply_markup=keyboard,
                quote=True
            )
        else:
            await message.reply_text(text, reply_markup=keyboard, quote=True)
            
        return False
    except Exception as e:
        logger.error(f"Error sending F-Sub message: {e}")
        # MODIFIED: Use text from config.py
        await message.reply_text(config.MSG_FSUB_ERROR)
        return False

async def is_authorized_user(user_id: int, chat_id: int) -> bool:
    """Checks if user is authorized in the current chat."""
    try:
        # Owner and Admins are authorized everywhere
        if user_id in config.ADMINS:
            return True
        
        # Check if user is banned
        if await db.is_user_banned(user_id):
            return False
        
        # Check if chat is authorized
        return await db.is_authorized_chat(chat_id)
        
    except Exception as e:
        logger.error(f"Error checking authorization: {e}")
        return False

async def verify_user_complete(client: Client, message_or_query) -> bool:
    """
    Runs all checks: Ban, F-Sub, and adds/updates user in DB.
    Returns True if user is verified, False otherwise.
    
    Handles both Message and CallbackQuery objects.
    """
    
    is_query = not hasattr(message_or_query, 'reply_text')
    user = message_or_query.from_user
    user_id = user.id
    
    # Define reply function based on object type
    async def reply(text, **kwargs):
        if is_query:
            # For queries, we can only answer or edit the original message
            # We'll answer with an alert
            await message_or_query.answer(text, show_alert=True)
        else:
            await message_or_query.reply_text(text, quote=True, **kwargs)

    try:
        # 1. Check if banned
        if await db.is_user_banned(user_id):
            # MODIFIED: Use text from config.py
            await reply(config.MSG_BANNED)
            return False
        
        # 2. Check F-Sub
        # We pass the original message/query object to handle F-Sub message reply
        if not await force_subscribe_check(client, message_or_query):
            if is_query:
                # The F-Sub check already sent the message, just answer the query
                await message_or_query.answer("Please join the channel to continue.", show_alert=True)
            return False
        
        # 3. Add user to database if new (for tracking purposes)
        # This also sets up their default settings
        await db.add_user(
            user_id=user_id,
            name=user.first_name,
            username=user.username
        )
        return True
        
    except Exception as e:
        logger.error(f"Error in verify_user_complete: {e}")
        return False
