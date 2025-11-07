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

        try:
            self.collection = self.client.get_or_create_collection(
                name="design_patterns",
                metadata={
                    "description": "KDP design patterns learned from professional Etsy PDFs",
                    "hnsw:space": "cosine"
                }
            )
        except Exception:
            import shutil, time
            backup = self.persist_directory.with_name(self.persist_directory.name + f"_backup_{int(time.time())}")
            try:
                if self.persist_directory.exists():
                    shutil.move(str(self.persist_directory), str(backup))
            except Exception:
                pass
            self.persist_directory.mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(path=str(self.persist_directory))
            self.collection = self.client.get_or_create_collection(
                name="design_patterns",
                metadata={
                    "description": "KDP design patterns learned from professional Etsy PDFs",
                    "hnsw:space": "cosine"
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
        
        # Sanitize metadata: flatten nested dicts/lists into primitives
        def _sanitize(prefix: str, value: Any, out: Dict[str, Any]):
            from collections.abc import Mapping, Sequence
            if value is None or isinstance(value, (str, int, float, bool)):
                out[prefix] = value
                return
            if isinstance(value, Mapping):
                for k, v in value.items():
                    key = f"{prefix}_{k}" if prefix else str(k)
                    _sanitize(key, v, out)
                return
            if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
                # If list of primitives and short, join; otherwise store count
                if all(isinstance(x, (str, int, float, bool)) or x is None for x in value) and len(value) <= 20:
                    out[prefix] = ",".join(str(x) for x in value)
                else:
                    out[f"{prefix}_count"] = len(value)
                return
            # Fallback: stringify
            out[prefix] = str(value)

        flat_meta: Dict[str, Any] = {}
        _sanitize("", metadata, flat_meta)
        # Remove empty root key if present
        if "" in flat_meta:
            val = flat_meta.pop("")
            if isinstance(val, (str, int, float, bool)):
                flat_meta["metadata"] = val

        # Add to collection
        self.collection.add(
            ids=[pattern_id],
            documents=[description],
            metadatas=[flat_meta],
            embeddings=[embedding] if embedding else None
        )
        
        print(f"✅ Added pattern: {pattern_id}")
        return pattern_id
    
    def add_extracted_pattern(
        self,
        pattern_id: Optional[str],
        description: str,
        metadata: Dict[str, Any],
        blocks: List[Dict[str, Any]],
        elements: List[Dict[str, Any]],
        style_tokens: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None
    ) -> str:
        """
        Add a pattern with extracted blocks, elements, and style tokens.

        Args:
            pattern_id: Unique pattern ID (auto-generated if None)
            description: Text description of the pattern
            metadata: Pattern metadata (measurements, colors, etc.)
            blocks: List of extracted blocks
            elements: List of raw elements
            style_tokens: Optional style tokens summary
            embedding: Optional custom embedding vector

        Returns:
            Pattern ID
        """
        if pattern_id is None:
            pattern_id = f"pattern_{uuid.uuid4().hex[:8]}"

        # Store blocks/elements JSON on disk under a new 'patterns' directory
        patterns_dir = Path("./data/patterns")
        patterns_dir.mkdir(parents=True, exist_ok=True)
        pattern_dir = patterns_dir / pattern_id
        pattern_dir.mkdir(parents=True, exist_ok=True)
        (pattern_dir / "blocks.json").write_text(json.dumps(blocks, indent=2))
        (pattern_dir / "elements.json").write_text(json.dumps(elements, indent=2))
        if style_tokens:
            (pattern_dir / "style_tokens.json").write_text(json.dumps(style_tokens, indent=2))

        # Sanitize metadata for ChromaDB (flatten nested dicts/lists)
        def _sanitize(prefix: str, value: Any, out: Dict[str, Any]):
            from collections.abc import Mapping, Sequence
            if value is None or isinstance(value, (str, int, float, bool)):
                out[prefix] = value
                return
            if isinstance(value, Mapping):
                for k, v in value.items():
                    key = f"{prefix}_{k}" if prefix else str(k)
                    _sanitize(key, v, out)
                return
            if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
                if all(isinstance(x, (str, int, float, bool)) or x is None for x in value) and len(value) <= 20:
                    out[prefix] = ",".join(str(x) for x in value)
                else:
                    out[f"{prefix}_count"] = len(value)
                return
            out[prefix] = str(value)

        flat_meta: Dict[str, Any] = {}
        _sanitize("", metadata, flat_meta)
        if "" in flat_meta:
            val = flat_meta.pop("")
            if isinstance(val, (str, int, float, bool)):
                flat_meta["metadata"] = val

        # Add to ChromaDB
        self.collection.add(
            ids=[pattern_id],
            documents=[description],
            metadatas=[flat_meta],
            embeddings=[embedding] if embedding else None
        )

        print(f"✅ Added extracted pattern: {pattern_id}")
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
    
    def get_pattern_with_extracted(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a pattern including its stored blocks, elements, and style tokens.

        Args:
            pattern_id: Pattern ID

        Returns:
            Pattern data with extracted payloads or None if not found
        """
        vec = self.get_pattern(pattern_id)
        if not vec:
            return None
        pattern_dir = Path("./data/patterns") / pattern_id
        extracted_dir = pattern_dir / "extracted"
        result = {"id": vec["id"], "description": vec["description"], "metadata": vec["metadata"]}
        try:
            # Prefer files in extracted/ if present
            blocks_path = (extracted_dir / "blocks.json") if (extracted_dir / "blocks.json").exists() else (pattern_dir / "blocks.json")
            elements_path = (extracted_dir / "elements.json") if (extracted_dir / "elements.json").exists() else (pattern_dir / "elements.json")
            style_path = (extracted_dir / "style_tokens.json") if (extracted_dir / "style_tokens.json").exists() else (pattern_dir / "style_tokens.json")

            if blocks_path.exists():
                result["blocks"] = json.loads(blocks_path.read_text())
            if elements_path.exists():
                result["elements"] = json.loads(elements_path.read_text())
            if style_path.exists():
                result["style_tokens"] = json.loads(style_path.read_text())
        except Exception as e:
            print(f"⚠️  Failed to load extracted files for {pattern_id}: {e}")
        return result
    
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
            # Also delete stored JSON files
            pattern_dir = Path("./data/patterns") / pattern_id
            if pattern_dir.exists():
                import shutil
                shutil.rmtree(pattern_dir)
            print(f"🗑️  Deleted pattern: {pattern_id}")
            return True
        except Exception as e:
            print(f"❌ Error deleting pattern {pattern_id}: {e}")
            return False
    
    def list_patterns_with_extracted(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        List patterns including a summary of extracted blocks and elements.

        Args:
            limit: Maximum number of patterns to return

        Returns:
            List of patterns with extracted summaries
        """
        vecs = self.get_all_patterns(limit)
        results = []
        for v in vecs:
            summary = {"id": v["id"], "description": v["description"], "metadata": v["metadata"]}
            pattern_dir = Path("./data/patterns") / v["id"]
            extracted_dir = pattern_dir / "extracted"
            try:
                blocks_path = (extracted_dir / "blocks.json") if (extracted_dir / "blocks.json").exists() else (pattern_dir / "blocks.json")
                elements_path = (extracted_dir / "elements.json") if (extracted_dir / "elements.json").exists() else (pattern_dir / "elements.json")
                if blocks_path.exists():
                    blocks = json.loads(blocks_path.read_text())["blocks"]
                    summary["blocks_summary"] = {
                        "count": len(blocks),
                        "types": list({b.get("type") for b in blocks})
                    }
                if elements_path.exists():
                    elements = json.loads(elements_path.read_text())["elements"]
                    summary["elements_summary"] = {
                        "count": len(elements),
                        "types": list({e.get("type") for e in elements})
                    }
                if (extracted_dir / "style_tokens.json").exists() or (pattern_dir / "style_tokens.json").exists():
                    summary["has_style_tokens"] = True
            except Exception as e:
                print(f"⚠️  Failed to summarize extracted files for {v['id']}: {e}")
            results.append(summary)
        return results
    
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
