# Handoff — state and next actions

Updated **20 November 2026, afternoon UK** (checkpoint: **engine v1.3** — D29 minutes + D30 defence inputs, both promoted on
the backtest; **joint and conditional outcomes in the app** (Scenarios tab, Given…, joint grids, drivers); Forecast Lab;
projected-starter record). Read [AGENTS.md](AGENTS.md) first. Rewrite this file at every checkpoint, then commit and push;
whoever reads it next may be a new agent.

**Git:** private repo `MusaMoholo/MusNBA` (`main`). Previous checkpoint `946314a`; this chunk's commit ("D29–D30 chunk: engine v1.3 …") is the
latest (`git log --oneline -3`). Snapshots 2026-11-20 (9 games) and 2026-11-21 (6) are engine v1.3 + team pathway v1; the
morning's v1.1 and the interim v1.2 snapshots are archived in `~/Basketball_archive_ops/`. **Nothing runs in the background.** The owner keeps `scripts/serve.py` on :8766 open — leave
it; use :8767 for your own checks.

**How the owner wants a chunk run (AGENTS §3):** state your understanding and **one or two headliners**; print the progress
board (active subtasks + overall, text bars) **in the reply text** at every subtask 10% / overall 5% mark — also during long
build stretches and while answering his mid-turn questions (he reminded us twice on 20 Nov).

## The product in one paragraph (ENGINE_PLAN D26)

On any date D: every game before D is resulted; the **play-by-play engine** (v1.3) simulates today's and tomorrow's games
— or the next slate if neither has games — with inputs carried over from every game before D; the **team engine**
(team pathway v1) plays every later game in each of 10,000 worlds with that world's own ratings, updated after every game.
Season outputs are counts over the worlds. The app slices the engine's stored worlds for joint and conditional outcomes.

## State

**Play-by-play engine v1.3 (D34; `ENGINE` in `scripts/engine.py`, `models/v1.3.json`, models `data/models/v1.3/`).**
- **D29 minutes** (`scripts/minutes.py`): healthy-role minutes (absence-corrected decayed average), priority (+ start
  share), 240 per team allocated by priority (shortfall shared by headroom under each player's recent maximum; surplus
  squeezed from the lowest priority), return ramp learned per cutoff, rotation share from coach's-decision DNPs (live
  only), per-world draws re-solved to 240; the engine's rotation tables keep a replayed template's shape and fit a
  per-player offset to each table's targets (`Game._target_tables`, 400 tables per side, 10-s bins). Projected starters =
  start share then priority (`minutes.projected_starters`) — they open the game and are the app's starters.
- **D30 defence inputs**: defender-side on-court defence with shrinkage ×0.2 (`features.py --defence --defence-k-scale 0.2`),
  a soft matchup assignment (`scripts/matchups.py`, θ `models/matchup_2025-12-31.json`) weighting each actor's likely
  defenders (`mu_*` inputs: FG% allowed by zone, turnovers forced, fouls on their men, size gap), help at the rim (best rim
  protector on the floor), shot-type shares from the play text. Variant data: `data/derived/variants/matchup/features/`,
  rebuilt by the nightly (`models/v1.3.json` → `features_variant`); the engine reads its profiles there (`engine.features_dir`).
- **Backtest (same 200 F4 games, FINDINGS §3r–§3s):** stars' minutes +6.5% → −0.9%, points +8.8% → +1.8%, minutes 10–90%
  coverage 58–63% → 77–83%; defence loading 0.42 → 0.69 (real 1.69); margin CRPS 9.64 → 9.37 (team-rating model 9.32), total
  12.10 → 11.72 (11.35), win log loss 0.592 → 0.571 (0.558). Still: offence ~65% of real, totals too narrow (coverage 70%),
  teammates' points barely correlated (−0.13 to −0.01; no shared upside → per-world form, M8).
- **Final test v1.3** (2026-27 to 19 Nov, scored once; `…120935Z_final_v1.3`): every node above its baselines, level with
  v1.1's (event +18.3%, assisted +25.7%, what +5.7%, location +4.4%, shot result +2.1%); ECE high only for rebound 0.017 and
  turnover type 0.024 (2026-27 shifts — refits with this season's rows, next actions 5).
- Lineups (D33): no external source passes (FINDINGS §1); the nightly scores projected v actual starters
  (`scripts/lineups.py` → `data/derived/lineups/accuracy.json`): 82.1% of slots / all five 30.4% over the 112 team-games
  before v1.2 (old rule); our projection on Jan–Apr 2026 with known availability: 89.4% / 53.5%.

**Team engine (team pathway v1, D25)** — unchanged this chunk (FINDINGS §3n).

**App (DASHBOARD_PLAN):** Engine v1.3 chip; Game Centre **Scenarios** tab (`#/game/<id>/scenario[/<conditions>]`: stack
conditions on any player, team or the game; both box scores, team points, win, total, margin re-read from the matching
worlds with Δ v all; joint chance v independence; quick scenarios incl. "X sits" for maybes); player sheet **Given…**
(overlay histogram + over/under under a condition), **joint grid** (any two outcomes, correlation), **Tonight v his
averages**, minutes basis; team view **who drives the result** (win % on big/quiet nights and without him, r with margin,
teammates' points correlations, who gains when a maybe sits); box score Δ v season average; Today cards show each side's
projected top scorer; **Lab** page (`#/lab`; owner: not a priority — keep, no more work). Data: `engine_players.npz` in
each engine snapshot → `api/game/<id>/worlds.json` (base64 uint8 worlds × players × 12 stats + team points by period).

**Checks (20 Nov, after the v1.3 nightly):** smoke **87/87**, `--fault` fails 11; browser **56/56** on :8767. New smoke checks: allocations sum to 240, ramp range, per-world draws re-solve
to 240, rotation tables five-on-court and 240, matchup assignment rows sum to 1, lineup record identity, worlds file
(players' points = team points in every world; mean = projection); `--fault` fails; browser checks on :8767 incl. lab,
scenario, scenario-set, team-drivers, sheet-whatif, today-leaders.

## Next actions (in order — the owner may reorder)

1. **NBA Stats data chunk (owner, D32; PLAN §9.1).** The owner authorised the unofficial NBA Stats API (browser-style
   headers) for richer data; this chunk is ingest and cleaning, then defence:
   (a) adapter `scripts/fetch_nbastats.py` with raw retention (`data/raw/nbastats/<endpoint>/<season>/`, gzip, polite
   spacing, resumable), starting with play-by-play v3, box score matchups (`boxscorematchupsv3`: partial possessions per
   defender–attacker pair, points, FGA), player tracking defence (shooting allowed by defender distance), hustle (contests,
   deflections) for 2022-23 → today; (b) crosswalk NBA ids ↔ ESPN ids (games by date + teams; players by team + name +
   jersey; log every unmatched); (c) reconciliation against our ESPN segments and box scores (points, possessions, minutes
   per player-game — expect mismatches; record them in FINDINGS); (d) replace the soft assignment with real matchup shares
   (who guarded whom, per game) and defender quality from them; fold models, then the backtest v v1.3 (judge: player
   tiers first, then `strength_loading.opp_defence` 0.69 → 1.69, margin CRPS v the team model 9.32).
2. **Lineups and maybes (D33).** A learned chance-to-play and chance-to-start per player from ESPN report history
   (questionable / doubtful / day-to-day / probable → played?, started?), replacing the fixed availability table; then
   D31 branches (X plays / X sits, 10,000 sims each, Expected = availability blend) — the Scenarios tab already shows
   "X sits" from the availability worlds. Done when the nightly record of starters beats 82% of slots.
3. **Shot-type node (FINDINGS §3q).** Knowing the shot type is worth −0.34% shot result, −1.3% blocked (upper bound; assisted
   −17% is partly a near-label). Test a "shot type given zone, band, shooter" node judged on the joint likelihood of the
   shared outcomes (type marginalised) and the backtest.
4. **Spread and form (M8):** totals coverage 70%, teammates' points nearly uncorrelated — per-world form (efficiency,
   pace) with role-dependent spread; OT rate.
5. **Team engine start and drift (M12)**, outcome-first market benchmark (`market.py`), refits with 2026-27 data and the
   weekly refit design (D11; also refit the matchup θ), M7 substitutions, M10 watch-a-sim — as listed in PLAN §6.
6. **UX backlog (PLAN §9b):** competition tabs (NBA Cup, playoffs bracket per world), watch-a-sim (D9/M10), the localhost
   lineup editor (D31). Scenario ideas the owner liked: extend "Given…" to quarter outcomes and leads, a "build a combo"
   list with correlation lift, player A v player B duels.

**End every chunk with the dashboard on the newest systems** (AGENTS §5 step 7): rerun the nightly so the slates and the
10k season come from the latest promoted engines.

**Housekeeping:** the dataset cache key includes the profile files' modification time, so every nightly rebuild makes the
next training run build a new cache folder (~8 GB); run `nodes.py --prune` before training (it keeps only the default
folder — also delete `data/derived/nodes/variant_*` by hand when no run needs it). `nodes.py`'s own hash is in the key too.
Backtests can reuse fitted fold models with `--models folds/<version>_F4_all`.

## How to judge a change

- **Play-by-play engine:** node changes by paired fold comparisons (TRAINING_PLAN §7: `train.py`, `compare.py --noise
  20261119T190747Z_control 20261119T190747Z_seed8`), then the **backtest** (`backtest.py`, same seed → same 200 games) v
  the current engine's run, compared with `backtest_compare.py` (players first: tier bias, coverage, CRPS paired by game;
  then strength loading, margins, CRPS v the team-rating model). Current engine run: `20261120T120816Z_backtest_v1.2d_minutes_F4`
  (v1.3); before it `…114433Z_backtest_v1.1_minutes_F4` (v1.2) and `…100616Z_backtest_v1.1_F4` (v1.1).
- **Minutes:** `minutes.py --evaluate` (no engine; tune on Jan–Apr 2025, confirm on 2026) before any backtest.
- **Team engine:** `season_backtest.py` (dispersion ≈ 1.0 at every start date, coverage 80%, persistence ≈ 0.40).

```sh
.venv/bin/python scripts/backtest.py --config models/v1.3.json --games 200 --worlds 1000 --jobs 7 --rotation targets   # v1.3 (fits F4 models first)
.venv/bin/python scripts/backtest_compare.py 20261120T120816Z_backtest_v1.2d_minutes_F4 <new run> [--log NAME]
.venv/bin/python scripts/minutes.py --evaluate --season 2025 --from 2025-01-01 --to 2025-04-30 [--set gamma=1]
.venv/bin/python scripts/season_backtest.py [--grid]
```

## File map

| Files | Responsibility |
|---|---|
| `basketball_common.py` | Paths, ET/UK time, conferences/divisions, NBA franchise ids, atomic JSON, archives |
| `scripts/fetch_espn.py` | Live collection: `data/raw/espn/runs/<UTC>/`, finals `data/raw/espn/final/`, logos |
| `scripts/master_fixtures.py`, `scripts/box_scores.py` | Live master fixtures; player/team game logs (DNP reasons); player registry |
| `scripts/plays.py`, `scripts/history.py` | Canonical play schema and adapters; history download and reconciliation |
| `scripts/pbp.py`, `scripts/possessions.py` | Per-period box scores and on-court seconds; segments (M2, D23 convention) |
| `scripts/rotations.py` | Stints, windows, substitutions, on-court shares; replay templates (shapes for the engine's tables) |
| `scripts/minutes.py` | **D29**: healthy roles, priority, 240 allocation, ramp, rotation share, per-world draws, projected starters, `--evaluate` |
| `scripts/matchups.py` | **D30**: soft matchup assignment (`--fit`), `mu_columns` shared by datasets and engine, shot types from the play text |
| `scripts/lineups.py` | Projected v actual starters per finished snapshot (nightly; D33) |
| `scripts/athletes.py`, `scripts/features.py` | Heights/weights; profiles and variants (`--defence --defence-k-scale`, `--matchup`, `--shot-types`, `--body`, `--archetypes`) |
| `scripts/evaluate.py`, `scripts/nodes.py`, `scripts/train.py` | Folds; datasets (defender-side and `mu_*` columns when the features carry them); LightGBM per node, `--final` |
| `scripts/compare.py`, `scripts/buckets.py`, `scripts/calibration.py`, `scripts/aggregate.py` | Paired node comparisons; calibration; M6a |
| `scripts/engine.py` | The engine (v1.3): `ENGINE` (`models`, `rotation`), `features_dir`, target rotation tables, matchup inputs |
| `scripts/backtest.py`, `scripts/backtest_compare.py` | M9 (`--rotation`, `--models`, `--known-starters`); paired run comparison |
| `scripts/pathway.py`, `scripts/season_backtest.py` | Team engine and its walk-forward test |
| `models/v1.1.json`, `v1.2.json`, `v1.2d.json`, `v1.3.json`, `matchup_2025-12-31.json` | Version settings, validating runs, reasons; matchup θ |
| `scripts/season_stats.py`, `scripts/projection.py` | Live season stats; placeholder; `simulate_season`; `package()` (minutes basis) |
| `scripts/nightly.py`, `scripts/views.py` | Nightly: input rebuild (+ the engine's features variant) → engine days (per-world player lines) → season → snapshots → views (averages, worlds, lab, leaders) |
| `scripts/serve.py`, `scripts/export_musnba.py`, `scripts/nightly_musnba.py` | Local server; static shell + bundle; iCloud export |
| `scripts/webapp/` | The app; `outcomes.mjs` (worlds, conditions, overlay, grids), `scenario.mjs` (Scenarios, Given…, drivers), `lab.mjs` |
| `scripts/smoke.py`, `analysis/*.mjs` | Accounting/model checks (fault run must fail); browser checks (`--only`, `--from N` captures a page's last N px) |

## Commands

```sh
git status && git log --oneline -5                                    # start of session; commit + push at checkpoints
.venv/bin/python scripts/smoke.py [--fault]                           # all checks (the fault run must fail)
.venv/bin/python scripts/nightly.py [--offline] [--no-rebuild] [--placeholder] [--ahead N] [--backfill-days N]
.venv/bin/python scripts/serve.py --port 8767                         # your own review server (owner uses :8766)
node analysis/browser_check.mjs --base http://127.0.0.1:8767 [--only a,b] [--from 2400]
.venv/bin/python scripts/lineups.py --score                           # projected v actual starters
.venv/bin/python scripts/matchups.py --fit --through 2025-12-31       # D30 assignment θ
.venv/bin/python scripts/features.py --out data/derived/variants/matchup/features --defence --defence-k-scale 0.2 --matchup models/matchup_2025-12-31.json --shot-types
.venv/bin/python scripts/nodes.py --features data/derived/variants/matchup/features/pregame.parquet   # variant datasets
.venv/bin/python scripts/train.py --config models/v1.3.json [--folds F4 | --final]
```

Rebuild order after new data or a parser change: history → possessions → rotations → features (default, then the
variant) → nodes → train (the nightly does the current-season part itself, variant included). The laptop: 14 cores,
48 GB; a chain build ~14 GB; the nightly with 15 engine games at 2,000 worlds ≈ 10–15 min when the machine is quiet.
