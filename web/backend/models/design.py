"""
Design data models for KDP Visual Editor

Defines the structure of designs, pages, and elements.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class ElementType(str, Enum):
    """Types of design elements"""
    TEXT = "text"
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    LINE = "line"
    IMAGE = "image"
    CHECKBOX = "checkbox"

class DesignElement(BaseModel):
    """Single design element (text, shape, image, etc.)"""
    id: str = Field(..., description="Unique element ID")
    type: ElementType = Field(..., description="Element type")
    x: float = Field(..., description="X position in points")
    y: float = Field(..., description="Y position in points")
    width: float = Field(..., description="Width in points")
    height: float = Field(..., description="Height in points")
    rotation: float = Field(default=0.0, description="Rotation in degrees")
    z_index: int = Field(default=0, description="Layer order")
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Element-specific properties (font, color, etc.)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "elem_123",
                "type": "text",
                "x": 100,
                "y": 500,
                "width": 200,
                "height": 50,
                "rotation": 0,
                "z_index": 1,
                "properties": {
                    "text": "HABIT TRACKER",
                    "fontSize": 48,
                    "fontFamily": "Helvetica-Bold",
                    "color": "#2C2C2C",
                    "align": "center"
                }
            }
        }

class DesignPage(BaseModel):
    """Single page in design"""
    page_number: int = Field(..., description="Page number (1-indexed)")
    elements: List[DesignElement] = Field(
        default_factory=list,
        description="Elements on this page"
    )
    background_color: str = Field(
        default="#FFFFFF",
        description="Page background color (hex)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "page_number": 1,
                "elements": [],
                "background_color": "#FFFFFF"
            }
        }

class Design(BaseModel):
    """Complete design document"""
    id: Optional[str] = Field(None, description="Design ID")
    name: str = Field(..., description="Design name")
    page_width: float = Field(default=432.0, description="Page width in points (6 inches)")
    page_height: float = Field(default=648.0, description="Page height in points (9 inches)")
    pages: List[DesignPage] = Field(
        default_factory=list,
        description="Pages in the design"
    )
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (tags, description, etc.)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "design_123",
                "name": "My Habit Tracker",
                "page_width": 432.0,
                "page_height": 648.0,
                "pages": [
                    {
                        "page_number": 1,
                        "elements": [],
                        "background_color": "#FFFFFF"
                    }
                ],
                "metadata": {
                    "tags": ["habit", "tracker"],
                    "description": "Monthly habit tracker"
                }
            }
        }

class DesignCreate(BaseModel):
    """Create new design request"""
    name: str = Field(..., description="Design name")
    page_width: float = Field(default=432.0, description="Page width in points")
    page_height: float = Field(default=648.0, description="Page height in points")
    num_pages: int = Field(default=1, description="Number of pages to create")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Daily Planner",
                "page_width": 432.0,
                "page_height": 648.0,
                "num_pages": 30
            }
        }

class DesignUpdate(BaseModel):
    """Update existing design request"""
    name: Optional[str] = Field(None, description="New design name")
    pages: Optional[List[DesignPage]] = Field(None, description="Updated pages")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")

class DesignResponse(BaseModel):
    """Design response"""
    success: bool
    message: str
    design: Optional[Design] = None
    
class DesignListResponse(BaseModel):
    """List of designs response"""
    success: bool
    designs: List[Design]
    total: int
