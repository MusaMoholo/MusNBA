# Product strategy

Build a play-by-play forecasting system whose player outcomes, team scores and uncertainty earn trust against real games.
Measured predictive skill is the goal; coherence and a usable product are necessary supporting properties.

The only detailed next charter lives in [HANDOFF_NEXT](HANDOFF_NEXT.md); model/evidence definitions in [MODEL](MODEL.md), rules in
[AGENTS](AGENTS.md), product use in [README](README.md). Previous roadmaps have no authority; later directions remain conditional.

## Why change the approach

Nothing technical is exempt from review: architecture, data/labels, features, evaluation metrics, promotion policy, unit/integration
tests, deployment and development workflow. Preserve a working product while replacements earn their cost; rewriting everything
is not itself progress. Player improvements must also preserve joint team behaviour. Diagnostics expose possible value;
only predictions from dated information can establish recoverable skill.

## Short term — prove predictable skill, then test the whole game

C02/C03 delivered working possession learners without forecast gains. Their limited/mismatched training packages cannot establish
an architecture or data ceiling. Stop treating plausible mechanisms and reusable infrastructure as sufficient reasons for another chunk.

C04 recovers dated minute skill; C05 carries calibrated standalone minute skill into improved overall player points on20 known
games but fails the high-usage-player harm limit. Neither earns release. MODEL owns all numbers and limits.
C06 challenges the capped-history/learner confound in on-court opportunity allocation: three conditional actor models, identical
uncapped supported history and dated inputs, then final coherent player/team distributions. Native minutes stay fixed to isolate
actor effects. High-usage harm may reflect role, opportunity, timing or sampling; the actor hypothesis is unproven. No criterion
rescue, arbitrary spread change or presumption that more data wins. Future combination with learned minutes depends on evidence.

The cultural change is explicit: measured error → admissible predictive signal → credible competing models → end-to-end benefit.
Each experiment must distinguish explanations. Use full supported information, training-only convergence checks and strong baselines;
record remaining confounds. Infrastructure serves a decision. No failed search becomes major product progress through acceptance credit.
MODEL owns results/limits; HANDOFF owns the frozen executable contract. Accuracy gains remain uncertain and production qualification separate.

## Medium term — spend effort where it can change results

Select each next bottleneck by measured headroom, support, uncertainty, end-to-end value and cost. Cheap diagnostics precede
expensive complete-game confirmation.

|Finding|Possible next chunk|Substantial deliverable even if a challenger fails|
|---|---|---|
|Knowing participation/minutes removes much error|Better dated roster/absence inputs and joint role/minute forecasts|Reusable causal input coverage and validated availability/minutes training/evaluation pipeline|
|Timing/opportunity counts dominate|Possession/restart/clock state and opportunity modelling|Audited state-transition representation and independently checked event/opportunity model|
|Opponent or zone effects are too weak or inaccurate|Shared team defence, lineup/likely-defender effects and zone-specific opportunity/conversion models|Reusable opponent/zone features and response tests, with honest source limits and end-to-end comparison|
|Observed-context event probabilities are weak|Player/team/context strength, shrinkage and event-rate modelling|Shared causal feature/training interface with measured component skill and reusable baselines|
|One-step predictions look sound but full games drift|Joint dynamics, shared game/team factors or an alternative coherent generator|A swappable coherent challenger and rollout diagnostics, rather than more isolated patches|
|Simple baselines beat the engine broadly|Challenge the architecture immediately|A fair, reproducible alternative modelling path; no obligation to preserve the sixteen-node design|
|Marginals are reasonable but wins/tails are wrong|Dependence and probability calibration|A learned, validated joint uncertainty layer; no arbitrary spread multiplier|

These are options, not a queue; findings can split, combine or eliminate them. Source limits remain explicit. Causal team/context
information is allowed: player-first means accurate coherent individuals and sums, not a ban on team information. A team-only
baseline cannot establish player/play-by-play accuracy.

## Long term — a coherent, proven predictive product

Earn reliable availability/minutes, conditional event probabilities and complete-game distributions together. The architecture
may become hierarchical or hybrid: shared team/game context, player roles and event transitions must agree within each legal world.
Earn accuracy, calibration and robustness through genuinely later games and immutable prospective forecasts, rather than
claiming operational skill from actual-participant backtests.

The goal is repeatable skill over both the incumbent and strong baselines across chronological windows, with credible player/team
uncertainty and prospective pre-tip evidence. No single favourable panel or seed establishes that goal.

Then propagate improved game worlds into season paths. Season tuning and unrelated interface polish are maintenance priorities
until the game engine earns more skill. Richer spatial/in-game prediction follows only when dated evidence and sources support it.

## How chunks make progress

Each modelling chunk is a bounded comparison of distinct MVPs for one bottleneck, followed by finalist delivery. Freeze the candidate
slate, practical promise/harm limits, selection budget, multiplicity and stopping before outcomes. Concentrate effort after evidence
of promise; build only shared infrastructure necessary for the experiment. Substantial reusable deliverables remain mandatory.

Report engineering acceptance, scientific conclusions and forecast gains separately. More green checks or a rejected model do not
prove major product progress. When all approaches lose, state that result and revisit the bottleneck/data/representation before
another chunk; do not fund another isolated recipe or expand the slate after seeing losses. Accuracy gains remain uncertain.

Each of 3–5 checkpoints ends with validation, lean docs, commit and push. Report skill separately from capability completion.
Keep one main question in progress; freeze candidate evidence rules before outcomes. Change the next charter, not a failed result’s meaning. If two consecutive modelling chunks deliver no meaningful end-to-end gain, prioritise an
architecture/data-ceiling challenge over a third local tweak. Production qualification remains independent of research completion.
