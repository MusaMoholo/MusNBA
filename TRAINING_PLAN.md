# Training and validation contract

Updated **23 November 2026**. Accepted systems: Rule3/independent-fit engine-v1.3-r2 (unchanged nodes) and team pathway v1.
[HANDOFF](HANDOFF_NEXT.md) owns current work; [FINDINGS](FINDINGS.md) owns outcomes. Frozen detailed protocols
are indexed in [docs/README](docs/README.md). D51 redesigns release classification prospectively; historical
results and numerical harm margins remain preserved.

## 1. Models

Sixteen LightGBM decisions: duration, event, who, what, location, shot result, assisted/assister,
blocked/blocker, turnover type/stealer, fouler, free throw, rebound/rebounder. Candidate rows score players
on the floor and softmax within segment; temperature and early stopping use only the latest 10% of training.
Clocks, bonus/free-throw counts, foul-outs and lineup legality are rules. See ENGINE_PLAN for chain/design.

## 2. Inputs

Point-in-time player role/starts/minutes/usage, zone mix/accuracy, creation/assists, ball security, fouls,
rebounds, individual/on-court defence, body/archetypes and effective exposures. Segment state includes the
ten players, relative roles, clock/score/period, start type, fouls/fatigue, team style and era. Optional
schedule/heat/shot-type groups earn inclusion by ablation; `models/v1.3.json` owns exact current node settings.
No team defensive rating enters the possession models. Missing data and provenance gaps remain explicit.

## 3. Decay and reliability

Feature half-life starting points: roles ~5 games, usage/mix/assist/rebound ~15, shooting ~40, FT ~80 attempts;
stat-specific shrinkage toward NBA archetypes. These starting values are not licence to retune without folds.
Measured model-fitting sample-weight choice: **no time decay**; era inputs carry drift. Buckets for sample-size
verdicts use decayed offensive segments (<250, 250–750, 750+), not role `games_eff` capped near 7.7.

## 4. Cutoff and parity

Every game at ET origin D uses games strictly before D. Every auxiliary fit (assignment, archetype, priors,
ramps, substitution/covariance/calibration) also predates the tested origin. Validation rows never fit
medians, priors or missing-profile fallbacks. Date-filter historical engine inputs and reject late-data injection.
Use one rebound-at-miss-clock convention in training/serving. A parser/feature revision requires matched
cross-data tests and an explicit cache/source identity, not silent replacement of v1.3 inputs.

Important audited limitations: production December-2025 assignment is unsafe for F1–F3; use dated fits AND
rebuilt fold-specific features. First-season whole-season priors, static measurements without as-of proof and
batch-wide missing-defender fills are not certified causal. Corrected integrity variants are research-only.
Do not equate historical event dates with proven original publication/revision timing.

Formal current-season rule evaluation needs its own loader: `backtest._init` reads historical season files.
For non-fold artifacts `Models` reads fallback medians from the full retained pregame table; a retrospective
adapter must use medians strictly before each evaluated origin in **both arms**. Live rebuilding already
retains only pre-origin games. Reuse the accepted nodes' existing final score; don't refit/rescore them as new nodes.

## 5. Folds and final test

| Fold | Fit through | Validate |
|---|---|---|
| F1 | 2023-12-31 | 2024-01-01 to 2024-04-30 |
| F2 | 2024-12-31 | 2025-01-01 to 2025-04-30 |
| F3 | 2025-09-30 | 2025-10-01 to 2025-12-31 |
| F4 | 2025-12-31 | 2026-01-01 to 2026-04-30 |

Burn-in starts December 2022; exclude reconciler-invalid games/rows per node and count exclusions. Final test
starts **2026-07-01** (2026–27), once per frozen version at promotion. `--final` currently fits through
2026-06-30; it is not a refit-through-today command. Never select/tune from its outcomes or rename a failed
recipe to rescore. Keep recipe identity distinct from dated fitted-artifact identity.

## 6. Compute and artifacts

Use the active **ten-total-thread** budget (AGENTS §6): process workers × inner compute threads across jobs.
Reuse measured worker choices, overlap independent I/O/work asynchronously, avoid nested BLAS/OpenMP and
reduce under memory pressure. Preserve deterministic seeds/inputs regardless of worker partitioning.

Configs/reports: `models/`, `analysis/experiments/`; ignored fits/rows/captures: `data/models/`,
`data/derived/{variants,experiments}/`. Cache keys include relevant code/input hashes. New runs use fresh
namespaces; never overwrite a retained or interrupted run. No unrequested provider or historical forecast replay.

## 7. Node retention gate

`scripts/compare.py A B --noise S0 S1` pairs identical held-out rows with game-clustered uncertainty.
Retain a node when mean four-fold change beats negative training noise, pooled z≤−2, and no fold is worse
than twice noise with z>2. Compare global changes on chain nats/game too. Fitting seed-only controls define
the measured relative-RMS floor. Settings may differ by node in the version config. Node improvement alone
never establishes whole-engine promotion. Frozen completed S02–S07 methods remain in the archived training plan.

## 8. A1 acceptance and reproducibility

**Versioned policy:** [v2](docs/protocols/promotion_v2_20261123.md) remains the default;
[v3 review](docs/protocols/promotion_v3_20261123.md), authorised by D51, freezes fresh confirmation
after the known r2 v2 failure. V3 keeps27 proper-score bounds and25 coverage diagnostics, and reports17
cohort-bias bounds separately. All numerical margins, learned primary benefits and invariants remain.
The final result is preserved and never rerun; no release follows from retrospective reclassification alone.
It distinguishes rule corrections, learned predictors and stored scenarios. The numerical CRPS/bias margins
below remain; primary-improvement and coverage-blocking requirements are class-specific. Old results
remain historical results under their original gate, not retroactively unseen confirmations.

### 8.1 Populations

- Node/M6a: actual state/lineups/clock; teacher-forced diagnostic, not a pre-game forecast.
- Conditional engine: actual participants, normally projected starters; `--known-starters` makes starts oracle too.
- Pre-game: only roster/report/play/start information available before origin. Inferred prior-box membership is
  not an official roster. Missing reports/labels stay unknown; never infer availability from the final box.

Use pre-game roles for selection. Realised margin/fouls can describe response, not train a pre-game predictor.

### 8.2 Active numerical compatibility margins

[Promotion v2](docs/protocols/promotion_v2_20261123.md) is the release policy. [Historical S01 v1](docs/protocols/promotion_v1_20261122.md)
is preserved verbatim for reproduction, not applied indiscriminately. S01 IDs/seeds/hashes remain in
`analysis/experiments/20261122_a1_manifest.json`. Supported known-role inference needs 100 player-games in
30 games; report sparse/unknown groups honestly. Star: pre-game usage >=.25; otherwise starter if prior
start share >=.5, else bench; missing required profiles stay unknown.

Retained maximum CRPS increases in each statistic's units:

| Tier | MIN | PTS | REB | AST | 3PM |
|---|---:|---:|---:|---:|---:|
| Star | .0578 | .0898 | .0304 | .0261 | .0200 |
| Starter | .0605 | .0711 | .0290 | .0207 | .0200 |
| Bench | .0796 | .0553 | .0237 | .0155 | .0200 |

Absolute-bias error increases: MIN/PTS .30, REB/AST .10, 3PM .05; team total/margin 1.0/.5 points.
Game total/margin CRPS .20, quarter total/margin .10; win Brier .005, log loss .010. These yield **44**
core compatibility bounds. Require upper paired 97.5% harm bound below the fixed margin; unresolved is
not evidence of harm or safety. All 25 legacy coverage diagnostics remain reported; mechanical changes
are blocked by demonstrated material coverage harm (lower 95% harm bound >.03), not arbitrary uncertainty
in every secondary cell. Distributional changes claiming calibration benefits need prespecified joint/
calibration improvements too. No bound was widened by D51.

Use 10,000 paired complete-game bootstrap replicates, seed 20261122; no player/world pseudo-replication.
Proper scoring rules evaluate full distributions. Learned changes require a frozen primary improvement
and multiplicity/independent-stream confirmation. Rule fixes require demonstrated correctness and
compatibility, not a detectable pooled accuracy gain. Independent-seed noise is a resolution diagnostic,
not a universal minimum-effect cutoff. Raw discrete worlds permit expected randomised-PIT coverage,
integrating its auxiliary uniform draw; retain legacy results separately. Infinite log loss stays infinite.

Pathway margins remain per supported start date: final-win CRPS .10 wins; absolute dispersion/coverage/
persistence error .10/.05/.05. Scenario assumptions need exact accounting and labels; learned injury
probability claims need genuinely dated development cohorts. Freeze candidate/source/population before
confirmation; keep conditional tests separate from pre-game availability forecasts.

### 8.3 Confirmation and release

For **learned changes**, after cheap accounting/node checks and the fixed 200-game F4 screen, freeze a survivor before confirmation on
**all eligible F4 games** and the fixed **200 games each from F1–F3** (manifest has 718 F4; 1,318 total).
Use fold-safe fits/features and matched controls; report exclusions/overlap. Run the second simulation stream
and the predeclared **20 games × 10k worlds** OT/short-roster/close/blowout stress subset. The outcome-stratified
stress subset is diagnostic, not an unbiased population or independent tier gate.

Rule-only fixes use the proportional, separately frozen v2 confirmation plan with unchanged fitted nodes;
stored-data/UI changes use structural/operational checks. Do not require unnecessary node refits for those classes.

Test combined components and removals; exact player/team/period/seconds/mixture identities, legal fives,
missing/cold/short rosters, foul-outs/OT, deterministic replay/worker changes, restart, cutoff injection,
source provenance and measured live-nightly runtime ≤60 minutes. Event capture cannot change draws.

Pathway candidates use identical schedules/Cup accounting and **16 origins** (four dates × four seasons),
leave-one-season-out selection, paired final-win CRPS/dispersion/coverage/persistence per date. A pooled result
cannot conceal a bad start date. No accepted future physical-absence hazard currently exists.

Release manifest freezes all retained/rejected components, code/input/config hashes, training cutoffs,
limitations/fallbacks and evidence. Only a qualifying recipe is fitted/scored once on the protected final test.
A failure may block release; further selection returns to development folds. Deliver accepted outputs/PWA,
keep original forecasts and state non-promotions explicitly. S13 remains deferred; S14 still requires the final nightly.

### 8.4 Current A1 branch boundary

S08 is accounting/coherence, not itself an accuracy win. Use D46 selection and exact branch/Expected/season
identities in ENGINE_PLAN. Fixed status weights are explicitly uncalibrated; independence is unvalidated.
No dated development injury-report cohort supports a status model. D47 quarter-scaling remains a candidate,
including its interaction with the 0.9 starter threshold. Do not silently change other players' probabilities.
D48 retries require world-local classification, caps, preserved rejection records and measured selection/
predictive effects; input/cutoff/accounting/unknown errors never qualify. Keep full D49 minute precision.
Read the [branch runbook](docs/research/a1_branches.md) before implementation; full original protocols remain frozen.

The 23 Nov prior-roster route has 783/800 supported contexts. Under D51 this limits that historical
pipeline's coverage; it does not veto every supported live scenario. Each published case still needs validation.

### 8.5 Current A2 protocols

Read [the frozen A2 methods](docs/protocols/a2_form_20261122.md) before resuming. They preserve the exact
residual, shot-feasibility, cross-game-persistence and synthetic-draw definitions. F4 informed hypotheses;
it is not untouched confirmation. Estimate persistent talent, nightly player form and shared conditions
separately from strictly prior/cross-fitted predictions. Compare observed AND baseline simulated dependence
before adding variation; event/minute/state randomness already creates covariance.

[Shared-shooting/world/late-state methods](docs/protocols/a2_joint_late_20261123.md) extend these diagnostics.
The [contextual late-clock screen](docs/protocols/a2_late_clock_20261123.md) freezes one prior-fitted candidate,
clean bridge removal control, earlier-fold proper-score criteria and a separate 200-game F4 manifest before results.
[Engine stages](docs/protocols/a2_clock_engine_20261123.md) freeze control reuse, sequential compatibility and survivor confirmation before clock-engine results;
[D56 amendment](docs/protocols/a2_clock_independence_amendment_20261123.md) prospectively requires the qualified independent fitter in both arms and reserves r3 for clock.
The fresh 200-game D51 confirmation pass captures accepted-control worlds once for both modules. A read-only
observer reproduces 1,556 legacy pilot fields; an independent auditor checks scores, precise minutes, rule/team
fouls and integrated discrete coverage. Stop/resume hashes match. Panel/stress/stream evidence is complete;
the [rule-level final](docs/protocols/rule3_final_20261123.md) completed once, with pre-origin medians in both arms.
`analysis/rule3_scores.py` retains legacy PIT alongside integrated coverage. No model is promoted by node loss alone.

D56's [independent-world contract](docs/protocols/world_independence_20261123.md),
[prospective clarification](docs/protocols/world_independence_amendment_20261123.md) and
[seed review](docs/protocols/world_independence_stream_review_20261123.md) are frozen v2 history:
fixed200 F4 passed44/44; seed30 had six imprecise/ten unsupported bounds; three10k stresses passed;
protected246 established42/44, all27 proper-score checks. Preserve this outcome, never repeat protected r2.
D57's [v3 revision](docs/protocols/promotion_v3_20261123.md) follows an independent arithmetic/policy audit
and returns to the previously reserved, unseen200 F4 IDs, with unchanged candidate and numerical margins.
Fresh confirmation/source hashes are frozen in `20261123_rotation_policy_confirmation_manifest_v1.json`;
its200-game run now establishes all27 proper bounds and all17 bias/25 coverage diagnostics.
`20261123_independent_rotation_qualification_v3.json` permits integration; six raw replays, three retained queue branches and the fresh full nightly/PWA delivery
now pass (`20261123_r2_release_v1.json`). Original protected limitations remain; no rescoring.
No retrospective reclassification alone approves release. Original v2 contracts above remain v2 contracts;
the v3 manifest explicitly selects the revised diagnostic classification for this new evidence.

Namespaced factors stay fixed per game/world/player or team; zero strength consumes no new draws. Tilts
preserve baseline marginal means without clipping. Unsupported/negative excess is not clamped into evidence.
Freeze strengths/cutoffs/joint estimands before an engine result; compare factors alone before combinations.
Require pooled PTS and joint checks plus every registered non-inferiority/noise/confirmation rule, not wider
intervals alone. A1 decisions precede integration. No calibrated form factor or production clock selection is delivered.
`ContextClock` has focused sampler tests and remains disconnected from the engine.
