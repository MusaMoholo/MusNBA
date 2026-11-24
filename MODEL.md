# Model contract and evidence

Current state/jobs/delivery: [HANDOFF](HANDOFF_NEXT.md). Scope: [PLAN](PLAN.md). Commands/product: [README](README.md).
This file owns current design, validation and facts that change future decisions. Older detailed measurements/protocols and D1–D57
wording are preserved in the verified [history archive](README.md#documentation-history); consult relevant sections only.

## Accepted architecture

**engine-v1.3-r3**, unchanged `models/v1.3.json` fitted nodes; D29 target rotations/pool 0, Rule 3 foul-outs,
independent per-world rotation fitting and deterministic 1k chunks,10k worlds/branch. **Contextual late-clock timing is accepted and delivered.**
For ET origin D, result games before D, rebuild dated profiles/minutes/rotations/matchups and team ratings.
Possession worlds cover today's games only. Team pathway v1 consumes those exact outcomes and plays tomorrow onward,
updating each world's offence/defence from its own score surprises. Serving only reads saved results. C1 `early-complete-game-v1` uses complete-game hashes, exact-input chunk resume, bounded cancellation and background scheduling beside publication. Partial bundles require `early-delivery-v1`; retained-season freshness stays explicit.

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

**D60 availability — report-bands-v1:** owner-selected0/25/50/75/100% assumptions, not a calibrated model upgrade.
Clear status: out/suspended/IR0, doubtful25, questionable50, probable75, active100. For generic DTD/unknown,
`projection.report_availability` uses explicit game-day wording only: target weekday or publication-day today/tonight,
report age 0–6 ET dates. Contradictory, stale, undated or ambiguous text stays50; no invented report interpretation.
Unlisted active remains a labelled assumption;≥3 recent games/no appearances reduces it to75 for prior 20+ minute roles, otherwise50.
Actual confirmed availability is not downgraded by that fallback. Preserve source comment, reason, policy, date and exact branch weights;
older forecasts retain original semantics. Dated outcome evidence is needed before claiming calibration or replacing this policy empirically.

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
A2's100/F1–F3+200F4+30seed+3×10k protocol is candidate-specific, not universal.
Pathway changes need 16 origins/four seasons, paired per-date CRPS/dispersion/coverage/persistence; pooled averages cannot hide bad dates.
Exact points/player sums, period/team/box seconds, legal distinct fives, clocks/order, OT/foul-outs, missing/short rosters,
cutoff injection, raw replay, worker/resume identities and≤60 min full nightly remain required. Capture cannot change draws.
Asynchronous vector worlds can consume RNG differently after divergence; clock-on Q1–Q3 bit parity is not guaranteed.

## Evidence to carry forward

- **Data:** 2,677 reconciled F1–F4 games: player-period points and21,702 explicit period-end scores reconcile; segments can differ by2 points.
  Use rebound-at-miss clocks and sequence-aware substitutions. NBA latest-team labels misattribute8,637/113,089 historical tracking rows;
  use dated logs. Missing publication times remain unknown.
- **Earlier candidates:** S04 rim signal did not beat training noise; tracking worsened loss. v1.4c/e/f PTS changes+.0062–.0075 span0;
  they do not disprove richer defence. NBA-only minutes Δ−.00416[−.02699,+.01913]. Independent S06 MIN gain−.03694[−.05002,−.02546] clears25/27
  proper bounds; win Brier/log-loss remain unresolved. Fixed attempt closed; retain r3.
- **A1/A2:** r2 independent fitting passed fresh 200-game v3 confirmation. Original protected v2 remains42/44. A2 found no supported stable
  missing shooting-form factor; synthetic variance is not calibration and form stays zero. Conditional participant tests cannot validate availability.
- **Clock:** prior Q4/OT≤24s pools,4clock×7margin cells, minimum 100 opportunities/30 games; bridge then legacy fallback. Development trailing4–8/≤24s:
 113opportunities, action time6.04→4.26s versus4.14actual; foul9.00→13.36% versus6.19%;3PA57.11→56.55% versus68.61%.
 Independent78opportunities unsupported. Timing evidence is not shot/foul-choice accuracy.
- **Protected r3:** once-only 246 games/5,492 player-games:27 proper,25 coverage,17 bias bounds clear. Total CRPS Δ+.04910[+.01256,+.08451],
 MINΔ+.000683: small overall regressions accepted for supported timing gains, not a universal accuracy win.
- **Closing r2 audit:**400 games/8,577 player-games: total bias+2.75[1.05,4.48], PTS80% coverage76.3% (bench75%,stars81.6%).
 391 complete-minute games: positive-minute players/team10.21 versus10.72actual; deep bench531player-games6.66 versus7.76minutes.
 Nine missing-minute games excluded. Actual-participant rosters cannot grade pre-tip DNPs; no blanket bench cut/range multiplier follows.
- **Scorers:** synthetic zero-SE neutrality and silent panel-intersection defects repaired prospectively; explicit policy required.
 No proof an old real candidate failed for either defect. Frozen final sources/results remain intact.

Canonical receipts under `analysis/experiments/`: `20261123_r2_release_v1.json`, `20261123_a2_release_decision_v1.json`,
`20261123_a2_clock_runtime_recipe_v1.json`, `a2_clock_final_20261123_v1{,_audit,_compare,_compare_gate}.json`,
`20261123_closing_{scorer_precheck,controls,scorer_audit}_v1.json`.
Frozen source: `data/derived/experiments/a2_clock_final_20261123_v1_sources/`; never overwrite or rescore.

## Decision continuity

D1–D57 remain in the verified archive; D58 defined Chunk C. D59 expands its product/calendar scope and pulls current-data UX into U24.
D60 authorises report-derived availability bands. New source permissions, protected tests and old decisions remain intact.

## Chunk C model and capture contract

D58/D59: C1 early exports, C2 zones, C3 S06, C4 analysis/replay, C5 competitions/integrated release.
[HANDOFF](HANDOFF_NEXT.md) owns weights/ladders; planning is not promotion.

**Zones:** [NBA basic/advanced areas](https://jr.nba.com/how-to-read-a-shot-chart/) define the taxonomy.
C2 derives22 cells, including unknown2/3, from rounded ESPN coordinates; it does not supply native annotations or tracking.
Three pre-burn-in native games validate units/orientation and mutually unique player/period clocks within1s; event IDs are not interchangeable.
Fine regions match529/530 native-coordinate pairs and505/530 rounded-coordinate pairs; one native label conflicts with official3PT value.
Official value remains authoritative. Raw sources/unknowns persist; dates do not prove original publication/revision timing.
C2's [fixed study](analysis/experiments/20261124_c2_research_decision_v1.json) found no PTS benefit versus either control; retain r3.

Research profiles use strictly prior shooter and defender/on-court **opportunities, attempts and makes**, separating frequency from conversion.
Use exposure-aware shrinkage to broader parents, fitted before each origin. Audit sums/denominators and assignment weights.
Distinguish recorded defenders, soft inferred assignments and on-court exposure: shot charts alone do not identify the nearest defender.
Compare a matched current-representation control and at most three declared node variants: zone-only; zones plus within-zone distance;
then supported defender-zone frequency/conversion. Select on F1–F3 only, without changing hyperparameters/decay opportunistically.
Keep player-before-zone ordering. Version/retrain affected node interfaces together, with prior-fit clock/matchup/role artifacts per fold.
Different zone label spaces make raw categorical losses incomparable: aggregate to an identical partition where valid; otherwise use
common make/miss rows and end-to-end proper scores, not a false node rejection. If inputs/parser eligibility change, isolate that bridge and require matched rows/source identity;
do not compare a new dataset to incompatible cached losses or silently drop unmatched outcomes.

**Rotations:** [C3](analysis/experiments/20261124_c3_research_decision_v1.json) recovered the exact S06 out/in models and timeout templates.
`StateRotations` keeps those pre-event score/clock/foul/target decisions, independent per-world r3 fitting and current Rule3 legality/penalties.
Strictly prior proxies reproduce7,317 old rows exactly. Publication LegalCapture and backtest Observer now delegate the selected policy;
three publication/research and three default-off full chunks match raw arrays. Independent200-game/4,287-player-game
confirmation improves MIN but leaves two win-score safeguards unresolved; no broader rescue/protected test. MIN80% coverage78.00→76.65%.
Canonical: `20261124_c4_s06_independent_decision_v1.json`. Conditional participation does not validate live DNP/availability.

**Finite qualification:** freeze namespaces, IDs/input-only exclusions, auxiliary cutoffs, learned/v3 and benefit multiplicity
before outcomes. Reuse raw-parity controls; never rescore protected r3. Each family gets three-game wiring and one 200-game F4 screen:
shots primary pooled PTS CRPS, rotations primary MIN CRPS. No rescue/replacement family; unchanged development recipes may repeat after
accounting/setup repairs. Freeze at most one survivor/family for combined/removal development tests; research checkpoints do not promote.

Reserve 200 disjoint F4 games before selection; candidate outcomes stay unseen until recipes freeze. Require independent primary benefit
and unchanged safeguards. Broader confirmation: all input-eligible F4 plus fixed200/F1–F3, reusing overlaps and distinguishing development
from independence. Freeze one 200-game independent-stream diagnostic and20-game×10k stress panel prospectively. Apply game-cluster
uncertainty, role support and multiplicity; disclose unresolved diagnostics and veto applicable harm. C4 freezes the qualifier; C5 runs
one protected evaluation. Retain r3 on failed/unsupported components; never rename failures, tune from final results or widen margins.

**Visible worlds:** save compact zone attempt/make counters with exact box/period/weighted identities; observed versus predicted maps
show sample support/unknowns and remain useful on r3 if no model promotes. Select five positive-mass Expected worlds/game: each team's
maximum own margin; each team's maximum individual NBA fantasy score (PTS+1.2REB+1.5AST+3STL+3BLK−TOV); one real representative
using frozen multi-stat normalisation/distance/ties. Record branch/chunk/world IDs and weights; labels may share a world.
Capture by replaying each selected world's **original full canonical chunk** with read-only observers and exact raw parity, never by
simulating that world alone. Bound/benchmark extra replay cost. Reconcile event clocks, scores, player boxes, minutes and legal fives.
Use known zones/events and a lineup/rotation strip, not invented tracking positions, pass sequences or trajectories.
Lineup filters must respect each example's source branch. Browsing only reads saved events; missing geometry permits event-list/box playback.

Zone-form factors, alternative chain ordering, talent uncertainty, new substitution families and pathway calibration remain separate work.
D39 replay stays deferred: any future reconstruction needs pre-origin inputs **and fits**, predicted minutes, immutable originals and explicit versions.

## Competition and analysis contract — C4/C5

Northstar: expose every meaningful stored/derived metric through discoverable definitions, support, tables/charts and conditions.
Inventory available versus missing capture; extend advanced rates/conditional outcomes/heatmaps, not one-off examples. Shared game/lineup
context, sortable tables and collapsible secondary tools continue U24. Use MusSim, MLB Savant and NFL Next Gen Stats for presentation
ideas; this grants no ingestion permission. Regular season/Cup/Playoffs become core sections with shared Players/Teams/Game Centre.

Retained2026–27 schedule:1200 games,30 teams×80 games,60 Cup-labelled; dynamic competitions are absent. Complete **82 regular games/team=1230 games**,
not82+2. One canonical event with competition flags prevents double simulation: group/QF/SF count in regular82; Cup final does not.
World-local Cup:6 group winners+2 wildcards, official regulation-only tiebreaks, correct hosts.22 nonqualifiers each get 2 games;
4 QF losers each get 1;4 QFs+2 SFs complete the30 missing league fixtures. Unpublished pairing/travel algorithms require frozen feasible
matching assumptions/sensitivity labels; actual draws replace slots. Prefer dated league announcements over stale FAQs/team pages:
[2026–27 semifinals](https://pr.nba.com/nba-cup-semifinal-host-sites-coachs-challenge-rules/) are higher-seed home games;
[final](https://pr.nba.com/hinkle-fieldhouse-emirates-nba-cup-2026-championship/) is neutral Indianapolis. Reverify season-versioned rules.

Play-in:7hosts8 for seed7;9hosts10, winner visits7/8loser for seed8. Fixed-bracket best-of-seven playoffs, no reseeding,
2-2-1-1-1 homes, stop at 4 wins; chronological world-local rating updates continue. Define regulation/final/OT scores explicitly:
current pathway has regulation scores plus separate tie winner, insufficient for every official standings tiebreak.
No rating/calibration retune here. Initial postseason outputs make no historical-calibration claim.

Acceptance:82 regular games/team; one Cup champion/world;16 playoff teams,15 series,one NBA champion/world; no duplicate/eliminated-team games,
correct hosts/counts and normalised weighted stage/matchup/series-length/title probabilities from the same paths. Scope accounting by
competition: unequal postseason game counts are valid. Rule/source manifest and design references: `20261123_chunk_c_plan_v2.json`.

U24 evidence: Expected Ty Jerome's earlier20k-world game labelled100k probability units as worlds; arithmetic was weighted correctly.
Views now record raw/defined counts separately and enrich every lineup case. Independent6,435 rate distributions pass.
Fresh reports remove Brandon Miller's uncertainty branch; Brown/Zion map75%,Siakam/Wembanyama50%. This is an assumed input policy, not calibrated accuracy.
