# Prediction and evidence contract

Strategy: [PLAN](PLAN.md). Current charter: [HANDOFF](HANDOFF_NEXT.md). Working rules: [AGENTS](AGENTS.md).
This describes the inherited system and the standards for replacing it. Its architecture, features, labels, metrics, test suite
and release policy are all reviewable. Past qualification is provenance, not proof of optimal design or current predictive skill.

## What the product must earn

The primary task is a pre-game probability distribution over coherent play-by-play worlds: participation/minutes, events,
player boxes, periods, scores and winners must describe the same games. Accurate outcomes and calibrated uncertainty both matter.
The owner requires possession-level generation: team shots/points emerge from events, with no separately predicted full-game
targets, remaining-quota features or aggregate steering. Historical player/team context may inform event probabilities. Coaching
rotation/minutes priors are explicit assumptions under legal time budgets; they are not a precedent for shot/score budgets.
Observed-context next-event prediction is a separate, useful diagnostic; good next-event scores do not establish good complete-game
forecasts. Live in-game prediction is not currently certified. Season forecasts are downstream consumers of game uncertainty.

Compare player and team accuracy together. A team-only model cannot establish player or event accuracy; a player model with
reasonable individual averages can still have bad joint totals, margins or tails. More simulated worlds reduce Monte Carlo noise,
not model error or historical sampling uncertainty. Nobody can guarantee that each plausible research idea improves accuracy.

## Inherited implementation — replaceable incumbent

`engine-v1.3-r3`, configuration `models/v1.3.json`, uses sixteen LightGBM event/actor/conversion decisions, prior role/minute
allocation, independently fitted world rotations, legal foul-outs/exhaustion and contextual late timing. State-responsive substitutions
were not promoted. It has no explicit 24/14-second shot-clock state or team-strength rating in possession nodes. Neither omission
alone proves an accuracy defect; quantify consequences.

This does not mean opponent-blind scoring. Fitted nodes already use opposing lineup defence, likely-defender/zone shooting-allowed
features and, in selected nodes, opposing team style. Broad shot locations cover rim, paint, midrange, corner three and above-break
three; defender shooting-allowed history combines the two three-point areas. These inputs can affect opportunities and conversion;
feature presence alone does not prove useful or sufficiently strong effects.

`report-bands-v1` availability probabilities and independence assumptions are uncalibrated. Up to one important uncertain player
per team creates two/four explicit branches. Expected retains exact mass; world count is not probability mass.
Runtime uses 10k worlds/branch in deterministic 1k chunks.

Team-pathway-v1 consumes near-term worlds once, then evolves per-world offence/defence: K8, initial uncertainty .4, gain1, memory cap20.
No learned future absence/rest/travel hazard. Competition scheduling, postseason/OT calibration and dependence remain limitations.
Keep it operational while game accuracy is the main development priority.

## Truth and information boundaries

ESPN/sportsdataverse/NBA Stats supply boxes, plays, coordinates, reconstructed fives and aggregate matchups. Reconcile identifiers,
points/seconds/periods, ordering and competition membership; Cup finals are not regular games. Distinguish scoring from possession
definitions. Missing observations stay missing.
All statistical features, fits, normalisation, residual calibration and priors precede the evaluated origin. Contemporaneous injury
reports require original retrieval/publication evidence as known before tip; source event date alone does not prove availability.

Keep four populations explicit:

|Population|Permitted claim|
|---|---|
|Original immutable forecast captured before tip|Operational forecasting performance for its recorded information set|
|Causal historical reconstruction with fully evidenced inputs/fits|Labelled hindcast performance; never an original forecast|
|Actual-participant/real-context replay|Conditional model diagnosis; not availability/DNP or pre-game operational validation|
|Realised-input oracle/intervention|Information/error headroom under its stated assumptions; not deployable skill or general causal proof|

Explicit DNP evidence establishes zero participation/counts even if the provider leaves that box blank; retain the raw missingness.
An unknown participation record cannot receive that interpretation. Rounded box minutes and reconstructed on-court seconds are
different observations. Event actors outside the reconstructed offensive five fail strict context validation; retain the mismatch
and declare supported rows rather than inventing a lineup or discarding otherwise reconciled game truth.

Historical reconstruction is a source/feasibility decision, not permanently forbidden or automatically valid. Audit what can really
be reconstructed. Prospective immutable capture is required where historical information timing cannot be recovered.

Broad-zone defender responsibility is already inferred from role/size/history. Ranks do not mean physical proximity. ESPN shot
coordinates/on-court fives and NBA aggregate matchups do not reveal every defender's location or verified primary/help roles.
Observed player defence maps are on-court exposure. No outcome-based assignment, invented tracking or false spatial precision.

## Four separate quality layers

1. **Truth/causality:** independent source reconciliation, identifiers, exclusions, timestamp/fit provenance and leakage injection.
2. **Mechanical correctness:** legal state transitions, clocks, five available teammates, fouls/OT, exact weights and conservation.
3. **Predictive skill:** future/out-of-sample player, event and joint team performance against strong baselines, with uncertainty.
4. **Operational reliability:** repeatable generation, immutable pre-tip capture, bounded runtime, import/offline/upgrade behaviour.

Passing one layer never establishes the others. The inherited 118-check smoke suite is an operational regression signal,
not an accuracy certificate. Existing tests/gates must be inventoried by failure mode and evidence independence before reuse.

Use hand-reconciled source fixtures and independent reference scorers; avoid checking a helper against itself.
Use property/metamorphic tests for conservation, player/team relabelling, legal bounds, worker/resume independence and future-input
injection. Known-good and deliberately bad forecasts must exercise scoring/ranking/acceptance behaviour, including zero-probability
log loss, missing support and values outside histogram support. Synthetic tests validate arithmetic/logic, not NBA predictive skill.
Keep deterministic, synthetic unit tests separate from real-source integration, statistical experiments and browser/release tests.
Real-source fixture data stays private/ignored with immutable hash manifests. Source rows do not belong in committed unit fixtures.
Retire duplicate, brittle or incumbent-behaviour-locking tests only after identifying their real protection and replacing it where needed.
Browser tests should use bounded calls, explicit document/data readiness and isolated fixtures rather than fragile navigation/count chains.

## Evaluation contracts

C01's [versioned contract](analysis/c01_contract_v1.json) defines its closed research comparison, not production promotion policy.
New experiments freeze their own recipes, benefit/harm/support criteria and stopping before outcomes. Common scores require the
same keys/truth and native units, keeping both sides/all players within each game and reporting calendar-block sensitivity.
Independent arithmetic and synthetic faults establish scoring logic, not NBA predictive skill.

Start with a common schema and exact population/period/availability semantics for incumbent and baselines. Score player MIN/PTS/REB/
AST/3PM distributions by prior role/support and team points/total/margin/wins together. Report CRPS or an appropriate proper probability
score, MAE/bias, interval/reliability behaviour and joint/tail diagnostics. Event classification uses probability scores; durations
also need conditional timing error/support. Do not turn every diagnostic into a mandatory significance test or optimise signed bias alone.

Check training/runtime feature parity on the same recorded history before blaming model capacity. Connect observed-context prediction to free-running rollouts. Diagnose participation/minutes, opportunities, allocation, conversion
and joint dependence; use exact scoring identities rather than multiplying marginal expectations and ignoring covariance.
Realised-input diagnostics must declare what was fixed, what changed and interactions. Do not sum their gains as independent causal effects.

Development is exploratory within logged exposure; confirmation uses an unchanged recipe on an independent chronological block.
Track prior inspection: reorganising does not make old folds fresh. Protected 2026–27 exposures remain consumed as recorded.
Honour each charter's outcome boundary; later splits change prospectively, preserving selection/monitoring/audit separation.
Never rescore an explored candidate under revised criteria and call it independent evidence.

Before any new promotion, freeze the candidate class, useful primary gain, practical critical-player/team harm limits, support,
calibration/joint requirements, multiplicity, precision/stopping rules and runtime/integration checks. Set numerical margins from
product stakes and outcome-blind precision/reference tests before candidate outcomes. Independent games/appropriate time blocks,
not players or Monte Carlo worlds, provide historical uncertainty. More worlds cannot resolve too few real games.
Unresolved evidence is not demonstrated harm or proof of safety. Known material harm blocks promotion; inadequate precision needs
more evidence or a research-only result. New policies are versioned; old decisions/thresholds are never rewritten retrospectively.
The three files under `docs/protocols/` are frozen historical reproduction inputs used by old tools, not the new operating policy.

For multiple MVPs, freeze the initial family/configuration slate, equal training-only selection allowances, shortlist rule, maximum
finalists and total compute/stopping budget before outcomes. Log every attempted recipe, including failures. Include all development
comparisons in multiplicity/selection-aware uncertainty; selecting a finalist does not reset exposure. Short complete-game tests can
inform the shortlist, but their games remain selection data. A best development score is not independently confirmed improvement.

The measurement basis is [proper probability scoring](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf)
and [chronological forecast evaluation](https://otexts.com/fpp3/toolbox.html#time-series-cross-validation). The specific architecture,
thresholds and bottleneck choices remain empirical product decisions.

## Invariants and credible alternatives

Within a world: player points equal team points, periods sum to the game, PTS = 2×FGM + 3PM + FTM, rebounds reconcile, and legal
minutes total 240/team in regulation plus 25/OT. Exact weights, unavailable-player constraints and source/world identities survive
branching, conditioning, aggregation and season coupling. A correction must preserve truths, not clamp/fabricate observations.
The same inputs/seeds reproduce independently of worker assignment. Serving only reads stored results.

Team/context priors, hierarchical shared game factors, different learners or a replacement generator are legitimate challengers.
Learn/calibrate them on prior data and connect them coherently to player events; no market fitting, arbitrary final-score correction
or unsupported spread multiplier. Stronger complexity earns its place through end-to-end evidence and manageable runtime.

Separately fitted conditional probabilities already define a joint law when multiplied along the event/actor/action chain.
A shared-learning claim requires common learned parameters or another explicit statistical coupling. Its legal next-choice law and
derived conditional probabilities must agree, including actorless outcomes. Compare architectures on identical supported information,
history and feature phase with declared capacity/selection budgets; keep legacy-package comparisons distinct. Joint learning has no
presumed accuracy advantage. A current-event label may condition a later head only after that event is sampled, never a joint input/mask.

## Evidence worth knowing, not repeating by default

The historical defence comparison (`20261120T120827Z_compare_defence_F4.json`) measured an opponent-rating association ratio
of about 41%. It is not current r3 accuracy or a causal share of defence; forcing it to 100% is not a modelling goal.

C01 [benchmark](analysis/experiments/20261125_c01_benchmark_v1.json) reuses the known B1 panel: 200 games, 400 team-games,
4,292 actual-participant player-games. Team-points CRPS (distribution error in points; lower is better) is 6.415 incumbent,
6.789 team-strength and 7.759 player-rate. Team-strength's extra error is 0.374 points (95% game interval .163–.586).
Older baseline history/shared minutes prevent pure architecture attribution; no production gain is claimed.

[Connected diagnostics](analysis/experiments/20261125_c01_localisation_v1.json): giving the fixed rate model real minutes reduces
player-points CRPS by 0.605 points (95% .549–.665) but worsens team-points CRPS by 0.294 (.115–.487). Real minutes plus shot attempts
reduce player error by 1.487 (1.407–1.572); team CRPS 6.568 still does not establish a gain over the incumbent. These are separate,
outcome-informed information diagnostics, not deployable gains or additive causal shares. Preserve joint team behaviour when improving players.
On identical recorded histories, shared and independently accumulated candidate features agree. The actor-time phase difference
has small one-step score impact; the opponent-defence coefficient gap is unresolved with game uncertainty. Zone replay is a separate
scenario, not original incumbent zones. These findings do not justify a clock/defence coefficient fix by assumption.

C01's [completion receipt](analysis/experiments/20261125_c01_workbench_v1.json) records independent fit/scoring reproduction and
worker replay; retained incumbent/zone worlds were pinned inputs. Its forecast ledger passed timing/fault integration on synthetic
artifacts only: zero real certified entries, no live hook. Outcome-informed headroom does not establish causal predictability.

C02's [frozen actor/action screen](analysis/experiments/20261125_c02_screen_v1.json) tests 200 known development games and 43,697
supported actions. Combined negative log probability (nats/action; lower better) is 3.19137 incumbent, 3.20253 candidate and 3.31416
role baseline. Candidate error rises 0.01116 (95% game interval 0.00921–0.01309; week 0.00895–0.01350). It fails the frozen screen;
no promotion or expansion beyond 20 wiring games. Candidate causal input features match independent event-history reconstruction
on 49,002 segments. The smaller training window/different feature/learner package limits attribution; this is not a possession-model ceiling.

The [paired C02 integration](analysis/experiments/20261125_c02_rollout_v1.json) generated 1,000 worlds per arm on 20 games
(427 player-games). Player-points CRPS change is +0.0109 points (95% game interval −0.0192 to +0.0427); team-points change is
+0.1168 (−0.0266 to +0.2585). These are wiring results, with insufficient support for qualification. All counts/scores emerge
from events. Schedule and rotation rules are shared; different simulated fouls can change realised player minutes between arms.

C02 closes in its [completion receipt](analysis/experiments/20261125_c02_completion_v1.json). Fresh independent training and
probability/scoring reproduction agree with the frozen run; a fresh-fit single-worker 1k game matches the ten-worker candidate arrays
exactly. The delivered research adapter generates shots/points from events, with no aggregate targets. Production is unchanged.

C03's [frozen three-family comparison](analysis/c03_contract_v1.json) uses common causal player/team/history inputs and 43 legal
next outcomes. [Event scores](analysis/experiments/20261125_c03_events_v1.json) cover 47,284 supported choices on 200 known games;
all candidates lose to the incumbent. The [paired20 comparison](analysis/experiments/20261125_c03_mvp_v1.json) covers 427 player-games,
1,000 worlds/arm/game. Player-points CRPS changes (points; lower better) are +0.0214 linear, +0.0156 separate nonlinear and +0.1436
shared scorer. The strongest nonlinear path's 95% game interval is −0.0213 to +0.0529; team-points change +0.1824 exceeds its +0.1
practical limit. No family meets primary promise or team harm rules; no finalist expands. All three initial comparisons count in
familywise game/week uncertainty; only four week blocks limit precision. This is a bounded development negative search, not a model-class
ceiling or operational confirmation. Production remains unchanged. The capped sample, finite model capacity and older incumbent
package limit attribution; diagnostics and legal/accounting checks do not establish forecast improvement.
The [independent negative audit](analysis/experiments/20261125_c03_negative_audit_v1.json) reproduces the failed primary/team decision
and selection-adjusted game intervals; 80,000 saved worlds pass independent accounting and 47,076 scalar/half-score checks.

C03 [closes](analysis/experiments/20261125_c03_completion_v1.json) after [fresh independent reproduction](analysis/experiments/20261125_c03_reproduction_v1.json):
all three model files/probabilities match exactly, independent probability scores agree within 7e-16, and each freshly fitted
single-worker 1,000-world replay matches every original multi-worker array. Deliverables are complete; forecast gains are not demonstrated.

C04's [joint-role screen](analysis/experiments/20261125_c04_minute_screen_v1.json), 200 known games/4,292 player-games, finds
predictable minute skill: regulation-minute CRPS falls from 3.522 native to 3.224/3.117/3.313 for residual/nonlinear/analogue models.
Lower is better; nonlinear change −0.405 minutes has 95% game interval −0.481 to −0.329 and familywise game/week support. However 80%
intervals cover only 71.4%/68.2%/73.9%, versus 78.7% native. All fail frozen coverage; no expanded game comparison or promotion.
These are dated actual-participant development component gains, not calibrated game/operational gains. Source minute gaps remain
unscaled/flagged. The [independent audit](analysis/experiments/20261125_c04_decision_v1.json) reproduces eligibility and confirms the same
gain/undercoverage pattern on 175 reconciled games. Two-game wiring is mechanical evidence; old rotation-fitter tail errors remain a translation limitation.

The B1 component audit remains reusable source evidence. The long-shot recipe failed
(`20261124_b1_development_decision_v2.json`). A substitution attempt improved minutes without establishing required game compatibility
(`20261124_c4_s06_independent_decision_v1.json`). Neither identifies the best next intervention.
`20261124_b2_decision_v1.json`: three season-strength candidates did not qualify; historical schedule/exposure limits remain.
`20261125_chunk_b_completion_v1.json` records the inherited app/runtime release and independent accounting/import checks.
Rotation maps use all weighted worlds; selected replay examples are illustrations. These receipts are evidence, never work to resume.
