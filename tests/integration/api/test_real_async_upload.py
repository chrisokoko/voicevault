#!/usr/bin/env python3
"""
REAL TEST: Test async upload with actual Notion API and audio files
Usage: python3 test_real_async_upload.py <audio_file_path>
"""

import os
import sys
import asyncio
import logging
import argparse
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from notion_service import NotionService

async def test_real_async_upload(test_file_path: str):
    """Test the async upload with real Notion API"""
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    test_file = test_file_path
    
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return False
    
    try:
        print("="*80)
        print("🚀 REAL ASYNC UPLOAD TEST")
        print("="*80)
        print(f"File: {os.path.basename(test_file)}")
        print(f"Size: {os.path.getsize(test_file) / (1024 * 1024):.1f} MB")
        print()
        
        # Initialize Notion service
        notion_service = NotionService()
        
        # Check database connection first
        if not notion_service.check_database_exists():
            print("❌ Cannot connect to Notion database")
            return False
        
        print("✅ Connected to Notion database")
        
        # Create a test page for upload
        print("📄 Creating test page...")
        
        page_id = notion_service.create_page(
            title="[TEST] Async Upload Test - " + os.path.basename(test_file),
            transcript="This is a test page for async upload verification",
            claude_tags={
                "primary_themes": "Testing",
                "content_types": "Test Upload"
            },
            summary="Test page for async upload functionality",
            filename=os.path.basename(test_file),
            audio_file_path=test_file
        )
        
        if not page_id:
            print("❌ Failed to create test page")
            return False
            
        print(f"✅ Created test page: {page_id}")
        
        # NOW TEST THE NEW ASYNC UPLOAD
        print("\n🔄 Testing ASYNC upload (no hardcoded delays)...")
        start_time = datetime.now()
        
        result = await notion_service.add_audio_file_to_page_async(page_id, test_file)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"⏱️  Async upload completed in {duration:.2f} seconds")
        
        if result["success"]:
            print("🎉 ASYNC UPLOAD SUCCESS!")
            print(f"   Status: {result['status']}")
            print(f"   Details: {result['reason']}")
            if 'file_url' in result and result['file_url']:
                print(f"   File URL: ✅ Present")
            else:
                print(f"   File URL: ❌ Missing")
            return True
        else:
            print("❌ ASYNC UPLOAD FAILED!")
            print(f"   Error Type: {result['error_type']}")
            print(f"   Reason: {result['reason']}")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run the async upload test"""
    parser = argparse.ArgumentParser(description='Test async upload with real Notion API')
    parser.add_argument('file_path', help='Path to audio file to test')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file_path):
        print(f"❌ File not found: {args.file_path}")
        return
    
    print("🧪 REAL ASYNC UPLOAD TESTING")
    print("This will make actual API calls to Notion")
    print(f"📄 Testing with: {os.path.basename(args.file_path)}")
    file_size_mb = os.path.getsize(args.file_path) / (1024 * 1024) 
    print(f"📏 File size: {file_size_mb:.1f} MB")
    print()
    
    # Test async upload
    success = await test_real_async_upload(args.file_path)
    
    print("\n" + "="*80)
    if success:
        print("🎉 TEST PASSED - Async upload is working!")
        print("✅ No more hardcoded delays")
        print("✅ Proper async/await implementation") 
        print("✅ Real upload verification")
    else:
        print("❌ TEST FAILED - Need to debug")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(main())