# Handoff — C07 complete; C08 at 0%

Updated 26 November 2026. [MODEL](MODEL.md) owns forecast results/limits, [PLAN](PLAN.md) strategy,
[README](README.md) commands and [AGENTS](AGENTS.md) workflow. [C07 completion](analysis/experiments/20261126_c07_completion_v1.json) records 2.43% lower player-points error on 159 known games,
but no candidate clears every team/calibration safeguard. C07 is complete; all four checkpoints accepted, production unchanged.
Production remains engine-v1.3-r3/report-bands-v1/team-pathway-v1. No active jobs or new app import. Owner port 8766 stays running; review on 8767.

## C08 — dated participation and whole-roster minute forecasts

**0% accepted; no C08 implementation, fits or generation.** Question: can dated participation forecasts improve unconditional
player minutes/points and joint team forecasts without using the realised participant list? C07 evaluates known historical
participants; that cannot certify pre-tip availability. Current report-band probabilities are uncalibrated; the retained
[coverage gate](analysis/experiments/20261122_a1_s07_dated_cohort_gate.json) found zero dated development report origins. This source/population
challenge addresses a product gap; it does not explain away C07's result or relax any failed rule.

The chain to test is explicit: measured absence/roster error → predictable signal in prior participation/role history → calibrated
joint participation/minute laws → better returned player/team distributions. Establish the error and learnability on a plain
supervised participation task before expensive worlds. Neither oracle-minute headroom nor a new dataset proves forecast improvement.

### Committed capability and three MVPs

Deliver a reusable dated cohort/participation dataset with explicit source support, three runnable joint participation/minute laws,
legal event-world adapters, final player/team proper scoring and independent fit/draw/world reproduction. Add a source-timed capture
adapter using the existing ledger API; report real certified entries separately from synthetic tests. No standalone workbench,
UI, provider expansion, event-head refit, aggregate score/shot targets or unsupported spread change.

Reuse existing participation/cohort helpers in `scripts/a1_availability_cohort.py`, baseline checks in
`scripts/a1_availability_baseline.py`, C04/C05 causal history/minute machinery, C07 weighted scoring/accounting and C01 ledger.
Historical receipts are evidence, not operating instructions; do not run their broad default folds or current-season loaders.

Compare distinct working packages, with exact features/capacity and numerical rules frozen at checkpoint 1:

- **A: shrunk participation-state model.** Learn player/run-length participation probabilities from prior explicit play/DNP labels,
  then use dated conditional minute allocation with uncertainty.
- **B: nonlinear supervised hurdle model.** Learn participation from common dated role/absence history, then conditional minutes. Train all
  supported rows, use training-only chronological selection and record convergence.
- **C: joint team analogue law.** Learn from prior whole-team participation/role patterns, retaining roster dependence rather than
  multiplying marginal probabilities. Map only through forecasted roles and legal eligible-player constraints.

All receive the same supported historical information and training examples. Hold the dated conditional minute law and
event/performance heads common so participation effects remain visible. C07 research gains are not automatically operational inputs. Retain strong
no-report/native-fallback and simple participation baselines. Maximum two training-only configurations/family, no replacement
candidate or development-driven repair. Deliver every mechanically valid two-game adapter, even after a component loss.

### Truth, timing and exposure boundaries

- Existing ESPN/sportsdataverse/NBA Stats only; historical seasons 2023–2026 and the exposed B1 game IDs for development. No protected
  2026–27 outcomes, generic current-season outcome reader or fresh-test claim. Use at most 159 known B1 evaluation games; freeze exact training/selection dates and
  common support before fitting; every feature, normalisation, state and fit precedes its forecast origin.
- Explicit DNP evidence establishes zero participation/counts, including source blanks covered by that flag. Positive reconstructed
  seconds establish play only after reconciliation. Missing/contradictory records stay unknown; never convert absent rows to DNP.
  Reconcile IDs, date/team assignments, game minutes, stat identities, duplicates and source conflicts independently.
- A prior-box cohort is a dated diagnostic, not a verified official pre-tip roster. Quantify stale members, additions, missed actual
  participants and unknown-label forecast mass. Preserve omitted positive players and source gaps in accounting; no convenient
  target-based exclusions or roster-oracle claim. Source eligibility must be fixed before candidate forecasts.
- Injury/report features require original publication/retrieval evidence before tip. A source event date alone is insufficient.
  If historical reports lack timing, compare explicitly labelled no-report laws and keep reports out of every arm. The prospective
  capture adapter must fail closed on late/unknown times; do not backfill historical forecasts as originals or claim operational
  validation from synthetic captures. Real capture/outcome support may require later games and remains a separate reported limit.
- Score participation probabilities after the legal available-roster sampler, not only standalone classifier outputs. Every world
  needs five distinct eligible players, legal fouls/clocks and 240 team regulation minutes plus overtime. Conditioning on legal
  rosters must retain exact probability semantics. Never splice player boxes or invent replacement players.

### Decision and four checkpoints

Before outcomes, freeze useful participation Brier/log-loss benefit, unconditional MIN/PTS proper-score gain, calibration, critical
players, roster/label support limits, team/win harms, multiplicity, precision and stopping. Begin from C07's practical player/team
harm margins, but freeze the policy for this broader population prospectively; old decisions remain unchanged. Unknown support
cannot count as safety. Compare all actual-player and explicit-zero outcomes on common keys, plus separate roster-coverage failures.
Only at most two qualified paths expand from fixed 20 games to the frozen final panel. No automatic production promotion.

|Checkpoint|Weight|Acceptance|
|---|---:|---|
|1. Source population and freeze|15%|Reuse inventory, immutable source/label/cohort/timing audit, measured baseline error, exact recipes/splits/gates/budget; meaningful future-label/DNP/cohort faults; commit/push before fits.|
|2. Working joint participation laws|35%|All three full-history models, training-only credibility, final constrained participation/minute scoring and all first two legal adapters; freeze shortlist.|
|3. End-to-end decision|35%|Qualified paired 20-game/conditional final player/team/critical/coverage comparison, otherwise independently audited bounded stop; real capture counts separate.|
|4. Reproduce and deliver|15%|Fresh fits/probabilities/worker replay, independent source/decision accounting, separate capability/forecast/release conclusions and next concrete 0% charter.|

Every checkpoint: relevant tests/accounting, lean live docs, staged inspection, commit and push before dependent work. Progress
15/50/85/100% measures accepted deliverables. Missing promised models/adapters/reproduction leaves C08 unfinished. If source support
or forecast gains fail, retain that conclusion and distinguish membership ambiguity from participation prediction and allocation
failure. If no admissible cohort can support the promised models, checkpoint the source blocker; do not declare capability delivery.
Engineering alone is not major product progress. Release needs separately frozen evidence and the full online nightly.

### Compute and exact first actions

Ten heavy threads total; fits up to 10 then workers 10×1, BLAS/Arrow 1. At most 606,000 new event worlds including controls, all attempts,
wiring, finalists and independent replays. One supported chronological data build, frozen family fits and one independent final
repeat. Reuse audited artifacts honestly; no budget extension. Private namespace `data/derived/experiments/c08_dated_participation_v1`;
aggregate receipts under `analysis/experiments/`. No production/input/asset changes or full nightly authorised by this charter alone.

```sh
git status --short --branch
git --no-pager log --oneline -5
.venv/bin/python scripts/smoke.py
ls -t analysis/experiments/ | head -15
.venv/bin/python -m unittest discover -s tests -p 'test_c07_*.py'
.venv/bin/python scripts/check_docs.py
```

Read C07 completion/decision evidence, inventory the reusable label/cohort/capture APIs and inspect source schemas/timing metadata.
Do not open protected outcomes. Freeze the C08 contract, support policy and faults before new fitting or simulation. C08 is ready
for execution; it has not begun.
