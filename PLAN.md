# MusNBA — game plan and progress

Updated **19 November 2026**. The single record of scope, progress and decisions. Every agent updates it at
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
                 → projection (placeholder today; the engine later) → data/snapshots/<D> → views → serve / export → PWA
HISTORY + MODEL  sportsdataverse ESPN season files → history (+ plays: one schema) → possessions (segments)
                 → rotations (stints, windows) → features (point-in-time profiles) → nodes (datasets)
                 → train (LightGBM per decision, rolling folds) → [M6] engine → [M9] replaces the placeholder
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
| 2 | Possession engine (data → models → engine → backtest) | `█████░░░░░` **M1–M4 done · M5 in progress** |
| 3 | Evaluation and nightly feedback (Forecast Lab view, refit cadence) | not started |
| 4 | Season on the engine: pathway calibration, availability, tiebreakers, play-in, Cup, what-ifs | not started |
| 5 | Polish: hosting, iPhone acceptance, watch-a-sim, more views | not started |

## 6. Phase 2 milestones — the current work

Design: [ENGINE_PLAN.md](ENGINE_PLAN.md) (decisions D1–D20). Training: [TRAINING_PLAN.md](TRAINING_PLAN.md).
Do them in this order; each ends with its checks passing and a checkpoint (AGENTS.md).

| # | Milestone | Status | Done when | Output |
|---|---|---|---|---|
| M1 | History ingest, one play schema | ✅ | Seasons reconcile with box scores | `plays.py`, `history.py` |
| M2 | Segments (possessions) | ✅ | Points, clock, alternation, lineups, possessions reconcile | `possessions.py` |
| M3 | Rotations + replay baseline | ✅ | Stints reconcile; replay backtest recorded | `rotations.py` |
| M4 | Profiles + harness + baselines | ✅ core | Point-in-time profiles; baselines on folds | `features.py`, `evaluate.py` |
| M5 | LightGBM per decision (15 nodes, D20) | ◐ **v1 done — every node ≥ baseline on every fold; tuning, calibration by period, persistence next** | Every node ≥ its best baseline on every fold, well calibrated (ECE ≤ baseline); per-node choice recorded; models persisted | `nodes.py`, `train.py` |
| M6a | Aggregation test with real rotations | ☐ | Replayed held-out games: player box-score bias ≈ 0 by role tier, 80% coverage | (to build) |
| M6 | Engine v1 (replay rotations) | ☐ | 10k sims per game in today's output contract | (to build) |
| M7 | Target-aware substitution model | ☐ | Minutes MAE < 5.2 and 10–90% coverage ≈ 80% (beats replay v0) | (to build) |
| M8 | Per-player form + end-game checks | ☐ | Variance and overtime rate (5.4%) calibrated | (to build) |
| M9 | Walk-forward backtest → switch the app | ☐ | Beats `baseline-v1` on game and player CRPS | (to build) |
| M10 | Watch-a-sim view | ☐ | Replays render | (to build) |
| M11 | Availability model | ☐ | Simulated games missed match history | (to build) |
| M12 | Season pathway calibration | ☐ | Dispersion ≈ 1.0, persistence matches | (to build) |

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
| `analysis/experiments/<UTC>_<name>.json` | Every experiment run: configuration, folds, per-node metrics |
| `data/snapshots/<D>/` | Immutable projections for slate D (meta, games, season, stats) |
| `data/views/api/**.json` | API-ready presentation; rebuildable without simulation |
| `MusNBA.musnba.gz` | gzip NDJSON bundle for the PWA |

## 9. Open decisions for the owner

1. NBA Stats API via `nba_api` (browser-style headers) — allow, or stay on ESPN only?
2. Hosting the PWA: the repo is **private** (`MusaMoholo/MusNBA`, created 19 Nov); GitHub Pages needs a public repo
   or a paid plan — decide when the phone app is ready. App name MusNBA.
3. iPhone acceptance of the PWA.

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

