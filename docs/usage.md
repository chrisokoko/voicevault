# VoiceVault Usage Guide

## Basic Usage

### Process All Files in Default Folder
```bash
python main.py
```

### Process Specific Folder
```bash
python main.py --folder path/to/audio/files
```

### Process Single File
```bash
python main.py --file "path/to/audio.m4a"
```

## Batch Processing Options

### Control Batch Size and Delays
```bash
# Process 5 files at a time with 2 second delays
python main.py --batch-size 5 --batch-delay 2.0

# Process maximum 50 files
python main.py --max-files 50

# Start from file number 25
python main.py --start-from 25
```

### Parallel Processing
```bash
# Run multiple processing threads
for i in {1..10}; do 
    nohup python main.py --batch-size 2 --max-files 20 > thread_$i.log 2>&1 &
done
```

## Dry Run Mode

Test processing without uploading to Notion:
```bash
python main.py --dry-run --max-files 3
```

## Performance Monitoring

### Generate Performance Reports
```bash
python main.py --performance-report my_session.json
```

### View Processing Statistics
Check the logs for detailed performance metrics:
```bash
tail -f logs/voice_memo_processor.log
```

## File Organization

The system automatically organizes files:

1. **Main Processing**: Put files in `audio_files/`
2. **Successful Processing**: Files automatically move to `audio_files/success/`
3. **Test Examples**: 
   - Keep examples in `audio_files/test_keep/`
   - Delete examples in `audio_files/test_delete/`

## Supported Audio Formats

- `.m4a` (Apple Voice Memos)
- `.mp3`
- `.wav`
- `.aac`
- `.flac`
- `.ogg`

## What Gets Created in Notion

### Database Properties
- **Title**: AI-generated specific title
- **Primary Themes**: 1-2 main themes
- **Specific Focus**: Detailed aspects
- **Content Types**: Format types
- **Emotional Tones**: Feeling states
- **Key Topics**: 3-6 specific topics
- **Summary**: AI-generated summary
- **Duration**: Formatted duration
- **File Created**: Original recording date
- **Audio File**: Playable audio file
- **Flagged for Deletion**: Auto-flagged content

### Page Content
- **Formatted Transcript**: Claude-improved transcript
- **Original Transcript**: Raw transcription (in toggle)
- **Claude Analysis**: Detailed AI reasoning (in toggle)
- **Metadata**: File information and processing details

## Troubleshooting

### Check Processing Status
```bash
# Count successfully processed files
ls audio_files/success/ | wc -l

# Check for errors in logs
grep -i error logs/voice_memo_processor.log
```

### Resume Interrupted Processing
The system automatically skips already-processed files, so you can safely restart:
```bash
python main.py --folder audio_files
```

### Clear Processing History
```bash
# WARNING: This will reprocess all files
rm processed_files.json
```

## Performance Tips

1. **Batch Size**: Smaller batches (2-5) for stability, larger (10-20) for speed
2. **Delays**: Increase delays if you hit API rate limits
3. **Parallel Processing**: Use multiple threads for large collections
4. **File Size**: Very large files (>20MB) may take longer to upload
5. **Network**: Stable internet connection recommended for Notion uploads