# Training plan — models for the possession engine

**Updated 22 November 2026.** Serving engine **v1.3**, 16 decision models, D29 minutes and D30 defence inputs;
real-matchup candidates v1.4c/e/f were rejected (D37). A1 S01–S03 are complete; S04 defence experiments and S05
minute screening follow. Historical
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
`scripts/a1_minutes_gate.py` is intended to apply the frozen pooled-MIN seed-noise screen and registered player/game
non-inferiority bounds to a paired report. Its first and v2 reports used the seed interval's half-width rather than
the registered maximum absolute endpoint; do not use it for selection until corrected and regression-tested.
Even after correction its uncorrected 95% result is an early screen only: Holm-adjusted family confirmation, wider
folds, mechanics and the other promotion gates still apply.
Before using the strict candidate's first historical screen for selection, a deterministic defect was found:
redistribution can activate a zero target even when already-positive targets can absorb the deficit, changing the
`draw > 0` target-play diagnostic. Correct this invariant without changing the registered populations, normal
streams, availability fallback, scoring, or other candidates; retain the uncorrected reports and hashes. Rerun
the conditional and both historical roster screens under new names, verify control/NBA-only values reproduce,
and report strict/combined results only from the corrected version. This is a candidate implementation repair,
not a revision of the promotion gates or evidence that the player is actually available.
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
