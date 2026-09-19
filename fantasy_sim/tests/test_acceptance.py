"""The manager behaviours the build spec asks for, one test each.

These are the behaviours from section 5.3 -- the ones that decide whether the
simulated managers look like people trying to win.  Each is set up as a small
hand-built league situation so the answer is unambiguous.
"""
from __future__ import annotations

import numpy as np
import pytest

from fantasy_sim import season, values
from fantasy_sim.config import ACTIVITY_PARAMS, LEAGUE, season_config
from .conftest import bare_sim, build_sd, make_team

N_WEEKS = 17


def filler(n, pos, prefix, prior, **kw):
    return [dict(name=f"{prefix}{i}", pos=pos, team=f"F{prefix}{i}",
                 prior=prior, **kw) for i in range(n)]


def base_roster_spec():
    """A plain, legal 16-man roster: 1 QB, 5 RB, 6 WR, 2 TE, 1 K, 1 DST."""
    return (filler(1, "QB", "qb", 16.0) + filler(5, "RB", "rb", 10.0)
            + filler(6, "WR", "wr", 10.0) + filler(2, "TE", "te", 7.0)
            + filler(1, "K", "k", 8.0) + filler(1, "DST", "dst", 6.0))


# --------------------------------------------------------------------------
def test_promoted_backup_replaces_a_lottery_ticket():
    """A round-10 lottery receiver is dropped for the obvious beneficiary when
    the starter ahead of him goes down."""
    week = 6
    roster = base_roster_spec()
    # The last receiver on the roster is the lottery ticket: nothing behind it.
    roster[-4] = dict(name="lottery_wr", pos="WR", team="LOT", prior=4.0,
                      proj=4.0, act=3.0)
    extra = [
        dict(name="hurt_starter_rb", pos="RB", team="BEN", prior=15.0, depth=1,
             proj=[15.0] * N_WEEKS, out=[w >= week - 1 for w in range(N_WEEKS)]),
        dict(name="beneficiary_rb", pos="RB", team="BEN", prior=5.0, depth=2,
             proj=[5.0] * (week - 1) + [14.0] * (N_WEEKS - week + 1)),
        dict(name="dull_wr", pos="WR", team="DUL", prior=6.0, proj=6.0),
    ]
    sd = build_sd(roster + extra)
    sim = bare_sim(sd)
    mine = list(range(len(roster)))
    team = make_team(sim, mine)
    sim.free[len(roster)] = False          # the hurt starter belongs to someone

    vals, opt = sim.team_values(team, week)
    moves = sim.candidate_moves(team, week, vals, opt, sim.free)
    assert moves, "manager saw no move at all"
    gain, add, drop = moves[0]
    assert sd.name[add] == "beneficiary_rb", sd.name[add]
    assert sd.name[drop] == "lottery_wr", sd.name[drop]


def test_handcuff_speculation_depends_on_how_thin_the_backfield_is():
    """A weak running-back room speculates on a star's backup when the star is
    Questionable; a strong one has better things to do with the roster spot."""
    week = 5
    quest = [w == week - 1 for w in range(N_WEEKS)]
    shared = [
        dict(name="star_rb", pos="RB", team="STR", prior=18.0, depth=1,
             proj=18.0, quest=quest),
        dict(name="handcuff_rb", pos="RB", team="STR", prior=4.0, depth=2,
             proj=4.0),
        dict(name="steady_wr", pos="WR", team="STD", prior=7.5, proj=7.5),
    ]
    gains = {}
    for label, rb_prior in (("weak", 5.0), ("strong", 15.0)):
        roster = (filler(1, "QB", "qb", 16.0) + filler(5, "RB", "rb", rb_prior)
                  + filler(6, "WR", "wr", 10.0) + filler(2, "TE", "te", 7.0)
                  + filler(1, "K", "k", 8.0) + filler(1, "DST", "dst", 6.0))
        sd = build_sd(roster + shared)
        sim = bare_sim(sd)
        team = make_team(sim, list(range(len(roster))))
        sim.free[len(roster)] = False          # the star is owned elsewhere
        vals, opt = sim.team_values(team, week)
        moves = sim.candidate_moves(team, week, vals, opt, sim.free)
        hc = next((g for g, a, _ in moves if sd.name[a] == "handcuff_rb"), -99.0)
        gains[label] = hc
    assert gains["weak"] > gains["strong"], gains


def test_stafford_drop_an_underperforming_early_pick_for_a_hot_waiver_qb():
    """The user's own 2025 season: the drafted quarterback throws
    interceptions, underperforms and gets hurt; the hot waiver quarterback is
    worth the roster spot."""
    week = 8
    bad = [22.0] + [6.0] * 6 + [0.0] * (N_WEEKS - 7)
    roster = base_roster_spec()
    roster[0] = dict(name="purdy", pos="QB", team="PUR", prior=17.0,
                     proj=[18.0] * 6 + [0.0] * (N_WEEKS - 6), act=bad,
                     out=[w >= 6 for w in range(N_WEEKS)])
    extra = [dict(name="stafford", pos="QB", team="STA", prior=7.0,
                  proj=[8.0] * 4 + [17.0] * (N_WEEKS - 4),
                  act=[7.0] * 4 + [26.0] * (N_WEEKS - 4))]
    sd = build_sd(roster + extra)
    sim = bare_sim(sd)
    team = make_team(sim, list(range(len(roster))),
                     first_qb_round=7)     # not an elite-QB drafter
    team.draft_pick_round = {0: 5}
    vals, opt = sim.team_values(team, week)
    moves = sim.candidate_moves(team, week, vals, opt, sim.free)
    gain, add, drop = moves[0]
    assert sd.name[add] == "stafford", sd.name[add]
    assert sd.name[drop] == "purdy", sd.name[drop]


def test_stafford_do_not_churn_a_hot_qb_for_a_better_one_week_projection():
    """Having found the hot quarterback, the manager keeps him: the streamer's
    single good week does not beat sustained form, and a second quarterback
    would cost a bench spot."""
    week = 11
    roster = base_roster_spec()
    roster[0] = dict(name="stafford", pos="QB", team="STA", prior=7.0,
                     proj=[17.0] * N_WEEKS, act=[26.0] * N_WEEKS)
    extra = [dict(name="streamer_qb", pos="QB", team="STR", prior=6.0,
                  # Better *this* week, worse everywhere else.
                  proj=[9.0] * (week - 1) + [21.0] + [9.0] * (N_WEEKS - week),
                  act=[9.0] * N_WEEKS)]
    sd = build_sd(roster + extra)
    sim = bare_sim(sd)
    team = make_team(sim, list(range(len(roster))), threshold=1.0)
    vals, opt = sim.team_values(team, week)
    moves = sim.candidate_moves(team, week, vals, opt, sim.free)
    wanted = [m for m in moves if m[0] > team.threshold]
    assert all(sd.name[a] != "streamer_qb" for _, a, _ in wanted), \
        "manager churned a productive QB for a one-week projection"
    assert all(sd.name[d] != "stafford" for _, _, d in wanted)


def test_an_elite_quarterback_drafter_does_not_shop_for_quarterbacks():
    """Persona leaves a residue: the manager who spent a third-round pick on a
    quarterback is not in the market for another one."""
    week = 7
    roster = base_roster_spec()
    roster[0] = dict(name="elite_qb", pos="QB", team="ELI", prior=21.0, proj=21.0)
    extra = [dict(name="good_waiver_qb", pos="QB", team="WAV", prior=16.0,
                  proj=16.0, act=16.0)]
    sd = build_sd(roster + extra)
    results = {}
    for label, rnd in (("elite", 3), ("late", 11)):
        sim = bare_sim(sd)
        team = make_team(sim, list(range(len(roster))), first_qb_round=rnd)
        vals, opt = sim.team_values(team, week)
        moves = sim.candidate_moves(team, week, vals, opt, sim.free)
        results[label] = next(
            (g for g, a, _ in moves if sd.name[a] == "good_waiver_qb"), -99.0)
    assert results["elite"] < results["late"], results


def test_injured_stars_are_stashed_not_cut_for_a_streaming_kicker():
    """The failure mode this guards against: an injured first-round pick coming
    out cheaper to drop than a bench receiver because his projection is zero."""
    week = 9
    roster = base_roster_spec()
    roster[1] = dict(name="hurt_star_rb", pos="RB", team="HSR", prior=17.0,
                     proj=[17.0] * 6 + [0.0] * (N_WEEKS - 6),
                     act=[20.0] * 6 + [0.0] * (N_WEEKS - 6),
                     out=[w >= 6 for w in range(N_WEEKS)])
    extra = [dict(name="better_kicker", pos="K", team="BK", prior=9.5, proj=9.5)]
    sd = build_sd(roster + extra)
    sim = bare_sim(sd)
    team = make_team(sim, list(range(len(roster))))
    team.draft_pick_round = {1: 1}
    vals, opt = sim.team_values(team, week)
    idx = np.array(team.roster)
    sw = values.starter_weakness(idx, sd, vals, week)
    base = values.roster_value(idx, sd, vals, sd.proj[:, week - 1], opt, sw)

    def cost(p):
        rest = idx[idx != p]
        return base - values.roster_value(rest, sd, vals, sd.proj[:, week - 1], opt, sw)

    star = int(np.where(sd.name == "hurt_star_rb")[0][0])
    bench_wr = int(np.where(sd.name == "wr5")[0][0])
    assert cost(star) > cost(bench_wr), (cost(star), cost(bench_wr))


def test_an_approach_shifts_with_the_standings():
    """Section 5.3: a team at 1-5 takes more upside swings, a 7-1 team plays
    it safe."""
    sd = build_sd(base_roster_spec())
    sim = bare_sim(sd)
    losing = make_team(sim, list(range(16)), tid=0)
    winning = make_team(sim, list(range(16)), tid=1)
    losing.wins, losing.losses = 1, 5
    winning.wins, winning.losses = 7, 1
    even = make_team(sim, list(range(16)), tid=2)
    even.wins, even.losses = 3, 3
    assert sim.risk_appetite(losing) > sim.risk_appetite(even) > sim.risk_appetite(winning)
    # Early on, before anyone knows anything, nobody has shifted yet.
    fresh = make_team(sim, list(range(16)), tid=3)
    fresh.wins, fresh.losses = 2, 1
    assert sim.risk_appetite(fresh) == 1.0


def test_a_bye_makes_a_backup_worth_carrying():
    """Section 5.2: a bench quarterback is worth something when the starter has
    a bye coming, and close to nothing when he does not."""
    week = 5
    roster = base_roster_spec()
    weakness = {}
    for label, bye in (("bye_soon", week + 1), ("no_bye", 0)):
        roster[0] = dict(name="qb_starter", pos="QB", team="QBT", prior=20.0,
                         proj=20.0, bye=bye)
        sd = build_sd(roster)
        sim = bare_sim(sd)
        team = make_team(sim, list(range(len(roster))))
        vals, _ = sim.team_values(team, week)
        sw = values.starter_weakness(np.array(team.roster), sd, vals, week)
        weakness[label] = sw[0]
    assert weakness["bye_soon"] > weakness["no_bye"]
    assert values.bench_boost(0, np.array([weakness["bye_soon"], 0, 0, 0, 0, 0])) > \
           values.bench_boost(0, np.array([weakness["no_bye"], 0, 0, 0, 0, 0]))


def test_a_bye_week_never_earns_an_injured_reserve_slot():
    week = 5
    roster = base_roster_spec()
    roster[2] = dict(name="bye_rb", pos="RB", team="BYE", prior=12.0, bye=week)
    roster[3] = dict(name="hurt_rb", pos="RB", team="HRT", prior=12.0,
                     out=[w >= 2 for w in range(N_WEEKS)])
    sd = build_sd(roster)
    sim = bare_sim(sd)
    team = make_team(sim, list(range(len(roster))))
    sim.manage_ir(team, week)
    assert [sd.name[p] for p in team.ir] == ["hurt_rb"]


# --------------------------------------------------------------------------
# Aggregate behaviours, measured on real simulated leagues
# --------------------------------------------------------------------------
@pytest.fixture(scope="module")
def sims(real):
    _, _, sd = real
    out = []
    for s in range(6):
        sim = season.LeagueSim(sd, LEAGUE, season_config(2025), 9000 + s)
        out.append((sim, sim.run()))
    return out


def test_move_counts_by_activity(sims):
    """Section 5.5: 15-30 moves for an active manager, 8-15 moderate, 2-6 lazy."""
    got = {0: [], 1: [], 2: []}
    for _, res in sims:
        for a, n in zip(res["activity"], res["adds"]):
            got[int(a)].append(int(n))
    bands = {0: (15, 30), 1: (8, 15), 2: (2, 6)}
    for a, (lo, hi) in bands.items():
        mu = float(np.mean(got[a]))
        assert lo <= mu <= hi, (a, mu)


def test_active_managers_stream_kickers_and_defences_and_lazy_ones_do_not(real):
    """Section 5.3: most active managers stream K and D/ST by matchup; lazy
    managers rarely bother."""
    from fantasy_sim.config import DST, K
    from fantasy_sim.trace import Tracer
    _, _, sd = real
    churn = {0: [], 1: [], 2: []}
    for s in range(5):
        tr = Tracer(team=None)
        sim = season.LeagueSim(sd, LEAGUE, season_config(2025), 9100 + s, tracer=tr)
        sim.run()
        per_team = {t.tid: 0 for t in sim.teams}
        for week, tid, kind, p, reason in tr.moves:
            if kind == "ADD" and sd.pos[p] in (K, DST):
                per_team[tid] += 1
        for t in sim.teams:
            churn[t.activity].append(per_team[t.tid])
    assert np.mean(churn[0]) > np.mean(churn[2]) + 1.0, \
        {k: float(np.mean(v)) for k, v in churn.items()}
    assert np.mean(churn[0]) >= 1.0


def test_no_team_hoards_quarterbacks(sims):
    over = []
    for sim, _ in sims:
        for t in sim.teams:
            over.append(sum(1 for p in t.all_players() if sim.sd.pos[p] == 0) >= 3)
    assert np.mean(over) < 0.05, np.mean(over)


def test_lazy_managers_make_more_lineup_mistakes(sims):
    """Section 5.3: lazy managers sometimes start an injured or bye player."""
    assert ACTIVITY_PARAMS["lazy"]["sloppy"] > ACTIVITY_PARAMS["active"]["sloppy"] * 3


def test_every_team_finishes_with_a_legal_roster(sims):
    for sim, _ in sims:
        for t in sim.teams:
            assert len(t.roster) <= LEAGUE.roster_size
            assert len(t.ir) <= LEAGUE.ir_slots
            assert len(set(t.all_players())) == len(t.all_players())


def test_the_same_seed_gives_the_same_league(real):
    _, _, sd = real
    a = season.LeagueSim(sd, LEAGUE, season_config(2025), 4242).run()
    b = season.LeagueSim(sd, LEAGUE, season_config(2025), 4242).run()
    for k in a:
        assert np.array_equal(a[k], b[k]), k


def test_records_and_playoffs_add_up(sims):
    for _, res in sims:
        assert set((res["wins"] + res["losses"] + res["ties"]
                    if "ties" in res else res["wins"] + res["losses"])) == {14}
        assert res["playoffs"].sum() == LEAGUE.playoff_teams
        assert res["champion"].sum() == 1
        assert res["runner_up"].sum() == 1
        assert res["champion"][res["playoffs"]].sum() == 1
