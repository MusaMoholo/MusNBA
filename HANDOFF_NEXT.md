# Handoff — C01 complete; C02 ready at 0%

Updated 25 November 2026. **C01 is 100% complete: all four capability checkpoints accepted. No production accuracy gain claimed.**
The [completion receipt](analysis/experiments/20261125_c01_workbench_v1.json) records the decision, validation, hashes and private namespaces.
[MODEL](MODEL.md) holds results/limitations; [README](README.md) holds the working source/reproduction/ledger commands.
No jobs remain running. Independent reproduction and ledger integration are complete, not pending work.

Incumbent remains engine-v1.3-r3 with accepted rotations/foul/timing rules, report-bands-v1 and team-pathway-v1.
No production model/input/generation hook, PWA asset or bundle changed; no refresh, publication or manual import is needed.
Owner server 8766 stays running; review uses 8767. Git owns checkpoint identities.
[PLAN](PLAN.md) holds conditional strategy; [AGENTS](AGENTS.md) holds workflow rules. Historical receipts are evidence, never a backlog.

## Next chunk: C02 — predict team shot volumes and player shares together

**Status: 0% accepted. Planning complete; no C02 implementation, fitting or evaluation has begun.**

Question: with incumbent minutes held fixed, can dated player/team information predict materially better joint shot opportunities,
including team volume and player allocation, while preserving player/team probability accuracy and coherent worlds?
C01 exposed information headroom, not its predictable fraction. Its older baseline histories confound architecture comparisons;
knowing real minutes improved individuals while damaging team scores. Do not assume that a clock change, defence loading,
standalone minutes correction or a particular learner is the answer.

### Intended change and why it matters

- Predict distributions for each team's two-point attempts, three-point attempts and free-throw attempts from evidenced pre-tip
  profiles, including recent opportunity rates, team/opponent style and rest where supported.
- Learn how players share those opportunities, conditional on the same incumbent world minutes used by the comparisons.
  Every sampled player count is a nonnegative integer and sums exactly to its team's count for that attempt type.
- Learn joint variation from earlier games: some game conditions move several players together, while teammates compete for
  a given team's attempts. Estimate that dependence; do not inflate uncertainty by an arbitrary multiplier.

Better opportunity forecasts could improve player points and threes while preserving plausible team totals, margins and wins.
C01's outcome-informed tests justify investigating this route; they do not establish a predictable gain. The guaranteed advance
is a trainable, reusable joint opportunity module, its dated dataset and its evaluation tools, including a working joint sampler.

### Committed deliverables and decision

- A reusable, source-bound opportunity dataset/feature pipeline: dated player/team labels, exact scoring/count identities,
  causal profile lineage, support/missingness and fit/evaluation exposure manifests. No invented tracking or publication history.
- A working chronological probabilistic fit/predict/evaluate path, with current-information baselines, shared game/team dependence,
  conditional player allocation and independent coherence/accounting checks. Cached fits/forecasts must be reusable by later engines.
  A feature audit or ranked list alone cannot earn completion.
- One bounded modelling decision: whether a frozen opportunity challenger earns further independent qualification, or the incumbent
  remains preferred. Freeze one transparent rate baseline and one joint count/allocation challenger, with learner/shrinkage selection
  confined to earlier training folds. This count-based path competes with the incumbent event/actor architecture; no broad recipe sweep.
  No production promotion is promised. The full dataset/training/scoring capability remains required if the modelling hypothesis fails.

The chunk makes us better by turning outcome-informed headroom into a test of information that could actually be available at tip,
and by making player improvements answer to team outcomes. Availability forecasting, conversion changes, season tuning and UI
redesign are outside this chunk; later work stays conditional.

### Evidence boundary and dependencies

- Reuse C01's exact 200 exposed development IDs from `analysis/experiments/20261124_b1_development_v2.json` → `game_ids`.
  First 20 in frozen order are wiring; full 200 are development, never fresh confirmation. Pin source/candidate inputs and support
  before scoring. Reuse audited C01 truth, scorer, incumbent worlds and deterministic common prefixes where compatible.
- New raw training outcomes stop at 31 December 2025. All fits, normalization, hyperparameter choice, residual laws and calibration
  precede their evaluation origins. Evaluation may use stored dated pre-tip player/team profiles from the allowed panel only after
  their causal lineage is checked. Apply the same information age to challengers and comparison features; disclose residual differences.
  If current profiles cannot be evidenced without forbidden outcomes, narrow the conditional claim and deliver the source capability.
- No reserved/protected outcomes, protected incumbent rescore or new provider. Do not rebuild current features by opening other
  post-cutoff games. Any later confirmation requires a separate prospectively frozen contract and audited prior exposure.
  Sources remain ESPN/sportsdataverse/NBA Stats under existing collection limits; no collection is implied by this charter.
- Keep actual-participant diagnosis separate from operational availability/DNP forecasting. Shared incumbent minutes do not test
  independent minutes skill. Preserve the prospective ledger; zero real certified captures at C01 closure is an explicit limitation.
- Score distributions for player points/opportunities and joint team points/total/margin/wins, not just marginal means or signed bias.
  Predeclare critical-player/context support, calibration and dependence checks. Historical uncertainty clusters whole games and
  calendar blocks; simulation worlds are not additional real games. Markets remain diagnostic references only.

### Comparison and success decision

- Compare the retained incumbent, a simple forecast using dated current opportunity profiles, and the joint challenger. Share
  information age, supported player keys, world minutes, seeds and simulation counts wherever applicable. This controls the stale-profile
  ambiguity in C01's fixed baseline; any remaining difference in model training history stays explicit.
- In the cheap count screen, both new methods use the same frozen prior-only conversion law to turn attempts into points.
  Score opportunity counts directly and player/team points together. These are conditional count forecasts, not legal play-by-play worlds.
- The primary benefit is better player-points probability accuracy; count scores explain its mechanism. Team points, totals,
  margins/wins, critical players and uncertainty calibration have precommitted practical harm limits. Freeze numerical margins and
  support before fitting/scoring. A smaller opportunity error alone cannot select a winner.
- Only a passing screen earns one bounded simulation adapter. Learned opportunity rates influence legal event/actor choices;
  preserve the incumbent conversion and timing rules. Do not force sampled full-game count targets into a game, rescale completed
  boxes or add final-score offsets. Check whether the benefit survives actual simulated games before recommending qualification.

### Modular checkpoints — sequential acceptance, commit and push

Weights total 100%; report accepted capability separately from measured forecast gains. Each checkpoint refreshes affected live
docs, inspects staged changes and commits/pushes before dependent work. Independent source/fixture I/O may overlap safely.

|Checkpoint|Weight|Deliverables|Acceptance|
|---|---:|---|---|
|1. Causal data and frozen comparison|25%|Opportunity labels/features with dated lineage, current-information fairness audit, independent fixtures and a versioned C02 contract|Exact game/player keys, count/point/minute identities, explicit exclusions/missingness. Deliberate future-input and corrupted-label faults fail at the intended boundary. Before candidate outcomes, freeze recipes, primary useful gain, numerical team/critical-player harm margins, support/calibration requirements, multiplicity, precision and stopping. No fitting before this checkpoint is committed/pushed.|
|2. Working learners and recoverability screen|25%|Chronological probabilistic training/prediction, current-information baseline, joint challenger and common cached scoring; separate team volume from player allocation with fixed minutes|Complete the frozen 20/200 comparison with uncertainty, simulation-noise sensitivity and supported contexts; independently reconcile joint draws. Actual labels/oracles cannot enter live features. Judge predictable benefit and team harm together; an oracle improvement alone cannot pass.|
|3. Coherent adapter or completed negative route|35%|Reusable joint opportunity sampler/adapter, exact player/team accounting and full diagnostic comparison. If the frozen screen passes, connect one challenger to coherent event worlds on 20 then 200 games|Legal clocks/fives/fouls, exact counts/weights and deterministic workers/resume. Use 1k worlds/game for a justified engine experiment; no conversion/clock patch to rescue results. If the screen fails, finish the full data/fit/joint-sampling/scoring API, independent accounting and bounded negative decision; no expensive unchanged production run.|
|4. Independent operation and decision|15%|Fresh fit/sample/scoring reproduction, documented commands, capability/skill decision and next concrete 0% charter|Independent aggregates agree; source/cutoff and meaningful fault checks pass. Report practical effect, support, cost and uncertainty. Retain incumbent unless separate release evidence qualifies a change; a failed model does not waive the promised working capability.|

Numerical research priorities and practical harm limits must be frozen in checkpoint 1 from product stakes and outcome-blind
precision checks. C01 signals are evidence for choosing the question, not automatic C02 promotion criteria. Never revise limits,
populations or recipes after seeing candidate outcomes to rescue a result.
Report capability at 25%, 50%, 85% and 100% only after acceptance; also report long-job completed counts. Planning earns no C02
checkpoint credit. A research survivor is eligible for a later frozen qualification, not an automatic app release.

### Compute, failure routes and release boundary

Use at most ten total heavy threads, including compression/validation and inner pools. Cap OMP/OpenBLAS/MKL/vecLib separately;
cap Arrow pools, preserve canonical seeds/1k grouping, and wait for pool shutdown before large parent work. Benchmark wiring first;
estimate runtimes only from measured logs. No broad sweep or precision extension without the frozen stopping rule.
Private fits/rows/worlds: new `data/derived/experiments/c02_opportunities_v1`; aggregate receipts:
`analysis/experiments/<actualETdate>_c02_*.json`. Refuse overwrites; preserve replaced dependencies at `~/Basketball_archive_ops`.
Record any detached log, namespace, completed count, blocker and exact resume command here before a session stops.

No recoverable gain: keep incumbent, deliver the complete reusable pipeline and explain the measured data/model ceiling.
Insufficient support or precision: state the unresolved decision and choose the source/measurement capability that resolves it;
no invented winner, repeated local tweaks or cosmetic fallback. Unsupported operational timing remains conditional research,
with future original forecasts eligible only through genuine pre-tip capture.

Isolated research needs targeted tests, leakage/fault/accounting and reproducibility. A production model/input/generation change
additionally needs prospectively frozen release evidence, affected views/bundles, full smoke/fault/accounting and one fresh full
online nightly: current ET-day 10k worlds/branch and fresh season worlds, measured against the existing 3600-second ceiling.
Cache-only reuse is not fresh generation. UI publication/browser checks apply only if assets change; none are planned.

### Exact first actions

```sh
git status --short --branch
git --no-pager log --oneline -5
.venv/bin/python scripts/smoke.py
ls -t analysis/experiments/ | head -15
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
.venv/bin/python analysis/c01_run.py source
rg -n 'SourceBoundary|load_game|profile|cutoff|opportun' analysis/c01_contexts.py analysis/c01_baselines.py analysis/c01_core.py
.venv/bin/python scripts/check_docs.py
```

Then implement the source-bound label/feature manifest, independent fixtures and frozen C02 comparison contract. Read only relevant
MODEL/source code and retained C01 manifests. Commit/push checkpoint 1 before fitting; no historical plan supplies extra tasks.
