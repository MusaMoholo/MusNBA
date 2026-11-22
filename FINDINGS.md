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
- **Projected-starter sources (probed 20 Nov 2026 from the owner's laptop, robots.txt and one page only):** RotoWire (`/basketball/nba-lineups.php`) and Lineups.com are **blocked by the work network's filter** (OpenDNS block page, HTTP 403); nba.com returns 403 to plain requests (as stats.nba.com). Reachable, with no blanket `Disallow: /` and no rule on lineup pages in robots.txt: Basketball Monster, FantasyPros, DailyFantasyFuel, CBS Sports, numberFire (redirects). Terms of use not yet read; no page content fetched.
- **NBA Stats API (probed 20 Nov 2026, D32 chunk; owner-authorised, D32).** stats.nba.com is reachable from the owner's
  network. Plain requests and requests with only the usual browser headers (User-Agent, Origin, Referer, `x-nba-stats-*`)
  **connect (TLS in 40 ms) and never receive a byte** (timeouts at 25–40 s); adding Chrome's fetch headers (`Sec-Fetch-Site/
  Mode/Dest`, `sec-ch-ua*`) gives 200 in 0.2–0.3 s over IPv4 and IPv6, HTTP/1.1 and HTTP/2, with stdlib urllib. Season logs
  (`playergamelogs`, `teamgamelogs`) take 1–2 s each (4–5 MB JSON); per-game `boxscorematchupsv3` ~0.25 s (140–190 KB JSON,
  14–19 KB gzip); the polite pace (1 s + 0–0.5 s jitter) gives ~0.8 games per second. From 2023-24 the NBA Cup games are
  listed under both `Regular Season` and `IST` (deduplicated); neutral-site games carry "@" on both sides in the logs.
- **Terms of use read (20 Nov 2026, second session):** Basketball Monster (`/TermsOfUse.aspx`): "You may not scrape or otherwise copy our Content without permission … not to use any data mining, data gathering or extraction method" — **forbids**; CBS Sports (Paramount/CBSi terms of use, effective 27 May 2025, §10): bars accessing the services "using any interface other than ours" and unauthorised scraping and data mining — **forbids**; FantasyPros (`/about/legal/`): silent on automated access, but copying allowed only as "a single copy made for personal use" — **unclear, owner decision**; its lineup page showed empty "Projected Lineup" slots when read, status flags only OUT and DTD; DailyFantasyFuel (terms of service, 7 Jun 2026): silent on automated access and copying, but it has **no NBA starting-lineups page** (home page links MLB and NHL lineups only; `/nba/projections/` is a 25-player preview with one "Q" flag; one request each, 20 Nov). **No source passes yet**; the engine opens games with its own projected starters (`minutes.projected_starters`, §3p) and the nightly scores them (`scripts/lineups.py`).

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

## 3o. Engine backtest — the play-by-play engine on past games (20 Nov 2026; M9 first run)

`scripts/backtest.py --config models/v1.1.json --games 200 --worlds 1000 --jobs 4`: 200 random reconciled regular-season F4
games (Jan–Apr 2026); all 16 node models fitted on the fold's training window (through Dec 2025; early stopping on the
held-out window, as in every fold run); each game's pre-game profiles and team style, rotations replayed from the team's
games before the date; **known availability** (the players who actually played). The engine plays its own clock — pace,
minutes and score emerge. Log `analysis/experiments/20261120T100616Z_backtest_v1.1_F4.json` (35 min with the fits).
Compared on the same games with the **team-rating model** — the team engine's game model (ratings before the date as
`team_table`, shrunk K = 8; scores normal, SD 11.25, rho 0.35) — and M6a (real possessions replayed, `…235148Z_m6a_v1.1`).

| Same 200 games | Engine v1.1 | Team-rating model | Paired difference (engine − team) |
|---|---|---|---|
| Total: bias / CRPS | +2.7 / 12.10 | −0.5 / 11.35 | CRPS +0.75 ± 0.29 (z +2.6) |
| Margin: CRPS / corr with real / slope of real on predicted | 9.64 / 0.46 / 1.45 | 9.32 / 0.56 / 1.65 | CRPS +0.32 ± 0.19 (z +1.7) |
| Win: log loss / Brier | 0.592 / 0.203 | 0.558 / 0.188 | +0.034 ± 0.018 (z +1.9) / +0.014 ± 0.008 |

- **The engine does not yet beat a plain team-rating model on game results**, although it knows who played. Worse on every
  game measure, consistently in direction (z 1.7–2.6 on 200 games).
- **Pace is right** (possessions per team +0.2%); **efficiency +0.9%** (114.7 v 113.7 per 100) → totals +2.7 (+1.2%).
- **Defence is the missing piece.** Points per 100 per team-game regressed on the side's offensive rating and the
  opponent's defensive rating (deviations from the league, ratings before the date): real games load **1.14 on offence and
  1.69 on the opponent's defence**; the engine **0.80 and 0.42** — offence at ~70% of its real effect, defence at ~25%.
  The possession models see defenders only through steal, block, foul and rebound rates; shot-making suppression and
  turnovers forced by a good defence barely reach them (the on-court defence profiles of §3l were shrunk to a small spread:
  rim 67.3% ± 1.5 points). This is why margins are half-sized (slope 1.45; market spreads ~2× ours, §3m) and why strong
  teams look ordinary (Memphis, §3j).
- **Stars play too much**: minutes +6.5% (33.4 v 31.3), points +8.8%, assists +7.1%; bench points −4.4%, assists −7.6%;
  starters +0.9% minutes. Replayed rotations (M3 v0) give stars their full-strength minutes in every world; part of the
  total's +1.2% follows (more of the best players on the floor).
- **Too narrow**: total simulated SD 17.0 v real deviation 21.0 (10–90% coverage 65%), margin 14.7 v 17.2 (72.5%),
  minutes coverage 58–63% (target 80%) — per-world form and strength uncertainty (M8) and game-state substitutions (M7).
- Overtime 2.8% v 2.5% on these games (small sample; 5.4% this season). Win calibration: in the 0.2–0.4 bin the home side
  won 17% of 41 games at 33% predicted — favourites are under-rated, as the margin slope says.
- M6a on the same games (real possessions, lineups and clock): total −1.0, margin corr 0.21 — teacher forcing replays each
  game's real state, so its margins are not forecasts; it agrees that the per-possession models carry little team strength.

## 3p. Minutes — healthy roles, 240 by priority, return ramp (20 Nov 2026; D29, `scripts/minutes.py`)

Regulation minutes from the M3 on-court shares, regular season 2022-23 → 2025-26 (105k player-games); allocator targets
v real minutes with **known availability** (the players who played); tuned on Jan–Apr 2025, confirmed on Jan–Apr 2026
(the backtest's season); logs `analysis/experiments/20261120T111337Z_minutes_alloc_F4.json`.

- **Return ramp** (players with a 20+ minute role; minutes in the k-th game back over the role before the absence):
  1 game missed 0.98 / 0.99 / 1.00; 2–3 missed 0.93 / 0.98 / 1.00; 4–6 0.90 / 0.96 / 0.99; 7–12 0.84 / 0.88 / 0.93 / 0.97
  / 1.00; 13–25 0.78 / 0.87 / 0.92 / 0.96 / 0.97; 26+ ≈ 0.7 (small samples). Steady state 1.004 (57,682 player-games).
  Learned per cutoff (`learn_ramp`, relative to the absence-only allocation, shrunk to 1).
- **Absorption** (who takes an absent player's minutes): equal sharing weighted by each player's headroom under his own
  recent maximum (gamma 0, room 1) beat proportional-to-role sharing (gamma 1): Jan–Apr 2025 MAE 4.91 v 5.03, RMSE 6.48 v
  6.62; gamma 2 was worse (5.07). Stars absorb less than proportional — they are already near their maximum.
- **Healthy minutes** with a half-strength absence correction (each game's minutes minus half the allocator's boost for
  that night's absences): MAE 4.91 v 4.99 with the full correction and 5.31 without (raw recent minutes inside the
  allocator: bench −4.4%, starters +4.3% by pre-game tier). Half-lives 3 / 8 and start bonus 0 / 8: neutral.
- **Jan–Apr 2026 (held out)**, by pre-game tier (start share ≥ 0.5; stars usage ≥ 25%): bias stars −1.0% (recent-minutes
  EWMA +1.8%), starters +2.9% (+2.1%), bench −1.9% (−3.8%); MAE 5.03 v 4.98 (level), RMSE 6.60 v 6.55; per-world draws
  10–90% coverage stars 84%, starters 80%, bench 76%. Returning players (25+ min role, 5+ games missed, first game
  back, n = 96): allocated 25.6 v real 22.7 (raw recent average 29.6).
- **Rotation share** (live only): DNP – coach's decision is 80% of DNPs in the 2025-26 hoopR boxes and 91% in ours for
  2026-27; healthy minutes average only games played, so live allocation uses healthy × rotation share (decayed share of
  available games played). Without it a full live roster sums far above 240 and the squeeze zeroed 17–19-minute bench
  players (Philadelphia, 21 Nov).
- **Projected starters** (start share, then priority; ≤ 3 guards, 3 forwards, 2 centres), Jan–Apr 2026 with known
  availability: 89.4% of starter slots right, all five in 53.5% of 1,474 team-games — the bar for a lineup source.
  The snapshots' old rule (recent starts, then minutes; prospective availability), 12–19 Nov: 82.1% / 30.4% (112 team-games).

## 3q. Implicit matchups and shot types (20 Nov 2026; D30, `scripts/matchups.py`)

- **Shot type from the play text**: all 921,103 history shots match a typed play (52 labels → 8 families: drive 30.7%,
  plain jump shot ≈ catch-and-shoot 29.2%, pull-up 13.5%, isolation/post (fade, turnaround, hook) 7.8%, cut/alley-oop 5.7%,
  step-back 5.3%, putback/tip 4.4%, other 3.5%). **Signal, not noise**: at the rim, same distance band, cuts make 89% /
  80%, drives 77% / 63%, putbacks 65% / 58% (1–2 ft / 2–3 ft); above the break catch 36–37% v pull-ups ~1.5 points lower;
  mid-range step-backs and pull-ups slightly above isolation. Knowing the type lowers held-out (2025-26) shot-result log
  loss by **0.61%** beyond zone and band (simple rates) — ~30% of the shot-result node's whole gain over baselines; part of
  it the node already sees (putbacks follow offensive rebounds).
- **Soft assignment** (weighted conditional logit on credited defenders, trained through 2025-12-31, log
  `…_matchup_fit.json`, θ `models/matchup_2025-12-31.json`): credits — fouled on a three 1.0, fouled on a two 0.5, and-ones
  1.0 (jump) / 0.3, blocks 1.0 (jump shot) / 0.25 (rim), steals 0.3. Matchup terms: −0.09 per 3 in of height gap, −0.07 per
  20 lb, +0.11 same position group, +0.05 per 10 min role gap (≈ 0), big on a guard −0.14, guard on a big −0.22; propensity
  terms (not part of the assignment): foul rate +0.25 SD, blocks +0.56 SD, steals +0.23 SD. Held-out (Jan–Apr 2026, 35,216
  credits) log-likelihood per credit: uniform −1.609, propensity only −1.558, + matchup −1.544; on-ball credits (fouls on
  threes, jump-shot blocks): top-1 26% v 20% random. **ESPN credits identify who-guards-whom only weakly** — the
  assignment is soft (the best-matched defender ≈ 30%).
- Consequence: assignment-weighted FG% allowed (decayed 40 games, shrinkage K 40 by zone, 80 for threes) correlates 0.96–0.97
  with plain on-court FG% allowed; lighter on-court shrinkage (×0.2 of §3l) widens the spread across 2025-26 player-games:
  rim 67.6% ± 2.6 points (§3l ± 1.5), three 35.9% ± 1.3 (± 0.7). Shot-type shares vary widely by player (self-created
  24% ± 10%, cut 7% ± 7%, putback 5% ± 6%).

- **Node level (F4 only, paired with v1.1 on identical rows; logs `…114726Z_v1.2d_F4`, `…120349Z_v1.2d_stype_F4`).**
  v1.2d = v1.1 settings + defender-side on-court defence (shrinkage ×0.2), assignment-weighted matchup inputs for the actor
  (mu_fg by zone, turnovers forced, fouls on his men, size gap), help at the rim (best rim protector on the floor) and
  shot-type shares: location −0.35% (z −5.7) and shot result −0.056% (z −2.5; noise 0.017%) better, the other 14 nodes
  neutral, chain −1.18 nats per game (z −6.0) — the first clean node-level gain from defence inputs (§3l's were mixed);
  `mu_fg_shot` is among shot result's four top inputs. **Shot-type upper bound** (the true per-shot type as an input —
  the engine cannot serve it): shot result −0.34% (z −9.9), blocked −1.34% (z −10.5), assisted −17.3% (z −59; partly a
  near-label — alley-oops and cuts are assisted almost by definition), chain −7.4 nats per game. A shot-type node must
  therefore be judged on the joint likelihood of the outcomes it shares (type marginalised) or the backtest, not on these
  conditional gains.

## 3r. Engine backtest with D29 minutes — v1.2 promoted (20 Nov 2026)

Same 200 F4 games, seed and fold models as the control (`…100616Z_backtest_v1.1_F4`); the only change: rotation tables
rescaled to D29 targets (`--rotation targets`; healthy roles, 240 by priority, ramp, per-world draws; starters projected
from start share, not the real ones). Log `…114433Z_backtest_v1.1_minutes_F4`, paired comparison `…_compare_minutes_F4`
(`scripts/backtest_compare.py`, standard errors clustered by game).

| Tier | Minutes bias | Minutes 10–90% | Minutes CRPS (z) | Points bias | Points 10–90% | Points CRPS (z) | Rebounds bias | Assists bias |
|---|---|---|---|---|---|---|---|---|
| Stars | +6.5% → −1.0% | 63% → 84% | −9.8% (−2.2) | +8.8% → +0.5% | 76% → 82% | −1.3% (−0.5) | +3.2% → −4.3% | +7.1% → −0.6% |
| Starters | +0.9% → −2.2% | 58% → 81% | −18.4% (−8.2) | +2.6% → −0.3% | 76% → 78% | −4.2% (−5.0) | +2.0% → −0.8% | +1.1% → −1.7% |
| Bench | −2.6% → +3.3% | 62% → 77% | −8.5% (−4.5) | −4.4% → +3.1% | 71% → 74% | −1.9% (−1.7) | −0.9% → +5.0% | −7.6% → +0.1% |

- Every player CRPS is better or level (rebounds −5.7% for starters, z −5.4; assists −2.8% to −2.9%, z −3 to −4).
- Team sums level: total bias +2.7 → +2.2, total CRPS 12.10 → 12.00 (−0.10 ± 0.07), margin CRPS 9.64 → 9.67 (+0.03 ±
  0.06), margin slope 1.45 → 1.48, defence loading 0.42 → 0.44 (real 1.69), win log loss 0.592 → 0.595. The team-rating
  model still wins every game measure (margin CRPS 9.32) — minutes were not the cause of the half-sized margins.
- New biases to watch: bench rebounds +5.0% and stars −4.3% (rebounding moves with the minutes shift), bench minutes +3.3%.
- **Promoted as engine v1.2** (`models/v1.2.json`: v1.1 node models + D29 minutes; D22's test met on player outcomes,
  team sums not worse).

## 3s. Engine backtest with D30 defence inputs — v1.3 promoted (20 Nov 2026)

Same 200 F4 games, seed and D29 minutes as v1.2; node models v1.2d fitted on the fold's training window (defender-side
on-court defence with shrinkage ×0.2, assignment-weighted matchup inputs, help at the rim, shot-type shares; matchup θ
through 2025-12-31). Log `…120816Z_backtest_v1.2d_minutes_F4`, paired comparison `…_compare_defence_F4`.

| Same 200 games | v1.1 (control) | v1.2 (minutes) | **v1.3 (minutes + defence)** | Team-rating model |
|---|---|---|---|---|
| Defence loading (real 1.69) | 0.42 | 0.44 | **0.69** | — |
| Offence loading (real 1.14) | 0.80 | 0.75 | 0.73 | — |
| Margin CRPS / corr with real | 9.64 / 0.46 | 9.67 / 0.45 | **9.37 / 0.51** | 9.32 / 0.56 |
| Total CRPS / bias | 12.10 / +2.7 | 12.00 / +2.2 | **11.72 / +1.8** | 11.35 / −0.5 |
| Win log loss | 0.592 | 0.595 | **0.571** | 0.558 |

- Paired v v1.2: margin CRPS −0.30 ± 0.08 (z −3.8), total −0.28 ± 0.11 (z −2.7), home points −0.31 ± 0.07.
- Players level or better: bench CRPS better on every stat (assists z −2.0, points −1.7); stars rebounds −1.0% (z −2.2),
  points −0.7% (z −0.9); starters assists −0.7% (z −2.5), points +0.3% (z +1.1, within noise). Biases: stars points
  +1.8% (v1.2 +0.5%), stars and starters assists −2.5%, bench rebounds +5.7%.
- The opponent's defence is now expressed at 41% of its real effect (26% before); the gap to the team-rating model on
  margins is 0.05 CRPS (was 0.35). Offence is still at ~65% of real. Next: real matchup data (NBA Stats, D32).
- **Promoted as engine v1.3** (`models/v1.3.json`: v1.2d settings + D29 minutes); production models trained on everything
  before 2026-07-01, final test scored once (below).
- **v1.3 final test, scored once** (2026-27 to 19 Nov; trained on everything before 2026-07-01; `…120935Z_final_v1.3`,
  models `data/models/v1.3/`): every node above its baselines and level with v1.1's final test (§3k) — event +18.25%,
  assisted +25.69%, rebound +7.30%, blocked +6.14%, what +5.66%, location +4.44% (v1.1 +4.2%), assister +2.97%, shot result
  +2.13%, fouler +2.00%, who +1.93%, blocker +1.84%, rebounder +1.67%, duration +1.57%, turnover type +3.61%, free throw
  +0.37%, stealer +0.18%; ECE ≤ 0.012 except rebound 0.017 and turnover type 0.024 (v1.1 0.017 / 0.026: the real 2026-27
  foul and turnover shifts). The defence inputs' gain is a game-level effect (the backtest), not a node-level one.
- **Engine teammates' points correlations** (live slate, 20 Nov, 2,000 worlds): all small negatives, −0.13 to −0.01 — shot
  competition, but almost no shared upside (pace, a team's hot night). Consistent with totals too narrow (coverage 65–70%):
  per-world form (M8) is missing.

## 3s′. Where the defence is missing — component loadings of engine v1.3 (20 Nov 2026; backtest rerun)

`backtest.py --config models/v1.2d.json --models folds/v1.2d_F4_all --games 200 --worlds 1000 --rotation targets` rerun with
per-side components (log `…133953Z_v1.3_components_F4`): **identical** to the stored v1.3 run on every summary number
(CRPS, means, loadings) — the engine is deterministic. Per team-game rates regressed on the side's offensive and the
opponent's defensive rating (as `strength_loading`), per point of the opponent's defensive rating (points per 100 worse):

| Component | Real games | Engine v1.3 | Engine / real |
|---|---|---|---|
| FG% allowed | +0.62 points | +0.23 | 37% |
| 3P% allowed | +0.22 points | +0.04 | 18% |
| FGA per 100 possessions | +0.28 | +0.13 | 47% |
| FTA per 100 | +0.30 | +0.12 | 40% |
| Turnovers per 100 | −0.165 | −0.156 | **95%** |
| Offensive rebounds per 100 | +0.19 | +0.04 | 20% |
| 3PA share | 0.000 | +0.001 | — |

- **Turnovers forced are fully expressed**; **shot-making allowed is the gap** — FG% carries ≈ 1.3 of the real 1.69 points
  per 100 (0.0062 × 87 FGA × 2.4 points per make) and the engine gives ≈ 0.5; three-point defence is at 18%. Free throws
  (defenders' foul rates, 40%) and defensive rebounding (20%) come next — fouler and rebound nodes, not the matchup inputs.
- Offence side (per point of the side's own offensive rating): FG% real +0.28 points v engine +0.14, OREB +0.15 v +0.05 — the
  offence under-expression (64%) is the same shape.
- Levels: FG% 47.4% real v 47.2%, 3P% 36.2% v 36.3%, FTA per 100 22.3 v 23.6 (+5.6%), OREB per 100 10.8 v 11.1.

## 3t. NBA Stats ingest — crosswalk and reconciliation with our ESPN data (20 Nov 2026; D32, `scripts/nbastats.py`)

Raw retention `data/raw/nbastats/<endpoint>/<season>/` (gzip + manifest; `fetch_nbastats.py`); season logs for 2022-23 →
2026-27 (51 requests), 5,508 games (regular season, Cup, play-in, playoffs; 2026-27 to 19 Nov). Report
`data/derived/nbastats/report.json`, unmatched log `unmatched.json`.

- **Games:** 5,508 of 5,508 matched both ways by ET date and the pair of teams (NBA tricodes NYK, SAS, GSW, NOP, UTA, WAS
  ↔ ESPN NY, SA, GS, NO, UTAH, WSH); no duplicates, none unmatched on either side.
- **Players:** 118,024 of 118,041 NBA player-games matched (99.986%): 118,014 by normalised name (accents, punctuation and
  Jr./II/III stripped), 10 by a unique stat line; 935 people, each with one ESPN id (no conflicts either way). Seconds-long
  appearances (0:01–0:29 in NBA's log) appear in ESPN's box with 0 minutes, so the candidate set keeps every ESPN row of the
  team. The 17 unmatched are all **Lachlan Olbrich (CHI, 2025-26)**, whose ESPN box rows carry no athlete id or name — an
  ESPN-side gap.
- **Box scores agree:** points identical in every player-game where both sides have a value (2022-26: 0 of 112,935
  differ); the 13 2026-27 "differences" are players NBA credits with seconds and 0 points whom our live ESPN box lists as DNP
  (no line). FGA differ 0.012%, rebounds 0.046%, assists 0.016%; box minutes (rounded) never differ by more than 1.
- **Minutes:** our on-court seconds (M3 rotations) v NBA's `MIN_SEC`: median absolute gap 0 s; > 30 s in 0.19% and > 60 s
  in 0.13% of player-games (2022-23 0.33%, 2025-26 0.007%, 2026-27 0.26%); the worst are whole quarters missing in a few
  2022-23 feed-gap games (e.g. 401468786, flagged `game_ok = false` already).
- **Possessions:** NBA `POSS` 100.01 per team-game v our segments' possessions 100.91 (+0.9, +0.9%; reconciled games,
  10,840 team-games), correlation 0.982; |difference| > 2 in 7.3%, > 5 in 0.15%. Our segment count runs one possession high
  on average (end-of-period possessions and our start rules) — a convention difference, not missing play.
- **Matchups (`boxscorematchupsv3`)** — per game, attacker × defender: partial possessions, seconds, the attacker's points,
  FGM/FGA, threes, free throws, turnovers, assists while guarded, help blocks, switches. **All 5,508 games fetched** (4 empty
  responses), 1,043,410 rows in 5,504 games; every person and game maps to an ESPN id. Partial possessions sum to **0.95 × (5 ×
  NBA possessions)** per team-game (p10–p90 0.89–0.99: ~5% of offensive player-possessions have no matched defender); an
  attacker meets 8.9 defenders per game and his main defender covers 36% of his partial possessions.
- **Season quirk:** in **2022-23 and 2023-24** matchups over-count — matched FGA 111–112% of box FGA (above the box in ~48% of
  attacker-games), points 105% — apparently some shots credited to two defenders (mid-possession switches); from **2024-25** they
  are consistent: FGA 97–98% of the box (equal in 77–86% of attacker-games), points 98–99%. The real-share weights are shares
  normalised over the five on court, so the early seasons are blurred, not biased; reliability measures use 2024-25 onward.
- **Coverage of the real weights** (full variant): 1,174,044 of 1,212,535 actor uses (96.8%) weighted by the use's own category
  (made/missed two/three, turnover, shooting foul), 37,452 (3.1%) by partial possessions, 1,039 (0.09%) by the soft fallback.

## 3u. Real matchups — what a defender controls, who guards whom, switch hunting (20 Nov 2026; D32/D35, `scripts/realmatch.py`)

Real NBA matchups (`boxscorematchupsv3`) in ESPN ids; first 3,220 games (2025-26, most of 2024-25) unless stated.

- **Defender traits, split-half reliability** (odd v even games; defenders with enough attempts faced in both halves):

| Trait (per defender, real matchups) | Defenders | Split-half r | Implied shrinkage K |
|---|---|---|---|
| Three-point attempt share allowed v his attackers' normal share (leave-one-out) | 407 (≥ 200 FGA per half) | **0.77** (0.73 at ≥ 100, 0.83 at ≥ 400); SD 4.4 points of share | ≈ 60–100 shots |
| Points allowed per partial possession v attackers' own rate | 466 (≥ 400 per half) | **0.85**; SD 6.2 per 100 (includes team scheme: halves share the season) | — |
| 2P% allowed | 363 (~370 attempts per half) | 0.49 | ≈ 400 attempts |
| FG% allowed | 407 (~600 per half) | 0.30 | ≈ 1,400 |
| **3P% allowed** | 375 (~260 per half) | **−0.05 (noise)** | ∞ — shrink to the prior |

  Defenders do not control whether threes go in; they clearly control **how many threes their man takes** (closeouts,
  run-off-the-line, drop coverage conceding pull-ups, size mismatches: attackers guarded by centres take 2.3 points fewer
  threes than their mix). Engineering decision (applied to the real-matchup variants before any backtest):
  `REAL_MATCHUP_K` = 2P zones 400, threes 3,000, deterrence 100 (the soft D30 variant v1.3 serves keeps its constants).
- **Who guards whom (pre-game assignment on real shares), full data**: trained on 951,824 actor uses through 2025-12-31, held
  out on Jan–Apr 2026 (166,725 uses): top-1 uniform 19.3%, old θ from ESPN credits 36.4%, refit with the same features 39.5%,
  + height/usage ranks in both fives 44.0%, + stopper tendency 45.3%, **+ pair history 50.2%** (cross-entropy 1.609 → 1.508,
  floor 1.331: 36% of the information captured v 15% for the old θ); 70% of attacker–defender pairs had met before (pair
  history over 5,504 games). θ `models/realmatch_2025-12-31.json` (run `…144519Z_realmatch_fit`). First look on 660 games:
  51.2% on Jan 1–22. At the shot (matchup FGA shares, partial data) the main defender is harder to predict: top-1 34% v 48%.
- **Switch hunting (D35)** — in who guards whom, an attacker-usage × defender-weakness term adds nothing on the full data
  (top-1 50.2% either way, cross-entropy 1.5084 → 1.5083) and its sign is slightly **negative** (θ −0.08): before the game, teams
  keep weak defenders off the opponent's high-usage attackers rather than the offence pulling them on (first look, 1,312 games:
  θ 0.005 over possessions, 0.008 at the shot). In *who ends the possession* (full data; each attacker's edge = his shot mix ×
  his likely defenders' FG% allowed v the five's mean, `nodes.mismatch_edges`): the biggest mismatch on the floor ends 22.2% of
  possessions v 19.1% for the smallest, but **within the same usage rank the gap is −0.7 to +0.3 points of share** (2024-26 and
  all seasons alike) — the raw gradient is usage composition. **Negative result: v1.4d not run.** Whatever hunting exists happens
  inside a possession (screens, switches), beyond a pre-game matchup.
- **Top-1 and top-2 likely defenders (owner's idea, 20 Nov)**, held out Jan–Apr 2026 (166,725 uses): the real main defender is
  the predicted top-1 50.2% of the time and in the predicted top-2 **75.0%**; the predicted top-2 hold 57.2% of his real partial
  possessions (any two of five: 40%). The assignment's confidence is informative and well ordered — top-1 right 91% when the
  top probability is ≥ 50% (6% of uses), 70% at 40–50% (16%), 49% at 30–40% (45%), 34% below 30% (32%) → v1.4f gives the
  models the top-1/top-2 defenders' own numbers with their probabilities beside the blend.

## 3v. Rough histograms — sampling noise, the rotation-table pool and game state (20 Nov 2026; 20 Nov snapshot, 2,000 worlds)

- **Points:** for the 22 players projected 18+ points, bar-to-bar wiggle in the 5–95% core is **0.81× multinomial noise**
  around a 5-point moving average (pure noise gives ≈ 0.8 after that smoothing); odd totals 49.3% of worlds (no parity
  artefact). Luka Dončić 42 / 43 / 44 points: 62 / 76 / 61 of 2,000 worlds (SD ≈ ±8 each). The spikes are sampling noise —
  10,000 worlds per game (D31/D36) shrink it by √5.
- **Minutes:** regulation minutes come from the rotation tables, and the engine builds **400 tables per side shared across
  the 2,000 worlds** (`ROTATION['pool']`, ~5 worlds per table) — effectively ~400 distinct minute draws, so the bars are
  lumpier than 2,000 worlds suggest (Dončić: 31: 73, 32: 99, 33: 136, 34: 102, 35: 122; mean 35.6, SD 4.2, left-skewed with
  a soft ceiling at 37–40 and OT to 45+). **One table per world** (`ENGINE['pool'] = 0`, D36; backtest `…162930Z_v1.3_pool_per_world_F4`
  v `…133953Z_v1.3_components_F4`, same 200 games): every player measure level (all |z| < 1.7; stars' minutes CRPS 2.901 → 2.891,
  z −0.57; starters' 3.229 → 3.219, z −0.95; coverage within ±0.01), total CRPS level (+0.00 ± 0.04), margin +0.04 ± 0.03 (noise);
  cost +5% (1,365 s v 1,306 s) → adopted for the dashboard (pure Monte Carlo: more distinct minute draws, same expectations).
- **Minutes do not respond to game state:** Dončić's simulated minutes by final margin — close (≤ 5) 35.4, 6–15 35.6,
  blowout (16+) 35.7, overtime 37.0 (2.2% of worlds). Real stars lose 3–5 minutes in blowouts; the tables are fixed per world
  before tip-off, so blowout benching and foul trouble are missing (M7, target-aware substitutions).

## 3w. Defence on real matchups — engine backtests (20 Nov 2026; D32/D35; negative result, v1.3 stays)

Same 200 F4 games, seed, 1,000 worlds and D29 minutes as v1.3's control (`…120816Z_backtest_v1.2d_minutes_F4`, reproduced
exactly by `…133953Z_v1.3_components_F4`); node models fitted on the fold's training window; matchup θ fitted through
2025-12-31 on real shares (§3u). Logs `…153853Z_v1.4c_F4`, `…153837Z_v1.4e_F4`, `…160608Z_v1.4f_F4`; paired comparisons
`…_compare_v1.4{c,e,f}_F4`.

**Seed clarification (22 Nov):** the same `--seed` selects the same games; the engine's simulation seed at source
`6d156a4` also includes the model version, so the four variants did **not** share identical simulation streams.
Same-game differences retain Monte Carlo noise and are not an event-by-event common-random-number comparison.

| Same 200 games | v1.3 | **v1.4c** real-share defender quality + real-share θ | **v1.4e** + deterrence (attempt shares allowed) | **v1.4f** + top-1/top-2 defenders and confidence | Team model |
|---|---|---|---|---|---|
| Defence loading (real 1.69) | 0.686 | 0.652 | **0.738** | 0.629 | — |
| Offence loading (real 1.14) | 0.732 | 0.762 | 0.774 | 0.754 | — |
| Margin CRPS (paired v v1.3) | 9.374 | 9.384 (+0.01 ± 0.06) | 9.374 (+0.00 ± 0.06) | 9.430 (+0.06 ± 0.06) | 9.322 |
| Total CRPS (paired) | 11.721 | 11.743 (+0.02 ± 0.09) | 11.842 (+0.12 ± 0.09) | 11.820 (+0.10 ± 0.08) | 11.353 |
| Total bias | +1.8 | +2.8 | +2.7 | +2.2 | −0.5 |
| Win log loss | 0.571 | 0.572 | 0.571 | 0.578 | 0.558 |
| Opponent-defence expression: FG% / 3P% / FTA / TOV / OREB | 37 / 18 / 40 / 95 / 20% | 37 / 19 / 32 / 78 / 31% | 41 / **30** / **48** / 90 / 29% | 34 / 12 / 36 / 78 / **35%** | — |
| Players (CRPS v v1.3, z) | — | level; stars' assists better (z −2.3) | level; stars' assists better (−2.1), stars' points +1.5 | **worse**: starters' assists (z +3.1), stars' points (+1.7) | — |

- **None beats v1.3 on D22/D28's test** (players level or worse; margins and totals level or worse). v1.3 stays the engine.
- Each input moves *its own* component — deterrence lifts 3P% defence from 18% to 30% of its real effect and FTA from 40% to
  48%; top-2 defenders lift offensive-rebound expression from 20% to 35% — but others fall back and the team sums cancel. The
  offence is compressed by the same amount (loading 0.73–0.77 v 1.14 real). **Reading:** the engine's under-expression is a
  general compression of team differences through the decision chain (shrunk profiles, smoothed node models, many small
  per-possession effects), not one missing defence input; better defender inputs alone do not lift the game-level signal.
- All real-matchup variants raise the total bias by +0.4 to +1.0 point (+1.8 → +2.2–2.8) — to trace before any reuse.
- Engine speed: the real-share assignment costs ~25% more per game (v1.4f alone 1,617 s v v1.3's 1,306 s, fits included).

## 3n. Team engine — the per-world season pathway, walk-forward (20 Nov 2026; M12 first cut, D25/D26)

`scripts/season_backtest.py`: from 20 Nov, 25 Dec, 1 Feb and 10 Mar of each season 2022-23 → 2025-26 (16 starts × 30
teams = 480 team-starts), ratings from the games before the date (as `team_table`: box possessions, shrunk with K = 8
games), the real remaining regular-season schedule played in 10,000 universes by `scripts/pathway.py`; real final wins
scored against the simulated distribution. Logs `analysis/experiments/20261120T093320Z_season_backtest.json` (variants)
and `…093809Z_season_calibration.json` (36-setting grid with leave-one-season-out selection). History only; the
2026-27 final test is untouched by this season-pathway calibration.

| Variant (start draw × posterior SD, gain × estimator's, memory) | Dispersion (1.0) | 10–90% coverage (80%) | CRPS of final wins | Persistence, sim (real 0.40) |
|---|---|---|---|---|
| Fixed probabilities — the season sim the app used until today | 1.53 | 64.6% | 2.727 | 0.00 |
| Start draw only (1, 0, —) | 1.10 | 79.4% | 2.621 | 0.31 |
| Updates only (0, 1, —) | 1.19 | 76.2% | 2.630 | 0.24 |
| v0: estimator's own response (1, 1, —) | 0.99 | 85.0% | 2.631 | 0.40 |
| **v1, promoted: (0.4, 1, 20 games)** | **1.00** | **84.2%** | **2.611** | 0.36 |

- **The old season sim was far too confident**: fixed per-game probabilities from today's ratings made real final wins
  fall outside the simulated 10–90% interval 35% of the time (dispersion 1.53; 1.63 from 20 Nov). Real strength moves
  during a season, and surprises persist: the correlation of a team's surprise (wins − expected) in the first and second
  halves of the remaining games is **0.40 in real seasons at every start date** (0.39–0.41) — fixed strengths give 0.
- **Per-world ratings fix most of it.** Leave one season out (choose by CRPS on three seasons, score the fourth): the chosen
  setting is (0.4, 1, 20) in 3 of 4 folds; held-out CRPS v fixed −2.5%, −3.5%, −6.0%, −3.8% (every season better), v v0
  −0.7%, −1.5%, +0.9%, −1.0%. CRPS is flat across most calibrated settings (2.61–2.64): the gain from fixed to any
  per-world pathway is the big step; the fine settings matter less.
- **What is still wrong — the shape by date.** v1 by start date: dispersion 0.84 / 1.00 / 1.07 / 1.06 (20 Nov / 25 Dec /
  1 Feb / 10 Mar), coverage 88 / 84 / 79 / 85%, simulated persistence 0.52 / 0.42 / 0.31 / 0.18 against a flat real 0.40.
  Too wide in November, a little narrow late; simulated surprises fade with the date while real ones do not (injuries,
  trades, tanking and rest arrive all season). Candidates: a better start estimate (season-to-date raw ratings ignore last
  season and the schedule — a carry-over prior and opponent adjustment would narrow November honestly) and a gain that does
  not decay with games played (the 20-game memory helps; a per-day drift, as MusSim's, may fit the flat persistence).
- Bias of the mean is zero by construction when pooled (every game has a winner); per-team bias is part of CRPS.
- The NBA Cup final is a regular-season game in hoopR (83 games for the two finalists) but not in the standings; it is
  in both the simulated and the real totals here, so the test is unaffected.

## 4. Placeholder model `baseline-v0` (19 Nov 2026, superseded by `baseline-v1`)

- Team score SD 11.25 with correlation 0.35 gives margin SD 12.8 and total SD ~19 in simulation.
- Simulated overtime 2.5–2.9% versus 5.4% observed: continuous score draws under-produce ties; end-game
  dynamics belong to the play-by-play engine.
- Retrospective 18 Nov slate: favourite won 8 of 12. This is one retrospective day, not an evaluation.
- Runtime: one game × 10,000 sims ≈ 0.2 s; season (978 games × 10,000) ≈ 0.06 s.

## 5. Dashboard completion and portability (22 Nov 2026)

- `analysis/experiments/20261122_dashboard_summary_parity.json`: 10,000 retained season worlds, 965 remaining fixtures,
  13 near-term engine games (21/22 Nov snapshots). Adding bottom-three record counts changes **none** of the existing
  season fields (exact JSON equality after removing the additive field). Bottom-three probabilities sum to **3.0000**.
  No model tuning, RNG changes or final-test scoring. Next-game roster minutes/starters/counts reconcile for **21 teams**.
- The 21 and 22 Nov snapshots carry the **same season forecast as of 21 Nov**. Movers must skip a later-slate copy and
  compare distinct season cutoffs; current comparison is 20 → 21 Nov, **30 teams, nine finals** in the interval. Projection
  changes include inputs and simulation variation; per-game causal attribution is not available from these snapshots.
- UI acceptance: **130/130** full browser cases, then **30/30** additional targeted cases (seed/rating tabs, no-projection
  roster, legacy Season redirect, Lab at all widths/themes). The first sweep's two transient metadata 404s coincided with
  `views.build` replacing the output folder; stable-data reruns passed. Avoid running a screenshot sweep across publication.
- PWA **14/14**: fresh import, logos, Game Centre, service worker, offline Standings/Races/Movers/Leaders/About, nine/six
  leader-card grouping, offline modules, no uncaught exceptions. Mutating only the browser's loaded data to **40 team GP**
  changes the leader qualifier to **28 GP** with honest empty states; **1,234 game worlds / 4,321 seasons** change the guide
  counts/example. No retained files changed. The old PWA test used removed `.odds`; updated to the current bezel + comparison.
- Static export initially failed its module-boundary assertion because earlier Spotlight work omitted `spotlight` from
  both export/SW inventories. Fixed with `season` and `about` also listed. Verified data-free shell at `/MusNBA/`; test bundle
  **1,998 records, 10.6 MB** before the close-out refresh (size/counts are this measured export, not a fixed UI assumption).

- **Final refreshed acceptance:** smoke **102/102**, fault run **80/102** (22 deliberate failures, exit 1), full browser
  **156/156**, then **12/12** phone stacking cases, hosted PWA **15/15**. The final screenshots caught a real CSS cascade
  issue: an earlier mobile `.form-grid` rule was overridden by the later base rule. Put the mobile override at the end;
  browser/PWA checks now assert the chart and fixture strip stack geometrically, rather than relying on overflow alone.
- **iCloud visibility failure, reproduced on the real export:** 10,620,938-byte bundle was present with `st_flags=32832`
  (`UF_HIDDEN` set), while the directory was visible. The one-shot post-rename flag clear was insufficient with the
  dot-prefixed staging name. Manual `chflags nohidden` exposed it; owner confirmed it appeared on the phone. Export now
  uses non-dot staging names and clears the flag on staging and destination. Atomic-byte/hidden-flag regression passes;
  a new real iCloud export remained visible after publication. Final bundle **1,998 records, 10,620,944 bytes**; matching
  visible copies in iCloud, `exports/`, Downloads. Payloads unchanged; export creation time changes the compressed file.
- **Publication (owner authorised public source, 22 Nov):** audited 431 historical blobs for credential patterns and
  data/export paths (none found); Pages publishes only the 24-file static shell from `gh-pages`, final commit `e302d27`.
  Public URL HTTP 200, Pages status built, hosted import/offline tests pass. Data remains local/iCloud.

## 6. Planning audit — current control and historical predictions (22 Nov 2026)

Repository/code audit only; no new model experiment or final-test scoring. Baseline smoke passes **102/102**.

- The serving-setting control is `20261120T162930Z_v1.3_pool_per_world_F4`: **200 F4 games, 1,000 worlds,
  rotation targets, pool 0**. Its saved log gives margin CRPS **9.415**, total CRPS **11.723**, total bias **+1.81**,
  win log loss **0.5738**, total 10–90% coverage **69%**, margin coverage **75.5%**. The earlier shared-pool control's
  9.374 margin CRPS is a different simulation setting; do not mix the two when claiming a gain.
- In that pool-0 control, offence loading is **0.727 v 1.144 real (63.5%)**; defence is **0.678 v 1.685 (40.2%)**.
  Earlier shorthand saying "offence 0.73 / defence 0.69 of real" confused raw regression coefficients with ratios.
  The same log's team benchmark gives margin/total CRPS **9.322 / 11.353**, win log loss **0.5584**.
  These are conditional, historical diagnostics, not current live accuracy claims.
- `scripts/backtest.py` explicitly uses **known availability: players who actually played**, even when
  `--known-starters` is absent. That flag separately supplies actual starters. This is useful for isolating engine
  quality but does not measure forecasting who plays. The next chunk must report conditional-engine and genuine
  pre-game-availability populations separately.
- `scripts/train.py::run_node` uses the latest 10% of the **training** window for early stopping and temperatures;
  the later fold validation window is scored separately. Earlier wording in §3o saying "early stopping on the
  held-out window" means that training-tail slice, not F4's scored games.
- `scripts/nightly.py::project_slate` deliberately restricts the possession engine to prospective slates because
  its normal inputs read latest profiles. Existing `--backfill-days` reconstructs **placeholder** snapshots.
  It is not yet an engine-as-of-date runner; changing a date argument alone would not make it safe.
- MusSim reference checked locally: `../Football/scripts/nightly.py::backfill_plan` preserves stored dates/cutoffs,
  validates their ordering and builds a plan without publication; its handoff distinguishes reconstruction from
  actual prospective publication. MusNBA must retain that distinction and use its own strict **games before ET D**
  convention, rather than copy football's inclusive date convention. No Football files or jobs were changed.
- At the planning checkpoint dashboard U1–U22 remained complete and A1 was **0% implemented**. D37 rejects specific
  defence variants; it does not establish that defence gains are impossible. No new gain is claimed here.

## 7. A1 S01 baseline audit — complete (22 Nov 2026)

No candidate has been fitted or selected, no final-test outcome scored, and serving v1.3/pathway v1 and the PWA
bundle are unchanged. The fixed pool-0 panel uses actual participants and projected, not actual, starters.

- **S02 preparation, downloader integrity:** a network-free mock of three cached games in one season constructed the
  NBA `Store` three times, not once (`fetch_games` evaluates `Store(...)` before `setdefault`). Each construction
  scans and may flush the manifest. In isolated temporary storage, a second store constructed before the owning
  store flushes actually writes a reconstructed entry with null URL/time; the owning store restores them on flush.
  An interruption can therefore preserve the missing provenance, but the cause of the existing gaps is unproven.
  A read-only inventory finds **45** retained play-by-play manifest entries without URL/fetch time
  (**23** in 2024–25 and **22** in 2025–26); no files are unindexed or referenced files missing in those folders.
  At ET 21 Nov, retained/eligible counts were **0/1,320** (2022–23), **0/1,319** (2023–24),
  **573/1,321** (2024–25), **1,322/1,322** (2025–26) and **0/235** (2026–27): **1,895/5,517** total.
  The 22 Nov manifest/file inventory found season-log counts **12/12/12/12/6**, matchup counts
  **1,320/1,319/1,321/1,322/235** and tracking-defence counts **636/624/642/636/90** in those same five seasons;
  across these endpoints and PBP, all **10,094** retained gzip entries match their manifest bytes and SHA-256:
  no retained gzip was unindexed, corrupt or hash-mismatched, and no manifest referenced a missing gzip.
  Missing timestamps cannot be reconstructed as fact.
  A separate temporary-store test interrupted `fetch_logs` after one successful request: its manifest was not flushed,
  and resume reconstructed that retained file with null URL/time. The exception surfaced normally. The season-log path
  needed a `finally` flush; this reproduction does not establish the cause of any existing metadata gap.
- **S02 downloader fix:** all three per-season fetchers now construct one owning `Store` per season, and season logs
  flush in `finally` while propagating request/parse exceptions. Network-free regression tests reproduced the three
  excess-constructor failures and missing manifest before the fix; afterwards these, exception propagation and a
  resumed game batch preserving URL/time/hash pass within **19** focused A1 tests. The authorised single PBP stream
  was resumed from the 3,622-game pre-batch queue; running progress is recorded in HANDOFF.
- **S02 crosswalk correction:** the retained `player_games_map.parquet` contains **five** stat-line "matches" with
  null ESPN player IDs, all 2025–26 Lachlan Olbrich box placeholders. These are not valid identity mappings; pandas
  can also match null join keys to one another. A synthetic regression failed before the fix. In a separate temporary
  rebuild of all **5,518** mapped games, excluding missing/non-numeric ESPN IDs yielded **118,220/118,242**
  matched NBA player-games and **22** unmatched, all Olbrich, versus the previous **118,225** including five null
  matches. The 935-person global map and game mapping remain unchanged. This corrects §3t's historical match count
  for that later snapshot; the source gap is not repaired by inventing identities. Raw/served data were not replaced.
  Evidence: `analysis/experiments/20261122_a1_crosswalk_temporary.json`.
- **S02 per-season reconciliation** (`analysis/experiments/20261122_a1_reconciliation.json`, NBA logged games
  strictly before ET 21 Nov): all **118,187** mapped player-point pairs where both boxes have values agree; **13**
  lack an ESPN value. The five invalid mapping rows are explicitly quarantined; **22** NBA appearances have no usable
  mapping. Across 2022–23→2026–27, mapped NBA-positive appearances rounded to zero ESPN minutes number
  **100/125/107/103/3**; a further **13** current-season NBA-positive appearances are marked ESPN DNP with no values.
  Missing outcomes cannot be treated as zero. For NBA-logged games in the five seasons, parser-flagged game counts are
  **22/26/15/22/2**, and **one** further 2025–26 game lacks segments; the JSON enumerates every excluded game.
  On **10,858** usable team-games, per-season mean segment-minus-NBA possessions are **+0.870/+0.833/+0.889/+1.011/
  +0.803**; these reflect the documented convention, not a claim of exact identity. Seconds and remaining comparison
  denominators are retained by season in the report.
- **S02 rotation and matchup integrity** (`analysis/experiments/20261122_a1_rotation_integrity.json`): in the
  2022–23→2026–27 retained ESPN populations, **231,291/228,567/232,904/236,901/43,564** recorded clock-grouped windows
  include **193,221/191,065/194,259/195,593/35,692** with no substitution and
  **18,869/19,061/20,086/21,817/4,211** with multiple substitutions at that clock. Window counts agree with the
  recorded substitutions in every season, with no orphan windows; **12/2/4/2/2** substitution rows repeat an entering
  player at the same team/clock and require investigation before training. **3,102/3,183/3,473/3,708/747** windows
  have substitutions but an unclassified stoppage; these are unknown, not proven illegal. Recorded windows are not
  necessarily every legal opportunity. Summed matchup FGA / NBA box FGA by season is
  **1.1163/1.1120/0.9707/0.9767/0.9800**; there are no duplicate attacker–defender *row keys*, so the early
  over-count is not explained by identical pair rows. One 2025–26 attacker-game has zero box FGA but positive summed
  matchup FGA. The causes of those over-counts are not established by this accounting.
- **S02 segment-start lineups** (`analysis/experiments/20261122_a1_lineup_integrity.json`): in the five retained
  reconciled seasons, **3,054/289,732; 3,192/286,629; 3,438/292,428; 3,611/294,626; 940/53,022** known actors
  are absent from their segment-start offensive lineup (**14,235/1,216,437** overall). These are not necessarily
  absent from the actual court. In `401809247`, Q2 8:55–8:39, Jalen Johnson entered at 8:54 after the segment
  opened and attempted the shot at 8:39; the old segment still records the player he replaced. Segment-credited
  versus independently reconstructed rotation seconds have median absolute differences **12/12/13/13/15 seconds**
  by season; these discrepancies are not uniquely attributable to substitutions.
- **S02 isolated lineup candidate:** split action-free segments at substitutions without adding possessions; same-clock
  substitutions are applied in source order. Candidate-only `lineup_valid`/`lineup_issues` retain but quarantine
  unresolved segments in player-feature and node-dataset construction. On the fixed **200 F4** games, replay of the
  unmodified parser exactly matches retained segments and the candidate preserves all event identities, points and
  possession IDs. Actor absence decreases **489/45,111→6/45,111**, assister absence **139→0**, blocker absence
  **22→1**, stealer absence **32→1**, fouler absence **106→5**; median absolute segment-v-rotation seconds fall
  **13→0** across 4,347/4,349 player-games. **70** candidate segments are quarantined, including **57** where a
  rebounder is absent from the earlier action lineup; in `401810338` Q3 2:27 a defensive substitute enters after an
  and-one shot and rebounds the missed free throw, so treating the shot-time lineup as the rebound lineup is unsafe.
  Prefix segments retain time accounting but do not double-count player exposure. Synthetic tests cover simultaneous
  subs, a pending free-throw trip, missing actor quarantine and protection against writing production segments.
  Independent feature/node accounting on the same 200 games (`analysis/experiments/20261122_a1_split_feature_nodes_200.json`)
  checks five per-player count columns across **4,349 player-games**, plus **47,775** event labels, **44,863**
  five-player shooter-choice groups and **35,397** shot-result labels; all agree, with the **70** bad segments
  quarantined. Earlier parser evidence: `analysis/experiments/20261122_a1_subsplit_quarantine_f4_200.json`.
  This is not a model-accuracy test; no candidate has been promoted, and substitutions after an action are not
  reconstructed as new action lineups.
- **S02 causal-prior candidate:** a separately hashed, history-only base build uses first-season position and team
  priors from dates strictly before each row, earlier-season priors thereafter, and same-day-safe player/team decays
  and rest. An empty prior remains missing until actual earlier evidence exists; when a prior is unavailable but the
  player's/team's own earlier exposure exists, the measured unshrunk rate is used. It covers **111,075 player-games,
  5,196 games, 10,392 team-games**, 18 Oct 2022–13 Jun 2026; no final-test games are included. On 83,797 later-season
  player rows, **38** common player and **14** team columns have zero changes from retained base profiles; first-season
  prior-dependent values change, and all **45** first-day player usage priors remain missing. Synthetic injected
  same-day/future outcomes do not alter earlier profiles. Independent accounting and hashes:
  `analysis/experiments/20261122_a1_causal_base_accounting.json`. This establishes only the stated prior/date scope:
  assignment parameters, static body provenance, reports and all downstream model inputs still need dated-fit checks.
- **S02 sampled feature parity and batch leakage:** in three fixed F4 games, **10/689** actor segments cannot be
  compared as an identical engine actor/lineup state because the actor is not in the recorded starting five. On the
  other **679** states, all **4,753** shared matchup-column values agree within 1e-6 absolute/relative tolerance
  (`analysis/experiments/20261122_a1_matchup_parity_after.json`). This is not full model-feature parity or proof of
  historical parameter availability. The candidate `missing_policy=retain_missing` preserves an all-missing defender
  metric as missing and makes it invariant to unrelated batch values, including top-two features; a synthetic test
  reproduced the previous dependence. The default v1.3 batch policy remains unchanged pending paired evaluation.
- **S02 assignment holdout preprocessing:** `matchups.design` previously recalculated missing-value medians and
  propensity standardisation independently on the whole held-out batch. A synthetic same-population test shows that
  changing an unrelated held-out game's player rates could change another held-out event's design. The fit now
  passes its training-only preprocessing to the held-out design, and the injection test passes. Fitting inputs and the
  accepted serving assignment have not been replaced. On the same **195,228** training and **35,216** held-out F4
  credited events, an isolated fit using the causal base yielded full weighted held-out log likelihood
  **−1.54375→−1.54347** with training-only preprocessing; on-ball top-1 stayed **25.92%** on 2,608 credits.
  **176,476** held-out design values changed. This measures a preprocessing/reporting correction, not an engine
  accuracy gain. Static body timing remains unproven, and the candidate is only valid from 1 Jan 2026. Evidence:
  `analysis/experiments/20261122_a1_assignment_f4_preprocessing.json`.
- **S02 four dated assignment diagnostics:** on F1/F2/F3, respectively, **78,311 / 135,404 / 172,166** training
  and **33,476 / 34,586 / 23,062** held-out usable credits give old versus training-only-preprocessed weighted log
  likelihood **−1.538308→−1.538506 / −1.535604→−1.535767 / −1.541928→−1.541655**. Fits are dated through their
  own training cutoffs and are not available for older rows. Each result is conditional on the retained game lineups;
  it does not measure pre-game availability or a full engine. Reports:
  `analysis/experiments/20261122_a1_assignment_f{1,2,3}_preprocessing.json`.
- **S02 unverified body provenance:** `athletes.py` takes the latest retained roster or a later athlete endpoint;
  the current registry does not establish historical publication dates, and historical hoopR player-box parquets have
  position but no height/weight columns. An isolated F4 fit that excludes height and weight from both training and
  inference gives weighted holdout log likelihood **−1.546114**, versus **−1.543475** including body, and on-ball
  top-1 **24.88% versus 25.92%** on the same **2,608** on-ball credits (35,216 total). Its height-gap feature remains
  missing, not a recorded zero; later-body injection leaves its assignment unchanged. Report:
  `analysis/experiments/20261122_a1_assignment_f4_bodyfree.json`. This does not establish position as-of provenance,
  solve historical fitted-parameter leakage, or justify promotion.
- **S02 dated position and assignment candidate:** among **111,075** historical player-games there are no
  conflicting same-player/same-day recognised position groups; 14 original rows have unknown/unrecognised position.
  Deriving the group from strictly earlier player-game records leaves **891** rows unknown, including the first
  observation for all **877** players. Later current-game positions cannot change the prior-date value in the
  synthetic injection test. Historical source publication/correction times remain unverified. Thirty body-free
  monthly assignment fits are frozen into four fold schedules, with no fit used before its `valid_from` date or
  after a fold's training cutoff (`analysis/experiments/20261122_a1_assignment_monthly_schedule_v2.json`).
  Candidate relative-player features use only the five-player lineup's known values and shared tie-symmetric ranks;
  all-missing five-player inputs stay missing. On the first three pinned games in each of F1–F4, **304,175/304,175**
  matchup, lineup and relative-input comparisons match engine calculations at combined 1e-6 absolute/relative
  tolerance; **36** actor/lineup mismatches were excluded. Reports:
  `analysis/experiments/20261122_a1_scheduled_F{1,2,3,4}_parity_v3.json`. This sampled audit is not full-feature
  parity, an engine-accuracy result or proof of original publication timing. The F4 full node chain built all
  **16** datasets in **59 s**, totalling **17,814,437** rows in a **9.1 GiB** isolated cache; accounting checks
  labels, dates, matrix/group dimensions, one chosen player per candidate group and source hashes. An isolated F4
  run fitted all **16** candidate nodes and simulated **3 games × 20 worlds** in **325 s**. Its independent accounting
  reconciles **24** quarter scores, **63** player 3PM outcomes and **6** team sums with no mismatches; it fingerprints
  the model and inputs (`analysis/experiments/20261122_a1_s02_wiring_accounting.json`). This is wiring validation,
  not accuracy evidence; original publication timing remains unverified.
- **S02 real-slice future injection:** on five retained 2022–23 games, a scratch rebuild changed **372** shot outcomes
  and **43** player-minute/position records in a different same-day game and a later game. All **3,098** checked
  earlier player/team feature values remained bit-identical; separate shot and minute/position injections changed
  **42** and **47** later numeric values respectively. The audit explicitly supplies both scratch source files:
  the initial trial used the real on-court source and was not a valid test of minute/position injection.
  `analysis/experiments/20261122_a1_future_injection_real_slice.json` pins the sample and source hashes. This checks
  base player/team profiles, not original publication times or fitted nodes.
- **S02 diagnostic-baseline leakage:** the `what` profile baseline filled missing held-out inputs using means of all
  held-out rows. Thus changing a different validation game's profiles could change a given missing-profile prediction.
  It now uses training-window means and rejects invalid or entirely missing training columns; a synthetic holdout
  injection changes another game's probability by **0.1759** before the fix and **0** after it. This baseline is
  diagnostic, not a feature supplied to the fitted or accepted engine. Fold-model cache keys include the training-code
  hash so previously saved
  baseline metrics cannot be silently reused after training-code changes.
- **S02 schedule corruption:** the old `matchups.dated_masks` accepted five synthetic corruptions: a fitted
  `through: "NaT"`, non-finite match/propensity/fill values, and a missing fitted fill. The candidate-only guard now
  rejects all five, requires valid ISO dates and complete finite fitted parameters, and its three focused
  schedule/serving tests pass. The 30 monthly fits, four schedules and four dependent feature snapshots were rebuilt
  against the guarded source; sampled F1–F4 parity again matched **304,175/304,175** comparisons, and independently
  accounted F4 nodes contain **17,814,437** rows across all 16 datasets. The independent real-slice injection
  (`analysis/experiments/20261122_a1_future_injection_guarded.json`) still preserves **3,098** earlier values and
  changes **42 / 47** later shot/player values. Matched-seed F4 wiring completed in **324 s** on three games × 20
  worlds; independent accounting reconciled **24** quarter scores, **63** player 3PM outcomes and **6** team sums.
  All **3 × 92** game fields and **63 × 20** player fields reproduced the pre-guard run to `1e-12`
  (`analysis/experiments/20261122_a1_s02_wiring_accounting_guarded.json`). Neither run is an accuracy test.
  Earlier reports describe the old source retained at checkpoint `6ec31d6`, not the guarded build.
- **S02 guarded-build equivalence:** the F4 guarded and pre-guard candidate `pregame.parquet` tables are exactly equal
  for all **111,075** player-games; `team_pregame.parquet` is exactly equal for all **10,392** team-games
  (`pandas.DataFrame.equals` on the two isolated outputs). This verifies valid feature values, not model accuracy.
- **S02 completed history retrieval** (`analysis/experiments/20261122_a1_raw_inventory_completed.json`): all
  **3,622** originally queued PBP responses were retained with no empty responses. Independent inventory matches
  **1,320 / 1,319 / 1,321 / 1,322 / 235** of the eligible logged games in 2022–23 through 2026–27 respectively,
  with **zero** missing, unindexed, corrupt or hash/size-mismatched NBA endpoint files. **45** older entries lack
  original fetch URL/time; absence of those timestamps remains unknown provenance, not a reconstruction.
- **S02 state-before-substitution caveat:** the repeated entrant rows are not necessarily duplicates. In ESPN game
  `401810498`, Q4 0:33.3, the same player enters for the same teammate twice with a reversal and other events between.
  The raw scoreboard before the first of those substitutions (sequence 709) is home **107–110**, but the derived
  clock-grouped window gives it home margin **−4**, after a later free throw at sequence 727 made it 107–111. The
  current `rotations.walk` groups events by clock and assigns its end-of-group margin to every sub, so this is not a
  safe pre-substitution label. Rebuild sequence-aware opportunities and validate state before using them in S06;
  do not drop repeats merely as duplicates. Case: `analysis/experiments/20261122_a1_same_clock_case.json`.
- **S02 tracking-defence coverage** (`analysis/experiments/20261122_a1_tracking_coverage.json`): for NBA logged
  dates before ET 21 Nov, the three categories each cover **212/212, 208/208, 214/214, 212/212 and 30/31** dates
  in 2022–23→2026–27; the missing current date is 20 Nov. The **113,089** Overall rows all join to a player in that
  day's NBA log and the retained global identity map, with GP=1; response hashes, category/date parameters and
  category-specific column schemas were verified. But **8,637/113,089 (7.64%)** `PLAYER_LAST_TEAM_ABBREVIATION`
  values disagree with that day's NBA log (e.g. Jonathan Kuminga's 21 Oct 2025 tracking row says ATL, while his
  game log says GSW). Never use that tracking field as the historic team: join by person and game date to the dated
  game log, reject ambiguous day/team matches, and use only dates strictly before the prediction origin. Overall,
  under-six-foot and three-point responses use **D_FGM/D_FGA**, **FGM_LT_06/FGA_LT_06** and **FG3M/FG3A**
  respectively. A fetch timestamp is collection time, not proof of when that historical data or any later correction
  was published. Global identity coverage is an audit fact, not proof that the mapping existed at a historical origin.
- **S02 preparation, ESPN raw inventory:** all eight retained 2022–23 through 2025–26 hoopR parquet files match
  their manifest byte counts and SHA-256 values. Their play-by-play unique-game counts are **1,321 / 1,320 / 1,324 /
  1,325**; player boxes cover **1,321 / 1,320 / 1,324 / 1,326**. The sole set difference is box-only game
  `401810469` (25 box rows, Clippers–Bulls, source `game_date` 2026-01-20); the mapped NBA play-by-play file
  `0022500614` is retained. This is a raw-coverage gap, not evidence that the ESPN file existed historically.
  The current ESPN collection has **236** retained 2026–27 final summaries and five collection-run reports; its final
  directory has no per-file acquisition/hash manifest. Full reproducible inventory:
  `analysis/experiments/20261122_a1_raw_inventory.json`.
- **S02 preparation, matchup batching:** `matchups.mu_columns` fills an all-missing five-defender metric from the
  entire batch. In a synthetic two-row test, changing only an unrelated row's defensive FG value from 0.4 to 0.6
  changed the missing row's `mu_fg_rim` from 0.4 to 0.6. Dataset batches can therefore borrow held-out/future values,
  while simulation batching can yield different fills. In the fixed 200 F4 games, none of **45,110** actor segments
  with five recorded defenders had all five `m_fg_*`, `m_tov_rate` or `m_foul_rate` values missing; other populations,
  body measurements and simulation lineups remain to be audited. Preserve accepted production behaviour until a
  cutoff-safe, training/serving-consistent candidate is isolated and tested.
- **Reproduction:** `20261122T015651Z_a1_s01_repro` repeats three outcome-blind selected F4 panel games with 1,000
  worlds, targets and pool 0. All shared game/player output columns match the retained 200-game control to
  absolute tolerance 1e-12 on **3 games / 64 player-games**, including randomized PITs; one worker took **46 s**.
  The full original-stream regeneration `20261122T022323Z_a1_s01_control` then reproduced all **59 game columns and
  16 player columns** on **200 games / 4,346 scored player-games** to 1e-12, taking **1,567 s** with four workers.
  Its output adds 3PM and quarter scores; independent seed `20261122T025114Z_a1_s01_seed2` completed in **1,566 s**.
  The same-game team-rating benchmark and M6a diagnostic summaries also reproduce exactly: team margin/total CRPS
  **9.322 / 11.353**, win log loss **0.5584**; M6a's **−1.0** total bias is teacher-forced diagnostic evidence,
  not a pre-game forecast.
- **Full-control accounting:** against raw period-end scores and boxes, all **1,600** quarter total/margin actuals
  and **4,346** available player 3PM actuals match; **399/400** team 3PM means reconcile to their player outputs.
  In game `401810691`, a player logged in the play-by-play for **179 seconds** is absent from the raw player box:
  the engine simulated **4,347** player-games, but only **4,346** have player output/box truth. The remaining team
  sum is explicitly incomplete, not a model/accounting pass or an invented zero. Exact IDs and independent checks:
  `analysis/experiments/20261122_a1_control_accounting.json`. S02 must audit this crosswalk/coverage class.
- **Independent simulation noise:** the same 200 games / 4,346 scored player-games, 1,000 worlds and unchanged
  fitted control were rerun with stream 1. Its accounting independently matched **1,600** quarter scores, **4,346**
  3PM actuals and **399** complete team 3PM sums, with the same one missing box outcome. For pooled
  MIN / PTS / REB / AST / 3PM CRPS, the preregistered larger-absolute-endpoint noise floors are
  **0.02634 / 0.00919 / 0.00384 / 0.00213 / 0.00158**, respectively. Total/margin CRPS floors are
  **0.09372 / 0.08323**. These are simulation-noise thresholds, not improvements or promotion decisions; paired
  intervals and subgroup counts are in `analysis/experiments/20261122_a1_seed_noise.json`.
- **Quarter truth:** on all **2,677** eligible reconciled F1–F4 regular-season games (731/738/490/718), summed
  player-period points match the final team boxes and each of **21,702** team-period end-score snapshots including OT.
  No period end was missing. The explicit `End Period`/`End Game` scoreboard event is needed: backfilled plays can
  have later sequence numbers despite an earlier clock. In the retained 200-game panel, raw segment-point sums differ
  from final boxes in **56 home and 54 away games**, by at most **2 points**; do not treat segment sums as quarter truth.
  Reproducible report: `analysis/experiments/20261122_a1_quarter_audit.json`.
- **Pre-game tiers:** on the **4,346** actual-participant player-games in that panel, using pre-game usage ≥0.25
  for stars and otherwise pre-game start share ≥0.5 for starters yields **284 star / 1,578 starter / 2,472 bench /
  12 unknown**. It changes **485** legacy labels, including 12 unknowns, because the legacy scorecard uses the
  game's actual starter flag. Exact-match, game-clustered comparisons now preserve the unknowns and reject mismatched
  game/player keys; the control-v-itself 200-game bootstrap gives exactly zero paired intervals on retained metrics.
  An independent recomputation from saved rows agrees with all **75** tier/stat CRPS, bias and coverage values; every
  supported self-comparison interval is exactly zero.
  The regenerated pooled **MIN / PTS / REB / AST / 3PM CRPS** are **3.5662 / 3.1614 / 1.3033 / 0.9006 / 0.5889**;
  randomized 10–90% coverage is **78.00 / 75.70 / 76.12 / 76.92 / 77.66%**. The previously unavailable 3PM CRPS is
  **0.8324 / 0.6790 / 0.5045** for star / starter / bench. Unknown has only 12 observations and is inconclusive.
- **Cutoff limits:** the F4 assignment θ fitted through 2025-12-31 is safe for its F4 validation window, but not for
  F1–F3; those folds need dated assignment fits **and** rebuilt matchup features. First-retained-season fallback
  priors use the whole season, affecting **27,278** first-season feature rows across **1,298** games (2022-10-18 to
  2023-06-12), so early training rows need correction; non-fold profile medians read the entire
  feature file; static body measurements have no demonstrated historical as-of provenance. No promotion or historical
  reconstruction can rely on these as already cutoff-safe.
  The retained matchup feature file has **0** player/date keys with multiple games among **116,302** player rows and
  **0** team/date keys with multiple games among **10,858** team rows. This describes the current data, not a general
  guarantee that the sequential feature builders reject same-day multi-game inputs.
- **Availability scope:** the five retained ESPN roster/injury collection origins are dated 19–21 Nov 2026, inside
  the protected final season. Requiring collection completion before scheduled tip plus the injury file and both
  roster files covers **4/4, 9/9 and 5/6** games on those dates; file presence does not establish player-level
  completeness (`analysis/experiments/20261122_a1_report_coverage.json`). No results were scored. Their existence is
  not permission to tune on those outcomes. TRAINING_PLAN
  §8.2 defines a separate, strictly prior-game inferred-membership diagnostic and requires coverage of unseen
  arrivals and stale memberships; it is not an official historical roster or a validated pre-game injury report.
- **Prior-box availability cohort, F4 screen:** on the 200 fixed games, constructing membership before the date from
  same-season prior boxes yields **7,305** candidate player-games: **4,310** positive-minute and **891** DNP labels,
  **2,095** unlisted candidates and **9** listed with zero/missing minutes (unknown). **32** positive-minute
  player-games in **24** games, plus **12** listed DNPs, are outside that inferred universe. Seven candidates have a
  conflicting later same-day team listing; no origin has an ambiguous latest prior team. All 7,305 source dates are
  strictly earlier. This is coverage, not a scored availability model, and the play-by-play-only player above is not
  counted as a known outcome. Retained prior boxes lack historical publication/correction timestamps, so date order
  alone does not prove the exact records were available then. An independent latest-prior-team reconstruction matches all **200** candidate sets;
  saved rows, report and coverage totals reproduce. `analysis/experiments/20261122_a1_prior_box_coverage.json` records
  per-game counts.
- **Correction discovered during S05:** the 2025–26 raw box file marks **73 rows in four All-Star games** as
  `season_type=2`, with three non-NBA team IDs. The original prior-box cohort above therefore displaced some players'
  latest NBA team. Keep that original report for audit, but use the separately rebuilt NBA-team-only cohort
  `analysis/experiments/20261122_a1_prior_box_coverage_nba_only.json`: **7,317** candidates, **4,316** known plays,
  **892** DNPs, **2,100** unlisted and **9** listed-unknown; **26** played outside the inferred universe in **22**
  games. The new cohort contains all 7,305 original keys plus **12** restored keys (six played, one DNP, five
  unlisted). The canonical 30-team filter is tested; it does not change the S01 conditional engine panel.
- **S05 pre-origin population audit:** on those 200 games, the 7,317 candidates comprise **4,316** plays, **675**
  explicit DNP-coach, **217** other DNP and **2,109** unknown. The last-five-appearance proxy (at least three prior
  appearances; not D29 healthy role) identifies **1,412** fringe (<10 minutes), **2,481** core (≥25), **257**
  players with a recorded team change within 30 days, and **29** first appearances after ≥5 team games missed in
  **24** games. The return sample is below S01's reporting gate. **89** team-games have a recorded core DNP; **253**
  have at least one core candidate with unknown status, so do not equate unlisted with absent. Team and appearance
  joins have **zero** same-day/future rows, but past box publication times and true availability remain unknown.
  `analysis/experiments/20261122_a1_s05_minutes_population.json` retains the counts and source fingerprints; the
  outcome-based core-absence grouping is post-game diagnostic only.
- **D29 input contamination:** the `season_type=2` on-court inputs read by `minutes.player_games` also contain
  non-NBA teams: **23 / 24 / 45 / 63** player-game rows in **1 / 1 / 3 / 4** All-Star games in seasons 2023–26.
  None of these games is in the fixed 200-game F4 panel, but D29's sequential states currently ingest them before
  subsequent real games. Any effect on minutes, ramps or accuracy remains to be measured; production v1.3 has not
  changed. A filtered candidate must be compared against the unmodified control with matched inputs and gates.
  The input also has one contradictory coach-DNP/on-court record: player `2999409` in game `401468760` has
  **119 seconds** and a coach-DNP label. D29 applies both updates; the diagnostic reproduces and flags that fact
  rather than silently selecting one source.
- **D29 rotation/share trace:** an independent chronological replay exactly reproduces the final D29 rotation
  shares for **892** players, including the one contradictory pair; source hashes match
  `analysis/experiments/20261122_a1_s05_minutes_diagnostic.json`. On the 200-game prior-box cohort, the **4,991**
  known plays or explicit coach-DNPs have mean predicted share **0.8596**, actual play rate **0.8648**, Brier
  **0.0832**. The <10 recent-minute fringe has **836** known labels in 191 games, share **0.5578** vs play
  **0.5622**, Brier **0.2434**; other DNPs and unknowns are excluded, so these are conditional diagnostics,
  not end-to-end availability calibration. Among ≥15-minute recent roles with rotation share <0.5 there are only
  **34** known labels in 29 games, below the reporting gate.
- **Richardson-like squeeze and overlapping evidence:** with the actual participants supplied as an oracle, applying
  the live rotation-share weighting to D29's regulation allocator produced targets <5 minutes for **105** players
  with ≥15 healthy-role minutes in **63** games. **83** were already below 5 without the weighting; **22** became
  <5 after it (21 games; mean healthy **18.51**, known-play target **15.82**, weighted target **1.05**, real
  regulation **8.42**). Both allocations independently sum to 240 in all **400** team-games; this counterfactual is
  not a prospective forecast. The engine draws physical-status availability once; rotation share also weights the
  target and priority, not a literal second identical Bernoulli draw. Of **1,672** inferred candidates with no known
  play in at least three recent team games, **255** have a coach-DNP among the last five and could also trigger the
  separate recent-nonappearance availability fallback if status were Active; **176** of those have at least one
  unknown prior listing. Historical pre-tip status is unavailable, so overlapping evidence is a risk, not proof of
  how often production double-counted. The regulation-only report is
  `analysis/experiments/20261122_a1_s05_rotation_diagnostic_reg.json`; the earlier mixed-total-minutes report is
  retained and explicitly marked superseded.
- **S05 fixed-panel D29 baseline:** among the **4,346** actual participants in 200 games, total-minute CRPS /
  bias / 10–90% coverage are **2.891 / −0.271 / 82.0%** for stars (284 player-games), **3.024 / +0.669 / 82.4%**
  for starters (1,578), and **3.980 / −0.355 / 74.8%** for bench (2,472), using S01's strictly pre-game role
  tiers. Recent-team-change participants (149 in 71 games) have minute CRPS **4.126** and coverage **67.1%**;
  29 core returns in 24 games are below the 100-player/30-game gate. Membership calibration uses the separate
  known-play/coach-DNP cohort and recent-minute role proxies above, because exact S01 profiles are not available
  for historical nonparticipants. Three on-court player records have no fixed-engine output; they are counted, not
  silently joined as scored participants. The baseline uses total minutes including overtime; allocator comparisons
  use regulation minutes.
- **NBA-only D29 history candidate, target screen only:** removing the 155 non-NBA rows increases star healthy roles
  by **0.853** minutes and conditional target allocations by **0.764** on average. Star target absolute error changes
  **−0.328** minutes (game-clustered 95% **−0.514 to −0.156**), while bench target absolute error changes
  **+0.036** (**+0.006 to +0.069**); overall **−0.013** (**−0.037 to +0.011**). These are exploratory
  target-level, actual-participant comparisons, not engine CRPS, a full availability forecast or a promotion decision.
  Ramp and residual-spread fitting used the same pre-2026-01-01 cutoff in both builds. A candidate engine backtest
  and the frozen player-first non-inferiority gates are still required.
- **NBA-only candidate wiring:** `scripts/a1_minutes_candidate.py` provides an isolated D29 build that excludes
  non-NBA teams, rejects same-day player/team duplicates and requires two canonical NBA teams per game. Its F4 audit
  `analysis/experiments/20261122_a1_s05_nba_candidate_wiring_v3.json` exactly matches all **4,346** independently
  built candidate player states (healthy, allocated, missed and return index; max difference **0**). A synthetic
  clean-history test also exactly matches the original D29 states. The module is connected to the backtest CLI
  only by an opt-in switch, not to production; this verifies implementation, not forecast accuracy.
- **D29 short-roster target integrity:** on 10,000 synthetic five-player draws, **9,910** legacy target vectors
  miss 240 minutes by >1e-6 (maximum deficit **11.33 minutes**); **1,000/1,000** sampled legacy mean allocations
  also exceed the hard 48-minute player limit. These are target-allocation defects, not proof the engine puts fewer
  than five players on court. The isolated strict candidate preserves the original draw before deterministic
  headroom redistribution: across **50,000** draws for 5/6/7/10/15 players, its largest team error is
  **1.43e-13 minutes**, no target exceeds 48, and same-seed draws reproduce. All **400** fixed-panel team targets and
  **400** remove-top-player absence cascades reconcile to ≤1.14e-13; rosters with fewer than five are rejected
  explicitly. Historical state learning still uses D29's original allocator; strict runtime allocation and NBA-only
  history are isolated candidates, not production changes or demonstrated accuracy wins. Log:
  `analysis/experiments/20261122_a1_s05_minutes_candidate_stress.json`.
- **Four-fold conditional regulation-minute screen:** `scripts/a1_minutes_fold_eval.py` compares the original,
  NBA-only-history, strict-runtime and combined allocations on **200 preselected games per fold**, using 1,000
  matched draws per team. The **17,303** scored participant-game records include 74 without a pre-game role tier.
  Original conditional CRPS is **3.393 / 3.477 / 3.503 / 3.522** minutes for F1–F4. NBA-only minus original
  star CRPS is **−0.020 / −0.081 / −0.023 / −0.196**; bench CRPS is **−0.001 / +0.010 / +0.015 / +0.022**.
  Game-clustered 95% intervals and all tier counts are in
  `analysis/experiments/20261122_a1_s05_minutes_fold_screen.json`. On these actual-participant rosters, the strict
  runtime allocation changes conditional CRPS by less than 1e-6 in every fold: fixing short-roster feasibility is
  not by itself evidence of forecast improvement. F4 game `401811045`, team `18`, has **239.618** observed
  regulation player-minutes; all other teams are within **0.002** minutes of 240. This is included, not silently
  repaired. This screen uses actual participants and is not unconditional availability, simulated in-game minutes,
  an engine backtest or promotion evidence. **Provisional strict results:** its redistribution can give a previously
  zero-minute target a positive infinitesimal amount even when positive targets have sufficient headroom. That
  artificially changes a `draw > 0` target-play probability and may affect coverage; strict/combined results
  require correction and a new screen. In the retained F1 no-report screen strict target-play probability increased
  for **4,390/7,423** candidates, including **2,715** with known play labels, and decreased for none; the largest
  increase was **0.155**. These changes do not demonstrate better availability. The control and NBA-only
  comparisons are unaffected. The corrected candidate first redistributes into already-positive legal headroom,
  using zero-target players only if that is insufficient. In the corrected no-report F1 sensitivity the strict
  and control target-play Brier are both **0.1211569**; all **7,423** original control and NBA-only rows reproduce
  to `1e-12` for both F1 screens. The corrected strict maximum team-draw error is **1.14e-13** minutes.
  The corrected conditional screen is independently reconciled in
  `analysis/experiments/20261122_a1_s05_minutes_conditional_accounting_corrected.json`: all **17,303** rows
  and **11** control/NBA-only values per row match the original within `1e-12`, all **13** corrected source/input
  hashes match, and each fold covers the fixed 200 games/400 team-sides. Strict target means sum to 240 with maximum
  per-fold error below `3e-13`. Strict-minus-control conditional CRPS is **−1.27e-8 / +3.58e-7 / +2.67e-8 /
  −5.44e-8** across F1–F4; these minuscule target-only differences are not evidence of an engine improvement.
  Corrected all-active and no-report screens now independently reconcile all four folds, with **21** input and
  **16** output hashes; control/NBA-only values match the original **28,530** candidate rows to `1e-12`
  (`analysis/experiments/20261122_a1_s05_minutes_screen_accounting_corrected.json`). F1–F4 score **200/200/195/200**
  games, **5,218/5,225/5,013/5,208** known regulation outcomes and **2,205/2,164/1,387/2,109** unknown play
  labels. F3's five missing games have no prior same-season team roster.

  On known labels, no-report control minute CRPS is **4.709/5.612/4.610/5.479** and 10–90% coverage is
  **68.8/64.5/68.9/65.6%**; NBA-only CRPS changes by **+0.0046/+0.0173/+0.0090/+0.0091** minutes. The
  corresponding all-active control CRPS is **5.039/6.010/4.961/5.884**. Corrected strict-minus-control CRPS is
  below `1e-6` in magnitude in each screen/fold, and target-play Brier agrees to the shown six decimals; the
  prior apparent strict Brier improvement was an artefact. Neither screen reconstructs injuries, official rosters
  or genuine pre-game play probabilities; incomplete-candidate and missing-label selection limit interpretation.

- **S04 rim-expression wiring, first F4 run:** on guarded causal inputs, the previously audited F4 shot model
  reproduced its held-out control log loss **0.7295266** over **135,680** shots in **766** games. The fitted
  level-preserving rim slope is **1.1315**, with training mean **0.683197** unchanged on **19,628** known rim
  shots. Candidate-minus-control shot log loss is **−0.0000312** (95% game-cluster bootstrap **−0.0000556 to
  −0.0000063**) over the full fold, and **−0.0000382** (**−0.0000836 to +0.0000058**) on the fixed 200 games.
  This is a preliminary causal-input node diagnostic, not a v1.3 engine comparison, all-fold decision or
  promotion. **Report metadata defect:** `training_tail_from` erroneously says 1970 due to pandas datetime-unit
  handling; an independent reconstruction verifies the actual **72,379** training rows span **2 Nov–31 Dec 2025**,
  before F4. Retain the original report/source, fix the label and rerun under a separate name before use.
- **S04 rim-expression decision:** corrected F1–F4 guarded-input screens scored **136,578 / 139,660 / 87,671 /
  135,680** shots in **773 / 782 / 490 / 766** games. Their level-preserving slopes were **+0.0718 / −2.1686 /
  −0.8422 / +1.1315**, and candidate-minus-control full-fold log losses **−0.00000222 / +0.00001481 / +0.00001113 /
  −0.00003117**. On the fixed 200 games per fold, changes were **−0.00000135 / +0.00001185 / −0.00001006 /
  −0.00003822**. Training tails, candidate/control predictions, original/corrected F4 rows, **80** populated
  measurement groups and recorded hashes independently reconcile (`20261122_a1_s04_rim_accounting.json`).
  A same-input seed-7/seed-8 model refit measures **0.013718%** relative RMS training noise; the candidate's
  four-fold mean is **−0.000259%**, with pooled game-cluster z **−0.283**
  (`20261122_a1_s04_rim_node_gate.json`). It therefore fails the existing node retention gate and is not retained
  for an engine test. The result is a guarded-input, actual-shot diagnostic, not proof that player-based defence
  cannot improve or that the serving v1.3 control was compared.
- **S04 lagged tracking-defence test:** the frozen experiment (`TRAINING_PLAN §8`, preregistered in **5e30f4**)
  read **1,692** under-six-foot and three-point source files, comprising **194,519** player/day/bucket rows; **15,060**
  latest-team labels disagreed with the dated NBA log and were not used. All five defender histories were known on
  **903,789/921,103 (98.12%)** shots for under-six-foot and **904,462/921,103 (98.19%)** for threes; **20** invalid
  fives remained missing. A separately implemented chronological reconstruction checked **146,581** distinct fives,
  **4,605,515** saved values and all source hashes (`20261122_a1_s04_tracking_accounting.json`). Cumulative counts
  use only source dates strictly earlier than the shot date, but source revisions and identity-crosswalk publication
  timing are unproven; these retrospective inputs are not proof of what was published at the original tip.

  On guarded historical shot nodes, paired full-fold loss changes F1–F4 were **+0.00022107 / +0.00002580 /
  +0.00000209 / +0.00001616**; fixed-200 changes were **+0.00018838 / +0.00002967 / −0.00000808 / −0.00000906**.
  Rim fitted slopes were **−1.5372 / −0.8092 / +0.6969 / +0.6302**, and three-point slopes **+2.9823 / −0.5322 /
  +0.6364 / −1.3056**. Independent reconstruction checked **499,589** predictions and **112** supported measurement
  groups (`20261122_a1_s04_tracking_node_gate.json`). Mean relative loss worsened **0.00906%**, pooled z **+3.76**;
  F1 worsened **0.03021%**, z **+3.63**, exceeding twice the same-input **0.01372%** seed-noise floor. The frozen
  node gate is **worse**, so this increment is not retained for an engine test. These are source buckets, not
  on-ball matchups; this result does not settle whether a different player/lineup defence mechanism could improve.
- **Post-hoc S04 interaction:** composing both frozen log-odds adjustments, without refitting, gives full-fold
  combined-minus-control losses **+0.00021749 / +0.00005594 / +0.00000852 / −0.00000768**. The non-additive
  interaction terms are **−0.00000137 / +0.00001533 / −0.00000470 / +0.00000733** on F1–F4. All **499,589**
  predictions and their paired game-cluster summaries independently reconcile
  (`20261122_a1_s04_defence_interaction_accounting.json`). This is descriptive and post hoc; neither rejected
  family nor the combination is retained, and no engine forecast or player gain was tested.
- **S04 cutoff and next tests:** fitted tails began **12 Dec 2023 / 18 Nov 2024 / 10 Mar 2025 / 2 Nov 2025**,
  with fold cutoffs **31 Dec 2023 / 31 Dec 2024 / 30 Sep 2025 / 31 Dec 2025**. No 2026–27 final-test rows were
  scored. The next falsifiable defence question is whether a defender's prior defended-shot residual **after**
  accounting for shot location, shooter and the other four defenders predicts held-out outcomes beyond D30,
  separately at the rim and three; reject if cross-fold loss does not beat same-input training noise or the
  player-first engine gates. A second question is whether observed defender-five strength changes the
  attacker's shot/turnover choice in `who`/`what` before shot quality; test as a separate pre-origin increment
  rather than adding arbitrary points. These are future hypotheses, not results or approved promotions, and
  historical source revision timing remains an explicit limitation.
- **S04 reproducibility after typed-ID guards:** the four-season NBA player/day/team lookup is unchanged across
  **112,952** keys. Rebuilding the feature table produced a byte-identical **921,103**-row parquet
  (`d88e47e2…b952866e`); an independent replay again checked **1,692** source files, **146,581** game-fives and
  **4,605,515** values (`20261122_a1_s04_tracking_accounting_typed.json`). Missing or non-finite IDs now fail
  explicitly rather than being silently converted to an integer. The original source/report hashes are preserved
  in the preceding evidence checkpoint; this verification does not change either model decision.
- **S05 NBA-only engine screen:** on the exact **200** fixed F4 games with **4,346** actual-participant
  player-games, NBA-only minute history changed pooled MIN CRPS by **−0.00416** minutes (95% game-clustered
  interval **−0.02699 to +0.01913**) against the registered **0.02634**-minute seed-noise floor: the primary screen does
  not establish an improvement. Stars (**284** player-games) changed **−0.14916** (95% **−0.27174 to −0.03359**),
  starters (**1,578**) **−0.02295** (**−0.04428 to −0.00263**) and bench (**2,472**) **+0.02440**
  (**−0.00625 to +0.05688**); 12 unknown-tier rows are insufficient for a tier decision. Margin CRPS changed
  **−0.08102** (95% **−0.14253 to −0.02176**) and total CRPS **+0.03237** (**−0.04004 to +0.10525**).
  Independently reconciled **1,600** raw quarter scores and **4,346** 3PM actuals have zero mismatches; one
  player and its team sum are incomplete. This is not a pre-game availability forecast, and the star gain cannot
  override the pooled primary gate. Of **69** listed player-tier/game non-inferiority interval checks, **59**
  are inside their frozen bounds; **10** are not established (six star bias/coverage and four game/quarter
  coverage intervals). An additional **10/10** pooled-player bias/coverage intervals are inside the same bounds.
  Direct sampling of game indices independently reproduced all **15** pooled player-statistic point estimates and
  bootstrap intervals to maximum absolute error **1.5e-15**; it confirmed those 10 pooled bounds. The reusable audit
  and source fingerprints are `20261122_a1_s05_nba_only_fixed200_bootstrap_accounting_v2.json`; its initial
  uncommitted test invocation had the same numbers but a source-level Pylance call-arity diagnostic, so the transient
  output was discarded and the corrected source rerun. An interval crossing a bound is inconclusive, not proof of harm.
  Full paired comparisons and accounting:
  `20261122_a1_s05_nba_only_fixed200_{comparison,accounting}.json`.
- **S05 control provenance:** the NBA-only audit matches the S01 manifest on all **38** shared data/model/config
  fingerprints (**17** fitted model files, **14** derived inputs, **5** raw inputs and **2** configurations).
  Six shared source files changed for opt-in A1 work; the tested feature and matchup metadata select the original
  legacy policies, and the backtest's `crps_samples` and `pit` function ASTs are unchanged. The old and new legacy
  matchup functions also produced bit-identical values in **9** columns on **1,000** synthetic lineups, including
  missing individuals and entirely missing defender rows. The new default engine reproduces all saved output
  columns on the three fixed wiring games, not a second full 200-game default rerun.
- **S05 strict-allocation engine screen:** on the same **200** F4 games and **4,346** scored actual-participant
  player-games, strict minus control pooled MIN CRPS is **+0.000268 minutes** (95% **−0.000111 to +0.000653**),
  below the **0.02634-minute** seed-noise floor and not an established improvement. Star/starter/bench changes are
  **+0.000768 / +0.000205 / +0.000220** minutes; pooled PTS/REB/AST/3PM changes are **−0.000731 / +0.000668 /
  +0.000395 / −0.000130**, respectively, with all four 95% intervals crossing zero. All **69/69** tier/game and
  **10/10** additional pooled bias/coverage bounds are established. Independent direct game-index resampling
  reproduces **15** pooled metrics and intervals to **2.6e-15**; raw accounting matches **1,600** quarter scores
  and **4,346** 3PM actuals, with the same one incomplete player/team output as the control. The run took **1,731 s**;
  its four candidate source hashes and all **38** shared data/model/config hashes match. Reports are
  `20261122_a1_s05_strict_fixed200_{accounting,comparison,gate,bootstrap_accounting}.json`.
  This is an actual-participant screen, not an availability forecast. **Decision for S06:** retain the existing
  D29 allocator/history as the engine control; keep both candidates isolated because neither passed the pooled
  primary win gate. The strict target solver's short-roster accounting fix remains useful for further research,
  but target conservation alone is not evidence that it improves real player forecasts.
- **Preliminary minute-gate defect:** the first and v2 gate reports used the seed interval's **0.01653** half-width
  instead of the preregistered maximum absolute endpoint **0.02634** (interval **−0.00671 to +0.02634**).
  They must not be used for selection. Their exact sources were preserved in **00a51cc** and **890bee3**;
  the corrected checker reuses the manifest's floor calculation and has an asymmetric-interval regression test.
  Its new `20261122_a1_s05_nba_only_fixed200_gate_v3.json` reports the correct floor and the same **59/69**
  established non-inferiority bounds. The NBA-only primary screen still fails because its improvement is smaller
  than the correct floor and its 95% interval includes zero.
- **Historical prior-box minute sensitivities:** the independently audited all-active and fixed no-report fallback
  screens cover F1–F4 respectively **200/200/195/200** games and **400/400/390/400** team-sides. The five F3
  season-opening games have no prior same-season team candidates; their players are not treated as zeroes. The
  candidate universes contain **7,423 / 7,390 / 6,400 / 7,317** player-games; known regulation outcomes are
  **5,218 / 5,225 / 5,013 / 5,208**, and unknown play labels **2,205 / 2,164 / 1,387 / 2,109**. One F2 known
  label has no usable regulation outcome. On known outcomes, the no-report control's minute CRPS is
  **4.709 / 5.612 / 4.610 / 5.479**, and target-play Brier is **0.1212 / 0.1392 / 0.1121 / 0.1311**. No
  fewer-than-five availability patterns required resampling; **200 / 209 / 281 / 179** fallback records lacked a
  prior minute EWMA. Neither sensitivity reconstructs historical injury reports or official dated rosters. The
  strict and combined results in that first run are superseded by the corrected screen above. Original audit:
  `analysis/experiments/20261122_a1_s05_minutes_screen_accounting_uncorrected.json` (21 input and 16 output
  fingerprints); individual JSON reports and ignored parquet distributions use the matching fold prefixes.
- **S05 isolated engine wiring:** the default three-game, 1,000-world replay matches the original S01 saved control
  exactly across **93 game** and **22 player** columns, **3 games / 64 player-games**. Separate NBA-only-history,
  strict-runtime and combined wiring runs each independently reconcile **24** quarter scores, **64** player
  three-point actuals and **6** team sums with zero mismatches; these are wiring checks, not accuracy tests. The
  NBA-only and strict full **200-game** candidates subsequently completed as described above; actual participants
  remain supplied by the box.
- **Preregistration:** `analysis/experiments/20261122_a1_pre_candidate_manifest.json` fixes the original 200-game
  screen, **200 / 200 / 200 / 718** F1–F4 confirmation games, simulation streams and input hashes before candidates.
  An independent check finds **1,318 distinct** game IDs within their declared fold dates and **2,636 distinct**
  stream seeds across the two predeclared confirmation streams.
  The earlier manifest did not include production-model hashes; still before any candidate, the separate
  `analysis/experiments/20261122_a1_production_baseline.json` pins **17** production model artifacts, **11**
  upstream-build inputs and the local bundle. All **67** original input fingerprints were independently unchanged.
  The separate 20-game 10k stress set deliberately spans five OT, five short-roster, five close and five blowout
  games; its **26 star player-games** do not meet the 100-player-game tier gate. It is not a representative sample.
  The full same-input independent-stream noise estimate and final manifest are complete, pinned to source checkpoint
  `c6d5db4`. After a type-only seed-list annotation, all 13 inspected semantic code fields and **3,036** recorded control/
  confirmation seeds match that checkpoint. Raw bytecode SHA-256 is
  `aa7233f20022d729a98acf25cb1b321678a83a3cfa33167ffc12f7b86db7e8c6`; a prior marshalled-tuple digest varied across
  processes and is not a valid equality test. No candidate has been scored.

### A1 S06 ordered substitution pilot (22 Nov 2026; descriptive)

- On the fixed **200** F4 games, sequential replay retained **191** and quarantined **9** for unsupported lineups,
  missing eligible entrants/team membership, or an end-game event incorrectly marked scoring with zero points.
  Ordering by period, descending clock and then within-clock sequence separates reversals and preserves the actual
  pre-substitution scoreboard; in game `401810498` sequence 709 the home margin is **−3**, not the grouped
  window's later **−4**.
- The original candidate inherited a substring match that labelled **22,224/22,577** non-jump-ball events, mostly
  jump shots, as jump balls. Its source/report remain archived; the corrected isolated pilot reconciles **23,160**
  windows, **11,277** raw substitutions, **46,320** scoreboards and lineups, and **502,773** personal-foul values.
  The independent accounting is `20261122_a1_s06_sequence_audit_v3.json`.
- For a conservative legal/no-sub sample, retain full timeouts with one timeout and no substitutions at that clock
  outside the immediately reconstructed group. This leaves **1,216** substitution and **600** no-sub windows among
  **1,972**, excluding **148** other-same-clock-substitution and **8** multiple-timeout windows. Independent
  group-by and every-field accounting passed on **1,816** windows and **3,632** team decisions. Outcome-dependent
  exclusions, inferred period lineups and actual-participant rosters prevent interpreting these as an unbiased,
  exhaustive substitution hazard or pre-game availability forecast.
- **Selected timeout state response:** `20261122_a1_s06_timeout_states.json` describes **39,380** player decisions
  across those 191 games using S01 pre-game role tiers. With 10,000 complete-game bootstrap replicates, starters
  leave in **55/202 = 27.2%** of defined foul-trouble decisions (95% **21.3–34.1%**), versus **1,334/8,651 = 15.4%**
  otherwise (**14.4–16.4%**). Starter exits occur at **5.3%** of 3,196 under-four-minute stints (**4.4–6.2%**)
  versus **26.0%** of 2,127 stints at least eight minutes (**23.4–28.5%**); all four cells meet the frozen
  100-player-game/30-game support floor. Margin, quarter, rest, role and sparse OT cells are in the report. These
  are descriptive, confounded and outcome-selected, not causal effects, calibrated hazards or forecast gains.
  An independent check reconciled **2,790** outgoing/incoming labels and **4,160** matching S05 role records.
- **Pre-window candidate feasibility:** using the audited prior-box cohort and S05 all-active mean target proxy,
  the 1,816 timeouts yield **18,160** observed-five out rows and **48,385** incoming candidates. Incoming
  non-entries are **45,604 unknown labels**, not assumed physically eligible negatives; **82** incoming rows
  are known ineligible after six fouls or an earlier ejection. **9** observed entrants were not in the prior roster
  or already observed on court. Missing prior targets affect **70** out and **63** in rows; **415** overtime rows
  have no regulation-target deficit. An independent raw-event and every-row audit reconciled all **66,545** rows,
  prior dates, player pools and **2,790** substitutions. Future-participant injection, same-day targets, earlier
  ejection and tampered-deficit tests guard the cutoff. The retrospective source lacks official pre-tip availability
  and publication timestamps; no model has yet been fitted or validated from this selected dataset.
- **Earlier-fold source edge case:** the first 200-game F1 replay reconciled **21,036** windows but could not
  construct candidates: game `401585742` contains an ejection with no athlete ID (its text names a coach), while
  `401585415` was already quarantined because a `No Foul` event had no player. No candidate output was written.
  The retry must explicitly exclude replay-retained games with an unidentifiable ejection; the feed does not
  establish a general actor-type rule. See `20261122_a1_s06_fold_F1_failed.json`.
- **F1 retry accounting:** of the fixed 200 games, **13** fail replay and **1** further game has an unidentified
  ejection. The remaining **186 games**, **1,768** selected timeouts and **65,864** candidate rows independently
  reconcile, including **2,673** substitutions, **5** unseen incoming players and **45,516** unknown incoming
  non-entries. This is coverage evidence, not a fold-model score or a pre-game availability estimate.
- **F2/F3 fold preflights:** both fixed 200-game panels replayed, independently accounting for **21,311** and
  **23,779** windows, but wrote no candidate data. In F2 game `401705329`, a recorded ejection at **11:26 Q4** left
  that player in the reconstructed five at the **11:13** timeout until the later feed substitution. In F3 game
  `401810097`, `Excess Timeout Technical` was incorrectly classified as an actual timeout by substring matching.
  Correct the latter at the sequence source and quarantine games with ejected-on-court conflicts; see
  `20261122_a1_s06_fold_F2_F3_failed.json`. Neither case establishes a deployable substitution model.
- **F2/F3 retries:** independent sequence and candidate accounting retain **181** and **178** games respectively,
  yielding **17,370** and **17,270** outgoing rows. F2 has **2** ejected-on-court conflicts; F3 has **5** missing
  prior rosters and **1** unidentified ejection. Incoming non-entry labels remain unknown (**44,231** and
  **36,922**); the populations are still selected full-timeout diagnostics.
- **V2 reproducibility and seed preflight:** corrected F1/F4 replays reproduce every one of **65,864/66,545** earlier
  candidate rows across all **23** columns. The 2022–23 seed replay reconciled **21,896** windows but its target
  builder stopped before output because the loader omitted a column required by the NBA-team helper. This is a
  software failure, not a measured model result; see `20261122_a1_s06_fold_seed_v2_failed.json`.
- **Dated seed v3:** the fixed 200-game sample yields **184** replay-reconciled games and **6,354** prior-roster
  targets. An independent audit verified all roster/profile dates, a maximum **0.0000931-minute** team target-sum
  error, and exact 1,000-draw reproduction of **71** targets in two games. Replacing **98,484** player-game minute
  outcomes from the 2022-12-01 fit cutoff onward left the earlier fitted ramp and spread unchanged. This establishes
  the sampled input mechanism, not the historical publication timing or a forecast gain.
- **S06 screen preflight:** the first attempt failed before fitting because this environment has LightGBM but not
  its optional scikit-learn wrapper. The retry uses the repository's native LightGBM API with the same frozen
  binary objective and hyperparameters; the failed source and error are preserved in
  `20261122_a1_s06_out_screen_wrapper_failed.json`. No fold result informed this implementation repair.
- **S06 outgoing screen:** on **70,480** selected full-timeout player decisions from **736** F1–F4 games, the fixed
  conditional period/tier baseline has Brier **0.127265** and the fixed state model **0.105985**; paired difference
  **−0.021280** (10,000 complete-game bootstrap 95% **−0.022412 to −0.020141**). All four folds improve
  (**−0.022331 / −0.021422 / −0.020079 / −0.021262**); pooled log loss falls **0.419834→0.341200**.
  Independent refits match **70,480/70,480** probabilities exactly and direct game-resampling reproduces
  20 fold/tier cells plus pooled metrics to **2.1e-16**. F3 has four baseline-fallback rows; no other fold has any.
  The selected timeout population is outcome-conditioned and prior-box membership does not establish current
  physical availability. This result is an event-level feasibility screen, not an engine or forecast improvement.
  Reports: `20261122_a1_s06_out_screen.json` and `20261122_a1_s06_out_screen_audit.json`.
- **S06 foul-out defect:** the current engine initialises its `fouled_out` mask to false but never updates it.
  In a one-world controlled state probe with five scheduled players, a sixth available teammate and both
  personal-foul counters set to six, the six-foul player remains in the next segment and the substitute is not used.
  The five-foul control also remains on court as expected. This proves the mechanism, not its frequency or forecast
  impact. Both the original probe and its type-correct v2 reproduce the same state
  (`20261122_a1_s06_foul_out_probe{,_v2}.json`); keep any correction isolated and subject to the existing paired
  engine gates.
- **S06 incoming coverage:** across the four fixed folds there are **182,984** potential off-court candidate rows,
  **10,711** observed in-pool entries and **172,273** non-entries with unknown eligibility; **242** rows are
  explicitly disqualified, and **22** observed entrants are outside the prospective pool. A strictly prior position
  is known for **179,478/182,984** candidate rows and **10,672/10,711** entries. The **14,096** team-timeouts include
  **6,507** with an in-pool entry, of which **2,845** have multiple entrants. **70,337** unknown non-entries later
  appear somewhere in the game's retrospective participant list; that future information is coverage only, not a
  predictor or proof of their current physical eligibility. Independent raw-window aggregation reproduces all
  five seed/fold coverage reports (`20261122_a1_s06_in_coverage{,_audit}.json`).
- **S06 incoming ranking:** given observed outgoing players and the in-pool entry count at **6,507** selected
  F1–F4 team-timeouts, a fixed positive-versus-unlabelled-mixture ranker recovers **58.10%** of **10,711** observed
  entrants versus **13.22%** for target-deficit ranking; paired gain **44.88 percentage points**, game-cluster
  95% **43.53–46.20 pp**, with 4/4 fold improvements. The population pool is over-inclusive and the simple
  baseline may rank unavailable prior-roster players. Restricting to the **6,493** complete transitions under an
  explicitly retrospective, assumed-active participant roster gives **61.71% versus 45.23%** on **10,680**
  entries (gain **16.48 pp**, 95% **15.32–17.70 pp**). Neither roster assumption proves physical availability;
  observed exits/counts are oracle conditioning. Independent source reconstruction reproduces **84,344** scores,
  all pool and participant-oracle selections, and bootstrap metrics exactly. The selector rejects inactive,
  disqualified or duplicate replacements and insufficient scoreable players. Reports:
  `20261122_a1_s06_in_screen{,_audit}.json`. These are ranking diagnostics, not calibrated entry probabilities
  or a production/engine result.
- **S06 engine-model preparation:** for the F4 feasibility candidate, frozen nodes refitted on **729** earlier games
  through **31 Dec 2025** reproduce both saved F4 screen predictions with maximum absolute error **0**. The earlier
  games contain **7,064** selected timeouts, yielding **729** regulation-game templates and **30** observed-overtime
  period templates, including periods without a selected timeout. This verifies reconstruction and cutoff, not the
  realism of those selected/opportunity-biased clocks or an engine gain. Manifest:
  `20261122_a1_s06_engine_models_F4.json`.
- **S06 engine wiring:** on the three fixed F4 reproduction games, the opt-in policy completed **3,000** simulated
  worlds in **63 s**; the unchanged default reproduced the earlier control to `1e-12` in **51 s**. The policy recorded
  **28,158** timeout-world events, **35,389** sampled exits, **1,395** forced foul-out replacements, **364**
  coalesced and **582** expired selected clocks, plus **88** overtime-timeout events. Counts describe only this
  candidate wiring sample; they are not historical rates. Independent saved-output checks reconcile **24** actual
  quarter scores, **64** player 3PM actuals and **6** complete team 3PM sums. Every-world team-minute and points
  assertions ran inside the candidate, but independent per-world saved accounting and the paired accuracy gate remain.
- **S07 retained ESPN report coverage:** five collections (19–21 Nov 2026) are all in the protected 2026–27 season;
  none is a permissible development report archive. Using each run's completion as a conservative capture bound gives
  **31** pre-tip snapshots over **18** games (**1** other snapshot is at/after tip), with **1,093** roster/player
  snapshots and **634** unique player-games. Every collection has all **30** roster teams and an injury file;
  **535** injury entries match team/player IDs (**426 Out**, **109 Day-To-Day**, counted per collection). The
  **2,105** roster records effectively labelled Active have no injury entry and are not proven healthy. Of the unique
  player-games, **331** are listed in retained final boxes, **128** are unlisted, and **175** lack a final box.
  Final-box listing does not establish play or DNP. Independent reconstruction matches all counts; no protected
  status/outcome calibration or model-selection score was computed. Reports:
  `20261122_a1_s07_report_coverage{,_audit}.json`.
- **S06 independent world replay:** a trace-enabled rerun of the three pinned F4 games preserves all **104** game
  and **20** player columns on **64** player-games to `1e-12`. Independent replay checked **3,000** worlds,
  **1,472,554** legal distinct/available/non-disqualified fives, **1,395** post-foul replacement snapshots and
  **77** OT worlds; reconstructed individual minutes differ by at most **1.78e-15** minutes. Player points reconcile
  to team periods and final scores. Synthetic four-player and no-replacement cases raise explicitly. This is
  actual-participant wiring/accounting, not a player-accuracy result. Reports:
  `20261122_a1_s06_world_trace_{accounting,reproduction}.json`.
- **S07 prior-box labels:** independent reconstruction of **7,317** strictly prior NBA-box memberships over **200**
  F4 games found **4,316** known plays, **892** DNPs, **2,100** unlisted and **9** listed-unknown player-games.
  Explicit retrospective DNP text partitions into **675** coach, **6** rest, **35** injury, **9** illness,
  **2** injury/illness and **165** other recorded reasons. Other reasons may describe injuries without using that
  word; none is silently made healthy. All known-play keys overlap the **4,346**-player-game oracle, which has
  **30** additional keys outside that cohort. Prior membership is not proof of eligibility and these are post-game
  labels, not dated pre-tip reports (`20261122_a1_s07_labels_audit.json`).
- **S06 fixed-screen failure:** the selected-timeout actual-participant F4 200-game/1,000-world screen completed at
  least **40** games (last progress **378 s**) before a world had fewer than five non-disqualified available players
  after a foul-out. It stopped explicitly and saved no aggregate outputs. Thus there is no 200-game minute-CRPS or
  state-response estimate and no promotion; the D29 control remains. The failed run and source/log fingerprints are
  preserved in `20261122_a1_s06_candidate_fixed200_failure.json`. A same-stream replay identified game
  **401810472** (20 Jan 2026), home team **7**, with **8** actual-participant inputs; world **563** reached the
  explicit no-eligible-five condition. This is a simulated failure, not a claim that the real team had four players.
  The single-game same-stream state replay found **four** six-foul players and **four** below six with **4.4 s**
  left in Q4 (`20261122_a1_s06_foulout_state_probe.json`); the error-context change does not change policy draws.
- **S06 isolated player-foul-penalty repair:** the opt-in rule candidate reproduces all **104** original
  game columns and **20** player columns on the same **3 games / 64 player-games**; its **3,000** worlds and
  **1,472,554** traced fives independently reconcile, with no exception event in those games. In the prior failure
  game, the saved **1,000** worlds, **473,544** fives, **38** overtime worlds and all saved player means independently
  reconcile; the former failure world records one made technical with **4.4 s** left. Maximum reconstructed
  player-minute error is **1.78e-15** in each audit. The one-game backtest process nevertheless exited **1**
  after simulation: its existing one-game summary contains non-finite statistics and cannot be serialized. The
  independent probe report records this failure rather than calling it a completed backtest. The repair uses an
  earlier FT percentage for the technical and does not model injury/ejection re-entry. No fixed-200 accuracy
  comparison or promotion is implied. Reports: `20261122_a1_s06_penalty_three_{output,world}_accounting.json`
  and `20261122_a1_s06_penalty_probe_world_accounting.json`.
- **S06 flow-instrumentation preflight:** on the same **3 games / 64 player-games**, opt-in flow capture
  reproduced **321** candidate game values and **1,408** player values, and independently reconciled **1,280**
  recorded player-period values and **96** simulated team-quarter/component sums (maximum floating difference
  **1.42e-14**). This validates wiring, not accuracy; the fixed **200-game** screen is still running.
  Reports: `20261122_a1_s06_penalty_flow_wiring_{output,flow}_accounting.json`.
- **S07 F4 fixed baselines:** on **5,208** known play/DNP labels from **7,317** strictly prior-box candidates,
  the no-report physical-availability fallback has play-proxy Brier **0.15450** (game-cluster 95%
  **0.14162–0.16773**) and infinite log loss due to **718** impossible predictions. The target-positive frequency
  proxy has Brier **0.13110** (95% **0.12445–0.13817**) and infinite log loss from **109** impossible predictions.
  Of **400** team-games, **399** have valid scores: starter-slot accuracy **78.05%** (95% **75.90–80.10%**) and
  exact-five accuracy **30.83%** (95% **26.25–35.34%**); **4** observed starters are outside inferred candidates.
  Independent reconstruction checks every score, cell and interval. The **2,109** unknown labels are excluded;
  inferred prior-box membership is not a dated roster, and physical-availability and play proxies are not the same
  outcome. Four-fold results follow. Reports: `20261122_a1_s07_baseline_F4{,_accounting}.json`.
- **S07 four-fold baseline completion:** independent accounting of the pre-registered F1–F4 fixed panels confirms
  **28,530** inferred candidates, **20,665** known play/DNP labels and **7,865** unknowns. F3 has **5** games without
  any prior roster. The **1,574** supported team-games have F1/F2/F3/F4 starter-slot accuracy
  **83.91/78.35/79.84/78.05%** and exact-five **42.36/31.25/29.79/30.83%**; **15** team-games lack required
  prior positions, **1** lacks complete observed starter truth and **10** lack prior rosters. The fixed no-report
  play-proxy Brier is **0.14565/0.17460/0.14566/0.15450**; corresponding log losses are infinite, with
  **673/815/664/718** impossible predictions. The target-positive play proxy has Brier
  **0.12116/0.13919/0.11205/0.13110** and infinite losses from **61/132/52/109** impossible outcomes.
  Each fold's **10,000** game-cluster bootstrap intervals and coverage are in
  `20261122_a1_s07_baseline_F{1,2,3,4}{,_accounting}.json`. Physical status, unlisted player outcomes and
  historical publication times remain unknown; these estimates cannot satisfy the dated availability gate.
- **S07 dated split gate:** all **5** independently inventoried retained report collections are from 19–21 Nov 2026
  in the protected season. F1, F2, F3 and F4 each have **0** retained report origins through their training cutoff
  and **0** within validation dates; see `20261122_a1_s07_dated_cohort_gate.json`. A report-status play/start model
  cannot be trained or calibrated on a genuinely dated development cohort. This is a statement about retained data,
  not about whether historical reports existed elsewhere; no protected outcomes were scored.
- **S07 status/start decision:** because the genuinely dated development cohort contains **0** origins, no
  report-status play/start candidate is calibrated or promoted. The existing fixed fallback is retained; the
  prospective collection/support gate is documented in TRAINING_PLAN §8.2. The retrospective baseline's Brier and
  starter accuracy do not establish status calibration or physical health.
- **S07 sequence-builder input preflight:** the 2022–23 development source yields **2,460** distinct NBA team-games,
  **31,551** player listings and **31,471** prior-state observations. Raw boxes and segment schedules agree on all
  **2,460** team-game sides for that season. This is a construction check, not a return/rest score, and the historical
  boxes still have no publication timestamps.
- **S07 development sequence coverage:** independent reconstruction matched **128,321** prior-state observations and
  **11** fields each over **9,846** team-games in 2022–23 through 2025–26. There are **6,137** left-censored recorded
  DNP observations, **8,490** unlisted next-team-game outcomes, **344** ambiguous next listings, **1,534**
  season-end cases and **27** observed prior/same-day team-change cases; none is silently filled as an absence.
  The remaining known outcomes include **15,543** non-left-censored DNP-return exposures and **97,808**
  recorded-rest exposures. The **17,261** non-left-censored return observations have **14,889** first reasons
  explicitly coach-related, **1,798** other recorded, **494** explicitly injury/illness and **80** exact rest;
  other reasons are not assumed healthy. Dates and source reports remain retrospective, and these counts are
  neither physical recovery estimates nor fitted/validated hazards.
  Reports: `20261122_a1_s07_sequences{,_accounting}.json`.
- **S07 recorded-DNP return/rest proxy screen:** on the fixed 200-game F1–F4 panels, earlier-fold reason-only versus
  reason-plus-duration return Brier differences (candidate minus baseline) are **−0.00540** (95% **−0.01265 to
  +0.00181**), **−0.01368** (**−0.02098 to −0.00638**), **−0.01082** (**−0.01878 to −0.00283**) and **−0.01380**
  (**−0.02275 to −0.00441**), on **612/713/503/649** known next-listing observations. Corresponding log-loss
  differences are **−0.01071/−0.02856/−0.02352/−0.02772**. Star-return cells have **23/54/23/22** observations
  and do not meet the 100-player-game/30-game floor. Recorded-rest role-versus-overall Brier changes are
  **+0.000000083/−0.000000122/−0.000000005/−0.000000591** on **4,051/4,005/4,001/4,078** observations; these
  are very small and the F2–F4 intervals include zero. An independent dictionary-based reconstruction checked
  all **18,612** predictions, training counts, group metrics, calibration cells and **10,000** game-bootstrap draws.
  Selection on known next box listings and retrospective reason text limits these to conditional play proxies; they
  neither establish physical recovery nor validate a season-absence hazard or pre-tip status. Reports:
  `20261122_a1_s07_sequence_screen{,_accounting}.json`.
- **S07 recorded-spell follow-up:** **1,493** non-left-censored first-DNP anchors (F1–F4: **371/439/308/375**)
  yielded **1,188** observed returns and **305** censored trajectories, including **216** unlisted gaps. The
  independent audit reproduced **29,860** analytic/simulated survival values and **80** role-horizon cells with
  **10,000** game-bootstrap draws. On the supported pooled first next-game horizon, censor-aware observed
  continued-DNP survival is **0.393/0.409/0.502/0.375**, versus duration-candidate
  **0.471/0.447/0.457/0.448**; the paired candidate-minus-observed 95% intervals are **[0.002, 0.157]**,
  **[−0.026, 0.102]**, **[−0.117, 0.029]** and **[−0.001, 0.144]**. The first recorded DNP is already one
  missed listing. All star/starter role horizons and all pooled horizons beyond the second next game are
  unsupported (<100 at risk or <30 games); reporting estimates there does not establish a reliable tail.
  Informative censoring and retrospective selected listings preclude a physical recovery or pre-tip forecast
  conclusion. Reports: `20261122_a1_s07_spell_sim{,_accounting}.json`.
- **S07 simulated starters and fallback stress:** the pre-registered independent-availability simulations and
  world-by-world replays cover **200/200, 200/200, 195/200 and 200/200** fixed development games. They reconcile
  **7,398/7,390/6,199/7,299** player-games and **769/805/569/904** distinct fives. Across **15,890,000**
  rostered team-worlds, **14,106,556** have supported positions and **1,783,444** have an active player whose prior
  position is unknown; none has fewer than five active players. On supported inferred-roster player-games, star
  projected starter frequencies are **0.924/0.927/0.919/0.881** versus recorded **0.762/0.665/0.678/0.645**,
  with Brier **0.177/0.263/0.293/0.274**; corresponding 10,000-game-bootstrap 95% Brier intervals are
  **[0.143, 0.212]/[0.225, 0.302]/[0.244, 0.342]/[0.235, 0.315]**. Starter-tier simulated frequencies are
  **0.803/0.780/0.795/0.743** versus **0.700/0.662/0.693/0.639**. These condition on supported worlds, use
  inferred prior-box membership and retrospective starter labels, and exclude **1/2/4/4** recorded starters
  outside the inferred pools; they do not establish pre-tip availability or independence calibration. F3 has five
  games without prior rosters and one F4 team lacks complete starter labels. Reports:
  `20261122_a1_s07_starter_sim_F{1,2,3,4}{,_accounting}.json`.
  Separately, a synthetic serving-path stress test with five roster players but only four available showed that
  the legacy target-table fallback reinstates the unavailable player for **2,880/2,880** seconds. This is a
  reproduced correctness bug, not an observed historical rate; the zero short-roster proxy-world count above
  cannot validate rare or uncertain prospective rosters. The serving path has not yet been changed.

## 6b. A1 S03 matched component diagnosis (22 Nov 2026; descriptive)

The fixed S01 pool-0 F4 control and manifest match on **200 games / 400 team-sides**. Pre-date own-offence and
opponent-defence ratings, real/simulated component outcomes and denominators are specified in TRAINING_PLAN §8.
The complete archived team-rating summary and every rounded component coefficient/mean reproduce. On
`analysis/experiments/20261122_a1_s03_components.json`, **10,000 complete-game paired bootstrap** replicates give:

| Sim minus real loading | Own offence (95% interval) | Opponent defence (95% interval) |
|---|---:|---:|
| Points/100 possessions | −0.417 (−0.837, −0.024) | −1.008 (−1.395, −0.640) |
| FG% | −0.00140 (−0.0034, 0.0005) | −0.00387 (−0.0055, −0.0022) |
| 3P% | −0.00170 (−0.0045, 0.0011) | −0.00181 (−0.0047, 0.0010) |
| FTA/100 | −0.0135 (−0.2296, 0.2042) | −0.1901 (−0.4158, 0.0282) |
| Offensive rebounds/100 | −0.0984 (−0.2364, 0.0389) | −0.1554 (−0.2839, −0.0353) |

Mean simulated/real points per 100 are **114.359 / 113.664**, and FTA per 100 **23.556 / 22.325**.
These are paired observational comparisons, not causal attributions; intervals that include zero are inconclusive,
and component comparisons are exploratory. Team scores and player-box components have different accounting
definitions. The model conditions on actual participants. No final-season outcome or new model was used.

**Rejected-variant scoring decomposition** (`analysis/experiments/20261122_a1_s03_variant_components.json`): on
the same 200 F4 games against the original shared-pool control, mean variant-minus-control total is **+0.996 / +0.893 /
+0.411** points for v1.4c/e/f (95% game-cluster intervals **+0.768 to +1.226 / +0.676 to +1.120 / +0.173 to
+0.656**). The exact two-point / three-point / remaining-score terms are **+0.565 / +0.698 / −0.266**,
**+0.747 / +0.496 / −0.350**, and **−0.126 / +0.749 / −0.212** points per game, respectively. Their FTA changes are
**−0.275 / −0.350 / −0.179**, and OREB changes **−0.029 / +0.042 / +0.024**. A symmetric algebraic
possessions/points-per-possession split assigns **−0.044 / −0.091 / +0.073** points to the pace term and
**+1.040 / +0.983 / +0.337** to the efficiency term. The score residual is reconstructed, not a stored FTM outcome;
the model-version streams differ. These identities describe what moved, not which mechanism caused it.

**Teacher-forced versus free-running flow** (`analysis/experiments/20261122_a1_s03_flow_comparison.json`;
independent accounting `analysis/experiments/20261122_a1_s03_flow_fixed200_accounting.json`): the matched
1,000-world control reproduced **18,600** original game and **95,612** original player values, and all **17**
fitted-model hashes. The independent audit checked **86,920** player-period values, **6,384** complete-roster
team-quarter/component sums, **400** recorded lineup-tick sets and **800** clock values; maximum difference was
**2.84e-14**. One simulated roster player lacks box output, so that one team-side is excluded from independent
player-sum accounting. The teacher/free player join contains **4,345** common player-games and one unmatched on
each side.

On these 200 games, the teacher-forced opponent-defence points/100 loading error is **−1.017** versus **−1.008**
free-running; the paired free-minus-teacher error change is **+0.009** (95% **−0.195 to +0.211**). Thus the
observed defence-loading shortfall is already present in conditional replay; the incremental flow contrast is
inconclusive, not proof rotations are irrelevant. Mean free-minus-recorded segment count is **+0.977** per game
(95% **−0.484 to +2.392**). Before foul-out replacements, scheduled fives match all five recorded players at
**10.34%** of valid regulation tick-worlds and match **3.13/5** slots on average. Among common player-games,
starters' free-running minutes average **+0.669** (95% **+0.298 to +1.037**) versus actual and bench minutes
**−0.361** (**−0.601 to −0.105**); absolute errors average **4.19 / 5.36 minutes**. Actual-event replay uses
event-filtered actuals, whereas free-running uses official/player-box outcomes; game state, clock and lineups
change together. These comparisons locate a descriptive bottleneck, not a causal defence attribution or a
pre-game availability forecast.

**Player-profile spread** (`analysis/experiments/20261122_a1_s03_profile_spread.json`): among **35,413** fixed-panel
shots, **378** actors are absent from the recorded offensive five; these remain identifiable shooters for the
descriptive player profile, but their actor inputs are missing in the cached node. One invalid defensive five is
excluded, leaving **177,060** on-court defender-shot exposures. The pre-specified 112/88-game temporal split requires
15 shots and 3 games per half per player/zone, weighted by the lesser half's exposure count. For **246** rim-exposed
defenders, the pre-game profile variance is **0.000465** versus cross-half observed-rate covariance **0.000983**; for
**69** above-break-three shooters, the corresponding values are **0.000275 / 0.000635**. These quantities are not
causal: five defenders share each shot, lineup/teammate/opponent and shot-selection effects are unadjusted, profile
averages change during the panel, and the same early outcomes can inform later pre-game profiles. Mid-range and corner
shooter cohorts have only **3 / 2** qualifying players; their observed covariance is not reliable. No negative
covariance is clamped.

**Actual-shot node trace** (`analysis/experiments/20261122_a1_s03_shot_trace.json`): all **35,413** rows align on
game, date, period, zone, shot result, margin, clock, coordinates and seven actor-profile fields; the cache signature
equals the saved F4 model's training signature. The model was scored with training-window distance bands and its
original fitted parameters, conditional on actual shot/zone. Across **200 games / 526 shooters**, mean predicted make
is **47.63%** versus **47.45%** observed (binary log loss **0.6437**, Brier **0.2265**). For rim shots, the
assignment-weighted matchup-profile Q4−Q1 observed make-rate difference is **6.66 pp**, versus **3.65 pp** in
predictions; their **3.01 pp** gap has a post hoc, paired game-bootstrap 95% interval **0.25–5.73 pp**. This is
unadjusted and one of many exploratory contrasts, not evidence that a specific defender caused the gap. Above the
break, the shooter-profile Q4−Q1 gap is **0.55 pp observed / 3.06 pp predicted**; its 95% observed-minus-predicted
interval is **−5.01 to −0.01 pp**, also exploratory. Within-zone bin cutpoints use input values only. The **378**
unknown actor-profile rows are counted, not filled; defender effective exposure is the mean of a valid five, not an
on-ball attribution. Original source publication/revision timing remains unproven.

**Falsifiable next mechanisms:** (1) the rim matchup quartile gap and defence-loading shortfall already present in
teacher forcing motivate testing whether the existing matchup signal is under-expressed by the shot node, using a
training-only, level-preserving calibration; held-out loss and player-first engine comparisons can disconfirm it.
(2) Rim defender cross-half covariance above profile variance and the independently audited tracking-date
coverage motivate a separately isolated lagged tracking-defence increment; overlapping five-player exposures,
selection and unknown historical publication timing make its value uncertain. Missing/unsafe joins, no
incremental fold gain or failed player/team gates disconfirm promotion. Both protocols are frozen in
TRAINING_PLAN §8; neither is an attribution of the observed error to an individual defender.
