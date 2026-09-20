"""Does a strategy that works in one season work in another?

This is the question the whole multi-season effort exists to answer, and it
needs one control to be worth anything.  Any two seasons will rank the eleven
strategies slightly differently through sampling noise alone, so a modest
disagreement between 2018 and 2025 proves nothing on its own.

The control is split-half reliability: cut a single season's leagues in two at
random and rank the strategies in each half.  Those two rankings come from the
*same* season, so any disagreement between them is pure noise.  That sets the
ceiling.  If seasons agree with each other about as well as a season agrees
with itself, the ranking is stable and the differences are measurement.  If
they agree much less, the ranking genuinely moves with the board -- which is
the thing worth knowing.

Season points are used rather than title rate throughout: a league produces one
champion and thousands of points, so points carry a fraction of the variance
and the between-season signal is not buried under it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .analyze import load_run
from .config import season_config


def _per_week(teams: pd.DataFrame, year: int) -> pd.Series:
    """Season points per regular-season week, so 13- and 14-week years compare."""
    return teams.reg_pts / season_config(year).regular_weeks


def strategy_table(years, tag: str = "base") -> pd.DataFrame:
    """Each strategy's standing in each season.

    Standing is a z-score across the eleven strategies within that season, so a
    high-scoring season does not read as a strong strategy.
    """
    rows = []
    for y in years:
        teams, _ = load_run(y, tag)
        if teams is None:
            continue
        teams = teams.assign(ppw=_per_week(teams, y))
        g = teams.groupby("persona_name").agg(
            ppw=("ppw", "mean"), title=("champion", "mean"),
            playoffs=("playoffs", "mean"), n=("ppw", "size"))
        g["z"] = (g.ppw - g.ppw.mean()) / g.ppw.std(ddof=0)
        g["year"] = y
        rows.append(g.reset_index())
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


def _spearman(a: pd.Series, b: pd.Series) -> float:
    joined = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    if len(joined) < 3:
        return np.nan
    return float(np.corrcoef(joined.a.rank(), joined.b.rank())[0, 1])


def between_season_agreement(table: pd.DataFrame, value: str = "ppw") -> pd.DataFrame:
    """Pairwise rank agreement between every pair of seasons."""
    wide = table.pivot(index="persona_name", columns="year", values=value)
    years = list(wide.columns)
    out = pd.DataFrame(np.nan, index=years, columns=years, dtype=float)
    for i, a in enumerate(years):
        out.loc[a, a] = 1.0
        for b in years[i + 1:]:
            r = _spearman(wide[a], wide[b])
            out.loc[a, b] = out.loc[b, a] = r
    return out


def within_season_agreement(years, tag: str = "base", splits: int = 12,
                            seed: int = 0) -> pd.Series:
    """Split-half reliability: how well a season agrees with itself.

    This is the ceiling on between-season agreement.  Leagues are split at
    random rather than by index so the halves are exchangeable.
    """
    rng = np.random.default_rng(seed)
    out = {}
    for y in years:
        teams, _ = load_run(y, tag)
        if teams is None:
            continue
        teams = teams.assign(ppw=_per_week(teams, y))
        leagues = teams.league.unique()
        vals = []
        for _ in range(splits):
            half = set(rng.choice(leagues, size=len(leagues) // 2, replace=False))
            mask = teams.league.isin(half)
            a = teams[mask].groupby("persona_name").ppw.mean()
            b = teams[~mask].groupby("persona_name").ppw.mean()
            vals.append(_spearman(a, b))
        out[y] = float(np.nanmean(vals))
    return pd.Series(out, name="split_half")


def conditional_fit(table: pd.DataFrame, profiles: pd.DataFrame,
                    value: str = "z") -> pd.DataFrame:
    """How each strategy's standing moves with each feature of the board.

    With a handful of seasons these correlations are indicative at best; the
    column that matters is ``n``, and the reader should treat anything under
    about ten seasons as a direction rather than a result.
    """
    feats = [c for c in profiles.columns if c.startswith(("ante_", "post_"))]
    rows = []
    for persona, g in table.groupby("persona_name"):
        s = g.set_index("year")[value]
        for f in feats:
            joined = pd.concat([s, profiles[f]], axis=1).dropna()
            if len(joined) < 4:
                continue
            r = float(np.corrcoef(joined[value], joined[f])[0, 1])
            rows.append(dict(persona=persona, feature=f, r=round(r, 3), n=len(joined)))
    return pd.DataFrame(rows)


def seasons_needed(observed_r: float, target_p: float = 0.05) -> int:
    """Roughly how many seasons it takes to call a correlation of this size real."""
    if not np.isfinite(observed_r) or abs(observed_r) >= 1:
        return 0
    for n in range(4, 200):
        if abs(observed_r) > 1.96 / np.sqrt(n - 1):
            return n
    return 200
