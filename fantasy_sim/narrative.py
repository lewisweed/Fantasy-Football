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
