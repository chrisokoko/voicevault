#!/usr/bin/env python3
"""
Visualize Voice Memo Embeddings in 2D

Extract vectors from unified database and create 2D visualization.
"""

import json
import numpy as np
from pathlib import Path
import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from hidden_genius import visualize_embeddings_2d

def main():
    # Load the unified embeddings data
    unified_file = Path("data/semantic_fingerprints_with_embeddings.json")
    
    if not unified_file.exists():
        print(f"Error: Unified embeddings file not found: {unified_file}")
        return
    
    with open(unified_file, 'r', encoding='utf-8') as f:
        unified_data = json.load(f)
    
    # Extract vectors, filenames, and titles
    vectors = []
    filenames = []
    titles = []
    
    for filename, entry in unified_data.items():
        if 'embedding' in entry and 'vector' in entry['embedding']:
            vectors.append(entry['embedding']['vector'])
            filenames.append(filename)
            
            # Get title from semantic fingerprint or use filename
            semantic_fp = entry.get('semantic_fingerprint', {})
            raw_essence = semantic_fp.get('raw_essence', '')
            
            # Create a short title from raw essence or filename
            if raw_essence:
                title = raw_essence[:60] + "..." if len(raw_essence) > 60 else raw_essence
            else:
                title = filename.replace('.m4a', '')[:30]
            
            titles.append(title)
    
    print(f"Found {len(vectors)} embeddings to visualize")
    
    if len(vectors) < 2:
        print("Need at least 2 vectors for visualization")
        return
    
    # Convert to numpy array
    embeddings = np.array(vectors)
    
    print("Creating 2D visualization...")
    
    # Create visualization without cluster labels first
    embeddings_2d, fig = visualize_embeddings_2d(embeddings, titles=titles, labels=None)
    
    # Save the plot
    plot_file = Path("data/embeddings_2d_visualization.png")
    fig.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"✅ 2D visualization saved to: {plot_file}")
    
    # Save the 2D coordinates
    coords_file = Path("data/embeddings_2d_coordinates.json")
    coords_data = {
        "filenames": filenames,
        "titles": titles,
        "coordinates": embeddings_2d.tolist()
    }
    
    with open(coords_file, 'w', encoding='utf-8') as f:
        json.dump(coords_data, f, indent=2, ensure_ascii=False)
    print(f"✅ 2D coordinates saved to: {coords_file}")
    
    print(f"\n🎉 Visualization complete!")
    print(f"Files created:")
    print(f"  📊 {plot_file} - 2D scatter plot visualization")
    print(f"  📝 {coords_file} - 2D coordinates and metadata")
    
    # Show the plot
    try:
        import matplotlib.pyplot as plt
        plt.show()
    except:
        print("Note: Display not available for showing plot interactively")

if __name__ == "__main__":
    main()