"""
Integration test for semantic fingerprinting functionality
Tests generate_semantic_fingerprint function with real Claude API
"""

import os
import sys
import json
import pytest
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../src'))

from claude_service import ClaudeService
from hidden_genius import generate_semantic_fingerprint
from config.config import CLAUDE_API_KEY

# Test data
SAMPLE_INSIGHT = """
I've been thinking about how relationships work, and I realized something important today. 
The key tension I keep running into is wanting deep connection but also needing personal space. 
What I figured out is that vulnerability isn't about removing boundaries - it's about being 
honest about what those boundaries are and why they exist. This feels like a breakthrough 
because I used to think I had to choose between closeness and independence. But actually, 
clear boundaries might be what makes real intimacy possible.
"""

@pytest.fixture
def claude_service():
    """Create Claude service instance for testing"""
    if not CLAUDE_API_KEY:
        pytest.skip("CLAUDE_API_KEY not available for integration test")
    return ClaudeService()

def test_generate_semantic_fingerprint(claude_service):
    """Test semantic fingerprinting with sample insight"""
    fingerprint = generate_semantic_fingerprint(SAMPLE_INSIGHT, claude_service)
    
    # Save result for manual review
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(__file__).parent.parent.parent / "fixtures" / "data" / "semantic_fingerprints"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    result_file = output_dir / f"test_result_{timestamp}.json"
    with open(result_file, 'w') as f:
        json.dump({
            "input_insight": SAMPLE_INSIGHT,
            "output_fingerprint": fingerprint,
            "timestamp": timestamp
        }, f, indent=2)
    
    print(f"Result saved to: {result_file}")
    
    # Basic assertions
    assert isinstance(fingerprint, dict), "Should return a dictionary"
    assert fingerprint != {}, "Should not return empty dictionary"
    
    # Validate required keys exist
    required_keys = ['core_exploration', 'conceptual_dna', 'pattern_signature', 
                    'bridge_potential', 'genius_indicators', 'raw_essence', 'embedding_text']
    for key in required_keys:
        assert key in fingerprint, f"Missing required key: {key}"
    
    print("✓ Semantic fingerprint generated successfully")
    print(f"Raw essence: {fingerprint.get('raw_essence', 'N/A')}")

def test_empty_insight_handling(claude_service):
    """Test handling of empty insights"""
    assert generate_semantic_fingerprint("", claude_service) == {}
    assert generate_semantic_fingerprint("   ", claude_service) == {}
    assert generate_semantic_fingerprint(None, claude_service) == {}