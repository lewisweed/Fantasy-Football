"""Fixtures: the real 2025 universe, plus a hand-built one for scenario tests."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from fantasy_sim import clean, season, values
from fantasy_sim.config import LEAGUE, POS_ID, season_config

N_WEEKS = 17


@pytest.fixture(scope="session")
def real():
    """The cleaned 2025 season, as the simulator actually runs it."""
    pool, arrays = clean.load(2025)
    return pool, arrays, values.SeasonData(pool, arrays, N_WEEKS)


def build_sd(players: list, n_weeks: int = N_WEEKS) -> values.SeasonData:
    """A small synthetic universe.

    Each entry is ``dict(name, pos, team, adp, prior, proj, act, out, quest,
    depth)`` where the weekly fields accept a scalar or a per-week sequence.
    """
    def spread(p, key, default, dtype=float):
        v = p.get(key, default)
        arr = np.full(n_weeks, v, dtype=dtype) if np.isscalar(v) else np.asarray(v, dtype=dtype)
        return arr

    pool = pd.DataFrame({
        "player": [p["name"] for p in players],
        "pos": [p["pos"] for p in players],
        "pos_id": [POS_ID[p["pos"]] for p in players],
        "team": [p.get("team", f"T{i}") for i, p in enumerate(players)],
        "adp": [float(p.get("adp", 200.0)) for p in players],
        "adp_sd": [float(p.get("adp_sd", 10.0)) for p in players],
        "prior_ppg": [float(p.get("prior", 8.0)) for p in players],
        "bye": [int(p.get("bye", 0)) for p in players],
    })
    arrays = {
        "proj": np.stack([spread(p, "proj", p.get("prior", 8.0)) for p in players]),
        "act": np.stack([spread(p, "act", p.get("prior", 8.0)) for p in players]),
        "out": np.stack([spread(p, "out", False, bool) for p in players]),
        "quest": np.stack([spread(p, "quest", False, bool) for p in players]),
        "played": np.stack([spread(p, "played", True, bool) for p in players]),
        "depth": np.stack([spread(p, "depth", 1, np.int8) for p in players]),
    }
    arrays["played"] &= ~arrays["out"]
    return values.SeasonData(pool, arrays, n_weeks)


def bare_sim(sd, waivers: str = "reset_inverse_standings"):
    """A LeagueSim with no draft run, for testing decisions in isolation."""
    from dataclasses import replace
    cfg = replace(LEAGUE, waiver_system=waivers)
    sim = season.LeagueSim(sd, cfg, season_config(2025), seed=1)
    sim.teams = []
    return sim


def make_team(sim, roster, *, tid=0, threshold=0.5, persona=0, first_qb_round=0):
    from fantasy_sim.season import Team
    t = Team(tid=tid, persona=persona, activity=0, slot=tid,
             roster=list(roster), opinion=np.ones(sim.sd.n),
             threshold=threshold, max_claims=3, first_qb_round=first_qb_round)
    sim.teams.append(t)
    for p in roster:
        sim.free[p] = False
    return t
