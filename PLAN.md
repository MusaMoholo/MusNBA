# Product strategy

Build a play-by-play forecasting system whose player outcomes, team scores and uncertainty earn trust against real games.
Measured predictive skill is the goal; coherence and a usable product are necessary supporting properties.

This is a fresh operating plan. Previous roadmaps, percentages and unfinished tasks are removed. The current executable charter
lives only in [HANDOFF_NEXT](HANDOFF_NEXT.md); model/evidence definitions in [MODEL](MODEL.md), rules in [AGENTS](AGENTS.md),
product use in [README](README.md). Only the next chunk is fixed. Everything beyond it changes when the evidence changes.

## Why change the approach

Nothing technical is exempt from review: architecture, data/labels, features, evaluation metrics, promotion policy, unit/integration
tests, deployment and development workflow. Preserve a working product while replacements earn their cost; rewriting everything
is not itself progress. Recent shooting, substitution and season-strength changes did not establish broad accuracy gains. One conditional 200-game audit showed team bias +1.08 points against mean absolute error 8.96: cancelling
average bias alone would leave most individual-game error. Player cohorts also differ. Those results do not identify the dominant cause.
We need a connected explanation of error and strong competing baselines before choosing another narrow intervention.

## Short term — establish the accuracy workbench

The next chunk builds a reusable benchmark and diagnosis system and challenges the measuring system itself.
Inventory tests by real failure mode, independently verify truth/scoring, and replace brittle or self-confirming checks. Separate data
validity, engine correctness, predictive skill and delivery reliability; a green inherited smoke suite certifies none of the others.
This is not another descriptive audit or predetermined clock fix.
Compare the incumbent with a transparent player-rate baseline and a direct team-strength baseline on identical, time-correct inputs.
Separate availability/minutes, opportunities, player allocation/conversion and error accumulated through simulated game states.
Connect next-event predictions in observed contexts to complete simulated games. Carefully labelled outcome-informed diagnostics
estimate where better information could help; they never count as deployable forecasts.

Deliver a repeatable workbench, independent reference tests, source/exposure manifests, competing forecasts, prospective capture
and an evidence-backed next decision. Reuse existing captures/audits; no production-model promotion is promised in this foundation chunk.

## Medium term — spend effort where it can change results

Select each next bottleneck by measured headroom, support, uncertainty, end-to-end value and cost. Cheap diagnostics precede
expensive complete-game confirmation.

|Finding|Possible next chunk|Substantial deliverable even if a challenger fails|
|---|---|---|
|Knowing participation/minutes removes much error|Better dated roster/absence inputs and joint role/minute forecasts|Reusable causal input coverage and validated availability/minutes training/evaluation pipeline|
|Timing/opportunity counts dominate|Possession/restart/clock state and opportunity modelling|Audited state-transition representation and independently checked event/opportunity model|
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
