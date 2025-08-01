#!/usr/bin/env python3
"""
Temporary script to test the Claude formatter function with large transcript
"""

import os
import sys
import logging
from datetime import datetime

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from claude_service import ClaudeService

def main():
    """Test the formatter function with the large transcript"""
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # Read the test transcript
    transcript_file = "/Users/chris/Desktop/Manual Library/voice-memo-processor/tests/large_file_transcipt.md"
    
    try:
        with open(transcript_file, 'r', encoding='utf-8') as f:
            original_transcript = f.read()
        
        logger.info(f"Loaded transcript: {len(original_transcript)} characters")
        
        # Initialize Claude service
        claude_service = ClaudeService()
        
        # Test the formatter
        print("="*80)
        print("TESTING TRANSCRIPT FORMATTER")
        print("="*80)
        print(f"Original transcript length: {len(original_transcript)} characters")
        print(f"Estimated tokens: {len(original_transcript) // 4}")
        print()
        
        # Format the transcript
        logger.info("Starting formatting...")
        formatted_transcript = claude_service.format_transcript(original_transcript)
        
        print(f"Formatted transcript length: {len(formatted_transcript)} characters")
        print()
        
        # Save the formatted result in tmp (regardless of success/failure)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"/tmp/formatted_transcript_{timestamp}.md"
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("# FORMATTED TRANSCRIPT OUTPUT\n")
                f.write(f"Generated: {datetime.now()}\n")
                f.write(f"Original length: {len(original_transcript)} chars\n")
                f.write(f"Formatted length: {len(formatted_transcript)} chars\n")
                f.write("\n" + "="*80 + "\n\n")
                f.write(formatted_transcript)
            
            print(f"✅ Results saved to: {output_file}")
        except Exception as save_error:
            print(f"❌ Error saving file: {save_error}")
        
        print()
        print("FORMATTED TRANSCRIPT PREVIEW:")
        print("-" * 80)
        print(formatted_transcript[:1000] + "..." if len(formatted_transcript) > 1000 else formatted_transcript)
        
    except FileNotFoundError:
        print(f"❌ Error: Could not find transcript file at {transcript_file}")
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Error in formatting test: {e}")

if __name__ == "__main__":
    main()