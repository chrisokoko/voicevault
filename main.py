#!/usr/bin/env python3
"""
Voice Memo Processor

This script processes voice memo files by:
1. Reading audio files from a specified folder
2. Transcribing them using Mac's speech recognition (with Google fallback)
3. Generating content-based tags
4. Uploading results to Notion

Usage:
    python main.py [--folder FOLDER] [--dry-run]
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import time
import json
import shutil

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from transcriber import AudioTranscriber
from claude_tagger import ClaudeTagger
from notion_uploader import NotionUploader
from config.config import (
    AUDIO_FOLDER, SUPPORTED_FORMATS, USE_MAC_SPEECH_RECOGNITION,
    is_file_processed, mark_file_as_processed, get_processed_file_info, get_processing_stats
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('voice_memo_processor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class VoiceMemoProcessor:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.transcriber = AudioTranscriber()
        self.claude_tagger = ClaudeTagger()
        self.notion_uploader = None
        
        # Performance tracking
        self.session_stats = {
            'start_time': datetime.now(),
            'files_processed': 0,
            'files_successful': 0,
            'files_failed': 0,
            'files_skipped': 0,
            'total_processing_time': 0,
            'avg_processing_time': 0
        }
        
        if not dry_run:
            try:
                self.notion_uploader = NotionUploader()
                if not self.notion_uploader.check_database_exists():
                    logger.error("Cannot access Notion database. Check your configuration.")
                    sys.exit(1)
            except Exception as e:
                logger.error(f"Failed to initialize Notion uploader: {e}")
                sys.exit(1)
    
    def find_audio_files(self, folder_path: str) -> List[Path]:
        """
        Find all supported audio files in the specified folder
        For audio_files directory, only process files in the root, not in subdirectories
        """
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
    
    def get_audio_duration(self, file_path: Path) -> Optional[float]:
        """
        Get the duration of an audio file in seconds
        """
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(str(file_path))
            return len(audio) / 1000.0  # Convert milliseconds to seconds
        except Exception as e:
            logger.warning(f"Could not get duration for {file_path}: {e}")
            return None
    
    def generate_title(self, filename: str, transcript: str) -> str:
        """
        Generate a meaningful title for the voice memo
        """
        # Use filename as base
        base_title = Path(filename).stem
        
        # Clean up the filename
        title = base_title.replace('_', ' ').replace('-', ' ')
        
        # If transcript is available, try to extract a better title from first sentence
        if transcript:
            sentences = transcript.split('.')
            first_sentence = sentences[0].strip()
            
            # Use first sentence if it's reasonable length and not too long
            if 10 <= len(first_sentence) <= 50:
                title = first_sentence
        
        return title.title()
    
    def process_file(self, file_path: Path) -> bool:
        """
        Process a single audio file
        """
        file_start_time = time.time()
        logger.info(f"Processing: {file_path.name}")
        
        # Check if file has already been processed
        if is_file_processed(str(file_path)):
            processed_info = get_processed_file_info(str(file_path))
            logger.info(f"File {file_path.name} already processed on {processed_info['processed_at'][:10]} - skipping")
            if processed_info.get('notion_page_id'):
                logger.info(f"  Notion page: {processed_info['notion_page_id']}")
            self.session_stats['files_skipped'] += 1
            return True
        
        try:
            # Get audio duration
            duration = self.get_audio_duration(file_path)
            
            # Transcribe the audio
            transcript = self.transcriber.transcribe(
                str(file_path), 
                use_whisper_first=True
            )
            
            if not transcript:
                logger.warning(f"Failed to transcribe {file_path.name}")
                return False
            
            logger.info(f"Transcription length: {len(transcript)} characters")
            
            # Generate tags and summary using Claude
            claude_result = self.claude_tagger.process_transcript(transcript, file_path.name)
            claude_tags = claude_result['claude_tags']
            summary = claude_result['summary']
            deletion_analysis = claude_result['deletion_analysis']
            formatted_transcript = claude_result['formatted_transcript']
            logger.info(f"Claude tags: {claude_tags}")
            logger.info(f"Summary: {summary[:100]}...")
            logger.info(f"Deletion analysis: {deletion_analysis['should_delete']} ({deletion_analysis['confidence']}) - {deletion_analysis['reason']}")
            logger.info(f"Formatted transcript: {len(formatted_transcript)} characters")
            
            # Generate title
            title = self.generate_title(file_path.name, transcript)
            
            if self.dry_run:
                processing_time = time.time() - file_start_time
                self.session_stats['files_successful'] += 1
                self.session_stats['files_processed'] += 1
                self.session_stats['total_processing_time'] += processing_time
                
                logger.info(f"DRY RUN - Would upload to Notion (processed in {processing_time:.1f}s):")
                logger.info(f"  Title: {title}")
                logger.info(f"  Filename: {file_path.name}")
                logger.info(f"  Duration: {duration}s")
                logger.info(f"  Summary: {summary}")
                logger.info(f"  Primary Themes: {claude_tags.get('primary_themes', 'N/A')}")
                logger.info(f"  Specific Focus: {claude_tags.get('specific_focus', 'N/A')}")
                logger.info(f"  Content Types: {claude_tags.get('content_types', 'N/A')}")
                logger.info(f"  Emotional Tones: {claude_tags.get('emotional_tones', 'N/A')}")
                logger.info(f"  Key Topics: {claude_tags.get('key_topics', 'N/A')}")
                logger.info(f"  Flagged for Deletion: {deletion_analysis['should_delete']} - {deletion_analysis['reason']}")
                logger.info(f"  Original Transcript: {transcript[:100]}...")
                logger.info(f"  Formatted Transcript: {formatted_transcript[:100]}...")
                return True
            
            # Upload to Notion
            page_id = self.notion_uploader.create_page(
                title=title,
                transcript=formatted_transcript,  # Use formatted transcript
                original_transcript=transcript,   # Keep original for reference
                claude_tags=claude_tags,
                summary=summary,
                filename=file_path.name,
                audio_file_path=str(file_path),
                audio_duration=duration,
                deletion_analysis=deletion_analysis
            )
            
            if page_id:
                processing_time = time.time() - file_start_time
                self.session_stats['files_successful'] += 1
                self.session_stats['files_processed'] += 1
                self.session_stats['total_processing_time'] += processing_time
                
                logger.info(f"Successfully processed {file_path.name} in {processing_time:.1f}s")
                
                # Mark file as processed
                if mark_file_as_processed(str(file_path), page_id):
                    logger.info(f"Marked {file_path.name} as processed")
                    
                    # Move to success folder if not in dry run mode
                    if not self.dry_run:
                        self.move_to_success_folder(file_path)
                        
                else:
                    logger.warning(f"Failed to mark {file_path.name} as processed")
                return True
            else:
                self.session_stats['files_failed'] += 1
                self.session_stats['files_processed'] += 1
                logger.error(f"Failed to upload {file_path.name} to Notion")
                # Mark as processed but without page ID (failed upload)
                mark_file_as_processed(str(file_path), None)
                return False
                
        except Exception as e:
            self.session_stats['files_failed'] += 1
            self.session_stats['files_processed'] += 1
            logger.error(f"Error processing {file_path.name}: {e}")
            return False
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        session_duration = (datetime.now() - self.session_stats['start_time']).total_seconds()
        
        # Calculate average processing time
        if self.session_stats['files_processed'] > 0:
            self.session_stats['avg_processing_time'] = (
                self.session_stats['total_processing_time'] / self.session_stats['files_processed']
            )
        
        report = {
            'session_summary': {
                'duration_seconds': round(session_duration, 2),
                'files_processed': self.session_stats['files_processed'],
                'files_successful': self.session_stats['files_successful'],
                'files_failed': self.session_stats['files_failed'],
                'files_skipped': self.session_stats['files_skipped'],
                'success_rate_percent': round(
                    (self.session_stats['files_successful'] / max(1, self.session_stats['files_processed'])) * 100, 1
                ),
                'avg_processing_time_seconds': round(self.session_stats['avg_processing_time'], 2),
                'files_per_minute': round(
                    (self.session_stats['files_processed'] / max(1, session_duration / 60)), 2
                )
            }
        }
        
        # Add Notion API performance if available
        if self.notion_uploader:
            api_stats = self.notion_uploader.get_performance_stats()
            report['api_performance'] = api_stats
        
        return report
    
    def print_performance_summary(self):
        """Print a human-readable performance summary"""
        report = self.generate_performance_report()
        session = report['session_summary']
        
        print("\n" + "="*60)
        print("🚀 PROCESSING PERFORMANCE SUMMARY")
        print("="*60)
        print(f"📊 Session Duration: {session['duration_seconds']}s")
        print(f"📁 Files Processed: {session['files_processed']}")
        print(f"✅ Successful: {session['files_successful']}")
        print(f"❌ Failed: {session['files_failed']}")
        print(f"⏭️  Skipped: {session['files_skipped']}")
        print(f"📈 Success Rate: {session['success_rate_percent']}%")
        print(f"⚡ Avg Processing Time: {session['avg_processing_time_seconds']}s per file")
        print(f"🎯 Processing Rate: {session['files_per_minute']} files/minute")
        
        # API performance
        if 'api_performance' in report:
            api = report['api_performance']
            print(f"\n🔌 API EFFICIENCY:")
            print(f"📞 API Calls Made: {api['api_calls_made']}")
            print(f"💾 Cache Hit Rate: {api['cache_hit_rate_percent']}%")
            print(f"💰 Estimated Savings: ${api['estimated_cost_savings']:.3f}")
            print(f"📦 Cached Items: {api['cached_items']}")
        
        print("="*60)
    
    def save_performance_report(self, filename: str = None) -> str:
        """Save detailed performance report to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"performance_report_{timestamp}.json"
        
        report = self.generate_performance_report()
        
        try:
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            logger.info(f"Performance report saved to: {filename}")
            return filename
        except Exception as e:
            logger.error(f"Failed to save performance report: {e}")
            return ""
    
    def move_to_success_folder(self, file_path: Path) -> bool:
        """Move successfully processed file to success folder"""
        try:
            # Only move files from the main audio_files directory (not subdirectories)
            if file_path.parent.name != "audio_files":
                return True  # Don't move test files, just return success
            
            success_folder = file_path.parent / "success"
            success_folder.mkdir(exist_ok=True)
            
            destination = success_folder / file_path.name
            shutil.move(str(file_path), str(destination))
            logger.info(f"Moved {file_path.name} to success folder")
            return True
            
        except Exception as e:
            logger.error(f"Failed to move {file_path.name} to success folder: {e}")
            return False
    
    def process_folder(self, folder_path: str, batch_size: int = 10, start_from: int = 0, 
                      max_files: Optional[int] = None, batch_delay: float = 2.0) -> None:
        """
        Process audio files in a folder with batch processing support
        """
        audio_files = self.find_audio_files(folder_path)
        
        if not audio_files:
            logger.info("No audio files found to process")
            return
        
        # Show processing statistics
        stats = get_processing_stats()
        logger.info(f"Processing statistics: {stats['total_processed']} files previously processed "
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
        logger.info(f"Batch processing: {batch_size} files per batch with {batch_delay}s delay between batches")
        
        successful = 0
        failed = 0
        skipped = 0
        
        # Process files in batches
        for batch_start in range(0, len(audio_files), batch_size):
            batch_end = min(batch_start + batch_size, len(audio_files))
            batch_files = audio_files[batch_start:batch_end]
            batch_num = (batch_start // batch_size) + 1
            total_batches = (len(audio_files) + batch_size - 1) // batch_size
            
            logger.info(f"\n--- BATCH {batch_num}/{total_batches} (files {batch_start + 1}-{batch_end}) ---")
            
            for i, file_path in enumerate(batch_files):
                file_num = batch_start + i + 1
                logger.info(f"Processing {file_num}/{len(audio_files)}: {file_path.name}")
                
                # Check if file was already processed before calling process_file
                if is_file_processed(str(file_path)):
                    skipped += 1
                    processed_info = get_processed_file_info(str(file_path))
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
            logger.info(f"Batch {batch_num} complete. Running totals: {successful} successful, {failed} failed, {skipped} skipped")
            
            # Delay between batches (except for the last batch)
            if batch_end < len(audio_files):
                logger.info(f"Waiting {batch_delay}s before next batch...")
                time.sleep(batch_delay)
        
        logger.info(f"\n=== PROCESSING COMPLETE ===")
        logger.info(f"Final results: {successful} successful, {failed} failed, {skipped} skipped")
        
        # Show updated statistics
        final_stats = get_processing_stats()
        logger.info(f"Total files processed across all runs: {final_stats['total_processed']}")
        
        # Generate and display performance report
        self.print_performance_summary()
        
        # Save detailed performance report
        report_file = self.save_performance_report()
        if report_file:
            logger.info(f"Detailed performance report saved to: {report_file}")

def main():
    parser = argparse.ArgumentParser(description="Process voice memos and upload to Notion")
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
    parser.add_argument(
        "--performance-report",
        help="Save performance report to specified filename"
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
    processor = VoiceMemoProcessor(dry_run=args.dry_run)
    
    if args.file:
        # Process single file
        file_path = Path(args.file)
        if file_path.suffix.lower() not in SUPPORTED_FORMATS:
            logger.error(f"Unsupported file format: {file_path.suffix}")
            sys.exit(1)
        
        success = processor.process_file(file_path)
        
        # Generate performance report even for single files
        processor.print_performance_summary()
        if args.performance_report:
            processor.save_performance_report(args.performance_report)
            
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
        
        # Save custom performance report if specified
        if args.performance_report:
            processor.save_performance_report(args.performance_report)

if __name__ == "__main__":
    main()