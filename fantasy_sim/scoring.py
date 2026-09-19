"""ESPN standard-PPR scoring applied to nflverse box scores.

ESPN's own ``appliedTotal`` is the preferred source of truth (see fetch.py); when
that feed is unavailable these functions reproduce the same rule set from raw
statistics, which is what the simulator scores seasons with in the fallback tier.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import DST_PA_TIERS, SCORING as S


def _col(df: pd.DataFrame, name: str) -> pd.Series:
    """Column as float with NaN -> 0, or an all-zero series when absent."""
    if name not in df.columns:
        return pd.Series(0.0, index=df.index)
    return pd.to_numeric(df[name], errors="coerce").fillna(0.0)


def score_offense(df: pd.DataFrame) -> pd.Series:
    """QB/RB/WR/TE fantasy points for a weekly player-stats frame."""
    fumbles_lost = (
        _col(df, "sack_fumbles_lost") + _col(df, "rushing_fumbles_lost")
        + _col(df, "receiving_fumbles_lost")
    )
    # nflverse also exposes a combined total; prefer it when the parts are absent.
    total_lost = _col(df, "fumbles_lost_total")
    fumbles_lost = np.maximum(fumbles_lost, total_lost)

    pts = (
        _col(df, "passing_yards") * S["pass_yd"]
        + _col(df, "passing_tds") * S["pass_td"]
        + _col(df, "passing_interceptions") * S["pass_int"]
        + _col(df, "passing_2pt_conversions") * S["pass_2pt"]
        + _col(df, "rushing_yards") * S["rush_yd"]
        + _col(df, "rushing_tds") * S["rush_td"]
        + _col(df, "rushing_2pt_conversions") * S["rush_2pt"]
        + _col(df, "receptions") * S["rec"]
        + _col(df, "receiving_yards") * S["rec_yd"]
        + _col(df, "receiving_tds") * S["rec_td"]
        + _col(df, "receiving_2pt_conversions") * S["rec_2pt"]
        + fumbles_lost * S["fumble_lost"]
        + (_col(df, "special_teams_tds") + _col(df, "fumble_recovery_tds")) * S["misc_td"]
    )
    return pts


def score_kicker(df: pd.DataFrame) -> pd.Series:
    """ESPN kicker scoring: distance-weighted makes, penalties on short misses."""
    made_short = _col(df, "fg_made_0_19") + _col(df, "fg_made_20_29") + _col(df, "fg_made_30_39")
    made_mid = _col(df, "fg_made_40_49")
    made_long = _col(df, "fg_made_50_59") + _col(df, "fg_made_60_")
    miss_short = (_col(df, "fg_missed_0_19") + _col(df, "fg_missed_20_29")
                  + _col(df, "fg_missed_30_39"))
    miss_mid = _col(df, "fg_missed_40_49")
    miss_long = _col(df, "fg_missed_50_59") + _col(df, "fg_missed_60_")
    return (
        made_short * S["fg_0_39"] + made_mid * S["fg_40_49"] + made_long * S["fg_50_plus"]
        + miss_short * S["fg_miss_0_39"] + miss_mid * S["fg_miss_40_49"]
        + miss_long * S["fg_miss_50_plus"]
        + _col(df, "pat_made") * S["pat_made"] + _col(df, "pat_missed") * S["pat_miss"]
    )


def _pa_points(points_allowed: np.ndarray) -> np.ndarray:
    out = np.full(points_allowed.shape, DST_PA_TIERS[-1][1], dtype=float)
    assigned = np.zeros(points_allowed.shape, dtype=bool)
    for cap, val in DST_PA_TIERS:
        hit = (~assigned) & (points_allowed <= cap)
        out[hit] = val
        assigned |= hit
    return out


def score_dst(team_week: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """Weekly D/ST scoring.  Returns columns ``team, week, points``."""
    from .clean import regular_season_rows
    t = regular_season_rows(team_week).copy()

    # Points allowed comes from the box score, not the defensive stat lines.
    home = games[["season", "week", "home_team", "away_score"]].rename(
        columns={"home_team": "team", "away_score": "pa"})
    away = games[["season", "week", "away_team", "home_score"]].rename(
        columns={"away_team": "team", "home_score": "pa"})
    pa = pd.concat([home, away], ignore_index=True)
    t = t.merge(pa, on=["season", "week", "team"], how="left")

    blocks = _col(t, "def_punt_blocks") + _col(t, "def_pat_blocks") + _col(t, "def_fg_blocks")
    tds = _col(t, "def_tds") + _col(t, "fumble_recovery_tds") + _col(t, "special_teams_tds")
    pts = (
        _col(t, "def_sacks") * S["dst_sack"]
        + _col(t, "def_interceptions") * S["dst_int"]
        + _col(t, "fumble_recovery_opp") * S["dst_fr"]
        + tds * S["dst_td"]
        + _col(t, "def_safeties") * S["dst_safety"]
        + blocks * S["dst_block"]
        + _pa_points(_col(t, "pa").to_numpy())
    )
    out = t[["season", "week", "team"]].copy()
    out["points"] = pts.to_numpy()
    return out


def score_player_week(player_week: pd.DataFrame) -> pd.DataFrame:
    """Offense + kickers from a weekly player-stats frame (REG only)."""
    from .clean import regular_season_rows
    df = regular_season_rows(player_week).copy()
    is_k = df["position"].eq("K")
    pts = score_offense(df)
    pts = pts.where(~is_k, score_kicker(df))
    out = df[["season", "week", "player_id", "player_display_name", "position", "team"]].copy()
    out["points"] = pts.to_numpy()
    return out
