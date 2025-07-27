# VoiceVault 🎙️

**Transform hundreds of scattered voice memos into an organized, searchable vault of personal insights with intelligent hierarchical taxonomy.**

Have hundreds of voice memos on your phone that were useful when you recorded them, but now they're just digital clutter? VoiceVault solves this by automatically transcribing, categorizing, and intelligently organizing your voice notes in Notion - turning audio chaos into curated, filterable knowledge.

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
✅ **Intelligently categorized** with hierarchical taxonomy system  
✅ **Searchable and filterable** by Life Areas and Topics  
✅ **Contextually organized** with summaries and metadata  
✅ **Smart deletion flagging** - automatically identifies content to review/delete  
✅ **Data-driven taxonomy** - builds categories from your actual content, not theories  

## ✨ New: Hierarchical Taxonomy System

VoiceVault now features a **revolutionary 4-phase taxonomy system** that transforms your scattered voice memos into an organized knowledge vault:

### 🏗️ **4-Phase Processing Pipeline**

**Phase 1: Data Extraction** (`get_pages_and_tags.py`)
- Extracts all voice memos and existing tags from Notion
- Clean input/output interface
- Rate-limited API calls for reliability

**Phase 2: Taxonomy Building** (`classify_tags.py`)  
- Uses Claude AI to analyze your actual tags
- Builds data-driven Life Areas and Topics from your content
- Creates 12 Life Areas and 25+ Topics based on your real usage

**Phase 3: Intelligent Classification** (`claude_taxonomy_classifier.py`)
- Claude AI classifies each voice memo using the custom taxonomy
- Assigns multiple Life Areas and Topics per memo
- Efficient batch processing with result caching

**Phase 4: Notion Integration** (`update_notion_taxonomy.py`)
- Updates Notion database with hierarchical classifications
- Creates "Life Area" and "Topic" columns for filtering
- Enables finding 20+ related memos instead of 1-2 exact matches

### 🎯 **Taxonomy Benefits**

**Before**: "I have a tag called 'spiritual practice' with 2 voice memos"
**After**: "I can filter by Life Area 'Spiritual & Ceremonial' and find 25+ related memos across multiple topics"

**Multi-category Assignment**: Each voice memo gets multiple relevant Life Areas and Topics
**Hierarchical Filtering**: Start broad (Life Areas) then narrow down (Topics)
**Content Discovery**: Find patterns and connections across your voice memo collection

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

## 🎙️ **Two Processing Systems**

### 📊 **Option 1: Hierarchical Taxonomy System (Recommended)**

Transform your voice memos into an organized knowledge vault with intelligent categorization:

```bash
# Phase 1: Extract all voice memos and tags
python3 src/get_pages_and_tags.py --output data.json

# Phase 2: Build custom taxonomy from your actual content
python3 src/classify_tags.py --input data.json --output taxonomy.json

# Phase 3: Classify all voice memos using Claude + taxonomy  
python3 src/claude_taxonomy_classifier.py --pages data.json --taxonomy taxonomy.json --output results.json

# Phase 4: Update Notion with hierarchical categories
python3 src/update_notion_taxonomy.py --pages data.json --classifications results.json
```

**Result**: Your voice memos will have:
- **Life Areas**: Broad categories like "Spiritual & Ceremonial", "Business & Career"
- **Topics**: Specific themes like "Community Building", "Content Creation"
- **Multi-category assignment**: Each memo can have multiple relevant categories
- **Powerful filtering**: Find 20+ related memos instead of 1-2 exact matches

### 🎛️ **Option 2: Basic Voice Memo Processing**

For simple transcription and basic tagging:

```bash
# Process your main collection (files auto-move to success/ when done)
python3 main.py --folder audio_files

# Test with a few files first
python3 main.py --folder audio_files --dry-run --max-files 5

# Large batch processing with delays
python3 main.py --folder audio_files --batch-size 10 --batch-delay 3.0
```

## 📁 **Folder Structure & Workflow**
```
audio_files/
├── [Your 500+ voice notes go here]    # Main processing queue
├── success/                           # ✅ Successfully processed files (auto-moved)
├── test_keep/                         # 🧪 Positive test examples  
└── test_delete/                       # 🗑️  Negative test examples
```

## 🔧 **Efficient API Usage & Caching**

VoiceVault is designed for efficiency:

**✅ Smart Result Caching**: Phase 3 classifications are saved - no need to re-run Claude
**✅ Clean Interfaces**: Each phase has specific input/output files  
**✅ Reusable Results**: Use existing taxonomy and classifications multiple times
**✅ Cost Optimization**: Avoid unnecessary API calls through intelligent caching

```bash
# Reuse existing results (no new Claude calls needed)
python3 src/update_notion_taxonomy.py --pages data.json --classifications existing_results.json

# Only run Phase 3 if you need new classifications
# All other phases use cached/saved results
```

## 📊 What Gets Created in Notion

### Hierarchical Taxonomy Columns
- **Life Area**: Broad life categories (e.g., "Spiritual & Ceremonial", "Business & Career")
- **Topic**: Specific themes (e.g., "Community Building", "Content Creation", "Sacred Practice")
- Both columns support **multiple values** per voice memo

### Traditional Database Properties  
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
├── src/                             # 🚀 CLEAN 4-PHASE PIPELINE
│   ├── get_pages_and_tags.py       # Phase 1: Extract data from Notion
│   ├── classify_tags.py            # Phase 2: Build taxonomy from actual content
│   ├── claude_taxonomy_classifier.py # Phase 3: Classify with Claude AI
│   ├── update_notion_taxonomy.py   # Phase 4: Update Notion with results
│   └── transcriber.py              # Core transcription utility
├── main.py                         # 🎛️ BASIC PROCESSING (Alternative)
├── audio_files/                    # 📁 VOICE MEMO STORAGE
│   ├── [500+ voice notes]          # ← Put your files here
│   ├── success/                    # ← Successfully processed files
│   ├── test_keep/                  # 🧪 Positive test examples
│   └── test_delete/                # 🗑️ Negative test examples
├── config/
│   └── config.py                   # Configuration settings
├── requirements.txt                # Python dependencies
├── database_config.json            # Database configuration
└── processed_files.json            # Processing tracking
```

**🎯 Two approaches: Advanced taxonomy system OR simple bulk processing!**

## 📁 Supported File Formats

- `.m4a` (Apple Voice Memos)
- `.mp3`, `.wav`, `.aac`, `.flac`, `.ogg`
- Automatic format detection and conversion

## 🛠️ Troubleshooting

### Taxonomy System Issues

**1. Classification Results Missing**
```bash
# Check if Phase 3 completed successfully
ls -la *.json  # Look for results.json file

# Re-run only the failed phase
python3 src/claude_taxonomy_classifier.py --pages data.json --taxonomy taxonomy.json --output results.json
```

**2. Notion Update Fails**
```bash
# Verify columns exist and integration has permissions
# Check the update logs for specific API errors
```

**3. Phase Dependencies**
- Phase 2 requires Phase 1 output (data.json)
- Phase 3 requires Phase 1 and 2 outputs (data.json + taxonomy.json)  
- Phase 4 requires Phase 1 and 3 outputs (data.json + results.json)

### Basic Processing Issues

**1. Processing Fails**
```bash
# Check logs for detailed errors
tail -n 50 voice_memo_processor.log

# Test with single file first
python3 main.py --file "test_file.m4a" --dry-run
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

# Start fresh with dry run
python3 main.py --folder your_folder --dry-run
```

## 🎯 Best Practices

### For Taxonomy System
1. **Start with Phase 1**: Always extract current data first
2. **Review Taxonomy**: Check Phase 2 output before proceeding  
3. **Batch Processing**: Phase 3 processes in efficient batches
4. **Reuse Results**: Save classification results for multiple Notion updates

### For Basic Processing
1. **Start Small**: Process 3-5 files with `--dry-run` first
2. **Test Setup**: Use `--max-files 3` for initial real processing
3. **Scale Up**: Use batch processing for larger collections

### For Large Collections (100+ files)
1. **Use Taxonomy System**: More efficient for large-scale organization
2. **Monitor API Costs**: Track Claude usage during classification
3. **Process in Sessions**: Can pause/resume between phases

## 🚀 Ready to Start?

### Recommended: Hierarchical Taxonomy System
```bash
# 1. Extract your voice memo data
python3 src/get_pages_and_tags.py --output my_data.json

# 2. Build custom taxonomy from your content
python3 src/classify_tags.py --input my_data.json --output my_taxonomy.json

# 3. Classify everything with Claude
python3 src/claude_taxonomy_classifier.py --pages my_data.json --taxonomy my_taxonomy.json --output my_results.json

# 4. Update Notion with organized categories
python3 src/update_notion_taxonomy.py --pages my_data.json --classifications my_results.json
```

### Alternative: Basic Processing
```bash
# Quick test
python3 main.py --folder audio_files --dry-run --max-files 3

# Full processing
python3 main.py --folder audio_files --batch-size 5
```

Your voice memo chaos is about to become an organized, searchable knowledge vault! 🎉

## 📚 What's Next?

After processing, you'll be able to:
- **Filter by Life Area** to find broad categories of content
- **Filter by Topic** for specific themes across your life
- **Combine filters** for precise content discovery  
- **Find patterns** and connections you never noticed
- **Transform scattered audio** into organized wisdom

**The days of lost voice memos are over!** 🎙️✨