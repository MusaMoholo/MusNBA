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

## 4. Placeholder model `baseline-v0` (19 Nov 2026, superseded by `baseline-v1`)

- Team score SD 11.25 with correlation 0.35 gives margin SD 12.8 and total SD ~19 in simulation.
- Simulated overtime 2.5–2.9% versus 5.4% observed: continuous score draws under-produce ties; end-game
  dynamics belong to the play-by-play engine.
- Retrospective 18 Nov slate: favourite won 8 of 12. This is one retrospective day, not an evaluation.
- Runtime: one game × 10,000 sims ≈ 0.2 s; season (978 games × 10,000) ≈ 0.06 s.
