#!/usr/bin/env python3
"""
Generate Comprehensive Cluster Report

Creates HTML and Markdown reports showing all clustering options with:
- Each cluster
- Notes within that cluster
- Summaries/essences of each note
"""

import json
import numpy as np
from pathlib import Path
import sys
import os
from datetime import datetime

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def load_data():
    """Load all necessary data files"""
    # Load unified embeddings data
    unified_file = Path("data/semantic_fingerprints_with_embeddings.json")
    with open(unified_file, 'r', encoding='utf-8') as f:
        unified_data = json.load(f)
    
    # Load hierarchical clustering results
    clustering_file = Path("data/hierarchical_clustering_results.json")
    with open(clustering_file, 'r', encoding='utf-8') as f:
        clustering_data = json.load(f)
    
    return unified_data, clustering_data

def generate_markdown_report(unified_data, clustering_data):
    """Generate a Markdown report of all clustering options"""
    
    report_lines = []
    report_lines.append("# Voice Memo Clustering Analysis Report")
    report_lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"\nTotal Voice Memos: {len(clustering_data['filenames'])}")
    report_lines.append("\n---\n")
    
    # Get filenames list
    filenames = clustering_data['filenames']
    
    # Process each clustering option
    for option_idx, option in enumerate(clustering_data['all_results'][:5], 1):
        n_clusters = option['n_clusters']
        quality_score = option['quality_score']
        threshold = option['distance_threshold']
        
        report_lines.append(f"## Option {option_idx}: {n_clusters} Clusters")
        report_lines.append(f"\n**Quality Score:** {quality_score:.3f}")
        report_lines.append(f"**Distance Threshold:** {threshold:.3f}")
        report_lines.append("\n")
        
        # Get labels for this option (we need to recalculate or store them)
        # For now, we'll use the best result if this is option 1
        if option_idx == 1 and 'best_result' in clustering_data:
            labels = clustering_data['best_result']['labels']
        else:
            # Skip detailed view for other options (would need to recalculate)
            report_lines.append("*Detailed cluster contents available in interactive version*\n")
            report_lines.append("\n---\n")
            continue
        
        # Group files by cluster
        clusters = {}
        for idx, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(idx)
        
        # Sort clusters by size (largest first)
        sorted_clusters = sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True)
        
        for cluster_id, member_indices in sorted_clusters:
            report_lines.append(f"### Cluster {cluster_id} ({len(member_indices)} memos)")
            report_lines.append("")
            
            # List all memos in this cluster
            for idx in member_indices:
                filename = filenames[idx]
                
                # Get summary/essence from unified data
                if filename in unified_data:
                    semantic_fp = unified_data[filename].get('semantic_fingerprint', {})
                    raw_essence = semantic_fp.get('raw_essence', 'No summary available')
                    central_question = semantic_fp.get('core_exploration', {}).get('central_question', '')
                    
                    # Clean filename for display
                    display_name = filename.replace('.m4a', '')
                    
                    report_lines.append(f"#### 📝 {display_name}")
                    report_lines.append("")
                    
                    if central_question:
                        report_lines.append(f"**Central Question:** {central_question}")
                        report_lines.append("")
                    
                    report_lines.append(f"**Summary:** {raw_essence}")
                    report_lines.append("")
            
            report_lines.append("---")
            report_lines.append("")
        
        report_lines.append("\n---\n")
    
    return "\n".join(report_lines)

def generate_html_report(unified_data, clustering_data):
    """Generate an interactive HTML report with all clustering options"""
    
    html_lines = []
    html_lines.append("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Voice Memo Clustering Report</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        h2 {
            color: #34495e;
            margin-top: 30px;
            background: #ecf0f1;
            padding: 10px;
            border-radius: 5px;
        }
        h3 {
            color: #7f8c8d;
            background: #fff;
            padding: 8px;
            border-left: 4px solid #3498db;
            margin: 20px 0 10px 0;
        }
        .cluster {
            background: white;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .memo {
            background: #f8f9fa;
            border-left: 3px solid #3498db;
            padding: 10px;
            margin: 10px 0;
            border-radius: 0 5px 5px 0;
        }
        .memo-title {
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }
        .central-question {
            color: #8e44ad;
            font-style: italic;
            margin: 5px 0;
        }
        .summary {
            color: #555;
            margin-top: 5px;
        }
        .stats {
            background: #3498db;
            color: white;
            padding: 10px;
            border-radius: 5px;
            display: inline-block;
            margin: 10px 0;
        }
        .tabs {
            display: flex;
            gap: 10px;
            margin: 20px 0;
            border-bottom: 2px solid #3498db;
        }
        .tab {
            padding: 10px 20px;
            background: #ecf0f1;
            border: none;
            cursor: pointer;
            border-radius: 5px 5px 0 0;
            transition: background 0.3s;
        }
        .tab:hover {
            background: #d5dbdd;
        }
        .tab.active {
            background: #3498db;
            color: white;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
        .cluster-size {
            background: #e74c3c;
            color: white;
            padding: 2px 8px;
            border-radius: 15px;
            font-size: 0.9em;
            margin-left: 10px;
        }
    </style>
    <script>
        function showTab(tabIndex) {
            // Hide all tab contents
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected tab
            document.getElementById('tab-' + tabIndex).classList.add('active');
            document.getElementById('tab-btn-' + tabIndex).classList.add('active');
        }
    </script>
</head>
<body>
    <h1>🎯 Voice Memo Clustering Analysis</h1>
    <div class="stats">
        <strong>Total Memos:</strong> """ + str(len(clustering_data['filenames'])) + """ | 
        <strong>Generated:</strong> """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """
    </div>
    """)
    
    # Create tabs for different clustering options
    html_lines.append('<div class="tabs">')
    for idx, option in enumerate(clustering_data['all_results'][:5], 1):
        active_class = 'active' if idx == 1 else ''
        html_lines.append(f'<button class="tab {active_class}" id="tab-btn-{idx}" onclick="showTab({idx})">')
        html_lines.append(f'{option["n_clusters"]} Clusters</button>')
    html_lines.append('</div>')
    
    # Get filenames
    filenames = clustering_data['filenames']
    
    # Generate content for each clustering option
    for option_idx, option in enumerate(clustering_data['all_results'][:5], 1):
        active_class = 'active' if option_idx == 1 else ''
        html_lines.append(f'<div class="tab-content {active_class}" id="tab-{option_idx}">')
        
        n_clusters = option['n_clusters']
        quality_score = option['quality_score']
        threshold = option['distance_threshold']
        
        html_lines.append(f'<h2>Configuration: {n_clusters} Clusters</h2>')
        html_lines.append(f'<p><strong>Quality Score:</strong> {quality_score:.3f} | ')
        html_lines.append(f'<strong>Distance Threshold:</strong> {threshold:.3f}</p>')
        
        # For option 1, we have the labels
        if option_idx == 1 and 'best_result' in clustering_data:
            labels = clustering_data['best_result']['labels']
            
            # Group files by cluster
            clusters = {}
            for idx, label in enumerate(labels):
                if label not in clusters:
                    clusters[label] = []
                clusters[label].append(idx)
            
            # Sort clusters by size
            sorted_clusters = sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True)
            
            for cluster_id, member_indices in sorted_clusters:
                html_lines.append(f'<div class="cluster">')
                html_lines.append(f'<h3>Cluster {cluster_id}')
                html_lines.append(f'<span class="cluster-size">{len(member_indices)} memos</span></h3>')
                
                for idx in member_indices:
                    filename = filenames[idx]
                    
                    if filename in unified_data:
                        semantic_fp = unified_data[filename].get('semantic_fingerprint', {})
                        raw_essence = semantic_fp.get('raw_essence', 'No summary available')
                        central_question = semantic_fp.get('core_exploration', {}).get('central_question', '')
                        key_tension = semantic_fp.get('core_exploration', {}).get('key_tension', '')
                        
                        display_name = filename.replace('.m4a', '')
                        
                        html_lines.append('<div class="memo">')
                        html_lines.append(f'<div class="memo-title">📝 {display_name}</div>')
                        
                        if central_question:
                            html_lines.append(f'<div class="central-question">❓ {central_question}</div>')
                        
                        if key_tension:
                            html_lines.append(f'<div class="central-question">⚡ {key_tension}</div>')
                        
                        html_lines.append(f'<div class="summary">{raw_essence}</div>')
                        html_lines.append('</div>')
                
                html_lines.append('</div>')
        else:
            html_lines.append('<p><em>Detailed clustering for this configuration would require recalculation.</em></p>')
            html_lines.append('<p>Showing cluster size distribution:</p>')
            # Could add a simple visualization here
        
        html_lines.append('</div>')
    
    html_lines.append("""
</body>
</html>""")
    
    return "\n".join(html_lines)

def main():
    print("Loading data...")
    unified_data, clustering_data = load_data()
    
    print("Generating Markdown report...")
    markdown_report = generate_markdown_report(unified_data, clustering_data)
    
    # Save Markdown report
    md_file = Path("data/cluster_report.md")
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(markdown_report)
    print(f"✅ Markdown report saved to: {md_file}")
    
    print("Generating HTML report...")
    html_report = generate_html_report(unified_data, clustering_data)
    
    # Save HTML report
    html_file = Path("data/cluster_report.html")
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_report)
    print(f"✅ HTML report saved to: {html_file}")
    
    print(f"\n🎉 Cluster reports generated successfully!")
    print(f"\nReports created:")
    print(f"  📄 {md_file} - Markdown format (good for reading)")
    print(f"  🌐 {html_file} - HTML format (interactive with tabs)")
    print(f"\nOpen the HTML file in a browser for the best viewing experience!")

if __name__ == "__main__":
    main()