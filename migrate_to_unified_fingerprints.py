#!/usr/bin/env python3
"""
Migration Script: Convert Individual Semantic Fingerprints to Unified JSON

This script consolidates all individual semantic fingerprint JSON files into a single
unified JSON file that can later be extended with embeddings.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def migrate_to_unified_format():
    """Migrate all individual semantic fingerprint files to unified format"""
    
    # Paths
    semantic_fingerprints_dir = Path("data/semantic_fingerprints")
    unified_file = Path("data/semantic_fingerprints_with_embeddings.json")
    
    # Check if source directory exists
    if not semantic_fingerprints_dir.exists():
        logger.error(f"Source directory not found: {semantic_fingerprints_dir}")
        return
    
    # Initialize unified data structure
    unified_data = {}
    
    # Check if unified file already exists
    if unified_file.exists():
        try:
            with open(unified_file, 'r', encoding='utf-8') as f:
                unified_data = json.load(f)
            logger.info(f"Found existing unified file with {len(unified_data)} entries")
        except Exception as e:
            logger.error(f"Error reading existing unified file: {e}")
            logger.info("Starting with empty unified data")
    
    # Process all JSON files in semantic fingerprints directory
    fingerprint_files = list(semantic_fingerprints_dir.glob("*.json"))
    logger.info(f"Found {len(fingerprint_files)} semantic fingerprint files to process")
    
    processed_count = 0
    skipped_count = 0
    
    for fingerprint_file in fingerprint_files:
        # Determine audio filename from JSON filename
        audio_filename = fingerprint_file.stem + ".m4a"
        
        # Skip if already exists in unified data
        if audio_filename in unified_data:
            logger.info(f"⏭️  Skipping {audio_filename} - already in unified file")
            skipped_count += 1
            continue
        
        try:
            # Load semantic fingerprint
            with open(fingerprint_file, 'r', encoding='utf-8') as f:
                semantic_fingerprint = json.load(f)
            
            # Create unified entry (without embedding for now)
            unified_data[audio_filename] = {
                "semantic_fingerprint": semantic_fingerprint,
                "metadata": {
                    "migrated_at": datetime.now().isoformat(),
                    "audio_filename": audio_filename,
                    "fingerprint_source": str(fingerprint_file)
                }
            }
            
            logger.info(f"✅ Migrated {audio_filename}")
            processed_count += 1
            
        except Exception as e:
            logger.error(f"❌ Error processing {fingerprint_file}: {e}")
    
    # Save unified file
    try:
        # Ensure directory exists
        unified_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(unified_file, 'w', encoding='utf-8') as f:
            json.dump(unified_data, f, indent=2, ensure_ascii=False)
        
        # Get file size
        file_size_mb = unified_file.stat().st_size / (1024 * 1024)
        
        logger.info(f"\n🎉 MIGRATION COMPLETE!")
        logger.info(f"📁 Total files processed: {processed_count}")
        logger.info(f"⏭️  Files skipped: {skipped_count}")
        logger.info(f"📄 Unified file: {unified_file}")
        logger.info(f"📊 File size: {file_size_mb:.2f} MB")
        logger.info(f"📦 Total entries: {len(unified_data)}")
        
    except Exception as e:
        logger.error(f"❌ Error saving unified file: {e}")
        return
    
    return unified_data

def preview_unified_structure():
    """Preview the structure of the unified file"""
    unified_file = Path("data/semantic_fingerprints_with_embeddings.json")
    
    if not unified_file.exists():
        logger.error("Unified file does not exist yet. Run migration first.")
        return
    
    try:
        with open(unified_file, 'r', encoding='utf-8') as f:
            unified_data = json.load(f)
        
        print(f"\n📊 UNIFIED FILE PREVIEW")
        print(f"Total entries: {len(unified_data)}")
        print(f"File size: {unified_file.stat().st_size / (1024 * 1024):.2f} MB")
        
        # Show first few entries
        sample_entries = list(unified_data.keys())[:3]
        print(f"\n📋 Sample entries:")
        for filename in sample_entries:
            entry = unified_data[filename]
            has_fingerprint = 'semantic_fingerprint' in entry
            has_embedding = 'embedding' in entry
            print(f"  • {filename}")
            print(f"    - Has semantic fingerprint: {has_fingerprint}")
            print(f"    - Has embedding: {has_embedding}")
            if has_fingerprint:
                fp = entry['semantic_fingerprint']
                raw_essence = fp.get('raw_essence', '')[:100] + "..." if len(fp.get('raw_essence', '')) > 100 else fp.get('raw_essence', 'N/A')
                print(f"    - Raw essence: {raw_essence}")
        
        print(f"\n🔧 Ready for embedding generation!")
        
    except Exception as e:
        logger.error(f"Error previewing unified file: {e}")

def main():
    """Main migration function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate semantic fingerprints to unified JSON format")
    parser.add_argument("--migrate", action="store_true", help="Run the migration")
    parser.add_argument("--preview", action="store_true", help="Preview the unified file structure")
    
    args = parser.parse_args()
    
    if args.preview:
        preview_unified_structure()
    elif args.migrate:
        migrate_to_unified_format()
    else:
        print("Use --migrate to run migration or --preview to view unified file")

if __name__ == "__main__":
    main()