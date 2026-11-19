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
the final-test calibration gap and must be fixed before the engine runs on live games (M6).

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

## 4. Placeholder model `baseline-v0` (19 Nov 2026, superseded by `baseline-v1`)

- Team score SD 11.25 with correlation 0.35 gives margin SD 12.8 and total SD ~19 in simulation.
- Simulated overtime 2.5–2.9% versus 5.4% observed: continuous score draws under-produce ties; end-game
  dynamics belong to the play-by-play engine.
- Retrospective 18 Nov slate: favourite won 8 of 12. This is one retrospective day, not an evaluation.
- Runtime: one game × 10,000 sims ≈ 0.2 s; season (978 games × 10,000) ≈ 0.06 s.
