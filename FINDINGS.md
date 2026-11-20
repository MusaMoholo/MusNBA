# Findings — measured facts

Measured facts only. Each entry states its date and population.

## 1. Data sources (probed 19 Nov 2026)

- ESPN site API answers plain requests (no key, no special headers): scoreboard by date, team schedules
  (80 scheduled regular-season games per team — the two NBA Cup-determined games are not yet listed),
  rosters with injury status, league injury report, game summaries.
- A final-game summary carries the box score (MIN, PTS, FG, 3PT, FT, REB, OREB, DREB, AST, STL, BLK, TO,
  PF, +/−, starter, DNP reason), header linescores, ~530 plays with type ids/text, period, clock, score,
  participants (athlete ids: shooter, assister, fouled, etc.), shot x/y (sentinel −214748340 when absent),
  every substitution, and betting lines (`pickcenter`). Typical size ~490 KB raw, ~45 KB gzip.
- ESPN date-range scoreboard (`dates=YYYYMMDD-YYYYMMDD`) returns 400. NBA CDN/stats endpoints return 403
  to plain requests.
- First collection: 345 requests, 222 finals, 0 failures, ~4 minutes at 0.35 s spacing.

## 2. League environment through 18 Nov 2026 (222 games)

ORtg 111.2 per 100 (possessions = FGA − OREB + TOV + 0.44 FTA, team turnovers included), pace 101.7,
113.7 points per team game, eFG 53.7%, TOV 15.0%, OREB 27.3%, FT rate 0.282, 3PA rate 0.433, 3P 35.3%,
2P 54.2%, FT 77.8%, assisted FG 65.3%. Quarter scoring shares Q1–Q4: 25.0 / 25.4 / 25.5 / 24.2%.
Mean home margin +0.95 (n=222, SE ≈ 0.9). Overtime in 5.4% of games.

## 3. Play-by-play reconstruction (222 games, 5,001 player-games, 19 Nov 2026)

- After fixes, per-player sums of play-by-play events differ from the box score in: points 0.08%, FGM 0.04%,
  FGA 0.48%, 3PA 0.16%, FTA 0.08%, OREB 0.46%, DREB 0.56%, AST 0.62%, STL 0.72%, BLK 0.30%, TOV 0.46%, PF 0.58%
  of player-games; on-court minutes differ by more than a minute in 0.92%.
- Box-score FGA excludes missed end-of-period heaves (counting them gave 4.8% FGA mismatch). Missed shots
  followed by the shooter's free-throw trip are counted (excluding them made agreement worse).
- Offensive fouls are often logged only as "Offensive Foul Turnover"; shot-clock and 8-second violations are team
  turnovers; technical fouls and timeouts include bench players and must not mark quarter starters.
- Residual lineup glitches: 28 of ~1,830 team-periods do not sum to 5 × period length; 41 periods inferred more
  than five starters; 48 substitutions remove a player not on court.
- Quarter minute shares in competitive games (|margin after Q3| ≤ 15): starters 26.2 / 23.6 / 25.9 / 24.3%,
  bench 22.9 / 27.4 / 23.5 / 26.2%.
- Players front-load scoring: Luka Doncic scores 37% of his regulation points in Q1 on 33% of his minutes;
  Alex Sarr 47% on 31%; Jayson Tatum 37% on 36% (minimum 375 minutes, 150 points).

## 3b. Historical play-by-play (sportsdataverse ESPN files, regular season)

| Season | Games | Points off | Minutes off (>1 min) | Lineup issues (over five / seconds off) |
|---|---|---|---|---|
| 2022-23 | 1,231 | 0.16% | 0.76% | 234 / 75 |
| 2023-24 | 1,232 | 0.08% | 0.58% | 259 / 101 |
| 2024-25 | 1,234 | 0.05% | 0.84% | 287 / 107 |
| 2025-26 | 1,234 | 0.09% | 0.97% | 295 / 203 |

- `points_attempted` is blank for ~99% of shots in 2022-23 and 2023-24. Inferred from type (free throws), points
  scored (makes), "three point" in the text, else location; agreement with the real field: 99.95–99.96% on the
  shots where both exist. Location alone: 99.93% (raw coordinates in feet, basket at (25, 0)).
- Missed threes without "three point" in the text are mostly "running pullup jump shot" descriptions.
- One 2025-26 game logs its clock as M:SS:hundredths; 33 games in 2025-26 carry an empty placeholder box row.
- Raw files: 8 parquet files, 87.7 MB, sha256 in `data/raw/hoopr/manifest.json` (retrieved 19 Nov 2026).

## 3c. Segments (ENGINE_PLAN M2; 19 Nov 2026)

| Season | Games | Segments | Points off | Clock off | Possessions v box estimate | Flagged games |
|---|---|---|---|---|---|---|
| 2022-23 | 1,231 | 297,848 | 0.45% | 0.28% | 101.4 v 101.7 | 22 |
| 2023-24 | 1,232 | 296,688 | 0.37% | 0.36% | 100.6 v 100.8 | 26 |
| 2024-25 | 1,234 | 299,695 | 0.20% | 0.26% | 100.8 v 101.0 | 18 |
| 2025-26 | 1,234 | 303,553 | 0.45% | 0.26% | 101.5 v 101.6 | 23 |
| 2026-27 to 18 Nov | 222 | 55,210 | 0.00% | 0.11% | 101.1 v 101.5 | 1 |

- Points mismatches are feed gaps: the feed's own scoring plays disagree with its box score (two games miss 24
  and 34 points of play-by-play). Late-logged plays (e.g. a challenge overturned into a turnover) appear after the
  period's end in feed order: segments order plays by game clock.
- 2025-26 + 2026-27 reconciled games: time to action by start — after a made basket 15.3 s (median 15), defensive
  rebound 9.3 (8), offensive rebound 3.1 (2), made free throw 14.0, steal 6.4 (5), defensive foul 9.3, dead-ball
  turnover 13.0, period start 16.6. Segment ends: shot 72.4%, turnover 11.9%, fouled shot 6.6%, non-shooting foul
  6.5%, period end 1.6%, unresolved 0.5%.
- Shot zones (raw feet, basket (25,0)): above-break 3 28.8%, rim 26.8%, paint 24.1%, corner 3 12.9%, mid 7.3%;
  FG% 34.9 / 67.9 / 44.8 / 38.0 / 40.8. Made FGs assisted 63.9%; missed FGs blocked 10.3%; turnovers that are
  steals 57.3%; offensive share of rebounds 30.9% (team rebounds 12.9% of all).

## 3d. Rotations (ENGINE_PLAN M3; 19 Nov 2026)

| Season | Subs per team-game | At 12:00 / 5:00 | Foul windows | Timeouts | Unlogged stoppage | Minutes off |
|---|---|---|---|---|---|---|
| 2022-23 | 27.2 | 14.0% | 42.6% | 28.3% | 7.1% | 0.43% |
| 2023-24 | 27.5 | 14.3% | 41.3% | 29.1% | 7.5% | 0.05% |
| 2024-25 | 28.6 | 14.7% | 40.3% | 29.3% | 7.8% | 0.24% |
| 2025-26 | 31.0 | 15.0% | 42.2% | 27.7% | 7.7% | 0.05% |
| 2026-27 to 18 Nov | 34.5 | 15.0% | 43.3% | 26.2% | 8.1% | 0.30% |

- Substitution volume rises every season; the early-season 2026-27 rate is the highest. Recency matters for M7.
- Quarter-start lineup changes are logged as substitutions at 12:00 in every season (not a feed difference).
- 18% of dead-ball windows contain a substitution (2026-27). Clock-ordered stints reconcile better than the
  feed-ordered per-period parser (minutes 0.30% v 0.92% off this season).
- Replay v0 backtest (2025-26 from 1 March, 7,229 player-games, players who played known): mean-minutes MAE 5.33
  (EWMA of recent minutes 5.29); rotation players (20+ min) 5.17 v 5.24; 10–90% interval coverage 60.1% v 80%
  nominal (simulated SD 4.4 min for rotation players) — rotation shape is right, game-state variance is missing.

## 3e. Game types (2022-23 → 2025-26, reconciled team-games)

| Type | Games | Players used (1+ min) | Top-8 share of minutes | Starter min | Top player min | Subs per team | Possessions per team | Points per possession |
|---|---|---|---|---|---|---|---|---|
| Regular season | 4,931 | 10.6 | 90.6% | 30.5 | 36.3 | 28.6 | 101.1 | 1.128 |
| Playoffs | 335 | 10.4 | 93.8% | 33.5 | 39.9 | 29.6 | 97.2 | 1.108 |
| Play-in | 24 | 10.3 | 94.6% | 34.0 | 40.4 | 31.1 | 99.0 | 1.106 |

Playoff rotations concentrate minutes on the top eight and the stars, pace drops ~4% and efficiency ~2%;
substitution counts barely change (blowouts still use the bench). History now includes playoffs and play-in
(5,290 games); reconciliation is unchanged.

## 3f. Profiles and node baselines (M4; folds F1–F4, final test untouched)

- Point-in-time profiles: 116,121 player-games, 99.2% with earlier history. Pre-game usage v the game's usage:
  r = 0.70 (players with 25+ offensive segments); minutes r = 0.79; three-point share of shots r = 0.77.
- Playoff time to action exceeds the regular season at every start type: +0.59 s after made baskets, +0.53 s after
  defensive rebounds, +0.50 s after defensive fouls, +0.40 s after steals, +0.18 s after offensive rebounds.

| Node | League baseline | Profile baseline | Gain |
|---|---|---|---|
| Who (of five) | 1.6094 | 1.567–1.571 | 2.5% |
| What (5 zones, turnover, foul drawn) | 1.843–1.851 | 1.733–1.748 | 5.9% |
| Shot result (zone known) | 0.655–0.658 | 0.653–0.656 | 0.3% |
| Rebound side | 0.594–0.621 | 0.590–0.617 | 0.6% |

"Who" has little room above usage shares — the choice is genuinely uncertain (entropy of typical usage shares
≈1.57). Shot results are mostly zone; player accuracy adds a little and context (clock, defenders) is the next test.

## 3g. M5 v1 — LightGBM per decision (folds F1–F4; logs `analysis/experiments/20261119T183451Z_m5_lightgbm.json`, free throw re-run after the fix)

Gain = held-out log-loss improvement over the better of the league and player-profile baselines.

| Node | Mean gain | Worst fold | Mean ECE (profile baseline) | Top inputs |
|---|---|---|---|---|
| duration (13 bins) | +1.32% | +1.31% | 0.0025 (0.0022) | start type, clock, margin |
| event | +15.13% | +14.06% | 0.0036 (0.0030) | time to event, game clock, margin, team fouls |
| who | +2.08% | +2.03% | 0.0017 (0.0120) | usage share and rank on the floor, usage |
| what (8 classes) | +5.33% | +5.13% | 0.0046 (0.0108) | time to action, start type, shot profile |
| shot result | +2.10% | +2.01% | 0.0054 (0.0043) | distance, zone, shooter accuracy |
| assisted | +25.45% | +24.86% | 0.0043 (0.0280) | zone, start type, time to action, self-creation |
| assister | +2.44% | +2.14% | 0.0061 (0.0183) | assist share on the floor |
| blocked | +6.39% | +6.10% | 0.0047 (0.0037) | distance, zone, rim protection on the floor |
| blocker | +1.20% | +0.88% | 0.0071 (0.0104) | block share on the floor |
| rebound (4 classes) | +7.95% | +7.64% | 0.0059 (0.0132) | miss type, distance, rebounding on the floor |
| rebounder | +1.52% | +1.36% | 0.0034 (0.0061) | side rebound rate, share, shooter |
| turnover type | +4.84% | +4.70% | 0.0125 (0.0247) | time to turnover, live-ball share |
| stealer | +0.10% | +0.05% | 0.0024 (0.0049) | steal share on the floor |
| fouler | +1.58% | +1.43% | 0.0017 (0.0018) | foul-rate share, fouls so far |
| free throw | +0.14% | +0.00% | 0.0052 (0.0047) | FT%, attempt order |

- Every node is at least level with its best baseline on every fold; calibration error ≤ 0.016 everywhere.
- **Negative result / caught leak**: the first free-throw run showed +15%. Segments stored only made-of-attempted
  per trip, and the dataset assigned makes to the first attempts, so `attempt` leaked the label. Fixed by recording
  each trip's real sequence (`ft_seq`). Real effect: first free throw of a two-shot trip 75.6% made, second 80.4%
  (2025-26). Lesson: any feature derived from within-segment order needs the real order.
- "Stealer" and "free throw" sit at their baselines: steal rate and FT% carry nearly all the signal.

## 3h. M5 tuning (folds F1–F4, 15 decisions; logs `analysis/experiments/20261119T19*`; 19 Nov 2026)

All comparisons are paired on identical held-out rows (`scripts/compare.py`), standard errors clustered by game.

- **Training noise.** Changing only the LightGBM seed moves a node's held-out log loss by (RMS over folds, % of loss):
  who 0.012, what 0.018, shot result 0.017, rebounder 0.018, duration 0.024, rebound 0.026, free throw 0.048, stealer
  0.055, assister 0.059, event 0.060, blocked 0.061, blocker 0.074, fouler 0.079, turnover type 0.108, assisted 0.154 —
  with game-clustered |z| up to 3.4. The z-score alone is too lenient; verdicts now also require beating this floor.
- **Sample-weight decay — negative result.** weight = 0.5^(age / half-life) on training rows, against no decay:
  one season worse on 10 of 15 nodes (none better; chain +1.68 nats per game, z up to +22), two seasons worse on 6
  (+0.69 nats per game). Shorter is worse. No decay is kept: all 2022-26 possessions count equally.
  Half a season is worse on all 15 nodes (+4.53 nats per game).
- **In-game form ("heat check", D3).** Leaving out the actor's makes, attempts and points so far this game costs
  +0.30 nats per game: who +0.038% (z 5.3), what +0.044%, turnover type +0.136%. **No hot hand in shot making**: shot
  result is unchanged without them (+0.001%, z 0.1) — a player's night changes how often and what he shoots, not whether
  it goes in. Free throws are better without them (−0.066%, z −2.7): dropped for that node only.
- **Team style (12 inputs: offence's pace, three/rim shares, turnover, foul-drawn and offensive-rebound rates; the same
  allowed by the defence — style, not strength, D18)**: chain −1.31 nats per game (z −5 to −8). Better for duration
  −0.174% (z −14.7), what −0.153% (z −9.1), shot result −0.033% (z −2.5); **worse** for assisted +0.159%, assister
  +0.069%, blocker +0.094%, turnover type +0.128% and event; neutral elsewhere. Kept for duration, what and shot result.
- **Schedule — negative result.** Rest days of both teams and day of season: chain +0.02 nats per game, no node better
  (blocker and turnover type worse). Rest does not move possession-level decisions; fatigue belongs to minutes (M7).
- **Clutch flag — negative result** (last 5 minutes, margin ≤ 5): chain +0.03 nats per game (z 0.3); trees already
  combine period, clock and margin.
- **Feature decay (profiles), against the defaults** (batch 2, All-Star games excluded): role half-life 3 games +0.02,
  10 games +0.05 nats per game (neutral; 5 kept); usage 8 games **+1.04** (z +10; worse on 9 nodes, blocker +0.33%,
  turnover type +0.20%) — a shorter usage memory loses signal; usage 30 games −0.13 (z −1.3, mixed: blocker −0.26% and
  rebounder −0.06% better, what +0.04% and assister +0.03% worse — rebounding/defence rates settle slower than usage and
  shot mix; next: split that family); accuracy 20 games +0.22 (z +2.8, worse), 80 games −0.08 (z −1.0; shot result
  −0.021%, just beyond noise) — longer shooting memory trends better; 40 kept for v1, 120+ to test; free throws 30
  attempts +0.11 (free throw +0.056%, worse), 120 −0.06 (z −0.8, neutral) — 60 kept. Single-node verdicts at ~1× the seed noise appear for
  unrelated changes alike (any input change reshuffles the trees like a new seed) and are not read as effects.
- **Playoff weights — negative result**: ×2 chain +0.29 nats per game (z +3.2), ×0.5 +0.13 (z +1.5); playoff rows count once.
- **Shot distance is the strongest input after zone.** Leaving out distance and lateral offset: blocked +3.85% log
  loss, assisted +1.13%, shot result +1.01%, blocker +0.41%, rebound +0.23%, rebounder +0.12% (every fold, z 3–34);
  chain +3.08 nats per game. Nothing in the 15-decision chain produced a location, so a 16th decision was added (D21).
  FG% falls with distance inside every zone (quintiles, 2023-24 → 2025-26): rim 75.9 → 54.3%, paint 46.2 → 44.3%,
  mid 43.0 → 38.7%, corner 3 38.7 → 36.7%, above-break 3 36.7 → 31.9% (deepest fifth ≥ 27.3 ft).
- **Team turnovers** (shot clock, 8-second; all dead ball) are 5.3% of turnovers (2024-25 + 2025-26) and carry no
  player. The event model counted them as actions, so "who" would have credited them to players (+5–6% player
  turnovers in simulation). Event now has a fourth class, team turnover.
- **All-Star games in the history files.** 2023-24 (1 game) and 2025-26 (3 games, the three-team format) pass
  reconciliation and were in training — about 400 segments (0.03%). Excluded from every dataset (ESPN franchise ids
  1–30 only); found because a smoke check saw rest days of 0.
- **Location (node 16, D21)**: +4.0 / +4.7 / +4.7 / +4.5% log loss over league band shares within the zone (F1–F4),
  ECE 0.006. Event with team turnovers as a fourth class: +16.5–17.9% over its baseline.
- **Banded distance.** Training later nodes on the band's mean distance instead of the exact one costs 0.50 nats per
  game (assisted +0.49%, blocked +0.16%, shot result +0.15%, rebound +0.06%; others neutral) — bands keep ~84% of
  distance's 3.1 nats. v1 trains on bands, since the engine samples a band; finer bands could close the gap.
- **Level recalibration — negative result.** Refitting class intercepts on the latest 10% of the training window:
  neutral on all 10 non-candidate nodes (chain −0.06 nats per game). The latest slice does not predict the next
  season's level better than the whole window.
- **Calibration by period and margin** (control run): in regulation, excess ECE over the perfect-calibration null is
  within 0.003 for nearly every node and bucket, with no period pattern — no per-period temperature is needed. OT
  buckets are small and noisy. The visible problem is a **level bias in every bucket**: "what" ≈ 0.8 points and
  "turnover type" 1.0–1.8 points on one class — drift between the training window and the season that follows.

## 3h′. Model v1 (settings `models/v1.json`; folds log `analysis/experiments/20261119T210324Z_v1_folds.json`)

v1 = no sample-weight decay; profile half-lives role 5 / usage 15 / accuracy 40 / free throws 60 games; location bands
for shot distance (banded inputs); team style for duration, what and shot result; day of season for event and turnover
type; in-game form everywhere except free throws; All-Star games excluded.

| Node | Mean gain v best baseline | Worst fold | Mean ECE |
|---|---|---|---|
| duration | +1.49% | +1.44% | 0.0025 |
| event (4 classes) | +17.45% | +16.61% | 0.0026 |
| who | +2.07% | +2.02% | 0.0019 |
| what | +5.47% | +5.26% | 0.0048 |
| location (new) | +4.48% | +3.96% | 0.0060 |
| shot result | +2.00% | +1.94% | 0.0037 |
| assisted | +25.15% | +24.59% | 0.0040 |
| assister | +2.44% | +2.08% | 0.0059 |
| blocked | +6.26% | +6.00% | 0.0049 |
| blocker | +1.18% | +0.77% | 0.0075 |
| rebound | +7.90% | +7.63% | 0.0065 |
| rebounder | +1.51% | +1.39% | 0.0029 |
| turnover type | +4.79% | +4.59% | 0.0113 |
| stealer | +0.07% | +0.02% | 0.0021 |
| fouler | +1.57% | +1.48% | 0.0020 |
| free throw | +0.14% | +0.03% | 0.0041 |

Against the clean-data control (v1 inputs, exact distance): chain −0.90 nats per game (z −9.3), net of the +0.50 that
bands cost; against an equally banded baseline the tuning is worth ≈ −1.4 nats per game.

**Final test, scored once (2026-27 to 18 Nov; trained on everything before 2026-07-01; log
`analysis/experiments/20261119T212218Z_final_v1.json`, models `data/models/v1/`, 44 MB).** Gain over the best baseline:
event +11.77%, assisted +22.68%, rebound +7.22%, blocked +6.19%, what +4.44%, location +2.94%, assister +2.89%, shot
result +1.70%, blocker +1.69%, rebounder +1.61%, who +1.39%, duration +1.37%, fouler +1.36%, free throw +0.38%,
stealer +0.12% — every node above its baselines. ECE is higher than on the folds (event 0.022, turnover type 0.033,
rebound 0.018, duration 0.014, location 0.011) and the excess is a uniform level shift in every quarter and margin
bucket, not noise — see the adapter skew below. Inference, one step for 10,000 worlds (50,000 candidate rows) on a
busy machine: 721 ms summed over all 16 nodes (assister 109, what 84, fouler 82, location 64, who 61, duration 57).

**Train/serve skew — the live ESPN adapter and the hoopR history differ** (Oct–Nov 2025 history, 294 games, v Oct–Nov
2026 live, 221 games): actions within 2 s of the segment start 8.4% v 2.9% — concentrated after offensive rebounds
(49% v 12% of oreb segments) and defensive rebounds (5.5% v 1.4%), so rebound times are stamped differently; non-shooting
defensive fouls 16.8 v 18.7 per game and shooting fouls 17.3 v 16.3 (the total is equal: the split differs); and-ones
4.9 v 4.5; live-ball share of turnovers 59.4% v 56.6%; offensive fouls 12.4% v 14.1%. Shot coordinates agree (rim
distance 1.94 v 1.83 ft). Models trained on history then see shifted inputs on live data — this explains most of
the final-test calibration gap and must be fixed before the engine runs on live games (M6). **Traced in §3k (M5b):** the
adapters agree; ESPN's 2026-27 feed stamps every rebound at the miss's clock (the timing skew), while the foul and
turnover shifts are real 2026-27 differences.

## 3i. M6a — aggregation test with real rotations (v1 candidate settings; log `analysis/experiments/20261119T204437Z_m6a.json`)

300 random F4 held-out games (Jan–Apr 2026), node models trained through Dec 2025 only, 10,000 worlds per game.
Every real segment keeps its lineups, clock, score and in-game counts; every decision is sampled (teacher forcing per
segment — possessions, minutes and segment counts are real). Baseline = the player's last 20 games per minute × his
real minutes.

| Tier (player-games) | PTS bias | REB | AST | 3PM | STL | BLK | TOV | FTA | PF | 10–90% coverage | CRPS skill v baseline |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Stars ≥ 25% usage (432) | +2.4% | −2.3% | −1.8% | +4.9% | +2.7% | −3.8% | +4.8% | +5.5% | +8.1% | 77–83% | +7.0 to +12.0% (PF +0.9%) |
| Other starters (2,594) | −0.4% | −0.3% | −1.4% | −0.5% | +1.2% | −1.5% | +0.9% | +0.2% | +6.5% | 77–80% | +6.5 to +10.3% (PF +2.7%) |
| Bench (3,434) | −1.8% | −0.8% | −1.7% | −3.1% | +1.1% | +4.4% | +3.1% | +7.6% | +2.5% | 78–82% | +7.3 to +10.8% |

- Team points: simulated 228.5 v actual 229.5 per game (−0.5%); home −0.97, away −0.09; margin −0.89 (SE ≈ 1.0).
  Simulated SD of the total 17.8 v real deviation around the simulation 18.2; margin 17.8 v 17.9; 10–90% coverage
  77–81% — given real possessions, game-level spread is right.
- Gate (bias ≈ 0 by tier, coverage ≈ 80%, CRPS better than recent averages): **met** for points, rebounds, assists,
  threes, steals, blocks. To trace: personal fouls +4.9% overall (2.9% of real shooting fouls have no recorded fouler,
  ≈ 1.3 points of it) and stars slightly hot on free throws, turnovers and threes.
- Speed: ~1.5 s per game for the branch tables and 10,000 worlds on a quiet machine (3.7 s with 10 jobs running).
- **Event accounting** (expected v actual counts in the same 300 games, `…205539Z_m6a.json`): actions −0.5%, FGA −1.1%,
  3PA −1.7%, but every foul runs hot — non-shooting defensive fouls +4.6% (4,754 v 4,545), penalty trips +7.6%,
  and-ones +4.6%, offensive fouls +7.8%, shooting fouls on a two +2.5% (on a three −21%, 162 v 206); violations +16%,
  team turnovers +8.4%. The personal-foul and free-throw biases trace to the event and what nodes.
- **Why: fouls fall through every season.** Non-shooting defensive fouls per game, Oct–Dec → Jan–Feb → Mar–Apr
  (regular season): 2022-23 15.6 → 14.2 → 13.3; 2023-24 15.2 → 14.0 → 13.6; 2024-25 15.4 → 14.1 → 13.7; 2025-26 16.5 →
  14.4 → 15.5. Models trained through December learn the new season's level from its foul-heavy first months. Day of
  season was neutral on log loss (schedule group) but the level shift adds up in box scores. Tested alone on the four
  foul-related nodes: log loss neutral (event −0.027%, others ±0.005%), signed class bias reduced — event defensive
  fouls F4 +2.4 → −0.6 per 1,000 (mean |bias| over folds 2.1 → 1.2), turnover type offensive fouls F4 +4.5 → +1.6,
  what fouled-on-a-two +3.1 → +1.7 (but turnovers +2.6 → +4.1). Kept for event and turnover type (judgement: neutral
  log loss, measured bias fix with a known mechanism).

**Full run, all 766 F4 games, final v1 settings** (`…220658Z_m6a.json`, 16,515 player-games): team total 229.1 v
228.0 (+0.5%), margin −1.0 (home low, ≈ 1 SE), 10–90% coverage 78%, SD 17.9 v 18.8. Player bias, stars / starters /
bench: points +0.9 / +0.4 / +0.4%, rebounds −1.2 / +0.1 / −0.9%, assists +1.3 / −0.8 / −1.1%, threes +3.6 / +1.2 /
+0.3%, turnovers +1.1 / +2.3 / +2.1%, free throws +3.5 / +0.3 / +6.2%, fouls +3.0 / +3.9 / +0.7%; coverage 77–81%
everywhere; CRPS 6–11% better than recent averages (fouls 1–7%). Event accounting: defensive fouls −1.2% (was +4.6%
before day of season), penalty trips +1.8%, and-ones +5.4%, offensive fouls +2.5%, shooting fouls on a two +3.4%, on a
three −24% — the remaining bias sits in what/shot result's foul classes.

## 3j. Engine v1 (`scripts/engine.py`; the default since D22; 19 Nov 2026 slate, 2,000 worlds per game)

The v1 nodes played forward: sampled durations on the game clock, replayed rotations (M3 v0), each world's own score,
team and personal fouls, foul-outs and in-game counts. Golden State–Memphis, per team: 114.0 / 114.4 points, 240.6
team minutes, FGA 91–92, 3PA 42–46, FTA 22, assists 28–29, steals 10–11, blocks 5, turnovers 16–18, rebounds 45–48,
≈105 possessions; total SD 16.7, overtime 2.2%; Q4 scoring lowest, as in real games. Against the league (§2): pace ≈ 3%
high, turnovers, steals and rebounds a few percent high, and the spread too narrow (total SD ≈ 18–19 and OT 5.4% in
real games) — per-world form (M8) and the duration node's possession count are the first suspects. Speed: 25 s per
game at 2,000 worlds on a busy laptop (four games + season in 105 s). Re-simulates bit-for-bit (smoke).

**Clock fixes (same evening).** (1) The duration node predicts time *to the action*; real game time also runs after it
— 243 s per game (8.4%): a missed shot runs 2.44 s to the rebound (median 2.3, p90 4.0), a shooting foul 0.46 s; made
shots, turnovers and other fouls ≈ 0. The engine now draws that gap from the real ones (by zone for misses).
(2) Recorded clocks are mostly whole seconds, so a 2–4 s bin holds 2 and 3 s (mean 2.5): uniform sampling inside bins
added ~0.5 s per segment; seconds are now drawn from the real values in each bin. (3) With ≤ 24 s left (4.5% of real
segments, 4.8 s to the action; trained duration rows have > 24 s), time to the action — or no action before the
buzzer — is drawn from real segments that started with the same whole seconds left (now 3.6%, 5.9 s). The errors
had cancelled: without (1) pace was +3%; with (1) only, −5%. After all three, Golden State–Memphis: 108.5–109 points
per team at ≈ 99 possessions v the teams' real 101.2 / 102.1; shooting on par with the league (2P 53–54%, 3P 35%);
turnovers ≈ +1 per team; Memphis's offence simulated at ≈ 110 per 100 v 117.8 real this season — team-level offensive
quality is under-expressed (candidates: live-adapter skew in this season's profiles, replay rotations, missing
defensive inputs). That is the M9 backtest's question.

## 3k. M5b — adapter and feed parity (19 Nov 2026; `scripts/parity.py`, log `analysis/experiments/20261119T223835Z_parity.json`)

**The adapters agree.** Five 2025-26 games (10 and 14 Nov 2025: NY–MIA, DET–PHI, DAL–LAC, DET–WSH, MIA–CLE) re-fetched
as ESPN summaries today (`data/raw/espn/parity/`) match the hoopR files play for play — same count (544, 473, 615, 589,
615), order, types, text, participants and shot coordinates. Only formatting differs: clocks under a minute (`59.1` v
`0:59.1`, parsed equal), free-throw coordinates (none v (25, 13.75)) and the participants of four technical fouls.
Through `possessions.py` both give identical segments (1,405 segments, zero field differences). ESPN has not revised
2025-26 games since hoopR built them.

**The skew is in ESPN's feed from 2026-27: every rebound carries the clock (and wallclock) of the miss it follows.**
Share of rebounds stamped at the miss's clock, by month: 7–12% in every month from Oct 2022 to Jun 2026 (mean miss →
rebound gap 2.1–2.6 s), then **100%** in Oct and Nov 2026 (22,573 rebounds; one exception). Free-throw rebounds too
(2.3 s → 0). Shots are stamped alike in both seasons — time to the shot after a made basket 16.1 / 16.4 s (made /
missed) live v 15.8 / 16.4 history; after a dead-ball turnover 13.8 / 14.1 v 13.8 / 14.4 — so the ~2.6 s of ball flight
moves into the next segment: time to the action after a defensive rebound 11.7 s live v 8.8 s (Oct–Nov 2025), after an
offensive rebound 5.4 v 2.9 s; offensive-rebound actions within 2 s 22% v 62%. Consequences under the feed's clocks:
`shot_time` (an input to 15 of 16 nodes) is ~2.6 s longer on every live rebound-start segment, and team pace style
(mean time to the action, offensive-rebound starts excluded) reads 12.93 s live v 12.02 s in Oct–Nov 2025 (+7.6%); the
decayed team feature in November is 12.58 v 12.18 s (+3.3%, diluted by last season's carry-over). The engine sees every
2026-27 team slower than it is — a candidate cause of its pace running ≈ 2.5% low (§3j).

**The `miss` convention** (`possessions.py --rebound-clock miss`): every rebound segment starts at the miss's clock in
every season. Games, segments and every reconciliation identity are unchanged in all four history seasons; ≥ 99.995% of
rebounds then start at their miss; on the live season it moves one boundary (2 of 55,210 segments). Oct–Nov 2025 under
it v live: time to the action after a defensive rebound 11.47 v 11.69 s, after an offensive rebound 5.12 v 5.37 s,
offensive-rebound actions within 2 s 26% v 22%, team pace input 12.88 v 12.93 s. Other start types differ by ≤ 0.3 s
either way (made basket 15.47 v 15.63, steal 6.40 v 6.58, dead-ball turnover 13.35 v 13.30, made free throw 14.68 v 14.38).

**Not feed artefacts — real 2026-27 differences** (same labels, recorded the same way; Oct–Nov 2025, 294 games, v
2026-27 to 18 Nov, 221 games): a "Personal Foul" gives free throws outside the penalty 0.15 times per game in both
seasons (labels consistent), but non-shooting defensive fouls rise to 18.7 v 16.8 per game and shooting fouls fall to
20.9 v 22.2 (and-ones 4.5 v 4.9); offensive-foul turnovers 4.1 v 3.6 per game and out-of-bounds bad passes 3.8 v 3.4,
so the live-ball share of turnovers falls to 53.6% v 56.5% (steals are recorded identically: two participants). Held-ball
jump balls all but vanish: 0.06 v 0.86 per game, with no other record in their place and implicit possession changes
unchanged (0.86 v 0.85 per game) — either an unrecorded event or a rule change; 0.35% of segments. These shifts can only
be learned from 2026-27 rows, which a single clock convention makes usable for training.

**What the skew costs v1, measured on the folds (paired cross-data test; logs `…224019Z_v1_cross.json` and
`…224019Z_v1.1_folds.json`).** v1's settings trained on the feed's clocks (as v1 was) and the same settings trained on
the `miss` convention (v1.1), both scored on the same held-out rows in the `miss` convention — what the engine meets on
live data. v1.1 is better on 12 of 16 nodes and worse on none; **chain −34.1 nats per game** (z −67 to −88 on every
fold): duration −3.61%, event −6.07%, assisted −3.26%, location −1.15%, what −1.13%, turnover type −0.69%, who −0.57%,
fouler −0.46%, shot result −0.35%, blocked −0.27%, assister −0.19%, rebound −0.16%; blocker, rebounder, stealer, free
throw neutral. v1's calibration error on these rows reproduces its final-test pattern: duration ECE 0.015–0.017 (v1.1
0.002–0.003; v1's own folds 0.0025, its final test 0.014), event 0.011–0.014 (v1.1 0.002–0.004; final test 0.022). The
final-test miscalibration was the rebound stamp.

**M6a on the same terms** (all 766 F4 games, 10,000 worlds, real lineups and clock in the `miss` convention; logs
`…235141Z_m6a_v1_cross.json` — v1's settings trained on the feed's clocks — and `…235148Z_m6a_v1.1.json`). Bias over all
16,514 player-games, v1 on live-style inputs → v1.1: points −0.3 → +0.6%, rebounds +2.4 → −0.4%, assists +2.5 → −0.6%,
threes +7.4 → +1.0%, steals +9.6 → +0.8%, turnovers +8.0 → +1.5%, free throws −2.0 → +2.7%, fouls −5.7 → +2.6%; CRPS
lower for every stat except blocks (level): points 2.563 → 2.546, rebounds 1.094 → 1.091, assists 0.808 → 0.802; 10–90%
coverage 77–80% for both. Team points CRPS 7.40 / 7.60 → 7.30 / 7.51 (home / away), margin 10.49 → 10.29, total 10.67 →
10.58; total bias −0.6 → +1.4 points. Event accounting: defensive fouls −20.5 → −1.0%, penalty trips −17.2 → +2.3%,
turnovers +8.0 → +1.5%, threes attempted +6.0 → −0.9%. v1.1's remaining biases: team turnovers +9.7%, and-ones +6.9%,
fouled on a three −28%, bench free throws +6.1%, stars' fouls +4.5%. **v1.1 replaced v1 as the engine's models (D23).**

**v1.1 final test, scored once** (2026-27 to 18 Nov; `…235457Z_final_v1.1.json`, models `data/models/v1.1/`): every node
above its baselines (event +18.3%, assisted +25.6%, rebound +7.3%, blocked +6.3%, what +5.7%, location +4.2%, assister
+3.1%, fouler +2.1%, shot result +2.1%, who +1.9%, blocker +1.7%, rebounder +1.6%, duration +1.6%, turnover type
+3.5%, free throw +0.4%, stealer +0.1%). ECE v v1's final test: duration 0.0021 v 0.014, event 0.0085 v 0.022, location
0.0094 v 0.011; still high: turnover type 0.026 (v1 0.033) and rebound 0.017 (v1 0.018) — the real 2026-27 turnover and
foul shifts, which only refits with this season's rows can learn.

**Engine pace is fixed.** The same four games (19 Nov slate), engine v1 → v1.1: possessions per team 97.8 → 102.1
(GS–MEM; the teams' real 101.2 / 102.1), 98.0 → 102.2 (POR–MIL; 102.7 / 102.4), 96.3 → 99.8 (NY–MIN; 97.5 / 103.4), 97.3 →
101.2 (LAC–SA; 101.6 / 100.6); points per team ≈ 108 → ≈ 115 (league 113.7); total SD 16.2–17.2 → 16.9–17.8. The ≈ 2.5%
pace shortfall (§3j) was the rebound stamp in the team pace input. Strong offences are still under-expressed (Memphis ≈
113 per 100 v 117.8 real; was ≈ 110).

## 3l. Size, archetype priors and on-court defence — first ablations (19 Nov 2026; negative results)

Inputs: heights and weights for all 935 profiled players (`scripts/athletes.py`: 508 from retained rosters, 427 from
one ESPN athlete request each, none missing; mean 78.4 in, 67–90; 215 lb, 159–305). Both runs use v1.1's settings and
data and are paired with `…224019Z_v1.1_folds` (identical rows); noise floor from the seed pair.

- **Archetype priors + body** (`features.py --body --archetypes 10`; run `…231756Z_v1.1_arch`): per season, k-means
  (k = 10) on standardised style rates plus height and weight of earlier player-seasons (≥ 1,000 offensive segments);
  each rate shrinks toward the player-game's archetype (nearest centroid to his pre-game profile and size) instead of his
  position group; inputs height, weight, archetype and lineup height/weight means. Archetypes separate by size (74.6–82.9
  in) and usage (0.12–0.27). Chain −0.21 nats per game, mixed across folds (F1 −1.07, F2 +0.33); better only for location
  (−0.18%), worse for who (+0.015%, z +1.9) and what (+0.044%, z +3.2). **By the deciding player's sample size** (decayed
  offensive segments): the low-sample bucket (< 250) gains nothing consistent (who −0.15% z −1.0, what +0.16%, rebounder
  +0.25%); part-time players (250–750) gain on rebounder −0.37% (z −7.7), blocker −0.44%, stealer −0.23% but lose on who
  +0.39% (z +9.5). Not kept: the owner's rule (low-sample buckets gain) is not met.
- **On-court defence** (`features.py --defence`; run `…231756Z_v1.1_def`): opponents' FG% at the rim, in the paint,
  mid-range and from three, turnover rate, rim and three shares while he defends (30-game half-life, strong shrinkage),
  plus lineup means. Spread across player-games is small after shrinkage (rim 67.3% ± 1.5 points, three 36.0% ± 0.7).
  Chain −0.27 nats per game, mixed (F2 +0.83); better for location (−0.25%), worse for event, who, assister, blocker and
  turnover type. Not kept.
- **Lead:** both variants help *location* (shot distance within the zone) on three or four folds — size and defence
  inputs for that node alone are the next test. Location has no seed-noise run yet, so its floor is 0 (lenient).
- `games_eff` (role family, 5-game half-life) caps at ~7.7 and cannot define sample-size buckets; `scripts/buckets.py`
  uses decayed offensive segments.

## 3m. Engine v1.1 v the betting market (19 Nov slate; benchmark only, D8)

DraftKings lines retained in the scoreboard (`data/raw/espn/runs/20261119T235714Z/scoreboard_2026-11-19.json.gz`, four
games); the owner's bet365 check agrees (NYK–MIN total 216.5, NYK −1.5). Four games — a direction, not a measurement.

| Game | Market total | v1.1 | v1 | Placeholder | Market home margin | v1.1 home margin |
|---|---|---|---|---|---|---|
| GS @ MEM | 225.5 | 230.7 | 217.0 | 226.1 | +5.5 | −0.6 |
| POR @ MIL | 230.5 | 238.2 | 221.1 | 229.5 | −11.5 | −4.7 |
| NY @ MIN | 216.5 | 231.2 | 219.6 | 212.6 | −1.5 | −2.7 |
| LAC @ SA | 224.5 | 227.5 | 217.4 | 222.0 | +15.5 | +7.2 |

- **Totals run high:** v1.1 +7.7 points per game above the market (+3.0 to +14.7); v1 was −5.4 below, the placeholder −1.7.
  Like for like (possessions counted as segments): the engine plays 101.3 possessions per team at 1.145 points each on
  these games; real 2026-27 games average 101.05 at 1.125 (113.7 points; §2, §3c) — so **efficiency +1.7%, pace +0.3%**,
  ≈ +4.6 points for an average matchup. The 2026-27 scoring level is not lower than history (1.125 v 1.128 per
  possession, §3e). The rest is matchup: the market prices these four games 3.1 points *below* the league's average total
  (224.3 v 227.4), the engine 4.5 *above* it (231.9) — matchup effects on totals are under-expressed, as on margins.
  M6a (real possessions replayed) showed only +0.6% on totals (+1.4 points) on 2025-26 games, so suspect engine-only
  effects first: free throws and the foul classes (and-ones +6.9%, team turnovers +9.7% in M6a), shot mix, end-of-period
  play, replayed rotations (stars' minutes) — the M9 backtest is the tool to separate them.
- **Spreads are about half the market's:** |0.6|, |4.7|, |2.7|, |7.2| v 5.5, 11.5, 1.5, 15.5 — team quality is
  under-expressed (§3j, Memphis ≈ 113 per 100 v 117.8 real). Market lines also carry injury and rest news; the engine
  reads the same injury report.
- Only today's lines are retained (the collection fetches today's scoreboard); tomorrow's slate has none.
- **Is the market itself biased? No, on this season's games.** The final summaries' `pickcenter` (DraftKings; most likely
  the closing line — no timestamp is kept) against the final scores of all 222 games of 2026-27 to 18 Nov: actual total
  − line −0.64 ± 1.20 points (median −0.5, SD 17.8, 48.2% overs); mean line 228.1 v actual 227.5; actual home margin −
  line −0.42 ± 0.98 (SD 14.5); slope of the actual margin on the line's margin 1.09 (full-sized, if anything slightly
  small). So the engine's high totals and half-sized spreads on 19 Nov are the engine's errors, not the market's. The
  owner's yardstick is real outcomes (D8 note); the market is a strong reference because it tracks them closely.

## 4. Placeholder model `baseline-v0` (19 Nov 2026, superseded by `baseline-v1`)

- Team score SD 11.25 with correlation 0.35 gives margin SD 12.8 and total SD ~19 in simulation.
- Simulated overtime 2.5–2.9% versus 5.4% observed: continuous score draws under-produce ties; end-game
  dynamics belong to the play-by-play engine.
- Retrospective 18 Nov slate: favourite won 8 of 12. This is one retrospective day, not an evaluation.
- Runtime: one game × 10,000 sims ≈ 0.2 s; season (978 games × 10,000) ≈ 0.06 s.
