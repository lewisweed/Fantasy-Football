"""How each season's draft board was shaped, and how it turned out.

The simulator can only run seasons that have weekly projections, which begin in
2018.  The question the project exists to answer -- which strategy works when
the board looks a certain way -- needs more seasons than that, and the
measurements that characterise a board need only its ADP and the scoring that
followed.  Both reach back to 2010.

Two families of number, kept deliberately apart:

**Ex ante** is what a manager could see on draft day: how the market priced
each position, how steeply cost fell away, how far down the board real ADP
reached.  Only these can condition advice, because only these are knowable in
August.

**Ex post** is what the season did with it: what paying up actually bought,
whether the board's ordering predicted anything, how many early picks stayed
good.  These explain *why* a board paid off or misled, which is the other half
of the question -- but a strategy conditioned on them is a strategy you can
only pick in January.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import clean
from .config import RAW

#: Roughly the last startable player at each position in a 12-team league.
STARTERS = {"QB": 12, "RB": 30, "WR": 36, "TE": 12}
#: The picks a manager spends real draft capital on.
PREMIUM = {"QB": 6, "RB": 15, "WR": 18, "TE": 6}
FFC_POS = {"PK": "K", "DEF": "DST"}


def ffc_board(year: int) -> pd.DataFrame:
    """That season's real mock-draft ADP, as a tidy frame."""
    path = RAW / f"ffc_adp_{year}.json"
    if not path.exists():
        return pd.DataFrame()
    raw = json.loads(path.read_text())
    rows = [dict(name=p["name"], nname=clean.norm_name(p["name"]),
                 pos=FFC_POS.get(p["position"], p["position"]),
                 team=clean.fix_team(p.get("team", "")),
                 adp=float(p["adp"]), stdev=float(p.get("stdev") or 0.0))
            for p in raw.get("players", [])]
    board = pd.DataFrame(rows).sort_values("adp").reset_index(drop=True)
    board["prank"] = board.groupby("pos").cumcount() + 1
    return board


def season_points(year: int, n_weeks: int) -> pd.DataFrame:
    """ESPN-PPR scoring for the fantasy regular season plus playoffs."""
    act = clean.actual_points(year)
    act = act[act.week <= n_weeks]
    tot = act.groupby(["player_display_name", "pos"], as_index=False).agg(
        pts=("points", "sum"), games=("points", "size"))
    tot["nname"] = tot["player_display_name"].map(clean.norm_name)
    return tot


def profile_season(year: int, n_weeks: int | None = None) -> dict | None:
    """One season's board shape and what became of it."""
    board = ffc_board(year)
    if board.empty:
        return None
    if n_weeks is None:
        n_weeks = 16 if year <= 2020 else 17
    tot = season_points(year, n_weeks)
    skill = board[board.pos.isin(STARTERS)].merge(
        tot[["nname", "pos", "pts", "games"]], on=["nname", "pos"], how="left")
    skill["pts"] = skill.pts.fillna(0.0)
    skill["games"] = skill.games.fillna(0.0)

    out = {"year": year, "board_depth": int(len(board)),
           "drafts": None, "n_weeks": n_weeks}
    meta = json.loads((RAW / f"ffc_adp_{year}.json").read_text()).get("meta", {})
    out["drafts"] = meta.get("total_drafts")

    # -- ex ante: how the market priced the board -------------------------
    top24 = board.head(24)
    for pos in ("RB", "WR"):
        out[f"ante_{pos.lower()}_top24"] = int((top24.pos == pos).sum())
    first = board.groupby("pos").adp.min()
    for pos in ("QB", "TE"):
        out[f"ante_first_{pos.lower()}"] = float(first.get(pos, np.nan))
    out["ante_qb_in_192"] = int(((board.pos == "QB") & (board.adp <= 192)).sum())
    # How steeply cost falls away inside each position: the ADP gap between the
    # premium tier and the last startable player, as a share of a full draft.
    for pos, n in PREMIUM.items():
        d = board[board.pos == pos]
        prem = d[d.prank <= n].adp.mean()
        last = d[d.prank == STARTERS[pos]].adp
        if len(last) and np.isfinite(prem):
            out[f"ante_{pos.lower()}_cliff"] = float(last.iloc[0] - prem)

    # -- ex post: what the board turned out to be worth -------------------
    for pos, n in PREMIUM.items():
        d = skill[skill.pos == pos].sort_values("prank")
        prem = d[d.prank <= n]
        repl = d[(d.prank > STARTERS[pos]) & (d.prank <= STARTERS[pos] + 8)]
        if len(prem) >= 3 and len(repl) >= 3:
            out[f"post_{pos.lower()}_edge"] = round(float(prem.pts.mean() - repl.pts.mean()), 1)
            out[f"post_{pos.lower()}_missed"] = round(float(n_weeks - prem.games.mean()), 1)
        if len(d) >= 12:
            out[f"post_{pos.lower()}_predict"] = round(
                float(np.corrcoef(-d.prank, d.pts)[0, 1]), 3)
        if len(prem) >= 3:
            elite = set(d.nlargest(n, "pts").nname)
            out[f"post_{pos.lower()}_hit"] = round(
                len(set(prem.nname) & elite) / max(len(prem), 1), 2)
    return out


def profile_all(years) -> pd.DataFrame:
    rows = [p for p in (profile_season(y) for y in years) if p is not None]
    return pd.DataFrame(rows).set_index("year")
