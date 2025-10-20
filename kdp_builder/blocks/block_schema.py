"""
Block Library Schema for AI-Powered Layout Generation

A "block" is a reusable layout component that can be:
- Learned from existing PDFs
- Combined by AI to create new pages
- Evolved to create novel layouts
"""

from typing import Dict, List, Any, Optional
from enum import Enum


class BlockCategory(str, Enum):
    """Categories for organizing blocks"""
    HEADER = "header"
    FOOTER = "footer"
    CALENDAR = "calendar"
    HABIT_TRACKER = "habit_tracker"
    WEEKLY_PLANNER = "weekly_planner"
    MONTHLY_PLANNER = "monthly_planner"
    GOAL_TRACKER = "goal_tracker"
    NOTE_SECTION = "note_section"
    CHECKLIST = "checklist"
    TIME_BLOCK = "time_block"
    GRID = "grid"
    LINED = "lined"
    DOT_GRID = "dot_grid"
    DIVIDER = "divider"
    TEXT_BOX = "text_box"
    QUOTE_BOX = "quote_box"


class BlockComplexity(str, Enum):
    """Complexity levels for blocks"""
    SIMPLE = "simple"  # Single element (line, text)
    MODERATE = "moderate"  # Few elements (header with line)
    COMPLEX = "complex"  # Multiple elements (full habit tracker)


# Block Schema Definition
BLOCK_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string", "description": "Unique block identifier"},
        "name": {"type": "string", "description": "Human-readable block name"},
        "category": {
            "type": "string",
            "enum": [cat.value for cat in BlockCategory],
            "description": "Block category for organization"
        },
        "complexity": {
            "type": "string",
            "enum": [comp.value for comp in BlockComplexity],
            "description": "Complexity level"
        },
        "description": {"type": "string", "description": "What this block does"},
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Search tags (e.g., 'daily', 'weekly', 'productivity')"
        },
        "dimensions": {
            "type": "object",
            "properties": {
                "width": {"type": "number", "description": "Width in points"},
                "height": {"type": "number", "description": "Height in points"},
                "flexible_width": {"type": "boolean", "description": "Can width be adjusted?"},
                "flexible_height": {"type": "boolean", "description": "Can height be adjusted?"}
            },
            "required": ["width", "height"]
        },
        "elements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["text", "line", "rectangle", "circle", "checkbox", "grid", "dot_grid"]
                    },
                    "x": {"type": "number", "description": "X position relative to block origin"},
                    "y": {"type": "number", "description": "Y position relative to block origin"},
                    "width": {"type": "number"},
                    "height": {"type": "number"},
                    "content": {"type": "string", "description": "Text content if applicable"},
                    "style": {
                        "type": "object",
                        "properties": {
                            "fontFamily": {"type": "string"},
                            "fontSize": {"type": "number"},
                            "fontWeight": {"type": "string"},
                            "color": {"type": "string"},
                            "lineWeight": {"type": "number"},
                            "fillColor": {"type": "string"}
                        }
                    }
                },
                "required": ["type", "x", "y", "width", "height"]
            }
        },
        "parameters": {
            "type": "object",
            "description": "Configurable parameters (e.g., number of rows, columns)",
            "additionalProperties": True
        },
        "usage_count": {"type": "integer", "description": "How many times this block has been used"},
        "success_rate": {"type": "number", "description": "AI success rate when using this block (0-1)"},
        "created_at": {"type": "string", "format": "date-time"},
        "updated_at": {"type": "string", "format": "date-time"},
        "source": {
            "type": "string",
            "enum": ["manual", "extracted", "ai_generated"],
            "description": "How this block was created"
        }
    },
    "required": ["id", "name", "category", "complexity", "elements"]
}


# Page Composition Schema (how AI combines blocks)
PAGE_COMPOSITION_SCHEMA = {
    "type": "object",
    "properties": {
        "page_number": {"type": "integer"},
        "page_type": {"type": "string", "description": "e.g., 'daily_planner', 'weekly_overview'"},
        "blocks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "block_id": {"type": "string", "description": "Reference to block in library"},
                    "x": {"type": "number", "description": "X position on page"},
                    "y": {"type": "number", "description": "Y position on page"},
                    "width": {"type": "number", "description": "Override block width if flexible"},
                    "height": {"type": "number", "description": "Override block height if flexible"},
                    "parameters": {
                        "type": "object",
                        "description": "Override block parameters",
                        "additionalProperties": True
                    }
                },
                "required": ["block_id", "x", "y"]
            }
        }
    },
    "required": ["page_number", "blocks"]
}


def create_block(
    name: str,
    category: BlockCategory,
    complexity: BlockComplexity,
    elements: List[Dict[str, Any]],
    description: str = "",
    tags: Optional[List[str]] = None,
    dimensions: Optional[Dict[str, Any]] = None,
    parameters: Optional[Dict[str, Any]] = None,
    source: str = "manual"
) -> Dict[str, Any]:
    """
    Helper function to create a block with proper schema.
    
    Args:
        name: Block name
        category: Block category
        complexity: Complexity level
        elements: List of visual elements
        description: What this block does
        tags: Search tags
        dimensions: Width/height info
        parameters: Configurable parameters
        source: How block was created
    
    Returns:
        Block dictionary conforming to BLOCK_SCHEMA
    """
    import uuid
    from datetime import datetime
    
    block_id = str(uuid.uuid4())
    
    return {
        "id": block_id,
        "name": name,
        "category": category.value,
        "complexity": complexity.value,
        "description": description,
        "tags": tags or [],
        "dimensions": dimensions or {"width": 400, "height": 100, "flexible_width": True, "flexible_height": True},
        "elements": elements,
        "parameters": parameters or {},
        "usage_count": 0,
        "success_rate": 1.0,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "source": source
    }
