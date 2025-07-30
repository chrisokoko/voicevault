#!/usr/bin/env python3
"""
Phase 3 Main - Assign Bucket Tags

This program takes all processed voice memos and assigns them to the classification
buckets (life_domains and focus_areas) created in Phase 2.

This performs batch classification by:
1. Loading the taxonomy created in Phase 2
2. Retrieving all processed voice memos from Notion
3. Sending batches of 150 voice memos to Claude for bucket assignment
4. Updating Notion pages with the assigned life_domain and focus_area tags

Run this after Phase 2 has created the classification taxonomy.
"""

import os
import sys
import argparse
import logging
import json
import time
from datetime import datetime
from typing import Dict, List, Any

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from claude_service import ClaudeService
from notion_service import NotionService
from utils import batch_items, calculate_percentage, sanitize_json_for_logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('phase3_assign_bucket_tags.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class Phase3BucketAssigner:
    def __init__(self, taxonomy_file: str, dry_run: bool = False):
        self.dry_run = dry_run
        self.taxonomy_data = None
        self.available_life_domains = []
        self.available_focus_areas = []
        
        # Initialize services
        self.claude_service = ClaudeService(taxonomy_file=taxonomy_file)
        self.notion_service = NotionService()
        
        # Performance tracking
        self.session_stats = {
            'start_time': datetime.now(),
            'pages_processed': 0,
            'pages_successful': 0,
            'pages_failed': 0,
            'batches_processed': 0,
            'total_batches': 0
        }
        
        # Load taxonomy
        if not self.load_taxonomy(taxonomy_file):
            logger.error("Failed to load taxonomy file")
            sys.exit(1)
        
        # Verify Notion connection
        if not self.notion_service.check_database_exists():
            logger.error("Cannot access Notion database. Check your configuration.")
            sys.exit(1)
        
        logger.info("Successfully connected to Notion database")

    def load_taxonomy(self, taxonomy_file: str) -> bool:
        """Load the classification taxonomy from Phase 2"""
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
            logger.info(f"📅 Taxonomy created: {self.taxonomy_data.get('created_at', 'Unknown')}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading taxonomy file: {e}")
            return False

    def get_pages_for_classification(self) -> List[Dict[str, Any]]:
        """Get all voice memo pages that need bucket classification"""
        logger.info("📥 Retrieving voice memo pages from Notion...")
        
        # Query all pages from the database
        all_pages = self.notion_service.query_all_pages()
        
        if not all_pages:
            logger.error("No pages found in Notion database")
            return []
        
        logger.info(f"Found {len(all_pages)} total pages")
        
        # Convert pages to format needed for Claude classification
        pages_for_classification = []
        
        for page in all_pages:
            try:
                properties = page.get('properties', {})
                
                # Get page title
                title_property = properties.get('Title', {}).get('title', [])
                title = title_property[0]['text']['content'] if title_property else 'Untitled'
                
                # Get freeform tags
                tags = {}
                
                # Primary Themes
                primary_themes = properties.get('Primary Themes', {}).get('multi_select', [])
                if primary_themes:
                    tags['primary_themes'] = ', '.join([tag['name'] for tag in primary_themes])
                
                # Specific Focus
                specific_focus = properties.get('Specific Focus', {}).get('multi_select', [])
                if specific_focus:
                    tags['specific_focus'] = ', '.join([tag['name'] for tag in specific_focus])
                
                # Content Types
                content_types = properties.get('Content Types', {}).get('multi_select', [])
                if content_types:
                    tags['content_types'] = ', '.join([tag['name'] for tag in content_types])
                
                # Emotional Tones
                emotional_tones = properties.get('Emotional Tones', {}).get('multi_select', [])
                if emotional_tones:
                    tags['emotional_tones'] = ', '.join([tag['name'] for tag in emotional_tones])
                
                # Key Topics
                key_topics = properties.get('Key Topics', {}).get('multi_select', [])
                if key_topics:
                    tags['key_topics'] = ', '.join([tag['name'] for tag in key_topics])
                
                # Only include pages that have some tags and don't already have bucket assignments
                life_domain_assigned = properties.get('Life Domain', {}).get('select')
                focus_area_assigned = properties.get('Focus Area', {}).get('select')
                
                has_tags = any(tags.values())
                needs_classification = not (life_domain_assigned and focus_area_assigned)
                
                if has_tags and needs_classification:
                    pages_for_classification.append({
                        'page_id': page['id'],
                        'title': title,
                        'tags': tags
                    })
                
            except Exception as e:
                logger.warning(f"Error processing page: {e}")
                continue
        
        logger.info(f"📊 Found {len(pages_for_classification)} pages needing bucket classification")
        return pages_for_classification

    def classify_batch(self, batch_pages: List[Dict[str, Any]], batch_number: int) -> Dict[str, Any]:
        """Send a batch of pages to Claude for bucket classification"""
        logger.info(f"🤖 Processing batch {batch_number} ({len(batch_pages)} pages)...")
        
        # Use Claude service to classify the batch
        result = self.claude_service.assign_bucket_tags_batch(
            batch_pages, 
            self.available_life_domains,
            self.available_focus_areas,
            batch_number
        )
        
        if result['success']:
            logger.info(f"✅ Batch {batch_number} classified successfully")
        else:
            logger.error(f"❌ Batch {batch_number} failed: {result.get('error', 'Unknown error')}")
        
        return result

    def update_notion_pages(self, batch_pages: List[Dict[str, Any]], classifications: Dict[str, Any]) -> int:
        """Update Notion pages with bucket classifications"""
        successful_updates = 0
        
        for i, page in enumerate(batch_pages):
            try:
                # Get classification for this page (1-indexed in Claude response)
                page_classification = classifications.get(str(i + 1))
                
                if not page_classification:
                    logger.warning(f"No classification found for page: {page['title']}")
                    continue
                
                life_domain = page_classification.get('life_domain')
                focus_area = page_classification.get('focus_area')
                
                if not life_domain or not focus_area:
                    logger.warning(f"Incomplete classification for page: {page['title']}")
                    continue
                
                if self.dry_run:
                    logger.info(f"🔥 DRY RUN - Would update page: {page['title']}")
                    logger.info(f"   Life Domain: {life_domain}")
                    logger.info(f"   Focus Area: {focus_area}")
                    successful_updates += 1
                    continue
                
                # Update the page in Notion
                success = self.notion_service.update_page_bucket_tags(
                    page['page_id'], 
                    life_domain, 
                    focus_area
                )
                
                if success:
                    logger.info(f"✅ Updated: {page['title']} → {life_domain} / {focus_area}")
                    successful_updates += 1
                else:
                    logger.error(f"❌ Failed to update: {page['title']}")
                
                # Small delay between updates
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error updating page {page['title']}: {e}")
                continue
        
        return successful_updates

    def process_all_pages(self, batch_size: int = 150, start_batch: int = 1, max_batches: int = None) -> None:
        """Process all pages needing bucket classification"""
        logger.info("🚀 Starting Phase 3: Assign Bucket Tags")
        
        # Get pages that need classification
        pages_to_classify = self.get_pages_for_classification()
        
        if not pages_to_classify:
            logger.info("✅ No pages need bucket classification. All done!")
            return
        
        # Create batches
        batches = batch_items(pages_to_classify, batch_size)
        self.session_stats['total_batches'] = len(batches)
        
        logger.info(f"📦 Processing {len(pages_to_classify)} pages in {len(batches)} batches of {batch_size}")
        
        # Apply start_batch and max_batches filters
        if start_batch > 1:
            batches = batches[start_batch - 1:]
            logger.info(f"Starting from batch #{start_batch}")
        
        if max_batches:
            batches = batches[:max_batches]
            logger.info(f"Limited to processing {max_batches} batches")
        
        if not batches:
            logger.info("No batches to process after applying filters")
            return
        
        logger.info(f"🎯 Will process {len(batches)} batches")
        
        # Process each batch
        for batch_num, batch_pages in enumerate(batches, start_batch):
            logger.info(f"\n📦 BATCH {batch_num}/{self.session_stats['total_batches']} ({len(batch_pages)} pages)")
            
            # Step 1: Classify batch with Claude
            classification_result = self.classify_batch(batch_pages, batch_num)
            
            if not classification_result['success']:
                logger.error(f"❌ Skipping batch {batch_num} due to classification failure")
                self.session_stats['pages_failed'] += len(batch_pages)
                continue
            
            # Step 2: Update Notion pages
            logger.info(f"📝 Updating Notion pages for batch {batch_num}...")
            successful_updates = self.update_notion_pages(
                batch_pages, 
                classification_result['classifications']
            )
            
            # Update statistics
            self.session_stats['batches_processed'] += 1
            self.session_stats['pages_processed'] += len(batch_pages)
            self.session_stats['pages_successful'] += successful_updates
            self.session_stats['pages_failed'] += len(batch_pages) - successful_updates
            
            logger.info(f"✅ Batch {batch_num} complete: {successful_updates}/{len(batch_pages)} pages updated")
            
            # Delay between batches
            if batch_num < len(batches) + start_batch - 1:
                logger.info("⏱️  Waiting 2s before next batch...")
                time.sleep(2)
        
        # Final summary
        self.print_final_summary()

    def print_final_summary(self):
        """Print final processing summary"""
        session_duration = (datetime.now() - self.session_stats['start_time']).total_seconds()
        success_rate = calculate_percentage(
            self.session_stats['pages_successful'], 
            self.session_stats['pages_processed']
        )
        
        print("\n" + "="*80)
        print("🎉 PHASE 3 - BUCKET ASSIGNMENT COMPLETE")
        print("="*80)
        print(f"📊 Session Duration: {session_duration:.1f}s")
        print(f"📦 Batches Processed: {self.session_stats['batches_processed']}/{self.session_stats['total_batches']}")
        print(f"📄 Pages Processed: {self.session_stats['pages_processed']}")
        print(f"✅ Successful Updates: {self.session_stats['pages_successful']}")
        print(f"❌ Failed Updates: {self.session_stats['pages_failed']}")
        print(f"📈 Success Rate: {success_rate}%")
        
        if self.session_stats['pages_processed'] > 0:
            avg_time = session_duration / self.session_stats['pages_processed']
            print(f"⚡ Average Time: {avg_time:.1f}s per page")
        
        # API performance
        api_stats = self.notion_service.get_performance_stats()
        print(f"\n🔌 NOTION API EFFICIENCY:")
        print(f"📞 API Calls Made: {api_stats['api_calls_made']}")
        print(f"💾 Cache Hit Rate: {api_stats['cache_hit_rate_percent']}%")
        
        print("\n" + "="*80)
        print("✅ All voice memos have been assigned to classification buckets!")
        print("   Your voice memo collection is now fully organized.")
        print("="*80)

def main():
    parser = argparse.ArgumentParser(description="Phase 3: Assign bucket tags to voice memos")
    parser.add_argument(
        "--taxonomy",
        required=True,
        help="JSON file with classification taxonomy from Phase 2"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process classifications but don't update Notion pages"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=150,
        help="Number of pages to process per Claude API call (default: 150)"
    )
    parser.add_argument(
        "--start-batch",
        type=int,
        default=1,
        help="Start processing from batch number N (1-indexed, default: 1)"
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        help="Maximum number of batches to process in this run"
    )
    
    args = parser.parse_args()
    
    # Validate taxonomy file exists
    if not os.path.exists(args.taxonomy):
        logger.error(f"Taxonomy file not found: {args.taxonomy}")
        sys.exit(1)
    
    # Initialize bucket assigner
    assigner = Phase3BucketAssigner(args.taxonomy, dry_run=args.dry_run)
    
    # Run the bucket assignment
    try:
        assigner.process_all_pages(
            batch_size=args.batch_size,
            start_batch=args.start_batch,
            max_batches=args.max_batches
        )
    except KeyboardInterrupt:
        logger.info("\n⏹️  Processing interrupted by user")
        assigner.print_final_summary()
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()