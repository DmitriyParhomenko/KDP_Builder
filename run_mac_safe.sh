#!/bin/bash
# Mac-safe server launch script
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.6
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
echo "Environment set for Mac-safe extraction."
uvicorn web.backend.main:app --host 0.0.0.0 --port 8000 --workers 1
