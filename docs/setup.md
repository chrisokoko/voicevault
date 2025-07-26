# VoiceVault Setup Guide

## Prerequisites

- Python 3.9 or higher
- FFmpeg (for audio processing)
- Notion account with integration token
- Claude API key from Anthropic

### Install FFmpeg

**macOS (using Homebrew):**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
Download from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)

## Installation

1. **Clone the repository:**
```bash
git clone https://github.com/[username]/voicevault.git
cd voicevault
```

2. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set up configuration:**
```bash
cp config/config.py.example config/config.py
```

4. **Edit configuration file:**
Open `config/config.py` and add your API keys:
- `NOTION_TOKEN`: Your Notion integration token
- `CLAUDE_API_KEY`: Your Claude API key from Anthropic
- `NOTION_PARENT_PAGE_ID`: (Optional) Page where database will be created

## Getting API Keys

### Notion Integration Token

1. Go to [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click "New integration"
3. Give it a name like "VoiceVault"
4. Select the workspace
5. Copy the "Internal Integration Token"

### Claude API Key

1. Sign up at [https://console.anthropic.com/](https://console.anthropic.com/)
2. Navigate to "API Keys" section
3. Create a new API key
4. Copy the key

## Notion Database Setup

The application can automatically create a Notion database for you, or you can use an existing one:

**Option 1: Automatic Creation**
- Set `NOTION_PARENT_PAGE_ID` to the ID of a Notion page where you want the database created
- The system will create a new "Voice Memos" database on first run

**Option 2: Use Existing Database**
- Set `NOTION_DATABASE_ID` to your existing database ID
- Make sure your integration has access to the database

## Verify Installation

Run a test with a single audio file:
```bash
python main.py --file "path/to/test/audio.m4a" --dry-run
```

This should process the file without uploading to Notion and show you the analysis results.

## Folder Structure

Create your audio processing folders:
```bash
mkdir -p audio_files/success
mkdir -p audio_files/test_keep
mkdir -p audio_files/test_delete
```

- `audio_files/`: Main processing queue
- `audio_files/success/`: Successfully processed files (auto-moved)
- `audio_files/test_keep/`: Test examples you want to keep
- `audio_files/test_delete/`: Test examples for deletion