"""
ChromaDB service for storing and retrieving design patterns

This service manages the vector database that stores learned patterns
from professional Etsy PDFs.
"""

import chromadb
from typing import List, Dict, Any, Optional
import json
import uuid
from pathlib import Path

class PatternDatabase:
    """Manages design patterns in ChromaDB"""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        Initialize ChromaDB client and collection.
        
        Args:
            persist_directory: Directory to persist the database
        """
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client with new API
        self.client = chromadb.PersistentClient(path=str(self.persist_directory))
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="design_patterns",
            metadata={
                "description": "KDP design patterns learned from professional Etsy PDFs",
                "hnsw:space": "cosine"  # Use cosine similarity
            }
        )
        
        print(f"✅ ChromaDB initialized at {self.persist_directory}")
        print(f"📊 Current patterns in database: {self.collection.count()}")
    
    def add_pattern(
        self,
        pattern_id: Optional[str],
        description: str,
        metadata: Dict[str, Any],
        embedding: Optional[List[float]] = None
    ) -> str:
        """
        Add a design pattern to the database.
        
        Args:
            pattern_id: Unique pattern ID (auto-generated if None)
            description: Text description of the pattern
            metadata: Pattern metadata (measurements, colors, etc.)
            embedding: Optional custom embedding vector
            
        Returns:
            Pattern ID
        """
        if pattern_id is None:
            pattern_id = f"pattern_{uuid.uuid4().hex[:8]}"
        
        # Add to collection
        self.collection.add(
            ids=[pattern_id],
            documents=[description],
            metadatas=[metadata],
            embeddings=[embedding] if embedding else None
        )
        
        print(f"✅ Added pattern: {pattern_id}")
        return pattern_id
    
    def search_patterns(
        self,
        query: str,
        n_results: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar patterns using semantic search.
        
        Args:
            query: Search query (e.g., "habit tracker layout")
            n_results: Number of results to return
            filter_metadata: Optional metadata filters
            
        Returns:
            List of matching patterns with scores
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=filter_metadata
        )
        
        # Format results
        patterns = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for i in range(len(results["ids"][0])):
                patterns.append({
                    "id": results["ids"][0][i],
                    "description": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if "distances" in results else None
                })
        
        return patterns
    
    def get_pattern(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific pattern by ID.
        
        Args:
            pattern_id: Pattern ID
            
        Returns:
            Pattern data or None if not found
        """
        results = self.collection.get(ids=[pattern_id])
        
        if results["ids"]:
            return {
                "id": results["ids"][0],
                "description": results["documents"][0],
                "metadata": results["metadatas"][0]
            }
        return None
    
    def get_all_patterns(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all stored patterns.
        
        Args:
            limit: Maximum number of patterns to return
            
        Returns:
            List of all patterns
        """
        results = self.collection.get(limit=limit)
        
        patterns = []
        for i in range(len(results["ids"])):
            patterns.append({
                "id": results["ids"][i],
                "description": results["documents"][i],
                "metadata": results["metadatas"][i]
            })
        
        return patterns
    
    def delete_pattern(self, pattern_id: str) -> bool:
        """
        Delete a pattern from the database.
        
        Args:
            pattern_id: Pattern ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        try:
            self.collection.delete(ids=[pattern_id])
            print(f"🗑️  Deleted pattern: {pattern_id}")
            return True
        except Exception as e:
            print(f"❌ Error deleting pattern {pattern_id}: {e}")
            return False
    
    def update_pattern(
        self,
        pattern_id: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update an existing pattern.
        
        Args:
            pattern_id: Pattern ID to update
            description: New description (optional)
            metadata: New metadata (optional)
            
        Returns:
            True if updated, False if not found
        """
        try:
            update_data = {}
            if description:
                update_data["documents"] = [description]
            if metadata:
                update_data["metadatas"] = [metadata]
            
            if update_data:
                self.collection.update(
                    ids=[pattern_id],
                    **update_data
                )
                print(f"✏️  Updated pattern: {pattern_id}")
                return True
            return False
        except Exception as e:
            print(f"❌ Error updating pattern {pattern_id}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        return {
            "total_patterns": self.collection.count(),
            "collection_name": self.collection.name,
            "persist_directory": str(self.persist_directory)
        }

# Global instance
pattern_db = PatternDatabase()
