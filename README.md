# Fantasy football league simulator

A Monte Carlo simulator of full 12-team ESPN PPR fantasy football seasons —
draft, weekly waivers, free agency, injured reserve, lineups, head-to-head and
playoffs — built to answer two questions:

1. **Which draft strategies win the most**, by season and by draft slot?
2. **Where should you draft a quarterback** in a 1-QB PPR league, and which
   quarterbacks were the best value relative to their draft cost?

Everything is parameterised by season. Adding 2024 or 2023 means adding a
`SeasonConfig` with that year's researched persona mix; no other module
hard-codes a year.

## Quick start

```bash
pip install numpy pandas pyarrow requests pytest

python -m fantasy_sim.fetch       --year 2025     # populate the raw cache
python -m fantasy_sim.clean       --year 2025     # build the season universe
python -m fantasy_sim.experiments --year 2025     # base + counterfactual + sensitivity
python -m fantasy_sim.analyze     --year 2025     # -> results/report_2025.md

python -m fantasy_sim.trace --seed 7 --team 3     # replay one league, move by move
python -m pytest fantasy_sim/tests -q             # the acceptance suite
```

The raw downloads are gitignored and reproducible from `fetch.py`. The derived
season universe under `fantasy_sim/data/clean/` **is** committed, so the
simulator runs with no network access.

## Data sources

| What | Source |
|---|---|
| Weekly actuals, injury reports, weekly rosters, depth charts, snap counts, schedules | [nflverse](https://github.com/nflverse/nflverse-data) |
| PPR draft board, weekly and rest-of-season consensus rankings | FantasyPros, via the [DynastyProcess](https://github.com/dynastyprocess/data) mirror |
| Scoring | ESPN standard PPR (`leaguedefaults/3`), applied to nflverse box scores by `scoring.py` |

### A note on ESPN and Fantasy Football Calculator

The build spec names ESPN's `kona_player_info` feed as the primary source and
Fantasy Football Calculator as the ADP source. **Both hosts are blocked by this
environment's egress policy** (`lm-api-reads.fantasy.espn.com` and
`fantasyfootballcalculator.com` are refused at the proxy), so neither could be
used here.

`fetch.py` implements both downloaders exactly as specified, so the files can
be fetched from any machine with open network access and dropped into
`fantasy_sim/data/raw/`. **The tier-1 reader in `clean.py` is not written yet**
— there was nothing to write it against — so today the pipeline runs on the
fallback tier regardless:

- **Scoring.** ESPN's own `appliedTotal` is replaced by ESPN's published PPR
  rules applied to nflverse box scores. Verified against nflverse's own PPR
  column to within 0.011 points per player-week.
- **Draft board.** Fantasy Football Calculator ADP is replaced by the final
  preseason FantasyPros PPR consensus board (535 players, with the expert
  standard deviation as the ADP spread). This lands very close to the spec's
  own calibration fact: the spec reports 29 quarterbacks inside FFC pick 192 in
  2025; the FantasyPros board has 27.
- **Projections.** ESPN's weekly projections are replaced by weekly FantasyPros
  PPR positional rankings converted to points through rank-to-points curves
  **fitted on 2021–2024 only**, with rest-of-season rankings filling the gaps.
  Weekly correlation with actual scoring is 0.63 overall (0.69 RB, 0.59 QB,
  0.58 WR, 0.57 TE), and the mean projection matches the mean outcome to within
  a few tenths of a point at every position.

Section 9's prior findings were produced from ESPN's own numbers, so
differences against them may be data-tier differences rather than model
differences. Treat that comparison with care.

## No hindsight

Every decision uses only what was public before that week's kickoff. Three
things are handled explicitly, because they are the easy ways to get this
wrong:

- **The zeroed-projection leak.** ESPN (and FantasyPros) show nothing for a
  week a player ended up missing, including the week he got hurt mid-game. A
  projection here is zeroed only on a bye or an official Out/Doubtful
  designation — never because the player turned out not to play. A test asserts
  this holds for every player-week.
- **Availability.** Out/Doubtful/Questionable come from the official weekly
  injury report; season-ending injuries become known through the weekly NFL
  roster (injured reserve), which is public; and a player ruled out who then
  drops out of the weekly rankings is still known to be out.
- **Calibration.** The curves that turn consensus rankings into points are
  fitted on other seasons. The target season never sees its own outcomes.

## How the managers work

**Drafting** is persona-driven. Each manager reads the board through his own
noise and takes the best score, tilted by his persona, by the habits nearly
everyone shares (fill your starters; do not take a second quarterback early),
by the cliff at a position, and by who he expects to survive until his next
pick. Biases tip close calls and never override a large value gap — a
receiver-leaning manager whose board says the top four are all running backs
still takes a running back.

**In season the personas stop mattering.** Everyone is trying to win.
Differences come from attention (active / moderate / lazy), from how fast a
manager stops trusting preseason hype, and from the fact that managers simply
disagree — each carries a persistent private opinion of every player. A persona
leaves only a residue: a manager who spent a third-round pick on a quarterback
is not going to stream one.

Moves are judged by what they do to the **roster**, not by comparing two
players in isolation. That is what makes the bench worth something: depth
behind thin starters, matchup coverage, handcuffs whose value is the chance
their role opens up, and injured starters worth stashing for what they will be
when they return.

## Layout

```
fantasy_sim/
  fetch.py        cached downloaders (ESPN + FFC, and the nflverse fallback tier)
  scoring.py      ESPN standard-PPR scoring applied to box scores
  clean.py        the season universe: board, projections, availability, roles
  config.py       league settings, scoring, persona mixes, waiver system
  values.py       player valuation and roster valuation
  draft.py        personas and the snake-draft engine
  season.py       waivers, free agency, IR, lineups, H2H, playoffs
  run.py          multiprocessing runner with resumable chunked checkpoints
  experiments.py  base run, counterfactuals, sensitivity runs
  analyze.py      tables, confidence intervals, the report
  trace.py        single-league debug trace
  tests/          the acceptance suite
results/
  report_2025.md  the write-up
```

## Configuration worth knowing about

- `config.LeagueConfig.waiver_system` — `reset_inverse_standings` (ESPN's
  default, and the default here) or `rolling`. Both are implemented and both
  are exercised in the sensitivity runs.
- `config.PERSONAS_2025` — the persona mix, grounded in 2025 draft advice.
  Every year is different; redo that research per season.
- `config.ACTIVITY_PARAMS` — thresholds calibrated so simulated move counts sit
  inside the spec's bands (15–30 moves a season active, 8–15 moderate, 2–6 lazy).

## Not implemented

Trades, by design — the spec excludes them to keep the league simple.
