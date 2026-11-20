# Engine plan — possession-level simulator (phase 2)

**v6 + D18–D25 · 19 November 2026 · approved; in implementation — progress in PLAN.md §6, next steps in HANDOFF_NEXT.md.** Nothing here is implemented. Items marked
**Proposed** become decisions once agreed; §14 lists the questions still open. Progress is tracked in
[PLAN.md](PLAN.md); measured facts live in [FINDINGS.md](FINDINGS.md).

## Decisions so far

| # | Question | Decision (19 Nov) |
|---|---|---|
| D1 | Possession unit | Segments; an offensive rebound continues the possession with a 14 s shot clock |
| D2 | Quarter models | One model per decision, trained on every quarter, with period, clock and game state as inputs; per-quarter variants tested per node and kept only where they predict held-out games better |
| D3 | Form | Per-player, per-world form (efficiency, aggressiveness, shot selection) with role-dependent spread, plus a tested "heat check" response to in-game makes (§5) |
| D4 | History and dependencies | 2022-23 onward from hoopR (ESPN IDs) plus our own collection; `lightgbm`, `pandas`, `pyarrow` approved |
| D5 | Low-sample players | Profile- and role-based representation with stat-specific shrinkage and per-world talent draws (§7a); NBA data only — no college/international translations |
| D6 | Chain order | Owner's order: who → what (shot zone, turnover, foul drawn) → result → assist / block → rebound; turnovers split live (steal) / dead (§2) |
| D7 | Minutes | Target-aware substitution model, replay rotations as v0; variance sources and measured targets in §4 |
| D8 | Market lines | Evaluation only. Lines should emerge from a good ground-up model; injuries enter as availability inputs, so a late scratch needs a refresh run (§9) |
| D9 | Watch a sim | Keep five sampled worlds per game |
| D10 | Speed | Nightly budget ≤ 60 min. The engine runs LightGBM in the loop; no lookup tables (§9) |
| D11 | Refit cadence | Refit when 7 or more days have passed since the last successful refit (date kept with the model), or when forced with `--refit`; features update nightly |
| D12 | Pre-tip refresh | Deferred to polish (phase 5) |
| D13 | Two horizons | **Near term** (next 7 days, ~50 games): full engine, 10,000 sims per game, player and period outputs. **Long range** (rest of season): team-strength model calibrated to the engine — win %, score, spread only (§12) |
| D14 | Season sim | 10,000 universes, every remaining game once per universe (as MusSim); universe *k* uses world *k* of each near-term engine sim, so both horizons share the same draws (§12) |
| D15 | Absences | Season universes sample future injuries and rest from players' historical games-missed patterns, on top of reported injuries and return dates (§12) |
| D16 | App beyond 7 days | Only win %, expected score and spread, labelled as a long-range estimate; no player or period detail |
| D18 | Inputs and updates | The possession models never take team strength as an input — only the ten players' profiles, game state and context; team strength is an output. Within the 7-day window each world plays a team's games in order, and after each game that world's player stats and form update from the simulated box score before the next. Beyond the window, team ratings start from an Elo/ratings fit on this season's real results and update in each world from its simulated games |
| D19 | Game types | One model per decision across regular season, NBA Cup, play-in and playoffs, with game type (and playoff round) as an input; game-type sample weights tested on the folds. Measured: playoff starters +3.0 min, top player +3.6, top-8 share 93.8% v 90.6%, pace −4%, points per possession 1.108 v 1.128 |
| D20 | Decision chain | Owner left the number of steps to the data. Fifteen decisions in four stages — **clock**: time to the event, event type (action, defensive foul, violation); **action**: who (of five) → what (rim, paint, mid, corner 3, above-break 3, turnover, fouled on a 2, fouled on a 3) → shot result (miss, make, and-one); **credit**: assisted → assister, blocked → blocker, turnover type (steal, offensive foul, other) → stealer, fouler; **after**: free throw, rebound (offence/defence × player/team) → rebounder. Rules, not models: free-throw counts, penalty/bonus, shot clock, period ends, foul-outs. Every node has ≥ 50k training rows |
| D17 | Long-range strength | MusSim's per-world pathway: each universe starts from a draw around today's strength and updates every team after every simulated game — near-term engine results included — by the rating system's own response to the result, against the world's own expectation, with one gain calibrated to real season dispersion (§12) |
| D21 | Shot location; team turnovers | **Engineering decision from data (19 Nov); owner confirmed the location stage (19 Nov) — team turnovers and team rebounds stay outcomes of existing stages, not new ones.** A 16th decision, **location** — the shot's distance band (21 bands, 3–5 per zone) given zone, shooter and context — sits between *what* and *shot result*; later decisions see the band's mean distance and lateral offset. Reason: distance is the strongest input after zone (leaving it out costs 3.1 nats per game over the chain: blocked +3.8%, assisted +1.1%, shot result +1.0%) and no step produced it. *Event* gains a fourth class, **team turnover** (shot clock, 8 s; 5.3% of turnovers), which credits no player. All-Star and exhibition games are excluded from every dataset |
| D22 | Default model and the floor | **Owner (19 Nov): the possession engine v1 (`scripts/engine.py`, `models/v1.json`) is the dashboard's default projection from now on, and it is the floor** — a later engine, model version or rule replaces it only when the backtest/aggregation tests show it is better (M6a, M9). The placeholder `baseline-v1` stays for retrospective backfills (the engine reads latest profiles, so past dates would leak) and as a comparison saved beside each engine snapshot. The season simulation is still the placeholder's team-strength pathway, fed the engine's win probabilities for today's games |
| D23 | Rebound clock convention | **Engineering decision from data (19 Nov), under D22's test.** From 2026-27 ESPN stamps every rebound with the clock of the miss it follows (100% v 7–12% in every earlier month; FINDINGS §3k). Every season's segments now use that convention (`possessions.py`, default `--rebound-clock miss`), so history and live inputs are built alike. Measured: on live-style held-out rows the old models are worse on 12 of 16 nodes (chain +34.1 nats per game) and M6a box scores improve (threes bias +7.4% → +1.0%, steals +9.6% → +0.8%, turnovers +8.0% → +1.5%, defensive fouls −20.5% → −1.0%; CRPS lower on every stat but blocks, level). **v1.1** (v1's settings on this data) replaced v1 as the engine's models; v1 and its data are kept (`data/derived/variants/rebound_feed/`) |
| D24 | Engine horizon: today and tomorrow | **Owner (19 Nov): the engine projects today's and tomorrow's slates, always** (replaces D13's seven-day near-term window for the dashboard). `nightly.py --ahead 1` (default) builds tomorrow's snapshot from what is known today — injury report, profiles through the last final — and rebuilds it the next night (the old one archived). The app's as-of date for standings and rosters stays the newest snapshot dated today or earlier (`views.current_snapshot`). Long-range games (D13/D16) are unchanged |
| D25 | Season beyond tomorrow | **Owner (19 Nov), to build:** the nightly simulates today's and tomorrow's games with the engine (universe k plays engine world k) and every later game with team strength in MusSim's fashion — per-world ratings that update after every simulated game by the rating estimator's own response, against the world's own expectation, carried forward fixture by fixture (D14, D17). Not built yet (HANDOFF next actions): today's season sim draws later games from fixed probabilities |

## 0. What "true to form" means

The engine is right when, on held-out games, its simulated distributions match reality:

| Level | Targets |
|---|---|
| Team | Points, margin, total and quarter scores (CRPS); win-probability calibration; overtime rate (5.4% this season) |
| Pace | Possessions per team-game (~99–102, SD ~9); possession duration by start type (§1) |
| Players | Minutes in total and by quarter; PTS/REB/AST/3PM/STL/BLK distributions (CRPS, PIT); shooting splits |
| Rotations | Substitutions per team-game (34.5; 10–90%: 26–44); stint lengths; starter minutes in blowouts v close games; foul-trouble response; lineup minute concentration |
| Identities (every world) | Five per side on court at all times; player-seconds per team-period = 5 × period length; player points = team points; possessions alternate legally |

## 1. What the data already says (222 games through 18 Nov)

| Measure | Value |
|---|---|
| Possession length (game clock), all | 14.3 s mean — the owner's "~15 s" estimate holds |
| … after a made basket | 16.4 s (10–90%: 9–24) |
| … after a made final free throw | 15.1 s |
| … after a dead-ball turnover | 14.3 s |
| … after a defensive rebound | 13.0 s (6–21.5) |
| … after a steal | 7.6 s (3–16) |
| … at period start | 17.5 s |
| Offensive rebounds per possession | 0.18 |
| Substitution events per team-game | 34.5 (26–44) |
| Quarter minute shares, competitive games | starters 26/24/26/24%, bench 23/27/24/26% |
| Player quarter tendencies | Doncic 37% of points in Q1 on 33% of minutes; Sarr 47% on 31% |

Exploratory parse; possession boundaries will be formalised in M2 (the crude parse finds ~99
possessions per team-game against the 102 box-score estimate).

## 2. Anatomy of a simulated game

Game → periods (Q1–Q4, overtime as needed) → **segments** on a running game clock. A segment runs
from a start (inbound, rebound, steal, jump ball) to a terminal event (shot, turnover, foul, end of
period). A **possession** is one or more segments — an offensive rebound continues the possession
with a fresh (14 s) shot clock.

```
period start → each side's five (rotation model); team fouls reset; carry score, fouls, minutes, form
while game clock > 0                                   (all 10,000 worlds advance together)
│
├─ DURATION   seconds this segment uses ← start type, game/shot clock, margin, lineups, pace
│             clock −= duration; the ten players on court accrue it  ← minutes come from here
│             period expires first → end-of-period outcome (heave or none)
│
├─ defensive foul, not in the penalty → dead ball, new segment (shot clock ≥ 14)
├─ violation · jump ball
└─ WHO        which of the five ends the segment (usage)
   │
   ├─ SHOT    zone: rim · paint · mid · corner 3 · above-break 3
   │  ├─ MAKE        → assisted? → by which of the four · and-one? → free throw
   │  │                 possession changes
   │  ├─ MISS        → blocked? → by which of the five defenders
   │  │                 → REBOUND: offence / defence / out of bounds → by whom
   │  │                    offence → new segment, 14 s shot clock (same possession)
   │  │                    defence → possession changes
   │  └─ FOULED      → which defender · two or three free throws → rebound if the last misses
   ├─ TURNOVER  live ball → steal by which defender → fast-break start
   │            dead ball → substitution window
   └─ FOUL DRAWN (non-shooting) → which defender · penalty? free throws : new segment
│
└─ dead ball? → timeout model → substitution model (who leaves, who enters)
period end → next period; tied after Q4 → five-minute overtime(s)
```

Rules are rules, not models: shot clock (24/14, off when the game clock is shorter), penalty and
bonus free throws (per-period team-foul limits, last-two-minutes and overtime variants), foul-outs,
period lengths, overtime, five players on court.

## 3. Time and possessions — the owner's clock idea, refined

Owner proposal: simulate each quarter from 0 to 12 minutes with possessions sprinkled along the
timeline, sampling observed time per possession, and accumulate minutes from it.

**Proposed: yes — the engine runs on the game clock**, with one refinement: each segment's duration
is sampled *sequentially*, conditioned on how it started and on the game state, instead of placing
"possession n at t seconds" independently. Why:

- Duration depends strongly on start type (7.6 s after a steal v 16.4 s after a made basket) and on
  state: end-of-quarter holds, 2-for-1s, trailing teams hurrying, leaders milking the clock.
- The number of possessions then *emerges* — pace varies between worlds as it does between real games —
  instead of being fixed at ~50 per quarter.
- Shot quality depends on duration (transition layups v late-clock jumpers): later nodes take the
  sampled duration as an input.
- Minutes are exact: every segment's duration accrues to the ten players on the floor; free throws
  use no game clock. Quarter minutes, stints and totals all come from the same timeline.

Duration model: whole seconds 0–24 (0–14 after an offensive rebound or kicked ball), unconstrained
when the game clock is below the shot clock, truncated at the buzzer. Parametrisation (decided by
benchmark, §9): start-type empirical distributions tilted by a small learned model, or a compact
multiclass model.

## 4. Rotations and minutes — the substitution model

Requirement: substitutions happen inside the possession simulation, minutes aggregate to realistic
expectations, and game state (fouls, blowouts, overtime) still bends them.

**Proposed: a target-aware substitution model.**

Before tip, per player and world:
- availability (injury report, as today) and **target minutes** m\* for a competitive game, sampled
  around the projection (recent minutes, teammates out, back-to-backs, restrictions);
- a **rotation curve** p_i(t): his chance of being on court at each game minute, from recent stints,
  shrunk to role templates (position × minutes tier) and fitted so the available players sum to five
  at every minute (baseline-v1's quarter fit, at minute resolution);
- planned minutes so far E_i(t) = ∫p_i, and the running **deficit** d_i(t) = E_i(t) − minutes so far.

At every dead ball (fouls, dead-ball turnovers, violations, timeouts, period starts), per side:
1. **Out model** — P(player leaves): stint length (fatigue), deficit, personal fouls × period
   (foul trouble), margin × time remaining (garbage time, closing lineups), period start, role.
2. **In model** — P(bench player enters | someone leaves): conditional logit over eligible bench
   players — deficit, rest since last stint, positional balance with the remaining four, role, fouls.
3. Forced moves: foul-outs; injuries are out of scope for v1.

The deficit term works as a feedback controller: players ahead of plan tend to sit, players behind
tend to enter, so minutes land on target in competitive worlds while blowouts, foul trouble and
overtime pull them away as they do in reality. Each team's history teaches its coach's habits — tight
or deep rotations, when the stars return, who closes.

**Fallback and v0: replay rotations.** Sample a real stint timeline from a recent game with a similar
available roster and repair conflicts. Realistic by construction but blind to game state; it lets the
engine run end-to-end before the substitution model is trained, and it is the baseline to beat.

**Where minutes variance comes from** — targets are a soft pull, never a fixed allocation:
1. the target itself is drawn per world (pre-game uncertainty: role, rest, coach's choice);
2. substitution timing is stochastic — the deficit shifts probabilities, it does not schedule exits;
3. foul trouble, from simulated fouls;
4. blowouts and closing lineups, from the simulated score;
5. overtime.
The strength of the pull (how rigidly each coach sticks to plan) is learned from his team's history.

Measured targets the simulated minutes must reproduce (players averaging 30+ minutes, 8+ games,
through 18 Nov): game-to-game minutes SD 4.1 (10–90%: 3.0–6.1), 3.1 in close games (final margin
≤ 10); 5.8 fewer minutes in blowouts (20+). Doncic: 36.4 average, SD 2.8; 37.8 in close games, 33 in blowouts.

Checks: minutes CRPS by player and quarter; minutes SD in close games and blowouts against the targets
above; stint-length distribution; substitutions per team-game; lineup minute shares; five on court.

## 5. Periods — style differences and carry-over

Owner proposal: quarter-specific play-by-play models, each quarter feeding the next.

**Decided (D2): one model per decision, trained on every quarter, with period and clock as inputs**,
plus player × period features (e.g. his own Q1 usage share — the Doncic effect). A boosted-tree model
grows quarter-specific branches wherever behaviour really differs — "Q4, under two minutes, trailing by
3–6 → foul" — and learns once, from all the data, what is the same in every quarter, such as a player's
corner-three accuracy. Four separate quarter models would each see a quarter of the data and could not
share any of it: more noise, no extra signal. Game state and tactics drive play in every quarter, and the
shared model sees them all. Per-quarter variants (or shared-plus-quarter-offset models) are still tested
per node and kept only where they beat the shared model on held-out log loss and per-quarter calibration.

What carries from one quarter to the next, in order of importance:
1. **State** — score margin, minutes and stint fatigue, personal fouls, timeouts (team fouls reset).
2. **Game-state behaviour** — trailing teams take more threes and play faster, leaders slow down,
   garbage-time lineups appear: all learned from margin × time features.
3. **Per-player form, per world (D3)** — at tip each world draws, for every player, a night's form in
   three facets: *efficiency* (make probability), *aggressiveness* (his weight in the "who acts" choice —
   teammates' shares fall accordingly, because the choice is among the five on court) and *shot selection*
   (tilt toward harder/pull-up or rim attempts). Plus a team-level shared component (pace, team shooting
   night). The spread of each facet is player-specific — estimated from his own game-to-game variation
   beyond chance (overdispersion in usage and efficiency), shrunk toward his role's typical spread
   (primary creators swing in usage, spot-up shooters in makes). Calibrated so player and team variance
   across worlds matches held-out reality.
4. **Heat-check behaviour** — players who have just made shots tend to shoot more and take harder shots.
   In-game makes so far (and a recent streak) enter the actor and shot-zone models as features, tested and
   kept only if held-out log loss improves. Facets 3 and 4 together produce "Luka on a heater" worlds:
   strong form → early makes → more and bolder shots, within realistic bounds.

## 6. The nested model chain (superseded in detail by D20 — see TRAINING_PLAN §1)

| # | Node | Choice set | Main features | Family |
|---|---|---|---|---|
| 1 | Duration | seconds 0–24 (0–14) | start type, game/shot clock, margin, period, lineup and team pace | tilted empirical or multiclass |
| 2 | Segment type | offensive action, defensive foul without free throws, violation/jump ball | duration bucket, state, defensive pressure, team fouls | multiclass |
| 3 | Who | the five on court | usage, quarter usage share, form, fatigue, fouls, teammates, opponent | per-candidate rows, softmax |
| 4 | What | shot by zone (rim, paint, mid, corner 3, above-break 3), turnover, non-shooting foul drawn | his profile, late clock, trailing late, rim protection, 3PA allowed, form | multiclass |
| 5 | Shot result | make, miss, fouled-make (and-one), fouled-miss | his zone accuracy, defence, fatigue, period, form | multiclass |
| 6 | Assist / block | assisted? by which of four · blocked? by which of five | zone, shooter self-creation, passers, rim protectors | binary + per-candidate |
| 7 | Free throws | makes | FT%, situation | binary |
| 8 | Rebound | offensive/defensive → rebounder or team | miss zone, lineup size and rebounding rates | binary + per-candidate |
| 9 | Defender attribution | fouler, stealer | defender rates, matchups | per-candidate |
| 10 | Timeout | yes/no at a dead ball | scoring runs, clock, margin, team | binary |
| 11 | Substitutions | out / in | §4 | binary + per-candidate |

Family per node (decided by held-out log loss): **LightGBM** as primary; shrunk multinomial logit
baseline; TabPFN or a small multi-head network for low-data nodes. Choices over players use one row
per candidate, normalised across the candidates, so probabilities exist only for players on the floor.

## 7. Players and lineups as inputs

- Players enter as **point-in-time features** built only from games before the date: shrunk usage by
  event type, shot-zone profile and accuracy, FT%, assist/turnover/foul/rebound/steal/block rates,
  quarter usage shares, minutes and stint patterns.
- Lineups enter as aggregates of their five (usage sum, spacing, size, playmaking, rim protection)
  and as the actor's four teammates. This generalises to lineups never seen together (trades,
  injuries), which lineup IDs cannot.
- Team and coach features: pace preference, shot profile, rotation depth, defensive-scheme proxies
  (opponent rim and three-point rates); recency-weighted so coaching changes show quickly.

## 7a. Low-sample players — rookies and second-years (D5)

Players play to their role given their statistical profile, so a rookie such as AJ Dybantsa, or a
second-year player such as Cooper Flagg, is predicted as "a player with this profile, in this role, in
this lineup" rather than from a long personal history:

- **Stat-specific shrinkage** — each rate is a blend of the player's own data and a prior, weighted by how
  quickly that stat stabilises: usage, rebound, assist and block rates settle within a few hundred
  possessions; three-point accuracy needs many hundreds of attempts, so it leans on the prior far longer.
  FT% (fast to settle) informs the three-point prior as a shooting-touch indicator.
- **Archetype priors** — players are grouped by statistical profile (e.g. primary creator, secondary
  creator, 3-and-D wing, stretch big, rim-running big, bench guard), with height/position from the roster.
  The archetype supplies the prior where the player's own data is thin, and is itself a model input.
- **Relative role in the lineup** — usage rank and share among the five on court, creator/finisher roles
  relative to teammates. When the star sits, the young player's relative role and shot share rise
  automatically; the same mechanism handles trades and new lineups.
- **Talent uncertainty carried into the sims** — each world draws the player's underlying rates from his
  posterior (narrow for veterans, wide for rookies), on top of the night's form. Projections for
  low-sample players therefore show honest, wider ranges that tighten as games accumulate.
- Out of scope for v1: pre-NBA (college/international) translations; trajectory models for in-season
  development beyond recency weighting.

## 8. Training data

- Seasons 2022-23 to 2025-26 from sportsdataverse hoopR-nba-data (ESPN play-by-play, same athlete IDs
  as our feed), plus this season from our own collection; recency-weighted, with season as a feature
  for drift (rule changes, the rising three-point rate).
- Volume: ~4,900 games, ~1.2M segments, ~5M substitution-window player rows — minutes of LightGBM
  training on the laptop.
- Leakage control: every feature rebuilt point-in-time; models evaluated walk-forward.
- Quality gates: periods failing reconciliation (points, lineup seconds) are excluded from the nodes
  they would corrupt, and counted in the report.
- New dependencies at this stage: `lightgbm`, plus `pandas`/`pyarrow` to read the historical parquet.

## 9. Speed — 10,000 worlds per game

- Worlds advance together, one segment per step, with finished worlds masked; quarters are
  synchronised (every world plays Q1 to 0:00, then the break, then Q2) — the owner's "sim Q1, then Q2".
- The bottleneck is model inference: ~250 steps × several nodes × 10,000 rows. Estimates to confirm
  by benchmark: batched LightGBM in the loop ≈ 20–60 s per game; nodes distilled into lookup tables
  (binned logits or boosted GAMs) ≈ 2–5 s per game, pure NumPy indexing.
- Games (and, for the season, batches of games) run in parallel processes; seeded per (model, date,
  game), so results are identical for any number of workers.

**Expected timings on the laptop** (estimates; measured in M5):

| Nightly step | LightGBM in the loop | Distilled tables |
|---|---|---|
| Collect + parse yesterday's games | 2–5 min | same |
| Point-in-time player/team features | < 1 min | same |
| Refit the node models (~1–5M rows each) | 5–15 min, weekly by default | same |
| One game, 10,000 worlds (~60M model row-evaluations) | 20–60 s | 2–5 s |
| Near-term engine, next 7 days (~50 games, median 52) on 6 cores | 3–8 min | — |
| Season universes: long-range games + absence sampling (10,000 × ~930 games) | 1–3 min (vectorised NumPy) | — |
| **Nightly total** | **~10–25 min**; refit nights +5–15 min | — |

Budget: ≤ 60 min nightly end to end, ≤ 60 s for one game. Once trained, a run is mechanical: inputs
(lineups, state) → probabilities → sample → next state.

**Why no lookup tables.** A lookup table is the same model with its answers precomputed on a grid of
situations and rounded to its cells: averages survive, but unusual situations (a star-heavy closing
lineup down three with 40 seconds left) blur into their band. Running every remaining game through the
engine 10,000 times would need them (~10M games a night), but the two-horizon design (D13) does not: the
engine only plays the next seven days, and long-range games need team-level results, which a
team-strength model provides more simply and more honestly.

**Cadence (D11):** player/team features, injuries and availability update every night — that is
where yesterday's games enter (one night is ~0.2% of the training rows). Model weights refit when 7 or
more days have passed since the last successful refit (a day-of-month rule such as `day % 7 == 0` would
skip the 29th–31st and leave 9–10-day gaps, and a missed night would skip a refit), or on demand with
`--refit`. A refit is promoted only if it matches or beats the current model on recent held-out games;
the previous model stays as a fallback. A pre-tip refresh for late scratches is deferred (D12).

## 10. Evaluation and acceptance

- **Node level**: held-out log loss and reliability, overall and by period and state bucket, against
  the shrunk-rate baseline.
- **Game level** (walk-forward over retained slates): win log loss/Brier; total, margin and quarter
  CRPS; player CRPS and PIT for MIN/PTS/REB/AST/3PM; minutes coverage — against `baseline-v1` and
  market closing lines (retained in raw summaries).
- **Realism panel**: possessions and durations by start type, substitutions, stints, overtime rate,
  free-throw rate, three-point rate, garbage-time minutes.
- **Gate** to replace `baseline-v1` in the app: better game and player CRPS over the backtest, no
  calibration regression, every identity passing.

## 11. Outputs

- Today's contract (periods q1–q4/h1/h2/fg for teams and players), so the app needs no change.
- New: lineup minutes per team, and **"watch a sim"** logs — full event timelines for a few sampled
  worlds, for a 2K-style replay in the app (clock runs, events appear, the box score fills).

## 12. Two horizons and the season simulation (D13–D16)

The aim is sensitivity in the short term — lineups, injuries, game state — and an honest aggregation of
it into end-of-season standings.

**Near term — next 7 days (48 games from 19 Nov; median 52 per week, max 58).** The full engine, 10,000
sims per game, with every player and period output. The app shows everything for these games.

**Long range — the rest of the season (~930 games).** A team-strength model gives each game a margin and
total distribution from the two teams' strength *that night in that universe*. Strength comes from who is
available (sampled absences) and the universe's talent draws, aggregated through player values over the
likely rotation. It is calibrated to the engine: on each night's near-term games, its win probabilities,
mean margins and totals must match the engine's within tolerance. The app shows only win %, expected score
and spread for these games, labelled as a long-range estimate (D16).

**Season universes (D14, D17) — the per-world pathway, as in MusSim.** 10,000 universes; each plays every
remaining game once, in date order, so every season output has 10k granularity ("NYK finish 1st in the
East: 2.34%"). Each universe carries its own strength state per team, and that state is what makes worlds
diverge — a team can catch fire in one universe and collapse in another.

For each universe *k*:
1. **Ratings start from this season's real results.** Each team's long-range rating at the start of a world
   is today's Elo/ratings fit on real results to date (plus a draw at its uncertainty, calibrated below).
   This is separate from the possession models, which never take team strength as an input (D18).
2. **Days 1–7: the engine plays.** Universe *k* takes world *k* of each near-term engine sim. Inside the
   window each world plays a team's games in order, and after each game that world's player stats and
   form update from the simulated box score before the next game (D18). Each result also updates both
   teams' long-range ratings — so if the Heat win three of their next four in a world, they carry that into
   the rest of that world's season.
3. **Day 8 onward: the team model plays**, date by date: that night's availability in universe *k*
   (sampled absences, D15) → each team's strength = pathway strength + availability adjustment →
   expected margin and total (home court, rest, back-to-backs) → a sampled margin and total (game-level
   spread calibrated to the engine) → result → both teams update → next game.
4. **Update rule.** The update is the long-range rating estimator's own response to one more game with
   that margin (as MusSim reads it by refitting with one synthetic match), scaled by one gain. The surprise is
   measured against **the world's own expectation**, availability included, so it averages zero: favourites
   do not drift up and a loss without the star does not mark down the full-strength team.
5. **End of season.** Standings, tiebreakers and seeds per universe; probabilities are counts over the
   10,000 universes. A long-range game's win % in the app is the share of universes in which that team won
   it — path effects included.

**Calibration (as MusSim's dispersion work).** Walk-forward on 2022-23 to 2025-26: from several dates each
season, simulate the rest of the season and compare with what happened. One gain (and the start-draw
width) is chosen so that (a) dispersion — actual final wins against the simulated distribution — is ≈ 1.0,
neither too narrow (fixed strengths were 13% too narrow in football) nor too wide; (b) persistence — the
correlation of each team's surprise in the first and second halves of the remaining season — matches the
real one; (c) no fade unless the data asks for it. All computed per universe in vectorised NumPy, a game
day at a time: seconds, not minutes.

**Availability (D15).** Per universe and player, across every remaining date:
- reported injuries hold until their expected return, with uncertainty around the date;
- new injuries arrive at a per-game hazard from the player's (shrunk) historical games-missed rate, with
  durations from historical absence lengths — most short, some long;
- rest: back-to-back and load-management absences for players with that history.
The same model sets availability for near-term games two to seven days out, where today's injury report
says nothing yet. Realism check: simulated games played per star across the season against history (few
stars play all 82).

Phase 4 adds the actual NBA tiebreak procedure, the play-in tournament, the playoff bracket and the NBA
Cup-determined games once scheduled.

## 13. Milestones (each ends with checks)

| # | Milestone | Done when |
|---|---|---|
| M1 | History ingest + one play schema | Seasons load; per-season reconciliation report like `pbp_report.json` |
| M2 | Segment/possession parser + state | Points, seconds and possession-alternation identities pass; durations match §1 |
| M3 | Rotation dataset + replay-rotation baseline | Stints, dead-ball windows, rotation curves; replay keeps five on court |
| M4 | Node baselines + evaluation harness | Log loss and calibration per node, by period |
| M5 | LightGBM per node + speed benchmark | Each node beats its baseline; inference path chosen |
| M6a | Aggregation test with real rotations | Held-out real games replayed possession by possession with the real lineups and clock; simulated v actual box scores per player and stat: bias ≈ 0 by role tier (stars, starters, bench), 10–90% coverage ≈ 80%, CRPS better than a recent-averages baseline — proves per-possession accuracy aggregates before rotation modelling |
| M6 | Engine v1 (replay rotations) | End-to-end 10k sims in the current output contract |
| M7 | Target-aware substitution model | Minutes, stints and subs within realism bands |
| M8 | World form + end-game checks | Variance and overtime rate calibrated |
| M9 | Walk-forward backtest | Gate in §10 passed → app switches (labelled) |
| M10 | Watch-a-sim view | Replays render on phone and desktop |
| M11 | Availability model | Simulated games missed per player match history; reported return dates honoured |
| M12 | Season pathway + calibration | Dispersion ≈ 1.0 and real persistence on 2022-23 to 2025-26 walk-forward; 10k universes in the app |

## 14. Open questions for the owner

Settled 19 Nov: D1–D16 above. Nothing blocking; to confirm when convenient:

1. **Near-term window**: fixed at seven days (proposed), or a number of games per team?
2. **Long-range calibration tolerance**: proposed — on each night's near-term games, team-strength win
   probabilities within 3 percentage points of the engine's on average, and mean margins within 1 point.

## 15. Risks

| Risk | Mitigation |
|---|---|
| ~1% lineup glitches in play-by-play | Reconciliation gates per node; counted in reports |
| Unseen lineups after trades/injuries | Player-feature lineups, not lineup IDs |
| Rare end-game situations overfit | Rules for mechanics; pooled models; regularisation |
| Too-smooth simulations (variance too low) | Per-player form and talent draws, calibrated on held-out variance |
| Rookie/second-year projections overconfident | Stat-specific shrinkage, archetype priors, posterior talent draws |
| Runtime | Engine limited to the 7-day horizon; quarter-synchronised vectorisation; parallel games |
| Long-range model drifting from the engine | Nightly calibration against the near-term engine sims |
| Data-source change (ESPN unofficial) | Adapter boundary; raw retention; NBA Stats as an alternative |
