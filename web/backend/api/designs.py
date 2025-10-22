"""
Design API endpoints

CRUD operations for managing planner designs.
"""

from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
import uuid
import json
from pathlib import Path

from web.backend.models.design import (
    Design,
    DesignCreate,
    DesignUpdate,
    DesignResponse,
    DesignListResponse,
    DesignPage
)

router = APIRouter()

# Simple file-based storage for now (will upgrade to DB later)
DESIGNS_DIR = Path("./designs_storage")
DESIGNS_DIR.mkdir(parents=True, exist_ok=True)

def _save_design(design: Design) -> None:
    """Save design to file"""
    file_path = DESIGNS_DIR / f"{design.id}.json"
    with open(file_path, "w") as f:
        json.dump(design.dict(), f, indent=2, default=str)

def _load_design(design_id: str) -> Design:
    """Load design from file"""
    file_path = DESIGNS_DIR / f"{design_id}.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Design not found")
    
    with open(file_path, "r") as f:
        data = json.load(f)
    return Design(**data)

def _list_all_designs() -> List[Design]:
    """List all designs"""
    designs = []
    for file_path in DESIGNS_DIR.glob("*.json"):
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            designs.append(Design(**data))
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
    return designs

@router.post("/", response_model=DesignResponse)
async def create_design(design_data: DesignCreate):
    """
    Create a new design.
    
    Creates a new planner design with the specified dimensions and pages.
    """
    # Generate unique ID
    design_id = f"design_{uuid.uuid4().hex[:12]}"
    
    # Create pages
    pages = [
        DesignPage(page_number=i+1, elements=[], background_color="#FFFFFF")
        for i in range(design_data.num_pages)
    ]
    
    # Create design
    design = Design(
        id=design_id,
        name=design_data.name,
        page_width=design_data.page_width,
        page_height=design_data.page_height,
        pages=pages,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        metadata={}
    )
    
    # Save to storage
    _save_design(design)
    
    return DesignResponse(
        success=True,
        message="Design created successfully",
        design=design
    )

@router.get("/", response_model=DesignListResponse)
async def list_designs():
    """
    List all designs.
    
    Returns a list of all saved designs.
    """
    designs = _list_all_designs()
    
    return DesignListResponse(
        success=True,
        designs=designs,
        total=len(designs)
    )

@router.get("/{design_id}", response_model=DesignResponse)
async def get_design(design_id: str):
    """
    Get a specific design by ID.
    
    Args:
        design_id: Design ID
    """
    try:
        design = _load_design(design_id)
        return DesignResponse(
            success=True,
            message="Design retrieved successfully",
            design=design
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{design_id}", response_model=DesignResponse)
async def update_design(design_id: str, update_data: DesignUpdate):
    """
    Update an existing design.
    
    Args:
        design_id: Design ID
        update_data: Fields to update
    """
    try:
        # Load existing design
        design = _load_design(design_id)
        
        # Update fields
        if update_data.name is not None:
            design.name = update_data.name
        if update_data.pages is not None:
            design.pages = update_data.pages
        if update_data.metadata is not None:
            design.metadata.update(update_data.metadata)
        
        design.updated_at = datetime.now()
        
        # Save updated design
        _save_design(design)
        
        return DesignResponse(
            success=True,
            message="Design updated successfully",
            design=design
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{design_id}")
async def delete_design(design_id: str):
    """
    Delete a design.
    
    Args:
        design_id: Design ID
    """
    file_path = DESIGNS_DIR / f"{design_id}.json"
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Design not found")
    
    try:
        file_path.unlink()
        return {
            "success": True,
            "message": "Design deleted successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
