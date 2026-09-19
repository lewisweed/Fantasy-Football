"""Monte Carlo runner.

Leagues are independent, so they are split across processes and written out in
chunks.  Every chunk is keyed by its league seeds, so an interrupted run picks
up exactly where it stopped, and re-running with the same seed reproduces the
same leagues.

Counterfactuals use common random numbers: the same league seed is replayed
with one team forced into a strategy, so the comparison is against that team's
own default behaviour in an otherwise identical league.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import replace
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

from . import clean, season, values
from .config import (ACTIVITY_WEIGHTS, LEAGUE, PERSONAS_2025, RESULTS,
                     RunConfig, season_config)
from .draft import PERSONA_NAMES
from .season import ACTIVITY_NAMES

_CACHE: dict = {}


def _season_data(year: int) -> values.SeasonData:
    """Built once per worker process and reused for every league."""
    if year not in _CACHE:
        pool, arrays = clean.load(year)
        _CACHE[year] = (values.SeasonData(pool, arrays, season_config(year).n_weeks),
                        pool)
    return _CACHE[year]


TEAM_COLS = ("persona", "activity", "draft_slot", "wins", "losses", "pts_for",
             "reg_pts", "seed", "playoffs", "champion", "runner_up", "adds",
             "drops", "first_qb_round", "first_qb", "qb_points")


def run_chunk(job) -> dict:
    """Simulate one block of leagues.  Runs inside a worker process."""
    year, seeds, league_cfg, scfg_overrides, force_qb_round, force_persona = job
    sd, _ = _season_data(year)
    scfg = season_config(year)
    if scfg_overrides:
        scfg = replace(scfg, **scfg_overrides)

    rows = {c: [] for c in TEAM_COLS}
    rows["league"] = []
    rows["team"] = []
    adds = np.zeros(sd.n, dtype=np.int64)
    drops = np.zeros(sd.n, dtype=np.int64)
    drafted_drops = np.zeros(sd.n, dtype=np.int64)
    drafted = np.zeros(sd.n, dtype=np.int64)
    pick_sum = np.zeros(sd.n, dtype=np.int64)
    qb_rostered = []

    for s in seeds:
        sim = season.LeagueSim(sd, league_cfg, scfg, int(s),
                               force_qb_round=force_qb_round,
                               force_persona=force_persona)
        res = sim.run()
        n = league_cfg.n_teams
        rows["league"].extend([int(s)] * n)
        rows["team"].extend(range(n))
        for c in TEAM_COLS:
            rows[c].extend(res[c].tolist())
        adds += sim.add_count.astype(np.int64)
        drops += sim.drop_count.astype(np.int64)
        drafted_drops += sim.drafted_drop_count.astype(np.int64)
        for t in sim.teams:
            for p, rnd in t.draft_pick_round.items():
                drafted[p] += 1
                pick_sum[p] += (rnd - 1) * n + 1
            qb_rostered.append(sum(1 for p in t.all_players() if sd.pos[p] == 0))

    df = pd.DataFrame(rows)
    return {
        "teams": df,
        "adds": adds, "drops": drops, "drafted_drops": drafted_drops,
        "drafted": drafted, "pick_sum": pick_sum,
        "qb_rostered": np.array(qb_rostered, dtype=np.int8),
    }


def _merge(parts: list) -> dict:
    out = {
        "teams": pd.concat([p["teams"] for p in parts], ignore_index=True),
        "qb_rostered": np.concatenate([p["qb_rostered"] for p in parts]),
    }
    for k in ("adds", "drops", "drafted_drops", "drafted", "pick_sum"):
        out[k] = np.sum([p[k] for p in parts], axis=0)
    return out


def run(cfg: RunConfig, *, scfg_overrides: dict | None = None,
        verbose: bool = True) -> Path:
    """Run a whole experiment, checkpointing as it goes."""
    outdir = RESULTS / f"{cfg.year}_{cfg.out_tag}"
    outdir.mkdir(parents=True, exist_ok=True)
    seeds = cfg.seed + np.arange(cfg.n_leagues)
    chunks = [seeds[i:i + cfg.chunk] for i in range(0, len(seeds), cfg.chunk)]
    workers = cfg.workers or os.cpu_count() or 1

    jobs, pending = [], []
    for i, ch in enumerate(chunks):
        path = outdir / f"chunk_{i:04d}.parquet"
        if path.exists():
            continue
        pending.append((i, path))
        jobs.append((cfg.year, ch, cfg.league, scfg_overrides,
                     cfg.force_qb_round, cfg.force_persona))

    t0 = time.time()
    if jobs:
        with Pool(workers) as pool:
            for (i, path), part in zip(pending, pool.imap(run_chunk, jobs)):
                part["teams"].to_parquet(path, index=False)
                np.savez_compressed(
                    outdir / f"diag_{i:04d}.npz",
                    **{k: v for k, v in part.items() if k != "teams"})
                if verbose:
                    done = pending.index((i, path)) + 1
                    rate = (time.time() - t0) / done
                    left = (len(pending) - done) * rate
                    print(f"  chunk {done}/{len(pending)}  "
                          f"{rate:.1f}s/chunk  ~{left/60:.1f} min left", flush=True)

    # Stitch the checkpoints back together.
    teams = pd.concat([pd.read_parquet(p) for p in sorted(outdir.glob("chunk_*.parquet"))],
                      ignore_index=True)
    teams.to_parquet(outdir / "teams.parquet", index=False)
    diag: dict = {}
    for p in sorted(outdir.glob("diag_*.npz")):
        z = np.load(p)
        for k in z.files:
            if k == "qb_rostered":
                diag[k] = np.concatenate([diag[k], z[k]]) if k in diag else z[k]
            else:
                diag[k] = diag.get(k, 0) + z[k]
    np.savez_compressed(outdir / "diagnostics.npz", **diag)
    (outdir / "config.json").write_text(json.dumps({
        "year": cfg.year, "n_leagues": cfg.n_leagues, "seed": cfg.seed,
        "waiver_system": cfg.league.waiver_system, "tag": cfg.out_tag,
        "force_qb_round": cfg.force_qb_round, "force_persona": cfg.force_persona,
        "personas": (scfg_overrides or {}).get("personas", PERSONAS_2025),
        "activity": ACTIVITY_WEIGHTS,
    }, indent=2, default=str))
    if verbose:
        print(f"  -> {outdir}  ({len(teams)} team-seasons, "
              f"{time.time() - t0:.0f}s)")
    return outdir


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run the Monte Carlo experiment.")
    ap.add_argument("--year", type=int, default=2025)
    ap.add_argument("--leagues", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=20250901)
    ap.add_argument("--chunk", type=int, default=250)
    ap.add_argument("--workers", type=int, default=0)
    ap.add_argument("--tag", default="base")
    ap.add_argument("--waivers", default="reset_inverse_standings",
                    choices=["reset_inverse_standings", "rolling"])
    ap.add_argument("--force-qb-round", type=int, default=0,
                    help="force team 0 to take its first QB in this round")
    ap.add_argument("--force-persona", default="")
    args = ap.parse_args(argv)

    cfg = RunConfig(year=args.year, n_leagues=args.leagues, seed=args.seed,
                    chunk=args.chunk, workers=args.workers, out_tag=args.tag,
                    league=replace(LEAGUE, waiver_system=args.waivers),
                    force_qb_round=args.force_qb_round,
                    force_persona=args.force_persona)
    run(cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
