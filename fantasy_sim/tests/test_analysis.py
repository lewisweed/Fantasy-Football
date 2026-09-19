"""The reporting layer: intervals, and the counterfactual comparison.

The counterfactual table is the load-bearing claim in the report -- it is the
only place the quarterback-timing question is asked with the rest of the league
held fixed -- so it gets a test with a known answer planted in it.
"""
from __future__ import annotations

import shutil

import numpy as np
import pandas as pd
import pytest

from fantasy_sim import analyze
from fantasy_sim.config import RESULTS

YEAR = 9999          # a scratch namespace, never a real season


def _fake_run(tag: str, n_leagues: int, seed0: int, rng, *,
              qb_round: int | None = None, bump: float = 0.0) -> None:
    """A results directory shaped like a real one, with a planted effect."""
    d = RESULTS / f"{YEAR}_{tag}"
    d.mkdir(parents=True, exist_ok=True)
    rows = []
    for lg in range(seed0, seed0 + n_leagues):
        for t in range(12):
            forced = qb_round is not None and t == 0
            rows.append(dict(
                league=lg, team=t, persona=0, activity=0, draft_slot=t,
                wins=7, losses=7, ties=0, pts_for=1500.0,
                reg_pts=1500.0 + (bump if t == 0 else 0.0) + rng.normal(0, 40),
                seed=0, playoffs=False, champion=bool(t == 0 and rng.random() < 0.09),
                runner_up=False, adds=10, drops=10,
                first_qb_round=qb_round if forced else int(rng.integers(2, 13)),
                first_qb=5, qb_points=300.0))
    pd.DataFrame(rows).to_parquet(d / "teams.parquet", index=False)


@pytest.fixture
def planted():
    rng = np.random.default_rng(0)
    _fake_run("base", 400, 1000, rng)
    _fake_run("cf_qb3", 300, 1000, rng, qb_round=3, bump=-25.0)
    _fake_run("cf_qb9", 300, 1000, rng, qb_round=9, bump=+18.0)
    yield
    for p in RESULTS.glob(f"{YEAR}_*"):
        shutil.rmtree(p)


def _cells(table: str) -> dict:
    """Markdown table -> {row label: [cell, ...]}, header and rule dropped."""
    out = {}
    for line in table.splitlines()[2:]:
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        out[cells[0]] = cells
    return out


def test_counterfactuals_recover_a_planted_effect(planted):
    base, _ = analyze.load_run(YEAR, "base")
    rows = _cells(analyze.counterfactuals(YEAR, base))
    assert set(rows) == {"3", "9"}, rows.keys()

    # Forcing the quarterback into round 3 was planted as -25 points a season
    # and round 9 as +18; both should come back inside sampling error.
    assert float(rows["3"][3]) == pytest.approx(-25.0, abs=8.0)
    assert float(rows["9"][3]) == pytest.approx(+18.0, abs=8.0)
    # Each is compared against the same league seeds it was run on.
    assert rows["3"][1] == "300" and rows["9"][1] == "300"
    # The interval brackets the estimate.
    for key in ("3", "9"):
        lo, hi = (float(x) for x in rows[key][4].split(" to "))
        assert lo < float(rows[key][3]) < hi


def test_counterfactuals_say_so_when_the_runs_are_missing():
    base = pd.DataFrame({"team": [0], "league": [1], "reg_pts": [1500.0],
                         "champion": [False]})
    assert "not present" in analyze.counterfactuals(YEAR, base)


def test_wilson_interval_brackets_the_estimate():
    lo, hi = analyze.wilson(50, 600)
    assert lo < 50 / 600 < hi
    # A wider sample gives a tighter interval.
    lo2, hi2 = analyze.wilson(500, 6000)
    assert (hi2 - lo2) < (hi - lo)


def test_wilson_handles_the_degenerate_cases():
    assert analyze.wilson(0, 0) == (0.0, 0.0)
    lo, hi = analyze.wilson(0, 100)
    assert lo == 0.0 and 0.0 < hi < 0.1


def test_mean_ci_brackets_the_mean():
    x = np.random.default_rng(1).normal(1500, 40, 500)
    lo, hi = analyze.mean_ci(x)
    assert lo < x.mean() < hi


def test_qb_band_labels():
    assert analyze.qb_band(2) == "2-3"
    assert analyze.qb_band(9) == "8-9"
    assert analyze.qb_band(14) == "10+"
    assert analyze.qb_band(1) == "1"
    assert analyze.qb_band(0) == "never"
