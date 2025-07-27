import logging
import json
import time
import argparse
from typing import Dict, List, Optional, Any
from notion_client import Client
from notion_client.errors import APIResponseError
from config.config import NOTION_TOKEN, NOTION_DATABASE_ID

logger = logging.getLogger(__name__)

class NotionTaxonomyUpdater:
    """
    Phase 4: Update Notion database with Claude's taxonomy classifications.
    
    This class is responsible for:
    1. Loading Claude's classification results from Phase 3
    2. Creating/updating taxonomy columns in Notion (Life Areas, Topics)
    3. Updating all pages with their classifications
    4. Providing detailed progress reporting
    """
    
    def __init__(self):
        if not NOTION_TOKEN:
            raise ValueError("NOTION_TOKEN not found in configuration")
        if not NOTION_DATABASE_ID:
            raise ValueError("NOTION_DATABASE_ID not found in configuration")
        
        self.client = Client(auth=NOTION_TOKEN)
        self.database_id = NOTION_DATABASE_ID
        
        # Will be loaded from input files
        self.classifications = None
        self.pages_data = None
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1
        
        # Progress tracking
        self.pages_processed = 0
        self.pages_updated = 0
        self.columns_created = 0
        self.update_errors = []
    
    def _rate_limit(self):
        """Apply rate limiting between API calls"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def load_data(self, pages_file: str, classifications_file: str) -> bool:
        """Load pages data and classification results"""
        try:
            # Load pages data
            with open(pages_file, 'r') as f:
                stage1_data = json.load(f)
            self.pages_data = {page['page_id']: page for page in stage1_data['pages']}
            logger.info(f"📥 Loaded {len(self.pages_data)} pages from {pages_file}")
            
            # Load classification results
            with open(classifications_file, 'r') as f:
                results_data = json.load(f)
            
            # Extract decoded classifications
            if 'decoded_classifications' in results_data:
                self.classifications = results_data['decoded_classifications']
            else:
                logger.error("No 'decoded_classifications' found in classification results")
                return False
            
            logger.info(f"📥 Loaded {len(self.classifications)} classifications from {classifications_file}")
            
            return True
            
        except FileNotFoundError as e:
            logger.error(f"Required data file not found: {e}")
            return False
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return False
    
    def create_taxonomy_columns(self) -> bool:
        """Create the new taxonomy columns in Notion database"""
        logger.info("🏗️  Creating taxonomy columns in Notion database...")
        
        try:
            # Get current database schema
            self._rate_limit()
            database = self.client.databases.retrieve(database_id=self.database_id)
            current_properties = database.get('properties', {})
            
            # Define taxonomy columns for 2-level taxonomy
            taxonomy_columns = ["Life Area", "Topic"]
            existing_columns = []
            
            # Check which columns already exist
            for col_name in taxonomy_columns:
                if col_name in current_properties:
                    existing_columns.append(col_name)
                    logger.info(f"✅ Column already exists: {col_name}")
            
            if len(existing_columns) == 2:
                logger.info("✅ All taxonomy columns already exist")
                return True
            
            # Create the columns that don't exist
            columns_to_create = [col for col in taxonomy_columns if col not in current_properties]
            
            for col_name in columns_to_create:
                logger.info(f"🔨 Creating column: {col_name}")
                
                # Define column as multi_select type (multiple values allowed)
                new_property = {
                    col_name: {
                        "multi_select": {
                            "options": []  # Options will be populated as we add values
                        }
                    }
                }
                
                # Create the column
                self._rate_limit()
                self.client.databases.update(
                    database_id=self.database_id,
                    properties=new_property
                )
                
                self.columns_created += 1
                logger.info(f"✅ Successfully created column: {col_name}")
            
            logger.info(f"✅ Taxonomy columns ready ({self.columns_created} created)")
            return True
                
        except APIResponseError as e:
            if "413" in str(e) or "payload too large" in str(e).lower():
                logger.error("❌ Database schema too large to add columns automatically")
                logger.error("Please manually create these columns in Notion:")
                logger.error("  • Life Area (Multi-select type)")
                logger.error("  • Topic (Multi-select type)")
                return False
            else:
                logger.error(f"Error creating taxonomy columns: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error creating columns: {e}")
            return False
    
    def update_page_with_classification(self, page_id: str, classification: Dict[str, List[str]], title: str) -> bool:
        """Update a single page with Claude's classification"""
        try:
            # Build properties update for taxonomy columns using multi_select
            properties_update = {}
            
            # Life Areas (multiple values)
            if classification.get('life_areas'):
                properties_update['Life Area'] = {
                    'multi_select': [
                        {'name': area} for area in classification['life_areas']
                    ]
                }
            
            # Topics (multiple values)
            if classification.get('topics'):
                properties_update['Topic'] = {
                    'multi_select': [
                        {'name': topic} for topic in classification['topics']
                    ]
                }
            
            # Only update if we have at least one classification
            if properties_update:
                self._rate_limit()
                
                response = self.client.pages.update(
                    page_id=page_id,
                    properties=properties_update
                )
                
                self.pages_updated += 1
                return True
            else:
                logger.debug(f"No classification for page: {title}")
                return False
                
        except APIResponseError as e:
            error_msg = f"Error updating page {page_id} ({title[:50]}...): {e}"
            logger.error(error_msg)
            self.update_errors.append(error_msg)
            return False
        except Exception as e:
            error_msg = f"Unexpected error updating page {page_id} ({title[:50]}...): {e}"
            logger.error(error_msg)
            self.update_errors.append(error_msg)
            return False
    
    def update_all_pages(self) -> Dict[str, Any]:
        """Update all pages with Claude classifications"""
        logger.info("🔄 Starting update of all pages in Notion...")
        
        results = {
            'success': False,
            'data_loaded': False,
            'columns_created': self.columns_created,
            'pages_processed': 0,
            'pages_updated': 0,
            'pages_with_classifications': 0,
            'errors': [],
            'update_details': []
        }
        
        try:
            # Create taxonomy columns if needed
            if not self.create_taxonomy_columns():
                results['errors'].append("Failed to create taxonomy columns")
                return results
            
            results['columns_created'] = self.columns_created
            results['data_loaded'] = True
            
            print(f"📋 Updating {len(self.classifications)} pages with classifications...")
            
            # Update each page that has classifications
            for page_id, classification in self.classifications.items():
                if page_id in self.pages_data:
                    page_info = self.pages_data[page_id]
                    title = page_info['title']
                    
                    # Show progress
                    if self.pages_processed % 50 == 0:
                        print(f"\n📄 Page {self.pages_processed + 1}: {title[:60]}...")
                        print(f"   Life Areas: {classification.get('life_areas', [])}")
                        print(f"   Topics: {classification.get('topics', [])}")
                    
                    # Update in Notion
                    update_success = self.update_page_with_classification(page_id, classification, title)
                    
                    update_detail = {
                        'page_id': page_id,
                        'title': title,
                        'classification': classification,
                        'update_success': update_success
                    }
                    results['update_details'].append(update_detail)
                    
                    if update_success and (classification.get('life_areas') or classification.get('topics')):
                        results['pages_with_classifications'] += 1
                        if self.pages_processed % 50 == 0:
                            print(f"   ✅ Updated successfully")
                    elif self.pages_processed % 50 == 0:
                        print(f"   ❌ Update failed or no classification")
                    
                    self.pages_processed += 1
                else:
                    logger.warning(f"Page ID {page_id} not found in pages data")
            
            # Final results
            results['pages_processed'] = self.pages_processed
            results['pages_updated'] = self.pages_updated
            results['errors'] = self.update_errors
            results['success'] = self.pages_updated > 0
            
            logger.info(f"✅ Update complete: {self.pages_updated}/{self.pages_processed} pages updated")
            
        except Exception as e:
            logger.error(f"Error in page update: {e}")
            results['errors'].append(str(e))
        
        return results
    
    def print_update_summary(self, results: Dict[str, Any]):
        """Print a summary of the update results"""
        print("\n" + "="*80)
        print("🔄 NOTION TAXONOMY UPDATE RESULTS")
        print("="*80)
        
        if results['success']:
            print("✅ UPDATE SUCCESSFUL!")
        else:
            print("❌ UPDATE FAILED")
        
        print(f"\n📊 UPDATE STATISTICS:")
        print(f"   • Data loaded: {'✅' if results['data_loaded'] else '❌'}")
        print(f"   • New columns created: {results['columns_created']}")
        print(f"   • Pages processed: {results['pages_processed']:,}")
        print(f"   • Pages updated: {results['pages_updated']:,}")
        print(f"   • Pages with classifications: {results['pages_with_classifications']:,}")
        
        if results['pages_processed'] > 0:
            update_rate = (results['pages_updated'] / results['pages_processed']) * 100
            classification_rate = (results['pages_with_classifications'] / results['pages_processed']) * 100
            print(f"   • Update success rate: {update_rate:.1f}%")
            print(f"   • Classification coverage: {classification_rate:.1f}%")
        
        if results['errors']:
            print(f"\n🚨 ERRORS ({len(results['errors'])}):") 
            for error in results['errors'][:5]:  # Show first 5 errors
                print(f"   • {error}")
            if len(results['errors']) > 5:
                print(f"   ... and {len(results['errors']) - 5} more errors")
        
        print(f"\n💡 NEXT STEPS:")
        print(f"   • Open your Notion database to see the updated taxonomy columns")
        print(f"   • Filter by 'Life Area' to find broad categories (e.g., Business & Career)")
        print(f"   • Filter by 'Topic' to find specific themes (e.g., Content Creation)")
        print(f"   • Use both filters together for precise content discovery")
        print(f"   • The taxonomy enables finding 20+ related memos instead of 1-2 exact matches!")
        
        print("\n" + "="*80)

def main():
    """Main function to update Notion with taxonomy classifications"""
    parser = argparse.ArgumentParser(description='Update Notion database with taxonomy classifications')
    parser.add_argument('--pages', '-p', required=True, help='Input JSON file with pages data')
    parser.add_argument('--classifications', '-c', required=True, help='Input JSON file with Claude classifications')
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        print("🔄 VoiceVault Notion Taxonomy Update (Phase 4)")
        print("Updating Notion database with Claude's taxonomy classifications...")
        
        # Initialize updater
        updater = NotionTaxonomyUpdater()
        
        # Load data
        if not updater.load_data(args.pages, args.classifications):
            print("❌ Failed to load data")
            return
        
        # Update all pages
        results = updater.update_all_pages()
        
        # Print summary
        updater.print_update_summary(results)
        
        if results['success']:
            print(f"\n🎉 Notion update complete! Check your database for the new taxonomy columns.")
        else:
            print(f"\n❌ Notion update failed. Check errors above.")
        
    except Exception as e:
        logger.error(f"Error in Notion update: {e}")
        print(f"❌ Notion update failed: {e}")

if __name__ == "__main__":
    main()