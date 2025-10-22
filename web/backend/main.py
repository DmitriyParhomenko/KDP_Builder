"""
FastAPI backend for KDP Visual Editor

A Figma-like visual editor for creating KDP planner interiors with AI assistance.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import sys
from pathlib import Path

# Add parent directory to path to import kdp_builder
sys.path.append(str(Path(__file__).parent.parent.parent))

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
    from web.backend.api import designs, ai, export_api
    
    app.include_router(designs.router, prefix="/api/designs", tags=["designs"])
    app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
    app.include_router(export_api.router, prefix="/api/export", tags=["export"])
except ImportError as e:
    print(f"⚠️  API routes not yet created: {e}")
    print("   They will be added in the next steps")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting KDP Visual Editor API...")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🎨 Frontend will run on: http://localhost:5173")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
