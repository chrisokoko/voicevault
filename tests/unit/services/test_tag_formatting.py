#!/usr/bin/env python3
"""
Unit tests for tag formatting - DEBUG the 500 error
Tests the parse_tags_to_multiselect function in isolation with verbose output
"""

import sys
import os
from pprint import pprint
import json

# Add project root to path
project_root = os.path.join(os.path.dirname(__file__), '../../..')
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'src'))

def test_parse_tags_to_multiselect():
    """Test the tag parsing function with various inputs - VERBOSE OUTPUT"""
    
    print("=" * 80)
    print("🔍 TESTING TAG FORMATTING FUNCTION")
    print("=" * 80)
    
    # Import the function we need to test
    from notion_service import NotionService
    notion = NotionService()
    
    # Test cases with various formats
    test_cases = [
        {
            "name": "Simple comma-separated",
            "input": "Business Systems, Client Management",
            "expected_count": 2
        },
        {
            "name": "With brackets (Claude format)",
            "input": "[Strategic Planning, Business Development]",
            "expected_count": 2
        },
        {
            "name": "Mixed with extra spaces",
            "input": " Business Systems , Client Management , CRM Design ",
            "expected_count": 3
        },
        {
            "name": "Single item",
            "input": "Strategic Planning",
            "expected_count": 1
        },
        {
            "name": "Empty string",
            "input": "",
            "expected_count": 0
        },
        {
            "name": "Special characters",
            "input": "AI & Machine Learning, Data-Driven Insights",
            "expected_count": 2
        },
        {
            "name": "Long tag names",
            "input": "Very Long Tag Name That Might Cause Issues, Another Extremely Long Tag That Could Be Problematic",
            "expected_count": 2
        },
        {
            "name": "Real Claude output example",
            "input": "Strategic Planning, Business Development",
            "expected_count": 2
        }
    ]
    
    # Define the parse function (extracted from NotionService)
    def parse_tags_to_multiselect(tag_string: str):
        if not tag_string:
            return []
        # Parse tags, clean brackets if present, and format for Notion
        tags = tag_string.replace('[', '').replace(']', '').split(',')
        return [{"name": tag.strip()} for tag in tags if tag.strip()]
    
    print(f"\n📋 Testing {len(test_cases)} different tag formats...\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"🧪 Test Case {i}: {test_case['name']}")
        print(f"   Input: '{test_case['input']}'")
        
        try:
            result = parse_tags_to_multiselect(test_case['input'])
            
            print(f"   Output: {result}")
            print(f"   Count: {len(result)} (expected: {test_case['expected_count']})")
            
            # Validate structure
            if result:
                for tag in result:
                    if not isinstance(tag, dict) or 'name' not in tag:
                        print(f"   ❌ MALFORMED: {tag}")
                        break
                else:
                    print(f"   ✅ Structure: Valid")
            else:
                print(f"   ✅ Structure: Empty (OK)")
            
            # Check count
            if len(result) == test_case['expected_count']:
                print(f"   ✅ Count: Correct")
            else:
                print(f"   ❌ Count: Expected {test_case['expected_count']}, got {len(result)}")
            
            # Show JSON representation
            json_str = json.dumps(result, indent=2)
            print(f"   JSON: {json_str}")
            
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
        
        print("-" * 50)
    
    print("\n🔍 TESTING WITH REAL CLAUDE OUTPUT DATA...")
    print("=" * 50)
    
    # Test with actual Claude output data
    real_claude_tags = {
        'primary_themes': 'Strategic Planning, Business Development',
        'specific_focus': 'Startup Strategy, Document Creation',
        'content_types': 'Task Direction, Project Planning',
        'emotional_tones': 'Professional, Directive',
        'key_topics': 'Content Strategy, Partnership Development, Community Engagement, Media Planning, Success Metrics, Strategic Documentation'
    }
    
    print("Real Claude tags received:")
    pprint(real_claude_tags)
    print()
    
    processed_tags = {}
    for category, tag_string in real_claude_tags.items():
        result = parse_tags_to_multiselect(tag_string)
        processed_tags[category] = result
        
        print(f"📂 {category}:")
        print(f"   Raw: '{tag_string}'")
        print(f"   Processed: {result}")
        print(f"   Count: {len(result)}")
        print()
    
    print("🎯 FINAL PROCESSED TAGS STRUCTURE:")
    print("=" * 50)
    pprint(processed_tags)
    
    # Test if this matches Notion's expected format
    print("\n🔍 NOTION MULTI-SELECT FORMAT VALIDATION:")
    print("=" * 50)
    
    sample_notion_property = {
        "Primary Themes": {
            "multi_select": processed_tags['primary_themes']
        }
    }
    
    print("Sample Notion property format:")
    print(json.dumps(sample_notion_property, indent=2))
    
    return processed_tags

if __name__ == "__main__":
    test_parse_tags_to_multiselect()