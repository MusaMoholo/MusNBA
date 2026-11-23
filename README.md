# MusNBA

NBA game, player and season simulations — MusSim's sibling for basketball. A laptop-run Python
pipeline collects box scores and play-by-play, simulates every game 10,000 times and every
remaining season 10,000 times, and a static, offline-capable app shows the results on a laptop
or phone.

> The app is live on localhost and as a static PWA. Two engines, one daily flow (D26/D50): today's games come
> from the **possession engine v1.3** (every possession simulated from 16 LightGBM decision models, inputs rebuilt nightly
> from games before the origin; 10,000 worlds per game, one rotation table per world; the floor for later improvements, D22); tomorrow onward uses the **team pathway v1**, where
> each simulated season carries its own team ratings and updates them after every game (D25). Past dates rebuilt after the
> fact currently use a labelled placeholder. U1–U22 and public Pages/iCloud delivery are complete. Accuracy chunk
> **A1 (14 tasks)** has completed S01–S07; S06's audited candidate did not clear its frozen gate. The 22 November
> ET nightly is delivered and historical forecast backfill is deferred. The owner has authorised two remaining chunks
> in order; Chunk A has started by freezing its lineup-branch contract. D50 is delivered: today's retained
> forecasts use the possession engine, and tomorrow onward uses the team pathway.
> The 2-D selected-world View Centre, designed
> for later resulted-game playback, remains unimplemented.
> See [PLAN.md](PLAN.md) and [HANDOFF_NEXT.md](HANDOFF_NEXT.md).

## Setup

Python 3.12+ and a virtual environment. Dependencies (pinned in `requirements.txt`): NumPy, pandas, pyarrow and
LightGBM. On macOS LightGBM needs OpenMP: `brew install libomp`.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Daily use

```sh
.venv/bin/python scripts/nightly.py          # collect → fixtures/box scores → simulate today (ET) → views
.venv/bin/python scripts/serve.py            # browse at http://127.0.0.1:8766
```

- Today's slate is projected by the possession engine v1.3 (D34/D36/D50; 10,000 worlds, measured ~130–150 s/game on the
  21 Nov run). `--ahead` must be zero; a game-free day still produces a fresh team-pathway season. Before the
  engine runs, its inputs (current-season segments, rotations, profiles) are rebuilt from every final before today
  (runtime depends on retained inputs; `--no-rebuild` skips only when those inputs are already current). The season sim then plays every later game through the team pathway (D25);
  `--placeholder` uses the old box-score placeholder instead, and backfilled past dates always do. `nightly.py --offline` reuses retained data; `--views-only` only rebuilds what the app reads;
  the optional `--backfill-days N` is a legacy retrospective-placeholder mode and is not part of the current nightly (D40).
  The late-refresh implementation retains verified pre-tip game worlds and original per-game metadata,
  requiring identical model and cutoff stats; it rejects a missing retained game or a replacement for a verified
  pre-tip forecast that crosses tip during publication. The all-retained live refresh and independent
  origin-registry audit passed; mixed live delivery across separate collections remains untested (see HANDOFF).
  Do not bypass the guard. If publication is interrupted,
  the current-day nightly preflight restores an orphaned `.previous` snapshot when retained fixtures exist; if both
  old and active snapshots remain, the nightly and view rebuild stop for review rather than silently discarding either.
  `analysis/a1_mixed_availability_audit.py` checks game reports against their individual raw collection origins;
  `analysis/a1_mixed_retention_rehearsal.py` exercises a temporary mixed snapshot with a synthetic clock. Neither
  publishes a forecast or proves its pre-tip publication time.
  `analysis/a1_minute_encoding_probe.py` compares candidate encodings against saved research-world minutes
  without scoring actual outcomes or changing forecasts.
  `scripts/webapp/precise-minutes.mjs` implements exact weighted minute thresholds and split display bins for
  the explicitly injected research view (`analysis/a1_precise_minutes.mjs` re-exports it);
  `analysis/a1_precise_minutes_probe.mjs` and `analysis/a1_precise_minutes_audit.py` measure and independently
  check it against original captures. `analysis/a1_minute_payload_probe.py` sizes minute-only storage options.
  New snapshots retain schema-1 float64 period minutes; old rounded snapshots cannot regain precision. Laptop
  sheets and Given/Joint preserve world identity; the phone carries independently sorted period marginals
  without conditional world controls. `analysis/a1_production_minutes_audit.py <capture-manifest> --output
  <new-report.json>` independently checks both representations. No normal route supplies precise branch worlds.
- The server reads files from disk: front-end edits appear on refresh, rebuilt views appear
  immediately; no restart needed. `serve.py --host 0.0.0.0` lets a phone on the same Wi-Fi in.
- Slates are US Eastern game dates; tip-offs show UK time with ET.

## Install on laptop or phone (MusSim pattern)

The public app shell is served from personal GitHub Pages at **https://musamoholo.github.io/MusNBA/** (publication status: HANDOFF_NEXT.md). Source: https://github.com/MusaMoholo/MusNBA. No account is needed in the
app; the public shell contains no collected data or projections.

On iPhone: open that address in Safari → Share → Add to Home Screen, open the installed icon, then choose
**Offline data & installation → Import data** and select **iCloud Drive/MusNBA/MusNBA.musnba.gz**. Import inside the installed
app; Safari and the installed app may have separate storage. Keep it open/unlocked while importing. On a laptop, open
the same address, use the browser's install option if offered, and import **iCloud Drive/MusNBA/MusNBA-laptop.musnba.gz**.
Each device imports separately.

Data stays on-device and browsing works offline after import. App updates arrive through Pages; data updates arrive via
iCloud imports. Keep the source bundle as a backup. The laptop bundle includes saved worlds and existing per-world
Scenarios/Given…/duels. The phone bundle keeps expected-lineup distributions without those world-based features.
Lineup branches remain planned. Real-device iPhone acceptance is an owner check.

### Nightly → iCloud → import

```sh
.venv/bin/python scripts/nightly_musnba.py                  # nightly; exports only after success
.venv/bin/python scripts/nightly_musnba.py --export-only    # export completed snapshots without re-simulating
```

The default destinations are iCloud Drive/MusNBA/MusNBA-laptop.musnba.gz (full) and MusNBA.musnba.gz (phone).
The wrapper checks access to both before starting and installs no scheduler. Exports are **after the nightly finishes**,
not streamed game by game. Each file is verified and published atomically, but the pair is not atomic: if the phone
export fails after the laptop export, retry both with `--export-only`. The wrapper checks that views did not change
across the two exports and reports an error if they did. `--output PATH` overrides the phone destination;
the laptop destination gets `-laptop` before `.musnba.gz`. Other options pass through to the nightly. Previous exports
are archived under `~/Basketball_archive_ops`. Export staging uses visible temporary names and clears Finder’s hidden
flag before/after publication so the bundle appears in iCloud file pickers.

### Keep the PWA current with model and app changes

At any subtask that promotes a model or changes stored forecast data, rebuild affected outputs on the accepted
systems, export a fresh iCloud bundle, and check model/version/cutoff labels plus import/offline compatibility.
For app-asset changes, also rebuild/publish the data-free shell below and verify its service-worker update.
For presentation-only export changes, `--export-only` reuses already-current completed forecasts. Research-only
candidate tests do not change the served model. Every actual development chunk still ends with a new live nightly
and final integrated PWA delivery. **Each device must import the new data bundle**; shell updates alone do not update
its simulations. Record the delivered model/generation separately from owner-confirmed device acceptance.
The game player and team tabs include per-world advanced box-score distributions for supported full-game worlds,
with undefined denominators counted separately; unavailable periods are labelled. Team possessions and ratings are
box estimates, not counted possessions. The latest action-share input is not conventional USG% or a game forecast.
Before rebuilding views directly with `.venv/bin/python scripts/views.py`, archive `data/views` outside the repo;
`--help` only prints usage and does not rebuild.
Audit retained advanced distributions with `.venv/bin/python -m analysis.advanced_world_audit`.

### Historical forecasts: deferred

Currently `nightly.py --backfill-days N` creates **retrospective placeholder** forecasts; it is not an engine replay.
The owner deferred S13 and historical forecast backfill for the current A1 run (D40); the nightly instead projects
today relative to its ET origin (D50). Existing forecasts and archives are retained.
If historical replay is reauthorised later, all historical inputs and fitted artifacts must precede each origin,
reconstructed predictions must be labelled retrospective, and versions must not be mixed silently. No new
engine-replay CLI exists. See ENGINE_PLAN §17 and TRAINING_PLAN §8.

### Build/publish the data-free shell

```sh
.venv/bin/python scripts/export_musnba.py --shell exports/MusNBA-web --base-path /MusNBA/
.venv/bin/python scripts/export_musnba.py --output exports/MusNBA.musnba.gz
```

Publish only the contents of `exports/MusNBA-web` on the `gh-pages` branch with `.nojekyll` (Pages branch source `/`).
Never put datasets or `.musnba.gz` files on that branch. Source remains on `main`; local identity and credentials stay
unchanged. `.github/workflows/pages.yml` is the same optional manually dispatched alternative as MusSim; it requires
selecting GitHub Actions as the Pages source. The active branch deployment does not run simulations or require Actions.

Dashboard routes: `#/standings/{forecast,seeds,wins,ratings,picture,races,movers,leaders}`, `#/team/<id>`, `#/about`.
`#/season` redirects to Standings Races. Counts/dates/model labels and qualifiers come from the loaded data/settings.

## Code map

| Location | Responsibility |
|---|---|
| `basketball_common.py` | Paths, time zones, team conferences/divisions, atomic writes, archives |
| `scripts/fetch_espn.py` | Provider adapter: raw ESPN responses retained gzip under `data/raw/espn` |
| `scripts/master_fixtures.py`, `scripts/box_scores.py` | Master fixture list; player/team game logs; player registry |
| `scripts/pbp.py` | Play-by-play: on-court seconds per period, per-period player box scores, reconciliation report |
| `scripts/plays.py`, `scripts/history.py` | One play schema for live and historical data; 2022-23 → 2025-26 history ingest and reconciliation |
| `scripts/possessions.py` | Possessions/segments with lineups, state and the who → what → result chain (training data); rebound-clock convention |
| `scripts/parity.py` | Live ESPN v hoopR history: same games through both adapters; season distributions under both rebound clocks |
| `scripts/rotations.py` | Stints, substitution windows, on-court minute shares; replay-rotation baseline and minutes backtest |
| `scripts/features.py`, `scripts/evaluate.py` | Point-in-time player and team-style profiles; rolling-fold evaluation harness and baselines |
| `scripts/nodes.py`, `scripts/train.py` | Datasets for the 16 decisions (cached); LightGBM per decision on the folds, persisted versions, final test |
| `scripts/compare.py`, `scripts/calibration.py` | Paired run comparisons (game-clustered, seed-noise floor); calibration by period and margin |
| `scripts/aggregate.py` | M6a: replay held-out games with real lineups and clock, sample every decision, score box scores |
| `scripts/engine.py` | The engine (default projection, v1.3 = D30 defence inputs + D29 minutes): plays games possession by possession; rotation tables rescaled to minutes targets; profiles from the version's features variant (`features_dir`) |
| `scripts/minutes.py` | D29 minutes: healthy-role minutes, priority, 240 per team by priority, return ramp, rotation share, per-world draws, projected starters |
| `scripts/a1_minutes_candidate.py` | Isolated NBA-team-only D29 history and strict regulation-allocation candidates; `--audit-f4` checks fixed-panel states. Backtest opts in via `--minutes-history nba_only` and/or `--strict-minute-targets`; production defaults remain unchanged |
| `scripts/a1_minutes_audit.py`, `scripts/a1_minutes_diagnose.py`, `scripts/a1_rotation_diagnose.py`, `scripts/a1_minutes_stress.py` | A1's prior-box population, D29 state/calibration, conditional target-squeeze and legal-allocation diagnostics; not pre-game availability forecasts |
| `scripts/a1_minutes_fold_eval.py`, `scripts/a1_minutes_unconditional.py`, `scripts/a1_minutes_no_report.py`, `scripts/a1_minutes_screen_audit.py` | Isolated fixed-fold minute screens and independent accounting; prior-box and no-report screens are incomplete-roster sensitivities, not injury forecasts |
| `scripts/a1_minutes_gate.py` | Preliminary A1 paired-report checker using the registered seed-noise floor and player/game bounds; not a promotion decision. Original/v2 reports used the wrong floor; use v3 or later |
| `scripts/a1_pooled_audit.py` | Independently reconstructs pooled player bootstrap intervals and checks pooled bias/coverage bounds from paired backtest reports |
| `scripts/a1_substitutions.py` | Experimental clock-and-sequence replay of observed stoppages and pre-substitution state; conditional on actual participants, with unreconciled games quarantined |
| `scripts/a1_substitution_audit.py`, `scripts/a1_substitution_opportunities.py`, `scripts/a1_substitution_states.py` | Independent sequence accounting, conservative full-timeout labels and descriptive state/role rates; not calibrated or pre-game availability forecasts |
| `scripts/a1_substitution_response_compare.py` | Matched Q4-minute and full-game minute-CRPS subgroup comparison by realised Q4 score and prior fouls; simulated quarter means are not state-conditioned |
| `scripts/a1_substitution_response_capture.py`, `scripts/a1_substitution_response_audit.py` | Opt-in same-policy replay capturing simulated selected-timeout exits by pre-decision state, with exact output reproduction and historical-state accounting |
| `scripts/a1_flow_audit.py` | Independent flow accounting; `--no-reference` explicitly omits same-policy reproduction when no separate reference exists |
| `scripts/a1_snapshot_availability_audit.py` | Check new live snapshot pre-origin inputs and completion/tip labels, reports against their origin registry, saved views, player/team points and season game worlds (`--days … --origin YYYY-MM-DD --expected-model … --expected-sims … --output …`) |
| `scripts/a1_substitution_dataset.py`, `scripts/a1_substitution_dataset_audit.py` | Prior-target and current-state candidate construction and independent accounting; unknown incoming eligibility stays unknown |
| `scripts/a1_substitution_fold_data.py`, `scripts/a1_substitution_seed_audit.py`, `scripts/a1_substitution_out_screen.py`, `scripts/a1_substitution_screen_audit.py` | Historical-fold candidates, seed-cutoff accounting, preregistered outgoing screen and independent score/bootstrap audit; research only, not a deployed substitution hazard |
| `scripts/a1_foul_out_probe.py` | Controlled reproduction of the existing engine's unupdated foul-out mask; research only |
| `scripts/a1_substitution_in_coverage.py`, `scripts/a1_substitution_in_coverage_audit.py` | Incoming eligibility/position coverage and independent reconciliation; not a current-availability forecast |
| `scripts/a1_substitution_in_screen.py`, `scripts/a1_substitution_in_screen_audit.py` | Frozen positive-versus-unlabelled incoming ranking screen, explicit-active-roster joint selector and independent accounting; research only |
| `scripts/a1_substitution_engine_models.py` | Reproduces saved fold-screen scores and builds strictly earlier selected-timeout model/template artifacts for an isolated engine candidate; research only |
| `scripts/a1_substitution_engine.py` | Opt-in selected-timeout lineup policy and foul-out handling for matched backtests; candidate only, not the served engine |
| `scripts/a1_foul_penalty_engine.py`, `scripts/a1_foul_penalty_probe_audit.py` | Isolated five-player foul-penalty exception and independent saved-world probe accounting; opt in with `--substitution-foul-penalty`, never serving |
| `scripts/a1_availability_report_audit.py`, `scripts/a1_availability_report_audit_check.py` | Conservative pre-tip archive, injury-status and final-box coverage inventory and independent accounting; protected-season outcomes are not scored |
| `scripts/a1_availability_labels_audit.py` | Independently reconstruct F4 prior-box membership and separate retrospective play/DNP reasons from the actual-participant oracle |
| `scripts/a1_availability_baseline.py`, `scripts/a1_availability_baseline_audit.py` | Frozen F1–F4 no-report play proxies and prior-roster D29 starter-selector baseline, with independent score and bootstrap accounting; missing status/position coverage stays explicit |
| `scripts/a1_availability_sequences.py`, `scripts/a1_availability_sequence_audit.py` | Development-only recorded DNP/return and rest sequence construction and independent accounting; unlisted games, trades, unknown labels and left-censored spells are not converted to absences |
| `scripts/a1_availability_sequence_screen.py`, `scripts/a1_availability_sequence_screen_audit.py` | Frozen earlier-fold return/rest play-proxy screen, independent probability/interval accounting; not physical recovery or a deployable season-absence hazard |
| `scripts/a1_availability_spell_sim.py`, `scripts/a1_availability_spell_audit.py` | Research-only, five-game censored recorded-DNP trajectories and independent accounting using earlier-fold play proxies; evaluated, not a physical-absence model |
| `scripts/a1_availability_starter_sim.py`, `scripts/a1_availability_starter_audit.py` | Research-only per-world starter frequencies for inferred rosters, with independent no-report draws and independent replay/accounting across F1–F4 |
| `scripts/a1_lineup_branches.py` | Isolated D46 top-three offensive-proxy selection (at most one uncertain player per team), exact-weight branches, simultaneous D29 preparation and fail-closed lineup/foul guard; not wired into the nightly or an Expected forecast |
| `scripts/a1_branch_persist.py`, `analysis/a1_branch_persist_audit.py`, `analysis/a1_branch_{runtime_audit,roster_pressure}.py` | Isolated D47 quarter-scale branch-world capture from a matching prospective snapshot with origin/model hashes and original availability; independent selection, branch-weight, saved-box, logged-runtime and completed-world roster-pressure checks. Research only; short rosters fail and production forecasts are unchanged |
| `scripts/a1_expected.py`, `scripts/a1_season_mixture.py` | Research-only exact-weight branch distributions and bounded weighted-season coupling; no serving or production integration |
| `analysis/a1_expected_joint_audit.py`, `analysis/a1_season_dependence.py`, `analysis/a1_season_mixture_audit.py` | Reproducible weighted Given/Joint reconstruction, cross-game covariance and independent season replay; not acceptance or calibration |
| `scripts/a1_world_retry.py`, `analysis/a1_world_retry_{probe,bias,stress}.py` | Research-only isolated retry coordinator, synthetic-injection/selection-bias and artificial short-roster probes; not connected to nightly |
| `analysis/a1_parallel_world_{retry,probe,scaling}.py` | Research-only bounded process coordinator and fixed-game identity/scaling probes; not connected to nightly |
| `analysis/a1_parallel_capture_{scale,audit}.py`, `analysis/a1_parallel_resume_compare.py` | Persist isolated fixed-game worlds in audited batches, optionally resume a complete prefix, and independently compare hashes, seeds, lineups, points and minutes. Single operator only; incomplete writes fail for inspection. Not a forecast |
| `analysis/a1_f4_exhaustion_{screen,audit}.py` | Research-only fixed-F4 actual-participant synthetic branch stress and independent saved-world accounting; not a pre-game failure-rate estimate or promoted retry policy |
| `analysis/a1_f4_six_roster_{stress,audit}.py` | Research-only first-attempt exhaustion stress and saved-world audit for the selected six-player F4 branch; not a league failure rate or retry-bias estimate |
| `analysis/a1_f4_six_roster_penalty_{compare,audit}.py` | Research-only S06 replay and saved-trace audit of the selected six-player D29-rejected seeds; policies and random paths differ |
| `analysis/a1_f4_six_roster_halftime{,_audit}.py` | Research-only replay and saved-state audit of pre-failure survivor selection in the selected six-player F4 branch |
| `analysis/a1_dated_fold_prepare.py`, `analysis/a1_dated_fold_exhaustion{,_audit}.py` | Research-only dated F1–F3 engine preparation and oracle-roster branch exhaustion screens; not availability calibration or promotion |
| `analysis/d50_today_only_probe.py` | Isolated retained-input season/view rebuild and independent future regulation-distribution audit; never publishes or replaces snapshots |
| `analysis/a1_retry_penalty_stress_compare.py`, `analysis/a1_retry_penalty_stress_audit.py` | Artificial five-player retry/S06 seed comparison and independent saved-trace accounting; policies and streams differ |
| `analysis/a1_branch_browser_fixture.py`, `analysis/a1_branch_browser_fixture_audit.py` | Research-only full-game and player-period branch fixture with exact minutes, simulated opening fives and independent capture decoder; no serving or bundle integration |
| `analysis/a1_branch_world_source.mjs`, `analysis/a1_branch_period_browser_audit.mjs`, `analysis/a1_branch_source_benchmark.mjs` | Isolated fail-closed weighted branch source, independent period and opening-five comparison and Node-only load benchmark; not a shipped UI |
| `analysis/a1_branch_game_summary.mjs`, `analysis/a1_branch_game_summary_probe.mjs`, `analysis/a1_branch_game_summary_audit.py` | Research-only selected-world player/team period summaries and independent capture reconstruction; weighted mass units are not world counts |
| `analysis/a1_expected_payload.mjs`, `analysis/a1_expected_payload_probe.mjs`, `analysis/a1_expected_payload_audit.py` | Isolated Expected-only payload serialization and independent accounting from audited fixtures; not a production bundle contract |
| `analysis/a1_game_view_contract.mjs`, `analysis/a1_game_view_contract_probe.mjs`, `analysis/a1_game_view_contract_audit.py` | Research-only selected Game Centre adapter and independent accounting; no normal route registers its injection hook |
| `analysis/a1_game_view_browser_check.mjs`, `analysis/a1_research_bundle.py` | Isolated injected browser check and private research bundle construction; neither publishes forecasts nor proves real-device acceptance |
| `analysis/a1_game_context_audit.py` | Research-only audit of a snapshot-pinned master, copied game context and strictly pre-origin team records; not runtime enforcement |
| `scripts/webapp/weighted-worlds.mjs`, `analysis/a1_weighted_browser.mjs`, `analysis/a1_weighted_browser_audit.mjs` | Shared exact integer-mass arithmetic and independent Python-reference accounting; research module re-exports it. No branch selector is enabled |
| `analysis/a1_scenario_browser_check.mjs` | Isolated local browser injection against retained branch fixture and independent scenario/grid references; not a production or phone acceptance test |
| `analysis/a1_weighted_grid_reference.py`, `analysis/a1_weighted_grid_audit.mjs` | Independent research comparison of weighted browser grids and correlations against saved branch captures |
| `analysis/a1_dynamic_grid_probe.mjs`, `analysis/a1_dynamic_grid_audit.py` | Research-only adaptive weighted continuous-minute grid and independent exact-mass reconstruction |
| `analysis/a1_expected_minutes_audit.py` | Research-only exact-second Given/Joint reconstruction from saved branch minutes; no production integration |
| `scripts/a1_branch_foul_out.py` | Opt-in branch-only foul-out repair with world-local change masks and explicit short-roster failure; full-game audit still pending |
| `scripts/a1_branch_world_probe.py` | Isolated fixed-F4 branch replay, `--repair` trace and independent world accounting; diagnostic only |
| `scripts/a2_residual_dependence.py` | Frozen F4 player/team residual covariance diagnostic with role-centred, game-cluster bootstrap intervals; actual-participant research only |
| `scripts/a2_shot_residuals.py` | Frozen F1–F3 teacher-forced shooting-residual feasibility screen with source alignment and game-cluster intervals; not a calibrated form model |
| `scripts/a2_shot_persistence.py` | Frozen earlier-fold cross-game shooting-residual screen with player/game bootstrap; not a talent-posterior estimate |
| `scripts/a2_form_prototype.py` | Synthetic-only bounded, mean-preserving player-draw mechanics; no fitted strengths or engine wiring |
| `scripts/a1_substitution_world_capture.py`, `scripts/a1_substitution_world_audit.py` | Research-only raw world/lineup capture and independent player-minute, legal-five and score replay; enable with backtest `--audit-substitution-worlds` |
| `scripts/matchups.py` | D30 implicit matchups: soft assignment of defenders to shooters from foul/block credits; shot types from the play text |
| `scripts/fetch_nbastats.py` | D32 NBA Stats adapter (browser fetch headers, ~1 request/s, resumable): season logs, `boxscorematchupsv3`, tracking defence, play-by-play v3 → `data/raw/nbastats/<endpoint>/<season>/` (gzip + manifest) |
| `scripts/nbastats.py` | D32 crosswalk (games by date + teams, players by name/stat line), reconciliation v ESPN (points, minutes, possessions), real matchups in ESPN ids → `data/derived/nbastats/` |
| `scripts/realmatch.py` | D32 real matchups: pre-game assignment fitted on real shares (ranks, stopper, pair history), per-game pair history (cutoff-safe) |
| `scripts/lineups.py` | Projected v actual starters for finished, verified pre-tip prospective snapshots; older unverified records are kept separately |
| `scripts/backtest.py`, `scripts/backtest_compare.py` | Engine backtest on held-out fold games (M9; `--rotation targets`, `--models` to reuse fold models), with the team-rating model on the same games; legacy paired scorecard |
| `scripts/a1_compare.py`, `scripts/a1_manifest.py`, `scripts/a1_quarter_audit.py`, `scripts/a1_output_audit.py`, `scripts/a1_availability_cohort.py`, `scripts/a1_data_inventory.py`, `scripts/a1_reconcile.py`, `scripts/a1_rotation_audit.py`, `scripts/a1_tracking_coverage.py`, `scripts/a1_lineup_audit.py`, `scripts/a1_subsplit_audit.py`, `scripts/a1_feature_parity.py`, `scripts/a1_causal_audit.py`, `scripts/a1_assignment_audit.py`, `scripts/a1_assignment_schedule.py`, `scripts/a1_node_cache_audit.py`, `scripts/a1_future_injection.py`, `scripts/a1_signal.py`, `scripts/a1_m6a_audit.py`, `scripts/a1_profile_spread.py`, `scripts/a1_shot_trace.py`, `scripts/a1_variant_components.py` | A1 paired bootstrap, frozen provenance, independent accounting, data integrity, dated assignment fits, sampled train/engine parity, causal injection tests and matched signal diagnosis |
| `scripts/a1_flow_capture.py`, `scripts/a1_flow_audit.py`, `scripts/a1_flow_compare.py` | Opt-in free-running player/quarter flow capture, independent accounting and paired teacher-forced comparison |
| `scripts/a1_rim_calibration.py`, `scripts/a1_rim_screen.py`, `scripts/a1_rim_audit.py`, `scripts/a1_rim_noise.py`, `scripts/a1_rim_noise_compare.py` | Isolated training-tail rim-expression screen, independent accounting and four-fold training-seed gate; not used by the served engine |
| `scripts/a1_tracking_features.py`, `scripts/a1_tracking_screen.py`, `scripts/a1_tracking_audit.py`, `scripts/a1_tracking_screen_audit.py` | Isolated prior-date tracking-defence features, guarded node ablation and independent chronological/prediction accounting; the feature auditor accepts `--feature-report`/`--features` for a new build. Retrospective provenance limitations apply |
| `scripts/a1_defence_interactions.py`, `scripts/a1_defence_interaction_audit.py` | Descriptive no-refit composition of the two frozen S04 adjustments and independent accounting; not a promotion test |
| `scripts/pathway.py` | Team engine (D25, D26): per-world offensive/defensive ratings, updated after every simulated game |
| `scripts/season_backtest.py` | Team engine trust test (M12 first cut): walk-forward seasons 2022-26, `--grid` calibration |
| `scripts/athletes.py`, `scripts/buckets.py` | Player heights/weights; paired comparisons by the player's sample size |
| `scripts/season_stats.py` | Cutoff-safe team ratings and player season stats |
| `scripts/projection.py` | Placeholder game model (`baseline-v1`, backfills) and the season sim (team pathway, D25) |
| `scripts/nightly.py`, `scripts/views.py` | Orchestration, immutable snapshots, API-ready views |
| `scripts/serve.py` | Read-only local server for the app and `/api/*` |
| `scripts/export_musnba.py`, `scripts/nightly_musnba.py` | Static shell, data bundle, iCloud export |
| `scripts/webapp/` | Native ES modules: `league.mjs` (Standings/teams), `season.mjs` (Races/Movers/Leaders), `about.mjs` (model guide); no build step |
| `scripts/smoke.py`, `analysis/*.mjs` | Accounting checks; optional browser/PWA acceptance (Node, no packages) |

## Engine data and models (phase 2)

Rebuild in order after new data: `scripts/history.py` → `scripts/possessions.py` → `scripts/rotations.py`
→ `scripts/features.py` → `scripts/nodes.py` (dataset cache) → `scripts/train.py`. State, next steps and commands:
[HANDOFF_NEXT.md](HANDOFF_NEXT.md).

```sh
.venv/bin/python scripts/train.py --name <label> [--drop @team …]     # an experiment on folds F1–F4 (~20 min)
.venv/bin/python scripts/compare.py <run A> <run B> --noise <seed A> <seed B>   # keep / reject, per node
.venv/bin/python scripts/train.py --config "models/<frozen-new-version>.json" --final  # only after acceptance; final test once
.venv/bin/python scripts/aggregate.py --config models/v1.3.json         # M6a diagnosis with real lineups/clock
.venv/bin/python scripts/parity.py [--fetch]                            # adapter and feed parity (M5b)
.venv/bin/python scripts/backtest.py --config models/v1.3.json --games 200 --worlds 1000 --jobs 7 --rotation targets --pool 0 [--models folds/v1.3_F4_all]   # engine v1.3 backtest (M9)
.venv/bin/python scripts/backtest_compare.py <run A> <run B> [--log NAME]   # paired: player tiers, loading, margins, CRPS
.venv/bin/python scripts/a1_compare.py <control-run> <candidate-run> --output <new-report.json>  # strict A1 paired intervals
.venv/bin/python scripts/a1_manifest.py --output <new-manifest.json>    # freeze selected games, seeds and hashes
.venv/bin/python scripts/a1_manifest.py --output <new-manifest.json> --control-run <run> --seed-run <run>  # final seed floors and provenance
.venv/bin/python scripts/a1_quarter_audit.py --output <new-report.json> # validate quarter actuals against raw scoreboard
.venv/bin/python -m scripts.a1_output_audit <run> [--reference <legacy-run>] [--pin-current-inputs] --output <new-report.json> # output accounting; hashes are as of audit time
.venv/bin/python scripts/a1_availability_cohort.py <control-run> --output <new-report.json> --rows-output <new-cohort.parquet>
.venv/bin/python scripts/a1_data_inventory.py --output <new-report.json> # verify retained NBA/ESPN source manifests
.venv/bin/python -m scripts.a1_reconcile --output <new-report.json>    # per-season player/possession reconciliation
.venv/bin/python -m scripts.a1_rotation_audit --output <new-report.json> # substitution and matchup source audit
.venv/bin/python -m scripts.a1_tracking_coverage --output <new-report.json> # dated tracking-defence coverage
.venv/bin/python -m scripts.a1_lineup_audit --output <new-report.json>  # event participants v segment-start lineups
.venv/bin/python -m scripts.a1_subsplit_audit --limit 200 --output <new-report.json> # isolated fixed-F4 lineup pilot
.venv/bin/python -m scripts.a1_feature_parity --output <new-report.json> # limited three-game matchup feature parity
.venv/bin/python scripts/features.py --history-only --causal-first-priors --out <new-variant-dir> # isolated base; not complete cutoff certification
.venv/bin/python -m scripts.a1_causal_audit --output <new-report.json>  # account for the pinned causal base build
.venv/bin/python -m scripts.a1_assignment_audit --through 2025-12-31 --holdout-to 2026-04-30 --output <new-report.json> --model-output data/derived/variants/<new-model.json>  # isolated dated assignment, not a promotion
.venv/bin/python -m scripts.a1_node_cache_audit --features <variant>/pregame.parquet --fold F4 --output <new-report.json> # audit a full isolated node cache
.venv/bin/python -m scripts.a1_subsplit_audit --limit 200 --account-pregame <variant>/pregame.parquet --output <new-report.json> # isolated split feature/node accounting
.venv/bin/python -m scripts.a1_future_injection --output <new-report.json> # real-slice same-day/future injection audit
.venv/bin/python -m scripts.a1_signal --dataset <new-sides.parquet> --output <new-report.json> # fixed F4 component loadings, game-clustered intervals
.venv/bin/python -m scripts.a1_variant_components --output <new-report.json> # matched shared-pool variant decomposition
.venv/bin/python -m scripts.a1_m6a_audit <run> --game-ids <ids.json> --output <new-report.json> # teacher-forced output and model accounting
.venv/bin/python -m scripts.a1_profile_spread --output <new-report.json> # descriptive shooter/defender profile spread
.venv/bin/python -m scripts.a1_shot_trace --output <new-report.json> # aligned frozen F4 shot node; actual-shot diagnostic, not forecast
.venv/bin/python -m scripts.a1_minutes_screen_audit --conditional --output <new-report.json> # corrected conditional-screen accounting
.venv/bin/python -m scripts.a1_minutes_screen_audit --suffix corrected --output <new-report.json> # corrected historical sensitivities
.venv/bin/python -m unittest discover -s tests -p 'test_a1*.py'       # focused A1 evaluation checks
.venv/bin/python scripts/minutes.py --evaluate [--season 2025 --from 2025-01-01 --to 2025-04-30] [--set gamma=1]   # allocator v real (no engine)
.venv/bin/python scripts/matchups.py --fit --through 2025-12-31            # D30 assignment θ → models/matchup_<through>.json
.venv/bin/python scripts/fetch_nbastats.py --logs --matchups [--ptdefend] [--pbp]   # D32 NBA Stats history (polite, resumable)
.venv/bin/python scripts/nbastats.py --crosswalk --reconcile --matchups     # ids ↔ ESPN, reconciliation, matchups.parquet
.venv/bin/python scripts/features.py --out data/derived/variants/realmatch/features --defence --defence-k-scale 0.2 \
    --matchup models/matchup_2025-12-31.json --shot-types --real-matchups data/derived/nbastats/matchups.parquet
.venv/bin/python scripts/realmatch.py --history                             # per-game pair history (cutoff-safe)
.venv/bin/python scripts/realmatch.py --fit --through 2025-12-31 --save     # real-share θ → models/realmatch_<through>.json
.venv/bin/python scripts/backtest.py --config models/v1.2d.json --models folds/v1.2d_F4_all --rotation targets --pool 0   # D36: one rotation table per world
.venv/bin/python scripts/features.py --out data/derived/variants/matchup/features --defence --defence-k-scale 0.2 --matchup models/matchup_2025-12-31.json --shot-types
.venv/bin/python scripts/lineups.py --score                                 # projected v actual starters (also in the nightly)
.venv/bin/python scripts/season_backtest.py [--grid]                    # team engine walk-forward (M12; ~1–4 min)
```

For exact A1 populations, `backtest.py --game-ids <file.json>` accepts a non-empty list of unique eligible game-ID
strings; `--simulation-stream 1` changes simulation draws without changing game selection. `--seed-key` explicitly
sets a shared starting seed namespace across model labels, not guaranteed event-by-event random alignment. Without
these flags the historical seed stream is unchanged. The legacy comparison uses actual-starter tiers; only the A1
comparison uses the preregistered pre-game tiers and fails on unmatched games/players. It identifies simulated
participants without player-box outputs separately rather than treating missing outcomes as zero. It reports intervals,
not a Holm-adjusted promotion decision. Its win scores use unmodified empirical probabilities; a realised winner
assigned zero probability is reported as infinite log loss rather than given the legacy scorecard's boundary safeguard.
The final S01 manifest fingerprints the exact control source at commit `c6d5db4`. To reproduce that byte-level
check after later source changes, use an isolated worktree at the pinned commit with the retained `data/`, `.venv/`
and `exports/` available; the current seed-list type annotation is bytewise different but behaviorally identical.
The separate prior-box cohort is inferred membership, not official rosters
or a validated availability forecast; unlisted and zero/missing-minute cases remain unknown. Historical availability
and first-season/assignment cutoff limitations still apply.

Data variants live under `data/derived/variants/<name>/` (segments root + `features/`): `possessions.py --rebound-clock miss
--out DIR` and `features.py --segments DIR --out DIR/features` build one; `nodes.py`/`train.py --segments DIR --features …`
read it; a version file can name it (`"segments"`, `"features"`). `train.py … --train-segments default --train-features
default` trains each fold on the canonical data and validates on the variant's rows (a paired cross-data test).

Fitted models live in `data/models/<version>/` (out of git, rebuilt by `--final`); the settings that define a version
are `models/<version>.json` (in git).

## Verification

```sh
.venv/bin/python scripts/smoke.py                                   # accounting + determinism
.venv/bin/python -m unittest tests.test_lineups_timing tests.test_nightly_origin -q  # pre-tip/origin regressions
.venv/bin/python scripts/a1_snapshot_shooting_audit.py --days <slate> [<slate> ...] --origin <ET-date> --model engine-v1.3 --worlds 10000 --output <new-report.json>
.venv/bin/python analysis/export_visibility_check.py                  # atomic bytes + macOS Finder visibility
node analysis/browser_check.mjs --base http://127.0.0.1:8767        # phone/desktop, both themes
node analysis/pwa_import_check.mjs --url <shell url> --bundle <file.musnba.gz> --profile laptop  # use phone for stripped bundle
```

Data: retained ESPN/hoopR history and owner-authorised NBA Stats API. Public source/app shell; data remains local/iCloud.

## Development handover

Read [AGENTS.md](AGENTS.md), then [HANDOFF_NEXT.md](HANDOFF_NEXT.md). A1's 14 subtasks, weights and 140 concrete
progress rungs live in HANDOFF; detailed scope/gates are PLAN §6a–6c. Each task ends with updated docs, evidence and
a commit/push. Every development chunk ends with a fresh nightly/PWA delivery and a successor chunk in the same
format. The earlier planning-only stop was lifted for the overnight A1 execution; resume the active rung in HANDOFF.
