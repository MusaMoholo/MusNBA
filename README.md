# MusNBA

NBA game, player and season simulations — MusSim's sibling for basketball. A laptop-run Python
pipeline collects box scores and play-by-play, simulates every game 10,000 times and every
remaining season 10,000 times, and a static, offline-capable app shows the results on a laptop
or phone.

> The app is live on localhost and as a static PWA. Today's and tomorrow's projections come from the **possession
> engine v1.1** (every possession simulated from 16 LightGBM decision models; the floor for later improvements, D22–D24);
> past dates rebuilt after the fact use a labelled placeholder. See [PLAN.md](PLAN.md) and [HANDOFF_NEXT.md](HANDOFF_NEXT.md).

## Setup

Python 3.12+ and a virtual environment. Dependencies (pinned in `requirements.txt`): NumPy, pandas, pyarrow and
LightGBM. On macOS LightGBM needs OpenMP: `brew install libomp`.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Daily use

```sh
.venv/bin/python scripts/nightly.py          # collect → fixtures/box scores → simulate today (ET) → views
.venv/bin/python scripts/serve.py            # browse at http://127.0.0.1:8766
```

- Today's and tomorrow's slates are projected by the possession engine v1.1 (the default, D22–D24; ~20 s per game at
  2,000 worlds; `--ahead N` sets how many days after today);
  `--placeholder` uses the old box-score placeholder instead, and backfilled past dates always do. `nightly.py --offline` reuses retained data; `--views-only` only rebuilds what the app reads;
  `--backfill-days N` adds retrospective snapshots (labelled as such) for the previous N slates.
- The server reads files from disk: front-end edits appear on refresh, rebuilt views appear
  immediately; no restart needed. `serve.py --host 0.0.0.0` lets a phone on the same Wi-Fi in.
- Slates are US Eastern game dates; tip-offs show UK time with ET.

## Phone app (static PWA)

```sh
.venv/bin/python scripts/export_musnba.py --shell _site --base-path /MusNBA/   # data-free shell
.venv/bin/python scripts/nightly_musnba.py                                     # nightly (engine) + iCloud export
```

Host `_site` (e.g. GitHub Pages, `gh-pages` branch with `.nojekyll`). The shell never contains
data. `nightly_musnba.py` writes **iCloud Drive/MusNBA/MusNBA.musnba.gz** after a successful
nightly; in the installed app choose **Offline data & installation → Import data**. Imports are
checksum-verified and atomic; the previous data stays available if an import fails.

## Code map

| Location | Responsibility |
|---|---|
| `basketball_common.py` | Paths, time zones, team conferences/divisions, atomic writes, archives |
| `scripts/fetch_espn.py` | Provider adapter: raw ESPN responses retained gzip under `data/raw/espn` |
| `scripts/master_fixtures.py`, `scripts/box_scores.py` | Master fixture list; player/team game logs; player registry |
| `scripts/pbp.py` | Play-by-play: on-court seconds per period, per-period player box scores, reconciliation report |
| `scripts/plays.py`, `scripts/history.py` | One play schema for live and historical data; 2022-23 → 2025-26 history ingest and reconciliation |
| `scripts/possessions.py` | Possessions/segments with lineups, state and the who → what → result chain (training data); rebound-clock convention |
| `scripts/parity.py` | Live ESPN v hoopR history: same games through both adapters; season distributions under both rebound clocks |
| `scripts/rotations.py` | Stints, substitution windows, on-court minute shares; replay-rotation baseline and minutes backtest |
| `scripts/features.py`, `scripts/evaluate.py` | Point-in-time player and team-style profiles; rolling-fold evaluation harness and baselines |
| `scripts/nodes.py`, `scripts/train.py` | Datasets for the 16 decisions (cached); LightGBM per decision on the folds, persisted versions, final test |
| `scripts/compare.py`, `scripts/calibration.py` | Paired run comparisons (game-clustered, seed-noise floor); calibration by period and margin |
| `scripts/aggregate.py` | M6a: replay held-out games with real lineups and clock, sample every decision, score box scores |
| `scripts/engine.py` | The engine (default projection, v1.1): plays games possession by possession |
| `scripts/backtest.py` | Engine backtest on held-out fold games (M9 first cut; written, not yet run) |
| `scripts/athletes.py`, `scripts/buckets.py` | Player heights/weights; paired comparisons by the player's sample size |
| `scripts/season_stats.py` | Cutoff-safe team ratings and player season stats |
| `scripts/projection.py` | Simulation engine (placeholder now; PBP engine in phase 2) and season sim |
| `scripts/nightly.py`, `scripts/views.py` | Orchestration, immutable snapshots, API-ready views |
| `scripts/serve.py` | Read-only local server for the app and `/api/*` |
| `scripts/export_musnba.py`, `scripts/nightly_musnba.py` | Static shell, data bundle, iCloud export |
| `scripts/webapp/` | The app: native ES modules, no build step |
| `scripts/smoke.py`, `analysis/*.mjs` | Accounting checks; optional browser/PWA acceptance (Node, no packages) |

## Engine data and models (phase 2)

Rebuild in order after new data: `scripts/history.py` → `scripts/possessions.py` → `scripts/rotations.py`
→ `scripts/features.py` → `scripts/nodes.py` (dataset cache) → `scripts/train.py`. State, next steps and commands:
[HANDOFF_NEXT.md](HANDOFF_NEXT.md).

```sh
.venv/bin/python scripts/train.py --name <label> [--drop @team …]     # an experiment on folds F1–F4 (~20 min)
.venv/bin/python scripts/compare.py <run A> <run B> --noise <seed A> <seed B>   # keep / reject, per node
.venv/bin/python scripts/train.py --config models/v1.1.json --final     # persist a version, score the final test once
.venv/bin/python scripts/aggregate.py --config models/v1.1.json         # M6a aggregation test on F4 games
.venv/bin/python scripts/parity.py [--fetch]                            # adapter and feed parity (M5b)
```

Data variants live under `data/derived/variants/<name>/` (segments root + `features/`): `possessions.py --rebound-clock miss
--out DIR` and `features.py --segments DIR --out DIR/features` build one; `nodes.py`/`train.py --segments DIR --features …`
read it; a version file can name it (`"segments"`, `"features"`). `train.py … --train-segments default --train-features
default` trains each fold on the canonical data and validates on the variant's rows (a paired cross-data test).

Fitted models live in `data/models/<version>/` (out of git, rebuilt by `--final`); the settings that define a version
are `models/<version>.json` (in git).

## Verification

```sh
.venv/bin/python scripts/smoke.py                                   # accounting + determinism
node analysis/browser_check.mjs --base http://127.0.0.1:8766        # phone/desktop, both themes
node analysis/pwa_import_check.mjs --url <shell url> --bundle <file.musnba.gz>
```

Data: ESPN's public site API (unofficial). Personal, local use.
