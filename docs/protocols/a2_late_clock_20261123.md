# A2 contextual late clock — before candidate results

The fresh F4 diagnostic informed this hypothesis: the legacy ≤24s sampler pools all periods and score
positions. This is development, not an untouched hypothesis. No protected-season outcomes are used.
This protocol operationalises A2 rung 60 under D51; it does not authorise engine integration before A1's decision.

## One candidate and a component-removal control

Use the same retained historical segments and fold cutoffs as the engine. Legacy reconstructs its exact
whole-second-clock pools, clipped action times and `end_period`/`unknown` no-action flag. Preserve this control.
The clean bridge uses known event labels and physically valid action times, or known period endings, with
the same whole-second pools. Count exclusions. It changes no period/score conditioning.

The candidate only changes Q4/OT at **0 < clock ≤24s**. Fit empirical pairs of consumed-clock fraction and
no-action flag, conditioned on clock bins **(0,4], (4,8], (8,16], (16,24]** and the existing seven offensive-margin
bins **≤−9, −8…−4, −3…−1, 0, 1…3, 4…8, ≥9**. Period endings consume the remaining clock. Other valid observations
use action-time/start-clock. A cell needs **100 prior opportunities and 30 prior games**; otherwise use the
clean whole-second bridge, and ultimately the legacy pool if that bridge is empty. Missing context uses legacy.
Q1–Q3 and clocks >24s remain legacy. No fitted latent strength, probability clipping or new data source.

Keep raw source files intact; save fitted pools/per-row scores under ignored experiment directories, with
source/recipe hashes, training cutoffs, cell support, unknown/invalid counts and fallback coverage in the report.

## Earlier-fold screen, then separate confirmation

Fit each table from games on/before that fold's training cutoff. Score complete eligible F1–F3 validation
windows, known labels/valid times, Q4/OT ≤24s; do not select only cells that looked bad in F4. The candidate
must work across the entire declared population, including its fallbacks. Report every fold and pooled F1–F3.
The F4 confirmation IDs are frozen separately before candidate predictions: 200 hash-selected original
confirmation games outside both the old S01 200 and the newly inspected Rule 3 200. This is independent of
these A2 late-state diagnostics, not a claim that all F4 basketball outcomes were globally unseen.

Implementation clarification before the first candidate scores: validation uses reconciled regular-season
games with both teams in the NBA registry, as M9 does. Legacy training retains its exact broader `game_ok`
history population. Equal weights mean `0.5 × (normalised time CRPS + no-action Brier)`.

Score the **joint effective time/no-action forecast** with normalised time CRPS plus no-action Brier, equal
weights. This is proper on the allowed support (no-action always consumes the clock). Report both components.
Use exact empirical-distribution scores, not noisy sampled forecasts. The candidate must improve the joint
score versus **both legacy and clean bridge**: upper 95% paired game-bootstrap difference <0 for both
(an intersection requirement). Each component's harm upper bound must be <**0.005** in its [0,1] score units;
this is a newly frozen small-component tolerance, not a widened existing engine margin. Report fold-level
harm, never hide a supported fold beyond this tolerance with pooling. Require 50 games/100 opportunities.
Bootstrap 10k complete games, seed 20261122, fitted training pools held fixed. These are conditional
teacher-forced forecasts; they do not establish simulated-game improvement or causal foul intent.

If this screen fails, retain the legacy clock and record a completed negative result; do not try new bins or
thresholds on the confirmation set. A bridge-only improvement is recorded, not silently promoted as this candidate.
If it passes, freeze the engine hook, same fitted tables, matched development panels and independent-stream
checks before engine results. Player-first v2 core bounds remain mandatory, followed by held-out clock/joint
benefit, game/quarter/calibration diagnostics and the protected final score only after a qualifying recipe.
This narrowly scoped learned clock change uses a prespecified proper decision score as its benefit; it must
not claim improved player scoring merely from node loss or reproduce the old universal seed-noise floor.

## Limits and delivery

Pace/minute covariance gaps are separate: no arbitrary variance widening and no interpretation of forecast-error
variance as an identified form variance. Retain their findings for independently calibrated work. NBA source-zone
exploration is successor work. Serving never samples; any accepted clock change regenerates the saved 10k
slate/season and required PWA/iCloud outputs. A no-promotion outcome still needs evidence, useful delivered UX,
current docs, commit/push and the final accepted-system nightly.
