"""The cleaned season must contain no information from after kickoff."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from fantasy_sim import scoring
from fantasy_sim.config import POS_NAMES


def test_no_scoring_week_carries_a_zero_projection(real):
    """The leak the build spec calls out.

    A source zeroes a weekly projection for any week the player ended up
    missing, including the week he got hurt mid-game -- so a week where he
    scored points must never come with a projection of zero unless he was
    officially unavailable before kickoff.
    """
    pool, arrays, _ = real
    proj, out, act = arrays["proj"], arrays["out"], arrays["act"]
    leaked = (proj <= 0) & ~out & (act > 0)
    assert leaked.sum() == 0, pool.player[np.where(leaked)[0][:5]].tolist()


def test_the_burrow_case_is_repaired(real):
    """2025 week 2: projection zero, seven points scored, because he was hurt
    during the game.  Weeks 3 to 12 he really was on injured reserve."""
    pool, arrays, _ = real
    hits = np.where(pool.player.to_numpy() == "Joe Burrow")[0]
    if not len(hits):
        pytest.skip("Joe Burrow not in this season's pool")
    i = int(hits[0])
    assert arrays["act"][i, 1] > 0
    assert arrays["proj"][i, 1] > 10, "week 2 projection was not restored"
    assert arrays["out"][i, 2:12].all(), "the injured-reserve weeks are missing"


def test_players_who_scored_were_not_marked_out_in_bulk(real):
    """Availability should be right nearly all the time; a handful of surprise
    activations is realistic, a systematic error is not."""
    pool, arrays, _ = real
    scored = arrays["act"] > 0
    wrong = scored & arrays["out"]
    assert wrong.sum() / max(scored.sum(), 1) < 0.02


def test_bye_weeks_come_from_the_schedule(real):
    """Every player on an NFL team has exactly one bye, and nobody is
    projected to score on it.  Free agents have no team and so no bye."""
    pool, arrays, _ = real
    byes = pool.bye.to_numpy()
    on_a_team = (pool.team != "FA").to_numpy()
    rows = np.where(byes > 0)[0]
    assert arrays["proj"][rows, byes[rows] - 1].max() == 0
    assert (byes[on_a_team] > 0).all(), \
        sorted(set(pool.team[on_a_team & (byes <= 0)]))
    # Each team's bye is shared by all of its players.
    per_team = pool[on_a_team].groupby("team").bye.nunique()
    assert (per_team == 1).all(), per_team[per_team > 1].to_dict()


def test_form_never_reads_the_current_week(real):
    """Rolling form at week w is built only from weeks before w."""
    _, arrays, sd = real
    i = int(np.argmax(arrays["act"].sum(1)))
    recent = [a for w, a in enumerate(sd.act[i]) if sd.played[i, w]]
    assert np.isnan(sd.form[i, 0])
    if len(recent) >= 4:
        first_played = int(np.argmax(sd.played[i]))
        assert np.isclose(sd.form[i, first_played + 1], sd.act[i, first_played])


def test_espn_scoring_reproduces_a_known_line():
    """300 passing yards, 2 TD, 1 INT = 12 + 8 - 2 = 18."""
    df = pd.DataFrame({"passing_yards": [300.0], "passing_tds": [2.0],
                       "passing_interceptions": [1.0]})
    assert np.isclose(scoring.score_offense(df).iloc[0], 18.0)


def test_kicker_scoring_uses_espn_distance_bands():
    df = pd.DataFrame({"fg_made_30_39": [1.0], "fg_made_40_49": [1.0],
                       "fg_made_50_59": [1.0], "pat_made": [2.0],
                       "fg_missed_20_29": [1.0]})
    # 3 + 4 + 5 + 2 - 2
    assert np.isclose(scoring.score_kicker(df).iloc[0], 12.0)


def test_pool_covers_every_position(real):
    pool, _, _ = real
    counts = pool.pos.value_counts()
    for p in POS_NAMES:
        assert counts.get(p, 0) >= 12, f"not enough {p} to fill a league"
