# Handoff — state and next actions

Updated **20 November 2026, ~00:45 UK** (checkpoint: M5b done, engine **v1.1** promoted, today + tomorrow on the engine,
owner's market and play-by-play notes recorded). Read [AGENTS.md](AGENTS.md) first. Rewrite this file at every
checkpoint, then commit and push; whoever reads it next may be a new agent.

**Git:** private repo `MusaMoholo/MusNBA` (`main`). This session: `5ec598f` (M5b + v1.1 + D24) and a docs follow-up
commit after it (owner's market check and play-by-play request) — `git log --oneline -3`. **Nothing runs in the
background.** The owner keeps `scripts/serve.py` on :8766 open — leave it; use :8767 for your own checks.

## State

**What changed this session (FINDINGS §3k–§3l, ENGINE_PLAN D23–D25).**
- **M5b done.** The live and history adapters agree (five 2025-26 games re-fetched into `data/raw/espn/parity/`:
  identical segments). The skew was ESPN's 2026-27 feed: every rebound carries the clock of the miss it follows (100% v
  7–12% in every earlier month), so ~2.6 s of ball flight landed in the next segment and every team looked 3–8% slower in
  team style. **D23:** every season now uses that convention (`possessions.py`, default `--rebound-clock miss`); the old
  data is kept for v1 in `data/derived/variants/rebound_feed/` (its `config.json` and `models/v1.json` point there).
- **v1.1 promoted** (D22's test): v1's settings on the new data. On live-style held-out rows v1 is worse on 12 of 16
  nodes (chain +34.1 nats per game, `…224019Z_v1_cross` v `…224019Z_v1.1_folds`) and in M6a (`…235141Z_m6a_v1_cross` v
  `…235148Z_m6a_v1.1`). Fitted files `data/models/v1.1/` (out of git); final test scored once (`…_final_v1.1.json`).
- **Engine serves v1.1 for today and tomorrow (D24, owner).** `nightly.py --ahead 1` (default) also projects tomorrow's
  slate from what is known today; it is rebuilt the next night (the old snapshot archived to `~/Basketball_archive_ops`).
  The app's as-of date stays the newest snapshot dated today or earlier (`views.current_snapshot`). Chip "Engine v1.1".
- **Pace fixed:** on the 19 Nov slate the engine now plays 99.8–102.2 possessions per team (v1: 96–98; the teams' real
  97.5–103.4) and ≈ 115 points per team (v1 ≈ 108; league 113.7). Snapshots 2026-11-19 (4 games, pre-game, the v1
  snapshot archived at `~/Basketball_archive_ops/archive_20261120T000217Z_13033`) and 2026-11-20 (9 games) are engine
  v1.1; browser checks 38/38 on :8767.
- **Season sim unchanged:** later games still use fixed per-game probabilities from team ratings. The owner wants a
  MusSim-style per-world rating pathway (D25) — next actions item 4.
- **Size and defence, first ablations — negative** (FINDINGS §3l): heights/weights for all 935 players
  (`scripts/athletes.py`, `data/derived/athletes.parquet`); archetype priors (k = 10) and on-court defence rates are
  options in `features.py` (`--body --archetypes K --defence`) and optional inputs in `nodes.py` (`@body`, `@defence`);
  neither beats v1.1 overall; both help the **location** node.
- **New tools:** `scripts/parity.py` (adapter/feed parity), `scripts/buckets.py` (paired comparison by the player's sample
  size), `train.py --segments/--train-segments/--train-features` (variants and the paired cross-data test),
  `aggregate.py --name/--train-segments/--train-features`, `scripts/backtest.py` (**written, not yet run**).

**App.** Localhost (`serve.py`, :8766) and the static PWA. Today's and tomorrow's slates come from engine v1.1 (the floor,
D22); backfills use the placeholder `baseline-v1`, saved beside each engine snapshot (`games_placeholder.json`).

**Market check (owner, FINDINGS §3m):** on the 19 Nov slate v1.1 totals run ≈ +8 above DraftKings/bet365 (NYK–MIN 231 v
216.5) and its spreads are about half the market's. The owner treats the market as broadly rational (D8) — item 3.

**Engine realism (still open, FINDINGS §3j):** strong offences under-expressed; outcomes too tightly spread (OT ≈ 3% v
5.4%); v1.1's M6a biases: team turnovers +9.7%, and-ones +6.9%, fouled on a three −28%, total +1.4 points.

**Known gap:** `nightly.py` does not rebuild segments, rotations or features — the engine's profiles stay as of the last
manual rebuild (now: games through 18 Nov). Next actions item 1.

## Next actions (in order — the owner may reorder; items 3–5 are his requests)

1. **Nightly rebuild of engine inputs.** `nightly.py` does not rebuild segments, rotations or features, so the engine's
   profiles stay as of the last manual rebuild (games through 18 Nov). Add current-season `possessions.py` →
   `rotations.py` → `features.py` (≈ 1–2 min) after collection and before the engine. Done when a nightly run after new
   finals changes `engine_inputs_sha256` and smoke's bit-for-bit re-simulation still passes.
2. **Engine backtest (M9 start)** — the yardstick every engine change must beat (D22).
   `.venv/bin/python scripts/backtest.py --config models/v1.1.json --games 200 --worlds 1000 --jobs 4`: fits all 16 fold
   models (`data/models/folds/v1.1_F4_all/`), plays F4 games forward with cutoff-safe inputs and real availability, scores
   team points/total/margin (CRPS, coverage, **slope of real on simulated margin**), possessions and points per possession,
   win calibration, OT, players by tier. **Never executed — expect to debug it first.** No `baseline-v1` comparison on
   history (its snapshots exist only for 2026-27). Add a smoke check for its output once it runs.
3. **Scoring level and matchup expression (owner, FINDINGS §3m).** v1.1 totals ≈ +8 above the market on the 19 Nov slate
   (efficiency +1.7%; matchups under-expressed in totals and margins — spreads about half the market's). (a) Build a
   market benchmark (`scripts/market.py`, evaluation only, D8): closing lines from the final summaries' `pickcenter` v
   each snapshot's engine and placeholder totals/margins, per day, with the line's timestamp; also make
   `fetch_espn.collect` save tomorrow's scoreboard (D24) so pre-game lines are retained. Owner: the market is broadly
   rational; we may differ far from tip-off — judge on closing lines. (b) Use the backtest (item 2) to separate causes:
   free throws and foul classes (M6a: and-ones +6.9%, team turnovers +9.7%), shot mix, end-of-period play, replayed
   rotations (stars' minutes), missing strength signal (strong offences under-expressed: Memphis ≈ 113 per 100 v 117.8).
4. **Season pathway (D25, owner).** In `projection.simulate_season`: universe k plays engine world k (mod the engine's
   worlds) for today's and tomorrow's games — `nightly.py` keeps each engine game's per-world points (`Engine.last.pts`)
   and runs the season sim once with both days; every later game, in date order, draws both scores from that universe's
   own ratings (offensive and defensive rating per team; start = today's shrunk estimate + a draw at its posterior SD
   ≈ 11 / √(games + 8) per 100) and updates both teams by the estimator's own response, 1/(n + 1 + k) with k = 8, to
   the surprise against that universe's expectation (zero on average). Long-range win % = share of universes won (D16).
   Done when smoke passes, a season re-simulates bit-for-bit, and the app labels the gain as uncalibrated. Calibrating the
   gain to real dispersion and persistence is M12 (walk-forward 2022-26, as MusSim's `analysis/calibrate_drift3.py`;
   MusSim's pathway: `../Football/scripts/simulate_season.py`, class `_World`).
5. **Game Centre play-by-play of a saved sim (owner; D9, M10).** (a) Engine: record an event log for five worlds per game
   (deterministic: worlds 0–4) — period, clock, team, players, action (shot zone/band/value and result, assist, block,
   rebound side and player, turnover live/dead and stealer, foul and free throws, substitutions in/out from the replayed
   lineups, period start/end), score after each event — saved beside `games.json` in the snapshot (≈ 450 events × 5
   worlds per game; keep it compact). (b) Views: `api/game/<id>/sim/<k>`. (c) App: a "Play-by-play" segment in the Game
   Centre listing a chosen sim like nba.com (period tabs, clock, team logo, description, running score; each sim labelled
   with its final score), both themes and phone width; then (d) a visual play-through on the running clock (box score
   filling as it plays). Browser checks for the new view.
6. **Location with size/defence:** keep `@body`/`@defence` inputs for the location node only (per-node `drop` in a version
   file) and test against `…224019Z_v1.1_folds`; first run a seed pair for location (its noise floor is 0).
7. **Engine realism:** spread (per-world form, D3/M8; targets total SD 18–19, OT 5.4%); the foul classes (fouled on a
   three −28%).
8. **Refits with 2026-27 data:** the single convention (D23) makes this season's rows usable for training — the 2026-27
   foul and turnover shifts (FINDINGS §3k) can only be learned from them. Design the weekly refit (D11) and its test.
9. Then M7 (target-aware substitutions — the biggest remaining risk) → M8 (form, end-game) → M9 (full backtest).

**Housekeeping before training anything:** the dataset caches in `data/derived/nodes/` are stale (built before D23 or for
ablations); run `nodes.py --prune` then `nodes.py` to rebuild the default (~1 min, ~14 GB). Rows and columns then match
the control run `…224019Z_v1.1_folds`. `data/derived/variants/rebound_miss/` duplicates the canonical data now (it
validated v1.1; safe to delete except `features_arch/`, `features_def/` if ablations are re-run). Fold models in
`data/models/folds/` refit themselves when their key changes.

## How to judge a change (TRAINING_PLAN §7)

```sh
.venv/bin/python scripts/nodes.py                         # dataset cache for the current code + inputs (~1 min, ~14 GB)
.venv/bin/python -u scripts/train.py --name <label> --threads 6 [--drop @team …]     # ~20 min; 2–4 in parallel
.venv/bin/python scripts/compare.py <control> <run> --noise 20261119T190747Z_control 20261119T190747Z_seed8
.venv/bin/python scripts/buckets.py <control> <run> --cache data/derived/nodes/<folder>   # by the player's sample size
.venv/bin/python scripts/calibration.py <run>              # excess ECE by period and margin
```

Control on the current data: `20261119T224019Z_v1.1_folds` (v1.1 = the engine's settings). A change is kept for a node
when its mean change beats −noise with pooled z ≤ −2 and no fold is worse by more than 2 × noise; global changes are also
read on the chain row (nats per game). **A change to how data are built** (like D23) is judged with the paired
cross-data test (`--train-segments default --train-features default`, TRAINING_PLAN §7). Log every run; record wins and
negative results in FINDINGS. Never edit `nodes.py` while runs read a cache built from it.

## File map

| Files | Responsibility |
|---|---|
| `basketball_common.py` | Paths, ET/UK time, conferences/divisions, NBA franchise ids, atomic JSON, archives |
| `scripts/fetch_espn.py` | Live collection: `data/raw/espn/runs/<UTC>/`, finals `data/raw/espn/final/`, logos |
| `scripts/master_fixtures.py`, `scripts/box_scores.py` | Live master fixtures; player/team game logs; player registry |
| `scripts/plays.py` | Canonical game/play schema; adapters for live ESPN and history; shot-value inference |
| `scripts/history.py` | History download (`--fetch`, manifest) and per-season reconciliation → `data/derived/history/<season>/` |
| `scripts/pbp.py` | Per-period player box scores and on-court seconds; lineup helpers |
| `scripts/possessions.py` | Segments (M2); rebound-clock convention (D23, `--rebound-clock`, `--out` for variants) |
| `scripts/parity.py` | M5b: same games through both adapters; Oct–Nov distributions under both conventions |
| `scripts/rotations.py` | Stints, dead-ball windows, substitutions, on-court shares; replay v0 templates (used by the engine) |
| `scripts/athletes.py` | Heights/weights/birth dates (rosters + ESPN athlete endpoint) → `data/derived/athletes.parquet` |
| `scripts/features.py` | Player profiles, team style/schedule, latest state; variants (`--segments`, `--body`, `--archetypes K`, `--defence`) |
| `scripts/evaluate.py` | Folds F1–F4, final-test boundary, M4 baselines; experiment log location |
| `scripts/nodes.py` | Datasets for the 16 decisions; cache (`data/derived/nodes/<hash>/`); optional `@body`/`@defence` inputs |
| `scripts/train.py` | LightGBM per node and fold; `--config` versions; `--final`; variants and cross-data test (`hybrid`) |
| `scripts/compare.py`, `scripts/buckets.py`, `scripts/calibration.py` | Paired comparisons (seed-noise floor; by sample size); calibration |
| `scripts/aggregate.py` | M6a: real segments replayed, every decision sampled, box-score and event accounting |
| `scripts/engine.py` | The engine (serves `ENGINE['version']` = v1.1); clock rules from the version's own segments |
| `scripts/backtest.py` | M9 first cut: fold models + cutoff-safe inputs, games played forward, scored (not yet run) |
| `models/v1.json`, `models/v1.1.json` | Version settings, data locations, validating runs, reasons |
| `scripts/season_stats.py`, `scripts/projection.py` | Live season stats; placeholder `baseline-v1`, season sim, `package()` |
| `scripts/nightly.py`, `scripts/views.py` | Live orchestration (engine today + tomorrow, D24), snapshots, API views |
| `scripts/serve.py`, `scripts/export_musnba.py`, `scripts/nightly_musnba.py` | Local server; static shell + bundle; iCloud export |
| `scripts/webapp/` | The app (ES modules, no build); `modelPill` in `ui.mjs` labels the model |
| `scripts/smoke.py`, `analysis/*.mjs` | 70+ accounting/model checks (fault run must fail); browser and PWA checks |

Data variants: `data/derived/variants/rebound_feed/` (v1's data, feed clocks), `data/derived/variants/rebound_miss/`
(the validated v1.1 data; identical to the canonical data now) with `features_arch/` and `features_def/` (ablations).

## Commands

```sh
git status && git log --oneline -5                                    # start of session; commit + push at checkpoints
.venv/bin/python scripts/smoke.py [--fault]                           # all checks (the fault run must fail)
.venv/bin/python scripts/nightly.py [--offline] [--placeholder] [--ahead N] [--backfill-days N]   # today + tomorrow (engine)
.venv/bin/python scripts/engine.py --game <id> [--worlds 2000]        # one game through the engine
.venv/bin/python scripts/serve.py --port 8767                         # your own review server (owner uses :8766)
node analysis/browser_check.mjs --base http://127.0.0.1:8767          # browser checks, both themes, phone/desktop
.venv/bin/python scripts/possessions.py [--history]                   # segments (M2; D23 convention by default)
.venv/bin/python scripts/rotations.py [--history | --backtest]        # rotations (M3)
.venv/bin/python scripts/features.py [--out DIR …]                    # profiles (M4); variants elsewhere
.venv/bin/python scripts/nodes.py [--segments DIR --features DIR/pregame.parquet | --prune]   # dataset cache
.venv/bin/python scripts/train.py --config models/v1.1.json [--final]   # validate a version / persist + final test once
.venv/bin/python -u scripts/aggregate.py --config models/v1.1.json [--games 300]   # M6a (~50 min for all 766)
.venv/bin/python scripts/parity.py [--fetch]                          # adapter/feed parity
.venv/bin/python scripts/athletes.py [--fetch]                        # player bodies
```

Rebuild order after new data or a parser change: history → possessions (`--history` and current) → rotations
(`--history` and current) → features → nodes → train. The laptop: 14 cores, 48 GB; a run from the cache needs ~2–4 GB, a
chain build ~14 GB; `data/derived/nodes/` holds ~8 GB per cache folder (`nodes.py --prune` clears all but the default).
