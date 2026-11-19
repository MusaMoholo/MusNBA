# Handoff — state and next actions

Updated **19 November 2026, ~21:45 UTC** (checkpoint: M5 tuned, v1 persisted, final test scored once, M6a gate met).
Read [AGENTS.md](AGENTS.md) first. Rewrite this file at every checkpoint, then commit and push; whoever reads it next
may be a new agent.

**Git:** private repo `MusaMoholo/MusNBA` (`main`). Previous checkpoint `539c0c7`; this checkpoint's commit is the
one after it ("M5 tuned + v1 + M6a …"). Nothing runs in the background; the owner may have `scripts/serve.py` on
:8766 open — leave it.

## State

**App (phases 1/1b, done).** Localhost (`scripts/serve.py`, :8766, owner-run) and a static PWA. Projections still come
from the labelled placeholder `baseline-v1`; the engine replaces it at M9.

**Engine (phase 2).** M1–M4 done (history 2022-23 → 2025-26, segments, rotations, profiles, folds F1–F4).
- **M5 done — model v1.** Sixteen decisions (D20 + **D21**: a *location* node — the shot's distance band within its
  zone — and *team turnover* as a fourth event class). Settings in `models/v1.json` (in git, with the reason for each);
  fitted models in `data/models/v1/` (out of git, 44 MB, rebuilt by `train.py --config models/v1.json --final`).
  Fold validation: every node ≥ its best baseline on every fold, ECE ≤ 0.012. **Final test (2026-27 to 18 Nov) scored
  once**: every node above its baselines. All tuning results, wins and negative results: FINDINGS §3h, §3h′.
- **Tooling.** `nodes.py` caches the 16 datasets (`data/derived/nodes/<hash>/`, ~8 GB; `--prune` removes stale
  folders). `train.py` stores per-row held-out losses; `compare.py A B --noise S0 S1` is the keep/reject test
  (game-clustered z plus a seed-noise floor — a seed change alone gives |z| up to 3.4); `calibration.py <run>` gives
  excess ECE by period and margin. `features.py --out DIR --family usage=30` builds profile variants.
- **M6a gate met** (`aggregate.py`, FINDINGS §3i): held-out F4 games replayed with real lineups and clock, every
  decision sampled, 10,000 worlds. 300 games: team total 228.5 v 229.5, player stats within ±2% for starters and bench,
  10–90% coverage 77–83%, CRPS 7–12% better than recent averages. Event accounting traced a +5% foul bias to fouls
  falling through every season (day of season now in event and turnover type). A full run on all 766 F4 games was
  run at the end of the session — numbers in FINDINGS §3i if present, else rerun it (step 2).
- **Problem found: live v history adapter skew** (FINDINGS §3h′). The live ESPN adapter (2026-27) and the hoopR
  history produce different segments at the same point of the season: actions within 2 s after an offensive rebound
  12% v 49%, non-shooting/shooting foul split 18.7/16.3 v 16.8/17.3 per game, live-ball turnovers 56.6% v 59.4%. Models
  trained on history see shifted inputs on live games; this is most of the final-test calibration gap. **Fix before
  the engine runs on live games.**

## Next actions (in order)

1. **M5b — adapter parity.** Pick five 2025-26 games present in the hoopR history; fetch their ESPN summaries with
   the live adapter (`scripts/fetch_espn.py` summary fetch, polite spacing — five requests) into a scratch folder; run
   both through `plays.py` → `possessions.py` and diff the segments play by play: rebound clock stamps (oreb → putback
   time), shooting v non-shooting foul classification, live v dead turnovers, offensive fouls. Fix the adapter that
   departs from ESPN's own data (history files are a third-party re-parse of the same ESPN feed). Done when the five
   games give identical segments and the 2026-27 distributions above match 2025-26 Oct–Nov within noise. Then rebuild
   current segments → rotations → features → nodes; v1 keeps its recorded final test; score the fixed data as **v1.1**
   (same settings, `models/v1.1.json`) once.
2. **M6a follow-ups.** (a) If FINDINGS §3i lacks the 766-game run, rerun
   `.venv/bin/python scripts/aggregate.py --config models/v1.json --games 0` (~40 min) and record it. (b) Trace the
   stars' +2–5% on points, free throws, turnovers and threes (who-node favourite bias by usage tier: compare forecast
   v hit rate for the top-usage candidate on folds) and the residual foul bias with the event table.
3. **Experiments queued by this session's results** (each one run on the folds, `compare.py` against
   `…control2` with the seed noise): split the profile *usage* family so rebounding/defence rates (oreb, dreb, blk,
   stl, pf) get their own longer half-life (usage 30 helped blocker −0.26% and rebounder −0.06% but hurt what);
   accuracy half-life 120 and 160 games (80 trended better); finer location bands to recover part of the 0.50 nats per
   game that bands cost; team style for more nodes in combination.
4. **Inference speed for M6.** One step for 10,000 worlds costs ~0.72 s summed over all nodes on a busy machine
   (`data/models/v1/config.json`, `predict_ms_10k_worlds`). Benchmark on a quiet machine, then design the engine
   step to score only the worlds that reach each node (blocker ≈ 5% of worlds, assister ≈ 25%, free throws ≈ 10%) and
   batch games together; target ≤ 60 s per game (D10).
5. Then **M6** (engine v1 with replay rotations: the same chain as `aggregate.py`, but sampling duration and carrying
   each world's own state — score, fouls, in-game counts — forward) → M7 (substitutions) → M8 (form, end-game) → M9.

## File map

| Files | Responsibility |
|---|---|
| `basketball_common.py` | Paths, ET/UK time, conferences/divisions, NBA franchise ids, atomic JSON, archives |
| `scripts/fetch_espn.py` | Live collection: `data/raw/espn/runs/<UTC>/`, finals `data/raw/espn/final/`, logos |
| `scripts/master_fixtures.py`, `scripts/box_scores.py` | Live master fixtures; player/team game logs; player registry |
| `scripts/plays.py` | Canonical game/play schema; adapters for live ESPN and history; shot-value inference |
| `scripts/history.py` | History download (`--fetch`, manifest) and per-season reconciliation → `data/derived/history/<season>/` |
| `scripts/pbp.py` | Per-period player box scores and on-court seconds; lineup helpers |
| `scripts/possessions.py` | Segments (M2) with lineups, state, outcomes, `ft_seq`; `game_ok` flag |
| `scripts/rotations.py` | Stints, dead-ball windows, substitutions, on-court minute shares; replay v0 + backtest (M3) |
| `scripts/features.py` | Point-in-time player profiles and team style/schedule (`team_pregame.parquet`); `--out`, `--family` variants |
| `scripts/evaluate.py` | Folds F1–F4, final-test boundary, M4 baselines; experiment log location |
| `scripts/nodes.py` | Datasets for the 16 decisions; on-disk cache; location bands (`LOCATION_EDGES`) |
| `scripts/train.py` | LightGBM per node and fold; experiment options; `--config` versions; `--final` persist + final test |
| `scripts/compare.py`, `scripts/calibration.py` | Paired run comparison with seed-noise floor; calibration by period/margin |
| `scripts/aggregate.py` | M6a: branch tables from real segments, 10,000-world sampler, box-score and event accounting |
| `models/v1.json` | v1 settings, the fold run that validated them, and why |
| `scripts/season_stats.py`, `scripts/projection.py` | Live season stats; placeholder engine `baseline-v1` and season sim |
| `scripts/nightly.py`, `scripts/views.py` | Live orchestration, snapshots, API views |
| `scripts/serve.py`, `scripts/export_musnba.py`, `scripts/nightly_musnba.py` | Local server; static shell + bundle; iCloud export |
| `scripts/webapp/` | The app (ES modules, no build) |
| `scripts/smoke.py`, `analysis/*.mjs` | Accounting and model checks (66); browser and PWA acceptance |

## Commands

```sh
git status && git log --oneline -5                                    # start of session; commit + push at checkpoints
.venv/bin/python scripts/smoke.py [--fault]                           # 66 checks (the fault run must fail)
.venv/bin/python scripts/nightly.py [--offline] [--backfill-days N]   # live: collect → snapshot → views
.venv/bin/python scripts/serve.py --port 8767                         # your own review server (owner uses :8766)
.venv/bin/python scripts/history.py [--fetch]                         # history reconcile (M1)
.venv/bin/python scripts/possessions.py [--history]                   # segments (M2)
.venv/bin/python scripts/rotations.py [--history | --backtest]        # rotations (M3)
.venv/bin/python scripts/features.py [--out DIR --family usage=30]    # profiles (M4); variants elsewhere
.venv/bin/python scripts/nodes.py [--features DIR/pregame.parquet | --prune]   # dataset cache (~1 min)
.venv/bin/python -u scripts/train.py --name <label> [--drop @team …] [--threads 3]   # experiment on folds (~20 min)
.venv/bin/python scripts/compare.py <run A> <run B> --noise 20261119T190747Z_control 20261119T190747Z_seed8
.venv/bin/python scripts/train.py --config models/v1.json [--final]   # validate a version / persist + final test once
.venv/bin/python -u scripts/aggregate.py --config models/v1.json [--games 300] [--worlds 10000]   # M6a
```

Rebuild order after new data or a parser change: history → possessions (`--history` and current) → rotations
(`--history` and current) → features → nodes → train. Experiments: 4 runs in parallel with `--threads 3` fit the
laptop (14 cores, 48 GB; ~2 GB each from the cache); never edit `nodes.py` while runs are reading a cache built from it
(folders are hash-named, so new code starts a new folder rather than breaking old runs).
