#!/usr/bin/env python3
"""
Simple test to identify the 500 error cause with multi-select tags
"""

import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from notion_service import NotionService

def test_simple_page_creation():
    """Test creating a page with minimal multi-select tags"""
    
    notion = NotionService()
    
    # Test data
    test_title = "Test Multi-Select Tags"
    test_transcript = "This is a test transcript for debugging multi-select tag issues."
    
    # Simple tags that should work
    claude_tags = {
        'primary_themes': 'Test Theme',
        'specific_focus': 'Debugging',  
        'content_types': 'Test Content',
        'emotional_tones': 'Neutral',
        'key_topics': 'Testing, Debugging'
    }
    
    print("Testing simple page creation with multi-select tags...")
    print(f"Tags: {claude_tags}")
    
    try:        
        # Test with minimal approach - no audio metadata
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.m4a', delete=False) as temp_file:
            temp_file.write(b'fake audio data')
            temp_path = temp_file.name
        
        page_id = notion.create_page(
            title=test_title,
            transcript=test_transcript,
            claude_tags=claude_tags,
            summary="Test summary",
            filename="test_file.m4a",
            audio_file_path=temp_path
        )
        
        # Clean up
        os.unlink(temp_path)
        
        if page_id:
            print(f"✅ SUCCESS: Page created with ID: {page_id}")
            return True
        else:
            print("❌ FAILED: Page creation returned None")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_simple_page_creation()