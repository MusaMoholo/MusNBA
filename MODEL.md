# Prediction and evidence contract

Strategy: [PLAN](PLAN.md). Current charter: [HANDOFF](HANDOFF_NEXT.md). Working rules: [AGENTS](AGENTS.md).
This describes the inherited system and the standards for replacing it. Its architecture, features, labels, metrics, test suite
and release policy are all reviewable. Past qualification is provenance, not proof of optimal design or current predictive skill.

## What the product must earn

The primary task is a pre-game probability distribution over coherent play-by-play worlds: participation/minutes, events,
player boxes, periods, scores and winners must describe the same games. Accurate outcomes and calibrated uncertainty both matter.
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

Rebuild tests around hand-reconciled source fixtures and independent reference scorers; avoid checking a helper against itself.
Use property/metamorphic tests for conservation, player/team relabelling, legal bounds, worker/resume independence and future-input
injection. Known-good and deliberately bad forecasts must exercise scoring/ranking/acceptance behaviour, including zero-probability
log loss, missing support and values outside histogram support. Synthetic tests validate arithmetic/logic, not NBA predictive skill.
Keep deterministic, synthetic unit tests separate from real-source integration, statistical experiments and browser/release tests.
Real-source fixture data stays private/ignored with immutable hash manifests. Source rows do not belong in committed unit fixtures.
Retire duplicate, brittle or incumbent-behaviour-locking tests only after identifying their real protection and replacing it where needed.
Browser tests should use bounded calls, explicit document/data readiness and isolated fixtures rather than fragile navigation/count chains.

## Evaluation to build and then freeze

Start with a common schema and exact population/period/availability semantics for incumbent and baselines. Score player MIN/PTS/REB/
AST/3PM distributions by prior role/support and team points/total/margin/wins together. Report CRPS or an appropriate proper probability
score, MAE/bias, interval/reliability behaviour and joint/tail diagnostics. Event classification uses probability scores; durations
also need conditional timing error/support. Do not turn every diagnostic into a mandatory significance test or optimise signed bias alone.

Check training/runtime feature parity on the same recorded history before blaming model capacity. Connect observed-context prediction to free-running rollouts. Diagnose participation/minutes, opportunities, allocation, conversion
and joint dependence; use exact scoring identities rather than multiplying marginal expectations and ignoring covariance.
Realised-input diagnostics must declare what was fixed, what changed and interactions. Do not sum their gains as independent causal effects.

Development is exploratory within logged exposure; confirmation uses an unchanged recipe on an independent chronological block.
Track prior inspection: reorganising does not make old folds fresh. Protected 2026–27 exposures remain consumed as recorded;
C01 must not access protected/reserved outcomes. Future splits may change prospectively, preserving selection/monitoring/audit
boundaries. Never rescore an explored candidate under revised criteria and call it independent evidence.

Before any new promotion, freeze the candidate class, useful primary gain, practical critical-player/team harm limits, support,
calibration/joint requirements, multiplicity, precision/stopping rules and runtime/integration checks. Set numerical margins from
product stakes and outcome-blind precision/reference tests before candidate outcomes. Independent games/appropriate time blocks,
not players or Monte Carlo worlds, provide historical uncertainty. More worlds cannot resolve too few real games.
Unresolved evidence is not demonstrated harm or proof of safety. Known material harm blocks promotion; inadequate precision needs
more evidence or a research-only result. New policies are versioned; old decisions/thresholds are never rewritten retrospectively.
The three files under `docs/protocols/` are frozen historical reproduction inputs used by old tools, not the new operating policy.

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

## Evidence worth knowing, not repeating by default

The older 200-game defence comparison (`20261120T120827Z_compare_defence_F4.json`) measured predicted scoring per 100 possessions
against prior offensive and opponent defensive ratings. The opponent-defence coefficient rose from .440 to .686 versus 1.685 in
actual games: about 26% to 41% of the observed association. This is not prediction accuracy, a causal share of all defence, or a
current r3 remeasurement. Observational context, rating noise and uncertainty matter; forcing the ratio to 100% is not a valid goal.
The broader defence change also improved historical probability scores; its remaining headroom must be re-established fairly.

`analysis/experiments/20261124_b1_source_audit_v2.json`: known 200-game conditional panel, team CRPS 6.4149, MAE 8.9648,
bias +1.0778 (95% −.1470 to 2.2897). Component/player breakdowns already exist; reuse them. The long-shot recipe failed
(`20261124_b1_development_decision_v2.json`). A substitution attempt improved minutes without establishing required game compatibility
(`20261124_c4_s06_independent_decision_v1.json`). Neither identifies the best next intervention.
`20261124_b2_decision_v1.json`: three season-strength candidates did not qualify; historical schedule/exposure limits remain.
`20261125_chunk_b_completion_v1.json` records the inherited app/runtime release and independent accounting/import checks.
Rotation maps use all weighted worlds; selected replay examples are illustrations. These receipts are evidence, never work to resume.
