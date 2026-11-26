# Handoff — C05 complete; C06 at 0%

Updated26November2026. MODEL owns numerical evidence and limitations; PLAN strategy, README commands, AGENTS workflow.
[C05 completion](analysis/experiments/20261126_c05_completion_v1.json) records minute/player-point skill into legal games but fails the critical-player harm guardrail. Production remains
engine-v1.3-r3/report-bands-v1/team-pathway-v1. No release/publication/manual import. Owner8766 stays running; review8767.

## C06 — full-history competition for on-court scoring opportunity

**Checkpoint 1 ready for acceptance; no C06 data/fits/outcomes.** [Exact frozen contract](analysis/c06_contract_v1.json) specifies the common uncapped information, one recipe per family, selection/critical limits and total budget. Baseline smoke118/118 and three synthetic law/label/future faults pass. Question: does a fair full-history actor-probability competition improve the allocation
of player opportunities, including high-usage players, and then improve coherent player/team forecasts? C05 improves bench players
most; its34 high-usage player-games gain little minute accuracy and worsen point forecasts. That does not identify the cause.
C01's extra actual-attempt headroom is diagnostic only. C02/C03's capped/mismatched learners did not establish an architecture/data
ceiling. This chunk challenges that confound with common full supported history and a plain supervised conditional-actor task.
It does not relax C05's failed rule or expand its rejected model.

### Committed capability and fair MVPs

Deliver an uncapped source-keyed actor dataset, three trained runnable conditional actor laws and legal event-world adapters,
with training-only convergence evidence, full200 recorded-context proper scoring, final player/team scoring and independent
fit/probability/world reproduction. Reuse C03 source/choice builders, C02 causal runtime view, C01 scorers and retained controls.
No new provider, UI, event/action/conversion refit, availability claim, standalone workbench or production change.

All three receive identical historical examples and dated common C03 context/player information. Compare (A) independently trained
nonlinear Bernoulli player-actor probabilities normalised over the five; (B) regularised conditional-logit actor choice with
lineup-relative features/context interactions; (C) nonlinear grouped-softmax actor choice. All define one positive probability law
over five eligible players. A's training objective differs from B/C; evaluation always scores the normalised returned law.
One recipe per family; no outcome-driven fourth recipe. Retain fixed causal usage-share and uniform baselines plus incumbent.
Capacity, selection, regularisation and numerical gates are frozen in the contract before data/fits/scores.

### Evidence, decisive contrast and limits

- Existing seasons2023–2026 only, history2022-12-01 through2025-12-31. Chronological selection Oct–Nov2025; final pre2026 refit
  includes December with selected iterations fixed. Common uncapped supported history, no speed-motivated sampling.
- Reuse only exposed B1's200 IDs for development. Source-supported nonheave shot/fouled/turnover actions whose actor is in the
  reconstructed offensive five; exact keys/truth common to every model. Actorless outcomes and defensive-foul actor resolution
  remain incumbent. No protected/reserved outcomes, fresh-test claim or operational participation claim.
- Primary component score is log probability of the actual actor (lower better), compared on identical keys with native incumbent
  and usage baseline. Also Brier score, star-actor reliability, support by game/week/role/close context, final probabilities after
  normalisation and training/runtime parity. Do not infer box gains from next-event gains.
- Freeze component benefit, calibration/critical-player harms, support, multiplicity3, shortlist<=2, point/uncertainty limits and
  stopping before outcomes. All three get first2×1000 legal wiring. Only qualified actors reach first20, then conditional200,
  preserving native and compatible-replay controls. Reuse audited compatible control worlds honestly; no unchanged production rerun.
- Fixed native rotation inputs in every C06 arm isolate actor effects; C05's rejected minute law is not an eligible challenger.
  Events sample actors; scores/counts emerge from events. No full-game shot/score targets or aggregate steering.
- Decisive contrast: same actor information/history, distinct probability learners. Common reduced information versus the incumbent
  remains an explicit package confound. A loss cannot establish an NBA predictability ceiling. A gain is known-development only;
  independent chronological/operational release evidence remains separate.

### Four sequential checkpoints

|Checkpoint|Weight|Acceptance|
|---|---:|---|
|1. Freeze fair architecture/data challenge|15%|Reuse inventory, exact numerical recipes/gates/budget, source/label/probability/expansion faults; commit/push before data/fits.|
|2. Deliver full-history actor laws|35%|All examples used, three fits and training-only convergence, matched recorded-context scoring, independent source/feature checks and all three first2 wiring adapters; frozen shortlist.|
|3. Returned-world decision|35%|Qualified paired20/conditional200 full player/team/critical/uncertainty comparison, otherwise independent bounded stop; no criterion changes.|
|4. Reproduce and hand over|15%|Fresh fit/probability/worker reproduction; honest capability/component/game/release conclusions; lean live docs and next evidence-led C07 charter at0%.|

At each checkpoint: proportionate tests/accounting, refresh docs, inspect staged changes, commit/push before dependent work.
Progress15/50/85/100% measures accepted deliverables. Missing promised models/adapters/reproduction leaves the chunk unfinished.
Major forecast improvement cannot be promised; a negative search must be called negative and isolate the remaining confound.

### Compute and exact first actions

Ten heavy threads maximum, BLAS/Arrow1; fitting10 then workers10×1, no nested pools. One yearly source pass, one recipe per family
with training-only selection/final refit and one independent repeat; at most606000 new event worlds including wiring/replays.
Stop before extra fitting or simulations beyond the frozen budget. Private namespace `data/derived/experiments/c06_actor_full_history_v1`;
aggregate receipts `analysis/experiments/20261126_c06_*`. Preserve technical failures and source-hash-guarded resume.

```sh
git status --short --branch
git --no-pager log --oneline -5
.venv/bin/python scripts/smoke.py
ls -t analysis/experiments/ | head -15
.venv/bin/python -m unittest discover -s tests -p 'test_c05_*.py'
.venv/bin/python analysis/c04_reproduce.py source
.venv/bin/python scripts/check_docs.py
```

Next: inspect/stage and commit/push checkpoint1, then build all supported actor rows without sampling, fit all three families sequentially, record convergence and score the fixed200 component panel. No active jobs. C06 private namespace is not yet created.
