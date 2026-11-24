# MusNBA

Offline NBA simulation PWA. Live state/next-agent actions: [HANDOFF](HANDOFF_NEXT.md); scope: [PLAN](PLAN.md);
methods/evidence: [MODEL](MODEL.md); contributor rules: [AGENTS](AGENTS.md).

## Install and update

Install [MusNBA PWA](https://musamoholo.github.io/MusNBA/). Update the app shell, then use **Offline data & installation → Import data**:

|Device|iCloud Drive/MusNBA file|Support|
|---|---|---|
|Laptop|`MusNBA-laptop.musnba.gz`|Full worlds, lineups, scenarios/conditions, replay and competition paths|
|Phone|`MusNBA.musnba.gz`|Expected distributions, shooting maps/metrics and competition aggregates|

Import separately on both devices. Safari/installed iPhone app can have separate storage; keep phone unlocked/app open while importing.
iCloud export and desktop-browser checks do not prove real-device acceptance. Shell updates and data imports are separate.
A checked complete game may publish early with a clearly retained season; import the final update again for the complete generation.
Exports are individually atomic; retry both after interruption. Replaced outputs archive to `~/Basketball_archive_ops`.
Only data-free shell assets go to `gh-pages`; no data/models/bundles or repository CI workflows.

## App behaviour

Today leads with games/player boxes and expandable insight. Game Centre shares period/lineup context across boxes, player sheets,
metrics and scenarios. FG includes OT for possession games. Future-game displayed distributions are regulation only, with a separate
season winner; future games have no player predictions. Dates are ET; times show UK and ET.

Analysis selects **team → team overview/player → that roster**, grouped by starters/bench. Shooting/metric tabs retain selection;
lineup changes preserve compatible player selection. Forecast maps use five pooled court zones; observed shots use recorded coordinates/22regions.
Opponent exposure means shots faced while on court, not a verified personal defender. Historical maps use the last10 recorded team games before origin.
New volume bars, quantile strips, competition progression bars and ratings scatter use saved values; missing samples stay unavailable.
Lineup assumptions are expandable; selected cases open clearly. Tabs support arrow/Home/End keys; controls support keyboard/focus/44px touch targets.
Tables remain sortable with exact keys, missing-last order and roster groups. Charts retain ordered axes and show values alongside colour.

Laptop scenarios support exact/strict/inclusive totals/rates, Given/Joint/duels and lineup comparisons. Participation filters mean simulated
minutes, not availability or causal effects. Five source-identified Saved worlds examples have seek/step/speed, boxes and rotations;
geometry represents segments/zones, without invented tracking/passes. Older snapshots show unavailable unsupported detail.

Regular season covers standings/seeds/wins/ratings/races. Cup/Playoffs use coherent82-game/calendar paths; laptop adds exact weighted
conditions, matchups and series lengths. Initial postseason/OT are uncalibrated; scheduling/matching assumptions are expandable.
Teams/Players show rosters/logs/form/advanced detail. Search and installation remain global; Lab is secondary through About.

Display rounding never changes float64-minute conditions or exact probability mass. Over is strictly greater than x.5; shooting rates
show no-attempt support. Actual/simulated, origin/model and pre-tip/retrospective/unverified timing remain explicit.

## Run and verify

Python3.12+, NumPy/pandas/pyarrow/LightGBM/macOS libomp; Node only for checks.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/nightly_musnba.py --engine 10000 --sims 10000
.venv/bin/python scripts/serve.py --port 8767
.venv/bin/python scripts/smoke.py
.venv/bin/python scripts/smoke.py --fault
.venv/bin/python scripts/check_docs.py
node analysis/browser_check.mjs --base http://127.0.0.1:8767
node analysis/pwa_import_check.mjs --url <shell-url> --bundle <bundle.musnba.gz> --profile laptop
```

Fault must fail; phone imports test separately. Inspect1440/960/390 in both themes. Owner8766 stays running;8767 is review.
The full nightly fetches authorised inputs, rebuilds prior-game inputs and refreshes today/season/views/both bundles. `--ahead` must0.
Missed finals are collected; missing historical possession forecasts are not reconstructed. Serving never fetches/fits/simulates.
`--offline --no-rebuild` needs unchanged-input justification; resume additionally requires `--resume-live-run PATH` and exact guards.
Archive views before standalone rebuilds. Do not bypass retained pre-tip/input guards.

```sh
.venv/bin/python scripts/nightly_musnba.py --export-only
.venv/bin/python scripts/export_musnba.py --shell exports/MusNBA-web --base-path /MusNBA/
```

Export-only reads saved outputs. `--output PATH` sets phone destination; laptop adds`-laptop`.
Core path: fetch/history→plays/possessions/rotations→features/minutes/matchups→nodes/train/evaluate→engine/live_forecast→pathway/competitions→views/PWA.
`compare.py` grades nodes; `a1_compare.py` engines; release gates require explicit policies. Legacy comparators are not generic promotion gates.
Backtests require fold-matched `--clock-recipe`; use≤10 total heavy threads, BLAS caps, `train.py --threads 10` or `backtest.py --jobs 10`.
Configurations/aggregate reports are committed; raw inputs/fits/arrays/worlds/exports remain ignored. Immutable experiment namespaces cannot be overwritten.
Fresh clones inspect hooks before `git config --local core.hooksPath .githooks`; the hook checks lean docs and archive hashes.

## Documentation history

Five core docs plus three frozen promotion policies are live. All live Markdown counts toward budgets.
Completed history is in Git and [one verified archive](docs/archive/20261123_document_history.tar.gz),
with [44-member hash manifest](docs/archive/20261123_document_history.manifest.json) and external backup `~/Basketball_archive_ops/docs_20261123_a2_close`.

```sh
tar -tzf docs/archive/20261123_document_history.tar.gz
tar -xOf docs/archive/20261123_document_history.tar.gz docs/archive/2026-11-23-before-lean/HANDOFF_NEXT.md
```

Extract relevant sections only. Historical instructions are not current actions; replay old sources in isolated checkouts, never restore stale docs over this root.
