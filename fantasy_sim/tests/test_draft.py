"""Draft rules and the aggregate shape of simulated drafts."""
from __future__ import annotations

import numpy as np

from fantasy_sim import draft
from fantasy_sim.config import (DRAFT_POS_CAP, DRAFT_POS_MIN, DST, K,
                                KDST_EARLIEST_ROUND, LEAGUE, PERSONAS_2025,
                                POS_NAMES, QB, RB, WR, season_config)


def drafts(sd, n=30, seed=5):
    rng = np.random.default_rng(seed)
    scfg = season_config(2025)
    for _ in range(n):
        personas = draft.sample_personas(rng, PERSONAS_2025, LEAGUE.n_teams)
        yield draft.run_draft(sd, rng, personas, LEAGUE, scfg)


def test_every_roster_is_legal(real):
    _, _, sd = real
    for rosters, _, _ in drafts(sd, n=12):
        for team in rosters:
            picks = [p for p in team if p >= 0]
            assert len(picks) == LEAGUE.draft_rounds
            assert len(set(picks)) == len(picks)
            counts = np.bincount(sd.pos[picks], minlength=6)
            for p, cap in DRAFT_POS_CAP.items():
                assert counts[p] <= cap, f"{POS_NAMES[p]} cap breached"
            for p, need in DRAFT_POS_MIN.items():
                assert counts[p] >= need, f"{POS_NAMES[p]} minimum not met"


def test_kickers_and_defences_wait_until_the_end(real):
    _, _, sd = real
    for rosters, pick_of, _ in drafts(sd, n=8):
        for team in rosters:
            for rnd, p in enumerate(team, start=1):
                if p >= 0 and sd.pos[p] in (K, DST):
                    assert rnd >= KDST_EARLIEST_ROUND


def test_round_one_is_running_backs_and_receivers_only(real):
    _, _, sd = real
    for rosters, _, _ in drafts(sd, n=12):
        for team in rosters:
            assert sd.pos[team[0]] in (RB, WR)


def test_quarterbacks_drafted_per_league_matches_2025(real):
    _, _, sd = real
    counts = []
    for rosters, _, _ in drafts(sd, n=25):
        picks = rosters[rosters >= 0]
        counts.append(int((sd.pos[picks] == QB).sum()))
    assert 19.0 <= np.mean(counts) <= 23.0, np.mean(counts)


def test_simulated_adp_tracks_the_board(real):
    _, _, sd = real
    total = np.zeros(sd.n)
    seen = np.zeros(sd.n)
    for _, pick_of, _ in drafts(sd, n=40):
        m = pick_of > 0
        total[m] += pick_of[m]
        seen[m] += 1
    avg = np.where(seen > 0, total / np.maximum(seen, 1), np.nan)
    m = (seen >= 20) & (sd.adp < 200)
    assert np.corrcoef(avg[m], sd.adp[m])[0, 1] > 0.9


def test_personas_shape_rosters_without_dictating_them(real):
    """Each persona leaves the signature the 2025 advice describes.

    They are tendencies, not rules: Zero RB still ends up with backs, and it is
    the *average* timing that separates the personas.
    """
    _, _, sd = real
    rng = np.random.default_rng(11)
    scfg = season_config(2025)
    first_rb, first_qb, first_te = {}, {}, {}
    for _ in range(40):
        personas = draft.sample_personas(rng, PERSONAS_2025, LEAGUE.n_teams)
        rosters, _, _ = draft.run_draft(sd, rng, personas, LEAGUE, scfg)
        for t, team in enumerate(rosters):
            name = draft.PERSONA_NAMES[personas[t]]
            for store, p in ((first_rb, RB), (first_qb, QB), (first_te, 3)):
                rounds = [r + 1 for r, pl in enumerate(team) if sd.pos[pl] == p]
                store.setdefault(name, []).append(rounds[0] if rounds else 17)

    def mean(store, name):
        return float(np.mean(store[name]))

    # Running-back timing separates Robust RB, Hero RB and Zero RB.
    assert mean(first_rb, "robust_rb") < mean(first_rb, "balanced")
    assert mean(first_rb, "zero_rb") > mean(first_rb, "balanced") + 2.0
    assert mean(first_rb, "hero_rb") < mean(first_rb, "balanced")
    # Quarterback timing separates the QB personas.
    assert mean(first_qb, "early_qb") < mean(first_qb, "balanced")
    assert mean(first_qb, "late_qb") > mean(first_qb, "balanced")
    assert mean(first_qb, "qb_streamer") > 9.5
    # Tight-end timing separates the TE personas.
    assert mean(first_te, "elite_te") < mean(first_te, "balanced") - 2.0
    assert mean(first_te, "elite_te_early_qb") < 5.0
    # ...but no persona is absolute: Zero RB still drafts running backs.
    assert mean(first_rb, "zero_rb") < 12.0


def test_the_counterfactual_lever_actually_forces_the_round(real):
    _, _, sd = real
    rng = np.random.default_rng(3)
    scfg = season_config(2025)
    for target in (3, 9):
        personas = draft.sample_personas(rng, PERSONAS_2025, LEAGUE.n_teams)
        rosters, _, _ = draft.run_draft(sd, rng, personas, LEAGUE, scfg,
                                        qb_round={0: target})
        qb_rounds = [r + 1 for r, p in enumerate(rosters[0]) if sd.pos[p] == QB]
        assert qb_rounds and min(qb_rounds) == target
