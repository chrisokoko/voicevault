import logging
import json
import os
import argparse
from collections import defaultdict
from typing import Dict, List, Set, Optional, Any
from anthropic import Anthropic

logger = logging.getLogger(__name__)

class TagClassifier:
    """
    Stage 2: Classify existing tags into 2-level taxonomy using Claude.
    
    This class is responsible for:
    1. Taking all existing tags from Stage 1
    2. Using Claude to create Life Areas (~10-15) and Topics (~50) from the actual tags
    3. Building tag-to-taxonomy mapping
    4. Saving complete taxonomy structure
    """
    
    def __init__(self):
        # Get Claude API key
        api_key = (os.getenv('ANTHROPIC_API_KEY') or 
                  os.getenv('CLAUDE_API_KEY') or 
                  getattr(__import__('config.config', fromlist=['CLAUDE_API_KEY']), 'CLAUDE_API_KEY', None))
        
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY or CLAUDE_API_KEY not found in environment or config")
        
        self.client = Anthropic(api_key=api_key)
        
        # Will be built from Claude's analysis
        self.taxonomy_structure = None
        
        # Statistics tracking
        self.classification_stats = {
            'total_tags': 0,
            'classified_tags': 0,
            'unclassified_tags': 0,
            'classification_rate': 0.0
        }
    
    def build_taxonomy_from_tags(self, tags_list: List[str]) -> Dict[str, Any]:
        """Use Claude to analyze tags and build 2-level taxonomy"""
        logger.info(f"🤖 Using Claude to build taxonomy from {len(tags_list)} actual tags...")
        
        # Create prompt for Claude to analyze tags and build taxonomy
        prompt = f"""You are analyzing {len(tags_list)} tags from voice memos to create a 2-level taxonomy.

TAGS TO ANALYZE:
{tags_list}

TASK: Create a 2-level taxonomy structure with:
1. **Life Areas** (10-15 broad life categories)
2. **Topics** (40-50 specific topics that could span multiple life areas)

REQUIREMENTS:
- Life Areas should be major pillars of human experience (like Partnerships, Health, Creative, etc.)
- Topics should be specific things someone would want to filter for
- Each tag should map to ONE Life Area and ONE Topic
- Base everything on the actual tags provided, not theoretical frameworks

Return JSON in this exact format:
{{
  "life_areas": {{
    "Partnerships": {{
      "description": "Romantic relationships, marriage, dating"
    }},
    "Friendships": {{
      "description": "Friend relationships, social connections"
    }},
    "Business": {{
      "description": "Work, career, entrepreneurship"
    }}
  }},
  "topics": {{
    "Romantic Relationships": {{
      "description": "Dating, love, romance, marriage"
    }},
    "Business Strategy": {{
      "description": "Planning, strategy, business decisions"
    }},
    "Financial Planning": {{
      "description": "Money management, budgeting, investments"
    }}
  }}
}}

Analyze the provided tags and create this taxonomy structure."""

        try:
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
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            json_str = response_text[json_start:json_end]
            
            taxonomy_data = json.loads(json_str)
            
            logger.info("✅ Successfully built taxonomy from tags using Claude")
            logger.info(f"   📊 {len(taxonomy_data.get('life_areas', {}))} Life Areas")
            logger.info(f"   📊 {len(taxonomy_data.get('topics', {}))} Topics")
            
            return taxonomy_data
            
        except Exception as e:
            logger.error(f"Error building taxonomy with Claude: {e}")
            raise
    
    def classify_all_tags(self, tags_list: List[str]) -> Dict[str, Any]:
        """
        Build taxonomy from tags and create classification mapping.
        
        Args:
            tags_list: List of all unique tags to classify
            
        Returns:
            {
                'life_areas': {life_area: {description, tags}},
                'topics': {topic: {description, tags}},
                'tag_mappings': {tag: {life_area, topic}},
                'statistics': {total_tags, classified_tags, etc.}
            }
        """
        logger.info(f"🏷️  Starting taxonomy building from {len(tags_list)} tags...")
        
        # Use Claude to build taxonomy from actual tags
        taxonomy_data = self.build_taxonomy_from_tags(tags_list)
        
        # Calculate statistics
        total_tags = len(tags_list)
        life_areas_count = len(taxonomy_data.get('life_areas', {}))
        topics_count = len(taxonomy_data.get('topics', {}))
        
        self.classification_stats = {
            'total_tags': total_tags,
            'life_areas_created': life_areas_count,
            'topics_created': topics_count
        }
        
        # Add statistics to taxonomy data
        taxonomy_data['statistics'] = self.classification_stats
        
        logger.info(f"✅ Taxonomy building complete!")
        logger.info(f"   📊 {total_tags} tags analyzed")
        logger.info(f"   📊 {life_areas_count} Life Areas created")
        logger.info(f"   📊 {topics_count} Topics created")
        
        return taxonomy_data
    
    def save_taxonomy(self, taxonomy_data: Dict[str, Any], filepath: str):
        """Save the taxonomy to JSON file"""
        # Format for compatibility with existing system
        formatted_taxonomy = {
            "taxonomy_structure": taxonomy_data,
            "classification_stats": taxonomy_data.get('statistics', {})
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(formatted_taxonomy, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Taxonomy saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving taxonomy: {e}")
            raise

def main():
    """Main function to build taxonomy from actual tags"""
    parser = argparse.ArgumentParser(description='Build taxonomy from extracted tags')
    parser.add_argument('--input', '-i', required=True, help='Input JSON file with pages and tags')
    parser.add_argument('--output', '-o', required=True, help='Output JSON file for taxonomy')
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        print("🏷️  VoiceVault Taxonomy Builder (Data-Driven)")
        print("Building taxonomy from your actual voice memo tags...")
        
        # Load tags from input file
        try:
            with open(args.input, 'r') as f:
                stage1_data = json.load(f)
            tags_list = stage1_data['all_unique_tags']
            print(f"📥 Loaded {len(tags_list)} unique tags from {args.input}")
        except FileNotFoundError:
            print(f"❌ Input file {args.input} not found. Please run Phase 1 first.")
            return
        except KeyError:
            print(f"❌ Input file {args.input} missing 'all_unique_tags' field.")
            return
        
        # Initialize classifier
        classifier = TagClassifier()
        
        # Build taxonomy from actual tags
        taxonomy_data = classifier.classify_all_tags(tags_list)
        
        # Save taxonomy to output file
        classifier.save_taxonomy(taxonomy_data, args.output)
        
        # Print summary
        stats = taxonomy_data['statistics']
        print(f"\n✅ Taxonomy Building Complete!")
        print(f"   🏷️  Total tags analyzed: {stats['total_tags']:,}")
        print(f"   🏛️  Life Areas created: {stats['life_areas_created']}")
        print(f"   🎯 Topics created: {stats['topics_created']}")
        
        print(f"\n📊 New Taxonomy Structure:")
        life_areas = taxonomy_data.get('life_areas', {})
        topics = taxonomy_data.get('topics', {})
        
        print(f"   🏛️  Life Areas ({len(life_areas)}):")
        for area in sorted(life_areas.keys()):
            description = life_areas[area].get('description', '')
            print(f"      • {area}: {description}")
        
        print(f"   🎯 Topics ({len(topics)}):")
        for i, topic in enumerate(sorted(topics.keys())[:10]):
            description = topics[topic].get('description', '')
            print(f"      • {topic}: {description}")
        if len(topics) > 10:
            print(f"      ... and {len(topics) - 10} more topics")
        
        print(f"\n💾 Data saved to {args.output}")
        print(f"   Ready for Phase 3: Implementation & Update")
        
    except Exception as e:
        logger.error(f"Error in taxonomy building: {e}")
        print(f"❌ Taxonomy building failed: {e}")

if __name__ == "__main__":
    main()