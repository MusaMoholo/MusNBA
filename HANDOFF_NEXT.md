# Handoff — C03 planned; 0% executed

Updated 25 November 2026. [C02 is complete](analysis/experiments/20261125_c02_completion_v1.json).
Homes: [MODEL](MODEL.md) evidence/contracts, [PLAN](PLAN.md) strategy, [README](README.md) commands, [AGENTS](AGENTS.md) workflow.
Production remains engine-v1.3-r3, report-bands-v1 and team-pathway-v1. No active jobs, publication or import. Owner 8766 stays running; review uses 8767.

## C03 — learn complete possession choices on equal information

**Status: 0% accepted. Planning only; no C03 implementation, fitting or scoring has begun.**

Question: does sharing what the model learns across event type, player choice and action improve the next-event probabilities
and the player/team outcomes generated from them, when competing models receive the same dated information and training history?

C02 changed training coverage, features and learners together. C03 extends its actor/action replacement path to complete
event/actor/action choice under a controlled comparison. Measured opportunity headroom and unresolved attribution justify the test;
neither proves joint learning will win.

### What we will build and why this is a substantial advance

- A reusable dataset covering the full supported earlier history, with dated player, lineup, opponent and game-state features.
  Qualify at least a supported opponent/lineup feature family; all admitted features have the same meaning during fitting and simulation.
  This removes C02's shorter-history/different-information ambiguity for the two new learners.
- One structured next-choice model that shares learned parameters across event/player/action alternatives. It returns one probability
  law over the legal next outcomes, including actorless team events. Event/player/action probabilities derived from it must agree.
  Multiplying independently fitted heads or placing them behind one command does not fulfil this deliverable.
- A matched model that learns those decisions separately, using the same recorded decisions, dated features, origins, selection
  allowance and declared capacity/compute budget. Select it using training-only evidence. Keep the unchanged incumbent
  as a third reference; its different information/training path cannot isolate architecture.
- Working simulator adapters, common player/team scoring and a command that independently refits, regenerates probabilities and
  repeats event worlds. Both new models must be usable from data through full games even if neither improves accuracy.

Completion requires this working causal training/choice/simulation capability. An audit, renamed model or negative report alone
cannot complete C03. Accuracy itself cannot be guaranteed.

### Possession boundary and bounded experiment

The model answers what happens next, which player is involved and which action follows, using only information available then.
Shots and scores accumulate from legal events. No full-game target/quota, output repair, market fit or arbitrary uncertainty
multiplier. Historical team/opponent context is input, never a desired outcome. Keep duration, conversion, rebound/foul resolution and rotations fixed.

Freeze one shared-parameter learner recipe and one matched separate-head recipe; use the existing NumPy/pandas/LightGBM stack.
Specify the finite legal choice space, actorless/missing-label support, common feature phase, decoder and comparable capacity before outcomes.
Any tuning is bounded, training-only and equally available to both paths. No development rescue sweep.

Three arms: unchanged incumbent, matched separate learner, shared learner. The architecture comparison is shared versus matched;
the product comparison asks whether either new model earns further qualification versus the incumbent. Predeclare both eligibility
routes and multiplicity so a matched-model win is legitimate and a joint-model loss stays a loss.

### Evidence, success and stopping

- Use the exact 200 exposed development IDs in `analysis/experiments/20261124_b1_development_v2.json`, first 20 for wiring.
  They are known development games, never fresh confirmation. Training may span supported December 2022–31 December 2025 history.
  Fit features/priors/assignments/normalisation/calibration strictly before each origin. No reserved/protected outcomes or new providers.
- Reuse retained causal-first/prior-position profiles and C02's guards. Audit any opponent/assignment lineage before admitting it.
  Prefer supported historical lineup exposure when personal defender truth is unavailable; no invented tracking. Both new learners
  get the identical qualified bundle, support and history. Exclusions/missingness are frozen before scores, never chosen by losses.
- Evaluate the joint next-choice probability and calibration on identical supported keys. Also report event, actor and action
  contributions. Freeze useful numerical gains, harm/support margins, class handling,
  multiplicity, seeds, selection folds, precision and stopping in the C03 contract at checkpoint 1, before any candidate fitting/scoring.
- Player-points distribution accuracy is the main full-game benefit; also score minutes, threes, rebounds/assists and joint team
  points/totals/margins/wins, critical-player harms and interval calibration. Define practical limits prospectively under MODEL.
  Event-score improvement alone cannot qualify a game model. Whole-game/calendar-block uncertainty and simulation-half sensitivity apply.
- Require three-arm 20-game integration at 1,000 worlds per arm regardless of the event-screen outcome. Expand to the fixed 200
  only for predeclared survivors and required controls. Stop failed recipes; no extra worlds or revised criteria to rescue them.
  Research survival means eligibility for later independent qualification, never an automatic production release.

### Four checkpoints — sequential acceptance, commit and push

|Checkpoint|Weight|Required deliverable and acceptance|
|---|---:|---|
|1. Equal information and frozen design|20%|Full supported data/feature manifest, qualified opponent information, explicit legal labels/choice space and both recipes. Meaningful future-input, label-dependent-mask and invalid-choice faults fail. Numerical benefit/harm/support/multiplicity/stopping rules frozen before fitting.|
|2. Working shared and separate learners|35%|Reusable chronological fit/predict/sample interface for both paths; genuine parameter sharing in the joint learner. Same information/history and declared capacity; independent probability arithmetic and full 200 recorded-context comparison, including calibration/branch/context support. No panel tuning.|
|3. Complete possession integration|30%|Adapters for both learned paths; training/runtime feature and decoder parity; fresh three-arm 20-game worlds with legal clocks/fives/fouls, exact player/team identities and deterministic seeds/resume. Conditional expansion follows the frozen screen; all outcomes emerge from events.|
|4. Independent operation and decision|15%|Fresh independent fits, probabilities, sampled choices and worker/world reproduction; documented reusable commands; accuracy and capability accepted separately; bounded architecture/product decisions and next concrete 0% charter.|

Accepted progress is 20/55/85/100%, separate from measured skill. Planning and launched jobs earn no credit.
Refresh affected canonical docs, inspect staged data/secrets and commit/push each checkpoint before dependent work. Report long-job
completed counts. At a stop, record exact command/log/session/namespace, counts, blockers and the next action here.

### Failure route, compute and release

If the shared learner loses but the matched model qualifies, retain the shared result and follow the predeclared matched-model route.
If both fail, keep production and still finish the full dataset, both working learners, choice interface, simulator adapters and
independent reproduction. Insufficient support/precision stays unresolved; a source gap must narrow claims, never fabricate evidence.
If any promised capability cannot yet run, the chunk remains unfinished. No cosmetic fallback or third local patch.

Use at most 10 total heavy threads, including inner pools/compression/validation; cap OMP/BLAS/Arrow, avoid nested pools, and shut
fitting down before large worker jobs. Benchmark wiring before estimating time. Preserve canonical seeds/1k chunks. New private
namespace: `data/derived/experiments/c03_joint_possession_v1`; aggregate receipts: `analysis/experiments/<actualETdate>_c03_*.json`.
Keep closed C01/C02 evidence reproducible; version new components and preserve replaced dependencies at `~/Basketball_archive_ops`.

Research stays isolated. A later production/input/generation release needs separate prospective qualification and all MODEL/AGENTS
release checks, including affected forecasts/bundles and a fresh full online nightly against the existing 3600-second ceiling.
No UI/platform or season work is planned. Raw revision/publication timing and actual-participant conditioning remain limitations.

### Exact first actions

```sh
git status --short --branch
git --no-pager log --oneline -5
.venv/bin/python scripts/smoke.py
ls -t analysis/experiments/ | head -15
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
.venv/bin/python analysis/c02_reproduce.py source
rg -n 'Boundary|COLS|objective|attached|validate_worlds' analysis/c02_data.py analysis/c02_model.py analysis/c02_runtime.py
.venv/bin/python scripts/check_docs.py
```

Then audit source/feature coverage, define the joint choice/decoder and matched comparison, and freeze the C03 contract. Commit/push
checkpoint 1 before fitting. The plan alone supplies no acceptance credit and creates no later-chunk obligations.
