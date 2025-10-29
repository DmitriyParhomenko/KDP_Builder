"""
AI API endpoints

AI-powered layout suggestions and pattern learning.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from web.backend.services.ai_service import ai_service
from web.backend.services.pattern_db import pattern_db
from kdp_builder.analysis.pdf_analyzer import PDFDesignAnalyzer

router = APIRouter()

class LayoutRequest(BaseModel):
    """Request for AI layout generation"""
    prompt: str
    page_width: float = 432.0
    page_height: float = 648.0

class LayoutResponse(BaseModel):
    """Response with generated layout"""
    success: bool
    elements: List[Dict[str, Any]] = []
    context_patterns: List[str] = []
    model: str = ""
    error: Optional[str] = None

class ImprovementRequest(BaseModel):
    """Request for design improvements"""
    design: Dict[str, Any]

class ImprovementResponse(BaseModel):
    """Response with improvement suggestions"""
    success: bool
    suggestions: List[str]

class PatternResponse(BaseModel):
    """Response with pattern data"""
    success: bool
    patterns: List[Dict[str, Any]]
    total: int

@router.post("/suggest", response_model=LayoutResponse)
async def suggest_layout(request: LayoutRequest):
    """
    Generate AI layout suggestions.
    
    Uses Ollama (Qwen2.5:7b) to generate layout based on learned patterns.
    
    Args:
        request: Layout request with prompt and dimensions
    """
    try:
        result = ai_service.generate_layout(
            prompt=request.prompt,
            page_width=request.page_width,
            page_height=request.page_height
        )
        
        return LayoutResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/improve", response_model=ImprovementResponse)
async def improve_design(request: ImprovementRequest):
    """
    Get AI suggestions for improving a design.
    
    Args:
        request: Current design data
    """
    try:
        suggestions = ai_service.suggest_improvements(request.design)
        
        return ImprovementResponse(
            success=True,
            suggestions=suggestions
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/learn")
async def learn_from_pdf(file: UploadFile = File(...)):
    """
    Learn design patterns from uploaded PDF.
    
    Analyzes a professional Etsy PDF and stores learned patterns.
    
    Args:
        file: PDF file to analyze
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Save uploaded file temporarily
    temp_path = Path(f"./temp_{file.filename}")
    try:
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Analyze PDF (always try to return this even if downstream fails)
        analyzer = PDFDesignAnalyzer()
        patterns = analyzer.analyze_pdf(str(temp_path), planner_type="uploaded") or {}

        # Try to generate AI description; fall back on failure
        try:
            description = ai_service.analyze_pdf_pattern(patterns)
        except Exception as e:
            description = "Professional planner layout"
            print(f"⚠️  AI description generation failed: {e}")

        # Try to add to vector DB; mark status
        stored = True
        pattern_id = None
        try:
            pattern_id = pattern_db.add_pattern(
                pattern_id=None,
                description=description,
                metadata=patterns
            )
        except Exception as e:
            stored = False
            print(f"⚠️  Storing pattern in DB failed: {e}")

        return {
            "success": True,
            "message": "PDF analyzed",
            "pattern_id": pattern_id,
            "db_stored": stored,
            "description": description,
            "patterns": patterns,
            "saved_to": str(analyzer.output_dir),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            if temp_path.exists():
                temp_path.unlink()
        except Exception:
            pass

@router.get("/patterns", response_model=PatternResponse)
async def get_patterns(query: Optional[str] = None, limit: int = 10):
    """
    Get learned patterns.
    
    Args:
        query: Optional search query
        limit: Maximum number of patterns to return
    """
    try:
        if query:
            patterns = pattern_db.search_patterns(query, n_results=limit)
        else:
            patterns = pattern_db.get_all_patterns(limit=limit)
        
        return PatternResponse(
            success=True,
            patterns=patterns,
            total=len(patterns)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/patterns/{pattern_id}")
async def get_pattern(pattern_id: str):
    """
    Get a specific pattern by ID.
    
    Args:
        pattern_id: Pattern ID
    """
    pattern = pattern_db.get_pattern(pattern_id)
    
    if pattern is None:
        raise HTTPException(status_code=404, detail="Pattern not found")
    
    return {
        "success": True,
        "pattern": pattern
    }

@router.delete("/patterns/{pattern_id}")
async def delete_pattern(pattern_id: str):
    """
    Delete a learned pattern.
    
    Args:
        pattern_id: Pattern ID
    """
    success = pattern_db.delete_pattern(pattern_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Pattern not found")
    
    return {
        "success": True,
        "message": "Pattern deleted successfully"
    }

@router.get("/stats")
async def get_ai_stats():
    """Get AI service statistics"""
    db_stats = pattern_db.get_stats()
    
    return {
        "success": True,
        "model": ai_service.model,
        "database": db_stats
    }
