# MusNBA — game plan and progress

Updated **22 November 2026 (S01–S07 complete; Chunk A A1 at 70%, A2 at 30%; View Centre planned, D42–D43)**. The single record of scope, progress and decisions. Every agent updates it at
every checkpoint (AGENTS.md § Checkpoint protocol). New here? Read [AGENTS.md](AGENTS.md) first, then
[HANDOFF_NEXT.md](HANDOFF_NEXT.md) — it says exactly what to do next.

## 1. Goal

A local-first NBA simulator PWA, sibling to the owner's MusSim football app (`../Football`):

- **Today**: the slate. Tap a game for projected team and player outcomes — win %, team/total/spread lines, quarter
  and half lines, both lineups with each player's projected box score; tap a player for his full distributions.
- **Every projection = 10,000 simulated games**, possession by possession on a running game clock (2K-style), so
  quarter, half, game and player outcomes all come from the same simulated events.
- **Season**: 10,000 universes, each playing every remaining game once → standings, seeds, play-in/playoff odds.
- **Feedback loop**: real results and features update nightly. Weekly refit/promotion automation remains planned (D11);
  model changes require the measured gate. A season-to-date forecast replay is not implemented and is deferred (D40).
- Lineup-sensitive and game-state-aware; coaching tendencies learned from data, not hand-labelled.

**The daily flow — two engines (owner, 20 Nov; ENGINE_PLAN D26).** On any date D:
1. **Result** every game played before D.
2. **Play-by-play engine** — today's and tomorrow's games (if neither day has games, the next slate), possession by
   possession, with player profiles, form, roles, rotations and injuries carried over from every game before D.
3. **Team engine** — every later game, as MusSim: each world carries its own offensive and defensive rating per team,
   starting from today's estimate (plus its uncertainty), taking in that world's play-by-play results first, then
   updating after every simulated game in date order. March games use the ratings each world's own path produced —
   never today's ratings frozen.
4. **Season** outputs are counts over the worlds.

Each chunk of work should move one or both engines closer to a state the owner trusts against real outcomes — the
play-by-play engine by the backtest (M9), the team engine by the walk-forward season test (M12).

## 2. Principles (carried over from MusSim)

| Principle | How it applies here |
|---|---|
| Laptop pipeline, static PWA | Python collects, fits and simulates; phones browse imported results |
| Data-free shell | The hosted app has no data; data arrives as a `.musnba.gz` import from iCloud Drive |
| Serving never computes | `serve.py`, views and the PWA never fetch providers, fit or simulate |
| Retain raw responses | Provider responses kept gzip under `data/raw/`; finals immutable; history files with a sha256 manifest |
| Cutoff-safe | A snapshot for date D, and every training feature for a game on D, uses only games before D |
| Deterministic sims | Seeded per (model, date, game); identical inputs give identical outputs |
| Honest unknowns | Missing stays missing; placeholders say so; failed experiments are recorded |
| Measured choices | Every model choice decided on rolling validation folds; the final test stays untouched |
| Lean dependencies | NumPy, pandas, pyarrow, LightGBM — nothing else without a reason recorded here |
| Design language | MusSim tokens, panels and heat cells; both themes; 1440/960/390 widths; 44px touch targets |

## 3. Architecture

```
LIVE (nightly)   ESPN site API → fetch_espn → data/raw/espn → master_fixtures, box_scores, pbp
                 → engine v1.3 (10k worlds, today + tomorrow) + team pathway v1 (10k seasons)
                 → data/snapshots/<D> → views → serve / export / iCloud → public data-free PWA
HISTORY + MODEL  sportsdataverse ESPN season files → history (+ plays: one schema) → possessions (segments)
                 → rotations (stints, windows) → features (point-in-time profiles) → nodes (datasets)
                 → train (16 LightGBM nodes, F1–F4) → models/v1.3 → engine.py → M9 backtest
DEFERRED A1 S13 versioned daily archives + dated-input/dated-fit season replay → atomic active-history generation
```

Slates are US Eastern game dates; tip-offs show UK time with ET alongside.

## 4. Data sources

| Source | Use | Status |
|---|---|---|
| ESPN site API (no key) | Live: schedules, rosters, injuries, box scores, play-by-play with athlete ids, shot x/y, substitutions | In use (unofficial; adapter + raw retention) |
| sportsdataverse `sportsdataverse-data` releases (hoopR) | History 2022-23 → 2025-26: ESPN play-by-play and player box scores, same ids | In use (`scripts/history.py`) |
| NBA Stats API (stats.nba.com; own stdlib adapter, D32) | Real matchups (who guarded whom, partial possessions), season logs (minutes to the second, possessions), tracking defence, play-by-play v3, hustle | **In use (owner, D32)**: `fetch_nbastats.py` — Chrome fetch headers required (FINDINGS §1), ~1 request/s, resumable, raw retention `data/raw/nbastats/` (gzip + manifest); history 2022-23 → today backfilled once, nightly adds new finals (~10–15 requests); crosswalk 5,508/5,508 games, 99.986% of player-games (FINDINGS §3t) |
| ESPN `pickcenter` lines | Benchmark only (D8) | Retained in raw summaries |
| Projected starting lineups (D33) | Learned/projected starts and chance-to-play from permitted retained data | **Own projected starters in use**, scored nightly. External lineup-source search closed by D33: forbidden sources not scraped; no approved external lineup feed. A1 S07 audits ESPN report history and tests play/start learning where development coverage permits. |
| Basketball-Reference | Spot checks | Not a pipeline source |

## 5. Phases

| # | Phase | Progress |
|---|---|---|
| 0 | Discovery, data probe, plan | `██████████` done |
| 1 | App shell, season stats, placeholder projections | `██████████` done — public Pages/iCloud live; real iPhone install/import acceptance pending |
| 1b | Per-period Game Centre (owner spec), play-by-play parser, quarter-aware placeholder | `██████████` done |
| 2 | Possession engine (data → models → engine → backtest) | `████████░░` **M1–M5b, M6a done · engine v1.3 is the app's default (D34), 10,000 worlds per game (D36) · backtest (M9) is the gate · NBA Stats matchups ingested; real-matchup defence not promoted (D37): team differences remain compressed (pool-0 offence ~64%, defence ~40% of observed effect) — A1 S01–S07 complete** |
| 3 | Evaluation and nightly feedback (Forecast Lab view, refit cadence) | `███░░░░░░░` **Forecast Lab page (`#/lab`), nightly projected-v-actual starters record (D33); refit cadence not started; S11 confirmation remains future work, S13 historical replay deferred** |
| 4 | Season on the engine: pathway calibration, availability, tiebreakers, play-in, Cup, what-ifs | `██░░░░░░░░` **team pathway v1 in the app (D25): per-world ratings, engine worlds for today + tomorrow; walk-forward calibration first cut (M12); A1 S07/S10 extends availability and calibration** |
| 5 | Polish: hosting, iPhone acceptance, watch-a-sim, more views | `█████░░░░░` **Dashboard U1–U22 complete (22 Nov); personal GitHub Pages + iCloud flow follows MusSim; real iPhone acceptance and watch-a-sim remain** |

## 6. Phase 2 milestones — the current work

Design: [ENGINE_PLAN.md](ENGINE_PLAN.md) (decisions D1–D39). Training: [TRAINING_PLAN.md](TRAINING_PLAN.md).
This table is the milestone history/current status; **A1 dependencies in §6a define the next execution order**.
Each subtask ends with evidence, current docs and a commit/push checkpoint (AGENTS.md).

| # | Milestone | Status | Done when | Output |
|---|---|---|---|---|
| M1 | History ingest, one play schema | ✅ | Seasons reconcile with box scores | `plays.py`, `history.py` |
| M2 | Segments (possessions) | ✅ | Points, clock, alternation, lineups, possessions reconcile | `possessions.py` |
| M3 | Rotations + replay baseline | ✅ | Stints reconcile; replay backtest recorded | `rotations.py` |
| M4 | Profiles + harness + baselines | ✅ core | Point-in-time profiles; baselines on folds | `features.py`, `evaluate.py` |
| M5 | LightGBM per decision (16 nodes, D20 + D21) | ✅ **v1 tuned, validated, persisted, final test scored once** — every node ≥ its best baseline on every fold and on the final test; settings `models/v1.json`; FINDINGS §3h–§3h′ | Every node ≥ its best baseline on every fold, well calibrated; per-node choice recorded; models persisted | `nodes.py`, `train.py`, `compare.py`, `calibration.py` |
| M5b | Adapter parity: live ESPN v hoopR history | ✅ **adapters agree** (5 games, identical segments); ESPN's 2026-27 feed stamps every rebound at the miss's clock → one convention for all seasons (D23); timing distributions now match; foul/turnover/jump-ball shifts are real 2026-27 changes (FINDINGS §3k) | Same game through both adapters gives the same segments; season distributions match | `plays.py`, `possessions.py`, `parity.py` |
| M6a | Aggregation test with real rotations | ✅ **v1.1 on all 766 F4 games** (2026-27-style inputs): player bias ≤ ±1.5% for points/rebounds/assists/threes/steals/turnovers, CRPS lower than v1 on every stat but blocks, coverage 77–80% (FINDINGS §3k). Earlier v1 **gate met on all 766 F4 games** (player stats within ±1.3% for points/rebounds/assists/threes in every tier, coverage 77–81%, CRPS +6–11%; earlier 300-game run: team total −0.5%, coverage 77–83%); fouls traced to the in-season decline (day of season added); and-ones +5%, fouled-on-a-three −24% to trace) | Replayed held-out games: player box-score bias ≈ 0 by role tier, 80% coverage | `aggregate.py` |
| M6 | Engine and 10k output contract | ✅ **v1.3 serves today/tomorrow (D34/D36)**: 10,000 worlds, per-world target rotation tables; 13 games refreshed at dashboard close-out. Model accuracy remains under M9/A1, not declared solved | Same-world player/team/period outputs reconcile at 10k | `engine.py` |
| M6c | **D29 minutes** (healthy roles, 240 by priority, return ramp, per-world draws) | ✅ **engine v1.2 (20 Nov), kept in v1.3**: backtest on the same 200 F4 games — stars' minutes +6.5% → −1.0%, points +8.8% → +0.5%, minutes 10–90% coverage 58–63% → 77–84%, every player CRPS better or level (starters' minutes −18%, z −8.2); team sums level (FINDINGS §3p, §3r) | Minutes bias ≈ 0 by tier, coverage ≈ 80% | `minutes.py`, `engine.py` (`_target_tables`) |
| M6d | **D30 defence inputs (ESPN only)** | ✅ **engine v1.3 (20 Nov, D34)**: defence loading 0.44 → 0.69 (real 1.69), margin CRPS 9.67 → 9.37 (team model 9.32), total 12.00 → 11.72, players level or better; final test scored once (FINDINGS §3q, §3s) | Defence loading toward real; margins v the team model | `matchups.py`, `features.py --defence --matchup --shot-types`, `models/v1.3.json` |
| M6e | **D32 NBA Stats + defence on real matchups** | ✅ **ingest done; defence negative (D37)**: adapter, crosswalk (5,508/5,508 games, 99.986% player-games), reconciliation (points identical, minutes median gap 0 s, possessions +0.9), 1.04M matchup rows in ESPN ids, tracking defence per date retained; assignment on real shares top-1 36.4% → 50.2% (top-2 75%); defender traits (3PA share allowed r 0.77; 3P% allowed noise); three engine candidates (v1.4c/e/f) level or worse than v1.3 on the 200-game backtest — **v1.3 stays**; switch hunting not visible (D35, v1.4d not run); FINDINGS §3s′, §3t–§3w | Defence loading toward real; margin CRPS ≤ team model; no player tier worse | `fetch_nbastats.py`, `nbastats.py`, `realmatch.py`, `features.py --real-matchups` |
| M7 | Target-aware substitution model | ☐ **A1 S05/S06**: membership/role audit, then dead-ball game-state substitutions | Improve v1.3 minute CRPS and state response without tier regressions; five on court/seconds identities | Planned |
| M8 | Per-world form + end-game checks | ☐ **A1 S09**: latent talent, shared/player form, late-game mechanics | Better CRPS and joint calibration; OT/state realism against the matching held-out population | Planned |
| M9 | Walk-forward backtest and promotion | ◐ **v1.3 pool-0 control:** 200 F4 games, margin CRPS 9.415, total 11.723, win log loss 0.5738; team benchmark 9.322/11.353/0.5584. Known participants, projected starters. **A1 S01/S11** broadens confirmation and separates availability-aware tests | Player-first improvements and no material core regression across matched confirmation sets (TRAINING §8) | `backtest.py`, `backtest_compare.py` |
| M10 | Watch-a-sim view (owner, 20 Nov: nba.com-style play-by-play list first, then visual play-through) | ☐ | A saved world's events list and replay in the Game Centre, phone and desktop | `engine.py` event log, views, `game.mjs` |
| M11 | Availability model | ☐ **A1 S07/S08/S10**: report coverage, play/start probabilities, branches and future absences | Held-out calibration and games-missed realism where dated development data supports them; honest fallbacks otherwise | Planned |
| M12 | Season pathway calibration | ◐ **first cut (20 Nov): team pathway v1 in the app** — walk-forward 2022-26 (480 team-starts): dispersion 1.00 (fixed probabilities 1.53), 10–90% coverage 84% (65%), CRPS −4% in every held-out season; still wide in November (0.84) and surprises fade with the date (sim 0.52 → 0.18 v real 0.40 flat) | Dispersion ≈ 1.0 **at every start date**, persistence matches | `pathway.py`, `season_backtest.py` |
| UX | Dashboard upgrade programme U1–U22 | ✅ **22 Nov:** all 22 shipped; U15–U22 adds roster roles, playoff picture, win ranges, races/movers/leaders inside Standings and model guide; 156 full + 12 final layout browser checks, hosted PWA 15/15 | Checked at 1440/960/390, both themes, stored data only | DASHBOARD_PLAN.md |
| A1 | Expanded accuracy/robustness programme | ◐ **58.0% — S01–S07 complete, 22 Nov**; Chunk A A1 contract frozen, original S08 still open | Gates in §6b; S13 history deferred (D40); integrated S14 remains open | HANDOFF § Progress ladders |

### 6a. Next chunk — A1: player accuracy, defence and trustworthy season paths

**Owner request, 22 Nov:** the earlier planning-only stop was lifted for overnight A1 execution, then D41 stopped
that session after the nightly. The owner has now authorised the two remaining chunks in order. U1–U22 are complete; do not restart
that programme. This replaces the old four-task S1–S4 chunk with **14 modular subtasks (3.5× the task count)** and
substantially more modelling scope: M7, M8, M11, M12, full-fold confirmation and versioned daily history and season-to-date model rebuilds.
This is not a claim of 3.5× runtime or a promised accuracy gain. All subtasks started at **0%**; live progress is in HANDOFF.

**Two headliners:** (1) player outcomes that respond correctly to role, availability, game state and the defenders
actually faced; (2) calibrated joint game/season outcomes. Historical forecast backfill is deferred (D40).
**Defence is central, not abandoned.** D37 rejected three particular variants; it did not show that
better defence is impossible. We will identify the loss of signal, then test different mechanisms with controlled
ablations. Player/lineup defence remains the design (D35); no team-rating input or post-hoc score scaling in the
possession engine. The team model remains a benchmark and the later-season engine.

The table defines scope and dependencies. **HANDOFF_NEXT.md § Progress ladders is the single live progress ledger**:
weights sum to 100; each subtask has ten explicit done-when steps. A task is complete only with evidence, a decision,
current docs, any necessary PWA delivery and a committed/pushed checkpoint. A well-tested negative result counts as completed research; merely
trying an idea or leaving a run underway does not. Data-limited work must deliver its coverage audit, safe fallback,
remaining gate and next action rather than claim a fitted model is validated.

**D42 split, now authorised for execution in order:** retain S01–S07 as completed and the original A1 weights/ladder below as the
historical ledger (**58.0%**, S13 deferred). The new separately weighted chunks and their 60 concrete rungs are in
HANDOFF § Execution; Chunk A A1 is at 70%, and Chunk B has not started. Chunk A targets believable lineup-aware games, shared form and
late-game behaviour, plus five saved game examples; Chunk B tests a new player/lineup-defence mechanism, legal
foul-outs, season calibration and integrated confirmation, and adds rotation visibility. Each has a fresh final
nightly and a useful shipped dashboard improvement if no model passes the unchanged gate. Chunk A can promote an
independently confirmed candidate without pretending S11's later combined season assessment is complete.
No historical forecast backfill is reauthorised. Keep current batch iCloud export until incremental delivery is
separately built and tested.

For each game, the planned five selections are: maximum own score margin for each team (even if all worlds lose);
the actual world closest to
Expected; and each team's highest single-player fantasy-score world. They are illustrative selected worlds, not
five independently likely outcomes; one world may satisfy multiple labels. Retain real, reconciled events rather
than a fabricated average, and specify selection/seed/version provenance, phone size and offline fallbacks before
implementation. See DASHBOARD_PLAN and HANDOFF for the contract and delivery gates.

**D43 View Centre:** Chunk A's five-world playback is an overhead 2-D basketball court, event overlays,
score/clock/live box and an interactive timeline with smooth play, pause, speed and seek. It reads stored or locally
opened, validated play-by-play files; it never simulates in the viewer. Build the player against a source-neutral
event interface so a later adapter can replay resulted games from retained play-by-play without mixing actuals
with forecasts. Actual-game playback is future work, not a forecast-history backfill. The current model produces
shot zones/distance bands, not tracked player/ball coordinates: display only supported spatial evidence and label
any illustrative animation. HANDOFF specifies provenance, deterministic capture, reconciliation, missing-data,
accessibility and phone/offline gates.

| ID | Subtask | Weight | Depends on | Concrete deliverable and completion evidence |
|---|---|---:|---|---|
| S01 | Reproducible baseline and evaluation contract | 6% | — | Freeze pool-0 v1.3 controls, game IDs, seeds, metrics, player tiers, exclusion rules and practical regression margins. Audit known-availability assumptions; create a separate pre-game-input evaluation track. Record paired uncertainty and simulation noise. Done when a manifest can reproduce the control and the promotion rules are fixed before candidates. |
| S02 | Data integrity and train/serve parity | 6% | S01 | Resume the authorised NBA pbp history in one polite stream; reconcile each retained season, quarantine irreparable rows and enumerate gaps. Audit cutoff joins, DNP/zero-minute handling, substitutions, matchup duplication and tracking-defence coverage. Produce fold-safe feature inputs and meaningful corruption/leakage checks. No automatic replacement of ESPN or unrequested new source. |
| S03 | Locate lost offence and defence signal | 8% | S01–S02 | On matched games, compare M6a real-state replay with free-running simulation; trace shooting, shot mix, foul/FTA, rebound and turnover effects through profiles, node outputs, lineup aggregation and minutes. Measure own-offence/opponent-defence loadings with uncertainty. Explain the +0.4–1.0 total-bias increase in rejected variants; choose the next mechanisms from this evidence. Teacher-forced M6a is a diagnostic, not a forecast. |
| S04 | Player-based defence and shot-quality improvements | 12% | S03 | Test profile reliability/shrinkage and model expression first, then shot-type/self-creation, deterrence, likely defender/help-at-rim, foul-drawing and rebound competition where S03 supports them. Parse retained tracking defence only with date-safe coverage; isolate its incremental value. Retrain assignment/priors inside each fold. At least two distinct mechanism families get controlled tests; only survivors get full backtests. No repeat of v1.4c/e/f unchanged, and no assumption that individual 3P% allowed is reliable. Done with ablation results and retained/rejected candidate specs. |
| S05 | Healthy roles, rotation membership and minute allocation | 8% | S01–S02 | Generalise the Richardson-style season-minutes→tiny-projection issue: distinguish active roster, chance to enter the rotation, minutes conditional on playing, starts, healthy role and return ramp. Audit recent trades, low samples, DNP-CD and absent teammates. Test an allocator/membership correction against D29 by tier and situation, with exact team-minute accounting and honest unconditional distributions. |
| S06 | M7 substitutions that react to the game | 12% | S05; S02 | Build dead-ball out/in examples with score, time, foul count, stint/rest and target deficit; learn from legal opportunities, including no-sub windows. Integrate a soft pull to S05 targets, forced foul-outs and legal lineups. Validate blowout/close and foul-trouble minutes by tier, stints, quarter shares and CRPS on held-out games. Preserve the old rotation path as control/fallback; never force every player's realised minutes back onto his target. |
| S07 | Availability, projected starters and future absences | 6% | S02, S05 | Audit timestamped ESPN injury-report history first; fit status→play/start only where the pre-tip population supports it. Test DNP/rest/return-duration models on historical sequences for M11. Report Brier/log loss/calibration and games-missed distributions, with cold-start fallbacks. Sparse current report history is a coverage limitation, not permission to fabricate old reports or tune on the final test. |
| S08 | Lineup branches and coherent Expected projections | 6% | S05–S07 | Implement D31 locally: 10,000 worlds per explicit branch; minutes and matchups re-solved per roster. For up to two maybes, store complete branch probabilities and an Expected mixture reused by the season engine. Verify mixture accounting and deterministic branch seeds; assess independence assumptions where data allows. More-than-two one-out comparisons stay explicitly non-exhaustive. Phone exports keep Expected only (D36). |
| S09 | M8 shared form, talent uncertainty and end-game behaviour | 10% | S04, S06; S08 for integration | Estimate residual player/team covariance after minutes/roles; distinguish persistent low-sample talent uncertainty from game-night form. Test player usage/efficiency/shot-selection draws and shared pace/shooting effects without double-counting variance or shifting unconditional means. Audit intentional fouling, clock use, late shot selection and OT on held-out states. Require better CRPS/calibration, realistic teammate/opponent dependence and preserved identities, not just wider intervals. |
| S10 | M12 season strength, persistence and availability | 8% | S07, S09 | Test carry-over/opponent-adjusted starting ratings, update memory/drift and future absence paths against pathway v1. Keep per-world rating updates centred on that world's expectation and consume the actual near-term Expected worlds. Leave-one-season-out selection over the 16 historical season/start combinations; report CRPS, dispersion, coverage and persistence at each start date. Correct schedule/Cup accounting before comparison if needed; do not calibrate away a schedule error. |
| S11 | Integrated confirmation and promotion decision | 5% | S04–S10 | Compare each retained component and their combination with v1.3/pathway v1. Screen on the fixed 200 F4 games; confirm the frozen candidate on all eligible F4 games and fixed samples from F1–F3, with matched controls. Keep actual-availability and pre-game-availability results separate. Run a second seed and a 10k-world subset, stress/identity/cutoff/runtime checks. Promote only what passes; freeze the recipe before a single final-test score. Preserve fallbacks, refresh/export the accepted model to the PWA and explain rejected components. |
| S12 | Make the model behaviour visible | 3% | S06, S08, S11 | Stored rotation probabilities (sum to five), a rotation-map view and five sampled-world event logs with a compact watch-a-sim list. Branch/availability and as-of labels must match stored evidence. Inspect 1440/960/390 in both themes; keep phone data small and Scenarios/branches local. If no model promotes, this is the useful dashboard improvement required at close-out. Face cards and unrelated polish remain backlog, not substitutes for model tests. |
| S13 | Current-model season history and daily archives | 5% | S11; S12 labels | **Deferred, not completed or credited, by owner D40:** do not implement or run historical forecast backfill in this A1 execution. Preserve existing forecasts and archives; the former versioned-replay and cutoff contract remains in ENGINE_PLAN §17 for any future reauthorisation. The original weight and ladder remain unchanged. |
| S14 | Fresh nightly, delivery and successor chunk | 5% | S01–S13 decided | Run the final live nightly on the best promoted engines, 10k game/branch worlds and 10k seasons, with authorised fetch/input rebuild and iCloud export. Verify smoke/fault, dashboard and hosted PWA, visible bundle and archives. Write the next evidence-led chunk in this same format before final commit/push; leave exact first commands, ten-step ladders, weights and run gates for the next agent. |

**Execution order:** follow the dependency column, normally S01→S14. S02's download may run while CPU work runs, but
pause it for nightly provider fetches. Only one engine backtest at a time (measured CPU oversubscription). Every run
has a retained log and deterministic resume information. Do not launch speculative full grids: S03 selects two or
three plausible levers; screen cheaply, reject poor candidates, then broaden confirmation for survivors. Dependencies
mean documented decisions, not mandatory promotion of every module; a rejected component leaves its control in place.

**S03 → S04 candidate matrix (frozen, not promoted):**

| Family | Evidence and predicted effect | Disconfirmation / required control |
|---|---|---|
| Rim matchup-expression calibration | Rim quartiles show more observed than predicted spread; training-tail calibration may express existing player/lineup signal without changing mean predicted make rate | Reject on paired fold shot loss or player-first engine gates; same baseline, games, seeds and strictly prior fold fits |
| Incremental tracking defence | Independent cross-half profile and source-coverage audits motivate testing defended-shot information through the defensive five | Reject unsafe/missing joins, lack of independent paired fold gain or failed player/team gates; do not relabel old v1.4e |

Both observations are descriptive; F4 suggested the hypotheses and cannot serve as sole independent confirmation.
FINDINGS §6b records uncertainty and TRAINING_PLAN §8 fixes the test protocol and provenance limitations.

**Larger scope, unchanged floor:** the chunk may span sessions. Each S completion earns a high-level owner summary:
what changed/was added, what the measured result was, what remains, commit and push status. No execution begins in the
22 Nov planning session. The standing rule is **commit and push**, not an optional push, at each completed S checkpoint.

### 6b. What earns promotion, and what “really happy” means

**Reference control:** `20261120T162930Z_v1.3_pool_per_world_F4` (200 F4 games, 1,000 worlds, known participants,
projected starters, rotation targets, pool 0): margin CRPS **9.415**, total CRPS **11.723**, total bias **+1.81**,
win log loss **0.5738**, total coverage **69%**, margin coverage **75.5%**. Offence loading **0.727/1.144 = 63.5%**
of observed; defence **0.678/1.685 = 40.2%**. Same-game team benchmark: **9.322 / 11.353 / 0.5584** for margin
CRPS / total CRPS / win log loss. Earlier 9.374 margin CRPS used a shared rotation pool: compare like with like.
Source: FINDINGS §6 and the saved control, not newly measured model performance.

**Ambitions, not promises or substitutes for the gate:** materially lower player errors (aim ≥5% minutes CRPS,
≥2% points/rebounds/assists CRPS in the affected sufficiently populated tiers), beat the team benchmark on game
CRPS and win log loss, bring 10–90% coverage toward 80% without inflating errors, and improve pathway v1 at each
start date. Team-strength regression loadings are diagnostic; their targets are the same population's observed
coefficients, not universally 1. These ambitions never justify player regressions or fitting to market lines.

Before any candidate, S01 records primary outcomes, sample counts and game-clustered uncertainty, practical
non-inferiority margins, seed noise and comparison families. TRAINING_PLAN §8 is the detailed gate:

1. **Player first.** Minutes and PTS/REB/AST/3PM CRPS, bias and coverage by pre-game role tier; low-sample, returning,
   fringe/DNP and foul/blowout groups where counts permit. A claimed improvement must beat noise on its prespecified
   primary outcome. All other required tiers/stats need non-inferiority evidence; “not statistically significant”
   alone is not evidence of no harm. Sparse groups stay labelled inconclusive.
2. **Then team and joint outcomes.** Paired margin/total/quarter CRPS, win log loss/Brier, calibration, conditional
   minute response, component expression and joint dependence; no material regression on core game outcomes.
   Evaluate combined changes as well as isolated ablations. Keep end-to-end availability tests separate from oracle
   availability diagnostics and teacher-forced aggregation.
3. **Generalisation and mechanics.** All-fold node evidence; whole-game confirmation across F1–F4; per-season/start
   pathway evidence; second-seed and 10k-world subset; exact five-player/seconds/points/mixture identities, leakage
   rejection, deterministic reruns, short rosters/OT/missing-data stress cases and measured runtime within D10.
   No promotion merely because the old 200-game development panel improved after many tries.
4. **Freeze, then final score once.** A release manifest names every retained/rejected component, feature/parser
   revision, training cutoff and hash. Only the frozen selected recipe is fitted/scored via `--final`; record one
   final-test evaluation per version. Do not tune on its results or rename a candidate to retry the final test.
   A failure can block release; further development returns to the historical folds and documents the failure.

**D40 supersedes the mandatory history work below for this A1 execution:** the owner wants the current nightly for
today and tomorrow, not a forecast backfill. S13 is deferred without progress credit; existing forecasts/archives
remain untouched. The following D39 design and safety requirements apply only if historical replay is reauthorised.

**Earlier D39 current-model history design.** Save each day's Today forecast;
Tomorrow is a dated preview. With a new accepted model, support rerunning the nightly from the season's first slate
through the latest completed ET date, then show that version's history throughout the default dashboard. This
supersedes the earlier small gap-fill plan. The owner expects to do this with each new model: make it a normal,
resumable workflow, not an ad-hoc script. Never silently mix model versions in a historical series or scorecard.

Keep the original live forecasts and old-version generations immutable in the archive. A current-version rebuild
is labelled a retrospective reconstruction, generated now using the current recipe and inputs available at each
origin; it is not claimed to have been published before those games. Within an active version, results join its
stored predictions; ordinary browsing never reruns the model. Freeze a first successful pre-tip Today forecast per
origin/game/run policy, keep same-day revisions explicit, and distinguish an earlier Tomorrow preview when no Today
forecast exists. ENGINE_PLAN §17 defines the storage/activation/provenance contract.

**Season-rebuild gate:** S11 must freeze a model that passes the player/game/season acceptance rules; S13 must prove
all inputs **and fitted parameters** precede each historical origin, deterministic resume, honest injury/roster
coverage and preservation of earlier generations. Models fitted through 2026-06-30 can cover the current 2026-27
season if all auxiliary fits are also safe. A later refit using current-season games cannot be reused on earlier
dates: use dated fits of the same recipe. A recipe selected with later development knowledge remains retrospective.
Fix the range from the actual season schedule before inspecting outcomes; run all eligible slate origins, logging
missing/unsupported dates rather than skipping poor predictions. Start with development-date safety tests, then
complete the selected version's season rebuild when the gate passes. Do not tune or repeatedly score the final test
from its reconstructed results. If no model promotes, keep the existing serving version; S13 still delivers and
tests the versioned runner, records whether a v1.3 reconstruction is justified, and carries any incomplete full run
as explicit work, never as a completed rebuild. A failing model/cutoff/coverage gate defers production reconstruction.

**Final live refresh:** S14 always runs `.venv/bin/python scripts/nightly_musnba.py` after the model decisions,
pauses history fetching first, and verifies today/tomorrow (or next slate) plus a new 10,000-world
season. Use `--offline --no-rebuild` only if retained inputs are current and unchanged, with the reason logged;
never use it to bypass rebuilding inputs after feature/parser/model changes. Include every explicit D31 branch
at 10k worlds when branches are implemented. Archive replaced artifacts. Source commits go to `main`; a changed
static shell is published to `gh-pages` only, data remains local/iCloud. Check imports after bundle changes.

### 6c. Checkpoints, handover and the successor chunk

At every completed S subtask **and every D42 A/B module**, update the live handoff and affected docs before
committing, then review, **commit and push before starting the next module** (no data). Keep the live log current
as evidence arrives, not only at chunk end. Record the checkpoint and remote status in HANDOFF's ledger at the next checkpoint, or use a named
checkpoint marker resolved by `git log` to avoid self-referential hashes. The completion summary includes the
measured outcome and whether the production model changed. Every partial-session stop also checkpoints resumable
state: exact command, log/output paths, PID if running, work completed, next rung, blockers and candidate status.
A scientific rejection closes the task only after its planned evidence and fallback decision are written.

**PWA obligation at each affected S checkpoint (owner, 22 Nov):** model promotion or changed stored forecast outputs
requires the necessary accepted-model refresh and iCloud export, with version/cutoff/world metadata and import/offline
verification. A changed app shell is rebuilt and published data-free to `gh-pages`, with service-worker compatibility
checked. Presentation/export-only changes can reuse current completed forecasts; research-only candidates leave the
served model/bundle unchanged. Future S11 delivers any promoted model and S12 its shipped app/output changes;
S13 is deferred (D40), and S14 repeats final delivery after its fresh nightly. Until a new
history is complete, clearly identify older historical generations rather than imply they use the new model. Log
bundle bytes/records/hash/version, shell revision where changed and checks; tell the owner to import the new bundle
on each device. Never equate export success with confirmed phone import.

HANDOFF owns live progress/next actions; PLAN owns scope/status/log; ENGINE_PLAN owns decisions/design;
TRAINING_PLAN owns experiments/promotion/cutoffs; FINDINGS owns measured evidence with populations and negative
results; DASHBOARD_PLAN owns shipped app behaviour; README owns runnable commands and public/PWA workflow.
Review all eight at each checkpoint, editing the affected ones and explicitly recording “no change” for the rest.
Do not present a proposal, planned script or candidate as shipped. Preserve useful historical findings; remove stale
instructions and duplicate active ladders. Documentation is the authoritative handover, not a chat recollection.

**S14 cannot finish without a constructed successor chunk.** Use the results just obtained to name one or two
headliners and modular IDs with dependencies, weights summing to 100%, ten done-when rungs per task, acceptance and
fallback rules, starting commands, evidence/artifact paths and the final nightly requirement. Prioritise unresolved
accuracy gaps, not a speculative wishlist. Archive A1's completion ledger in PLAN, make the successor the active
0% ladder in HANDOFF, and give its first open action. Include this same successor-construction requirement in it.
If the owner asks to stop earlier, finish that stop point and leave partial tasks honestly unfinished.

**Planning-only checkpoint exception (owner, 22 Nov):** this documentation session does not run experiments, fetches,
training, a nightly or historical reconstruction. Baseline smoke and documentation checks are enough; retain the
last successful live refresh. This does not waive S14's nightly at the end of actual engine development.

## 7. Phase 1 record (done)

- [x] Collection, master fixtures, box scores, cutoff-safe stats, placeholder engine (`baseline-v1`), snapshots, views
- [x] Local server (:8766); app: Today, Game Centre (bezel, Q1–FG, Player/Team, Matchup, player sheet), Standings
      (forecast, seeds, ratings), Teams, Players, Search; static PWA with checksum-verified import and offline cache
- [x] Verification: smoke, browser (39 checks over 18 views × 3 widths × 2 themes), PWA import/offline (8 checks)
- [x] Public GitHub repo and Pages live; iCloud export delivered and visible on phone (22 Nov).
- [ ] Owner: real iPhone install/import acceptance. Automated hosted import/offline checks passed 15/15.

## 8. Contracts

| Artifact | Contract |
|---|---|
| `data/raw/espn/final/<game>.json.gz` | Final-game summary; written once |
| `data/raw/espn/runs/<UTC>/…` | Volatile responses per collection run |
| `data/raw/hoopr/*.parquet` + `manifest.json` | Unmodified history files with url, bytes, sha256 |
| `data/master_fixtures.csv` | One row per scheduled game (live season) |
| `data/derived/history/<season>/segments.parquet` | One row per segment (M2); `game_ok` marks reconciled games |
| `data/derived/history/<season>/{stints,windows,subs,on_court}.parquet` | Rotations (M3) |
| `data/derived/features/pregame.parquet` | One row per player-game: profile as of tip-off (M4) |
| `analysis/experiments/<UTC>_<name>.json` | Every experiment run: configuration, folds, per-node metrics, commit |
| `data/derived/experiments/<UTC>_<name>.npz` | Per-row held-out log losses of a run (paired comparisons) |
| `data/derived/features/team_pregame.parquet` | One row per team-game: team style as of tip-off, rest, day of season |
| `data/derived/nodes/<key>/<node>.npz` | Cached datasets per decision (folder = hash of code + inputs) |
| `models/<version>.json` | A model version's settings and the fold run that validated it (in git) |
| `data/models/<version>/` | Fitted LightGBM files + `config.json` (inputs, temperatures, final-test scores) |
| `data/snapshots/<D>/` | Current daily snapshots (meta/games/season/stats); replacements archived. S13 versioned active-generation history is not implemented and is deferred (D40) |
| `data/views/api/**.json` | API-ready presentation; rebuildable without simulation |
| `MusNBA.musnba.gz` | gzip NDJSON bundle for the PWA |

## 9. Open decisions for the owner

1. NBA Stats API via `nba_api` (browser-style headers) — allow, or stay on ESPN only? **Owner (20 Nov): stay on ESPN and take
   implicit matchups as far as possible (D30); revisit only if the backtest's defence loading stalls short of real.**
   **Owner (20 Nov, later): go with the NBA Stats API (D32)** — ESPN credits identify matchups only weakly (FINDINGS §3q);
   ingest/crosswalk/reconciliation are complete; three real-matchup engine variants were rejected (D37). A1 S03/S04 now targets the remaining defence gap with diagnosed mechanisms. What it
   would add: per-game matchups (partial possessions each defender spent on each attacker, with points and shots),
   shooting by closest-defender distance (player-season aggregates, not per shot), touches/drives/speed, hustle stats
   (contests, deflections). Why it is not simple: stats.nba.com returns 403 to plain requests (measured 19 Nov) and answers
   only requests imitating a browser on nba.com — unofficial use, hence the owner's sign-off; different player and game ids
   (a crosswalk by name, team and date); endpoints that change or rate-limit (a second adapter with raw retention). ESPN
   already gives shooter/assister/blocker/fouler/stealer, shot x/y, the ten on court and shot type in the play text — not
   who guarded whom or defender distance.
**Phone app (owner, 20 Nov, D36; laptop clarification D45):** stripped back — 10,000-world distributions for the expected lineup (players, teams, periods);
   no Scenarios, Given…, joint grids, duels or lineup branches. The laptop PWA retains saved worlds and existing world-based views;
   lineup branches remain planned, not implemented.
2. **Decided (owner, 22 Nov):** make `MusaMoholo/MusNBA` public and copy MusSim’s personal GitHub Pages/iCloud flow.
   Only the data-free shell is published on `gh-pages`; simulations stay local/iCloud. App name MusNBA. **Live:** https://musamoholo.github.io/MusNBA/ (22 Nov; `gh-pages` f2932e1).
3. iPhone acceptance of the PWA.
4. ~~Player heights/weights~~ — **owner (19 Nov): needed** ("size and defence are important"): a polite ESPN athlete
   fetch (~1,000 players, one request each) for height and weight, then **archetype priors** — players clustered by
   role, style and size; every rate shrinks toward the player's archetype instead of his position group; rookies
   start from the archetype matched by position, size and draft slot (D5: no college data).

5. **Owner (19 Nov, late):** the engine projects **today and tomorrow, always** (D24, replaces the seven-day window), and the
   season sim should then play every later game with **per-world team ratings, MusSim-style** (D25) — left as future work
   at the owner's request; **built 20 Nov** (team pathway v1, D25–D27).

6. ~~Engine v team model for today's win %~~ — **owner (20 Nov, D28): players first.** The engine stays the default; team results follow from perfecting player outcomes (minutes, performance, defenders faced); the team model is only a yardstick.

### 9b. Dashboard UX backlog (owner, 20 Nov) — headliners for chunks that cannot improve an engine

**Done 20 Nov:** item 2 first cut — joint and conditional outcomes (Scenarios tab, Given…, joint grids, drivers, averages
deltas; DASHBOARD_PLAN). Owner: the Lab page is not a dashboard-user priority.

1. **Watch a sim, 2K-style** (M10, extends D9): a saved world played through time on an aerial view of the court — shots
   placed where they were taken (zone, distance band, side), makes and misses, the clock running, the box score filling;
   after the nba.com-style play-by-play list. Needs the engine's event log (five worlds per game) and shot coordinates
   sampled within the band for display. A1 S12 builds the event-list/rotation-map foundation; court playback remains later.
2. **More depth on game outcomes** (owner, 22 Nov): histograms need not be the only visualisation; creatively show
   more signal from the 10k simulations, using percentile bands, exceedance curves and joint/conditional views where
   saved data support them. Keep distributions and denominators honest, avoid presenting extreme examples as typical,
   and respect laptop/phone world availability. Existing lines, ladders, joint outcomes and game-flow fans remain.
3. **Competition tabs**: NBA regular season · **NBA Cup** · **NBA playoffs** — the playoffs tab seeds the bracket from the
   standings as they are expected to finish (per simulated season) and plays the play-in and every round per world,
   MusSim cup-style (bracket probabilities by round).

4. **Lineup what-ifs** (owner, 20 Nov; D31): the nightly plays games with an uncertain high-impact player once per lineup
   scenario (X plays / X sits) and the Game Centre offers a lineup selector; later a localhost **lineup editor** (default
   expected lineup and minutes; change who plays and their minutes → minutes re-solved to 240 (D29), matchups re-formed
   (D30)) through a separate what-if runner. A1 S08 adds stored branches on localhost; phone exports keep Expected only (D36).

5. **Incremental iCloud delivery** (owner suggestion, 22 Nov): consider publishing each finished game atomically
   during a nightly, with a generation manifest and validated resume. Keep partial and complete generations visibly
   distinct and retain the previous complete bundle; PWA import/offline support must understand the new contract.
   iCloud sync alone does not import data on the phone. This is future work: the delivered nightly and subsequent
   nightlies still export both bundles at the end until incremental delivery is implemented and verified.

6. **Player usage and advanced game stats** (owner suggestions, 22 Nov): expose honestly defined player usage,
   on-court +/−, offensive and defensive rating, Box Plus/Minus and other supported advanced stats, with
   simulated-game distributions where meaningful. Existing model input is player uses per offensive segment while
   on court, not necessarily conventional possession-based USG%. Reconcile scoring and the on-court possession
   denominator against play-by-play, including substitutions, offensive-rebound continuations and free throws;
   disclose zero-exposure/absent worlds and match historical and forecast definitions. On-court ratings describe
   team outcomes with the player on the floor, not causal individual impact. Box Plus/Minus is a modelled estimate,
   distinct from game +/−; validate and label its definition rather than inventing it. **Partial delivery:** six
   box-derived player rates, 15 team metrics per side (including explicitly box-estimated ratings), actual full-game
   +/− and a clearly labelled, dated action-share profile now appear where retained data support them. Projected
   rates now have per-world distributions with explicit undefined counts; unavailable periods are labelled, never
   substituted with ratios of means. True per-world USG%, on-court ratings and BPM remain unimplemented. The next
   normal nightly rebuilds these summaries; no nightly is needed yet for this presentation work. Nightlies are
   mainly for major improvements (owner, 22 Nov).

7. **Dashboard house design** (owner, 22 Nov): keep as much supported information accessible and interactive as
   possible without overcrowding. Reorder around the important game/player signals and use clearly labelled
   collapsible groups for secondary details; preserve controls, truthfulness and laptop/phone responsive behaviour.
   Carry this across the dashboard as the authorised chunks proceed.

### 9c. Realism sweep — current mapping to A1 (updated 22 Nov)

1. ~~Live v history adapter skew~~ — M5b done: ESPN's 2026-27 rebound stamp; one convention (D23); v1.1 promoted.
2. Minutes: target-aware substitutions (blowouts, foul trouble, fatigue, closing lineups) — M7; the biggest risk.
3. **Size and archetype priors** (owner: low-sample players borrow from similar players' profiles) — heights/weights fetched
   (935 players); first ablation negative (low-sample players do not gain; FINDINGS §3l); location node gains — next test.
4. **Player/lineup defensive impact** — v1.3 already models on-court shooting suppression and likely defenders.
   The pool-0 control expresses about **40%** of observed defence loading (0.678 v 1.685), not the old v1.1 25%.
   Real-matchup variants did not improve game scores; A1 S03/S04 traces compression and tests new mechanisms rather
   than abandoning defence or repeating the same inputs (FINDINGS §3s–§3w, §6).
5. Timeouts (after-timeout plays, late-game advance), end-of-period heaves, technical/flagrant free throws,
   goaltending, lane violations — rules or small nodes in M6/M8.
6. End-game behaviour (deliberate fouling, two-for-ones, last-shot holds), per-world form, overtime rate — M8.
7. NBA Stats is authorised/ingested. Retained tracking defence needs safe date joins and ablation (A1 S02/S04);
   no new source is assumed. Face cards remain a future presentation task, using retained ESPN assets if implemented.

## 10. Log

- **22 Nov 2026 · D46:** owner narrowed lineup branching to the highest-impact uncertain player per team, only
  within its top three; at most four exhaustive combinations. Freeze and label the pre-origin offensive proxy in
  ENGINE_PLAN; earlier >2 sensitivities remain historical research, not the new design. Current production unchanged.
  Planned presentation: one shared lineup control across game/team/player views, compact comparisons and gated
  Expected default; details in DASHBOARD_PLAN.
- **22 Nov 2026 · D47:** owner requested a five-level 0/25/50/75/100% lineup-certainty signal. Test the
  prospective candidate consistently across selected and other uncertain players; retain the unrounded
  assumptions and sources, preserve uncertain endpoints, and do not claim calibration or change serving before
  its gates. The interrupted pre-D47 capture is wiring evidence.
- **22 Nov 2026 · D48:** owner proposed generally replacing isolated random-world failures until 10,000 valid
  worlds exist. Test deterministic isolation, counted/capped retries and conditional-sampling bias against the
  S06 foul-penalty candidate; missing/corrupt inputs, cutoff/accounting defects and unknown or systematic failures
  still fail. No player is silently reactivated and no production behaviour changed.
- **22 Nov 2026 · Chunk A A1 40%:** isolated D47 one-/two-player cases completed **20,000 / 40,000** worlds,
  exact weights and independent saved-world accounting; four/eight-thread replays matched every array and
  capture hash. **77** focused tests, smoke **108/108**, deliberate fault **86/108**. A prior 10k short-roster
  failure remains explicit; no candidate or bundle promoted. Chunk A **22.5%**; next is exact Expected mixtures.
- **22 Nov 2026 · Chunk A A1 50%:** isolated exact mixtures independently reconcile **40k / 20k / 40k** saved
  worlds and **90 / 88 / 209** bins; the **1/20,000** counterexample and per-world undefined rates are preserved.
  **32** focused tests pass. No model/bundle changed; Chunk A **25.5%**, next is the exact season identity.
- **22 Nov 2026 · Chunk A A1 60%:** independent replay verified **17** complete score-vector marginals and
  per-path results, **959** game win probabilities and **30** teams' win/seed distributions over **122,428**
  weighted paths. Only two games use mixtures; 15 use unconditional inputs. Across **32** seeds, 136-pair
  win-covariance deviations ranged **−0.00712 to +0.00728**; dependence is not validated. Existing pathway and
  served forecasts remain unchanged; Chunk A **28.5%**, next is explicit status/dependence/cold-roster handling.
- **22 Nov 2026 · Chunk A A1 70%:** research Expected and season reports retain status/source, prior-role,
  missing-field and uncalibrated-independence labels; **33** focused tests pass. Across the two captured games,
  **4/71** ranked records used prior roles and **48/71** were unlisted-active assumptions. Replayed labelled
  output preserved all 17-game accounting; no dashboard, forecast or bundle changed. Chunk A **31.5%**.
- **22 Nov 2026 · Chunk A A1 80% partial:** an isolated browser-format branch fixture independently reconciled
  **40,000** worlds and **16.8 million** player-stat values, with availability separate from minutes and exact
  weights. Its uncompressed size is **24.4 MB** for one two-player game; no app or phone compatibility is yet
  claimed. Artificial five-player retry stress required **28** attempts for **10** audited worlds; caps stopped
  a separate run. This deliberately extreme setup is not an NBA rate. Smoke **108/108**, deliberate fault
  **86/108**; no production model or bundle changed. A1 remains **70%**, Chunk A **31.5%**.
- **22 Nov 2026 · A1 80% participation correction:** **6,527 / 1,120,000** research player-world appearances
  had positive minutes rounded to zero, while **182,738** available player-worlds did not play. Exact separate
  flags now survive the fixture. A research JS implementation matches independent full/partial/empty weighted
  Given/Joint references and **90** histogram bins on each of the **20k / 40k** one-/two-player captures; it is
  not integrated into the UI. A1 and Chunk A progress remain **70% / 31.5%**; production forecasts and bundles
  remain unchanged.
- **22 Nov 2026 · D49 playing-time sensitivity:** retained exact float64 simulated minutes in isolated fixtures;
  for the selected player, exact versus rounded 30-minute filters differ in **187 / 20,000** and
  **963 / 40,000** worlds on the one-/two-player games. Cross-language weighted accounting matches.
  This is research-only: existing dashboard imports still use rounded minutes. A1 remains **70%**.
- **22 Nov 2026 · dashboard house follow-up:** player box scores now precede game insights; game availability,
  bench, secondary team-roster groups and player game logs expand on demand. **61/61** responsive cases,
  laptop/phone offline **29/29 / 28/28** and laptop shell upgrade **31/31** passed. Startup race fixed in
  data-free Pages **1fa44ca**; hosted forced-bypass laptop/phone checks **31/31 / 30/30**. Existing data remains
  valid, no nightly or model change.
- **22 Nov 2026 · A1 40% partial:** cutoff-checked origin selection and conservative missing-data labels passed
  **60** focused tests. One current-origin game selected **3** uncertain players and **4** unweighted sensitivities;
  no branch simulations or mixture yet. Chunk A remains **19.5%**.
- **22 Nov 2026 · A1 30%:** isolated one/two-player branches use exact rational uncalibrated independent weights
  and simultaneous D29 reallocation; larger selections expose only unweighted all-play/one-out sensitivities.
  **57** focused tests passed. No actual-input selection, persisted branch worlds, Expected mixture, model or
  served forecast is claimed. Chunk A **19.5%**; next is origin-safe selection and branch persistence.
- **22 Nov 2026 · dashboard house pass:** games first on Today with a shortcut to slate insights; Players table
  and next-game forecast prioritised; secondary movers, opponent history and advanced rates expandable. Player
  and team chart expansion survives stat/line changes. **43/43** responsive checks and **26/26 / 25/25** local and hosted
  laptop/phone offline checks passed; old-to-new upgrade **28/28**. Data-free Pages **8dfbbd7**, existing bundles
  retained, no nightly or model change. Continue the owner-requested usability/design work alongside Chunk A.
- **22 Nov 2026 · per-world advanced visibility:** independently reconciled **6,300** metric distributions
  across **32** saved games / **935** player-game entries. Defined counts and quantile bands accompany expandable
  histograms; 15 team metrics are box-derived estimates where required. Local and hosted PWA checks **24/24 laptop**,
  **23/23 phone**, old-to-new update **26/26**, expanded responsive checks **15/15**. Both iCloud bundles and
  data-free Pages **857183b** delivered; devices need manual imports. No model or nightly changed. Owner requested
  a broader progressive-disclosure/dashboard organisation pass while keeping information interactive.
- **22 Nov 2026 · Chunk A A1 10%:** owner authorised both planned chunks in order; baseline clean at `e35fbe2`,
  smoke **108/108**. Froze selection, branch IDs, seeds, uncalibrated weights, provenance and non-exhaustive
  sensitivities in HANDOFF before implementation. Chunk A **3%**; original A1 remains **58%**. The exact weighted
  season mixture is unresolved; v1.3/pathway v1 and the delivered bundle remain unchanged.
- **22 Nov 2026 · Chunk A A1 20% partial:** isolated one-player D29 game copy and synthetic plays/sits tests;
  **36/36** focused tests pass. Scheduled fives and defender inputs are checked, but full-engine branch and
  post-foul-out legality remain unverified, so no additional rung is credited and no production output changes.
  Smoke **108/108**, deliberate fault exited **1** (86/108 passed); Pylance diagnostics clean on both new files.
- **22 Nov 2026 · A1 20% probe protocol:** predeclared the F4 known-participant single-game, 32-world-per-branch
  observational replay and independent accounting in HANDOFF before running it; no prediction or model choice is
  inferred from the probe. The user instructed continuation unless he asks to stop.
- **22 Nov 2026 · A1 20% probe result:** both branches of fixed F4 game 401810327 preserved traced outputs exactly
  but failed independent foul-out accounting. Disqualified lineups occurred in **14/32** plays worlds and
  **16/32** sits worlds; no production branch or rung is claimed. An isolated fail-closed guard rejects a sixth
  foul and invalid fives; **24** focused checks pass. Preserve v1.3; any legal-play repair remains isolated until
  the registered gates pass. Normal smoke **108/108**; deliberate fault exited **1** with **86/108** passing.
- **22 Nov 2026 · A1 guarded replay protocol:** freeze the same fixed game, 32 worlds and branch seeds with the
  isolated guard enabled; record any sixth-foul failure rather than emitting a forecast. The unguarded source
  and evidence were pushed as `a3baeab`.
- **22 Nov 2026 · A1 guarded replay:** both fixed F4 branches correctly failed closed at an unsupported sixth foul
  in Q3; neither emitted a forecast. A foul-out-only isolated candidate is needed before branch validity can be
  established, and must pass the unchanged model gates before serving. A1 remains at 10%, Chunk A at 3%.
- **22 Nov 2026 · Owner UX requests, in progress (D44):** minutes-share filter and grouped shooting distributions;
  percentage outcomes exclude no-attempt worlds and disclose their share. New snapshot fields need a full nightly,
  archived delivery and PWA verification. A legacy-replay smoke mismatch was reproduced and a schema-aware check
  added; the final smoke passed **108/108**, and the deliberate fault failed as intended (**86/108**).
  Isolated browser **19/19** and old-bundle PWA **18/18** passed; completion and delivery remain unverified.
- **22 Nov 2026 · Chunk A A2 10%:** frozen F4 residual screen and independent raw-pair accounting on **3,604**
  player-games / **200** games. Teammate scoring-rate residual covariance **−1.215** (95% **−1.999 to −0.424**)
  versus opponent **+0.462** (95% **−0.410 to +1.283**). This is a retrospective, actual-participant descriptive
  result, not a model improvement or simulated-world comparison; v1.3/pathway v1 remain unchanged. Two focused
  tests passed; the report reproduced byte-for-byte and all **12** point estimates reconciled independently.
  Smoke **107/107**, with the changed-input replay skipped pending nightly completion; deliberate fault exited
  **1**. Chunk A **6.5%**, original A1 **58%**. The D44 delivery nightly is still running.
- **22 Nov 2026 · Chunk A A2 20%:** froze cutoff-safe talent, nightly form and shared-factor hypotheses and
  explicit no-double-count controls in TRAINING_PLAN; no candidate was fitted or promoted. The inspected F4
  descriptive screen is not untouched confirmation. Chunk A **10%**; A1 **10%**, A2 **20%**, A3 **0%**.
- **22 Nov 2026 · A2 earlier-fold feasibility:** **595** fixed-panel F1–F3 games / **11,217** player-games;
  pooled teacher-forced within-game shot-residual covariance **0.001368** (95% **−0.000104 to +0.002874**).
  Individual components are not identified. All **16** estimates and clustered intervals independently
  reconciled; v2 clarifies limited role-panel coverage and reproduces v1. A2 remains **20%**, no model changes.
- **22 Nov 2026 · A2 cross-game feasibility:** **595** fixed-panel games / **10,977** player-games; pooled
  shot-residual persistence **−0.000066** (two-way 95% **−0.002095 to +0.001786**). F3 star coverage is
  insufficient. An independent sparse-matrix calculation reproduced all **15** supported estimates and intervals.
  No separately identified talent variance or candidate is claimed; A2 remains **20%** and v1.3 is retained.
- **22 Nov 2026 · Chunk A A2 30%:** isolated synthetic-only mean-preserving player-effect mechanics with
  deterministic namespaced streams, zero-draw fallback and valid probability bounds. **9/9** focused A2 tests
  pass; at **10,000** synthetic worlds the two tested probability means differ by **+0.001567 / −0.000420**
  from baseline. Normal smoke **107/107** (newer inputs skip one replay); deliberate fault exited **1**.
  Uniform factors and strengths are arbitrary research fixtures, not a calibrated or wired model. Chunk A
  **13.5%**, original A1 **58%**; the D44 nightly subsequently completed as logged below.
- **22 Nov 2026 · D44 delivery:** live nightly rebuilt inputs through 21 Nov and refreshed **7 + 10** games ×
  **10,000** worlds and **10,000** season paths (959 games). Independent checks reconciled **340,000**
  player/team world totals and **4,509** full-game shooting histograms; **10,521** period/player/shooting
  triplets passed conditional/no-attempt accounting. Smoke **108/108**; local offline PWA **19/19** and
  responsive pages **18/18**, with screenshots inspected. The iCloud bundle and data-free `gh-pages`
  `707f6e9` were delivered; the hosted PWA passed **19/19** and phone import remains manual. Neither
  model was promoted; Chunk A remains **13.5%**.
- **22 Nov 2026 · D45 laptop PWA:** owner's laptop-first clarification corrected the phone-only export.
  Laptop bundle **64.2 MB / 2,031 records**, phone **12.9 MB / 1,999**, including/excluding **32** saved-world
  files; all **1,971** laptop API records reconciled to retained views. Fixed a visibly clickable but inactive
  update button. Isolated offline checks: laptop **28/28**, phone **21/21**, old-to-new update **6/6**.
  No model or forecast changed; Chunk A remains **13.5%**. Each device requires its own manual import.
- **22 Nov 2026 · A1 20% partial, source freeze:** the opt-in foul-out candidate now returns a per-world
  change mask; the engine refreshes only those worlds' lineup columns and rejects unsupported mismatch features.
  Legacy/no-policy tests and the combined branch, availability, substitution and world-audit suite passed
  **73/73**. Smoke passed **108/108**; deliberate fault exited **1** (**86/108** passing). The previously frozen fixed 32-world F4 branch replay is still required; no rung or
  model promotion is claimed.
- **22 Nov 2026 · A1 20%:** frozen fixed-game repaired plays/sits replay passed, 32 worlds each. Independent
  reconstruction checked **16,130/16,336** legal fives and reconciled player minutes and team scores; trace
  outputs were unchanged, **59** focused tests and **108/108** smoke checks passed; the deliberate fault exited
  **1** (86/108). This is isolated wiring, not a promoted model or
  availability calibration. Chunk A **16.5%**, original A1 **58%**. Next: finish the owner's advanced-stat
  presentation and start the frozen two-player/non-exhaustive branch rung.
- **22 Nov 2026 · advanced game visibility:** six player rates, latest pre-origin action-share profile, actual
  full-game +/−, OREB/DREB/TOV player boxes and 15 collapsible team metrics per side; possession-based team
  ratings explicitly estimated from box totals. **1,971** prior laptop API records reconciled except new profile
  fields and the build timestamp; current-origin profiles cover **17** games / **487** player-game entries.
  Hosted offline checks **24/24 laptop**, **23/23 phone**; responsive checks **24/24**. Both iCloud bundles
  require manual imports. A reproduced stale-asset upgrade was fixed; old-to-new upgrade and offline checks passed
  **26/26**. Data-free Pages **3567ed9**; smoke **108/108**, deliberate fault exited **1** (86/108).
  No model promotion or new nightly.
- **19 Nov 2026** — Studied MusSim. Probed sources: ESPN site API works with plain requests; NBA CDN returns 403.
  Owner: app shell first, play-by-play sim later.
- **19 Nov 2026** — Phase 1 shipped (collection, placeholder engine, snapshots, views, server, app, PWA). Fixed: a
  loop-closure bug, a `conf` field collision, phone screenshots needing device emulation. Owner asked for this
  detailed plan file and localhost-first development.
- **19 Nov 2026** — Phase 1b: owner's Game Centre spec (bezel, Q1–FG dropdown, Player/Team, Matchup). `pbp.py`
  reconciles after measured fixes (missed heaves are not FGA; offensive fouls often only as turnover records;
  shot-clock/8-second violations are team turnovers; technical fouls/timeouts do not mark quarter starters). A
  "fouled missed shot" rule was tried and reverted (worse). Model choice: LightGBM (Jev is proprietary).
- **19 Nov 2026** — Engine design rounds 1–5 with the owner → ENGINE_PLAN v6: clock-driven segments, target-aware
  substitutions, shared models with quarter as an input, per-player form, two horizons, MusSim-style per-world
  season pathway, 10k universes, 60-minute nightly budget, weekly refits.
- **19 Nov 2026** — **M1**: one play schema; history 2022-23 → 2025-26 reconciles (points 0.05–0.16%, minutes
  0.58–0.97% of player-games off). Blank `points_attempted` in 2022-24 inferred (99.96% agreement where known).
- **19 Nov 2026** — **M2**: 1.25M segments; identities pass per season; late-logged plays ordered by clock; ~2% of
  games flagged (feed gaps) and excluded from training; realism matches NBA norms.
- **19 Nov 2026** — **M3**: stints reconcile (minutes 99.6–99.95%); substitutions rise every season (27.2 → 34.5);
  replay v0: minutes MAE 5.17 for rotation players but 60% interval coverage (needs game state → M7).
- **19 Nov 2026** — TRAINING_PLAN v1 → v2 (owner: maximise accuracy, rich data, experiment freely): four rolling
  folds, untouched final test, ablations, experiment log with negative results.
- **19 Nov 2026** — Owner: playoffs/Cup differ mainly by rotations → one model with game type (D19); history now
  includes playoffs and play-in (5,290 games). Measured: playoff starters +3.0 min, pace −4%, possessions longer
  at every start type (+0.4–0.6 s).
- **19 Nov 2026** — **M4 core**: point-in-time profiles (116k player-games; usage r = 0.70 with the game, minutes 0.79);
  harness and baselines on folds F1–F4.
- **19 Nov 2026** — Owner left the number of steps to the data → **D20**: fifteen decisions in four stages (all ≥ 50k
  rows). M5 started: datasets for all 15 nodes; first fold-F4 runs: blocked +6.5% over the best baseline, turnover
  type +4.9%, stealer and free throws level (FT attempt-order features then added). Full 15 × 4 run launched.
- **19 Nov 2026** — Owner asked for an honest read (placeholder: Brunson 20.6 points v 27.0 actual). Diagnosis:
  placeholder minutes spread too thin (29.3 v 34.2) and team-total-then-split scoring; the engine removes both by
  design. Added **M6a** (real-rotation aggregation test). Owner: docs must let a new agent take over at every
  checkpoint — AGENTS/HANDOFF rewritten as a prescriptive hand-over; checkpoint protocol added.
- **19 Nov 2026** — **M5 v1**: all 15 nodes beat or match their best baseline on every fold (mean gains: event 15.1%,
  assisted 25.5%, rebound 8.0%, blocked 6.4%, what 5.3%, turnover type 4.8%, assister 2.4%, shot result 2.1%, who 2.1%,
  fouler 1.6%, rebounder 1.5%, duration 1.3%, blocker 1.2%, free throw 0.1%, stealer 0.1%); ECE ≤ 0.016. Caught and fixed
  a label leak in the free-throw dataset (attempt order); real effect: second FT 80.4% v first 75.6%.
- **19 Nov 2026** — Git: repository initialised with the owner's personal identity (as MusSim), first commit `3291ffc`,
  pushed to the new **private** GitHub repo `MusaMoholo/MusNBA`. Owner's standing rule: agents commit and push at every
  checkpoint (AGENTS.md §4–§5).
- **19 Nov 2026** — **M5 tuning** (≈1,000 fits, paired game-clustered comparisons with a seed-noise floor): no sample-weight
  decay (every half-life worse; ½ season +4.5 nats per game); shot distance worth 3.1 nats per game → **D21: location node**
  (16 decisions) and team turnovers as an event class; team style kept for duration/what/shot result (−1.3); in-game
  form kept except free throws (no hot hand in shot making); schedule, clutch, playoff weights, recalibration and profile
  decay variants not better; fouls fall through every season → day of season for event and turnover type. All-Star
  games found in history and excluded. **v1** validated on folds (every node ≥ baseline on every fold, ECE ≤ 0.012),
  persisted (`data/models/v1/`, 44 MB) and **final test scored once**: every node above its baselines (event +11.8%,
  assisted +22.7%, rebound +7.2%, blocked +6.2%, what +4.4%). Final-test calibration exposed a **live-v-history adapter
  skew** (M5b, next).
- **19 Nov 2026** — **M6a** (`aggregate.py`): 300 F4 games × 10,000 worlds with real lineups and clock — team total
  228.5 v 229.5, player points/rebounds/assists/threes within ±2% for starters and bench, 10–90% coverage 77–83%,
  CRPS 7–12% better than recent averages on every stat. Fouls +5% traced (event accounting) to the in-season foul
  decline; stars run 2–5% hot on points, free throws, turnovers and threes (to trace).
- **19 Nov 2026** — Owner: put the current model in the dashboard. **Engine v1 preview** (`engine.py`): the v1 nodes
  played forward possession by possession (sampled durations, replayed rotations, per-world score, fouls, foul-outs,
  in-game counts), packaged in the app contract (`projection.package`); `nightly.py --engine` builds today's slate
  with it (placeholder kept beside it in `games_placeholder.json`); the app labels it "Engine v1 · preview". Today's
  four games: plausible box scores (114 points, 240.6 team minutes, 91 FGA, 22 FTA); pace ≈ 3% high and spread too
  narrow (OT 2.2%) — the M8 work. Owner realism sweep recorded (PLAN §9): size + archetype priors (owner: needed), on-court
  defensive impact, substitutions (M7) as the biggest remaining risk.
- **19 Nov 2026** — M6a full run (766 F4 games): gate confirmed. Engine clock rules from data: post-action game time
  (8.4% of the clock, mostly 2.4 s from a miss to its rebound), whole-second durations within bins, end-of-period
  segments from real ones; the first two errors had cancelled (pace +3% → −5% → ≈ −2.5% after all three). Owner:
  scores too high on the first preview — they were (+1.5%, from pace); now slightly low, strong offences under-expressed.
- **19 Nov 2026** — **Owner (D22): engine v1 is the dashboard default and the floor** — later changes replace it only when
  measured better. `nightly.py` now uses the engine by default (`--placeholder` opts out); the chip reads "Engine v1";
  backfills stay on the placeholder (cutoff safety). Docs brought up to date for a hand-over to a new agent.
- **19 Nov 2026 (late)** — **M5b**: the adapters agree (five 2025-26 games re-fetched: identical segments); ESPN's 2026-27 feed
  stamps every rebound at the miss's clock (100% v 7–12% in every month since 2022), moving ~2.6 s of ball flight into
  the next segment and making every team look 3–8% slower in team style. One convention for every season (**D23**):
  on live-style held-out rows v1 is worse on 12 of 16 nodes (chain +34.1 nats per game; reproduces its final-test
  miscalibration) and in M6a (threes +7.4%, steals +9.6%, defensive fouls −20.5% → v1.1 +1.0%, +0.8%, −1.0%).
  **v1.1 promoted** (v1's settings on the new data; final test scored once) and the engine serves it for **today and
  tomorrow (D24, owner)**: pace fixed (≈ 97 → ≈ 101 possessions per team on the 19 Nov slate; points ≈ 108 → ≈ 115).
  v1.1 final test: duration ECE 0.002 (v1 0.014), event 0.009 (v1 0.022). Foul, turnover and held-ball shifts in 2026-27 are real. Heights/weights for 935 players;
  archetype priors and on-court defence: first ablations negative (only the location node gains). Owner asked for a
  MusSim-style per-world rating pathway beyond tomorrow (D25) — next session.
- **20 Nov 2026** — Owner check against bet365/DraftKings (FINDINGS §3m): v1.1 totals run ≈ +8 points above the market on
  the 19 Nov slate (NYK–MIN 231 v 216.5) and its spreads are about half the market's — efficiency +1.7%, and matchup
  effects (totals and margins) under-expressed. Owner: the market is broadly rational (D8 note; compare with closing
  lines). Owner request: the Game Centre should show a saved sim's play-by-play like nba.com, then a visual play-through
  (D9, M10). Both queued in HANDOFF for the next agent.
- **20 Nov 2026** — Owner: the goal is a ground-up simulation as accurate as possible against real outcomes, not betting;
  the market is a reference. Measured: DraftKings' lines are unbiased against 2026-27 results (222 games: totals −0.6 ±
  1.2, margin slope 1.09), so v1.1's high totals and half-sized spreads are engine errors to fix (HANDOFF item 3).
- **20 Nov 2026** — Owner: the product is two engines in one daily flow (**D26**); each chunk has one or two headliners that move them toward trust; every chunk ends with the dashboard on the newest systems; UX backlog §9b. **Nightly input rebuild:** segments → rotations → profiles from every final before today (~50 s; 4 new finals → engine inputs changed), next slate when today and tomorrow are empty. **Team pathway v1 (D25) in the app:** per-world offence/defence ratings, engine worlds for today + tomorrow, updates on the points surprise (D27: a good loss keeps ratings); walk-forward 2022-26: the old fixed-probability season sim had dispersion 1.53 and coverage 65%, v1 1.00 and 84%, CRPS −4% in every held-out season (still wide in November). **First engine backtest (M9, 200 F4 games):** pace +0.2%, totals +2.7, margin slope 1.45, defence expressed at ~25% of its real effect (offence ~70%), stars' minutes +6.5%; the team-rating model beats the engine on margin CRPS (9.32 v 9.64), totals and win log loss. Smoke 80/80, browser 38/38.
- **20 Nov 2026** — Owner (**D28**): the guiding light is player outcomes — a team's results are the aggregation of its players, so minutes, performance and the defence each player faces come first and team results short and long term follow; the engine stays the dashboard default; the team-rating model is a yardstick only.
- **20 Nov 2026** — Design with the owner for the next chunk (new agent): **D29** minutes — healthy-role minutes and priority, 240 per game allocated by priority (an absent star's minutes cascade and return), a learned return ramp; **D30** defence — stay on ESPN data (NBA Stats only if this stalls), soft matchup assignment over the five on court from size/role/position, learned from foul and block credits, defender quality weighted by it, shot type from the play text; **D31** lineup scenarios in the nightly for uncertain high-impact players (Expected = their availability-weighted mixture), later a localhost lineup editor.
- **20 Nov 2026 (afternoon, D29–D30 chunk)** — **Engine v1.2 → v1.3 promoted on the backtest (same 200 F4 games).** D29 minutes
  (healthy roles, 240 by priority, return ramp, rotation share, per-world draws; `minutes.py`): stars' minutes +6.5% → −1.0%,
  points +8.8% → +0.5%, minutes coverage 58–63% → 77–84%, team sums level. D30 defence (defender-side on-court defence with
  ×0.2 shrinkage, a soft matchup assignment from foul/block credits — weak: top-1 26% v 20% — help at the rim, shot-type
  shares): defence loading 0.44 → 0.69 (real 1.69), margin CRPS 9.67 → 9.37 (team model 9.32), total 12.00 → 11.72, win log
  loss 0.595 → 0.571, players level or better. Shot type is real signal (−0.61% shot-result log loss on simple rates; node
  ablation −0.34%). Lineups: Basketball Monster and CBS forbid scraping, DailyFantasyFuel has no NBA page, FantasyPros unclear
  → our own projected starters (89.4% of slots on 2026 history) and a nightly record (D33). **Owner:** NBA Stats API for the
  next chunk (D32: ingest, crosswalk, cleaning, then defence on real matchups); the Lab page is not a priority; this chunk's
  UX headliner: joint and conditional outcomes — Game Centre Scenarios tab, Given…, joint grids, drivers, teammate
  correlations, who-gains-if-X-sits, averages deltas, Today leaders (`outcomes.mjs`, `scenario.mjs`; worlds stored per game).
- **20 Nov 2026 (evening, D32 chunk)** — **NBA Stats ingested (D32):** own stdlib adapter (Chrome fetch headers needed; ~1 req/s,
  resumable, gzip + manifest), 5,508 games 2022-23 → 19 Nov: season logs, `boxscorematchupsv3` (1.04M attacker–defender rows),
  tracking defence per date (2,628), play-by-play v3 (in progress); crosswalk 5,508/5,508 games, 99.986% of player-games
  (17 unmatched: one player without an ESPN id); reconciliation: points identical, our minutes within 60 s of NBA's in 99.87%,
  possessions +0.9 per team-game; 2022-24 matchups over-count FGA (111%). **Real matchups:** who-guards-whom top-1 36.4% → 50.2%
  (top-2 75%, confidence well ordered); defender traits — 3PA share allowed r 0.77, 2P% 0.49, 3P% −0.05 (noise) → shrinkage from
  reliability; switch hunting not visible (D35). **Engine:** v1.3's defence gap is shot-making (FG% 37%, 3P% 18% of real) while
  turnovers are 95%; v1.4c (real-share defence), v1.4e (+ deterrence: 3P% → 30%, FTA → 48%) and v1.4f (+ top-1/top-2 defenders,
  owner's idea) all level or worse on margins/totals/players → **v1.3 stays (D37)**; reading: general compression of team
  differences. **App:** who-guards-whom (Matchup), player head-to-head, game flow + duels in Scenarios, duel of the night,
  standings Wins tab + wins/seed pickers + W%/Proj W/Proj L sortable, grouped controls, multi-doubles/5×5, OREB/DREB/FGM/FTM,
  box and bezel Δs, phone bundle stripped back (D36), 10,000 worlds per game (D36).
- **21 Nov 2026 (close-out of the D32 chunk)** — Close-out nightly (21 Nov, 23:01 UK): 10 new finals, 9 new NBA matchup games,
  real matchups 5,513 games; snapshots 21 Nov (6 games) and 22 Nov (7) at **10,000 worlds per game with one rotation table
  per world** (D36; backtest: players level, +5% time), ~130–150 s per game. App: spotlight v2 (headliner sparkline and
  chances, breakout dumbbell with the why, chance to lead the night/game, games to watch), fixed layouts at 1440/960/390.
  Docs made model- and environment-agnostic (AGENTS §6 long jobs, preferences moved out of private notes). Smoke 99/99
  (`--fault` fails 19), browser 81/81.

- **22 Nov 2026 · U15**: Roster grouped into projected starters, bench, rotation fringe and reported out; season minute bars against next-game projections, minute deltas and injury details. Six size/theme cases passed; desktop/phone screenshots inspected.

- **22 Nov 2026 · U16**: Playoff picture tab: seed 1–10 favourites and alternatives, a unique-team illustrative first-round field and play-in paths; marginal probabilities explicitly distinguished from pairing odds. Six responsive/theme checks passed and screenshots inspected.

- **22 Nov 2026 · U17**: Wins tab adds per-team mini histograms on a shared 0–82 axis, median and 10–90% ranges, and widest-range sorting. Six responsive/theme checks passed; screenshots reviewed.

- **22 Nov 2026 · U18**: New Season tab: conference/league win-range race, #1 seed races and worst-record race. Bottom-three record counts added to the season simulation (no changes to draws); populated by close-out nightly. Six browser cases passed, screenshots reviewed; Season included in PWA caches/export.

- **22 Nov 2026 · U19**: Movers compares distinct season cutoffs (30 teams; 20→21 Nov, nine results), projected-win and Top 6/play-in/#1 changes, risers/fallers and linked interval results. Races/Movers/Leaders merged under Standings per owner; /season redirects. Six Movers cases and twelve merged-navigation cases passed; screenshots inspected.

- **22 Nov 2026 · U20**: Standings Leaders: seven player leaderboards (PTS/REB/AST/3PM/STL/BLK/FG%) and four team rating/pace leaderboards. Explicit minimum-games and shooting-attempt filters; current data qualifies at 12 GP. Distinct from forecast Races; six size/theme checks passed and screenshots reviewed.

- **22 Nov 2026 · U21**: About the model guide: two engines, 10k worlds, ranges and probability changes, cutoff safety, decision highlights, known limitations, sources and live retained-data freshness. Linked from engine/season chips and Model & data; PWA included. Six size/theme checks passed and screenshots reviewed.

### Superseded four-task engine chunk (21 Nov)

The former S1 compression / S2 substitutions / S3 dashboard / S4 close-out plan is replaced by A1 in §6a–6c and
HANDOFF's live ladders. Its detailed original is retained in git at `86c2a46:PLAN.md`; do not run both plans.
Rotation maps and event playback moved to A1 S12; existing U3 role badges/U11 defence profiles are already shipped;
face cards and unrelated presentation remain §9b backlog. NBA history moved to S02; all core model work is expanded.

- **22 Nov 2026 · U22:** grouped Standings controls; 9 player/6 team cards; counts/dates/thresholds and win scales from loaded
  data/configuration; loading/empty states; all 130 browser cases pass plus 30 targeted cases, PWA 14/14 including dynamic
  count/qualification changes. Owner: keep season insights in Standings, comparable card groups in multiples of three,
  copy MusSim's personal GitHub Pages + iCloud setup; explicitly approved making MusNBA source public.

- **22 Nov 2026 · dashboard close-out:** U1–U22 complete; public source + Pages (`gh-pages` e302d27), URL
  https://musamoholo.github.io/MusNBA/. Nightly refreshed ET 21/22 Nov: **13 × 10,000 game worlds + 10,000 seasons**
  (965 remaining games). Smoke **102/102**, fault detects **22**, browser **156/156 + 12/12** final phone-layout cases,
  hosted PWA **15/15**. Final **10.6 MB / 1,998-record** iCloud bundle delivered; owner confirms phone file visibility.
  Fixed iCloud hidden-file inheritance with non-dot staging + pre/post flag clearing. Next: expanded A1 accuracy programme (§6a);
  actual iPhone installation/import acceptance remains with owner. No model/training/final-test changes.

- **22 Nov 2026 · A1 planning-only checkpoint:** rewrote all eight root docs against the shipped v1.3/10k/public-PWA
  state. Replaced the four broad queued tasks with **14 weighted subtasks / 140 concrete 10% rungs** (all at 0%).
  Defence stays central; broadened minutes, availability, form, season calibration, robustness and promotion evidence.
  Owner clarified the historical workflow: preserve Today, distinguish Tomorrow previews, and rebuild season start→now
  under each accepted current model with dated inputs/fits and archived previous versions. Every task commits/pushes
  with current docs and necessary PWA model/data/shell delivery; every development chunk ends in a fresh nightly and a constructed successor chunk. Baseline smoke
  **102/102**; no model/data/shell change, training, fetch, final-test scoring or nightly in this planning session.

- **22 Nov 2026 · A1 S01 complete:** owner lifted the planning-only stop. S01 is **100%** (A1 **6.0%**); both
  200-game controls completed, legacy fields reproduce to 1e-12 and quarter scores reconcile across **2,677** fold
  games. Independent-seed pooled MIN/PTS CRPS noise floors are **0.02634/0.00919**; one raw-box player outcome is
  missing. The prior-box cohort is separately labelled inferred availability, not actual-participant engine evaluation.
  Smoke **102/102**, deliberate fault **22 detected** and **15 focused tests** passed; final manifest pins
  1,318 confirmation games and source checkpoint `c6d5db4`. No candidate, production model or PWA bundle changed;
  S02 begins with downloader integrity and history inventory.

- **22 Nov 2026 · A1 S02 10%:** inventoried **10,094** NBA raw files and manifests with no missing, unindexed,
  corrupt or hash/size-mismatched files; **45** entries lack acquisition metadata. **3,622** logged PBP games remain.
  Eight hoopR files match their manifests; one 2025–26 box-only game has no retained ESPN play-by-play. Current ESPN
  final summaries have no per-file acquisition/hash manifest. Production and PWA remain unchanged.

- **22 Nov 2026 · A1 S02 20%:** fixed three eager per-season `Store` paths and added exceptional-exit flushing to
  season logs; all **19** focused A1 tests pass, including the reproduced interruption and resume failures. One
  363-request PBP batch is running; selected audit cases cover missing ESPN play-by-play, an unscored player and
  overtime. Production models, forecasts and PWA remain unchanged.

- **22 Nov 2026 · A1 S02 ongoing:** four history batches retained **1,452/3,622** originally missing games; batch 5
  runs toward the half-queue rung. Across five retained seasons **14,235/1,216,437** actors are absent from the
  segment-start offence. An isolated substitution-split/quarantine pilot on the fixed 200 F4 games reduces this
  **489→6**, preserves event/possession accounting and reduces median credited-seconds discrepancy **13→0**;
  70 unresolved segments remain quarantined. A history-only causal-prior build covers **111,075 player-games /
  5,196 games**, with zero later-season differences across 38 player and 14 team columns; assignment/body cutoff
  safety remains open. Production and PWA remain unchanged; full evidence and commands are in HANDOFF/FINDINGS.
- **22 Nov 2026 · A1 S02 30%:** five batches retained **1,815/3,622** original PBP items, with no empty
  responses; batch 6 runs in the same single stream. Fold-dated assignment diagnostics cover F1–F4. On F4's
  **35,216** held-out credits, dropping historically unverified body measurements worsens weighted log likelihood
  **−1.54347→−1.54611**; this is not an engine test. Chronological training-row assignment and position provenance
  remain open. No production model, forecast or PWA bundle changed.
- **22 Nov 2026 · A1 S02 ongoing:** nine batches retained **3,267/3,622** original items; the final 355-item batch runs. A
  prior-position base keeps **891/111,075** player-games' positions unknown, including all **877** first observations.
  Thirty monthly body-free assignment fits and four fold-frozen schedules are isolated; all four corresponding feature
  snapshots are built. Sampled F1–F4 parity: **304,175/304,175** matchup, lineup and relative-column comparisons
  match, excluding 36 actor/lineup conflicts. Full F4 chain built **16** datasets / **17,814,437** rows; accounting
  passed, and a fitted-model wiring run completed **3 games × 20 worlds** with independent score/player accounting.
  Real-slice injections left **3,098** earlier values unchanged and changed
  **42** shot-derived and **47** minute/position-derived later values. A diagnostic baseline's held-out-batch fill now
  uses training data.
  Accepted-system smoke **102/102**, including bit-for-bit v1.3 replay; deliberate `--fault` exited 1 as intended
  (**80/102** checks passed after injected corruption). No model, forecast or PWA bundle changed.
- **22 Nov 2026 · A1 S02 partial checkpoint `6ec31d6`:** candidate dated schedules now reject five reproduced corrupt
  cutoff/parameter cases; **46** focused tests pass. Thirty monthly fits and four schedules were rebuilt with the guarded
  source; four dependent feature builds and sampled parity completed. All **3,622/3,622** originally queued PBP items
  have been retained with zero empty responses; independent inventory and F4 node rebuilding are running. This is
  data-integrity work, not a promotion.
- **22 Nov 2026 · A1 S02 40%:** independent inventory confirms **5,517/5,517** eligible NBA PBP games and all
  **3,622** originally queued downloads; zero missing/corrupt/hash-mismatched files. Forty-five older entries retain
  unknown fetch metadata. Guarded node-cache accounting and model wiring remain.
- **22 Nov 2026 · A1 S02 50%:** per-season NBA/ESPN reconciliation covers **118,187** known points rows with
  zero differences, on-court seconds and possession conventions; parser-flagged games are listed, not silently included.
- **22 Nov 2026 · A1 S02 60%:** audited **973,227** clock-grouped windows, including **809,830** no-substitution and
  **84,044** multi-substitution windows; **438** NBA-positive appearances rounded to zero ESPN minutes and **13** were
  marked ESPN DNP. Early matchup FGA sums exceed official totals by **11.6% / 11.2%**; causes remain unresolved.
- **22 Nov 2026 · A1 S02 70%:** tracking defence/report/roster coverage and cutoff-safe joins are mapped. Tracking's
  last-team field disagrees with dated game logs in **8,637/113,089** Overall rows; use person/date and the dated team,
  retaining unknowns. Historical report publication and roster completeness remain unproven.
- **22 Nov 2026 · A1 S02 80%:** guarded fold/serving parity matched **304,175/304,175** sampled values; independent
  F4 cache accounting passed **16 datasets / 17,814,437 rows**. Guarded matched-seed model wiring is running.
- **22 Nov 2026 · A1 S02 90%:** **46** focused tests pass, including five corrupt schedule cases; a real-slice future
  injection preserves **3,098** earlier values while changing **42** shot and **47** minute/position later values.
  The split candidate's 200-game independent feature/node accounting passes (**44,863** five-player choice groups;
  **70** quarantined segments). Matched-seed guarded wiring reproduces the old three-game run to `1e-12` and passes
  independent accounting; final smoke/fault and checkpoint remain.
- **22 Nov 2026 · A1 S02 100%:** final guarded-source smoke passed **102/102**; deliberate fault exited 1 with
  **80/102** passing. **5,517/5,517** eligible games were inventoried, and all **304,175** sampled train/serve
  comparisons matched. S02 is research/data-integrity only: v1.3 and the served PWA/bundle remain unchanged. S03
  begins with the fixed matched-game signal diagnosis; publication-time and historical availability limits remain.
- **22 Nov 2026 · A1 S03 10%:** fixed the component/strength diagnosis to the S01 **200 games / 400 team-sides**,
  pre-date rating predictors and 10,000 paired game-cluster bootstraps. All games match the manifest and all relevant
  denominators are positive. Rejected matchup variants share those IDs but require their original shared-pool control.
- **22 Nov 2026 · A1 S03 20%:** reproduced the archived pool-0 strength and component loadings with **10,000**
  game-cluster replicates. Simulated minus real points/100 loading: offence **−0.417** (95% **−0.837 to −0.024**),
  opponent defence **−1.008** (**−1.395 to −0.640**); descriptive, not causal. Same-model M6a is next.
- **22 Nov 2026 · A1 S03 30%:** the same-model, **200-game × 10,000-world** teacher-forced replay completed in
  **705 s**. Independent accounting matches **17** model hashes and **12,000** component values; **110/400** real
  event-filtered scores differ from official totals. This is diagnostic only and does not change production.
- **22 Nov 2026 · A1 S03 40%:** independently checked the preregistered 112/88-game profile split: **35,413**
  shooter exposures and **177,060** defender-on-court exposures; one invalid defensive five excluded. Overlap and
  selection make this descriptive rather than an individual-defence causal estimate.
- **22 Nov 2026 · A1 S03 50%:** traced the saved F4 shot node on **35,413** aligned shots, by shooter, zone, usage,
  matchup and exposure. Rim matchup-profile quartiles differ **6.66 pp observed / 3.65 pp predicted**; post hoc
  game-clustered gap interval **0.25–5.73 pp**, exploratory and unadjusted. No candidate has been promoted.
- **22 Nov 2026 · A1 S03 60%:** the **200-game** free-running capture reproduced **114,212** original game/player
  values and all **17** model hashes; independent quarter, lineup and clock accounting passed except one explicitly
  incomplete roster side. Defence-loading error is **−1.017** in teacher forcing and **−1.008** free-running;
  their paired change **+0.009** (95% **−0.195 to +0.211**) does not locate additional loss in flow. Starters'
  minutes are **+0.669**, bench **−0.361** against actuals. These are descriptive conditional diagnostics.
- **22 Nov 2026 · A1 S03 70%:** the rejected v1.4c/e/f shared-pool variants' total shifts were **+0.996 / +0.893 /
  +0.411 points per game**. Exact two-/three-point and residual score terms, FTA, offensive rebounds and the
  pace/efficiency split are recorded in FINDINGS §6b; differing model-version streams preclude causal attribution.
- **22 Nov 2026 · A1 S03 80%:** froze two falsifiable S04 families: training-only rim matchup-expression
  calibration with the predicted make level preserved, and an isolated pre-origin tracking-defence increment through
  the defending five. Both retain player-first fold/engine gates; F4 observations are hypothesis-generating, not
  independent confirmation. Protocol and disconfirming conditions are in TRAINING_PLAN §8.
- **22 Nov 2026 · A1 S03 90%:** linked each frozen mechanism to the matched node, profile, flow and
  tracking-coverage evidence in FINDINGS §6b, including population, missingness and non-causal limitations.
  Final checkpoint checks then passed.
- **22 Nov 2026 · A1 S03 complete:** matched flow and replay independently reconciled; both defence families
  have falsifiable cutoff-safe protocols. Smoke **102/102**, deliberate fault exited 1 with **80/102**, and
  **30** focused tests passed. No model or PWA promotion; S04 and the concurrent S05 minute screens follow.
- **22 Nov 2026 · A1 S04 10%:** the rim-expression and incrementally added tracking-defence levers are fixed before
  their candidate runs. The accepted v1.3 baseline remains unchanged; safe fold-fitted controls and exact engine
  comparisons are required before promotion.
- **22 Nov 2026 · A1 S04 partial wiring:** reused the audited guarded F4 shot model and reproduced its
  **0.7295266** held-out log loss on **135,680** shots. The exploratory paired loss change was **−0.0000312**;
  its report's tail-start label is invalid due to datetime units, while the actual fitted mask is independently
  verified as 2 Nov–31 Dec 2025. Preserve source, repair/report under a new name, then complete other folds.
- **22 Nov 2026 · A1 S04 20%:** isolated rim-expression calibration and guarded fold runner are implemented.
  Corrected F4 metadata reproduces all **135,680** original predictions and population metrics exactly; four
  focused tests pass. No production path changed. F1–F3 and independent accounting are underway.
- **22 Nov 2026 · A1 S04 30%:** all four guarded folds and fixed-200 subsets are independently reconciled:
  **499,589** shots, **80** supported metric groups, all recorded hashes and **135,680** original/corrected F4
  rows. Full-fold paired loss differences are **−0.00000222/+0.00001481/+0.00001113/−0.00003117**; fitted
  slopes change signs across folds. The independent same-input training-noise gate is being verified. This is
  conditional shot-node evidence, not a v1.3 engine or forecast improvement.
- **22 Nov 2026 · A1 S04 rim gate:** independently verified seed-7/8 training noise is **0.013718%** relative RMS;
  the mean candidate change is **−0.000259%**, pooled game-cluster z **−0.283**. The pre-existing node gate is
  neutral, so this bounded calibration is not retained for an engine test; tracking defence is a separate family.
- **22 Nov 2026 · A1 S04 40%:** froze the tracking test before execution in **5e30f4**; isolated builder/screen
  now use strictly earlier defended-shot counts, unique dated NBA-team/ESPN identities and all-five-or-missing
  lineup rates. The builder checked **1,692** source files and wrote **921,103** historical shot feature rows.
  **24** focused tests pass; independent cutoff/coverage accounting and fold tests remain.
- **22 Nov 2026 · A1 S04 50%:** independent chronological reconstruction reconciled **146,581** distinct fives
  and **4,605,515** values across **921,103** shot rows. All-five tracking coverage was **98.12%** for the
  source's under-six-foot bucket and **98.19%** for its three-point bucket; **20** invalid defensive fives remain
  missing. All four guarded fold screens ran; their metrics and noise gate await independent checks. Source revision
  timing is unproven, so the data does not establish historical publication.
- **22 Nov 2026 · A1 S04 60%:** independently checked **499,589** tracking-ablation predictions and **112**
  supported groups across F1–F4. Candidate-minus-control full-fold log loss was **+0.00022107 / +0.00002580 /
  +0.00000209 / +0.00001616**; mean relative change **+0.00906%**, pooled z **+3.76**. F1 alone worsens
  **0.03021%** with z **+3.63**, more than twice same-input seed noise **0.01372%**. The pre-existing node gate
  rejects this increment; no unchanged-v1.3 engine or forecast win is claimed.
- **22 Nov 2026 · A1 S04 70%:** neither prespecified family survives the node gate, so the survivor-only fixed-game
  engine-test set is empty. No candidate player or team improvement is claimed; S03's matched v1.3 component and
  total-bias accounting remains the control. A labelled post-hoc frozen-adjustment interaction is being audited.
- **22 Nov 2026 · A1 S04 80%:** no retained input requires engine confirmation. The explicitly post-hoc,
  no-refit interaction was independently reconciled on **499,589** shots; combined full-fold loss changes were
  **+0.00021749 / +0.00005594 / +0.00000852 / −0.00000768**. This descriptive check cannot promote a combination
  of the rejected families.
- **22 Nov 2026 · A1 S04 90%:** recorded both rejection decisions, all four dated fitted-artifact cutoffs and
  falsifiable future tests of covariate-adjusted defender residuals and defender-five effects on attacker choices.
  Final checkpoint checks and push remain; no final-season test was used.
- **22 Nov 2026 · A1 S04 complete:** rim calibration was neutral (**−0.000259%** mean loss change versus
  **0.013718%** seed noise); the tracking increment was worse (**+0.00906%**, z **+3.76**). Both remain rejected.
  Independent typed-source tracking replay checked **4,605,515** values; **85** focused tests, **102/102** smoke and
  the expected failing fault check passed. The served v1.3 model and all bundle copies are unchanged.
- **22 Nov 2026 · A1 S05 80%:** NBA-only minute history completed its **200-game / 4,346-player-game** matched
  engine test. Pooled MIN CRPS changed **−0.00416** minutes (95% **−0.02699 to +0.01913**) against a
  **0.02634**-minute registered seed-noise floor; stars improved **−0.14916**, but the pooled primary gate is not met.
  The first preliminary gate reports instead used the **0.01653** half-width; their exact sources were preserved,
  the checker corrected and an asymmetric-interval regression test added. The corrected report does not change
  the NBA-only rejection.
  The separately queued strict-runtime test later completed; actual participants were supplied to both comparisons.
- **22 Nov 2026 · A1 S05 90%:** strict target allocation changed pooled MIN CRPS **+0.000268 minutes** (95%
  **−0.000111 to +0.000653**) against the **0.02634-minute** noise floor; all **69/69** tier/game and **10/10**
  pooled bias/coverage bounds were established. Independent bootstrap and raw-output accounting passed. Neither
  minute candidate meets the pooled primary win gate, so retain D29 for S06.
- **22 Nov 2026 · A1 S05 100%:** both minute candidates remain research-only; normal smoke passed **102/102**
  and deliberate fault exited **1** (**80/102** passing). The accepted v1.3/pathway-v1 systems and PWA bundle
  remain unchanged; the conditional panel is not an availability forecast. S06 uses the D29 control.
- **22 Nov 2026 · A1 S06 10%:** independent replay/accounting reconciled **11,277** substitutions and **23,160**
  ordered windows across **191** fixed-panel games; **9** games were quarantined. A conservative subset has **1,216**
  full-timeout substitution windows and **600** no-sub windows, excluding **156** ambiguous cases. It is not an
  exhaustive or unbiased legal-opportunity population and uses actual participants.
- **22 Nov 2026 · A1 S06 20%:** descriptive rates cover **39,380** player decisions with pre-game role tiers and
  score/foul/stint/rest/period states. Starter exits at selected timeouts are **27.2%** in 202 foul-trouble
  decisions versus **15.4%** in 8,651 others; these are confounded, outcome-selected descriptions, not calibrated
  hazards. Independent accounting reconciled all **2,790** outgoing/incoming labels.
- **22 Nov 2026 · A1 S06 30%:** constructed **18,160** out and **48,385** prospective-pool in rows using strictly
  prior S05 target proxies and current state. **45,604** unconfirmed incoming non-entries remain unknown; **9**
  entries fall outside the pre-window candidate set. All **66,545** rows independently reconciled; there is no
  claim that the inferred prior-box roster proves physical availability.
- **22 Nov 2026 · A1 S06 40%:** a frozen selected-timeout outgoing screen improved pooled Brier **0.127265→0.105985**
  over **70,480** decisions / **736** games, with **4/4** fold improvements and game-cluster 95% paired difference
  **−0.022412 to −0.020141**. Independent re-fitting reproduces all probabilities and 10,000-draw interval
  accounting. This does not establish an unbiased substitution hazard or an engine gain; incoming availability,
  joint selection and the pooled-minute engine gate remain open. Production and PWA remain unchanged.
- **22 Nov 2026 · A1 S06/S07 partial:** the 200-game S06 candidate screen failed explicitly after at least **40**
  games on a no-eligible-five foul-out; same-stream replay identified game **401810472**. No accuracy comparison
  or promotion is claimed. S07 F4's independent audit
  reconciled **5,208** known-label play proxies and **399** supported starter team-games: no-report Brier **0.15450**,
  infinite log loss; starter slots **78.05%**, exact five **30.83%**. F1–F3 and failure isolation continue;
  At that point A1 was **49.6%**, and the served model/PWA were unchanged.
- **22 Nov 2026 · A1 S07 30%:** the independently audited four-fold baselines cover **28,530** inferred candidates,
  **20,665** known play labels and **1,574** supported starter team-games. Starter-slot accuracy ranges
  **78.05–83.91%**; all no-report play-proxy log losses are infinite. Five F3 games have no prior roster; unknowns
  remain excluded. These are retrospective proxies, not dated status forecasts. A1 is **50.2%**; the served model,
  forecasts and PWA bundle remain unchanged.
- **22 Nov 2026 · A1 S07 40%:** all **5** retained timestamped report collections belong to the protected season;
  there are **0** dated report origins in the training or validation portion of every development fold. The
  status-to-play/start split is unsupported, so retain the fallback and dated-collection gate; A1 is **50.8%**.
- **22 Nov 2026 · A1 S07 50%:** report-status candidate calibration is unsupported, so the existing fallback remains.
  The future dated pre-tip collection gate requires at least **100 known player-games / 30 games** per assessed group,
  chronological splits and the unchanged paired promotion gates. Censored return/rest research remains; A1 is **51.4%**.
- **22 Nov 2026 · A1 S07 60%:** independently reconstructed **18,612** earlier-fold return/rest proxy predictions and
  their game-bootstrap intervals. Duration reduces return Brier by **0.00540–0.01380** across folds, with F1's
  interval crossing zero; role-based rest differences are tiny. These are retrospective known-listing play proxies,
  not physical injury recovery. No model or bundle changed; A1 is **52.0%**.
- **22 Nov 2026 · S07 spell follow-up, partial:** **1,493** recorded-DNP anchors and **29,860** simulated/analytic
  survival values independently reconcile. Star/starter horizons and longer tails lack the predeclared support;
  censoring may be informative. At the time, starter-frequency simulations and audits had not finished.
- **22 Nov 2026 · A1 S07 70%:** all four starter-frequency simulations and independent replays finished, checking
  **14,106,556** supported and **1,783,444** unknown-position worlds. Star starter frequencies were **88–93%**
  versus **65–76%** observed on inferred-roster proxies, not dated pre-tip forecasts. A synthetic short-roster
  stress test reproduced an existing silent activation of an unavailable player; that serving bug is unresolved.
  Engine, forecasts and PWA remain unchanged; A1 is **52.6%**.
- **22 Nov 2026 · S07 fallback work, partial:** an ingest/UI repair for missing and cross-team reports is under
  validation; all **five** retained valid roster-status inventories reproduce, **20** focused ingest tests pass,
  and initial dashboard checks passed **36/36**. It is not yet committed or delivered; short-roster and missing
  status safeguards remain. S07 remains **70%**.
- **22 Nov 2026 · S06 isolated robustness repair:** **3,000** worlds reproduce the earlier candidate and reconcile;
  another **1,000** saved worlds from the original failure game reconcile with the required technical. The
  single-game process exited 1 when its unsupported summary could not be serialized; no complete 200-game accuracy
  result exists. The repair is research-only; S06 remains **70%** and the served model/PWA are unchanged.
- **22 Nov 2026 · S06 flow preflight:** **3** same-policy games reproduced **321** game and **1,408** player
  values; independent quarter/component accounting passed. The fixed **200-game** flow screen is running, so
  there is no measured candidate gain yet. S07's censored-spell and starter-simulation sources are prepared and
  unit-tested, not scored.
  Production and PWA remain unchanged; A1 remains **52.0%**.
- **22 Nov 2026 · S06 fixed candidate, partial:** **200/200** games completed and independent flow/player
  accounting passed. Pooled minute CRPS improved **3.5662→3.5309**, clearing the preliminary seed-noise screen,
  but **3/69** non-inferiority bounds remain unestablished; direct state replay and confirmation remain. No
  candidate was promoted; S06 remains **70%**.
- **22 Nov 2026 · S06 90%:** the **200-game** same-policy replay reproduced **21,400** game and **95,612** player
  values; independent accounting checked **800** state totals and **191** common historical games. Selected
  close-state exits were **15.31% recorded / 11.91% simulated**. Because **3/69** frozen non-inferiority bounds
  remain unestablished, retain v1.3/D29 without a protected-season score. S06 evidence/checkpoint checks remain;
  A1 is **55.0%**.
- **22 Nov 2026 · S07 90%:** roster/report, unknown, cold-start and legal-five safeguards plus shared-origin preview
  handling passed **82** focused tests. Retain uncalibrated status/starter fallbacks; no future physical-absence
  hazard is supported. Old preview inputs contained one origin-day game and its timing is unverified. Fresh live
  forecasts, PWA delivery, smoke and checkpoint remain; A1 is **56.2%**.
- **22 Nov 2026 · S06 complete:** independent state accounting and fixed-screen decision retain v1.3/D29; **66/69**
  bounds established, so no promotion or protected-season score. Final smoke **102/102**, deliberate fault
  **80/102** as expected. S07's tested source is preserved but its live nightly and PWA delivery remain; A1 **57.4%**.
- **22 Nov 2026 · S07 complete:** the delivered ET-origin nightly rebuilt **241** pre-origin games and simulated
  **7 + 10** games at **10,000** worlds plus **10,000** season paths over **959** games. Independent accounting
  reconciled **340,000** player/team-world totals and **17** season/game identities. Status/start probabilities
  remain uncalibrated fallbacks: no dated development report cohort supports fitting them. Engine v1.3 and pathway v1
  remain active. Normal smoke **108/108**, fault **86/108** as expected, browser **72/72**, hosted PWA import/offline
  **17/17**. The **1,999-record** iCloud bundle needs manual device import; Pages shell `f2932e1` is data-free.
  S08–S14 remain future work; S13 history is deferred. A1 **58.0%**.
- **22 Nov 2026 · D42 planning:** the owner proposed splitting remaining work into two modular chunks and selecting
  five meaningful simulated games per matchup. HANDOFF specifies both chunk weights, dependencies, ten-rung
  modules, acceptance/fallback and final-nightly requirements. Planning only: no model, app, forecast or bundle changed.
- **22 Nov 2026 · D43 planning:** the owner requested an overhead animated court View Centre, first for saved simulated
  worlds and later for resulted games. The source-neutral player, event provenance and spatial limitations are
  specified; actual-game playback remains future work. Planning only; no simulations or app changes.
- **22 Nov 2026 · live handoff:** added a first-screen state/next-action summary and explicitly tied every completed
  D42 module to a refreshed log, verification and its own commit/push. No development or nightly was started.
- **22 Nov 2026 · S06 foul-out probe:** in a controlled world, an available substitute does not replace a player
  with six fouls because the current engine's foul-out mask is never updated. The finding is not a forecast gain
  or a population frequency; isolate and gate a repair alongside substitution research.
- **22 Nov 2026 · A1 S06 50%:** a frozen positive-versus-unlabelled incoming ranker improved selected-timeout
  entrant recall **13.22%→58.10%** over **10,711** entrants; an explicitly retrospective participant-roster diagnostic
  improved **45.23%→61.71%** over **10,680** entrants. All four folds improve; **84,344** ranks and game-bootstrap
  metrics independently reproduce. Both diagnostics condition on observed exits/counts, and neither proves current
  eligibility or an engine gain. The explicit joint selector preserves five and rejects insufficient replacements;
  actual engine integration and the foul-out repair remain open. Production and PWA remain unchanged.
- **22 Nov 2026 · A1 S06 60%:** isolated hooks passed **36** focused tests; the unchanged default reproduced **3/3**
  pinned games and **64** player-games to `1e-12` in **51 s**. The candidate completed the same games in **63 s**
  with **1,395** foul-out replacements across **3,000** worlds; independent aggregate accounting passed. This is
  wiring, not an accuracy result or promotion. S07's independent archive inventory is prepared without protected-outcome scoring.
- **22 Nov 2026 · A1 S07 10%:** independently audited **5** protected-season report collections and **18** pre-tip
  games; **634** unique roster/player-games have **331** listed, **128** unlisted and **175** missing final-box
  coverage. There are **0** development-season collections; no protected status/outcome scores were computed.
- **22 Nov 2026 · A1 S06 70%:** independently replayed **3,000** candidate worlds and **1,472,554** fives;
  player-minute reconstruction error ≤**1.78e-15**, including **1,395** foul replacements and **77** OT worlds.
  Trace capture reproduces the earlier candidate; short-roster/no-replacement tests fail explicitly as intended.
- **22 Nov 2026 · A1 S07 20%:** independently reconstructed **7,317** F4 prior-box memberships: **4,316** plays,
  **892** DNPs and **2,109** unknowns. Retrospective reason labels and the **4,346**-player-game actual-participant
  oracle remain separate from pre-game eligibility and status.
- **22 Nov 2026 · A1 S05 10–20%:** separated membership, physical availability, rotation entry, starts, healthy role
  and conditional/unconditional minutes. The 200-game prior-box audit found **73** All-Star rows incorrectly labelled
  regular season; NBA-only reconstruction restores **12** memberships. Audited **7,317** candidates, including
  **675** DNP-coach and **2,109** unknown; the 29 core returns in 24 games are below the reporting gate.
- **22 Nov 2026 · A1 S05 30%:** the D29 rotation replay matches **892** final player states exactly. Among known
  participants, rotation weighting pushes **22** additional ≥15-minute healthy roles below five minutes; the same
  coach-DNP evidence may also trigger a separate recent-absence fallback, but unobserved historical status prevents
  an actual double-counting claim. All **400** counterfactual team allocations sum to 240.
- **22 Nov 2026 · A1 S05 40%:** on the 4,346-player conditional panel, star / starter / bench minute CRPS is
  **2.891 / 3.024 / 3.980**, coverage **82.0 / 82.4 / 74.8%**. The NBA-only D29 history candidate improves star
  target MAE **0.328 min** but worsens bench target MAE **0.036 min**; this is not yet a full-engine comparison.
- **22 Nov 2026 · A1 S05 50%:** implemented the isolated NBA-only D29 history candidate, with same-day and two-team
  guards. All **4,346** fixed-panel candidate states match the independent target-screen build exactly; no
  production or engine-backtest path has changed.
- **22 Nov 2026 · A1 S05 60%:** exposed short-roster target underfill and >48-minute allocations; isolated strict
  runtime allocation conserves 240 to **1.43e-13 min** across 50,000 synthetic draws and all **400** fixed-panel
  absence cascades. It remains separate from the history filter and from production.
- **22 Nov 2026 · A1 S05 70%:** the corrected conditional and two incomplete-roster screens are independently
  reconciled across F1–F4. Their known outcomes are **5,218/5,225/5,013/5,208**, and F3 has five unscorable
  opening games. No-report control CRPS is **4.709/5.612/4.610/5.479**; the corrected strict target differences
  are negligible, not the spurious earlier Brier improvement. Full-engine checks remain.
- **22 Nov 2026 · A1 S05 ongoing:** the first strict allocator distorted target-play Brier by turning a zero target
  positive; the original source is preserved in `ab32eda`. The corrected candidate passes **30** focused tests.
  Its **17,303** conditional participant rows independently reproduce original control/NBA-only values;
  unconditional screens are still running and are not injury forecasts. Production and PWA remain unchanged.
