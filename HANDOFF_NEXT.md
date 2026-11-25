# Handoff — C03 comparison frozen; 15% accepted

Updated 25 November 2026. [C02 is complete](analysis/experiments/20261125_c02_completion_v1.json); its decision is unchanged.
[PLAN](PLAN.md) owns strategy, [MODEL](MODEL.md) evidence/evaluation, [AGENTS](AGENTS.md) workflow, [README](README.md) commands.
Production stays engine-v1.3-r3, report-bands-v1 and team-pathway-v1. No active jobs. Owner 8766 stays running; review uses 8767.

## C03 — compare several possession models, then develop the strongest

**Status: checkpoint 1 accepted (15% deliverables); no forecast gain claimed.** The owner authorised execution.
The [frozen numerical contract](analysis/c03_contract_v1.json) owns exact recipes, budgets and selection. No C03 fitting/scoring yet.
Baseline smoke passes 118/118; C02 pinned sources and docs pass. Probability, future-input and current-label-mask faults fail closed.

Question: which affordable way of learning possession decisions offers material player/team forecast improvement on the same
causal information? The focus is opportunity generation: next event, player and action. Joint learning is one option, not the objective.
C01 showed information headroom; C02's narrower input/history/learner package lost without isolating the cause. Reuse that work.

### Chunk design and committed deliverables

- Reuse C01/C02 source guards, causal features, scoring, simulation mechanics and reproduction. Add only shared support needed by
  the candidate comparison; no new standalone infrastructure phase beyond the first checkpoint.
- Build three small working alternatives on the same supported decisions, dated player/lineup/opponent/context features and history.
  Each must fit, predict and drive legal event worlds; seeds or minor settings do not count as distinct approaches.
- Compare all valid MVPs cheaply before investing in one or two finalists. Keep the unchanged incumbent as the common reference.
  Freeze a maximum of two training-only configurations per family and one selected MVP recipe per family before development scoring.
- Deliver the reusable candidate library/common choice interface and fair comparison records. Develop and independently reproduce
  only qualifying finalists. Do not polish or rebuild losing prototypes after the stopping rule rejects them.

Engineering acceptance requires runnable, tested outputs. It does not imply major product progress: if no model improves forecasts,
report a completed negative search and no demonstrated product gain. A missing committed deliverable leaves the chunk unfinished.

### The three MVP families

|Option|Smallest credible implementation|Question it tests|
|---|---|---|
|A. Simple role/context choice|Regularised probabilistic event/player/action choices using dated role rates, lineup competition and qualified opponent/context features; explicit shrinkage/missing support|Can a simpler, strongly regularised model use the available information better?|
|B. Refreshed separate learners|Nonlinear event, actor and action learners trained separately on the full supported common information/history; comparable selection allowance|Does a stronger version of the existing decision structure recover the opportunity error?|
|C. Shared possession-choice learner|One parameter-sharing scorer over legal next outcomes, with consistent event/player/action probabilities derived from it, including actorless events|Does sharing learned effects across decisions improve predictions?|

Use the existing NumPy/pandas/LightGBM stack. Exact features, legal labels, learner settings, capacity/compute budgets and decoder
are frozen at checkpoint 1. All families get the same training/selection origins and admitted information. Record capacity differences;
use matched subsets/ablations only if prospectively included. The legacy incumbent's different history remains explicit.
Separately fitted conditionals already describe a joint law; multiplying them is not a new shared learner.

### Pure possession boundary

All MVPs predict the next event from current state and dated information. Shots, points and winners emerge from the generated events.
No full-game shot/point/possession targets, remaining quotas, output repairs, market fitting or arbitrary uncertainty inflation.
Historical team/opponent information is permitted as context. Keep duration, conversion, rebound/foul resolution and rotations fixed.
Missing tracking is not invented; opponent exposure is not verified personal defender responsibility.

### Evidence, selection and stopping

- Use the exact 200 exposed development IDs in `analysis/experiments/20261124_b1_development_v2.json`, first 20 for short rollouts.
  They remain known development, never independent confirmation. Training may span supported December 2022–31 December 2025 history.
  Every feature, prior, assignment, normalisation, calibration and fit precedes its origin. No reserved/protected outcomes or new providers.
- Reuse causal-first/prior-position profiles. Audit opponent-feature lineage before admission; all MVPs receive the same qualified
  bundle and support. Freeze exclusions/missingness before scores. Validate feature phase and forbid current-label-dependent inputs/masks.
- Freeze numerical useful gains, practical player/team harms, support/calibration requirements, multiplicity, shortlist rule, maximum
  finalists, precision and stopping before fitting/scoring. Keep a complete recipe/trial ledger, including failed implementations and
  training-only selection. No development-driven recipe changes, replacements or budget extensions.
- Score next-event probability/calibration and branch/context errors for each MVP. Give every mechanically valid MVP a 20-game,
  1,000-world/game rollout with the common incumbent control. Complete-game player/team results inform the shortlist; a next-event
  score alone neither establishes game improvement nor selects a product winner. Source-invalid or mechanically invalid MVPs fail closed with the reason retained.
- Shortlist at most two candidates with predeclared practical promise and acceptable harm/runtime. Being least bad is insufficient.
  If early evidence cannot distinguish two credible paths, carry both within the fixed cap instead of declaring a winner from noise.
  Expand only finalists and required controls to the fixed 200 at 1,000 worlds/game. Reuse audited compatible control worlds honestly.
- Primary game benefit is player-points distribution accuracy, with minutes/threes/rebounds/assists, critical-player harms and joint
  team points/totals/margins/wins/calibration judged together. Whole-game/calendar-block uncertainty and both simulation halves apply.
  All initial MVP comparisons count in selection/multiplicity; selection-panel gains never become fresh confirmation.

A predeclared survivor can be recommended for independent qualification. Production changes still require separately frozen independent
release evidence; if no eligible untouched evidence exists, retain research status. No automatic promotion of the best development score.

### Four checkpoints — sequential acceptance, commit and push

|Checkpoint|Weight|Required acceptance|
|---|---:|---|
|1. Reuse and freeze the comparison|15%|Only necessary common data/feature support; three distinct recipes and budgets; exact choice/population/selection contract. Meaningful future-input/invalid-probability/label-mask faults fail. No fitting before commit/push.|
|2. Working MVPs and cheap comparison|35%|Fit/predict adapters for all three families, independent probability/feature checks, recorded-context scores and 20-game event-generated rollouts for valid MVPs. Same information/support; complete trial ledger. Shortlist at most two by the frozen rule.|
|3. Finalist development and full comparison|35%|Finalists get robust integration, proper player/team scoring on 200 known games, legal/accounting/worker/resume checks and selection-aware uncertainty. If none qualifies, finish the working MVP library and independently check the negative comparison; no expensive unchanged-model rerun.|
|4. Reproduce and deliver the decision|15%|Fresh independent finalist fits/probabilities/world replay, or fresh reproduction of the bounded negative search. Reusable candidate commands/artifacts; report product gain, research result and accepted deliverables separately; next concrete 0% charter.|

Accepted deliverable progress is 15/50/85/100%; launched jobs earn no credit. Refresh affected live docs, inspect staged changes and
commit/push before dependent work. Report long-job completed counts. Session stops record exact commands/logs/session/namespace,
counts, blockers and next action. No arbitrary deadline or unsupported runtime promise.

### Failure route, compute and scope

If a finalist earns all frozen requirements, deliver its research/qualification package and measured limitations. If none wins,
retain production, deliver the runnable distinct MVPs and reproducible comparison, and explicitly report no demonstrated forecast gain.
A whole-slate failure triggers review of the bottleneck, representation or data ceiling before another modelling chunk; no fourth
post-hoc idea or repeated one-recipe tweak. Do not rewrite old decisions or invent a winner to satisfy the desire for progress.

Training uses a common outcome-blind capped sample spanning supported December 2022–December 2025 history: 60k earlier
events and 15k chronological selection events. A uses separate L2 linear choices, B separate nonlinear heads, C a single
shared scalar tree scorer over 43 legal alternatives. Defensive-foul FT actor selection stays the common fixed resolver.

At most 10 total heavy threads, counting concurrent fits/workers/inner pools/compression/validation; cap OMP/BLAS/Arrow and reduce
under memory pressure. Share caches, overlap safe independent work and benchmark the first fit/rollout before estimating cost.
MVP and finalist work share the same precommitted total budget; any technical rerun preserves the old evidence and explains the fault.
Private namespace: `data/derived/experiments/c03_possession_options_v1`; aggregates: `analysis/experiments/<actualETdate>_c03_*.json`.
Version new components; preserve closed evidence/dependencies in place or `~/Basketball_archive_ops`.

No UI/platform/season scope. A production/input/generation release additionally needs all MODEL/AGENTS checks, affected bundles and
a fresh full online nightly against the existing 3600-second ceiling. Actual-participant and raw publication/revision limits remain explicit.

### Exact next actions

```sh
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
.venv/bin/python -m unittest discover -s tests -p 'test_c03_*.py'
.venv/bin/python scripts/check_docs.py
```

After checkpoint-1 commit/push: implement source-bound common arrays, three fit/predict adapters, recorded-context scoring and
paired20 rollouts. Finish all MVPs before finalist investment. No active C03 jobs yet; private namespace above is unused.
