#!/usr/bin/env python3
"""
Integration test to isolate 500 error - Test ONE multi-select field at a time
This will help us identify which specific field or combination is causing issues
"""

import sys
import os
from pprint import pprint
import json
import tempfile

# Add project root to path
project_root = os.path.join(os.path.dirname(__file__), '../../..')
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'src'))

from notion_service import NotionService

def test_single_multiselect_fields():
    """Test creating pages with ONE multi-select field at a time to isolate the 500 error"""
    
    print("=" * 80)
    print("🎯 TESTING SINGLE MULTI-SELECT FIELDS")
    print("=" * 80)
    
    notion = NotionService()
    
    # Base test data (minimal to avoid other issues)
    base_title = "Single Multi-Select Test"
    base_transcript = "This is a test transcript for debugging multi-select issues."
    base_summary = "Test summary"
    base_filename = "test.m4a"
    
    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(suffix='.m4a', delete=False) as temp_file:
        temp_file.write(b'fake audio data for testing')
        temp_path = temp_file.name
    
    # Define each multi-select field to test individually
    multiselect_tests = [
        {
            "name": "Primary Themes",
            "claude_key": "primary_themes",
            "test_value": "Business Systems, Client Management"
        },
        {
            "name": "Specific Focus", 
            "claude_key": "specific_focus",
            "test_value": "Pipeline Design, Lead Management"
        },
        {
            "name": "Content Types",
            "claude_key": "content_types", 
            "test_value": "Process Planning, Strategic Thinking"
        },
        {
            "name": "Emotional Tones",
            "claude_key": "emotional_tones",
            "test_value": "Analytical, Methodical"
        },
        {
            "name": "Key Topics",
            "claude_key": "key_topics",
            "test_value": "CRM System, Sales Pipeline, Lead Tracking"
        },
        {
            "name": "Tags (Combined)",
            "claude_key": "combined_tags",
            "test_value": "Test Tag 1, Test Tag 2, Test Tag 3"
        }
    ]
    
    results = []
    
    print(f"🧪 Testing {len(multiselect_tests)} multi-select fields individually...\n")
    
    for i, test_config in enumerate(multiselect_tests, 1):
        field_name = test_config["name"]
        claude_key = test_config["claude_key"]
        test_value = test_config["test_value"]
        
        print(f"🔍 Test {i}/{len(multiselect_tests)}: {field_name}")
        print(f"   Testing with value: '{test_value}'")
        
        # Create claude_tags with ONLY this field
        claude_tags = {claude_key: test_value}
        
        try:
            print(f"   📤 Creating page with ONLY {field_name} multi-select...")
            
            page_id = notion.create_page(
                title=f"{base_title} - {field_name}",
                transcript=base_transcript,
                claude_tags=claude_tags,
                summary=base_summary,
                filename=f"{field_name.lower().replace(' ', '_')}_test.m4a",
                audio_file_path=temp_path
            )
            
            if page_id:
                print(f"   ✅ SUCCESS: Page created with ID: {page_id}")
                results.append({
                    "field": field_name,
                    "status": "SUCCESS",
                    "page_id": page_id,
                    "error": None
                })
                
                # Verify the field was actually set
                try:
                    page_data = notion.get_page(page_id)
                    properties = page_data.get('properties', {})
                    
                    if field_name in properties:
                        field_data = properties[field_name]
                        if 'multi_select' in field_data:
                            values = field_data['multi_select']
                            value_names = [v.get('name', '') for v in values]
                            print(f"   ✅ VERIFIED: Field has {len(values)} values: {value_names}")
                        else:
                            print(f"   ⚠️  WARNING: Field exists but not as multi_select")
                    else:
                        print(f"   ⚠️  WARNING: Field not found in page properties")
                        
                except Exception as verify_error:
                    print(f"   ⚠️  WARNING: Could not verify field: {verify_error}")
                
            else:
                print(f"   ❌ FAILED: Page creation returned None")
                results.append({
                    "field": field_name,
                    "status": "FAILED_NULL",
                    "page_id": None,
                    "error": "Page creation returned None"
                })
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results.append({
                "field": field_name,
                "status": "ERROR",
                "page_id": None,
                "error": str(e)
            })
        
        print("-" * 60)
    
    # Clean up temp file
    os.unlink(temp_path)
    
    # Summary
    print("\n🎯 SINGLE MULTI-SELECT TEST RESULTS:")
    print("=" * 60)
    
    successful = [r for r in results if r["status"] == "SUCCESS"]
    failed = [r for r in results if r["status"] != "SUCCESS"]
    
    print(f"✅ Successful: {len(successful)}/{len(results)}")
    print(f"❌ Failed: {len(failed)}/{len(results)}")
    
    if successful:
        print(f"\n✅ WORKING FIELDS:")
        for result in successful:
            print(f"   • {result['field']}: {result['page_id']}")
    
    if failed:
        print(f"\n❌ FAILING FIELDS:")
        for result in failed:
            print(f"   • {result['field']}: {result['error']}")
    
    # Test the control case - NO multi-select fields
    print(f"\n🔬 CONTROL TEST: Page with NO multi-select fields")
    print("-" * 60)
    
    try:
        control_page_id = notion.create_page(
            title="Control Test - No Multi-Select",
            transcript=base_transcript,
            claude_tags={},  # Empty tags
            summary=base_summary,
            filename="control_test.m4a",
            audio_file_path=temp_path  # This will fail but that's OK
        )
        
        if control_page_id:
            print(f"✅ CONTROL SUCCESS: No multi-select fields work fine: {control_page_id}")
        else:
            print(f"❌ CONTROL FAILED: Even basic page creation fails")
            
    except Exception as control_error:
        print(f"❌ CONTROL ERROR: {control_error}")
    
    print("\n🔍 ANALYSIS:")
    print("=" * 40)
    
    if len(successful) == len(multiselect_tests):
        print("🤔 ALL individual fields work - issue might be with COMBINING multiple fields")
    elif len(successful) == 0:
        print("😱 NO fields work individually - fundamental multi-select issue")
    else:
        print(f"🎯 PARTIAL SUCCESS - {len(successful)} work, {len(failed)} fail")
        print("   Issue might be with specific field names or data types")
    
    return results

if __name__ == "__main__":
    test_single_multiselect_fields()