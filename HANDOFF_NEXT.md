# Handoff — C04 frozen; 15% accepted

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

### Committed model capability

- Full supported chronological minute-history/roster dataset, no arbitrary training-row cap, same admitted information for every family.
- Three working joint-minute distribution models: A learns corrections to the dated role allocator; B directly learns nonlinear minute
  quantiles with historically learned joint dependence; C resamples analogous whole-team role/minute allocations. These are distinct
  pre-game modelling architectures, not three settings of an event head. Closed-form A, training-only converged B and exact C get a credible fit.
- All three must fit, predict and drive legal event worlds. Reuse source guards, rotation fitter, incumbent event/conversion mechanics,
  scorers and independent accounting. No standalone trace workbench, UI, new provider or platform work.
- Deliver the reusable joint-role/rotation model library, honest comparative evidence and independently reproduced finalists or a
  bounded negative decision that distinguishes predictable-minute failure from failure to translate minute gains into joint forecasts.

### Evidence and decision

All statistical inputs precede origin. Training spans supported December 2022–December 2025 history; model iteration selection uses
October–November 2025 after fitting through June 2025; final means fit through November, joint residual/PIT calibration uses December.
Only historical seasons 2023–2026 are read. Earlier games may update dated features before each evaluation origin; they do not become
fresh tests. Current starters/minutes/labels never enter prediction. Roster membership is the same actual-participant conditional
information used by the incumbent; no operational availability or original pre-tip claim.

Use exactly the known B1 200 games, first 2 for wiring and first 20 for complete-game selection. First compare regulation-minute
distributions cheaply against stored incumbent draws on all 200. A model needs at least 2% lower minute error with game/week
selection-adjusted intervals below zero and acceptable critical-player/coverage behaviour. At most two pass, ordered by minute error.
All mechanically valid families still deliver first 2 ×1,000-world adapters; no knowledge-only completion.

Schedule translation is a named confound. A bridge control sends incumbent minute draws through the exact same new rotation decoder.
Compare candidates with both the native stored incumbent and bridge control. Hold event/duration/conversion/foul/rebound policies fixed.
No predicted full-game shots/points/possessions, quotas, market fit, output corrections or arbitrary variance inflation. Minute totals
are legal time constraints: 0–48 per player and 240 per team in regulation, plus legal generated overtime.

Only minute-screen survivors proceed to 20 games. Require at least 0.5% lower player-points distribution error against both controls,
both simulation halves improving, and frozen player/team harm/runtime limits. Expand only qualifying finalists to fixed 200 ×1,000;
require at least 1% player-points gain, familywise game/week support and acceptable minutes/threes/rebounds/assists, critical players,
team scores/totals/margins/wins and coverage. All initial comparisons remain in multiplicity; development gains are never fresh confirmation.
A research survivor requires separately frozen independent release evidence; no automatic promotion or production refresh.

### Four checkpoints — commit/push before dependent work

|Checkpoint|Weight|Required acceptance|
|---|---:|---|
|1. Freeze decisive comparison|15%|Changed culture/charter, full-history causal target/features, three credible recipes and exact budget/selection rules; invalid minutes, future/same-day history and current-label faults fail. Baseline smoke/docs pass. No fitting before commit/push.|
|2. Learnable task and working models|35%|All full-history fits/predictions; training-only convergence/neutral-baseline evidence; all 200 minute screen; first 2 legal event-world adapters and bridge control; complete trial ledger and frozen shortlist.|
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

Baseline smoke has passed 118/118. Exact next actions:

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_c04_*.py'
.venv/bin/python scripts/check_docs.py
git diff --check
```

Then present this charter at high level, commit/push checkpoint 1, and implement the full-history data and three frozen models.
Checkpoint 1 is accepted: no C04 data/model jobs have started. Source inspection/schema reads only; baseline log `/tmp/c04_baseline_smoke.log`.
