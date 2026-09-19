"""One full fantasy season: waivers, free agency, IR, lineups, H2H, playoffs.

The draft personas stop mattering here.  In season everyone is trying to win,
and the differences between managers come from how much attention they pay,
how they weigh preseason hype against recent form, and the fact that they
simply disagree about players.  A persona leaves only a light residue -- the
manager who spent a third-round pick on a quarterback is not going to stream
one -- and no persona ever makes someone play badly on purpose.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .config import ACTIVITY_PARAMS, ACTIVITY_WEIGHTS, N_POS, QB
from . import values as V
from .draft import PERSONA_ID, run_draft, sample_personas

ACTIVITY_NAMES = list(ACTIVITY_WEIGHTS)


# --------------------------------------------------------------------------
# Schedule
# --------------------------------------------------------------------------
def make_schedule(rng: np.random.Generator, n_teams: int, weeks: int) -> np.ndarray:
    """Balanced random regular season: ``weeks x n_teams`` of opponent ids."""
    teams = list(rng.permutation(n_teams))
    fixed, rot = teams[0], teams[1:]
    rounds = []
    for _ in range(n_teams - 1):
        pairs = [(fixed, rot[0])]
        for i in range(1, n_teams // 2):
            pairs.append((rot[i], rot[-i]))
        rounds.append(pairs)
        rot = rot[1:] + rot[:1]
    # Rounds repeat (with home/away flipped) until the season is long enough.
    order = list(rng.permutation(len(rounds)))
    sched = np.full((weeks, n_teams), -1, dtype=np.int8)
    for w in range(weeks):
        pairs = rounds[order[w % len(rounds)]]
        for a, b in pairs:
            sched[w, a] = b
            sched[w, b] = a
    return sched


# --------------------------------------------------------------------------
# Team state
# --------------------------------------------------------------------------
@dataclass
class Team:
    tid: int
    persona: int
    activity: int
    slot: int                       # draft slot, 0-based
    roster: list = field(default_factory=list)
    ir: list = field(default_factory=list)
    opinion: np.ndarray = None
    alpha_trait: float = 0.0
    threshold: float = 1.0
    p_check: float = 1.0
    max_claims: int = 2
    fa_moves: int = 1
    sloppy: float = 0.05
    sunk_cost: float = 0.0          # reluctance to drop an early pick
    wins: int = 0
    losses: int = 0
    ties: int = 0
    pts_for: float = 0.0
    adds: int = 0
    drops: int = 0
    first_qb_round: int = 0
    first_qb: int = -1
    qb_points: float = 0.0
    draft_pick_round: dict = field(default_factory=dict)

    def all_players(self):
        return self.roster + self.ir


# --------------------------------------------------------------------------
# The season
# --------------------------------------------------------------------------
class LeagueSim:
    def __init__(self, sd: V.SeasonData, cfg, season_cfg, seed: int,
                 tracer=None, force_qb_round: int = 0, force_persona: str = "",
                 force_team: int = 0):
        self.sd = sd
        self.cfg = cfg
        self.scfg = season_cfg
        self.rng = np.random.default_rng(seed)
        self.seed = seed
        self.tracer = tracer
        self.force_qb_round = force_qb_round
        self.force_persona = force_persona
        self.force_team = force_team
        self.n_weeks = season_cfg.n_weeks
        self.free = np.ones(sd.n, dtype=bool)
        # The week a player was dropped.  He is claimable on the next waiver
        # run but cannot be picked straight back up as a free agent, which is
        # ESPN's waiver period.
        self.dropped_week = np.full(sd.n, -1, dtype=np.int16)
        self.add_count = np.zeros(sd.n, dtype=np.int32)
        self.drop_count = np.zeros(sd.n, dtype=np.int32)
        self.drafted_drop_count = np.zeros(sd.n, dtype=np.int32)

    # -- setup ------------------------------------------------------------
    def setup(self):
        sd, cfg, rng = self.sd, self.cfg, self.rng
        personas = sample_personas(rng, self.scfg.personas, cfg.n_teams)
        if self.force_persona:
            personas[self.force_team] = PERSONA_ID[self.force_persona]
        act_p = np.array([ACTIVITY_WEIGHTS[a] for a in ACTIVITY_NAMES])
        acts = rng.choice(len(ACTIVITY_NAMES), cfg.n_teams, p=act_p / act_p.sum())

        qb_round = ({self.force_team: self.force_qb_round}
                    if self.force_qb_round else None)
        rosters, pick_of, slot_of_team = run_draft(
            sd, rng, personas, cfg, self.scfg,
            trace=self.tracer.draft if self.tracer else None,
            qb_round=qb_round)

        self.pick_of = pick_of          # overall pick number, per player
        self.teams = []
        for t in range(cfg.n_teams):
            ap = ACTIVITY_PARAMS[ACTIVITY_NAMES[acts[t]]]
            team = Team(
                tid=t, persona=int(personas[t]), activity=int(acts[t]),
                slot=int(slot_of_team[t]),
                roster=[int(p) for p in rosters[t] if p >= 0],
                opinion=np.clip(rng.normal(1.0, 0.07, sd.n), 0.6, 1.5),
                alpha_trait=float(rng.uniform(-0.15, 0.15)),
                threshold=ap["threshold"] * float(rng.uniform(0.75, 1.3)),
                p_check=ap["p_check"], max_claims=ap["max_claims"],
                fa_moves=ap["fa_moves"], sloppy=ap["sloppy"],
                sunk_cost=float(rng.uniform(0.0, 0.5)),
            )
            for r, p in enumerate(rosters[t]):
                if p >= 0:
                    team.draft_pick_round[int(p)] = r + 1
                    self.free[p] = False
            qbs = [(r + 1, int(p)) for r, p in enumerate(rosters[t])
                   if p >= 0 and sd.pos[p] == QB]
            if qbs:
                team.first_qb_round, team.first_qb = qbs[0]
            self.teams.append(team)

        # Rolling waivers start in reverse draft order.
        self.waiver_order = sorted(range(cfg.n_teams),
                                   key=lambda t: -slot_of_team[t])
        self.slot_of_team = slot_of_team
        self.schedule = make_schedule(rng, cfg.n_teams, cfg.regular_weeks)
        self.weekly_points = np.zeros((cfg.n_teams, self.n_weeks))

    # -- valuation --------------------------------------------------------
    def team_values(self, team: Team, week: int):
        alpha = V.prior_weight(week, team.alpha_trait)
        vals = V.player_values(self.sd, week, alpha, team.opinion)
        # An elite-quarterback drafter does not go shopping for quarterbacks.
        if team.first_qb_round and team.first_qb_round <= 5:
            vals = vals.copy()
            mine = [p for p in team.all_players() if self.sd.pos[p] == QB]
            mask = (self.sd.pos == QB)
            if mine:
                mask[mine] = False
            vals[mask] *= 0.55
        avail = V.availability(self.sd, week)
        opt = V.option_value(self.sd, week, vals, avail)
        return vals * avail, opt

    # -- lineups ----------------------------------------------------------
    def set_lineup(self, team: Team, week: int):
        """Highest projected legal lineup, with human-sized wobble."""
        sd = self.sd
        idx = np.array(team.roster, dtype=int)
        if len(idx) == 0:
            return [], 0.0
        w = week - 1
        forgot = self.rng.random() < team.sloppy
        # A manager who never opened the app is still on last week's lineup.
        src = max(w - 1, 0) if forgot else w
        scores = sd.proj[idx, src].copy()
        if forgot:
            # Last week's projection says nothing about this week's bye.
            pass
        else:
            scores = scores * (1.0 - 0.35 * sd.quest[idx, w])
        scores = scores + self.rng.normal(0.0, 0.6, len(idx))
        _, picked = V.best_lineup(scores, sd.pos[idx])
        starters = idx[picked]
        pts = float(sd.act[starters, w].sum())
        return starters.tolist(), pts

    # -- roster bookkeeping ----------------------------------------------
    def manage_ir(self, team: Team, week: int):
        """Stash the injured, activate the returning, and shed the surplus.

        A bye week is not an injury, so it never earns an IR slot.
        """
        sd, w = self.sd, week - 1
        cap = self.cfg.ir_slots
        # Anyone eligible to play again has to come back onto the active roster.
        for p in [p for p in team.ir if not sd.injured[p, w]]:
            team.ir.remove(p)
            team.roster.append(p)
        # Stash the injured to free a bench spot -- the best player first,
        # because that is the one worth waiting for.
        if len(team.ir) < cap:
            vals, _ = self.team_values(team, week)
            while len(team.ir) < cap:
                cands = [p for p in team.roster if sd.injured[p, w]]
                if not cands:
                    break
                p = max(cands, key=lambda i: vals[i] * (1.0 + sd.out_streak[i, w]))
                team.roster.remove(p)
                team.ir.append(p)
        # An over-full roster sheds its least useful player.
        while len(team.roster) > self.cfg.roster_size:
            vals, up = self.team_values(team, week)
            worst = self.worst_drop(team, vals, up, week)
            self.execute_drop(team, worst, week, "roster overflow")

    def execute_drop(self, team: Team, p: int, week: int, reason: str):
        if p in team.roster:
            team.roster.remove(p)
        elif p in team.ir:
            team.ir.remove(p)
        else:
            return
        self.free[p] = True
        self.dropped_week[p] = week
        team.drops += 1
        self.drop_count[p] += 1
        if p in team.draft_pick_round:
            self.drafted_drop_count[p] += 1
        if self.tracer:
            self.tracer.move(week, team.tid, "DROP", p, reason)

    def execute_add(self, team: Team, p: int, week: int, reason: str):
        team.roster.append(p)
        self.free[p] = False
        self.dropped_week[p] = -1
        team.adds += 1
        self.add_count[p] += 1
        if self.tracer:
            self.tracer.move(week, team.tid, "ADD", p, reason)

    # -- move evaluation --------------------------------------------------
    def roster_pack(self, team: Team, week: int, vals, up, roster=None):
        idx = np.array(team.all_players() if roster is None else roster, dtype=int)
        sw = V.starter_weakness(idx, self.sd, vals)
        wk = self.sd.proj[:, week - 1]
        base = V.roster_value(idx, self.sd, vals, wk, up, sw)
        return idx, sw, wk, base

    def worst_drop(self, team: Team, vals, up, week: int) -> int:
        """The player whose loss costs this roster least."""
        idx, sw, wk, base = self.roster_pack(team, week, vals, up)
        best_p, best_cost = int(idx[0]), np.inf
        for p in idx:
            rest = idx[idx != p]
            cost = base - V.roster_value(rest, self.sd, vals, wk, up, sw)
            # Sunk cost: a manager is a little slow to bin an early pick.
            rnd = team.draft_pick_round.get(int(p))
            if rnd and rnd <= 6:
                cost += team.sunk_cost * (7 - rnd) * 0.25
            if cost < best_cost:
                best_cost, best_p = cost, int(p)
        return best_p

    def candidate_moves(self, team: Team, week: int, vals, up, pool_mask,
                        top_n: int = 3, roster=None):
        """Ranked ``(gain, add, drop)`` triples this manager would like to make.

        Adds and drops are first priced separately -- what a player is worth to
        this roster, and what losing one would cost -- which is how managers
        actually think, and then the best few combinations are re-scored
        exactly.
        """
        sd = self.sd
        idx, sw, wk, base = self.roster_pack(team, week, vals, up, roster)
        if len(idx) == 0:
            return []

        # -- what each free agent would add -------------------------------
        cands = []
        for p in range(N_POS):
            sel = np.where(pool_mask & (sd.pos == p))[0]
            if len(sel) == 0:
                continue
            score = vals[sel] + up[sel] + 0.35 * wk[sel]
            k = min(top_n, len(sel))
            cands.extend(sel[np.argpartition(-score, k - 1)[:k]].tolist())
        if not cands:
            return []

        add_gain = {}
        for p in cands:
            ext = np.append(idx, p)
            add_gain[p] = V.roster_value(ext, sd, vals, wk, up, sw) - base

        drop_cost = {}
        for p in idx:
            rest = idx[idx != p]
            cost = base - V.roster_value(rest, sd, vals, wk, up, sw)
            rnd = team.draft_pick_round.get(int(p))
            if rnd and rnd <= 6:
                cost += team.sunk_cost * (7 - rnd) * 0.25
            drop_cost[int(p)] = cost

        rough = []
        for a, g in add_gain.items():
            for d, c in drop_cost.items():
                rough.append((g - c, a, d))
        rough.sort(key=lambda x: -x[0])
        shortlist = [(a, d) for _, a, d in rough[:8]]

        # Pricing adds and drops apart misses the case where they interact most:
        # the replacement at the same position.  Dropping a manager's only
        # quarterback looks ruinous on its own and is obviously fine once the
        # new one is on the roster, so those pairs are always re-scored.
        best_adds = sorted(add_gain, key=lambda a: -add_gain[a])[:3]
        for a in best_adds:
            same = sorted((p for p in idx if sd.pos[p] == sd.pos[a]),
                          key=lambda p: drop_cost[int(p)])[:2]
            shortlist.extend((a, int(d)) for d in same)

        # Exact re-score of the shortlist (the two moves can interact).
        out = []
        for a, d in dict.fromkeys(shortlist):
            newidx = np.append(idx[idx != d], a)
            gain = V.roster_value(newidx, sd, vals, wk, up, sw) - base
            out.append((gain, int(a), int(d)))
        out.sort(key=lambda x: -x[0])
        return out

    def why(self, add: int, drop: int, week: int, gain: float, kind: str) -> tuple:
        """A human-readable reason for a move, for the trace.

        Purely descriptive -- it never feeds back into the decision.
        """
        sd, w = self.sd, week - 1
        from .config import DST, K
        tags = []
        if sd.injured[drop, w]:
            tags.append(f"dropping an injured player (out {sd.out_streak[drop, w]}w)")
        if sd.pos[add] in (K, DST):
            tags.append("streaming")
        starter = sd.ahead[add, w]
        if starter >= 0 and sd.out[starter, w]:
            tags.append(f"role change behind {sd.name[starter]}")
        elif starter >= 0 and sd.quest[starter, w]:
            tags.append(f"handcuff, {sd.name[starter]} questionable")
        if sd.injured[add, w]:
            tags.append("stash")
        note = f"{kind} (+{gain:.1f})" + (" -- " + "; ".join(tags) if tags else "")
        return note, note

    # -- waivers ----------------------------------------------------------
    def waiver_priority(self, week: int):
        cfg = self.cfg
        if cfg.waiver_system == "reset_inverse_standings":
            order = sorted(range(cfg.n_teams),
                           key=lambda t: (self.teams[t].wins, self.teams[t].pts_for))
            return order
        return list(self.waiver_order)

    def plan_claims(self, team: Team, week: int, vals, up, pool):
        """A manager's ranked waiver claims for the week.

        Claims are built one at a time against the roster the previous claim
        would leave behind, so a manager never queues two defences or asks for
        the same player twice.
        """
        roster = list(team.all_players())
        avail = pool.copy()
        ranked = []
        for _ in range(team.max_claims):
            moves = self.candidate_moves(team, week, vals, up, avail, roster=roster)
            if not moves:
                break
            gain, add, drop = moves[0]
            if gain <= team.threshold:
                break
            ranked.append((gain, add, drop))
            roster = [p for p in roster if p != drop] + [add]
            avail[add] = False
        return ranked

    def run_waivers(self, week: int):
        """Wednesday waiver run under the league's ESPN waiver system."""
        pool = self.free.copy()
        claims = {}
        for team in self.teams:
            if self.rng.random() > team.p_check:
                continue
            vals, up = self.team_values(team, week)
            ranked = self.plan_claims(team, week, vals, up, pool)
            if ranked:
                claims[team.tid] = ranked

        order = [t for t in self.waiver_priority(week) if t in claims]
        while order:
            retry, to_back = [], []
            for t in order:
                queue = claims[t]
                if not queue:
                    continue
                gain, add, drop = queue.pop(0)
                team = self.teams[t]
                if not self.free[add]:
                    # Beaten to him.  He keeps his place and his next claim is
                    # tried when his turn comes round again.
                    if queue:
                        retry.append(t)
                    continue
                if drop not in team.all_players():
                    vals, up = self.team_values(team, week)
                    drop = self.worst_drop(team, vals, up, week)
                d_why, a_why = self.why(add, drop, week, gain, "waiver claim")
                self.execute_drop(team, drop, week, d_why)
                self.execute_add(team, add, week, a_why)
                if self.cfg.waiver_system == "rolling":
                    self.waiver_order.remove(t)
                    self.waiver_order.append(t)
                if queue:
                    to_back.append(t)
            # Successful claimants drop to the back of the line for this run.
            order = retry + to_back

    def run_free_agency(self, week: int):
        """Thursday-to-Sunday pickups: streaming, late injury news, hunches."""
        order = [t.tid for t in self.teams for _ in range(t.fa_moves)]
        if not order:
            return
        self.rng.shuffle(order)
        for t in order:
            team = self.teams[t]
            if self.rng.random() > team.p_check:
                continue
            # Anyone dropped this week is still sitting on waivers.
            pool = self.free & (self.dropped_week < week)
            vals, up = self.team_values(team, week)
            moves = self.candidate_moves(team, week, vals, up, pool, top_n=2)
            if not moves:
                continue
            gain, add, drop = moves[0]
            # Free agency is a lower bar than a waiver claim but not a free lunch.
            if gain <= team.threshold * 0.7:
                continue
            if drop not in team.all_players():
                continue
            d_why, a_why = self.why(add, drop, week, gain, "free agent")
            self.execute_drop(team, drop, week, d_why)
            self.execute_add(team, add, week, a_why)

    # -- play -------------------------------------------------------------
    def play_week(self, week: int, matchups, record: bool = True):
        pts = {}
        for team in self.teams:
            starters, p = self.set_lineup(team, week)
            pts[team.tid] = p
            team.pts_for += p
            self.weekly_points[team.tid, week - 1] = p
            qb_pts = sum(float(self.sd.act[s, week - 1]) for s in starters
                         if self.sd.pos[s] == QB)
            team.qb_points += qb_pts
            if self.tracer:
                self.tracer.lineup(week, team.tid, starters, p)
        if not record:
            return pts
        for a, b in matchups:
            if pts[a] > pts[b]:
                self.teams[a].wins += 1
                self.teams[b].losses += 1
            elif pts[b] > pts[a]:
                self.teams[b].wins += 1
                self.teams[a].losses += 1
            else:
                self.teams[a].ties += 1
                self.teams[b].ties += 1
        return pts

    def regular_season(self):
        for week in range(1, self.cfg.regular_weeks + 1):
            if week > 1:
                self.manage_all_ir(week)
                self.run_waivers(week)
                self.run_free_agency(week)
            opp = self.schedule[week - 1]
            seen = set()
            matchups = []
            for a in range(self.cfg.n_teams):
                b = int(opp[a])
                if a in seen or b < 0 or b in seen:
                    continue
                seen.update((a, b))
                matchups.append((a, b))
            self.play_week(week, matchups)

    def manage_all_ir(self, week: int):
        for team in self.teams:
            self.manage_ir(team, week)

    def seeds(self):
        order = sorted(self.teams, key=lambda t: (-t.wins, -t.pts_for))
        return [t.tid for t in order[:self.cfg.playoff_teams]]

    def playoffs(self):
        seeds = self.seeds()
        cfg = self.cfg
        w1, w2, w3 = cfg.playoff_weeks
        self.manage_all_ir(w1)
        self.run_waivers(w1)
        self.run_free_agency(w1)
        p = self.play_week(w1, [(seeds[2], seeds[5]), (seeds[3], seeds[4])], record=False)
        rd1 = [seeds[2] if p[seeds[2]] >= p[seeds[5]] else seeds[5],
               seeds[3] if p[seeds[3]] >= p[seeds[4]] else seeds[4]]
        # The top seed draws the lowest survivor.
        rd1.sort(key=lambda t: seeds.index(t))
        # Everyone still playing -- and everyone eliminated -- keeps managing.
        self.manage_all_ir(w2)
        self.run_waivers(w2)
        self.run_free_agency(w2)
        p = self.play_week(w2, [(seeds[0], rd1[1]), (seeds[1], rd1[0])], record=False)
        finalists = [seeds[0] if p[seeds[0]] >= p[rd1[1]] else rd1[1],
                     seeds[1] if p[seeds[1]] >= p[rd1[0]] else rd1[0]]
        self.manage_all_ir(w3)
        self.run_waivers(w3)
        self.run_free_agency(w3)
        p = self.play_week(w3, [(finalists[0], finalists[1])], record=False)
        champ = finalists[0] if p[finalists[0]] >= p[finalists[1]] else finalists[1]
        runner = finalists[1] if champ == finalists[0] else finalists[0]
        return seeds, champ, runner

    def run(self) -> dict:
        self.setup()
        self.regular_season()
        self.reg_pts_for = np.array([t.pts_for for t in self.teams])
        seeds, champ, runner = self.playoffs()
        sd = self.sd
        n = self.cfg.n_teams
        res = {
            "seed": np.full(n, 0, dtype=np.int8),
            "persona": np.array([t.persona for t in self.teams], dtype=np.int8),
            "activity": np.array([t.activity for t in self.teams], dtype=np.int8),
            "draft_slot": np.array([t.slot for t in self.teams], dtype=np.int8),
            "wins": np.array([t.wins for t in self.teams], dtype=np.int8),
            "losses": np.array([t.losses for t in self.teams], dtype=np.int8),
            "pts_for": self.reg_pts_for,
            "reg_pts": np.array([self.weekly_points[t.tid, :self.cfg.regular_weeks].sum()
                                 for t in self.teams]),
            "champion": np.zeros(n, dtype=bool),
            "runner_up": np.zeros(n, dtype=bool),
            "playoffs": np.zeros(n, dtype=bool),
            "adds": np.array([t.adds for t in self.teams], dtype=np.int16),
            "drops": np.array([t.drops for t in self.teams], dtype=np.int16),
            "first_qb_round": np.array([t.first_qb_round for t in self.teams], dtype=np.int8),
            "first_qb": np.array([t.first_qb for t in self.teams], dtype=np.int32),
            "qb_points": np.array([t.qb_points for t in self.teams]),
            "ties": np.array([t.ties for t in self.teams], dtype=np.int8),
        }
        for rank, t in enumerate(seeds):
            res["seed"][t] = rank + 1
            res["playoffs"][t] = True
        res["champion"][champ] = True
        res["runner_up"][runner] = True
        return res
