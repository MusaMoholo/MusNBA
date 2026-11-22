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
2026-27 final test is untouched.

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
