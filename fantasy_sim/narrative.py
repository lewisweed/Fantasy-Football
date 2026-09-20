"""Per-season write-up: what the board looked like, what happened, who caused it.

Everything here is hindsight.  It explains a season after the fact; none of it
was available to the managers while they were drafting, and none of it is used
to make a decision anywhere in the simulation.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import attribution as A, crossseason as cs
from .config import LEAGUE

SEASONS = (2018, 2019, 2023, 2024, 2025)


def board_shape(year: int) -> pd.Series:
    """How each position's first-five-round picks paid off against projection."""
    s = A.surprise(year)
    e = s[s["round"] <= 5]
    g = e.groupby("pos").gap.mean()
    m = e.groupby("pos").missed.mean()
    return pd.Series({
        "rb_gap": g.get("RB", np.nan), "wr_gap": g.get("WR", np.nan),
        "qb_gap": g.get("QB", np.nan), "te_gap": g.get("TE", np.nan),
        "rb_minus_wr": g.get("RB", np.nan) - g.get("WR", np.nan),
        "rb_missed": m.get("RB", np.nan), "wr_missed": m.get("WR", np.nan),
        "qb_missed": m.get("QB", np.nan),
    })


def season_story(year: int, z: pd.Series, n_drafts: int = 3000) -> dict:
    """Best and worst strategy of the season, and the players behind each."""
    s = A.surprise(year)
    att = A.attribute(year, n_drafts=n_drafts)
    best, worst = z.idxmax(), z.idxmin()
    keep = ["player", "pos", "adp", "own", "field", "gap", "edge", "how"]
    return {
        "year": year,
        "shape": board_shape(year),
        "best": best, "best_z": z[best],
        "worst": worst, "worst_z": z[worst],
        "busts": s[s["round"] <= 5].nsmallest(6, "gap"),
        "hits": s[s["round"] >= 8].nlargest(6, "gap"),
        "best_helped": att[att.persona == best].nlargest(5, "edge")[keep],
        "best_hurt": att[att.persona == best].nsmallest(3, "edge")[keep],
        "worst_hurt": att[att.persona == worst].nsmallest(5, "edge")[keep],
        "worst_helped": att[att.persona == worst].nlargest(3, "edge")[keep],
        "edge": att.groupby("persona").edge.sum(),
    }


def all_stories(years=SEASONS, n_drafts: int = 3000) -> list[dict]:
    w = cs.strategy_table(list(years)).pivot(
        index="persona_name", columns="year", values="z")
    return [season_story(y, w[y], n_drafts) for y in years]


def _md(df: pd.DataFrame, cols: dict, fmt: dict | None = None) -> str:
    fmt = fmt or {}
    head = "| " + " | ".join(cols.values()) + " |"
    rule = "|" + "|".join("---" for _ in cols) + "|"
    out = [head, rule]
    for r in df.itertuples():
        cells = []
        for c in cols:
            v = getattr(r, c)
            cells.append(fmt.get(c, lambda x: f"{x}")(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def season_markdown(st: dict) -> str:
    y, sh = st["year"], st["shape"]
    n0 = lambda v: f"{v:+.0f}"
    n1 = lambda v: f"{v:.1f}"
    pc = lambda v: f"{v*100:.0f}%"
    L = [f"### {y}", ""]
    L.append(f"Best strategy **{st['best']}** ({st['best_z']:+.2f} sd above the "
             f"field), worst **{st['worst']}** ({st['worst_z']:+.2f}).")
    L.append("")
    L.append("How the first five rounds paid off, by position — points versus "
             "each player's own preseason projection, and games missed:")
    L.append("")
    L.append("| | QB | RB | WR | TE |")
    L.append("|---|---|---|---|---|")
    L.append(f"| points vs projection | {sh.qb_gap:+.0f} | {sh.rb_gap:+.0f} | "
             f"{sh.wr_gap:+.0f} | {sh.te_gap:+.0f} |")
    L.append(f"| games missed | {sh.qb_missed:.1f} | {sh.rb_missed:.1f} | "
             f"{sh.wr_missed:.1f} | — |")
    L.append("")
    L.append("**What went wrong that nobody could have known.** Picks from the "
             "first five rounds, by how far they fell short:")
    L.append("")
    L.append(_md(st["busts"], {"player": "player", "pos": "pos", "adp": "ADP",
                               "expected": "projected", "actual": "scored",
                               "gap": "gap", "missed": "games missed"},
                 {"adp": n1, "expected": lambda v: f"{v:.0f}",
                  "actual": lambda v: f"{v:.0f}", "gap": n0,
                  "missed": lambda v: f"{v:.0f}"}))
    L.append("")
    L.append("**What went right that nobody could have known.** Players drafted "
             "in round 8 or later, or not drafted at all:")
    L.append("")
    L.append(_md(st["hits"], {"player": "player", "pos": "pos", "adp": "ADP",
                              "expected": "projected", "actual": "scored",
                              "gap": "gap"},
                 {"adp": n1, "expected": lambda v: f"{v:.0f}",
                  "actual": lambda v: f"{v:.0f}", "gap": n0}))
    L.append("")
    L.append(f"**Why {st['best']} won.** Each player's contribution is how much "
             "more (or less) often this strategy rostered him than the league "
             "did, times how far he beat his projection:")
    L.append("")
    cols = {"player": "player", "pos": "pos", "adp": "ADP", "how": "",
            "own": "this strategy", "field": "league", "gap": "his gap",
            "edge": "points of edge"}
    f = {"adp": n1, "own": pc, "field": pc, "gap": n0, "edge": n0}
    L.append(_md(st["best_helped"], cols, f))
    L.append("")
    L.append(f"**Why {st['worst']} lost.**")
    L.append("")
    L.append(_md(st["worst_hurt"], cols, f))
    L.append("")
    return "\n".join(L)
