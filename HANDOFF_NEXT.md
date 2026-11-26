# Handoff — C04 complete; C05 at 0%

Updated 26 November 2026. [C04 completion](analysis/experiments/20261125_c04_completion_v1.json) records a component gain with a
calibration block: all three models improve minute-distribution scores; none earns complete-game expansion. [MODEL](MODEL.md) owns
numbers/limits, [PLAN](PLAN.md) strategy, [AGENTS](AGENTS.md) culture/workflow and [README](README.md) commands.
Production remains engine-v1.3-r3, report-bands-v1 and team-pathway-v1. No active jobs. Owner 8766 stays running; review 8767.

## C05 — preserve learned minute skill through calibrated joint laws and faithful rotations

**Checkpoint 1 ready for acceptance; no C05 fits/draws/outcomes.** Exact recipes and numerical gates are frozen in [C05 contract](analysis/c05_contract_v1.json). Baseline smoke118/118, C04 source and8 tests pass. Exact decoder passes random/boundary and deliberate illegal-law/target-corruption checks. C04 demonstrates admissible role/minute signal on known development games,
with unacceptably narrow intervals. That failure precedes the rotation decoder. Separately, the old offset decoder sometimes misses
forecasted targets by many minutes. Freeze a new comparison prospectively; never change C04's failed coverage rule or promote its models.

Question: can a complete joint-minute forecast retain C04's skill, express honest uncertainty after constraints, and improve player
points without harming joint team outcomes? Score the distribution actually returned to consumers after every transform.

### Committed capability and three-model comparison

Deliver three runnable joint uncertainty models around the same dated role-mean information, a faithful legal rotation decoder,
proper minute/player/team comparisons, and independent fit/draw/world reproduction. Reuse C04 data, models, source guards and scorers.
No standalone workbench, event-head refit, UI or provider work. Tools alone cannot establish forecast gain.

Compare distinct uncertainty laws, with exact recipes/capacity frozen at checkpoint 1: (A) whole-team empirical residual resampling
trained/scored after legal allocation; (B) a learned latent joint distribution mapped directly into bounded team-minute allocations;
(C) a whole-team probability mixture of the learned role model and a dated legacy-family minute law. Learn parameters/weights from
prior outcomes; no arbitrary spread multiplier. Minor spread settings do not count as separate approaches. All see identical eligible
histories/mean information, with maximum two training-only configurations per family and one selected recipe before development scoring.

The shared decoder must preserve sampled player targets within one second while assigning five distinct eligible players throughout
regulation. Use explicit constrained scheduling and independent accounting; retain original forecasted timing shapes as preferences.
Calibrate/evaluate the returned legal law, including roster-size mapping and quantisation. Preserve a bridge control through the same
decoder and the original native forecasts so translation effects remain visible. Generated fouls/overtime remain legal and explicit.

### Evidence and stopping

- Use only existing historical seasons 2023–2026 and the exposed B1 200 IDs; no protected/reserved outcomes, new provider or fresh-test
  claim. Keep original source truth/gap flags. Actual-participant membership remains conditional, not validated pre-tip availability.
- Every fit, mean/residual calibration, normalisation and feature precedes evaluated origin. Generate chronological training residuals
  where needed; future-trained mean predictions cannot masquerade as out-of-time calibration. Freeze dates/selection before new scores.
- Before development outcomes, freeze numerical proper-score benefit, interval/reliability requirements, critical/player/team harms,
  support, multiplicity, precision and stopping. Retain C04/native references and account for all three initial comparisons. No criterion
  rescue or replacement fourth model. Training-only uncertainty tuning is recorded fully; no development-driven changes.
- Screen all 200 minute distributions after legal allocation/decoder. Prove both skill and uncertainty; point accuracy alone is insufficient.
  Deliver first two ×1,000-world legal wiring adapters for valid families. At most two qualified paths proceed to first 20 then fixed 200
  at 1,000 worlds/game; require player-points benefit against native and bridge, plus minutes/threes/rebounds/assists, critical players,
  scores/totals/margins/wins/coverage, whole-game/week uncertainty and both simulation halves. No automatic production release.

### Four sequential checkpoints

|Checkpoint|Weight|Acceptance|
|---|---:|---|
|1. Freeze final-object comparison|15%|Exact dated recipes/data/support/decision/total budget; reuse inventory; meaningful future-input, illegal-law and target-to-schedule faults; commit/push before fits.|
|2. Working calibrated laws|35%|All three fit/predict; training-only capacity evidence; exact-time decoder and bridge tests; all 200 minute-law comparison and first-two-game adapters; frozen shortlist.|
|3. End-to-end decision|35%|Qualified 20/conditional 200 native/bridge comparison with proper joint scoring and uncertainty; otherwise independent bounded stop. No repeated unchanged production refresh.|
|4. Reproduce/deliver|15%|Fresh fits/draws/worker replay and independent decision; working models delivered; component/end-to-end/release status separate; next concrete 0% charter.|

Every checkpoint: affected tests/docs, staged inspection, commit and push before dependent work. Progress 15/50/85/100% counts accepted
deliverables only. If calibration and skill cannot coexist under the frozen comparison, retain that result and identify whether the
remaining limit is data support, the law or translation. No impossibility claim or engineering-as-product success.

### Compute and exact first actions

Ten heavy threads total; fits 10 then workers 10×1, BLAS/Arrow1. At most four chronological mean-fit origins and the frozen family fits,
plus one independent repeat. Maximum 606,000 new worlds including wiring/finalists/replays; native controls reused honestly. No budget
extensions. Private namespace `data/derived/experiments/c05_joint_role_laws_v1`; aggregate receipts under `analysis/experiments/`.
No production/input/asset changes or nightly refresh are authorised by this charter alone.

```sh
git status --short --branch
git --no-pager log --oneline -5
.venv/bin/python scripts/smoke.py
ls -t analysis/experiments/ | head -15
.venv/bin/python analysis/c04_reproduce.py source
.venv/bin/python -m unittest discover -s tests -p 'test_c04_*.py'
.venv/bin/python scripts/check_docs.py
```

Next: implement the frozen chronological shared means and three uncertainty laws; run training-only diagnostics before the fixed200 minute screen. Decoder uses original timing as a preference; realistic substitution timing remains unproven. Private namespace/logs will retain every stage. No active jobs.
