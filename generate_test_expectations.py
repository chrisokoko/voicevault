#!/usr/bin/env python3
"""
Generate expected outputs for test audio files using Whisper

This processes each test audio file and creates expected output JSON files
that the tests can validate against.
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, Any
import subprocess

def get_audio_duration_ffprobe(file_path: str) -> float:
    """Get duration using ffprobe"""
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-print_format', 'json', 
            '-show_format', str(file_path)
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            duration = float(data['format']['duration'])
            return duration
    except Exception as e:
        print(f"Error getting duration: {e}")
    return 0.0

def transcribe_with_whisper(file_path: str) -> str:
    """Transcribe audio file using Whisper"""
    try:
        print(f"  Transcribing with Whisper...")
        result = subprocess.run([
            'python3', '-m', 'whisper', str(file_path), 
            '--model', 'base',
            '--output_format', 'txt',
            '--output_dir', '/tmp'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            # Read the generated transcript file
            txt_file = Path('/tmp') / f"{Path(file_path).stem}.txt"
            if txt_file.exists():
                transcript = txt_file.read_text().strip()
                txt_file.unlink()  # Clean up
                return transcript
        
        print(f"  Whisper failed: {result.stderr}")
        return ""
        
    except Exception as e:
        print(f"  Error with Whisper: {e}")
        return ""

def generate_expected_output(file_path: Path) -> Dict[str, Any]:
    """Generate expected output for a test audio file"""
    print(f"\nProcessing: {file_path.name}")
    
    file_size = file_path.stat().st_size
    file_size_mb = file_size / (1024 * 1024)
    
    # Handle edge cases
    if file_size == 0:
        return {
            "file_name": file_path.name,
            "file_size_bytes": 0,
            "file_size_mb": 0.0,
            "duration_seconds": 0.0,
            "transcript": "",
            "upload_should_succeed": False,
            "transcription_should_succeed": False,
            "expected_error": "empty_file",
            "deletion_analysis": {
                "should_delete": True,
                "confidence": "high",
                "reason": "Empty file with no content"
            }
        }
    
    if "corrupted" in file_path.name:
        return {
            "file_name": file_path.name,
            "file_size_bytes": file_size,
            "file_size_mb": file_size_mb,
            "duration_seconds": 0.0,
            "transcript": "",
            "upload_should_succeed": False,
            "transcription_should_succeed": False,
            "expected_error": "invalid_format",
            "deletion_analysis": {
                "should_delete": True,
                "confidence": "high",
                "reason": "Corrupted or invalid audio format"
            }
        }
    
    # Get duration
    duration = get_audio_duration_ffprobe(str(file_path))
    print(f"  Duration: {duration:.1f} seconds")
    print(f"  Size: {file_size_mb:.2f} MB")
    
    # Transcribe
    transcript = transcribe_with_whisper(str(file_path))
    print(f"  Transcript length: {len(transcript)} characters")
    if transcript:
        print(f"  First 100 chars: {transcript[:100]}...")
    
    # Determine expected behavior
    upload_should_succeed = file_size > 0 and not "corrupted" in file_path.name
    transcription_should_succeed = duration > 0.5 and transcript.strip() != ""
    
    # Generate Claude-style tags based on file characteristics
    claude_tags = {
        "primary_themes": "Testing, Audio Processing",
        "specific_focus": f"File Upload Testing - {file_path.stem}",
        "content_types": "Voice Note, Technical Test",
        "emotional_tones": "Neutral, Professional",
        "key_topics": "Upload Validation, Audio Testing"
    }
    
    # Basic summary
    if transcript:
        summary = f"Test audio file containing: {transcript[:100]}..."
    else:
        summary = f"Test audio file for {file_path.stem} validation"
    
    # Deletion analysis
    should_delete = duration < 2.0 or len(transcript.strip()) < 10
    deletion_analysis = {
        "should_delete": should_delete,
        "confidence": "medium",
        "reason": "Very short content" if should_delete else "Contains meaningful content"
    }
    
    return {
        "file_name": file_path.name,
        "file_size_bytes": file_size,
        "file_size_mb": round(file_size_mb, 2),
        "duration_seconds": round(duration, 1),
        "transcript": transcript,
        "transcript_length": len(transcript),
        "upload_should_succeed": upload_should_succeed,
        "transcription_should_succeed": transcription_should_succeed,
        "use_multipart_upload": file_size_mb > 20,
        "claude_tags": claude_tags,
        "summary": summary,
        "deletion_analysis": deletion_analysis,
        "expected_processing_time_range": [1.0, min(duration * 2, 300.0)],  # 1s to 5min max
        "metadata": {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "whisper_model": "base",
            "test_category": "essential"
        }
    }

def main():
    fixtures_dir = Path("tests/fixtures")
    audio_dir = fixtures_dir / "audio_samples"
    output_dir = fixtures_dir / "expected_outputs"
    
    output_dir.mkdir(exist_ok=True)
    
    print("🎯 Generating Expected Outputs for Updated Test Files")
    print("=" * 60)
    
    # Focus on the 4 new audio files plus edge cases
    target_files = [
        "30s test - NE Cully Blvd.m4a",
        "40 min test - Odyssey - Interview Questions.m4a", 
        "background noise - Wallflower Coffee Company 19.m4a",
        "no text - Edificio Paso Moná  .m4a",
        "test_0kb_0sec_voice.m4a",
        "test_corrupted_voice.m4a"
    ]
    
    audio_files = []
    for filename in target_files:
        file_path = audio_dir / filename
        if file_path.exists():
            audio_files.append(file_path)
        else:
            print(f"⚠️  File not found: {filename}")
    
    if not audio_files:
        print("❌ No target audio files found in tests/fixtures/audio_samples/")
        return
    
    print(f"Found {len(audio_files)} test files to process")
    
    for audio_file in sorted(audio_files):
        expected_output = generate_expected_output(audio_file)
        
        # Save to JSON file
        output_file = output_dir / f"{audio_file.stem}.json"
        
        with open(output_file, 'w') as f:
            json.dump(expected_output, f, indent=2, ensure_ascii=False)
        
        print(f"  ✅ Generated: {output_file.name}")
    
    print("\n" + "=" * 60)
    print("🎉 Expected outputs generated!")
    print(f"📁 Files saved to: {output_dir}")
    print("\nThese files now provide deterministic test expectations for:")
    print("  ✅ Transcription accuracy validation")
    print("  ✅ Upload success/failure expectations") 
    print("  ✅ File processing behavior")
    print("  ✅ Edge case handling")
    
    # Print summary
    print(f"\n📊 Test File Summary:")
    for audio_file in sorted(audio_files):
        output_file = output_dir / f"{audio_file.stem}.json"
        if output_file.exists():
            with open(output_file) as f:
                data = json.load(f)
            print(f"  • {audio_file.name}: {data['file_size_mb']}MB, {data['duration_seconds']}s, "
                  f"Upload: {'✅' if data['upload_should_succeed'] else '❌'}")

if __name__ == "__main__":
    main()