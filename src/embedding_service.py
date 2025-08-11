"""
Embedding Service

Handles vector embedding generation for semantic fingerprints using OpenAI's API.
Creates and manages unified storage of semantic fingerprints with their embeddings.
"""

import os
import sys
import json
import logging
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import numpy as np
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from config.config import OPENAI_API_KEY
except ImportError:
    # Fallback to environment variable
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Service for generating and managing vector embeddings from semantic fingerprints"""
    
    def __init__(self, api_key: str = None, model: str = "text-embedding-3-small"):
        """
        Initialize the embedding service
        
        Args:
            api_key: OpenAI API key (uses OPENAI_API_KEY from config if not provided)
            model: OpenAI embedding model to use (default: text-embedding-3-small)
        """
        api_key = api_key or OPENAI_API_KEY
        if not api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY in your config.")
        
        self.client = OpenAI(api_key=api_key)
        self.model = model
        
        # Set embedding dimensions based on model
        if "text-embedding-3-small" in model:
            self.embedding_dimension = 1536
        elif "text-embedding-3-large" in model:
            self.embedding_dimension = 3072
        elif "text-embedding-ada-002" in model:
            self.embedding_dimension = 1536
        else:
            self.embedding_dimension = 1536  # Default fallback
        
        # File paths
        self.unified_file = Path("data/semantic_fingerprints_with_embeddings.json")
        self.semantic_fingerprints_dir = Path("data/semantic_fingerprints")
        
        # Ensure data directory exists
        self.unified_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load or initialize unified data
        self.unified_data = self._load_unified_data()
        
        # Rate limiting
        self.requests_per_minute = 3000  # OpenAI default
        self.tokens_per_minute = 1000000  # OpenAI default
        self.last_request_time = 0
        self.min_request_interval = 60 / self.requests_per_minute
    
    def _load_unified_data(self) -> Dict:
        """Load the unified semantic fingerprints + embeddings file"""
        if self.unified_file.exists():
            try:
                with open(self.unified_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading unified data: {e}")
                return {}
        return {}
    
    def _save_unified_data(self) -> None:
        """Save the unified data to file"""
        try:
            with open(self.unified_file, 'w', encoding='utf-8') as f:
                json.dump(self.unified_data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved unified data with {len(self.unified_data)} entries")
        except Exception as e:
            logger.error(f"Error saving unified data: {e}")
            raise
    
    def extract_embedding_text(self, semantic_fingerprint: Dict) -> str:
        """
        Extract and combine specified fields from semantic fingerprint for embedding
        
        Fields used:
        - central_question
        - key_tension  
        - breakthrough_moment
        - edge_of_understanding
        - conceptual_dna (array combined)
        - raw_essence
        
        Args:
            semantic_fingerprint: The semantic fingerprint data
            
        Returns:
            Combined text for embedding generation
        """
        parts = []
        
        # Extract core_exploration fields
        core_exploration = semantic_fingerprint.get('core_exploration', {})
        if core_exploration.get('central_question'):
            parts.append(f"Central Question: {core_exploration['central_question']}")
        if core_exploration.get('key_tension'):
            parts.append(f"Key Tension: {core_exploration['key_tension']}")
        if core_exploration.get('breakthrough_moment'):
            parts.append(f"Breakthrough: {core_exploration['breakthrough_moment']}")
        if core_exploration.get('edge_of_understanding'):
            parts.append(f"Edge: {core_exploration['edge_of_understanding']}")
        
        # Extract conceptual_dna
        conceptual_dna = semantic_fingerprint.get('conceptual_dna', [])
        if conceptual_dna:
            dna_text = " ".join(conceptual_dna)
            parts.append(f"Conceptual DNA: {dna_text}")
        
        # Extract raw_essence
        raw_essence = semantic_fingerprint.get('raw_essence', '')
        if raw_essence:
            parts.append(f"Raw Essence: {raw_essence}")
        
        # Combine all parts
        combined_text = " | ".join(parts)
        
        return combined_text

    def generate_embedding(self, text: str, retries: int = 3) -> Optional[List[float]]:
        """
        Generate embedding for the given text using OpenAI API
        
        Args:
            text: Text to embed
            retries: Number of retry attempts for API calls
            
        Returns:
            Embedding vector as list of floats, or None if failed
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return None
        
        # Clean text (OpenAI has a max of 8191 tokens)
        text = text.strip()
        if len(text) > 30000:  # Rough estimate to stay under token limit
            logger.warning(f"Text too long ({len(text)} chars), truncating to 30000")
            text = text[:30000]
            
        for attempt in range(retries):
            try:
                # Rate limiting
                current_time = time.time()
                time_since_last_request = current_time - self.last_request_time
                if time_since_last_request < self.min_request_interval:
                    sleep_time = self.min_request_interval - time_since_last_request
                    time.sleep(sleep_time)
                
                response = self.client.embeddings.create(
                    input=text,
                    model=self.model
                )
                
                self.last_request_time = time.time()
                embedding = response.data[0].embedding
                logger.debug(f"Generated embedding with {len(embedding)} dimensions")
                return embedding
                
            except Exception as e:
                logger.error(f"Error generating embedding (attempt {attempt + 1}): {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    
        return None
    
    def process_semantic_fingerprint(self, audio_filename: str, semantic_fingerprint: Dict) -> bool:
        """
        Process a semantic fingerprint and generate its embedding
        
        Args:
            audio_filename: Original audio filename (e.g., "example.m4a")
            semantic_fingerprint: The semantic fingerprint data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if already processed
            if audio_filename in self.unified_data:
                existing_entry = self.unified_data[audio_filename]
                if 'embedding' in existing_entry and existing_entry['embedding'].get('vector'):
                    logger.info(f"Embedding already exists for {audio_filename}")
                    return True
            
            # Extract text for embedding
            embedding_text = self.extract_embedding_text(semantic_fingerprint)
            if not embedding_text:
                logger.warning(f"No text extracted for embedding from {audio_filename}")
                return False
            
            # Generate embedding
            logger.info(f"Generating embedding for {audio_filename}")
            vector = self.generate_embedding(embedding_text)
            if not vector:
                logger.error(f"Failed to generate embedding for {audio_filename}")
                return False
            
            # Create unified entry
            self.unified_data[audio_filename] = {
                "semantic_fingerprint": semantic_fingerprint,
                "embedding": {
                    "vector": vector,
                    "model": self.model,
                    "created_at": datetime.now().isoformat(),
                    "embedding_text": embedding_text
                },
                "metadata": {
                    "processed_at": datetime.now().isoformat(),
                    "audio_filename": audio_filename,
                    "fingerprint_source": f"data/semantic_fingerprints/{Path(audio_filename).stem}.json"
                }
            }
            
            # Save to file
            self._save_unified_data()
            logger.info(f"✅ Successfully processed embedding for {audio_filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing semantic fingerprint for {audio_filename}: {e}")
            return False
    
    def batch_process_existing_fingerprints(self, max_files: Optional[int] = None) -> Dict[str, Any]:
        """
        Process all existing semantic fingerprint files to generate embeddings
        
        Args:
            max_files: Maximum number of files to process (for testing)
            
        Returns:
            Processing statistics
        """
        stats = {
            "total_files": 0,
            "processed": 0,
            "skipped": 0,
            "failed": 0,
            "start_time": datetime.now()
        }
        
        if not self.semantic_fingerprints_dir.exists():
            logger.error(f"Semantic fingerprints directory not found: {self.semantic_fingerprints_dir}")
            return stats
        
        # Get all JSON files
        fingerprint_files = list(self.semantic_fingerprints_dir.glob("*.json"))
        stats["total_files"] = len(fingerprint_files)
        
        if max_files:
            fingerprint_files = fingerprint_files[:max_files]
            logger.info(f"Limited processing to {max_files} files")
        
        logger.info(f"🚀 Starting batch processing of {len(fingerprint_files)} semantic fingerprints")
        
        for i, fingerprint_file in enumerate(fingerprint_files, 1):
            # Determine audio filename from JSON filename
            audio_filename = fingerprint_file.stem + ".m4a"
            
            logger.info(f"📝 Processing {i}/{len(fingerprint_files)}: {audio_filename}")
            
            try:
                # Load semantic fingerprint
                with open(fingerprint_file, 'r', encoding='utf-8') as f:
                    semantic_fingerprint = json.load(f)
                
                # Check if already processed
                if audio_filename in self.unified_data:
                    existing_entry = self.unified_data[audio_filename]
                    if 'embedding' in existing_entry and existing_entry['embedding'].get('vector'):
                        logger.info(f"⏭️ Skipping {audio_filename} - already has embedding")
                        stats["skipped"] += 1
                        continue
                
                # Process the fingerprint
                success = self.process_semantic_fingerprint(audio_filename, semantic_fingerprint)
                if success:
                    stats["processed"] += 1
                    logger.info(f"✅ Successfully processed {audio_filename}")
                else:
                    stats["failed"] += 1
                    logger.error(f"❌ Failed to process {audio_filename}")
                
                # Small delay to be nice to the API
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"❌ Error processing {fingerprint_file}: {e}")
                stats["failed"] += 1
        
        stats["end_time"] = datetime.now()
        stats["duration"] = (stats["end_time"] - stats["start_time"]).total_seconds()
        
        # Print summary
        logger.info(f"\n🎉 BATCH PROCESSING COMPLETE")
        logger.info(f"📊 Total files: {stats['total_files']}")
        logger.info(f"✅ Processed: {stats['processed']}")
        logger.info(f"⏭️ Skipped: {stats['skipped']}")
        logger.info(f"❌ Failed: {stats['failed']}")
        logger.info(f"⏱️ Duration: {stats['duration']:.1f}s")
        
        return stats
    
    def get_embedding(self, audio_filename: str) -> Optional[List[float]]:
        """Get embedding vector for a specific audio file"""
        entry = self.unified_data.get(audio_filename)
        if entry and 'embedding' in entry:
            return entry['embedding'].get('vector')
        return None
    
    def get_semantic_fingerprint(self, audio_filename: str) -> Optional[Dict]:
        """Get semantic fingerprint for a specific audio file"""
        entry = self.unified_data.get(audio_filename)
        if entry:
            return entry.get('semantic_fingerprint')
        return None
    
    def list_processed_files(self) -> List[str]:
        """Get list of all processed audio filenames"""
        return list(self.unified_data.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the embedding database"""
        total_entries = len(self.unified_data)
        entries_with_embeddings = sum(1 for entry in self.unified_data.values() 
                                    if 'embedding' in entry and entry['embedding'].get('vector'))
        
        return {
            "total_entries": total_entries,
            "entries_with_embeddings": entries_with_embeddings,
            "embedding_model": self.model,
            "unified_file_path": str(self.unified_file),
            "file_size_mb": self.unified_file.stat().st_size / (1024 * 1024) if self.unified_file.exists() else 0
        }
    
    def calculate_similarity_matrix(self, vectors: List[List[float]]) -> np.ndarray:
        """
        Calculate cosine similarity matrix for an array of vectors
        
        Args:
            vectors: List of embedding vectors
            
        Returns:
            Similarity matrix where matrix[i][j] is similarity between vectors[i] and vectors[j]
        """
        vectors_array = np.array(vectors)
        return cosine_similarity(vectors_array)


def main():
    """CLI interface for embedding service"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate embeddings for semantic fingerprints")
    parser.add_argument("--batch", action="store_true", help="Process all existing semantic fingerprints")
    parser.add_argument("--max-files", type=int, help="Maximum number of files to process")
    parser.add_argument("--model", default="text-embedding-3-small", help="OpenAI embedding model to use")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize service
    service = EmbeddingService(model=args.model)
    
    if args.stats:
        stats = service.get_stats()
        print("\n📊 EMBEDDING DATABASE STATS")
        print(f"Total entries: {stats['total_entries']}")
        print(f"Entries with embeddings: {stats['entries_with_embeddings']}")
        print(f"Model: {stats['embedding_model']}")
        print(f"File size: {stats['file_size_mb']:.2f} MB")
        return
    
    if args.batch:
        service.batch_process_existing_fingerprints(max_files=args.max_files)
    else:
        print("Use --batch to process existing fingerprints or --stats to show database info")


if __name__ == "__main__":
    main()