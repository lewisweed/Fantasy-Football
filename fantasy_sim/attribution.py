"""Which players actually drove each strategy's season.

The Monte Carlo runs answer *whether* a persona beat the field.  They cannot
say *why*, because they only keep team-level outcomes.  This module re-runs the
drafts on their own -- cheap, since no season is simulated -- and records which
players each persona ended up rostering.  Combining that exposure with how far
each player beat or missed his own preseason projection decomposes a persona's
season into named players.

Nothing here is available to the managers in the simulation: it is hindsight
used strictly for explanation, never for a decision.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import draft, run as runmod
from .config import LEAGUE, PERSONAS_2025, POS_NAMES, season_config


def exposure(year: int, n_drafts: int = 3000, seed: int = 99,
             personas: dict | None = None) -> tuple[np.ndarray, pd.DataFrame]:
    """Draft-only sweep.  Returns ``counts[persona, player]`` and the pool."""
    sd, pool = runmod._season_data(year)
    scfg = season_config(year)
    n_pers = len(draft.PERSONA_NAMES)
    counts = np.zeros((n_pers, sd.n), dtype=np.int64)
    teams = np.zeros(n_pers, dtype=np.int64)
    mix = personas or PERSONAS_2025
    for d in range(n_drafts):
        rng = np.random.default_rng(seed + d)
        pers = draft.sample_personas(rng, mix, LEAGUE.n_teams)
        rosters, _, _ = draft.run_draft(sd, rng, pers, LEAGUE, scfg)
        for m in range(LEAGUE.n_teams):
            p = int(pers[m])
            teams[p] += 1
            counts[p, rosters[m]] += 1
    return counts, teams, pool


def surprise(year: int) -> pd.DataFrame:
    """Per-player: preseason expectation, what he actually scored, the gap."""
    sd, pool = runmod._season_data(year)
    scfg = season_config(year)
    reg = slice(0, scfg.regular_weeks)
    act = sd.act[:, reg]
    played = sd.played[:, reg]
    df = pool[["player", "pos", "team", "adp", "season_prior"]].copy()
    df["actual"] = act.sum(axis=1)
    df["games"] = played.sum(axis=1)
    # Scale the preseason total to the fantasy regular season for a fair gap.
    df["expected"] = df.season_prior * (scfg.regular_weeks / sd.n_weeks)
    df["gap"] = df.actual - df.expected
    df["missed"] = np.clip(scfg.regular_weeks - 1 - df.games, 0, None)
    df["round"] = np.ceil(df.adp / LEAGUE.n_teams)
    return df


def attribute(year: int, n_drafts: int = 3000) -> pd.DataFrame:
    """Per persona and player: points of surprise captured versus the field.

    ``edge`` is ``(this persona's rate of rostering him - the league's rate)``
    times how far he beat his projection.  Summed over players it is the
    persona's draft-day edge, in points, decomposed by name.
    """
    counts, teams, _ = exposure(year, n_drafts)
    s = surprise(year)
    rate = counts / np.maximum(teams, 1)[:, None]          # per team of that persona
    league = counts.sum(axis=0) / max(teams.sum(), 1)      # per team, any persona
    rows = []
    for p, name in enumerate(draft.PERSONA_NAMES):
        if teams[p] == 0:
            continue
        edge = (rate[p] - league) * s.gap.to_numpy()
        # A positive edge has two very different causes: rostering a player
        # who beat his projection more than the field did, or dodging one who
        # missed it.  Keep them apart -- they are opposite stories.
        d = s.assign(persona=name, own=rate[p], field=league, edge=edge,
                     how=np.where(rate[p] >= league, "rostered", "avoided"))
        rows.append(d)
    return pd.concat(rows, ignore_index=True)
