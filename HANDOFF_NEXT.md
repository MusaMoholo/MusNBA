# Handoff — state and next actions

Updated **19 November 2026, ~22:30 UTC** (checkpoint: engine v1 is the app's default and the floor, D22). Read
[AGENTS.md](AGENTS.md) first. Rewrite this file at every checkpoint, then commit and push; whoever reads it next may be
a new agent.

**Git:** private repo `MusaMoholo/MusNBA` (`main`). This session's commits: `029bbe5` (M5 tuned, v1, M6a), `c1f2f5b`
(engine in the app), `bbd2bab` (engine clock rules, M6a full), then this checkpoint's commit ("D22: engine v1 is the
default…"). **Nothing runs in the background.** The owner keeps `scripts/serve.py` on :8766 open — leave it; use :8767
for your own checks.

## State

**App.** Localhost (`serve.py`, :8766) and the static PWA. **Today's slate is projected by the possession engine v1 —
the default and the floor (owner, D22)**: a later change replaces it only when the measured tests say it is better.
`nightly.py` uses the engine by default (`--placeholder` opts out; `nightly_musnba.py` passes options through).
Retrospective backfills always use the placeholder `baseline-v1` (the engine reads latest profiles — cutoff safety).
The season simulation is still the placeholder's team-strength pathway, fed the engine's win probabilities for today.
The chip in the app reads "Engine v1" (`modelPill`, `webapp/ui.mjs`); the placeholder's results are saved beside the
engine's in each snapshot (`games_placeholder.json`).

**Models (M5 done).** Model **v1**: 16 LightGBM decisions (D20 + D21: *location* — distance band within the zone — and
*team turnover* as a fourth event class). Settings and reasons in `models/v1.json` (in git); fitted files in
`data/models/v1/` (out of git, 44 MB; rebuild with `train.py --config models/v1.json --final`, which also scores the
final test — v1's is already recorded, do not rescore v1). Every node beats its best baseline on every fold (ECE ≤ 0.012)
and on the final test. All tuning results, wins and negative results: FINDINGS §3h–§3h′.

**Aggregation test (M6a done).** `aggregate.py` replays held-out games with real lineups and clock and samples every
decision: on all 766 F4 games, player points/rebounds/assists/threes within ±1.3% in every role tier, 10–90% coverage
77–81%, CRPS 6–11% better than recent averages (FINDINGS §3i). Remaining small biases: and-ones +5.4%, fouled on a three
−24%, bench free throws +6%.

**Engine (M6, default since D22).** `engine.py` plays games forward: sampled durations plus data rules for the clock
(game time after each action; whole-second bins; end-of-period segments drawn from real ones), replayed rotations
(M3 v0), each world's score, fouls, foul-outs and in-game counts; 2,000 worlds, ~20 s per game. Realism (FINDINGS §3j):
shooting on par with the league; pace ≈ 2.5% low; turnovers ≈ +1 per team; **strong offences under-expressed**
(Memphis ≈ 110 v 117.8 per 100); outcomes too tightly spread (OT ≈ 3% v 5.4%). Smoke re-simulates the stored engine game
bit-for-bit.

**Known data problem — live v history adapter skew** (FINDINGS §3h′): the live ESPN adapter (2026-27) and the hoopR
history produce different segments at the same point of the season (actions within 2 s of an offensive rebound 12% v
49%; non-shooting/shooting foul split 18.7/16.3 v 16.8/17.3 per game; live-ball turnovers 56.6% v 59.4%). Models trained
on history see shifted inputs on live games — most of the final-test calibration gap, and it biases the engine.

**Owner direction this session** (PLAN §9): shot location confirmed (D21); size and defence "are important" — fetch
heights/weights and build archetype priors so low-sample players borrow from similar players; add on-court defensive
impact; substitutions (M7) are the biggest remaining risk for box scores; the engine is the floor (D22).

## Next actions (in order)

1. **M5b — adapter parity.** Pick five 2025-26 games in the hoopR history; fetch their ESPN summaries with the live
   adapter (`scripts/fetch_espn.py` summary fetch, polite spacing — five requests) into a scratch folder; run both
   through `plays.py` → `possessions.py` and diff the segments play by play: rebound clock stamps (oreb → putback time),
   shooting v non-shooting foul classification, live v dead turnovers, offensive fouls. Fix the adapter that departs
   from ESPN's own data. Done when the five games give identical segments and 2026-27 distributions match 2025-26
   Oct–Nov within noise. Then rebuild current segments → rotations → features → nodes; v1 keeps its recorded final
   test; fit the same settings on the fixed data as **v1.1** (`models/v1.1.json`), validate on the folds, check M6a,
   and make it the engine's models only if it does better (D22).
2. **Engine backtest (start of M9).** Run `engine.py` on past games with cutoff-safe inputs — pregame profiles and team
   style for that date (`pregame.parquet`, `team_pregame.parquet`), fold models (as `aggregate.fit_models`), replay
   rotations from games before the date — and compare with what happened: possessions, team ORtg and points, margin
   and total CRPS, win calibration, player box scores, v `baseline-v1` (its snapshots exist). This is the yardstick
   every later engine change must beat (D22). `engine.Engine.diag = []` records each segment's start type, seconds and
   clock for pace diagnostics.
3. **Size and archetype priors** (owner). (a) Fetch height/weight for every player in the registry and history (ESPN
   athlete endpoint, polite, raw kept under `data/raw/espn/athletes/`). (b) In `features.py`, cluster players (k-means
   on role/style rates plus size, fitted on earlier seasons only) and shrink each rate toward the player's archetype
   instead of his position group; rookies take the archetype nearest their position and size. (c) Ablate on the folds
   with log loss by sample size (games_eff < 10, 10–40, 40+); keep if the low-sample buckets gain. Add height/weight
   and lineup size sums in the same test.
4. **On-court defensive impact** (owner): per-player pre-game rates of opponents' FG% by zone, turnover rate and rim
   share while he is on the floor (decayed, shrunk) in `features.py`; lineup sums in `nodes.py` (`def_*`); ablate on
   shot result, what, blocked, turnover type, rebound. Expected to help strong/weak teams separate (the engine's
   under-expressed offences).
5. **Engine realism** (FINDINGS §3j): pace ≈ 2.5% low and turnovers ≈ +1 per team — confirm over many games in the
   backtest, then trace with the diag records and M6a event accounting; per-world form (D3, M8) for the spread
   (targets: total SD ≈ 18–19, OT ≈ 5.4%).
6. **M6a follow-ups**: the foul classes of what/shot result (and-ones +5.4%, fouled on a three −24%, bench free
   throws +6%).
7. **Experiments queued by the tuning results** (each on the folds, `compare.py` against `…control2` with seed noise):
   split the profile *usage* family so rebounding/defence rates get their own longer half-life; accuracy half-life
   120/160 games; finer location bands (bands cost 0.50 nats per game v exact distance); team style for more nodes.
8. **Speed**: one engine step for 10,000 worlds costs ~0.72 s summed over nodes on a busy machine; score only the worlds
   that reach each node and batch games before raising worlds to 10,000 (D10: ≤ 60 s per game).
9. Then M7 (target-aware substitutions — the biggest remaining risk) → M8 (form, end-game) → M9 (full backtest).

## How to judge a change (TRAINING_PLAN §7)

```sh
.venv/bin/python scripts/nodes.py                         # dataset cache for the current code + inputs (~1 min)
.venv/bin/python -u scripts/train.py --name <label> --threads 3 [--drop @team …]     # ~20 min; 4 in parallel fit the laptop
.venv/bin/python scripts/compare.py <control> <run> --noise 20261119T190747Z_control 20261119T190747Z_seed8
.venv/bin/python scripts/calibration.py <run>              # excess ECE by period and margin
```

Control on the current data: `20261119T194404Z_control2` (v1 inputs, exact distance); v1 as a whole:
`20261119T210324Z_v1_folds`. A change is kept for a node when its mean change beats −noise with pooled z ≤ −2 and no fold
is worse by more than 2 × noise; global changes are also read on the chain row (nats per game). Log every run; record
wins and negative results in FINDINGS. Never edit `nodes.py` while runs read a cache built from it.

## File map

| Files | Responsibility |
|---|---|
| `basketball_common.py` | Paths, ET/UK time, conferences/divisions, NBA franchise ids, atomic JSON, archives |
| `scripts/fetch_espn.py` | Live collection: `data/raw/espn/runs/<UTC>/`, finals `data/raw/espn/final/`, logos |
| `scripts/master_fixtures.py`, `scripts/box_scores.py` | Live master fixtures; player/team game logs; player registry |
| `scripts/plays.py` | Canonical game/play schema; adapters for live ESPN and history; shot-value inference |
| `scripts/history.py` | History download (`--fetch`, manifest) and per-season reconciliation → `data/derived/history/<season>/` |
| `scripts/pbp.py` | Per-period player box scores and on-court seconds; lineup helpers |
| `scripts/possessions.py` | Segments (M2) with lineups, state, outcomes, `ft_seq`; `game_ok` flag |
| `scripts/rotations.py` | Stints, dead-ball windows, substitutions, on-court shares; replay v0 templates (used by the engine) |
| `scripts/features.py` | Player profiles, team style/schedule (`team_pregame`), latest team style (`team_latest`); variants |
| `scripts/evaluate.py` | Folds F1–F4, final-test boundary, M4 baselines; experiment log location |
| `scripts/nodes.py` | Datasets for the 16 decisions; on-disk cache (`data/derived/nodes/<hash>/`); location bands |
| `scripts/train.py` | LightGBM per node and fold; options; `--config` versions; `--final` persist + final test |
| `scripts/compare.py`, `scripts/calibration.py` | Paired run comparison with seed-noise floor; calibration by period/margin |
| `scripts/aggregate.py` | M6a: branch tables from real segments, 10,000-world sampler, box-score and event accounting |
| `scripts/engine.py` | Engine v1 (default projection): games played forward with the v1 nodes and clock rules |
| `models/v1.json` | v1 settings, the fold run that validated them, and why |
| `scripts/season_stats.py`, `scripts/projection.py` | Live season stats; placeholder `baseline-v1`, season sim, `package()` (output contract) |
| `scripts/nightly.py`, `scripts/views.py` | Live orchestration (engine by default), snapshots, API views |
| `scripts/serve.py`, `scripts/export_musnba.py`, `scripts/nightly_musnba.py` | Local server; static shell + bundle; iCloud export |
| `scripts/webapp/` | The app (ES modules, no build); `modelPill` in `ui.mjs` labels the model |
| `scripts/smoke.py`, `analysis/*.mjs` | 66 accounting/model checks (fault run must fail); browser (38) and PWA checks |

## Commands

```sh
git status && git log --oneline -5                                    # start of session; commit + push at checkpoints
.venv/bin/python scripts/smoke.py [--fault]                           # 66 checks (the fault run must fail)
.venv/bin/python scripts/nightly.py [--offline] [--placeholder] [--backfill-days N]   # collect → snapshot (engine) → views
.venv/bin/python scripts/engine.py --game <id> [--worlds 2000]        # one game through the engine
.venv/bin/python scripts/serve.py --port 8767                         # your own review server (owner uses :8766)
node analysis/browser_check.mjs --base http://127.0.0.1:8767          # 38 browser checks, both themes, phone/desktop
.venv/bin/python scripts/history.py [--fetch]                         # history reconcile (M1)
.venv/bin/python scripts/possessions.py [--history]                   # segments (M2)
.venv/bin/python scripts/rotations.py [--history | --backtest]        # rotations (M3)
.venv/bin/python scripts/features.py [--out DIR --family usage=30]    # profiles (M4); variants elsewhere
.venv/bin/python scripts/nodes.py [--features DIR/pregame.parquet | --prune]   # dataset cache
.venv/bin/python scripts/train.py --config models/v1.json [--final]   # validate a version / persist + final test once
.venv/bin/python -u scripts/aggregate.py --config models/v1.json [--games 300] [--worlds 10000]   # M6a (~45 min for all)
```

Rebuild order after new data or a parser change: history → possessions (`--history` and current) → rotations
(`--history` and current) → features → nodes → train. The laptop: 14 cores, 48 GB; a run from the cache needs ~2 GB, a
chain build ~14 GB; `data/derived/nodes/` holds ~8 GB per cache folder (`nodes.py --prune` clears stale ones).
