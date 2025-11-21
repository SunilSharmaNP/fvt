# config.py (v7.0 - Professional Enhanced)
# SS Video Workstation Bot - Complete Configuration
# All Bugs Fixed & Production Ready
# ==================================================

import os
import logging
from dotenv import load_dotenv

# Load environment variables from config.env
load_dotenv('config.env')

# Setup logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== HELPER FUNCTION (Module-level) ====================

def clean_value(value_str: str) -> str:
    """Cleans env variables from comments (#) and extra quotes/spaces"""
    if not value_str:
        return ""
    cleaned = value_str.split('#')[0]
    cleaned = cleaned.strip().strip('"').strip("'").strip()
    return cleaned

class Config:
    """
    Configuration class for the bot.
    Reads all necessary environment variables.
    """

    # ==================== TELEGRAM BOT CONFIGURATION ====================

    # Clean and convert API_ID (required, must be integer)
    _api_id_raw = os.environ.get("API_ID", "")
    try:
        API_ID = int(clean_value(_api_id_raw)) if _api_id_raw else None
    except ValueError:
        logger.error(f"API_ID must be a valid integer, got: {_api_id_raw}")
        API_ID = None

    API_HASH = clean_value(os.environ.get("API_HASH", ""))
    BOT_TOKEN = clean_value(os.environ.get("BOT_TOKEN", ""))

    # ==================== MONGODB CONFIGURATION ====================

    MONGO_URI = clean_value(os.environ.get("MONGO_URI", "mongodb://localhost:27017"))
    DATABASE_NAME = clean_value(os.environ.get("DATABASE_NAME", "VideoWorkstationBot"))

    # ==================== ADMIN CONFIGURATION ====================

    # Clean and convert OWNER_ID (required, must be integer)
    _owner_id_raw = os.environ.get("OWNER_ID", "")
    try:
        OWNER_ID = int(clean_value(_owner_id_raw)) if _owner_id_raw else None
    except ValueError:
        logger.error(f"OWNER_ID must be a valid integer, got: {_owner_id_raw}")
        OWNER_ID = None

    ADMINS = os.environ.get("ADMINS", "")
    SUDO_USERS = os.environ.get("SUDO_USERS", "")

    # ==================== CHANNEL & GROUP CONFIGURATION ====================

    FORCE_SUB_CHANNEL = clean_value(os.environ.get("FORCE_SUB_CHANNEL", ""))
    UPDATE_CHANNEL = clean_value(os.environ.get("UPDATE_CHANNEL", ""))
    SUPPORT_GROUP = clean_value(os.environ.get("SUPPORT_GROUP", ""))

    # ==================== LOGGING CHANNELS ====================

    # Clean and convert LOG_CHANNEL (optional, must be integer if provided)
    _log_channel_raw = os.environ.get("LOG_CHANNEL", "")
    try:
        LOG_CHANNEL = int(clean_value(_log_channel_raw)) if _log_channel_raw else None
    except ValueError:
        logger.warning(
            f"LOG_CHANNEL must be a valid integer, got: {_log_channel_raw}. Setting to None."
        )
        LOG_CHANNEL = None

    # Clean and convert TASK_LOG_CHANNEL (optional, must be integer if provided)
    _task_log_channel_raw = os.environ.get("TASK_LOG_CHANNEL", "")
    try:
        TASK_LOG_CHANNEL = int(clean_value(_task_log_channel_raw)) if _task_log_channel_raw else None
    except ValueError:
        logger.warning(
            f"TASK_LOG_CHANNEL must be a valid integer, got: {_task_log_channel_raw}. Setting to None."
        )
        TASK_LOG_CHANNEL = None

    # ==================== FILE STORAGE & PROCESS ====================

    DOWNLOAD_DIR = clean_value(os.environ.get("DOWNLOAD_DIR", "downloads"))
    PROCESS_POLL_INTERVAL_S = 3
    PROCESS_CANCEL_TIMEOUT_S = 3

    # ==================== BOT UI SETTINGS ====================

    BOT_NAME = clean_value(os.environ.get("BOT_NAME", "SS Video Workstation"))
    BOT_USERNAME = clean_value(os.environ.get("BOT_USERNAME", "SSVideoBot"))
    DEVELOPER = clean_value(os.environ.get("DEVELOPER", "Sunil Sharma 2.0"))

    IMG_START = clean_value(os.environ.get(
        "IMG_START",
        "https://i.ibb.co/PvC54s2V/Lucid-Origin-I-have-a-Telegram-bot-named-SS-Merger-Bot-and-I-w-3.jpg"
    ))
    IMG_SETTINGS = clean_value(os.environ.get(
        "IMG_SETTINGS",
        "https://i.ibb.co/mC1cNmyP/Leonardo-Phoenix-10-Create-a-modern-clean-and-eyecatching-land-1-2.jpg"
    ))
    IMG_TOOLS = clean_value(os.environ.get(
        "IMG_TOOLS",
        "https://i.ibb.co/mC1cNmyP/Leonardo-Phoenix-10-Create-a-modern-clean-and-eyecatching-land-1-2.jpg"
    ))
    IMG_FSUB = clean_value(os.environ.get(
        "IMG_FSUB",
        "https://i.ibb.co/mC1cNmyP/Leonardo-Phoenix-10-Create-a-modern-clean-and-eyecatching-land-1-2.jpg"
    ))
    IMG_ADMIN = clean_value(os.environ.get(
        "IMG_ADMIN",
        "https://i.ibb.co/mC1cNmyP/Leonardo-Phoenix-10-Create-a-modern-clean-and-eyecatching-land-1-2.jpg"
    ))

    # ==================== UPLOAD SETTINGS ====================

    GOFILE_TOKEN = clean_value(os.environ.get("GOFILE_TOKEN", ""))
    MAX_TG_UPLOAD_SIZE_BYTES = int(os.environ.get("MAX_TG_UPLOAD_SIZE", 2097152000))  # 2GB

    # ==================== BOT BUTTONS (English - v7.0 Professional) ====================

    # --- Main Menu ---
    BTN_USER_SETTINGS = clean_value(os.environ.get("BTN_USER_SETTINGS", "⚙️ User Settings"))
    BTN_VIDEO_TOOLS = clean_value(os.environ.get("BTN_VIDEO_TOOLS", "🛠️ Video Tools"))
    BTN_ABOUT = clean_value(os.environ.get("BTN_ABOUT", "ℹ️ About"))
    BTN_HELP = clean_value(os.environ.get("BTN_HELP", "📚 Help"))
    BTN_UPDATES = clean_value(os.environ.get("BTN_UPDATES", "📢 Updates"))
    BTN_SUPPORT = clean_value(os.environ.get("BTN_SUPPORT", "💬 Support"))
    BTN_BACK = clean_value(os.environ.get("BTN_BACK", "🔙 Back"))
    BTN_VT_BACK = clean_value(os.environ.get("BTN_VT_BACK", "🔙 Back to Tools"))
    BTN_CANCEL = clean_value(os.environ.get("BTN_CANCEL", "❌ Cancel"))
    BTN_ENABLE_TOOL = clean_value(os.environ.get("BTN_ENABLE_TOOL", "Enable this Tool"))

    # --- User Settings (/us) ---
    BTN_UPLOAD_MODE = clean_value(os.environ.get("BTN_UPLOAD_MODE", "📤 Upload Mode"))
    BTN_DOWNLOAD_MODE = clean_value(os.environ.get("BTN_DOWNLOAD_MODE", "📥 Download Mode"))
    BTN_USER_HOLD = clean_value(os.environ.get("BTN_USER_HOLD", "⏸️ Hold My Tasks"))
    BTN_METADATA = clean_value(os.environ.get("BTN_METADATA", "📝 Metadata"))
    BTN_THUMBNAIL = clean_value(os.environ.get("BTN_THUMBNAIL", "🖼️ Set Thumbnail"))
    BTN_CLEAR_THUMB = clean_value(os.environ.get("BTN_CLEAR_THUMB", "🗑️ Clear Thumb"))
    BTN_SET_FILENAME = clean_value(os.environ.get("BTN_SET_FILENAME", "✏️ Set Filename"))

    # --- Video Tools (/vt) Main Hub ---
    BTN_MERGE = clean_value(os.environ.get("BTN_MERGE", "🎬 Merge Videos"))
    BTN_ENCODE = clean_value(os.environ.get("BTN_ENCODE", "⚡ Encode"))
    BTN_TRIM = clean_value(os.environ.get("BTN_TRIM", "✂️ Trim"))
    BTN_WATERMARK = clean_value(os.environ.get("BTN_WATERMARK", "🖼️ Watermark"))
    BTN_SAMPLE = clean_value(os.environ.get("BTN_SAMPLE", "🎞️ Sample"))
    BTN_MEDIAINFO = clean_value(os.environ.get("BTN_MEDIAINFO", "📊 MediaInfo"))
    BTN_ROTATE = clean_value(os.environ.get("BTN_ROTATE", "🔄 Rotate"))
    BTN_FLIP = clean_value(os.environ.get("BTN_FLIP", "🔃 Flip"))
    BTN_SPEED = clean_value(os.environ.get("BTN_SPEED", "⚡ Speed"))
    BTN_VOLUME = clean_value(os.environ.get("BTN_VOLUME", "🔊 Volume"))
    BTN_CROP = clean_value(os.environ.get("BTN_CROP", "✂️ Crop"))
    BTN_GIF = clean_value(os.environ.get("BTN_GIF", "🎞️ GIF Converter"))
    BTN_REVERSE = clean_value(os.environ.get("BTN_REVERSE", "⏪ Reverse"))
    BTN_EXTRACT_THUMB = clean_value(os.environ.get("BTN_EXTRACT_THUMB", "📸 Extract Thumbnail"))

    # --- NEW: Extract and Extra Tools Main Buttons ---
    BTN_EXTRACT = clean_value(os.environ.get("BTN_EXTRACT", "📦 Extract"))
    BTN_EXTRA_TOOLS = clean_value(os.environ.get("BTN_EXTRA_TOOLS", "🔧 Extra Tools"))
    BTN_AUDIO_REMOVER = clean_value(os.environ.get("BTN_AUDIO_REMOVER", "🔇 Remove Audio"))
    BTN_HD_COVER = clean_value(os.environ.get("BTN_HD_COVER", "🎨 HD Cover"))
    BTN_SCREENSHOT = clean_value(os.environ.get("BTN_SCREENSHOT", "📸 Screenshots"))

    # --- Extract Sub-Menu ---
    BTN_EXTRACT_VIDEO = clean_value(os.environ.get("BTN_EXTRACT_VIDEO", "🎬 Extract Video"))
    BTN_EXTRACT_AUDIO = clean_value(os.environ.get("BTN_EXTRACT_AUDIO", "🎵 Extract Audio"))
    BTN_EXTRACT_SUBTITLES = clean_value(os.environ.get("BTN_EXTRACT_SUBTITLES", "💬 Extract Subtitles"))
    BTN_EXTRACT_THUMBNAILS = clean_value(os.environ.get("BTN_EXTRACT_THUMBNAILS", "🖼️ Extract Thumbnails"))

    # --- Merge Sub-Menu ---
    BTN_MERGE_VID = clean_value(os.environ.get("BTN_MERGE_VID", "Video + Video"))
    BTN_MERGE_AUD = clean_value(os.environ.get("BTN_MERGE_AUD", "Video + Audio"))
    BTN_MERGE_SUB = clean_value(os.environ.get("BTN_MERGE_SUB", "Video + Subtitle"))

    # --- Encode Sub-Menu ---
    BTN_ENCODE_VCODEC = clean_value(os.environ.get("BTN_ENCODE_VCODEC", "📹 Video Codec"))
    BTN_ENCODE_CRF = clean_value(os.environ.get("BTN_ENCODE_CRF", "🎚️ Quality (CRF)"))
    BTN_ENCODE_PRESET = clean_value(os.environ.get("BTN_ENCODE_PRESET", "⚡ Speed Preset"))
    BTN_ENCODE_RESOLUTION = clean_value(os.environ.get("BTN_ENCODE_RESOLUTION", "📺 Resolution"))
    BTN_ENCODE_ACODEC = clean_value(os.environ.get("BTN_ENCODE_ACODEC", "🎤 Audio Codec"))
    BTN_ENCODE_ABITRATE = clean_value(os.environ.get("BTN_ENCODE_ABITRATE", "📊 Audio Bitrate"))
    BTN_ENCODE_SUFFIX = clean_value(os.environ.get("BTN_ENCODE_SUFFIX", "✏️ Filename Suffix"))

    # --- Trim Sub-Menu ---
    BTN_TRIM_START = clean_value(os.environ.get("BTN_TRIM_START", "▶️ Start Time"))
    BTN_TRIM_END = clean_value(os.environ.get("BTN_TRIM_END", "⏹️ End Time"))

    # --- Watermark Sub-Menu ---
    BTN_WATERMARK_TYPE = clean_value(os.environ.get("BTN_WATERMARK_TYPE", "🏷️ Type"))
    BTN_WATERMARK_TEXT = clean_value(os.environ.get("BTN_WATERMARK_TEXT", "✍️ Set Text"))
    BTN_WATERMARK_IMAGE = clean_value(os.environ.get("BTN_WATERMARK_IMAGE", "🖼️ Set Image"))
    BTN_WATERMARK_POSITION = clean_value(os.environ.get("BTN_WATERMARK_POSITION", "📍 Position"))
    BTN_WATERMARK_OPACITY = clean_value(os.environ.get("BTN_WATERMARK_OPACITY", "👁️ Opacity"))

    # --- Sample Sub-Menu ---
    BTN_SAMPLE_DURATION = clean_value(os.environ.get("BTN_SAMPLE_DURATION", "⏳ Duration"))
    BTN_SAMPLE_FROM = clean_value(os.environ.get("BTN_SAMPLE_FROM", "📍 Extract From"))

    # --- Rotate Sub-Menu ---
    BTN_ROTATE_ANGLE = clean_value(os.environ.get("BTN_ROTATE_ANGLE", "📐 Angle"))

    # --- Flip Sub-Menu ---
    BTN_FLIP_DIRECTION = clean_value(os.environ.get("BTN_FLIP_DIRECTION", "📐 Direction"))

    # --- Speed Sub-Menu ---
    BTN_SPEED_MULTIPLIER = clean_value(os.environ.get("BTN_SPEED_MULTIPLIER", "🎬 Speed"))

    # --- Volume Sub-Menu ---
    BTN_VOLUME_LEVEL = clean_value(os.environ.get("BTN_VOLUME_LEVEL", "🎚️ Level"))

    # --- Crop Sub-Menu ---
    BTN_CROP_ASPECT = clean_value(os.environ.get("BTN_CROP_ASPECT", "📐 Aspect Ratio"))

    # --- GIF Sub-Menu ---
    BTN_GIF_FPS = clean_value(os.environ.get("BTN_GIF_FPS", "📊 FPS"))
    BTN_GIF_QUALITY = clean_value(os.environ.get("BTN_GIF_QUALITY", "🎨 Quality"))
    BTN_GIF_SCALE = clean_value(os.environ.get("BTN_GIF_SCALE", "📏 Scale"))

    # --- Extract Thumbnail Sub-Menu ---
    BTN_THUMB_MODE = clean_value(os.environ.get("BTN_THUMB_MODE", "🎯 Mode"))
    BTN_THUMB_TIMESTAMP = clean_value(os.environ.get("BTN_THUMB_TIMESTAMP", "⏱️ Timestamp"))
    BTN_THUMB_COUNT = clean_value(os.environ.get("BTN_THUMB_COUNT", "🔢 Count"))

    # --- Admin Menu ---
    BTN_ADMIN_STATS = clean_value(os.environ.get("BTN_ADMIN_STATS", "📊 Bot Stats"))
    BTN_ADMIN_TASKS = clean_value(os.environ.get("BTN_ADMIN_TASKS", "⏳ Active Tasks"))
    BTN_ADMIN_BROADCAST = clean_value(os.environ.get("BTN_ADMIN_BROADCAST", "📢 Broadcast"))
    BTN_ADMIN_RESTART = clean_value(os.environ.get("BTN_ADMIN_RESTART", "🔄 Restart Bot"))

    # ==================== BOT UI MESSAGES (Professional v7.0) ====================

    # --- Main Menus ---
    MSG_START = clean_value(os.environ.get(
        "MSG_START",
        "👋 **Welcome, {user_name}!**\n\n🎬 **{bot_name}** - Your Professional Video Processing Studio\n\n━━━━━━━━━━━━━━━━━━━━━━\n\n✨ **What I Can Do:**\n🎥 Merge multiple videos seamlessly\n⚡ Encode with custom quality settings\n✂️ Trim videos to perfection\n🖼️ Add watermarks (text/image)\n🎞️ Convert to GIF\n📊 Extract detailed media info\n...and much more!\n\n━━━━━━━━━━━━━━━━━━━━━━\n\n🚀 **Quick Start:**\n▫️ **/vt** - Browse video tools\n▫️ **/us** - Customize settings\n▫️ **/help** - View detailed guide\n\n💡 **Tip:** Enable your desired tool first, then send your files!"
    ))

    MSG_HELP = clean_value(os.environ.get(
        "MSG_HELP",
        "📚 **Complete User Guide**\n\n━━━━━━━━━━━━━━━━━━━━━━\n\n**1️⃣ User Settings (/us)**\n⚙️ Configure your personal preferences:\n • Upload Mode: Telegram or GoFile\n • Download Mode: Direct files or URLs\n • Task Hold: Pause processing\n • Custom Metadata, Thumbnails & Filenames\n\n**2️⃣ Video Tools (/vt)**\n🛠️ Access professional editing tools:\n • Click any tool to view settings\n • Customize parameters (codec, quality, resolution)\n • Enable tool (✅ mark appears)\n • Send your file to process\n\n**3️⃣ Processing Files**\n📁 **For Merge Tool:**\n ▪️ Send 2 or more files\n ▪️ Type **/process** to start\n\n📁 **For Other Tools:**\n ▪️ Send one file at a time\n ▪️ Processing starts automatically\n\n**4️⃣ Available Commands**\n🎯 **/start** - Main menu\n🛠️ **/vt** - Video tools\n⚙️ **/us** - User settings\n⏸️ **/hold** - Pause/resume tasks\n❌ **/cancel** - Stop current task\n🔀 **/process** - Begin merge operation\n\n━━━━━━━━━━━━━━━━━━━━━━\n\n💬 **Need help?** Contact support anytime!"
    ))

    MSG_ABOUT = clean_value(os.environ.get(
        "MSG_ABOUT",
        "ℹ️ **About {bot_name}**\n\n━━━━━━━━━━━━━━━━━━━━━━\n\n🎬 **Professional Video Processing Platform**\n\nPowered by cutting-edge technology to deliver studio-quality video processing directly through Telegram.\n\n**🔧 Technical Stack:**\n• FFmpeg - Industry-standard encoding\n• yt-dlp - Universal media downloader\n• MongoDB - Persistent user data\n• Pyrogram - Fast async framework\n\n**📊 Features:**\n• 15+ video processing tools\n• Granular quality control\n• Real-time progress tracking\n• Cloud & local upload support\n\n━━━━━━━━━━━━━━━━━━━━━━\n\n👨💻 **Developer:** {developer}\n📦 **Version:** 7.0 Pro (Enhanced UI)\n\nMade with ❤️ for video enthusiasts"
    ))

    MSG_USER_SETTINGS = clean_value(os.environ.get(
        "MSG_USER_SETTINGS",
        "⚙️ **Personal Settings Panel**\n\n━━━━━━━━━━━━━━━━━━━━━━\n\nCustomize your video processing experience. All settings are automatically saved and applied to your tasks.\n\n**📊 Current Configuration:**\n\n📤 **Upload Mode:** `{upload_mode}`\n └─ Where processed files are uploaded\n\n📥 **Download Mode:** `{download_mode}`\n └─ How you send files to me\n\n⏸️ **Task Hold:** `{is_on_hold}`\n └─ Pause new task processing\n\n📝 **Metadata:** `{metadata}`\n └─ Keep or clear video metadata\n\n🖼️ **Thumbnail:** `{thumbnail}`\n └─ Custom preview image\n\n✏️ **Filename:** `{filename}`\n └─ Default output name\n\n━━━━━━━━━━━━━━━━━━━━━━\n\n💡 **Tip:** Tap any button to modify settings"
    ))

    MSG_VIDEO_TOOLS = clean_value(os.environ.get(
        "MSG_VIDEO_TOOLS",
        "🛠️ **Professional Video Tools**\n\n━━━━━━━━━━━━━━━━━━━━━━\n\nChoose from our comprehensive suite of video processing tools. Each tool offers advanced customization options.\n\n**🎯 Currently Active:** `{active_tool}`\n\n━━━━━━━━━━━━━━━━━━━━━━\n\n**📋 Tool Categories:**\n🎬 **Editing** - Merge, Trim, Rotate, Flip\n⚡ **Conversion** - Encode, GIF, Extract\n🎨 **Enhancement** - Watermark, Volume, Speed\n📊 **Analysis** - MediaInfo, Sampling\n\n💡 **Quick Tip:**\nClick a tool → Configure settings → Enable (✅) → Send file"
    ))

    MSG_ADMIN_PANEL = clean_value(os.environ.get(
        "MSG_ADMIN_PANEL",
        "🤖 **Administrator Control Panel**\n\n━━━━━━━━━━━━━━━━━━━━━━\n\n**📊 System Status:**\n\n🌐 **Bot Mode:** `{bot_mode}`\n⚙️ **Active Tasks:** `{task_count}`\n\n━━━━━━━━━━━━━━━━━━━━━━\n\n**🔧 Admin Commands:**\n• **/activate** - Enable bot globally\n• **/deactivate** - Hold all tasks\n• **/s** - View task details\n• **/restart** - Restart bot (sudo only)\n\nUse buttons below for quick actions"
    ))

    # --- VT Main Menus (Professional v7.0) ---
    MSG_VT_MERGE_MAIN = clean_value(os.environ.get(
        "MSG_VT_MERGE_MAIN",
        "🎬 **Video Merge Studio**\n\n━━━━━━━━━━━━━━━━━━━━━━\n\nSeamlessly combine multiple media files into one perfect output.\n\n**🎯 Current Mode:** `{mode}`\n\n━━━━━━━━━━━━━━━━━━━━━━\n\n**📋 Available Modes:**\n🎥 **Video + Video** - Concatenate clips\n🎧 **Video + Audio** - Replace/add audio track\n💬 **Video + Subtitle** - Embed subtitles\n\n**📝 How to Use:**\n1️⃣ Select merge mode\n2️⃣ Enable this tool (✅)\n3️⃣ Send files (2 or more)\n4️⃣ Type **/process** to merge\n\n💡 **Pro Tip:** Files with matching specs merge faster!"
    ))

    MSG_VT_ENCODE_MAIN = clean_value(os.environ.get(
        "MSG_VT_ENCODE_MAIN",
        "⚡ **Advanced Encoding Studio**\n\n━━━━━━━━━━━━━━━━━━━━━━\n\nProfessional-grade encoding with full control over quality and compression.\n\n**🎬 Video Settings:**\n📹 Codec: `{vcodec}`\n🎚️ Quality (CRF): `{crf}`\n⚡ Speed Preset: `{preset}`\n📺 Resolution: `{resolution}`\n\n**🎵 Audio Settings:**\n🎤 Codec: `{acodec}`\n📊 Bitrate: `{abitrate}`\n\n**📝 Output:**\n✏️ Filename Suffix: `{suffix}`\n\n━━━━━━━━━━━━━━━━━━━━━━\n\n💡 **Quality Guide:**\n• CRF 18-23: High quality (larger file)\n• CRF 24-28: Balanced (recommended)\n• CRF 29-35: Lower quality (smaller file)"
    ))

    MSG_VT_TRIM_MAIN = clean_value(os.environ.get(
        "MSG_VT_TRIM_MAIN",
        "✂️ **Precision Trim Tool**\n\n━━━━━━━━━━━━━━━━━━━━━━\n\nExtract specific segments from your video with frame-accurate precision.\n\n**⏱️ Current Selection:**\n▶️ **Start Time:** `{start}`\n⏹️ **End Time:** `{end}`\n\n━━━━━━━━━━━━━━━━━━━━━━\n\n**📝 Time Format:**\n• HH:MM:SS → `00:01:30` (1 min 30 sec)\n• Seconds → `90` (same as above)\n\n**🎯 Quick Actions:**\n• Tap 'Start Time' to set beginning\n• Tap 'End Time' to set finish\n• Enable tool and send your video\n\n💡 **Tip:** Leave end time as `00:00:00` to trim till the end"
    ))

    MSG_VT_WATERMARK_MAIN = clean_value(os.environ.get(
        "MSG_VT_WATERMARK_MAIN",
        "🖼️ **Watermark Designer**\n\n━━━━━━━━━━━━━━━━━━━━━━\n\nProtect your content with custom watermarks. Add branding or copyright protection effortlessly.\n\n**🎨 Current Configuration:**\n🏷️ **Type:** `{type}`\n✍️ **Text:** `{text}`\n🖼️ **Image:** `{image}`\n📍 **Position:** `{position}`\n👁️ **Opacity:** `{opacity}`\n\n━━━━━━━━━━━━━━━━━━━━━━\n\n**📋 Available Types:**\n• **Text** - Custom text overlay\n• **Image** - Logo/graphic watermark\n• **None** - No watermark\n\n**📍 Position Options:**\nTop/Bottom × Left/Right/Center\n\n💡 **Tip:** Lower opacity creates subtle watermarks"
    ))

    MSG_VT_SCREENSHOT_MAIN = clean_value(os.environ.get(
        "MSG_VT_SCREENSHOT_MAIN",
        "📸 **Video Screenshot Tool**\n\n━━━━━━━━━━━━━━━━━━━━━━\n\nExtract high-quality screenshots from your video.\n\n**🎯 Current Settings:**\n• **Timestamp:** `{timestamp}`\n• **Count:** `{count}` screenshots\n• **Mode:** `{mode}`\n\n━━━━━━━━━━━━━━━━━━━━━━\n\n**📋 Modes:**\n• **Single** – Capture 1 frame\n• **Multiple** – Capture N frames\n• **Auto** – Capture frames at equal intervals\n\n💡 **Tip:** Use 'Multiple' mode to generate preview strips!"
    ))

    # --- Generic Messages ---
    MSG_SELECT_TOOL_FIRST = "❌ **No tool selected!**\nPlease use `/vt` to select and enable a tool (✅) before sending files."
    MSG_BOT_ON_HOLD = "⏸️ **Bot is globally on HOLD.**\nYour task will not be processed. Please wait for an admin to `/activate` the bot."
    MSG_USER_ON_HOLD = "⏸️ **Your tasks are ON HOLD.**\nYour task has been rejected. Use /hold to reactivate your tasks."
    MSG_TASK_IN_PROGRESS = "⏳ **You already have a task in progress.**\nPlease wait for it to complete or use /cancel to stop it."
    MSG_NO_ACTIVE_TASK = "You have no active tasks to cancel."

    # --- Task Messages ---
    MSG_TASK_ACCEPTED = "⏳ **Task `{task_id}` Accepted.**\nInitializing task... Tool: `MERGE` ({count} files)"
    MSG_TASK_ACCEPTED_SINGLE = "⏳ **Task `{task_id}` Accepted.**\nInitializing task... Tool: `{tool}`"
    MSG_TASK_CANCELLED = "🚫 **Task `{task_id}` Cancelled!**\n✅ All processes stopped and temporary files cleaned."
    MSG_TASK_FAILED = "❌ **Task `{task_id}` Failed!**\n\n`{error}`"

    # --- Upload Messages ---
    MSG_UPLOAD_COMPLETE = "✅ **Task `{task_id}` Complete!**\n\n👤 **User:** {user_mention}\n**File:** `{file_name}`\n**Size:** `{file_size}`"
    MSG_UPLOAD_COMPLETE_GOFILE = "✅ **Task `{task_id}` Complete!**\n\n👤 **User:** {user_mention}\n🔗 **Link:** {link}"
    MSG_UPLOAD_FAILED = "❌ **Upload Failed!**\n\n`{error}`"

    # --- Error Messages ---
    MSG_PRIVATE_CHAT_RESTRICTED = "🚫 **Private Chat Restricted**\nPlease use me in authorized groups."
    MSG_GROUP_NOT_AUTHORIZED = "❌ **Group Not Authorized**\nContact the owner to authorize this group."
    MSG_BANNED = "🚫 **You are banned.**\n\nContact the owner if you believe this is a mistake."

# ==================== VALIDATION & CONVERSION ====================

def validate_config():
    """Validate and convert configuration values"""
    
    # Validate required string variables
    string_vars = [
        "API_HASH", "BOT_TOKEN", "MONGO_URI", "DATABASE_NAME",
        "FORCE_SUB_CHANNEL", "UPDATE_CHANNEL", "SUPPORT_GROUP",
        "BOT_NAME", "BOT_USERNAME", "DEVELOPER",
        "IMG_START", "IMG_SETTINGS", "IMG_TOOLS", "IMG_FSUB", "IMG_ADMIN",
        "GOFILE_TOKEN"
    ]

    for var in string_vars:
        if hasattr(Config, var):
            value = getattr(Config, var)
            if isinstance(value, str):
                setattr(Config, var, clean_value(value))

    # Validate required variables
    required = ["API_ID", "API_HASH", "BOT_TOKEN", "OWNER_ID", "MONGO_URI"]
    missing = [var for var in required if not getattr(Config, var, None)]

    if missing:
        raise ValueError(f"❌ Missing required environment variables: {', '.join(missing)}")

    # Convert numeric variables
    try:
        if isinstance(Config.PROCESS_POLL_INTERVAL_S, str):
            Config.PROCESS_POLL_INTERVAL_S = int(clean_value(str(Config.PROCESS_POLL_INTERVAL_S)))
        
        if isinstance(Config.PROCESS_CANCEL_TIMEOUT_S, str):
            Config.PROCESS_CANCEL_TIMEOUT_S = int(clean_value(str(Config.PROCESS_CANCEL_TIMEOUT_S)))
        
        # Convert ADMINS and SUDO_USERS to list
        def to_int_list(var_str):
            if var_str:
                return [
                    int(clean_value(x)) for x in var_str.split(",")
                    if clean_value(x).lstrip('-').isdigit()
                ]
            return []

        Config.ADMINS = to_int_list(Config.ADMINS)
        Config.SUDO_USERS = to_int_list(Config.SUDO_USERS)

        # Ensure OWNER_ID is in both lists
        if Config.OWNER_ID:
            if Config.OWNER_ID not in Config.ADMINS:
                Config.ADMINS.append(Config.OWNER_ID)
            if Config.OWNER_ID not in Config.SUDO_USERS:
                Config.SUDO_USERS.append(Config.OWNER_ID)

    except ValueError as e:
        logger.error(f"Config validation error: {e}", exc_info=True)
        raise ValueError(f"❌ Configuration error: {e}")

    # Ensure download directory exists
    if not os.path.isdir(Config.DOWNLOAD_DIR):
        try:
            os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)
            logger.info(f"Created download directory: {Config.DOWNLOAD_DIR}")
        except Exception as e:
            logger.error(f"Could not create download directory: {e}")
            raise

    logger.info("✅ Configuration validated successfully")

# Run validation
validate_config()

# Create singleton instance
config = Config()
