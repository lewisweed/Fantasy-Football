"""The cleaned season must contain no information from after kickoff."""
from __future__ import annotations

import numpy as np
import pandas as pd

from fantasy_sim import scoring
from fantasy_sim.config import POS_NAMES


def test_projection_is_only_zeroed_when_the_player_is_known_out(real):
    """The leak the build spec calls out: a projection must never be zeroed
    just because the player turned out not to play."""
    pool, arrays, _ = real
    proj, out = arrays["proj"], arrays["out"]
    zeroed_but_available = (proj <= 0) & ~out
    assert zeroed_but_available.sum() == 0


def test_players_who_scored_were_not_marked_out_in_bulk(real):
    """Availability should be right nearly all the time; a handful of surprise
    activations is realistic, a systematic error is not."""
    pool, arrays, _ = real
    scored = arrays["act"] > 0
    wrong = scored & arrays["out"]
    assert wrong.sum() / max(scored.sum(), 1) < 0.02


def test_bye_weeks_come_from_the_schedule(real):
    pool, arrays, _ = real
    byes = pool.bye.to_numpy()
    has_bye = byes > 0
    # Every team's players share one bye, and nobody is projected on it.
    rows = np.where(has_bye)[0]
    assert arrays["proj"][rows, byes[rows] - 1].max() == 0
    assert 0.9 < has_bye.mean() <= 1.0


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
