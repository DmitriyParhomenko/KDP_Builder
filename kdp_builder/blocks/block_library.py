"""
Block Library Manager

Manages a library of reusable layout blocks that can be:
- Stored and retrieved
- Searched by category, tags, complexity
- Learned from PDFs
- Combined by AI
"""

import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

from kdp_builder.blocks.block_schema import BlockCategory, BlockComplexity, BLOCK_SCHEMA


class BlockLibrary:
    """Manages a library of reusable layout blocks"""
    
    def __init__(self, library_path: str = "kdp_builder/blocks/library"):
        """
        Initialize block library.
        
        Args:
            library_path: Path to store block JSON files
        """
        self.library_path = Path(library_path)
        self.library_path.mkdir(parents=True, exist_ok=True)
        self.blocks: Dict[str, Dict[str, Any]] = {}
        self.load_all_blocks()
    
    def add_block(self, block: Dict[str, Any]) -> str:
        """
        Add a block to the library.
        
        Args:
            block: Block dictionary conforming to BLOCK_SCHEMA
        
        Returns:
            Block ID
        """
        block_id = block["id"]
        self.blocks[block_id] = block
        self._save_block(block)
        return block_id
    
    def get_block(self, block_id: str) -> Optional[Dict[str, Any]]:
        """Get a block by ID"""
        return self.blocks.get(block_id)
    
    def search_blocks(
        self,
        category: Optional[BlockCategory] = None,
        tags: Optional[List[str]] = None,
        complexity: Optional[BlockComplexity] = None,
        name_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search blocks by various criteria.
        
        Args:
            category: Filter by category
            tags: Filter by tags (any match)
            complexity: Filter by complexity
            name_query: Search in name/description
        
        Returns:
            List of matching blocks
        """
        results = []
        
        for block in self.blocks.values():
            # Category filter
            if category and block.get("category") != category.value:
                continue
            
            # Complexity filter
            if complexity and block.get("complexity") != complexity.value:
                continue
            
            # Tags filter (any tag matches)
            if tags:
                block_tags = set(block.get("tags", []))
                if not any(tag in block_tags for tag in tags):
                    continue
            
            # Name/description search
            if name_query:
                query_lower = name_query.lower()
                name_match = query_lower in block.get("name", "").lower()
                desc_match = query_lower in block.get("description", "").lower()
                if not (name_match or desc_match):
                    continue
            
            results.append(block)
        
        return results
    
    def get_all_blocks(self) -> List[Dict[str, Any]]:
        """Get all blocks in the library"""
        return list(self.blocks.values())
    
    def get_blocks_by_category(self, category: BlockCategory) -> List[Dict[str, Any]]:
        """Get all blocks in a specific category"""
        return self.search_blocks(category=category)
    
    def update_block_stats(self, block_id: str, success: bool = True):
        """
        Update block usage statistics.
        
        Args:
            block_id: Block to update
            success: Whether the block was used successfully
        """
        block = self.blocks.get(block_id)
        if not block:
            return
        
        # Update usage count
        block["usage_count"] = block.get("usage_count", 0) + 1
        
        # Update success rate (exponential moving average)
        current_rate = block.get("success_rate", 1.0)
        alpha = 0.1  # Learning rate
        new_rate = alpha * (1.0 if success else 0.0) + (1 - alpha) * current_rate
        block["success_rate"] = new_rate
        
        # Update timestamp
        block["updated_at"] = datetime.utcnow().isoformat()
        
        self._save_block(block)
    
    def get_popular_blocks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most frequently used blocks"""
        sorted_blocks = sorted(
            self.blocks.values(),
            key=lambda b: b.get("usage_count", 0),
            reverse=True
        )
        return sorted_blocks[:limit]
    
    def get_high_quality_blocks(self, min_success_rate: float = 0.8) -> List[Dict[str, Any]]:
        """Get blocks with high success rates"""
        return [
            block for block in self.blocks.values()
            if block.get("success_rate", 0) >= min_success_rate
        ]
    
    def load_all_blocks(self):
        """Load all blocks from disk"""
        if not self.library_path.exists():
            return
        
        for block_file in self.library_path.glob("*.json"):
            try:
                with open(block_file, "r") as f:
                    block = json.load(f)
                    self.blocks[block["id"]] = block
            except Exception as e:
                print(f"Warning: Failed to load block {block_file}: {e}")
    
    def _save_block(self, block: Dict[str, Any]):
        """Save a block to disk"""
        block_id = block["id"]
        block_file = self.library_path / f"{block_id}.json"
        
        with open(block_file, "w") as f:
            json.dump(block, f, indent=2)
    
    def export_library(self, output_path: str):
        """Export entire library to a single JSON file"""
        with open(output_path, "w") as f:
            json.dump(list(self.blocks.values()), f, indent=2)
    
    def import_library(self, input_path: str, merge: bool = True):
        """
        Import blocks from a JSON file.
        
        Args:
            input_path: Path to JSON file with blocks
            merge: If True, merge with existing blocks; if False, replace
        """
        with open(input_path, "r") as f:
            imported_blocks = json.load(f)
        
        if not merge:
            self.blocks = {}
        
        for block in imported_blocks:
            self.add_block(block)
    
    def get_library_stats(self) -> Dict[str, Any]:
        """Get statistics about the library"""
        total_blocks = len(self.blocks)
        
        # Count by category
        category_counts = {}
        for block in self.blocks.values():
            cat = block.get("category", "unknown")
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Count by complexity
        complexity_counts = {}
        for block in self.blocks.values():
            comp = block.get("complexity", "unknown")
            complexity_counts[comp] = complexity_counts.get(comp, 0) + 1
        
        # Average success rate
        success_rates = [b.get("success_rate", 0) for b in self.blocks.values()]
        avg_success = sum(success_rates) / len(success_rates) if success_rates else 0
        
        return {
            "total_blocks": total_blocks,
            "categories": category_counts,
            "complexity": complexity_counts,
            "average_success_rate": avg_success,
            "total_usage": sum(b.get("usage_count", 0) for b in self.blocks.values())
        }
