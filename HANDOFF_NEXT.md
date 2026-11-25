# Handoff — C04 models delivered; 85% accepted

Updated 25 November 2026. [AGENTS](AGENTS.md) owns the changed working culture, [PLAN](PLAN.md) strategy,
[MODEL](MODEL.md) evidence, [README](README.md) commands. C03 remains a completed negative search.
Production stays engine-v1.3-r3, report-bands-v1 and team-pathway-v1. Owner 8766 stays running; review uses 8767.

## C04 — learn joint player roles/minutes, then earn complete-game gains

The owner authorised redesign, presentation and execution. This replaces the unstarted trace-workbench charter prospectively.
Question: can information available before a game predict player minutes better, and do those improvements survive coherent player/team
simulation? C01's real-minute headroom motivates the target; it does not prove predictability. Earlier substitution improvements did
not establish joint forecast benefit. No favoured model or guaranteed accuracy gain.

The [frozen numerical contract](analysis/c04_contract_v1.json) owns recipes, exact features/dates, budgets, thresholds and stopping.
First establish a learnable causal task; then compare complete games. Infrastructure is supporting cost, not fallback product success.

### Frozen design and committed capability

The contract freezes three distinct joint-minute architectures: learned residual correction (A), nonlinear quantile forecasts with
empirical joint dependence (B), and whole-team historical roster analogues (C). All use full supported history and prior-only own/roster
features. Final mean fits precede December 2025; December calibrates uncertainty. Same actual-participant information and exact native
player keys throughout. No arbitrary training-row cap or outcome-driven recipe changes.

All three must fit, predict and generate legal event worlds. Reuse source guards, fixed event/conversion/foul/clocks, rotation/scoring
infrastructure and native stored controls. A bridge control passes native minutes through the same decoder to expose translation.
No shot/point/possession targets, quotas, market fit or variance inflation. Minutes obey legal 0–48/player and 240/team constraints.

First screen all 200 known games' minute distributions. At most two models earning 2% lower minute CRPS with familywise game/week support,
critical-player safety and acceptable 80%-interval coverage proceed. Valid models still deliver first two wiring games. Survivors alone
get first 20 ×1,000 worlds and must improve player PTS by 0.5% against native/bridge controls with acceptable harms. Qualifiers alone
expand to fixed 200 for 1% benefit, uncertainty and joint player/team checks. Development never becomes independent confirmation.

### Four checkpoints — commit/push before dependent work

|Checkpoint|Weight|Required acceptance|
|---|---:|---|
|1. Freeze decisive comparison|15%|Changed culture/charter, full-history causal target/features, three credible recipes and exact budget/selection rules; invalid minutes, future/same-day history and current-label faults fail. Baseline smoke/docs pass. No fitting before commit/push.|
|2. Learnable task and working models|35%|All full-history fits/predictions; training-only convergence/neutral-baseline evidence; all 200 minute screen; first 2 legal event-world adapters and bridge control; complete trial ledger and frozen shortlist. Accepted.|
|3. Complete-game decision|35%|Survivors on20 then conditional 200, proper joint player/team scoring against both references, source/legal/accounting/worker/resume and selection-aware uncertainty. If none survives, independently verify the bounded negative; no unchanged-model ritual rerun.|
|4. Reproduce and deliver|15%|Independent fits/probabilities/minute draws/world replay and decision; reusable model commands/artifacts; honest forecast gain versus accepted deliverables; replace HANDOFF with next concrete 0% charter.|

Accepted deliverable progress is 15/50/85/100%; launched jobs earn no credit. Refresh affected canonical docs and relevant checks at each
checkpoint; inspect staged changes, commit and push. A negative search must name what it ruled out and the remaining confound.

### Compute, failure route and exact first actions

At most ten total heavy threads: fitting 10 then generation 10×1; BLAS/OMP/Arrow1; pool shutdown before parent work. No extra recipes,
selection or precision extensions. Maximum 606,000 new worlds includes conditional finalists and independent replays; reuse native
incumbent worlds honestly. Benchmark first fit/game; estimate only from measured logs. Preserve failed stages for justified technical
repairs without recipe/criterion changes. Private namespace `data/derived/experiments/c04_joint_roles_v1`; aggregates
`analysis/experiments/<actualETdate>_c04_*.json`. Completed evidence and raw sources are immutable.

If dated minute skill fails, say these models did not recover it. If minutes improve while full games fail, report the translation/joint
failure. If native and bridge disagree, keep that confound visible. No class-wide impossibility claim or fourth post-hoc model.

### Accepted evidence and exact next action

Checkpoints 1/2 committed/pushed as `e0e0752`/`ae40636`. All three full-history models fit and improve the proper minute score;
all fail the frozen uncertainty-coverage limit. [Minute screen](analysis/experiments/20261125_c04_minute_screen_v1.json) owns exact results.
No 20/200 game expansion. These are conditional development component gains, not calibrated game improvement or operational confirmation.

The [independent decision audit](analysis/experiments/20261125_c04_decision_v1.json) reproduces simultaneous intervals and the stop.
Both score gains and undercoverage persist on 175 games with exactly reconciled source minutes; source gaps do not explain the pattern.
Existing audits check 1,256,216 lag/truth values, 51,504 minute/half scores and coverage, 8,000 legal wiring worlds and 3,270 game/half scores.
The decoder's mean target error is about 0.5 minutes for challengers, with rare errors near 16 minutes, separate from pre-decoder coverage.
[Trial ledger](analysis/experiments/20261125_c04_trials_v1.json) retains all recipes, capacity evidence and two pre-fit reader repairs.

No active jobs. Logs: `/tmp/c04_data_v3.log`, `/tmp/c04_fits.log`, `/tmp/c04_screen.log`, `/tmp/c04_wiring.log`, `/tmp/c04_audit.log`.
Private namespace holds data/models/draws/completed game receipts. Baseline smoke 118/118; C04 tests 7/7; docs pass.
Exact next: commit/push checkpoint 3, then run fresh independent fits, all-200 minute draws and single-worker world reproduction:

```sh
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
.venv/bin/python analysis/c04_reproduce.py run --output data/derived/experiments/c04_reproduction_v1
```

Report component gains, calibration failure and end-to-end/release status separately; replace this charter with next 0% work.
