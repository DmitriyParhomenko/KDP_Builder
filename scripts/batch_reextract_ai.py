#!/usr/bin/env python3
"""
Batch re-extract all patterns with AI detection enabled and collect metrics.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
import sys
import os

# Add web/backend to sys.path for direct imports
backend_path = Path(__file__).resolve().parents[2] / "web" / "backend"
sys.path.insert(0, str(backend_path))
os.chdir(Path(__file__).resolve().parents[2])

from services.block_extractor import extract_blocks
from services.pattern_db import pattern_db

def count_block_types(blocks: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for b in blocks:
        t = b.get("type", "unknown")
        counts[t] = counts.get(t, 0) + 1
    return counts

def main():
    patterns_dir = Path("./data/patterns")
    if not patterns_dir.exists():
        print("data/patterns not found")
        return

    pattern_dirs = [d for d in patterns_dir.iterdir() if d.is_dir() and (d / "original.pdf").exists()]
    print(f"Found {len(pattern_dirs)} patterns to re-extract with AI detection.")

    metrics = []
    for pd in pattern_dirs:
        pid = pd.name
        print(f"\n=== {pid} ===")
        try:
            result = extract_blocks(pd, ai_detect=True)
            if not result.get("success"):
                print(f"  FAILED: {result.get('error')}")
                continue
            blocks = result.get("blocks", [])
            ai_dets = result.get("ai_detections", [])
            block_counts = count_block_types(blocks)
            metric = {
                "pattern_id": pid,
                "total_blocks": len(blocks),
                "ai_detections": len(ai_dets),
                "block_counts": block_counts,
            }
            metrics.append(metric)
            print(f"  Blocks: {len(blocks)}; AI detections: {len(ai_dets)}")
            print("  Types:", block_counts)
        except Exception as e:
            print(f"  EXCEPTION: {e}")
            continue

    # Save metrics
    out = Path("./batch_ai_metrics.json")
    out.write_text(json.dumps(metrics, indent=2))
    print(f"\nMetrics saved to {out}")

if __name__ == "__main__":
    main()
