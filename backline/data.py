"""Download and read SkillCorner open data (A-League 2024/25), pinned to one commit for reproducibility."""
import json
import os
import urllib.request
from pathlib import Path

import pandas as pd

SHA = "4340d274572876239c154c90bc507a9b3250a656"   # SkillCorner/opendata, 2026-09-14
RAW = f"https://raw.githubusercontent.com/SkillCorner/opendata/{SHA}/data"
LFS = f"https://media.githubusercontent.com/media/SkillCorner/opendata/{SHA}/data"


def data_dir() -> Path:
    d = Path(os.environ.get("BACKLINE_DATA", Path.home() / ".cache" / "backline"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def league_dir() -> Path:
    """League reference folder: BACKLINE_LEAGUE if set (built by `python -m backline.league`), else the packaged one."""
    return Path(os.environ["BACKLINE_LEAGUE"]) if os.environ.get("BACKLINE_LEAGUE") else Path(__file__).parent


def _fetch(url: str, dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 1000:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    tmp.rename(dest)
    return dest


def match_ids() -> list[int]:
    p = _fetch(f"{RAW}/matches.json", data_dir() / "matches.json")
    return sorted(m["id"] for m in json.loads(p.read_text()))


def download(mids=None, verbose=True) -> None:
    """Fetch events, metadata, phases and tracking (~90 MB per match)."""
    for mid in mids or match_ids():
        base = data_dir() / str(mid)
        for name in ("dynamic_events.csv", "match.json", "phases_of_play.csv"):
            _fetch(f"{RAW}/matches/{mid}/{mid}_{name}", base / f"{mid}_{name}")
        trk = base / f"{mid}_tracking_extrapolated.jsonl"
        if not (trk.exists() and trk.stat().st_size > 1000):
            print(f"downloading match {mid} tracking (~90 MB, first run only)...", flush=True)
        _fetch(f"{LFS}/matches/{mid}/{mid}_tracking_extrapolated.jsonl", trk)
        if verbose:
            print("downloaded", mid, flush=True)


def events(mid: int) -> pd.DataFrame:
    return pd.read_csv(data_dir() / str(mid) / f"{mid}_dynamic_events.csv", low_memory=False)


def phases(mid: int) -> pd.DataFrame:
    return pd.read_csv(data_dir() / str(mid) / f"{mid}_phases_of_play.csv")


def meta(mid: int) -> dict:
    return json.loads((data_dir() / str(mid) / f"{mid}_match.json").read_text())


def tracking(mid: int, frames=None):
    """Yield tracking frames (10 fps). If `frames` is given, only those frame numbers."""
    want = None if frames is None else set(frames)
    with open(data_dir() / str(mid) / f"{mid}_tracking_extrapolated.jsonl") as fh:
        for line in fh:
            fr = json.loads(line)
            if not fr.get("player_data"):
                continue
            if want is None or fr["frame"] in want:
                yield fr


def roster(m: dict):
    """team_id per player, goalkeeper ids, home team id, attacking side of home team per period."""
    team = {p["id"]: p["team_id"] for p in m["players"]}
    gk = {p["id"] for p in m["players"] if p["player_role"]["name"] == "Goalkeeper"}
    side = {i + 1: s for i, s in enumerate(m["home_team_side"])}
    return team, gk, m["home_team"]["id"], side
