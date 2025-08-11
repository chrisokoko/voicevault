#!/usr/bin/env python3
"""
Run Automatic Clustering on Voice Memo Embeddings

Uses the auto_cluster_embeddings function to find optimal clusters.
"""

import json
import numpy as np
from pathlib import Path
import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from hidden_genius import auto_cluster_embeddings

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
    
    print("\n🔬 Running automatic clustering analysis...")
    print("Testing both hierarchical and DBSCAN methods...")
    
    # Run automatic clustering
    result = auto_cluster_embeddings(embeddings)
    
    # Display results
    print(f"\n✅ CLUSTERING COMPLETE")
    print(f"="*60)
    print(f"Best Method: {result['method']}")
    print(f"Number of Clusters: {result['n_clusters']}")
    print(f"Quality Score: {result['quality_score']:.3f}")
    print(f"Parameters: {result['params']}")
    
    # Count cluster sizes
    labels = result['labels']
    unique_labels = np.unique(labels)
    
    print(f"\n📊 CLUSTER DISTRIBUTION:")
    cluster_info = []
    for label in unique_labels:
        if label == -1:
            count = np.sum(labels == label)
            print(f"  Outliers: {count} memos")
        else:
            count = np.sum(labels == label)
            print(f"  Cluster {label}: {count} memos")
            cluster_info.append({
                'cluster_id': int(label),
                'size': int(count),
                'member_indices': np.where(labels == label)[0].tolist()
            })
    
    # Show sample memos from each cluster
    print(f"\n📝 SAMPLE MEMOS FROM EACH CLUSTER:")
    for label in unique_labels:
        if label == -1:
            continue  # Skip outliers for samples
        
        cluster_indices = np.where(labels == label)[0]
        print(f"\nCluster {label} ({len(cluster_indices)} memos):")
        
        # Show first 3 memos in cluster
        for idx in cluster_indices[:3]:
            filename = filenames[idx]
            title = titles[idx]
            print(f"  • {filename}")
            print(f"    {title}")
    
    # Save clustering results
    output_file = Path("data/clustering_results.json")
    output_data = {
        "method": result['method'],
        "n_clusters": result['n_clusters'],
        "quality_score": float(result['quality_score']),
        "parameters": result['params'],
        "labels": result['labels'].tolist(),
        "filenames": filenames,
        "titles": titles,
        "cluster_info": cluster_info,
        "all_methods_tested": len(result.get('all_results', [])),
        "summary": {
            "total_memos": len(labels),
            "n_clusters": result['n_clusters'],
            "n_outliers": int(np.sum(labels == -1)),
            "largest_cluster_size": max([c['size'] for c in cluster_info]) if cluster_info else 0,
            "smallest_cluster_size": min([c['size'] for c in cluster_info]) if cluster_info else 0
        }
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Results saved to: {output_file}")
    
    # Show alternative clustering options
    if 'all_results' in result and len(result['all_results']) > 1:
        print(f"\n🔍 ALTERNATIVE CLUSTERING OPTIONS TESTED:")
        for i, alt in enumerate(result['all_results'][:5], 1):
            if alt['quality_score'] == result['quality_score']:
                continue  # Skip the winner we already showed
            print(f"  {i}. {alt['method']} - {alt['n_clusters']} clusters, score: {alt['quality_score']:.3f}")
    
    print(f"\n🎉 Clustering analysis complete!")
    print(f"Next steps:")
    print(f"  1. Review cluster assignments in {output_file}")
    print(f"  2. Visualize clusters with UMAP")
    print(f"  3. Analyze themes within each cluster")

if __name__ == "__main__":
    main()