#!/usr/bin/env python3
"""
Ongoing Main - Process New Voice Memo

This is the ongoing processing program for new voice memos after the initial
taxonomy setup is complete. It combines Phase 1 processing with immediate
bucket assignment using the existing classification taxonomy.

This program:
1. Transcribes and generates freeform tags (Phase 1 processing)
2. Immediately assigns bucket tags using existing taxonomy (Phase 3 logic)
3. Creates a complete Notion page with both freeform and bucket classifications

Use this for processing new voice memos after Phases 1-3 have been completed
and your taxonomy is established.
"""

import os
import sys
import argparse
import logging
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import time

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from audio_service import AudioService
from claude_service import ClaudeService
from notion_service import NotionService
from audio_classifier import YAMNetAudioClassifier
from utils import validate_audio_file, clean_filename, format_duration_human
from config.config import (
    AUDIO_FOLDER, SUPPORTED_FORMATS,
    is_file_processed, mark_file_as_processed, get_processed_file_info
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ongoing_process_new_voice_memo.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class OngoingVoiceMemoProcessor:
    def __init__(self, taxonomy_file: str = None, dry_run: bool = False):
        self.dry_run = dry_run
        self.taxonomy_data = None
        self.available_life_domains = []
        self.available_focus_areas = []
        
        # Initialize services
        self.audio_service = AudioService()
        self.claude_service = ClaudeService(taxonomy_file=taxonomy_file)
        self.notion_service = None
        self.audio_classifier = YAMNetAudioClassifier()
        
        # Performance tracking
        self.session_stats = {
            'start_time': datetime.now(),
            'files_processed': 0,
            'files_successful': 0,
            'files_failed': 0,
            'files_skipped': 0,
            'total_processing_time': 0
        }
        
        # Load taxonomy if provided
        if taxonomy_file:
            if not self.load_taxonomy(taxonomy_file):
                logger.warning("Failed to load taxonomy file - will process without bucket assignment")
        else:
            logger.info("No taxonomy file provided - will process without bucket assignment")
        
        # Initialize Notion service if not dry run
        if not dry_run:
            try:
                from config.config import DATABASE_ID
                if not DATABASE_ID:
                    logger.error("DATABASE_ID not configured in config.py. Please set a valid database ID.")
                    sys.exit(1)
                
                self.notion_service = NotionService(DATABASE_ID)
                if not self.notion_service.check_database_exists():
                    logger.error("Cannot access Notion database. Check DATABASE_ID in config.py.")
                    sys.exit(1)
                logger.info(f"Successfully connected to Notion database: {DATABASE_ID}")
            except Exception as e:
                logger.error(f"Failed to initialize Notion service: {e}")
                sys.exit(1)
        else:
            logger.info("Running in DRY RUN mode - no Notion uploads will be made")

    def load_taxonomy(self, taxonomy_file: str) -> bool:
        """Load the classification taxonomy for bucket assignment"""
        try:
            if not os.path.exists(taxonomy_file):
                logger.error(f"Taxonomy file not found: {taxonomy_file}")
                return False
            
            with open(taxonomy_file, 'r') as f:
                self.taxonomy_data = json.load(f)
            
            # Extract available domains and areas
            classification_buckets = self.taxonomy_data.get('classification_buckets', {})
            self.available_life_domains = classification_buckets.get('life_domains', [])
            self.available_focus_areas = classification_buckets.get('focus_areas', [])
            
            logger.info(f"📥 Loaded taxonomy: {len(self.available_life_domains)} life domains, {len(self.available_focus_areas)} focus areas")
            return True
            
        except Exception as e:
            logger.error(f"Error loading taxonomy file: {e}")
            return False

    def assign_bucket_tags(self, title: str, claude_tags: Dict[str, str]) -> Dict[str, str]:
        """Assign bucket tags to a single voice memo"""
        if not self.taxonomy_data:
            return {'life_domain': None, 'focus_area': None}
        
        try:
            # Create a single-item batch for Claude processing
            batch_pages = [{
                'title': title,
                'tags': claude_tags
            }]
            
            # Use Claude service to assign bucket tags
            result = self.claude_service.assign_bucket_tags_batch(
                batch_pages,
                self.available_life_domains,
                self.available_focus_areas,
                batch_number=1
            )
            
            if result['success'] and '1' in result['classifications']:
                classification = result['classifications']['1']
                return {
                    'life_domains': classification.get('life_domains', []),
                    'focus_areas': classification.get('focus_areas', [])
                }
            else:
                logger.warning("Failed to assign bucket tags")
                return {'life_domains': [], 'focus_areas': []}
                
        except Exception as e:
            logger.error(f"Error assigning bucket tags: {e}")
            return {'life_domains': [], 'focus_areas': []}


    def process_file(self, file_path: Path) -> bool:
        """Process a single audio file with complete pipeline"""
        file_start_time = time.time()
        logger.info(f"🎵 Processing new voice memo: {file_path.name}")
        
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
            
            # Step 3: Classify audio content type
            logger.info("🎵 Classifying audio content type...")
            try:
                audio_classification = self.audio_classifier.classify_audio(str(file_path))
                content_type = audio_classification['primary_class']
                classification_confidence = audio_classification['confidence']
                logger.info(f"Audio classified as: {content_type} (confidence: {classification_confidence:.3f})")
            except Exception as e:
                logger.warning(f"Audio classification failed: {e}")
                # Fallback
                audio_classification = {
                    'primary_class': 'Unknown',
                    'confidence': 0.0,
                    'top_yamnet_predictions': []
                }
                content_type = 'Unknown'
            
            # Step 4: Transcribe the audio
            logger.info("🎙️ Transcribing audio...")
            transcript = self.audio_service.transcribe_audio(str(file_path), use_whisper_first=True)
            
            if not transcript:
                logger.warning(f"Failed to transcribe {file_path.name}")
                return False
            
            logger.info(f"Transcription complete: {len(transcript)} characters")
            
            # Step 5: Comprehensive Claude processing with audio type context
            logger.info("🤖 Processing transcript with Claude (comprehensive analysis)...")
            claude_result = self.claude_service.process_transcript_complete(
                transcript, 
                file_path.name, 
                audio_type=content_type,
                audio_classification=audio_classification
            )
            
            # Extract results
            title = claude_result['title']
            formatted_transcript = claude_result['formatted_transcript']
            claude_tags = claude_result['claude_tags']
            summary = claude_result['summary']
            deletion_analysis = claude_result['deletion_analysis']
            
            logger.info(f"✅ Claude analysis complete:")
            logger.info(f"  📝 Title: {title}")
            logger.info(f"  🏷️ Generated {len([v for v in claude_tags.values() if v])} tag categories")
            logger.info(f"  🔍 Deletion analysis: {deletion_analysis['should_delete']} ({deletion_analysis['confidence']})")
            
            # Step 9: Assign bucket tags (if taxonomy available)
            bucket_assignment = {'life_domains': [], 'focus_areas': []}
            if self.taxonomy_data:
                logger.info("🏷️ Assigning bucket tags...")
                bucket_assignment = self.assign_bucket_tags(title, claude_tags)
                if bucket_assignment['life_domains'] or bucket_assignment['focus_areas']:
                    life_domains_str = ", ".join(bucket_assignment['life_domains']) if bucket_assignment['life_domains'] else "None"
                    focus_areas_str = ", ".join(bucket_assignment['focus_areas']) if bucket_assignment['focus_areas'] else "None"
                    logger.info(f"Assigned: {life_domains_str} / {focus_areas_str}")
                else:
                    logger.warning("Could not assign bucket tags")
            
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
                logger.info(f"  🏷️  Tags: {claude_tags.get('tags', 'N/A')}")
                if bucket_assignment['life_domains']:
                    logger.info(f"  🏛️  Life Domains: {', '.join(bucket_assignment['life_domains'])}")
                if bucket_assignment['focus_areas']:
                    logger.info(f"  🎯 Focus Areas: {', '.join(bucket_assignment['focus_areas'])}")
                logger.info(f"  🗑️  Flagged for Deletion: {deletion_analysis['should_delete']} - {deletion_analysis['reason']}")
                return True
            
            # Step 10: Create comprehensive Notion page
            logger.info("📤 Creating comprehensive Notion page...")
            page_id = self.notion_service.create_page(
                title=title,
                transcript=formatted_transcript,
                claude_tags=claude_tags,
                summary=summary,
                filename=file_path.name,
                audio_file_path=str(file_path),
                audio_duration=metadata['duration_seconds'],
                deletion_analysis=deletion_analysis,
                original_transcript=transcript,
                content_type=content_type
            )
            
            if page_id:
                # Step 11: Add bucket tags if available
                if bucket_assignment['life_domains'] or bucket_assignment['focus_areas']:
                    logger.info("🏷️ Adding bucket tags to page...")
                    bucket_success = self.notion_service.update_page_bucket_tags_multiple(
                        page_id,
                        bucket_assignment['life_domains'],
                        bucket_assignment['focus_areas']
                    )
                    if bucket_success:
                        logger.info("✅ Bucket tags added successfully")
                    else:
                        logger.warning("⚠️ Failed to add bucket tags")
                
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
                logger.error(f"❌ Failed to create Notion page for {file_path.name}")
                mark_file_as_processed(str(file_path), None)
                return False
                
        except Exception as e:
            self.session_stats['files_failed'] += 1
            self.session_stats['files_processed'] += 1
            logger.error(f"❌ Error processing {file_path.name}: {e}")
            return False

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
            # For other directories, process all files
            for file in folder.iterdir():
                if file.is_file() and file.suffix.lower() in SUPPORTED_FORMATS:
                    audio_files.append(file)
        
        logger.info(f"Found {len(audio_files)} audio files in {folder_path}")
        return sorted(audio_files)

    def process_folder(self, folder_path: str, max_files: Optional[int] = None) -> None:
        """Process audio files in a folder"""
        logger.info(f"🚀 Starting ongoing voice memo processing: {folder_path}")
        
        audio_files = self.find_audio_files(folder_path)
        
        if not audio_files:
            logger.info("No audio files found to process")
            return
        
        # Apply max_files filter
        if max_files:
            audio_files = audio_files[:max_files]
            logger.info(f"Limited to processing {max_files} files")
        
        # Filter out already processed files for counting
        unprocessed_files = [f for f in audio_files if not is_file_processed(str(f))]
        already_processed = len(audio_files) - len(unprocessed_files)
        
        logger.info(f"Found {already_processed} already processed files")
        logger.info(f"Will process {len(unprocessed_files)} new files")
        
        successful = 0
        failed = 0
        skipped = 0
        
        # Process files one by one
        for i, file_path in enumerate(audio_files, 1):
            logger.info(f"\n🎵 Processing {i}/{len(audio_files)}: {file_path.name}")
            
            if is_file_processed(str(file_path)):
                skipped += 1
                logger.info(f"File {file_path.name} already processed - skipping")
            else:
                result = self.process_file(file_path)
                if result:
                    successful += 1
                else:
                    failed += 1
                
                # Small delay between files
                time.sleep(1)
        
        logger.info(f"\n🎉 ONGOING PROCESSING COMPLETE")
        logger.info(f"Final results: {successful} successful, {failed} failed, {skipped} skipped")
        
        # Generate performance report
        self.print_performance_summary()

    def print_performance_summary(self):
        """Print a human-readable performance summary"""
        session_duration = (datetime.now() - self.session_stats['start_time']).total_seconds()
        
        if self.session_stats['files_processed'] > 0:
            avg_processing_time = self.session_stats['total_processing_time'] / self.session_stats['files_processed']
            files_per_minute = self.session_stats['files_processed'] / max(1, session_duration / 60)
            success_rate = (self.session_stats['files_successful'] / self.session_stats['files_processed']) * 100
        else:
            avg_processing_time = 0
            files_per_minute = 0
            success_rate = 0
        
        print("\n" + "="*60)
        print("🚀 ONGOING PROCESSING SUMMARY")
        print("="*60)
        print(f"📊 Session Duration: {session_duration:.1f}s")
        print(f"📁 Files Processed: {self.session_stats['files_processed']}")
        print(f"✅ Successful: {self.session_stats['files_successful']}")
        print(f"❌ Failed: {self.session_stats['files_failed']}")
        print(f"⏭️  Skipped: {self.session_stats['files_skipped']}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        print(f"⚡ Avg Processing Time: {avg_processing_time:.1f}s per file")
        print(f"🎯 Processing Rate: {files_per_minute:.1f} files/minute")
        
        # Show taxonomy status
        if self.taxonomy_data:
            print(f"🏷️ Bucket Classification: Enabled ({len(self.available_life_domains)} domains, {len(self.available_focus_areas)} areas)")
        else:
            print(f"🏷️ Bucket Classification: Disabled (no taxonomy file)")
        
        # API performance
        if self.notion_service:
            api_stats = self.notion_service.get_performance_stats()
            print(f"\n🔌 NOTION API EFFICIENCY:")
            print(f"📞 API Calls Made: {api_stats['api_calls_made']}")
            print(f"💾 Cache Hit Rate: {api_stats['cache_hit_rate_percent']}%")
        
        print("="*60)

def main():
    parser = argparse.ArgumentParser(description="Ongoing: Process new voice memos with complete pipeline")
    parser.add_argument(
        "--folder", 
        default=AUDIO_FOLDER,
        help=f"Folder containing audio files (default: {AUDIO_FOLDER})"
    )
    parser.add_argument(
        "--taxonomy",
        help="JSON file with classification taxonomy for bucket assignment"
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
        "--max-files",
        type=int,
        help="Maximum number of files to process in this run"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.file and not Path(args.file).exists():
        logger.error(f"File does not exist: {args.file}")
        sys.exit(1)
    
    if not args.file and not Path(args.folder).exists():
        logger.error(f"Folder does not exist: {args.folder}")
        sys.exit(1)
    
    if args.taxonomy and not os.path.exists(args.taxonomy):
        logger.error(f"Taxonomy file not found: {args.taxonomy}")
        sys.exit(1)
    
    # Initialize processor
    processor = OngoingVoiceMemoProcessor(
        taxonomy_file=args.taxonomy, 
        dry_run=args.dry_run
    )
    
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
        # Process folder
        processor.process_folder(args.folder, max_files=args.max_files)

if __name__ == "__main__":
    main()