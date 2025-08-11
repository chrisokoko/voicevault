#!/usr/bin/env python3
"""
Calculate Similarity Matrix

Extract vectors from the unified embeddings database and calculate cosine similarity matrix.
"""

import json
import numpy as np
from pathlib import Path
import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from embedding_service import EmbeddingService

def main():
    # Load the unified embeddings data
    unified_file = Path("data/semantic_fingerprints_with_embeddings.json")
    
    if not unified_file.exists():
        print(f"Error: Unified embeddings file not found: {unified_file}")
        return
    
    with open(unified_file, 'r', encoding='utf-8') as f:
        unified_data = json.load(f)
    
    # Extract vectors and filenames
    vectors = []
    filenames = []
    
    for filename, entry in unified_data.items():
        if 'embedding' in entry and 'vector' in entry['embedding']:
            vectors.append(entry['embedding']['vector'])
            filenames.append(filename)
    
    print(f"Found {len(vectors)} vectors from {len(unified_data)} total entries")
    
    if len(vectors) == 0:
        print("No vectors found in database")
        return
    
    # Initialize embedding service and calculate similarity matrix
    service = EmbeddingService()
    print("Calculating similarity matrix...")
    similarity_matrix = service.calculate_similarity_matrix(vectors)
    
    print(f"Similarity matrix shape: {similarity_matrix.shape}")
    print(f"Matrix statistics:")
    print(f"  Mean similarity: {np.mean(similarity_matrix):.4f}")
    print(f"  Min similarity: {np.min(similarity_matrix):.4f}")
    print(f"  Max similarity: {np.max(similarity_matrix):.4f}")
    
    # Save similarity matrix
    matrix_file = Path("data/similarity_matrix.npy")
    np.save(matrix_file, similarity_matrix)
    print(f"✅ Similarity matrix saved to: {matrix_file}")
    
    # Save filename mapping
    filenames_file = Path("data/similarity_matrix_filenames.json")
    with open(filenames_file, 'w', encoding='utf-8') as f:
        json.dump(filenames, f, indent=2, ensure_ascii=False)
    print(f"✅ Filename mapping saved to: {filenames_file}")
    
    # Save summary info
    summary = {
        "total_files": len(vectors),
        "matrix_shape": list(similarity_matrix.shape),
        "statistics": {
            "mean": float(np.mean(similarity_matrix)),
            "min": float(np.min(similarity_matrix)),
            "max": float(np.max(similarity_matrix)),
            "std": float(np.std(similarity_matrix))
        }
    }
    
    summary_file = Path("data/similarity_matrix_summary.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(f"✅ Summary saved to: {summary_file}")
    
    print(f"\n🎉 Similarity matrix calculation complete!")
    print(f"Files created:")
    print(f"  📊 {matrix_file} - Numpy similarity matrix")
    print(f"  📝 {filenames_file} - Filename mapping")
    print(f"  📈 {summary_file} - Matrix statistics")

if __name__ == "__main__":
    main()