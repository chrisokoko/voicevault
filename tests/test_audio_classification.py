#!/usr/bin/env python3
"""
Audio classification test script - moved to tests directory
Usage: python3 tests/test_audio_classification.py <audio_file_path>
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from audio_classifier import YAMNetAudioClassifier, classify_audio_file

def test_single_file(audio_file_path: str):
    """Test classification on a single audio file"""
    
    print("="*80)
    print("🎵 YAMNET AUDIO CLASSIFICATION TEST")
    print("="*80)
    print(f"File: {os.path.basename(audio_file_path)}")
    
    if not os.path.exists(audio_file_path):
        print(f"❌ File not found: {audio_file_path}")
        return False
    
    file_size_mb = os.path.getsize(audio_file_path) / (1024 * 1024)
    print(f"Size: {file_size_mb:.2f} MB")
    print()
    
    try:
        # Test classification
        print("🔄 Classifying audio with YAMNet...")
        result = classify_audio_file(audio_file_path)
        
        if result.get('primary_class') == 'error' or 'error' in result:
            print(f"❌ Classification failed: {result.get('error', 'Unknown error')}")
            return False
        
        print("✅ Classification successful!")
        print()
        
        # Display results
        print("📊 CLASSIFICATION RESULTS:")
        print(f"   YAMNet Primary Class: {result['primary_class']}")
        print(f"   Confidence: {result['confidence']:.3f}")
        print(f"   Duration: {result['audio_duration']:.1f} seconds")
        print(f"   Should Transcribe: {'YES' if result['should_transcribe'] else 'NO'}")
        print(f"   Processing Method: {result['processing_recommendation']}")
        
        print(f"\n🤖 TOP YAMNET PREDICTIONS:")
        for i, (class_name, confidence) in enumerate(result['top_yamnet_predictions'], 1):
            print(f"   {i}. {class_name}: {confidence:.3f}")
        
        print("\n" + "="*80)
        
        # Interpretation
        primary_class_lower = result['primary_class'].lower()
        
        if any(word in primary_class_lower for word in ['music', 'singing', 'vocal']):
            print("🎵 DETECTED: Musical content")
            print("   ✅ Will be transcribed to capture any lyrics")
            print("   ✅ YAMNet classification will inform tagging")
        elif any(word in primary_class_lower for word in ['speech', 'conversation', 'narration']):
            print("🗣️  DETECTED: Speech content")
            print("   ✅ Will be transcribed normally")
        else:
            print(f"🔊 DETECTED: {result['primary_class']}")
            print("   ✅ Will be transcribed - let content determine value")
            
        print("="*80)
        return True
        
    except Exception as e:
        print(f"❌ Error during classification: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_multiple_files():
    """Test classification on multiple sample files"""
    
    # Look for test files in audio_files directory
    audio_dir = Path("audio_files")
    if not audio_dir.exists():
        print("No audio_files directory found for batch testing")
        return
    
    # Find a few different types of files
    test_files = []
    for pattern in ["*.m4a", "*.mp3", "*.wav"]:
        test_files.extend(list(audio_dir.glob(pattern))[:3])  # Max 3 per type
    
    if not test_files:
        print("No audio files found for batch testing")
        return
    
    print(f"\n🔄 BATCH TESTING {len(test_files)} files...")
    
    try:
        classifier = YAMNetAudioClassifier()
        results = classifier.batch_classify([str(f) for f in test_files])
        
        print(f"\n📈 BATCH RESULTS SUMMARY:")
        summary = classifier.get_classification_summary(results)
        
        print(f"   Total files tested: {summary['total_files']}")
        print(f"   Average confidence: {summary['avg_confidence']:.3f}")
        
        print(f"\n📊 CATEGORY DISTRIBUTION:")
        for category, count in sorted(summary['category_counts'].items(), key=lambda x: x[1], reverse=True):
            print(f"   {category.capitalize()}: {count} files")
        
        print(f"\n⚙️  PROCESSING RECOMMENDATIONS:")
        for method, count in sorted(summary['processing_recommendations'].items(), key=lambda x: x[1], reverse=True):
            print(f"   {method}: {count} files")
            
    except Exception as e:
        print(f"❌ Batch testing failed: {e}")

def main():
    """Main test function"""
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    parser = argparse.ArgumentParser(description='Test YAMNet audio classification')
    parser.add_argument('audio_file', help='Path to audio file to classify')
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    
    args = parser.parse_args()
    
    # Test single file
    success = test_single_file(args.audio_file)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()