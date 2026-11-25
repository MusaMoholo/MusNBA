# Handoff — C03 executing; 85% accepted

Updated 25 November 2026. [PLAN](PLAN.md) owns strategy, [MODEL](MODEL.md) evidence/evaluation,
[AGENTS](AGENTS.md) workflow, [README](README.md) commands. Production remains engine-v1.3-r3,
report-bands-v1 and team-pathway-v1. Owner 8766 stays running; review uses 8767. No UI/release work.

## C03 — compare possession models, then develop qualifying finalists

Question: which affordable way of learning next event, player and action offers material player/team improvement on common causal
information? [Frozen contract](analysis/c03_contract_v1.json) owns exact recipes, numerical benefit/harm/support limits, feature phase,
selection/multiplicity and compute budget. Checkpoint 1 committed/pushed as `e3c3d98` before fitting; no development-driven recipe changes.

Committed deliverables: three distinct runnable fit/predict/event-world adapters, reusable common choice interface and fair comparison
records; robust integration and independent reproduction of qualifying finalists, or independent reproduction of the bounded negative
search. Deliverable acceptance and accuracy gains are separate. No improvement means no demonstrated product gain.

### Frozen slate and evidence boundaries

- A: separate regularised linear event/actor/action softmax heads with training-only normalisation/missingness and L2 shrinkage.
- B: refreshed separate nonlinear LightGBM event/actor/action heads.
- C: one shared scalar LightGBM scorer over all 43 legal alternatives: five players × eight actions plus three actorless events.
  Shared learned trees determine consistent event/player/action probabilities. No truth-dependent choice mask.
- Common causal-first/prior-position player/team profiles, lineup competition, opponent style/core defensive aggregates and history.
  No new provider, body/tracking/verified-defender claim, full-game target, quota, market fit or score repair.
  Duration, conversion, foul/FT/rebound resolution and rotations stay fixed; defensive-foul FT actor uses the unchanged common resolver.
- Training: supported December 2022–December 2025 history; outcome-blind 60k earlier training and 15k chronological selection events.
  One configuration per family; training-only iteration selection/refit. All features/fits precede origin. Legacy history differences explicit.
- Exactly the 200 already exposed B1 IDs; first20 ×1,000 worlds per mechanically valid arm with common control for shortlist.
  Player-points distribution error is primary; minutes/threes/rebounds/assists, critical players and team points/totals/margins/wins,
  coverage and runtime constrain selection. Both simulation halves must improve. At most two practically promising finalists expand
  to fixed200 ×1,000. Whole-game/week intervals count all three initial comparisons; selection games never become fresh confirmation.

### Four sequential checkpoints

|Checkpoint|Weight|Acceptance|
|---|---:|---|
|1. Freeze comparison|15%|Common interface, three distinct recipes, exact budget/population/decision contract; future-input/probability/label-mask faults; commit/push before fitting. Accepted.|
|2. Working MVP comparison|35%|All fit/predict adapters; independent probability/features; recorded-event scores; legal paired20; complete trial ledger; frozen shortlist. Accepted.|
|3. Finalist comparison|35%|Qualifiers: robust200 integration/player-team uncertainty, worker/resume/accounting; otherwise finish working library and independently check negative comparison, no unchanged-model expansion. Accepted negative route.|
|4. Reproduce/deliver|15%|Fresh independent fits/probabilities/full-game replay per family, reusable commands, honest result, next concrete 0% charter.|

Each checkpoint requires relevant checks, affected live docs, staged inspection, commit and push before dependent work.
Accepted progress is 15/50/85/100%; launched jobs earn no credit.

### Current state and exact continuation

Baseline smoke 118/118 and C02 pinned-source checks pass. All three families fit. Independent source-history reconstruction checks
13,239,520 feature values across 47,284 supported panel events with zero mismatches. Recorded-context scores are retained in
[events receipt](analysis/experiments/20261125_c03_events_v1.json); they are diagnostics, not game improvement.
Private namespace: `data/derived/experiments/c03_possession_options_v1`. Fits, arrays, plans and per-game receipts stay ignored.

Paired20 is complete: 80,000 legal worlds, 427 player-games and no qualifying finalist. [MVP receipt](analysis/experiments/20261125_c03_mvp_v1.json)
and [complete trial ledger](analysis/experiments/20261125_c03_trials_v2.json) retain all results/faults. Independent accounting checks
47,076 scalar/half scores with maximum discrepancy below 1e-12 points. Production unchanged; no demonstrated forecast gain.

No active jobs. Completed command: `.venv/bin/python analysis/c03_rollout.py mvp --jobs 9`, log `/tmp/c03_mvp.log`, session 95422 finished.
All 20 receipts exist under the private namespace. No expansion to remaining180 is permitted; source/signature guards remain active.

Checkpoint 2 committed/pushed as `0439b53`. The [independent negative audit](analysis/experiments/20261125_c03_negative_audit_v1.json)
recomputes all primary/team means, both halves and selection-adjusted game intervals from saved rows. All three fail primary promise,
both halves and the team harm limit independently. Modified source/completed-game resume faults fail closed. No finalist integration
or unchanged-model expansion is warranted. Exact next action after checkpoint-3 commit/push: fresh independent reproduction:

```sh
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
.venv/bin/python analysis/c03_reproduce.py run --output data/derived/experiments/c03_reproduction_v1
```

At most ten heavy threads total; fitting10 then sequential replay, BLAS/Arrow1. No nested pools or further precision.
Two pre-score scoring-loader faults and a 16-world/arm unscored wiring preflight are retained in the trial ledger; no recipe changes.
Finish the negative search honestly; C02/C03 now motivate an architecture/data-ceiling review before another local modelling attempt.
