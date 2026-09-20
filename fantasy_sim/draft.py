"""Snake draft with human-shaped managers.

Every manager scores the whole board and takes the best score, where the score
is his own noisy read of ADP nudged by four things: the persona he drafts with,
the universal habits nearly all managers share (fill your starters, do not take
a backup quarterback early), the cliff at a position, and what he expects to
still be there at his next pick.

Personas tilt close calls.  They never override a large value gap -- a
receiver-leaning manager at pick one whose board says the top four are all
running backs still takes a running back.
"""
from __future__ import annotations

import numpy as np

from .config import (DRAFT_POS_CAP, DRAFT_POS_MIN, DST, K, KDST_EARLIEST_ROUND,
                     N_POS, POS_NAMES, QB, RB, TE, WR)

PERSONA_NAMES = [
    "balanced", "late_qb", "robust_rb", "hero_rb", "early_qb", "elite_te",
    "zero_rb", "elite_qb_only", "backup_qb_hoard", "elite_te_early_qb",
    "qb_streamer", "adaptive_vona", "rebalancer",
]
PERSONA_ID = {n: i for i, n in enumerate(PERSONA_NAMES)}

#: How many recent picks the run-aware drafter reads, and how strongly the
#: league-average positional mix anchors that read before evidence arrives.
RUN_WINDOW = 12
RUN_PRIOR = 6.0
#: How hard the run-aware drafter leans on a departure from normal pace.
RUN_SENSITIVITY = 1.0
#: Roughly the positional mix of a 16-round draft: QB RB WR TE K DST.
_PICK_RATE_PRIOR = np.array([0.13, 0.32, 0.38, 0.11, 0.03, 0.03])

#: Personas that deliberately skew their running-back timing.
_RB_TIMING = {PERSONA_ID["zero_rb"], PERSONA_ID["hero_rb"]}


def persona_bias(pid: int, rnd: int, counts: np.ndarray, out: np.ndarray) -> None:
    """Fill ``out`` (length 6) with this persona's tilt, in bias units.

    Positive favours the position.  One bias unit is worth ``bias_strength``
    picks on the board, so the same tilt matters more in round 11 than round 1.
    """
    out[:] = 0.0
    name = PERSONA_NAMES[pid]

    if name in ("balanced", "adaptive_vona", "rebalancer"):
        return

    if name == "late_qb":
        out[QB] = -1.8 if rnd < 8 else 0.5

    elif name == "robust_rb":
        out[RB] = 1.3 if rnd <= 5 else 0.2

    elif name == "hero_rb":
        if rnd <= 2:
            out[RB] = 2.0 if counts[RB] == 0 else -2.5
        elif rnd <= 5:
            out[RB] = -2.6
            out[WR] = 0.8
        else:
            out[RB] = 1.0

    elif name == "early_qb":
        if counts[QB] == 0:
            out[QB] = 2.6 if 3 <= rnd <= 5 else (-1.0 if rnd < 3 else 0.4)

    elif name == "elite_te":
        if counts[TE] == 0:
            out[TE] = 3.4 if 2 <= rnd <= 4 else (-0.5 if rnd < 2 else 0.0)

    elif name == "zero_rb":
        if rnd <= 6:
            out[RB] = -6.5 if rnd <= 4 else -4.0
            out[WR] = 1.0
            out[TE] = 0.6
        else:
            out[RB] = 1.6

    elif name == "elite_qb_only":
        # Take a top-tier quarterback in rounds 2-4 or wait until very late.
        if counts[QB] == 0:
            out[QB] = 2.6 if 2 <= rnd <= 4 else (-3.0 if rnd < 9 else 0.8)

    elif name == "backup_qb_hoard":
        out[QB] = 0.5 if counts[QB] == 0 else (1.1 if rnd >= 9 else 0.2)

    elif name == "elite_te_early_qb":
        if counts[TE] == 0 and rnd in (2, 3, 4):
            out[TE] = 5.0
        if counts[QB] == 0 and rnd in (3, 4, 5):
            out[QB] = 3.4
        if rnd < 2:
            out[QB] = out[TE] = -0.6

    elif name == "qb_streamer":
        out[QB] = -2.5 if rnd < 11 else 0.6


def universal_bias(pid: int, rnd: int, counts: np.ndarray, out: np.ndarray) -> None:
    """Habits almost every manager shares, whatever their persona."""
    out[:] = 0.0
    # Starters first: from round 6 a thin backfield or receiver room hurts.
    if rnd >= 6:
        if counts[RB] < 2:
            out[RB] += 1.6
        if counts[WR] < 2:
            out[WR] += 1.6
        if counts[TE] < 1 and rnd >= 9:
            out[TE] += 1.2
    # The 2025 running-back pool thinned faster than the receiver pool.
    if rnd >= 4 and counts[RB] == 1 and counts[WR] >= 1 and pid not in _RB_TIMING:
        out[RB] += 0.55


#: Absolute board penalties, in picks, for redundant positions.  The
#: quarterback figure is calibrated against the validation check that a league
#: drafts 20-22 of them, not chosen a priori.
BACKUP_QB_PENALTY = 20.0
BACKUP_TE_PENALTY = 30.0


def legal_mask(avail: np.ndarray, pos: np.ndarray, counts: np.ndarray,
               rnd: int, picks_left: int, round1_positions,
               qb_round: int = 0) -> np.ndarray:
    """Which available players this manager may actually take.

    ``qb_round`` is the counterfactual lever: force this manager to take his
    first quarterback in a given round (or, with a round past the end of the
    draft, never take one until the roster minimum makes him).
    """
    ok = avail.copy()
    if qb_round and counts[QB] == 0:
        if rnd < qb_round:
            ok &= pos != QB
        elif rnd == qb_round:
            forced = ok & (pos == QB)
            if forced.any():
                return forced
    for p in range(N_POS):
        if counts[p] >= DRAFT_POS_CAP[p]:
            ok &= pos != p
    if rnd < KDST_EARLIEST_ROUND:
        ok &= (pos != K) & (pos != DST)
    if rnd == 1:
        allowed = np.zeros(N_POS, dtype=bool)
        for p in round1_positions:
            allowed[p] = True
        ok &= allowed[pos]
    # If every remaining pick is needed to fill a mandatory slot, fill them.
    unmet = [p for p in range(N_POS) if counts[p] < DRAFT_POS_MIN[p]]
    if unmet and picks_left <= len(unmet):
        need = np.zeros(N_POS, dtype=bool)
        need[unmet] = True
        forced = ok & need[pos]
        if forced.any():
            ok = forced
    return ok


def cliff_and_lookahead(sd, avail: np.ndarray, pick_no: int, next_pick_no: int,
                        cliff_out: np.ndarray, look_out: np.ndarray) -> None:
    """Positional urgency, in bias units.

    ``cliff`` measures the drop from the best player left at a position to the
    next one -- a tier break that makes managers reach.  ``lookahead`` measures
    the drop from the best player left to whoever is likely to survive until
    this manager picks again, which is why the managers at the turn pair
    premium players.
    """
    cliff_out[:] = 0.0
    look_out[:] = 0.0
    vor = sd.draft_vor
    adp = sd.adp
    for p in range(N_POS):
        sel = np.where(avail & (sd.pos == p))[0]
        if len(sel) < 2:
            continue
        order = sel[np.argsort(-vor[sel])]
        best = vor[order[0]]
        cliff_out[p] = np.clip((best - vor[order[1]]) / 3.0, 0.0, 1.2)
        # Who is realistically still on the board next time round?
        survivors = order[adp[order] >= next_pick_no]
        nxt = vor[survivors[0]] if len(survivors) else vor[order[-1]]
        look_out[p] = np.clip((best - nxt) / 4.0, 0.0, 1.5)


def run_aware_lookahead(sd, avail: np.ndarray, pos_rate: np.ndarray, gap: int,
                        out: np.ndarray) -> None:
    """Lookahead that reads the room instead of the preseason ADP sheet.

    ``cliff_and_lookahead`` asks "who does August say will still be here at my
    next pick?".  That answer is fixed before the draft starts, so a manager
    using it sits through a six-deep run on running backs without blinking.
    This asks the same question of *this* draft: positions are coming off the
    board at the rates in ``pos_rate``, so roughly ``pos_rate[p] * gap`` more
    players go at position ``p`` before I am back on the clock.  The gap
    between the best one left and the one that deep is what waiting costs.
    """
    out[:] = 0.0
    vor = sd.draft_vor
    for p in range(N_POS):
        sel = np.where(avail & (sd.pos == p))[0]
        if len(sel) < 2:
            continue
        order = sel[np.argsort(-vor[sel])]
        taken = int(round(pos_rate[p] * gap))
        nxt = vor[order[min(taken, len(order) - 1)]]
        out[p] = np.clip((vor[order[0]] - nxt) / 4.0, 0.0, 1.5)


def snake_order(n_teams: int, rounds: int) -> np.ndarray:
    """Draft-slot index for every overall pick."""
    base = np.arange(n_teams)
    out = np.empty(n_teams * rounds, dtype=np.int16)
    for r in range(rounds):
        seq = base if r % 2 == 0 else base[::-1]
        out[r * n_teams:(r + 1) * n_teams] = seq
    return out


def run_draft(sd, rng: np.random.Generator, personas: np.ndarray,
              cfg, season_cfg, trace: list | None = None,
              qb_round: dict | None = None):
    """Run one 16-round snake draft from a random draft order.

    Returns ``(rosters, pick_of_player, slot_of_team)`` where ``rosters`` is
    ``n_teams x rounds`` of player indices and ``slot_of_team`` gives each
    team's 0-based draft slot.
    """
    n_teams = cfg.n_teams
    rounds = cfg.draft_rounds
    n_picks = n_teams * rounds
    team_at_slot = rng.permutation(n_teams)
    slot_of_team = np.empty(n_teams, dtype=np.int16)
    slot_of_team[team_at_slot] = np.arange(n_teams)
    slots = team_at_slot[snake_order(n_teams, rounds)]

    # Each manager reads the board through his own noise.
    boards = sd.adp[None, :] + rng.normal(0.0, 1.0, (n_teams, sd.n)) * sd.adp_sd[None, :]
    # A few managers just autodraft off ADP; a few love a particular player.
    autodraft = rng.random(n_teams) < 0.08
    favourite = rng.integers(0, sd.n, n_teams)
    fav_strength = rng.uniform(12.0, 26.0, n_teams)

    avail = np.ones(sd.n, dtype=bool)
    counts = np.zeros((n_teams, N_POS), dtype=np.int16)
    rosters = np.full((n_teams, rounds), -1, dtype=np.int32)
    recent = np.zeros(n_picks, dtype=np.int64)   # position taken at each pick
    pick_of = np.full(sd.n, -1, dtype=np.int16)

    pbias = np.zeros(N_POS)
    ubias = np.zeros(N_POS)
    cliff = np.zeros(N_POS)
    hot = np.zeros(N_POS)
    norm = np.zeros(N_POS)
    look = np.zeros(N_POS)
    score = np.empty(sd.n)

    for pick in range(n_picks):
        m = int(slots[pick])
        rnd = pick // n_teams + 1
        picks_left = rounds - (rnd - 1)
        # When does this manager pick again?
        future = np.where(slots[pick + 1:] == m)[0]
        next_pick_no = pick + 2 + int(future[0]) if len(future) else n_picks + 1

        ok = legal_mask(avail, sd.pos, counts[m], rnd, picks_left,
                        season_cfg.round1_positions,
                        (qb_round or {}).get(m, 0))
        if not ok.any():
            ok = avail.copy()

        score[:] = boards[m]
        if not autodraft[m]:
            persona_bias(int(personas[m]), rnd, counts[m], pbias)
            universal_bias(int(personas[m]), rnd, counts[m], ubias)
            cliff_and_lookahead(sd, ok, pick + 1, next_pick_no, cliff, look)
            if PERSONA_NAMES[personas[m]] == "adaptive_vona":
                # React to the *deviation* from normal pace, not to pace
                # itself.  Running backs and receivers always leave the board
                # quickly because there are more slots to fill, and a drafter
                # that treats raw speed as urgency simply reaches at those two
                # positions all draft long.  Measuring the observed rate
                # against the rate that was expected anyway isolates the part
                # that is actually a run.
                seen = recent[max(0, pick - RUN_WINDOW):pick]
                gap_to_next = next_pick_no - (pick + 1)
                rate = _PICK_RATE_PRIOR * RUN_PRIOR
                if len(seen):
                    rate = rate + np.bincount(seen, minlength=N_POS)
                rate = rate / rate.sum()
                run_aware_lookahead(sd, ok, rate, gap_to_next, hot)
                run_aware_lookahead(sd, ok, _PICK_RATE_PRIOR, gap_to_next, norm)
                look += RUN_SENSITIVITY * (hot - norm)
            strength = max(3.0, 0.18 * (pick + 1))
            tilt = (pbias + ubias + cliff + look) * strength
            score -= tilt[sd.pos]
            if counts[m, QB] >= 1 and PERSONA_NAMES[personas[m]] != "backup_qb_hoard":
                score[sd.pos == QB] += BACKUP_QB_PENALTY
            if counts[m, TE] >= 1:
                score[sd.pos == TE] += BACKUP_TE_PENALTY
            # An occasional reach for a guy the manager just likes.
            if rng.random() < 0.04:
                score[favourite[m]] -= fav_strength[m]

        score[~ok] = np.inf
        choice = int(np.argmin(score))
        avail[choice] = False
        counts[m, sd.pos[choice]] += 1
        recent[pick] = sd.pos[choice]
        rosters[m, rnd - 1] = choice
        pick_of[choice] = pick + 1
        if trace is not None:
            trace.append((pick + 1, rnd, m, choice, POS_NAMES[sd.pos[choice]]))

    return rosters, pick_of, slot_of_team


def sample_personas(rng: np.random.Generator, weights: dict, n_teams: int) -> np.ndarray:
    names = list(weights)
    p = np.array([weights[n] for n in names], dtype=float)
    p /= p.sum()
    draw = rng.choice(len(names), size=n_teams, p=p)
    return np.array([PERSONA_ID[names[d]] for d in draw], dtype=np.int8)
