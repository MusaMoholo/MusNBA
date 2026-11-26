# MusNBA

An NBA simulation and forecasting PWA. We are rebuilding the development process around measured player/team accuracy,
credible uncertainty and coherent play-by-play. The working product remains available while challengers earn replacement.

Start with [PLAN](PLAN.md) for the new strategy, [HANDOFF_NEXT](HANDOFF_NEXT.md) for the only executable next chunk,
[MODEL](MODEL.md) for model/evaluation definitions and [AGENTS](AGENTS.md) for contribution rules.
Previous roadmaps and unfinished commitments are removed. Historical evidence is not an operating plan.

## Install and use

Install [MusNBA](https://musamoholo.github.io/MusNBA/). Update the app shell, then use **Offline data & installation → Import data**.

|Device|iCloud Drive/MusNBA file|Current support|
|---|---|---|
|Laptop|`MusNBA-laptop.musnba.gz`|Full saved worlds, lineup cases, scenarios, replay and competition paths|
|Phone|`MusNBA.musnba.gz`|Expected distributions, player/team analysis and competition aggregates|

Import separately on both devices. Safari and the installed iPhone app can have separate storage. Keep the phone unlocked/app open
while importing. Desktop browser automation and iCloud export do not prove real-device acceptance. Shell updates and data imports
are separate. Early checked games can publish with an explicitly retained season; import the final update for a complete generation.
Exports are individually atomic; retry the pair after interruption. Only the data-free shell goes to Pages, never models or bundles.

## What the current app shows

Today leads with games/player boxes. Game Centre shares period and lineup context with player sheets, metrics and scenarios.
Possession-game full-game predictions include OT. Later team-pathway game score distributions are regulation-only, with separate
season winners and no invented future player predictions. Slate dates are ET; tip times show UK and ET.

Analysis selects a team and then its overview/player. Shooting maps distinguish generated pooled zones from recorded coordinates;
observed opponent exposure is not verified personal defence. Rotation maps use all saved weighted worlds at 48 regulation minute
midpoints, with quarter/time controls, player curves and a sortable roster. They are separate from continuous-minute forecasts;
older snapshots without capture show unavailable. About includes saved model-study results and unresolved accuracy limitations.

Laptop Scenarios/Given/Joint/duels select exact stored worlds; association is not causation. Five source-identified replays
illustrate clocks/boxes/rotations, not population probabilities or unobserved tracking. Rounding never changes exact probability
weights or float64-minute conditions. Missing/no-attempt support and older timing/semantics remain explicit.

Regular season, Cup/playoffs, Teams/Players and global search use retained results; scheduling/postseason calibration limits remain.
The app and its tests are reviewable; existing functionality is not proof of forecast accuracy.

## Run and check

Python 3.12+, the existing NumPy/pandas/pyarrow/LightGBM stack and macOS libomp; Node is for browser checks.

```sh
.venv/bin/python scripts/serve.py --port 8767
.venv/bin/python scripts/smoke.py
.venv/bin/python scripts/smoke.py --fault
.venv/bin/python scripts/check_docs.py
node analysis/browser_check.mjs --base http://127.0.0.1:8767
node analysis/pwa_import_check.mjs --url <shell-url> --bundle <bundle.musnba.gz> --profile laptop
```

The inherited smoke/fault commands remain regression checks; the C01 inventory records their protection and gaps. A passing count is not predictive validation.
Use 8767 for review; owner 8766 stays running. Pure docs/research checkpoints do not trigger a full production refresh.

C01 provides separate synthetic/fault and pinned-source checks:

```sh
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
.venv/bin/python -m unittest discover -s tests -p 'test_c01_*.py'
.venv/bin/python analysis/c01_run.py source
.venv/bin/python analysis/c01_run.py reproduce --jobs 10
.venv/bin/python analysis/c01_run.py ledger-audit
```

`source` checks pinned hashes/private fixtures without fitting or simulation. `reproduce` creates a fresh ignored namespace and
recreates fits, baseline draws, oracle/event scores and aggregate conclusions from pinned inputs; incumbent/zone worlds are reused
as inputs. Completed experiment stages refuse overwrite. The legacy-test inventory stays private with the foundation manifest.
`ledger-capture --request PATH` requires all artifact hashes and model/input/report/retrieval/generation times; see
[the capture API](analysis/c01_ledger.py). Unknown/late evidence fails closed. Historical snapshots are never backfilled as originals.
The separate browser/release commands above cover UI/delivery; research commands do not publish or promote a model.

Research is isolated from serving/release. Completed stages refuse overwrite; expansion requires the frozen survivors. Private
fits, draws and worlds remain ignored. MODEL links numerical decisions; contracts/receipts retain exact recipes and namespaces.

|Completed research|Fresh reproduction command after `.venv/bin/python`|
|---|---|
|C02/C03 possession learners; C04 joint minutes|`analysis/c02_reproduce.py`, `analysis/c03_reproduce.py`, `analysis/c04_reproduce.py`: each has `source` and `run --output <new-private-directory>`|
|C05 minute uncertainty and exact rotations|`analysis/c05_reproduce.py --output data/derived/experiments/c05_reproduction_v1`|
|C06 full-history actor choice|`analysis/c06_reproduce.py --output data/derived/experiments/c06_reproduction_v1`|
|C07 coherent expert selection|`analysis/c07_reproduce.py --output data/derived/experiments/c07_reproduction_v1`|

Use the thread caps above and a fresh output directory. Source hashes guard retained inputs; preserve partial faults before technical
resumption. C06 supports provenance-checked `--resume`; other stages need their recorded exclusive namespace. Reproduction does not
make explored games fresh evidence or promote a model. C07 checks weighted player/team distributions, fresh gates and four world
replays. Its source check is `.venv/bin/python -c "from analysis.c07_data import verify; verify()"`; independent final accounting is
`analysis/c07_audit.py final` (completed evidence refuses overwrite). C08's executable first actions and boundaries live only in HANDOFF.

For a qualified production/input/generation release:

```sh
.venv/bin/python scripts/nightly_musnba.py --engine 10000 --sims 10000
.venv/bin/python scripts/nightly_musnba.py --export-only
.venv/bin/python scripts/export_musnba.py --shell exports/MusNBA-web --base-path /MusNBA/
```

The full nightly fetches authorised inputs, rebuilds prior-game inputs and creates today/season/views/both bundles. `--ahead` is 0.
Export-only reads saved outputs; `--output PATH` changes the phone destination and laptop adds `-laptop`.
`--offline --no-rebuild` needs recorded unchanged-input justification; resume needs `--resume-live-run PATH` and exact guards.
Serving never fetches, fits or simulates. Preserve replaced outputs/dependencies outside the repo before replacement.
Use at most ten total heavy threads including inner BLAS/OMP/compression. No repository CI workflows; existing local hooks check docs.

## Evidence and document hygiene

Five core docs are the live handover. Three immutable historical qualification files under `docs/protocols/` remain solely because
reproduction tools reference them; they impose no new roadmap or automatic future gates. Old numerical decisions remain as recorded.
Older document snapshots are in [the verified evidence archive](docs/archive/20261123_document_history.tar.gz), with its
[hash manifest](docs/archive/20261123_document_history.manifest.json), and Git. Do not load them as current instructions.
Run an old experiment from its recorded commit in isolation, not by restoring old plans over the current handover.

Aggregate evidence/configurations are committed; raw inputs, fits, row arrays, worlds and exports remain ignored. Never overwrite
completed evidence or commit secrets/data/bundles. Preserve the existing identity/helper and history on `MusaMoholo/MusNBA` main.
Keep live docs lean: one canonical home per fact, current charter replaced at each closure, later possibilities kept provisional.
