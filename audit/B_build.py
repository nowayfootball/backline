"""Audit B: cache back_four frame tables for all matches (/tmp/B_frames)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backline import data, frames
OUT = Path("/tmp/B_frames")
for mid in data.match_ids():
    p = OUT / f"{mid}.parquet"
    if p.exists():
        continue
    frames.back_four(mid).to_parquet(p)
    print("done", mid, flush=True)
