# modules/ui_menus.py (v6.8 — Production Ready)
# Final fixed production-ready version
# - Removed duplicate functions
# - Added Screenshot, Audio Remover, HD Cover menus
# - Ensured consistency with callback handlers and database schema
# - Ready to paste into modules/ui_menus.py

import logging
from pyrogram.types import InlineKeyboardButton
from config import config
from modules.ui_core import create_keyboard
from modules.database import db

logger = logging.getLogger(__name__)


# Helper
def tick(value: bool):
    return "✅" if value else ""


# =========================================================
# START MENU
# =========================================================
async def get_start_menu(user_id: int):
    try:
        user_name = (await db.get_user_settings(user_id)).get("name", "User")
    except Exception:
        user_name = "User"

    buttons = [
        InlineKeyboardButton(config.BTN_USER_SETTINGS,
                             callback_data="open:settings"),
        InlineKeyboardButton(config.BTN_VIDEO_TOOLS,
                             callback_data="open:tools"),
        InlineKeyboardButton(config.BTN_HELP, callback_data="open:help"),
        InlineKeyboardButton(config.BTN_ABOUT, callback_data="open:about")
    ]
    if getattr(config, "UPDATE_CHANNEL", None):
        buttons.append(
            InlineKeyboardButton(
                config.BTN_UPDATES,
                url=f"https://t.me/{config.UPDATE_CHANNEL.lstrip('@')}"))
    if getattr(config, "SUPPORT_GROUP", None):
        buttons.append(
            InlineKeyboardButton(
                config.BTN_SUPPORT,
                url=f"https://t.me/{config.SUPPORT_GROUP.lstrip('@')}"))

    keyboard = create_keyboard(buttons, 2)
    caption = config.MSG_START.format(user_name=user_name,
                                      bot_name=config.BOT_NAME)
    return config.IMG_START, caption, keyboard


# =========================================================
# USER SETTINGS
# =========================================================
async def get_user_settings_menu(user_id: int):
    settings = await db.get_user_settings(user_id)
    upload_mode = str(settings.get("upload_mode", "telegram"))
    download_mode = str(settings.get("download_mode", "telegram"))
    is_on_hold = settings.get("is_on_hold", False)
    metadata = settings.get("metadata", False)
    thumbnail_id = settings.get("custom_thumbnail")
    filename = settings.get("custom_filename", "N/A")

    caption = config.MSG_USER_SETTINGS.format(
        upload_mode=upload_mode.capitalize(),
        download_mode=download_mode.capitalize(),
        is_on_hold="Yes" if is_on_hold else "No",
        metadata="Keep" if metadata else "Clear",
        thumbnail="Set" if thumbnail_id else "Not Set",
        filename=filename)

    buttons = [
        InlineKeyboardButton(f"📥 Downloading",
                             callback_data="us:mode:download:open"),
        InlineKeyboardButton(f"📤 Uploading",
                             callback_data="us:mode:upload:open"),
        InlineKeyboardButton(f"{config.BTN_METADATA}",
                             callback_data="us:metadata:open:main"),
        InlineKeyboardButton(f"{config.BTN_USER_HOLD}: {tick(is_on_hold)}",
                             callback_data="us:toggle:is_on_hold"),
        InlineKeyboardButton(
            f"{config.BTN_THUMBNAIL} {tick(bool(thumbnail_id))}",
            callback_data="us:ask:custom_thumbnail"),
        InlineKeyboardButton(f"{config.BTN_CLEAR_THUMB}",
                             callback_data="us:set:custom_thumbnail:none"),
        InlineKeyboardButton(f"{config.BTN_SET_FILENAME}",
                             callback_data="us:ask:custom_filename"),
        InlineKeyboardButton(f"🔙 {config.BTN_BACK}",
                             callback_data="open:start")
    ]
    return config.IMG_SETTINGS, caption, create_keyboard(buttons, 2)


async def get_download_mode_submenu(user_id: int):
    """Download mode submenu with Telegram/URL toggles"""
    settings = await db.get_user_settings(user_id)
    download_mode = str(settings.get("download_mode", "telegram"))

    caption = ("📥 **Download Mode Settings**\n\n"
               f"**Current Mode:** {download_mode.capitalize()}\n\n"
               "Select your preferred download method:")

    buttons = [
        InlineKeyboardButton(f"Telegram {tick(download_mode == 'telegram')}",
                             callback_data="us:set:download_mode:telegram"),
        InlineKeyboardButton(f"URL {tick(download_mode == 'url')}",
                             callback_data="us:set:download_mode:url"),
        InlineKeyboardButton(f"🔙 {config.BTN_BACK}",
                             callback_data="open:settings")
    ]
    return config.IMG_SETTINGS, caption, create_keyboard(buttons, 2)


async def get_upload_mode_submenu(user_id: int):
    """Upload mode submenu with Telegram/GoFile toggles"""
    settings = await db.get_user_settings(user_id)
    upload_mode = str(settings.get("upload_mode", "telegram"))

    caption = ("📤 **Upload Mode Settings**\n\n"
               f"**Current Mode:** {upload_mode.capitalize()}\n\n"
               "Select your preferred upload method:")

    buttons = [
        InlineKeyboardButton(f"Telegram {tick(upload_mode == 'telegram')}",
                             callback_data="us:set:upload_mode:telegram"),
        InlineKeyboardButton(f"GoFile {tick(upload_mode == 'gofile')}",
                             callback_data="us:set:upload_mode:gofile"),
        InlineKeyboardButton(f"🔙 {config.BTN_BACK}",
                             callback_data="open:settings")
    ]
    return config.IMG_SETTINGS, caption, create_keyboard(buttons, 2)


async def get_metadata_submenu(user_id: int):
    settings = await db.get_user_settings(user_id)
    metadata_keep = settings.get("metadata", False)

    metadata_custom = settings.get("metadata_custom", {}) or {}
    title = metadata_custom.get("title", "Not Set")
    artist = metadata_custom.get("artist", "Not Set")
    comment = metadata_custom.get("comment", "Not Set")

    caption = (
        "📝 **Metadata Configuration Studio**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Control how video metadata is handled and customize file information.\n\n"
        f"**📊 Current Settings:**\n\n"
        f"🔖 **Keep Original:** {'✅ Yes' if metadata_keep else '❌ No (Clear)'}\n"
        f"🎬 **Custom Title:** `{title}`\n"
        f"🎤 **Custom Artist:** `{artist}`\n"
        f"💬 **Custom Comment:** `{comment}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💡 **Tip:** Custom metadata overrides original values when set")

    buttons = [
        InlineKeyboardButton(f"Keep Original: {tick(metadata_keep)}",
                             callback_data="us:toggle:metadata"),
        InlineKeyboardButton(f"Set Title: {title[:15]}",
                             callback_data="us:metadata:ask:title"),
        InlineKeyboardButton(f"Set Artist: {artist[:15]}",
                             callback_data="us:metadata:ask:artist"),
        InlineKeyboardButton(f"Set Comment: {comment[:15]}",
                             callback_data="us:metadata:ask:comment"),
        InlineKeyboardButton("Clear All Custom",
                             callback_data="us:metadata:clear:all"),
        InlineKeyboardButton(f"🔙 {config.BTN_BACK}",
                             callback_data="open:settings")
    ]

    return config.IMG_SETTINGS, caption, create_keyboard(buttons, 2)


# =========================================================
# VIDEO TOOLS HUB
# =========================================================
async def get_video_tools_menu(user_id: int):
    settings = await db.get_user_settings(user_id)
    active_tool = settings.get("active_tool", "none")
    caption = config.MSG_VIDEO_TOOLS.format(active_tool=active_tool.upper())

    buttons = [
        InlineKeyboardButton(
            f"{config.BTN_MERGE} {tick(active_tool == 'merge')}",
            callback_data="vt:merge:open:main"),
        InlineKeyboardButton(
            f"{config.BTN_ENCODE} {tick(active_tool == 'encode')}",
            callback_data="vt:encode:open:main"),
        InlineKeyboardButton(
            f"{config.BTN_TRIM} {tick(active_tool == 'trim')}",
            callback_data="vt:trim:open:main"),
        InlineKeyboardButton(
            f"{config.BTN_WATERMARK} {tick(active_tool == 'watermark')}",
            callback_data="vt:watermark:open:main"),
        InlineKeyboardButton(
            f"{config.BTN_SAMPLE} {tick(active_tool == 'sample')}",
            callback_data="vt:sample:open:main"),
        InlineKeyboardButton(
            f"{config.BTN_MEDIAINFO} {tick(active_tool == 'mediainfo')}",
            callback_data="vt:toggle:mediainfo"),
        InlineKeyboardButton(
            f"{config.BTN_EXTRACT} {tick(active_tool == 'extract')}",
            callback_data="vt:extract:open:main"),
        # NEW VIDEO TOOLS
        InlineKeyboardButton(
            f"📸 Screenshot {tick(active_tool == 'screenshot')}",
            callback_data="vt:screenshot:open:main"),
        InlineKeyboardButton(
            f"🎧 Audio Remover {tick(active_tool == 'audioremover')}",
            callback_data="vt:audioremover:open:main"),
        InlineKeyboardButton(f"🖼️ HD Cover {tick(active_tool == 'hdcover')}",
                             callback_data="vt:hdcover:open:main"),
        InlineKeyboardButton(f"{config.BTN_EXTRA_TOOLS}",
                             callback_data="vt:extra:open:main"),
        InlineKeyboardButton(f"🔙 {config.BTN_BACK}",
                             callback_data="open:start")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, 2)


# =========================================================
# MERGE MENU WITH QUEUE SUPPORT
# =========================================================
async def get_vt_merge_menu(user_id: int, menu_type: str = "main"):
    from modules.queue_manager import queue_manager

    settings = await db.get_user_settings(user_id)
    active_tool = settings.get("active_tool")
    mode = settings.get("merge_mode", "video+video")

    # Get queue count
    current_queue_count = queue_manager.get_queue_count(user_id)

    # Build caption dynamically
    caption = config.MSG_VT_MERGE_MAIN.format(
        mode=mode.replace('+', ' + ').title())

    if current_queue_count > 0:
        caption += f"\n\n**📦 Merge Queue Status:**\n"
        caption += f"📊 **Items in queue:** {current_queue_count}\n"
        if current_queue_count >= 2:
            caption += f"✅ **Status:** Ready! Click 'Merge Now' to combine files.\n"
        else:
            caption += f"⏳ **Status:** Add {2 - current_queue_count} more item(s) to merge.\n"

    buttons = [
        InlineKeyboardButton(
            f"🎬 Video + Video {tick(mode == 'video+video')}",
            callback_data="vt:merge:set:merge_mode:video+video"),
        InlineKeyboardButton(
            f"🎧 Video + Audio {tick(mode == 'video+audio')}",
            callback_data="vt:merge:set:merge_mode:video+audio"),
        InlineKeyboardButton(
            f"💬 Video + Subtitle {tick(mode == 'video+subtitle')}",
            callback_data="vt:merge:set:merge_mode:video+subtitle"),
    ]

    # Add queue control buttons if queue has items
    if current_queue_count > 0:
        buttons.extend([
            InlineKeyboardButton("➕ Add More",
                                 callback_data="vt:merge:queue:wait_more"),
            InlineKeyboardButton("🗑️ Clear",
                                 callback_data="vt:merge:queue:clear"),
        ])
        if current_queue_count >= 2:
            buttons.insert(
                3,
                InlineKeyboardButton("🔀 Merge Now",
                                     callback_data="vt:merge:queue:process"))

    buttons.extend([
        InlineKeyboardButton(
            f"{config.BTN_ENABLE_TOOL} {tick(active_tool == 'merge')}",
            callback_data="vt:toggle:merge"),
        InlineKeyboardButton(f"🔙 {config.BTN_VT_BACK}",
                             callback_data="open:tools")
    ])

    return config.IMG_TOOLS, caption, create_keyboard(buttons, 2)


# =========================================================
# ENCODE MENUS
# =========================================================
async def get_vt_encode_menu(user_id: int, menu_type: str = "main"):
    settings = await db.get_user_settings(user_id)
    encode_settings = settings.get(
        "encode_settings",
        db.get_default_settings(user_id)['encode_settings'])
    active_tool = settings.get("active_tool")

    if menu_type == "main":
        return _get_vt_encode_main(encode_settings, active_tool)
    if menu_type == "vcodec":
        return _get_vt_encode_vcodec_menu(encode_settings)
    if menu_type == "crf":
        return _get_vt_encode_crf_menu(encode_settings)
    if menu_type == "preset":
        return _get_vt_encode_preset_menu(encode_settings)
    if menu_type == "resolution":
        return _get_vt_encode_resolution_menu(encode_settings)
    if menu_type == "acodec":
        return _get_vt_encode_acodec_menu(encode_settings)
    if menu_type == "abitrate":
        return _get_vt_encode_abitrate_menu(encode_settings)
    return _get_vt_encode_main(encode_settings, active_tool)


# --- ENCODE Submenus ---
def _get_vt_encode_main(settings: dict, active_tool: str):
    res = settings.get('resolution', 'source')
    if res == 'custom':
        res = settings.get('custom_resolution', 'custom')
    caption = config.MSG_VT_ENCODE_MAIN.format(
        vcodec=settings.get('vcodec', 'N/A'),
        crf=settings.get('crf', 'N/A'),
        preset=settings.get('preset', 'N/A'),
        resolution=res,
        acodec=settings.get('acodec', 'N/A'),
        abitrate=settings.get('abitrate', 'N/A'),
        suffix=settings.get('suffix', 'N/A'))
    buttons = [
        InlineKeyboardButton(f"{config.BTN_ENCODE_CRF}: {settings.get('crf')}",
                             callback_data="vt:encode:open:crf"),
        InlineKeyboardButton(
            f"{config.BTN_ENCODE_ABITRATE}: {settings.get('abitrate')}",
            callback_data="vt:encode:open:abitrate"),
        InlineKeyboardButton(f"{config.BTN_ENCODE_RESOLUTION}: {res}",
                             callback_data="vt:encode:open:resolution"),
        InlineKeyboardButton(
            f"{config.BTN_ENCODE_PRESET}: {settings.get('preset')}",
            callback_data="vt:encode:open:preset"),
        InlineKeyboardButton(
            f"{config.BTN_ENCODE_VCODEC}: {settings.get('vcodec')}",
            callback_data="vt:encode:open:vcodec"),
        InlineKeyboardButton(
            f"{config.BTN_ENCODE_ACODEC}: {settings.get('acodec')}",
            callback_data="vt:encode:open:acodec"),
        InlineKeyboardButton(
            f"{config.BTN_ENCODE_SUFFIX}: {settings.get('suffix', 'None')}",
            callback_data="vt:encode:ask:suffix"),
        InlineKeyboardButton(
            f"{config.BTN_ENABLE_TOOL} {tick(active_tool == 'encode')}",
            callback_data="vt:toggle:encode"),
        InlineKeyboardButton(f"🔙 {config.BTN_VT_BACK}",
                             callback_data="open:tools")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, 2)


def _get_vt_encode_vcodec_menu(settings: dict):
    current = settings.get('vcodec')
    caption = "🎞 Select **Video Codec**:"
    buttons = [
        InlineKeyboardButton(f"libx264 (H.264) {tick(current == 'libx264')}",
                             callback_data="vt:encode:set:vcodec:libx264"),
        InlineKeyboardButton(f"libx265 (HEVC) {tick(current == 'libx265')}",
                             callback_data="vt:encode:set:vcodec:libx265"),
        InlineKeyboardButton(f"copy (No Encode) {tick(current == 'copy')}",
                             callback_data="vt:encode:set:vcodec:copy"),
        InlineKeyboardButton("🔙 Back", callback_data="vt:encode:open:main")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, 1)


def _get_vt_encode_crf_menu(settings: dict):
    current = settings.get('crf')
    caption = "🎚 Select CRF (Quality):"
    buttons = [
        InlineKeyboardButton(f"18 (High) {tick(current == 18)}",
                             callback_data="vt:encode:set:crf:18"),
        InlineKeyboardButton(f"23 (Default) {tick(current == 23)}",
                             callback_data="vt:encode:set:crf:23"),
        InlineKeyboardButton(f"26 (Balanced) {tick(current == 26)}",
                             callback_data="vt:encode:set:crf:26"),
        InlineKeyboardButton(f"28 (Low) {tick(current == 28)}",
                             callback_data="vt:encode:set:crf:28"),
        InlineKeyboardButton("Custom...", callback_data="vt:encode:ask:crf"),
        InlineKeyboardButton("🔙 Back", callback_data="vt:encode:open:main")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, 2)


def _get_vt_encode_preset_menu(settings: dict):
    current = settings.get('preset')
    caption = "⚡ Choose Encoding Speed:"
    buttons = [
        InlineKeyboardButton(f"ultrafast {tick(current == 'ultrafast')}",
                             callback_data="vt:encode:set:preset:ultrafast"),
        InlineKeyboardButton(f"fast {tick(current == 'fast')}",
                             callback_data="vt:encode:set:preset:fast"),
        InlineKeyboardButton(f"medium {tick(current == 'medium')}",
                             callback_data="vt:encode:set:preset:medium"),
        InlineKeyboardButton(f"slow {tick(current == 'slow')}",
                             callback_data="vt:encode:set:preset:slow"),
        InlineKeyboardButton("🔙 Back", callback_data="vt:encode:open:main")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, 2)


def _get_vt_encode_resolution_menu(settings: dict):
    current_res = settings.get('resolution')
    current_vcodec = settings.get('vcodec')
    caption = "📺 Choose Resolution:"
    buttons = [
        InlineKeyboardButton(
            f"1080p (H.264) {tick(current_res == '1080p' and current_vcodec == 'libx264')}",
            callback_data="vt:encode:set:resolution:1080p"),
        InlineKeyboardButton(
            f"720p (H.264) {tick(current_res == '720p' and current_vcodec == 'libx264')}",
            callback_data="vt:encode:set:resolution:720p"),
        InlineKeyboardButton(
            f"480p (H.264) {tick(current_res == '480p' and current_vcodec == 'libx264')}",
            callback_data="vt:encode:set:resolution:480p"),
        InlineKeyboardButton(
            f"1080p (HEVC) {tick(current_res == '1080p' and current_vcodec == 'libx265')}",
            callback_data="vt:encode:set:resolution:1080p_hevc"),
        InlineKeyboardButton(
            f"720p (HEVC) {tick(current_res == '720p' and current_vcodec == 'libx265')}",
            callback_data="vt:encode:set:resolution:720p_hevc"),
        InlineKeyboardButton(
            f"480p (HEVC) {tick(current_res == '480p' and current_vcodec == 'libx265')}",
            callback_data="vt:encode:set:resolution:480p_hevc"),
        InlineKeyboardButton(f"Custom... {tick(current_res == 'custom')}",
                             callback_data="vt:encode:ask:resolution"),
        InlineKeyboardButton("🔙 Back", callback_data="vt:encode:open:main")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, 2)


def _get_vt_encode_acodec_menu(settings: dict):
    current = settings.get('acodec')
    caption = "🎵 Select **Audio Codec**:"
    buttons = [
        InlineKeyboardButton(f"aac {tick(current == 'aac')}",
                             callback_data="vt:encode:set:acodec:aac"),
        InlineKeyboardButton(f"mp3 {tick(current == 'mp3')}",
                             callback_data="vt:encode:set:acodec:mp3"),
        InlineKeyboardButton(f"opus {tick(current == 'opus')}",
                             callback_data="vt:encode:set:acodec:opus"),
        InlineKeyboardButton(f"copy (No Encode) {tick(current == 'copy')}",
                             callback_data="vt:encode:set:acodec:copy"),
        InlineKeyboardButton("🔙 Back", callback_data="vt:encode:open:main")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, 1)


def _get_vt_encode_abitrate_menu(settings: dict):
    current = settings.get('abitrate')
    caption = "🎚 Select **Audio Bitrate**:"
    buttons = [
        InlineKeyboardButton(f"64k {tick(current == '64k')}",
                             callback_data="vt:encode:set:abitrate:64k"),
        InlineKeyboardButton(f"96k {tick(current == '96k')}",
                             callback_data="vt:encode:set:abitrate:96k"),
        InlineKeyboardButton(f"128k {tick(current == '128k')}",
                             callback_data="vt:encode:set:abitrate:128k"),
        InlineKeyboardButton(f"192k {tick(current == '192k')}",
                             callback_data="vt:encode:set:abitrate:192k"),
        InlineKeyboardButton(f"256k {tick(current == '256k')}",
                             callback_data="vt:encode:set:abitrate:256k"),
        InlineKeyboardButton("Custom...",
                             callback_data="vt:encode:ask:abitrate"),
        InlineKeyboardButton("🔙 Back", callback_data="vt:encode:open:main")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, 2)


# =========================================================
# TRIM MENU
# =========================================================
async def get_vt_trim_menu(user_id: int, menu_type: str = "main"):
    settings = await db.get_user_settings(user_id)
    trim = settings.get("trim_settings",
                        db.get_default_settings(user_id)['trim_settings'])
    active_tool = settings.get("active_tool")
    caption = config.MSG_VT_TRIM_MAIN.format(start=trim.get('start'),
                                             end=trim.get('end'))
    buttons = [
        InlineKeyboardButton(f"Start: {trim.get('start')}",
                             callback_data="vt:trim:ask:start"),
        InlineKeyboardButton(f"End: {trim.get('end')}",
                             callback_data="vt:trim:ask:end"),
        InlineKeyboardButton(
            f"{config.BTN_ENABLE_TOOL} {tick(active_tool == 'trim')}",
            callback_data="vt:toggle:trim"),
        InlineKeyboardButton(f"🔙 {config.BTN_VT_BACK}",
                             callback_data="open:tools")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, 1)


# --- 3.5 Watermark Menus ---
async def get_vt_watermark_menu(user_id: int, menu_type: str = "main"):
    """Handles ALL watermark sub-menus."""
    settings = await db.get_user_settings(user_id)
    watermark_settings = settings.get(
        "watermark_settings",
        db.get_default_settings(user_id)['watermark_settings'])
    active_tool = settings.get("active_tool")

    if menu_type == "main":
        return _get_vt_watermark_main(watermark_settings, active_tool)
    if menu_type == "type":
        return _get_vt_watermark_type_menu(watermark_settings)
    if menu_type == "position":
        return _get_vt_watermark_position_menu(watermark_settings)

    return _get_vt_watermark_main(watermark_settings, active_tool)


def _get_vt_watermark_main(settings: dict, active_tool: str):
    """Builds the main Watermark hub panel."""
    text = settings.get('text', 'N/A')
    if len(text) > 20:
        text = text[:20] + "..."
    image = "Set" if settings.get('image_id') else "Not Set"

    caption = config.MSG_VT_WATERMARK_MAIN.format(
        type=settings.get('type', 'none'),
        text=text,
        image=image,
        position=settings.get('position', 'N/A'),
        opacity=settings.get('opacity', 0.7))
    buttons = [
        InlineKeyboardButton(
            f"{config.BTN_WATERMARK_TYPE}: {settings.get('type')}",
            callback_data="vt:watermark:open:type"),
        InlineKeyboardButton(
            f"{config.BTN_WATERMARK_POSITION}: {settings.get('position')}",
            callback_data="vt:watermark:open:position"),
        InlineKeyboardButton(f"{config.BTN_WATERMARK_TEXT}",
                             callback_data="vt:watermark:ask:text"),
        InlineKeyboardButton(f"{config.BTN_WATERMARK_IMAGE}",
                             callback_data="vt:watermark:ask:image"),
        InlineKeyboardButton(
            f"{config.BTN_ENABLE_TOOL} {tick(active_tool == 'watermark')}",
            callback_data="vt:toggle:watermark"),
        InlineKeyboardButton(f"🔙 {config.BTN_VT_BACK}",
                             callback_data="open:tools")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, columns=2)


def _get_vt_watermark_type_menu(settings: dict):
    """Sub-menu for Watermark Type."""
    current = settings.get('type')
    caption = "Select a **Watermark Type**:"
    buttons = [
        InlineKeyboardButton(f"Text {tick(current == 'text')}",
                             callback_data="vt:watermark:set:type:text"),
        InlineKeyboardButton(f"Image {tick(current == 'image')}",
                             callback_data="vt:watermark:set:type:image"),
        InlineKeyboardButton(f"None {tick(current == 'none')}",
                             callback_data="vt:watermark:set:type:none"),
        InlineKeyboardButton(f"🔙 {config.BTN_BACK}",
                             callback_data="vt:watermark:open:main")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, columns=1)


def _get_vt_watermark_position_menu(settings: dict):
    """Sub-menu for Watermark Position."""
    current = settings.get('position')
    caption = config.MSG_VT_WATERMARK_POSITION_MENU
    buttons = [
        InlineKeyboardButton(
            f"Top Left {tick(current == 'top_left')}",
            callback_data="vt:watermark:set:position:top_left"),
        InlineKeyboardButton(
            f"Top Right {tick(current == 'top_right')}",
            callback_data="vt:watermark:set:position:top_right"),
        InlineKeyboardButton(
            f"Bottom Left {tick(current == 'bottom_left')}",
            callback_data="vt:watermark:set:position:bottom_left"),
        InlineKeyboardButton(
            f"Bottom Right {tick(current == 'bottom_right')}",
            callback_data="vt:watermark:set:position:bottom_right"),
        InlineKeyboardButton(f"Center {tick(current == 'center')}",
                             callback_data="vt:watermark:set:position:center"),
        InlineKeyboardButton(f"🔙 {config.BTN_BACK}",
                             callback_data="vt:watermark:open:main")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, columns=2)


# --- 3.6 Sample Menus ---
async def get_vt_sample_menu(user_id: int, menu_type: str = "main"):
    """Handles ALL sample sub-menus."""
    settings = await db.get_user_settings(user_id)
    sample_settings = settings.get(
        "sample_settings",
        db.get_default_settings(user_id)['sample_settings'])
    active_tool = settings.get("active_tool")

    if menu_type == "main":
        return _get_vt_sample_main(sample_settings, active_tool)
    if menu_type == "from":
        return _get_vt_sample_from_menu(sample_settings)

    return _get_vt_sample_main(sample_settings, active_tool)


def _get_vt_sample_main(settings: dict, active_tool: str):
    """Builds the main Sample hub panel."""
    caption = config.MSG_VT_SAMPLE_MAIN.format(
        duration=settings.get('duration', 30),
        from_point=settings.get('from_point', 'start'))
    buttons = [
        InlineKeyboardButton(
            f"{config.BTN_SAMPLE_DURATION}: {settings.get('duration')}s",
            callback_data="vt:sample:ask:duration"),
        InlineKeyboardButton(
            f"{config.BTN_SAMPLE_FROM}: {settings.get('from_point')}",
            callback_data="vt:sample:open:from"),
        InlineKeyboardButton(
            f"{config.BTN_ENABLE_TOOL} {tick(active_tool == 'sample')}",
            callback_data="vt:toggle:sample"),
        InlineKeyboardButton(f"🔙 {config.BTN_VT_BACK}",
                             callback_data="open:tools")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, columns=1)


def _get_vt_sample_from_menu(settings: dict):
    """Sub-menu for Sample From."""
    current = settings.get('from_point')
    caption = config.MSG_VT_SAMPLE_FROM_MENU
    buttons = [
        InlineKeyboardButton(f"Start {tick(current == 'start')}",
                             callback_data="vt:sample:set:from_point:start"),
        InlineKeyboardButton(f"Middle {tick(current == 'middle')}",
                             callback_data="vt:sample:set:from_point:middle"),
        InlineKeyboardButton(f"End {tick(current == 'end')}",
                             callback_data="vt:sample:set:from_point:end"),
        InlineKeyboardButton(f"🔙 {config.BTN_BACK}",
                             callback_data="vt:sample:open:main")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, columns=1)


# =========================================================
# NEW TOOLS MENUS (Rotate, Flip, Speed, Volume, Crop, GIF, Reverse, Extract Thumbnail)
# =========================================================


# --- 3.7 Rotate Menu ---
async def get_vt_rotate_menu(user_id: int, menu_type: str = "main"):
    """Handles rotate menu."""
    settings = await db.get_user_settings(user_id)
    rotate_settings = settings.get(
        "rotate_settings",
        db.get_default_settings(user_id)['rotate_settings'])
    active_tool = settings.get("active_tool")

    if menu_type == "main":
        return _get_vt_rotate_main(rotate_settings, active_tool)
    elif menu_type == "angle":
        return _get_vt_rotate_angle_menu(rotate_settings)
    return _get_vt_rotate_main(rotate_settings, active_tool)


def _get_vt_rotate_main(settings: dict, active_tool: str):
    """Main rotate panel."""
    caption = config.MSG_VT_ROTATE_MAIN.format(angle=settings.get('angle', 90))
    buttons = [
        InlineKeyboardButton(
            f"{config.BTN_ROTATE_ANGLE}: {settings.get('angle')}°",
            callback_data="vt:rotate:open:angle"),
        InlineKeyboardButton(
            f"{config.BTN_ENABLE_TOOL} {tick(active_tool == 'rotate')}",
            callback_data="vt:toggle:rotate"),
        InlineKeyboardButton(f"🔙 {config.BTN_VT_BACK}",
                             callback_data="open:tools")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, columns=1)


def _get_vt_rotate_angle_menu(settings: dict):
    """Rotation angle selection menu."""
    current = settings.get('angle', 90)
    caption = config.MSG_VT_ROTATE_ANGLE_MENU
    buttons = [
        InlineKeyboardButton(f"90° {tick(current == 90)}",
                             callback_data="vt:rotate:set:angle:90"),
        InlineKeyboardButton(f"180° {tick(current == 180)}",
                             callback_data="vt:rotate:set:angle:180"),
        InlineKeyboardButton(f"270° {tick(current == 270)}",
                             callback_data="vt:rotate:set:angle:270"),
        InlineKeyboardButton(f"🔙 {config.BTN_BACK}",
                             callback_data="vt:rotate:open:main")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, columns=1)


# --- 3.8 Flip Menu ---
async def get_vt_flip_menu(user_id: int, menu_type: str = "main"):
    """Handles flip menu."""
    settings = await db.get_user_settings(user_id)
    flip_settings = settings.get(
        "flip_settings",
        db.get_default_settings(user_id)['flip_settings'])
    active_tool = settings.get("active_tool")

    if menu_type == "main":
        return _get_vt_flip_main(flip_settings, active_tool)
    elif menu_type == "direction":
        return _get_vt_flip_direction_menu(flip_settings)
    return _get_vt_flip_main(flip_settings, active_tool)


def _get_vt_flip_main(settings: dict, active_tool: str):
    """Main flip panel."""
    caption = config.MSG_VT_FLIP_MAIN.format(
        direction=settings.get('direction', 'horizontal'))
    buttons = [
        InlineKeyboardButton(
            f"{config.BTN_FLIP_DIRECTION}: {settings.get('direction')}",
            callback_data="vt:flip:open:direction"),
        InlineKeyboardButton(
            f"{config.BTN_ENABLE_TOOL} {tick(active_tool == 'flip')}",
            callback_data="vt:toggle:flip"),
        InlineKeyboardButton(f"🔙 {config.BTN_VT_BACK}",
                             callback_data="open:tools")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, columns=1)


def _get_vt_flip_direction_menu(settings: dict):
    """Flip direction selection menu."""
    current = settings.get('direction', 'horizontal')
    caption = config.MSG_VT_FLIP_DIRECTION_MENU
    buttons = [
        InlineKeyboardButton(f"Horizontal {tick(current == 'horizontal')}",
                             callback_data="vt:flip:set:direction:horizontal"),
        InlineKeyboardButton(f"Vertical {tick(current == 'vertical')}",
                             callback_data="vt:flip:set:direction:vertical"),
        InlineKeyboardButton(f"🔙 {config.BTN_BACK}",
                             callback_data="vt:flip:open:main")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, columns=1)


# --- 3.9 Speed Menu ---
async def get_vt_speed_menu(user_id: int, menu_type: str = "main"):
    """Handles speed adjustment menu."""
    settings = await db.get_user_settings(user_id)
    speed_settings = settings.get(
        "speed_settings",
        db.get_default_settings(user_id)['speed_settings'])
    active_tool = settings.get("active_tool")

    if menu_type == "main":
        return _get_vt_speed_main(speed_settings, active_tool)
    elif menu_type == "multiplier":
        return _get_vt_speed_multiplier_menu(speed_settings)
    return _get_vt_speed_main(speed_settings, active_tool)


def _get_vt_speed_main(settings: dict, active_tool: str):
    """Main speed panel."""
    caption = config.MSG_VT_SPEED_MAIN.format(speed=settings.get('speed', 1.0))
    buttons = [
        InlineKeyboardButton(
            f"{config.BTN_SPEED_MULTIPLIER}: {settings.get('speed')}x",
            callback_data="vt:speed:open:multiplier"),
        InlineKeyboardButton(
            f"{config.BTN_ENABLE_TOOL} {tick(active_tool == 'speed')}",
            callback_data="vt:toggle:speed"),
        InlineKeyboardButton(f"🔙 {config.BTN_VT_BACK}",
                             callback_data="open:tools")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, columns=1)


def _get_vt_speed_multiplier_menu(settings: dict):
    """Speed multiplier selection menu."""
    current = settings.get('speed', 1.0)
    caption = config.MSG_VT_SPEED_MENU
    buttons = [
        InlineKeyboardButton(f"0.5x {tick(current == 0.5)}",
                             callback_data="vt:speed:set:speed:0.5"),
        InlineKeyboardButton(f"0.75x {tick(current == 0.75)}",
                             callback_data="vt:speed:set:speed:0.75"),
        InlineKeyboardButton(f"1.0x {tick(current == 1.0)}",
                             callback_data="vt:speed:set:speed:1.0"),
        InlineKeyboardButton(f"1.25x {tick(current == 1.25)}",
                             callback_data="vt:speed:set:speed:1.25"),
        InlineKeyboardButton(f"1.5x {tick(current == 1.5)}",
                             callback_data="vt:speed:set:speed:1.5"),
        InlineKeyboardButton(f"2.0x {tick(current == 2.0)}",
                             callback_data="vt:speed:set:speed:2.0"),
        InlineKeyboardButton(f"Custom...", callback_data="vt:speed:ask:speed"),
        InlineKeyboardButton(f"🔙 {config.BTN_BACK}",
                             callback_data="vt:speed:open:main")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, columns=2)


# --- 3.10 Volume Menu ---
async def get_vt_volume_menu(user_id: int, menu_type: str = "main"):
    """Handles volume adjustment menu."""
    settings = await db.get_user_settings(user_id)
    volume_settings = settings.get(
        "volume_settings",
        db.get_default_settings(user_id)['volume_settings'])
    active_tool = settings.get("active_tool")

    if menu_type == "main":
        return _get_vt_volume_main(volume_settings, active_tool)
    elif menu_type == "level":
        return _get_vt_volume_level_menu(volume_settings)
    return _get_vt_volume_main(volume_settings, active_tool)


def _get_vt_volume_main(settings: dict, active_tool: str):
    """Main volume panel."""
    caption = config.MSG_VT_VOLUME_MAIN.format(
        volume=settings.get('volume', 100))
    buttons = [
        InlineKeyboardButton(
            f"{config.BTN_VOLUME_LEVEL}: {settings.get('volume')}%",
            callback_data="vt:volume:open:level"),
        InlineKeyboardButton(
            f"{config.BTN_ENABLE_TOOL} {tick(active_tool == 'volume')}",
            callback_data="vt:toggle:volume"),
        InlineKeyboardButton(f"🔙 {config.BTN_VT_BACK}",
                             callback_data="open:tools")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, columns=1)


def _get_vt_volume_level_menu(settings: dict):
    """Volume level selection menu."""
    current = settings.get('volume', 100)
    caption = config.MSG_VT_VOLUME_MENU
    buttons = [
        InlineKeyboardButton(f"50% {tick(current == 50)}",
                             callback_data="vt:volume:set:volume:50"),
        InlineKeyboardButton(f"75% {tick(current == 75)}",
                             callback_data="vt:volume:set:volume:75"),
        InlineKeyboardButton(f"100% {tick(current == 100)}",
                             callback_data="vt:volume:set:volume:100"),
        InlineKeyboardButton(f"150% {tick(current == 150)}",
                             callback_data="vt:volume:set:volume:150"),
        InlineKeyboardButton(f"200% {tick(current == 200)}",
                             callback_data="vt:volume:set:volume:200"),
        InlineKeyboardButton(f"Custom...",
                             callback_data="vt:volume:ask:volume"),
        InlineKeyboardButton(f"🔙 {config.BTN_BACK}",
                             callback_data="vt:volume:open:main")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, columns=2)


# --- 3.11 Crop Menu ---
async def get_vt_crop_menu(user_id: int, menu_type: str = "main"):
    """Handles crop menu."""
    settings = await db.get_user_settings(user_id)
    crop_settings = settings.get(
        "crop_settings",
        db.get_default_settings(user_id)['crop_settings'])
    active_tool = settings.get("active_tool")

    if menu_type == "main":
        return _get_vt_crop_main(crop_settings, active_tool)
    elif menu_type == "aspect":
        return _get_vt_crop_aspect_menu(crop_settings)
    return _get_vt_crop_main(crop_settings, active_tool)


def _get_vt_crop_main(settings: dict, active_tool: str):
    """Main crop panel."""
    caption = config.MSG_VT_CROP_MAIN.format(
        aspect_ratio=settings.get('aspect_ratio', '16:9'))
    buttons = [
        InlineKeyboardButton(
            f"{config.BTN_CROP_ASPECT}: {settings.get('aspect_ratio')}",
            callback_data="vt:crop:open:aspect"),
        InlineKeyboardButton(
            f"{config.BTN_ENABLE_TOOL} {tick(active_tool == 'crop')}",
            callback_data="vt:toggle:crop"),
        InlineKeyboardButton(f"🔙 {config.BTN_VT_BACK}",
                             callback_data="open:tools")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, columns=1)


def _get_vt_crop_aspect_menu(settings: dict):
    """Aspect ratio selection menu."""
    current = settings.get('aspect_ratio', '16:9')
    caption = config.MSG_VT_CROP_ASPECT_MENU
    buttons = [
        InlineKeyboardButton(f"16:9 {tick(current == '16:9')}",
                             callback_data="vt:crop:set:aspect_ratio:16:9"),
        InlineKeyboardButton(f"4:3 {tick(current == '4:3')}",
                             callback_data="vt:crop:set:aspect_ratio:4:3"),
        InlineKeyboardButton(f"1:1 {tick(current == '1:1')}",
                             callback_data="vt:crop:set:aspect_ratio:1:1"),
        InlineKeyboardButton(f"9:16 {tick(current == '9:16')}",
                             callback_data="vt:crop:set:aspect_ratio:9:16"),
        InlineKeyboardButton(f"🔙 {config.BTN_BACK}",
                             callback_data="vt:crop:open:main")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, columns=2)


# --- 3.12 GIF Converter Menu ---
async def get_vt_gif_menu(user_id: int, menu_type: str = "main"):
    """Handles GIF converter menu."""
    settings = await db.get_user_settings(user_id)
    gif_settings = settings.get(
        "gif_settings",
        db.get_default_settings(user_id)['gif_settings'])
    active_tool = settings.get("active_tool")

    if menu_type == "main":
        return _get_vt_gif_main(gif_settings, active_tool)
    elif menu_type == "fps":
        return _get_vt_gif_fps_menu(gif_settings)
    elif menu_type == "quality":
        return _get_vt_gif_quality_menu(gif_settings)
    elif menu_type == "scale":
        return _get_vt_gif_scale_menu(gif_settings)
    return _get_vt_gif_main(gif_settings, active_tool)


def _get_vt_gif_main(settings: dict, active_tool: str):
    """Main GIF panel."""
    caption = config.MSG_VT_GIF_MAIN.format(fps=settings.get('fps', 10),
                                            quality=settings.get(
                                                'quality', 'medium'),
                                            scale=settings.get('scale', 480))
    buttons = [
        InlineKeyboardButton(f"{config.BTN_GIF_FPS}: {settings.get('fps')}",
                             callback_data="vt:gif:open:fps"),
        InlineKeyboardButton(
            f"{config.BTN_GIF_QUALITY}: {settings.get('quality')}",
            callback_data="vt:gif:open:quality"),
        InlineKeyboardButton(
            f"{config.BTN_GIF_SCALE}: {settings.get('scale')}p",
            callback_data="vt:gif:open:scale"),
        InlineKeyboardButton(
            f"{config.BTN_ENABLE_TOOL} {tick(active_tool == 'gif')}",
            callback_data="vt:toggle:gif"),
        InlineKeyboardButton(f"🔙 {config.BTN_VT_BACK}",
                             callback_data="open:tools")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, columns=1)


def _get_vt_gif_fps_menu(settings: dict):
    """GIF FPS selection menu."""
    current = settings.get('fps', 10)
    caption = config.MSG_VT_GIF_FPS_MENU
    buttons = [
        InlineKeyboardButton(f"10 {tick(current == 10)}",
                             callback_data="vt:gif:set:fps:10"),
        InlineKeyboardButton(f"15 {tick(current == 15)}",
                             callback_data="vt:gif:set:fps:15"),
        InlineKeyboardButton(f"20 {tick(current == 20)}",
                             callback_data="vt:gif:set:fps:20"),
        InlineKeyboardButton(f"25 {tick(current == 25)}",
                             callback_data="vt:gif:set:fps:25"),
        InlineKeyboardButton(f"Custom...", callback_data="vt:gif:ask:fps"),
        InlineKeyboardButton(f"🔙 {config.BTN_BACK}",
                             callback_data="vt:gif:open:main")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, columns=2)


def _get_vt_gif_quality_menu(settings: dict):
    """GIF quality selection menu."""
    current = settings.get('quality', 'medium')
    caption = config.MSG_VT_GIF_QUALITY_MENU
    buttons = [
        InlineKeyboardButton(f"Low {tick(current == 'low')}",
                             callback_data="vt:gif:set:quality:low"),
        InlineKeyboardButton(f"Medium {tick(current == 'medium')}",
                             callback_data="vt:gif:set:quality:medium"),
        InlineKeyboardButton(f"High {tick(current == 'high')}",
                             callback_data="vt:gif:set:quality:high"),
        InlineKeyboardButton(f"🔙 {config.BTN_BACK}",
                             callback_data="vt:gif:open:main")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, columns=1)


def _get_vt_gif_scale_menu(settings: dict):
    """GIF scale selection menu."""
    current = settings.get('scale', 480)
    caption = config.MSG_VT_GIF_SCALE_MENU
    buttons = [
        InlineKeyboardButton(f"240p {tick(current == 240)}",
                             callback_data="vt:gif:set:scale:240"),
        InlineKeyboardButton(f"360p {tick(current == 360)}",
                             callback_data="vt:gif:set:scale:360"),
        InlineKeyboardButton(f"480p {tick(current == 480)}",
                             callback_data="vt:gif:set:scale:480"),
        InlineKeyboardButton(f"720p {tick(current == 720)}",
                             callback_data="vt:gif:set:scale:720"),
        InlineKeyboardButton(f"Custom...", callback_data="vt:gif:ask:scale"),
        InlineKeyboardButton(f"🔙 {config.BTN_BACK}",
                             callback_data="vt:gif:open:main")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, columns=2)


# --- 3.13 Reverse Menu ---
async def get_vt_reverse_menu(user_id: int, menu_type: str = "main"):
    """Handles reverse menu."""
    settings = await db.get_user_settings(user_id)
    active_tool = settings.get("active_tool")
    return _get_vt_reverse_main(active_tool)


def _get_vt_reverse_main(active_tool: str):
    """Main reverse panel."""
    caption = config.MSG_VT_REVERSE_MAIN
    buttons = [
        InlineKeyboardButton(
            f"{config.BTN_ENABLE_TOOL} {tick(active_tool == 'reverse')}",
            callback_data="vt:toggle:reverse"),
        InlineKeyboardButton(f"🔙 {config.BTN_VT_BACK}",
                             callback_data="open:tools")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, columns=1)


# --- 3.14 Extract Thumbnail Menu ---
async def get_vt_extract_thumb_menu(user_id: int, menu_type: str = "main"):
    """Handles thumbnail extraction menu."""
    settings = await db.get_user_settings(user_id)
    thumb_settings = settings.get(
        "extract_thumb_settings",
        db.get_default_settings(user_id)['extract_thumb_settings'])
    active_tool = settings.get("active_tool")

    if menu_type == "main":
        return _get_vt_extract_thumb_main(thumb_settings, active_tool)
    elif menu_type == "mode":
        return _get_vt_extract_thumb_mode_menu(thumb_settings)
    return _get_vt_extract_thumb_main(thumb_settings, active_tool)


def _get_vt_extract_thumb_main(settings: dict, active_tool: str):
    """Main extract thumbnail panel."""
    caption = config.MSG_VT_EXTRACT_THUMB_MAIN.format(
        mode=settings.get('mode', 'single'),
        timestamp=settings.get('timestamp', '00:00:05'),
        count=settings.get('count', 5))
    buttons = [
        InlineKeyboardButton(
            f"{config.BTN_THUMB_MODE}: {settings.get('mode')}",
            callback_data="vt:extract_thumb:open:mode"),
        InlineKeyboardButton(
            f"{config.BTN_THUMB_TIMESTAMP}: {settings.get('timestamp')}",
            callback_data="vt:extract_thumb:ask:timestamp"),
        InlineKeyboardButton(
            f"{config.BTN_THUMB_COUNT}: {settings.get('count')}",
            callback_data="vt:extract_thumb:ask:count"),
        InlineKeyboardButton(
            f"{config.BTN_ENABLE_TOOL} {tick(active_tool == 'extract_thumb')}",
            callback_data="vt:toggle:extract_thumb"),
        InlineKeyboardButton(f"🔙 {config.BTN_VT_BACK}",
                             callback_data="open:tools")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, columns=1)


def _get_vt_extract_thumb_mode_menu(settings: dict):
    """Thumbnail extraction mode selection menu."""
    current = settings.get('mode', 'single')
    caption = config.MSG_VT_THUMB_MODE_MENU
    buttons = [
        InlineKeyboardButton(f"Single {tick(current == 'single')}",
                             callback_data="vt:extract_thumb:set:mode:single"),
        InlineKeyboardButton(
            f"Interval {tick(current == 'interval')}",
            callback_data="vt:extract_thumb:set:mode:interval"),
        InlineKeyboardButton(f"🔙 {config.BTN_BACK}",
                             callback_data="vt:extract_thumb:open:main")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, columns=1)


# =========================================================
# NEW: EXTRACT MENU
# =========================================================
async def get_vt_extract_menu(user_id: int, menu_type: str = "main"):
    """Handles the Extract submenu."""
    settings = await db.get_user_settings(user_id)
    extract_settings = settings.get(
        "extract_settings",
        db.get_default_settings(user_id)['extract_settings'])
    active_tool = settings.get("active_tool")

    mode = extract_settings.get('mode', 'video')
    caption = config.MSG_VT_EXTRACT_MAIN.format(mode=mode.capitalize())

    buttons = [
        InlineKeyboardButton(
            f"{config.BTN_EXTRACT_VIDEO} {tick(mode == 'video')}",
            callback_data="vt:extract:set:mode:video"),
        InlineKeyboardButton(
            f"{config.BTN_EXTRACT_AUDIO} {tick(mode == 'audio')}",
            callback_data="vt:extract:set:mode:audio"),
        InlineKeyboardButton(
            f"{config.BTN_EXTRACT_SUBTITLES} {tick(mode == 'subtitles')}",
            callback_data="vt:extract:set:mode:subtitles"),
        InlineKeyboardButton(
            f"{config.BTN_EXTRACT_THUMBNAILS} {tick(mode == 'thumbnails')}",
            callback_data="vt:extract:set:mode:thumbnails"),
        InlineKeyboardButton(
            f"{config.BTN_ENABLE_TOOL} {tick(active_tool == 'extract')}",
            callback_data="vt:toggle:extract"),
        InlineKeyboardButton(f"🔙 {config.BTN_VT_BACK}",
                             callback_data="open:tools")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, columns=2)


# =========================================================
# NEW: EXTRA TOOLS MENU
# =========================================================
async def get_vt_extra_menu(user_id: int, menu_type: str = "main"):
    """Handles the Extra Tools submenu."""
    settings = await db.get_user_settings(user_id)
    active_tool = settings.get("active_tool", "none")

    caption = config.MSG_VT_EXTRA_TOOLS_MAIN

    buttons = [
        InlineKeyboardButton(
            f"{config.BTN_ROTATE} {tick(active_tool == 'rotate')}",
            callback_data="vt:rotate:open:main"),
        InlineKeyboardButton(
            f"{config.BTN_FLIP} {tick(active_tool == 'flip')}",
            callback_data="vt:flip:open:main"),
        InlineKeyboardButton(
            f"{config.BTN_SPEED} {tick(active_tool == 'speed')}",
            callback_data="vt:speed:open:main"),
        InlineKeyboardButton(
            f"{config.BTN_VOLUME} {tick(active_tool == 'volume')}",
            callback_data="vt:volume:open:main"),
        InlineKeyboardButton(
            f"{config.BTN_CROP} {tick(active_tool == 'crop')}",
            callback_data="vt:crop:open:main"),
        InlineKeyboardButton(f"{config.BTN_GIF} {tick(active_tool == 'gif')}",
                             callback_data="vt:gif:open:main"),
        InlineKeyboardButton(
            f"{config.BTN_REVERSE} {tick(active_tool == 'reverse')}",
            callback_data="vt:reverse:open:main"),
        InlineKeyboardButton(f"🔙 {config.BTN_VT_BACK}",
                             callback_data="open:tools")
    ]
    return config.IMG_TOOLS, caption, create_keyboard(buttons, columns=2)


# =========================================================
# NEW VIDEO TOOLS: Screenshot, Audio Remover, HD Cover
# =========================================================


async def get_vt_screenshot_menu(user_id: int, menu_type: str = "main"):
    """
    Screenshot tool menu.
    Supports setting screenshot count and toggling the tool.
    """
    settings = await db.get_user_settings(user_id)
    screenshot_settings = settings.get(
        "screenshot_settings",
        db.get_default_settings(user_id)['screenshot_settings'])
    active_tool = settings.get("active_tool")

    if menu_type == "main":
        caption = config.MSG_VT_SCREENSHOT_MAIN.format(
            count=screenshot_settings.get('count', 5))
        buttons = [
            InlineKeyboardButton(
                f"📸 Count: {screenshot_settings.get('count', 5)}",
                callback_data="vt:screenshot:open:count"),
            InlineKeyboardButton(
                f"{config.BTN_ENABLE_TOOL} {tick(active_tool == 'screenshot')}",
                callback_data="vt:toggle:screenshot"),
            InlineKeyboardButton(f"🔙 {config.BTN_VT_BACK}",
                                 callback_data="open:tools")
        ]
        return config.IMG_TOOLS, caption, create_keyboard(buttons, columns=1)

    if menu_type == "count":
        current = screenshot_settings.get('count', 5)
        caption = "📸 Choose number of screenshots:"
        buttons = [
            InlineKeyboardButton(f"1 {tick(current == 1)}",
                                 callback_data="vt:screenshot:set:count:1"),
            InlineKeyboardButton(f"3 {tick(current == 3)}",
                                 callback_data="vt:screenshot:set:count:3"),
            InlineKeyboardButton(f"5 {tick(current == 5)}",
                                 callback_data="vt:screenshot:set:count:5"),
            InlineKeyboardButton(f"10 {tick(current == 10)}",
                                 callback_data="vt:screenshot:set:count:10"),
            InlineKeyboardButton("Custom...",
                                 callback_data="vt:screenshot:ask:count"),
            InlineKeyboardButton(f"🔙 {config.BTN_BACK}",
                                 callback_data="vt:screenshot:open:main")
        ]
        return config.IMG_TOOLS, caption, create_keyboard(buttons, columns=2)

    # fallback
    return config.IMG_TOOLS, "⚠️ Invalid screenshot menu.", create_keyboard([
        InlineKeyboardButton("🔙 Back", callback_data="vt:screenshot:open:main")
    ])


async def get_vt_audioremover_menu(user_id: int, menu_type: str = "main"):
    """
    Audio Remover tool menu.
    Options: remove audio, keep original, enable tool.
    """
    settings = await db.get_user_settings(user_id)
    ar_settings = settings.get("audioremover_settings", {"mode": "remove"})
    active_tool = settings.get("active_tool")

    if menu_type == "main":
        mode = ar_settings.get("mode", "remove")
        MSG_VT_AUDIO_REMOVER_MAIN = ("🔇 **Audio Remover Tool**\n\n"
                                     "Current Mode: **{mode}**\n\n"
                                     "Choose what you want to do:")
        caption = MSG_VT_AUDIO_REMOVER_MAIN.format(
            mode=mode.capitalize() if mode else "N/A")
        buttons = [
            InlineKeyboardButton(
                f"Remove Audio {tick(mode == 'remove')}",
                callback_data="vt:audioremover:set:mode:remove"),
            InlineKeyboardButton(
                f"Keep Audio {tick(mode == 'keep')}",
                callback_data="vt:audioremover:set:mode:keep"),
            InlineKeyboardButton(
                f"{config.BTN_ENABLE_TOOL} {tick(active_tool == 'audioremover')}",
                callback_data="vt:toggle:audioremover"),
            InlineKeyboardButton(f"🔙 {config.BTN_VT_BACK}",
                                 callback_data="open:tools")
        ]
        return config.IMG_TOOLS, caption, create_keyboard(buttons, columns=1)

    # fallback
    return config.IMG_TOOLS, "⚠️ Invalid audio remover menu.", create_keyboard(
        [
            InlineKeyboardButton("🔙 Back",
                                 callback_data="vt:audioremover:open:main")
        ])


async def get_vt_hdcover_menu(user_id: int, menu_type: str = "main"):
    """
    HD Cover menu: view/set/clear temporary cover and enable tool.
    Uses db.save_temp_cover/get_temp_cover/delete_temp_cover
    """
    settings = await db.get_user_settings(user_id)
    active_tool = settings.get("active_tool")
    cover_file_id = await db.get_temp_cover(user_id)

    if menu_type == "main":
        status_text = "Set" if cover_file_id else "Not Set"
        caption = config.MSG_VT_HD_COVER_MAIN.format(status=status_text)
        buttons = [
            InlineKeyboardButton(f"Upload Cover",
                                 callback_data="vt:hdcover:ask:upload"),
            InlineKeyboardButton(f"Clear Cover {tick(bool(cover_file_id))}",
                                 callback_data="vt:hdcover:clear"),
            InlineKeyboardButton(
                f"{config.BTN_ENABLE_TOOL} {tick(active_tool == 'hdcover')}",
                callback_data="vt:toggle:hdcover"),
            InlineKeyboardButton(f"🔙 {config.BTN_VT_BACK}",
                                 callback_data="open:tools")
        ]
        return config.IMG_TOOLS, caption, create_keyboard(buttons, columns=1)

    # fallback
    return config.IMG_TOOLS, "⚠️ Invalid HD Cover menu.", create_keyboard(
        [InlineKeyboardButton("🔙 Back", callback_data="vt:hdcover:open:main")])


# ==================== 4. ADMIN MENU ====================


async def get_admin_menu():
    """Generates the /admin menu."""
    from modules.bot_state import get_bot_mode
    from modules.utils import process_manager

    bot_mode = get_bot_mode()
    task_count = len(process_manager.active_processes)
    mode_btn_text = f"Mode: {bot_mode} {'✅' if bot_mode == 'ACTIVE' else '⏸️'}"

    caption = config.MSG_ADMIN_PANEL.format(bot_mode=bot_mode,
                                            task_count=task_count)

    buttons = [
        InlineKeyboardButton(mode_btn_text, callback_data="admin:toggle:mode"),
        InlineKeyboardButton(f"{config.BTN_ADMIN_TASKS} ({task_count})",
                             callback_data="admin:show:tasks"),
        InlineKeyboardButton(config.BTN_ADMIN_STATS,
                             callback_data="admin:show:stats"),
        InlineKeyboardButton(config.BTN_ADMIN_BROADCAST,
                             callback_data="admin:broadcast"),
        InlineKeyboardButton(config.BTN_ADMIN_RESTART,
                             callback_data="admin:restart"),
        InlineKeyboardButton(f"🔙 {config.BTN_BACK}",
                             callback_data="open:start")
    ]

    keyboard = create_keyboard(buttons, 2)
    return config.IMG_ADMIN, caption, keyboard
