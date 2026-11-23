# MusNBA

Local-first NBA player/game/season simulations: **10,000 possession worlds for today's ET games**, then
**10,000 seasons** using each world's own evolving team ratings from tomorrow onward. Accepted engines:
**engine-v1.3-r2 / team-pathway-v1** (unchanged v1.3 fitted nodes). The laptop PWA is primary; phone is stripped. Stored lineup branches are delivered on laptop; the 2-D
View Centre remains future work. See [HANDOFF](HANDOFF_NEXT.md) for current state and [docs index](docs/README.md)
for focused references/history; contributors start with [AGENTS](AGENTS.md).

## Setup and daily use

Python 3.12+, NumPy, pandas, pyarrow, LightGBM; macOS LightGBM requires libomp. Node is optional for browser checks.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/nightly_musnba.py
.venv/bin/python scripts/serve.py
```

The wrapper collects permitted ESPN/NBA Stats inputs, rebuilds current-season inputs, simulates today's games
and future season, writes snapshots/views and exports to iCloud after success. `nightly.py --ahead` must be zero;
a game-free day still builds a fresh season. Use `--offline --no-rebuild` only for recorded current/unchanged inputs.
The server at :8766 belongs to the owner; use `serve.py --port 8767` for agent review and never stop :8766.
Serving/browsing never fetches, fits or simulates.

Late refresh preserves matching verified pre-tip games and their provenance, rejects invalid/cross-tip replacements
and guards interrupted snapshot publication. All-retained live delivery was tested; mixed collections remain
untested. Do not bypass guards. Archive existing views outside the repo before invoking `scripts/views.py` to rebuild;
`--help` is read-only.

## PWA and iCloud

App: [MusNBA](https://musamoholo.github.io/MusNBA/). Public source:
[MusaMoholo/MusNBA](https://github.com/MusaMoholo/MusNBA). Pages contains the data-free shell only.

Install the website as an app. In **Offline data & installation → Import data**, select from iCloud Drive/MusNBA:

| Device | Bundle | Contents |
|---|---|---|
| Laptop | `MusNBA-laptop.musnba.gz` | Saved worlds, Scenarios/Given/Joint/duels and distributions. |
| Phone | `MusNBA.musnba.gz` | Distributions; no world-dependent tools or lineup branches. |

Each device imports separately; Safari and the installed iPhone app may use separate storage. Keep the app open
and phone unlocked during import. An app-shell update does not import new simulations. Manual device import/
memory acceptance remains necessary; exact current delivery sizes/checks are in HANDOFF.

```sh
.venv/bin/python scripts/nightly_musnba.py --export-only
.venv/bin/python scripts/export_musnba.py --shell exports/MusNBA-web --base-path /MusNBA/
```

Export-only reuses completed snapshots. Both bundles publish after the nightly, not game-by-game. Each file
is atomic, the pair is not; retry both after partial export. `--output PATH` overrides the phone destination,
with `-laptop` added for laptop. Replaced artifacts archive to `~/Basketball_archive_ops`; visible staging and
hidden-flag clearing keep exports in Finder/file pickers. Only shell contents and `.nojekyll` go to `gh-pages`
(branch source `/`), never datasets/models/bundles. Existing local Git identity/helper stays unchanged.
There are no repository CI workflows; GitHub's built-in Pages deployment serves this branch.

## Verification

```sh
.venv/bin/python scripts/smoke.py
.venv/bin/python scripts/smoke.py --fault
.venv/bin/python scripts/check_docs.py
node analysis/browser_check.mjs --base http://127.0.0.1:8767
node analysis/pwa_import_check.mjs --url <shell-url> --bundle <bundle.musnba.gz> --profile laptop
.venv/bin/python analysis/export_visibility_check.py
```

The deliberate fault must exit nonzero. Browser checks cover both themes at 1440/960/390; inspect screenshots.
Use `--profile phone` for the stripped bundle. Baseline smoke is 108 checks at the current checkpoint; version,
cutoff, import/offline and model/accounting gates are described in AGENTS/TRAINING, not inferred from counts.

Documentation budgets/links/archive integrity run at every local commit through `.githooks/pre-commit`.
This checkout has it enabled; for a fresh clone, inspect existing hooks first, then enable with
`git config --local core.hooksPath .githooks`. Checks stay local (D52); do not add GitHub CI pipelines.

## Model work and file map

Rebuild order: history → possessions → rotations → features → nodes → train. Use isolated variants and frozen
populations/hashes; never overwrite served inputs during research. Model version configs live in `models/`;
ignored fitted artifacts in `data/models/`; raw/derived/snapshots/views in `data/`. Experiment reports are committed
under `analysis/experiments/`, per-row arrays/captures stay ignored under `data/derived/experiments/`.

| Files | Role |
|---|---|
| `basketball_common.py` | Paths, identities, ET/UK, atomic writes and archives. |
| `scripts/fetch_espn.py`, `fetch_nbastats.py`, `history.py` | Permitted retained providers/history; NBA one polite resumable stream. |
| `scripts/plays.py`, `possessions.py`, `rotations.py` | Canonical events, reconciled segments/periods, stints/opportunities. |
| `scripts/features.py`, `minutes.py`, `matchups.py`, `realmatch.py` | Dated player/lineup inputs, D29 targets, implicit/real assignments. |
| `scripts/nodes.py`, `train.py`, `evaluate.py`, `compare.py`, `aggregate.py` | Cached datasets, fold models, node gate and teacher-forced aggregation. |
| `scripts/engine.py`, `backtest.py`, `backtest_compare.py`, `a1_compare.py` | Possession worlds, matched engine tests, legacy and strict A1 comparisons. |
| `scripts/pathway.py`, `season_backtest.py`, `projection.py`, `season_stats.py` | Per-world team seasons, historical calibration, packaging/stats/placeholder. |
| `scripts/nightly.py`, `nightly_musnba.py`, `views.py`, `serve.py`, `export_musnba.py` | Pipeline, snapshots, read-only app and PWA delivery. |
| `scripts/live_forecast.py`, `lineup_forecast.py`, `forecast_output.py`, `world_mass.py` | Offline world queue, stored lineup cases and exact weighted summaries; independent-fit queue is runtime-gated. |
| `scripts/player_worlds.py`, `lineup_minutes.py`, `player_icons.py` | Precise world/CDF storage and retained offline photo catalogue. |
| `scripts/webapp/`, `analysis/*.mjs` | Native ES-module UI, browser/PWA checks; no build dependency. |
| `scripts/a1_*.py`, `scripts/a2_*.py`, `analysis/a1_*` | Research/audits; [branch runbook](docs/research/a1_branches.md), frozen protocols and old full command map via docs index. |

`scripts/foul_out.py:Rule3Policy` passed its single protected confirmation; qualified r2 is delivered
with lineup/headshot PWA bundles; HANDOFF owns current generation state.
`tests/test_foul_out.py` covers isolated accounting/rule cases. D56's per-world fitter and shared ten-worker
world queue are qualified/default r2; recorded older runtimes retain their original fitting behaviour.

`scripts/release_gate.py` applies the current class-specific statistical compatibility gate; it never publishes
or promotes a model. Default policy: [v2](docs/protocols/promotion_v2_20261123.md); explicit
[v3](docs/protocols/promotion_v3_20261123.md) requires fresh frozen confirmation after the documented audit.

`scripts/a1_prior_roster_screen.py` and `analysis/a1_prior_roster_audit.py` census/reconstruct prior-box
membership and required starter-position coverage without reading outcome columns or generating forecasts.

`analysis/rule3_confirmation.py` runs the frozen opt-in paired rule checks (`--pilot`, `--stress`,
`--stream-check`, verified `--resume`). Set OMP/BLAS threads to one and budget its `--jobs` across all runs.
`analysis/rule3_capture_audit.py` independently reconciles captures; `analysis/rule3_scores.py` reports v2 bounds.
`analysis/rotation_confirmation.py` and `rotation_final.py` qualify D56 with reused controls and a frozen,
once-only protected run; HANDOFF owns active namespaces, logs and stop conditions.
`analysis/a2_{shared_shooting,world_diagnostics}.py` implement the frozen A2 diagnostics, without fitting factors.

Use `--help` to inspect a runner before choosing controls. Heavy compute totals at most ten threads; actual
`--jobs` × inner-thread settings matter (AGENTS §6). Examples after protocol/namespace freeze:

```sh
.venv/bin/python scripts/train.py --config <candidate.json> --threads 10 --folds F4
OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv/bin/python scripts/backtest.py --config <candidate.json> --fold F4 --games 200 --worlds 1000 --jobs 10 --rotation targets --pool 0
.venv/bin/python scripts/a1_compare.py <control-run> <candidate-run> --output <new-report.json>
.venv/bin/python scripts/season_backtest.py --help
```

`--game-ids` fixes selected games; `--simulation-stream 1` changes draws without game selection;
`--seed-key` shares a starting namespace, not guaranteed event-aligned RNG. Legacy comparisons use actual-starter
tiers; A1 uses pre-game tiers, strict matching and unmodified probabilities (zero winner probability gives
infinite log loss). Neither exploratory output nor an interval alone is a promotion decision.

Historical forecast replay is **deferred (D40)**. Existing `--backfill-days` is a labelled placeholder workflow,
not a possession replay. Preserve archives; no runnable engine-reconstruction command is implied. Refitting/
promotion automation and full availability modelling are also unfinished; consult HANDOFF before launching work.
