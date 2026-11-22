# Training plan — models for the possession engine

**Updated 22 November 2026.** Serving engine **v1.3**, 16 decision models, D29 minutes and D30 defence inputs;
real-matchup candidates v1.4c/e/f were rejected (D37). A1 S01–S06 are complete; S07's selected fallback and
availability/timing safeguards are delivered. Historical
M5 results remain in FINDINGS §3g–§3h; current contracts and promotion/replay gates are in §8 below. Progress and scope
live in [PLAN.md](PLAN.md) and [HANDOFF_NEXT.md](HANDOFF_NEXT.md).

## 1. What we are training (ENGINE_PLAN D20)

One LightGBM model per decision, trained on every quarter and game type with period, clock, game state and
game type as inputs. Labels come from the M2 segments (history 2022-23 → 2025-26, reconciled games).

| Stage | Node | Choice | Rows | Type |
|---|---|---|---|---|
| Clock | duration | time to the event, 13 two-second bins | 1.20M segments | multiclass |
| Clock | event | offensive action · defensive foul · violation/jump ball · team turnover (D21) | 1.23M | multiclass |
| Action | who | which of the five ends it (incl. who is fouled in the penalty) | 1.15M × 5 | candidate |
| Action | what | rim · paint · mid · corner 3 · above-break 3 · turnover · fouled on a 2 · on a 3 | 1.14M | multiclass |
| Action | location (D21) | distance band within the zone: 21 bands, 3–5 per zone (`nodes.LOCATION_EDGES`) | 0.92M | multiclass, masked to the zone |
| Action | shot result | miss · make · and-one | 0.92M | multiclass |
| Credit | assisted / assister | assisted? then which of four | 0.43M / 0.27M × 4 | binary / candidate |
| Credit | blocked / blocker | blocked? then which of five | 0.49M / 50k × 5 | binary / candidate |
| Credit | turnover type / stealer | steal · offensive foul · other dead ball; then which of five | 0.14M / 80k × 5 | multiclass / candidate |
| Credit | fouler | which defender fouled | 0.18M × 5 | candidate |
| After | free throw | make or miss, per attempt (attempt order, trip size) | 0.23M | binary |
| After | rebound / rebounder | offence/defence × player/team; then which of five | 0.52M / 0.45M × 5 | multiclass / candidate |

Rules, not models: free-throw counts (2/3 by shot value, 1 for an and-one), penalty and bonus, shot clock,
period ends, foul-outs. Substitution models (out/in at dead balls) are M7.

Choices among players use one row per candidate. Each candidate is scored by the model and the scores are
normalised over the candidates on the floor (softmax), with a per-node temperature fitted on the latest slice
of the training window, so probabilities exist only for players actually on court.

## 2. Inputs

### 2.1 Player profile (built point-in-time: only games before the date)

| Group | Features |
|---|---|
| Role | minutes per game, starts share, typical stint length, quarter minute shares, usage rate, archetype |
| Usage by type | share of on-court segments he ends: shots, turnovers, fouls drawn; by quarter (the Doncic effect) |
| Shot profile | zone shares (rim, paint, mid, corner 3, above-break 3); assisted share by zone (self-creation); **built (D30, v1.3)**: shot-type shares from the play text (self-created, drive, cut, putback, catch); a per-shot type node is the next test (FINDINGS §3q) |
| Accuracy | FG% by zone, FT%, and-one rate, blocked rate |
| Playmaking | assist rate on teammates' made shots while on court |
| Ball security | turnover rate per use; live/dead split |
| Fouls | fouls drawn (shooting / non-shooting), personal fouls committed per minute |
| Rebounding | offensive and defensive rebound share of available rebounds while on court |
| Defence | steal rate, block rate on opponent rim attempts, opponents' turnover and rim rates while he is on court; **built (D30, v1.3)**: on-court FG% allowed by zone with ×0.2 shrinkage (defender side only), weighted for each actor by a soft matchup assignment over the five on court (size, role, position; learned from foul and block credits — weak, FINDINGS §3q), plus help at the rim; real NBA matchups ingested (D32), but their three tested engine variants did not improve the full engine (D37); A1 S03/S04 diagnoses and tests new mechanisms |
| Body | height, weight, position, age, experience (from rosters) |
| Reliability | sample sizes behind each rate (possessions, attempts), so the model knows how far to trust them |

### 2.2 In the moment (per segment)

- **Relative role**: his usage rank and share among the five on court; teammates' combined usage, creation
  and spacing; who else is a primary creator.
- **Opponents on the floor**: rim protection, perimeter defence, foul tendencies, size — aggregated over the five.
- **Fatigue and fouls**: seconds into his current stint, minutes so far, rest since last stint, personal fouls.
- **Game state**: period, seconds left in the period and game, time since the segment started (shot clock
  proxy), start type (transition after a steal, set play after a made basket…), score margin, team fouls and
  bonus, garbage-time indicator.
- **Heat check** (tested, D3): his makes and attempts so far this game, recent streak.
- **Team and coach context**: team pace and shot-profile tendencies, defensive-scheme proxies, rotation depth.
- **Schedule**: rest days and back-to-backs for both teams, home or away.
- **Era**: season and days into the season, for league drift (three-point share, substitution volume —
  27 → 34 per team-game since 2022-23).

## 3. Time decay — two different things

**Feature decay: how a player's profile weighs his own recent games.** Each rate is an exponentially decayed
average of his games, then shrunk toward his archetype prior by how much data he has. Half-lives differ by
stat because stats settle at different speeds:

| Stat family | Starting half-life (tuned on validation) | Prior strength |
|---|---|---|
| Minutes, starts, role | ~5 games — roles change fast | light |
| Usage, shot profile, assist and rebound rates | ~15 games | moderate |
| Shooting accuracy by zone | ~40 games | strong (three-point accuracy settles slowly) |
| Free throws | ~80 attempts | moderate; informs the three-point prior |
| Quarter usage multipliers | whole season | strong |

Last season carries over at reduced weight (more for stable skills such as shooting, less for role). Rookies
start from their archetype, as agreed (D5).

**Sample-weight decay: how much older possessions count when the models learn.** The league changes — more
threes, more substitutions, rule tweaks — so a 2022-23 possession should teach the model less than one from
last month. Proposed: weight = 0.5^(age / one season), with this season counted fully. Validation chooses
among half-lives of half a season, one season, two seasons and no decay. **Measured (FINDINGS §3h): no decay wins** —
every half-life is worse on nearly every node (one season: +1.7 nats per game over the chain; two: +0.7). League drift
is carried by the season input; older possessions still teach the models.

## 4. Guarding against leakage

- Every feature for a game on date D is computed from games before D; profiles are a dated table
  (player × date) joined to segments.
- Archetypes are refit from data available at each refit date, never from future seasons.
- Lineups and availability in training are the real ones (we model decisions given who is on court);
  forecasting who will be available is the separate availability model (M11).
- Games flagged `game_ok = false` in M2 (≈2%) are excluded.

## 5. Splits, tuning and acceptance

**Rolling-origin validation** — every choice (features, half-lives, sample-weight decay, hyperparameters,
pooled v per-quarter, playoffs in or out) is scored on several time folds, each trained only on earlier data:

| Fold | Train on | Validate on | Why |
|---|---|---|---|
| F1 | 2022-23 → Dec 2023 | Jan–Apr 2024 | mid-season |
| F2 | → Dec 2024 | Jan–Apr 2025 | mid-season |
| F3 | → Sep 2025 | Oct–Dec 2025 | early season, like now |
| F4 | → Dec 2025 | Jan–Apr 2026 | mid-season, most recent |

A choice wins only if it improves the average held-out log loss across folds without hurting any fold
badly. **Final test** — 2026-27 to date, scored once per model version and never used for choices; it
grows as the season goes on. Features need history, so training rows start in December 2022 (burn-in).
- Hyperparameters: modest trees (31–63 leaves, learning rate ~0.05, early stopping on the latest 10% of the training window).
- **Per node**: held-out log loss against two baselines — league rates and shrunk player rates (M4);
  reliability curves overall, by period and by game-state bucket.
- **Promotion** (D11): a weekly refit replaces the current models only if it matches or beats them on
  recent held-out games; the previous set stays as a fallback.
- The engine-level backtest (M9) then judges the whole chain: minutes, player stats, quarters, game results.

## 6. Data volumes and compute

About 1.2M segments (≈850k shots), 5M candidate rows for "who", ~0.2M substitution windows × 10–15 player rows.
LightGBM fits each node in seconds to a few minutes on the laptop; a full weekly refit ≈ 5–15 minutes.

## 7. Experiment protocol (owner: "as accurate as possible")

Decided by the folds above, not by default:
- **Decay**: feature half-lives per stat family, season carry-over, sample-weight half-life (½, 1, 2 seasons, none).
- **Data scope** (D19): every game type in one model per decision — regular season, NBA Cup, play-in, playoffs —
  with game type and playoff round as inputs; game-type weights tested. Garbage time kept, with and without
  down-weighting.
- **Structure**: pooled v per-quarter models per node (D2); candidate-row temperature; heat-check inputs (D3).
- **Inputs**: every feature group must earn its place by ablation (held-out log loss with v without). Candidate
  groups beyond §2: coach identity and tenure, referee crew foul tendencies (officials are in our game
  summaries; history coverage to check), travel distance and time zones, altitude (Denver, Utah), lineup
  familiarity (minutes the five have shared), on/off context.
- **Model settings**: leaves, learning rate, minimum leaf size, regularisation — random search with early stopping.

Every run is logged (configuration, data range, per-fold metrics) under `analysis/experiments/`; measured wins
and **negative results** go to FINDINGS so failed ideas are not repeated without a new reason.

**How a change is judged (tooling, 19 Nov).** `scripts/nodes.py` caches the sixteen datasets (folder named by a hash
of code and inputs), so runs that change only training load in seconds and run in parallel. `scripts/train.py` stores
every held-out decision's log loss; `scripts/compare.py A B --noise S0 S1` compares two runs on identical rows, with
standard errors clustered by game and a **training-noise floor** from two runs that differ only in seed (a seed change
alone moves small nodes by up to 0.15% with |z| up to 3.4). A change is kept for a node when its mean change over the
four folds beats −noise with pooled z ≤ −2 and no fold is worse by more than 2 × noise with z > 2; global changes
(feature decay) are also read on the **chain** row — the change in log-likelihood of whole games, in nats per game.
Settings that differ by node are kept per node in the version file (`models/<version>.json`).

**Train/serve parity (M5b, 19 Nov).** Inputs must be built the same way for training rows and for the games the engine
serves. ESPN's 2026-27 feed stamps every rebound at the miss's clock (FINDINGS §3k), so segments use that convention
for every season (`possessions.py --rebound-clock miss`). A data change like this cannot be judged on folds built the
old way — the old models are right there by construction — so it is judged by a **paired cross-data test**:
`train.py … --train-segments default --train-features default` trains each fold on the old data and scores it on the new
data's held-out rows, paired with a run trained on the new data (`compare.py`). Data variants live under
`data/derived/variants/<name>/`; a version file names its data (`"segments"`, `"features"`).

**A1 integrity candidate (22 Nov).** Historical assignment fits are body-free, dated before each row and frozen at
the fold cutoff; position groups use only earlier observed games, and missing lineup-relative profiles are filled
within that lineup. Sampled F1–F4 parity and an isolated F4 wiring run do not establish original publication timing
or promotion. The `what` diagnostic profile baseline now fills from the training window, never the held-out batch;
fold-model cache keys include the training-code hash. The candidate schedule rejects `NaT`, malformed dates and
incomplete/non-finite fitted parameters; dependent F1–F4 features/parity and F4 nodes/wiring were rebuilt and
accounted separately (HANDOFF). This is not an accuracy or promotion result.

**Game-level gate (20 Nov).** Node log loss is necessary, not sufficient: small per-possession effects add up over a game
(on-court defence was neutral at node level, §3l, while the backtest shows defence expressed at ~25% of its real effect,
FINDINGS §3o). Inputs aimed at team strength are judged by the engine backtest as well (`backtest.py`, same seed and games
as the control run): `strength_loading`, margin slope, margin/total CRPS and win log loss against the current engine and
the team-rating model.

**Sample-size buckets.** `games_eff` (role family, 5-game half-life) caps at ~7.7, so per-sample-size verdicts use the
deciding player's decayed offensive segments (`scripts/buckets.py`: < 250, 250–750, 750+).

NBA Stats API access is authorised and in use (D32). Retained tracking-defence inputs still need date-safe parsing
and ablation (A1 S02/S04); untested richer inputs are candidates, not assumed improvements. A new provider still
requires owner sign-off. Learned availability from short report history must respect §8 and the untouched final test.

## 8. A1 acceptance and reproducibility contract (22 Nov 2026)

A1's scopes are PLAN §6a, progress is HANDOFF § Progress ladders. **Nothing below is a new measured gain.**
Keep v1.3 and pathway v1 until evidence supports a change. The preceding 22 Nov planning pass ran no training/final scoring.

### 8.1 Three populations, never interchangeable

1. **Node / M6a diagnosis:** real lineups, game state and clock may be supplied to isolate per-possession errors.
   Teacher-forced aggregation is not a pre-game forecast, particularly for margins and conditional score effects.
2. **Conditional engine:** the existing backtest knows actual participants. It normally predicts starters; the
   separate `--known-starters` flag makes those oracle too. This isolates performance/minutes and provides comparable
   historical controls. Report its availability assumption beside every result, not only in code.
3. **Pre-game forecast:** reconstruct eligible rosters, reports and play/start probabilities from information before
   the origin. Report coverage, exclusions and low-sample/missing-report handling. Do not use the final box to decide
   who was available. Recent injury-report history may be too short for a validated model; retaining fixed status
   probabilities with an explicit coverage gap is better than leaking future information.

All tiers and evaluation subgroup membership used for selection come from pre-game variables. Final margin/fouls may
be used to analyse realised state-response, but never as pre-game training inputs. Unknown truth stays unknown.

### 8.2 Freeze before experiments

S01 writes a committed manifest under `analysis/experiments/` with the control run/model/data/code hashes, all game IDs,
seeds/world counts, fold dates, preprocessing, role tiers and metrics; per-game arrays stay ignored under
`data/derived/experiments/`. Preserve the serving-setting pool-0 control and same-game team benchmark (FINDINGS §6).
Record exclusions, missingness, primary hypotheses, candidate families and the exact confirmation populations.

For each family predeclare a primary metric and practical non-inferiority margins for the other core metrics,
in their actual units. Derive margins from meaningful predictive loss and control repeatability, write their values
before seeing candidates, and never widen them to pass a result. Pin minimum subgroup counts and how unsupported
groups are treated. Audit the existing seed scheme: sharing a game-selection seed is not automatically common random
numbers when a model-version label changes simulation seeds. Record effective simulation seeds and compare paired
game means; use common streams only where structurally valid and a second-seed check for Monte Carlo sensitivity.

Use game-clustered paired differences/intervals (not independent player rows). A primary improvement should beat the
training/simulation noise floor with a 95% paired interval favouring the candidate (or the existing equivalent z rule).
For required non-inferiority outcomes, the upper uncertainty bound must sit inside the declared harm margin;
non-significance alone does not establish equivalence. Name comparison families to limit selection by repeated tries;
all exploratory attempts stay in the log. Existing §7 node gates continue to apply, including the seed-noise floor.

#### S01 preregistration — 22 Nov, before A1 candidates

The fixed development screen is the 200 retained F4 games in `20261120T162930Z_v1.3_pool_per_world_F4`, 1,000 worlds,
known actual participants and projected starters, pool 0. The independent pre-game-availability track is separate.
For player selection tiers, **star** means pre-game usage ≥0.25; otherwise **starter** means pre-game start share
≥0.5 and **bench** is below 0.5. Missing usage or start share is **unknown**, never silently bench. The older logged
scorecard uses actual game starters and remains a historical reference, not a selection gate. The screen has 284 star,
1,578 starter, 2,472 bench and 12 unknown player-games. A reportable tier/subgroup needs **at least 100 player-games
in 30 distinct games**; rarer cases are inconclusive, and required sparse tiers block a promotion claim rather than
being dropped. Game/season populations and exclusions must match exactly.

Player non-inferiority margins below are increases in CRPS in the statistic's own units. They are **2% of the
pre-game-tier pool-0 control**, rounded to four decimals; 3PM is fixed in advance at **0.0200 made threes** because the
old saved player output omitted 3PM. Its matched control must be regenerated before any 3PM decision.

| Pre-game tier | MIN CRPS (minutes) | PTS CRPS (points) | REB CRPS (rebounds) | AST CRPS (assists) | 3PM CRPS (makes) |
|---|---:|---:|---:|---:|---:|
| Star | 0.0578 | 0.0898 | 0.0304 | 0.0261 | 0.0200 |
| Starter | 0.0605 | 0.0711 | 0.0290 | 0.0207 | 0.0200 |
| Bench | 0.0796 | 0.0553 | 0.0237 | 0.0155 | 0.0200 |

The 2% bound is a small, meaningful loss relative to prediction error; a paired pool-400 versus pool-0 check on all
4,346 matched player-games had 95% game-clustered CRPS difference intervals narrower than these margins for these
four retained statistics. This is **not** a pure seed-noise experiment; S01 still measures an independent simulation
seed. If noise or the confidence interval is too large to demonstrate non-inferiority, increase worlds/games or report
inconclusive; **do not widen margins**.

Additional maximum harms: margin and total CRPS **0.20 points**, each quarter CRPS **0.10 points**, win log loss
**0.010 nats/game**, Brier **0.005**, and 10–90% coverage's absolute deviation from 0.80 **0.03**. For absolute signed
bias, the allowable increase in its magnitude is **0.30 minutes**, **0.30 points**, **0.10 rebounds**, **0.10 assists**
or **0.05 made threes** per player-game; team total/margin biases may grow by **1.0/0.5 points**. Season final-win CRPS
may worsen by at most **0.10 wins** on each supported start date; absolute dispersion, coverage and persistence error
may grow by at most **0.10, 0.05 and 0.05**, respectively. These are maximum harms, not desired target values.

Families and primary outcomes, frozen before candidate results: S04 defence/shot quality → pooled PTS CRPS;
S05/S06 membership/minutes/substitutions → pooled MIN CRPS; S07 availability → pre-game play Brier on a genuinely
dated cohort; S09 form/end-game → pooled PTS CRPS plus the prespecified joint-dependence checks; S10 pathway → pooled
final-win CRPS across the 16 matched season/start origins with each date separately reported. S08 is an accounting and
coherence change, not by itself an accuracy win. Pooled player CRPS weights eligible player-games equally; all three
supported tiers and the other core stats must pass their non-inferiority gates. Claims across multiple tested primary
families use Holm's 0.05 correction; exploratory within-family variants and all rejected runs are recorded.

Use **10,000 paired game-cluster bootstrap replicates**, NumPy seed **20261122**, sampling complete game IDs with
replacement and retaining all player rows from each sampled game; report the 2.5/97.5 percentiles. Required
non-inferiority passes only if the upper 97.5% bound of candidate-minus-control harm is strictly inside its frozen
margin. A primary win requires its corrected 95% upper bound below zero **and** its observed improvement larger than
the independently measured simulation-noise floor. For coverage/bias use the paired change in the absolute deviation,
not the signed change. Report sample sizes, point differences and intervals. Different model names alter the current
simulation seed; common streams may be used only when their semantics are explicitly fixed and valid, never assumed.
For each primary CRPS, define the 1,000-world simulation-noise floor conservatively as the larger absolute endpoint
of the 95% paired game-cluster bootstrap interval comparing the same control and inputs under its original stream and
an independent stream on the entire pinned 200-game panel. This rule is frozen before that comparison; it is not a
licence to discard an inconclusive interval or to lower the registered harm margins.
Win Brier and log loss use the empirical simulated probability without modification. A zero probability assigned to
the observed winner has genuinely infinite log loss: the report marks it explicitly instead of inventing a finite
value or an interval. This differs from the legacy backtest summary's numerical boundary safeguard.
The second-seed result, exact confirmation IDs, 10k subset and reproducibility manifest are recorded in
`analysis/experiments/20261122_a1_manifest.json`, pinned to source checkpoint `c6d5db4`; the later seed-list type
annotation preserves the compiled function and all 3,036 recorded seeds.

#### Chunk A A2 residual-dependence screen — 22 Nov, before measurement

Use the immutable S01 F4 control's 200 games and 1,000-world player summaries, joined one-to-one to the independently
fingerprinted, strictly pre-game S05 F4 role table. Report missing joins and unknown roles; never fill them from
post-game information. This is a retrospective, actual-participant diagnostic, not an availability forecast. The
F4 games end before the protected 2026–27 final test. Freeze this screen before examining its results.

The supported sample has known star/starter/bench role, at least eight actual minutes and at least eight simulated
mean minutes. Examine both all supported players and the pre-game star/starter subset. For each player compute
minutes error `actual - simulated mean` and scoring-rate error
`36 * (actual points / actual minutes - simulated mean points / simulated mean minutes)`. Subtract each role's
sample mean separately for each error; re-estimate those role means in each bootstrap replicate. For each eligible
team-game calculate the mean product across distinct ordered teammate pairs, then average team-games equally.
Calculate the corresponding opponent-pair mean product, averaging games equally, as a comparison. Report both
covariances, their difference, complete-game counts, player/team-game/pair counts and 10,000 complete-game bootstrap
95% intervals (seed 20261122). Do not report a cohort without at least 50 distinct games and 100 contributing
team-games. These are exploratory observed residual associations, not causal evidence, simulated-world covariance,
or a model-selection/promotion result; actual-minute selection and ratio-of-means are explicit limitations.

#### Chunk A A2 talent/form hypotheses — 22 Nov, before fitting

The F4 screen above was inspected during hypothesis construction and is **not an untouched confirmation set**.
Test the following separately on F1–F4, with calibration based only on games and fitted parameters strictly before
the assessed origin: (1) player talent uncertainty narrows with earlier effective shot exposure; (2) a distinct
within-game player shooting-form factor persists across that player's shots; (3) a shared team/game component
changes joint pace or shooting outcomes. These are falsifiable hypotheses, not presumed positive effects: the
observed F4 scoring-rate teammate residual covariance was negative. If a credible variance component or a
cutoff-safe estimate is unavailable, report it as unsupported and retain the control; never clamp a negative
estimated excess to zero and call it evidence.

Use chronological out-of-sample or cross-fitted pre-origin event predictions to estimate components; any training
row's prediction must come from parameters fitted before that row. For F1, use only earlier training-window games
and nested earlier fits, never a later development fold. F2–F4 may use earlier folds only where every event and
its scoring parameters precede that fold's origin. Record all component sample sizes, effective exposures,
estimates and uncertainty, including absent roles and sparse players; no post-origin identity or availability
is used as a pre-game predictor. Actual-participant backtests remain explicitly conditional.

No-double-count controls: estimate baseline **simulated-world** player and teammate/opponent dependence on the
same games, in addition to observed residual dependence, because event draws, clock/score responses and minutes
already create variation. For each latent factor compare control, that factor alone and (only if individually
supported) combinations; identify whether uncertainty in persistent talent, nightly form and shared conditions
is separately identifiable rather than summing overlapping residual variances. Factor draws must be independently
namespaced by game/world/player or game/world/team, deterministic for a fixed seed and input, held fixed over the
game, and never shared accidentally across players, teams, games or factors. The exact zero-factor path must
reproduce the old engine without consuming additional draws. Probability tilts must preserve the baseline marginal
mean over the factor distribution and leave valid outcome probabilities; verify numerically across boundary and
interior cases rather than clipping or silently renormalising errors.

Before any candidate engine result, freeze its calibration/implementation, fold-specific fitting cutoffs, paired
game IDs, simulation seeds, joint-dependence estimands and any component-specific decisions. Compare player PTS
CRPS first, then all registered tier/player/team non-inferiority bounds, seed-noise and coverage, plus observed and
simulated teammate/opponent covariance with complete-game bootstrap uncertainty. No factor is promoted on
node-level fit or matching covariance alone. Multiple tested candidates remain in the experiment log and use the
existing familywise and once-per-version final-test rules; an unresolved interaction or excessive uncertainty is
inconclusive, not a pass. A1 lineup-branch decisions are required before integrating a survivor.

**Earlier-fold event feasibility screen, frozen before residual measurement:** reuse the retained S04 v2 control
shot-node probabilities, not its rim candidate, for the complete validation dates of F1, F2 and F3. The models were
fit before their respective validation windows; F4 and the protected final test are excluded. Join each prediction
to its actual shooter only after reconciling source/cache rows by game, date, period, zone, result, score margin,
clock, shot time and coordinates, with their recorded fingerprints; exclude and count any shooter outside the
recorded offensive five or lacking a valid prior role. This is teacher-forced observed-shot research, not a
forecast or a comparison against simulated worlds.

For each known-role player-game with at least two eligible shots, define residuals `actual_make − control_make`
and calculate the mean product over distinct ordered shots of that player in that game. Within each game average
eligible player-games equally; then average games equally. Report each fold and pooled F1–F3, all players and
each prior star/starter/bench role, with player-game/shot/pair/game counts and 10,000 complete-game bootstrap
95% intervals (seed 20261122). Require at least 50 games and 100 player-games per reported cohort. Count all
missing/invalid exclusions; no negative estimate is clamped. The within-game residual excess combines any
persistent talent, form, shared game effects and model misspecification, so it cannot identify their separate
variance or justify a draw by itself. A valid component still needs a separately frozen identification and
simulated-world comparison, with the original player-first gates.

**Coverage discovered after the first run:** the fingerprinted S05 prior-role tables cover only fixed panels of
200 F1, 200 F2 and 195 F3 games, not every validation game. The v2 report explicitly distinguishes outside-panel
shots from in-panel missing/wrong-team/unknown roles; it reproduces all first-run estimates and intervals exactly.
This is a fixed-panel screen, not an all-validation-games estimate.

#### S03 signal-diagnosis specification — 22 Nov, before the diagnosis

The fixed unit is a team-game side: the **200 unique S01 F4 game IDs** in the manifest, exactly matching the retained
pool-0 control, form **400 sides**. For each side retain its game ID, team/opponent, simulated and real possession
counts, points, FGA, FGM, 3PA, 3PM, FTA, player turnovers and offensive rebounds. Both possession counts, FGA and
3PA are positive for every side. Simulated points are engine scoreboard means; real points are official scores;
real component totals are player-box sums, so any administrative/team discrepancy remains a labelled limitation.

Use the existing pre-date team-rating yardstick: for each game, `season_backtest.state_before` uses only earlier
same-season boxes, and `pathway.start_ratings` supplies own offence and opponent defence, each minus the league
offensive rating. On the *same* 400 sides regress each outcome on an intercept, own offence and opponent defence.
Outcomes are points/100 possessions, FG%, 3P%, 3PA/FGA and FGA, FTA, turnovers and offensive rebounds per 100
possessions; sim and real each use their own matching denominators. Report unrounded coefficients and levels plus
10,000 paired complete-game bootstrap intervals (seed 20261122), including sim-minus-real coefficients. Do not treat
ratios with near-zero observed coefficients as identified or interpret these observational loadings causally.

The like-for-like M6a diagnostic uses the same frozen game IDs and the **v1.2d** F4 fitted inputs used by the
accepted v1.3 control, not the retained v1.1 M6a run. Its actual lineups, clock, score and prior in-game state are
teacher forced, its selected participants are retrospective and it is **not a pre-game forecast**. Different
accounting populations (heaves, malformed lineups or non-player scoring) must be counted before comparison.
For rejected v1.4c/e/f only, compare the same 200 IDs against their original shared-rotation-pool v1.3 control
`20261120T133953Z_v1.3_components_F4`; do not present that comparison as a pool-0 paired run. FTM is not retained
in these game outputs: any score residual after field goals is a residual, not an observed free-throw-make count.

For S03's descriptive player-profile spread, split the fixed panel at **1 March 2026**, before inspecting outcomes
(112 earlier / 88 later games). Compare shooter zone-specific pre-game FG profiles with real shots, and defensive
on-court zone profiles with opponent shots taken while each defender was on the floor; one shot belongs to five
defensive exposures and does **not** identify the on-ball defender's causal effect. For each player/zone, retain
only those with at least **15** opportunities and **3** distinct games in *each* half; report the number retained,
the profile variance and covariance of the two halves' observed rates, weighted by the lesser half's opportunity
count. Missing or duplicate defensive lineups and unmatched/incorrect team assignments are counted and excluded. Do not clamp
negative covariance or present it as a causal individual-defence estimate. The effective-exposure bins are
`<250`, `250–750`, `>750` and unknown (shooter `shots_eff`, defender `d_segs_eff`); report all sample sizes and
missingness. These are exploratory diagnostics, not tuned thresholds or promotion gates.

For the same panel's frozen **shot-result** node, align cached rows to retained shot events using game, date, period,
zone, result, score state, clock, coordinates and actor-profile values; explicitly count actors missing from their
recorded offensive five. Apply the saved F4 model, including distance bands fitted on its training window, to the
aligned rows. Within each zone, form quartiles from the *input values alone* for the shooter zone profile, the
assignment-weighted opponent profile (`mu_fg_shot`) and shooter usage. Report prediction, observed make rate,
binary log loss, Brier score, game and exposure counts, plus the same metrics per shooter and for effective-exposure
bins. Defensive effective exposure is the mean of the five recorded defenders' pre-game `d_segs_eff`, not an
on-ball assignment; invalid fives and unknown means remain missing. Quartiles are descriptive, not thresholds fitted
to outcomes, and the node is conditional on the actual shot/zone rather than a pre-game or full-engine forecast.
After seeing the initial bin means, add **10,000 paired game-cluster bootstrap** intervals for every input's Q4−Q1
observed and predicted difference and their difference; these intervals are descriptive, not a newly preregistered
selection gate, and do not adjust for confounding or multiple comparisons.

For S05, keep these quantities distinct before evaluating minutes: **roster membership** means the strictly
prior-box inferred team membership in §8.2, not a proven historical roster; **physical availability** is not
reconstructible from an unlisted/unknown or unspecified DNP; **rotation membership** means whether a known-available
player enters, with positive-minute appearances and explicit DNP-coach labels as an incomplete diagnostic cohort;
**start** is a separate outcome. A DNP for injury, rest or an unspecified reason is not automatically a coach's
rotation rejection. **Healthy role** is the cutoff-safe D29 latent minutes level learned from appearances with its
absence correction and ramp handling; it is not the allocated target or unconditional expectation. **Conditional
minutes** score the known-participant S01 panel and must not be presented as an availability forecast. **Unconditional
minutes** need a pre-game candidate universe and physical-availability plus rotation probabilities, including
observed zeros; unknown/unlisted players stay unknown. Report total vs regulation minutes, cutoff, origin, counts,
and S01 pre-game role tiers explicitly. Returning-player, low-history, recent-team-change and absent-core analyses
must use pre-origin definitions where inputs are used for selection; realised absences can be shown only as labelled
post-game diagnostics. Stale inferred rosters, unseen arrivals, and source records without publication timestamps
remain limitations rather than silently excluded proof of forecast quality.

S05's first isolated candidate removes non-NBA-team games from the D29 minutes history, while retaining its
healthy-role, allocation, ramp, spread, node and rotation settings. Both sides of every retained game must be
canonical NBA teams; same-date duplicate player/team games fail rather than leaking. Ramp and residual-spread fits
use the same pre-validation cutoff as the original D29 build. Compare the candidate and unchanged v1.3 control on
S01's exact F4 participants, games and streams; the primary engine outcome remains pooled MIN CRPS and all S01
non-inferiority/confirmation gates remain fixed. The preliminary target-only result is exploratory and not a
promotion. The candidate module is opt-in through the isolated backtest CLI and is not connected to production.
An independent strict-runtime candidate repairs D29's underfilled short-roster draws and >48-minute targets by
redistributing only within legal regulation headroom; fewer than five available players fail explicitly. Keep the
NBA-only-history and strict-runtime switches separately identifiable so their effects and interaction can be tested.
The history candidate currently learns past states with the original D29 allocator; do not describe that as a
strict-allocation training rebuild.
`scripts/a1_minutes_gate.py` applies the frozen pooled-MIN seed-noise screen and registered player/game
non-inferiority bounds to a paired report, reusing the manifest's maximum-absolute-endpoint calculation. Its first
and v2 reports used the interval's half-width instead and are preserved only as invalid preliminary evidence;
v3 corrects this without changing the NBA-only rejection. Its uncorrected 95% result is an early screen only:
Holm-adjusted family confirmation, wider folds, mechanics and the other promotion gates still apply.
`scripts/a1_pooled_audit.py` independently reconstructs pooled player intervals by direct complete-game resampling
and checks the 10 pooled bias/coverage bounds; it does not turn the preliminary screen into confirmation.
Before using the strict candidate's first historical screen for selection, a deterministic defect was found:
redistribution could activate a zero target even when already-positive targets could absorb the deficit, changing
the `draw > 0` target-play diagnostic. The invariant was corrected without changing the registered populations,
normal streams, availability fallback, scoring or other candidates; uncorrected reports and hashes remain retained.
The conditional and both historical roster screens were rerun under new names and independently reconciled against
the original control/NBA-only values. Report strict/combined results only from the corrected version. This is a
candidate implementation repair, not a revision of the promotion gates or evidence of actual availability.
Before full-engine runs, compare conditional regulation-minute target distributions on S01's predeclared **200**
F1, **200** F2, **200** F3 and fixed **200** F4 games. Use the same actual-participant team sets for every variant,
1,000 draws per team with the same explicit per-game/team normal stream, each fold's own earlier ramp/spread fit,
pre-game role tiers from the isolated causal-base features, and paired 10,000-game-cluster bootstrap intervals.
Report the original, NBA-only-history, strict-runtime and combined variants separately; these allocator-only screens
do not establish engine CRPS or availability accuracy. An unconditional evaluation also needs zero-minute players
from a pre-origin membership/availability universe; missing reports and unlisted players stay unknown.

For an honest partial sensitivity while historical physical-availability reports remain unavailable, construct the
same prior-box candidate universe separately on the fixed 200 games in each fold. Before scoring the first such
run, hold all inferred candidates physically active, carry unknown/unlisted candidates into each team allocation
without assigning them zero outcomes, and score recorded DNP zeroes and available positive regulation minutes.
Contradictory DNP/on-court records and positive boxes lacking on-court regulation minutes remain missing for the
minute score. Use strictly pre-origin reconstructed D29 states, each fold's earlier ramp/spread fit, 1,000 matched
draws per team and 10,000 paired game-cluster bootstrap replicates. Compare the same four original, NBA-only,
strict-runtime and combined variants as the conditional screen. Use the latest strictly earlier player profile
for role tiers, and report unlisted, unseen-arrival and source-conflict counts. A zero-target-draw frequency is an
allocator diagnostic, not simulated rotation membership; this deliberately optimistic all-active fallback and its
known-label subset are not a complete unconditional forecast or a replacement for date-stamped injury reports.
The run was started 22 Nov with the outcomes still uninspected, as separate per-fold immutable reports.

For the further no-report availability fallback, use the existing production rule rather than assume all candidates
are certainly active: absent a report, the status fallback starts at 1.0; if none of the last five prior team games
has a listed play and the window contains at least three, use 0.8 for a recent 20+ minute role and 0.5 otherwise.
Build the role from strictly earlier same-season positive-minute appearances with the existing four-game EWMA.
Record unknown prior box entries rather than presenting them as confirmed absences. Draw physically-available
patterns from those probabilities with a matched deterministic stream, re-solve targets per pattern, and condition
on at least five eligible players by resampling; record every resampled world. This is a no-report fallback
counterfactual with incomplete inferred rosters and known-label scoring, not a reconstruction of actual pre-tip
injury reports. Hold it fixed across the four allocator variants and all four folds; no later tuning to its results.

For S06's initial **descriptive** state-response audit, use only independently reconciled full-timeout windows in the
fixed F4 panel, with actual participants and S01's pre-game role tiers. Before inspecting rates, divide team-relative
margin into behind by at least 15, close within five, ahead by at least 15, and the remaining intermediate states;
group periods 1–4 and overtime separately; define foul trouble as at least two/three/four/five fouls in periods
1/2/3/4-or-later; and divide elapsed stint or rest into under four, four-to-under-eight, and at least eight minutes.
For each tier and state, separately report outgoing rates among on-court players and incoming rates among off-court
participants. Count distinct player-games and games, use the existing 100-player-game/30-game support floor, and
compute 10,000 complete-game bootstrap intervals with S01's seed for supported cells. These observed-window rates
are not causal estimates, unbiased substitution hazards, pre-game availability forecasts, or promotion gates:
same-clock exclusions depend on observed substitutions, and the participant universe is retrospective. Later model
selection must use appropriate fold-safe data and the frozen S06 pooled-minute engine gate.

For S06's first prospective-input feasibility dataset, use the saved F4 prior-box all-active sensitivity from S05:
its `control_mean` is the mean of 1,000 target draws, a **proxy** for a per-world D29 target, not the realised
game's minutes. Keep only the pre-origin roster, target, prior dates and prior-profile tier columns; require all
membership/profile dates strictly before the game. At each regulation timeout, target deficit is proxy target
times elapsed regulation fraction minus the player's seconds already played, in minutes; leave it missing for
overtime and unknown prior targets. Current five, score, fouls and stint/rest are observed in-game state, not final
game totals. Build off-court candidates from the prior-box roster plus players already observed on court earlier;
do not add a candidate merely because the player enters later. Exclude known six-foul or earlier recorded ejection
cases from normal incoming eligibility; a prior appearance is evidence of prior participation, not proof of current
physical availability. Never label an unconfirmed-availability non-entry as a known eligible negative: retain it
as unknown. Count entrants not in the prospective candidate set and all missing targets/availability. Prior boxes
are not official dated rosters and their historical publication times are unknown; this diagnostic dataset alone
cannot establish a deployable substitution model. F1–F4 fitting and the existing promotion/engine gates remain
unchanged.

For S06's first **outgoing-decision fold screen**, freeze the following before fitting or inspecting its results.
The evaluation populations are the previously fixed S05 200-game panels in F1–F4, less explicitly recorded replay
quarantines and games lacking a prior roster. Seed the first training set by sampling 200 NBA regular-season games
without replacement (NumPy seed 20261122, sorted game IDs) from the 2022–23 retained, `game_ok` games dated
2023-01-01–2023-04-14; this selection uses no game outcomes. For these seed games reconstruct prior-box rosters
and 1,000-draw all-active D29 target means using ramp/spread fitted strictly before **2022-12-01**, with all player
states and profile dates strictly earlier than each origin. Each fold may train only on those seed games and
previous fixed-fold games dated strictly before that fold's validation start; no game may train and validate the
same fold. The simple baseline is the earlier-training outgoing rate by period (OT pooled) and prior role tier,
shrunk with 20 pseudo-observations toward the earlier-training overall rate; an unseen group uses that overall rate
and its row count is reported. Compare it with one deterministic
native-API LightGBM binary model (120 trees, 15 leaves, learning rate 0.05, minimum leaf 80, L2 1,
seed 20261122, one thread):
period, clock, team-relative margin, fouls, elapsed seconds, stint, prior tier indicators, target mean and the
regulation target deficit. Native missing values remain missing. The primary diagnostic is paired outgoing Brier
loss; also report binary log loss, per-fold populations, missingness and 10,000 complete-game clustered bootstrap
intervals with seed 20261122. A selected-timeout model is worth further investigation only if its pooled Brier
interval favours the candidate and at least three of four fold point differences favour it. This is a node screen,
not the S06 pooled-minute promotion gate. It cannot establish an all-stoppage hazard or production gain: the
opportunity subset is outcome-selected, incoming availability is unknown, and the engine currently has no timeout
events. No parameter or threshold may be retuned on the F4 or protected final-season results.

For S06's first **incoming-selection feasibility screen**, freeze the following before fitting. Use the same seed
and F1–F4 candidate windows and chronology as the outgoing screen. Join a position group only from the candidate's
recorded strictly earlier profile date; unknown positions remain unknown. Condition on a team having at least one
observed outgoing player and on its observed outgoing set: this is an oracle transition diagnostic, not a forecast
of who will leave or how many will change. Describe the remaining on-court players by their prior G/F/C/unknown
counts. The case sample consists solely of observed entrants in the prior candidate pool. The reference sample is
the entire potentially selectable off-court pool at those same team-windows, excluding only recorded six-foul or
earlier-ejection ineligibility; it includes the cases as well as unknown non-entries. Compare cases against this
unlabelled mixture, **not** against supposedly eligible negative labels. Weight each case by the reciprocal of its
team-window's observed in-pool entry count and each reference row by the reciprocal of its pool size. Fit one native
LightGBM binary case-versus-mixture discriminator (120 trees, 15 leaves, learning rate 0.05, minimum leaf 80, L2 1,
seed 20261122, one thread) on earlier populations only. Its output is a relative density-ratio ranking score, not a
calibrated probability of entry or physical eligibility. Inputs are period, clock, margin, fouls, elapsed seconds,
rest, target mean and deficit, prior-tier/position indicators and the four remaining-lineup position counts; retain
native numeric missingness.

On each validation team-window with an in-pool entrant, rank all potentially selectable candidates and take the
observed number of in-pool entrants **for scoring only**. Compare observed entrant recall at that `k` with a fixed
target-deficit ranking (overtime/missing-deficit fallback to target mean, then missing last; deterministic player-ID
ties). Report excluded/out-of-pool entrants, missingness and 10,000 complete-game paired bootstrap intervals.
Further investigation requires pooled recall's paired 95% lower bound above zero and at least three favourable
fold points. The ranker and its unknown candidate pool do not establish active-roster eligibility or an engine gain.
Any joint selector must receive an explicit per-world active roster and disqualification state; it must choose
distinct players and preserve five on court, use positional context without inventing legal position limits, and
surface insufficient eligible replacements rather than quietly activating an unavailable player.

For S06's first **isolated engine feasibility candidate**, freeze the following before any engine result. Fit the
outgoing and incoming node models exactly as above on each fold's earlier seed/fold populations and verify their
validation scores reproduce the stored screen predictions. Sample each simulated world's regulation timeout clocks
from one complete earlier-training game's *selected* timeout template; sample overtime clocks independently from
earlier-training observed overtime periods. Defer a sampled clock to the next recognised simulated dead ball in the
same period; count expired/coalesced clocks. These templates intentionally cover only the selected timeout subset,
not every timeout or legal stoppage, and their outcome-selection bias remains a limitation. At a sampled timeout,
draw the five outgoing Bernoulli decisions jointly conditional on there being enough explicitly active,
non-disqualified bench players; do not activate an unavailable player or silently clamp a proposed lineup. Rank
eligible incoming players with the fitted relative score and sample without replacement using independent Gumbel
noise (temperature 1). The models receive the same strictly prior per-game target proxy, tier and position as their
fold datasets; missing stays missing. The existing per-world D29 schedule is the plan: keep a timeout override until
the plan next changes at a recognised dead ball, and reset at period starts; overtime starts from the closing plan.
Six-foul players must be replaced before a subsequent free-throw rebound, or the simulation must explicitly report
the no-eligible-replacement condition rather than pretending to obey the rule. Use a separate deterministic policy
random stream, preserve the unmodified default path, and report missing inputs, opportunity timing and runtime.

The fixed F4 paired 200-game, 1,000-world actual-participant screen remains the first engine gate, not a pre-game
availability test. Before it, reproduce the saved default on the pinned small-game subset and test simultaneous
substitutions, foul-outs, period changes, overtime, five-player/seconds/points identities and short rosters. A
failure or a negative player-minute result retains the D29 control; no selected-timeout node score is itself a
promotion or a reason to weaken S01's confirmation gates.

For the independent S06 identity check, opt-in capture saves each segment's actual five and each post-foul
replacement five, with the world, period, clock, availability and foul counts, alongside individual player
minutes/points and team scores. A separate auditor reconstructs each player's time from successive lineup clocks,
checks every traced five against roster, availability and foul limits, and reconciles player/period/team totals and
saved backtest means. The same three pinned games and seeds must reproduce the prior candidate before the 200-game
screen. This capture changes no policy draw and is diagnostic only.

For the S06 **player-foul-penalty robustness repair**, freeze the following before another candidate engine
result. The first fixed screen failed because it rejected a world with only four players below six fouls. The
NBA's five-player exception permits the last player to remain when he reaches six, with one technical free throw
for that foul and each subsequent personal foul; a previously removed player is not voluntarily reintroduced.
The [NBA official rule page](https://official.nba.com/rule-no-3-players-substitutes-and-coaches/) returned HTTP
403 to this environment; the rule description is corroborated by the
[basketball personal-foul reference](https://en.wikipedia.org/wiki/Personal_foul_(basketball)#Fouling_out).
Ejections and in-game injuries are not modelled, so their separate re-entry exception is out of this candidate's
scope. Fewer than five explicitly available players at game start still fails.

Keep the original failed policy reproducible; add this only as an opt-in research policy. Continue to replace a
six-foul player whenever an eligible substitute exists. Otherwise retain only the necessary already-on-court
players, never activate an unavailable player, never reintroduce a previously removed foul-out and never suppress
the foul or technical. For each triggering foul, the opposing on-court player with the highest finite pre-game
`ft_pct` shoots one independent technical attempt using that earlier profile probability; player/team FTA, FTM,
points and score must reconcile, the clock and possession are unchanged, and an isolated deterministic random
stream leaves the ordinary policy's draws untouched. An all-missing or invalid shooter probability is an explicit
failure, not an imputed success. This is a rare-rule approximation using the existing pre-game FT profile, not a
new fitted free-throw model or a claim that technical shooters are known prospectively.

Before the unchanged fixed F4 200-game / 1,000-world screen, unit-test sixth and subsequent foul penalties,
available replacements, both sides, technical misses/makes, no voluntary re-entry, short rosters, ordinary
free-throw rebound ordering and deterministic streams. Independently audit captured actual fives, all-player foul
states, technical events, box-score points, seconds, overtime and roster eligibility in the original three games
and in the previously failing game **401810472** using the same seeds. Preserve the originally failed screen,
freeze source fingerprints before rerunning, and report a second failure honestly if one occurs. The original
player-first/minute CRPS, state-response, paired uncertainty, seed-noise and confirmation gates are unchanged;
neither an exception repair nor the node results alone justifies promotion.

For the in-flight fixed S06 screen, before inspecting any candidate score, additionally compare matched control
and candidate fourth-quarter player-minute errors by **realised** start-of-Q4 score margin (ahead or behind by
at least 15, within five, otherwise intermediate) and by recognised personal fouls through Q3 (four or more versus
fewer), as well as by S01 pre-game role. Derive Q4 score state from independently reconciled recorded quarter
scores and foul counts from retained raw play-by-play using the existing personal-foul parser; missing or
inconsistent game/player foul data remain unknown. Report differences in Q4 mean-minute bias, Q4 absolute error
and full-game minute CRPS with 10,000 paired complete-game bootstrap draws and the 100-player-game/30-game support
floor. These bins use outcomes unavailable pregame solely for retrospective analysis. The saved per-player
quarter means are unconditional over simulated states, so this is a **historical-state subgroup diagnostic**, not
a direct measurement of how the policy reacts within a simulated close game, blowout or foul-trouble world. Direct
state-conditioned policy behaviour requires a separate event/state capture; do not claim it from these aggregates.
For that separate check, replay the unchanged fixed candidate with an opt-in capture around its selected-timeout
decisions, using the same game IDs, per-game simulation seeds and 1,000 worlds; first reproduce all shared outputs
on the three preflight games, then on the complete fixed panel. Compare simulated outgoing decisions with the
independently audited historical selected-timeout player decisions on their common games. Classify both using the
same S01 pre-game role and pre-decision period, score margin, foul-trouble and stint bins from the earlier
descriptive protocol; report counts, rates and paired complete-game bootstrap intervals with its existing
100-player-game/30-game support floor. This measures state-conditioned behaviour within simulated selected
timeouts, but the simulated template selection, actual-participant conditioning, unequal opportunity counts and
historical outcome-selected windows prevent causal or pre-game availability claims. No changed draw or promotion
is implied by capture alone.

The completed fixed S06 screen did not establish **3/69** registered non-inferiority bounds despite its uncorrected
pooled-minute improvement. Its full same-policy replay and independent state accounting completed; see FINDINGS for
population-specific rates and uncertainty. Retain the S05/D29 control. Wider-fold and multiplicity-adjusted
confirmation and the protected final test were not run for this non-passing candidate.

For S07's initial report-coverage audit, inventory every retained ESPN collection run without fetching a new source.
Treat each collection's `finished` UTC timestamp as the conservative latest capture time; a dated tip is usable only
when the entire run finished strictly before that tip. Audit missing rosters, injury files, status counts, unmatched
injury IDs and final-box **coverage** separately. Absence of an injury entry is not proof of health. Because retained
2026-27 snapshots belong to the protected final season, count whether a final box contains a rostered player but do
not compare status with play/start outcomes, estimate calibration or use those outcomes for selection. Development
coverage and the scoring gate must be reported separately from this descriptive archive inventory.

**S07 fallback selection:** no retained development-origin injury reports support a status-to-play/start fit.
Keep the fixed status probabilities as explicitly uncalibrated assumptions; a genuinely missing/unknown status
uses the existing 0.6 unknown fallback rather than silently becoming Active. An unlisted injury is an Active
availability assumption, not a reported healthy status; the existing recent-inactivity fallback remains labelled.
Use D29's pre-origin projected-starter rule, filling from eligible uncertain players when fewer than five are
near-certain. Missing rosters and any sampled world with fewer than five available players fail explicitly. A cold
placeholder roster may use a disclosed equal-share fallback; it is not an accuracy result. No future physical-absence
hazard is promoted from censored, coach-DNP-dominated proxies.

For S08, these fixed probabilities are scenario weights, not calibrated injury probabilities; multiplying two of
them is an unvalidated independence assumption, and more-than-two one-out branches are non-exhaustive. The exact
Expected/season mixture must meet D31's accounting requirements rather than round away a discrepancy. For S10,
the retained pathway has no fitted future player-absence hazard; do not treat DNP proxy durations or actual future
participants as future availability. New hazard work requires dated pre-origin cohorts and the unchanged gates.

Chunk A A1 froze the prospective selection, branch identifiers and mixture contract in HANDOFF before implementation.
The 15-minute healthy-role or 0.25 prior-usage selection threshold is an engineering scope rule, not fitted
availability evidence. Missing criteria are conservatively included and labelled. The exact season representation
and its runtime remain untested; no production or accuracy claim follows from freezing this contract.

For S07's first **historical no-report and starter baselines**, freeze the following before scoring. Reuse the
independently audited corrected S05 no-report F1–F4 candidate rows and fixed game IDs; prior-box membership is
inferred, not a dated official roster. Report missing roster games, unlisted/unknown labels and source conflicts.
Compare the existing no-report physical-availability fallback and the already-simulated target-positive frequency
with known play/DNP labels as two separately named **play proxies**, not proven injury-status calibration or an
end-to-end forecast. Give Brier, unmodified log loss (including infinite loss when appropriate), fixed-bin
calibration and 10,000 game-cluster bootstrap intervals on supported populations.

For projected starters, reconstruct D29 state strictly before each origin with each fold's earlier fitted
parameters. On its inferred candidate roster, use the existing no-report availability fallback and the production
`>=0.9` sure-player selection (all candidates only when none qualify), then the existing
`minutes.projected_starters` ranking and positional limits, with player ID as its input-order tie-break because
the original live roster ordering is unavailable. This is a D29-selector proxy, not an exact replay of that order.
Positions must come from a strictly earlier profile;
if a candidate considered for selection lacks a known position, or fewer than five candidates can be selected,
mark that team-game unsupported rather than impute a position or activate a player. Only after selecting compare
against complete observed five-starter sets, including starters outside the prior roster; report unsupported sets,
outside-roster starters, slot accuracy, exact-five accuracy and game-cluster uncertainty. These historical boxes lack
publication timestamps and status reports, so even a good result cannot satisfy S07's genuinely dated promotion gate.
The retained report archive contains no development-origin training or validation examples. Therefore no
report-status play/start candidate can be calibrated under this gate; retain the current fixed status and
no-report fallback without treating its retrospective play-proxy scores as physical-availability calibration.
Continue timestamped pre-tip collection, preserving both rosters and injury files and their capture bounds.
For each status or starter subgroup evaluated, require at least the existing **100 known player-games across
30 games**, explicit unknown/coach-DNP handling, a strictly chronological train/validation split and paired
game-cluster uncertainty; unsupported cells remain inconclusive. These minima are necessary, not sufficient for
promotion, which still requires the full S01 player-first and genuinely dated availability gates.

For S07's exploratory **recorded DNP return/rest sequences**, freeze the following before building the sequence
population or examining its scores. Use only retained regular-season NBA boxes from 2022–23 through 2025–26;
the protected season is excluded. Reconstruct each team's ordered games, player/team listings and strictly prior
outcomes. A known positive-minute appearance is play; a recorded DNP is not-play. A player unlisted in the next
team game, ambiguous minutes/DNP, a team change, season boundary or missing next game censors the sequence rather
than proving continued physical absence. Do not bridge a missing team-game or infer a player's prior injury from
a later label. Report left-censored starts, unlisted gaps and reason categories separately. Explicitly identify
coach DNP, exact `REST`, explicit injury/illness text and other/missing reasons; the last categories are not
classified as injury or health.

At each next-team-game origin immediately following an observed DNP, use the earlier observed DNP spell length
(1, 2–3, or 4+ consecutive listed games), its first recorded reason category and the prior positive-minute role
as retrospective play-proxy features. A spell is left-censored unless its immediately preceding team game listed
the player as playing; exclude these spells from both paired return models. Define prior role from the mean of up to
five earlier positive-minute appearances on the same team in that season: at least 30 minutes is a star proxy,
18 to under 30 a starter proxy, under 18 a bench proxy, and no earlier positive minutes unknown. Compare a
Beta(1,1)-smoothed earlier-training return-to-play rate by reason
with the same rate additionally grouped by the fixed duration bins. For each F1–F4 fold, fit only examples whose
outcome date is before that fold's validation start; validate on its already-fixed 200 game IDs. Report counts,
right-censoring, unmodified probability log loss, Brier and 10,000 complete-game bootstrap intervals with S01's
seed, including the paired Brier difference; use the existing 100-player-game/30-game support floor. Separately,
on a prior listed play, fit a smoothed earlier-training chance that the next known listed outcome is an explicit
rest DNP, comparing an overall rate to the same fixed prior-role groups. A rest or injury subgroup without that support is
inconclusive, not a zero-risk estimate. These models condition on being listed with a known outcome in the next
game and use retrospective DNP reasons with unknown publication times: they do not prove physical recovery,
future roster membership, pre-tip report availability or a deployable season-absence hazard. Because the F4
label-coverage audit has already been seen, this is exploratory rather than a new untouched confirmation. A genuinely
dated cohort and the frozen availability promotion gate remain mandatory.

For S07's exploratory **recorded-spell and starter-frequency follow-up**, freeze the following before evaluating it.
Use the already-audited sequence and F1–F4 fixed game manifests, and each fold's earlier fitted reason-only and
reason-plus-duration rates from the frozen screen. Anchor a spell at a non-left-censored first recorded DNP whose
next scheduled team game is in the fixed validation panel; follow that player's consecutive same-team listings
for at most five next games, stopping at a return, an unlisted/unknown/traded/season-end outcome or the fold's
validation end. The first DNP counts as one recorded missed game. Treat the latter outcomes as right-censored,
not observed continued absences; do not extend a fold into the protected season. Compare baseline and candidate
10,000-draw simulated recorded-spell lengths with the corresponding analytic survival and censor-aware observed
return-time/recorded-games-missed estimates. Give risk/event/censor counts and 10,000 complete-anchor-game
bootstrap intervals by prior role; require 100 at-risk observations across 30 games for each reported horizon.
Kaplan–Meier comparisons assume non-informative censoring and remain explicitly descriptive because unlisted
players may be selectively missing. The simulations model recorded listings and DNPs, not physical absence.

Separately, on the already-audited inferred prior-box candidate rosters and complete observed five-starter
team-games, draw 10,000 independent per-player no-report fallback states for each game/team with deterministic
game/team seeds. Apply the existing as-of D29 starter ordering and G/F/C limits to each active world, not the
observed lineup; count a world with fewer than five candidates or an active player of unknown position as
unsupported rather than activating or imputing anyone. Report support, five-player identities and predicted versus
observed starter frequency and Brier by pre-game role with game-cluster bootstrap intervals, plus observed
starters outside inferred rosters. These are exploratory independent-fallback scenarios: the fallback was not
validated as physical availability, independence is untested, and conditioning on complete known rosters/starter
labels is not a dated pre-tip forecast. No candidate is promoted, and no fold, support threshold, horizon or
setting is selected using these follow-up results.

**S07 hand-off contract for S08/S10:** the retained dated development-report cohort has zero origins, so the fixed
status-to-availability values remain uncalibrated fallbacks, not fitted play probabilities; an unknown or missing
status must remain visibly unknown. A same-team current roster/report match may supply a status, but an ambiguous
multi-team roster or stale other-team report cannot establish eligibility. Cold players retain explicitly labelled
prior-based roles, missing rosters must not be repaired from actual game participants or starters, and an
impossible five-player availability pattern must not silently activate a player. S08 may multiply up to two
reported-maybe fallback probabilities only as an explicit, unvalidated independence assumption; more-than-two
one-out branches are non-exhaustive under D31. S10 may consume an accepted near-term Expected mixture, but the
recorded-listing survival proxies do not justify adding physical injury, return-date or rest hazards to the
long-range pathway. Until dated evidence passes the frozen chronological support and calibration gates, retain
pathway v1's no-future-absence model and disclose that limitation.

The delivered S07 placeholder repair explicitly flags worlds with fewer than five positive minute inputs and uses
equal regulation-minute shares among their sampled available players; it is an uncalibrated emergency assumption,
not inferred health or a replacement for the engine's separate D29 cold-player prior. Fewer than five available
players still fails explicitly. Do not treat this synthetic fallback as a measured accuracy improvement.
Daily starter accuracy uses only prospective games whose saved snapshot completion is verified before tip.
Retrospective and completion-unverified legacy records remain separate and do not enter that pre-game aggregate;
current-season monitoring is not a feature-selection or promotion dataset.

For S03's remaining flow diagnosis, reproduce the **same 200-game, 1,000-world** free-running control with its
original seeds and opt-in diagnostics only; audit every original output field against the retained reproduction before
using the extras. Record player FGA/FTA/turnovers and quarter minutes/scoring, simulated segment-clock summaries,
and scheduled-five overlap against retained real stints at 10-second midpoints in regulation. Report invalid/missing
real fives and unknown profile values rather than filling them. Scheduled tables precede foul-out substitutions and
do not prove which five was on court at every simulated event. Compare teacher-forced and free-running components and
pre-game role cohorts with paired game-cluster intervals, keeping each source's actual accounting separate; quarter
and lineup/clock measurements are supporting diagnostics, not a causal isolation of each mechanism. This
instrumentation and comparison are specified before running the expanded control, not a model-promotion test.

S03's two S04 mechanism families are frozen after the full matched-flow audit, before their candidate runs:

1. **Rim node expression.** Test a training-tail-fitted, zone-specific additive log-odds response to the existing
   implicit player/defender matchup input on actual rim shots. Preserve the baseline training-tail mean predicted
   make rate when fitting the response; missing matchup inputs retain the unchanged baseline prediction. Fit all
   coefficients and centring using that fold's earlier training data only, and keep the original three-class
   make/and-one ratio. The exploratory F4 trace predicts more matchup-profile expression at the rim, but the
   positive contrast is confounded and post hoc. Reject the family if paired held-out shot loss or independently
   confirmed player-first engine gates do not improve; increased spread alone is not success.
2. **Incremental tracking defence.** From retained dated NBA tracking responses, test strictly pre-origin
   player-level defended-shot counts/rates, aggregated through the actual or simulated defensive five, as a
   separate increment over the same baseline. Join person to team through the dated game log, not the unreliable
   latest-team field; retain unknown rates and audit all date/identity/five coverage. The provider's
   `Less Than 6Ft` and `3 Pointers` categories must be described as source buckets, not assumed on-ball matchups.
   Predict better rim/three-quality calibration without inflating the score level; disconfirm on paired fold loss,
   missing-coverage/cutoff failures or the original player-first and team non-inferiority gates. Do not treat
   v1.4e's mixed real-matchup-plus-deterrence result as this isolated ablation.

Both use the exact S01 controls, fixed game sets, seeds and thresholds where applicable; F4 suggested these
hypotheses, so F1–F3 and the predeclared confirmation/second-stream tests are essential independent checks. The
tracking files' original publication/revision timing remains unproven. Neither family may use final-season
results for selection, and a node-only gain never constitutes a model promotion.

For the first family's historical node screen, refit the v1.3 shot-node recipe on each S02 guarded,
body-free dated-assignment feature schedule; compare the exact same fitted node and rows with and without the rim
calibration. These guarded inputs differ from v1.3's historical static assignment and causal fixes, so this is a
matched **causal-input diagnostic**, not the unchanged v1.3 engine control. Report both the full held-out fold and
the S01 fixed 200-game subset, with game-clustered uncertainty, rim/profile-reliability counts, and other-zone
invariance. The original v1.3 control remains unchanged and is mandatory for any later engine gate. Fit the
calibration only on the latest training-window tenth; its intercept preserves that slice's known-rim baseline mean,
not the held-out outcome rate. Keep a direct dependency on SciPy for its deterministic root/optimizer routines.

For the second family's first isolated node test, freeze the following before fitting: accumulate each defender's
retained `Less Than 6Ft` and `3 Pointers` made/attempted counts over dates **strictly before** the shot's origin,
with no tuned decay or attempt threshold. An unknown player or zero prior attempts remains unknown. Match every
source row to its unique NBA player/day team log and the ESPN identity crosswalk, and validate each defender against
the target game's dated team; never use the source's latest-team label. For a valid defensive five, use the equal
mean of all five known defended-shot rates; if any are unknown, leave the candidate input missing and retain the
baseline. The source categories are tracking buckets, not necessarily actual shot zones or on-ball assignments.
Fit separate level-preserving additive log-odds slopes on the earlier training tail for actual rim shots and for
corner/above-the-break threes; hold each fold's previously saved guarded shot node fixed and retain its make/and-one
ratio. Report data/identity/lineup coverage, complete folds and the fixed-200 subsets with paired game-cluster
intervals; compare against the measured same-input seed-noise floor under the existing node gate. These retrospective
tracking files and the global identity crosswalk lack historical publication/revision timestamps; they do not prove
the feature was available unchanged at the original date. A node win is not a forecast or promotion, and deployable
use would need the same cutoff-safe feature online plus the player-first engine gates.

After both isolated S04 families failed their node gates, an interaction check may compose their already-fitted
log-odds increments on the identical held-out shots without refitting either family. Compare the combined loss and
its non-additive interaction with the two single-family losses using game-clustered intervals. This is post hoc
and descriptive: it cannot rescue a failed family, qualify a combination for promotion or substitute for the
unchanged-v1.3 player-first engine gates.

#### S01 population separation — 22 Nov, before availability candidates

The conditional-engine panel is the fixed 200 F4 games above: the box supplies **who played**, while starters are
projected from pre-game features. Player outcomes therefore condition on actual participation and cannot measure
missed players, false availability or real pre-tip roster coverage. State that assumption, the exact game/player
counts, unknown tiers and missing outcomes beside every score.

The separate historical availability diagnostic must construct its candidate `(game, team, player)` universe
**before joining that game's box**. For origin D, use players observed in retained same-season team box records
(including listed DNPs) strictly before D, assigning a player to their most recently observed team before D; ties or
unresolved team identity are unknown and reported. This is an inferred historical membership universe, **not an
official dated roster**: separately count players who actually appeared but were absent from the pre-game universe,
stale memberships, games without prior history, ambiguous labels and all excluded/unmatched rows. Do not select or
remove candidates based on their same-day box. Report play Brier/log loss and calibration with game-clustered
intervals; evaluate starter predictions separately, conditional on the declared cohort. A probability cannot pass
as an end-to-end availability model merely because it scores well after excluding unknown arrivals or transfers.
Restrict historical box events to the 30 canonical NBA team IDs: the 2025–26 file includes four All-Star games
marked `season_type=2`. The separately retained NBA-only candidate cohort corrects 12 displaced memberships; the
original S01 report remains archived for audit. This data correction does not change the pinned engine panel.

Historical F1–F4 lack the current ESPN collection's dated injury/roster reports. The only retained ESPN collection
origins currently span **19–21 Nov 2026**, inside the protected 2026–27 final season; checking their existence is
not permission to tune or repeatedly score against those outcomes. Conservatively requiring collection completion
before the scheduled tip, an injury file and both roster files gives file coverage of **4/4, 9/9 and 5/6 games**
on those dates, respectively. This verifies file presence only, not player-level completeness or predictive quality.
Missing historical reports stay unknown, not silently active or retrospectively reconstructed from the final box.
Any claim requiring report-dated injury status remains unsupported until an admissible dated cohort has enough games
and provenance. S07 must document cohort coverage and retain the existing fallback if that evidence is insufficient.

The prior-box cohort is now built by `scripts/a1_availability_cohort.py` on the pinned 200 F4 games, before any
availability candidate. It contains **7,305** inferred player-games; **5,201** have known positive-minute or DNP box
labels, **2,095** are unlisted and **9** have zero/missing-minute ambiguous labels. **32** positive-minute player-games
in **24** games are absent from the inferred universe; another **12** newly listed DNP player-games are outside it.
Seven candidate records conflict with a same-day listing for another team, checked only after constructing the cohort.
The row artifact includes each strictly earlier source date; its `listed_in_box`, `played`, `minutes` and `starter`
columns are retrospective labels/audit facts, never pre-game features. This is coverage evidence only, not a scored
forecast; retained prior boxes have no historical publication/correction timestamps and do not prove an original report
was available. The additional play-by-play participant missing from the raw box remains unscored. Exact counts and limitations:
`analysis/experiments/20261122_a1_prior_box_coverage.json`.

### 8.3 Candidate sequence and promotion

- S03 chooses two or three mechanisms with falsifiable predictions. S04 tests profile/defence/shot-quality changes
  separately; S05/S06 minutes; S07/S08 availability; S09 form/end-game; S10 pathway. Keep candidate config and artifact
  namespaces separate from production. No arbitrary post-hoc team-score inflation to match a regression slope.
- Cheap accounting/node/allocator checks first, then fixed 200-game F4 screening at 1,000 worlds. Record conditional
  engine player MIN/PTS/REB/AST/3PM CRPS, bias and interval coverage by tier and reliability/return/rotation groups;
  secondary steals/blocks/fouls/shooting checks help explain changes. A better team total cannot compensate for a
  materially worse player tier. Do not optimise these many metrics separately until all look good.
- Retained inputs get F1–F4 node ablations; every learned auxiliary artifact must be fitted inside that fold, including
  assignment θ, archetypes, reliability/shrinkage estimates, minute ramps, substitution models and covariance draws.
  A December-2025 assignment file cannot be used for F1 or F2. Cross-data comparisons keep held-out rows identical.
- S11 freezes the combined candidate and compares it against matched controls on **all eligible F4 games**, plus
  fixed **200-game samples from each of F1–F3** (or all if fewer). The exact manifest is fixed in S01; add missing-game
  accounting and exact overlap assertions. These are broader historical validation populations, not a newly untouched
  final test. Confirm with a second simulation seed and **20 prespecified games at 10,000 worlds** spanning tiers,
  short rosters, close/blowout outcomes and overtime diagnostics. Run backtests sequentially, measure actual pace.
- Team gates: paired margin/total/quarter CRPS, win log loss/Brier and calibration; joint dependence, tails and
  state-responsive minutes. Compare strength/component loadings against observed coefficients on those same games,
  with uncertainty. Coverage improving only because intervals became overly wide is not success: CRPS must hold up.
- Season candidates use 2022-23→2025-26 and the existing four start dates (16 origins), selecting on three seasons and
  scoring the fourth. Report final-win CRPS, dispersion, coverage and surprise persistence **by start date**, not just
  pooled. Compare on identical schedules with the same Cup/final standings convention and document any correction.
- Integrated acceptance includes component-removal ablations, short/missing rosters, foul-outs, simultaneous subs,
  period ends/OT, unknown reports, deterministic reruns/worker changes, late-data-injection tests and measured whole-
  nightly runtime within D10. Every world preserves five on court, team seconds, score identities and branch/season
  mixture accounting. Instrumentation for sampled event logs must not alter draws or outcomes.
- A release manifest records retained/rejected components, data/schema/config hashes, fitted model dates, evidence,
  limitations and fallback. Only then fit/score the frozen new version on the final test **once**. The current `--final`
  implementation trains through **2026-06-30** and scores from **2026-07-01**; inspect and record this, never treat it as
  a generic refit-through-today command. Model recipe and fitted artifact versions are separate identities.
- A final-test failure may stop release but never invites tuning to that result, rerunning it under cosmetic version
  names or selecting among multiple final-tested candidates. Further modelling returns to F1–F4. A negative chunk
  retains v1.3/pathway v1, delivers S12's model-facing UI improvement, and still finishes with S14's live nightly.

### 8.4 Date-safe current-model history

**Deferred by owner D40 (22 Nov):** do not implement or run the historical forecast replay during this A1
execution. The rules below remain safety requirements if it is later reauthorised; they do not justify running it now.

The owner's preferred historical view uses the current accepted recipe across the whole season (ENGINE_PLAN D39/§17).
This is retrospective reconstruction, distinct from originally published forecasts. A pre-season-trained version may
serve every subsequent origin; a later refit cannot be used before its training cutoff. Build/reuse dated fits of the
same frozen recipe for earlier origins, including all auxiliary estimators. All inputs use games strictly before ET D;
Tomorrow previews share D's cutoff. Archived report timestamps, raw revisions and missing roster history are recorded.

The season-to-date replay is for a coherent dashboard under that version. It is **not another tuning/selection loop
on the 2026-27 final test**. Freeze settings before replay, preserve prior-version/original forecasts, keep display
scores labelled by version and live/reconstructed kind, and record the version's single formal final-test score.
Do not repeatedly score growing final-test windows to choose changes. Normal result-review pages may join actuals to
saved forecasts; those observations cannot be used to tune the next candidate on that held-out season.

### 8.5 Research checkpoint record

Each completed S task records the hypothesis, eligible population, cutoffs, run/config IDs, metrics and uncertainty,
negative results, keep/reject decision, production/PWA impact, runtime and exact next command. Update FINDINGS for measured
facts and PLAN/HANDOFF for status, review the remaining docs, then commit and push. Do not leave a finding solely in
terminal output or chat. Candidate work may span sessions; preserve partial run logs/resume state and the next rung.
S14 creates the successor chunk with the same modular scope, weighted ladders and end-of-chunk nightly requirement.

At an accepted-model/output checkpoint, refresh the affected forecasts and iCloud bundle, update a changed static
shell, and verify PWA model/cutoff metadata and import/offline compatibility (owner, 22 Nov; AGENTS §5). Candidate-only
research does not publish unaccepted models. S14 still performs the final nightly and integrated delivery.
