"""League settings, scoring, persona mixes and run configuration.

Everything a season needs to be reproduced lives here.  Adding 2023/2024 means
adding an entry to ``SEASON_CONFIG`` -- no other module hard-codes a year.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RAW = DATA / "raw"
CLEAN = DATA / "clean"
RESULTS = ROOT.parent / "results"

# --------------------------------------------------------------------------
# Positions
# --------------------------------------------------------------------------
QB, RB, WR, TE, K, DST = 0, 1, 2, 3, 4, 5
POS_NAMES = ["QB", "RB", "WR", "TE", "K", "DST"]
POS_ID = {n: i for i, n in enumerate(POS_NAMES)}
N_POS = 6

# Lineup slots.  FLEX accepts RB/WR/TE.
SLOT_QB, SLOT_RB1, SLOT_RB2, SLOT_WR1, SLOT_WR2, SLOT_TE, SLOT_FLEX, SLOT_DST, SLOT_K = range(9)
SLOT_NAMES = ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "D/ST", "K"]
# Which positions may fill each starting slot.
SLOT_ELIGIBLE = (
    (QB,), (RB,), (RB,), (WR,), (WR,), (TE,), (RB, WR, TE), (DST,), (K,),
)
N_SLOTS = len(SLOT_NAMES)


@dataclass(frozen=True)
class LeagueConfig:
    n_teams: int = 12
    n_starters: int = N_SLOTS
    bench: int = 7
    ir_slots: int = 1
    draft_rounds: int = 16
    playoff_teams: int = 6
    byes: int = 2               # top-2 seeds skip round 1
    trades: bool = False
    waiver_system: str = "reset_inverse_standings"   # or "rolling"

    @property
    def roster_size(self) -> int:
        return self.n_starters + self.bench


LEAGUE = LeagueConfig()

# --------------------------------------------------------------------------
# ESPN standard PPR scoring (leaguedefaults/3)
# --------------------------------------------------------------------------
SCORING = {
    "pass_yd": 1 / 25, "pass_td": 4, "pass_int": -2, "pass_2pt": 2,
    "rush_yd": 1 / 10, "rush_td": 6, "rush_2pt": 2,
    "rec": 1.0, "rec_yd": 1 / 10, "rec_td": 6, "rec_2pt": 2,
    "fumble_lost": -2, "misc_td": 6,          # return / fumble-recovery TDs
    # Kicker: ESPN pays by distance and penalises misses inside 40.
    "fg_0_39": 3, "fg_40_49": 4, "fg_50_plus": 5,
    "fg_miss_0_39": -2, "fg_miss_40_49": -1, "fg_miss_50_plus": 0,
    "pat_made": 1, "pat_miss": -1,
    # D/ST
    "dst_sack": 1, "dst_int": 2, "dst_fr": 2, "dst_td": 6,
    "dst_safety": 2, "dst_block": 2,
}
# D/ST points-allowed tiers: (max_points_allowed, fantasy_points)
DST_PA_TIERS = ((0, 5), (6, 4), (13, 3), (17, 1), (27, 0), (34, -1), (45, -3), (999, -5))
# D/ST yards-allowed tiers are ESPN-optional and off in leaguedefaults/3.

# --------------------------------------------------------------------------
# Draft: roster caps and requirements
# --------------------------------------------------------------------------
DRAFT_POS_CAP = {QB: 2, RB: 8, WR: 8, TE: 2, K: 1, DST: 1}
DRAFT_POS_MIN = {QB: 1, RB: 2, WR: 2, TE: 1, K: 1, DST: 1}
# K and D/ST are only taken in the final two rounds.
KDST_EARLIEST_ROUND = 15

# --------------------------------------------------------------------------
# Personas
# --------------------------------------------------------------------------
PERSONAS_2025 = {
    "balanced":        0.22,
    "late_qb":         0.14,
    "robust_rb":       0.11,
    "hero_rb":         0.11,
    "early_qb":        0.09,
    "elite_te":        0.08,
    "zero_rb":         0.07,
    "elite_qb_only":   0.05,
    "backup_qb_hoard": 0.05,
    "elite_te_early_qb": 0.04,
    "qb_streamer":     0.04,
}

ACTIVITY_WEIGHTS = {"active": 0.55, "moderate": 0.35, "lazy": 0.10}

# Thresholds are in points per game of roster value and are calibrated so the
# simulated move counts land inside the ranges in the build spec: roughly 15-30
# moves a season for an active manager, 8-15 for a moderate one and 2-6 for a
# lazy one.  See tests/test_acceptance.py::test_move_counts_by_activity.
ACTIVITY_PARAMS = {
    #                p(check week)  claim threshold  max claims  fa moves  lineup-error p
    "active":   dict(p_check=1.00, threshold=2.00, max_claims=3, fa_moves=1, sloppy=0.02),
    "moderate": dict(p_check=0.92, threshold=2.40, max_claims=2, fa_moves=0, sloppy=0.05),
    "lazy":     dict(p_check=0.50, threshold=3.30, max_claims=1, fa_moves=0, sloppy=0.20),
}


@dataclass(frozen=True)
class SeasonConfig:
    """Everything that changes from one season to the next."""
    year: int
    personas: dict = field(default_factory=lambda: dict(PERSONAS_2025))
    # Round-1 position restriction reflecting that year's consensus.
    round1_positions: tuple = (RB, WR)
    # Rounds 1..n where the restriction applies.
    round1_restricted_rounds: int = 1
    # The fantasy calendar, which is a property of the season and not of the
    # league.  The NFL played 17 weeks through 2020 and 18 from 2021, so a
    # fantasy season that ends in week 16 in 2019 ends in week 17 in 2022 --
    # and its regular season is a game shorter.
    n_weeks: int = 17
    regular_weeks: int = 14
    playoff_weeks: tuple = (15, 16, 17)
    # Season-long ADP calibration: multiplicative stretch applied to the ECR
    # board so simulated ADP lines up with observed draft behaviour.
    adp_sd_floor: float = 0.8
    adp_sd_scale: float = 1.35


def short_season(**kw) -> SeasonConfig:
    """A pre-2021 season: 17 NFL weeks, so 13 fantasy weeks and a week-16 final."""
    return SeasonConfig(n_weeks=16, regular_weeks=13, playoff_weeks=(14, 15, 16), **kw)


# Round-1 rules are read off each season's real ADP board rather than assumed.
# Travis Kelce is the reason this has to be per-season: he went at pick 8.2 in
# 2021 and 5.9 in 2023, so a tight end in round 1 was ordinary in those years
# and a reach in the others, where the first tight end went between 16 and 27.
#
# The persona mix is deliberately held constant across seasons.  The question
# these runs exist to answer is how a strategy performs when the *board* looks
# a certain way, and letting the field composition move at the same time would
# confound the two.  Varying the mix is a sensitivity check, not the design.
SEASON_CONFIG = {
    2018: short_season(year=2018),
    2019: short_season(year=2019),
    # 2020 is excluded: no preseason, opt-outs, and COVID-list absences that
    # read as injuries in the roster data without being injuries.
    2021: SeasonConfig(year=2021, round1_positions=(RB, WR, TE)),
    2022: SeasonConfig(year=2022),
    2023: SeasonConfig(year=2023, round1_positions=(RB, WR, TE)),
    2024: SeasonConfig(year=2024),
    2025: SeasonConfig(year=2025),
}

#: Seasons with both ESPN projections and real ADP, so they can be simulated.
SIMULATABLE = tuple(sorted(SEASON_CONFIG))


def season_config(year: int) -> SeasonConfig:
    if year not in SEASON_CONFIG:
        raise KeyError(
            f"No SeasonConfig for {year}. Add one to config.SEASON_CONFIG "
            "with that season's researched persona mix."
        )
    return SEASON_CONFIG[year]


@dataclass(frozen=True)
class RunConfig:
    year: int = 2025
    n_leagues: int = 5000
    seed: int = 20250901
    chunk: int = 250
    workers: int = 0            # 0 => os.cpu_count()
    league: LeagueConfig = LEAGUE
    out_tag: str = "base"
    # Counterfactual: force team 0 to take its first QB in this round.
    force_qb_round: int = 0     # 0 => off
    force_persona: str = ""     # "" => off


def with_waivers(cfg: RunConfig, system: str) -> RunConfig:
    return replace(cfg, league=replace(cfg.league, waiver_system=system))
