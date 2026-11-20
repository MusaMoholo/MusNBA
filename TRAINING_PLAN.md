# Training plan — models for the possession engine

**v3 · 19 November 2026 · approved (owner: as accurate as possible, rich data, experiment freely). M5 v1 results: FINDINGS §3g; tuning: §3h.** It details
[ENGINE_PLAN.md](ENGINE_PLAN.md) §6–§10 for the data built in M1–M3. Progress lives in [PLAN.md](PLAN.md).

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
| Shot profile | zone shares (rim, paint, mid, corner 3, above-break 3); assisted share by zone (self-creation); **next (D30)**: shot type from the play text (pull-up, step-back, driving, cutting, alley-oop) |
| Accuracy | FG% by zone, FT%, and-one rate, blocked rate |
| Playmaking | assist rate on teammates' made shots while on court |
| Ball security | turnover rate per use; live/dead split |
| Fouls | fouls drawn (shooting / non-shooting), personal fouls committed per minute |
| Rebounding | offensive and defensive rebound share of available rebounds while on court |
| Defence | steal rate, block rate on opponent rim attempts, opponents' turnover and rim rates while he is on court; **next (D30)**: opponent FG% allowed by zone (lighter shrinkage), weighted for each shooter by a soft matchup assignment over the five on court (size, role, position; learned from foul and block credits), plus help defence |
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
- Hyperparameters: modest trees (31–63 leaves, learning rate ~0.05, early stopping on validation).
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

**Game-level gate (20 Nov).** Node log loss is necessary, not sufficient: small per-possession effects add up over a game
(on-court defence was neutral at node level, §3l, while the backtest shows defence expressed at ~25% of its real effect,
FINDINGS §3o). Inputs aimed at team strength are judged by the engine backtest as well (`backtest.py`, same seed and games
as the control run): `strength_loading`, margin slope, margin/total CRPS and win log loss against the current engine and
the team-rating model.

**Sample-size buckets.** `games_eff` (role family, 5-game half-life) caps at ~7.7, so per-sample-size verdicts use the
deciding player's decayed offensive segments (`scripts/buckets.py`: < 250, 250–750, 750+).

Richer sources needing an owner decision: NBA tracking data (drives, touches, catch-and-shoot v pull-up,
defender distance) via the NBA Stats API (PLAN.md §7 item 1).
