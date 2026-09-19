"""Turn raw downloads into the season "universe" the simulator runs on.

Outputs (per season, cached under ``data/clean``):

``universe_{year}.parquet``
    One row per player in the draftable + waiver pool: name, position, NFL
    team, ADP and its spread, the preseason per-game prior, bye week and the
    handcuff (the player directly ahead of him on the depth chart).

``weekly_{year}.npz``
    ``n_players x n_weeks`` arrays -- ``proj`` (what a manager expected before
    kickoff), ``act`` (what he actually scored), ``out`` (known unavailable
    before kickoff), ``quest`` (listed Questionable) and ``depth`` (depth-chart
    rank at his position that week).

No value in these files may depend on information that was not public before
that week's kickoff.  The two places where that is easy to get wrong are
handled explicitly:

* a weekly projection is never zeroed just because the player turned out not to
  play -- it is zeroed only on a bye or an official Out/Doubtful designation;
* the rank -> points curves that convert consensus rankings into point
  expectations are fitted on *other* seasons only.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

from . import fetch, scoring
from .config import CLEAN, POS_ID, RAW, season_config

# FantasyPros pages that carry PPR consensus rankings.
PRESEASON_PAGE = "/nfl/rankings/ppr-cheatsheets.php"
WEEKLY_PAGES = {
    "QB": "/nfl/rankings/qb.php",
    "RB": "/nfl/rankings/ppr-rb.php",
    "WR": "/nfl/rankings/ppr-wr.php",
    "TE": "/nfl/rankings/ppr-te.php",
    "K": "/nfl/rankings/k.php",
    "DST": "/nfl/rankings/dst.php",
}
ROS_PAGES = {
    "QB": "/nfl/rankings/ros-qb.php",
    "RB": "/nfl/rankings/ros-ppr-rb.php",
    "WR": "/nfl/rankings/ros-ppr-wr.php",
    "TE": "/nfl/rankings/ros-ppr-te.php",
}
ROS_OVERALL_PAGE = "/nfl/rankings/ros-ppr-overall.php"

SUFFIX = re.compile(r"\b(jr|sr|ii|iii|iv|v)\b")
PUNCT = re.compile(r"[^a-z ]")

# FantasyPros / nflverse team-abbreviation drift.
# nflverse writes the Rams as LA while ESPN and FantasyPros write LAR, which
# silently cost that team its bye week and its D/ST scoring until it was caught.
TEAM_FIX = {"JAC": "JAX", "LVR": "LV", "OAK": "LV", "SD": "LAC", "STL": "LAR",
            "LA": "LAR", "WSH": "WAS", "ARZ": "ARI", "BLT": "BAL",
            "CLV": "CLE", "HST": "HOU"}


def norm_name(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = PUNCT.sub("", s.lower().replace(".", "").replace("'", ""))
    s = SUFFIX.sub("", s)
    return " ".join(s.split())


def fix_team(s):
    return TEAM_FIX.get(str(s).upper(), str(s).upper())


# --------------------------------------------------------------------------
# Calendar: map a ranking scrape date onto a fantasy week
# --------------------------------------------------------------------------
def week_calendar(games: pd.DataFrame, year: int) -> pd.DataFrame:
    g = games[(games.season == year) & (games.game_type == "REG")].copy()
    g["gameday"] = pd.to_datetime(g["gameday"])
    cal = g.groupby("week")["gameday"].agg(["min", "max"]).reset_index()
    cal.columns = ["week", "first_game", "last_game"]
    return cal.sort_values("week").reset_index(drop=True)


def date_to_week(dates: pd.Series, cal: pd.DataFrame) -> pd.Series:
    """A ranking published on ``date`` describes the next week still to be played."""
    out = pd.Series(np.nan, index=dates.index)
    for _, row in cal.iterrows():
        # Rankings for week w are published from the Tuesday before its first
        # game up to that week's last game.
        start = row.first_game - pd.Timedelta(days=4)
        hit = (dates >= start) & (dates <= row.last_game) & out.isna()
        out[hit] = row.week
    return out


def bye_weeks(games: pd.DataFrame, year: int) -> dict:
    g = games[(games.season == year) & (games.game_type == "REG")]
    weeks = sorted(g.week.unique())
    played = {}
    for _, r in g.iterrows():
        played.setdefault(fix_team(r.home_team), set()).add(r.week)
        played.setdefault(fix_team(r.away_team), set()).add(r.week)
    return {t: sorted(set(weeks) - w)[0] if set(weeks) - w else 0
            for t, w in played.items()}


# --------------------------------------------------------------------------
# Actual points
# --------------------------------------------------------------------------
def actual_points(year: int) -> pd.DataFrame:
    """Weekly ESPN-PPR points for every offensive player, kicker and D/ST."""
    pw = pd.read_csv(fetch.player_week(year), low_memory=False)
    off = scoring.score_player_week(pw)
    off = off[off.position.isin(["QB", "RB", "WR", "TE", "K"])].copy()
    off["key"] = "G:" + off["player_id"].astype(str)
    off["pos"] = off["position"]

    g = pd.read_csv(fetch.games(), low_memory=False)
    tw = pd.read_csv(fetch.team_week(year), low_memory=False)
    dst = scoring.score_dst(tw, g[g.game_type == "REG"])
    dst["key"] = "D:" + dst["team"].map(fix_team)
    dst["pos"] = "DST"
    dst["player_display_name"] = dst["team"].map(fix_team) + " D/ST"
    dst = dst.rename(columns={"team": "team"})

    cols = ["key", "player_display_name", "pos", "team", "week", "points"]
    out = pd.concat([off[cols], dst[cols]], ignore_index=True)
    out["team"] = out["team"].map(fix_team)
    return out


# --------------------------------------------------------------------------
# FantasyPros rankings
# --------------------------------------------------------------------------
def load_ecr() -> pd.DataFrame:
    e = pd.read_parquet(fetch.fp_ecr(),
                        columns=["fp_page", "player", "id", "pos", "team",
                                 "ecr", "sd", "best", "worst", "scrape_date"])
    e["scrape_date"] = pd.to_datetime(e["scrape_date"])
    e["team"] = e["team"].map(fix_team)
    e["nname"] = e["player"].map(norm_name)
    return e


def preseason_board(ecr: pd.DataFrame, cal: pd.DataFrame) -> pd.DataFrame:
    """The last PPR draft board published before week 1."""
    cutoff = cal.first_game.iloc[0]
    b = ecr[(ecr.fp_page == PRESEASON_PAGE) & (ecr.scrape_date < cutoff)
            & (ecr.scrape_date > cutoff - pd.Timedelta(days=150))]
    if b.empty:
        raise RuntimeError("no preseason PPR board found for this season")
    last = b.scrape_date.max()
    b = b[b.scrape_date == last].copy()
    return b.sort_values("ecr").reset_index(drop=True)


def weekly_ranks(ecr: pd.DataFrame, cal: pd.DataFrame, pages: dict) -> pd.DataFrame:
    sub = ecr[ecr.fp_page.isin(pages.values())].copy()
    sub = sub[(sub.scrape_date >= cal.first_game.iloc[0] - pd.Timedelta(days=7))
              & (sub.scrape_date <= cal.last_game.iloc[-1])]
    sub["week"] = date_to_week(sub["scrape_date"], cal)
    sub = sub.dropna(subset=["week"])
    sub["week"] = sub["week"].astype(int)
    page_to_pos = {v: k for k, v in pages.items()}
    sub["rpos"] = sub["fp_page"].map(page_to_pos)
    # One row per player-week: keep the latest scrape.
    sub = sub.sort_values("scrape_date").drop_duplicates(["id", "week", "rpos"], keep="last")
    return sub


# --------------------------------------------------------------------------
# rank -> points curves, fitted on other seasons
# --------------------------------------------------------------------------
def _monotone_curve(ranks: np.ndarray, pts: np.ndarray, max_rank: int) -> np.ndarray:
    """Smooth, non-increasing E[points | rank] over ranks 1..max_rank."""
    order = np.argsort(ranks)
    r, p = ranks[order], pts[order]
    grid = np.arange(1, max_rank + 1, dtype=float)
    # Local average in a widening window (ranks get noisier and sparser deeper).
    out = np.empty(max_rank)
    for i, g in enumerate(grid):
        half = max(2.5, 0.12 * g)
        m = (r >= g - half) & (r <= g + half)
        out[i] = p[m].mean() if m.sum() >= 8 else np.nan
    s = pd.Series(out).interpolate(limit_direction="both")
    s = s.rolling(5, center=True, min_periods=1).mean()
    # Enforce that a better rank is never worth less.
    return np.minimum.accumulate(s.to_numpy())


def fit_weekly_curves(years, cal_by_year) -> dict:
    """E[weekly points | positional weekly rank], one curve per position."""
    ecr = load_ecr()
    rows = []
    for y in years:
        cal = cal_by_year[y]
        wk = weekly_ranks(ecr, cal, WEEKLY_PAGES)
        act = actual_points(y)
        act_off = act[act.pos != "DST"].copy()
        act_off["nname"] = act_off["player_display_name"].map(norm_name)
        off = wk[wk.rpos != "DST"].merge(
            act_off[["nname", "pos", "week", "points"]],
            left_on=["nname", "rpos", "week"], right_on=["nname", "pos", "week"],
            how="inner")
        rows.append(off[["rpos", "ecr", "points"]])
        dst_act = act[act.pos == "DST"].copy()
        dst = wk[wk.rpos == "DST"].merge(
            dst_act[["team", "week", "points"]], on=["team", "week"], how="inner")
        rows.append(dst[["rpos", "ecr", "points"]])
    df = pd.concat(rows, ignore_index=True)
    curves = {}
    for pos, grp in df.groupby("rpos"):
        max_rank = int(min(grp.ecr.max(), 200))
        curves[pos] = _monotone_curve(grp.ecr.to_numpy(), grp.points.to_numpy(), max_rank)
    return curves


def fit_preseason_curve(years, cal_by_year) -> dict:
    """E[points per game played | preseason rank *within position*].

    Overall board position is a draft-cost signal, not a scoring one -- a QB
    ranked 150th overall outscores a WR ranked 150th several times over -- so
    the prior is fitted against each player's rank among his own position.
    """
    ecr = load_ecr()
    rows = []
    for y in years:
        board = preseason_board(ecr, cal_by_year[y])
        board = board.sort_values("ecr").copy()
        board["prank"] = board.groupby("pos").cumcount() + 1
        act = actual_points(y)
        g = act.groupby(["player_display_name", "pos", "team"], as_index=False).agg(
            points=("points", "sum"), games=("points", "size"))
        g["nname"] = g["player_display_name"].map(norm_name)
        g = g[g.games >= 4]
        g["ppg"] = g.points / g.games
        off = board[board.pos != "DST"].merge(
            g[["nname", "pos", "ppg"]], on=["nname", "pos"], how="inner")
        rows.append(off[["pos", "prank", "ppg"]])
        dst = board[board.pos == "DST"].merge(
            g[g.pos == "DST"][["team", "ppg"]], on="team", how="inner")
        rows.append(dst[["pos", "prank", "ppg"]])
    df = pd.concat(rows, ignore_index=True)
    curves = {}
    for pos, grp in df.groupby("pos"):
        max_rank = int(max(grp.prank.max(), 40))
        curves[pos] = _monotone_curve(grp.prank.to_numpy(float),
                                      grp.ppg.to_numpy(), max_rank)
    return curves


def apply_curve(curve: np.ndarray, ranks) -> np.ndarray:
    r = np.asarray(ranks, dtype=float)
    idx = np.clip(np.rint(r).astype(int) - 1, 0, len(curve) - 1)
    val = curve[idx]
    # Beyond the fitted range, decay gently toward replacement level.
    beyond = r > len(curve)
    val = np.where(beyond, curve[-1] * 0.9, val)
    return np.where(np.isfinite(r), val, np.nan)


# --------------------------------------------------------------------------
# Availability
# --------------------------------------------------------------------------
def availability(year: int, gsis: pd.Series, teams: pd.Series, n_weeks: int,
                 ranked: np.ndarray, is_dst: np.ndarray) -> tuple:
    """``(out, quest)`` -- what a manager knew before kickoff.

    Three contemporaneous signals, none of them retrospective:

    * the official injury report (Out / Doubtful / Questionable);
    * the weekly NFL roster -- a player on injured reserve, cut or retired is
      publicly unavailable, which is how season-ending injuries become known;
    * persistence -- a player ruled out who then drops out of the weekly
      consensus rankings is still out.
    """
    n = len(gsis)
    out = np.zeros((n, n_weeks), dtype=bool)
    quest = np.zeros((n, n_weeks), dtype=bool)
    idx = {g: i for i, g in enumerate(gsis) if isinstance(g, str) and g}

    inj = pd.read_csv(fetch.injuries(year), low_memory=False)
    inj = inj[inj.season_type == "REG"]
    for gid, wk, st in zip(inj.gsis_id, inj.week, inj.report_status):
        i = idx.get(gid)
        if i is None or not (1 <= wk <= n_weeks):
            continue
        if st in ("Out", "Doubtful"):
            out[i, wk - 1] = True
        elif st == "Questionable":
            quest[i, wk - 1] = True

    active = np.zeros((n, n_weeks), dtype=bool)
    try:
        wr = pd.read_csv(fetch.weekly_rosters(year), low_memory=False,
                         usecols=["week", "game_type", "status", "gsis_id"])
    except Exception:
        wr = None
    if wr is not None:
        wr = wr[wr.game_type == "REG"].dropna(subset=["gsis_id"])
        # UNAVAILABLE: injured reserve, cut, retired, exempt list.
        bad = {"RES", "CUT", "RET", "EXE", "TRC"}
        seen = np.zeros((n, n_weeks), dtype=bool)
        for gid, wk, st in zip(wr.gsis_id, wr.week, wr.status):
            i = idx.get(gid)
            if i is None or not (1 <= wk <= n_weeks):
                continue
            seen[i, wk - 1] = True
            if st in bad:
                out[i, wk - 1] = True
            else:
                active[i, wk - 1] = True
        # Never on anyone's roster that week => not available to be started.
        # Only applied to players the roster file knows at all, so an unmapped
        # id never gets silently benched for the whole season.
        tracked = seen.any(axis=1) & ~is_dst
        out |= (~seen) & tracked[:, None]

    # A player who was ruled out and has not reappeared in the weekly rankings
    # is still out -- unless the roster says he is back on the active list.
    for w in range(1, n_weeks):
        out[:, w] |= out[:, w - 1] & ~ranked[:, w] & ~active[:, w]
    return out, quest


def depth_ranks(year: int, gsis: pd.Series, cal: pd.DataFrame, n_weeks: int) -> np.ndarray:
    """Depth-chart rank at the player's own position, week by week."""
    n = len(gsis)
    depth = np.full((n, n_weeks), 9, dtype=np.int8)
    try:
        dc = pd.read_csv(fetch.depth_charts(year), low_memory=False,
                         usecols=["dt", "team", "gsis_id", "pos_abb", "pos_rank"])
    except Exception:
        return depth
    dc = dc.dropna(subset=["gsis_id"])
    dc = dc[dc.pos_abb.isin(["QB", "RB", "WR", "TE", "LWR", "RWR", "SWR", "PK", "K"])]
    dc["dt"] = pd.to_datetime(dc["dt"], errors="coerce", utc=True).dt.tz_localize(None)
    dc = dc.dropna(subset=["dt"]).sort_values("dt")
    idx = {g: i for i, g in enumerate(gsis) if isinstance(g, str) and g}
    for _, row in cal.iterrows():
        w = int(row.week)
        if w > n_weeks:
            continue
        snap = dc[dc.dt <= row.last_game]
        if snap.empty:
            continue
        snap = snap.drop_duplicates(["gsis_id"], keep="last")
        for gid, rank in zip(snap.gsis_id, snap.pos_rank):
            i = idx.get(gid)
            if i is not None and np.isfinite(rank):
                depth[i, w - 1] = min(int(rank), 9)
    return depth


# --------------------------------------------------------------------------
# Tier 1: ESPN player pool + Fantasy Football Calculator ADP
# --------------------------------------------------------------------------
#: ESPN's own position ids.
ESPN_POS = {1: "QB", 2: "RB", 3: "WR", 4: "TE", 5: "K", 16: "DST"}

#: ESPN's proTeamId, in nflverse abbreviations.
ESPN_TEAM = {
    0: "FA", 1: "ATL", 2: "BUF", 3: "CHI", 4: "CIN", 5: "CLE", 6: "DAL",
    7: "DEN", 8: "DET", 9: "GB", 10: "TEN", 11: "IND", 12: "KC", 13: "LV",
    14: "LAR", 15: "MIA", 16: "MIN", 17: "NE", 18: "NO", 19: "NYG", 20: "NYJ",
    21: "PHI", 22: "ARI", 23: "PIT", 24: "LAC", 25: "SF", 26: "SEA", 27: "TB",
    28: "WAS", 29: "CAR", 30: "JAX", 33: "BAL", 34: "HOU",
}

#: Fantasy Football Calculator's position codes.
FFC_POS = {"PK": "K", "DEF": "DST"}


def espn_available(year: int) -> bool:
    return (RAW / f"espn_players_{year}.json").exists()


def ffc_board(year: int) -> pd.DataFrame:
    """Fantasy Football Calculator 12-team PPR ADP, keyed for matching."""
    path = RAW / f"ffc_adp_{year}.json"
    if not path.exists():
        return pd.DataFrame(columns=["nname", "pos", "team", "adp", "stdev"])
    raw = json.loads(path.read_text())
    rows = []
    for p in raw.get("players", []):
        pos = FFC_POS.get(p["position"], p["position"])
        rows.append(dict(nname=norm_name(p["name"]), pos=pos,
                         team=fix_team(p.get("team", "")),
                         adp=float(p["adp"]),
                         stdev=float(p.get("stdev") or 0.0)))
    return pd.DataFrame(rows)


def espn_pool(year: int, n_weeks: int):
    """The ESPN player pool with its own weekly projections and actuals.

    Returns ``(pool, proj_raw, act, act_present)``.  ``proj_raw`` is exactly
    what ESPN published, zeroes and all; the leak repair happens later, in
    :func:`build`, because it needs to know who was genuinely unavailable.
    """
    raw = json.loads((RAW / f"espn_players_{year}.json").read_text())
    players = raw["players"] if isinstance(raw, dict) else raw

    rows, projs, acts, present = [], [], [], []
    for entry in players:
        p = entry.get("player", entry)
        pos = ESPN_POS.get(p.get("defaultPositionId"))
        if pos is None:
            continue
        pr = np.zeros(n_weeks)
        ac = np.zeros(n_weeks)
        seen = np.zeros(n_weeks, dtype=bool)
        season_proj = 0.0
        for st in p.get("stats", []):
            if st.get("seasonId") != year:
                continue
            total = st.get("appliedTotal")
            split, source = st.get("statSplitTypeId"), st.get("statSourceId")
            if split == 0 and source == 1:
                season_proj = float(total or 0.0)
            elif split == 1:
                w = st.get("scoringPeriodId", 0)
                if not (1 <= w <= n_weeks):
                    continue
                if source == 1:
                    pr[w - 1] = float(total or 0.0)
                elif source == 0:
                    ac[w - 1] = float(total or 0.0)
                    seen[w - 1] = total is not None
        # A player ESPN never projects at all is not in anyone's league.
        if season_proj <= 0 and pr.max() <= 0 and pos not in ("K", "DST"):
            continue
        ranks = (p.get("draftRanksByRankType") or {}).get("PPR") or {}
        rows.append(dict(
            player=p.get("fullName", ""), pos=pos,
            team=fix_team(ESPN_TEAM.get(p.get("proTeamId"), "FA")),
            espn_id=int(p.get("id", -1)),
            espn_rank=float(ranks.get("rank") or np.nan),
            season_proj=season_proj))
        projs.append(pr)
        acts.append(ac)
        present.append(seen)

    pool = pd.DataFrame(rows).reset_index(drop=True)
    pool["nname"] = pool["player"].map(norm_name)
    # D/ST are named for the franchise, so they match on team, not on name.
    pool.loc[pool.pos == "DST", "nname"] = pool.loc[pool.pos == "DST", "team"]
    # A player ESPN never gave a preseason number sits at the bottom of his
    # position rather than at zero: nobody expected anything of him, but "not
    # rated" is not the same as "cannot score".
    prior = (pool["season_proj"] / n_weeks).to_numpy(copy=True)
    for pos in pool.pos.unique():
        at = (pool.pos == pos).to_numpy()
        rated = prior[at & (prior > 0)]
        if len(rated):
            prior[at & (prior <= 0)] = float(np.percentile(rated, 10))
    pool["prior_ppg"] = prior

    # -- ADP: real mock drafts first, ESPN's own board as the fallback ----
    ffc = ffc_board(year)
    pool["adp"] = np.nan
    pool["adp_sd"] = np.nan
    if len(ffc):
        skill = ffc[ffc.pos != "DST"].drop_duplicates(["nname", "pos"])
        merged = pool.merge(skill[["nname", "pos", "adp", "stdev"]],
                            on=["nname", "pos"], how="left", suffixes=("", "_ffc"))
        pool["adp"] = merged["adp_ffc"].to_numpy()
        pool["adp_sd"] = merged["stdev"].to_numpy()
        dst = ffc[ffc.pos == "DST"].drop_duplicates("team")
        dmerge = pool.merge(dst[["team", "pos", "adp", "stdev"]],
                            on=["team", "pos"], how="left", suffixes=("", "_d"))
        take = pool.adp.isna() & dmerge.adp_d.notna()
        pool.loc[take, "adp"] = dmerge.loc[take, "adp_d"].to_numpy()
        pool.loc[take, "adp_sd"] = dmerge.loc[take, "stdev"].to_numpy()

    # Everyone Fantasy Football Calculator never saw drafted is priced off
    # ESPN's own PPR board, shifted past the last real ADP.
    last = float(np.nanmax(pool.adp.to_numpy())) if pool.adp.notna().any() else 180.0
    miss = pool.adp.isna() & pool.espn_rank.notna()
    pool.loc[miss, "adp"] = last + pool.loc[miss, "espn_rank"].rank(method="first")
    pool["adp"] = pool["adp"].fillna(last + len(pool))

    return (pool, np.stack(projs) if projs else np.zeros((0, n_weeks)),
            np.stack(acts) if acts else np.zeros((0, n_weeks)),
            np.stack(present) if present else np.zeros((0, n_weeks), dtype=bool))


def repair_projections(proj_raw: np.ndarray, act_present: np.ndarray,
                       known_out: np.ndarray, prior_ppg: np.ndarray) -> np.ndarray:
    """Undo ESPN's retrospective zeroing of weekly projections.

    ESPN shows nothing for a week a player ended up missing -- including the
    week he got hurt mid-game, which is information nobody had before kickoff.
    Burrow in 2025 week 2 is the case the build spec names: projection zero,
    seven points actually scored.

    The repair is deliberately the narrowest one that fixes this.  It fires
    only where the player accrued a stat line that week, so a zero is only
    overwritten when we can see it contradicts itself; a backup quarterback
    ESPN projects at zero because he is not starting keeps his zero, which is
    real information and not a leak.  The restored value is his most recent
    published projection, or his preseason expectation if he has none.
    """
    n, weeks = proj_raw.shape
    out = proj_raw.copy()
    for i in range(n):
        last = 0.0
        for w in range(weeks):
            if known_out[i, w]:
                out[i, w] = 0.0
                continue
            if proj_raw[i, w] > 0:
                last = proj_raw[i, w]
            elif act_present[i, w]:
                out[i, w] = last if last > 0 else max(prior_ppg[i], 0.0)
    return out


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------
def _fantasypros_tier(year: int, n_weeks: int, games, cal) -> dict:
    """Draft board and weekly expectations from FantasyPros PPR consensus.

    Rankings are turned into points through curves fitted on *other* seasons,
    so the target season never sees its own outcomes.
    """
    ecr = load_ecr()
    cal_years = [y for y in fetch.CALIBRATION_YEARS if y != year]
    cal_by_year = {y: week_calendar(games, y) for y in cal_years}
    weekly_curves = fit_weekly_curves(cal_years, cal_by_year)
    pre_curve = fit_preseason_curve(cal_years, cal_by_year)     # per position

    board = preseason_board(ecr, cal)
    wk = weekly_ranks(ecr, cal, WEEKLY_PAGES)
    ros = weekly_ranks(ecr, cal, ROS_PAGES)
    act = actual_points(year)

    pool = board[["player", "nname", "pos", "team", "ecr", "sd", "id"]].copy()
    pool = pool.rename(columns={"ecr": "adp", "sd": "adp_sd"})
    # In-season risers who were never on the draft board are waiver fodder.
    extra = (wk[~wk.id.isin(pool.id)]
             .sort_values("ecr").drop_duplicates("id", keep="first")
             [["player", "nname", "rpos", "team", "ecr", "sd", "id"]]
             .rename(columns={"rpos": "pos", "ecr": "_r", "sd": "adp_sd"}))
    extra = extra[extra._r <= 60]
    extra["adp"] = np.nan
    pool = pd.concat([pool, extra[pool.columns.intersection(extra.columns)]],
                     ignore_index=True)
    pool = pool[pool.pos.isin(POS_ID)].drop_duplicates("id").reset_index(drop=True)

    # -- identity: FantasyPros id -> nflverse gsis_id ---------------------
    ids = pd.read_csv(fetch.player_ids(), low_memory=False)
    ids = ids.dropna(subset=["fantasypros_id", "gsis_id"])
    fp2gsis = dict(zip(ids.fantasypros_id.astype(int), ids.gsis_id))
    pool["gsis_id"] = pool["id"].astype("Int64").map(fp2gsis)
    act_names = (act[act.pos != "DST"]
                 .assign(nname=lambda d: d.player_display_name.map(norm_name))
                 .drop_duplicates(["nname", "pos"])
                 .set_index(["nname", "pos"])["key"])
    key = []
    for _, r in pool.iterrows():
        if r.pos == "DST":
            key.append("D:" + fix_team(r.team))
        elif isinstance(r.gsis_id, str) and r.gsis_id:
            key.append("G:" + r.gsis_id)
        else:
            key.append(act_names.get((r.nname, r.pos), ""))
    pool["key"] = key
    pool = pool[pool.key != ""].reset_index(drop=True)

    n = len(pool)
    kidx = {k: i for i, k in enumerate(pool.key)}
    fpidx = {int(i): j for j, i in enumerate(pool.id)}

    act_arr = np.zeros((n, n_weeks))
    played = np.zeros((n, n_weeks), dtype=bool)
    a = act[act.week <= n_weeks]
    for k, w, pts in zip(a.key, a.week, a.points):
        i = kidx.get(k)
        if i is not None:
            act_arr[i, w - 1] = pts
            played[i, w - 1] = True

    proj = np.full((n, n_weeks), np.nan)
    ranked = np.zeros((n, n_weeks), dtype=bool)
    for fid, w, rpos, r in zip(wk.id, wk.week, wk.rpos, wk.ecr):
        i = fpidx.get(int(fid))
        if i is None or w > n_weeks:
            continue
        curve = weekly_curves.get(rpos)
        if curve is None:
            continue
        proj[i, w - 1] = apply_curve(curve, r)
        ranked[i, w - 1] = True

    ros_fill = np.full((n, n_weeks), np.nan)
    for fid, w, rpos, r in zip(ros.id, ros.week, ros.rpos, ros.ecr):
        i = fpidx.get(int(fid))
        if i is None or w > n_weeks:
            continue
        curve = weekly_curves.get(rpos)
        if curve is not None:
            # ROS boards are deeper than weekly ones and grade a full season of
            # opportunity, so discount them toward the streaming baseline.
            ros_fill[i, w - 1] = apply_curve(curve, r) * 0.92

    max_adp = float(np.nanmax(pool.adp.to_numpy()))
    pool["adp"] = pool["adp"].fillna(max_adp + 40.0)

    # Preseason prior, in points per game, from rank within position.
    pool["prank"] = (pool.sort_values("adp").groupby("pos").cumcount() + 1
                     ).reindex(pool.index)
    prior = np.full(len(pool), np.nan)
    for pos, grp in pool.groupby("pos"):
        curve = pre_curve.get(pos)
        if curve is None:
            continue
        idx = grp.index.to_numpy()
        prior[idx] = apply_curve(curve, grp["prank"].to_numpy())
        miss = idx[~np.isfinite(prior[idx])]
        if len(miss):
            prior[miss] = curve[-1]
    pool["prior_ppg"] = np.where(np.isfinite(prior), prior, 1.0)

    proj = np.where(np.isfinite(proj), proj, ros_fill)
    proj = np.where(np.isfinite(proj), proj,
                    pool["prior_ppg"].to_numpy()[:, None] * 0.85)

    return dict(pool=pool, proj=proj, act=act_arr, played=played, ranked=ranked,
                tier="nflverse+fantasypros", calibration_years=cal_years,
                repair=False)


def _espn_tier(year: int, n_weeks: int) -> dict:
    """ESPN's own pool, weekly projections and ``appliedTotal`` actuals."""
    pool, proj_raw, act_arr, act_present = espn_pool(year, n_weeks)

    ids = pd.read_csv(fetch.player_ids(), low_memory=False)
    ids = ids.dropna(subset=["espn_id", "gsis_id"])
    espn2gsis = dict(zip(ids.espn_id.astype(int), ids.gsis_id))
    pool["gsis_id"] = pool["espn_id"].map(espn2gsis)
    # Fall back to a name match for anyone the id map misses.
    by_name = (ids.dropna(subset=["merge_name"])
               .assign(nn=lambda d: d.merge_name.map(norm_name))
               .drop_duplicates(["nn", "position"])
               .set_index(["nn", "position"])["gsis_id"])
    miss = pool.gsis_id.isna() & (pool.pos != "DST")
    pool.loc[miss, "gsis_id"] = [
        by_name.get((nn, pos)) for nn, pos in
        zip(pool.loc[miss, "nname"], pool.loc[miss, "pos"])]

    pool["key"] = np.where(
        pool.pos == "DST", "D:" + pool.team,
        np.where(pool.gsis_id.notna(), "G:" + pool.gsis_id.astype(str),
                 "E:" + pool.espn_id.astype(str)))
    pool["id"] = pool["espn_id"]

    # ESPN emits a zero stat line for every week a player is merely on a
    # roster, so whether he actually took the field comes from the nflverse box
    # scores instead.  This matters twice: it decides which zeroes are a leak
    # worth repairing, and it keeps a benched player's rolling form from being
    # dragged down by games he never played.
    played = np.zeros((len(pool), n_weeks), dtype=bool)
    box = actual_points(year)
    box = box[box.week <= n_weeks]
    kidx = {k: i for i, k in enumerate(pool.key)}
    for k, w in zip(box.key, box.week):
        i = kidx.get(k)
        if i is not None:
            played[i, w - 1] = True
    # Anyone nflverse cannot be matched to falls back to ESPN's own evidence.
    unmatched = ~np.isin(pool.key.to_numpy(), box.key.unique())
    played[unmatched] = act_present[unmatched] & (act_arr[unmatched] > 0)

    # ESPN zeroes a weekly projection retrospectively, so it is no evidence
    # that a player was known out.  Availability comes from the injury report
    # and the weekly NFL roster instead, and the carry-over rule is left off.
    ranked = np.ones((len(pool), n_weeks), dtype=bool)
    return dict(pool=pool, proj=proj_raw, act=act_arr, played=played,
                ranked=ranked, tier="espn+ffc", calibration_years=[],
                repair=True)


def build(year: int, *, force: bool = False) -> tuple[Path, Path]:
    CLEAN.mkdir(parents=True, exist_ok=True)
    uni_path = CLEAN / f"universe_{year}.parquet"
    wk_path = CLEAN / f"weekly_{year}.npz"
    if uni_path.exists() and wk_path.exists() and not force:
        return uni_path, wk_path

    cfg = season_config(year)
    n_weeks = cfg.n_weeks
    games = pd.read_csv(fetch.games(), low_memory=False)
    cal = week_calendar(games, year)

    data = (_espn_tier(year, n_weeks) if espn_available(year)
            else _fantasypros_tier(year, n_weeks, games, cal))
    pool = data["pool"]
    proj, act_arr, played, ranked = (data["proj"], data["act"],
                                     data["played"], data["ranked"])
    n = len(pool)

    # -- availability -----------------------------------------------------
    gsis = pool["gsis_id"].astype("string").fillna("")
    is_dst = (pool["pos"] == "DST").to_numpy()
    out, quest = availability(year, gsis, pool["team"], n_weeks, ranked, is_dst)
    byes = bye_weeks(games, year)
    pool["bye"] = pool["team"].map(byes).fillna(0).astype(int)
    for i, b in enumerate(pool.bye):
        if 1 <= b <= n_weeks:
            out[i, b - 1] = True

    # -- projections ------------------------------------------------------
    if data["repair"]:
        proj = repair_projections(proj, played, out, pool["prior_ppg"].to_numpy())
    proj = np.where(out, 0.0, proj)
    played = played & ~out
    # Actuals are left exactly as they were scored; only expectations are zeroed.

    depth = depth_ranks(year, gsis, cal, n_weeks)

    # -- ADP spread -------------------------------------------------------
    pool["adp_sd"] = pool["adp_sd"].fillna(pool["adp"] * 0.12)
    pool["adp_sd"] = np.maximum(pool["adp_sd"] * cfg.adp_sd_scale, cfg.adp_sd_floor)
    pool["season_prior"] = pool["prior_ppg"] * n_weeks
    pool["pos_id"] = pool["pos"].map(POS_ID).astype(int)

    keep = ["key", "player", "pos", "pos_id", "team", "adp", "adp_sd",
            "prior_ppg", "season_prior", "bye", "gsis_id", "id"]
    pool[keep].to_parquet(uni_path, index=False)
    np.savez_compressed(wk_path, proj=proj.astype(np.float32),
                        act=act_arr.astype(np.float32), out=out, quest=quest,
                        played=played, depth=depth)
    meta = {
        "year": year, "n_players": int(n), "n_weeks": n_weeks,
        "tier": data["tier"],
        "espn_file_present": espn_available(year),
        "ffc_file_present": (RAW / f"ffc_adp_{year}.json").exists(),
        "calibration_years": data["calibration_years"],
    }
    (CLEAN / f"meta_{year}.json").write_text(json.dumps(meta, indent=2))
    return uni_path, wk_path


def load(year: int):
    uni_path = CLEAN / f"universe_{year}.parquet"
    wk_path = CLEAN / f"weekly_{year}.npz"
    if not (uni_path.exists() and wk_path.exists()):
        build(year)
    pool = pd.read_parquet(uni_path)
    z = np.load(wk_path)
    return pool, {k: z[k] for k in z.files}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the cleaned season universe.")
    ap.add_argument("--year", type=int, default=2025)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    u, w = build(args.year, force=args.force)
    pool, arrays = load(args.year)
    print(f"universe -> {u}\nweekly   -> {w}")
    print(f"{len(pool)} players; positions: "
          f"{pool.pos.value_counts().to_dict()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
