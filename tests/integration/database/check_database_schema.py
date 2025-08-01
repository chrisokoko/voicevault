#!/usr/bin/env python3
"""
Check the Notion database schema to see what properties exist
"""

import sys
import os
import json

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from notion_service import NotionService

def check_database_properties():
    """Check what properties exist in the database"""
    
    notion = NotionService()
    
    try:
        # Get database info
        database_info = notion._make_api_call(
            "get_database",
            database_id=notion.database_id,
            use_cache=False
        )
        
        properties = database_info.get('properties', {})
        
        print("📊 DATABASE PROPERTIES:")
        print("=" * 50)
        
        for prop_name, prop_config in properties.items():
            prop_type = prop_config.get('type', 'unknown')
            print(f"• {prop_name}: {prop_type}")
            
            if prop_type == 'multi_select':
                options = prop_config.get('multi_select', {}).get('options', [])
                print(f"  └─ Options: {len(options)} existing options")
        
        print("\n🔍 CHECKING FOR EXPECTED PROPERTIES:")
        expected_props = [
            'Primary Themes', 'Specific Focus', 'Content Types', 
            'Emotional Tones', 'Key Topics', 'Tags'
        ]
        
        for prop in expected_props:
            if prop in properties:
                prop_type = properties[prop].get('type')
                print(f"✅ {prop}: {prop_type}")
            else:
                print(f"❌ {prop}: MISSING")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    check_database_properties()