# App — shipped behaviour

As of **20 November 2026**. Proposals and progress live in [PLAN.md](PLAN.md).

## Navigation

| Area | Behaviour |
|---|---|
| Today | One ET slate date: previous/next game day (skipping empty days), date input, Today. One card per game: logos, records before the game, win % per side, projected points (italic) or final score, win bar, total / median margin / OT chance. Finals show the pre-game favourite and ✓/✗, projected v actual total. Tap opens Game Centre |
| Game Centre | **Bezel**: Team A (PTS, WIN, 10–90%) · centre (period, status, TOTAL, SPREAD = projected margin, 10–90% total, OT or tie chance) · Team B; finals show the period's actual points, W/L/T with pre-game win %, actual total/spread with projections. Below: grouped **period** dropdown (Quarters Q1–Q4, Halves H1/H2, Game FG) driving everything, **Player / Team** segments, separate **Matchup**. Routes `#/game/<id>/<period>[/team]`, `#/game/<id>/matchup`; changes replace history |
| Player view | Per-period box score, away then home: MIN (MM:SS), PTS, REB, AST, STL, BLK, FG, 3P, FT as made-attempted (pct). Starters, bench, team projected (and actual) totals; players out in every simulation listed once. Finals: Projected / Actual / Actual vs projected (default; green/red outside the period's 10th–90th percentile). Actual periods come from play-by-play |
| Team view | Per-period team box (PTS, win, REB, AST, STL, BLK, TOV, FG/3P/FT) projected and actual, linescore for finals, then team points ×2, total and margin distributions with editable lines (tap a bar), over/under/push and N+ ladders; actual value and percentile for finals |
| Matchup | Season-to-date team comparison (records, ratings with ranks, four factors, quarter scoring) as of the projection's cutoff |
| Player sheet | `#/game/<id>/player/<pid>/<period>`: period selector; tiles (MIN MM:SS, PTS, REB, AST, FG, plays %, double-double in FG); stat picker (16 stats in FG, 8 per period) with histogram, line, ladder, actual and percentile; season per-period splits (selected period highlighted) and points by game |
| Standings | East / West / League × Forecast / Seeds / Ratings. Forecast: current record, GB, L10, streak, net, projected W–L, Top 6, Play-in, Out, #1 seed (League: best/worst record). Seeds: 1–15 heat matrix, Exactly / At least, ordered by average seed. Ratings: ORtg/DRtg/Net/Pace/four factors with ranks. Phones hide GB/L10/Strk/Net |
| Teams | Directory by conference and division; team page with ratings and ranks, forecast tiles, simulated final-wins histogram, roster (season per-game), schedule (results; win % from game sims or the season sim's team estimate) |
| Players | Sortable table: Per game / Totals / Per 36, search, team filter, minimum games; player page with season tiles + last 5, next game with projection, by-quarter per-game splits (play-by-play), points-by-game chart, game log |
| Search | `/` or Search: teams and players, diacritic-insensitive; Enter opens the first result |
| Model & data | Closed panel: model label, sims, data coverage, snapshot list (pre-game v retrospective) |

## Conventions

- Slates are US Eastern dates; tip-offs show UK time (weekday when it differs) with ET.
- Periods: quarters and halves are regulation only; FG includes overtime. Spread = projected mean margin
  (so team points, total and spread add up); lines use the full distributions.
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

Every projection shows which model made it: **Engine v1.1** (green chip; today's and tomorrow's slates by default, D24)
or **Placeholder model** (retrospective backfills, or a nightly run with `--placeholder`). Tomorrow's slate is projected a
day ahead from what is known today and rebuilt the next night; the app's as-of date (standings, rosters, schedules)
stays the newest snapshot dated today or earlier. The full label — with the engine's known
gaps — is the chip's tooltip and appears in the Model & data panel. `modelPill` in `scripts/webapp/ui.mjs` is the
single place this is decided.
