# Handoff — C06 complete; C07 at 0%

Updated 26 November 2026. MODEL owns numerical evidence/limits, PLAN strategy, README commands, AGENTS workflow.
[C05 completion](analysis/experiments/20261126_c05_completion_v1.json) records minute/player-point gains with critical-player harm blocking qualification. [C06 completion](analysis/experiments/20261126_c06_completion_v1.json) records no useful actor gain. Production remains engine-v1.3-r3/report-bands-v1/team-pathway-v1; no publication/import needed.
No active jobs. Owner 8766 stays running; review 8767.

## C07 — preserve role skill through coherent forecast combination

**50% deliverables validated: checkpoint1 pushed as a3b8803; checkpoint2 ready for commit/push.** Baseline smoke118/118, prior12tests and weighted-law faults pass. [Exact contract](analysis/c07_contract_v1.json) freezes recipes,41/159split,7comparison multiplicity and806000world ceiling. Question: can a learned combination of complete native and role-informed
worlds retain C05's player-point gain while protecting high-usage players and joint team outcomes? This challenges the replacement
architecture: a useful role model need not replace the incumbent uniformly. It is not another actor-head tweak, a C05 criterion
relaxation, or a claim that C06 establishes an actor-model ceiling. Major forecast improvement remains an aim, not a promise.

### Committed capability and credible alternatives

Deliver three runnable coherent expert-combination models, a chronological member-forecast archive, exact weighted player/team
proper scoring, and independent fit/weight/world reproduction. Every generated world must still arise from legal possession events.
Reuse C05's fixed learned role law, exact decoder, source guards, native captures and C06's matched scoring/accounting. Hold all
possession heads fixed. No UI/provider/availability work, new workbench phase, full-game shot/score targets, offsets or spread inflation.

Compare distinct selection levels, with exact recipes frozen at checkpoint 1:

- **A: whole-game stacking.** Learn a global probability mixture of complete native and both-team role-informed worlds using prior
  joint player/team proper scores. Retain a fixed 50/50 pool as a strong simple baseline; learning must earn its complexity.
- **B: team expert selection.** Learn dated team-context probabilities for using native or learned-role rotations before simulating
  the joint game. Include home-only/away-only role members: team interactions must emerge inside the shared event engine.
- **C: player role selection.** Learn prior-role/reliability gates between native and learned minute draws, then enforce legal joint
  time and generate complete event worlds. Score the law after projection, scheduling, substitutions, fouls and overtime.

All see the same eligible history, roster/role/performance inputs and training truths; native and learned inputs remain explicitly
identified. Freeze fitting losses, capacity, maximum two training-only configurations/family, strong-baseline policy and any unequal
resource/representation choices before outcomes. Different selector levels change dependence; loss/representation differences still
limit pure causal attribution. Do not build one favourite fully before the three working MVPs compete.

### Chronology, decisive contrast and acceptance

- Existing 2023–2026 sources and B1's exposed 200 games only; no protected/reserved outcomes, fresh-test claim or new provider.
  Members use fits/calibration through 31 December 2025. Learn combination parameters only from the **41 B1 games dated through
  21 January 2026**; evaluate the fixed **159 games from 22 January onward**. Split by date, never reference-list order; same-day
  outcomes cannot enter features or fitting. All 200 were previously explored; this is causal development, not confirmation.
- Preserve original truth/gap flags and actual-participant conditioning. No operational availability claim. Every feature, fit,
  normalisation and gate precedes its evaluated origin. Fixed model-member generation may be reused after source/hash verification;
  earlier exposed C05 scores are not new evidence. Generating members for C07 does not reopen C05's failed decision.
- Decisive contrast: whole-game versus team versus player use of the same predictable role signal and strong incumbent. Measure
  high-usage players, bench players and team dependence together. Learned weights must come from earlier games, not a blend chosen
  to make the known development panel pass.
- Before new forecasts/outcomes, freeze numerical primary benefit, calibration/joint harms, critical support, multiplicity over all
  initial candidates/baselines, precision, shortlist and stopping. Target at least **1% player-point proper-score improvement versus
  native**, both simulation halves, whole-game/week uncertainty, and no practical critical-player/team harm. Start from C05's
  numerical harm limits; freeze the final exact policy prospectively. A simple baseline win counts honestly; it cannot prove learned
  gating helps. No automatic production promotion or changed meaning for C05/C06 results.
- Reject cheaply using training-only credibility and first two legal wiring games, then a fixed first 20 evaluation games. Only
  at most two qualified finalists expand to all 159; retain native and simple-pool controls. Validate the final returned weighted
  distribution with exact mass, common support and independent arithmetic. Extra Monte Carlo draws cannot masquerade as model skill.

### Four sequential checkpoints

|Checkpoint|Weight|Acceptance|
|---|---:|---|
|1. Freeze coherent comparison|15%|Reuse/source/split inventory, exact recipes/losses/gates/budget, meaningful future-label/weight/illegal-law faults; commit/push before fits/worlds.|
|2. Deliver competing MVPs|35%|Three working learned models, dated training members, training-only credibility, exact weighted scoring and all wiring adapters; freeze shortlist.|
|3. End-to-end decision|35%|Qualified paired20/conditional159 player/team/critical/uncertainty comparison, otherwise independently audited bounded stop.|
|4. Reproduce and deliver|15%|Fresh fits/weights/worker replay and independent decision; separate capability/component/game/release status; next concrete 0% charter.|

Each checkpoint ends with relevant tests/accounting, live docs, staged inspection, commit and push before dependent work. Progress
15/50/85/100% counts accepted deliverables. Missing models/reproduction leaves the chunk unfinished. If all lose, report a completed
negative search, retain the incumbent, and distinguish insufficient calibration support from integration/dependence failure.

### Compute and exact first actions

Ten heavy threads total; fits up to10 then workers10×1, BLAS/Arrow1. Maximum **806000 new event worlds**, including training members,
all candidate/configuration attempts, wiring, finalists and independent repeats. Reuse audited native/C05 worlds honestly; no budget
extension. One chronological gate fit per frozen configuration and one independent final-recipe repeat. Benchmark runtime; no estimate
is inherited. Private namespace `data/derived/experiments/c07_coherent_experts_v1`; aggregate receipts under `analysis/experiments/`.
No production/input/asset change or full nightly is authorised by this charter alone.

```sh
git status --short --branch
git --no-pager log --oneline -5
.venv/bin/python scripts/smoke.py
ls -t analysis/experiments/ | head -15
.venv/bin/python -m unittest discover -s tests -p 'test_c05_*.py'
.venv/bin/python -m unittest discover -s tests -p 'test_c06_*.py'
.venv/bin/python scripts/check_docs.py
```

Training archive:41games,103000new worlds,843seconds. All3gates converge using only earlier games. Wiring generates8000new member
worlds in263seconds; [independent audit](analysis/experiments/20261126_c07_wiring_audit_v1.json) checks10000returned worlds and3345scalar/half scores,
exact masses/source mappings and conservation. [Training arithmetic](analysis/experiments/20261126_c07_training_math_v1.json) independently
matches the fitted composite objective. Seven synthetic/fault tests pass. These are capability/mechanical results, not accuracy gains.
Namespace `data/derived/experiments/c07_coherent_experts_v1`; no active jobs. Logs under private `logs/`.
Next: inspect/stage, commit/push checkpoint2, then run `analysis/c07_evaluate.py short --jobs 10` with inner thread caps1 and log
`/tmp/c07_short.log`. All3converged families plus fixed pool enter the frozen first20evaluation games. Run `analysis/c07_audit.py short`;
only precommitted qualifiers may expand. Partial stages fail closed; retain faults before technical resumption.
