# Handoff — state and next actions

Updated **20 November 2026, ~00:30 UK** (checkpoint: M5b done, engine **v1.1** promoted, today + tomorrow on the engine).
Read [AGENTS.md](AGENTS.md) first. Rewrite this file at every checkpoint, then commit and push; whoever reads it next may
be a new agent.

**Git:** private repo `MusaMoholo/MusNBA` (`main`). Last session's checkpoint: `7a23a48` (D22). This session's commit:
"M5b + v1.1 …" (see `git log -1`). **Nothing runs in the background.** The owner keeps `scripts/serve.py` on :8766 open —
leave it; use :8767 for your own checks.

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
  MusSim-style per-world rating pathway (D25) — next actions item 1.
- **Size and defence, first ablations — negative** (FINDINGS §3l): heights/weights for all 935 players
  (`scripts/athletes.py`, `data/derived/athletes.parquet`); archetype priors (k = 10) and on-court defence rates are
  options in `features.py` (`--body --archetypes K --defence`) and optional inputs in `nodes.py` (`@body`, `@defence`);
  neither beats v1.1 overall; both help the **location** node.
- **New tools:** `scripts/parity.py` (adapter/feed parity), `scripts/buckets.py` (paired comparison by the player's sample
  size), `train.py --segments/--train-segments/--train-features` (variants and the paired cross-data test),
  `aggregate.py --name/--train-segments/--train-features`, `scripts/backtest.py` (**written, not yet run**).

**App.** Localhost (`serve.py`, :8766) and the static PWA. Today's and tomorrow's slates come from engine v1.1 (the floor,
D22); backfills use the placeholder `baseline-v1`, saved beside each engine snapshot (`games_placeholder.json`).

**Engine realism (still open, FINDINGS §3j):** strong offences under-expressed; outcomes too tightly spread (OT ≈ 3% v
5.4%); v1.1's M6a biases: team turnovers +9.7%, and-ones +6.9%, fouled on a three −28%, total +1.4 points.

**Known gap:** `nightly.py` does not rebuild segments, rotations or features — the engine's profiles stay as of the last
manual rebuild (now: games through 18 Nov). Next actions item 2.

## Next actions (in order)

1. **Season pathway (D25, owner).** In `projection.simulate_season`: universe k plays engine world k (mod the engine's
   worlds) for today's and tomorrow's games — `nightly.py` must keep each engine game's per-world points
   (`Engine.last.pts`) and run the season sim once with both days; then every later game, in date order, draws both
   scores from that universe's own ratings (offensive and defensive rating per team, start = today's shrunk estimate +
   a draw at its posterior SD ≈ 11 / √(games + 8) per 100) and updates both teams by the estimator's own response,
   1/(n + 1 + k) with k = 8 prior games, to the surprise against that universe's expectation (zero on average). A game's
   long-range win % = share of universes won (D16). Done when smoke passes, a season re-simulates bit-for-bit, and the
   app labels the pathway as uncalibrated. Calibration of the gain to real dispersion and persistence is M12 (walk-forward
   2022-26, as MusSim's `analysis/calibrate_drift3.py`).
2. **Nightly rebuild of engine inputs:** `nightly.py` should run current-season `possessions.py` → `rotations.py` →
   `features.py` before the engine (≈ 1–2 min), so profiles include last night's games. Done when a nightly run's
   `engine_inputs_sha256` changes after new finals and smoke's re-simulation still passes.
3. **Engine backtest (M9 start):** `.venv/bin/python scripts/backtest.py --config models/v1.1.json --games 200 --worlds 1000
   --jobs 4` — fits all 16 fold models (`data/models/folds/v1.1_F4_all/`), plays F4 games forward with cutoff-safe inputs
   and real availability, and scores team points/margin/total (CRPS, coverage, slope of real on simulated margin — the
   "strong offences under-expressed" test), possessions and points per 100, win calibration, OT and player box scores by
   tier. First run will need debugging (never executed). This becomes the yardstick every later engine change must beat
   (D22). Note: no `baseline-v1` comparison on history yet (its snapshots exist only for 2026-27).
4. **Location with size/defence:** keep `@body`/`@defence` inputs for the location node only (per-node `drop` in a
   version file) and test against `…224019Z_v1.1_folds`; first run a seed pair for location (its noise floor is 0).
5. **Engine realism** (FINDINGS §3j–§3k): spread (per-world form, D3/M8; targets total SD 18–19, OT 5.4%), team turnovers
   +9.7%, the foul classes (and-ones +6.9%, fouled on a three −28%).
6. **Refits with 2026-27 data:** the single convention makes this season's rows usable for training — the 2026-27 foul
   and turnover shifts (FINDINGS §3k) can only be learned from them. Design the weekly refit (D11) and its promotion test.
7. Then M7 (target-aware substitutions — the biggest remaining risk) → M8 (form, end-game) → M9 (full backtest).

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
