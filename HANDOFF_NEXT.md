# Handoff — state and next actions

Updated **19 November 2026, ~20:15 UTC** (checkpoint: M5 v1 done; git set up). Read [AGENTS.md](AGENTS.md) first.
Rewrite this file at every checkpoint, then commit and push; whoever reads it next may be a new agent.

**Git:** private repo `MusaMoholo/MusNBA` (`main`), first commit `3291ffc` + this checkpoint's docs commit. Nothing is
running in the background; the owner may have `scripts/serve.py` on :8766 open — leave it.

## State

**App (phases 1/1b, done).** Localhost (`scripts/serve.py`, :8766, owner-run) and a static PWA. Projections come from
the labelled placeholder `baseline-v1` (box-score rates + play-by-play quarter profiles, 10,000 sims per game and per
season). Its known weakness — minutes spread too thin and team totals imposed then split (Brunson 20.6 projected v
27.0 actual) — is not worth fixing; the engine replaces it at M9.

**Engine (phase 2).**
- M1–M4 done: history 2022-23 → 2025-26 incl. playoffs/play-in (5,290 games) in one play schema; 1.26M reconciled
  segments (now with each free-throw trip's real make/miss order, `ft_seq`); stints, windows, substitutions;
  point-in-time player profiles; rolling folds F1–F4 with the final test (2026-27) untouched.
- **M5 v1 done.** The chain is 15 decisions (ENGINE_PLAN D20). `scripts/nodes.py` builds the datasets (~40 s);
  `scripts/train.py` fits LightGBM per node and fold. **Every node beats or matches its best baseline on every fold,
  with calibration error ≤ 0.016** — table in FINDINGS §3g; logs in `analysis/experiments/`. A free-throw label leak
  was caught and fixed (FINDINGS §3g). Smoke 61/61 guards both properties.
- Not yet done in M5: tuning on the folds, calibration by period/state, ablations, persisted models.

## Next actions (in order)

1. **Tune on the folds** (TRAINING_PLAN §7). One change at a time, scored with
   `.venv/bin/python -u scripts/train.py --nodes <node…>`; keep a change only if mean fold log loss improves and no
   fold gets worse by more than noise. Record every attempt in FINDINGS (wins and negative results):
   - sample-weight decay: add `weight = 0.5 ** (age_days / half_life)` to the training `lgb.Dataset` in
     `train.run_node`; try half-lives of ½, 1, 2 seasons and none;
   - feature half-lives and season carry in `scripts/features.py` (`FAMILIES`), then rebuild features;
   - game-type weights (D19); heat-check ablation (drop `made_so_far`, `fga_so_far`, `pts_so_far`);
   - new context where the node's top features suggest gaps: team pace and shot-profile tendencies (duration, what),
     opponent team defensive rating (shot result), defender size (blocked, rebound), clutch (free throw).
2. **Calibration by period and state** for who, what, shot result and rebound: ECE per period (Q1–Q4, OT) and per
   margin bucket (≤ −15, −14…−6, −5…5, 6…14, ≥ 15). Fix anything systematic (e.g. per-period temperature) before M6a.
3. **Persist models**: train every node on all data before the final test with the chosen settings; save
   `models/v1/<node>.txt` (LightGBM model) and `models/v1/config.json` (feature lists, temperatures, decay settings,
   data range, experiment ids). Add a smoke check that every node file loads and predicts. Then score the **final
   test once** (2026-27 to date) per node and record it in FINDINGS and PLAN.
4. **M6a — aggregation test** (ENGINE_PLAN §13): for held-out games, keep the real lineups and real segment clock,
   sample every decision from the node models (10,000 worlds per game, vectorised), and compare simulated with actual
   box scores per player and stat. Report bias by role tier (stars ≥ 25% usage, starters, bench), 10–90% coverage and
   CRPS v a recent-averages baseline. Done when bias ≈ 0 and coverage ≈ 80%; otherwise trace the bias to its node.
5. Then M6 (engine with replay rotations) → M7 (substitution model) → M8 (form, end-game) → M9 (backtest, switch app).

## File map

| Files | Responsibility |
|---|---|
| `basketball_common.py` | Paths, ET/UK time, conferences/divisions, atomic JSON, archives |
| `scripts/fetch_espn.py` | Live collection: `data/raw/espn/runs/<UTC>/`, finals `data/raw/espn/final/`, logos |
| `scripts/master_fixtures.py`, `scripts/box_scores.py` | Live master fixtures; player/team game logs; player registry |
| `scripts/plays.py` | Canonical game/play schema; adapters for live ESPN and history; shot-value inference |
| `scripts/history.py` | History download (`--fetch`, manifest) and per-season reconciliation → `data/derived/history/<season>/` |
| `scripts/pbp.py` | Per-period player box scores and on-court seconds; lineup helpers `game_context`, `period_starters` |
| `scripts/possessions.py` | Segments (M2) with lineups, state, outcomes, `ft_seq`; `game_ok` flag |
| `scripts/rotations.py` | Stints, dead-ball windows, substitutions, on-court minute shares; replay v0 + backtest (M3) |
| `scripts/features.py` | Point-in-time player profiles (M4) |
| `scripts/evaluate.py` | Folds F1–F4, final-test boundary, baselines; experiment log location |
| `scripts/nodes.py` | Datasets for the 15 decisions (M5) |
| `scripts/train.py` | LightGBM per node and fold, baselines, temperatures, calibration, experiment log (M5) |
| `scripts/season_stats.py`, `scripts/projection.py` | Live season stats; placeholder engine `baseline-v1` and season sim |
| `scripts/nightly.py`, `scripts/views.py` | Live orchestration, snapshots, API views |
| `scripts/serve.py`, `scripts/export_musnba.py`, `scripts/nightly_musnba.py` | Local server; static shell + bundle; iCloud export |
| `scripts/webapp/` | The app (ES modules, no build) |
| `scripts/smoke.py`, `analysis/*.mjs` | Accounting and model checks; browser and PWA acceptance |

## Commands

```sh
git status && git log --oneline -5                                    # start of session; commit + push at checkpoints
.venv/bin/python scripts/smoke.py [--fault]                           # checks (the fault run must fail)
.venv/bin/python scripts/nightly.py [--offline] [--backfill-days N]   # live: collect → snapshot → views
.venv/bin/python scripts/serve.py --port 8767                         # your own review server (owner uses :8766)
.venv/bin/python scripts/history.py [--fetch]                         # history reconcile (M1)
.venv/bin/python scripts/possessions.py [--history]                   # segments (M2)
.venv/bin/python scripts/rotations.py [--history | --backtest]        # rotations (M3)
.venv/bin/python scripts/features.py                                  # profiles (M4)
.venv/bin/python scripts/evaluate.py                                  # baselines on folds (M4)
.venv/bin/python -u scripts/train.py [--folds F4] [--nodes who what]  # node models on folds (M5; full run ≈ 20 min)
```

Rebuild order after new data or a parser change: history → possessions (`--history` and current) → rotations
(`--history` and current) → features → train.
