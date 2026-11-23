# Model contract and evidence

Current state/jobs/delivery: [HANDOFF](HANDOFF_NEXT.md). Scope: [PLAN](PLAN.md). Commands/product: [README](README.md).
This file owns current design, validation and facts that change future decisions. Older detailed measurements/protocols and D1–D57
wording are preserved in the verified [history archive](README.md#documentation-history); consult relevant sections only.

## Accepted architecture

**engine-v1.3-r3**, unchanged `models/v1.3.json` fitted nodes; D29 target rotations/pool 0, Rule 3 foul-outs,
independent per-world rotation fitting and deterministic 1k chunks,10k worlds/branch. **Contextual late-clock timing is accepted and delivered.**
For ET origin D, result games before D, rebuild dated profiles/minutes/rotations/matchups and team ratings.
Possession worlds cover today's games only. Team pathway v1 consumes those exact outcomes and plays tomorrow onward,
updating each world's offence/defence from its own score surprises. Serving only reads saved results.

Sixteen LightGBM decisions: duration, event, who, what, location, shot result, assisted, assister, blocked, blocker,
turnover type, stealer, fouler, free throw, rebound, rebounder. Candidate-player nodes softmax the five on court;
temperature/early stopping use the latest 10% of training. Chain: player → action → location/result → credits → rebound.
Player/lineup defence uses soft role/size assignments, individual quality, help and matchup/shot-type history;
no team-strength rating enters possession nodes. `models/v1.3.json` owns exact inputs/settings.

D29 uses healthy-core roles, starts/minute rank/usage and learned return ramp; priority allocation totals 240 regulation minutes
(+25/OT), with independent target variation/world and rescaled replay stints. Availability is not positive playing time.
State-responsive substitutions remain unpromoted. Rule 3 replaces disqualified players and handles NBA roster exhaustion/technical
penalties without rejecting worlds. Recorded older runtimes retain original semantics.

Regulation periods 720s, OT 300s. Segments may continue after offensive rebounds/non-shooting fouls.
**No explicit 24/14-second shot-clock state exists**; period/minute checks do not prove shot-clock compliance.
Raw coordinates are feet, basket(25,0); rim≤4 ft, paint |x−25|≤8/y≤19, corner 3 |x−25|≥21.8/y≤14.
Current shot inputs pool sides into rim/paint/mid/corner 3/above 3 plus 21 distance bands, with training-band mean distance/lateral offset.
Defence accuracy groups rim/paint/mid/combined 3. No precise simulated trajectories or observed primary-defender claim.

D46 selects at most one uncertain player/team, only within the full roster's top three by prior healthy minutes×
(points+.7 assists)/minute, deterministic ID ties. Two/four full 10k branches force plays/sits before minutes/starters/matchups.
Stable `lineup-v1:` IDs identify sorted assignments. Expected is the **exact weighted empirical mixture**, never rounded to 10k
or re-simulated. Fixed status probabilities/independence are uncalibrated; unknown/cold inputs remain labelled.
Keep source/seed/version/origin hashes, precise float64 minutes and exact mass through Given/Joint/season operations.

Pathway v1: K8, initial uncertainty scale.4, update scale 1, memory cap 20 games; future score distributions are regulation,
with tied-score winner resolved separately. No learned future injury/rest hazard or complete postseason simulation.
Weighted near-term coupling preserves every original atom; it is **not certified iid season sampling**.

## Validation and release

Every input **and auxiliary fit** precedes origin. Important hazards: December 2025 assignment fits are unsafe for F1–F3;
whole-season priors/undated body data and batch defender fills need causal guards; fitted missing-profile medians precede
each test origin in both arms. Validation never fits fallback values. Input-only roster/position readiness is required: A2 found missing positions, with 190/190/179 supported games out of 200 per earlier fold; it selected the first 100 in frozen order without outcome selection (`20261123_a2_clock_ready_panels_v1.json`). Backtest clock parameters must match the fold node cutoff (`--clock-recipe`); parent preflight prevents a failing initializer from repeatedly respawning workers. Parser/input changes need matched cross-data tests.

| Fold | Fit through | Validation |
|---|---|---|
| F1 | 2023-12-31 | Jan–Apr 2024 |
| F2 | 2024-12-31 | Jan–Apr 2025 |
| F3 | 2025-09-30 | Oct–Dec 2025 |
| F4 | 2025-12-31 | Jan–Apr 2026 |

Burn-in Dec 2022. Protected 2026–27 starts 2026-07-01; once/frozen recipe at promotion. `train.py --final` fits through
2026-06-30, not today. Distinguish recipe identity from dated artifacts; a renamed failed recipe is not a new test.
Feature decay starts around 5 games roles,15 mix/usage,40 shooting,80 FT attempts with stat-specific archetype shrinkage;
accepted model-fitting weights have **no time decay**. Low-sample buckets use decayed offensive segments, not role games_eff.

Use an **explicit policy**, never an implicit historical default:
[v1](docs/protocols/promotion_v1_20261122.md) preserves original S01,
[v2](docs/protocols/promotion_v2_20261123.md) separates mechanics/learned/scenarios,
[v3](docs/protocols/promotion_v3_20261123.md) retains 27 proper-score bounds and 25 coverage diagnostics while reporting 17 cohort-bias
bounds separately. V3 followed the known r2v2 failure and required newly frozen independent confirmation; it does not rewrite that result.

Known pre-game roles: usage≥.25 star; otherwise start_share≥.5 starter, else bench; missing role stays unknown.
Supported tier inference needs 100 player-games/30 games. Pair identical games/inputs and bootstrap complete games 10,000 times,
seed 20261122; never count simulated worlds/players as independent historical observations. Proper scores grade whole distributions.
Keep bias, integrated expected randomized-PIT 80%coverage and joint/tail/pace diagnostics visible. No probability clipping;
zero winner probability yields infinite log loss. Distinguish material harm, unresolved precision and unsupported data.

Retained CRPS harm limits by star/starter/bench: MIN .0578/.0605/.0796; PTS .0898/.0711/.0553;
REB .0304/.0290/.0237; AST .0261/.0207/.0155;3PM .0200 each. Game total/margin .20, quarter total/margin .10,
win Brier .005/logloss .010. Upper paired 95% interval must lie below margin. Material coverage-harm lower bound>.03 vetoes.
Cohort signed-bias changes are diagnostic under v3: cancellation can make every individual prediction improve while cohort bias increases.
No margin was widened to pass r2/r3. Learned changes need a frozen primary benefit; mechanical fixes need correctness/compatibility.

Node comparator pairs declared node/fold panels with game-clustered loss uncertainty plus seed-only relative-RMS training noise.
Retain mean improvement beyond noise, pooled 2 SE evidence and no fold materially worse than twice noise. Explicit partial scope is
allowed; it is not all-fold confirmation. Node wins alone cannot promote an engine. Row game IDs/order do not prove unique decision identity
across rebuilt datasets; preserve dataset provenance. Constant nonzero changes with zero estimated SE retain their direction and are labelled.

Freeze component/removal tests, class-proportionate independent folds/streams and 10k stress **before** confirmation.
Current A2's frozen supported 100/F1–F3 + separate 200F4 +30 seed +3×10k protocol is candidate-specific, not a universal template.
Pathway changes need 16 origins/four seasons, paired per-date CRPS/dispersion/coverage/persistence; pooled averages cannot hide bad dates.
Exact points/player sums, period/team/box seconds, legal distinct fives, clocks/order, OT/foul-outs, missing/short rosters,
cutoff injection, raw replay, worker/resume identities and≤60 min full nightly remain required. Capture cannot change draws.
Asynchronous vector worlds can consume RNG differently after divergence; clock-on Q1–Q3 bit parity is not guaranteed.

## Evidence to carry forward

- **Data:** use rebound-at-miss clock across sources. In 2,677 reconciled F1–F4 games, player-period points and 21,702 explicit period-end
  scoreboards reconcile; segment sums can differ by 2 points. Same-clock substitutions need sequence-aware pre-event state.
  NBA tracking latest-team labels are wrong historically in 8,637/113,089 rows; use dated logs. Missing source publication times remain unknown.
- **Baseline:** legacy 200F4×1k: total/margin CRPS 11.723/9.415, total bias+1.81,80%coverage 69%/75.5%.
  Same-game team benchmark 11.353/9.322. Teacher-forced defence signal loss already exists; rotations are not proved irrelevant.
- **Earlier candidates:** S04 rim expression did not beat training noise; tracking increment worsened held-out loss.
  v1.4c/e/f pooled PTS changes+.0062–.0075 had intervals spanning 0. Their rejection does not disprove richer defence.
  NBA-only minutes had Δ−.00416[−.02699,+.01913]. S06 substitution MIN gain−.03529[−.04462,−.02609] was blocked by
  three old coverage-imprecision checks. Development-only v3 review clears 27/27 proper bounds: **revisit, not promoted**;
  current-baseline/seed/coverage provenance and independent confirmation remain necessary.
- **A1/r2:** original protected v2 remains 42/44(all 27 proper), with two cohort-bias bounds unresolved.
  Fresh independent 200F4/4,297 player-games under prospective v3 passes 27 proper/17 bias/25 coverage;
  MINΔ−.02345[−.04275,−.00640], PTS−.00806[−.01540,−.00129]. Raw replay, queue/resume and 227.8M legal fives pass.
  Conditional actual-participant accuracy does not validate availability probabilities.
- **A2 form:** residual/shot/persistence screens do not identify a stable pooled missing shooting factor beyond existing
  minute/event/state variance. Mean-preserving synthetic draws are tested, not calibrated or shipped. Unsupported form stays zero.
- **A2 clock:** contextual prior Q4/OT 0<clock≤24s pools use 4 clock×7 margin cells, minimum 100 opportunities/30 games;
  fallback clean whole-second bridge then legacy. No extra fitted node family or shared form factor.
  Earlier 1,932 games/5,382 opportunities joint timing loss .19856→.12849; independent F4 199/474 .21633→.13415,
  also beating the clean bridge. Engine development 200, supported earlier 300 and independent F4 200 each clear 27/27 proper bounds.
  Seed 30 clears 21/27 with five unsupported star cells/one imprecise Q4 score, no demonstrated harm under its frozen diagnostic rule.
  Three 10k stresses:34,679,026 legal fives; resume preserves 41 files; six raw wiring comparisons match.
- **Limits:** trailing 4–8/≤24s development 113 opportunities: action time 6.04→4.26s versus 4.14 actual;
  defensive foul share 9.00→13.36% versus 6.19%,3PA share 57.11→56.55% versus 68.61%.
  Independent corresponding 78 opportunities is unsupported. Better clock timing is not proof of better foul/shot choice or universal accuracy.
- **Protected clock decision:** accepted after the single protected 246-game/5,492-player-game test: 27 proper, 25 coverage and 17 bias bounds clear. Total CRPS Δ+.04910[+.01256,+.08451] and MINΔ+.000683 are small regressions, not an overall accuracy win. Receipt `20261123_a2_release_decision_v1.json` records the trade-off.
- **Closing 400-game r2 control audit:** 400 games/8,577 scored player-games: total bias +2.75 [1.05,4.48]; nominal 80% PTS coverage 76.3% (bench 75.0%, stars 81.6%). On 391 complete-minute games, simulated positive-minute players/team 10.21 versus 10.72 actual. Prior deep bench 531 player-games: 6.66 versus 7.76 minutes. Nine games excluded for missing minute truth; actual-participant rosters cannot grade full pre-tip DNP forecasting. This does not justify cutting bench minutes or uniformly widening ranges.
- **Scorer audit:** synthetic zero-SE neutrality and silent panel-intersection defects repaired prospectively; explicit policy selection required.
  This does not establish that an old real candidate was rejected for either defect. Frozen final sources/results remain intact.

Aggregate evidence: `analysis/experiments/20261123_r2_release_v1.json`,
`20261123_a2_clock_runtime_recipe_v1.json`, `a2_clock_final_20261123_v1{,_audit,_compare,_compare_gate}.json`,
`20261123_closing_scorer_precheck_v1.json`, `20261123_closing_controls_v1.json`, `20261123_closing_scorer_audit_v1.json`.
Clock source snapshot: `data/derived/experiments/a2_clock_final_20261123_v1_sources/`; do not overwrite.

## Decision index and deferred design

D1–D21 establish segments, shared nodes, investigated form, NBA priors, player-first chain, no market fitting,
five-world playback, runtime/refit goals and pathway identity. D22–D37 establish possession floor, miss-clock rebounds,
two engines, D29 minutes/D30 defence, branches, permitted NBA source and unchanged v1.3 after failed matchup variants.
D38–D43 establish weighted/checkpointed chunks, cutoff-safe history (deferredD 40), A/B scope and source-honest 2-D replay.
D44–D50 establish shooting distributions, laptop/phone, top-three branch selection, unpromoted availability/retries,
full minute precision and today-only possession boundary. D51–D57 establish audited release policy, noCI, PWA delivery,
incremental-export successor, photos, independent-world queue and cohort-bias correction. Full exact decisions remain archived.

Future zone work: start with NBA source-defined zones; audit units/orientation/labels/coverage and observed versus inferred defender
attribution. Estimate shooter/defender **attempts and makes**, shrink sparse cells to broader parents; retain supported side/direction.
Compare current bands, zone-only and within-zone distance. Player→zone versus zone→player are alternative joint factorisations;
test identical folds after selecting a shot branch. Zone form must separate opportunity/mix, conversion luck and defensive lineup,
without double-counting player/team variance. These are hypotheses, not approved representations or A2 additions.

A3 saves each team's maximum margin and maximum individual NBA fantasy world, plus a real representative world selected by
frozen multi-stat distance. Preserve actual draws; no isolated-world replay assumption. Reconcile event/box/clock/lineups before
one stored-only 2-D renderer, labelled spatial precision and local-file validation. Actual-game adapter follows later.
D39 history, if reauthorised, needs pre-origin inputs **and fits**, labelled actual-participant reconstructions, immutable originals,
explicit versions/coverage and safe atomic resume. Never silently mix recipes or supply actual minutes as predictions.
