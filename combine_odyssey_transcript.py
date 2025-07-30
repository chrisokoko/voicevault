#!/usr/bin/env python3
"""
Combine all Odyssey transcript chunks into one complete transcript
"""

from pathlib import Path

def combine_transcripts():
    chunks = []
    
    # Read all chunks in order
    for i in range(4):
        chunk_file = f"/tmp/odyssey_chunk_{i:03d}.txt"
        if Path(chunk_file).exists():
            with open(chunk_file) as f:
                chunk_text = f.read().strip()
                chunks.append(chunk_text)
                print(f"✅ Read chunk {i}: {len(chunk_text)} characters")
        else:
            print(f"❌ Missing chunk {i}: {chunk_file}")
    
    # Combine all chunks
    full_transcript = "\n\n".join(chunks)
    
    # Save combined transcript
    output_file = "/tmp/40 min test - Odyssey - Interview Questions.txt"
    with open(output_file, 'w') as f:
        f.write(full_transcript)
    
    print(f"\n🎉 Combined transcript saved: {output_file}")
    print(f"📊 Total length: {len(full_transcript)} characters")
    print(f"📊 Total chunks: {len(chunks)}")

if __name__ == "__main__":
    combine_transcripts()