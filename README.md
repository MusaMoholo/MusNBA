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
Owner:8766 stays running; review uses `serve.py --port 8767`. Serving never computes.
Verified matching pre-tip forecasts may be retained with their original provenance; invalid/cross-tip replacements fail.
Resume a logged run with `--offline --no-rebuild --resume-live-run PATH`; inputs, sources and grouping must match. Wrong roots/duplicates fail.
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

Export-only reuses saved outputs. With a retained season, nightly publishes one interim complete-game update: all branches/Expected, prior forecasts preserved, season labelled retained. Final export refreshes the season; import again after an interim update.
Files are individually atomic; retry both after partial export. `--output PATH` sets the phone destination; laptop adds `-laptop`.
Replacements archive to `~/Basketball_archive_ops`. Visible staging/hidden-flag clearing keeps files selectable.
Only the data-free shell plus `.nojekyll` goes to `gh-pages` (branch source `/`), never models/data/bundles.
No repository CI workflows; built-in Pages deployment provides hosting. Preserve local Git identity/helper.

## App contract

Today prioritises games/player boxes and expandable slate insight. Game Centre shares Q1–Q4/H1/H2/FG selectors across player/team/sheet/scenarios;
FG includes OT for possession games. Future pathway totals/margins are regulation with a separately resolved winner, no player forecasts.
Regular season contains standings/seeds/wins/ratings/races. Cup and Playoffs show coherent stage probabilities; laptop adds exact conditional paths, matchups and series lengths. Initial postseason odds are uncalibrated; calendar/OT assumptions remain expandable.
Teams/Players lead with schedules/rosters/logs and expandable advanced detail. Teams has three headline cards, six expandable profile cards and collapsible form;
Standings collapses threshold controls. Lab is accessible through About, outside primary navigation.

**U24:** one game owns Expected and explicit lineup cases. Its selector controls boxes, sheets, advanced distributions and scenarios;
Compare lineup cases shows win chances/totals. Advanced panels separate raw saved-world counts from weighted probability support,
with nine player/eighteen team box-derived metrics, quantiles, histograms and player-rate scenario links. Phone retains Expected only.
Scenarios offers attempts, combined totals and rates, exact/strict/inclusive comparisons and Core/Shooting/Efficiency/Combined tables.
Current colour is table shading: **Standings → Ratings** shows ranked columns; laptop **Game → Scenarios**, after a condition, shows player deltas.
Game → Analysis exposes 18 team and nine player metrics, distributions and conditions. Shooting zones separates five pooled forecast regions
from recorded ESPN coordinates / 22 derived regions, with sample support and unknowns. Zero denominators stay undefined.
Participation filters mean simulated minutes, not availability or causal effects. Report-band semantics/version live in MODEL.
Advanced links and phone sortable headers have 44px targets. Sortable columns support click/keyboard, direction markers, missing-last order and preserved roster groups. Player directory name/team/stat
sorting covers the full filtered population; other enhanced tables sort displayed rows. Shooting pairs sort by percentage; charts/period axes retain order.
U23 joint-scorer/Q3 outcome stories, offline photos/initials fallback and startup Reload remain. Laptop Saved worlds plays five source-identified examples with seek/step/speed, cumulative boxes and rotations; lineup filters preserve
branch identity. These are generated segments/zones, without tracking or invented passes. Phone retains Expected maps/metrics.
Older snapshots lacking capture show unavailable detail. Phone keeps aggregate competition probabilities; conditional paths stay laptop-only.

Slates are ET; times show UK/ET. Spreads are projected mean margins. Exact float64 minutes drive conditions; display rounds to seconds.
Over is strictly greater than x.5; shooting percentages condition on attempts and show no-attempt mass separately.
Missing denominators/old unavailable periods stay undefined. Dates/counts/versions/thresholds come from loaded data; labelled examples stay illustrative.
Actual/simulated, origin/cutoff/model and pre-tip/retrospective/unverified timing remain explicit; after-tip/unverified forecasts do not establish pre-game accuracy.
Both themes at 1440/960/390, grouped controls, three/two/one card rows and 44 px touch targets are required.

## Verification and code map

```sh
.venv/bin/python scripts/smoke.py
.venv/bin/python scripts/smoke.py --fault
.venv/bin/python -m unittest tests.test_release_gate tests.test_late_clock tests.test_late_clock_recipe tests.test_court_profiles tests.test_court_node_grade tests.test_court_runtime tests.test_state_rotations
.venv/bin/python scripts/check_docs.py
node analysis/browser_check.mjs --base http://127.0.0.1:8767
node analysis/pwa_import_check.mjs --url <shell-url> --bundle <bundle.musnba.gz> --profile laptop
```

Fault must fail. Use `--profile phone` separately; inspect responsive screenshots. The local pre-commit hook runs docs checks.
Fresh clones: inspect existing hooks before `git config --local core.hooksPath .githooks`. Heavy jobs total≤10 compute threads including inner OMP/BLAS.

Core path: `fetch_*`/`history` → `plays`/`possessions`/`rotations` → `features`/`minutes`/`matchups` → `nodes`/`train`/`evaluate`.
`engine.py` simulates, `live_forecast.py` queues canonical chunks, `lineup_forecast.py`/`world_mass.py` preserve exact mixtures,
`pathway.py` supplies ratings; `competitions.py`/`competition_rules.py` build versioned calendar/postseason paths, `nightly*.py` orchestrates, `views.py`/`serve.py`/`webapp/` serve stored results.
`compare.py` grades node runs; `a1_compare.py` grades matched engine distributions; `release_gate.py` requires explicit policy.
Legacy `backtest_compare.py`/`a1_minutes_gate.py` are historical protocols, not generic promotion gates.
Use `--help` and MODEL before launching. Fold backtests require `--clock-recipe` when the production pool cutoff differs from the fold nodes; freeze prior-fitted fold parameters first. Parent preflight rejects mismatched dates before worker startup. `train.py --threads 10` caps fitting; backtest uses `--jobs 10` plus BLAS caps.
Configurations/reports are committed in `models/`/`analysis/experiments/`; fits, raw inputs, per-row arrays/worlds and exports stay ignored under `data/`.
Research uses `analysis/c2_*`/`c3_*`; rich records/fits stay ignored; public reports contain aggregate evidence/hash links.
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
