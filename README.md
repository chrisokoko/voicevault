# VoiceVault 🎙️

**Transform hundreds of scattered voice memos into an organized, searchable vault of personal insights with intelligent data-driven taxonomy.**

Turn your audio chaos into curated, searchable knowledge! VoiceVault automatically transcribes, categorizes, and intelligently organizes your voice notes in Notion using AI-powered analysis and data-driven taxonomy generation.

## 🎯 **The Problem VoiceVault Solves**

You probably have hundreds of voice notes on your phone. They were captured for a reason - insights, ideas, reflections, reminders. But now:

- **It would take hundreds of hours** to listen through them all
- **They're impossible to search** or find when you need them  
- **Context is lost** - you can't remember what each one contains
- **They're not organized** - no categories, tags, or structure
- **They're trapped on your phone** - not integrated with your knowledge system

## 🚀 **The VoiceVault Solution**

VoiceVault **gets your voice memos out of audio prison** and into your Notion workspace where they become:

✅ **Fully transcribed** with AI-improved readability  
✅ **Intelligently categorized** with data-driven taxonomy system  
✅ **Searchable and filterable** by multiple Life Areas and Topics  
✅ **Contextually organized** with summaries and metadata  
✅ **Smart deletion flagging** - automatically identifies content to review/delete  
✅ **Multiple category assignment** - each memo can have multiple relevant life areas and topics

## ✨ Service-Based Architecture

VoiceVault features a **clean service-based architecture** that transforms your scattered voice memos into an organized knowledge vault through automated processing and intelligent categorization.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd voicevault
pip install -r requirements.txt
brew install ffmpeg  # On macOS
```

### 2. Configuration
Create your configuration file:
```bash
cp config/config.py.example config/config.py
```

Edit `config/config.py` with your API keys:
```python
NOTION_TOKEN = "your_notion_integration_token"
NOTION_DATABASE_ID = "your_database_id"  # Optional - will create if not provided
CLAUDE_API_KEY = "your_claude_api_key"  # Required for taxonomy system
AUDIO_FOLDER = "./audio_files"  # Default folder for your voice notes
```

### 3. Set up Notion Integration
1. Create integration at https://www.notion.so/my-integrations
2. Copy the integration token to your config
3. Share your database with the integration (or let the script create one)

## 🎙️ **Processing Your Voice Memos**

### 🚀 **Main Processing**

Transform your voice memos into organized knowledge with the main processing script:

```bash
# Process new voice memos
python3 ongoing_main_process_new_voice_memo.py

# Process with specific phases
python3 phase1-create-pages-and-get-pages.py
python3 phase2-transcribe.py  
python3 phase3-final.py
```

## 📁 **Folder Structure & Workflow**
```
audio_files/
├── [Your 500+ voice notes go here]    # Main processing queue
├── success/                           # ✅ Successfully processed files (auto-moved)
├── test_keep/                         # 🧪 Positive test examples  
└── test_delete/                       # 🗑️  Negative test examples
```

## 🔧 **Efficient Processing**

VoiceVault is designed for efficiency:

**✅ Automated Processing**: Handles transcription, analysis, and organization automatically
**✅ Smart File Management**: Moves processed files to appropriate directories
**✅ Progress Tracking**: Maintains state between processing sessions
**✅ Error Handling**: Robust error handling and recovery mechanisms

## 📊 What Gets Created in Notion

### Database Properties  
- **Title**: AI-generated specific title (e.g., "Inner Child Healing Session")
- **Primary Themes**: 1-2 main themes (e.g., "Self Love", "Spiritual Practice")
- **Specific Focus**: Detailed aspects (e.g., "Emotional Safety", "Personal Ceremony")  
- **Content Types**: Format types (e.g., "Personal Reflection", "Affirmation Letter")
- **Emotional Tones**: Feeling states (e.g., "Contemplative", "Nurturing")
- **Key Topics**: 3-6 specific topics (e.g., "Inner Peace", "Authentic Living")
- **Summary**: AI-generated 2-3 sentence summary
- **Duration**: Formatted duration (e.g., "5m 23s")
- **File Created**: Original recording date
- **Audio File**: Playable audio file in Notion
- **Flagged for Deletion**: Auto-flagged non-personal content

### Page Content
- **Formatted Transcript**: Claude-improved transcript with fixed grammar and readability
- **Original Transcript**: Raw transcription preserved in collapsible section
- **Claude Analysis**: Collapsible section with detailed AI reasoning
- **Metadata**: File information and processing details

## 🔧 System Architecture

```
voicevault/
├── ongoing_main_process_new_voice_memo.py  # 🚀 MAIN PROCESSING SCRIPT
├── phase1-create-pages-and-get-pages.py   # Phase 1: Create and extract pages
├── phase2-transcribe.py                    # Phase 2: Transcription processing
├── phase3-final.py                         # Phase 3: Final analysis and organization
├── src/                                    # 📁 CORE UTILITIES
│   └── transcriber.py                      # Core transcription utility
├── audio_files/                            # 📁 VOICE MEMO STORAGE
│   ├── [your voice notes]                  # ← Put your files here
│   ├── success/                            # ← Successfully processed files
│   ├── test_keep/                          # 🧪 Positive test examples
│   └── test_delete/                        # 🗑️ Negative test examples
├── config/
│   └── config.py                           # Configuration settings
├── requirements.txt                        # Python dependencies
├── database_config.json                    # Database configuration
└── processed_files.json                    # Processing tracking
```

## 📁 Supported File Formats

- `.m4a` (Apple Voice Memos)
- `.mp3`, `.wav`, `.aac`, `.flac`, `.ogg`
- Automatic format detection and conversion

## 🛠️ Troubleshooting

### Processing Issues

**1. Processing Fails**
```bash
# Check logs for detailed errors
tail -n 50 voice_memo_processor.log

# Test with main processing script
python3 ongoing_main_process_new_voice_memo.py
```

**2. Audio Transcription Problems**
- Verify ffmpeg installation: `ffmpeg -version`
- Check audio file isn't corrupted
- Try with a known good file first

### General Troubleshooting

**Reset and Restart**
```bash
# Clear all processing history (reprocess everything)
rm processed_files.json

# Start fresh processing
python3 ongoing_main_process_new_voice_memo.py
```

## 🎯 Best Practices

### For Voice Memo Processing
1. **Start Small**: Test with a few files initially
2. **Check Configuration**: Verify API keys and settings before processing
3. **Monitor Progress**: Watch processing logs for any issues
4. **Regular Processing**: Run the main script regularly to handle new voice memos

### For Large Collections (100+ files)
1. **Process in Sessions**: Handle large batches over time
2. **Monitor API Usage**: Track Claude and transcription API costs
3. **Check Results**: Review processed memos in Notion for quality

## 🚀 Ready to Start?

```bash
# Start processing your voice memos
python3 ongoing_main_process_new_voice_memo.py

# Or run individual phases
python3 phase1-create-pages-and-get-pages.py
python3 phase2-transcribe.py
python3 phase3-final.py
```

Your voice memo chaos is about to become an organized, searchable knowledge vault! 🎉

## 📚 What's Next?

After processing, you'll be able to:
- **Search transcribed content** in your Notion database
- **Browse organized summaries** and AI-generated insights
- **Access original audio** files directly from Notion
- **Find patterns** and connections across your voice memos
- **Transform scattered audio** into organized wisdom

**The days of lost voice memos are over!** 🎙️✨