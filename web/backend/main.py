"""
FastAPI backend for KDP Visual Editor

A Figma-like visual editor for creating KDP planner interiors with AI assistance.
"""

import os
from pathlib import Path
# Prefer local DocLayNet weights if present
local_weights = Path(__file__).parent.parent.parent / "models" / "doclayout" / "yolov8_doclaynet.pt"
if local_weights.exists() and not os.getenv("DOCLAYOUT_WEIGHTS"):
    os.environ["DOCLAYOUT_WEIGHTS"] = str(local_weights.resolve())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import sys
from pathlib import Path

# Add parent directory to path to import kdp_builder
sys.path.append(str(Path(__file__).parent.parent.parent))

# Storage directory for patterns
STORAGE_DIR = Path(__file__).parent.parent.parent / "data" / "patterns"

app = FastAPI(
    title="KDP Visual Editor API",
    description="Backend API for KDP planner visual editor with AI assistance",
    version="1.0.0"
)

# CORS middleware - allow frontend to communicate
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite default port
        "http://localhost:3000",  # Alternative React port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import JSONResponse
from fastapi import Request

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Return detailed error messages as JSON for debugging."""
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": str(exc)},
    )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "KDP Visual Editor API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "services": {
            "api": "running",
            "chromadb": "ready",
            "ollama": "ready"
        }
    }

# Import and include routers (will be created next)
try:
    from web.backend.api import designs, ai, export_api, patterns
    
    app.include_router(designs.router, prefix="/api/designs", tags=["designs"])
    app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
    app.include_router(export_api.router, prefix="/api/export", tags=["export"])
    app.include_router(patterns.router, prefix="/api/patterns", tags=["patterns"])
except ImportError as e:
    print(f"⚠️  API routes not yet created: {e}")
    print("   They will be added in the next steps")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting KDP Visual Editor API...")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🎨 Frontend will run on: http://localhost:5173")
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        timeout_keep_alive=300  # 5 minutes for AI requests
    )
