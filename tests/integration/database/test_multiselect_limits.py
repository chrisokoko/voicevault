#!/usr/bin/env python3
"""
Test to investigate multi-select option limits causing 500 errors
"""

import sys
import os

# Add project root to path
project_root = os.path.join(os.path.dirname(__file__), '../../..')
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'src'))

from notion_service import NotionService

def check_multiselect_limits():
    """Check option counts and potential limits for failing fields"""
    
    print("=" * 80)
    print("🔍 INVESTIGATING MULTI-SELECT OPTION LIMITS")
    print("=" * 80)
    
    notion = NotionService()
    
    try:
        # Get full database schema
        database_info = notion._make_api_call(
            "get_database",
            database_id=notion.database_id,
            use_cache=False
        )
        
        properties = database_info.get('properties', {})
        
        multiselect_fields = []
        
        for prop_name, prop_config in properties.items():
            if prop_config.get('type') == 'multi_select':
                options = prop_config.get('multi_select', {}).get('options', [])
                option_count = len(options)
                
                multiselect_fields.append({
                    'name': prop_name,
                    'count': option_count,
                    'working': prop_name not in ['Specific Focus', 'Key Topics']
                })
        
        # Sort by option count
        multiselect_fields.sort(key=lambda x: x['count'], reverse=True)
        
        print("📊 MULTI-SELECT FIELDS BY OPTION COUNT:")
        print("=" * 60)
        
        for field in multiselect_fields:
            status = "✅ WORKING" if field['working'] else "❌ FAILING"
            print(f"{field['count']:>4} options | {field['name']:<20} | {status}")
        
        print(f"\n🎯 ANALYSIS:")
        print("=" * 40)
        
        working_fields = [f for f in multiselect_fields if f['working']]
        failing_fields = [f for f in multiselect_fields if not f['working']]
        
        if working_fields:
            max_working = max(f['count'] for f in working_fields)
            min_working = min(f['count'] for f in working_fields)
            print(f"✅ Working fields: {min_working}-{max_working} options")
        
        if failing_fields:
            max_failing = max(f['count'] for f in failing_fields)
            min_failing = min(f['count'] for f in failing_fields)
            print(f"❌ Failing fields: {min_failing}-{max_failing} options")
        
        # Check if there's a clear threshold
        if failing_fields and working_fields:
            threshold = max_working
            print(f"\n💡 POTENTIAL THRESHOLD: ~{threshold} options")
            print(f"   Fields with >{threshold} options are failing")
            print(f"   Fields with ≤{threshold} options are working")
        
        # Show specific failing field details
        print(f"\n🔍 FAILING FIELD DETAILS:")
        print("-" * 40)
        
        for field_name in ['Specific Focus', 'Key Topics']:
            if field_name in properties:
                field_config = properties[field_name]['multi_select']
                options = field_config.get('options', [])
                
                print(f"\n📂 {field_name}:")
                print(f"   Total options: {len(options)}")
                
                # Show sample options to check for corruption
                if options:
                    print(f"   Sample options:")
                    for i, option in enumerate(options[:5]):
                        name = option.get('name', 'NO_NAME')
                        color = option.get('color', 'NO_COLOR')
                        print(f"     {i+1}. '{name}' ({color})")
                    
                    if len(options) > 5:
                        print(f"     ... and {len(options) - 5} more")
                    
                    # Check for duplicates or weird options
                    names = [opt.get('name', '') for opt in options]
                    duplicates = len(names) - len(set(names))
                    if duplicates > 0:
                        print(f"   ⚠️  {duplicates} duplicate option names found!")
                    
                    # Check for problematic names
                    long_names = [name for name in names if len(name) > 100]
                    if long_names:
                        print(f"   ⚠️  {len(long_names)} options with >100 character names!")
                    
                    empty_names = [name for name in names if not name.strip()]
                    if empty_names:
                        print(f"   ⚠️  {len(empty_names)} options with empty/blank names!")
        
        return multiselect_fields
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return []

if __name__ == "__main__":
    check_multiselect_limits()