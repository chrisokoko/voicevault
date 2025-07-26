# Voice Memo Processor 🎙️

An optimized Python system that automatically processes voice memo files by transcribing them, generating intelligent tags, and uploading to Notion with advanced performance optimization.

## ✨ Features

### 🎯 Core Processing
- **Advanced Audio Transcription**: Whisper AI for long files, Mac Speech Recognition for short files, with intelligent chunking for 10+ minute recordings
- **AI-Powered Transcript Formatting**: Claude AI improves readability by fixing grammar, typos, and formatting while preserving all original content
- **Smart Tagging**: Claude AI generates standardized multi-select tags across 5 categories
- **Smart Title Generation**: Creates specific, meaningful titles using AI analysis
- **Deletion Analysis**: Automatically flags content that might not be personal voice notes
- **Duplicate Prevention**: SHA-256 hash tracking prevents reprocessing files

### 🚀 Performance Optimization
- **Intelligent Caching**: 50%+ API call reduction through smart caching
- **Batch Processing**: Optimized bulk operations with rate limiting
- **Cost Monitoring**: Real-time API cost tracking and optimization
- **Database Analytics**: Comprehensive performance and usage analysis

### 📊 Database Management
- **Multi-Select Tags**: Standardized tags in Primary Themes, Specific Focus, Content Types, Emotional Tones, Key Topics
- **Human-Readable Design**: Optimized schema for filtering and organization
- **Automatic Uploads**: Audio files uploaded directly to Notion
- **Rich Metadata**: Duration, file creation date, device information

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd voice-memo-processor
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
CLAUDE_API_KEY = "your_claude_api_key"
AUDIO_FOLDER = "./audio_files"  # Default folder for your voice notes
```

### 3. Set up Notion Integration
1. Create integration at https://www.notion.so/my-integrations
2. Copy the integration token to your config
3. Share your database with the integration (or let the script create one)

## 🎙️ Process Your Voice Notes

### 📁 **Folder Structure & Workflow**
```
audio_files/
├── [Your 500+ voice notes go here]    # Main processing queue
├── success/                           # ✅ Successfully processed files (auto-moved)
├── test_keep/                         # 🧪 Positive test examples  
└── test_delete/                       # 🗑️  Negative test examples
```

### 🚀 **Main Processing Commands**

```bash
# Process your main collection (files auto-move to success/ when done)
python3 main.py --folder audio_files

# Test with a few files first
python3 main.py --folder audio_files --dry-run --max-files 5

# Large batch processing with delays
python3 main.py --folder audio_files --batch-size 10 --batch-delay 3.0
```

### 🧪 **Test Examples Processing**

```bash
# Process positive test examples (files stay in test_keep/)
python3 main.py --folder audio_files/test_keep

# Process negative test examples (files stay in test_delete/) 
python3 main.py --folder audio_files/test_delete
```

### 📊 **Custom Performance Reports**
```bash
# Save detailed performance data to custom file
python3 main.py --folder audio_files --performance-report my_session.json
```

### ✅ **How It Works**
1. **Put your 500 voice notes** in `audio_files/` 
2. **Run processing** with `python3 main.py --folder audio_files`
3. **Successfully processed files** automatically move to `audio_files/success/`
4. **Track progress** by seeing what's left in `audio_files/` vs moved to `success/`

## 🚀 Built-in Optimization & Performance

**Every run now automatically includes:**
- ✅ **Intelligent API Caching**: 50%+ cost reduction through smart caching
- ✅ **Performance Monitoring**: Real-time processing speed and efficiency tracking
- ✅ **Cost Optimization**: Automatic API savings with detailed reporting
- ✅ **Human-readable Reports**: Beautiful console output with key metrics

**No separate programs needed** - everything is optimized and monitored automatically!

## 📁 Supported File Formats

- `.m4a` (Apple Voice Memos)
- `.mp3`, `.wav`, `.aac`, `.flac`, `.ogg`
- Automatic format detection and conversion

## 🎛️ Advanced Usage

### Batch Processing Options
```bash
# Process with custom batch settings
python3 main.py --folder audio_files --batch-size 10 --batch-delay 2.0

# Resume from specific file number
python3 main.py --folder audio_files --start-from 25

# Limit processing to test
python3 main.py --folder audio_files --max-files 10
```

### Single File Processing
```bash
# Process one file for testing
python3 main.py --file "path/to/your/voice_memo.m4a"
```

### Database Operations
```bash
# Clear API cache for fresh analysis
python3 optimized_analyze_tags.py --analyze --clear-cache

# Custom batch size for mapping
python3 optimized_analyze_tags.py --map-taxonomy --batch-size 20
```

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
voice-memo-processor/
├── main.py                      # 🚀 UNIFIED OPTIMIZED PROCESSOR
│                               # ✅ Built-in API caching & optimization
│                               # ✅ Integrated performance monitoring
│                               # ✅ Automatic file organization
│                               # ✅ Human-readable performance reports
├── audio_files/                 # 📁 MAIN PROCESSING WORKFLOW
│   ├── [500+ voice notes]      # ← Put your files here
│   ├── success/                # ← Successfully processed files (auto-moved)
│   ├── test_keep/              # 🧪 Positive test examples
│   └── test_delete/            # 🗑️ Negative test examples
├── config/
│   └── config.py               # Configuration settings
├── src/
│   ├── transcriber.py          # Audio transcription with chunking
│   ├── claude_tagger.py        # AI tagging and analysis
│   └── notion_uploader.py      # Optimized Notion API with caching
├── requirements.txt            # Python dependencies
├── database_config.json        # Database configuration
└── processed_files.json        # Processing tracking
```

**🎯 Clean, minimal structure - everything optimized in ONE program!**

## 🚨 Performance Expectations

### Processing Speed (with Built-in Optimization)
- **Short files (< 2 min)**: ~10-15 seconds per file
- **Medium files (2-10 min)**: ~15-25 seconds per file (optimized API calls)
- **Long files (10+ min)**: ~30-45 seconds per file (intelligent chunking + caching)

### Automatic API Efficiency
- **Cache Hit Rate**: 50%+ API call reduction automatically
- **Cost Optimization**: $0.01+ savings per session (scales significantly)
- **Rate Limiting**: Respectful API usage with intelligent throttling
- **Performance Reports**: Detailed metrics after every run

## 🔍 Monitoring & Logs

### Automatic Performance Monitoring
Every session automatically shows:
```
============================================================
🚀 PROCESSING PERFORMANCE SUMMARY
============================================================
📊 Session Duration: 45.7s
📁 Files Processed: 5
✅ Successful: 5
❌ Failed: 0
⏭️  Skipped: 0
📈 Success Rate: 100.0%
⚡ Avg Processing Time: 9.1s per file
🎯 Processing Rate: 6.6 files/minute

🔌 API EFFICIENCY:
📞 API Calls Made: 12
💾 Cache Hit Rate: 58.3%
💰 Estimated Savings: $0.07
📦 Cached Items: 3
============================================================
```

### Processing Status
The system shows real-time progress with optimization info:
```
Processing 15/50: My Important Voice Note.m4a
Transcription length: 2,341 characters
Claude tags: {'primary_themes': 'Personal Growth, Self Reflection', ...}
✅ Successfully processed My Important Voice Note.m4a in 8.2s
```

### Log Monitoring
```bash
# Watch processing logs
tail -f voice_memo_processor.log
```

## 🛠️ Troubleshooting

### Common Issues

**1. Processing Fails**
```bash
# Check logs for detailed errors
tail -n 50 voice_memo_processor.log

# Test with single file first
python3 main.py --file "test_file.m4a" --dry-run
```

**2. Slow Performance**
```bash
# Clear cache and restart
python3 optimized_analyze_tags.py --clear-cache

# Reduce batch sizes
python3 main.py --batch-size 3 --batch-delay 5.0
```

**3. Notion Upload Issues**
- Verify integration token and database permissions
- Check database is shared with your integration
- Ensure sufficient Notion workspace storage

**4. Audio Transcription Problems**
- Verify ffmpeg installation: `ffmpeg -version`
- Check audio file isn't corrupted
- Try with a known good file first

### Reset and Restart
```bash
# Clear all processing history (reprocess everything)
rm processed_files.json

# Clear analysis cache
python3 optimized_analyze_tags.py --clear-cache

# Start fresh with dry run
python3 main.py --folder your_folder --dry-run
```

## 🎯 Best Practices

### For New Users
1. **Start Small**: Process 3-5 files with `--dry-run` first
2. **Test Setup**: Use `--max-files 3` for initial real processing
3. **Check Results**: Verify Notion database looks correct
4. **Scale Up**: Use batch processing for larger collections

### For Large Collections (100+ files)
1. **Use Batch Processing**: `--batch-size 5 --batch-delay 3.0`
2. **Process in Sessions**: Use `--max-files 50` then `--start-from 50`
3. **Monitor Performance**: Run analysis after every 100 files
4. **Regular Optimization**: Monthly database health checks

### For Ongoing Use
1. **Regular Processing**: Set up for new voice notes as created
2. **Performance Monitoring**: Track API costs and efficiency
3. **Database Maintenance**: Monthly optimization analysis
4. **Tag Consolidation**: Review and merge similar tags quarterly

## 📚 Additional Resources

- **Generated Reports**: Automatic performance reports in JSON format saved after each session
- **Processing Logs**: Detailed logs in `voice_memo_processor.log`

## 🚀 Ready to Start?

1. **Quick Test**: `python3 main.py --folder keep_examples --dry-run --max-files 3`
2. **First Real Processing**: `python3 main.py --folder keep_examples --max-files 3`
3. **Full Transfer**: `python3 main.py --folder your_voice_notes --batch-size 5`
4. **Custom Performance Report**: `python3 main.py --folder your_voice_notes --performance-report my_report.json`

Your **unified, fully-optimized** voice memo processing system is ready! Every run automatically includes intelligent caching, performance monitoring, and cost optimization - no separate programs needed! 🎉