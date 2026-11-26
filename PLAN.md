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
C06's three full-history conditional actor laws fail useful-gain requirements; two nonlinear fits remain budget-bound. The actor
replacement hypothesis has not explained C05's high-usage harm. Further actor work needs convergence/information parity evidence,
not another isolated head recipe. C07 coherent selection improves overall player points on 159 known games and clears critical-player harm limits, but no candidate
clears all team/calibration safety requirements; learned selection lacks decisive benefit over a simple pool. Production stays fixed.
C08 challenges the actual-participant input boundary through dated participation/full-roster forecasts. First measure supported
absence/cohort error and supervised learnability; do not presume it explains C07 conditional calibration or rescues its decision.

Follow [AGENTS](AGENTS.md): measured error → admissible signal → credible competing models → end-to-end benefit.
MODEL owns results and limits; HANDOFF owns the executable contract. Research completion and production qualification remain separate.

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

AGENTS owns checkpoint, validation and delivery rules. Select one measured bottleneck, compare distinct credible models and report
capability separately from forecast gains. After two chunks without meaningful end-to-end gains, prioritise a data/architecture
challenge over another local tweak. A failed decision stays failed; the next charter changes. Production qualification remains
independent of research completion.
