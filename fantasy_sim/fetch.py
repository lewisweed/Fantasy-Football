"""Idempotent, cached downloaders for every data source the simulator uses.

Two tiers:

* **Tier 1 (preferred)** -- ESPN's ``kona_player_info`` feed and Fantasy
  Football Calculator ADP.  These give ESPN's own ``appliedTotal`` scoring and
  real mock-draft ADP, exactly as the build spec asks for.
* **Tier 2 (fallback)** -- nflverse box scores scored with ESPN's rule set, and
  FantasyPros PPR consensus rankings (via the DynastyProcess mirror) for the
  draft board and weekly expectations.

``clean.py`` prefers tier 1 when its files are present and falls back to tier 2
otherwise, so the same codebase runs in a network-restricted environment and in
an open one.  Run ``python -m fantasy_sim.fetch --year 2025`` to populate the
cache; everything already on disk is skipped.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

from .config import RAW

UA = {"User-Agent": "Mozilla/5.0"}
TIMEOUT = 300

NFLVERSE = "https://github.com/nflverse/nflverse-data/releases/download"
NFLDATA_GAMES = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
DP = "https://raw.githubusercontent.com/dynastyprocess/data/master/files"

ESPN_URL = (
    "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{year}"
    "/segments/0/leaguedefaults/3?view=kona_player_info&scoringPeriodId=0"
)
ESPN_FILTER = {
    "players": {
        "filterSlotIds": {"value": [0, 2, 4, 6, 16, 17]},
        "limit": 1200,
        "sortPercOwned": {"sortAsc": False, "sortPriority": 1},
    }
}
FFC_URL = "https://fantasyfootballcalculator.com/api/v1/adp/ppr?teams=12&year={year}"


class SourceUnavailable(RuntimeError):
    """Raised when a host cannot be reached (egress policy, outage, ...)."""


def _download(url: str, dest: Path, *, headers: dict | None = None) -> Path:
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with requests.get(url, headers={**UA, **(headers or {})}, stream=True,
                          timeout=TIMEOUT) as r:
            r.raise_for_status()
            with open(tmp, "wb") as fh:
                for chunk in r.iter_content(1 << 20):
                    fh.write(chunk)
    except requests.RequestException as exc:      # network / policy failure
        tmp.unlink(missing_ok=True)
        raise SourceUnavailable(f"{url}: {exc}") from exc
    tmp.replace(dest)
    return dest


# --------------------------------------------------------------------------
# Tier 1
# --------------------------------------------------------------------------
def espn_players(year: int) -> Path:
    """ESPN player pool with weekly projections and actuals (``appliedTotal``)."""
    dest = RAW / f"espn_players_{year}.json"
    if dest.exists():
        return dest
    try:
        r = requests.get(
            ESPN_URL.format(year=year),
            headers={**UA, "X-Fantasy-Filter": json.dumps(ESPN_FILTER)},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
    except requests.RequestException as exc:
        raise SourceUnavailable(f"ESPN kona_player_info for {year}: {exc}") from exc
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(r.json()))
    return dest


def ffc_adp(year: int) -> Path:
    """Fantasy Football Calculator 12-team PPR ADP from real mock drafts."""
    dest = RAW / f"ffc_adp_{year}.json"
    if dest.exists():
        return dest
    try:
        r = requests.get(FFC_URL.format(year=year), headers=UA, timeout=TIMEOUT)
        r.raise_for_status()
    except requests.RequestException as exc:
        raise SourceUnavailable(f"FFC ADP for {year}: {exc}") from exc
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(r.json()))
    return dest


# --------------------------------------------------------------------------
# Tier 2
# --------------------------------------------------------------------------
def player_week(year: int) -> Path:
    return _download(f"{NFLVERSE}/stats_player/stats_player_week_{year}.csv",
                     RAW / f"stats_player_week_{year}.csv")


def team_week(year: int) -> Path:
    return _download(f"{NFLVERSE}/stats_team/stats_team_week_{year}.csv",
                     RAW / f"stats_team_week_{year}.csv")


def injuries(year: int) -> Path:
    return _download(f"{NFLVERSE}/injuries/injuries_{year}.csv",
                     RAW / f"injuries_{year}.csv")


def depth_charts(year: int) -> Path:
    return _download(f"{NFLVERSE}/depth_charts/depth_charts_{year}.csv",
                     RAW / f"depth_charts_{year}.csv")


def snap_counts(year: int) -> Path:
    return _download(f"{NFLVERSE}/snap_counts/snap_counts_{year}.csv",
                     RAW / f"snap_counts_{year}.csv")


def rosters(year: int) -> Path:
    return _download(f"{NFLVERSE}/rosters/roster_{year}.csv",
                     RAW / f"roster_{year}.csv")


def weekly_rosters(year: int) -> Path:
    """Week-by-week roster status (ACT / RES=IR / INA / DEV / CUT)."""
    return _download(f"{NFLVERSE}/weekly_rosters/roster_weekly_{year}.csv",
                     RAW / f"roster_weekly_{year}.csv")


def games() -> Path:
    return _download(NFLDATA_GAMES, RAW / "games.csv")


def fp_ecr() -> Path:
    """FantasyPros expert-consensus rankings, all seasons, all pages."""
    return _download(f"{DP}/db_fpecr.parquet", RAW / "db_fpecr.parquet")


def player_ids() -> Path:
    return _download(f"{DP}/db_playerids.csv", RAW / "db_playerids.csv")


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------
#: Seasons used only to fit rank -> points curves (never for the target season).
CALIBRATION_YEARS = (2021, 2022, 2023, 2024)


def fetch_all(year: int, *, calibration: bool = True) -> dict:
    """Download everything for ``year``.  Returns a report of what worked."""
    report = {"ok": [], "unavailable": []}

    def attempt(name, fn, *a):
        try:
            p = fn(*a)
            report["ok"].append((name, str(p)))
        except SourceUnavailable as exc:
            report["unavailable"].append((name, str(exc).split(":")[0]))

    attempt("espn_players", espn_players, year)
    attempt("ffc_adp", ffc_adp, year)

    for name, fn in (("player_week", player_week), ("team_week", team_week),
                     ("injuries", injuries), ("depth_charts", depth_charts),
                     ("snap_counts", snap_counts), ("rosters", rosters),
                     ("weekly_rosters", weekly_rosters)):
        attempt(f"{name}_{year}", fn, year)
    attempt("games", games)
    attempt("fp_ecr", fp_ecr)
    attempt("player_ids", player_ids)

    if calibration:
        for y in CALIBRATION_YEARS:
            if y == year:
                continue
            attempt(f"player_week_{y}", player_week, y)
            attempt(f"team_week_{y}", team_week, y)
            attempt(f"injuries_{y}", injuries, y)
            attempt(f"weekly_rosters_{y}", weekly_rosters, y)
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Populate the raw data cache.")
    ap.add_argument("--year", type=int, default=2025)
    ap.add_argument("--no-calibration", action="store_true")
    args = ap.parse_args(argv)

    rep = fetch_all(args.year, calibration=not args.no_calibration)
    for name, path in rep["ok"]:
        print(f"  ok           {name:24s} {path}")
    for name, why in rep["unavailable"]:
        print(f"  UNAVAILABLE  {name:24s} {why}", file=sys.stderr)
    if rep["unavailable"]:
        print(
            "\nSome sources could not be reached.  clean.py falls back to the "
            "nflverse + FantasyPros tier for anything missing.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
