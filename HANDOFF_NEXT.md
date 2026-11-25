# Handoff — C02 pure possession learning

Updated 25 November 2026. C01 is complete; its [receipt](analysis/experiments/20261125_c01_workbench_v1.json) and [MODEL](MODEL.md)
hold evidence. Incumbent engine-v1.3-r3, availability and season engines remain live. No production/PWA change is planned.
[PLAN](PLAN.md) holds strategy; [AGENTS](AGENTS.md) governs checkpoints; [README](README.md) holds operation commands.

## Active chunk C02 — learn who acts and what happens within possessions

**Status: checkpoint1 accepted — 25% capability complete. Authorised to finish the whole chunk.** The owner requires a pure possession model: player/team shot counts,
points and winners emerge from legal events. Historical team context may inform event probabilities; full-game count/score forecasts
must never guide, constrain or repair the events. Minutes/rotation priors model coaching choices under the legal regulation budget;
they do not justify a shot budget. The previous unstarted count-first charter is replaced before any C02 fitting/scoring.

Question: can newly trained, causally featured actor/action probabilities recover useful player error while preserving team accuracy?
C01 showed outcome-information headroom, not that this mechanism will win. No particular learner or architecture earns protection.

### Committed capability and bounded decision

- Deliver a reusable source-bound possession dataset, chronological fitting path, simple role baseline, swappable probability heads,
  legal simulator adapter, common player/team scoring and independent reproduction. Even a failed challenger leaves working model-building tools.
- Test one frozen challenger: a five-way conditional actor-choice learner and an eight-way action learner. Both use dated causal
  player/lineup/team context; no aggregate target or future remaining-quota feature. All other event, conversion and timing rules stay fixed.
- Decide whether it merits later independent qualification. Accuracy improvement is uncertain; completion requires the full working capability.

The [frozen contract](analysis/c02_contract_v1.json) specifies recipes, numerical research benefit/harm/support limits, uncertainty,
multiplicity and stopping before new predictions. Primary rollout benefit is at least 1% lower player-points distribution error;
team/critical-player harm and calibration limits also apply. Research evidence alone never promotes a model.

### Evidence boundary

Reuse C01's exact 200 exposed B1 development IDs; first20 are wiring. Actual participants/stored simulated rotations define conditional
research, not original pre-tip availability evidence. Training source reads are predicate-bound to 1 October 2024–31 December 2025;
earlier training fits use only earlier origins. October–December 2025 selects stopping rounds; refit the fixed recipe through December.
No reserved/protected outcomes, current-season loader, new provider or market targets. Old games never become fresh confirmation.

Use retained causal-first, prior-position, body-free base profiles; hash source/build provenance and independently check temporal logic.
Read evaluation profile rows only for allowed IDs. Candidate heads must receive these same causal features during recorded-context
scoring and simulation; incumbent features stay untouched for a matched comparison. Exclude unqualified matchup/body features from
new learners. Disclose remaining source revision/actual-participant limits. Preserve C01 artifacts and completed namespaces.

### Four sequential checkpoints

|Checkpoint|Weight|Required acceptance before commit/push|
|---|---:|---|
|1. Data and frozen experiment|25%|Dated source/feature manifest and cached actor/action tables; supported keys, exact five-way labels, missingness/exclusions; meaningful future-input/corruption faults; recipe and numerical criteria frozen before predictions.|
|2. Working learners and screen|25%|Fixed chronological fit/selection/refit, role baseline and full200 recorded-context comparison. Joint actor/action probability error and uncertainty; exact support, proper scoring and deterministic predictions. No panel-driven tuning.|
|3. Pure possession integration|35%|Working adapter, feature parity and legal/scoring/minute/accounting safeguards. Fresh paired control/candidate20 games at1k worlds each, even if screen fails. Remaining180 only if the frozen recorded-context screen passes. No full-game targets; player/team outcomes must come from the actual events.|
|4. Independent operation and decision|15%|Fresh independent fit/prediction and accounting/worker checks; reproducible commands, accepted capability versus accuracy decision, limitations and concrete next0charter.|

Report accepted progress at25/50/85/100%; launching jobs earns no credit. Checkpoints depend on preceding commits/pushes and refresh
affected live docs. Long-job updates include completed counts. Baseline118 smoke passed before changes; source/fault/unit tests
validate the changed research boundary. No browser/production nightly is needed without a production change.

### Compute, stopping and failure route

At most10 total heavy threads: fitting10, generation10 workers×1, never overlapping those heavy pools. Cap OMP/BLAS/Arrow explicitly.
Benchmark20 wiring before estimating full work. Canonical seeds/1k groups; evaluate both500 halves; whole-game and calendar-block
uncertainty. One recipe, no rescue sweep or optional precision extension. No production refresh for a negative research result.

Private namespace: `data/derived/experiments/c02_possession_v2`; aggregate receipts under `analysis/experiments/<actualETdate>_c02_*.json`.
Completed evidence is immutable. Keep row arrays/fits/worlds ignored; preserve replaced dependencies in `~/Basketball_archive_ops`.
If the screen fails, retain incumbent and complete the reusable data/fit/adapter/scoring/reproduction path, including paired20 integration.
Insufficient precision remains unresolved. Never redefine harm/support after outcomes. Any eventual production release requires separate
prospective qualification and all MODEL/AGENTS release checks, including a fresh full online nightly.

### Exact next actions

1. Build source-bound actor/action data and synthetic boundary tests, freeze the contract and source manifest; commit/push checkpoint1.
2. Fit only the frozen recipe, complete recorded-context screen, document and commit/push checkpoint2 before rollout.
3. Run paired20 wiring, then conditional remaining180; complete independent verification and close the chunk.

Checkpoint1: [data receipt](analysis/experiments/20261125_c02_data_v2.json); 1704 training games, 200 known development games.
Cached actor/action keys and missingness are explicit; 11 C02 boundary/probability tests and31 inherited integrity tests pass, including causal
first-season/same-day/position safeguards. Source signature verification passes. No candidate predictions have been produced.
A pre-scoring repair removed an inherited cross-row median: roles now use only the current five, tested against extreme future-row
injection. Original v1 data and interrupted/unqualified fit remain intact; dependencies are archived at
`~/Basketball_archive_ops/20261125_c02_relative_boundary_v1`. Criteria unchanged; no development predictions preceded repair.
Data log: `/private/tmp/musnba-c02-data-v2.log`; no job running. Next commands:
`OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv/bin/python -u analysis/c02_model.py fit`,
then `analysis/c02_model.py screen` with the same interpreter/caps. Implementation and composite-score semantics are frozen before fitting. Do not start rollout until checkpoint2 is committed/pushed.
