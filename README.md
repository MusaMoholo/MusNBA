# MusNBA

Local-first NBA simulations:10,000 possession worlds per lineup case for today's ET games, then season pathways with evolving
team ratings from tomorrow. Current runtime/delivery: [HANDOFF](HANDOFF_NEXT.md). Contributors start with [AGENTS](AGENTS.md);
[MODEL](MODEL.md) owns design/validation/evidence, [PLAN](PLAN.md) scope and backlog.

## Daily use

Python 3.12+, NumPy/pandas/pyarrow/LightGBM (macOS libomp); Node for browser checks.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/nightly_musnba.py
.venv/bin/python scripts/serve.py
```

The nightly collects authorised ESPN/NBA inputs, rebuilds prior-game features, simulates today and a fresh season,
writes snapshots/views and exports both bundles. `nightly.py --ahead` must be 0. Game-free days still refresh the season.
Missed finals are collected; missed possession forecasts are **not** reconstructed. `--offline --no-rebuild` needs recorded unchanged-input justification.
Owner's:8766 server stays running; agent review uses `serve.py --port 8767`. Serving never computes.
Verified matching pre-tip forecasts may be retained with their original provenance; invalid/cross-tip replacements fail.
Do not bypass guards. Archive existing views before standalone `scripts/views.py` rebuilds; `--help` is read-only.

## PWA and bundles

Install [MusNBA](https://musamoholo.github.io/MusNBA/). Source: [MusaMoholo/MusNBA](https://github.com/MusaMoholo/MusNBA).
In **Offline data & installation → Import data**, select from iCloud Drive/MusNBA:

| Device | File | Contents |
|---|---|---|
| Laptop | `MusNBA-laptop.musnba.gz` | Full saved worlds, lineup cases, Scenarios/Given/Joint/duels. |
| Phone | `MusNBA.musnba.gz` | Expected distributions; no saved-world tools or lineup cases. |

Each device imports separately; Safari and the installed iPhone app may have separate storage. Keep the phone unlocked/app open during import.
Shell updates and data imports are separate. iCloud export is not proof of import or real-device memory acceptance.

```sh
.venv/bin/python scripts/nightly_musnba.py --export-only
.venv/bin/python scripts/export_musnba.py --shell exports/MusNBA-web --base-path /MusNBA/
```

Export-only reuses completed outputs. Current publication is end-of-nightly, not game-by-game; D54 is planned next.
Each file is atomic, the pair is not: retry both after partial export. `--output PATH` sets the phone destination; laptop adds `-laptop`.
Replacements archive to `~/Basketball_archive_ops`. Visible staging/hidden-flag clearing keeps files selectable.
Only the data-free shell plus `.nojekyll` goes to `gh-pages` (branch source `/`), never models/data/bundles.
No repository CI workflows; built-in Pages deployment provides hosting. Preserve local Git identity/helper.

## App contract

Today prioritises games/player boxes and expandable slate insight. Game Centre shares Q1–Q4/H1/H2/FG selectors across player/team/sheet/scenarios;
FG includes OT for possession games. Future pathway totals/margins are regulation with a separately resolved winner, no player forecasts.
Standings contains forecast/seeds/wins/ratings, races/playoff picture; marginal seeds are not simulated playoff winners.
Teams/Players lead with schedules/rosters/logs/forecasts and expandable advanced detail. Lab is secondary.

Laptop lineup controls and Given/Joint use the same exact weighted stored worlds; Expected is default and “either status” marginalises remaining weights.
Participation conditions mean positive simulated minutes, not availability or causal lineup effects. Phone retains Expected only.
U23 outcome stories show joint scorer and Q3-conditional win events from loaded worlds; headshots 526/528 use offline images/initials fallback.
Startup Reload recovers failed shell downloads. View Centre/rotation map remain future work.

Slates are ET; times show UK/ET. Spreads are projected mean margins. Exact float64 minutes drive conditions; display rounds to seconds.
Over is strictly greater than x.5; shooting percentages condition on attempts and show no-attempt mass separately.
Missing denominators/old unavailable periods stay undefined. Dates/counts/versions/thresholds come from loaded data; labelled examples stay illustrative.
Actual/simulated, origin/cutoff/model and pre-tip/retrospective/unverified timing remain explicit; after-tip/unverified forecasts do not establish pre-game accuracy.
Both themes at 1440/960/390, grouped controls, three/two/one card rows and 44 px touch targets are required.

## Verification and code map

```sh
.venv/bin/python scripts/smoke.py
.venv/bin/python scripts/smoke.py --fault
.venv/bin/python -m unittest tests.test_release_gate tests.test_late_clock tests.test_late_clock_recipe
.venv/bin/python scripts/check_docs.py
node analysis/browser_check.mjs --base http://127.0.0.1:8767
node analysis/pwa_import_check.mjs --url <shell-url> --bundle <bundle.musnba.gz> --profile laptop
```

Fault must fail. Use `--profile phone` separately; inspect responsive screenshots. The local pre-commit hook runs docs checks.
Fresh clones: inspect existing hooks before `git config --local core.hooksPath .githooks`. Heavy jobs total≤10 compute threads including inner OMP/BLAS.

Core path: `fetch_*`/`history` → `plays`/`possessions`/`rotations` → `features`/`minutes`/`matchups` → `nodes`/`train`/`evaluate`.
`engine.py` simulates, `live_forecast.py` queues canonical chunks, `lineup_forecast.py`/`world_mass.py` preserve exact mixtures,
`pathway.py` simulates seasons, `nightly*.py` orchestrates, `views.py`/`serve.py`/`webapp/` serve stored results.
`compare.py` grades node runs; `a1_compare.py` grades matched engine distributions; `release_gate.py` requires explicit policy.
Legacy `backtest_compare.py`/`a1_minutes_gate.py` are historical protocols, not generic promotion gates.
Use runner `--help` and MODEL before launching. Fold backtests require `--clock-recipe` when the production pool cutoff differs from the fold nodes; freeze prior-fitted fold parameters first. Parent preflight rejects mismatched dates before worker startup. `train.py --threads 10` caps fitting; backtest uses `--jobs 10` plus BLAS caps.
Configurations/reports are committed in `models/`/`analysis/experiments/`; fits, raw inputs, per-row arrays/worlds and exports stay ignored under `data/`.
Current experiment namespaces are immutable; do not restart completed protected runs. `analysis/a2_world_diagnostics.py --closing-controls`
audits existing 400-game controls without new worlds (fresh output required).

## Documentation history

Five core docs plus three versioned policy contracts are live. Budgets include **all live Markdown**, not only root files.
Completed protocols, old decision details and original pre-lean docs are retained exactly in
[one archive](docs/archive/20261123_document_history.tar.gz), with a [44-member hash manifest](docs/archive/20261123_document_history.manifest.json)
and external backup `~/Basketball_archive_ops/docs_20261123_a2_close`.

```sh
tar -tzf docs/archive/20261123_document_history.tar.gz
tar -xOf docs/archive/20261123_document_history.tar.gz ENGINE_PLAN.md
tar -xOf docs/archive/20261123_document_history.tar.gz docs/archive/2026-11-23-before-lean/HANDOFF_NEXT.md
```

Read/extract only needed sections. Historical commands/next actions are not current instructions; replay old sources in an isolated checkout
with their declared inputs, not by restoring stale docs over this root. Frozen source copies remain ignored under experiment namespaces.
New completed history uses Git/aggregate JSON rather than another live narrative file.
