"""python -m backline MATCH_ID [--team ID|NAME] [--lang en|ko] [--font FILE] [--out DIR]"""
import argparse
from pathlib import Path

import pandas as pd

from . import data, frames, metrics, report
from .league import OUT as LEAGUE


def main():
    ap = argparse.ArgumentParser(description="Back-line match report (SkillCorner open data)")
    ap.add_argument("match_id", type=int)
    ap.add_argument("--team", help="team id or (part of) name; default: both teams")
    ap.add_argument("--lang", default="en", choices=["en", "ko"])
    ap.add_argument("--font", help="font file for --lang ko (e.g. Pretendard)")
    ap.add_argument("--out", default="reports")
    ap.add_argument("--scenes", action="store_true", help="also draw a page of cards for every time the last line was broken")
    ap.add_argument("--max-scenes", type=int, help="scene cards: keep only the first N (on-camera first)")
    ap.add_argument("--include-failed", action="store_true", help="scene cards: include attempted (incomplete) line-breaking passes")
    a = ap.parse_args()
    data.download([a.match_id], verbose=False)
    m = data.meta(a.match_id)
    teams = {m["home_team"]["id"]: m["home_team"]["short_name"], m["away_team"]["id"]: m["away_team"]["short_name"]}
    if a.team:
        pick = [t for t, n in teams.items() if a.team == str(t) or a.team.lower() in n.lower()]
    else:
        pick = list(teams)
    f = frames.back_four(a.match_id)
    league = pd.read_csv(LEAGUE)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    for t in pick:
        met = metrics.team_metrics(f, t)
        opp = [n for k, n in teams.items() if k != t][0]
        stem = out / f"{a.match_id}_{t}_{a.lang}"
        met.to_csv(stem.with_suffix(".csv"), index=False)
        p = report.render(f, met, t, teams[t], opp, league, stem.with_suffix(".png"), lang=a.lang, font=a.font, match_id=a.match_id)
        print("wrote", p)
        if a.scenes:
            from . import cards, scenes
            sc = scenes.scenes(a.match_id, t, include_failed=a.include_failed)
            total = len(sc)
            if a.max_scenes:
                sc = sc[:a.max_scenes]
            q = cards.render(sc, teams[t], opp, Path(str(stem) + "_scenes.png"), lang=a.lang, font=a.font,
                             attempts=scenes.attempts(a.match_id, t), total=total)
            print("wrote", q, f"({len(sc)} scenes)")


if __name__ == "__main__":
    main()
