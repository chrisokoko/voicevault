import logging
import json
import time
import argparse
from typing import Dict, List, Optional, Any
from notion_client import Client
from notion_client.errors import APIResponseError
from config.config import NOTION_TOKEN, NOTION_DATABASE_ID

logger = logging.getLogger(__name__)

class NotionPagesExtractor:
    """
    Stage 1: Extract all pages and existing tags from Notion database.
    
    This class is responsible for:
    1. Connecting to Notion database
    2. Reading all pages 
    3. Extracting all existing tags from all tag columns
    4. Returning clean structured data for further processing
    """
    
    def __init__(self):
        if not NOTION_TOKEN:
            raise ValueError("NOTION_TOKEN not found in configuration")
        if not NOTION_DATABASE_ID:
            raise ValueError("NOTION_DATABASE_ID not found in configuration")
        
        self.client = Client(auth=NOTION_TOKEN)
        self.database_id = NOTION_DATABASE_ID
        
        # Tag columns to extract from
        self.tag_columns = [
            "Primary Themes", 
            "Specific Focus", 
            "Content Types",
            "Emotional Tones", 
            "Key Topics", 
            "Tags"
        ]
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1
        
        # Statistics
        self.pages_read = 0
        self.total_tags_found = 0
        self.unique_tags = set()
    
    def _rate_limit(self):
        """Apply rate limiting between API calls"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def extract_all_pages_and_tags(self) -> Dict[str, Any]:
        """
        Extract all pages and their tags from Notion database.
        
        Returns:
            {
                'pages': [
                    {
                        'page_id': str,
                        'title': str,
                        'all_tags': [str],  # All tags from all columns combined
                        'tags_by_column': {column_name: [tags]}
                    }
                ],
                'statistics': {
                    'total_pages': int,
                    'total_tags': int,
                    'unique_tags': int,
                    'tags_per_column': {column: count}
                },
                'all_unique_tags': [str]  # Complete list of unique tags
            }
        """
        logger.info("🔍 Starting extraction of all pages and tags from Notion...")
        
        all_pages = []
        has_more = True
        next_cursor = None
        
        try:
            while has_more:
                self._rate_limit()
                
                query_params = {
                    "database_id": self.database_id,
                    "page_size": 100
                }
                
                if next_cursor:
                    query_params["start_cursor"] = next_cursor
                
                response = self.client.databases.query(**query_params)
                
                # Process pages in this batch
                for page in response["results"]:
                    page_data = self._extract_page_data(page)
                    if page_data:
                        all_pages.append(page_data)
                
                has_more = response.get("has_more", False)
                next_cursor = response.get("next_cursor")
                
                logger.info(f"   Processed batch. Total pages: {len(all_pages)}")
        
        except APIResponseError as e:
            logger.error(f"Error reading pages from Notion: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error reading pages: {e}")
            raise
        
        # Calculate statistics
        statistics = self._calculate_statistics(all_pages)
        
        result = {
            'pages': all_pages,
            'statistics': statistics,
            'all_unique_tags': sorted(list(self.unique_tags))
        }
        
        logger.info(f"✅ Extraction complete!")
        logger.info(f"   📊 {statistics['total_pages']} pages")
        logger.info(f"   📊 {statistics['total_tags']} total tags")
        logger.info(f"   📊 {statistics['unique_tags']} unique tags")
        
        return result
    
    def _extract_page_data(self, page: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract data from a single Notion page"""
        try:
            page_id = page.get("id", "")
            properties = page.get("properties", {})
            
            # Extract title
            title_prop = properties.get("Title", {})
            title = ""
            if title_prop.get("type") == "title" and title_prop.get("title"):
                title = "".join([t.get("plain_text", "") for t in title_prop["title"]])
            
            # Extract tags from all tag columns
            all_tags = []
            tags_by_column = {}
            
            for column_name in self.tag_columns:
                column_prop = properties.get(column_name, {})
                
                if column_prop.get("type") == "multi_select":
                    tags = [tag["name"] for tag in column_prop.get("multi_select", [])]
                    tags_by_column[column_name] = tags
                    all_tags.extend(tags)
                    
                    # Track unique tags
                    self.unique_tags.update(tags)
                    self.total_tags_found += len(tags)
                else:
                    tags_by_column[column_name] = []
            
            self.pages_read += 1
            
            return {
                "page_id": page_id,
                "title": title,
                "all_tags": all_tags,
                "tags_by_column": tags_by_column
            }
            
        except Exception as e:
            logger.warning(f"Error extracting page data: {e}")
            return None
    
    def _calculate_statistics(self, pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate statistics about the extracted data"""
        tags_per_column = {}
        
        for column_name in self.tag_columns:
            column_tags = set()
            for page in pages:
                column_tags.update(page['tags_by_column'].get(column_name, []))
            tags_per_column[column_name] = len(column_tags)
        
        return {
            'total_pages': len(pages),
            'total_tags': self.total_tags_found,
            'unique_tags': len(self.unique_tags),
            'tags_per_column': tags_per_column
        }
    
    def save_to_file(self, data: Dict[str, Any], filepath: str):
        """Save extracted data to JSON file"""
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Data saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving data to file: {e}")
            raise

def main():
    """Main function to extract pages and tags"""
    parser = argparse.ArgumentParser(description='Extract pages and tags from Notion database')
    parser.add_argument('--output', '-o', required=True, help='Output JSON file path')
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        print("🔍 VoiceVault Page & Tag Extraction")
        print("Extracting all pages and tags from Notion database...")
        
        # Initialize extractor
        extractor = NotionPagesExtractor()
        
        # Extract all data
        data = extractor.extract_all_pages_and_tags()
        
        # Save to specified output file
        extractor.save_to_file(data, args.output)
        
        # Print summary
        stats = data['statistics']
        print(f"\n✅ Extraction Complete!")
        print(f"   📄 Pages extracted: {stats['total_pages']:,}")
        print(f"   🏷️  Total tags: {stats['total_tags']:,}")
        print(f"   🔖 Unique tags: {stats['unique_tags']:,}")
        print(f"\n📊 Tags per column:")
        for column, count in stats['tags_per_column'].items():
            print(f"   • {column}: {count:,} unique tags")
        
        print(f"\n💾 Data saved to {args.output}")
        print(f"   Ready for Phase 2: Tag Classification")
        
    except Exception as e:
        logger.error(f"Error in page extraction: {e}")
        print(f"❌ Extraction failed: {e}")

if __name__ == "__main__":
    main()