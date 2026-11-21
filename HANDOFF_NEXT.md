# Handoff — state and next actions

Updated **20 November 2026, evening UK** (checkpoint: **D32 chunk** — NBA Stats ingested and cross-walked; defence on real
matchups built and measured (**negative: v1.3 stays, D37**); 10,000 worlds per game and one rotation table per world (D36);
a large dashboard round). Read [AGENTS.md](AGENTS.md) first. Rewrite this file at every checkpoint, then commit and push;
whoever reads it next may be a new agent.

**Git:** private repo `MusaMoholo/MusNBA` (`main`). Previous checkpoint `6d156a4`; this chunk's commit ("D32 chunk: …") is the
latest (`git log --oneline -3`). Snapshots **2026-11-21 (6 games) and 2026-11-22 (7 games) were built by the close-out nightly
on 21 Nov, 23:01 UK, at 10,000 worlds per game with per-world rotation tables** (engine v1.3, team pathway v1, season 965 games);
earlier copies archived in `~/Basketball_archive_ops/`. **Nothing runs in the background**: the NBA Stats history download is
paused at play-by-play v3 1,895 / 5,508 games (resumable — next actions 4). The owner keeps `scripts/serve.py` on :8766 open —
leave it; use :8767 for your own checks.

**How the owner wants a chunk run (AGENTS §3):** state your understanding and **one or two headliners**; **plan every subtask as
a ladder of ten 10% steps with done-when criteria** and weights for the chunk %, keep the ladders below, and print the board
(active subtasks + overall, text bars) **in your messages to him** at every subtask 10% / overall 5% mark — during long jobs and
while answering his questions too. **Give time estimates from measured job rates** (he says agents overestimate). He sends
many UX requests mid-chunk; do them, check every touched page at 1440 / 960 / 390 in both themes and look at the screenshots.

## Progress ladders — next chunk: "Express team strength, make minutes react" (proposed to the owner, 21 Nov)

Headliners: **(1) team-difference compression** (next actions 1) and **(2) M7 game-state substitutions** (next actions 2); the
chunk closes with major and minor dashboard work tied to both. Chunk % = 0.35 · S1 + 0.30 · S2 + 0.25 · S3 + 0.10 · S4; each step
is 10% of its subchunk — post the board when a step or a 5% chunk mark is crossed.

| Subchunk | Steps (10% each, in order; done when …) |
|---|---|
| **S1 Team-difference compression (35%)** | M6a v engine component loadings on the same 200 games (where the signal is lost) · node expression audit (slope real-on-predicted by shooter/defender/team-style deciles) · 2–3 levers chosen with expected effects · candidate A built · A fold runs paired v v1.3 · candidate B built · B fold runs paired · backtests A and B (one at a time) · decision (promote v1.4, final test once, or D38 negative) · total-bias (+1 pt in v1.4 variants) traced + FINDINGS/ENGINE_PLAN |
| **S2 M7 game-state substitutions (30%)** | substitution windows with game state + FINDINGS facts (blowout minutes by tier, foul-trouble benching) · out/in datasets per dead ball · baseline: replayed schedules v real sub rates · models on the folds · engine integration as a soft pull to D29 targets (five on court, 240 minutes — smoke) · minutes by game state by tier v history (F4) · backtest (minutes by tier first) · pull strength tuned on F4 · decision · docs + smoke identities |
| **S3 Dashboard (25%)** | **major**: rotation-map data (P on court per player per minute; Σ = 5 smoke) · rotation-map view (players × 48-min heat strip; blowout/close toggle if M7 promotes) · watch-a-sim data (5 saved worlds' event logs, D9/M10) · watch-a-sim list (nba.com-style play-by-play, quarter jumps, filters) · **minor**: player face cards fetched once + retained · face cards in spotlight, sheets, box scores, player pages · tracking-defence insight on player pages (contest FG% allowed v normal) · win % Δ back if S1 makes engine and ratings consistent (else deferred + alternative) · "role change tonight" badges on Today (±4 min and why) · full sweep 1440/960/390 both themes + DASHBOARD_PLAN |
| **S4 Close-out (10%)** | resume NBA pbp history early (background, ~75 min) · pbp complete · nightly 10k started · nightly done (~30 min) · browser checks · browser fixes · smoke + new checks · `--fault` fails · docs · commit + push |

Sequencing: S2's data steps run while S1's fold models train; never two backtests at once; pause the pbp download during the
nightly; if S1 and S2 both promote, one production retrain (`train.py --final`) covers both.

## The product in one paragraph (ENGINE_PLAN D26)

On any date D: every game before D is resulted; the **play-by-play engine** (v1.3) simulates today's and tomorrow's games
— or the next slate if neither has games — with inputs carried over from every game before D, **10,000 worlds per game**; the
**team engine** (team pathway v1) plays every later game in each of 10,000 worlds with that world's own ratings. Season outputs
are counts over the worlds. The app slices the engine's stored worlds for joint and conditional outcomes (localhost only; the
phone bundle is stripped back, D36).

## State

**Play-by-play engine v1.3 (D34; `ENGINE` in `scripts/engine.py`, `models/v1.3.json`, models `data/models/v1.3/`)** — unchanged
models; **10,000 worlds** (`ENGINE['sims']`, nightly default) and **one rotation table per world** (`ENGINE['pool'] = 0`;
backtest: players level, totals level, +5% time; FINDINGS §3v). D29 minutes, D30 defence inputs as before.

**NBA Stats (D32) — ingested, retained, refreshed nightly.**
- `scripts/fetch_nbastats.py`: stdlib urllib with Chrome fetch headers (`Sec-Fetch-*`, `sec-ch-ua` — without them stats.nba.com
  connects and never answers), ~1 request/s with jitter, retries with backoff, stops after 5 failures in a row, resumable
  (present files skipped; un-flushed files recorded in the manifest on resume). Raw: `data/raw/nbastats/<endpoint>/<season>/`
  (gzip + `manifest.json` with sha256). Retained: season logs (51), `boxscorematchupsv3` all 5,508 games (2022-23 → 19 Nov 2026),
  `leaguedashptdefend` per date (Overall, <6 ft, threes; 2,628), `playbyplayv3` 1,895 games (paused). Hustle (`--hustle`, per
  date) coded, not fetched. The nightly fetches new finals (`fetch_nba_stats`: ~10–15 requests; failures never stop it).
- `scripts/nbastats.py`: crosswalk 5,508/5,508 games (ET date + team pair), 118,024/118,041 player-games (17 unmatched: Lachlan
  Olbrich has no ESPN id); reconciliation (points identical, our minutes within 60 s of NBA's in 99.87%, possessions +0.9);
  matchups → `data/derived/nbastats/matchups.parquet` (1.04M rows, ESPN ids). 2022-24 matchups over-count FGA (111%) — FINDINGS §3t.
- `scripts/realmatch.py`: pre-game assignment on real shares (top-1 36.4% → 50.2%, top-2 75%; θ `models/realmatch_2025-12-31.json`,
  `realmatch_top2_…`), per-game pair history (`pair_history.parquet`). The nightly refreshes crosswalk, matchups and pair history
  (`refresh_real_matchups`) whenever NBA files are retained.

**Defence on real matchups — measured, not promoted (D37; FINDINGS §3s′, §3u, §3w).** v1.3's gap is shot-making (FG% 37%, 3P%
18% of the real effect; turnovers 95%). Candidates on the 200-game F4 backtest: v1.4c (real-share defender quality + θ), v1.4e
(+ deterrence: 3P% → 30%, FTA → 48% of real), v1.4f (+ top-1/top-2 defenders, owner's idea) — all level or worse on margins,
totals and players. Switch hunting (D35) not visible (v1.4d not run). Defender traits: 3PA share allowed r 0.77, 2P% 0.49, 3P%
allowed noise (−0.05). **Reading: the engine compresses team differences generally** (offence 0.73, defence 0.69 of real;
every component but turnovers at 20–40%). Specs `models/v1.4{c,d,e,f}.json` (status NOT PROMOTED / NOT RUN), variants
`data/derived/variants/realmatch{,_dx,_top2,_hunt}/`, fold models `data/models/folds/v1.4{c,e,f}_F4_all`.

**Team engine (team pathway v1, D25)** — unchanged.

**App (DASHBOARD_PLAN) — this chunk:** Today/Game Centre **Spotlight** (headliner with points sparkline and 30+/40+/double/
triple chances; breakout watch as a season→tonight dumbbell with the why; six leaders with each one's chance to lead the night
or game; Today's games to watch: closest finish, highest-scoring, likeliest overtime);
**who guards whom** (Matchup view, real matchups, earlier meetings + this game) and **player head-to-head** on sheets; Scenarios
**game flow** (quarters, leads, comebacks, sweeps, lead changes) and **Duels**, grouped dropdowns and quick-scenario rows; Today
**duel of the night**, stacked leaders with suffixes; Standings **Wins** tab (5-win bands), Forecast **wins/seed pickers**, W%,
Proj W / Proj L, sortable, current | projected split; player sheet **Shooting/Chances tiles** (multi-doubles, 5×5), grouped
picker (Scoring · Rebounding ALL/OFF/DEF · Handling · Defense · Time; makes and main stats only); box score Δ v season (incl.
STL/BLK, shooting x/y (z%) coloured per part); bezel points Δ v season (above the value; no win/total Δ); player page "Open
simulation" for tomorrow's games; phone bundle stripped back (D36).

**Checks (close-out, 21 Nov):** smoke **99/99**, `--fault` fails 19 (new: NBA Stats manifests, crosswalk one-to-one, matchups =
raw, real weights sum to 1, pair history cutoff-safe, phone bundle stripped, multi-doubles nested, wins distributions sum to
the seasons); browser **81/81** on :8767 (cases now include `game-proj` on a 22 Nov game, `today-leaders` 21 Nov, `tomorrow`
22 Nov, `standings-wins`, `game-duels`). Nightly at 10,000 worlds: ~4 min input rebuild (incl. NBA Stats refresh) + ~130–150 s
per game (13 games ≈ 30 min).

## Next actions (in order — the owner may reorder)

1. **Team-difference compression (the real engine gap, D37).** Measure where team differences are lost: M6a (real possessions
   replayed) v the free-running engine on component loadings (FG%, OREB, FTA, TOV by opponent and own rating); per-node
   "expression" of profile differences (e.g. shot-result prediction spread v real spread across shooters/defences); profile
   shrinkage (accuracy family K, defence ×0.2) and node temperatures as levers. Judge only on the backtest (players first).
   Also trace why every real-matchup variant raised the total bias by ~+1 point.
2. **M7 game-state substitutions** (owner, 20 Nov: minutes should react to blowouts and foul trouble; Dončić's minutes are 35.4
   / 35.6 / 35.7 in close / mid / blowout games, FINDINGS §3v): a substitution model at dead balls from score, clock, fouls,
   stint length, learned from `subs.parquet` windows; done when blowout and foul-trouble minutes match history by tier and the
   backtest's minutes CRPS improves.
3. **Lineups and maybes (D33)** — learned chance-to-play/start from ESPN report history; then D31 branches (localhost only, D36).
4. **NBA Stats housekeeping:** resume the play-by-play history when convenient
   (`.venv/bin/python -u scripts/fetch_nbastats.py --pbp`, ~75 min polite), optionally `--hustle` (~18 min). Parse tracking
   defence (`leaguedashptdefend`: D_FG% v normal by closest defender) into a defender column and test it as a candidate input.
5. **Per-world form and spread (M8)** — totals coverage 69%, teammates' points nearly uncorrelated.
6. **UX backlog (PLAN §9b + owner, 20 Nov):** player face cards (ESPN headshots fetched once, retained locally like logos) in
   spotlight cards, box scores and player pages; win % Δ only once the engine expresses team strength (dropped: two models
   disagree); competition tabs; watch-a-sim (M10); localhost lineup editor.

**End every chunk with the dashboard on the newest systems** (AGENTS §5 step 7): rerun the nightly (10,000 worlds now takes
~25–30 min for 15 games) so the slates and the 10k season come from the latest promoted engines.

**Housekeeping:** dataset caches under `data/derived/nodes/` (~9 GB each; this chunk added the realmatch variants — prune with
`nodes.py --prune` plus the `variant_*` folders when no run needs them; two are symlinks to unchanged folders). The cache key
now includes the assignment θ, `matchups.py`, `realmatch.py` and the pair history (`nodes.signature`).

## How to judge a change

- **Play-by-play engine:** node changes by paired fold comparisons (TRAINING_PLAN §7), then the **backtest** (`backtest.py`, same
  seed → same 200 games) v the current engine's run with `backtest_compare.py` (players first: tier bias, coverage, CRPS paired by
  game; then strength loading, component loadings, margins, CRPS v the team-rating model). Current engine runs:
  `20261120T133953Z_v1.3_components_F4` (v1.3, shared pool, with components) and `…162930Z_v1.3_pool_per_world_F4` (per-world
  tables — the serving setting). Backtests now log per-side components (`summary.team_rating_baseline.component_loadings`).
- **Minutes:** `minutes.py --evaluate` before any backtest. **Team engine:** `season_backtest.py`.

```sh
.venv/bin/python scripts/backtest.py --config models/v1.2d.json --models folds/v1.2d_F4_all --games 200 --worlds 1000 --jobs 7 --rotation targets --pool 0   # v1.3 as served
.venv/bin/python scripts/backtest_compare.py 20261120T162930Z_v1.3_pool_per_world_F4 <new run> [--log NAME]
```

Two backtests at once oversubscribe the CPU (each worker predicts with every core): one alone takes ~22–27 min for 200 games.

## File map

| Files | Responsibility |
|---|---|
| `basketball_common.py` | Paths, ET/UK time, conferences/divisions, NBA franchise ids, atomic JSON, archives |
| `scripts/fetch_espn.py` | Live collection: `data/raw/espn/runs/<UTC>/`, finals `data/raw/espn/final/`, logos |
| `scripts/fetch_nbastats.py` | **D32** NBA Stats adapter (Chrome fetch headers, ~1 req/s, resumable): logs, matchups, tracking defence, pbp v3, hustle; `recent()` in the nightly |
| `scripts/nbastats.py` | **D32** crosswalk, reconciliation v ESPN, matchups in ESPN ids → `data/derived/nbastats/` (`games`, `players`, `matchups`, `pair_history`, `report.json`, `unmatched.json`) |
| `scripts/realmatch.py` | **D32** assignment on real shares (`--fit [--save --set]`), pair history (`--history`), `pair_matrix` for the engine |
| `scripts/master_fixtures.py`, `scripts/box_scores.py` | Live master fixtures; player/team game logs (DNP reasons); player registry |
| `scripts/plays.py`, `scripts/history.py` | Canonical play schema and adapters; history download and reconciliation |
| `scripts/pbp.py`, `scripts/possessions.py` | Per-period box scores and on-court seconds; segments (M2, D23 convention) |
| `scripts/rotations.py` | Stints, windows, substitutions, on-court shares; replay templates (shapes for the engine's tables) |
| `scripts/minutes.py` | **D29**: healthy roles, priority, 240 allocation, ramp, rotation share, per-world draws, projected starters, `--evaluate` |
| `scripts/matchups.py` | **D30**: soft assignment (`--fit`); `mu_columns` (soft or real θ; top-2 and deterrence outputs) shared by datasets and engine; shot types |
| `scripts/lineups.py` | Projected v actual starters per finished snapshot (nightly; D33) |
| `scripts/athletes.py`, `scripts/features.py` | Heights/weights; profiles and variants (`--defence`, `--matchup`, `--real-matchups` (REAL_MATCHUP_K, stopper, deterrence), `--shot-types`, `--body`, `--archetypes`) |
| `scripts/evaluate.py`, `scripts/nodes.py`, `scripts/train.py` | Folds; datasets (`mu_*`, top-2, deterrence, who-mismatch columns by report flags); LightGBM per node, `--final` |
| `scripts/compare.py`, `scripts/buckets.py`, `scripts/calibration.py`, `scripts/aggregate.py` | Paired node comparisons; calibration; M6a |
| `scripts/engine.py` | The engine (v1.3): `ENGINE` (`models`, `rotation`, `sims` 10,000, `pool` 0), target rotation tables, matchup inputs |
| `scripts/backtest.py`, `scripts/backtest_compare.py` | M9 (`--rotation`, `--models`, `--known-starters`, `--pool`; component loadings); paired comparison |
| `scripts/pathway.py`, `scripts/season_backtest.py` | Team engine and its walk-forward test |
| `models/*.json` | Version settings (v1.1–v1.3 promoted; v1.4c/d/e/f not promoted), matchup θ (soft `matchup_…`, real `realmatch_…`) |
| `scripts/season_stats.py`, `scripts/projection.py` | Live season stats; placeholder; `simulate_season`; `package()` (OREB/DREB/FGM/FTM distributions, multi-doubles, 5×5) |
| `scripts/nightly.py`, `scripts/views.py` | Nightly: ESPN + NBA Stats fetch → input rebuild (+ real matchups) → engine days (10k worlds) → season → snapshots → views (spotlight, duels, who-guards-whom, multi, averages, worlds, lab) |
| `scripts/serve.py`, `scripts/export_musnba.py`, `scripts/nightly_musnba.py` | Local server; static shell + bundle (`phone_record`: stripped back, D36); iCloud export |
| `scripts/webapp/` | The app; `spotlight.mjs` (headliner, breakout, leaders), `outcomes.mjs` (worlds, conditions, grouped variables), `scenario.mjs` (Scenarios, game flow, duels, Given…, drivers), `league.mjs` (standings tabs, pickers, sorting) |
| `scripts/smoke.py`, `analysis/*.mjs` | Accounting/model checks (fault run must fail); browser checks (`--only`; cases incl. game-proj, game-duels, standings-wins) |

## Commands

```sh
git status && git log --oneline -5                                    # start of session; commit + push at checkpoints
.venv/bin/python scripts/smoke.py [--fault]                           # all checks (the fault run must fail)
.venv/bin/python scripts/nightly.py [--offline] [--no-rebuild] [--engine 10000] [--ahead N]
.venv/bin/python scripts/serve.py --port 8767                         # your own review server (owner uses :8766)
node analysis/browser_check.mjs --base http://127.0.0.1:8767 [--only a,b]
.venv/bin/python scripts/fetch_nbastats.py --recent | --logs | --matchups | --ptdefend | --pbp | --hustle
.venv/bin/python scripts/nbastats.py --crosswalk --reconcile --matchups
.venv/bin/python scripts/realmatch.py --history; .venv/bin/python scripts/realmatch.py --fit [--save --set +pair_history]
.venv/bin/python scripts/features.py --out data/derived/variants/realmatch/features --defence --defence-k-scale 0.2 --matchup models/matchup_2025-12-31.json --shot-types --real-matchups data/derived/nbastats/matchups.parquet
.venv/bin/python scripts/nodes.py --features <variant>/pregame.parquet
.venv/bin/python scripts/train.py --config models/v1.3.json [--folds F4 | --final]
```

Rebuild order after new data or a parser change: history → possessions → rotations → features (default, then the
variant) → nodes → train (the nightly does the current-season part itself). The laptop: 14 cores, 48 GB; a chain build ~20 GB.
