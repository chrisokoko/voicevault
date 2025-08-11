#!/usr/bin/env python3
"""
Visualize Voice Memo Embeddings using UMAP

Extract vectors from unified database and create 2D visualization using UMAP.
UMAP often provides better clustering visualization than t-SNE.
"""

import json
import numpy as np
from pathlib import Path
import sys
import os
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def main():
    # Load the unified embeddings data
    unified_file = Path("data/semantic_fingerprints_with_embeddings.json")
    
    if not unified_file.exists():
        print(f"Error: Unified embeddings file not found: {unified_file}")
        return
    
    print("Loading embeddings...")
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
            
            # Get short title from filename
            title = filename.replace('.m4a', '')[:30]
            titles.append(title)
    
    print(f"Found {len(vectors)} embeddings to visualize")
    
    if len(vectors) < 2:
        print("Need at least 2 vectors for visualization")
        return
    
    # Convert to numpy array
    embeddings = np.array(vectors)
    
    print("Performing UMAP dimensionality reduction...")
    print("(This may take a moment for first run)")
    
    # Perform UMAP reduction
    try:
        import umap
    except ImportError:
        print("UMAP not installed. Installing now...")
        os.system("pip3 install umap-learn")
        import umap
    
    # Configure UMAP
    reducer = umap.UMAP(
        n_neighbors=15,      # Balance between local and global structure
        min_dist=0.1,        # Minimum distance between points in 2D
        n_components=2,      # 2D output
        metric='cosine',     # Use cosine similarity (good for embeddings)
        random_state=42      # For reproducibility
    )
    
    # Fit and transform
    embeddings_2d = reducer.fit_transform(embeddings)
    
    print("Creating visualization...")
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Create scatter plot
    scatter = ax.scatter(
        embeddings_2d[:, 0], 
        embeddings_2d[:, 1],
        alpha=0.7,
        s=100,
        c=range(len(embeddings_2d)),  # Color by index for now
        cmap='viridis'
    )
    
    # Add labels for some points (to avoid overcrowding)
    # Show every 5th label to reduce clutter
    for i in range(0, len(titles), 5):
        ax.annotate(
            titles[i], 
            (embeddings_2d[i, 0], embeddings_2d[i, 1]),
            fontsize=8,
            alpha=0.7,
            xytext=(5, 5),
            textcoords='offset points'
        )
    
    ax.set_title('Voice Memo Embeddings - UMAP Visualization', fontsize=16)
    ax.set_xlabel('UMAP Dimension 1', fontsize=12)
    ax.set_ylabel('UMAP Dimension 2', fontsize=12)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save the plot
    plot_file = Path("data/embeddings_umap_visualization.png")
    fig.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"✅ UMAP visualization saved to: {plot_file}")
    
    # Save the 2D coordinates
    coords_file = Path("data/embeddings_umap_coordinates.json")
    coords_data = {
        "method": "UMAP",
        "parameters": {
            "n_neighbors": 15,
            "min_dist": 0.1,
            "metric": "cosine"
        },
        "filenames": filenames,
        "titles": titles,
        "coordinates": embeddings_2d.tolist(),
        "statistics": {
            "x_min": float(embeddings_2d[:, 0].min()),
            "x_max": float(embeddings_2d[:, 0].max()),
            "y_min": float(embeddings_2d[:, 1].min()),
            "y_max": float(embeddings_2d[:, 1].max()),
            "x_mean": float(embeddings_2d[:, 0].mean()),
            "y_mean": float(embeddings_2d[:, 1].mean())
        }
    }
    
    with open(coords_file, 'w', encoding='utf-8') as f:
        json.dump(coords_data, f, indent=2, ensure_ascii=False)
    print(f"✅ UMAP coordinates saved to: {coords_file}")
    
    # Close the figure
    plt.close(fig)
    
    print(f"\n🎉 UMAP visualization complete!")
    print(f"Files created:")
    print(f"  📊 {plot_file} - UMAP 2D scatter plot")
    print(f"  📝 {coords_file} - 2D coordinates and metadata")
    print(f"\nUMAP Parameters used:")
    print(f"  n_neighbors: 15 (balances local vs global structure)")
    print(f"  min_dist: 0.1 (controls clumping)")
    print(f"  metric: cosine (good for embeddings)")

if __name__ == "__main__":
    main()