# 2025 fantasy football league simulation

5,000 simulated 12-team ESPN PPR leagues (60,000 team-seasons), 16-round snake drafts, weekly waivers and free agency, 14-week regular season and a 6-team playoff.

- Player data tier: `espn+ffc`
- Waiver system: `reset_inverse_standings`
- Base seed: `20250901` (every table here is reproducible from it)

## 1. Persona leaderboard

Fair share is 8.33% (one title in twelve).

| persona | teams | title % | 95% CI | x fair share | playoff % | 95% CI | avg wins | 95% CI | avg season pts | flag |
|---|---|---|---|---|---|---|---|---|---|---|
| elite_te | 4,747 | 10.74% | 9.89%-11.66% | 1.29 | 53.91% | 52.49%-55.32% | 7.22 | 7.16-7.28 | 1586 | over |
| qb_streamer | 2,475 | 10.30% | 9.17%-11.56% | 1.24 | 51.19% | 49.22%-53.16% | 7.05 | 6.97-7.14 | 1576 | over |
| robust_rb | 6,556 | 10.13% | 9.42%-10.88% | 1.22 | 56.39% | 55.19%-57.59% | 7.29 | 7.24-7.34 | 1595 | over |
| late_qb | 8,451 | 9.17% | 8.57%-9.80% | 1.10 | 50.68% | 49.61%-51.75% | 7.02 | 6.98-7.07 | 1577 | over |
| balanced | 13,108 | 8.40% | 7.94%-8.89% | 1.01 | 50.11% | 49.25%-50.96% | 7.02 | 6.99-7.06 | 1573 |  |
| hero_rb | 6,745 | 8.17% | 7.54%-8.85% | 0.98 | 50.64% | 49.45%-51.84% | 7.03 | 6.98-7.08 | 1578 |  |
| backup_qb_hoard | 3,088 | 7.87% | 6.97%-8.87% | 0.94 | 49.81% | 48.04%-51.57% | 6.98 | 6.91-7.06 | 1572 |  |
| elite_te_early_qb | 2,405 | 7.53% | 6.54%-8.65% | 0.90 | 48.15% | 46.16%-50.15% | 6.91 | 6.82-6.99 | 1564 |  |
| early_qb | 5,401 | 6.85% | 6.21%-7.56% | 0.82 | 47.03% | 45.70%-48.36% | 6.84 | 6.78-6.89 | 1561 | under |
| elite_qb_only | 2,960 | 6.22% | 5.40%-7.14% | 0.75 | 45.64% | 43.85%-47.44% | 6.82 | 6.74-6.89 | 1559 | under |
| zero_rb | 4,064 | 4.08% | 3.52%-4.74% | 0.49 | 39.94% | 38.44%-41.45% | 6.50 | 6.44-6.56 | 1533 | under |

## 2. By draft slot

**Read this table as a fact about 2025, not about snake drafts.** Every league here replays the same season, so a slot is worth whatever the players who fall to it happened to do -- and in 2025 the picks around 5 to 8 were Jefferson, Gibbs and Nabers, who between them scored at 0.0, 0.6 and 0.8 times their own pace once the fantasy playoffs arrived. The draft itself is even: expected value on draft day is flat across all twelve slots (below). None of this spread should be expected to repeat.

| draft slots | teams | title % | 95% CI | playoff % | avg wins | avg pts |
|---|---|---|---|---|---|---|
| 1-4 | 20,000 | 8.04% | 7.68%-8.43% | 48.11% | 6.88 | 1564 |
| 5-8 | 20,000 | 6.62% | 6.28%-6.97% | 49.28% | 6.97 | 1572 |
| 9-12 | 20,000 | 10.34% | 9.93%-10.77% | 52.62% | 7.14 | 1582 |

| slot | teams | title % | 95% CI | playoff % | avg pts |
|---|---|---|---|---|---|
| 1 | 5,000 | 7.34% | 6.65%-8.10% | 46.72% | 1561 |
| 2 | 5,000 | 9.54% | 8.76%-10.39% | 48.50% | 1567 |
| 3 | 5,000 | 8.48% | 7.74%-9.28% | 49.28% | 1566 |
| 4 | 5,000 | 6.82% | 6.15%-7.55% | 47.94% | 1563 |
| 5 | 5,000 | 4.92% | 4.35%-5.55% | 46.64% | 1560 |
| 6 | 5,000 | 5.54% | 4.94%-6.21% | 47.64% | 1569 |
| 7 | 5,000 | 7.60% | 6.90%-8.37% | 50.40% | 1577 |
| 8 | 5,000 | 8.40% | 7.66%-9.20% | 52.42% | 1583 |
| 9 | 5,000 | 9.74% | 8.95%-10.59% | 52.14% | 1582 |
| 10 | 5,000 | 9.48% | 8.70%-10.32% | 52.08% | 1582 |
| 11 | 5,000 | 11.30% | 10.45%-12.21% | 53.60% | 1583 |
| 12 | 5,000 | 10.84% | 10.01%-11.73% | 52.64% | 1582 |

### The draft itself is fair

| slot | draft-day expected ppg | points those picks scored |
|---|---|---|
| 1 | 182.3 | 2383 |
| 2 | 183.0 | 2400 |
| 3 | 181.8 | 2373 |
| 4 | 182.1 | 2386 |
| 5 | 182.1 | 2365 |
| 6 | 180.0 | 2325 |
| 7 | 180.0 | 2365 |
| 8 | 181.3 | 2393 |
| 9 | 179.8 | 2395 |
| 10 | 179.7 | 2409 |
| 11 | 180.2 | 2393 |
| 12 | 179.9 | 2434 |

Spread in draft-day expected value across slots: **1.8%** -- flat. The spread in what those picks went on to score is several times larger, and that difference is the season, not the format.

### Persona x draft slot (title rate)

| persona | 1-4 | 5-8 | 9-12 |
|---|---|---|---|
| backup_qb_hoard | 7.3% (n=1,076) | 5.5% (n=1,031) | 10.9% (n=981) |
| balanced | 8.7% (n=4,334) | 6.0% (n=4,407) | 10.5% (n=4,367) |
| early_qb | 6.3% (n=1,827) | 5.6% (n=1,827) | 8.8% (n=1,747) |
| elite_qb_only | 5.6% (n=1,006) | 4.7% (n=1,007) | 8.6% (n=947) |
| elite_te | 10.3% (n=1,580) | 8.9% (n=1,550) | 12.9% (n=1,617) |
| elite_te_early_qb | 8.3% (n=803) | 5.2% (n=794) | 9.0% (n=808) |
| hero_rb | 6.8% (n=2,260) | 7.3% (n=2,229) | 10.4% (n=2,256) |
| late_qb | 9.0% (n=2,790) | 6.4% (n=2,821) | 12.0% (n=2,840) |
| qb_streamer | 9.0% (n=831) | 8.7% (n=809) | 13.2% (n=835) |
| robust_rb | 10.5% (n=2,145) | 10.1% (n=2,192) | 9.8% (n=2,219) |
| zero_rb | 3.3% (n=1,348) | 2.9% (n=1,333) | 6.0% (n=1,383) |

## 3. By the round the first quarterback went

| first QB round | teams | title % | 95% CI | playoff % | 95% CI | avg wins | avg season pts | QB slot PPG |
|---|---|---|---|---|---|---|---|---|
| 2-3 | 21,014 | 5.98% | 5.67%-6.31% | 45.11% | 44.44%-45.78% | 6.77 | 1555 | 18.2 |
| 4-5 | 9,945 | 9.10% | 8.55%-9.68% | 54.41% | 53.43%-55.39% | 7.22 | 1590 | 18.2 |
| 6-7 | 6,176 | 9.38% | 8.67%-10.13% | 54.23% | 52.98%-55.47% | 7.21 | 1587 | 18.0 |
| 8-9 | 11,877 | 9.86% | 9.34%-10.41% | 52.41% | 51.51%-53.31% | 7.10 | 1582 | 17.5 |
| 10+ | 10,988 | 9.90% | 9.36%-10.47% | 50.38% | 49.45%-51.32% | 7.02 | 1574 | 17.6 |

## 4. By which quarterback was drafted first

`QB slot PPG` is what the team's starting quarterback slot actually produced across the season, replacements included -- so it prices injuries and benchings, not just the player.

| first QB drafted | teams | avg round | title % | 95% CI | playoff % | QB slot PPG | avg season pts |
|---|---|---|---|---|---|---|---|
| Drake Maye | 1,185 | 11.3 | 13.25% | 11.44%-15.30% | 57.30% | 19.3 | 1600 |
| Brock Purdy | 3,555 | 7.9 | 10.97% | 9.98%-12.04% | 52.21% | 17.4 | 1580 |
| Justin Herbert | 1,418 | 10.8 | 10.58% | 9.08%-12.29% | 52.89% | 18.1 | 1588 |
| Bo Nix | 3,866 | 7.0 | 10.42% | 9.50%-11.43% | 52.56% | 17.7 | 1588 |
| Dak Prescott | 3,123 | 8.3 | 10.31% | 9.29%-11.43% | 54.02% | 17.7 | 1588 |
| Justin Fields | 1,178 | 11.1 | 10.02% | 8.43%-11.86% | 50.76% | 17.1 | 1570 |
| Jared Goff | 2,298 | 9.5 | 9.92% | 8.77%-11.21% | 51.31% | 17.5 | 1576 |
| Caleb Williams | 1,873 | 10.4 | 9.88% | 8.61%-11.31% | 53.66% | 18.3 | 1585 |
| Patrick Mahomes | 4,255 | 5.1 | 9.75% | 8.90%-10.68% | 62.47% | 19.5 | 1617 |
| Trevor Lawrence | 575 | 12.9 | 9.39% | 7.27%-12.05% | 47.13% | 17.2 | 1561 |
| Baker Mayfield | 4,169 | 5.5 | 9.31% | 8.46%-10.23% | 50.54% | 17.2 | 1575 |
| J.J. McCarthy | 1,432 | 11.0 | 9.29% | 7.89%-10.90% | 48.81% | 17.0 | 1570 |
| Aaron Rodgers | 413 | 10.4 | 8.96% | 6.57%-12.10% | 45.28% | 17.6 | 1569 |
| Matthew Stafford | 192 | 12.3 | 8.85% | 5.60%-13.72% | 53.65% | 18.0 | 1578 |
| Sam Darnold | 162 | 11.9 | 8.64% | 5.22%-13.98% | 50.00% | 17.2 | 1559 |
| Jaxson Dart | 811 | 9.1 | 8.26% | 6.56%-10.36% | 51.54% | 17.2 | 1572 |
| Kyler Murray | 3,105 | 8.6 | 8.02% | 7.12%-9.03% | 49.37% | 16.9 | 1568 |
| Josh Allen | 4,944 | 2.6 | 7.28% | 6.59%-8.04% | 59.97% | 21.9 | 1605 |
| Jordan Love | 709 | 12.3 | 7.19% | 5.51%-9.33% | 47.53% | 17.5 | 1565 |
| C.J. Stroud | 502 | 12.5 | 7.17% | 5.22%-9.77% | 44.42% | 16.6 | 1553 |
| Jayden Daniels | 4,932 | 3.1 | 6.73% | 6.07%-7.47% | 39.96% | 17.0 | 1540 |
| Jalen Hurts | 4,813 | 3.6 | 6.65% | 5.98%-7.39% | 54.89% | 18.7 | 1589 |
| Joe Burrow | 4,921 | 3.0 | 6.32% | 5.67%-7.03% | 37.11% | 16.3 | 1526 |
| Lamar Jackson | 4,976 | 2.4 | 4.26% | 3.73%-4.86% | 38.65% | 17.1 | 1533 |
| Cam Ward | 183 | 12.0 | 3.83% | 1.87%-7.68% | 45.36% | 16.9 | 1559 |

## 5. Counterfactual: forcing the first quarterback into a given round

Common random numbers: each league seed is replayed with one team forced into the strategy, and compared against that same team in the same league under its own persona.

| forced first-QB round | leagues | season pts | vs own default | 95% CI | title % | 95% CI | default title % | QB slot PPG |
|---|---|---|---|---|---|---|---|---|
| 2 | 1,200 | 1545 | -18.1 | -23.5 to -12.7 | 4.17% | 3.17%-5.45% | 7.17% | 18.7 |
| 3 | 1,200 | 1551 | -11.8 | -16.2 to -7.4 | 5.83% | 4.64%-7.31% | 7.17% | 18.0 |
| 4 | 1,200 | 1572 | +8.5 | +3.7 to +13.3 | 6.67% | 5.39%-8.22% | 7.17% | 18.0 |
| 5 | 1,200 | 1580 | +16.6 | +11.8 to +21.5 | 7.75% | 6.37%-9.40% | 7.17% | 18.0 |
| 6 | 1,200 | 1573 | +9.4 | +4.5 to +14.2 | 8.67% | 7.20%-10.39% | 7.17% | 17.9 |
| 7 | 1,200 | 1568 | +4.7 | +0.0 to +9.4 | 7.58% | 6.22%-9.22% | 7.17% | 17.6 |
| 8 | 1,200 | 1571 | +7.4 | +2.9 to +12.0 | 8.08% | 6.67%-9.76% | 7.17% | 17.5 |
| 9 | 1,200 | 1569 | +6.2 | +1.7 to +10.8 | 9.25% | 7.74%-11.02% | 7.17% | 17.5 |
| 10 | 1,200 | 1571 | +7.5 | +2.9 to +12.1 | 10.42% | 8.81%-12.27% | 7.17% | 17.6 |
| 11 | 1,200 | 1571 | +7.6 | +3.1 to +12.2 | 9.25% | 7.74%-11.02% | 7.17% | 17.8 |
| 12 | 1,200 | 1572 | +8.8 | +4.2 to +13.3 | 9.67% | 8.12%-11.47% | 7.17% | 17.7 |
| never (forced late) | 1,200 | 1555 | -8.3 | -13.2 to -3.4 | 8.83% | 7.36%-10.57% | 7.17% | 17.2 |

## 6. By activity level

| activity | teams | title % | 95% CI | playoff % | avg wins | avg season pts | avg moves |
|---|---|---|---|---|---|---|---|
| active | 33,145 | 9.45% | 9.14%-9.77% | 55.70% | 7.27 | 1597 | 17.6 |
| moderate | 20,846 | 7.64% | 7.28%-8.01% | 46.03% | 6.83 | 1558 | 9.2 |
| lazy | 6,009 | 4.61% | 4.11%-5.17% | 32.32% | 6.10 | 1493 | 4.0 |

## 7. Sensitivity

Title rate by first-QB round under different persona mixes and the other ESPN waiver system.

| run | leagues | QB r2-3 | r4-5 | r6-7 | r8-9 | r10+ | best persona |
|---|---|---|---|---|---|---|---|
| base | 5,000 | 5.98% | 9.10% | 9.38% | 9.86% | 9.90% | elite_te |
| rolling waivers | 2,000 | 6.15% | 8.75% | 9.48% | 9.60% | 10.14% | robust_rb |
| more late-QB drafters | 2,000 | 6.05% | 8.02% | 9.48% | 10.48% | 9.23% | robust_rb |
| more early-QB drafters | 2,000 | 6.78% | 8.09% | 9.95% | 9.42% | 10.00% | robust_rb |

## 8. Waiver diagnostics

| most added | pos | adds per league |
|---|---|---|
| Packers D/ST | DST | 1.89 |
| Eddy Pineiro | K | 1.79 |
| Jason Myers | K | 1.75 |
| Chargers D/ST | DST | 1.75 |
| Daniel Jones | QB | 1.73 |
| Darren Waller | TE | 1.70 |
| Jaguars D/ST | DST | 1.70 |
| Brock Purdy | QB | 1.69 |
| Patriots D/ST | DST | 1.60 |
| Matthew Stafford | QB | 1.54 |
| Bills D/ST | DST | 1.54 |
| Juwan Johnson | TE | 1.53 |
| AJ Barner | TE | 1.51 |
| Browns D/ST | DST | 1.50 |
| Eagles D/ST | DST | 1.46 |

| most dropped draftee | pos | drops per draft | drafted per league |
|---|---|---|---|
| Joe Burrow | QB | 1.00 | 1.00 |
| Kyler Murray | QB | 1.00 | 1.00 |
| Brandon Aiyuk | WR | 0.99 | 0.65 |
| Ray-Ray McCloud III | WR | 0.99 | 0.45 |
| Najee Harris | RB | 0.99 | 0.80 |
| Brock Purdy | QB | 0.99 | 1.00 |
| Braelon Allen | RB | 0.99 | 0.89 |
| Joe Mixon | RB | 0.99 | 1.00 |
| J.J. McCarthy | QB | 0.99 | 0.97 |
| C.J. Stroud | QB | 0.98 | 0.46 |
| Aaron Rodgers | QB | 0.98 | 0.35 |
| Austin Ekeler | RB | 0.97 | 1.00 |
| Dont'e Thornton Jr. | WR | 0.97 | 0.61 |
| Justin Fields | QB | 0.96 | 0.98 |
| Jaxson Dart | QB | 0.96 | 0.53 |

- QBs rostered per team at season's end: **1.37** (3 or more: 0.2% of teams)
- Kicker and defence churn: **61.5** adds per league across all twelve teams (streaming).
- Moves per manager by activity: active **17.6**, moderate **9.2**, lazy **4.0**

## 9. Validation checklist

| result | check | detail |
|---|---|---|
| PASS | Simulated ADP tracks the draft board | r = 0.934 over 188 players; mean absolute gap in the top 100 = 5.5 picks |
| PASS | ~20-22 QBs drafted per league | 20.4 per league |
| PASS | No quarterback goes in round 1 | 0 teams took a QB in round 1 |
| PASS | No team hoards quarterbacks | 0.2% of teams end with 3 or more |
| PASS | Moves per season match the activity bands | active 17.6 (target 15-30); moderate 9.2 (target 8-15); lazy 4.0 (target 2-6) |
| PASS | 2025's busts get dropped | Sam LaPorta 22%, Malik Nabers 55%, Joe Mixon 99%, Tyreek Hill 58%, James Conner 86% |
| PASS | 2025's breakouts get added | in the 40 most-added skill players: Jaxson Dart, Brenton Strange |
| PASS | The snake draft is even across slots | draft-day expected value varies 1.9% across the twelve slots |
| PASS | Weekly team scores look like an ESPN PPR league | 112.3 points per team per week |

## 10. Summary

### How much of this matters

Persona, activity level and quarterback timing together account for **10% of the variance in season points**. The other 90% is draft luck, how the players actually performed, and the schedule.

That sets the ceiling on what any of these tables can do for one league. Ranking twelve teams by strategy alone and correlating with their real finish gives a rank correlation of **0.21 on average, with a standard deviation of 0.29** and a 10th-to-90th-percentile range of -0.17 to 0.57. A single season can neither confirm nor refute any of it.

### What the season says

**Roster construction mattered more than quarterback timing.** The spread between the best and worst persona (elite_te at 10.74%, zero_rb at 4.08%) is wider than anything the quarterback tables produce.

**The mistake is the early reach, not the timing after it.** The counterfactual in section 5 is the load-bearing version of this, because it replays the same league seed with one team forced into a round and compares it against that same team's own default. Forcing a quarterback in rounds 2 and 3 costs 18 and 12 season points. Every round from 4 to 12 is worth between +5 and +17 instead, peaking around round 5 -- a band, not a trend. The raw table in section 3 looks more like 'later is better' only because the personas that reach early are worse in other ways too.

**No quarterback taken in the first five rounds paid for himself.** The best of them, Josh Allen, still came in at 7.28% -- under the 8.33% a team gets for turning up. Drake Maye did the most for the teams that took him, at a fraction of the cost. Section 4 prices each one.

**Attention beat every draft strategy.** Active managers won 9.45% of titles against 4.61% for lazy ones, and the gap in season points is larger still. It comes entirely from in-season work.

**Draft slot mattered a great deal in 2025 -- and tells you nothing about next year.** Title rates ran from 4.92% at slot 5 to 11.30% at slot 11, well outside the confidence intervals. But draft-day expected value is flat across all twelve slots (section 2), so this is not the format favouring anybody: it is one season's players landing where they landed.

### Caveats

1. **One season, one set of outcomes.** Every league replays the same 2025: the same players get hurt in the same weeks and the same breakouts happen. The variation is in drafts, schedules, waiver runs and manager noise, not in football. The draft-slot table is the clearest illustration -- a large, confidently-measured effect that is pure season-specific luck. Adding 2023 and 2024 is what separates the two.
2. **Data tier: `espn+ffc`.** Player pool, weekly projections and scoring are ESPN's own; the draft board is real Fantasy Football Calculator mock-draft ADP. Availability and depth-chart roles come from nflverse.
3. **Managers are model managers.** They do not trade, do not read beat reports, and do not tilt. Their disagreements are Gaussian noise rather than genuinely different theories of football.
4. **Title rates are noisy; season points are not.** A league produces one champion, so even 5,000 leagues gives a few hundred titles per persona. Prefer season points and playoff rate when ranking, and read the intervals rather than the point estimates.
5. **The persona mix is an assumption**, set from 2025 draft advice rather than observed from real leagues. Section 7 re-runs the question under different mixes and the other ESPN waiver system; anything that moves between them is not a conclusion.
