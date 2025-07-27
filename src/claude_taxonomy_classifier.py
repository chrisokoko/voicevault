import logging
import json
import time
import os
import argparse
from typing import Dict, List, Optional, Any
from anthropic import Anthropic

logger = logging.getLogger(__name__)

class ClaudeTaxonomyClassifier:
    """
    Uses Claude to classify voice memo tags into taxonomy categories.
    
    This approach sends batches of voice memos to Claude with a compressed
    taxonomy and gets back structured classifications using mapped codes.
    """
    
    def __init__(self):
        # Get API key from environment or config
        api_key = (os.getenv('ANTHROPIC_API_KEY') or 
                  os.getenv('CLAUDE_API_KEY') or 
                  getattr(__import__('config.config', fromlist=['CLAUDE_API_KEY']), 'CLAUDE_API_KEY', None))
        
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY or CLAUDE_API_KEY not found in environment or config")
        
        self.client = Anthropic(api_key=api_key)
        
        # Load pages data and taxonomy
        self.pages_data = None
        self.taxonomy_structure = None
        
        # Code mappings for efficient output - will be built when taxonomy is loaded
        self.code_mappings = {}
        
        # Progress tracking
        self.batches_processed = 0
        self.total_classifications = 0
    
    def _build_code_mappings(self) -> Dict[str, Dict[str, str]]:
        """Build code mappings for categories - will be populated dynamically"""
        return {
            "life_areas": {},
            "topics": {}
        }
    
    def _build_reverse_code_mappings(self) -> Dict[str, Dict[str, str]]:
        """Build reverse mappings from codes back to full names"""
        reverse_mappings = {}
        for category_type, mappings in self.code_mappings.items():
            reverse_mappings[category_type] = {code: name for name, code in mappings.items()}
        return reverse_mappings
    
    def load_data(self, pages_file: str, taxonomy_file: str) -> bool:
        """Load pages data and taxonomy structure"""
        try:
            # Load pages data
            with open(pages_file, 'r') as f:
                stage1_data = json.load(f)
            self.pages_data = stage1_data['pages']
            logger.info(f"📥 Loaded {len(self.pages_data)} pages from {pages_file}")
            
            # Load taxonomy structure  
            with open(taxonomy_file, 'r') as f:
                taxonomy_data = json.load(f)
            self.taxonomy_structure = taxonomy_data['taxonomy_structure']
            logger.info(f"📥 Loaded taxonomy structure from {taxonomy_file}")
            
            return True
            
        except FileNotFoundError as e:
            logger.error(f"Required data file not found: {e}")
            return False
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return False
    
    def _build_compressed_taxonomy_prompt(self) -> str:
        """Build compressed taxonomy description for Claude from the loaded taxonomy"""
        if not self.taxonomy_structure:
            raise ValueError("Taxonomy structure not loaded")
        
        life_areas = self.taxonomy_structure.get('life_areas', {})
        topics = self.taxonomy_structure.get('topics', {})
        
        # Build dynamic code mappings
        life_area_codes = {}
        topic_codes = {}
        
        # Generate codes for life areas (LA1, LA2, etc.)
        for i, area in enumerate(sorted(life_areas.keys()), 1):
            life_area_codes[area] = f"LA{i:02d}"
        
        # Generate codes for topics (TP1, TP2, etc.)  
        for i, topic in enumerate(sorted(topics.keys()), 1):
            topic_codes[topic] = f"TP{i:02d}"
        
        # Update code mappings
        self.code_mappings = {
            "life_areas": life_area_codes,
            "topics": topic_codes
        }
        
        prompt = f"""# 2-LEVEL TAXONOMY + CODE MAPPING FOR VOICE MEMO CLASSIFICATION

## Code Map:

**Life Area Codes:**
"""
        for area, code in life_area_codes.items():
            description = life_areas[area].get('description', '')
            prompt += f"- {code} = {area} ({description})\n"
        
        prompt += f"""
**Topic Codes:**
"""
        for topic, code in topic_codes.items():
            description = topics[topic].get('description', '')
            prompt += f"- {code} = {topic} ({description})\n"
        
        prompt += f"""
## Classification Instructions:
- Life Areas are broad life pillars (relationship, health, business, etc.)
- Topics are specific themes that can span multiple life areas
- Each voice memo can have MULTIPLE Life Areas and MULTIPLE Topics
- Assign ALL relevant categories - don't limit to just one
- Base classifications on the memo's title and tags"""
        
        return prompt
    
    def _build_batch_prompt(self, batch_pages: List[Dict[str, Any]], batch_number: int) -> str:
        """Build prompt for a batch of voice memos"""
        taxonomy_prompt = self._build_compressed_taxonomy_prompt()
        
        batch_prompt = f"{taxonomy_prompt}\n\n"
        batch_prompt += f"# VOICE MEMO BATCH {batch_number} CLASSIFICATION\n\n"
        batch_prompt += f"Please classify the following {len(batch_pages)} voice memos based on their titles and tags.\n\n"
        batch_prompt += "For each memo, determine ALL relevant Life Areas and Topics. A memo can belong to multiple categories at each level.\n\n"
        
        # Add voice memos to prompt
        for i, page in enumerate(batch_pages, 1):
            title = page['title'][:100] + "..." if len(page['title']) > 100 else page['title']
            tags = page['all_tags'][:50]  # Limit to first 50 tags to manage size
            if len(page['all_tags']) > 50:
                tags.append(f"... and {len(page['all_tags']) - 50} more tags")
            
            batch_prompt += f"**Memo {i}:**\n"
            batch_prompt += f"Title: \"{title}\"\n"
            batch_prompt += f"Tags: {tags}\n\n"
        
        batch_prompt += """Return JSON with codes only. Use arrays for multiple values:
{
  "1": {"life_area": ["LA01","LA03"], "topic": ["TP05","TP12","TP08"]},
  "2": {"life_area": ["LA03"], "topic": ["TP08","TP15"]},
  ...
}

Important:
- Use the 4-character codes only (LA01, TP05, etc.)
- Include ALL relevant categories (multiple values encouraged)
- A memo can have multiple Life Areas and multiple Topics
- Focus on assigning ALL relevant categories, not just the top one"""
        
        return batch_prompt
    
    def classify_batch_with_claude(self, batch_pages: List[Dict[str, Any]], batch_number: int) -> Dict[str, Any]:
        """Send a batch of voice memos to Claude for classification"""
        prompt = self._build_batch_prompt(batch_pages, batch_number)
        
        try:
            logger.info(f"🤖 Sending batch {batch_number} to Claude ({len(batch_pages)} memos)...")
            
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=8000,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Parse Claude's response
            response_text = message.content[0].text
            
            # Extract JSON from response
            try:
                # Find JSON in the response
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                json_str = response_text[json_start:json_end]
                
                classifications = json.loads(json_str)
                
                logger.info(f"✅ Successfully classified batch {batch_number}")
                return {
                    'success': True,
                    'classifications': classifications,
                    'batch_size': len(batch_pages)
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing Claude's JSON response: {e}")
                logger.error(f"Response text: {response_text[:500]}...")
                return {
                    'success': False,
                    'error': f"JSON parsing error: {e}",
                    'raw_response': response_text
                }
        
        except Exception as e:
            logger.error(f"Error calling Claude API: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def classify_all_pages(self, batch_size: int = 150) -> Dict[str, Any]:
        """Classify all pages using Claude in batches"""
        if not self.pages_data:
            logger.error("No pages data loaded. Run load_data() first.")
            return {'success': False, 'error': 'No data loaded'}
        
        logger.info(f"🚀 Starting Claude classification of {len(self.pages_data)} pages in batches of {batch_size}...")
        
        results = {
            'success': False,
            'total_pages': len(self.pages_data),
            'batches_processed': 0,
            'classifications': {},
            'errors': [],
            'batch_results': []
        }
        
        # Split pages into batches
        batches = []
        for i in range(0, len(self.pages_data), batch_size):
            batch = self.pages_data[i:i + batch_size]
            batches.append(batch)
        
        logger.info(f"📊 Created {len(batches)} batches")
        
        # Process each batch
        for batch_num, batch_pages in enumerate(batches, 1):
            print(f"\n📤 Processing batch {batch_num}/{len(batches)} ({len(batch_pages)} memos)...")
            
            batch_result = self.classify_batch_with_claude(batch_pages, batch_num)
            results['batch_results'].append(batch_result)
            
            if batch_result['success']:
                # Add classifications to overall results
                batch_classifications = batch_result['classifications']
                
                # Convert batch-relative indices to global indices
                global_start_idx = (batch_num - 1) * batch_size
                for local_idx, classification in batch_classifications.items():
                    global_idx = global_start_idx + int(local_idx) - 1  # Convert to 0-based
                    page_id = batch_pages[int(local_idx) - 1]['page_id']
                    results['classifications'][page_id] = classification
                
                results['batches_processed'] += 1
                self.total_classifications += len(batch_classifications)
                
                print(f"   ✅ Batch {batch_num} successful ({len(batch_classifications)} classifications)")
            else:
                error_msg = f"Batch {batch_num} failed: {batch_result.get('error', 'Unknown error')}"
                results['errors'].append(error_msg)
                print(f"   ❌ {error_msg}")
            
            # Small delay between batches
            if batch_num < len(batches):
                time.sleep(1)
        
        # Final results
        results['success'] = results['batches_processed'] > 0
        results['total_classifications'] = self.total_classifications
        
        logger.info(f"🎉 Classification complete!")
        logger.info(f"   📊 {results['batches_processed']}/{len(batches)} batches successful")
        logger.info(f"   📊 {self.total_classifications} total classifications")
        
        return results
    
    def decode_classifications(self, coded_classifications: Dict[str, Any]) -> Dict[str, Any]:
        """Convert coded classifications back to full category names"""
        reverse_mappings = self._build_reverse_code_mappings()
        decoded = {}
        
        for page_id, classification in coded_classifications.items():
            decoded[page_id] = {
                'life_areas': [reverse_mappings['life_areas'].get(code, code) for code in classification.get('life_area', [])],
                'topics': [reverse_mappings['topics'].get(code, code) for code in classification.get('topic', [])]
            }
        
        return decoded
    
    def save_results(self, results: Dict[str, Any], filepath: str):
        """Save classification results to file"""
        
        # Decode classifications for readability
        if 'classifications' in results:
            decoded_classifications = self.decode_classifications(results['classifications'])
            results['decoded_classifications'] = decoded_classifications
        
        try:
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Results saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving results: {e}")
            raise

def main():
    """Main function to classify all voice memos using Claude"""
    parser = argparse.ArgumentParser(description='Classify voice memos using Claude and taxonomy')
    parser.add_argument('--pages', '-p', required=True, help='Input JSON file with pages and tags')
    parser.add_argument('--taxonomy', '-t', required=True, help='Input JSON file with taxonomy structure')
    parser.add_argument('--output', '-o', required=True, help='Output JSON file for classifications')
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        print("🤖 VoiceVault Claude Taxonomy Classification")
        print("Using Claude to classify voice memo tags into taxonomy categories...")
        
        # Initialize classifier
        classifier = ClaudeTaxonomyClassifier()
        
        # Load data
        if not classifier.load_data(args.pages, args.taxonomy):
            print("❌ Failed to load data")
            return
        
        # Classify all pages
        results = classifier.classify_all_pages(batch_size=150)
        
        # Save results
        classifier.save_results(results, args.output)
        
        # Print summary
        if results['success']:
            print(f"\n🎉 Classification Complete!")
            print(f"   📊 Total pages: {results['total_pages']:,}")
            print(f"   ✅ Successful batches: {results['batches_processed']}")
            print(f"   📊 Total classifications: {results['total_classifications']:,}")
            
            if results['errors']:
                print(f"   ⚠️  Errors: {len(results['errors'])}")
                for error in results['errors']:
                    print(f"      • {error}")
            
            print(f"\n💾 Results saved to {args.output}")
        else:
            print(f"\n❌ Classification failed")
            for error in results['errors']:
                print(f"   • {error}")
        
    except Exception as e:
        logger.error(f"Error in Claude classification: {e}")
        print(f"❌ Classification failed: {e}")

if __name__ == "__main__":
    main()