#!/usr/bin/env python3
"""
Phase 1 Main - Transcribe and Tag Voice Memos

This is the primary voice memo processing program that:
1. Transcribes audio files using Whisper (with Google fallback)
2. Generates freeform tags using Claude AI
3. Creates formatted transcripts and summaries
4. Uploads processed data to Notion with deletion analysis

This handles the initial processing of new voice memos with generic tagging.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import time

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from audio_service import AudioService
from claude_service import ClaudeService
from notion_service import NotionService
from utils import validate_audio_file, clean_filename, format_duration_human
from config.config import (
    AUDIO_FOLDER, SUPPORTED_FORMATS,
    is_file_processed, mark_file_as_processed, get_processed_file_info, get_processing_stats
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('phase1_transcribe_and_tag.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class Phase1Processor:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        
        # Initialize services
        self.audio_service = AudioService()
        self.claude_service = ClaudeService()  # Phase 1 doesn't need taxonomy file
        self.notion_service = None
        
        # Performance tracking
        self.session_stats = {
            'start_time': datetime.now(),
            'files_processed': 0,
            'files_successful': 0,
            'files_failed': 0,
            'files_skipped': 0,
            'total_processing_time': 0
        }
        
        # Initialize Notion service if not dry run
        if not dry_run:
            try:
                self.notion_service = NotionService()
                if not self.notion_service.check_database_exists():
                    logger.error("Cannot access Notion database. Check your configuration.")
                    sys.exit(1)
                logger.info("Successfully connected to Notion database")
            except Exception as e:
                logger.error(f"Failed to initialize Notion service: {e}")
                sys.exit(1)
        else:
            logger.info("Running in DRY RUN mode - no Notion uploads will be made")

    def find_audio_files(self, folder_path: str) -> List[Path]:
        """Find all supported audio files in the specified folder"""
        folder = Path(folder_path)
        if not folder.exists():
            logger.error(f"Folder does not exist: {folder_path}")
            return []
        
        audio_files = []
        
        # If processing audio_files directory, only get files from root (not subdirectories)
        if folder.name == "audio_files":
            for file in folder.iterdir():
                if file.is_file() and file.suffix.lower() in SUPPORTED_FORMATS:
                    audio_files.append(file)
        else:
            # For other directories, process all files (existing behavior)
            for file in folder.iterdir():
                if file.is_file() and file.suffix.lower() in SUPPORTED_FORMATS:
                    audio_files.append(file)
        
        logger.info(f"Found {len(audio_files)} audio files in {folder_path}")
        return sorted(audio_files)


    def process_file(self, file_path: Path) -> bool:
        """Process a single audio file through Phase 1"""
        file_start_time = time.time()
        logger.info(f"🎵 Processing: {file_path.name}")
        
        # Check if file has already been processed
        if is_file_processed(str(file_path)):
            processed_info = get_processed_file_info(str(file_path))
            logger.info(f"File {file_path.name} already processed on {processed_info['processed_at'][:10]} - skipping")
            if processed_info.get('notion_page_id'):
                logger.info(f"  Notion page: {processed_info['notion_page_id']}")
            self.session_stats['files_skipped'] += 1
            return True
        
        try:
            # Step 1: Validate audio file
            validation = validate_audio_file(str(file_path))
            if not validation["valid"]:
                logger.error(f"Invalid audio file {file_path.name}: {validation['reason']}")
                return False
            
            # Step 2: Extract audio metadata
            logger.info("📊 Extracting audio metadata...")
            metadata = self.audio_service.get_audio_metadata(str(file_path))
            duration_str = format_duration_human(metadata['duration_seconds'])
            logger.info(f"Duration: {duration_str}")
            
            # Step 3: Transcribe the audio
            logger.info("🎙️ Transcribing audio...")
            transcript = self.audio_service.transcribe_audio(str(file_path), use_whisper_first=True)
            
            if not transcript:
                logger.warning(f"Failed to transcribe {file_path.name}")
                return False
            
            logger.info(f"Transcription complete: {len(transcript)} characters")
            
            # Step 4: Comprehensive Claude processing (single API call)
            logger.info("🤖 Processing transcript with Claude (comprehensive analysis)...")
            claude_result = self.claude_service.process_transcript_complete(transcript, file_path.name)
            
            # Extract results
            title = claude_result['title']
            formatted_transcript = claude_result['formatted_transcript']
            claude_tags = claude_result['claude_tags']
            summary = claude_result['summary']
            deletion_analysis = claude_result['deletion_analysis']
            
            logger.info(f"✅ Claude analysis complete:")
            logger.info(f"  📝 Title: {title}")
            logger.info(f"  ✍️ Formatted transcript: {len(formatted_transcript)} characters")
            logger.info(f"  📝 Summary: {len(summary)} characters")
            logger.info(f"  🏷️ Generated {len([v for v in claude_tags.values() if v])} tag categories")
            logger.info(f"  🔍 Deletion analysis: {deletion_analysis['should_delete']} ({deletion_analysis['confidence']}) - {deletion_analysis['reason']}")
            
            if self.dry_run:
                processing_time = time.time() - file_start_time
                self.session_stats['files_successful'] += 1
                self.session_stats['files_processed'] += 1
                self.session_stats['total_processing_time'] += processing_time
                
                logger.info(f"🔥 DRY RUN - Would upload to Notion (processed in {processing_time:.1f}s):")
                logger.info(f"  📝 Title: {title}")
                logger.info(f"  📁 Filename: {file_path.name}")
                logger.info(f"  ⏱️  Duration: {duration_str}")
                logger.info(f"  📋 Summary: {summary[:100]}...")
                logger.info(f"  🏷️  Primary Themes: {claude_tags.get('primary_themes', 'N/A')}")
                logger.info(f"  🎯 Specific Focus: {claude_tags.get('specific_focus', 'N/A')}")
                logger.info(f"  📄 Content Types: {claude_tags.get('content_types', 'N/A')}")
                logger.info(f"  😊 Emotional Tones: {claude_tags.get('emotional_tones', 'N/A')}")
                logger.info(f"  🔑 Key Topics: {claude_tags.get('key_topics', 'N/A')}")
                logger.info(f"  🗑️  Flagged for Deletion: {deletion_analysis['should_delete']} - {deletion_analysis['reason']}")
                return True
            
            # Step 9: Upload to Notion
            logger.info("📤 Uploading to Notion...")
            page_id = self.notion_service.create_page(
                title=title,
                transcript=formatted_transcript,
                claude_tags=claude_tags,
                summary=summary,
                filename=file_path.name,
                audio_file_path=str(file_path),
                audio_duration=metadata['duration_seconds'],
                deletion_analysis=deletion_analysis,
                original_transcript=transcript
            )
            
            if page_id:
                processing_time = time.time() - file_start_time
                self.session_stats['files_successful'] += 1
                self.session_stats['files_processed'] += 1
                self.session_stats['total_processing_time'] += processing_time
                
                logger.info(f"✅ Successfully processed {file_path.name} in {processing_time:.1f}s")
                logger.info(f"📄 Notion page created: {page_id}")
                
                # Mark file as processed
                if mark_file_as_processed(str(file_path), page_id):
                    logger.info(f"✅ Marked {file_path.name} as processed")
                else:
                    logger.warning(f"⚠️ Failed to mark {file_path.name} as processed")
                
                return True
            else:
                self.session_stats['files_failed'] += 1
                self.session_stats['files_processed'] += 1
                logger.error(f"❌ Failed to upload {file_path.name} to Notion")
                # Mark as processed but without page ID (failed upload)
                mark_file_as_processed(str(file_path), None)
                return False
                
        except Exception as e:
            self.session_stats['files_failed'] += 1
            self.session_stats['files_processed'] += 1
            logger.error(f"❌ Error processing {file_path.name}: {e}")
            return False

    def process_folder(self, folder_path: str, batch_size: int = 10, start_from: int = 0, 
                      max_files: Optional[int] = None, batch_delay: float = 2.0) -> None:
        """Process audio files in a folder with batch processing support"""
        logger.info(f"🚀 Starting Phase 1 processing: {folder_path}")
        
        audio_files = self.find_audio_files(folder_path)
        
        if not audio_files:
            logger.info("No audio files found to process")
            return
        
        # Show processing statistics
        stats = get_processing_stats()
        logger.info(f"📊 Processing statistics: {stats['total_processed']} files previously processed "
                   f"({stats['successful_uploads']} successful, {stats['failed_uploads']} failed)")
        
        # Apply start_from and max_files filters
        if start_from > 0:
            audio_files = audio_files[start_from:]
            logger.info(f"Starting from file #{start_from}")
        
        if max_files:
            audio_files = audio_files[:max_files]
            logger.info(f"Limited to processing {max_files} files")
        
        if not audio_files:
            logger.info("No files to process after applying filters")
            return
        
        # Filter out already processed files for counting
        unprocessed_files = [f for f in audio_files if not is_file_processed(str(f))]
        already_processed = len(audio_files) - len(unprocessed_files)
        
        logger.info(f"Found {already_processed} already processed files")
        logger.info(f"Will process {len(unprocessed_files)} new files out of {len(audio_files)} total files")
        logger.info(f"📦 Batch processing: {batch_size} files per batch with {batch_delay}s delay between batches")
        
        successful = 0
        failed = 0
        skipped = 0
        
        # Process files in batches
        for batch_start in range(0, len(audio_files), batch_size):
            batch_end = min(batch_start + batch_size, len(audio_files))
            batch_files = audio_files[batch_start:batch_end]
            batch_num = (batch_start // batch_size) + 1
            total_batches = (len(audio_files) + batch_size - 1) // batch_size
            
            logger.info(f"\n📦 BATCH {batch_num}/{total_batches} (files {batch_start + 1}-{batch_end})")
            
            for i, file_path in enumerate(batch_files):
                file_num = batch_start + i + 1
                logger.info(f"Processing {file_num}/{len(audio_files)}: {file_path.name}")
                
                # Check if file was already processed before calling process_file
                if is_file_processed(str(file_path)):
                    skipped += 1
                    logger.info(f"File {file_path.name} already processed - skipping")
                else:
                    result = self.process_file(file_path)
                    if result:
                        successful += 1
                    else:
                        failed += 1
                    
                    # Add a small delay between files to be respectful to APIs
                    time.sleep(1)
            
            # Show batch completion status
            logger.info(f"✅ Batch {batch_num} complete. Running totals: {successful} successful, {failed} failed, {skipped} skipped")
            
            # Delay between batches (except for the last batch)
            if batch_end < len(audio_files):
                logger.info(f"⏱️ Waiting {batch_delay}s before next batch...")
                time.sleep(batch_delay)
        
        logger.info(f"\n🎉 PHASE 1 PROCESSING COMPLETE")
        logger.info(f"Final results: {successful} successful, {failed} failed, {skipped} skipped")
        
        # Show updated statistics
        final_stats = get_processing_stats()
        logger.info(f"📊 Total files processed across all runs: {final_stats['total_processed']}")
        
        # Generate performance report
        self.print_performance_summary()

    def print_performance_summary(self):
        """Print a human-readable performance summary"""
        session_duration = (datetime.now() - self.session_stats['start_time']).total_seconds()
        
        # Calculate averages
        avg_processing_time = (
            self.session_stats['total_processing_time'] / max(1, self.session_stats['files_processed'])
        )
        files_per_minute = (
            self.session_stats['files_processed'] / max(1, session_duration / 60)
        )
        success_rate = (
            (self.session_stats['files_successful'] / max(1, self.session_stats['files_processed'])) * 100
        )
        
        print("\n" + "="*60)
        print("🚀 PHASE 1 PERFORMANCE SUMMARY")
        print("="*60)
        print(f"📊 Session Duration: {session_duration:.1f}s")
        print(f"📁 Files Processed: {self.session_stats['files_processed']}")
        print(f"✅ Successful: {self.session_stats['files_successful']}")
        print(f"❌ Failed: {self.session_stats['files_failed']}")
        print(f"⏭️  Skipped: {self.session_stats['files_skipped']}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        print(f"⚡ Avg Processing Time: {avg_processing_time:.1f}s per file")
        print(f"🎯 Processing Rate: {files_per_minute:.1f} files/minute")
        
        # API performance
        if self.notion_service:
            api_stats = self.notion_service.get_performance_stats()
            print(f"\n🔌 NOTION API EFFICIENCY:")
            print(f"📞 API Calls Made: {api_stats['api_calls_made']}")
            print(f"💾 Cache Hit Rate: {api_stats['cache_hit_rate_percent']}%")
            print(f"💰 Estimated Savings: ${api_stats['estimated_cost_savings']:.3f}")
            print(f"📦 Cached Items: {api_stats['cached_items']}")
        
        print("="*60)

def main():
    parser = argparse.ArgumentParser(description="Phase 1: Transcribe and tag voice memos")
    parser.add_argument(
        "--folder", 
        default=AUDIO_FOLDER,
        help=f"Folder containing audio files (default: {AUDIO_FOLDER})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process files but don't upload to Notion"
    )
    parser.add_argument(
        "--file",
        help="Process a single file instead of a folder"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of files to process in each batch (default: 10)"
    )
    parser.add_argument(
        "--start-from",
        type=int,
        default=0,
        help="Start processing from file number N (0-indexed, default: 0)"
    )
    parser.add_argument(
        "--max-files",
        type=int,
        help="Maximum number of files to process in this run"
    )
    parser.add_argument(
        "--batch-delay",
        type=float,
        default=2.0,
        help="Delay in seconds between batches (default: 2.0)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.file and not Path(args.file).exists():
        logger.error(f"File does not exist: {args.file}")
        sys.exit(1)
    
    if not args.file and not Path(args.folder).exists():
        logger.error(f"Folder does not exist: {args.folder}")
        sys.exit(1)
    
    # Initialize processor
    processor = Phase1Processor(dry_run=args.dry_run)
    
    if args.file:
        # Process single file
        file_path = Path(args.file)
        if file_path.suffix.lower() not in SUPPORTED_FORMATS:
            logger.error(f"Unsupported file format: {file_path.suffix}")
            sys.exit(1)
        
        success = processor.process_file(file_path)
        processor.print_performance_summary()
        sys.exit(0 if success else 1)
    else:
        # Process folder with batch processing options
        processor.process_folder(
            args.folder,
            batch_size=args.batch_size,
            start_from=args.start_from,
            max_files=args.max_files,
            batch_delay=args.batch_delay
        )

if __name__ == "__main__":
    main()