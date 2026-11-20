# App — shipped behaviour

As of **20 November 2026** (Scenarios, Given…, joint grids, drivers, averages deltas, Lab view, minutes basis and engine v1.3 added in the D29–D30 chunk). Proposals and progress live in [PLAN.md](PLAN.md).

## Navigation

| Area | Behaviour |
|---|---|
| Today | Cards show each side's projected top scorer (points, rebounds, assists) before tip. One ET slate date: previous/next game day (skipping empty days), date input, Today. One card per game: logos, records before the game, win % per side, projected points (italic) or final score, win bar, total / median margin / OT chance. Finals show the pre-game favourite and ✓/✗, projected v actual total. Tap opens Game Centre |
| Game Centre | **Bezel**: Team A (PTS, WIN, 10–90%) · centre (period, status, TOTAL, SPREAD = projected margin, 10–90% total, OT or tie chance) · Team B; finals show the period's actual points, W/L/T with pre-game win %, actual total/spread with projections. Below: grouped **period** dropdown (Quarters Q1–Q4, Halves H1/H2, Game FG) driving everything, **Player / Team** segments, separate **Matchup**. Routes `#/game/<id>/<period>[/team]`, `#/game/<id>/matchup`; changes replace history |
| Player view | Per-period box score, away then home (projected FG: small numbers under MIN, PTS, REB, AST = projection minus season average): MIN (MM:SS), PTS, REB, AST, STL, BLK, FG, 3P, FT as made-attempted (pct). Starters, bench, team projected (and actual) totals; players out in every simulation listed once. Finals: Projected / Actual / Actual vs projected (default; green/red outside the period's 10th–90th percentile). Actual periods come from play-by-play |
| Team view (drivers) | Full game, engine worlds: per team **who drives the result** — for the eight most-used players, team win % on his big night (top quarter of his simulated points) and quiet night (bottom quarter), without him (share of worlds he does not play), correlation of his points with the margin; teammates' points correlation matrix (top six scorers); "if X sits" — the teammates who gain minutes and points when a maybe sits |
| Team view | Per-period team box (PTS, win, REB, AST, STL, BLK, TOV, FG/3P/FT) projected and actual, linescore for finals, then team points ×2, total and margin distributions with editable lines (tap a bar), over/under and N+ ladders; actual value and percentile for finals |
| Scenarios (20 Nov) | `#/game/<id>/scenario[/<conditions>]` (engine games with stored worlds): stack conditions as chips — any player (plays, sits, minutes, points, rebounds, assists, threes, PRA, steals, blocks, turnovers, attempts, FG% ≥/≤ N), either team (wins, loses, points, margin, half-time margin, Q1/Q4/2nd-half points) or the game (total, margin either way, overtime); quick scenarios incl. "X sits" for every player who sits in 1–99% of worlds, close game, blowout, shootout, star big/quiet nights. Shows the scenario's chance (worlds matching) and, with two or more conditions, the chance if independent and the correlation lift; team points, win, total, margin, OT under the scenario v all; both box scores (MIN, PTS, REB, AST, 3PM, STL, BLK, TOV, FG%) under the scenario with Δ v all. Conditions live in the route (shareable) |
| Matchup | Season-to-date team comparison (records, ratings with ranks, four factors, quarter scoring) as of the projection's cutoff |
| Player sheet | `#/game/<id>/player/<pid>/<period>`: period selector; tiles (MIN MM:SS, PTS, REB, AST, FG, plays %, double-double in FG); **Given…** (full game, engine worlds): one condition on anyone in the game redraws the selected stat as bars over the all-simulations outline, with mean, median, 10–90% and over the current line given v all; **joint outcomes**: the selected stat against any other numeric outcome (his own, another player's, a team's, the game's) as a heat grid of shares with the mean per band and the correlation; **Tonight v his averages** (projected v season and last-10, games played, as of the cutoff); **minutes basis** (engine v1.2+, D29): healthy role, share of available games played (when below 95%), target if the listed roster plays, return ramp after missed games, projected starter; stat picker (16 stats in FG, 8 per period) with histogram, line, ladder, actual and percentile; season per-period splits (selected period highlighted) and points by game |
| Standings | East / West / League × Forecast / Seeds / Ratings. Forecast: current record, GB, L10, streak, net, projected W–L, Top 6, Play-in, Out, #1 seed (League: best/worst record). Seeds: 1–15 heat matrix, Exactly / At least, ordered by average seed. Ratings: ORtg/DRtg/Net/Pace/four factors with ranks. Phones hide GB/L10/Strk/Net |
| Teams | Directory by conference and division; team page with ratings and ranks, forecast tiles, simulated final-wins histogram, roster (season per-game), schedule (results; win % from game sims or the season sim's team estimate) |
| Players | Sortable table: Per game / Totals / Per 36, search, team filter, minimum games; player page with season tiles + last 5, next game with projection, by-quarter per-game splits (play-by-play), points-by-game chart, game log |
| Search | `/` or Search: teams and players, diacritic-insensitive; Enter opens the first result |
| Lab (20 Nov) | `#/lab` — **Forecast Lab**: the engines' trust tests as logged. Players first (D28): per backtest run and tier (stars, starters, bench) minutes and points real v simulated, bias (green within ±2%), 10–90% coverage (green within 75–85%), rebound/assist bias, points CRPS; then team strength (defence and offence loading v real games, margin slope, margin/total CRPS and win log loss v the team-rating model on the same games, total bias and coverage); the nightly projected-v-actual starters record; the minutes allocator check. Phones hide secondary columns. Built by `views.lab()` from `analysis/experiments` and `data/derived/lineups` (serving never computes) |
| Model & data | Closed panel: model label, sims, data coverage, snapshot list (pre-game v retrospective) |

## Conventions

- Slates are US Eastern dates; tip-offs show UK time (weekday when it differs) with ET.
- Periods: quarters and halves are regulation only; FG includes overtime. Spread = projected mean margin
  (so team points, total and spread add up); lines use the full distributions.
- **Over/under lines are always x.5** (owner, 20 Nov) — team points, totals, margins and every player prop: the default
  is the x.5 below the median, tapping a bar sets the x.5 below it, a typed integer moves to the x.5 above (the same
  "over" chance), so there are no pushes (`halfLine` in `ui.mjs`). Everything else about how figures are shown stays.
- Probabilities: one decimal in the game and player views, whole percent in heat cells; `<0.1%`/`>99.9%`
  at the extremes; zero shows as "–". Over means strictly more than the line.
- Pre-game snapshot = built before tip-off with that day's injury report. Retrospective = rebuilt from box
  scores before that date without injury news; always labelled.
- Availability per simulation: Out 0, Doubtful 0.15, Questionable 0.5, Day-To-Day 0.7, Probable 0.9.
  Distributions include simulations where a player sits.
- Theme: automatic, dark or light (toggle; per device). Logos switch to dark variants on dark themes.

## Architecture

`views.py` writes API-ready JSON; `serve.py` serves it read-only; the PWA bundle contains exactly the same
files plus logos, so laptop and phone responses are identical. Routes are hash-based for static hosting.
In static mode `pwa.mjs` answers `/api/*` from IndexedDB and the service worker serves logos and the
cached shell. Imports stage a new generation and switch one active pointer after verification.

## Model chip (19 Nov 2026, D22–D24)

Every projection shows which model made it: **Engine v1.3** (green chip, since 20 Nov — D30 defence inputs and D29 minutes; Engine v1.1/v1.2 on older snapshots; today's and tomorrow's slates by default, D24)
or **Placeholder model** (retrospective backfills, or a nightly run with `--placeholder`). Tomorrow's slate is projected a
day ahead from what is known today and rebuilt the next night; the app's as-of date (standings, rosters, schedules)
stays the newest snapshot dated today or earlier. The full label — with the engine's known
gaps — is the chip's tooltip and appears in the Model & data panel. `modelPill` in `scripts/webapp/ui.mjs` is the
single place this is decided.

**Season model (20 Nov, D25/D26).** Standings show which model made the season forecast: **Team pathway v1** (green chip; tooltip = its label) when the season was played by the per-world team pathway — today's and tomorrow's games from the engine's worlds, every later game from each simulated season's own ratings, updated after every game — or **Placeholder model** for older snapshots. The "How the forecast works" note follows the same switch (`seasonPill` in `league.mjs`; `season_model` in `standings/<date>.json`). A long-range game's win % is the share of simulated seasons in which that team won it (D16).
