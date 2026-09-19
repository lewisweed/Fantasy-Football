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
| Player pool, weekly projections, weekly actuals (`appliedTotal`) | ESPN `kona_player_info`, PPR league defaults |
| Average draft position | Fantasy Football Calculator, 12-team PPR, 8,470 real mock drafts |
| Injury reports, weekly rosters, depth charts, schedules, byes | [nflverse](https://github.com/nflverse/nflverse-data) |
| Fallback board and projections when ESPN is unavailable | FantasyPros PPR consensus, via the [DynastyProcess](https://github.com/dynastyprocess/data) mirror |

`clean.py` has two tiers and picks whichever it can actually build.

**Tier 1 (`espn+ffc`, the default when the files are present).** ESPN supplies
the pool, its own weekly projections and its own scoring; Fantasy Football
Calculator supplies real mock-draft ADP with the spread across drafts, and
ESPN's PPR board prices anyone FFC never saw drafted. The 2025 board has 29
quarterbacks inside pick 192, and simulated drafts reproduce real ADP at
r = 0.934 with a mean gap of 5.4 picks across the top 100.

The two ESPN and FFC snapshots are not in this repository — they are large and
are fetched rather than derived. `python -m fantasy_sim.fetch` downloads them
where the hosts are reachable; otherwise drop `espn_players_{year}.json` and
`ffc_adp_{year}.json` into `fantasy_sim/data/raw/` by hand. Availability and
depth-chart roles always come from nflverse, in both tiers, because ESPN's feed
carries only an end-of-season snapshot of a player's status.

**Tier 2 (`nflverse+fantasypros`).** Used automatically when the ESPN file is
absent. ESPN's `appliedTotal` is replaced by ESPN's published PPR rules applied
to nflverse box scores (`scoring.py`, verified against nflverse's own PPR column
to within 0.011 points per player-week), the draft board by the final preseason
FantasyPros PPR consensus, and weekly projections by FantasyPros weekly
rankings mapped to points through curves **fitted on other seasons only**.
Weekly correlation with actual scoring is 0.63 against tier 1's 0.66, and the
resulting persona leaderboard agrees with tier 1 closely, so the fallback is a
reasonable stand-in rather than a different experiment.

`meta_{year}.json` records which tier a build used.

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
