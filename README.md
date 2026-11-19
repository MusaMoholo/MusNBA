# MusNBA

NBA game, player and season simulations — MusSim's sibling for basketball. A laptop-run Python
pipeline collects box scores and play-by-play, simulates every game 10,000 times and every
remaining season 10,000 times, and a static, offline-capable app shows the results on a laptop
or phone.

> Phase 1 (app shell) is live. Projections currently come from a **placeholder** box-score-rate
> model, clearly labelled in the app; the possession-by-possession engine is phase 2.
> See [PLAN.md](PLAN.md).

## Setup

Python 3.12+ and a virtual environment. NumPy is the only numerical dependency.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Daily use

```sh
.venv/bin/python scripts/nightly.py          # collect → fixtures/box scores → simulate today (ET) → views
.venv/bin/python scripts/serve.py            # browse at http://127.0.0.1:8766
```

- `nightly.py --offline` reuses retained data; `--views-only` only rebuilds what the app reads;
  `--backfill-days N` adds retrospective snapshots (labelled as such) for the previous N slates.
- The server reads files from disk: front-end edits appear on refresh, rebuilt views appear
  immediately; no restart needed. `serve.py --host 0.0.0.0` lets a phone on the same Wi-Fi in.
- Slates are US Eastern game dates; tip-offs show UK time with ET.

## Phone app (static PWA)

```sh
.venv/bin/python scripts/export_musnba.py --shell _site --base-path /MusNBA/   # data-free shell
.venv/bin/python scripts/nightly_musnba.py                                     # nightly + iCloud export
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
| `scripts/possessions.py` | Possessions/segments with lineups, state and the who → what → result chain (training data) |
| `scripts/rotations.py` | Stints, substitution windows, on-court minute shares; replay-rotation baseline and minutes backtest |
| `scripts/features.py`, `scripts/evaluate.py` | Point-in-time player profiles; rolling-fold evaluation harness and baselines |
| `scripts/season_stats.py` | Cutoff-safe team ratings and player season stats |
| `scripts/projection.py` | Simulation engine (placeholder now; PBP engine in phase 2) and season sim |
| `scripts/nightly.py`, `scripts/views.py` | Orchestration, immutable snapshots, API-ready views |
| `scripts/serve.py` | Read-only local server for the app and `/api/*` |
| `scripts/export_musnba.py`, `scripts/nightly_musnba.py` | Static shell, data bundle, iCloud export |
| `scripts/webapp/` | The app: native ES modules, no build step |
| `scripts/smoke.py`, `analysis/*.mjs` | Accounting checks; optional browser/PWA acceptance (Node, no packages) |

## Engine data and models (phase 2)

Rebuild in order after new data: `scripts/history.py` → `scripts/possessions.py` → `scripts/rotations.py`
→ `scripts/features.py` → `scripts/train.py`. State, next steps and commands: [HANDOFF_NEXT.md](HANDOFF_NEXT.md).

## Verification

```sh
.venv/bin/python scripts/smoke.py                                   # accounting + determinism
node analysis/browser_check.mjs --base http://127.0.0.1:8766        # phone/desktop, both themes
node analysis/pwa_import_check.mjs --url <shell url> --bundle <file.musnba.gz>
```

Data: ESPN's public site API (unofficial). Personal, local use.
