#!/usr/bin/env python3
"""
Phase 2 Main - Create Classification Buckets

This program analyzes all existing freeform tags from processed voice memos and creates
the master classification taxonomy buckets (life_domains and focus_areas).

This is a one-time analysis that:
1. Retrieves all processed voice memos from Notion
2. Collects all freeform tags across all categories
3. Uses Claude to analyze patterns and create master taxonomy
4. Outputs the final classification system for Phase 3 use

Run this after you have a good collection of processed voice memos from Phase 1.
"""

import os
import sys
import argparse
import logging
import json
from datetime import datetime
from typing import Dict, List, Any

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from claude_service import ClaudeService
from notion_service import NotionService
from utils import parse_comma_separated_tags, sanitize_json_for_logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('phase2_create_classification_buckets.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class Phase2BucketCreator:
    def __init__(self):
        # Initialize services
        self.claude_service = ClaudeService()  # Phase 2 uses default taxonomy for analysis
        from config.config import DATABASE_ID
        if not DATABASE_ID:
            logger.error("DATABASE_ID not configured in config.py. Please set a valid database ID.")
            sys.exit(1)
        
        self.notion_service = NotionService(DATABASE_ID)
        
        # Verify Notion connection
        if not self.notion_service.check_database_exists():
            logger.error("Cannot access Notion database. Check your configuration.")
            sys.exit(1)
        
        logger.info("Successfully connected to Notion database")

    def extract_all_freeform_tags(self) -> List[Dict[str, str]]:
        """Extract all freeform tags from processed voice memos in Notion"""
        logger.info("📥 Retrieving all voice memo pages from Notion...")
        
        # Query all pages from the database
        all_pages = self.notion_service.query_all_pages()
        
        if not all_pages:
            logger.error("No pages found in Notion database")
            return []
        
        logger.info(f"Found {len(all_pages)} voice memo pages")
        
        # Extract freeform tags from each page
        all_freeform_tags = []
        
        for page in all_pages:
            try:
                properties = page.get('properties', {})
                
                # Extract standardized tag categories
                freeform_tags = {}
                
                # Tags (consolidated field)
                tags_field = properties.get('Tags', {}).get('rich_text', [])
                if tags_field and len(tags_field) > 0:
                    freeform_tags['tags'] = tags_field[0].get('text', {}).get('content', '')
                
                # Only add pages that have some freeform tags
                if any(freeform_tags.values()):
                    all_freeform_tags.append(freeform_tags)
                
            except Exception as e:
                logger.warning(f"Error extracting tags from page: {e}")
                continue
        
        logger.info(f"📊 Extracted freeform tags from {len(all_freeform_tags)} pages")
        return all_freeform_tags

    def analyze_tags_and_create_buckets(self, all_freeform_tags: List[Dict[str, str]]) -> Dict[str, List[str]]:
        """Use Claude to analyze all tags and create classification buckets"""
        if not all_freeform_tags:
            logger.error("No freeform tags to analyze")
            return {'life_domains': [], 'focus_areas': []}
        
        logger.info("🤖 Analyzing freeform tags with Claude to create classification buckets...")
        
        # Count total unique tags for reporting
        all_unique_tags = set()
        for tag_set in all_freeform_tags:
            for category, tags in tag_set.items():
                if tags:
                    tag_list = parse_comma_separated_tags(tags)
                    all_unique_tags.update(tag_list)
        
        logger.info(f"📊 Analyzing {len(all_unique_tags)} unique tags across {len(all_freeform_tags)} voice memos")
        
        # Use Claude service to analyze tags
        classification_result = self.claude_service.analyze_all_tags_for_classification(all_freeform_tags)
        
        logger.info("✅ Claude analysis complete")
        logger.info(f"📋 Recommended Life Domains: {len(classification_result['life_domains'])}")
        logger.info(f"📋 Recommended Focus Areas: {len(classification_result['focus_areas'])}")
        
        return classification_result

    def save_classification_taxonomy(self, classification_result: Dict[str, List[str]], output_file: str) -> bool:
        """Save the classification taxonomy to a JSON file"""
        try:
            # Create comprehensive taxonomy structure
            taxonomy_data = {
                'created_at': datetime.now().isoformat(),
                'created_by': 'Phase 2 - Create Classification Buckets',
                'taxonomy_structure': {
                    'life_domains': {},
                    'focus_areas': {}
                },
                'classification_buckets': classification_result,
                'meta': {
                    'total_life_domains': len(classification_result['life_domains']),
                    'total_focus_areas': len(classification_result['focus_areas']),
                    'taxonomy_version': '1.0'
                }
            }
            
            # Build structured taxonomy from Claude's universal taxonomy
            # Add descriptions for each life domain
            for domain in classification_result['life_domains']:
                taxonomy_data['taxonomy_structure']['life_domains'][domain] = {
                    'description': self.claude_service.taxonomy['life_domains'].get(domain, ''),
                    'included': True
                }
            
            # Add focus areas with their parent domains
            for area in classification_result['focus_areas']:
                # Find which life domain this focus area belongs to
                parent_domain = None
                for domain, areas in self.claude_service.taxonomy['focus_areas'].items():
                    if area in areas:
                        parent_domain = domain
                        break
                
                taxonomy_data['taxonomy_structure']['focus_areas'][area] = {
                    'parent_life_domain': parent_domain,
                    'description': f"Focus area under {parent_domain}" if parent_domain else "Custom focus area",
                    'included': True
                }
            
            # Save to file
            with open(output_file, 'w') as f:
                json.dump(taxonomy_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Saved classification taxonomy to: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving classification taxonomy: {e}")
            return False

    def display_taxonomy_summary(self, classification_result: Dict[str, List[str]]):
        """Display a human-readable summary of the created taxonomy"""
        print("\n" + "="*80)
        print("🏗️  PHASE 2 - CLASSIFICATION TAXONOMY CREATED")
        print("="*80)
        
        print(f"\n📊 LIFE DOMAINS ({len(classification_result['life_domains'])} total):")
        for i, domain in enumerate(classification_result['life_domains'], 1):
            description = self.claude_service.taxonomy['life_domains'].get(domain, 'Custom domain')
            print(f"  {i:2d}. {domain}")
            print(f"      {description}")
        
        print(f"\n🎯 FOCUS AREAS ({len(classification_result['focus_areas'])} total):")
        
        # Group focus areas by their parent life domain
        focus_by_domain = {}
        orphaned_areas = []
        
        for area in classification_result['focus_areas']:
            parent_found = False
            for domain, areas in self.claude_service.taxonomy['focus_areas'].items():
                if area in areas:
                    if domain not in focus_by_domain:
                        focus_by_domain[domain] = []
                    focus_by_domain[domain].append(area)
                    parent_found = True
                    break
            
            if not parent_found:
                orphaned_areas.append(area)
        
        # Display focus areas grouped by domain
        for domain in classification_result['life_domains']:
            if domain in focus_by_domain:
                print(f"\n  {domain}:")
                for area in focus_by_domain[domain]:
                    print(f"    • {area}")
        
        # Display any orphaned focus areas
        if orphaned_areas:
            print(f"\n  Custom/Ungrouped Areas:")
            for area in orphaned_areas:
                print(f"    • {area}")
        
        print("\n" + "="*80)
        print("✅ Ready for Phase 3: Assign Bucket Tags")
        print("   Use the saved taxonomy file for batch classification")
        print("="*80)

    def run_analysis(self, output_file: str = None) -> bool:
        """Run the complete Phase 2 analysis"""
        try:
            # Default output filename
            if not output_file:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_file = f"classification_taxonomy_{timestamp}.json"
            
            logger.info("🚀 Starting Phase 2: Create Classification Buckets")
            
            # Step 1: Extract all freeform tags from Notion
            all_freeform_tags = self.extract_all_freeform_tags()
            
            if not all_freeform_tags:
                logger.error("❌ No freeform tags found. Run Phase 1 first to process some voice memos.")
                return False
            
            # Step 2: Analyze tags and create classification buckets
            classification_result = self.analyze_tags_and_create_buckets(all_freeform_tags)
            
            if not classification_result['life_domains'] and not classification_result['focus_areas']:
                logger.error("❌ Failed to create classification taxonomy")
                return False
            
            # Step 3: Save taxonomy to file
            if not self.save_classification_taxonomy(classification_result, output_file):
                logger.error("❌ Failed to save classification taxonomy")
                return False
            
            # Step 4: Display summary
            self.display_taxonomy_summary(classification_result)
            
            logger.info("🎉 Phase 2 complete! Classification taxonomy created successfully.")
            logger.info(f"📁 Next step: Run Phase 3 with the taxonomy file: {output_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error in Phase 2 analysis: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Phase 2: Create classification buckets from freeform tags")
    parser.add_argument(
        "--output",
        help="Output JSON file for classification taxonomy (default: auto-generated filename)"
    )
    parser.add_argument(
        "--min-pages",
        type=int,
        default=20,
        help="Minimum number of processed pages required to run analysis (default: 20)"
    )
    
    args = parser.parse_args()
    
    # Initialize bucket creator
    creator = Phase2BucketCreator()
    
    # Check if we have enough processed pages
    logger.info("🔍 Checking if enough voice memos have been processed...")
    all_pages = creator.notion_service.query_all_pages()
    
    if len(all_pages) < args.min_pages:
        logger.warning(f"⚠️  Found only {len(all_pages)} processed pages. Recommended minimum: {args.min_pages}")
        logger.warning("   Consider processing more voice memos with Phase 1 before running Phase 2")
        
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            logger.info("Exiting. Run Phase 1 to process more voice memos first.")
            sys.exit(0)
    
    # Run the analysis
    success = creator.run_analysis(args.output)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()