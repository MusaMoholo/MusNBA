# Promotion and delivery v2 — 23 November 2026

**Authority D51:** the owner explicitly authorised auditing/redesigning the inherited promotion framework.
This revision is made with the old development results already known; it is not a preregistration retroactively
applied to unseen results. Preserve all old decisions/metrics. Freeze this contract and a fresh confirmation
population before another candidate result. Cutoffs, raw retention, ten-thread budget and protected final test
remain mandatory. No automatic promotion follows from a reclassified historical screen.

## Classify the change before choosing its test

| Class | Required benefit | Evidence required before delivery |
|---|---|---|
| Stored-data/UI/accounting | Correct, coherent and useful representation | Exact identities, deterministic/legacy handling, fail-closed missing cases, responsive/PWA/performance checks. No statistical accuracy gain is needed for a selector or lossless decoder. |
| Basketball-rule/implementation correction | A reproduced defect is corrected to the intended rule | Authoritative rule/independent reference; affected/unaffected-state tests, score/minute/lineup accounting, deterministic streams; paired player-first **non-inferiority** on development games and separate confirmation. It need not manufacture a detectable pooled accuracy improvement. |
| Learned predictor, minute policy, form or calibration | Prespecified improvement against real outcomes | Primary proper-score improvement with game-cluster uncertainty and required core non-inferiority; fold-safe calibration, matched controls, independent confirmation/seed evidence. Added variance or matching a descriptive covariance is insufficient. |
| Availability/scenario assumption | Transparent conditional sensitivity under a stated input | Validate each published roster/branch and exact weights/season use. Fixed or user-selected weights are labelled assumptions. A claim of learned injury probability additionally needs genuinely dated report cohorts and held-out play/start scores. |

Mixed changes meet every applicable class. A correction that changes a learned substitution policy cannot be
declared mechanical merely to avoid predictor tests. Mechanically changing fitted weights also remains a learned
change. The supported publication scope may be narrower than every historical context; state that scope explicitly.

## Invariants and provenance — hard stops

Every published case must have valid inputs/model identity and origin-safe joins, legal available fives (or a
documented NBA exception), exact player/team/period/seconds/mixture identities, finite supported outputs and
deterministic replay. Missing/corrupt/late inputs and unknown exceptions are never retried into acceptance.
Unsupported games/branches fail with reasons and remain outside published forecast coverage; retain their counts
and characteristics. A missing historical roster does **not** prove every supported live game is unsafe. Nor may
supported live rosters be presented as historical availability validation. All published cases need their own checks.

For sixth-foul exhaustion, use NBA Rule 3-I: normally remove disqualified players; when no legal substitute
remains, retain the necessary currently playing offender and apply the specified personal/team/technical foul
penalties, including subsequent offensive fouls. Injury/ejection re-entry is a distinct rule and cannot be
claimed when not modelled. Technical shooters must be eligible in-game players (Rules 3-V/12A-V).
Sources: [NBA Rule 3](https://official.nba.com/rule-no-3-players-substitutes-and-coaches/),
[NBA Rule 12](https://official.nba.com/rule-no-12-fouls-and-penalties/).

## Predictive evidence — measure loss, harm and uncertainty separately

Retain pre-game star/starter/bench definitions and original CRPS/bias harm margins in TRAINING's legacy S01
table. Compare identical game/player keys and outcomes, reporting unknown/missing tiers separately. Supported
inference still needs 100 player-games/30 games; sparse groups are explicitly unsupported, not zero/harm-free.
Do not require 100 observations of a rare unknown tier before any unrelated supported feature can ship.

Mandatory compatibility outcomes for rule corrections and predictors are the **15 tier/stat CRPS bounds**,
**10 full-game/quarter total/margin CRPS bounds**, **17 player/full-game bias bounds**, and win **Brier/log loss**:
44 bounds. Retain their numerical margins unchanged. Upper 97.5% paired game-bootstrap harm bound must be below
the margin. A lower bound already beyond it is evidence of material harm; an interval straddling it requests
more information, not a claim of safety or demonstrated harm. Do not widen margins to pass a candidate.

Coverage, PIT, tails, OT, state response and joint dependence remain required diagnostics. All 25 original
coverage outcomes are reported with uncertainty. A mechanics release is blocked by demonstrated material
calibration harm (lower 95% harm bound > the unchanged 0.03 coverage-error margin), not solely an upper bound
that lacks precision. Unresolved diagnostic cells stay labelled and inform targeted confirmation. A form/
uncertainty candidate claiming calibration or joint improvement must preregister relevant distributional/joint
outcomes as mandatory benefits; it cannot hide worsening calibration behind improved means.

Use CRPS/Brier/log score as proper distribution-quality objectives, rather than optimising one arbitrary
coverage threshold alone; [Gneiting & Raftery](https://stat.uw.edu/research/tech-reports/strictly-proper-scoring-rules-prediction-and-estimation).
For discrete predictions, report deterministic expected randomised-PIT coverage when raw worlds exist:
the length of `[F(y-),F(y)] ∩ [0.1,0.9]` divided by the point mass; at zero mass use the usual PIT indicator.
This integrates the auxiliary uniform draw instead of making a release depend on its seed. Preserve legacy
single-random-PIT results alongside it; never invent raw counts from rounded summaries.

Bootstrap complete paired games, 10k resamples, fixed seed 20261122; never treat player rows/worlds as independent
real games. Use actual participants only for explicitly conditional diagnostics. Simulation replicates quantify
Monte Carlo sensitivity. An independent-seed control comparison is a resolution diagnostic, not a universal
minimum effect size imposed on a strongly paired correction. Learned improvements require a primary interval
favouring the candidate and consistent independent-stream confirmation; report effect size and simulation noise.
Keep all attempts and apply Holm correction to multiple primary benefit claims. Requiring all mandatory
non-inferiority outcomes is an intersection requirement; do not falsely describe the old issue as an automatic
type-I-error inflation from 69 tests. Its observed problem includes precision/power and applying the wrong class.

## Confirmation and final holdout

Learned changes retain the existing F1–F4/broader-game/component-removal and season-origin confirmation design.
Rule-only changes with unchanged fitted nodes use a proportional frozen plan: existing dev evidence plus a fresh
matched game panel, independent-stream/stress checks and explicit rule/accounting coverage. They do not need
to refit sixteen unchanged nodes merely to test an implementation correction. Source/recipe and fitted-model
identities remain distinct. No release can rely only on a repeatedly inspected 200-game screen.

For the current foul-rule reassessment, freeze **200 F4 games outside the old 200-game panel**, selected by
ascending SHA-256 of `promotion-v2-rule3|game_id` from the original 718 eligible confirmation IDs. Pair control
and corrected rule at 1,000 worlds with the original seed namespace. Record every selected ID/input hash before
runs; a three-game integration pilot precedes the full panel. Capture raw worlds and late-state diagnostics in
this same pass for A2, avoiding a separate control rerun. Predeclare stress/independent-stream checks before
their outputs; these may establish mechanics/resolution, never replace the independent real-game denominator.

The 2026–27 final test stays unavailable for selection. Freeze a qualifying changed recipe before its one
formal final-test evaluation; unchanged node artifacts retain their existing recorded node score and are not
refitted/rescored as if new models. Any rule-level final evaluation is separately versioned and never used to
retune the correction. Release may be blocked by a final failure; further work returns to development data.

## Delivery

A release manifest records class, fixed recipe, evidence, unresolved limits and fallback. Refresh accepted
outputs, audit all published cases and verify runtime, responsive/offline/import/upgrade and version labels;
publish only the data-free shell. A conditional/scenario UI can ship with assumption labels after structural
checks without claiming a calibrated availability model. Every affected checkpoint delivers what changed;
every actual development chunk/session boundary still ends with the required fresh nightly and iCloud exports.
Manual device import remains separate. A no-release conclusion is justified only by an applicable failed gate,
not by mechanically inheriting an irrelevant requirement.
