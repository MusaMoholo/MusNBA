# MusNBA — game plan and progress

Updated **20 November 2026 (00:xx UK, end of the 19 Nov session)**. The single record of scope, progress and decisions. Every agent updates it at
every checkpoint (AGENTS.md § Checkpoint protocol). New here? Read [AGENTS.md](AGENTS.md) first, then
[HANDOFF_NEXT.md](HANDOFF_NEXT.md) — it says exactly what to do next.

## 1. Goal

A local-first NBA simulator PWA, sibling to the owner's MusSim football app (`../Football`):

- **Today**: the slate. Tap a game for projected team and player outcomes — win %, team/total/spread lines, quarter
  and half lines, both lineups with each player's projected box score; tap a player for his full distributions.
- **Every projection = 10,000 simulated games**, possession by possession on a running game clock (2K-style), so
  quarter, half, game and player outcomes all come from the same simulated events.
- **Season**: 10,000 universes, each playing every remaining game once → standings, seeds, play-in/playoff odds.
- **Feedback loop**: real results enter nightly; features update nightly, models refit weekly.
- Lineup-sensitive and game-state-aware; coaching tendencies learned from data, not hand-labelled.

**The daily flow — two engines (owner, 20 Nov; ENGINE_PLAN D26).** On any date D:
1. **Result** every game played before D.
2. **Play-by-play engine** — today's and tomorrow's games (if neither day has games, the next slate), possession by
   possession, with player profiles, form, roles, rotations and injuries carried over from every game before D.
3. **Team engine** — every later game, as MusSim: each world carries its own offensive and defensive rating per team,
   starting from today's estimate (plus its uncertainty), taking in that world's play-by-play results first, then
   updating after every simulated game in date order. March games use the ratings each world's own path produced —
   never today's ratings frozen.
4. **Season** outputs are counts over the worlds.

Each chunk of work should move one or both engines closer to a state the owner trusts against real outcomes — the
play-by-play engine by the backtest (M9), the team engine by the walk-forward season test (M12).

## 2. Principles (carried over from MusSim)

| Principle | How it applies here |
|---|---|
| Laptop pipeline, static PWA | Python collects, fits and simulates; phones browse imported results |
| Data-free shell | The hosted app has no data; data arrives as a `.musnba.gz` import from iCloud Drive |
| Serving never computes | `serve.py`, views and the PWA never fetch providers, fit or simulate |
| Retain raw responses | Provider responses kept gzip under `data/raw/`; finals immutable; history files with a sha256 manifest |
| Cutoff-safe | A snapshot for date D, and every training feature for a game on D, uses only games before D |
| Deterministic sims | Seeded per (model, date, game); identical inputs give identical outputs |
| Honest unknowns | Missing stays missing; placeholders say so; failed experiments are recorded |
| Measured choices | Every model choice decided on rolling validation folds; the final test stays untouched |
| Lean dependencies | NumPy, pandas, pyarrow, LightGBM — nothing else without a reason recorded here |
| Design language | MusSim tokens, panels and heat cells; both themes; 1440/960/390 widths; 44px touch targets |

## 3. Architecture

```
LIVE (nightly)   ESPN site API → fetch_espn → data/raw/espn → master_fixtures, box_scores, pbp
                 → engine v1.1 (default, D22–D24: today + tomorrow; placeholder for backfills) → data/snapshots/<D> → views → serve / export → PWA
HISTORY + MODEL  sportsdataverse ESPN season files → history (+ plays: one schema) → possessions (segments)
                 → rotations (stints, windows) → features (point-in-time profiles) → nodes (datasets)
                 → train (LightGBM per decision, rolling folds) → models/v1 → engine.py (M6) → [M9] backtest
```

Slates are US Eastern game dates; tip-offs show UK time with ET alongside.

## 4. Data sources

| Source | Use | Status |
|---|---|---|
| ESPN site API (no key) | Live: schedules, rosters, injuries, box scores, play-by-play with athlete ids, shot x/y, substitutions | In use (unofficial; adapter + raw retention) |
| sportsdataverse `sportsdataverse-data` releases (hoopR) | History 2022-23 → 2025-26: ESPN play-by-play and player box scores, same ids | In use (`scripts/history.py`) |
| NBA Stats / CDN via `nba_api` | Richer: tracking, play types | **Owner decision open** (needs browser-style headers, blocked here) |
| ESPN `pickcenter` lines | Benchmark only (D8) | Retained in raw summaries |
| Basketball-Reference | Spot checks | Not a pipeline source |

## 5. Phases

| # | Phase | Progress |
|---|---|---|
| 0 | Discovery, data probe, plan | `██████████` done |
| 1 | App shell, season stats, placeholder projections | `██████████` done — owner checks pending (iPhone, hosting) |
| 1b | Per-period Game Centre (owner spec), play-by-play parser, quarter-aware placeholder | `██████████` done |
| 2 | Possession engine (data → models → engine → backtest) | `███████░░░` **M1–M5b, M6a done · engine v1.1 is the app's default (D22–D24), inputs rebuilt nightly (D26) · first backtest run (M9): defence under-expressed — the next fix** |
| 3 | Evaluation and nightly feedback (Forecast Lab view, refit cadence) | not started |
| 4 | Season on the engine: pathway calibration, availability, tiebreakers, play-in, Cup, what-ifs | `██░░░░░░░░` **team pathway v1 in the app (D25): per-world ratings, engine worlds for today + tomorrow; walk-forward calibration first cut (M12)** |
| 5 | Polish: hosting, iPhone acceptance, watch-a-sim, more views | not started |

## 6. Phase 2 milestones — the current work

Design: [ENGINE_PLAN.md](ENGINE_PLAN.md) (decisions D1–D25). Training: [TRAINING_PLAN.md](TRAINING_PLAN.md).
Do them in this order; each ends with its checks passing and a checkpoint (AGENTS.md).

| # | Milestone | Status | Done when | Output |
|---|---|---|---|---|
| M1 | History ingest, one play schema | ✅ | Seasons reconcile with box scores | `plays.py`, `history.py` |
| M2 | Segments (possessions) | ✅ | Points, clock, alternation, lineups, possessions reconcile | `possessions.py` |
| M3 | Rotations + replay baseline | ✅ | Stints reconcile; replay backtest recorded | `rotations.py` |
| M4 | Profiles + harness + baselines | ✅ core | Point-in-time profiles; baselines on folds | `features.py`, `evaluate.py` |
| M5 | LightGBM per decision (16 nodes, D20 + D21) | ✅ **v1 tuned, validated, persisted, final test scored once** — every node ≥ its best baseline on every fold and on the final test; settings `models/v1.json`; FINDINGS §3h–§3h′ | Every node ≥ its best baseline on every fold, well calibrated; per-node choice recorded; models persisted | `nodes.py`, `train.py`, `compare.py`, `calibration.py` |
| M5b | Adapter parity: live ESPN v hoopR history | ✅ **adapters agree** (5 games, identical segments); ESPN's 2026-27 feed stamps every rebound at the miss's clock → one convention for all seasons (D23); timing distributions now match; foul/turnover/jump-ball shifts are real 2026-27 changes (FINDINGS §3k) | Same game through both adapters gives the same segments; season distributions match | `plays.py`, `possessions.py`, `parity.py` |
| M6a | Aggregation test with real rotations | ✅ **v1.1 on all 766 F4 games** (2026-27-style inputs): player bias ≤ ±1.5% for points/rebounds/assists/threes/steals/turnovers, CRPS lower than v1 on every stat but blocks, coverage 77–80% (FINDINGS §3k). Earlier v1 **gate met on all 766 F4 games** (player stats within ±1.3% for points/rebounds/assists/threes in every tier, coverage 77–81%, CRPS +6–11%; earlier 300-game run: team total −0.5%, coverage 77–83%); fouls traced to the in-season decline (day of season added); and-ones +5%, fouled-on-a-three −24% to trace) | Replayed held-out games: player box-score bias ≈ 0 by role tier, 80% coverage | `aggregate.py` |
| M6 | Engine (replay rotations) | ◐ **v1.1 is the app's default (D22, D23), today and tomorrow (D24)** — `nightly.py` (chip "Engine v1.1"; `--placeholder` opts out, `--ahead N`): 2,000 worlds per game, ~20 s per game; strong offences under-expressed, spread too narrow | 10k sims per game in today's output contract | `engine.py` |
| M7 | Target-aware substitution model | ☐ | Minutes MAE < 5.2 and 10–90% coverage ≈ 80% (beats replay v0) | (to build) |
| M8 | Per-player form + end-game checks | ☐ | Variance and overtime rate (5.4%) calibrated | (to build) |
| M9 | Walk-forward backtest (engine on past games) | ◐ **first run (20 Nov, 200 F4 games)**: pace right (+0.2%), totals +2.7, margins half-sized (slope 1.45), defence expressed at ~25% of its real effect, stars' minutes +6.5%, totals too narrow (coverage 65%); **the team-rating model beats the engine on every game measure** (margin CRPS 9.32 v 9.64, win log loss 0.558 v 0.592) — FINDINGS §3o | Measures the engine (the floor, D22) and every candidate on game and player CRPS, win calibration and realism v the team-rating model and the current engine; a candidate replaces the engine only if better | `backtest.py` |
| M10 | Watch-a-sim view (owner, 20 Nov: nba.com-style play-by-play list first, then visual play-through) | ☐ | A saved world's events list and replay in the Game Centre, phone and desktop | `engine.py` event log, views, `game.mjs` |
| M11 | Availability model | ☐ | Simulated games missed match history | (to build) |
| M12 | Season pathway calibration | ◐ **first cut (20 Nov): team pathway v1 in the app** — walk-forward 2022-26 (480 team-starts): dispersion 1.00 (fixed probabilities 1.53), 10–90% coverage 84% (65%), CRPS −4% in every held-out season; still wide in November (0.84) and surprises fade with the date (sim 0.52 → 0.18 v real 0.40 flat) | Dispersion ≈ 1.0 **at every start date**, persistence matches | `pathway.py`, `season_backtest.py` |

## 7. Phase 1 record (done)

- [x] Collection, master fixtures, box scores, cutoff-safe stats, placeholder engine (`baseline-v1`), snapshots, views
- [x] Local server (:8766); app: Today, Game Centre (bezel, Q1–FG, Player/Team, Matchup, player sheet), Standings
      (forecast, seeds, ratings), Teams, Players, Search; static PWA with checksum-verified import and offline cache
- [x] Verification: smoke, browser (39 checks over 18 views × 3 widths × 2 themes), PWA import/offline (8 checks)
- [ ] Owner: real iPhone install and import; GitHub repo/Pages path; first `nightly_musnba.py` run to iCloud

## 8. Contracts

| Artifact | Contract |
|---|---|
| `data/raw/espn/final/<game>.json.gz` | Final-game summary; written once |
| `data/raw/espn/runs/<UTC>/…` | Volatile responses per collection run |
| `data/raw/hoopr/*.parquet` + `manifest.json` | Unmodified history files with url, bytes, sha256 |
| `data/master_fixtures.csv` | One row per scheduled game (live season) |
| `data/derived/history/<season>/segments.parquet` | One row per segment (M2); `game_ok` marks reconciled games |
| `data/derived/history/<season>/{stints,windows,subs,on_court}.parquet` | Rotations (M3) |
| `data/derived/features/pregame.parquet` | One row per player-game: profile as of tip-off (M4) |
| `analysis/experiments/<UTC>_<name>.json` | Every experiment run: configuration, folds, per-node metrics, commit |
| `data/derived/experiments/<UTC>_<name>.npz` | Per-row held-out log losses of a run (paired comparisons) |
| `data/derived/features/team_pregame.parquet` | One row per team-game: team style as of tip-off, rest, day of season |
| `data/derived/nodes/<key>/<node>.npz` | Cached datasets per decision (folder = hash of code + inputs) |
| `models/<version>.json` | A model version's settings and the fold run that validated it (in git) |
| `data/models/<version>/` | Fitted LightGBM files + `config.json` (inputs, temperatures, final-test scores) |
| `data/snapshots/<D>/` | Immutable projections for slate D (meta, games, season, stats) |
| `data/views/api/**.json` | API-ready presentation; rebuildable without simulation |
| `MusNBA.musnba.gz` | gzip NDJSON bundle for the PWA |

## 9. Open decisions for the owner

1. NBA Stats API via `nba_api` (browser-style headers) — allow, or stay on ESPN only?
2. Hosting the PWA: the repo is **private** (`MusaMoholo/MusNBA`, created 19 Nov); GitHub Pages needs a public repo
   or a paid plan — decide when the phone app is ready. App name MusNBA.
3. iPhone acceptance of the PWA.
4. ~~Player heights/weights~~ — **owner (19 Nov): needed** ("size and defence are important"): a polite ESPN athlete
   fetch (~1,000 players, one request each) for height and weight, then **archetype priors** — players clustered by
   role, style and size; every rate shrinks toward the player's archetype instead of his position group; rookies
   start from the archetype matched by position, size and draft slot (D5: no college data).

5. **Owner (19 Nov, late):** the engine projects **today and tomorrow, always** (D24, replaces the seven-day window), and the
   season sim should then play every later game with **per-world team ratings, MusSim-style** (D25) — left as future work
   at the owner's request; **built 20 Nov** (team pathway v1, D25–D27).

6. ~~Engine v team model for today's win %~~ — **owner (20 Nov, D28): players first.** The engine stays the default; team results follow from perfecting player outcomes (minutes, performance, defenders faced); the team model is only a yardstick.

### 9b. Dashboard UX backlog (owner, 20 Nov) — headliners for chunks that cannot improve an engine

1. **Watch a sim, 2K-style** (M10, extends D9): a saved world played through time on an aerial view of the court — shots
   placed where they were taken (zone, distance band, side), makes and misses, the clock running, the box score filling;
   after the nba.com-style play-by-play list. Needs the engine's event log (five worlds per game) and shot coordinates
   sampled within the band for display.
2. **More depth on game outcomes**: richer, more sensitive graphs of player and team outcome distributions per game
   (lines, ladders, joint outcomes, how a line moves with a player in or out).
3. **Competition tabs**: NBA regular season · **NBA Cup** · **NBA playoffs** — the playoffs tab seeds the bracket from the
   standings as they are expected to finish (per simulated season) and plays the play-in and every round per world,
   MusSim cup-style (bracket probabilities by round).

### 9c. Realism sweep (owner, 19 Nov) — gaps, in priority order (HANDOFF next actions)

1. ~~Live v history adapter skew~~ — M5b done: ESPN's 2026-27 rebound stamp; one convention (D23); v1.1 promoted.
2. Minutes: target-aware substitutions (blowouts, foul trouble, fatigue, closing lineups) — M7; the biggest risk.
3. **Size and archetype priors** (owner: low-sample players borrow from similar players' profiles) — heights/weights fetched
   (935 players); first ablation negative (low-sample players do not gain; FINDINGS §3l); location node gains — next test.
4. **On-court defensive impact** — **the top engine fix (backtest 20 Nov: the opponent's defence is expressed at ~25% of its real
   effect, FINDINGS §3o)**; first ablation negative at node level (FINDINGS §3l; helps location only) per player (opponents' shooting by zone and turnover rate while he is on the floor,
   shrunk) — positional defenders who force misses without blocks are invisible today; TRAINING_PLAN §2.1 lists it.
5. Timeouts (after-timeout plays, late-game advance), end-of-period heaves, technical/flagrant free throws,
   goaltending, lane violations — rules or small nodes in M6/M8.
6. End-game behaviour (deliberate fouling, two-for-ones, last-shot holds), per-world form, overtime rate — M8.
7. Nearest-defender and other tracking data need the NBA Stats API (decision 1 above).

## 10. Log

- **19 Nov 2026** — Studied MusSim. Probed sources: ESPN site API works with plain requests; NBA CDN returns 403.
  Owner: app shell first, play-by-play sim later.
- **19 Nov 2026** — Phase 1 shipped (collection, placeholder engine, snapshots, views, server, app, PWA). Fixed: a
  loop-closure bug, a `conf` field collision, phone screenshots needing device emulation. Owner asked for this
  detailed plan file and localhost-first development.
- **19 Nov 2026** — Phase 1b: owner's Game Centre spec (bezel, Q1–FG dropdown, Player/Team, Matchup). `pbp.py`
  reconciles after measured fixes (missed heaves are not FGA; offensive fouls often only as turnover records;
  shot-clock/8-second violations are team turnovers; technical fouls/timeouts do not mark quarter starters). A
  "fouled missed shot" rule was tried and reverted (worse). Model choice: LightGBM (Jev is proprietary).
- **19 Nov 2026** — Engine design rounds 1–5 with the owner → ENGINE_PLAN v6: clock-driven segments, target-aware
  substitutions, shared models with quarter as an input, per-player form, two horizons, MusSim-style per-world
  season pathway, 10k universes, 60-minute nightly budget, weekly refits.
- **19 Nov 2026** — **M1**: one play schema; history 2022-23 → 2025-26 reconciles (points 0.05–0.16%, minutes
  0.58–0.97% of player-games off). Blank `points_attempted` in 2022-24 inferred (99.96% agreement where known).
- **19 Nov 2026** — **M2**: 1.25M segments; identities pass per season; late-logged plays ordered by clock; ~2% of
  games flagged (feed gaps) and excluded from training; realism matches NBA norms.
- **19 Nov 2026** — **M3**: stints reconcile (minutes 99.6–99.95%); substitutions rise every season (27.2 → 34.5);
  replay v0: minutes MAE 5.17 for rotation players but 60% interval coverage (needs game state → M7).
- **19 Nov 2026** — TRAINING_PLAN v1 → v2 (owner: maximise accuracy, rich data, experiment freely): four rolling
  folds, untouched final test, ablations, experiment log with negative results.
- **19 Nov 2026** — Owner: playoffs/Cup differ mainly by rotations → one model with game type (D19); history now
  includes playoffs and play-in (5,290 games). Measured: playoff starters +3.0 min, pace −4%, possessions longer
  at every start type (+0.4–0.6 s).
- **19 Nov 2026** — **M4 core**: point-in-time profiles (116k player-games; usage r = 0.70 with the game, minutes 0.79);
  harness and baselines on folds F1–F4.
- **19 Nov 2026** — Owner left the number of steps to the data → **D20**: fifteen decisions in four stages (all ≥ 50k
  rows). M5 started: datasets for all 15 nodes; first fold-F4 runs: blocked +6.5% over the best baseline, turnover
  type +4.9%, stealer and free throws level (FT attempt-order features then added). Full 15 × 4 run launched.
- **19 Nov 2026** — Owner asked for an honest read (placeholder: Brunson 20.6 points v 27.0 actual). Diagnosis:
  placeholder minutes spread too thin (29.3 v 34.2) and team-total-then-split scoring; the engine removes both by
  design. Added **M6a** (real-rotation aggregation test). Owner: docs must let a new agent take over at every
  checkpoint — AGENTS/HANDOFF rewritten as a prescriptive hand-over; checkpoint protocol added.
- **19 Nov 2026** — **M5 v1**: all 15 nodes beat or match their best baseline on every fold (mean gains: event 15.1%,
  assisted 25.5%, rebound 8.0%, blocked 6.4%, what 5.3%, turnover type 4.8%, assister 2.4%, shot result 2.1%, who 2.1%,
  fouler 1.6%, rebounder 1.5%, duration 1.3%, blocker 1.2%, free throw 0.1%, stealer 0.1%); ECE ≤ 0.016. Caught and fixed
  a label leak in the free-throw dataset (attempt order); real effect: second FT 80.4% v first 75.6%.
- **19 Nov 2026** — Git: repository initialised with the owner's personal identity (as MusSim), first commit `3291ffc`,
  pushed to the new **private** GitHub repo `MusaMoholo/MusNBA`. Owner's standing rule: agents commit and push at every
  checkpoint (AGENTS.md §4–§5).
- **19 Nov 2026** — **M5 tuning** (≈1,000 fits, paired game-clustered comparisons with a seed-noise floor): no sample-weight
  decay (every half-life worse; ½ season +4.5 nats per game); shot distance worth 3.1 nats per game → **D21: location node**
  (16 decisions) and team turnovers as an event class; team style kept for duration/what/shot result (−1.3); in-game
  form kept except free throws (no hot hand in shot making); schedule, clutch, playoff weights, recalibration and profile
  decay variants not better; fouls fall through every season → day of season for event and turnover type. All-Star
  games found in history and excluded. **v1** validated on folds (every node ≥ baseline on every fold, ECE ≤ 0.012),
  persisted (`data/models/v1/`, 44 MB) and **final test scored once**: every node above its baselines (event +11.8%,
  assisted +22.7%, rebound +7.2%, blocked +6.2%, what +4.4%). Final-test calibration exposed a **live-v-history adapter
  skew** (M5b, next).
- **19 Nov 2026** — **M6a** (`aggregate.py`): 300 F4 games × 10,000 worlds with real lineups and clock — team total
  228.5 v 229.5, player points/rebounds/assists/threes within ±2% for starters and bench, 10–90% coverage 77–83%,
  CRPS 7–12% better than recent averages on every stat. Fouls +5% traced (event accounting) to the in-season foul
  decline; stars run 2–5% hot on points, free throws, turnovers and threes (to trace).
- **19 Nov 2026** — Owner: put the current model in the dashboard. **Engine v1 preview** (`engine.py`): the v1 nodes
  played forward possession by possession (sampled durations, replayed rotations, per-world score, fouls, foul-outs,
  in-game counts), packaged in the app contract (`projection.package`); `nightly.py --engine` builds today's slate
  with it (placeholder kept beside it in `games_placeholder.json`); the app labels it "Engine v1 · preview". Today's
  four games: plausible box scores (114 points, 240.6 team minutes, 91 FGA, 22 FTA); pace ≈ 3% high and spread too
  narrow (OT 2.2%) — the M8 work. Owner realism sweep recorded (PLAN §9): size + archetype priors (owner: needed), on-court
  defensive impact, substitutions (M7) as the biggest remaining risk.
- **19 Nov 2026** — M6a full run (766 F4 games): gate confirmed. Engine clock rules from data: post-action game time
  (8.4% of the clock, mostly 2.4 s from a miss to its rebound), whole-second durations within bins, end-of-period
  segments from real ones; the first two errors had cancelled (pace +3% → −5% → ≈ −2.5% after all three). Owner:
  scores too high on the first preview — they were (+1.5%, from pace); now slightly low, strong offences under-expressed.
- **19 Nov 2026** — **Owner (D22): engine v1 is the dashboard default and the floor** — later changes replace it only when
  measured better. `nightly.py` now uses the engine by default (`--placeholder` opts out); the chip reads "Engine v1";
  backfills stay on the placeholder (cutoff safety). Docs brought up to date for a hand-over to a new agent.
- **19 Nov 2026 (late)** — **M5b**: the adapters agree (five 2025-26 games re-fetched: identical segments); ESPN's 2026-27 feed
  stamps every rebound at the miss's clock (100% v 7–12% in every month since 2022), moving ~2.6 s of ball flight into
  the next segment and making every team look 3–8% slower in team style. One convention for every season (**D23**):
  on live-style held-out rows v1 is worse on 12 of 16 nodes (chain +34.1 nats per game; reproduces its final-test
  miscalibration) and in M6a (threes +7.4%, steals +9.6%, defensive fouls −20.5% → v1.1 +1.0%, +0.8%, −1.0%).
  **v1.1 promoted** (v1's settings on the new data; final test scored once) and the engine serves it for **today and
  tomorrow (D24, owner)**: pace fixed (≈ 97 → ≈ 101 possessions per team on the 19 Nov slate; points ≈ 108 → ≈ 115).
  v1.1 final test: duration ECE 0.002 (v1 0.014), event 0.009 (v1 0.022). Foul, turnover and held-ball shifts in 2026-27 are real. Heights/weights for 935 players;
  archetype priors and on-court defence: first ablations negative (only the location node gains). Owner asked for a
  MusSim-style per-world rating pathway beyond tomorrow (D25) — next session.
- **20 Nov 2026** — Owner check against bet365/DraftKings (FINDINGS §3m): v1.1 totals run ≈ +8 points above the market on
  the 19 Nov slate (NYK–MIN 231 v 216.5) and its spreads are about half the market's — efficiency +1.7%, and matchup
  effects (totals and margins) under-expressed. Owner: the market is broadly rational (D8 note; compare with closing
  lines). Owner request: the Game Centre should show a saved sim's play-by-play like nba.com, then a visual play-through
  (D9, M10). Both queued in HANDOFF for the next agent.
- **20 Nov 2026** — Owner: the goal is a ground-up simulation as accurate as possible against real outcomes, not betting;
  the market is a reference. Measured: DraftKings' lines are unbiased against 2026-27 results (222 games: totals −0.6 ±
  1.2, margin slope 1.09), so v1.1's high totals and half-sized spreads are engine errors to fix (HANDOFF item 3).
- **20 Nov 2026** — Owner: the product is two engines in one daily flow (**D26**); each chunk has one or two headliners that move them toward trust; every chunk ends with the dashboard on the newest systems; UX backlog §9b. **Nightly input rebuild:** segments → rotations → profiles from every final before today (~50 s; 4 new finals → engine inputs changed), next slate when today and tomorrow are empty. **Team pathway v1 (D25) in the app:** per-world offence/defence ratings, engine worlds for today + tomorrow, updates on the points surprise (D27: a good loss keeps ratings); walk-forward 2022-26: the old fixed-probability season sim had dispersion 1.53 and coverage 65%, v1 1.00 and 84%, CRPS −4% in every held-out season (still wide in November). **First engine backtest (M9, 200 F4 games):** pace +0.2%, totals +2.7, margin slope 1.45, defence expressed at ~25% of its real effect (offence ~70%), stars' minutes +6.5%; the team-rating model beats the engine on margin CRPS (9.32 v 9.64), totals and win log loss. Smoke 80/80, browser 38/38.
- **20 Nov 2026** — Owner (**D28**): the guiding light is player outcomes — a team's results are the aggregation of its players, so minutes, performance and the defence each player faces come first and team results short and long term follow; the engine stays the dashboard default; the team-rating model is a yardstick only.
