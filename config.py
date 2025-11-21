# config.py (v6.0)
# MODIFIED for Granular 've' Repo UI (Step 2)
# 1. Added dozens of new buttons for granular settings (BTN_ENCODE_VCODEC, BTN_ENCODE_CRF, etc.)
# 2. Added dozens of new captions for all sub-menus (MSG_VT_ENCODE_MAIN, MSG_VT_ENCODE_VCODEC_MENU, etc.)
# 3. Added new "ask" prompts for custom values (MSG_ASK_CUSTOM_CRF, etc.)
# 4. Updated `validate_config()` to include all new variables.

import os
import logging
from dotenv import load_dotenv

# Load environment variables from config.env
load_dotenv('config.env')

# Setup logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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

    API_HASH = os.environ.get("API_HASH")
    BOT_TOKEN = os.environ.get("BOT_TOKEN")

    # ==================== MONGODB CONFIGURATION ====================
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    DATABASE_NAME = os.environ.get("DATABASE_NAME", "VideoWorkstationBot")

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
    FORCE_SUB_CHANNEL = os.environ.get("FORCE_SUB_CHANNEL", "")
    UPDATE_CHANNEL = os.environ.get("UPDATE_CHANNEL", "")
    SUPPORT_GROUP = os.environ.get("SUPPORT_GROUP", "")

    # ==================== LOGGING CHANNELS ====================
    # Clean and convert LOG_CHANNEL (optional, must be integer if provided)
    _log_channel_raw = os.environ.get("LOG_CHANNEL", "")
    try:
        LOG_CHANNEL = int(
            clean_value(_log_channel_raw)) if _log_channel_raw else None
    except ValueError:
        logger.warning(
            f"LOG_CHANNEL must be a valid integer, got: {_log_channel_raw}. Setting to None."
        )
        LOG_CHANNEL = None

    # Clean and convert TASK_LOG_CHANNEL (optional, must be integer if provided)
    _task_log_channel_raw = os.environ.get("TASK_LOG_CHANNEL", "")
    try:
        TASK_LOG_CHANNEL = int(clean_value(
            _task_log_channel_raw)) if _task_log_channel_raw else None
    except ValueError:
        logger.warning(
            f"TASK_LOG_CHANNEL must be a valid integer, got: {_task_log_channel_raw}. Setting to None."
        )
        TASK_LOG_CHANNEL = None

    # ==================== HELPER FUNCTION (Static Method) ====================
    @staticmethod
    def clean_value(value_str: str) -> str:
        """Cleans env variables from comments (#) and extra quotes/spaces"""
        return clean_value(value_str)

    # ==================== FILE STORAGE & PROCESS ====================
    DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "downloads")
    PROCESS_POLL_INTERVAL_S = os.environ.get("PROCESS_POLL_INTERVAL_S", 3)
    PROCESS_CANCEL_TIMEOUT_S = os.environ.get("PROCESS_CANCEL_TIMEOUT_S", 3)

    # ==================== BOT UI SETTINGS ====================
    BOT_NAME = os.environ.get("BOT_NAME", "SS Video Workstation")
    BOT_USERNAME = os.environ.get("BOT_USERNAME", "SSVideoBot")
    DEVELOPER = os.environ.get("DEVELOPER", "Sunil Sharma 2.0")

    IMG_START = os.environ.get(
        "IMG_START",
        "https://i.ibb.co/PvC54s2V/Lucid-Origin-I-have-a-Telegram-bot-named-SS-Merger-Bot-and-I-w-3.jpg"
    )
    IMG_SETTINGS = os.environ.get(
        "IMG_SETTINGS",
        "https://i.ibb.co/mC1cNmyP/Leonardo-Phoenix-10-Create-a-modern-clean-and-eyecatching-land-1-2.jpg"
    )
    IMG_TOOLS = os.environ.get(
        "IMG_TOOLS",
        "https://i.ibb.co/mC1cNmyP/Leonardo-Phoenix-10-Create-a-modern-clean-and-eyecatching-land-1-2.jpg"
    )
    IMG_FSUB = os.environ.get(
        "IMG_FSUB",
        "https://i.ibb.co/mC1cNmyP/Leonardo-Phoenix-10-Create-a-modern-clean-and-eyecatching-land-1-2.jpg"
    )
    IMG_ADMIN = os.environ.get(
        "IMG_ADMIN",
        "https://i.ibb.co/mC1cNmyP/Leonardo-Phoenix-10-Create-a-modern-clean-and-eyecatching-land-1-2.jpg"
    )

    # ==================== UPLOAD SETTINGS ====================
    GOFILE_TOKEN = os.environ.get("GOFILE_TOKEN")
    MAX_TG_UPLOAD_SIZE_BYTES = int(
        os.environ.get("MAX_TG_UPLOAD_SIZE", 2097152000))  # 2GB

    # ==================== BOT BUTTONS (English - v6.0) ====================
    # --- Main Menu ---
    BTN_USER_SETTINGS = os.environ.get("BTN_USER_SETTINGS", "⚙️ User Settings")
    BTN_VIDEO_TOOLS = os.environ.get("BTN_VIDEO_TOOLS", "🛠️ Video Tools")
    BTN_ABOUT = os.environ.get("BTN_ABOUT", "ℹ️ About")
    BTN_HELP = os.environ.get("BTN_HELP", "📚 Help")
    BTN_UPDATES = os.environ.get("BTN_UPDATES", "📢 Updates")
    BTN_SUPPORT = os.environ.get("BTN_SUPPORT", "💬 Support")
    BTN_BACK = os.environ.get("BTN_BACK", "🔙 Back")
    BTN_VT_BACK = os.environ.get("BTN_VT_BACK", "🔙 Back to Tools")
    BTN_CANCEL = os.environ.get("BTN_CANCEL", "❌ Cancel")
    BTN_ENABLE_TOOL = os.environ.get("BTN_ENABLE_TOOL",
                                     "Enable this Tool")  # Generic

    # --- User Settings (/us) ---
    BTN_UPLOAD_MODE = os.environ.get("BTN_UPLOAD_MODE", "📤 Upload Mode")
    BTN_DOWNLOAD_MODE = os.environ.get("BTN_DOWNLOAD_MODE", "📥 Download Mode")
    BTN_USER_HOLD = os.environ.get("BTN_USER_HOLD", "⏸️ Hold My Tasks")
    BTN_METADATA = os.environ.get("BTN_METADATA", "📝 Metadata")
    BTN_THUMBNAIL = os.environ.get("BTN_THUMBNAIL", "🖼️ Set Thumbnail")
    BTN_CLEAR_THUMB = os.environ.get("BTN_CLEAR_THUMB", "🗑️ Clear Thumb")
    BTN_SET_FILENAME = os.environ.get("BTN_SET_FILENAME", "✏️ Set Filename")

    # --- Video Tools (/vt) Main Hub ---
    BTN_MERGE = os.environ.get("BTN_MERGE", "🎬 Merge Videos")
    BTN_ENCODE = os.environ.get("BTN_ENCODE", "⚡ Encode")
    BTN_TRIM = os.environ.get("BTN_TRIM", "✂️ Trim")
    BTN_WATERMARK = os.environ.get("BTN_WATERMARK", "🖼️ Watermark")
    BTN_SAMPLE = os.environ.get("BTN_SAMPLE", "🎞️ Sample")
    BTN_MEDIAINFO = os.environ.get("BTN_MEDIAINFO", "📊 MediaInfo")
    BTN_ROTATE = os.environ.get("BTN_ROTATE", "🔄 Rotate")
    BTN_FLIP = os.environ.get("BTN_FLIP", "🔃 Flip")
    BTN_SPEED = os.environ.get("BTN_SPEED", "⚡ Speed")
    BTN_VOLUME = os.environ.get("BTN_VOLUME", "🔊 Volume")
    BTN_CROP = os.environ.get("BTN_CROP", "✂️ Crop")
    BTN_GIF = os.environ.get("BTN_GIF", "🎞️ GIF Converter")
    BTN_REVERSE = os.environ.get("BTN_REVERSE", "⏪ Reverse")
    BTN_EXTRACT_THUMB = os.environ.get("BTN_EXTRACT_THUMB",
                                       "📸 Extract Thumbnail")

    # --- NEW: Extract and Extra Tools Main Buttons ---
    BTN_EXTRACT = os.environ.get("BTN_EXTRACT", "📦 Extract")
    BTN_EXTRA_TOOLS = os.environ.get("BTN_EXTRA_TOOLS", "🔧 Extra Tools")

    # --- Extract Sub-Menu ---
    BTN_EXTRACT_VIDEO = os.environ.get("BTN_EXTRACT_VIDEO", "🎬 Extract Video")
    BTN_EXTRACT_AUDIO = os.environ.get("BTN_EXTRACT_AUDIO", "🎵 Extract Audio")
    BTN_EXTRACT_SUBTITLES = os.environ.get("BTN_EXTRACT_SUBTITLES",
                                           "💬 Extract Subtitles")
    BTN_EXTRACT_THUMBNAILS = os.environ.get("BTN_EXTRACT_THUMBNAILS",
                                            "🖼️ Extract Thumbnails")

    # --- Merge Sub-Menu ---
    BTN_MERGE_VID = os.environ.get("BTN_MERGE_VID", "Video + Video")
    BTN_MERGE_AUD = os.environ.get("BTN_MERGE_AUD", "Video + Audio")
    BTN_MERGE_SUB = os.environ.get("BTN_MERGE_SUB", "Video + Subtitle")

    # --- Encode Sub-Menu ---
    BTN_ENCODE_VCODEC = os.environ.get("BTN_ENCODE_VCODEC", "📹 Video Codec")
    BTN_ENCODE_CRF = os.environ.get("BTN_ENCODE_CRF", "🎚️ Quality (CRF)")
    BTN_ENCODE_PRESET = os.environ.get("BTN_ENCODE_PRESET", "⚡ Speed Preset")
    BTN_ENCODE_RESOLUTION = os.environ.get("BTN_ENCODE_RESOLUTION",
                                           "📺 Resolution")
    BTN_ENCODE_ACODEC = os.environ.get("BTN_ENCODE_ACODEC", "🎤 Audio Codec")
    BTN_ENCODE_ABITRATE = os.environ.get("BTN_ENCODE_ABITRATE",
                                         "📊 Audio Bitrate")
    BTN_ENCODE_SUFFIX = os.environ.get("BTN_ENCODE_SUFFIX",
                                       "✏️ Filename Suffix")

    # --- Trim Sub-Menu ---
    BTN_TRIM_START = os.environ.get("BTN_TRIM_START", "▶️ Start Time")
    BTN_TRIM_END = os.environ.get("BTN_TRIM_END", "⏹️ End Time")

    # --- Watermark Sub-Menu ---
    BTN_WATERMARK_TYPE = os.environ.get("BTN_WATERMARK_TYPE", "🏷️ Type")
    BTN_WATERMARK_TEXT = os.environ.get("BTN_WATERMARK_TEXT", "✍️ Set Text")
    BTN_WATERMARK_IMAGE = os.environ.get("BTN_WATERMARK_IMAGE", "🖼️ Set Image")
    BTN_WATERMARK_POSITION = os.environ.get("BTN_WATERMARK_POSITION",
                                            "📍 Position")
    BTN_WATERMARK_OPACITY = os.environ.get("BTN_WATERMARK_OPACITY",
                                           "👁️ Opacity")

    # --- Sample Sub-Menu ---
    BTN_SAMPLE_DURATION = os.environ.get("BTN_SAMPLE_DURATION", "⏳ Duration")
    BTN_SAMPLE_FROM = os.environ.get("BTN_SAMPLE_FROM", "📍 Extract From")

    # --- Rotate Sub-Menu ---
    BTN_ROTATE_ANGLE = os.environ.get("BTN_ROTATE_ANGLE", "📐 Angle")

    # --- Flip Sub-Menu ---
    BTN_FLIP_DIRECTION = os.environ.get("BTN_FLIP_DIRECTION", "📐 Direction")

    # --- Speed Sub-Menu ---
    BTN_SPEED_MULTIPLIER = os.environ.get("BTN_SPEED_MULTIPLIER", "🎬 Speed")

    # --- Volume Sub-Menu ---
    BTN_VOLUME_LEVEL = os.environ.get("BTN_VOLUME_LEVEL", "🎚️ Level")

    # --- Crop Sub-Menu ---
    BTN_CROP_ASPECT = os.environ.get("BTN_CROP_ASPECT", "📐 Aspect Ratio")

    # --- GIF Sub-Menu ---
    BTN_GIF_FPS = os.environ.get("BTN_GIF_FPS", "📊 FPS")
    BTN_GIF_QUALITY = os.environ.get("BTN_GIF_QUALITY", "🎨 Quality")
    BTN_GIF_SCALE = os.environ.get("BTN_GIF_SCALE", "📏 Scale")

    # --- Extract Thumbnail Sub-Menu ---
    BTN_THUMB_MODE = os.environ.get("BTN_THUMB_MODE", "🎯 Mode")
    BTN_THUMB_TIMESTAMP = os.environ.get("BTN_THUMB_TIMESTAMP", "⏱️ Timestamp")
    BTN_THUMB_COUNT = os.environ.get("BTN_THUMB_COUNT", "🔢 Count")

    # --- Admin Menu ---
    BTN_ADMIN_STATS = os.environ.get("BTN_ADMIN_STATS", "Bot Stats")
    BTN_ADMIN_TASKS = os.environ.get("BTN_ADMIN_TASKS", "Active Tasks")
    BTN_ADMIN_BROADCAST = os.environ.get("BTN_ADMIN_BROADCAST", "Broadcast")
    BTN_ADMIN_RESTART = os.environ.get("BTN_ADMIN_RESTART", "Restart Bot")

    # ==================== BOT UI MESSAGES (Professional v7.0) ====================
    # --- Main Menus ---
    MSG_START = os.environ.get(
        "MSG_START",
        ("👋 **Welcome, {user_name}!**\n\n"
         "🎬 **{bot_name}** - Your Professional Video Processing Studio\n\n"
         "━━━━━━━━━━━━━━━━━━━━━━\n\n"
         "✨ **What I Can Do:**\n"
         "🎥 Merge multiple videos seamlessly\n"
         "⚡ Encode with custom quality settings\n"
         "✂️ Trim videos to perfection\n"
         "🖼️ Add watermarks (text/image)\n"
         "🎞️ Convert to GIF\n"
         "📊 Extract detailed media info\n"
         "...and much more!\n\n"
         "━━━━━━━━━━━━━━━━━━━━━━\n\n"
         "🚀 **Quick Start:**\n"
         "▫️ **/vt** - Browse video tools\n"
         "▫️ **/us** - Customize settings\n"
         "▫️ **/help** - View detailed guide\n\n"
         "💡 **Tip:** Enable your desired tool first, then send your files!"))
    MSG_HELP = os.environ.get(
        "MSG_HELP", ("📚 **Complete User Guide**\n\n"
                     "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                     "**1️⃣ User Settings (/us)**\n"
                     "⚙️ Configure your personal preferences:\n"
                     "   • Upload Mode: Telegram or GoFile\n"
                     "   • Download Mode: Direct files or URLs\n"
                     "   • Task Hold: Pause processing\n"
                     "   • Custom Metadata, Thumbnails & Filenames\n\n"
                     "**2️⃣ Video Tools (/vt)**\n"
                     "🛠️ Access professional editing tools:\n"
                     "   • Click any tool to view settings\n"
                     "   • Customize parameters (codec, quality, resolution)\n"
                     "   • Enable tool (✅ mark appears)\n"
                     "   • Send your file to process\n\n"
                     "**3️⃣ Processing Files**\n"
                     "📁 **For Merge Tool:**\n"
                     "   ▪️ Send 2 or more files\n"
                     "   ▪️ Type **/process** to start\n\n"
                     "📁 **For Other Tools:**\n"
                     "   ▪️ Send one file at a time\n"
                     "   ▪️ Processing starts automatically\n\n"
                     "**4️⃣ Available Commands**\n"
                     "🎯 **/start** - Main menu\n"
                     "🛠️ **/vt** - Video tools\n"
                     "⚙️ **/us** - User settings\n"
                     "⏸️ **/hold** - Pause/resume tasks\n"
                     "❌ **/cancel** - Stop current task\n"
                     "🔀 **/process** - Begin merge operation\n\n"
                     "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                     "💬 **Need help?** Contact support anytime!"))
    MSG_ABOUT = os.environ.get("MSG_ABOUT", (
        "ℹ️ **About {bot_name}**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎬 **Professional Video Processing Platform**\n\n"
        "Powered by cutting-edge technology to deliver studio-quality video processing directly through Telegram.\n\n"
        "**🔧 Technical Stack:**\n"
        "• FFmpeg - Industry-standard encoding\n"
        "• yt-dlp - Universal media downloader\n"
        "• MongoDB - Persistent user data\n"
        "• Pyrogram - Fast async framework\n\n"
        "**📊 Features:**\n"
        "• 15+ video processing tools\n"
        "• Granular quality control\n"
        "• Real-time progress tracking\n"
        "• Cloud & local upload support\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👨‍💻 **Developer:** {developer}\n"
        "📦 **Version:** 7.0 Pro (Enhanced UI)\n\n"
        "Made with ❤️ for video enthusiasts"))
    MSG_USER_SETTINGS = os.environ.get("MSG_USER_SETTINGS", (
        "⚙️ **Personal Settings Panel**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Customize your video processing experience. All settings are automatically saved and applied to your tasks.\n\n"
        "**📊 Current Configuration:**\n\n"
        "📤 **Upload Mode:** `{upload_mode}`\n"
        "   └─ Where processed files are uploaded\n\n"
        "📥 **Download Mode:** `{download_mode}`\n"
        "   └─ How you send files to me\n\n"
        "⏸️ **Task Hold:** `{is_on_hold}`\n"
        "   └─ Pause new task processing\n\n"
        "📝 **Metadata:** `{metadata}`\n"
        "   └─ Keep or clear video metadata\n\n"
        "🖼️ **Thumbnail:** `{thumbnail}`\n"
        "   └─ Custom preview image\n\n"
        "✏️ **Filename:** `{filename}`\n"
        "   └─ Default output name\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💡 **Tip:** Tap any button to modify settings"))
    MSG_VIDEO_TOOLS = os.environ.get("MSG_VIDEO_TOOLS", (
        "🛠️ **Professional Video Tools**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Choose from our comprehensive suite of video processing tools. Each tool offers advanced customization options.\n\n"
        "**🎯 Currently Active:** `{active_tool}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "**📋 Tool Categories:**\n"
        "🎬 **Editing** - Merge, Trim, Rotate, Flip\n"
        "⚡ **Conversion** - Encode, GIF, Extract\n"
        "🎨 **Enhancement** - Watermark, Volume, Speed\n"
        "📊 **Analysis** - MediaInfo, Sampling\n\n"
        "💡 **Quick Tip:**\n"
        "Click a tool → Configure settings → Enable (✅) → Send file"))
    MSG_ADMIN_PANEL = os.environ.get(
        "MSG_ADMIN_PANEL", ("🤖 **Administrator Control Panel**\n\n"
                            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                            "**📊 System Status:**\n\n"
                            "🌐 **Bot Mode:** `{bot_mode}`\n"
                            "⚙️ **Active Tasks:** `{task_count}`\n\n"
                            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                            "**🔧 Admin Commands:**\n"
                            "• **/activate** - Enable bot globally\n"
                            "• **/deactivate** - Hold all tasks\n"
                            "• **/s** - View task details\n"
                            "• **/restart** - Restart bot (sudo only)\n\n"
                            "Use buttons below for quick actions"))

    # --- VT Sub-Menus (Professional v7.0) ---
    MSG_VT_MERGE_MAIN = os.environ.get(
        "MSG_VT_MERGE_MAIN",
        ("🎬 **Video Merge Studio**\n\n"
         "━━━━━━━━━━━━━━━━━━━━━━\n\n"
         "Seamlessly combine multiple media files into one perfect output.\n\n"
         "**🎯 Current Mode:** `{mode}`\n\n"
         "━━━━━━━━━━━━━━━━━━━━━━\n\n"
         "**📋 Available Modes:**\n"
         "🎥 **Video + Video** - Concatenate clips\n"
         "🎧 **Video + Audio** - Replace/add audio track\n"
         "💬 **Video + Subtitle** - Embed subtitles\n\n"
         "**📝 How to Use:**\n"
         "1️⃣ Select merge mode\n"
         "2️⃣ Enable this tool (✅)\n"
         "3️⃣ Send files (2 or more)\n"
         "4️⃣ Type **/process** to merge\n\n"
         "💡 **Pro Tip:** Files with matching specs merge faster!"))
    MSG_VT_ENCODE_MAIN = os.environ.get("MSG_VT_ENCODE_MAIN", (
        "⚡ **Advanced Encoding Studio**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Professional-grade encoding with full control over quality and compression.\n\n"
        "**🎬 Video Settings:**\n"
        "📹 Codec: `{vcodec}`\n"
        "🎚️ Quality (CRF): `{crf}`\n"
        "⚡ Speed Preset: `{preset}`\n"
        "📺 Resolution: `{resolution}`\n\n"
        "**🎵 Audio Settings:**\n"
        "🎤 Codec: `{acodec}`\n"
        "📊 Bitrate: `{abitrate}`\n\n"
        "**📝 Output:**\n"
        "✏️ Filename Suffix: `{suffix}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "💡 **Quality Guide:**\n"
        "• CRF 18-23: High quality (larger file)\n"
        "• CRF 24-28: Balanced (recommended)\n"
        "• CRF 29-35: Lower quality (smaller file)"))
    MSG_VT_TRIM_MAIN = os.environ.get("MSG_VT_TRIM_MAIN", (
        "✂️ **Precision Trim Tool**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Extract specific segments from your video with frame-accurate precision.\n\n"
        "**⏱️ Current Selection:**\n"
        "▶️ **Start Time:** `{start}`\n"
        "⏹️ **End Time:** `{end}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "**📝 Time Format:**\n"
        "• HH:MM:SS → `00:01:30` (1 min 30 sec)\n"
        "• Seconds → `90` (same as above)\n\n"
        "**🎯 Quick Actions:**\n"
        "• Tap 'Start Time' to set beginning\n"
        "• Tap 'End Time' to set finish\n"
        "• Enable tool and send your video\n\n"
        "💡 **Tip:** Leave end time as `00:00:00` to trim till the end"))
    MSG_VT_WATERMARK_MAIN = os.environ.get("MSG_VT_WATERMARK_MAIN", (
        "🖼️ **Watermark Designer**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Protect your content with custom watermarks. Add branding or copyright protection effortlessly.\n\n"
        "**🎨 Current Configuration:**\n"
        "🏷️ **Type:** `{type}`\n"
        "✍️ **Text:** `{text}`\n"
        "🖼️ **Image:** `{image}`\n"
        "📍 **Position:** `{position}`\n"
        "👁️ **Opacity:** `{opacity}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "**📋 Available Types:**\n"
        "• **Text** - Custom text overlay\n"
        "• **Image** - Logo/graphic watermark\n"
        "• **None** - No watermark\n\n"
        "**📍 Position Options:**\n"
        "Top/Bottom × Left/Right/Center\n\n"
        "💡 **Tip:** Lower opacity creates subtle watermarks"))
    MSG_VT_SAMPLE_MAIN = os.environ.get("MSG_VT_SAMPLE_MAIN", (
        "🎞️ **Video Sample Generator**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Create preview clips from your videos. Perfect for sharing teasers or demos.\n\n"
        "**⏱️ Current Settings:**\n"
        "⏳ **Duration:** `{duration}` seconds\n"
        "📍 **Extract From:** `{from_point}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "**📋 Extraction Points:**\n"
        "• **Start** - Beginning of video\n"
        "• **Middle** - Center segment\n"
        "• **End** - Final portion\n\n"
        "**🎯 Common Durations:**\n"
        "• 15s - Social media preview\n"
        "• 30s - Standard sample\n"
        "• 60s - Extended teaser\n\n"
        "💡 **Tip:** 30-second samples work best for most platforms"))
    MSG_VT_ROTATE_MAIN = os.environ.get("MSG_VT_ROTATE_MAIN", (
        "🔄 **Video Rotation Tool**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Fix orientation issues or create unique perspectives by rotating your video.\n\n"
        "**📐 Current Angle:** `{angle}°`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "**🎯 Available Angles:**\n"
        "• **90°** - Quarter turn clockwise\n"
        "• **180°** - Full flip (upside down)\n"
        "• **270°** - Quarter turn counter-clockwise\n\n"
        "**📱 Common Uses:**\n"
        "• Fix portrait/landscape orientation\n"
        "• Correct upside-down videos\n"
        "• Creative visual effects\n\n"
        "💡 **Tip:** Use 90° or 270° to switch between portrait and landscape"))
    MSG_VT_FLIP_MAIN = os.environ.get("MSG_VT_FLIP_MAIN", (
        "🔃 **Video Flip Tool**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Mirror your video horizontally or vertically for creative effects or corrections.\n\n"
        "**📐 Current Direction:** `{direction}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "**🎯 Flip Options:**\n"
        "• **Horizontal** - Mirror left ↔️ right\n"
        "• **Vertical** - Mirror top ↔️ bottom\n\n"
        "**🎨 Common Uses:**\n"
        "• Fix mirror-recorded videos\n"
        "• Create mirror effects\n"
        "• Correct front camera footage\n\n"
        "💡 **Tip:** Horizontal flip is most common for selfie videos"))
    MSG_VT_SPEED_MAIN = os.environ.get("MSG_VT_SPEED_MAIN", (
        "⚡ **Speed Control Studio**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Create slow-motion or time-lapse effects by adjusting playback speed.\n\n"
        "**🎬 Current Speed:** `{speed}x`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "**🎯 Speed Presets:**\n"
        "• **0.5x** - Half speed (slow-mo)\n"
        "• **0.75x** - Slightly slower\n"
        "• **1.0x** - Normal speed\n"
        "• **1.5x** - Faster playback\n"
        "• **2.0x** - Double speed (time-lapse)\n\n"
        "**📝 Effects:**\n"
        "• Audio pitch is maintained\n"
        "• Video duration changes proportionally\n\n"
        "💡 **Tip:** Use 0.5x for cinematic slow-motion, 2x for quick recaps"))
    MSG_VT_VOLUME_MAIN = os.environ.get("MSG_VT_VOLUME_MAIN", (
        "🔊 **Audio Volume Adjuster**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Boost or reduce audio volume without re-encoding the entire video.\n\n"
        "**🎚️ Current Level:** `{volume}%`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "**🎯 Volume Levels:**\n"
        "• **50%** - Reduce to half\n"
        "• **100%** - Original volume\n"
        "• **150%** - 1.5x louder\n"
        "• **200%** - Double volume\n\n"
        "**⚠️ Important:**\n"
        "• Values >150% may cause distortion\n"
        "• Always preview audio quality\n\n"
        "💡 **Tip:** Use 120-150% for quiet recordings, 50-75% to reduce noise"
    ))
    MSG_VT_CROP_MAIN = os.environ.get("MSG_VT_CROP_MAIN", (
        "✂️ **Smart Crop Tool**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Resize your video to fit different platform requirements perfectly.\n\n"
        "**📐 Current Ratio:** `{aspect_ratio}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "**📱 Platform Presets:**\n"
        "• **16:9** - YouTube, Landscape (default)\n"
        "• **9:16** - TikTok, Instagram Reels, Stories\n"
        "• **4:3** - Classic TV, vintage look\n"
        "• **1:1** - Instagram Posts, Square\n\n"
        "**🎯 Auto-Centering:**\n"
        "Content is automatically centered during crop\n\n"
        "💡 **Tip:** Use 9:16 for vertical social media, 16:9 for desktop viewing"
    ))
    MSG_VT_GIF_MAIN = os.environ.get("MSG_VT_GIF_MAIN", (
        "🎞️ **GIF Conversion Studio**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Convert videos to animated GIFs optimized for web and social media.\n\n"
        "**⚙️ Current Settings:**\n"
        "📊 **FPS:** `{fps}`\n"
        "🎨 **Quality:** `{quality}`\n"
        "📏 **Scale:** `{scale}px`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "**🎯 Quality Presets:**\n"
        "• **Low** - Smaller file, faster loading\n"
        "• **Medium** - Balanced (recommended)\n"
        "• **High** - Best quality, larger file\n\n"
        "**📊 FPS Guide:**\n"
        "• 10-15 FPS: Smooth, smaller file\n"
        "• 20-25 FPS: High quality, larger file\n\n"
        "💡 **Tip:** Use 10 FPS + Medium quality for best balance"))
    MSG_VT_REVERSE_MAIN = os.environ.get("MSG_VT_REVERSE_MAIN", (
        "⏪ **Video Reverser**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Play your video in reverse for creative effects and unique perspectives.\n\n"
        "**🎬 What Gets Reversed:**\n"
        "✅ Video frames (backward playback)\n"
        "✅ Audio track (reversed sound)\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "**🎨 Creative Uses:**\n"
        "• Unique visual effects\n"
        "• Reverse motion shots\n"
        "• Comedic timing adjustments\n"
        "• Magical reveal effects\n\n"
        "**⚠️ Note:**\n"
        "Processing time depends on video length\n\n"
        "💡 **Tip:** Works best with short clips (< 30 seconds)"))
    MSG_VT_EXTRACT_THUMB_MAIN = os.environ.get(
        "MSG_VT_EXTRACT_THUMB_MAIN",
        ("**📸 Extract Thumbnail Settings**\n\n"
         "Extract thumbnail images from your video.\n\n"
         "• **Mode:** `{mode}`\n"
         "• **Timestamp:** `{timestamp}`\n"
         "• **Count:** `{count}`"))
    MSG_VT_SCREENSHOT_MAIN = os.environ.get(
        "MSG_VT_SCREENSHOT_MAIN",
        ("📸 **Video Screenshot Tool**\n\n"
         "━━━━━━━━━━━━━━━━━━━━━━\n\n"
         "Extract high-quality screenshots from your video.\n\n"
         "**🎯 Current Settings:**\n"
         "• **Timestamp:** `{timestamp}`\n"
         "• **Count:** `{count}` screenshots\n"
         "• **Mode:** `{mode}`\n\n"
         "━━━━━━━━━━━━━━━━━━━━━━\n\n"
         "**📋 Modes:**\n"
         "• **Single** – Capture 1 frame\n"
         "• **Multiple** – Capture N frames\n"
         "• **Auto** – Capture frames at equal intervals\n\n"
         "💡 **Tip:** Use 'Multiple' mode to generate preview strips!"))

    # --- NEW: Extract and Extra Tools Main Menus ---
    MSG_VT_EXTRACT_MAIN = os.environ.get(
        "MSG_VT_EXTRACT_MAIN",
        ("**📦 Extract Settings**\n\n"
         "Select what you want to extract from your video file.\n\n"
         "• **Current Mode:** `{mode}`\n\n"
         "After selecting a mode, click 'Enable this Tool' to activate."))
    MSG_VT_EXTRA_TOOLS_MAIN = os.environ.get("MSG_VT_EXTRA_TOOLS_MAIN", (
        "**🔧 Extra Tools**\n\n"
        "Additional video processing tools. Select a tool to configure and enable it.\n\n"
        "Click on any tool below to access its settings."))

    # --- VT Granular Menus (v6.0) ---
    MSG_VT_ENCODE_VCODEC_MENU = os.environ.get("MSG_VT_ENCODE_VCODEC_MENU",
                                               "Select a **Video Codec**:")
    MSG_VT_ENCODE_CRF_MENU = os.environ.get(
        "MSG_VT_ENCODE_CRF_MENU",
        "Select a **CRF (Quality)** value (Lower is better):")
    MSG_VT_ENCODE_PRESET_MENU = os.environ.get(
        "MSG_VT_ENCODE_PRESET_MENU",
        "Select a **Speed Preset** (Slower is better):")
    MSG_VT_ENCODE_RESOLUTION_MENU = os.environ.get(
        "MSG_VT_ENCODE_RESOLUTION_MENU", "Select a **Resolution**:")
    MSG_VT_ENCODE_ACODEC_MENU = os.environ.get("MSG_VT_ENCODE_ACODEC_MENU",
                                               "Select an **Audio Codec**:")
    MSG_VT_WATERMARK_POSITION_MENU = os.environ.get(
        "MSG_VT_WATERMARK_POSITION_MENU", "Select a **Watermark Position**:")
    MSG_VT_SAMPLE_FROM_MENU = os.environ.get(
        "MSG_VT_SAMPLE_FROM_MENU", "Select where to take the sample **From**:")
    MSG_VT_ROTATE_ANGLE_MENU = os.environ.get("MSG_VT_ROTATE_ANGLE_MENU",
                                              "Select a **Rotation Angle**:")
    MSG_VT_FLIP_DIRECTION_MENU = os.environ.get(
        "MSG_VT_FLIP_DIRECTION_MENU", "Select a **Flip Direction**:")
    MSG_VT_SPEED_MENU = os.environ.get("MSG_VT_SPEED_MENU",
                                       "Select a **Speed Multiplier**:")
    MSG_VT_VOLUME_MENU = os.environ.get("MSG_VT_VOLUME_MENU",
                                        "Select a **Volume Level**:")
    MSG_VT_CROP_ASPECT_MENU = os.environ.get("MSG_VT_CROP_ASPECT_MENU",
                                             "Select an **Aspect Ratio**:")
    MSG_VT_GIF_FPS_MENU = os.environ.get("MSG_VT_GIF_FPS_MENU",
                                         "Select **GIF FPS**:")
    MSG_VT_GIF_QUALITY_MENU = os.environ.get("MSG_VT_GIF_QUALITY_MENU",
                                             "Select **GIF Quality**:")
    MSG_VT_GIF_SCALE_MENU = os.environ.get("MSG_VT_GIF_SCALE_MENU",
                                           "Select **GIF Scale**:")
    MSG_VT_THUMB_MODE_MENU = os.environ.get("MSG_VT_THUMB_MODE_MENU",
                                            "Select **Extraction Mode**:")

    # ==================== BOT PROMPT MESSAGES (English - v6.0) ====================
    # --- client.ask Prompts ---
    MSG_ASK_FILENAME = os.environ.get(
        "MSG_ASK_FILENAME",
        "✏️ **Enter New Default Filename**\n\nPlease send the new filename (one word, no extension). Type /cancel to abort."
    )
    MSG_ASK_THUMBNAIL = os.environ.get(
        "MSG_ASK_THUMBNAIL",
        "🖼️ **Send New Default Thumbnail**\n\nPlease send a photo. Type /cancel to abort."
    )

    # (Granular Asks)
    MSG_ASK_TRIM_START = os.environ.get(
        "MSG_ASK_TRIM_START",
        "✂️ **Enter Start Time**\n\nPlease send the start time in `HH:MM:SS` format (e.g., `00:01:30`) or seconds (e.g., `90`). Type /cancel to abort."
    )
    MSG_ASK_TRIM_END = os.environ.get(
        "MSG_ASK_TRIM_END",
        "✂️ **Enter End Time**\n\nPlease send the end time in `HH:MM:SS` format (e.g., `00:05:00`) or seconds (e.g., `300`). Type /cancel to abort."
    )
    MSG_ASK_WATERMARK_TEXT = os.environ.get(
        "MSG_ASK_WATERMARK_TEXT",
        "✍️ **Enter Watermark Text**\n\nPlease send the text. Type /cancel to abort."
    )
    MSG_ASK_WATERMARK_IMAGE = os.environ.get(
        "MSG_ASK_WATERMARK_IMAGE",
        "🏞️ **Send Watermark Image**\n\nPlease send a compressed photo. Type /cancel to abort."
    )
    MSG_ASK_CUSTOM_CRF = os.environ.get(
        "MSG_ASK_CUSTOM_CRF", "Enter **Custom CRF** (0-51, e.g., `23`):")
    MSG_ASK_CUSTOM_RESOLUTION = os.environ.get(
        "MSG_ASK_CUSTOM_RESOLUTION",
        "Enter **Custom Resolution** (e.g., `1280x720`):")
    MSG_ASK_CUSTOM_ABITRATE = os.environ.get(
        "MSG_ASK_CUSTOM_ABITRATE",
        "Enter **Custom Audio Bitrate** (e.g., `192k`):")
    MSG_ASK_ENCODE_SUFFIX = os.environ.get(
        "MSG_ASK_ENCODE_SUFFIX",
        "Enter a **Filename Suffix** (e.g., `[HEVC]`):")
    MSG_ASK_SAMPLE_DURATION = os.environ.get(
        "MSG_ASK_SAMPLE_DURATION", "Enter **Sample Duration** (in seconds):")
    MSG_ASK_VOLUME_LEVEL = os.environ.get(
        "MSG_ASK_VOLUME_LEVEL",
        "Enter **Volume Level** (e.g., `50` for 50%, `200` for 200%):")
    MSG_ASK_THUMB_TIMESTAMP = os.environ.get(
        "MSG_ASK_THUMB_TIMESTAMP",
        "Enter **Timestamp** (e.g., `00:01:30` or `90` for 90 seconds):")
    MSG_ASK_THUMB_COUNT = os.environ.get(
        "MSG_ASK_THUMB_COUNT", "Enter **Number of Thumbnails** to extract:")
    MSG_ASK_CUSTOM_SPEED = os.environ.get(
        "MSG_ASK_CUSTOM_SPEED",
        "Enter **Custom Speed** (e.g., `0.75` for 75%, `1.5` for 150%):")
    MSG_ASK_GIF_FPS = os.environ.get(
        "MSG_ASK_GIF_FPS", "Enter **GIF FPS** (recommended: 10-15):")
    MSG_ASK_GIF_SCALE = os.environ.get(
        "MSG_ASK_GIF_SCALE",
        "Enter **GIF Scale** (e.g., `480` for 480p width):")

    # --- client.ask Success/Fail ---
    MSG_SET_SUCCESS = os.environ.get("MSG_SET_SUCCESS",
                                     "✅ Setting updated.")  # Generic
    MSG_SET_ERROR_FILENAME = os.environ.get(
        "MSG_SET_ERROR_FILENAME",
        "❌ Invalid filename. Must be one word, no extension.")
    MSG_SET_ERROR_TRIM_TIME = os.environ.get(
        "MSG_SET_ERROR_TRIM_TIME",
        "❌ Invalid format. Must be `HH:MM:SS` or seconds.")
    MSG_SET_ERROR_NOT_PHOTO = os.environ.get(
        "MSG_SET_ERROR_NOT_PHOTO",
        "❌ That's not a photo. Please send a compressed photo.")
    MSG_SET_ERROR_CRF = os.environ.get(
        "MSG_SET_ERROR_CRF", "❌ Invalid CRF. Must be a number (0-51).")
    MSG_SET_ERROR_RESOLUTION = os.environ.get(
        "MSG_SET_ERROR_RESOLUTION",
        "❌ Invalid Resolution. Must be `WidthxHeight`.")
    MSG_SET_ERROR_BITRATE = os.environ.get(
        "MSG_SET_ERROR_BITRATE", "❌ Invalid Bitrate. Must be like `128k`.")
    MSG_SET_ERROR_DURATION = os.environ.get(
        "MSG_SET_ERROR_DURATION",
        "❌ Invalid Duration. Must be a number (seconds).")

    MSG_SET_TIMEOUT = os.environ.get("MSG_SET_TIMEOUT",
                                     "⏰ Timeout. No changes were made.")
    MSG_SET_CANCELLED = os.environ.get("MSG_SET_CANCELLED",
                                       "🚫 Operation cancelled.")

    # ==================== BOT GENERIC MESSAGES (English - v6.0) ====================
    # --- Auth ---
    MSG_PRIVATE_CHAT_RESTRICTED = "🚫 **Private Chat Restricted**\nPlease use me in authorized groups."
    MSG_GROUP_NOT_AUTHORIZED = "❌ **Group Not Authorized**\nContact the owner to authorize this group."
    MSG_FSUB_REQUIRED = "🔒 **Access Denied!**\nTo use this bot, you must join **{title}** first. Click the button below to join, then click **'Check Again'**."
    MSG_FSUB_ERROR = "An error occurred while checking subscription. Please contact an admin."
    MSG_BANNED = "🚫 **You are banned.**\n\nContact the owner if you believe this is a mistake."

    # --- Task & Mode Errors ---
    MSG_SELECT_TOOL_FIRST = "❌ **No tool selected!**\nPlease use `/vt` to select and enable a tool (✅) before sending files."
    MSG_BOT_ON_HOLD = "⏸️ **Bot is globally on HOLD.**\nYour task will not be processed. Please wait for an admin to `/activate` the bot."
    MSG_USER_ON_HOLD = "⏸️ **Your tasks are ON HOLD.**\nYour task has been rejected. Use /hold to reactivate your tasks."
    MSG_USER_HOLD_ENABLED = "⏸️ **Your tasks are now ON HOLD.**\nI will reject new tasks from you until you use /hold again."
    MSG_USER_HOLD_DISABLED = "✅ **Your tasks are now ACTIVE.**\nI will now accept new tasks from you."
    MSG_TASK_IN_PROGRESS = "⏳ **You already have a task in progress.**\nPlease wait for it to complete or use /cancel to stop it."
    MSG_NO_ACTIVE_TASK = "You have no active tasks to cancel."

    # --- Mode Mismatch ---
    MSG_MODE_MISMATCH_URL = "❌ **Download Mode Mismatch!**\nYour current download mode is set to **Telegram**. Please use `/us` to change your mode to **URL** to send links."
    MSG_MODE_MISMATCH_FILE = "❌ **Download Mode Mismatch!**\nYour current download mode is set to **URL**. Please use `/us` to change your mode to **Telegram** to send files."

    # --- Merge Tool ---
    MSG_MERGE_FILE_ONE = "✅ **Merge Mode: File 1 added.**\n\nPlease send your other files. When finished, send /process"
    MSG_MERGE_FILE_NEXT = "✅ **Merge Mode: File {count} added.**\n\nSend more files or use /process to start merging."
    MSG_PROCESS_FOR_MERGE_ONLY = "❌ **/process command is only for 'merge' tool.**\nYour active tool is `{active_tool}`. Please send a single file."
    MSG_MERGE_NO_FILES = "❌ **Not enough files to merge!**\nPlease send at least 2 files before using /process."
    MSG_MERGE_URL_REJECTED = "❌ **Merge tool does not support URLs.**\nPlease set download mode to **Telegram** and send files."

    # --- Task Lifecycle ---
    MSG_TASK_ACCEPTED = "⏳ **Task `{task_id}` Accepted.**\nInitializing task... Tool: `MERGE` ({count} files)"
    MSG_TASK_ACCEPTED_SINGLE = "⏳ **Task `{task_id}` Accepted.**\nInitializing task... Tool: `{tool}`"
    MSG_DOWNLOAD_MERGE_PROGRESS = "⏳ **Task `{task_id}`: Downloading...**\nTool: `MERGE`\nDownloading file {file_num} of {total_files}..."
    MSG_TASK_CANCELLED = "🚫 **Task `{task_id}` Cancelled!**\n✅ All processes stopped and temporary files cleaned."
    MSG_TASK_FAILED = "❌ **Task `{task_id}` Failed!**\n\n`{error}`"
    MSG_MEDIAINFO_COMPLETE = "✅ **Task `{task_id}` Complete!**\nTool: `MediaInfo`\nMediaInfo has been sent."

    # --- Upload ---
    MSG_FORCE_GOFILE = "File size (`{size}`) is larger than 2GB.\n**Forcing GoFile upload.**"
    MSG_UPLOAD_COMPLETE = "✅ **Task `{task_id}` Complete!**\n\n👤 **User:** {user_mention}\n**File:** `{file_name}`\n**Size:** `{file_size}`"
    MSG_UPLOAD_COMPLETE_GOFILE = "✅ **Task `{task_id}` Complete!**\n\n👤 **User:** {user_mention}\n🔗 **Link:** {link}"
    MSG_FLOOD_WAIT = "⏳ FloodWait... sleeping for {seconds}s."
    MSG_UPLOAD_FAILED = "❌ **Upload Failed!**\n\n`{error}`"


# ==================== VALIDATION & CONVERSION ====================


def validate_config():
    """Validate and convert configuration values"""

    # MODIFIED: Added all new BTN_ and MSG_ variables
    string_vars = [
        "API_HASH",
        "BOT_TOKEN",
        "MONGO_URI",
        "DATABASE_NAME",
        "FORCE_SUB_CHANNEL",
        "UPDATE_CHANNEL",
        "SUPPORT_GROUP",
        "BOT_NAME",
        "BOT_USERNAME",
        "DEVELOPER",
        "IMG_START",
        "IMG_SETTINGS",
        "IMG_TOOLS",
        "IMG_FSUB",
        "IMG_ADMIN",
        "GOFILE_TOKEN",

        # --- Buttons (v6.0) ---
        "BTN_USER_SETTINGS",
        "BTN_VIDEO_TOOLS",
        "BTN_ABOUT",
        "BTN_HELP",
        "BTN_UPDATES",
        "BTN_SUPPORT",
        "BTN_BACK",
        "BTN_VT_BACK",
        "BTN_CANCEL",
        "BTN_ENABLE_TOOL",
        "BTN_UPLOAD_MODE",
        "BTN_DOWNLOAD_MODE",
        "BTN_USER_HOLD",
        "BTN_METADATA",
        "BTN_THUMBNAIL",
        "BTN_CLEAR_THUMB",
        "BTN_SET_FILENAME",
        "BTN_MERGE",
        "BTN_ENCODE",
        "BTN_TRIM",
        "BTN_WATERMARK",
        "BTN_SAMPLE",
        "BTN_MEDIAINFO",
        "BTN_ROTATE",
        "BTN_FLIP",
        "BTN_SPEED",
        "BTN_VOLUME",
        "BTN_CROP",
        "BTN_GIF",
        "BTN_REVERSE",
        "BTN_EXTRACT_THUMB",
        "BTN_EXTRACT",
        "BTN_EXTRA_TOOLS",
        "BTN_EXTRACT_VIDEO",
        "BTN_EXTRACT_AUDIO",
        "BTN_EXTRACT_SUBTITLES",
        "BTN_EXTRACT_THUMBNAILS",
        "BTN_MERGE_VID",
        "BTN_MERGE_AUD",
        "BTN_MERGE_SUB",
        "BTN_ENCODE_VCODEC",
        "BTN_ENCODE_CRF",
        "BTN_ENCODE_PRESET",
        "BTN_ENCODE_RESOLUTION",
        "BTN_ENCODE_ACODEC",
        "BTN_ENCODE_ABITRATE",
        "BTN_ENCODE_SUFFIX",
        "BTN_TRIM_START",
        "BTN_TRIM_END",
        "BTN_WATERMARK_TYPE",
        "BTN_WATERMARK_TEXT",
        "BTN_WATERMARK_IMAGE",
        "BTN_WATERMARK_POSITION",
        "BTN_WATERMARK_OPACITY",
        "BTN_SAMPLE_DURATION",
        "BTN_SAMPLE_FROM",
        "BTN_ROTATE_ANGLE",
        "BTN_FLIP_DIRECTION",
        "BTN_SPEED_MULTIPLIER",
        "BTN_VOLUME_LEVEL",
        "BTN_CROP_ASPECT",
        "BTN_GIF_FPS",
        "BTN_GIF_QUALITY",
        "BTN_GIF_SCALE",
        "BTN_THUMB_MODE",
        "BTN_THUMB_TIMESTAMP",
        "BTN_THUMB_COUNT",
        "BTN_ADMIN_STATS",
        "BTN_ADMIN_TASKS",
        "BTN_ADMIN_BROADCAST",
        "BTN_ADMIN_RESTART",

        # --- UI Messages (v6.0) ---
        "MSG_START",
        "MSG_HELP",
        "MSG_ABOUT",
        "MSG_USER_SETTINGS",
        "MSG_VIDEO_TOOLS",
        "MSG_ADMIN_PANEL",
        "MSG_VT_MERGE_MAIN",
        "MSG_VT_ENCODE_MAIN",
        "MSG_VT_TRIM_MAIN",
        "MSG_VT_WATERMARK_MAIN",
        "MSG_VT_SAMPLE_MAIN",
        "MSG_VT_ROTATE_MAIN",
        "MSG_VT_FLIP_MAIN",
        "MSG_VT_SPEED_MAIN",
        "MSG_VT_VOLUME_MAIN",
        "MSG_VT_CROP_MAIN",
        "MSG_VT_GIF_MAIN",
        "MSG_VT_REVERSE_MAIN",
        "MSG_VT_EXTRACT_THUMB_MAIN",
        "MSG_VT_EXTRACT_MAIN",
        "MSG_VT_EXTRA_TOOLS_MAIN",
        "MSG_VT_ENCODE_VCODEC_MENU",
        "MSG_VT_ENCODE_CRF_MENU",
        "MSG_VT_ENCODE_PRESET_MENU",
        "MSG_VT_ENCODE_RESOLUTION_MENU",
        "MSG_VT_ENCODE_ACODEC_MENU",
        "MSG_VT_WATERMARK_POSITION_MENU",
        "MSG_VT_SAMPLE_FROM_MENU",
        "MSG_VT_ROTATE_ANGLE_MENU",
        "MSG_VT_FLIP_DIRECTION_MENU",
        "MSG_VT_SPEED_MENU",
        "MSG_VT_VOLUME_MENU",
        "MSG_VT_CROP_ASPECT_MENU",
        "MSG_VT_GIF_FPS_MENU",
        "MSG_VT_GIF_QUALITY_MENU",
        "MSG_VT_GIF_SCALE_MENU",
        "MSG_VT_THUMB_MODE_MENU",
        "MSG_VT_SCREENSHOT_MAIN",

        # --- Prompt Messages (v6.0) ---
        "MSG_ASK_FILENAME",
        "MSG_ASK_THUMBNAIL",
        "MSG_ASK_TRIM_START",
        "MSG_ASK_TRIM_END",
        "MSG_ASK_WATERMARK_TEXT",
        "MSG_ASK_WATERMARK_IMAGE",
        "MSG_ASK_CUSTOM_CRF",
        "MSG_ASK_CUSTOM_RESOLUTION",
        "MSG_ASK_CUSTOM_ABITRATE",
        "MSG_ASK_ENCODE_SUFFIX",
        "MSG_ASK_SAMPLE_DURATION",
        "MSG_ASK_VOLUME_LEVEL",
        "MSG_ASK_THUMB_TIMESTAMP",
        "MSG_ASK_THUMB_COUNT",
        "MSG_ASK_CUSTOM_SPEED",
        "MSG_ASK_GIF_FPS",
        "MSG_ASK_GIF_SCALE",
        "MSG_SET_SUCCESS",
        "MSG_SET_ERROR_FILENAME",
        "MSG_SET_ERROR_TRIM_TIME",
        "MSG_SET_ERROR_NOT_PHOTO",
        "MSG_SET_ERROR_CRF",
        "MSG_SET_ERROR_RESOLUTION",
        "MSG_SET_ERROR_BITRATE",
        "MSG_SET_ERROR_DURATION",
        "MSG_SET_TIMEOUT",
        "MSG_SET_CANCELLED",

        # --- Generic Messages (v6.0) ---
        "MSG_PRIVATE_CHAT_RESTRICTED",
        "MSG_GROUP_NOT_AUTHORIZED",
        "MSG_FSUB_REQUIRED",
        "MSG_FSUB_ERROR",
        "MSG_BANNED",
        "MSG_SELECT_TOOL_FIRST",
        "MSG_BOT_ON_HOLD",
        "MSG_USER_ON_HOLD",
        "MSG_USER_HOLD_ENABLED",
        "MSG_USER_HOLD_DISABLED",
        "MSG_TASK_IN_PROGRESS",
        "MSG_NO_ACTIVE_TASK",
        "MSG_MODE_MISMATCH_URL",
        "MSG_MODE_MISMATCH_FILE",
        "MSG_MERGE_FILE_ONE",
        "MSG_MERGE_FILE_NEXT",
        "MSG_PROCESS_FOR_MERGE_ONLY",
        "MSG_MERGE_NO_FILES",
        "MSG_MERGE_URL_REJECTED",
        "MSG_TASK_ACCEPTED",
        "MSG_TASK_ACCEPTED_SINGLE",
        "MSG_DOWNLOAD_MERGE_PROGRESS",
        "MSG_TASK_CANCELLED",
        "MSG_TASK_FAILED",
        "MSG_MEDIAINFO_COMPLETE",
        "MSG_FORCE_GOFILE",
        "MSG_UPLOAD_COMPLETE",
        "MSG_UPLOAD_COMPLETE_GOFILE",
        "MSG_FLOOD_WAIT",
        "MSG_UPLOAD_FAILED"
    ]

    for var in string_vars:
        if hasattr(Config, var):
            setattr(Config, var, clean_value(getattr(Config, var)))

    # --- Validation ---
    required = ["API_ID", "API_HASH", "BOT_TOKEN", "OWNER_ID", "MONGO_URI"]
    missing = [var for var in required if not getattr(Config, var, None)]

    if missing:
        raise ValueError(
            f"❌ Missing required environment variables: {', '.join(missing)}")

    # Convert numeric and list variables (API_ID, OWNER_ID, LOG_CHANNEL, TASK_LOG_CHANNEL already converted above)
    try:
        # Only convert PROCESS_POLL_INTERVAL_S and PROCESS_CANCEL_TIMEOUT_S if they're strings
        if isinstance(Config.PROCESS_POLL_INTERVAL_S, str):
            Config.PROCESS_POLL_INTERVAL_S = int(
                clean_value(str(Config.PROCESS_POLL_INTERVAL_S)))
        else:
            Config.PROCESS_POLL_INTERVAL_S = int(
                Config.PROCESS_POLL_INTERVAL_S)

        if isinstance(Config.PROCESS_CANCEL_TIMEOUT_S, str):
            Config.PROCESS_CANCEL_TIMEOUT_S = int(
                clean_value(str(Config.PROCESS_CANCEL_TIMEOUT_S)))
        else:
            Config.PROCESS_CANCEL_TIMEOUT_S = int(
                Config.PROCESS_CANCEL_TIMEOUT_S)

        def to_int_list(var_str):
            if var_str:
                return [
                    int(clean_value(x)) for x in var_str.split(",")
                    if clean_value(x).lstrip('-').isdigit()
                ]
            return []

        Config.ADMINS = to_int_list(Config.ADMINS)
        Config.SUDO_USERS = to_int_list(Config.SUDO_USERS)

        if Config.OWNER_ID not in Config.ADMINS:
            Config.ADMINS.append(Config.OWNER_ID)
        if Config.OWNER_ID not in Config.SUDO_USERS:
            Config.SUDO_USERS.append(Config.OWNER_ID)

    except ValueError as e:
        logger.error(f"Config validation error: {e}", exc_info=True)
        raise ValueError(f"❌ Configuration error: {e}")

    # Check for @ in channel usernames
    for name in ["FORCE_SUB_CHANNEL", "UPDATE_CHANNEL", "SUPPORT_GROUP"]:
        value = getattr(Config, name)
        if value and not (value.startswith('@')
                          or value.lstrip('-').isdigit()):
            print(
                f"⚠️ Warning: {name} ({value}) should start with @ or be a numeric ID"
            )

    # Ensure download directory exists
    if not os.path.isdir(Config.DOWNLOAD_DIR):
        try:
            os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)
            print(f"Created download directory: {Config.DOWNLOAD_DIR}")
        except Exception as e:
            logger.error(f"Could not create download directory: {e}")
            raise

    # --- Format final text strings ---
    try:
        # Note: We skip formatting strings that need runtime values like {user_name}
        # MSG_ABOUT formatting is now done at runtime in bot.py
        pass
    except Exception as e:
        logger.warning(f"Failed to pre-format some text strings: {e}")


# Run validation
validate_config()

# Create singleton instance
config = Config()
