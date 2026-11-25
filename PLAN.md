# Product strategy

Build a play-by-play forecasting system whose player outcomes, team scores and uncertainty earn trust against real games.
Measured predictive skill is the goal; coherence and a usable product are necessary supporting properties.

This is a fresh operating plan. Previous roadmaps, percentages and unfinished tasks are removed. The current executable charter
lives only in [HANDOFF_NEXT](HANDOFF_NEXT.md); model/evidence definitions in [MODEL](MODEL.md), rules in [AGENTS](AGENTS.md),
product use in [README](README.md). Only the next chunk is fixed. Everything beyond it changes when the evidence changes.

## Why change the approach

Nothing technical is exempt from review: architecture, data/labels, features, evaluation metrics, promotion policy, unit/integration
tests, deployment and development workflow. Preserve a working product while replacements earn their cost; rewriting everything
is not itself progress. Recent shooting, substitution and season-strength changes did not establish broad accuracy gains.
C01's connected comparison shows why player improvements must answer to joint team behaviour. Diagnostics expose possible value;
only predictions from dated information can establish recoverable skill. Use that distinction before choosing a narrow intervention.

## Short term — test predictable joint opportunity improvements

C01 delivered the working comparison/diagnosis system, independent checks, competing baselines and prospective capture API.
Its measured results and limits live in MODEL. The incumbent remains preferred to the fixed simple challengers; no production
accuracy gain is claimed. Reuse the workbench rather than rebuilding another audit.

Next, test whether dated current player/team information can improve joint shot opportunities with incumbent minutes held fixed.
Build reusable labels, causal features and chronological probabilistic learners; distinguish team volume from player allocation.
Outcome-informed diagnostics exposed headroom but did not identify the fraction predictable before tip, and older comparator
histories limit architecture attribution. Better individual forecasts must also preserve team probability accuracy and dependence.

Cheap recoverability evidence determines whether to connect one challenger to coherent event worlds. Shared game/team factors,
conditional allocation and a coherent count alternative compete fairly; preserving the sixteen-node architecture is not a goal.
No clock change, forced defence loading or standalone minutes correction follows automatically from the diagnostics.
The committed data/training/scoring capability must work even if the challenger fails. Separate truth, mechanics, skill and
operational checks; synthetic passes alone establish no NBA forecast improvement. Qualification on independent evidence remains
separate from research completion, and operational claims require genuine pre-tip captures.

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

Every charter has one bottleneck, a bounded modelling decision and a precommitted major reusable capability. The capability must
serve the accuracy goal directly: better causal data, measurement, representation, training or deployment reliability.
A failed hypothesis does not justify cosmetic consolation work. A failed model is not an accuracy improvement, and an unfinished
capability does not become complete because an experiment ended. Scientific gains are uncertain; engineering acceptance is explicit.

Each of 3–5 checkpoints ends with validation, lean docs, commit and push. Report skill separately from capability completion.
Keep one main question in progress; freeze candidate evidence rules before outcomes. Change the next charter, not a failed result’s meaning. If two consecutive modelling chunks deliver no meaningful end-to-end gain, prioritise an
architecture/data-ceiling challenge over a third local tweak. Production qualification remains independent of research completion.
