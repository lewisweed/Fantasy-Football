"""Single-league debug trace.

``python -m fantasy_sim.trace --seed 7 --team 3`` replays one league and prints
that team's draft, every roster move with the reason behind it, and each week's
lineup and result.  This is how the behaviours in section 5.3 of the build spec
are checked by eye rather than only in aggregate.
"""
from __future__ import annotations

import argparse

import numpy as np

from . import clean, season, values
from .config import LEAGUE, POS_NAMES, season_config
from .draft import PERSONA_NAMES
from .season import ACTIVITY_NAMES


class Tracer:
    def __init__(self, team: int | None = None):
        self.team = team
        self.draft: list = []
        self.moves: list = []
        self.lineups: list = []

    def move(self, week, tid, kind, player, reason):
        if self.team is None or tid == self.team:
            self.moves.append((week, tid, kind, player, reason))

    def lineup(self, week, tid, starters, pts):
        if self.team is None or tid == self.team:
            self.lineups.append((week, tid, list(starters), pts))


def run_trace(seed: int, team: int, year: int = 2025, waivers: str | None = None):
    pool, arrays = clean.load(year)
    sd = values.SeasonData(pool, arrays, season_config(year).n_weeks)
    cfg = LEAGUE
    if waivers:
        from dataclasses import replace
        cfg = replace(cfg, waiver_system=waivers)
    tr = Tracer(team)
    sim = season.LeagueSim(sd, cfg, season_config(year), seed, tracer=tr)
    res = sim.run()
    return sd, sim, res, tr


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Trace one simulated league.")
    ap.add_argument("--trace-league", "--seed", dest="seed", type=int, required=True)
    ap.add_argument("--team", type=int, default=0)
    ap.add_argument("--year", type=int, default=2025)
    ap.add_argument("--waivers", default=None)
    args = ap.parse_args(argv)

    sd, sim, res, tr = run_trace(args.seed, args.team, args.year, args.waivers)
    t = sim.teams[args.team]
    print(f"League seed {args.seed} | team {args.team} | "
          f"persona {PERSONA_NAMES[t.persona]} | {ACTIVITY_NAMES[t.activity]} | "
          f"draft slot {t.slot + 1}")
    print(f"waivers: {sim.cfg.waiver_system}\n")

    print("DRAFT")
    for pick, rnd, m, p, pos in tr.draft:
        if m == args.team:
            print(f"  R{rnd:<2d} pick {pick:3d}  {pos:4s} {sd.name[p]:26s} "
                  f"(board {sd.adp[p]:6.1f}, prior {sd.prior[p]:5.1f} ppg)")

    print("\nMOVES")
    if not tr.moves:
        print("  (none)")
    for week, tid, kind, p, reason in tr.moves:
        print(f"  wk{week:<3d} {kind:5s} {POS_NAMES[sd.pos[p]]:4s} {sd.name[p]:26s} "
              f"-- {reason}")

    print("\nWEEKS")
    opp_pts = sim.weekly_points
    for week, tid, starters, pts in tr.lineups:
        names = ", ".join(f"{sd.name[s]}({sd.act[s, week-1]:.0f})" for s in starters)
        print(f"  wk{week:<3d} {pts:6.1f}   {names}")

    print(f"\nFINAL  {t.wins}-{t.losses}  {t.pts_for:.1f} pts  "
          f"seed {res['seed'][args.team]}  "
          f"{'CHAMPION' if res['champion'][args.team] else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
