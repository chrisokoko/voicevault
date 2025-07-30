#!/usr/bin/env python3
"""
Create expected outputs using actual transcription data
"""

import json
import os
from pathlib import Path

def create_expected_outputs():
    fixtures_dir = Path("tests/fixtures")
    output_dir = fixtures_dir / "expected_outputs"
    output_dir.mkdir(exist_ok=True)
    
    # Read actual transcripts
    transcripts = {}
    
    # 30s test
    with open("/tmp/30s test - NE Cully Blvd.txt") as f:
        transcripts["30s test - NE Cully Blvd.m4a"] = f.read().strip()
    
    # Background noise test  
    with open("/tmp/background noise - Wallflower Coffee Company 19.txt") as f:
        transcripts["background noise - Wallflower Coffee Company 19.m4a"] = f.read().strip()
    
    # No text test (empty file)
    transcripts["no text - Edificio Paso Moná  .m4a"] = ""
    
    # 40 min test - full transcript  
    with open("/tmp/40 min test - Odyssey - Interview Questions.txt") as f:
        transcripts["40 min test - Odyssey - Interview Questions.m4a"] = f.read().strip()
    
    # Test cases
    test_cases = [
        {
            "filename": "30s test - NE Cully Blvd.m4a",
            "size_mb": 0.27,
            "duration": 32.0,
            "upload_should_succeed": True,
            "transcription_should_succeed": True
        },
        {
            "filename": "background noise - Wallflower Coffee Company 19.m4a", 
            "size_mb": 0.49,
            "duration": 59.6,
            "upload_should_succeed": True,
            "transcription_should_succeed": True
        },
        {
            "filename": "no text - Edificio Paso Moná  .m4a",
            "size_mb": 0.07,
            "duration": 8.3,
            "upload_should_succeed": True,
            "transcription_should_succeed": False  # No speech detected
        },
        {
            "filename": "40 min test - Odyssey - Interview Questions.m4a",
            "size_mb": 19.19,
            "duration": 2312.4,
            "upload_should_succeed": True,
            "transcription_should_succeed": True
        },
        {
            "filename": "test_0kb_0sec_voice.m4a",
            "size_mb": 0.0,
            "duration": 0.0,
            "upload_should_succeed": False,
            "transcription_should_succeed": False
        },
        {
            "filename": "test_corrupted_voice.m4a", 
            "size_mb": 3.719329833984375e-05,
            "duration": 0.0,
            "upload_should_succeed": False,
            "transcription_should_succeed": False
        }
    ]
    
    for test_case in test_cases:
        filename = test_case["filename"]
        transcript = transcripts.get(filename, "")
        
        expected_output = {
            "file_name": filename,
            "file_size_bytes": int(test_case["size_mb"] * 1024 * 1024),
            "file_size_mb": test_case["size_mb"],
            "duration_seconds": test_case["duration"],
            "transcript": transcript,
            "transcript_length": len(transcript),
            "upload_should_succeed": test_case["upload_should_succeed"],
            "transcription_should_succeed": test_case["transcription_should_succeed"],
            "use_multipart_upload": test_case["size_mb"] > 20,
            "claude_tags": {
                "primary_themes": "Testing, Audio Processing",
                "specific_focus": f"File Upload Testing - {Path(filename).stem}",
                "content_types": "Voice Note, Technical Test",
                "emotional_tones": "Neutral, Professional", 
                "key_topics": "Upload Validation, Audio Testing"
            },
            "summary": transcript[:100] + "..." if transcript else f"Test audio file for {Path(filename).stem} validation",
            "deletion_analysis": {
                "should_delete": test_case["duration"] < 2.0 or len(transcript.strip()) < 10,
                "confidence": "medium",
                "reason": "Very short content" if (test_case["duration"] < 2.0 or len(transcript.strip()) < 10) else "Contains meaningful content"
            },
            "expected_processing_time_range": [1.0, min(test_case["duration"] * 2, 300.0)],
            "metadata": {
                "generated_at": "2025-07-30 20:30:00",
                "whisper_model": "base",
                "test_category": "essential"
            }
        }
        
        # Handle edge cases
        if test_case["size_mb"] == 0.0:
            expected_output.update({
                "expected_error": "empty_file",
                "deletion_analysis": {
                    "should_delete": True,
                    "confidence": "high", 
                    "reason": "Empty file with no content"
                }
            })
        elif "corrupted" in filename:
            expected_output.update({
                "expected_error": "invalid_format",
                "deletion_analysis": {
                    "should_delete": True,
                    "confidence": "high",
                    "reason": "Corrupted or invalid audio format"
                }
            })
        
        # Save to JSON
        output_file = output_dir / f"{Path(filename).stem}.json"
        with open(output_file, 'w') as f:
            json.dump(expected_output, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Generated: {output_file.name}")
    
    print(f"\n🎉 All expected outputs generated in {output_dir}")

if __name__ == "__main__":
    create_expected_outputs()