# MusNBA

NBA game, player and season simulations — MusSim's sibling for basketball. A laptop-run Python
pipeline collects box scores and play-by-play, simulates every game 10,000 times and every
remaining season 10,000 times, and a static, offline-capable app shows the results on a laptop
or phone.

> The app is live on localhost and as a static PWA. Two engines, one daily flow (D26): today's and tomorrow's games come
> from the **possession engine v1.1** (every possession simulated from 16 LightGBM decision models, inputs rebuilt nightly
> from every game so far; the floor for later improvements, D22–D24); every later game from the **team pathway v1**, where
> each simulated season carries its own team ratings and updates them after every game (D25). Past dates rebuilt after the
> fact use a labelled placeholder. See [PLAN.md](PLAN.md) and [HANDOFF_NEXT.md](HANDOFF_NEXT.md).

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
  2,000 worlds; `--ahead N` sets how many days after today; no games in that window → the next slate, D26). Before the
  engine runs, its inputs (current-season segments, rotations, profiles) are rebuilt from every final before today
  (~50 s; `--no-rebuild` skips). The season sim then plays every later game through the team pathway (D25);
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
| `scripts/engine.py` | The engine (default projection, v1.3 = D30 defence inputs + D29 minutes): plays games possession by possession; rotation tables rescaled to minutes targets; profiles from the version's features variant (`features_dir`) |
| `scripts/minutes.py` | D29 minutes: healthy-role minutes, priority, 240 per team by priority, return ramp, rotation share, per-world draws, projected starters |
| `scripts/matchups.py` | D30 implicit matchups: soft assignment of defenders to shooters from foul/block credits; shot types from the play text |
| `scripts/fetch_nbastats.py` | D32 NBA Stats adapter (browser fetch headers, ~1 request/s, resumable): season logs, `boxscorematchupsv3`, tracking defence, play-by-play v3 → `data/raw/nbastats/<endpoint>/<season>/` (gzip + manifest) |
| `scripts/nbastats.py` | D32 crosswalk (games by date + teams, players by name/stat line), reconciliation v ESPN (points, minutes, possessions), real matchups in ESPN ids → `data/derived/nbastats/` |
| `scripts/realmatch.py` | D32 real matchups: pre-game assignment fitted on real shares (ranks, stopper, pair history), per-game pair history (cutoff-safe) |
| `scripts/lineups.py` | Projected v actual starters for every finished snapshot (nightly record, D33) |
| `scripts/backtest.py`, `scripts/backtest_compare.py` | Engine backtest on held-out fold games (M9; `--rotation targets`, `--models` to reuse fold models), with the team-rating model on the same games; paired comparison of runs (players first) |
| `scripts/pathway.py` | Team engine (D25, D26): per-world offensive/defensive ratings, updated after every simulated game |
| `scripts/season_backtest.py` | Team engine trust test (M12 first cut): walk-forward seasons 2022-26, `--grid` calibration |
| `scripts/athletes.py`, `scripts/buckets.py` | Player heights/weights; paired comparisons by the player's sample size |
| `scripts/season_stats.py` | Cutoff-safe team ratings and player season stats |
| `scripts/projection.py` | Placeholder game model (`baseline-v1`, backfills) and the season sim (team pathway, D25) |
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
.venv/bin/python scripts/backtest.py --config models/v1.3.json --games 200 --worlds 1000 --jobs 7 --rotation targets [--models folds/v1.3_F4_all]   # engine v1.3 backtest (M9)
.venv/bin/python scripts/backtest_compare.py <run A> <run B> [--log NAME]   # paired: player tiers, loading, margins, CRPS
.venv/bin/python scripts/minutes.py --evaluate [--season 2025 --from 2025-01-01 --to 2025-04-30] [--set gamma=1]   # allocator v real (no engine)
.venv/bin/python scripts/matchups.py --fit --through 2025-12-31            # D30 assignment θ → models/matchup_<through>.json
.venv/bin/python scripts/fetch_nbastats.py --logs --matchups [--ptdefend] [--pbp]   # D32 NBA Stats history (polite, resumable)
.venv/bin/python scripts/nbastats.py --crosswalk --reconcile --matchups     # ids ↔ ESPN, reconciliation, matchups.parquet
.venv/bin/python scripts/features.py --out data/derived/variants/realmatch/features --defence --defence-k-scale 0.2 \
    --matchup models/matchup_2025-12-31.json --shot-types --real-matchups data/derived/nbastats/matchups.parquet
.venv/bin/python scripts/realmatch.py --history                             # per-game pair history (cutoff-safe)
.venv/bin/python scripts/realmatch.py --fit --through 2025-12-31 --save     # real-share θ → models/realmatch_<through>.json
.venv/bin/python scripts/backtest.py --config models/v1.2d.json --models folds/v1.2d_F4_all --rotation targets --pool 0   # D36: one rotation table per world
.venv/bin/python scripts/features.py --out data/derived/variants/matchup/features --defence --defence-k-scale 0.2 --matchup models/matchup_2025-12-31.json --shot-types
.venv/bin/python scripts/lineups.py --score                                 # projected v actual starters (also in the nightly)
.venv/bin/python scripts/season_backtest.py [--grid]                    # team engine walk-forward (M12; ~1–4 min)
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
