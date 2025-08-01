#!/usr/bin/env python3
"""
Create a fresh Notion database and test multi-select functionality
This will help isolate if the issue is with the current database or the code
"""

import sys
import os
import tempfile

# Add project root to path
project_root = os.path.join(os.path.dirname(__file__), '../../..')
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'src'))

from notion_service import NotionService
from config.config import NOTION_PARENT_PAGE_ID

def test_fresh_database():
    """Create a fresh database and test all multi-select fields"""
    
    print("=" * 80)
    print("🆕 TESTING WITH FRESH NOTION DATABASE")
    print("=" * 80)
    
    # Create a new NotionService instance that will create a fresh database
    print("🔧 Creating fresh Notion database...")
    
    # Temporarily override the database ID to force creation of new database
    original_db_id = os.environ.get('NOTION_DATABASE_ID')
    if 'NOTION_DATABASE_ID' in os.environ:
        del os.environ['NOTION_DATABASE_ID']
    
    try:
        # This should create a new database since NOTION_DATABASE_ID is not set
        fresh_notion = NotionService()
        
        if not fresh_notion.database_id:
            print("❌ Failed to create fresh database")
            return False
        
        print(f"✅ Created fresh database: {fresh_notion.database_id}")
        
        # Test data
        test_title = "Fresh DB Test - Multi-Select"
        test_transcript = "This is a test transcript for the fresh database multi-select test."
        test_summary = "Testing multi-select fields in fresh database"
        test_filename = "fresh_test.m4a"
        
        # Create test file
        with tempfile.NamedTemporaryFile(suffix='.m4a', delete=False) as temp_file:
            temp_file.write(b'test audio data')
            temp_path = temp_file.name
        
        # Test consolidated tags approach
        test_cases = [
            {
                "name": "Comprehensive Business Tags",
                "claude_tags": {
                    'tags': 'Business Systems, Client Management, Pipeline Design, Process Planning, Strategic Thinking, Analytical, CRM System, Sales Pipeline'
                }
            },
            {
                "name": "Focused Business Tags",
                "claude_tags": {
                    'tags': 'Pipeline Design, Lead Management, CRM System, Sales Pipeline'
                }
            },
            {
                "name": "Simple Business Tags",
                "claude_tags": {
                    'tags': 'Pipeline Design, Business Planning, CRM'
                }
            },
            {
                "name": "Minimal Tags",
                "claude_tags": {
                    'tags': 'CRM System, Business'
                }
            }
        ]
        
        print(f"\n🧪 Running {len(test_cases)} test cases on fresh database...")
        
        results = []
        
        for i, test_case in enumerate(test_cases, 1):
            case_name = test_case["name"]
            claude_tags = test_case["claude_tags"]
            
            print(f"\n🔍 Test {i}/{len(test_cases)}: {case_name}")
            print(f"   Tags: {claude_tags}")
            
            try:
                page_id = fresh_notion.create_page(
                    title=f"{test_title} - Case {i}",
                    transcript=test_transcript,
                    claude_tags=claude_tags,
                    summary=test_summary,
                    filename=f"case_{i}_{test_filename}",
                    audio_file_path=temp_path
                )
                
                if page_id:
                    print(f"   ✅ SUCCESS: Page created with ID: {page_id}")
                    
                    # Verify the multi-select fields were set
                    try:
                        page_data = fresh_notion.get_page(page_id)
                        properties = page_data.get('properties', {})
                        
                        # Verify Tags field (now rich_text)
                        tags_field = properties.get('Tags', {}).get('rich_text', [])
                        if tags_field and len(tags_field) > 0:
                            tags_content = tags_field[0].get('text', {}).get('content', '')
                            print(f"      • Tags: {tags_content}")
                        else:
                            print(f"      • Tags: NOT FOUND OR EMPTY")
                        
                    except Exception as verify_error:
                        print(f"   ⚠️  Could not verify fields: {verify_error}")
                    
                    results.append({
                        "case": case_name,
                        "status": "SUCCESS",
                        "page_id": page_id
                    })
                else:
                    print(f"   ❌ FAILED: Page creation returned None")
                    results.append({
                        "case": case_name,
                        "status": "FAILED_NULL",
                        "page_id": None
                    })
                    
            except Exception as e:
                print(f"   ❌ ERROR: {e}")
                results.append({
                    "case": case_name,
                    "status": "ERROR",
                    "error": str(e)
                })
        
        # Clean up
        os.unlink(temp_path)
        
        # Summary
        print(f"\n🎯 FRESH DATABASE TEST RESULTS:")
        print("=" * 50)
        
        successful = [r for r in results if r["status"] == "SUCCESS"]
        failed = [r for r in results if r["status"] != "SUCCESS"]
        
        print(f"✅ Successful: {len(successful)}/{len(results)}")
        print(f"❌ Failed: {len(failed)}/{len(results)}")
        
        if successful:
            print(f"\n✅ WORKING TEST CASES:")
            for result in successful:
                print(f"   • {result['case']}: {result['page_id']}")
        
        if failed:
            print(f"\n❌ FAILING TEST CASES:")
            for result in failed:
                error_msg = result.get('error', 'Unknown error')
                print(f"   • {result['case']}: {error_msg}")
        
        print(f"\n🔍 CONCLUSION:")
        print("=" * 30)
        
        if len(successful) == len(results):
            print("🎉 ALL TESTS PASSED - Issue was with the old database!")
            print("   The multi-select implementation works perfectly with fresh database")
        elif len(successful) > 0:
            print("🤔 PARTIAL SUCCESS - Some tests work in fresh database")
            print("   Issue might be specific to certain field combinations")
        else:
            print("😱 ALL TESTS FAILED - Issue is with the code, not database")
            print("   Need to investigate the multi-select implementation further")
        
        print(f"\n📋 FRESH DATABASE INFO:")
        print(f"   Database ID: {fresh_notion.database_id}")
        print(f"   Can be used for future testing if needed")
        
        return fresh_notion.database_id
        
    except Exception as e:
        print(f"❌ ERROR creating fresh database: {e}")
        return None
        
    finally:
        # Restore original database ID
        if original_db_id:
            os.environ['NOTION_DATABASE_ID'] = original_db_id

if __name__ == "__main__":
    fresh_db_id = test_fresh_database()
    
    if fresh_db_id:
        print(f"\n💡 TIP: You can use this fresh database for testing:")
        print(f"   export NOTION_DATABASE_ID='{fresh_db_id}'")
        print(f"   Or update your config.py with this ID")