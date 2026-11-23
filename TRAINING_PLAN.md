# Training and validation contract

Updated **23 November 2026**. Accepted systems: engine v1.3 and team pathway v1. No new promotion is implied.
[HANDOFF](HANDOFF_NEXT.md) owns current work; [FINDINGS](FINDINGS.md) owns outcomes. Frozen detailed protocols
are indexed in [docs/README](docs/README.md). This condensation changes no experiment gates or prior results.

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

### 8.1 Populations

- Node/M6a: actual state/lineups/clock; teacher-forced diagnostic, not a pre-game forecast.
- Conditional engine: actual participants, normally projected starters; `--known-starters` makes starts oracle too.
- Pre-game: only roster/report/play/start information available before origin. Inferred prior-box membership is
  not an official roster. Missing reports/labels stay unknown; never infer availability from the final box.

Use pre-game roles for selection. Realised margin/fouls can describe response, not train a pre-game predictor.

### 8.2 Frozen preregistration

The following S01 gate is retained **verbatim** from the pre-cleanup document. Exact IDs/seeds/fingerprints
and noise floors are in `analysis/experiments/20261122_a1_manifest.json`; the pre-candidate and production-baseline
manifests preserve what was frozen before candidate work. Shared starting seeds do not guarantee event-by-event
RNG alignment after paths diverge.

#### S01 preregistration — 22 Nov, before A1 candidates

The fixed development screen is the 200 retained F4 games in `20261120T162930Z_v1.3_pool_per_world_F4`, 1,000 worlds,
known actual participants and projected starters, pool 0. The independent pre-game-availability track is separate.
For player selection tiers, **star** means pre-game usage ≥0.25; otherwise **starter** means pre-game start share
≥0.5 and **bench** is below 0.5. Missing usage or start share is **unknown**, never silently bench. The older logged
scorecard uses actual game starters and remains a historical reference, not a selection gate. The screen has 284 star,
1,578 starter, 2,472 bench and 12 unknown player-games. A reportable tier/subgroup needs **at least 100 player-games
in 30 distinct games**; rarer cases are inconclusive, and required sparse tiers block a promotion claim rather than
being dropped. Game/season populations and exclusions must match exactly.

Player non-inferiority margins below are increases in CRPS in the statistic's own units. They are **2% of the
pre-game-tier pool-0 control**, rounded to four decimals; 3PM is fixed in advance at **0.0200 made threes** because the
old saved player output omitted 3PM. Its matched control must be regenerated before any 3PM decision.

| Pre-game tier | MIN CRPS (minutes) | PTS CRPS (points) | REB CRPS (rebounds) | AST CRPS (assists) | 3PM CRPS (makes) |
|---|---:|---:|---:|---:|---:|
| Star | 0.0578 | 0.0898 | 0.0304 | 0.0261 | 0.0200 |
| Starter | 0.0605 | 0.0711 | 0.0290 | 0.0207 | 0.0200 |
| Bench | 0.0796 | 0.0553 | 0.0237 | 0.0155 | 0.0200 |

The 2% bound is a small, meaningful loss relative to prediction error; a paired pool-400 versus pool-0 check on all
4,346 matched player-games had 95% game-clustered CRPS difference intervals narrower than these margins for these
four retained statistics. This is **not** a pure seed-noise experiment; S01 still measures an independent simulation
seed. If noise or the confidence interval is too large to demonstrate non-inferiority, increase worlds/games or report
inconclusive; **do not widen margins**.

Additional maximum harms: margin and total CRPS **0.20 points**, each quarter CRPS **0.10 points**, win log loss
**0.010 nats/game**, Brier **0.005**, and 10–90% coverage's absolute deviation from 0.80 **0.03**. For absolute signed
bias, the allowable increase in its magnitude is **0.30 minutes**, **0.30 points**, **0.10 rebounds**, **0.10 assists**
or **0.05 made threes** per player-game; team total/margin biases may grow by **1.0/0.5 points**. Season final-win CRPS
may worsen by at most **0.10 wins** on each supported start date; absolute dispersion, coverage and persistence error
may grow by at most **0.10, 0.05 and 0.05**, respectively. These are maximum harms, not desired target values.

Families and primary outcomes, frozen before candidate results: S04 defence/shot quality → pooled PTS CRPS;
S05/S06 membership/minutes/substitutions → pooled MIN CRPS; S07 availability → pre-game play Brier on a genuinely
dated cohort; S09 form/end-game → pooled PTS CRPS plus the prespecified joint-dependence checks; S10 pathway → pooled
final-win CRPS across the 16 matched season/start origins with each date separately reported. S08 is an accounting and
coherence change, not by itself an accuracy win. Pooled player CRPS weights eligible player-games equally; all three
supported tiers and the other core stats must pass their non-inferiority gates. Claims across multiple tested primary
families use Holm's 0.05 correction; exploratory within-family variants and all rejected runs are recorded.

Use **10,000 paired game-cluster bootstrap replicates**, NumPy seed **20261122**, sampling complete game IDs with
replacement and retaining all player rows from each sampled game; report the 2.5/97.5 percentiles. Required
non-inferiority passes only if the upper 97.5% bound of candidate-minus-control harm is strictly inside its frozen
margin. A primary win requires its corrected 95% upper bound below zero **and** its observed improvement larger than
the independently measured simulation-noise floor. For coverage/bias use the paired change in the absolute deviation,
not the signed change. Report sample sizes, point differences and intervals. Different model names alter the current
simulation seed; common streams may be used only when their semantics are explicitly fixed and valid, never assumed.
For each primary CRPS, define the 1,000-world simulation-noise floor conservatively as the larger absolute endpoint
of the 95% paired game-cluster bootstrap interval comparing the same control and inputs under its original stream and
an independent stream on the entire pinned 200-game panel. This rule is frozen before that comparison; it is not a
licence to discard an inconclusive interval or to lower the registered harm margins.
Win Brier and log loss use the empirical simulated probability without modification. A zero probability assigned to
the observed winner has genuinely infinite log loss: the report marks it explicitly instead of inventing a finite
value or an interval. This differs from the legacy backtest summary's numerical boundary safeguard.
The second-seed result, exact confirmation IDs, 10k subset and reproducibility manifest are recorded in
`analysis/experiments/20261122_a1_manifest.json`, pinned to source checkpoint `c6d5db4`; the later seed-list type
annotation preserves the compiled function and all 3,036 recorded seeds.

### 8.3 Confirmation and release

After cheap accounting/node checks and the fixed 200-game F4 screen, freeze a survivor before confirmation on
**all eligible F4 games** and the fixed **200 games each from F1–F3** (manifest has 718 F4; 1,318 total).
Use fold-safe fits/features and matched controls; report exclusions/overlap. Run the second simulation stream
and the predeclared **20 games × 10k worlds** OT/short-roster/close/blowout stress subset. The outcome-stratified
stress subset is diagnostic, not an unbiased population or independent tier gate.

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

### 8.5 Current A2 protocols

Read [the frozen A2 methods](docs/protocols/a2_form_20261122.md) before resuming. They preserve the exact
residual, shot-feasibility, cross-game-persistence and synthetic-draw definitions. F4 informed hypotheses;
it is not untouched confirmation. Estimate persistent talent, nightly player form and shared conditions
separately from strictly prior/cross-fitted predictions. Compare observed AND baseline simulated dependence
before adding variation; event/minute/state randomness already creates covariance.

Namespaced factors stay fixed per game/world/player or team; zero strength consumes no new draws. Tilts
preserve baseline marginal means without clipping. Unsupported/negative excess is not clamped into evidence.
Freeze strengths/cutoffs/joint estimands before an engine result; compare factors alone before combinations.
Require pooled PTS and joint checks plus every registered non-inferiority/noise/confirmation rule, not wider
intervals alone. A1 decisions precede integration. No calibrated draw or engine wiring has been delivered.
