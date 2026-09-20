# Five seasons of simulated fantasy football

2018, 2019, 2023, 2024 and 2025, each played 5,000 times: 300,000 simulated
leagues and 3.6 million team-seasons. 2020 is excluded (no preseason, opt-outs,
COVID-list absences) and 2012 (the ADP source returned only eight rounds).

Every number below comes from managers who could only see what was knowable at
the moment they decided. The hindsight in this report is used to *explain*
results, never to produce them.

---

## 1. The headline: no draft strategy is reliably better than any other

Each strategy's standing is expressed as a z-score — how many standard
deviations its teams' scoring rate sat above or below the league average that
season. Zero is average; +1.0 is a full standard deviation better than the
field.

| strategy | 2018 | 2019 | 2023 | 2024 | 2025 | mean | sd | 95% CI |
|---|---|---|---|---|---|---|---|---|
| elite_te | 0.14 | 0.44 | 0.57 | -0.33 | 0.95 | 0.35 | 0.48 | -0.24 to +0.95 |
| late_qb | 0.01 | 0.78 | -0.29 | 0.29 | 0.42 | 0.24 | 0.41 | -0.26 to +0.75 |
| balanced | -0.12 | 0.41 | 0.1 | 0.55 | 0.25 | 0.24 | 0.26 | -0.09 to +0.56 |
| backup_qb_hoard | -0.2 | 0.6 | -0.14 | 0.52 | 0.09 | 0.17 | 0.37 | -0.28 to +0.63 |
| elite_qb_only | -0.84 | 0.22 | 1.31 | 0.8 | -0.69 | 0.16 | 0.93 | -0.99 to +1.32 |
| hero_rb | 1.87 | -0.14 | -0.1 | -1.44 | 0.48 | 0.13 | 1.2 | -1.35 to +1.62 |
| early_qb | -0.67 | 0.08 | 1.09 | 0.67 | -0.56 | 0.12 | 0.76 | -0.83 to +1.07 |
| qb_streamer | 0.23 | 0.32 | -1.27 | 0.15 | 0.35 | -0.04 | 0.69 | -0.90 to +0.81 |
| robust_rb | -1.66 | 0.38 | -2.26 | 1.49 | 1.6 | -0.09 | 1.78 | -2.31 to +2.12 |
| elite_te_early_qb | -0.54 | -0.03 | 0.96 | -0.59 | -0.45 | -0.13 | 0.65 | -0.94 to +0.68 |
| zero_rb | 1.79 | -3.06 | 0.03 | -2.12 | -2.44 | -1.16 | 2.02 | -3.66 to +1.34 |

Read the last column. **Not one of the eleven strategies has a five-season
average that can be distinguished from zero.** Even Zero RB, which is worst by
a distance, has an interval spanning +1.34 — because in 2018 it was the single
best strategy on the board.

This is not a failure to find a signal. It is the finding. The per-season
columns are not noise: within any one season these gaps are measured across
tens of thousands of teams and are extremely precise. They simply point in
different directions each year.

## 2. The rankings actively invert

If strategy rankings were stable, the order in one season would predict the
order in another. Rank correlation runs from +1 (identical) through 0 (no
relationship) to −1 (exactly reversed).

| season | 2018 | 2019 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| 2018 | 1.0 | -0.2 | -0.25 | -0.84 | 0.12 |
| 2019 | -0.2 | 1.0 | -0.35 | 0.43 | 0.47 |
| 2023 | -0.25 | -0.35 | 1.0 | 0.02 | -0.6 |
| 2024 | -0.84 | 0.43 | 0.02 | 1.0 | 0.08 |
| 2025 | 0.12 | 0.47 | -0.6 | 0.08 | 1.0 |

mean off-diagonal -0.111, range -0.84 to +0.47

The mean is **−0.11**: slightly worse than useless. 2018 and 2024 sit at
**−0.84**, close to a perfect reversal.

Two controls make this interpretable:

- **Random baseline.** Shuffling eleven strategies gives 0.00 ± 0.32. The
  observed −0.11 is comfortably inside that band; there is no cross-season
  signal at all.
- **Reliability ceiling.** Split each season's leagues into two halves and rank
  strategies in each independently. Agreement is **+0.93**. So the measurement
  is nearly perfect — a season's ranking reproduces itself almost exactly. The
  ranking is real, precise, and specific to that season.

A ceiling of +0.93 against an observed +(−0.11) is about as cleanly as this
question can be settled. **Strategy rankings do not transfer between seasons.**

## 3. What decides it

For each season, how far the first five rounds' picks at each position
finished above or below their own preseason projection:

| season | QB | RB | WR | TE | RB-WR |
|---|---|---|---|---|---|
| 2018 | -18 | -38 | -9 | -15 | -30 |
| 2019 | -28 | -31 | -32 | -45 | 1 |
| 2023 | -46 | -61 | -30 | -18 | -31 |
| 2024 | 2 | 0 | -40 | -26 | 41 |
| 2025 | -88 | -41 | -60 | -41 | 19 |

(All columns are negative because projections are optimistic — they price a
full healthy season. What matters is the *difference* between positions.)

The last column, how much better early running backs paid off than early
receivers, tracks strategy performance closely:

| strategy | r |
|---|---|
| zero_rb | -0.757 |
| hero_rb | -0.689 |
| elite_te_early_qb | -0.573 |
| elite_te | -0.273 |
| early_qb | 0.034 |
| elite_qb_only | 0.039 |
| qb_streamer | 0.53 |
| late_qb | 0.578 |
| backup_qb_hoard | 0.739 |
| balanced | 0.865 |
| robust_rb | 0.949 |

Robust RB correlates **+0.95** with that single number and Zero RB **−0.76**.
These strategies are not really strategies. They are leveraged bets on one
quantity, and their season is decided by it.

Balanced sits at +0.87, which is worth naming honestly: a manager who simply
follows ADP inherits a running-back-heavy early board in this era, and so
carries much of the same exposure without choosing it.

## 4. Can you see it coming in August?

If the shape of a season were visible before it started, all of the above would
be actionable. So we profiled fourteen seasons of draft boards (2010–2025,
excluding 2012 and 2020) on nine measures knowable in August — how many running
backs and receivers went in the top 24, where the first quarterback and tight
end left the board, how steep each position's tier cliff was — and tested each
against how that season actually paid off.

One of the nine reaches nominal significance: the receiver tier cliff, at
r = −0.63 (p ≈ 0.015, n = 14). **Nine tests were run.** The chance that at
least one clears p < 0.05 by luck alone is about 37%, and the finding does not
survive correction for multiple comparisons. It is a hypothesis for future
data, not a result.

Market pricing does no better: the correlation between what a position cost in
August and what it returned runs between −0.35 and +0.08 across the fourteen
seasons, with none significant.

**Nothing observable before the draft predicts which kind of season you are
about to play.**

## 5. What did work, every single year

| manager | 2018 | 2019 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| active | 9.31 | 9.59 | 9.44 | 9.36 | 9.78 |
| lazy | 5.64 | 4.89 | 5.24 | 4.84 | 4.38 |
| moderate | 7.56 | 7.33 | 7.46 | 7.7 | 7.17 |

| manager | 2018 | 2019 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| active | 1566 | 1515 | 1625 | 1619 | 1595 |
| lazy | 1505 | 1436 | 1552 | 1532 | 1490 |
| moderate | 1546 | 1483 | 1597 | 1586 | 1557 |

Active managers beat lazy ones in all five seasons, on both measures, without
exception — 3.7 to 5.4 percentage points of title rate and 61 to 105 points of
scoring. The ordering active > moderate > lazy holds 15 times out of 15.

Set that against Section 1, where no draft strategy is distinguishable from
average over the same five seasons. The contrast is the practical conclusion of
this entire project: **how you draft is a bet on the season; whether you manage
the roster afterwards is not.**


---

## 6. Season by season

### 2018

Best strategy **hero_rb** (+1.87 sd above the field), worst **robust_rb** (-1.66).

**What happened.** Le'Veon Bell was the third pick of the average draft and
scored nothing at all. He sat out the entire season in a franchise-tag dispute
and never reported. No projection could price that: he was still going in the
first round in late August, because holdouts of that length essentially do not
happen. Behind him the rest of the early running-back board came apart too —
Devonta Freeman (10 games missed), Dalvin Cook, Leonard Fournette, LeSean
McCoy. Early running backs finished 38 points below projection while early
receivers lost only 9, the most RB-hostile board of the five seasons.

**The twist.** The single largest windfall in the entire dataset was James
Conner, who went at pick 157 and scored 268 points — 215 above projection. He
was Bell's backup. The event that destroyed Robust RB *created* the season's
best value, and it was available to anyone in the last third of the draft.

**Why the winner won.** Hero RB — take one elite back early, then ignore the
position for several rounds — had its best season of the five at +1.87. Note
the mechanism in the table: one line is Conner rostered, and the rest are
Freeman, McCoy, Ajayi and Crowder *avoided*. It won by holding one running back
instead of three, and by having the roster space to absorb Conner.

**Why the loser lost.** Robust RB (−1.66) committed three early picks to the
position that collapsed. Zero RB, by contrast, posted +1.79 — its best season
ever, and the reason it cannot be called a bad strategy.

How the first five rounds paid off, by position — points versus each player's own preseason projection, and games missed:

| | QB | RB | WR | TE |
|---|---|---|---|---|
| points vs projection | -18 | -38 | -9 | -15 |
| games missed | 0.0 | 2.5 | 0.7 | — |

**What went wrong that nobody could have known.** Picks from the first five rounds, by how far they fell short:

| player | pos | ADP | projected | scored | gap | games missed |
|---|---|---|---|---|---|---|
| Le'Veon Bell | RB | 3.0 | 231 | 0 | -231 | 12 |
| Devonta Freeman | RB | 19.1 | 189 | 14 | -175 | 10 |
| Dalvin Cook | RB | 15.6 | 213 | 80 | -133 | 5 |
| Leonard Fournette | RB | 9.4 | 212 | 89 | -123 | 7 |
| Rob Gronkowski | TE | 21.0 | 204 | 98 | -106 | 3 |
| LeSean McCoy | RB | 29.9 | 205 | 110 | -95 | 1 |

**What went right that nobody could have known.** Players drafted in round 8 or later, or not drafted at all:

| player | pos | ADP | projected | scored | gap |
|---|---|---|---|---|---|
| James Conner | RB | 157.1 | 52 | 268 | +215 |
| Phillip Lindsay | RB | 344.6 | 60 | 192 | +132 |
| Tyler Boyd | WR | 304.6 | 77 | 199 | +122 |
| James White | RB | 99.5 | 119 | 233 | +114 |
| Patrick Mahomes | QB | 118.1 | 222 | 333 | +111 |
| Nick Chubb | RB | 126.4 | 47 | 149 | +102 |

**Why hero_rb won.** Each player's contribution is how much more (or less) often this strategy rostered him than the league did, times how far he beat his projection:

| player | pos | ADP |  | this strategy | league | his gap | points of edge |
|---|---|---|---|---|---|---|---|
| James Conner | RB | 157.1 | rostered | 14% | 8% | +215 | +13 |
| Devonta Freeman | RB | 19.1 | avoided | 2% | 8% | -175 | +11 |
| LeSean McCoy | RB | 29.9 | avoided | 1% | 8% | -95 | +7 |
| Jamison Crowder | WR | 79.5 | avoided | 2% | 8% | -107 | +7 |
| Jay Ajayi | RB | 46.6 | avoided | 1% | 8% | -93 | +7 |

**Why robust_rb lost.**

| player | pos | ADP |  | this strategy | league | his gap | points of edge |
|---|---|---|---|---|---|---|---|
| Devonta Freeman | RB | 19.1 | rostered | 17% | 8% | -175 | -15 |
| Dalvin Cook | RB | 15.6 | rostered | 15% | 8% | -133 | -9 |
| Jay Ajayi | RB | 46.6 | rostered | 17% | 8% | -93 | -8 |
| Royce Freeman | RB | 29.0 | rostered | 16% | 8% | -90 | -7 |
| LeSean McCoy | RB | 29.9 | rostered | 14% | 8% | -95 | -6 |


### 2019

Best strategy **late_qb** (+0.78 sd above the field), worst **zero_rb** (-3.06).

**What happened.** This is the most instructive season in the set, because the
board was *flat*: early running backs finished 31 points below projection and
early receivers 32. Neither position had an edge. And yet Zero RB recorded
−3.06, the worst single-season result of any strategy in five years.

**Why.** Zero RB does not need running backs to bust in order to win; it needs
receivers to outperform, and in 2019 they did not. Antonio Brown, drafted 21st
on average, played one game. Davante Adams — Zero RB's single largest loss at
−20 points of edge — JuJu Smith-Schuster and Tyreek Hill all missed their
marks. A strategy that concedes the position with two starting slots and a flex
needs to be compensated somewhere. On a neutral board it is not, and it loses
badly.

**What made the winner.** Late QB (+0.78) won on one player: Lamar Jackson,
available at pick 98, who produced a unanimous-MVP season worth 110 points over
projection. Waiting at quarterback is only a good idea when someone like that
is sitting in round eight, and there is no way to know in August that he is.

How the first five rounds paid off, by position — points versus each player's own preseason projection, and games missed:

| | QB | RB | WR | TE |
|---|---|---|---|---|
| points vs projection | -28 | -31 | -32 | -45 |
| games missed | 0.7 | 1.1 | 1.5 | — |

**What went wrong that nobody could have known.** Picks from the first five rounds, by how far they fell short:

| player | pos | ADP | projected | scored | gap | games missed |
|---|---|---|---|---|---|---|
| Antonio Brown | WR | 21.4 | 192 | 16 | -176 | 11 |
| Saquon Barkley | RB | 1.4 | 298 | 139 | -158 | 3 |
| Kerryon Johnson | RB | 28.5 | 192 | 68 | -123 | 6 |
| JuJu Smith-Schuster | WR | 12.9 | 228 | 106 | -121 | 2 |
| David Johnson | RB | 7.1 | 247 | 126 | -121 | 3 |
| Tyreek Hill | WR | 13.9 | 234 | 129 | -105 | 4 |

**What went right that nobody could have known.** Players drafted in round 8 or later, or not drafted at all:

| player | pos | ADP | projected | scored | gap |
|---|---|---|---|---|---|
| Patriots D/ST | DST | 159.1 | 75 | 191 | +116 |
| Lamar Jackson | QB | 97.6 | 219 | 329 | +110 |
| DJ Chark Jr. | WR | 207.7 | 100 | 198 | +98 |
| 49ers D/ST | DST | 319.7 | 70 | 160 | +90 |
| Daniel Jones | QB | 259.7 | 78 | 165 | +87 |
| Darius Slayton | WR | 435.7 | 31 | 117 | +86 |

**Why late_qb won.** Each player's contribution is how much more (or less) often this strategy rostered him than the league did, times how far he beat his projection:

| player | pos | ADP |  | this strategy | league | his gap | points of edge |
|---|---|---|---|---|---|---|---|
| Lamar Jackson | QB | 97.6 | rostered | 14% | 8% | +110 | +6 |
| Baker Mayfield | QB | 63.2 | avoided | 3% | 8% | -62 | +3 |
| Patrick Mahomes | QB | 19.3 | avoided | 4% | 8% | -64 | +3 |
| Russell Wilson | QB | 88.4 | rostered | 13% | 8% | +40 | +2 |
| Mitchell Trubisky | QB | 139.2 | avoided | 4% | 6% | -87 | +2 |

**Why zero_rb lost.**

| player | pos | ADP |  | this strategy | league | his gap | points of edge |
|---|---|---|---|---|---|---|---|
| Davante Adams | WR | 6.4 | rostered | 29% | 8% | -93 | -20 |
| Antonio Brown | WR | 21.4 | rostered | 15% | 8% | -176 | -11 |
| Brandin Cooks | WR | 39.1 | rostered | 19% | 8% | -99 | -10 |
| JuJu Smith-Schuster | WR | 12.9 | rostered | 15% | 8% | -121 | -8 |
| Austin Ekeler | RB | 61.7 | avoided | 1% | 8% | +99 | -7 |


### 2023

Best strategy **elite_qb_only** (+1.31 sd above the field), worst **robust_rb** (-2.26).

**What happened.** The worst running-back season in the set: 61 points below
projection, with the damage concentrated in career-altering injuries rather
than underperformance. Nick Chubb's knee gave way in week 2. J.K. Dobbins tore
his Achilles in week 1. Jonathan Taylor and Aaron Jones both lost six games.
Justin Jefferson, the first pick of the average draft, missed seven.

**The cleanest example of winning by avoidance.** Elite QB Only (+1.31) took
the season, and every one of its five largest contributions is a player it
*did not have*: Aaron Rodgers, who tore his Achilles four snaps into the
season; Deshaun Watson; Anthony Richardson; Daniel Jones. By spending a
round 2–4 pick on a top quarterback it was never shopping in the aisle where
every mid-tier option detonated. It did not find a bargain. It simply was not
standing there when the floor gave way.

**Why the loser lost.** Robust RB (−2.26) is a near-mirror of 2018: Aaron
Jones, Dobbins, Chubb, Taylor and Kenneth Walker, all rostered, all short.

How the first five rounds paid off, by position — points versus each player's own preseason projection, and games missed:

| | QB | RB | WR | TE |
|---|---|---|---|---|
| points vs projection | -46 | -61 | -30 | -18 |
| games missed | 1.0 | 2.6 | 1.2 | — |

**What went wrong that nobody could have known.** Picks from the first five rounds, by how far they fell short:

| player | pos | ADP | projected | scored | gap | games missed |
|---|---|---|---|---|---|---|
| Nick Chubb | RB | 12.5 | 222 | 23 | -199 | 11 |
| Justin Jefferson | WR | 1.4 | 282 | 114 | -169 | 7 |
| J.K. Dobbins | RB | 55.1 | 151 | 12 | -140 | 12 |
| Aaron Jones | RB | 38.9 | 205 | 76 | -128 | 6 |
| Jonathan Taylor | RB | 25.9 | 216 | 101 | -115 | 6 |
| Cooper Kupp | WR | 7.0 | 228 | 116 | -112 | 4 |

**What went right that nobody could have known.** Players drafted in round 8 or later, or not drafted at all:

| player | pos | ADP | projected | scored | gap |
|---|---|---|---|---|---|
| Trey McBride | TE | 350.1 | 58 | 129 | +71 |
| Cowboys D/ST | DST | 135.6 | 86 | 153 | +67 |
| Josh Reynolds | WR | 362.1 | 54 | 108 | +55 |
| Ravens D/ST | DST | 149.4 | 85 | 134 | +49 |
| Jets D/ST | DST | 154.2 | 76 | 118 | +42 |
| Latavius Murray | RB | 460.1 | 35 | 76 | +41 |

**Why elite_qb_only won.** Each player's contribution is how much more (or less) often this strategy rostered him than the league did, times how far he beat his projection:

| player | pos | ADP |  | this strategy | league | his gap | points of edge |
|---|---|---|---|---|---|---|---|
| Deshaun Watson | QB | 76.2 | avoided | 3% | 8% | -135 | +7 |
| Nick Chubb | RB | 12.5 | avoided | 5% | 8% | -199 | +6 |
| Aaron Rodgers | QB | 103.6 | avoided | 6% | 8% | -223 | +5 |
| Daniel Jones | QB | 103.9 | avoided | 6% | 8% | -170 | +3 |
| Anthony Richardson | QB | 125.5 | avoided | 6% | 7% | -200 | +3 |

**Why robust_rb lost.**

| player | pos | ADP |  | this strategy | league | his gap | points of edge |
|---|---|---|---|---|---|---|---|
| Nick Chubb | RB | 12.5 | rostered | 14% | 8% | -199 | -11 |
| Aaron Jones | RB | 38.9 | rostered | 16% | 8% | -128 | -10 |
| J.K. Dobbins | RB | 55.1 | rostered | 15% | 8% | -140 | -9 |
| Jonathan Taylor | RB | 25.9 | rostered | 15% | 8% | -115 | -8 |
| Kenneth Walker III | RB | 47.9 | rostered | 17% | 8% | -69 | -6 |


### 2024

Best strategy **robust_rb** (+1.49 sd above the field), worst **zero_rb** (-2.12).

**What happened.** The inversion of 2018. Early running backs finished exactly
on projection and early receivers 40 points under, the most RB-friendly board
of the five. Robust RB took the season at +1.49 and Zero RB finished −2.12.

**The nuance that matters most in this report.** The single biggest bust of
2024 was a running back — Christian McCaffrey, the first pick of the average
draft, 228 points below projection with nine games missed. A reader who knew
only that fact would conclude 2024 punished running backs. The opposite is
true. The *class* delivered: Barkley, Henry, Gibbs, Jacobs and Montgomery all
paid off, and Chuba Hubbard and Bucky Irving arrived off the wire.

"The top running back busted" and "running backs were a bad investment" are
different claims, and only the second one has anything to do with strategy.
The damage in 2024 was at receiver — Chris Olave, Brandon Aiyuk, Christian
Kirk — which is exactly where Zero RB had spent its early picks.

How the first five rounds paid off, by position — points versus each player's own preseason projection, and games missed:

| | QB | RB | WR | TE |
|---|---|---|---|---|
| points vs projection | +2 | +0 | -40 | -26 |
| games missed | 0.6 | 1.5 | 2.1 | — |

**What went wrong that nobody could have known.** Picks from the first five rounds, by how far they fell short:

| player | pos | ADP | projected | scored | gap | games missed |
|---|---|---|---|---|---|---|
| Christian McCaffrey | RB | 1.4 | 276 | 48 | -228 | 9 |
| Isiah Pacheco | RB | 19.8 | 192 | 46 | -146 | 9 |
| Chris Olave | WR | 26.2 | 202 | 77 | -126 | 5 |
| Brandon Aiyuk | WR | 48.1 | 183 | 62 | -121 | 6 |
| Anthony Richardson | QB | 55.2 | 227 | 129 | -98 | 4 |
| Christian Kirk | WR | 55.6 | 169 | 71 | -98 | 5 |

**What went right that nobody could have known.** Players drafted in round 8 or later, or not drafted at all:

| player | pos | ADP | projected | scored | gap |
|---|---|---|---|---|---|
| Jauan Jennings | WR | 341.5 | 60 | 170 | +110 |
| Jonnu Smith | TE | 289.5 | 69 | 160 | +91 |
| Chuba Hubbard | RB | 108.8 | 112 | 200 | +88 |
| Brock Bowers | TE | 121.7 | 119 | 206 | +87 |
| Sam Darnold | QB | 204.5 | 159 | 241 | +83 |
| Bucky Irving | RB | 152.9 | 92 | 174 | +81 |

**Why robust_rb won.** Each player's contribution is how much more (or less) often this strategy rostered him than the league did, times how far he beat his projection:

| player | pos | ADP |  | this strategy | league | his gap | points of edge |
|---|---|---|---|---|---|---|---|
| Chris Olave | WR | 26.2 | avoided | 3% | 8% | -126 | +7 |
| Brandon Aiyuk | WR | 48.1 | avoided | 4% | 8% | -121 | +5 |
| David Montgomery | RB | 54.6 | rostered | 16% | 8% | +68 | +5 |
| Derrick Henry | RB | 15.9 | rostered | 16% | 8% | +69 | +5 |
| James Conner | RB | 47.6 | rostered | 18% | 8% | +47 | +4 |

**Why zero_rb lost.**

| player | pos | ADP |  | this strategy | league | his gap | points of edge |
|---|---|---|---|---|---|---|---|
| Jonathon Brooks | RB | 85.4 | rostered | 19% | 8% | -108 | -12 |
| Tyjae Spears | RB | 91.4 | rostered | 19% | 8% | -93 | -10 |
| Chris Olave | WR | 26.2 | rostered | 15% | 8% | -126 | -9 |
| Ty Chandler | RB | 130.3 | rostered | 18% | 8% | -86 | -9 |
| Tyreek Hill | WR | 2.6 | rostered | 20% | 8% | -69 | -8 |


### 2025

Best strategy **robust_rb** (+1.60 sd above the field), worst **zero_rb** (-2.44).

**What happened.** The most quarterback-hostile season of the five by a wide
margin: early quarterbacks finished 88 points below projection, roughly double
the next-worst year. Joe Burrow and Jayden Daniels, both going in round 3, were
the two largest busts anywhere in the first five rounds, at −214 and −192.
Between them they account for more than the whole of Early QB's season deficit.

**Receivers were nearly as bad**, 60 points under, with Malik Nabers, Tyreek
Hill, Mike Evans, Terry McLaurin and Calvin Ridley all missing six games or
more. Running backs were poor in absolute terms (−41) but 19 points better than
receivers, and the waiver crop was extraordinary — Rico Dowdle (+114), Quinshon
Judkins (+114) and Kyle Monangai (+75) were all essentially free.

**Result.** Robust RB +1.60, Zero RB −2.44, and every early-quarterback
strategy underwater while Late QB finished positive. This is the season the
original version of this report was built on, and it is why that version
advised drafting a quarterback late and called Zero RB unambiguously bad. Both
claims describe 2025 accurately. Neither survives contact with 2018.

How the first five rounds paid off, by position — points versus each player's own preseason projection, and games missed:

| | QB | RB | WR | TE |
|---|---|---|---|---|
| points vs projection | -88 | -41 | -60 | -41 |
| games missed | 2.6 | 1.4 | 2.3 | — |

**What went wrong that nobody could have known.** Picks from the first five rounds, by how far they fell short:

| player | pos | ADP | projected | scored | gap | games missed |
|---|---|---|---|---|---|---|
| Joe Burrow | QB | 30.3 | 272 | 58 | -214 | 9 |
| Jayden Daniels | QB | 31.4 | 306 | 114 | -192 | 6 |
| Malik Nabers | WR | 7.5 | 248 | 57 | -191 | 9 |
| James Conner | RB | 42.3 | 206 | 33 | -173 | 10 |
| Tyreek Hill | WR | 26.4 | 217 | 53 | -164 | 9 |
| Mike Evans | WR | 30.0 | 194 | 34 | -160 | 9 |

**What went right that nobody could have known.** Players drafted in round 8 or later, or not drafted at all:

| player | pos | ADP | projected | scored | gap |
|---|---|---|---|---|---|
| Rico Dowdle | RB | 171.1 | 69 | 183 | +114 |
| Quinshon Judkins | RB | 125.4 | 41 | 155 | +114 |
| Harold Fannin Jr. | TE | 351.0 | 44 | 144 | +100 |
| Jacoby Brissett | QB | 231.0 | 86 | 164 | +78 |
| Kyle Monangai | RB | 156.8 | 42 | 117 | +75 |
| Parker Washington | WR | 384.0 | 37 | 111 | +75 |

**Why robust_rb won.** Each player's contribution is how much more (or less) often this strategy rostered him than the league did, times how far he beat his projection:

| player | pos | ADP |  | this strategy | league | his gap | points of edge |
|---|---|---|---|---|---|---|---|
| Malik Nabers | WR | 7.5 | avoided | 4% | 8% | -191 | +7 |
| Joe Burrow | QB | 30.3 | avoided | 5% | 8% | -214 | +7 |
| Mike Evans | WR | 30.0 | avoided | 4% | 8% | -160 | +7 |
| Terry McLaurin | WR | 38.3 | avoided | 3% | 8% | -135 | +7 |
| Austin Ekeler | RB | 84.3 | avoided | 4% | 8% | -158 | +6 |

**Why zero_rb lost.**

| player | pos | ADP |  | this strategy | league | his gap | points of edge |
|---|---|---|---|---|---|---|---|
| Austin Ekeler | RB | 84.3 | rostered | 24% | 8% | -158 | -24 |
| Tyreek Hill | WR | 26.4 | rostered | 17% | 8% | -164 | -13 |
| Malik Nabers | WR | 7.5 | rostered | 15% | 8% | -191 | -13 |
| Kaleb Johnson | RB | 79.2 | rostered | 18% | 8% | -123 | -12 |
| Mike Evans | WR | 30.0 | rostered | 15% | 8% | -160 | -11 |

---

## 7. Effort does not merely beat strategy; it dominates every cell

Title rate for each combination of draft strategy and manager effort, pooled
over the five seasons:

| strategy | lazy | moderate | active |
|---|---|---|---|
| elite_te | 6.00 | 7.76 | 10.09 |
| late_qb | 5.91 | 8.15 | 10.26 |
| qb_streamer | 5.17 | 8.62 | 10.51 |
| robust_rb | 5.28 | 7.73 | 9.91 |
| balanced | 4.94 | 7.63 | 9.97 |
| elite_te_early_qb | 4.84 | 7.25 | 9.36 |
| early_qb | 4.84 | 6.93 | 9.10 |
| backup_qb_hoard | 4.78 | 6.86 | 9.79 |
| elite_qb_only | 4.39 | 6.74 | 8.62 |
| hero_rb | 4.12 | 7.28 | 8.65 |
| zero_rb | 3.78 | 5.80 | 6.91 |

Two comparisons matter:

- Spread **across strategies**, holding effort at active: **3.60** points.
- Spread **across effort levels**, averaged within a strategy: **4.47** points.

Effort is the larger effect even measured this way, and unlike strategy it
never changes sign. The three best strategy-by-effort cells in every one of the
five seasons belong to active managers — fifteen out of fifteen — while the
strategy occupying those cells changes completely, from Zero RB in 2018 to
Robust RB in 2025.

Zero RB gains least from activity (3.13 against a 4.47 average). A structural
hole at a position with two starting slots and a flex is not something the
waiver wire repairs.

## 8. August cannot see the season. The first month can.

Section 4 established that nothing observable before the draft predicts how a
season will pay off. That is only half the question, because the draft is not
the last decision a manager makes.

Measuring the same RB-minus-WR payoff over different windows:

| season | weeks 1–4 | weeks 1–6 | rest of season |
|---|---|---|---|
| 2018 | −3.03 | −2.65 | −1.98 |
| 2019 | −1.56 | −0.45 | +0.60 |
| 2023 | −2.36 | −2.64 | −1.88 |
| 2024 | +3.15 | +1.73 | +3.77 |
| 2025 | +1.57 | +1.03 | +1.59 |

- Weeks 1–4 against the rest of the season: **r = +0.95**
- Weeks 1–6 against the rest of the season: **r = +0.98**

The obvious objection is that this is injury carry-over — a player who is out
in week 2 is still out in week 10, so the same absences appear on both sides.
So we recomputed the back half using **only players who were still healthy at
week 6**, which removes that path entirely. The correlation is **+0.84**.

So the signal is real and not merely mechanical, on five seasons. The quantity
that decides which draft strategy wins is invisible in August and largely
resolved by early October.

That asymmetry is the strongest practical claim this project can make, and it
points at a behaviour none of the eleven playbooks implements: **draft without a
positional thesis, then let the first month tell you what kind of season it is
and reallocate accordingly.** Section 9 tests it.

## 9. Testing the behaviour: the in-season rebalancer

Section 8 says the quantity that decides a season is invisible in August and
largely resolved by early October. So we built a manager to exploit exactly
that: **the rebalancer drafts with no positional thesis at all, then from week 4
tilts what it shops for toward whichever position is actually delivering.** The
signal it reads is `positional_form`, computed only from completed weeks — it
returns zeros before week 4 and never looks forward.

Tested the strongest way the simulator allows: identical league seeds, one team
forced into the behaviour, compared against that same team's own default.

| season | points/season | 95% CI | titles | playoffs |
|---|---|---|---|---|
| 2018 | **−6.2** | −8.9 to −3.5 | 8.34% → 7.96% | 50.1% → 48.7% |
| 2019 | **+8.3** | +6.0 to +10.6 | 8.32% → 8.92% | 49.6% → 52.8% |
| 2023 | +1.3 | −1.0 to +3.6 | 7.46% → 8.14% | 50.4% → 50.6% |
| 2024 | **+9.2** | +6.8 to +11.6 | 8.80% → 8.80% | 49.2% → 51.8% |
| 2025 | −1.9 | −4.3 to +0.6 | 7.86% → 8.00% | 50.1% → 49.7% |
| **pooled** | **+2.1** | **+1.0 to +3.2** | | |

**It works, and it barely matters.** The pooled gain is statistically solid
across 25,000 paired leagues and comes to 2.1 points on a season of roughly
1,560 — about 0.13%. Manager effort is worth 61 to 105 points over the same
seasons. And it is negative in two of five, so it does not clear the bar the
question set: a behaviour that outperforms every year, or nearly every year.

**Why it captures so little.** The information arrives after the decision it
would inform. The draft allocates sixteen picks in August and closes; the signal
resolves in October; the only lever still available is the waiver wire, which
offers marginal players. Checking the add counts confirms the lever is genuinely
weak rather than mis-aimed — no player's add rate moves by even 6%. **A waiver
wire cannot undo a draft.**

We looked for a specific culprit in 2018, the worst season, and did not find one.
The tempting story was that the signal correctly said "receivers" and so talked
the manager out of James Conner, the season's biggest prize and a running back.
The add counts do not support it: Conner's rate moves by 7 out of 257. The
honest account is the general one above, not a narrative about one player.

### What this rules out

Two candidate behaviours were built and tested against the gap Section 8
identifies. Both fail, in instructive ways:

- **Reacting to the draft in front of you** (`adaptive_vona`) loses 9.2 points
  a season in 2018 even after its confound is removed. Reacting to a positional
  run means paying the run premium.
- **Reacting to the season in front of you** (`rebalancer`) gains 2.1 points and
  swings negative in two seasons of five.

The behaviour that does outperform every year was already in the data before we
went looking for a clever one: **be an active manager.** Fifteen orderings out of
fifteen, worth twenty to fifty times what either of these behaviours produced.

## 10. Draft slot: a correction to the single-season report

The 2025-only report concluded that draft slot produced a large effect that
carried no information. Five seasons say half of that is right.

Championship rate by slot, fair share 8.33%:

| slot | 2018 | 2019 | 2023 | 2024 | 2025 | mean |
|---|---|---|---|---|---|---|
| 1 | 6.72 | 8.20 | 10.50 | 2.64 | 7.94 | 7.20 |
| 2 | 6.72 | 9.44 | 8.02 | 3.10 | 9.20 | 7.30 |
| 3 | 6.24 | 11.06 | 7.54 | 4.32 | 8.84 | 7.60 |
| 4 | 7.02 | 10.92 | 7.08 | 6.02 | 6.14 | 7.44 |
| 5 | 7.82 | 7.56 | 6.96 | 8.04 | 5.70 | 7.22 |
| 6 | 8.88 | 4.94 | 5.42 | 9.10 | 5.38 | 6.74 |
| 7 | 9.74 | 4.70 | 5.96 | 9.60 | 8.02 | 7.60 |
| 8 | 9.92 | 5.52 | 6.32 | 11.04 | 8.58 | 8.28 |
| 9 | 9.24 | 6.76 | 7.88 | 11.72 | 8.92 | 8.90 |
| 10 | 8.86 | 8.78 | 9.24 | 10.90 | 10.60 | 9.68 |
| 11 | 9.50 | 11.18 | 12.14 | 11.58 | 10.98 | 11.08 |
| 12 | 9.34 | 10.94 | 12.94 | 11.94 | 9.70 | 10.97 |

**Still right:** any one season's pattern is that season. Slot 1 won 2.64% of
titles in 2024, when Christian McCaffrey was the first pick and missed nine
games, and 10.50% in 2023.

**Now wrong:** that slot carries no information at all. Slots 11 and 12 finish
above fair share in all five seasons — ten results out of ten — and the middle
of the snake is consistently the worst place to sit, slot 6 averaging 6.74%.
The ends of a snake draft take their picks in pairs; the middle never does.

We ruled out an assignment bug: personas and activity levels are distributed
across all twelve slots to within 1.7 percentage points, consistent with
sampling noise at 5,000 leagues per slot.

**What we have not established is the mechanism.** The effect is clear in
championships and inconsistent in scoring — the back of the draft outscores the
front in three of five seasons and loses in two (+53, −18, −19, +52, +17). A
mechanism that always moves titles but only sometimes moves points is not one we
understand. Five seasons is enough to notice this and not enough to explain it.
