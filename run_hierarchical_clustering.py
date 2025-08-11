#!/usr/bin/env python3
"""
Run Hierarchical Clustering Analysis on Voice Memo Embeddings

Forces hierarchical clustering with different granularity levels.
"""

import json
import numpy as np
from pathlib import Path
import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from hidden_genius import hierarchical_clustering_analysis

def main():
    # Load the unified embeddings data
    unified_file = Path("data/semantic_fingerprints_with_embeddings.json")
    
    if not unified_file.exists():
        print(f"Error: Unified embeddings file not found: {unified_file}")
        return
    
    print("Loading embeddings...")
    with open(unified_file, 'r', encoding='utf-8') as f:
        unified_data = json.load(f)
    
    # Extract vectors and filenames
    vectors = []
    filenames = []
    titles = []
    
    for filename, entry in unified_data.items():
        if 'embedding' in entry and 'vector' in entry['embedding']:
            vectors.append(entry['embedding']['vector'])
            filenames.append(filename)
            
            # Get title/essence for display
            semantic_fp = entry.get('semantic_fingerprint', {})
            raw_essence = semantic_fp.get('raw_essence', '')
            title = raw_essence[:80] + "..." if len(raw_essence) > 80 else raw_essence
            titles.append(title)
    
    print(f"Found {len(vectors)} embeddings to cluster")
    
    if len(vectors) < 2:
        print("Need at least 2 vectors for clustering")
        return
    
    # Convert to numpy array
    embeddings = np.array(vectors)
    
    print("\n🔬 Running hierarchical clustering analysis...")
    print("Testing multiple distance thresholds for different granularities...")
    
    # Run hierarchical clustering analysis
    result = hierarchical_clustering_analysis(embeddings)
    
    # Display results for different clustering levels
    print(f"\n✅ HIERARCHICAL CLUSTERING RESULTS")
    print(f"="*60)
    
    if result['clustering_results']:
        print(f"Found {len(result['clustering_results'])} different clustering options:")
        
        # Show top 5 clustering options
        for i, clustering in enumerate(result['clustering_results'][:5], 1):
            labels = clustering['labels']
            n_clusters = clustering['n_clusters']
            quality = clustering['quality_score']
            threshold = clustering['params']['distance_threshold']
            
            # Count cluster sizes
            cluster_sizes = []
            for label in range(n_clusters):
                size = np.sum(labels == label)
                cluster_sizes.append(size)
            
            print(f"\n📊 Option {i}: {n_clusters} clusters")
            print(f"  Distance threshold: {threshold:.3f}")
            print(f"  Quality score: {quality:.3f}")
            print(f"  Cluster sizes: {sorted(cluster_sizes, reverse=True)}")
            
            # For the best result, show sample memos
            if i == 1:
                print(f"\n  📝 SAMPLE MEMOS FROM EACH CLUSTER:")
                for cluster_id in range(min(n_clusters, 5)):  # Show max 5 clusters
                    cluster_indices = np.where(labels == cluster_id)[0]
                    print(f"\n  Cluster {cluster_id} ({len(cluster_indices)} memos):")
                    
                    # Show first 2 memos in cluster
                    for idx in cluster_indices[:2]:
                        filename = filenames[idx]
                        title = titles[idx][:60] + "..." if len(titles[idx]) > 60 else titles[idx]
                        print(f"    • {filename}")
                        print(f"      {title}")
        
        # Save best clustering result
        best_result = result['best_result']
        if best_result:
            output_file = Path("data/hierarchical_clustering_results.json")
            output_data = {
                "method": "hierarchical",
                "best_result": {
                    "n_clusters": best_result['n_clusters'],
                    "quality_score": float(best_result['quality_score']),
                    "distance_threshold": float(best_result['params']['distance_threshold']),
                    "labels": best_result['labels'].tolist()
                },
                "all_results": [
                    {
                        "n_clusters": r['n_clusters'],
                        "quality_score": float(r['quality_score']),
                        "distance_threshold": float(r['params']['distance_threshold'])
                    }
                    for r in result['clustering_results']
                ],
                "filenames": filenames,
                "titles": titles
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n✅ Results saved to: {output_file}")
    
    print(f"\n🎉 Hierarchical clustering analysis complete!")
    print(f"The analysis tested multiple granularity levels.")
    print(f"Choose the number of clusters that best matches your needs.")

if __name__ == "__main__":
    main()