# Handoff — C03 complete; C04 at 0%

Updated 25 November 2026. C03 closes as a bounded negative search: no demonstrated forecast gain, no qualifying finalist, no production
change. [Completion receipt](analysis/experiments/20261125_c03_completion_v1.json) owns accepted deliverables/reproduction;
[MODEL](MODEL.md) owns numerical results/limits, [PLAN](PLAN.md) strategy, [README](README.md) commands, [AGENTS](AGENTS.md) workflow.
Production remains engine-v1.3-r3, report-bands-v1 and team-pathway-v1. Owner 8766 stays running; review uses 8767. No active jobs.

## C04 — architecture/data-ceiling audit before another learner

**Status: 0% accepted; no C04 implementation, collection, fitting or simulation started.** C02 and all three C03 models failed to
show end-to-end benefit. Their finite samples/capacity and legacy-package differences cannot establish a model-class or data ceiling.
Do not start a third local learner tweak or assume that clocks, opponents, joint learning or more trees are the answer.

Question: which observed information/support or state-dynamics limitation has enough evidenced headroom to justify the next model
comparison? Separate missing/changed information, recorded-context probability errors and feedback through generated states before
choosing another architecture. This is an attribution/representation audit, not a promotion or accuracy-improvement claim.

### Committed capability and bounded decision

Deliver a runnable source-to-state/event-trace comparison workbench, extending the existing choice library and source guards. It must
replay selected complete games, retain causal state/lineup/history and decision probabilities, reconcile emitted choices to saved
player/team boxes, compare recorded-state and generated-state populations, and expose lineage/support differences by feature family.
Provide CLI commands, immutable manifests, independent checks and replayable private traces. Reuse C01/C02 parity/scorers and C03
adapters; no new generic infrastructure phase, standalone dashboard or duplicate source rebuild.

Deliver one evidence-based decision: prioritise a dated-data/coverage challenge, a transition/generator architecture challenge, or
report insufficient attribution and specify the missing evidence. A selected priority is not a proven gain. A no-headroom or unresolved
result must still deliver the working trace/replay capability; do not relabel it major product progress.

### Evidence boundaries and controls

- Use only the same exposed 200 B1 games, their existing common causal arrays, pinned source events/profiles, C01 diagnostics,
  C03 event scores, paired20 worlds and independent negative audit. Old games remain development; no reserved/protected outcomes,
  new provider, market fitting or historical publication-time invention. No new fits or candidate recipes in this diagnostic chunk.
- Freeze three diagnostic views before new traces: source/feature lineage and support; probabilities on identical recorded states;
  generated-state visitation and opportunity/conversion/minute accounting. Hold control and frozen C03-B recipes fixed. Distinguish
  training sample/history, missing inputs and representation changes; do not claim a causal decomposition from associations.
- Trace only the first two frozen wiring IDs, control and C03-B, 1,000 worlds/arm/game, with existing seeds/schedules. Retain full
  state/probability traces for the first 16 world IDs and aggregate visitation for all 1,000. Replayed terminal arrays must equal C03.
  These reruns collect missing transition evidence; they are not another forecast test or a production refresh.
- Use first-game independent 1,000-world replays per arm for reproduction: maximum 6,000 new diagnostic worlds total. No other
  generation/precision extensions. Store private traces under `data/derived/experiments/c04_state_ceiling_v1`; aggregates under
  `analysis/experiments/<actualETdate>_c04_*.json`. Preserve raw responses and completed namespaces.
- Source truth/state may diagnose headroom but never enter deployable predictions. Missing shot-clock/tracking/defender truth stays
  missing. No outcome-dependent inference masks, total targets/quotas, output repairs or variance inflation. Duration, conversion,
  foul/FT/rebound resolution and rotations stay fixed; availability/actual-participant limitations remain explicit.

### Four checkpoints — sequential acceptance, commit and push

|Checkpoint|Weight|Acceptance and dependencies|
|---|---:|---|
|1. Freeze attribution audit|15%|Reuse source/exposure inventory; freeze exact common keys, views/features, native units, support, materiality/uncertainty and decision rule before new trace outcomes. Identify which contrasts are diagnostic rather than causal. Source/future-input/label-mask faults fail. Commit/push before generation.|
|2. Working trace/replay capability|35%|Both arms replay both pinned games; causal trace interface, legal clocks/fives/fouls and event/box identities; terminal arrays equal original C03. Deliberate altered-trace and probability faults fail. Versioned reusable commands and manifests.|
|3. Matched audit and bounded decision|35%|All 200 recorded-state/context comparison plus paired20 saved-score linkage and two-game generated-state audit. Quantify support, sampling/history/package limits and block sensitivity; choose one justified priority or unresolved result by frozen rules. No post-hoc recipes or extrapolated operational skill.|
|4. Reproduce and hand over|15%|Fresh single-worker first-game replay per arm, independently accumulated source/state/accounting summaries and decision reproduction; working capability delivered, honest accuracy status, next concrete 0% charter.|

Accepted deliverable progress is 15/50/85/100%; launched jobs earn no credit. At every checkpoint run affected checks and docs checks,
refresh canonical homes, inspect staged changes, commit and push before dependent work. If source/support or attribution fails, retain
that failure and the working audit interface; never invent missing truth or nominate a mechanism merely to fill the next charter.

### Compute and exact first actions

At most ten heavy threads total, BLAS/OMP/Arrow explicitly capped; no fitting, nested pools, production refresh, season or UI scope.
One generation stream per replay worker; benchmark first trace before estimating time. Bound trace storage to 4GiB; fail with retained
partial evidence if exceeded, without dropping inconvenient rows. Existing source caches and completed controls are immutable.

```sh
git status --short --branch
git --no-pager log --oneline -5
.venv/bin/python scripts/smoke.py
ls -t analysis/experiments/ | head -15
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
.venv/bin/python analysis/c03_reproduce.py source
.venv/bin/python -m unittest discover -s tests -p 'test_c03_*.py'
.venv/bin/python scripts/check_docs.py
```

Then read the C03 completion/negative-audit receipts and the existing context/ZoneObserver interfaces; freeze C04's numerical
attribution contract and exact trace schema, not a preferred replacement model. No C04 jobs are active or required to close C03.
