# Engine design and decisions

Updated **23 November 2026**. Current behaviour is below; [HANDOFF](HANDOFF_NEXT.md) owns delivery/progress,
[TRAINING_PLAN](TRAINING_PLAN.md) the promotion gates, [FINDINGS](FINDINGS.md) measured evidence. Full original
decision wording/design is preserved in the [frozen engine plan](docs/archive/2026-11-23-before-lean/ENGINE_PLAN.md).
Later decisions override earlier horizons/delivery assumptions; do not reopen settled choices without new evidence.

## Current architecture

For ET origin D, result games before D and rebuild pre-origin profiles, rotations, minutes, pair history and
team ratings. **Possession engine v1.3** plays today's games only (10k worlds/game); **team pathway v1** plays
tomorrow onward (10k seasons), including a fresh season on game-free days. Each season consumes its own stored
near-term outcomes, then updates its own team ratings after every later result. No per-world player carry-over
is needed inside the possession horizon. Views/PWA only read stored outputs.

`models/v1.3.json` defines production; fitted nodes are in `data/models/v1.3/`. `scripts/engine.py:ENGINE`
uses target rotations, 10,000 worlds and pool 0 (one target rotation table/world). Neither richer real-matchup
candidates, responsive substitutions, branch repairs, D47 scaling nor latent form are promoted.

## Decisions so far

This compact index preserves every D-number. Full rationale/dated wording is in the frozen plan; present-day
behaviour follows the latest applicable decision, especially D45–D50.

| ID | Decision |
|---|---|
| D1 | Possessions consist of segments; offensive rebounds continue with 14-second shot clock. |
| D2 | Shared node models across quarters, with period/clock/state inputs; variants must earn their place. |
| D3 | Test player/world efficiency, aggressiveness and shot-selection form plus heat response; not assumed validated. |
| D4 | ESPN/sportsdataverse history from 2022–23; NumPy/pandas/pyarrow/LightGBM stack. |
| D5 | Shrunk NBA-only low-sample profiles, archetype priors and tested talent uncertainty; no pre-NBA translation. |
| D6 | Chain order: who → what → result → credits → rebound. |
| D7 | Target-aware substitutions are the design; replay/target tables are the current fallback. |
| D8 | Accuracy against real outcomes; market closing lines benchmark only. |
| D9 | Five saved world event logs/game, list then playback; D42 defines selection. |
| D10 | Live nightly ≤60 minutes; LightGBM inference remains in-loop, no lookup approximation. |
| D11 | Proposed refit after ≥7 days or forced; automated refit/promotion is not delivered. |
| D12 | Pre-tip refresh deferred; planned branches address lineup uncertainty. |
| D13 | Original seven-day horizon superseded by D24 then D50; long range has team-level outputs. |
| D14 | Coherent season universes consume stored near-term worlds; weighted branch extension must preserve identity. |
| D15 | Future injury/rest paths are planned, not delivered. |
| D16 | Long-range views show team win/score/margin only, labelled. |
| D17 | Each world's ratings update against its own expected points, not today's fixed expectation. |
| D18 | Possession inputs are players/lineups/context, never team-strength ratings; older horizon superseded. |
| D19 | One model across regular season/Cup/play-in/playoffs with game type/round; test sample weighting. |
| D20 | Fifteen learned decisions plus basketball rules; D21 adds location to make sixteen. |
| D21 | Distance-band location node; team turnovers/rebounds remain outcomes in existing stages. |
| D22 | Possession engine is the served floor; changes need measured improvement. |
| D23 | All seasons stamp rebound segments at the miss clock, matching live ESPN; v1.1 promotion. |
| D24 | Former Today/Tomorrow horizon; superseded by D50. |
| D25 | Pathway v1: per-world offence/defence, near-term outcomes first, points-based updates. |
| D26 | Two engines in one daily flow; D50 sets their current boundary. |
| D27 | Nightly pre-origin rebuild supplies player carry-over; team pathways learn from their own score surprises. |
| D28 | Players first, then team sums; team model is a yardstick, never a replacement near-term forecast. |
| D29 | Healthy roles, priority-based 240-minute allocation, return ramp and per-world target variation. |
| D30 | Player/lineup defence via implicit matchups, on-court quality, help and shot-type profiles. |
| D31 | Full 10k plays/sits branches; exact weighted Expected/season blend; D46 limits selection. |
| D32 | NBA Stats API authorised: retained polite adapter, crosswalk, reconcile, matchups/tracking. |
| D33 | No forbidden scraping; own projected starters and ESPN statuses, later learned availability/editor. |
| D34 | v1.3 promoted with D29 minutes and D30 defence. |
| D35 | Defence remains player/lineup-dependent; test switch hunting, never insert team ratings. |
| D36 | 10k worlds, pool 0; phone drops worlds/branches/dependent tools. Laptop amended by D45. |
| D37 | Real-matchup candidates v1.4c/e/f rejected; v1.3 retained; hunting v1.4d not run. |
| D38 | Larger modular chunks, weighted ladders, per-module commit/push, final nightly and successor. |
| D39 | Future versioned daily archives/current-recipe reconstruction with dated inputs AND fitted parameters. |
| D40 | Defer historical forecast backfill; preserve existing archives. |
| D41 | Stopped the prior session after its nightly; unfinished work remained future. |
| D42 | Split remaining work into Chunks A/B; retain five meaningful selected worlds per game. |
| D43 | Reusable source-neutral 2-D event View Centre; actual-game adapter later, no invented tracking. |
| D44 | Season-minute share filters; grouped makes/attempts/conditional percentage distributions. |
| D45 | Laptop PWA primary/full saved worlds; phone stripped; both manually import. |
| D46 | At most one uncertainty/team, within full-roster top three by labelled pre-origin offensive proxy. |
| D47 | Proposed 0/25/50/75/100 availability scale; uncertain inputs stay 25–75%; not accepted. |
| D48 | Proposed capped, classified world-local retries; audit rejection/selection bias; unwired. |
| D49 | Preserve full simulated minute precision; conditions use exact values, display may round. |
| D50 | Today-only possession slate; tomorrow onward uses pathway regulation distributions; preserve originals. |
| D51 | Owner (23 Nov) authorises promotion-framework audit/redesign; v2 separates mechanics, learned changes and stored scenarios. Preserve old evidence; freeze new gates/confirmation before further results, never auto-ship. |

## 2. Possession chain

Sixteen LightGBM nodes: duration, event, who, what, location, shot result, assisted, assister, blocked, blocker,
turnover type, stealer, fouler, free throw, rebound, rebounder. Candidate nodes score players on the five and
softmax within the segment, with training-tail temperature. Team turnovers/rebounds credit no player where appropriate.

Rules govern 24/14-second clocks, period ends, free-throw counts, bonus, five-player lineups and foul-outs.
Regulation periods are 720 seconds, OT 300; quarters/halves exclude OT, full game includes it. Offensive rebounds
and non-shooting defensive fouls can continue a possession. Worlds advance quarter-synchronously in vector batches.

**Known defect:** production initialises the foul-out mask but does not update it. The controlled six-foul
reproduction leaves a disqualified player on court. Research legal-five repairs/penalty continuations exist but
have not passed the production gates; do not describe serving mechanics as solved. D48 cannot mask this through
unmeasured rejection. Missing/corrupt inputs, cutoff/accounting errors and unknown exceptions always fail.

## 3. Time, location and accounting

Every event accrues seconds to the ten players on court. Independently require points = sum of player scoring,
five eligible/distinct players per side, player-seconds = five × elapsed period seconds, valid clock/order and
period/team/box reconciliation. Technical-penalty candidates need their own explicit accounting.

Raw shot feet use basket (25, 0): rim ≤4 ft; paint |x−25| ≤8 and y≤19; corner three |x−25|≥21.8 and y≤14.
The model supplies zones/distance bands, not continuous trajectories. Shot credits can indicate involvement,
not proof of a primary defender or tracking position.

## 4. Minutes and defence

D29 estimates healthy roles from games with the core available, priority from starts/minute rank/usage, and
learned return ramp. Allocate 240 regulation minutes (+25 per OT) by available-player priority with observed
limits/shares; draw targets/world and rescale replay stints. Targets are not a future guarantee. M7 would make
them a soft pull at legal dead balls, allowing state/fouls/blowouts; its candidate remains unpromoted.

D30 aggregates the five defenders through soft assignments using size/role/position, player quality and help.
Real-share matchup history improves assignment visibility but its tested possession variants did not improve
predictions. New defence work must use the S03/S04 evidence, not repeat failed inputs unchanged.

## 5. Form and low samples

Point-in-time rates are shrunk toward NBA archetype priors with stat-specific reliability. Persistent talent,
game-night player form and shared team/game factors must be separately supported and avoid double-counting
variance already created by events/minutes/state. A2's mean-preserving synthetic perturbation is not fitted or
wired. Frozen hypotheses/methods are linked in TRAINING; inconclusive components retain zero added factor.

## 9. Runtime

D10's whole live-nightly budget remains ≤60 minutes. Use the active ten-thread total budget in AGENTS §6;
worker count does not change model settings/seeds. Historical 10k pool-0 games took ~130–150s/game (21 Nov).
New branches, retries and weighted pathways need their own measured representative runtime/memory evidence.

## 12. Branches and season coherence

Select the highest eligible uncertain player per team only within its full-origin-roster top three, including
players already out. Rank by D29 healthy-role minutes × pre-origin shrunk points-plus-0.7-assists per minute,
ties by player ID; disclose cold priors and that this is an offensive proxy, not total/defensive impact.

Stable `lineup-v1:` IDs contain sorted digit team/player plays/sits assignments; record seed, version,
origin, status/source, exact model/input hashes and world count. One/two selections give two/four exhaustive
branches, 10k worlds each. Forced availability precedes recalculated starters/minutes/matchups; unselected
uncertainties still draw normally. Availability differs from positive playing time.

Expected is the full weighted empirical mixture, never a third simulation or rounded 10k subset. Weights are
uncalibrated assumptions; two-player independence is unvalidated. Preserve exact rational/integer masses in
marginal/conditional/joint calculations and season consumption, with every near-term game used once.
Existing common-interval season coupling and browser adapters are research only; see the branch runbook.

Production pathway v1 starts from pre-origin offence/defence plus uncertainty; K=8, start scale=0.4,
update scale=1, memory cap=20 games. Every result updates that world's ratings from points surprise relative
to its own expectation. Tomorrow/future score distributions are regulation; tied scores resolve a winner
separately without OT points. No fitted future injury/rest hazard is present.

Late refresh retains verified pre-tip games and per-game provenance only when model/cutoff stats match; it
rejects replacing a pre-tip forecast if publication crosses tip. All-retained delivery was tested; mixed live
collections remain untested. Staged completion alone is not proof of publication. Legacy timing stays unverified.

## 17. Deferred history and planned playback

D40 defers S13. If reauthorised, preserve immutable original/old-version forecasts, label reconstruction,
require every input and fitted parameter before origin, freeze complete date coverage and validate resume/
atomic activation without version splicing or repeated final-test selection. Full prospective contract is in
the frozen engine plan §17; no runnable engine-history replay is implied.

A3 selects five real worlds: each team's maximum own margin; each team's maximum single-player NBA fantasy
score (PTS + 1.2 REB + 1.5 AST + 3 STL + 3 BLK − TOV); one real representative world by a predeclared
multi-stat distance to Expected. Deterministic ties/missingness/zero variance must be frozen first. Labels may
share worlds; extremes are illustrative. Capture without changing RNG or reproduce the original full batch,
never assume an isolated world replay matches a vector seed. Reconcile event files before playback.

One stored/local-file renderer will provide court, supported overlays, score/clock/box, timeline and seek.
Source/version/spatial precision and actual/simulated kind remain explicit. No fake tracking, future-event
leakage or simulation while viewing; missing geometry still permits honest event-list/box playback.
