# MusNBA — game plan and progress

Updated **22 November 2026 (dashboard complete/public; A1 S01 underway)**. The single record of scope, progress and decisions. Every agent updates it at
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
  model changes require the measured gate. Each accepted version can rebuild a consistent season-to-date history (D39).
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
PLANNED A1 S13  versioned daily archives + dated-input/dated-fit season replay → atomic active-history generation
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
| 2 | Possession engine (data → models → engine → backtest) | `████████░░` **M1–M5b, M6a done · engine v1.3 is the app's default (D34), 10,000 worlds per game (D36) · backtest (M9) is the gate · NBA Stats matchups ingested; real-matchup defence not promoted (D37): team differences remain compressed (pool-0 offence ~64%, defence ~40% of observed effect) — A1 S01 underway; S02–S09 planned** |
| 3 | Evaluation and nightly feedback (Forecast Lab view, refit cadence) | `███░░░░░░░` **Forecast Lab page (`#/lab`), nightly projected-v-actual starters record (D33); refit cadence not started; A1 S11/S13 adds confirmation and versioned historical replay** |
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
| A1 | Expanded accuracy/robustness programme | ◐ **4.8% — S01 80%, 22 Nov**; 14 tasks, fixed weights, 140 rungs | Gates in §6b; final nightly + versioned history + successor chunk | HANDOFF § Progress ladders |

### 6a. Next chunk — A1: player accuracy, defence and trustworthy season paths

**Owner request, 22 Nov:** the earlier planning-only stop is lifted for overnight A1 execution. U1–U22 are complete; do not restart
that programme. This replaces the old four-task S1–S4 chunk with **14 modular subtasks (3.5× the task count)** and
substantially more modelling scope: M7, M8, M11, M12, full-fold confirmation and versioned daily history and season-to-date model rebuilds.
This is not a claim of 3.5× runtime or a promised accuracy gain. All subtasks started at **0%**; live progress is in HANDOFF.

**Two headliners:** (1) player outcomes that respond correctly to role, availability, game state and the defenders
actually faced; (2) calibrated joint game/season outcomes, with daily archives and a consistent season history under the current model. **Defence is central, not abandoned.** D37 rejected three particular variants; it did not show that
better defence is impossible. We will identify the loss of signal, then test different mechanisms with controlled
ablations. Player/lineup defence remains the design (D35); no team-rating input or post-hoc score scaling in the
possession engine. The team model remains a benchmark and the later-season engine.

The table defines scope and dependencies. **HANDOFF_NEXT.md § Progress ladders is the single live progress ledger**:
weights sum to 100; each subtask has ten explicit done-when steps. A task is complete only with evidence, a decision,
current docs, any necessary PWA delivery and a committed/pushed checkpoint. A well-tested negative result counts as completed research; merely
trying an idea or leaving a run underway does not. Data-limited work must deliver its coverage audit, safe fallback,
remaining gate and next action rather than claim a fitted model is validated.

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
| S13 | Current-model season history and daily archives | 5% | S11; S12 labels | Preserve every daily Today forecast and distinguish Tomorrow previews. Build a resumable season-start→latest-completed-date replay using the selected model recipe and strictly dated inputs/fits. Store histories by model version; activate a complete validated generation so the default dashboard consistently uses the current model. Retain prior versions/original forecasts for audit. Test cutoffs, retries, results joins, after-tip labels, reschedules and older imports; run the season rebuild after a trusted promotion, then S14's fresh live nightly. |
| S14 | Fresh nightly, delivery and successor chunk | 5% | S01–S13 decided | Run the final live nightly on the best promoted engines, 10k game/branch worlds and 10k seasons, with authorised fetch/input rebuild and iCloud export. Verify smoke/fault, dashboard and hosted PWA, visible bundle and archives. Write the next evidence-led chunk in this same format before final commit/push; leave exact first commands, ten-step ladders, weights and run gates for the next agent. |

**Execution order:** follow the dependency column, normally S01→S14. S02's download may run while CPU work runs, but
pause it for nightly provider fetches. Only one engine backtest at a time (measured CPU oversubscription). Every run
has a retained log and deterministic resume information. Do not launch speculative full grids: S03 selects two or
three plausible levers; screen cheaply, reject poor candidates, then broaden confirmation for survivors. Dependencies
mean documented decisions, not mandatory promotion of every module; a rejected component leaves its control in place.

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

**Current-model history is the default (latest owner clarification, 22 Nov).** Save each day's Today forecast;
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

**Final live refresh:** S14 always runs `.venv/bin/python scripts/nightly_musnba.py` after the model decisions and any
current-version season rebuild, pauses history fetching first, and verifies today/tomorrow (or next slate) plus a new 10,000-world
season. Use `--offline --no-rebuild` only if retained inputs are current and unchanged, with the reason logged;
never use it to bypass rebuilding inputs after feature/parser/model changes. Include every explicit D31 branch
at 10k worlds when branches are implemented. Archive replaced artifacts. Source commits go to `main`; a changed
static shell is published to `gh-pages` only, data remains local/iCloud. Check imports after bundle changes.

### 6c. Checkpoints, handover and the successor chunk

At every S completion, **update docs before committing**, then commit and push the reviewed source/docs/experiment
logs (no data). Record the checkpoint and remote status in HANDOFF's ledger at the next checkpoint, or use a named
checkpoint marker resolved by `git log` to avoid self-referential hashes. The completion summary includes the
measured outcome and whether the production model changed. Every partial-session stop also checkpoints resumable
state: exact command, log/output paths, PID if running, work completed, next rung, blockers and candidate status.
A scientific rejection closes the task only after its planned evidence and fallback decision are written.

**PWA obligation at each affected S checkpoint (owner, 22 Nov):** model promotion or changed stored forecast outputs
requires the necessary accepted-model refresh and iCloud export, with version/cutoff/world metadata and import/offline
verification. A changed app shell is rebuilt and published data-free to `gh-pages`, with service-worker compatibility
checked. Presentation/export-only changes can reuse current completed forecasts; research-only candidates leave the
served model/bundle unchanged. S11 therefore delivers any promoted model, S12 delivers its shipped app/output changes,
and S13 delivers the activated history generation; S14 repeats final delivery after its fresh nightly. Until a new
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
| `data/snapshots/<D>/` | Current daily snapshots (meta/games/season/stats); replacements archived. A1 S13 will add version/origin/run identity and active-generation history; not implemented yet |
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
**Phone app (owner, 20 Nov, D36):** stripped back — 10,000-world distributions for the expected lineup (players, teams, periods);
   no Scenarios, Given…, joint grids, duels or lineup branches (those stay on localhost).
2. **Decided (owner, 22 Nov):** make `MusaMoholo/MusNBA` public and copy MusSim’s personal GitHub Pages/iCloud flow.
   Only the data-free shell is published on `gh-pages`; simulations stay local/iCloud. App name MusNBA. **Live:** https://musamoholo.github.io/MusNBA/ (22 Nov; `gh-pages` e302d27).
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
2. **More depth on game outcomes**: richer, more sensitive graphs of player and team outcome distributions per game
   (lines, ladders, joint outcomes, how a line moves with a player in or out).
3. **Competition tabs**: NBA regular season · **NBA Cup** · **NBA playoffs** — the playoffs tab seeds the bracket from the
   standings as they are expected to finish (per simulated season) and plays the play-in and every round per world,
   MusSim cup-style (bracket probabilities by round).

4. **Lineup what-ifs** (owner, 20 Nov; D31): the nightly plays games with an uncertain high-impact player once per lineup
   scenario (X plays / X sits) and the Game Centre offers a lineup selector; later a localhost **lineup editor** (default
   expected lineup and minutes; change who plays and their minutes → minutes re-solved to 240 (D29), matchups re-formed
   (D30)) through a separate what-if runner. A1 S08 adds stored branches on localhost; phone exports keep Expected only (D36).

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

- **22 Nov 2026 · A1 execution underway:** owner lifted the planning-only stop. S01 is **80%** (A1 **4.8%**); both
  200-game controls completed, legacy fields reproduce to 1e-12 and quarter scores reconcile across **2,677** fold
  games. Independent-seed pooled MIN/PTS CRPS noise floors are **0.02634/0.00919**; one raw-box player outcome is
  missing. The prior-box cohort is separately labelled inferred availability, not actual-participant engine evaluation.
  Smoke **102/102**, deliberate fault **22 detected** and **15 focused tests** passed. Final manifest remains; no
  candidate, production model or PWA bundle changed.
