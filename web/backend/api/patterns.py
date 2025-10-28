from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List, Dict, Any
from pathlib import Path
from uuid import uuid4
import shutil
import json
import os

router = APIRouter()

# Config approved by user
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50MB per file
MAX_FILES_PER_UPLOAD = 20
STORAGE_DIR = Path(__file__).resolve().parents[3] / "data" / "patterns"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def _is_pdf(file: UploadFile) -> bool:
    name_ok = file.filename.lower().endswith(".pdf") if file.filename else False
    type_ok = (file.content_type or "").lower() in {"application/pdf", "application/x-pdf", "application/octet-stream"}
    return name_ok or type_ok


@router.post("/upload")
async def upload_patterns(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    if len(files) > MAX_FILES_PER_UPLOAD:
        raise HTTPException(status_code=400, detail=f"Too many files. Max {MAX_FILES_PER_UPLOAD}")

    results: List[Dict[str, Any]] = []
    errors: List[str] = []

    for file in files:
        if not _is_pdf(file):
            errors.append(f"{file.filename}: not a PDF")
            continue

        pattern_id = str(uuid4())
        out_dir = STORAGE_DIR / pattern_id
        out_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = out_dir / "original.pdf"
        meta_path = out_dir / "metadata.json"

        # Stream to disk and enforce 50MB size cap
        size = 0
        try:
            with pdf_path.open("wb") as f:
                while True:
                    chunk = await file.read(1024 * 1024)  # 1MB chunks
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_FILE_SIZE_BYTES:
                        f.close()
                        pdf_path.unlink(missing_ok=True)
                        errors.append(f"{file.filename}: exceeds 50MB limit")
                        # Drain remaining to release the request body
                        while await file.read(1024 * 1024):
                            pass
                        break
                    f.write(chunk)
        finally:
            await file.close()

        if not pdf_path.exists():
            # file rejected due to size or other error already recorded
            continue

        # Write metadata
        metadata = {
            "pattern_id": pattern_id,
            "original_filename": file.filename,
            "size_bytes": size,
            "path": str(pdf_path),
        }
        with meta_path.open("w", encoding="utf-8") as mf:
            json.dump(metadata, mf, ensure_ascii=False, indent=2)

        results.append({"pattern_id": pattern_id, "filename": file.filename, "size_bytes": size})

    return {"success": len(results) > 0, "uploaded": results, "errors": errors}
