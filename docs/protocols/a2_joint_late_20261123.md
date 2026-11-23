# A2 shared-factor and late-state evidence — frozen 23 November 2026

This extends the [frozen A2 methods](a2_form_20261122.md). No added form factor is presumed useful.
A1 selected no release; accepted v1.3/targets/pool 0 is the control, not its rejected foul-penalty repair.
No protected-season outcome or new provider. No new model strength is selected from these diagnostics.

## Shared shooting feasibility

Reuse S04 v2 **control** actual-shot make probabilities on F1–F4, with their earlier-fitted parameters,
source/cache alignment and fixed prior-role panels. Keep actors on their recorded offensive five and known
prior roles; count all exclusions. Report all eligible players and stars/starters separately, by fold
and pooled earlier F1–F3. These are teacher-forced associations, not simulated-game forecasts.

Centre make residuals by each fold/cohort's shot-weighted mean. Within each team-game, average products
over distinct shots by **different players** (exclude within-player pairs). Opponent comparison uses
cross-team shot products in the same game. Average team-games/games equally. Compute 10,000 complete-game
bootstrap intervals (seed 20261122), refitting the residual centre in each replicate. Report counts; require
50 games and 100 contributing team-games per cohort. Negative/inconclusive excess is not clamped. Persistent
talent, player form, team/game conditions and misspecification remain confounded. If independently calibrated
shared variation cannot be identified, retain the control and mark this factor unsupported, not fitted.

## Accepted-engine world dependence and late states

**D51 pre-execution revision:** use the fresh **200 F4 games × 1,000 worlds** in
`analysis/experiments/20261123_rule3_confirmation_manifest_v1.json`, outside the old 200-game panel. The
paired rule-confirmation pass captures accepted-control dependence and late states, avoiding a duplicate
control run. Use original seed semantics, fitted nodes, targets and pool 0. Observers consume no randomness
or alter lineups/state. First prove original-control output equality to 1e-12 on the original three-game
wiring panel, then capture the fixed fresh 200. No A2 world/factor measurement preceded this revision.
Store raw MIN/PTS by player-period, team points/possessions, final period, identities and narrow late traces.
Use eight single-thread workers; independent fold diagnostics may use at most two more. Cap BLAS at one.

Use the old residual cohort definition on the fresh games: known pre-game role, actual and simulated mean minutes >=8; report all and
stars/starters. For MIN and PTS, compare role-centred observed forecast-error pair products against the
same players' within-world mean-centred covariance. Teammate pairs exclude self; opponent pairs span teams.
Each eligible team-game/game has equal weight; bootstrap complete games (10k, seed 20261122), re-estimating
observed role centres per replicate. This differs from the earlier PTS/36 ratio diagnostic and is labelled.
State-induced minutes/shot/score dependence is already in the baseline; no factor is selected by matching
these moments alone. Also compare real possession errors with simulated possession variance/opponent covariance.

Observe Q4 and OT segment starts at clock <=120s; retain exact period/clock, offensive margin and before/after
personal-foul/FGA/3PA counts at the action stage, before FT/rebound gaps. Use disjoint clock bins (0,24],
(24,60], (60,120] and offensive-margin bins <=-9, -8..-4, -3..-1, 0, 1..3, 4..8, >=9.
Compare action time, any defensive personal foul (including shooting/and-one) and three share among recorded
FG attempts with held-out actual segments under the same definitions. Minimum 30 distinct actual games and
100 actual opportunities; other cells remain unsupported. State populations differ, so these are descriptive,
not causal or matched-opportunity policy effects. Do not call fouls intentional without a source label.
Compare actual versus simulated OT frequency over all 200 games with game bootstrap uncertainty.

An isolated observational policy must reproduce baseline outputs. Independently reconcile player/team
points, period minutes, clocks, count deltas, source fingerprints and sample metrics before interpreting results.
Persist completed games under hashed input/source identity; resume only fully written, verified game pairs.
Orphan/partial files fail closed for inspection. This is single-operator resume, not silent corruption repair.

## Decisions and stopping rule

Existing talent/player-form screens are inconclusive. New factors/corrections require separately identified
strictly prior calibration and a frozen implementation before engine candidate results. No arbitrary draw
strength, multiplicative widening or held-out-state patching. If diagnostics do not support a separately
calibrated mechanism, record unsupported components and retain v1.3; candidate/combination/seed/final gates
are then not run because no recipe survived, never claimed passed. If one survives, apply all original
player-first primary/non-inferiority/multiplicity/confirmation rules unchanged. A dashboard outcome improvement
and fresh accepted-system nightly/delivery still finish A2; A3/Chunk B remain open.
