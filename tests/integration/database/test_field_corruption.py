#!/usr/bin/env python3
"""
Deep inspection of failing fields to find corruption or configuration issues
"""

import sys
import os
import json

# Add project root to path
project_root = os.path.join(os.path.dirname(__file__), '../../..')
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'src'))

from notion_service import NotionService

def inspect_field_corruption():
    """Deep inspection of failing vs working fields"""
    
    print("=" * 80)
    print("🔍 DEEP FIELD CORRUPTION ANALYSIS")
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
        
        # Compare working vs failing fields
        field_comparison = {
            'working': ['Tags', 'Primary Themes', 'Content Types', 'Emotional Tones'],
            'failing': ['Specific Focus', 'Key Topics']
        }
        
        print("🔍 COMPARING WORKING vs FAILING FIELD CONFIGURATIONS:")
        print("=" * 70)
        
        for status, field_names in field_comparison.items():
            print(f"\n{status.upper()} FIELDS:")
            print("-" * 40)
            
            for field_name in field_names:
                if field_name not in properties:
                    print(f"❌ {field_name}: NOT FOUND IN DATABASE")
                    continue
                
                field_config = properties[field_name]
                multiselect_config = field_config.get('multi_select', {})
                options = multiselect_config.get('options', [])
                
                print(f"\n📂 {field_name}:")
                print(f"   Type: {field_config.get('type')}")
                print(f"   Options count: {len(options)}")
                
                # Check configuration details
                print(f"   Config keys: {list(multiselect_config.keys())}")
                
                # Analyze options for corruption
                if options:
                    # Check for invalid option structures
                    invalid_options = []
                    for i, option in enumerate(options):
                        if not isinstance(option, dict):
                            invalid_options.append(f"Index {i}: Not a dict - {type(option)}")
                        elif 'name' not in option:
                            invalid_options.append(f"Index {i}: Missing 'name' key")
                        elif not isinstance(option.get('name'), str):
                            invalid_options.append(f"Index {i}: Invalid name type - {type(option.get('name'))}")
                        elif option.get('name') is None or option.get('name') == '':
                            invalid_options.append(f"Index {i}: Empty name")
                    
                    if invalid_options:
                        print(f"   ❌ CORRUPTION FOUND: {len(invalid_options)} invalid options")
                        for error in invalid_options[:5]:  # Show first 5
                            print(f"      • {error}")
                        if len(invalid_options) > 5:
                            print(f"      • ... and {len(invalid_options) - 5} more")
                    else:
                        print(f"   ✅ All options have valid structure")
                    
                    # Check for duplicate names
                    names = [opt.get('name', '') for opt in options]
                    unique_names = set(names)
                    if len(names) != len(unique_names):
                        duplicates = len(names) - len(unique_names)
                        print(f"   ⚠️  {duplicates} duplicate names found")
                    
                    # Check for extremely long names
                    long_names = [name for name in names if len(str(name)) > 100]
                    if long_names:
                        print(f"   ⚠️  {len(long_names)} names >100 chars")
                        for long_name in long_names[:3]:
                            print(f"      • '{str(long_name)[:50]}...' ({len(str(long_name))} chars)")
                    
                    # Check for special characters that might cause issues
                    problematic_chars = ['\\n', '\\r', '\\t', '\\0', '"', "'", '`']
                    problematic_names = []
                    for name in names[:100]:  # Check first 100 to avoid performance issues
                        for char in problematic_chars:
                            if char in str(name):
                                problematic_names.append((name, char))
                                break
                    
                    if problematic_names:
                        print(f"   ⚠️  {len(problematic_names)} names with special chars")
                        for name, char in problematic_names[:3]:
                            print(f"      • Contains '{char}': '{str(name)[:30]}...'")
        
        # Try to create new options on failing fields to see the exact error
        print(f"\n🧪 TESTING OPTION CREATION ON FAILING FIELDS:")
        print("=" * 60)
        
        failing_fields = ['Specific Focus', 'Key Topics']
        
        for field_name in failing_fields:
            print(f"\n🔍 Testing {field_name}:")
            
            # Try to create a page with a completely new option value
            test_value = f"TEST_OPTION_{field_name.replace(' ', '_').upper()}"
            
            claude_tags = {}
            if field_name == 'Specific Focus':
                claude_tags['specific_focus'] = test_value
            elif field_name == 'Key Topics':
                claude_tags['key_topics'] = test_value
            
            try:
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.m4a', delete=False) as temp_file:
                    temp_file.write(b'test data')
                    temp_path = temp_file.name
                
                print(f"   Testing with new option: '{test_value}'")
                
                page_id = notion.create_page(
                    title=f"Corruption Test - {field_name}",
                    transcript="Test transcript",
                    claude_tags=claude_tags,
                    summary="Test summary",
                    filename="test.m4a",
                    audio_file_path=temp_path
                )
                
                os.unlink(temp_path)
                
                if page_id:
                    print(f"   ✅ SUCCESS: New option creation works")
                else:
                    print(f"   ❌ FAILED: Cannot create new options")
                    
            except Exception as e:
                print(f"   ❌ ERROR: {e}")
                if "500" in str(e) or "Internal Server Error" in str(e):
                    print(f"   🎯 CONFIRMED: 500 error on this field")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    inspect_field_corruption()