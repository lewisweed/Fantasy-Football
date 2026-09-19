"""How a manager values a player, and how he values his roster.

Two ideas do most of the work here.

**Player value** is a blend of what the player was expected to be on draft day
and what he has looked like since, with the weight on draft day decaying as
evidence accumulates.  Managers disagree: each one carries a persistent,
multiplicative opinion of every player, so two teams looking at the same waiver
wire see different bargains.

**Roster value** is what moves are actually judged against.  A manager does not
compare two players in isolation; he asks whether his team gets better.  That
makes the bench worth something -- injury insurance behind thin starters, a
backup quarterback when his starter is shaky or on bye, and lottery tickets
whose value is the chance their role expands.  It is also why a good player on
a roster that cannot start him is worth less than his raw score suggests.
"""
from __future__ import annotations

import numpy as np

from .config import DST, K, N_POS, QB, RB, TE, WR

# Bench weights: what the nth-best bench player at a position is worth, as a
# fraction of his standalone value.  RB/WR depth starts high (byes, injuries and
# flex weeks mean it gets used); a third quarterback is worth essentially zero.
BENCH_WEIGHTS = {
    QB: (0.08, 0.005),
    RB: (0.34, 0.20, 0.11, 0.05, 0.02),
    WR: (0.32, 0.19, 0.10, 0.05, 0.02),
    TE: (0.14, 0.04, 0.01),
    K:  (0.03, 0.0),
    DST: (0.05, 0.01),
}
MAX_BENCH_W = 6


def bench_weight_table() -> np.ndarray:
    """``[position, depth]`` lookup so the hot path never touches a dict."""
    t = np.zeros((N_POS, MAX_BENCH_W))
    for p, ws in BENCH_WEIGHTS.items():
        for i, w in enumerate(ws[:MAX_BENCH_W]):
            t[p, i] = w
    return t


BW = bench_weight_table()


# --------------------------------------------------------------------------
# Season-wide precomputation (identical for every league, so done once)
# --------------------------------------------------------------------------
class SeasonData:
    """Immutable, league-independent arrays the simulation reads from."""

    def __init__(self, pool, arrays, n_weeks: int):
        self.n_weeks = n_weeks
        self.n = len(pool)
        self.name = pool["player"].to_numpy()
        self.pos = pool["pos_id"].to_numpy().astype(np.int8)
        self.team = pool["team"].to_numpy()
        self.adp = pool["adp"].to_numpy().astype(np.float64)
        self.adp_sd = pool["adp_sd"].to_numpy().astype(np.float64)
        self.prior = pool["prior_ppg"].to_numpy().astype(np.float64)
        self.bye = pool["bye"].to_numpy().astype(np.int8)
        self.proj = arrays["proj"].astype(np.float64)
        self.act = arrays["act"].astype(np.float64)
        self.out = arrays["out"]
        self.quest = arrays["quest"]
        self.played = arrays["played"]
        self.depth = arrays["depth"]

        self.is_bye = np.zeros((self.n, n_weeks), dtype=bool)
        for i, b in enumerate(self.bye):
            if 1 <= b <= n_weeks:
                self.is_bye[i, b - 1] = True
        #: Unavailable for a reason a manager can stash on IR (not a bye).
        self.injured = self.out & ~self.is_bye

        self._form()
        self._roles()
        self._replacement()
        self._draft_vor()

    # -- form ------------------------------------------------------------
    def _form(self):
        """Rolling average of the last three games actually played.

        Week ``w`` only ever reads weeks strictly before ``w``.
        """
        n, W = self.n, self.n_weeks
        form = np.zeros((n, W))
        ngames = np.zeros((n, W), dtype=np.int16)
        out_streak = np.zeros((n, W), dtype=np.int16)
        for i in range(n):
            recent: list[float] = []
            g = 0
            streak = 0
            for w in range(W):
                form[i, w] = np.mean(recent[-3:]) if recent else np.nan
                ngames[i, w] = g
                out_streak[i, w] = streak
                if self.played[i, w] and not self.out[i, w]:
                    recent.append(self.act[i, w])
                    g += 1
                    streak = 0
                elif self.out[i, w]:
                    streak += 1
        self.form = form
        self.ngames = ngames
        self.out_streak = out_streak

    # -- depth-chart roles ------------------------------------------------
    def _roles(self):
        """Who is ahead of each player week by week, and how likely a promotion is.

        The weekly depth chart is the real signal; draft cost only breaks ties
        for players the depth chart does not list.
        """
        n, W = self.n, self.n_weeks
        groups: dict = {}
        for i in range(n):
            if self.pos[i] in (QB, RB, WR, TE):
                groups.setdefault((self.team[i], int(self.pos[i])), []).append(i)

        ahead = np.full((n, W), -1, dtype=np.int32)
        for idxs in groups.values():
            arr = np.array(sorted(idxs, key=lambda i: self.adp[i]))
            for w in range(W):
                d = self.depth[arr, w].astype(int)
                order = np.lexsort((np.arange(len(arr)), d))
                avail = ~self.out[arr, w]
                starter_j = next((j for j in order if avail[j]), order[0])
                starter = int(arr[starter_j])
                ahead[arr, w] = starter
                ahead[starter, w] = -1
        self.ahead = ahead

        # P(role expands) rises sharply when the man ahead is hurt or sitting.
        base = np.where(self.pos == RB, 0.075, 0.045)[:, None]
        pexp = np.where(ahead >= 0, np.repeat(base, W, axis=1), 0.0)
        rows, cols = np.where(ahead >= 0)
        if len(rows):
            a = ahead[rows, cols]
            pexp[rows, cols] += 0.55 * self.out[a, cols] + 0.18 * self.quest[a, cols]
        # A player who cannot play is not a lottery ticket this week.
        pexp = np.where(self.out, 0.0, pexp)
        self.p_expand = np.clip(pexp, 0.0, 0.85)

    def _draft_vor(self):
        """Draft-day value over replacement, the currency for tier breaks.

        Points per game are not comparable across positions on a draft board --
        every startable quarterback outscores every running back -- so urgency
        is measured against the last startable player at each position.
        """
        starters = {0: 13, 1: 32, 2: 40, 3: 13, 4: 12, 5: 12}
        vor = np.zeros(self.n)
        for p, k in starters.items():
            sel = np.where(self.pos == p)[0]
            if len(sel) == 0:
                continue
            order = sel[np.argsort(-self.prior[sel])]
            repl = self.prior[order[min(k, len(order)) - 1]]
            vor[sel] = self.prior[sel] - repl
        self.draft_vor = vor

    # -- replacement level -------------------------------------------------
    def _replacement(self):
        """Roughly the best player at each position a manager could stream."""
        rep = np.zeros((N_POS, self.n_weeks))
        # 12-team league: ~14 QB, 36 RB, 48 WR, 14 TE, 12 K, 12 DST rostered.
        depth_n = {QB: 16, RB: 40, WR: 54, TE: 16, K: 13, DST: 13}
        for p in range(N_POS):
            m = self.pos == p
            sub = self.proj[m]
            k = min(depth_n.get(p, 20), max(sub.shape[0] - 1, 1))
            part = np.sort(sub, axis=0)[::-1]
            rep[p] = part[k - 1] if part.shape[0] >= k else part[-1]
        self.replacement = rep


# --------------------------------------------------------------------------
# Per-manager valuation
# --------------------------------------------------------------------------
def prior_weight(week: int, trait: float) -> float:
    """Weight on the draft-day prior; decays over roughly half a season."""
    return float(np.clip(1.0 - (week - 1) / 8.0 + trait, 0.08, 1.0))


def player_values(sd: SeasonData, week: int, alpha: float,
                  opinion: np.ndarray) -> np.ndarray:
    """Each player's worth to one manager when he plays, in points per game.

    A player who is ruled out has a weekly projection of zero, which says
    nothing about how good he is -- so his projection is ignored that week and
    the evidence comes from his recent form instead.  Availability is priced
    separately, in :func:`option_value`, because a hurt star is still worth a
    roster spot and a hurt scrub is not.
    """
    w = week - 1
    form = sd.form[:, w]
    proj = np.where(sd.out[:, w], np.nan, sd.proj[:, w])
    have_form = np.isfinite(form)
    have_proj = np.isfinite(proj)
    evidence = np.where(
        have_form & have_proj, 0.45 * np.nan_to_num(proj) + 0.55 * np.nan_to_num(form),
        np.where(have_form, np.nan_to_num(form),
                 np.where(have_proj, np.nan_to_num(proj), sd.prior)))
    v = alpha * sd.prior + (1.0 - alpha) * evidence
    return np.maximum(v * opinion, 0.0)


def availability(sd: SeasonData, week: int) -> np.ndarray:
    """How much of a player's value is actually reachable from here.

    An injury bites harder the longer it drags on, but it never writes a star
    off completely -- that is what makes him worth stashing rather than cutting.
    """
    w = week - 1
    streak = np.maximum(sd.out_streak[:, w], 1)
    hurt = sd.injured[:, w]
    # A star keeps more of his value than a scrub through a short absence...
    floor = 0.18 + 0.32 * np.clip(sd.prior / 15.0, 0.0, 1.0)
    # ...but a month on the sidelines starts to look like a lost season.
    floor = floor * 0.8 ** np.maximum(streak - 3, 0)
    decay = np.maximum(0.82 ** streak, floor)
    return np.where(hurt, decay, 1.0)


def option_value(sd: SeasonData, week: int, values: np.ndarray,
                 avail: np.ndarray) -> np.ndarray:
    """What a bench player is worth beyond his slot weight.

    Two things live here.  A backup whose starter is hurt or sitting is a
    lottery ticket worth P(the role opens) x what the role pays.  An injured
    starter is worth stashing for what he will be when he returns, which is why
    managers carry them rather than cut them for a streaming kicker.
    """
    w = week - 1
    ahead = sd.ahead[:, w]
    val = np.zeros(sd.n)
    idx = np.where(ahead >= 0)[0]
    if len(idx):
        val[idx] = np.maximum(0.72 * values[ahead[idx]] - values[idx], 0.0)
    val *= sd.p_expand[:, w]

    hurt = sd.injured[:, w]
    over_replacement = np.maximum(values - sd.replacement[sd.pos, w], 0.0)
    val = val + np.where(hurt, 0.45 * over_replacement * avail, 0.0)
    return val


#: How much this week's lineup counts against season-long roster strength.
WEEK_WEIGHT = 0.30


def bench_boost(p: int, weakness: np.ndarray) -> float:
    """How much a bench spot at this position is really worth to this roster.

    Depth behind thin starters matters more.  A backup quarterback is close to
    worthless behind a healthy elite one and valuable behind a shaky one, which
    is what stops managers carrying two quarterbacks for no reason.
    """
    if p in FLEX_POS:
        return 1.0 + 0.9 * weakness[p]
    if p == QB:
        return 0.25 + 1.7 * weakness[QB]
    return 1.0


#: Starters required at each position before FLEX is filled.
SLOT_NEED = (1, 2, 2, 1, 1, 1)          # QB, RB, WR, TE, K, DST
FLEX_POS = (RB, WR, TE)


def _lineup(scores: list, poss: list):
    """Best legal lineup from plain Python lists.

    Filling the dedicated slots before FLEX is optimal here because FLEX takes a
    superset of RB/WR/TE and every other slot is single-position.  This runs
    tens of thousands of times per simulated season, so it avoids numpy.
    """
    buckets = ([], [], [], [], [], [])
    for i, p in enumerate(poss):
        buckets[p].append((scores[i], i))
    total = 0.0
    picked = []
    leftovers = []
    for p in range(N_POS):
        b = buckets[p]
        if not b:
            continue
        b.sort(reverse=True)
        need = SLOT_NEED[p]
        for sc, i in b[:need]:
            total += sc
            picked.append(i)
        if p in FLEX_POS:
            leftovers.extend(b[need:])
    if leftovers:
        sc, i = max(leftovers)
        total += sc
        picked.append(i)
    return total, picked


def best_lineup(scores: np.ndarray, pos: np.ndarray):
    """Array-friendly wrapper around :func:`_lineup`."""
    return _lineup(np.asarray(scores).tolist(), np.asarray(pos).tolist())


def roster_value(idx: np.ndarray, sd: "SeasonData", values: np.ndarray,
                 wkproj: np.ndarray, option: np.ndarray,
                 starter_weakness: np.ndarray) -> float:
    """What this roster is worth to its manager right now.

    Starting-lineup strength dominates; this week's lineup is a secondary term
    because managers do care about the game in front of them; and the bench
    contributes injury insurance, matchup coverage and upside.
    """
    n = len(idx)
    if n == 0:
        return 0.0
    poss = sd.pos.take(idx).tolist()
    v = values.take(idx).tolist()
    total, picked = _lineup(v, poss)
    wk_total, _ = _lineup(wkproj.take(idx).tolist(), poss)
    # Season-long lineup strength dominates; the game in front of him is worth
    # something but it is one week out of the whole run.
    val = total + WEEK_WEIGHT * wk_total

    bench = [(v[i], poss[i], i) for i in range(n)]
    for i in picked:
        bench[i] = None
    bench = [b for b in bench if b is not None]
    if not bench:
        return val
    ups = option.take(idx).tolist()
    by_pos = ([], [], [], [], [], [])
    for sc, p, i in bench:
        by_pos[p].append(sc)
        # A lottery ticket is worth more to a manager who would actually have
        # to start him.
        val += ups[i] * (1.0 + 0.9 * starter_weakness[p] if p in FLEX_POS else 1.0)
    for p in range(N_POS):
        b = by_pos[p]
        if not b:
            continue
        b.sort(reverse=True)
        boost = bench_boost(p, starter_weakness)
        row = BW[p]
        for j in range(min(len(b), MAX_BENCH_W)):
            val += b[j] * row[j] * boost
    return val


def starter_weakness(idx: np.ndarray, sd: SeasonData, values: np.ndarray) -> np.ndarray:
    """0 = elite starters at this position, 1 = replacement level."""
    out = np.zeros(N_POS)
    if len(idx) == 0:
        return out
    pos = sd.pos[idx]
    v = values[idx]
    for p, need, good in ((RB, 2, 13.0), (WR, 2, 13.0), (TE, 1, 10.0), (QB, 1, 18.0)):
        sel = v[pos == p]
        if len(sel) == 0:
            out[p] = 1.0
            continue
        sel = np.sort(sel)[::-1][:need]
        out[p] = float(np.clip(1.0 - sel.mean() / good, 0.0, 1.0))
    return out
