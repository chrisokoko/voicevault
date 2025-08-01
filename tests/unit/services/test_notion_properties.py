#!/usr/bin/env python3
"""
Unit tests for Notion properties building - DEBUG the 500 error
Tests the complete properties dictionary that gets sent to Notion API
"""

import sys
import os
from pprint import pprint
import json
from datetime import datetime

# Add project root to path
project_root = os.path.join(os.path.dirname(__file__), '../../..')
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'src'))

def test_notion_properties_building():
    """Test building the complete Notion properties dictionary with verbose output"""
    
    print("=" * 80)
    print("🏗️  TESTING NOTION PROPERTIES BUILDING")
    print("=" * 80)
    
    # Test data mimicking real Claude output
    test_title = "CRM Pipeline Design For Client Management"
    test_claude_tags = {
        'primary_themes': 'Business Systems, Client Management',
        'specific_focus': 'Pipeline Design, Lead Management',
        'content_types': 'Process Planning, Strategic Thinking',
        'emotional_tones': 'Analytical, Methodical',
        'key_topics': 'CRM System, Sales Pipeline, Lead Tracking, Business Process, Client Conversion'
    }
    test_summary = "The speaker is planning the structure of a CRM system, specifically focusing on pipeline organization..."
    test_filename = "30s test - NE Cully Blvd.m4a"
    
    print("🔍 INPUT DATA:")
    print("-" * 30)
    print(f"Title: {test_title}")
    print(f"Filename: {test_filename}")
    print(f"Summary: {test_summary[:50]}...")
    print("Claude Tags:")
    pprint(test_claude_tags)
    print()
    
    # Replicate the property building logic from NotionService.create_page()
    def parse_tags_to_multiselect(tag_string: str):
        if not tag_string:
            return []
        tags = tag_string.replace('[', '').replace(']', '').split(',')
        return [{"name": tag.strip()} for tag in tags if tag.strip()]
    
    print("🔄 PROCESSING TAGS...")
    print("-" * 30)
    
    # Process each tag category
    primary_themes_tags = parse_tags_to_multiselect(test_claude_tags.get('primary_themes', ''))
    specific_focus_tags = parse_tags_to_multiselect(test_claude_tags.get('specific_focus', ''))
    content_types_tags = parse_tags_to_multiselect(test_claude_tags.get('content_types', ''))
    emotional_tones_tags = parse_tags_to_multiselect(test_claude_tags.get('emotional_tones', ''))
    key_topics_tags = parse_tags_to_multiselect(test_claude_tags.get('key_topics', ''))
    
    print(f"Primary Themes: {primary_themes_tags}")
    print(f"Specific Focus: {specific_focus_tags}")
    print(f"Content Types: {content_types_tags}")
    print(f"Emotional Tones: {emotional_tones_tags}")
    print(f"Key Topics: {key_topics_tags}")
    print()
    
    # Combine all tags for the main Tags field
    all_tags = []
    for tag_list in [primary_themes_tags, specific_focus_tags, content_types_tags, emotional_tones_tags, key_topics_tags[:6]]:
        all_tags.extend(tag_list)
    unique_tags = list({tag['name']: tag for tag in all_tags}.values())[:15]
    
    print(f"Combined unique tags ({len(unique_tags)}): {unique_tags}")
    print()
    
    # Build the properties dictionary exactly as NotionService does
    properties = {
        "Title": {
            "title": [
                {
                    "text": {
                        "content": test_title
                    }
                }
            ]
        },
        "Primary Themes": {
            "multi_select": primary_themes_tags
        } if primary_themes_tags else None,
        "Specific Focus": {
            "multi_select": specific_focus_tags
        } if specific_focus_tags else None,
        "Content Types": {
            "multi_select": content_types_tags
        } if content_types_tags else None,
        "Emotional Tones": {
            "multi_select": emotional_tones_tags
        } if emotional_tones_tags else None,
        "Key Topics": {
            "multi_select": key_topics_tags
        } if key_topics_tags else None,
        "Tags": {
            "multi_select": unique_tags[:10]
        },
        "Summary": {
            "rich_text": [
                {
                    "text": {
                        "content": test_summary
                    }
                }
            ]
        },
        "Duration": {
            "rich_text": [
                {
                    "text": {
                        "content": "31s"
                    }
                }
            ]
        },
        "Duration (Seconds)": {
            "number": 31
        },
        "File Created": {
            "date": {
                "start": datetime.now().isoformat()
            }
        },
        "File Size": {
            "rich_text": [
                {
                    "text": {
                        "content": "0.27 MB"
                    }
                }
            ]
        },
        "Audio File": {
            "files": []
        },
        "Audio Content Type": {
            "select": {
                "name": "Speech"
            }
        },
        "Flagged for Deletion": {
            "checkbox": True
        },
        "Deletion Confidence": {
            "select": {
                "name": "High"
            }
        },
        "Deletion Reason": {
            "rich_text": [
                {
                    "text": {
                        "content": "Business process planning content"
                    }
                }
            ]
        }
    }
    
    # Remove None values
    properties = {k: v for k, v in properties.items() if v is not None}
    
    print("🏗️  FINAL PROPERTIES DICTIONARY:")
    print("=" * 50)
    
    # Show each property type and its structure
    for prop_name, prop_data in properties.items():
        prop_type = list(prop_data.keys())[0]  # Get the property type
        print(f"📌 {prop_name} ({prop_type}):")
        
        if prop_type == "multi_select":
            values = prop_data["multi_select"]
            print(f"   Count: {len(values)}")
            print(f"   Values: {[item['name'] for item in values]}")
            
            # Check for potential issues
            for item in values:
                if not isinstance(item, dict):
                    print(f"   ❌ ISSUE: Non-dict item: {item}")
                elif 'name' not in item:
                    print(f"   ❌ ISSUE: Missing 'name' key: {item}")
                elif not isinstance(item['name'], str):
                    print(f"   ❌ ISSUE: Non-string name: {item}")
                elif len(item['name']) > 100:  # Notion has a 100 char limit
                    print(f"   ⚠️  WARNING: Long name ({len(item['name'])} chars): {item['name'][:50]}...")
        else:
            print(f"   Value: {str(prop_data)[:100]}...")
        
        print()
    
    print("📊 PROPERTIES SUMMARY:")
    print("-" * 30)
    print(f"Total properties: {len(properties)}")
    multi_select_props = [k for k, v in properties.items() if 'multi_select' in v]
    print(f"Multi-select properties: {len(multi_select_props)}")
    print(f"Multi-select names: {multi_select_props}")
    
    # Calculate payload size
    json_str = json.dumps(properties)
    print(f"JSON payload size: {len(json_str)} characters")
    
    if len(json_str) > 100000:  # 100KB
        print("⚠️  WARNING: Large payload size!")
    
    print("\n🔍 FULL JSON PAYLOAD:")
    print("=" * 50)
    print(json.dumps(properties, indent=2))
    
    print("\n🎯 POTENTIAL ISSUES TO CHECK:")
    print("=" * 50)
    
    issues_found = []
    
    # Check for common Notion API issues
    for prop_name, prop_data in properties.items():
        if 'multi_select' in prop_data:
            values = prop_data['multi_select']
            if len(values) > 100:  # Notion limit
                issues_found.append(f"Too many {prop_name} values: {len(values)}")
            
            for item in values:
                if len(item.get('name', '')) > 100:
                    issues_found.append(f"Long {prop_name} name: {item['name'][:50]}...")
    
    if issues_found:
        for issue in issues_found:
            print(f"❌ {issue}")
    else:
        print("✅ No obvious format issues detected")
    
    return properties

if __name__ == "__main__":
    test_notion_properties_building()