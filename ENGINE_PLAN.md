# Engine plan — possession-level simulator (phase 2)

**Updated 22 November 2026 — serving v1.3, A1 S01–S07 complete; later tasks remain open.** Sixteen LightGBM nodes, D29 target minutes,
D30 player/lineup defence, 10,000 worlds per game and one rotation table per world. Team pathway v1 handles later games.
M7 responsive substitutions, M8 shared form and M11 availability remain planned. U1–U22 and public Pages/iCloud delivery
are complete. PLAN §6a–6c defines the expanded next chunk; HANDOFF owns progress; TRAINING_PLAN §8 owns acceptance.

The dated decision table preserves how the design evolved. **D24/D26/D27/D35/D36 override older seven-day, player
carry-over, defence-input and phone assumptions**; D38/D39 add the next-chunk protocol and current-model history,
and D40 defers historical forecast backfill in favour of the current nightly. D41 stopped execution after that run;
D42 plans two future chunks, D43 defines the reusable View Centre, D45 clarifies laptop/phone delivery, D46 narrows
lineup branching, D47 requests a five-level availability scale, D48 proposes invalid-world replacement, and
D49 preserves simulated playing-time precision. D50 supersedes the possession-engine two-day horizon.
Sections below distinguish current behaviour from unimplemented design. Measured evidence lives in FINDINGS.

## Decisions so far

| # | Question | Decision (dated in each entry; later decisions take precedence) |
|---|---|---|
| D1 | Possession unit | Segments; an offensive rebound continues the possession with a 14 s shot clock |
| D2 | Quarter models | One model per decision, trained on every quarter, with period, clock and game state as inputs; per-quarter variants tested per node and kept only where they predict held-out games better |
| D3 | Form | Per-player, per-world form (efficiency, aggressiveness, shot selection) with role-dependent spread, plus a tested "heat check" response to in-game makes (§5) |
| D4 | History and dependencies | 2022-23 onward from hoopR (ESPN IDs) plus our own collection; `lightgbm`, `pandas`, `pyarrow` approved |
| D5 | Low-sample players | Profile- and role-based representation with stat-specific shrinkage and per-world talent draws (§7a); NBA data only — no college/international translations |
| D6 | Chain order | Owner's order: who → what (shot zone, turnover, foul drawn) → result → assist / block → rebound; turnovers split live (steal) / dead (§2) |
| D7 | Minutes | Target-aware substitution model, replay rotations as v0; variance sources and measured targets in §4 |
| D8 | Market lines | Evaluation only. Lines should emerge from a good ground-up model; injuries enter as availability inputs, so a late scratch needs a refresh run (§9). **Owner (20 Nov):** the goal is a ground-up simulation as accurate as possible against **real outcomes** — not betting. The market is a reference, not the target: if it is biased against actual results, we stay true to the outcomes. It is broadly rational, so a large gap is a signal to investigate (we may differ far from tip-off); compare with **closing** lines (final summaries' `pickcenter`), never fit to them. Measured: DraftKings' lines are unbiased against 2026-27 results (totals −0.6 ± 1.2, margin slope 1.09; FINDINGS §3m) |
| D9 | Watch a sim | Keep five sampled worlds per game. **Owner (20 Nov):** the Game Centre should offer a saved sim's play-by-play — first as a list like nba.com's play-by-play (period, clock, team, description, score), then a visual play-through on the running clock (M10) |
| D10 | Speed | Nightly budget ≤ 60 min. The engine runs LightGBM in the loop; no lookup tables (§9) |
| D11 | Refit cadence | Refit when 7 or more days have passed since the last successful refit (date kept with the model), or when forced with `--refit`; features update nightly |
| D12 | Pre-tip refresh | Deferred to polish (phase 5). **Owner (20 Nov): not needed** — lineup branches for every maybe (D31) cover late changes |
| D13 | Two horizons | *(Engine window for the dashboard superseded by D24: today and tomorrow.)* **Near term** (next 7 days, ~50 games): full engine, 10,000 sims per game, player and period outputs. **Long range** (rest of season): team-strength model calibrated to the engine — win %, score, spread only (§12) |
| D14 | Season sim | 10,000 universes, every remaining game once per universe (as MusSim); universe *k* uses world *k* of each near-term engine sim, so both horizons share the same draws (§12) |
| D15 | Absences | Season universes sample future injuries and rest from players' historical games-missed patterns, on top of reported injuries and return dates (§12) |
| D16 | App beyond 7 days | Only win %, expected score and spread, labelled as a long-range estimate; no player or period detail |
| D18 | Inputs and updates | The possession models never take team strength as an input — only the ten players' profiles, game state and context; team strength is an output. Within the 7-day window each world plays a team's games in order, and after each game that world's player stats and form update from the simulated box score before the next. Beyond the window, team ratings start from an Elo/ratings fit on this season's real results and update in each world from its simulated games **Evidence to weigh (20 Nov, backtest FINDINGS §3o):** the engine expresses the opponent's defence at ~25% of its real effect (points per 100 load 0.42 on the opponent's defensive rating v 1.69 in real games; offence 0.80 v 1.14), and loses to a plain team-rating model on margins and wins. First route inside D18: player on-court defence with lighter shrinkage, judged by the backtest (not node log loss alone). If that cannot close the gap, the owner decides whether opponent defensive rates (shot-making allowed by zone, turnovers forced) may enter the possession models |
| D19 | Game types | One model per decision across regular season, NBA Cup, play-in and playoffs, with game type (and playoff round) as an input; game-type sample weights tested on the folds. Measured: playoff starters +3.0 min, top player +3.6, top-8 share 93.8% v 90.6%, pace −4%, points per possession 1.108 v 1.128 |
| D20 | Decision chain | Owner left the number of steps to the data. Fifteen decisions in four stages — **clock**: time to the event, event type (action, defensive foul, violation); **action**: who (of five) → what (rim, paint, mid, corner 3, above-break 3, turnover, fouled on a 2, fouled on a 3) → shot result (miss, make, and-one); **credit**: assisted → assister, blocked → blocker, turnover type (steal, offensive foul, other) → stealer, fouler; **after**: free throw, rebound (offence/defence × player/team) → rebounder. Rules, not models: free-throw counts, penalty/bonus, shot clock, period ends, foul-outs. Every node has ≥ 50k training rows |
| D17 | Long-range strength | MusSim's per-world pathway: each universe starts from a draw around today's strength and updates every team after every simulated game — near-term engine results included — by the rating system's own response to the result, against the world's own expectation, with one gain calibrated to real season dispersion (§12) |
| D21 | Shot location; team turnovers | **Engineering decision from data (19 Nov); owner confirmed the location stage (19 Nov) — team turnovers and team rebounds stay outcomes of existing stages, not new ones.** A 16th decision, **location** — the shot's distance band (21 bands, 3–5 per zone) given zone, shooter and context — sits between *what* and *shot result*; later decisions see the band's mean distance and lateral offset. Reason: distance is the strongest input after zone (leaving it out costs 3.1 nats per game over the chain: blocked +3.8%, assisted +1.1%, shot result +1.0%) and no step produced it. *Event* gains a fourth class, **team turnover** (shot clock, 8 s; 5.3% of turnovers), which credits no player. All-Star and exhibition games are excluded from every dataset |
| D22 | Default model and the floor | *(Original decision; v1.3 now serves under D34.)* **Owner (19 Nov): the possession engine v1 (`scripts/engine.py`, `models/v1.json`) is the dashboard's default projection from now on, and it is the floor** — a later engine, model version or rule replaces it only when the backtest/aggregation tests show it is better (M6a, M9). The placeholder `baseline-v1` stays for retrospective backfills (the engine reads latest profiles, so past dates would leak) and as a comparison saved beside each engine snapshot. The season simulation is still the placeholder's team-strength pathway, fed the engine's win probabilities for today's games |
| D23 | Rebound clock convention | **Engineering decision from data (19 Nov), under D22's test.** From 2026-27 ESPN stamps every rebound with the clock of the miss it follows (100% v 7–12% in every earlier month; FINDINGS §3k). Every season's segments now use that convention (`possessions.py`, default `--rebound-clock miss`), so history and live inputs are built alike. Measured: on live-style held-out rows the old models are worse on 12 of 16 nodes (chain +34.1 nats per game) and M6a box scores improve (threes bias +7.4% → +1.0%, steals +9.6% → +0.8%, turnovers +8.0% → +1.5%, defensive fouls −20.5% → −1.0%; CRPS lower on every stat but blocks, level). **v1.1** (v1's settings on this data) replaced v1 as the engine's models; v1 and its data are kept (`data/derived/variants/rebound_feed/`) |
| D24 | Engine horizon: today and tomorrow | **Owner (19 Nov): the engine projects today's and tomorrow's slates, always** (replaces D13's seven-day near-term window for the dashboard). `nightly.py --ahead 1` (default) builds tomorrow's snapshot from what is known today — injury report, profiles through the last final — and rebuilds it the next night (the old one archived). The app's as-of date for standings and rosters stays the newest snapshot dated today or earlier (`views.current_snapshot`). Long-range games (D13/D16) are unchanged |
| D25 | Season beyond tomorrow | **Owner (19 Nov); built 20 Nov as team pathway v1 (`scripts/pathway.py`, called by `projection.simulate_season`).** The nightly simulates today's and tomorrow's games with the engine and keeps each game's per-world points (`engine_worlds.npz` in the snapshot); one season is then played as of today: universe k takes engine world k mod W for those games, and every later game, in date order, draws both scores from that universe's own offensive and defensive ratings, after which both teams move by the rating estimator's response (1 / (n + 1 + K), K = 8) to the surprise against that universe's expectation (zero on average). **Spread calibrated on the walk-forward season test (M12 first cut, FINDINGS §3n):** start draw 0.4 × the estimate's posterior SD, the estimator's own gain, a 20-game memory (the gain stops shrinking after 20 games) — dispersion of final wins 1.00 (the old fixed-probability season sim: 1.53), 10–90% coverage 84% (65%), CRPS 2.611 v 2.727; chosen in 3 of 4 leave-one-season-out folds. Engineering decision from data: v1 replaces the fixed-probability season sim. Still slightly wide in November and its surprises fade with the date where real ones persist (0.40) — M12 continues. Today's and tomorrow's snapshots carry the same season (as of today) |
| D26 | **The dashboard's two engines — the daily flow** | **Owner (20 Nov), the overarching design; D13/D14/D17/D24/D25 are parts of it.** On any date D: **(1) Result** every game played before D (real scores, box scores, play-by-play). **(2) Play-by-play engine** for today's and tomorrow's games — or, if neither day has games, the next slate: every possession simulated, with every input (player profiles, form, roles, rotations, team style, injuries) carried over from all games before D, in MusSim's spirit; `nightly.py` rebuilds those inputs from the latest finals before it runs. **(3) Team engine** for every later game, MusSim-adjacent: each world (universe) k carries its own ratings per team — offence and defence — that start from the real-results estimate as of D plus a draw at its uncertainty, take in world k's play-by-play results first, then play every later game in date order, each simulated result updating both teams' ratings *in that world*. A March game is played with the ratings that world's own simulated path produced — **never today's ratings carried unchanged to March**; pathways are fully dynamic. **(4) Season outputs** (standings, seeds, play-in, long-range win %) are counts over the worlds. Each engine has its own trust test against real outcomes: the play-by-play engine the walk-forward backtest (M9: totals, margins, win calibration, players), the team engine the walk-forward season test (M12: dispersion of final wins ≈ 1.0, persistence). Within the play-by-play horizon nothing else needs to carry per world (D27) |
| D27 | Carry-over inside the play-by-play horizon; how the team engine moves | **Owner (20 Nov).** (a) The play-by-play engine only ever plays the first games after the latest results (today, tomorrow), so the nightly input rebuild is all the carry-over it needs; no per-world player state is carried from a simulated today into tomorrow. The one link — a team playing on both days — is small: rest and schedule inputs were neutral on every possession-level decision (FINDINGS §3h). (b) The team engine stays MusSim-style: an offensive and a defensive rating per team, each game's points for both sides derived from them (offence against the opponent's defence, pace, home court), and ratings that move on the *points* surprise against the world's own expectation, with an Elo-like gain that starts large and settles (D25). Winning or losing moves nothing by itself, so a team can win the ratings battle, lose a close game at random and keep its ratings — a good loss. A results-only Elo is a comparison to measure, not the design |
| D28 | **Guiding light: players first** | **Owner (20 Nov).** The play-by-play engine exists to show how individual players perform, and a team's results are the aggregation of its players. Every effort goes into player outcomes — minutes, per-possession performance, and the defenders and lineups they face — and team results, short and long term, are expected to follow from them. The engine stays the dashboard's default for today and tomorrow (D22); the team-rating model is a yardstick its summed outcomes must beat on the backtest, never a replacement or a side-by-side win %. Engine work is judged first on the backtest's player outcomes (bias by tier, 10–90% coverage, CRPS for minutes, points, rebounds, assists), then on the team sums (strength loading, margin slope, CRPS v the team model) |
| D29 | Minutes: healthy roles, 240 per game, stars first | **Owner (20 Nov), design for the next chunk.** Recent minutes are contaminated by absences (a backup's minutes inflate while the starter is out; a returning star's recent minutes are zero), so: (1) each player's **healthy-role minutes** — a decayed average over games where the team's core was available — and a **priority** (the coach's pecking order: starts, minutes rank, usage); (2) per game, **allocate 240** (+ 25 per overtime) **by priority**: fill the highest-priority available players up to their healthy-role minutes, each capped by his own observed maximum, then share the rest down the rotation in proportion to healthy shares, rescaling and capping until the sum is exact — a star's absence cascades to the players who historically absorb his minutes, and reverses when he returns; (3) a **return ramp** after long absences, learned from history (minutes in the first games back after N games missed, v healthy minutes). Targets are drawn per world (D7) so minutes have honest ranges. Near term the replayed stint templates are rescaled to these targets (today they give stars full-strength minutes in every world: +6.5% in the backtest); M7's substitution model later treats them as a soft pull (blowouts, fouls). Judge on the backtest's minutes by tier (bias ≈ 0, 10–90% coverage ≈ 80%) and on returning-star games specifically |
| D30 | Defence: implicit matchups from ESPN data | **Owner (20 Nov): stay on current data and take the implicit route as far as possible; NBA tracking only if it stalls (PLAN §9.1).** Position is only a guide — a guard can defend a forward depending on the five on the floor — so each shooter gets a **soft assignment**: a probability over the five defenders on court from size (height, weight), role and position similarity, recomputed for whoever is on the floor (small v big lineups shift it automatically). It can be partly **learned from play-by-play**: the defender credited with a shooting foul or a block is the defender who affected that shot (owner, 20 Nov: if not the assigned man, close enough to count) — use those credits as given for shot outcomes; for fitting *who guards whom*, lean on fouls on jump shots (mostly the on-ball defender) more than rim blocks and rim fouls (often a rotating help big), then fit assignment weights (1.2M possessions). The shooter's likely defender then enters shot result and what (and turnover/steal) **weighted by that assignment** — his opponent shooting allowed by zone with much lighter shrinkage than §3l's, size, steal/block rates, recent defensive form — plus help defence (rim protection on the floor for every rim attempt). Also unused today: **shot type from the play text** (pull-up, step-back, driving, cutting, alley-oop, catch-and-shoot by assist) — a shot-quality and self-creation signal. Judge by the backtest: player points by tier, then `strength_loading.opp_defence` (0.42 → real 1.69) and margins. Reason: §3o — defence is expressed at ~25% of its real effect, which inflates shooters' makes against good defences |
| D31 | Lineup scenarios in the nightly (what-ifs) | **Owner (20 Nov).** For each game with an uncertain high-impact player (questionable / doubtful / day-to-day, and a large healthy-role minutes share or usage), the nightly also plays the game per lineup scenario — "X plays", "X sits"; two such players → four scenarios, more → each one out alone — with deterministic seeds per scenario, saved in the snapshot; the Game Centre gets a lineup selector (Expected · X plays · X out). **Owner (20 Nov): each scenario is its own independent run with the full 10,000 sims** — two branches of the same game. The headline **Expected** view is not a third simulation: it is the branches blended by the injury report's availability (X Questionable 50% → half "plays", half "sits"; two uncertain players → four branches weighted p1·p2 …), so it always sits exactly between the branches; the season sim draws from the same blend. Availability comes from the injury report (Out 0, Doubtful 0.15, Questionable 0.5, Day-to-day 0.7, Probable 0.9); starters from a **projected-lineup source** (owner, 20 Nov: RotoWire-style sites publish projected starters — PLAN §4; recent games when none is available) and minutes from D29. **Owner (20 Nov): projected starters are enough; choose the source that is most honest about maybes** (game-time decisions, questionable starters) — its maybes join ESPN's report in defining the branches, so a late change is already simulated and **no pre-tip refresh is needed** (D12). **Sims: 10,000 per game and per branch** (owner; the engine runs 2,000 today) — ~100–125 s per run, a two-day slate of ~14 games + 3–4 branches ≈ 30 min sequential, ≈ 12–15 min with 2–3 games in parallel: inside D10's 60-minute budget. Needs D29 (a sitting star's minutes must cascade right). Later, on localhost only, a **lineup editor** (set who plays and expected minutes; D29 re-solves to 240, D30 re-forms the matchups) through a separate what-if runner that writes a labelled what-if snapshot — serving still never computes; the phone app shows precomputed scenarios only (PLAN §9b) |
| D32 | NBA Stats API for defence | **Owner (20 Nov, during the D29–D30 chunk): go with the unofficial NBA Stats API (browser-style headers) for richer data** — answers PLAN §9.1. Evidence: ESPN credits identify who guards whom only weakly (soft assignment top-1 26% v 20% random; matchup-weighted defence ≈ on-court defence, r 0.96–0.97; FINDINGS §3q). **Next chunk:** a second adapter with raw retention (polite, cached, one pass per season), a crosswalk of players and games (name + team + date → ESPN ids), and a reconciliation/cleaning pass against our ESPN data (mismatches expected); then defence on real matchups (partial possessions per defender, shooting by defender distance), judged by the backtest's player outcomes and `strength_loading.opp_defence` |
| D33 | Lineups without forbidden sources | **Owner (20 Nov):** where a site's terms forbid automated access we do not scrape it — the owner may check such sites by eye; we predict lineups and the maybes ourselves. Built: projected starters from start share and priority (`minutes.projected_starters`; 89.4% of starter slots right on Jan–Apr 2026 with known availability), ESPN's injury statuses for the maybes, and a nightly record of projected v actual starters (`scripts/lineups.py`, `data/derived/lineups/accuracy.json`). Next: a learned lineup and availability model (questionable/probable/day-to-day → chance to play and to start, from ESPN report history), and the localhost lineup editor (D31) for the owner's overrides. FantasyPros (terms silent on automation, single personal copy) stays a manual reference |
| D34 | Engine v1.3 | **Engineering decision from data (20 Nov), under D22/D28's test.** v1.2 (D29 minutes on v1.1's models) and v1.3 (D30 defence inputs + D29 minutes) promoted in turn on the same 200-game F4 backtest: players first (minutes bias +6.5% → −1% for stars, coverage ≈ 80%; no tier worse with defence), then team sums (defence loading 0.42 → 0.69 of real 1.69; margin CRPS 9.64 → 9.37 v the team model's 9.32). Matchup θ fitted through 2025-12-31 and kept for production so the final test stays out of sample for it. FINDINGS §3p–§3s |
| D35 | Defence stays player- and lineup-based; switch hunting | **Owner (20 Nov, D32 chunk):** a team's defensive rate in real life is drawn from the individual defenders in the lineup, so the engine keeps defence **strictly player- and lineup-dependent** — team defensive ratings never enter the possession models (answers D18's open question: no). Team defence is the aggregate of the five on the floor and how they are deployed (who guards whom, help at the rim). **Attackers hunt switches onto weak defenders**, so deployment is chosen by both sides: the assignment gets a hunting term (attacker usage × defender weakness, beside size, ranks, stopper tendency and pair history) and the *who* decision sees each attacker's likely defender (a mismatch draws the ball). Tested as v1.4d after v1.4c on the same backtest |
| D36 | Phone app stripped back; localhost full; 10k worlds | **Owner (20 Nov, D32 chunk):** the phone (PWA bundle) carries the **10,000-world distributions for the expected lineup** — players and teams, every period — and nothing that needs the per-world files: no Scenarios, Given…, joint grids, duels or duel of the night, and no lineup branches (D31 stays a localhost feature). `export_musnba.phone_record` leaves out `api/game/<id>/worlds` and switches the flag off. Localhost keeps everything. The dashboard moves to **10,000 worlds per game** (D31's number) and **one rotation table per world** (minutes from 5× more distinct draws), the latter measured on the backtest first (minutes CRPS/coverage not worse). Reason: smoother, honest distributions (2,000 worlds: sampling noise ±10–20% per histogram bar, FINDINGS §3v) without a heavy phone bundle |
| D37 | Real-matchup defence not promoted; v1.3 stays | **Engineering decision from data (20 Nov), under D22/D28.** NBA Stats matchups (D32) ingested and reconciled (FINDINGS §3t); the pre-game assignment on real shares is far better (top-1 36% → 50%, top-2 75%; §3u); defender traits measured (3PA share allowed r 0.77, 3P% allowed noise). Three engine candidates on the same 200-game backtest — v1.4c (real-share defender quality and θ), v1.4e (+ deterrence), v1.4f (+ top-1/top-2 defenders with confidence) — none beats v1.3 (margins level or worse, totals worse, players level or worse; §3w). Switch hunting (D35) shows no effect in who guards whom or who shoots (v1.4d not run). The data, crosswalk and assignment stay (nightly keeps them current; the Matchup view's who-guards-whom uses them). Reading: the engine compresses team differences generally (offence loading 0.73 v 1.14 real, defence 0.69 v 1.69 real; most component ratios 20–40% except turnovers), so the next engine work targets that compression, not more defender inputs |
| D38 | Larger accuracy chunks and durable checkpoints | **Owner (22 Nov).** Replace the queued four-task chunk with a substantially larger modular programme (A1, 14 tasks), fixed weighted percentage progress and ten concrete steps per task. At every task completion update all affected docs, commit/push under the standing Git rule, and give a high-level result summary. Every actual development chunk ends with a fresh nightly and a fully specified successor chunk in the same format. Every affected subtask also delivers necessary PWA model/data/shell updates (latest owner clarification). The original session was documentation-only; overnight A1 execution has since started. Defence remains a priority; negative variants are evidence about those variants, not a reason to abandon defence. |
| D39 | Daily forecasts and a consistent current-model history | **Owner (22 Nov, latest clarification).** Store each day's Today prediction, with Tomorrow as an origin-dated preview. With a new accepted model, support rerunning season start→now so the default dashboard uses that model consistently. Preserve original and prior-version generations, but use the active version for normal historical review. Rebuilt predictions use the current frozen recipe with only pre-origin inputs and fitted parameters; label them retrospective, never originally published forecasts. Ordinary browsing reads stored predictions/results. See §17 for cutoffs, versioning, resume and atomic activation; the final test remains protected. |
| D40 | Defer historical forecast backfill | **Owner (22 Nov, during A1):** “forget nightly backfill. lets just get nightly for next slate (today and tomorrow relative to this date). since were probably not at a perfect model yet”. Do not run or implement the S13 historical forecast replay during this A1 execution; preserve existing snapshots and history. Use the accepted engines for the current ET-origin Today/Tomorrow slates or next slate. The required rebuild of pre-origin model inputs and the 10,000-world future season simulation are not historical forecast backfills. D39/§17 remains a future safety design, not an instruction to run a replay now. |
| D41 | Stop after the active nightly | **Owner (22 Nov):** “well stop after this nightly run, anything undone is future work”. Finish the currently running S07 nightly, its required verification/delivery and checkpoint, then stop; do not start a second nightly or S08–S14 in this session. Keep all uncompleted work explicitly open for a future session. This S07 delivery is not completion of the integrated S14 or the A1 chunk. |
| D42 | Two future chunks and selected game worlds | **Owner proposal (22 Nov):** “split the rest of A1 into 2 chunks”, each delivering modular outcomes and a dashboard improvement if no model improves; retain five meaningful simulated games per matchup. Plan the split in HANDOFF/PLAN without resetting the original A1 progress or starting execution. Five labels may share a world; extremes are conditional examples, and the representative Expected game is a real selected world, not a synthetic mean. Existing cutoffs, model-promotion gates, data retention and D40 remain unchanged. |
| D43 | Reusable 2-D View Centre | **Owner (22 Nov):** “a view centre that takes a play-by-play file from a world and can play it out ... 2-d aerial view of a court with events overlaid”, and “that same view centre will later be used to play out resulted games play by play”. Plan one source-neutral renderer/player; Chunk A first supplies reconciled simulated-world files, while a later actual-game adapter uses retained data and remains distinctly labelled. Display supported shot zones/bands or validated recorded positions, never invent player tracking. Ordinary viewing never fetches or simulates. D40 still defers historical *forecast* reconstruction. |
| D44 | Player filters and shooting distributions | **Owner (22 Nov):** replace fixed minimum-game filters with a season-adjusted minutes proportion and group shooting makes, attempts and percentages, using judgement about honest percentage presentation. This supersedes the earlier player-sheet restriction on attempts. New simulated period percentages are derived from paired makes/attempts, conditional on a positive attempt count; display the no-attempt chance separately. Delivered without a model promotion. |
| D45 | Laptop PWA is primary | **Owner (22 Nov):** “laptop pwa is the main one bro, phone is just a stripped back version of that”. This corrects D36's localhost-only delivery assumption, not its phone restriction: the laptop bundle retains the full saved per-world data and dependent features; the phone bundle remains stripped. Both are imported explicitly, and Pages remains data-free. No model or forecast changes follow from this delivery correction. |
| D46 | At most one impactful uncertainty per team | **Owner (22 Nov):** consider only the most impactful uncertain player on each team, and only if he is among that team's top three impactful players. At most two players per game give at most four exhaustive branches; other uncertain players retain their existing world-by-world availability draws. Engineering proxy to implement and label: rank the full origin roster, including players already out, by D29 healthy-role minutes multiplied by the existing pre-origin shrunk points-plus-0.7-assists-per-minute `projection.player_inputs` value; ties use player ID. This is an offensive contribution proxy, not measured total or defensive impact, and cold roles must be identified as priors. Select the highest-ranked uncertain player within the top three per team, if any. This supersedes D31's larger-selection rule and A1's earlier 15-minute/usage/missing-data threshold; it does not calibrate availability or establish two-player independence. |
| D47 | Five-level lineup availability | **Owner (22 Nov):** use 0%, 25%, 50%, 75% and 100% as a simpler lineup-certainty signal. Research candidate: map each prospective availability assumption to its nearest quarter, with exact halfway ties rounded up; preserve uncertain inputs strictly inside 0 and 1 by limiting them to 25–75%, so a reported uncertainty is never made certain. Thus current doubtful 15% → 25%, questionable 50% → 50%, day-to-day 70% → 75%, probable 90% → 75%, unknown 60% → 50% and recent-inactivity 80% → 75%. Zero and one remain zero and one; unlisted Active remains an assumption, not a medical guarantee. Apply the same candidate scale to all prospective roster availability, while unselected players continue per-world draws. Keep original values and their sources in provenance. Branch preparation re-solves starters using the existing 0.9 near-certain threshold, so a scaled 75% probable no longer qualifies as near-certain; evaluate that interaction before any production integration. These are engineering assumptions, not calibrated injury probabilities; compare the change using the applicable player-first gates, and do not silently change the served model. Pre-D47 captures retain their original probabilities as wiring evidence. |
| D48 | Invalid-world replacement fallback | **Owner (22 Nov):** generally continue until 10,000 valid worlds exist instead of letting an isolated random-world failure abort the simulation. This is a proposed, explicitly labelled fallback, not implemented in production. Only explicitly identified world-local recoverable failures qualify; missing inputs, model corruption, cutoff violations, accounting defects and unknown/systemic exceptions still fail immediately. Count and preserve every rejected attempt and its reason; cap retries and fail rather than conceal frequent failures. Rejection conditions the result on avoiding the invalid state, so measure its rate and effect and compare the short-roster case with the existing isolated S06 foul-penalty exception under unchanged player-first gates. Deterministic replacement needs world-local isolation: the current vectorised engine shares random streams, aborts the batch on the exception and cannot simply restart one world while claiming the other worlds are unchanged. Never silently activate unavailable players or claim NBA exception support; retain the proper rule as the long-term fix. |
| D49 | Preserve playing-time sensitivity | **Owner (22 Nov):** “why round minutes to whole numbers, we can preserve seconds as far as i care, just better sensitivity”. Preserve the engine's full available precision in saved world data and apply minute/second conditions to those unrounded values; formatting and histogram bins may be rounded only for display. Availability is distinct from positive playing time. The existing production bundle stores rounded full-game minutes, so it remains unchanged until a compatible contract, regeneration, tests and delivery pass; do not claim its lost precision can be reconstructed. |
| D50 | Today-only possession horizon | **Owner (22 Nov):** remove tomorrow from the play-by-play slate and discard tomorrow's old possession forecast from the active dashboard: player/possession sensitivities are for today only. Each nightly results prior games, builds possession forecasts for today's ET games only and uses the season team engine for tomorrow onward; expose future team-level distributions from its season worlds. Label pathway score distributions regulation: tied scores have the winner resolved separately without overtime points. Preserve originals/archives, do not fabricate historical predictions, and show existing pre-tip forecast-versus-result analysis where available. Fresh season output is still required on game-free days. Deliver affected PWA/output changes. Implementation pending. |

**D48 isolated prototype:** `a1_world_retry.py` supplies independent per-world/attempt seeds and explicit
per-world/total caps to research callbacks; `ExhaustedEligiblePlayers` classifies only the branch repair's
post-foul-out shortfall. No engine/nightly caller uses this coordinator. A synthetic-injection development
probe preserves unaffected seeds and complete captured arrays, but is not a real-failure or bias estimate.
The single-world stream intentionally differs from the production vectorized stream. FINDINGS records a
separate synthetic demonstration of rejection bias; real rates, comparison and gates remain open.

**A1 20% partial implementation:** an opt-in foul-out policy can return a boolean mask over active worlds; only
masked worlds' lineup-dependent features are refreshed. Boolean policies and no-policy execution keep their existing
path. Masked substitutions with mismatch features fail explicitly until those features are supported. This is a
wiring change, not promotion; the frozen branch replay and player-first gates remain open.

## 0. What "true to form" means

The engine is right when, on held-out games, its simulated distributions match reality. Numbers below are historical
reference populations (see §1/FINDINGS), not universal targets; A1 evaluates each measure on its matched held-out cohort:

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

**Implementation gap found in A1 S06:** the serving engine's foul-out mask is initialised but not updated. A
controlled six-foul state remains on court despite an available substitute (FINDINGS § A1 S06). This is a defect
against the rule above; the repair must be isolated and pass the same paired engine gates before replacing v1.3.

## 3. Time and possessions — the owner's clock idea, refined

Owner proposal: simulate each quarter from 0 to 12 minutes with possessions sprinkled along the
timeline, sampling observed time per possession, and accumulate minutes from it.

**Implemented: the engine runs on the game clock**, with one refinement: each segment's duration
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

**Planned M7 (A1 S06): a target-aware substitution model.** Currently v1.3 rescales replayed rotation tables
to D29 per-world targets; these do not respond to simulated score or ordinary foul trouble. The design below is not
serving. S05 tested role/minute candidates; S06's isolated state-responsive candidate improved pooled minute CRPS but
did not establish all frozen non-inferiority bounds, so v1.3/D29 remains selected. Its foul-out repair is not
silently promoted; the production mask defect remains an explicitly documented limitation.

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
3. **Per-player form, per world (D3; planned M8/A1 S09, not yet serving)** — at tip each world draws, for every player, a night's form in
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

**Measured runtime, not the original design estimates:** on the 21 Nov close-out, 10,000-world games with one
rotation table per world took about **130–150 seconds/game**. The 200-game F4 pool-0 backtest at 1,000 worlds took
**1,365 seconds** (FINDINGS §3v). A 13-game live refresh completed in the dashboard close-out; new substitutions,
branches and dated season rebuilds must be benchmarked separately. Run one backtest at a time; concurrent ones
oversubscribe the laptop. Report log-derived rates and completed items, not invented deadlines.

D10's **≤60-minute live nightly** remains the acceptance budget; the original ≤60-second single-game aspiration is
not met at 10k worlds and must not be quoted as current performance. Full-season historical rebuilds are separately
resumable batch jobs, not work the server performs or that must fit a single live-nightly budget. No lookup-table
approximation is adopted: near-term inference stays in LightGBM; the horizon is **today/tomorrow or the next slate**.

**Cadence (D11; scheduled model refit/promotion automation still unimplemented):** player/team features, injuries and availability update every night — that is
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
- **Current promotion floor:** engine v1.3 and pathway v1, not the superseded placeholder. TRAINING_PLAN §8
  and PLAN §6b specify player-first paired confirmation, uncertainty, robustness and final-test gates for A1.

## 11. Outputs

- Today's contract (periods q1–q4/h1/h2/fg for teams and players), so the app needs no change.
- New: lineup minutes per team, and **"watch a sim"** logs — full event timelines for a few sampled
  worlds, for the planned 2-D View Centre (clock runs, events appear, the box score fills; D43). A shared
  event interface leaves room for later resulted-game playback without silently mixing sources.

## 12. Two horizons and the season simulation (D13–D16)

**Delivered two-engine flow (D24–D27):** the possession engine ran Today and Tomorrow from the same origin's
pre-date inputs; every later scheduled game used the per-world team pathway. D50 supersedes that horizon with
today-only possession forecasts, but its live output delivery remains pending. The earlier seven-day design in
D13/D18 is also superseded, not an open choice.

A delivered S07 correction makes that origin explicit in snapshot metadata and team/player/period inputs; the
engine now guards profiles and uses pre-origin minutes, stints and pair history. Older previews without explicit
origin are not certified cutoff-safe. Forecast completion,
not simulation start, is needed for a pre-tip label. Older outputs without completion metadata remain timing-unverified;
their original fields are preserved, not reinterpreted as proof of publication.

For the in-progress D50 late refresh, snapshot schema 1 may carry `game_provenance_schema: 1` and an original
metadata record per game. Consumers resolve the game's record rather than claiming the new season's completion
time for an old forecast. Retained game summaries, placeholder and player/team worlds must match the old snapshot;
their model and cutoff stats must equal the new season context. The season uses those same worlds. A replacement for
an existing verified pre-tip forecast crossing tip while staged or archived stops publication; it is not
automatically retried. Mixed live delivery,
per-origin availability auditing and PWA validation remain pending.

S06's selected-timeout substitution candidate is not promoted: its fixed player-first screen improved pooled minute
CRPS but did not establish all registered non-inferiority bounds. v1.3's existing D29 path remains the control and
served policy; the state-response replay is descriptive and uses actual participants (FINDINGS §6a).

Universe k takes world k of each near-term engine game (modulo available worlds only where counts differ); those
results update its own offensive/defensive ratings before later games. Later games draw scores using that world's
ratings, then update against that world's own expected points. The ratings are never frozen at today's values.
The estimator starts from pre-origin season ratings plus uncertainty; current pathway-v1 settings are K=8,
start scale=0.4, update scale=1, memory cap=20 games (FINDINGS §3n). Each game's winner and every season probability
come from those same worlds. Today/Tomorrow snapshots share one origin-date season forecast.

**M12 measured first cut:** 480 team-starts (four dates × four historical seasons × 30 teams), dispersion 1.00,
10–90% coverage 84.2%, final-win CRPS 2.611 versus fixed probabilities 2.727. Per-date persistence still fades
(0.52→0.18 simulated versus about 0.40 observed); November is too wide. A1 S10 tests improved starting estimates,
gain/drift and availability with leave-one-season-out selection. Ratings may enter the **team pathway**; D35
still prohibits feeding team defensive ratings into possession models or forcing their scores to match a benchmark.

**Planned availability (D15/M11, A1 S07/S10):** reported absences and uncertain returns, historical injury/rest hazards
and durations, with role-specific evidence and uncertainty. This is not yet built into the long-range pathway.
Evaluate games missed, return timing and calibration with dated information, without known future participants.
A1 S08's Expected branch worlds, if validated, become the same near-term draws consumed by the season engine.
Chunk A A1's first execution contract is frozen in HANDOFF: high-impact uncertain-player selection, deterministic
branch IDs and seeds, and explicitly uncalibrated one/two-player weights. More-than-two one-out comparisons are
non-exhaustive. No branch or exact weighted-season implementation has been delivered.
The first fixed F4 full-game branch probe failed foul-out accounting in both branches. An isolated guard now rejects
any sixth foul or invalid five rather than silently using an illegal lineup; it is not the NBA foul-penalty rule and
is not wired into the serving engine. An isolated world-local repair completed the fixed 32-world plays/sits
replay with legal fives and reconciled scores/minutes; it fails closed on insufficient eligible players and remains
subject to the player-first promotion gates. Neither the repair nor branches are served.
The selected S07 fallback keeps fixed report-status probabilities and recent-inactivity heuristics as uncalibrated,
labels unlisted injuries as assumptions, and rejects unavailable five-player worlds. There is no supported
future physical-absence hazard; S10 must retain that limitation unless a candidate passes the frozen tests.

Official postseason/tiebreak/Cup completeness remains later work. Current playoff pictures show marginal regular-
season seeds and illustrative paths, not simulated playoff winners. Historical schedule definitions must reconcile
before S10 compares calibration. S13 historical forecasts are deferred by D40.

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

## 14. Owner decisions and remaining product acceptance

No open decision blocks A1. Today/tomorrow is settled (D24/D27); player-based defence is settled (D35); public source,
GitHub Pages and stripped-back phone are settled. The current-model historical workflow is D39. Real iPhone
installation/import acceptance remains an owner check; iCloud file delivery was confirmed. Do not reopen these
choices without new evidence. A new data provider still needs sign-off; ESPN and NBA Stats are already authorised.

## 15. Risks

| Risk | Mitigation |
|---|---|
| ~1% lineup glitches in play-by-play | Reconciliation gates per node; counted in reports |
| Unseen lineups after trades/injuries | Player-feature lineups, not lineup IDs |
| Rare end-game situations overfit | Rules for mechanics; pooled models; regularisation |
| Too-smooth simulations (variance too low) | Per-player form and talent draws, calibrated on held-out variance |
| Rookie/second-year projections overconfident | Stat-specific shrinkage, archetype priors, posterior talent draws |
| Runtime | Engine limited to today/tomorrow (or next slate); quarter-synchronised vectorisation; parallel games |
| Long-range model drifting from the engine | Compare on held-out outcomes; shared near-term worlds; do not force engine scores to match team ratings |
| Data-source change (ESPN unofficial) | Adapter boundary; raw retention; NBA Stats already retained; source-parity and cutoff audits |

## 16. Additive season presentation outputs (22 Nov 2026)

The season summariser records the chance of a bottom-three league record, using the same wins and random tiebreak
already drawn for best/worst record. Exactly three teams qualify per world. This adds no RNG calls and changes no
forecasts: parity verified on 10,000 retained worlds, 965 remaining games, 13 engine games (FINDINGS §5). Playoff diagrams
are explicitly illustrations of marginal regular-season seeds; no postseason engine or joint pairing odds were added.
Engine v1.3 and team pathway v1 remain promoted; no training changes or final-test use.

## 17. Versioned daily forecasts and current-model season rebuilds (22 Nov)

**Deferred by D40 (22 Nov):** the season-to-date forecast replay and S13 history work below are not to be run or
implemented in the current A1 execution. They remain a prospective design only; existing forecasts and archives must
be preserved, and no progress is credited for the deferred work.

**Earlier D39 design:** preserve daily Today predictions, but with each new model the owner expects
to rerun season start→now so the active dashboard treats the contemporary model as its consistent reference.
S13 therefore builds both a durable daily archive and a resumable full-season replay. This supersedes the interim
“gap-fill only” idea. Ordinary review reads the selected version's saved forecast and actual result; it never runs
simulation while browsing. Earlier versions/original forecasts remain retained, not the default comparison target.

### Daily archive and active version

- Identity: model recipe/version + stable game ID + forecast origin (ET date/input cutoff) + run ID. Store generation
  time, scheduled tip known at the run, model/config/input hashes, fit cutoffs, worlds, report provenance and kind.
- Today and Tomorrow share the same before-origin inputs (D27). Tomorrow is a preview. On its own origin day, a new
  Today forecast becomes the normal reference; keep the preview separately identifiable. Season outputs are keyed by
  origin too; Tomorrow's identical season copy is not another historical observation for Movers.
- For original live history choose the first successful origin-day forecast generated before the game's tip. Retain
  later same-day runs as explicit revisions. A retry is idempotent; after-tip runs cannot claim pre-game provenance.
  A missing Today forecast may use a labelled earlier preview, never an unlabelled hindsight substitution.
- Predictions are immutable within a generation. Actuals join separately by game ID; reschedules, score corrections,
  partial finals and later model versions do not rewrite old forecast values. Preserve archives on schema migration.
- Histories live in distinct version/generation namespaces. Build the new version's season history in staging;
  validate the required date manifest and then switch an active-generation pointer atomically. A failed or partial
  build leaves the previous complete generation available. Never join old-version dates into a new-version series
  silently; unsupported dates are explicit coverage gaps. Daily runs append to the chosen version's history.
- Views, Movers, result reviews and PWA exports carry the active version, origin and reconstruction/live kind. An
  active-version historical scorecard may review reconstructed predictions, but must not call them an original
  prospective track record. Retain enough provenance to distinguish live, replay and placeholder populations.

### Rebuild season start to now with the accepted recipe

Derive the first slate and latest completed ET origin from the retained season schedule, not a hard-coded date.
Produce an immutable run plan of origins, game IDs, expected outputs, hashes and coverage before running. For each D:
result games before D; build dated inputs; run D and D+1 (or the next slate) with the chosen recipe; run its 10k-world
season pathway. The stored **Today** output is that date's normal review reference; next-day previews stay separate.
Do not duplicate a game in a date's season worlds. Finish with S14's live nightly and iCloud delivery.

All player profiles, rotation/pair histories, team ratings and availability evidence must use games strictly before
ET D; tomorrow uses the same origin. Every fitted artifact—node and assignment models, minute/ramp parameters,
priors, calibration, availability—must have a recorded training cutoff before D. The current pre-season-trained
v1.3 weights may be reused for later origins; a new recipe also trained pre-season can similarly cover the season.
If weekly/new fits include games after an earlier origin, refit that same frozen recipe on the earlier window or
use its matching dated fit. Merely filtering the input CSV is insufficient. Record warm-up/cold-start limitations.

Use retained pre-origin injury reports/rosters and schedule revisions where available. Missing historical reports
are explicitly reconstructed availability, never the actual participants, actual starters or eventual return date.
Later revisions and a recipe selected retrospectively prevent claiming these forecasts were actually available then.
The user's current-model view is compatible with honest retrospective labels; it does not waive cutoff safety.

Build an isolated dated runner, reusing normal nightly components without overwriting live `latest` features during
replay. Resume identity includes origin, raw/model/config hashes and seed; invalidated dependencies rebuild. Archive
replaced generations outside the repo. Test interruptions/restart, stale-cache rejection, later-data injection,
worker-count determinism, origin/preview/result transitions, model switch, postponed games and old bundles. Compare
numerical payloads, excluding generation timestamps, on reproducibility tests. Existing `--backfill-days` is still a
placeholder runner; no documented engine-replay command is runnable until S13 implements and tests it.

**Future run gate, only if reauthorised:** S11 freezes an accepted model and S13 proves cutoff/coverage/accounting safety before full reconstruction.
Use development dates for safety checks first. Current-season reconstructed results are for review, not repeated
model selection: the once-per-version final-test rule still applies. If the gate fails, keep the previous accepted
model/history, record the concrete limitation and do not claim a rebuild completed. S14 ends with a fresh live nightly
and a fully specified successor chunk in this same format; it does not wait for or run the deferred historical replay.
