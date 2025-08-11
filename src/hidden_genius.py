"""
Hidden Genius - Automatic clustering system for voice note embeddings
Production-ready clustering with automatic parameter optimization
"""

import numpy as np
import logging
import json
from typing import List, Dict, Optional, Union, Tuple
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import pdist, squareform
from sklearn.cluster import DBSCAN
from sklearn.metrics import silhouette_score
from sklearn.metrics.pairwise import cosine_distances
import warnings

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


def generate_semantic_fingerprint(insight: str, claude_service) -> Dict:
    """Generate semantic fingerprint for an insight using Claude AI."""
    from config.prompts import PromptTemplates
    
    if not insight or not insight.strip():
        logger.error("No insight provided for semantic fingerprinting")
        return {}
    
    try:
        prompt = PromptTemplates.SEMANTIC_FINGERPRINTING_PROMPT.substitute(insight=insight.strip())
        
        # Call Claude API using the same pattern as other methods
        response_chunks = []
        with claude_service.client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            for text in stream.text_stream:
                response_chunks.append(text)
        
        content = ''.join(response_chunks).strip()
        
        # Extract and parse JSON from response
        if '{' in content:
            json_str = content[content.find('{'):content.rfind('}')+1]
            return json.loads(json_str)
        return {}
        
    except Exception as e:
        logger.error(f"Semantic fingerprinting failed: {e}")
        return {}


def _hierarchical_clustering(embeddings: Union[List[List[float]], np.ndarray], 
                           distance_thresholds: Optional[List[float]] = None) -> List[Dict]:
    """
    Internal function: Run hierarchical clustering with multiple distance thresholds.
    
    Args:
        embeddings: List/array of embedding vectors
        distance_thresholds: List of distances to test (use sensible defaults if None)
    
    Returns:
        List of clustering results, each containing:
        - 'labels': cluster assignment array
        - 'method': 'hierarchical'
        - 'params': {'distance_threshold': value}
        - 'n_clusters': number of clusters found
    """
    # Convert to numpy array if needed
    if isinstance(embeddings, list):
        embeddings = np.array(embeddings)
    
    n_samples = embeddings.shape[0]
    
    # Handle edge cases
    if n_samples < 2:
        return [{
            'labels': np.zeros(n_samples, dtype=int),
            'method': 'hierarchical',
            'params': {'distance_threshold': 0},
            'n_clusters': 1 if n_samples == 1 else 0
        }]
    
    # Calculate cosine distance matrix
    distance_matrix = cosine_distances(embeddings)
    condensed_distances = squareform(distance_matrix)
    
    # Perform hierarchical clustering
    linkage_matrix = linkage(condensed_distances, method='ward')
    
    # Default distance thresholds if not provided
    if distance_thresholds is None:
        # Use percentiles of the linkage heights for automatic thresholds
        heights = linkage_matrix[:, 2]
        distance_thresholds = [
            np.percentile(heights, p) for p in [10, 20, 30, 40, 50, 60, 70, 80]
        ]
    
    results = []
    for threshold in distance_thresholds:
        try:
            # Get cluster assignments
            labels = fcluster(linkage_matrix, threshold, criterion='distance') - 1  # Convert to 0-indexed
            n_clusters = len(np.unique(labels))
            
            # Skip if we get degenerate clustering
            if n_clusters == 0 or n_clusters == n_samples:
                continue
            
            results.append({
                'labels': labels,
                'method': 'hierarchical',
                'params': {'distance_threshold': float(threshold)},
                'n_clusters': n_clusters
            })
        except Exception as e:
            logger.warning(f"Hierarchical clustering failed for threshold {threshold}: {str(e)}")
            continue
    
    return results


def _dbscan_clustering(embeddings: Union[List[List[float]], np.ndarray],
                      eps_values: Optional[List[float]] = None,
                      min_samples_values: Optional[List[int]] = None) -> List[Dict]:
    """
    Internal function: Run DBSCAN clustering with multiple parameter combinations.
    
    Args:
        embeddings: List/array of embedding vectors  
        eps_values: List of eps values to test (use sensible defaults if None)
        min_samples_values: List of min_samples values to test (use sensible defaults if None)
    
    Returns:
        List of clustering results, each containing:
        - 'labels': cluster assignment array  
        - 'method': 'dbscan'
        - 'params': {'eps': value, 'min_samples': value}
        - 'n_clusters': number of clusters found
        - 'n_outliers': number of outlier points (-1 labels)
    """
    # Convert to numpy array if needed
    if isinstance(embeddings, list):
        embeddings = np.array(embeddings)
    
    n_samples = embeddings.shape[0]
    
    # Handle edge cases
    if n_samples < 2:
        return [{
            'labels': np.zeros(n_samples, dtype=int),
            'method': 'dbscan',
            'params': {'eps': 0.5, 'min_samples': 1},
            'n_clusters': 1 if n_samples == 1 else 0,
            'n_outliers': 0
        }]
    
    # Calculate cosine distance matrix
    distance_matrix = cosine_distances(embeddings)
    
    # Default parameters if not provided
    if eps_values is None:
        # Use percentiles of pairwise distances
        flat_distances = distance_matrix[np.triu_indices_from(distance_matrix, k=1)]
        eps_values = [
            np.percentile(flat_distances, p) for p in [5, 10, 15, 20, 30, 40, 50]
        ]
    
    if min_samples_values is None:
        # Adaptive min_samples based on dataset size
        if n_samples < 50:
            min_samples_values = [2, 3]
        elif n_samples < 500:
            min_samples_values = [3, 5, 10]
        else:
            min_samples_values = [5, 10, 20]
        
        # Ensure min_samples doesn't exceed 10% of dataset
        min_samples_values = [m for m in min_samples_values if m <= max(2, int(0.1 * n_samples))]
    
    results = []
    for eps in eps_values:
        for min_samples in min_samples_values:
            try:
                # Run DBSCAN
                clusterer = DBSCAN(eps=eps, min_samples=min_samples, metric='precomputed')
                labels = clusterer.fit_predict(distance_matrix)
                
                # Calculate metrics
                unique_labels = np.unique(labels)
                n_clusters = len(unique_labels[unique_labels != -1])
                n_outliers = np.sum(labels == -1)
                
                # Skip if we get degenerate clustering
                if n_clusters == 0:
                    continue
                
                results.append({
                    'labels': labels,
                    'method': 'dbscan',
                    'params': {'eps': float(eps), 'min_samples': int(min_samples)},
                    'n_clusters': n_clusters,
                    'n_outliers': int(n_outliers)
                })
            except Exception as e:
                logger.warning(f"DBSCAN failed for eps={eps}, min_samples={min_samples}: {str(e)}")
                continue
    
    return results


def _evaluate_clustering_quality(labels: np.ndarray, embeddings: np.ndarray) -> float:
    """
    Internal function: Evaluate clustering quality using multiple metrics.
    
    Args:
        labels: Cluster assignment array (may contain -1 for outliers)
        embeddings: Original embedding vectors
    
    Returns:
        float: Quality score (higher = better clustering)
        
    Should consider:
    - Silhouette score (cluster separation)
    - Cluster size distribution (avoid too many tiny clusters)
    - Avoid degenerate cases (0 clusters, all points in one cluster)
    - Handle outliers appropriately
    """
    n_samples = len(labels)
    unique_labels = np.unique(labels)
    n_clusters = len(unique_labels[unique_labels != -1])
    
    # Handle degenerate cases
    if n_clusters == 0:
        return -1.0
    
    if n_clusters == 1:
        # Single cluster - check if it's reasonable
        n_outliers = np.sum(labels == -1)
        if n_outliers == 0:
            return -0.5  # All points in one cluster is bad
        else:
            # Some outliers with one main cluster might be okay
            outlier_ratio = n_outliers / n_samples
            if outlier_ratio > 0.5:
                return -0.5  # Too many outliers
            return 0.1  # Low but not terrible score
    
    # Calculate silhouette score
    try:
        # For silhouette calculation, we need at least 2 non-outlier clusters
        non_outlier_mask = labels != -1
        if np.sum(non_outlier_mask) < 2:
            silhouette = 0.0
        else:
            silhouette = silhouette_score(embeddings[non_outlier_mask], 
                                        labels[non_outlier_mask], 
                                        metric='cosine')
    except:
        silhouette = 0.0
    
    # Calculate cluster size distribution
    cluster_sizes = []
    for label in unique_labels:
        if label != -1:  # Skip outliers
            cluster_sizes.append(np.sum(labels == label))
    
    if not cluster_sizes:
        return -1.0
    
    # Penalize very uneven cluster sizes
    cluster_sizes = np.array(cluster_sizes)
    size_std = np.std(cluster_sizes) / np.mean(cluster_sizes) if len(cluster_sizes) > 1 else 0
    size_penalty = min(size_std / 2, 0.3)  # Cap penalty at 0.3
    
    # Penalize too many tiny clusters
    tiny_clusters = np.sum(cluster_sizes < max(3, n_samples * 0.02))  # Clusters < 2% of data
    tiny_cluster_ratio = tiny_clusters / n_clusters
    tiny_penalty = tiny_cluster_ratio * 0.2
    
    # Handle outliers
    n_outliers = np.sum(labels == -1)
    outlier_ratio = n_outliers / n_samples
    
    # Penalize excessive outliers, but allow some
    if outlier_ratio > 0.5:
        outlier_penalty = 0.5
    elif outlier_ratio > 0.3:
        outlier_penalty = outlier_ratio - 0.2
    else:
        outlier_penalty = outlier_ratio * 0.3  # Small penalty for reasonable outliers
    
    # Combine metrics
    # Silhouette is primary metric (range -1 to 1), penalties reduce it
    quality_score = silhouette - size_penalty - tiny_penalty - outlier_penalty
    
    # Bonus for reasonable number of clusters (between 2 and sqrt(n))
    ideal_clusters = max(2, min(int(np.sqrt(n_samples)), 20))
    if 2 <= n_clusters <= ideal_clusters:
        quality_score += 0.1
    
    return float(quality_score)


def auto_cluster_embeddings(embeddings: Union[List[List[float]], np.ndarray]) -> Dict:
    """
    Public function: Automatically find optimal clustering for embeddings.
    
    Args:
        embeddings: List or array of embedding vectors
        
    Returns:
        dict containing:
        - 'labels': Best cluster assignments
        - 'method': Which algorithm was selected ('hierarchical' or 'dbscan')
        - 'params': Parameters used for best clustering
        - 'n_clusters': Number of clusters found
        - 'quality_score': Quality score of selected clustering
        - 'all_results': List of all clustering attempts with their scores
    """
    # Convert to numpy array if needed
    if isinstance(embeddings, list):
        embeddings = np.array(embeddings)
    
    n_samples = embeddings.shape[0]
    logger.info(f"Auto-clustering {n_samples} embeddings")
    
    # Handle edge cases
    if n_samples == 0:
        return {
            'labels': np.array([]),
            'method': 'none',
            'params': {},
            'n_clusters': 0,
            'quality_score': 0.0,
            'all_results': []
        }
    
    if n_samples == 1:
        return {
            'labels': np.array([0]),
            'method': 'single',
            'params': {},
            'n_clusters': 1,
            'quality_score': 1.0,
            'all_results': []
        }
    
    all_results = []
    
    # Try hierarchical clustering
    try:
        hier_results = _hierarchical_clustering(embeddings)
        for result in hier_results:
            score = _evaluate_clustering_quality(result['labels'], embeddings)
            all_results.append({
                **result,
                'quality_score': score
            })
    except Exception as e:
        logger.error(f"Hierarchical clustering failed: {str(e)}")
    
    # Try DBSCAN clustering
    try:
        dbscan_results = _dbscan_clustering(embeddings)
        for result in dbscan_results:
            score = _evaluate_clustering_quality(result['labels'], embeddings)
            all_results.append({
                **result,
                'quality_score': score
            })
    except Exception as e:
        logger.error(f"DBSCAN clustering failed: {str(e)}")
    
    # Find best result
    if not all_results:
        # Fallback: create single cluster
        logger.warning("All clustering methods failed, using fallback")
        return {
            'labels': np.zeros(n_samples, dtype=int),
            'method': 'fallback',
            'params': {},
            'n_clusters': 1,
            'quality_score': 0.0,
            'all_results': []
        }
    
    # Sort by quality score
    all_results.sort(key=lambda x: x['quality_score'], reverse=True)
    best_result = all_results[0]
    
    logger.info(f"Best clustering: {best_result['method']} with {best_result['n_clusters']} clusters, "
                f"score: {best_result['quality_score']:.3f}")
    
    return {
        'labels': best_result['labels'],
        'method': best_result['method'],
        'params': best_result['params'],
        'n_clusters': best_result['n_clusters'],
        'quality_score': best_result['quality_score'],
        'all_results': all_results
    }


# Additional visualization functions for the original request

def visualize_embeddings_2d(embeddings: Union[List[List[float]], np.ndarray], 
                           titles: Optional[List[str]] = None,
                           labels: Optional[np.ndarray] = None) -> Tuple[np.ndarray, object]:
    """
    Reduce high-dimensional embeddings to 2D and create a visual plot.
    
    Args:
        embeddings: List or numpy array of embeddings (n_samples, n_features)
        titles: Optional list of titles for reference
        labels: Optional cluster labels for coloring
        
    Returns:
        embeddings_2d: 2D coordinates array
        fig: matplotlib figure object
    """
    import matplotlib.pyplot as plt
    from sklearn.manifold import TSNE
    
    # Convert to numpy array if needed
    if isinstance(embeddings, list):
        embeddings = np.array(embeddings)
    
    # Apply t-SNE for dimensionality reduction
    tsne = TSNE(n_components=2, random_state=42, perplexity=min(30, len(embeddings)-1))
    embeddings_2d = tsne.fit_transform(embeddings)
    
    # Create visualization
    fig, ax = plt.subplots(figsize=(10, 8))
    
    if labels is not None:
        # Color by cluster
        unique_labels = np.unique(labels)
        colors = plt.cm.Set3(np.linspace(0, 1, len(unique_labels)))
        
        for i, label in enumerate(unique_labels):
            mask = labels == label
            ax.scatter(embeddings_2d[mask, 0], embeddings_2d[mask, 1], 
                      c=[colors[i]], label=f'Cluster {label}' if label != -1 else 'Outliers',
                      alpha=0.6, s=50)
    else:
        ax.scatter(embeddings_2d[:, 0], embeddings_2d[:, 1], alpha=0.6, s=50)
    
    # Add titles as annotations if provided
    if titles is not None and len(titles) < 50:  # Only annotate if not too many points
        for i, title in enumerate(titles):
            ax.annotate(str(i), (embeddings_2d[i, 0], embeddings_2d[i, 1]), 
                       fontsize=8, alpha=0.7)
    
    ax.set_xlabel('t-SNE Dimension 1')
    ax.set_ylabel('t-SNE Dimension 2')
    ax.set_title('Voice Note Embeddings Visualization')
    
    if labels is not None:
        ax.legend()
    
    plt.tight_layout()
    
    return embeddings_2d, fig


def hierarchical_clustering_analysis(embeddings: Union[List[List[float]], np.ndarray]) -> Dict:
    """
    Perform hierarchical clustering with analysis of different granularity options.
    
    Args:
        embeddings: List or numpy array of embeddings
        
    Returns:
        results: Dictionary containing clustering results at different granularity levels
    """
    import matplotlib.pyplot as plt
    from scipy.cluster.hierarchy import dendrogram
    
    # Get multiple clustering results
    clustering_results = _hierarchical_clustering(embeddings)
    
    # Evaluate each result
    for result in clustering_results:
        result['quality_score'] = _evaluate_clustering_quality(result['labels'], np.array(embeddings))
    
    # Sort by quality
    clustering_results.sort(key=lambda x: x['quality_score'], reverse=True)
    
    # Create dendrogram if we have enough samples
    fig = None
    if len(embeddings) > 2:
        distance_matrix = cosine_distances(embeddings)
        condensed_distances = squareform(distance_matrix)
        linkage_matrix = linkage(condensed_distances, method='ward')
        
        fig, ax = plt.subplots(figsize=(12, 8))
        dendrogram(linkage_matrix, ax=ax, truncate_mode='level', p=6)
        ax.set_title('Hierarchical Clustering Dendrogram')
        ax.set_xlabel('Sample Index')
        ax.set_ylabel('Distance')
        plt.tight_layout()
    
    return {
        'clustering_results': clustering_results,
        'best_result': clustering_results[0] if clustering_results else None,
        'dendrogram_figure': fig
    }


def dbscan_clustering_analysis(embeddings: Union[List[List[float]], np.ndarray]) -> Dict:
    """
    Perform DBSCAN clustering with exploration of different parameter configurations.
    
    Args:
        embeddings: List or numpy array of embeddings
        
    Returns:
        results: Dictionary containing clustering results for different parameter settings
    """
    import matplotlib.pyplot as plt
    
    # Get multiple clustering results
    clustering_results = _dbscan_clustering(embeddings)
    
    # Evaluate each result
    for result in clustering_results:
        result['quality_score'] = _evaluate_clustering_quality(result['labels'], np.array(embeddings))
    
    # Sort by quality
    clustering_results.sort(key=lambda x: x['quality_score'], reverse=True)
    
    # Create parameter exploration visualization
    fig = None
    if clustering_results and len(embeddings) > 2:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Extract data for plotting
        eps_vals = [r['params']['eps'] for r in clustering_results]
        n_clusters_vals = [r['n_clusters'] for r in clustering_results]
        quality_scores = [r['quality_score'] for r in clustering_results]
        
        # Plot number of clusters vs eps
        ax1.scatter(eps_vals, n_clusters_vals, alpha=0.6)
        ax1.set_xlabel('Epsilon')
        ax1.set_ylabel('Number of Clusters')
        ax1.set_title('Clusters vs Epsilon')
        ax1.grid(True, alpha=0.3)
        
        # Plot quality score vs eps
        ax2.scatter(eps_vals, quality_scores, alpha=0.6, color='green')
        ax2.set_xlabel('Epsilon')
        ax2.set_ylabel('Quality Score')
        ax2.set_title('Clustering Quality vs Epsilon')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
    
    return {
        'clustering_results': clustering_results,
        'best_result': clustering_results[0] if clustering_results else None,
        'parameter_figure': fig
    }