# SS Video Workstation Bot

A professional Telegram bot for comprehensive video processing and manipulation operations.

## Features

### Video Processing Tools
- **Merge**: Combine multiple video files with advanced options
- **Encode**: Convert videos with H.264/H.265 encoding
- **Trim**: Cut videos to specific time ranges
- **Watermark**: Add text/image overlays to videos
- **Sample/Screenshots**: Generate video samples and screenshots
- **Extract**: Extract audio/video streams
- **Rotate/Flip**: Transform video orientation
- **Speed/Volume**: Adjust playback speed and audio volume
- **Crop**: Crop videos to custom dimensions
- **GIF Conversion**: Convert videos to animated GIFs
- **Reverse**: Reverse video playback

### Advanced Features
- **Queue Management**: Organize files for batch merge operations
- **GoFile.io Integration**: Upload large files without Telegram limits
- **Telegraph Integration**: Share media information as web pages
- **Progress Tracking**: Real-time progress updates with ETA
- **Custom Thumbnails**: Set custom video thumbnails
- **Metadata Control**: Keep or clear video metadata
- **Bot State Management**: ACTIVE/HOLD mode control for admins

## Project Structure

```
.
├── main.py                 # Bot entry point and initialization
├── config.py              # Configuration management
├── handlers/              # Modular handler organization
│   ├── start_handlers.py      # Start menu, help, about, settings
│   ├── admin_handlers.py      # Admin commands and controls
│   ├── task_handlers.py       # Video processing task initiation
│   └── callback_handlers.py   # Inline button callbacks
├── modules/               # Core functionality modules
│   ├── database.py           # MongoDB operations
│   ├── processor.py          # Task processing engine
│   ├── ffmpeg_tools.py       # FFmpeg video operations
│   ├── queue_manager.py      # File queue management
│   ├── ui_core.py            # UI theming and styling
│   ├── ui_menus.py           # Menu generation functions
│   ├── progress_ui.py        # Progress display formatting
│   ├── helpers.py            # Utility functions
│   └── bot_state.py          # Bot state management
└── downloads/             # Temporary file storage

## Recent Refactoring (November 2025)

The codebase underwent a major refactoring to improve maintainability and organization:

### Before
- Single monolithic `bot.py` file (1373 lines)
- All handlers mixed together
- Difficult to navigate and maintain

### After
- Modular handler structure with clear separation of concerns:
  - **start_handlers.py**: User-facing commands and menus
  - **admin_handlers.py**: Administrative functions
  - **task_handlers.py**: Video processing task handlers
  - **callback_handlers.py**: Inline keyboard callbacks
- Clean `main.py` entry point
- Each module focuses on a specific responsibility
- Easier testing and future development

### Key Improvements
✅ No circular import issues
✅ All handlers register correctly
✅ Preserved all original functionality
✅ Better code organization
✅ Easier to add new features

## Installation

### Prerequisites
- Python 3.11+
- MongoDB
- FFmpeg and FFprobe
- MediaInfo (optional, for detailed media analysis)

### Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd ss-video-workstation-bot
```

2. **Install Python dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables**
```bash
cp config.env.example config.env
# Edit config.env with your credentials
```

Required configuration:
- `API_ID`: Telegram API ID from https://my.telegram.org
- `API_HASH`: Telegram API Hash
- `BOT_TOKEN`: Bot token from @BotFather
- `MONGO_URI`: MongoDB connection string (default: mongodb://localhost:27017)
- `OWNER_ID`: Your Telegram user ID (get from @userinfobot)

Optional configuration:
- `FORCE_SUB_CHANNEL`: Channel username for forced subscription
- `TASK_LOG_CHANNEL`: Channel ID for task logging
- `GOFILE_TOKEN`: GoFile.io API token for large file uploads
- `UPDATE_CHANNEL`: Your updates channel username
- `SUPPORT_GROUP`: Your support group username

4. **Start MongoDB**
```bash
# Using system MongoDB
sudo systemctl start mongodb

# Or using Docker
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

5. **Run the bot**
```bash
python main.py
```

## Usage

### For Users

1. Start the bot with `/start`
2. Choose a video tool from the menu
3. Follow the prompts to upload files and configure settings
4. Receive processed videos directly in Telegram or via GoFile.io links

### For Admins

- `/activate` - Enable bot for all users (default is HOLD mode)
- `/deactivate` - Restrict bot to admins only
- `/stats` - View bot statistics
- `/broadcast` - Send messages to all users
- `/auth` - Authorize groups/channels

## Architecture

### Handler Registration Flow
```
main.py
  ├── Initialize Pyrogram Client
  ├── Connect to MongoDB
  ├── Register handlers (modular)
  │   ├── start_handlers.register_start_handlers()
  │   ├── admin_handlers.register_admin_handlers()
  │   ├── task_handlers.register_task_handlers()
  │   └── callback_handlers.register_callback_handlers()
  └── Start bot
```

### Task Processing Pipeline
```
User Input → Task Creation → Queue → Download → Process → Upload → Cleanup
                                        ↓
                                    Progress Updates
```

### Key Design Decisions

**Modular Handlers**: Separating handlers by responsibility improves code navigation and allows independent testing of different features.

**Async-First**: Full async/await architecture provides better resource utilization for I/O-bound operations (network, disk).

**MongoDB**: NoSQL chosen for flexibility in evolving settings structure without schema migrations.

**FFmpeg**: Industry-standard video processing with excellent format support and real-time progress tracking.

## Dependencies

### Core Framework
- `pyrogram` - Telegram MTProto framework
- `tgcrypto` - Encryption for Pyrogram
- `pyromod` - Conversation flow helpers

### Database
- `motor` - Async MongoDB driver
- `pymongo` - Synchronous MongoDB driver

### Media Processing
- `ffmpeg-python` - FFmpeg Python bindings
- `pymediainfo` - MediaInfo wrapper
- `Pillow` - Image processing

### Utilities
- `python-dotenv` - Environment configuration
- `humanize` - Human-readable formatting
- `psutil` - System monitoring
- `aiohttp` - Async HTTP client
- `yt-dlp` - Video downloading
- `matplotlib` - Graph generation

## Development

### Adding New Handlers

1. Choose the appropriate handler file based on functionality
2. Add the handler function with proper decorators
3. No need to modify `main.py` - handlers auto-register

Example:
```python
# In handlers/task_handlers.py
@app.on_message(filters.command("newtool"))
async def new_tool_handler(client: Client, message: Message):
    # Your handler code
    pass
```

### Testing

The bot requires valid Telegram credentials to test. Configure `config.env` with test credentials and run:

```bash
python main.py
```

Monitor logs for handler registration and error messages.

## Troubleshooting

### Bot won't start
- Verify `API_ID`, `API_HASH`, and `BOT_TOKEN` are correct
- Check MongoDB is running and accessible
- Ensure FFmpeg is installed: `ffmpeg -version`

### Handlers not responding
- Check bot is in ACTIVE mode (use `/activate` command)
- Verify user/chat authorization
- Check logs for errors

### Video processing fails
- Verify FFmpeg is installed correctly
- Check available disk space
- Review task logs for specific error messages

## License

This project is for educational and personal use.

## Support

For issues and questions, contact the bot developer or join the support group (if configured).
