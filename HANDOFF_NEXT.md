# Handoff — state and next actions

Updated **20 November 2026, ~10:10 UK** (checkpoint: nightly input rebuild, **team pathway v1** in the app (D25–D27),
first **engine backtest** (M9) and the first **walk-forward season test** (M12)). Read [AGENTS.md](AGENTS.md) first.
Rewrite this file at every checkpoint, then commit and push; whoever reads it next may be a new agent.

**Git:** private repo `MusaMoholo/MusNBA` (`main`). Previous checkpoint `043654c`; this session's commit follows it —
`git log --oneline -3`. **Nothing runs in the background.** The owner keeps `scripts/serve.py` on :8766 open — leave it;
use :8767 for your own checks.

**How the owner wants a chunk run (AGENTS §3):** state your understanding and **one or two headliners** that move the two
engines toward trust; print the progress board (active subtasks + overall, text bars) in your reply whenever a subtask
reaches a new 10% mark or the chunk a new 5% mark.

## The product in one paragraph (ENGINE_PLAN D26)

On any date D: every game before D is resulted; the **play-by-play engine** (v1.1) simulates today's and tomorrow's
games — or the next slate if neither has games — with inputs carried over from every game before D; the **team engine**
(team pathway v1) plays every later game in each of 10,000 worlds with that world's own offensive and defensive ratings,
updated after every game, so March is played from each world's own path. Season outputs are counts over the worlds.

## State

**Play-by-play engine (v1.1, the floor, D22).**
- **Inputs now carry over nightly (D26).** `nightly.py` rebuilds current-season segments → rotations → profiles from every
  final before today (`rebuild_engine_inputs`, ~50 s; `--no-rebuild` skips), cutoff-safe (`possessions.current_games(before=)`
  drops games dated today even if final). Verified 20 Nov: 4 new finals → `latest`, `team_latest` and `stints` hashes
  changed; profiles through 19 Nov. No games today or tomorrow → the next slate (`nightly.engine_days`).
- **Backtest (M9) — first run:** 200 F4 games (Jan–Apr 2026), fold models through Dec 2025, known availability (`…100616Z_backtest_v1.1_F4`, FINDINGS §3o). Pace right (+0.2%), efficiency +0.9% → totals +2.7; margins half-sized (slope of real on simulated 1.45); **defence expressed at ~25% of its real effect** (points per 100 load 0.42 on the opponent's defensive rating v 1.69 in real games; offence 0.80 v 1.14 — `strength_loading` in the log); stars' minutes +6.5% (points +8.8%), bench −2.6%; totals too narrow (SD 17.0 v 21.0, coverage 65%), minutes coverage 58–63%. **The team-rating model beats the engine on every game measure** on the same games: margin CRPS 9.32 v 9.64, total 11.35 v 12.10, win log loss 0.558 v 0.592 (paired z 1.7–2.6). Evidence recorded against D18 (ENGINE_PLAN); owner question PLAN §9.6.
- Live symptoms (FINDINGS §3j, §3m): totals ≈ +8 v the market on the 19 Nov slate, spreads about half the market's
  (the defence finding above), OT ≈ 3% v 5.4%; M6a biases: team turnovers +9.7%, and-ones +6.9%, fouled on a three −28%.

**Team engine (team pathway v1, D25) — new, in the app.**
- `scripts/pathway.py` (called by `projection.simulate_season`): per-world offence/defence ratings start at the shrunk
  season estimate (K = 8) + 0.4 × its posterior SD (11 / √(gp + 8)); engine games take universe k's result from engine
  world k mod 2,000; every later game draws scores from the world's current ratings (baseline-v1's form: pace × off × def /
  league, home court 2, SD 11.25, rho 0.35) and both teams update by the estimator's gain 1 / (min(n, 20) + 9) on the
  surprise v the world's own expectation. ~1 s for 974 games × 10,000 worlds.
- `nightly.py` now projects the engine days first (`project_slate`, keeps per-world points), runs **one season as of
  today** with both days' engine worlds, and writes the same season into today's and tomorrow's snapshots
  (`write_snapshot`; per-world points in `engine_worlds.npz`). Fixes a D24 bug: tomorrow's snapshot used to run its own
  season without today's games.
- **Walk-forward trust test (M12 first cut, FINDINGS §3n):** 2022-26 from 20 Nov / 25 Dec / 1 Feb / 10 Mar (480 team-starts):
  the old fixed-probability season sim had dispersion 1.53 and 10–90% coverage 65%; v1 1.00 and 84%, CRPS −4% in every
  held-out season. Still wide in November (0.84, coverage 88%) and simulated surprises fade with the date (0.52 → 0.18)
  where real ones persist (0.40 at every date).
- App: Standings chip "Team pathway v1" and a rewritten "How the forecast works" (`seasonPill`, `league.mjs`).

**Checks:** smoke 80/80 (new: each engine game's season win % equals the engine's; the season re-simulates bit-for-bit;
the backtest's totals and margins add up;
rebound-convention checks now compare the live season on the games both copies hold); `--fault` fails 9; browser 38/38
on :8767. Snapshots 2026-11-20 (9 games) and 2026-11-21 (6 games): engine v1.1 + team pathway v1; their engine games are
byte-identical to the morning run (determinism).

## Next actions (in order — the owner may reorder)

1. **Defence expression (play-by-play headliner).** The engine's opponent-defence loading is 0.42 v 1.69 real. Route
   inside D18 first: on-court defence profiles (`features.py --defence`) with much lighter shrinkage (today rim 67.3% ± 1.5
   points), fed to what, shot result, event and turnover type (the location test, old item 6, folds in here); then fold
   models and the backtest. **Judge by the backtest, not node log loss alone** (§3l's node-level verdict was negative):
   `backtest.py --config <version file> --games 200 --worlds 1000 --jobs 4` with the same seed (same games) and compare
   with `…100616Z_backtest_v1.1_F4`: `strength_loading.sim.opp_defence` toward 1.69, margin slope toward 1, margin CRPS
   and log loss below the team-rating model's (9.32, 0.558). If player inputs cannot close it, take the D18 question to
   the owner (opponent defensive rates as inputs). Done when a candidate beats v1.1 on the backtest and the team model on
   margins, or the owner has the D18 question with numbers.
2. **Stars' minutes** (+6.5% in the backtest): replayed rotations give stars full-strength minutes in every world. Scale the
   template minutes to each player's recent minutes distribution (or start M7); judge by the backtest's player tiers
   (minutes bias ≈ 0, coverage toward 80%) and totals.
3. **Team engine start and drift (M12 continues; FINDINGS §3n).** (a) Start ratings: last season's rating as a prior
   (carry-over) and opponent adjustment — November dispersion 0.84 → 1.0 honestly; (b) per-day drift so simulated
   persistence stays ≈ 0.40 through March (now 0.52 → 0.18); (c) owner's question: a results-only Elo variant as a
   comparison on `season_backtest.py` (expected worse — margins carry most of the information; measure it); (d) a
   basketball "xG" for real games: rate real results on shot quality (opponent three-point and free-throw shooting are
   mostly luck) — the true good-loss rule for today's start ratings. Judge every variant with `season_backtest.py`
   (by date) and keep the paired seed.
4. **Outcome-first benchmark (owner):** `scripts/market.py` (evaluation only) — for every saved engine/placeholder
   snapshot once its games are final: engine v actual (bias, CRPS of total and margin, win log loss), closing line v
   actual, engine v line; also let `fetch_espn.collect` save tomorrow's scoreboard (D24) so pre-game lines are kept.
5. **Spread:** per-world form and strength uncertainty (D3/M8) — totals coverage 65%, margin 72.5%; OT rate.
6. **Dashboard UX backlog (PLAN §9b)** — the headliner of any chunk that cannot improve an engine: Game Centre
   play-by-play of a saved sim (D9, M10: event log for worlds 0–4, `api/game/<id>/sim/<k>`, nba.com-style list, then a
   2K-style aerial play-through), deeper outcome graphs, Reg season / NBA Cup / Playoffs tabs (bracket from expected
   standings per world, MusSim cup-style).
7. **Refits with 2026-27 data** (the D23 convention makes them usable; the 2026-27 foul and turnover shifts need them);
   design the weekly refit (D11) and its test.
8. Then M7 (target-aware substitutions) → M8 (form, end-game) → full M9 on all folds.

**End every chunk with the dashboard on the newest systems** (AGENTS §5 step 7): rerun the nightly so the slates and the
10k season come from the latest promoted engines.

**Housekeeping:** the dataset cache key includes the profile files' modification time, so every nightly rebuild makes the
next training run build a new cache folder (~8 GB); run `nodes.py --prune` before training. `data/derived/variants/rebound_miss/`
duplicates the canonical data (safe to delete except `features_arch/`, `features_def/`). Fold models refit themselves
when their key changes.

## How to judge a change

- **Play-by-play engine:** node changes by paired fold comparisons (TRAINING_PLAN §7: `nodes.py`, `train.py`,
  `compare.py --noise 20261119T190747Z_control 20261119T190747Z_seed8`, `buckets.py`, `calibration.py`; control
  `20261119T224019Z_v1.1_folds`), then M6a (`aggregate.py`) and the **backtest** (`backtest.py`, control run below), which
  also scores the team-rating model and M6a on the same games — the engine should beat the team model on margins.
- **Team engine:** `season_backtest.py` (dispersion ≈ 1.0 at every start date, coverage 80%, CRPS, persistence ≈ 0.40);
  `--grid` with leave-one-season-out selection for settings. History only — never the 2026-27 final test.

```sh
.venv/bin/python scripts/backtest.py --config models/v1.1.json --games 200 --worlds 1000 --jobs 4   # ~30 min with fits
.venv/bin/python scripts/backtest.py --config models/v1.1.json --summarise <stamp>_backtest_v1.1_F4   # re-score a saved run
.venv/bin/python scripts/season_backtest.py [--grid]                                                # 1 min / 4 min
```

## File map

| Files | Responsibility |
|---|---|
| `basketball_common.py` | Paths, ET/UK time, conferences/divisions, NBA franchise ids, atomic JSON, archives |
| `scripts/fetch_espn.py` | Live collection: `data/raw/espn/runs/<UTC>/`, finals `data/raw/espn/final/`, logos |
| `scripts/master_fixtures.py`, `scripts/box_scores.py` | Live master fixtures; player/team game logs; player registry |
| `scripts/plays.py` | Canonical game/play schema; adapters for live ESPN and history; shot-value inference |
| `scripts/history.py` | History download (`--fetch`, manifest) and per-season reconciliation → `data/derived/history/<season>/` |
| `scripts/pbp.py` | Per-period player box scores and on-court seconds; lineup helpers |
| `scripts/possessions.py` | Segments (M2); rebound-clock convention (D23); `current_games(before=)` (cutoff-safe live games) |
| `scripts/parity.py` | M5b: same games through both adapters; Oct–Nov distributions under both conventions |
| `scripts/rotations.py` | Stints, dead-ball windows, substitutions, on-court shares; replay v0 templates (used by the engine) |
| `scripts/athletes.py` | Heights/weights/birth dates (rosters + ESPN athlete endpoint) → `data/derived/athletes.parquet` |
| `scripts/features.py` | Player profiles, team style/schedule, latest state; variants (`--segments`, `--body`, `--archetypes K`, `--defence`) |
| `scripts/evaluate.py` | Folds F1–F4, final-test boundary, M4 baselines; experiment log location |
| `scripts/nodes.py` | Datasets for the 16 decisions; cache (`data/derived/nodes/<hash>/`); optional `@body`/`@defence` inputs |
| `scripts/train.py` | LightGBM per node and fold; `--config` versions; `--final`; variants and cross-data test (`hybrid`) |
| `scripts/compare.py`, `scripts/buckets.py`, `scripts/calibration.py` | Paired comparisons (seed-noise floor; by sample size); calibration |
| `scripts/aggregate.py` | M6a: real segments replayed, every decision sampled, box-score and event accounting |
| `scripts/engine.py` | The play-by-play engine (serves `ENGINE['version']` = v1.1); clock rules from the version's own segments |
| `scripts/backtest.py` | M9: fold models + cutoff-safe inputs, games played forward, scored; team-rating model and M6a on the same games |
| `scripts/pathway.py` | **Team engine** (D25, D26): per-world offence/defence ratings, engine worlds first, updates after every game |
| `scripts/season_backtest.py` | **Team engine trust test** (M12): walk-forward 2022-26, variants and `--grid` (leave one season out) |
| `models/v1.json`, `models/v1.1.json` | Version settings, data locations, validating runs, reasons |
| `scripts/season_stats.py`, `scripts/projection.py` | Live season stats; placeholder `baseline-v1`; `simulate_season` (team pathway), `package()` |
| `scripts/nightly.py`, `scripts/views.py` | Nightly: input rebuild → engine days (`project_slate`) → one season → snapshots (`write_snapshot`) → views |
| `scripts/serve.py`, `scripts/export_musnba.py`, `scripts/nightly_musnba.py` | Local server; static shell + bundle; iCloud export |
| `scripts/webapp/` | The app (ES modules, no build); `modelPill` (`ui.mjs`) and `seasonPill` (`league.mjs`) label the models |
| `scripts/smoke.py`, `analysis/*.mjs` | 80 accounting/model checks (fault run must fail); browser and PWA checks |

Data variants: `data/derived/variants/rebound_feed/` (v1's data, feed clocks; its live season frozen at 18 Nov),
`data/derived/variants/rebound_miss/` (validated v1.1 data) with `features_arch/` and `features_def/` (ablations).

## Commands

```sh
git status && git log --oneline -5                                    # start of session; commit + push at checkpoints
.venv/bin/python scripts/smoke.py [--fault]                           # all checks (the fault run must fail)
.venv/bin/python scripts/nightly.py [--offline] [--no-rebuild] [--placeholder] [--ahead N] [--backfill-days N]
.venv/bin/python scripts/engine.py --game <id> [--worlds 2000]        # one game through the engine
.venv/bin/python scripts/serve.py --port 8767                         # your own review server (owner uses :8766)
node analysis/browser_check.mjs --base http://127.0.0.1:8767          # browser checks, both themes, phone/desktop
.venv/bin/python scripts/possessions.py [--history]                   # segments (M2; D23 convention by default)
.venv/bin/python scripts/rotations.py [--history | --backtest]        # rotations (M3)
.venv/bin/python scripts/features.py [--out DIR …]                    # profiles (M4); variants elsewhere
.venv/bin/python scripts/nodes.py [--segments DIR --features DIR/pregame.parquet | --prune]   # dataset cache
.venv/bin/python scripts/train.py --config models/v1.1.json [--final]   # validate a version / persist + final test once
.venv/bin/python -u scripts/aggregate.py --config models/v1.1.json [--games 300]   # M6a (~50 min for all 766)
```

Rebuild order after new data or a parser change: history → possessions (`--history` and current) → rotations
(`--history` and current) → features → nodes → train (the nightly does the current-season part itself). The laptop:
14 cores, 48 GB; a run from the cache needs ~2–4 GB, a chain build ~14 GB.
