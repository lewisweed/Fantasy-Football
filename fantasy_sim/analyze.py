"""Tables, confidence intervals and the written report.

``python -m fantasy_sim.analyze --year 2025`` reads everything under
``results/`` and writes ``results/report_{year}.md``.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import clean
from .config import RESULTS, season_config
from .draft import PERSONA_NAMES
from .season import ACTIVITY_NAMES

FAIR_SHARE = 1.0 / 12.0
Z = 1.959964


# --------------------------------------------------------------------------
# Confidence intervals
# --------------------------------------------------------------------------
def wilson(k: int, n: int) -> tuple[float, float]:
    """Wilson score interval -- behaves at the small counts title rates produce."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + Z * Z / n
    centre = (p + Z * Z / (2 * n)) / d
    half = Z * np.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def mean_ci(x: np.ndarray) -> tuple[float, float]:
    x = np.asarray(x, dtype=float)
    if len(x) < 2:
        return (float(x.mean()) if len(x) else 0.0,) * 2
    se = x.std(ddof=1) / np.sqrt(len(x))
    return (x.mean() - Z * se, x.mean() + Z * se)


def pct(x: float) -> str:
    return f"{100 * x:.2f}%"


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------
def load_run(year: int, tag: str):
    d = RESULTS / f"{year}_{tag}"
    if not (d / "teams.parquet").exists():
        return None, None
    teams = pd.read_parquet(d / "teams.parquet")
    teams["persona_name"] = [PERSONA_NAMES[i] for i in teams.persona]
    teams["activity_name"] = [ACTIVITY_NAMES[i] for i in teams.activity]
    diag = dict(np.load(d / "diagnostics.npz")) if (d / "diagnostics.npz").exists() else {}
    return teams, diag


def md_table(rows: list, header: list) -> str:
    out = ["| " + " | ".join(header) + " |",
           "|" + "|".join(["---"] * len(header)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


# --------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------
def persona_leaderboard(teams: pd.DataFrame) -> str:
    rows = []
    for name, g in teams.groupby("persona_name"):
        n = len(g)
        k = int(g.champion.sum())
        lo, hi = wilson(k, n)
        plo, phi = wilson(int(g.playoffs.sum()), n)
        wl, wh = mean_ci(g.wins.to_numpy())
        rows.append((name, n, k / n, lo, hi, k / n / FAIR_SHARE,
                     g.playoffs.mean(), plo, phi, g.wins.mean(), wl, wh,
                     g.reg_pts.mean()))
    rows.sort(key=lambda r: -r[2])
    body = [(r[0], f"{r[1]:,}", pct(r[2]), f"{pct(r[3])}-{pct(r[4])}", f"{r[5]:.2f}",
             pct(r[6]), f"{pct(r[7])}-{pct(r[8])}", f"{r[9]:.2f}",
             f"{r[10]:.2f}-{r[11]:.2f}", f"{r[12]:.0f}",
             "over" if r[3] > FAIR_SHARE else ("under" if r[4] < FAIR_SHARE else ""))
            for r in rows]
    return md_table(body, ["persona", "teams", "title %", "95% CI", "x fair share",
                           "playoff %", "95% CI", "avg wins", "95% CI",
                           "avg season pts", "flag"])


def by_slot(teams: pd.DataFrame) -> tuple[str, str]:
    teams = teams.assign(slot1=teams.draft_slot + 1)
    bands = pd.cut(teams.slot1, [0, 4, 8, 12], labels=["1-4", "5-8", "9-12"])
    rows = []
    for band, g in teams.groupby(bands, observed=True):
        lo, hi = wilson(int(g.champion.sum()), len(g))
        rows.append((band, f"{len(g):,}", pct(g.champion.mean()),
                     f"{pct(lo)}-{pct(hi)}", pct(g.playoffs.mean()),
                     f"{g.wins.mean():.2f}", f"{g.reg_pts.mean():.0f}"))
    band_tbl = md_table(rows, ["draft slots", "teams", "title %", "95% CI",
                               "playoff %", "avg wins", "avg pts"])

    each = []
    for s, g in teams.groupby("slot1"):
        lo, hi = wilson(int(g.champion.sum()), len(g))
        each.append((s, f"{len(g):,}", pct(g.champion.mean()),
                     f"{pct(lo)}-{pct(hi)}", pct(g.playoffs.mean()),
                     f"{g.reg_pts.mean():.0f}"))
    slot_tbl = md_table(each, ["slot", "teams", "title %", "95% CI",
                               "playoff %", "avg pts"])

    # persona x slot band
    piv = teams.pivot_table(index="persona_name", columns=bands,
                            values="champion", aggfunc="mean", observed=True)
    cnt = teams.pivot_table(index="persona_name", columns=bands,
                            values="champion", aggfunc="size", observed=True)
    rows = []
    for name in piv.index:
        cells = [f"{100*piv.loc[name, c]:.1f}% (n={int(cnt.loc[name, c]):,})"
                 for c in piv.columns]
        rows.append([name] + cells)
    cross = md_table(rows, ["persona"] + [str(c) for c in piv.columns])
    return band_tbl + "\n\n" + slot_tbl, cross


QB_BANDS = [(2, 3), (4, 5), (6, 7), (8, 9), (10, 16)]


def qb_band(r: int) -> str:
    if r == 0:
        return "never"
    for lo, hi in QB_BANDS:
        if lo <= r <= hi:
            return f"{lo}-{hi}" if hi < 16 else "10+"
    return "1"


def by_first_qb_round(teams: pd.DataFrame) -> str:
    band = teams.first_qb_round.map(qb_band)
    order = ["1", "2-3", "4-5", "6-7", "8-9", "10+", "never"]
    rows = []
    for b in order:
        g = teams[band == b]
        if len(g) == 0:
            continue
        lo, hi = wilson(int(g.champion.sum()), len(g))
        plo, phi = wilson(int(g.playoffs.sum()), len(g))
        rows.append((b, f"{len(g):,}", pct(g.champion.mean()),
                     f"{pct(lo)}-{pct(hi)}", pct(g.playoffs.mean()),
                     f"{pct(plo)}-{pct(phi)}", f"{g.wins.mean():.2f}",
                     f"{g.reg_pts.mean():.0f}",
                     f"{g.qb_points.mean()/17:.1f}"))
    return md_table(rows, ["first QB round", "teams", "title %", "95% CI",
                           "playoff %", "95% CI", "avg wins", "avg season pts",
                           "QB slot PPG"])


def by_qb_drafted(teams: pd.DataFrame, pool: pd.DataFrame, min_n: int = 150) -> str:
    t = teams[teams.first_qb >= 0].copy()
    t["qb_name"] = pool.player.to_numpy()[t.first_qb.to_numpy()]
    rows = []
    for name, g in t.groupby("qb_name"):
        if len(g) < min_n:
            continue
        lo, hi = wilson(int(g.champion.sum()), len(g))
        rows.append((name, len(g), g.first_qb_round.mean(), g.champion.mean(),
                     lo, hi, g.playoffs.mean(), g.qb_points.mean() / 17,
                     g.reg_pts.mean()))
    rows.sort(key=lambda r: -r[3])
    body = [(r[0], f"{r[1]:,}", f"{r[2]:.1f}", pct(r[3]), f"{pct(r[4])}-{pct(r[5])}",
             pct(r[6]), f"{r[7]:.1f}", f"{r[8]:.0f}") for r in rows]
    return md_table(body, ["first QB drafted", "teams", "avg round", "title %",
                           "95% CI", "playoff %", "QB slot PPG", "avg season pts"])


def by_activity(teams: pd.DataFrame) -> str:
    rows = []
    for name in ACTIVITY_NAMES:
        g = teams[teams.activity_name == name]
        if len(g) == 0:
            continue
        lo, hi = wilson(int(g.champion.sum()), len(g))
        rows.append((name, f"{len(g):,}", pct(g.champion.mean()),
                     f"{pct(lo)}-{pct(hi)}", pct(g.playoffs.mean()),
                     f"{g.wins.mean():.2f}", f"{g.reg_pts.mean():.0f}",
                     f"{g.adds.mean():.1f}"))
    return md_table(rows, ["activity", "teams", "title %", "95% CI", "playoff %",
                           "avg wins", "avg season pts", "avg moves"])


def counterfactuals(year: int, base: pd.DataFrame) -> str:
    """Forced first-QB round vs the same team's default, on identical seeds."""
    from .experiments import QB_ROUNDS
    rows = []
    base0 = base[base.team == 0].set_index("league")
    for r in QB_ROUNDS:
        teams, _ = load_run(year, f"cf_qb{r}")
        if teams is None:
            continue
        g = teams[teams.team == 0].set_index("league")
        ref = base0.reindex(g.index).dropna(subset=["reg_pts"])
        g = g.reindex(ref.index)
        n = len(g)
        if n == 0:
            continue
        d_pts = (g.reg_pts - ref.reg_pts).to_numpy()
        lo, hi = mean_ci(d_pts)
        tl, th = wilson(int(g.champion.sum()), n)
        label = f"{r}" if r <= 12 else "never (forced late)"
        rows.append((label, f"{n:,}", f"{g.reg_pts.mean():.0f}",
                     f"{d_pts.mean():+.1f}", f"{lo:+.1f} to {hi:+.1f}",
                     pct(g.champion.mean()), f"{pct(tl)}-{pct(th)}",
                     pct(ref.champion.mean()),
                     f"{g.qb_points.mean()/17:.1f}"))
    if not rows:
        return "_(counterfactual runs not present)_"
    return md_table(rows, ["forced first-QB round", "leagues", "season pts",
                           "vs own default", "95% CI", "title %", "95% CI",
                           "default title %", "QB slot PPG"])


def sensitivity(year: int) -> str:
    rows = []
    for tag, label in (("base", "base"),
                       ("sens_rolling", "rolling waivers"),
                       ("sens_more_late_qb", "more late-QB drafters"),
                       ("sens_more_early_qb", "more early-QB drafters")):
        teams, _ = load_run(year, tag)
        if teams is None:
            continue
        band = teams.first_qb_round.map(qb_band)
        cells = []
        for b in ["2-3", "4-5", "6-7", "8-9", "10+"]:
            g = teams[band == b]
            cells.append(pct(g.champion.mean()) if len(g) > 100 else "-")
        best = teams.groupby("persona_name").champion.mean().idxmax()
        rows.append([label, f"{len(teams)//12:,}"] + cells + [best])
    return md_table(rows, ["run", "leagues", "QB r2-3", "r4-5", "r6-7", "r8-9",
                           "r10+", "best persona"])


def waiver_diagnostics(teams: pd.DataFrame, diag: dict, pool: pd.DataFrame) -> str:
    n_leagues = len(teams) // 12
    df = pd.DataFrame({
        "player": pool.player, "pos": pool.pos,
        "adds": diag["adds"], "drops": diag["drops"],
        "drafted": diag["drafted"], "drafted_drops": diag["drafted_drops"],
    })
    df["add_rate"] = df.adds / n_leagues
    df["drop_rate"] = np.where(df.drafted > 0, df.drafted_drops / df.drafted, np.nan)

    most_added = md_table(
        [(r.player, r.pos, f"{r.add_rate:.2f}") for r in
         df.nlargest(15, "adds").itertuples()],
        ["most added", "pos", "adds per league"])
    drafted = df[df.drafted >= n_leagues * 0.35]
    most_dropped = md_table(
        [(r.player, r.pos, f"{100*r.drop_rate:.0f}%",
          f"{r.drafted/n_leagues:.2f}") for r in
         drafted.nlargest(15, "drop_rate").itertuples()],
        ["most dropped draftee", "pos", "dropped when drafted", "drafted per league"])

    qb = diag.get("qb_rostered")
    extra = []
    if qb is not None:
        extra.append(f"- QBs rostered per team at season's end: "
                     f"**{qb.mean():.2f}** (3 or more: {100*(qb >= 3).mean():.1f}% of teams)")
    extra.append(f"- Moves per manager by activity: " + ", ".join(
        f"{a} **{teams[teams.activity_name == a].adds.mean():.1f}**"
        for a in ACTIVITY_NAMES))
    return most_added + "\n\n" + most_dropped + "\n\n" + "\n".join(extra)


# --------------------------------------------------------------------------
# Validation checklist
# --------------------------------------------------------------------------
def validation(year: int, teams: pd.DataFrame, diag: dict, pool: pd.DataFrame) -> str:
    n_leagues = len(teams) // 12
    checks = []

    def add(name, ok, detail):
        checks.append((("PASS" if ok else "CHECK"), name, detail))

    # Simulated ADP against the draft board.
    drafted = diag["drafted"]
    avg_pick = np.where(drafted > 0, diag["pick_sum"] / np.maximum(drafted, 1), np.nan)
    m = (drafted > n_leagues * 0.5) & (pool.adp.to_numpy() < 200)
    corr = float(np.corrcoef(avg_pick[m], pool.adp.to_numpy()[m])[0, 1])
    top = pool.adp.to_numpy() < 100
    mad = float(np.nanmean(np.abs(avg_pick[top] - pool.adp.to_numpy()[top])))
    add("Simulated ADP tracks the draft board", corr > 0.9,
        f"r = {corr:.3f} over {int(m.sum())} players; "
        f"mean absolute gap in the top 100 = {mad:.1f} picks")

    # Quarterbacks drafted per league.
    qb_mask = (pool.pos_id.to_numpy() == 0)
    qb_per_league = drafted[qb_mask].sum() / n_leagues
    add("~20-22 QBs drafted per league", 19.0 <= qb_per_league <= 23.0,
        f"{qb_per_league:.1f} per league")

    # Round-1 discipline.
    r1 = teams.first_qb_round
    add("No quarterback goes in round 1", (r1 == 1).sum() == 0,
        f"{int((r1 == 1).sum())} teams took a QB in round 1")

    # Quarterbacks per roster.
    qb_r = diag.get("qb_rostered")
    if qb_r is not None:
        add("No team hoards quarterbacks", (qb_r >= 3).mean() < 0.05,
            f"{100*(qb_r >= 3).mean():.1f}% of teams end with 3 or more")

    # Move counts.
    ok = True
    parts = []
    for name, (lo, hi) in (("active", (15, 30)), ("moderate", (8, 15)), ("lazy", (2, 6))):
        mu = teams[teams.activity_name == name].adds.mean()
        ok &= lo <= mu <= hi
        parts.append(f"{name} {mu:.1f} (target {lo}-{hi})")
    add("Moves per season match the activity bands", ok, "; ".join(parts))

    # The disappointments the 2025 season actually produced.
    df = pd.DataFrame({"player": pool.player, "drafted": diag["drafted"],
                       "dd": diag["drafted_drops"]})
    df["rate"] = df.dd / df.drafted.clip(lower=1)
    expect = ["Tyreek Hill", "Malik Nabers", "Sam LaPorta", "Joe Mixon", "James Conner"]
    hits = df[df.player.isin(expect)]
    add("2025's busts get dropped",
        bool(len(hits) and (hits.rate > 0.25).mean() >= 0.6),
        ", ".join(f"{r.player} {100*r.rate:.0f}%" for r in hits.itertuples()))

    # The breakouts the season actually produced.
    adds = pd.DataFrame({"player": pool.player, "adds": diag["adds"]})
    top_adds = set(adds.nlargest(40, "adds").player)
    expect_add = ["Jaxson Dart", "Sam Darnold", "Brenton Strange", "Alec Pierce"]
    found = [p for p in expect_add if p in top_adds]
    add("2025's breakouts get added", len(found) >= 2,
        f"in the 40 most-added: {', '.join(found) if found else 'none'}")

    # Scoring realism.
    ppw = teams.reg_pts.mean() / 14
    add("Weekly team scores look like an ESPN PPR league", 100 <= ppw <= 130,
        f"{ppw:.1f} points per team per week")

    return md_table([(c[0], c[1], c[2]) for c in checks],
                    ["result", "check", "detail"])


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------
def build_report(year: int) -> Path:
    teams, diag = load_run(year, "base")
    if teams is None:
        raise SystemExit(f"no base run for {year}; run fantasy_sim.experiments first")
    pool, _ = clean.load(year)
    meta_path = (RESULTS / f"{year}_base" / "config.json")
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    clean_meta_path = pool_meta = Path(clean.CLEAN / f"meta_{year}.json")
    src = json.loads(pool_meta.read_text())["tier"] if pool_meta.exists() else "?"

    n_leagues = len(teams) // 12
    slot_tbl, persona_slot = by_slot(teams)

    parts = [
        f"# {year} fantasy football league simulation",
        "",
        f"{n_leagues:,} simulated 12-team ESPN PPR leagues "
        f"({len(teams):,} team-seasons), 16-round snake drafts, weekly waivers "
        f"and free agency, 14-week regular season and a 6-team playoff.",
        "",
        f"- Player data tier: `{src}`",
        f"- Waiver system: `{meta.get('waiver_system', '?')}`",
        f"- Base seed: `{meta.get('seed', '?')}` (every table here is reproducible "
        "from it)",
        "",
        "## 1. Persona leaderboard",
        "",
        "Fair share is 8.33% (one title in twelve).",
        "",
        persona_leaderboard(teams),
        "",
        "## 2. By draft slot",
        "",
        slot_tbl,
        "",
        "### Persona x draft slot (title rate)",
        "",
        persona_slot,
        "",
        "## 3. By the round the first quarterback went",
        "",
        by_first_qb_round(teams),
        "",
        "## 4. By which quarterback was drafted first",
        "",
        "`QB slot PPG` is what the team's starting quarterback slot actually "
        "produced across the season, replacements included -- so it prices "
        "injuries and benchings, not just the player.",
        "",
        by_qb_drafted(teams, pool),
        "",
        "## 5. Counterfactual: forcing the first quarterback into a given round",
        "",
        "Common random numbers: each league seed is replayed with one team "
        "forced into the strategy, and compared against that same team in the "
        "same league under its own persona.",
        "",
        counterfactuals(year, teams),
        "",
        "## 6. By activity level",
        "",
        by_activity(teams),
        "",
        "## 7. Sensitivity",
        "",
        "Title rate by first-QB round under different persona mixes and the "
        "other ESPN waiver system.",
        "",
        sensitivity(year),
        "",
        "## 8. Waiver diagnostics",
        "",
        waiver_diagnostics(teams, diag, pool),
        "",
        "## 9. Validation checklist",
        "",
        validation(year, teams, diag, pool),
        "",
    ]
    out = RESULTS / f"report_{year}.md"
    out.write_text("\n".join(parts))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the results report.")
    ap.add_argument("--year", type=int, default=2025)
    args = ap.parse_args(argv)
    print(build_report(args.year))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
