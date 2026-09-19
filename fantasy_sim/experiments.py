"""The full experiment suite for a season.

Three families of run:

* **base** -- the headline 5,000 leagues.
* **counterfactuals** -- the same league seeds replayed with one team forced to
  take its first quarterback in a given round, which isolates the effect of
  that decision from everything else in the league.
* **sensitivity** -- the same question asked of a different persona mix and of
  the other ESPN waiver system.  A conclusion that moves between these is not a
  conclusion.
"""
from __future__ import annotations

import argparse
from dataclasses import replace

from .config import LEAGUE, PERSONAS_2025, RunConfig
from .run import run

#: Rounds tested in the counterfactual, plus "never" (the roster minimum still
#: forces a quarterback in the last rounds).
QB_ROUNDS = (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 15)

#: Persona mixes used for the sensitivity check.
SENSITIVITY_MIXES = {
    "more_late_qb": {**PERSONAS_2025, "late_qb": 0.26, "early_qb": 0.04,
                     "elite_qb_only": 0.02, "backup_qb_hoard": 0.02},
    "more_early_qb": {**PERSONAS_2025, "late_qb": 0.06, "early_qb": 0.17,
                      "elite_qb_only": 0.11, "qb_streamer": 0.02},
}


def normalise(mix: dict) -> dict:
    total = sum(mix.values())
    return {k: v / total for k, v in mix.items()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run every experiment for a season.")
    ap.add_argument("--year", type=int, default=2025)
    ap.add_argument("--leagues", type=int, default=5000)
    ap.add_argument("--cf-leagues", type=int, default=1200)
    ap.add_argument("--sens-leagues", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20250901)
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--only", default="", help="base | cf | sens")
    args = ap.parse_args(argv)

    base = RunConfig(year=args.year, n_leagues=args.leagues, seed=args.seed,
                     workers=args.workers, out_tag="base")

    if args.only in ("", "base"):
        print("== base ==", flush=True)
        run(base)

    if args.only in ("", "cf"):
        for r in QB_ROUNDS:
            print(f"== counterfactual: first QB in round {r} ==", flush=True)
            run(replace(base, n_leagues=args.cf_leagues, out_tag=f"cf_qb{r}",
                        force_qb_round=r))

    if args.only in ("", "sens"):
        print("== sensitivity: rolling waivers ==", flush=True)
        run(replace(base, n_leagues=args.sens_leagues, out_tag="sens_rolling",
                    league=replace(LEAGUE, waiver_system="rolling")))
        for name, mix in SENSITIVITY_MIXES.items():
            print(f"== sensitivity: {name} ==", flush=True)
            run(replace(base, n_leagues=args.sens_leagues, out_tag=f"sens_{name}"),
                scfg_overrides={"personas": normalise(mix)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
