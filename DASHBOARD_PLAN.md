# App — shipped behaviour

**Phone v localhost (owner, 20 Nov, D36):** the phone bundle is stripped back — the 10,000-world distributions for the expected lineup only; everything built on the per-world files (Scenarios, Given…, joint grids, team drivers, duels, duel of the night, lineup branches) is localhost-only (`export_musnba.phone_record`).

**U1–U22 complete as of 22 November 2026.** Historical implementation notes: Scenarios, Given…, joint grids, drivers, averages deltas, Lab view, minutes basis and engine v1.3 added in the D29–D30 chunk; game flow, duels, duel of the night and who-guards-whom added in the D32 chunk. A1 S01–S06 are research-only and complete; S07 delivery is pending. No A1 dashboard changes have shipped. Scope/progress live in [PLAN.md](PLAN.md) and HANDOFF.

**A1 S07, in review and not yet shipped:** prospective unknown statuses are visible rather than hidden, with the
uncalibrated fallback labelled in the Game Centre. Status-tag percentages are explicitly uncalibrated availability
assumptions, including unknown statuses and the active-but-recently-inactive fallback; the Availability panel
separately shows the observed share of simulated games played. New prospective outputs retain their own roster and
report, including ruled-out players; older outputs show only saved player statuses and disclose missing coverage
rather than silently borrowing today's report. New reports distinguish reported health status from the existing
available assumption when no injury is listed; the Game Centre says an unlisted injury is not proof of availability.
The updated shared availability display passed 36/36 projection/flow, player sheet, player list/detail and team
checks at desktop/half/phone and both themes; all six projection screenshots and representative other pages were
inspected after wrapping availability tags below player names.
An uncalibrated equal-share cold-roster fallback, when present in a placeholder forecast, is disclosed with its
team and simulated-world count; the production engine's separate cold-player prior is unchanged. The final isolated
shell (`c6977df6e7c00067d19b`) passed 15/15 import/offline checks with the old bundle.
The data-free Pages shell and
iCloud bundle remain unchanged until the S07 delivery checkpoint.
The same unshipped work corrects Tomorrow's shared-origin cutoff. New snapshots record completion after their atomic
write; Game Centre and final-game cards distinguish pre-game, after-tip, retrospective and timing-unverified forecasts,
including old phone bundles without completion metadata. Unverified/after-tip forecasts are excluded from the
pre-game accuracy summary. Today describes a prospective slate without claiming every game was pre-tip.
The isolated timing-aware shell `f79ce8eab3ebe9182d59` imported the existing bundle and passed **16/16** checks,
including honest legacy timing and offline use; this is not a Pages publication or a new phone import.
The unshipped Lab also excludes starter scores without verified pre-tip snapshot completion, including legacy
imported bundles; it discloses the number of unverified slates instead of presenting their accuracy as pre-game.
The prior per-slate and overall scores are retained separately in the next scorer run. Lab passed **6/6**
width/theme checks and all six screenshots were inspected; isolated shell `0d7693ac00bad5eb2e00` imported the
legacy bundle and passed **17/17** import/offline checks, including Lab timing. A new-bundle check remains.

## Navigation

| Area | Behaviour |
|---|---|
| Today | **Spotlight (owner, 20–21 Nov), projected slates (games not yet final):** *Headliner of the night* (the top projected all-round line by NBA's standard fantasy weights PTS + 1.2 REB + 1.5 AST + 3 STL + 3 BLK − TOV) beside *Breakout watch* (the biggest projected rise over his own season average among rotation players with 8+ games, never the headliner) — the headliner card: identity, a points-distribution sparkline (1st–99th percentile, average marked), chances of 30+ and 40+ points, double- and triple-double, then his six projected stats as one fixed row of six (three-by-two on a phone); the breakout card: a season → tonight dumbbell per stat (PTS, REB, AST, 3PM, MIN) with values and Δ, and the *why* (more minutes, or similar minutes at higher rates); then **Games to watch** (closest finish = chance the margin ends within 5, highest-scoring, likeliest overtime — three different games); then the six leaders (PTS, REB, AST, 3PM, STL, BLK) six across (3 at half width, 2 on a phone), each with the leader's **chance to lead the night** and the 2nd/3rd's chances (paired worlds across games: world k of each game is one simulated night). Every name opens his sheet in that game (`views.spotlight`, `views.games_to_watch`, `views.lead_chances`; `spotlight.mjs`). Cards show each side's projected top scorer (points, rebounds, assists; one per line, away above home; surname with suffix, e.g. "Porter Jr.") before tip and the **duel of the night** (20 Nov, D32 chunk): the chance each top scorer outscores the other, and level, from the stored worlds (`views.scorer_duel`). One ET slate date: previous/next game day (skipping empty days), date input, Today. One card per game: logos, records before the game, win % per side, projected points (italic) or final score, win bar, total / median margin / OT chance. Finals show the pre-game favourite and ✓/✗, projected v actual total. Tap opens Game Centre |
| Game Centre | **Spotlight (projected games, FG, Player view):** the same headliner, breakout watch and six leaders over the two teams (chance to lead the game). **Bezel**: Team A (PTS, WIN, 10–90%) · centre (period, status, TOTAL, SPREAD = projected margin, 10–90% total, OT or tie chance) · Team B; finals show the period's actual points, W/L/T with pre-game win %, actual total/spread with projections. Below: grouped **period** dropdown (Quarters Q1–Q4, Halves H1/H2, Game FG) driving everything, **Player / Team** segments, separate **Matchup**. Routes `#/game/<id>/<period>[/team]`, `#/game/<id>/matchup`; changes replace history. **Deltas (owner, 20 Nov):** each team's points carry Δ v its season scoring average for the selected period (FG, quarter or half; projected or actual); no Δ on the win % (owner, 20 Nov: tonight's win % comes from the engine and any baseline from the team ratings — two models that disagree on team strength while the engine compresses it, so both sides could show a positive Δ; revisit once the engine expresses strength) and none on the total. **Box score (projected, FG):** small Δ v season average under MIN, PTS, REB, AST, STL, BLK; shooting as x/y (z%) with its Δ in the same shape (makes/attempts/percentage, each coloured by its own sign) |
| Player view | Per-period box score, away then home (projected FG: small numbers under MIN, PTS, REB, AST = projection minus season average): MIN (MM:SS), PTS, REB, AST, STL, BLK, FG, 3P, FT as made-attempted (pct). Starters, bench, team projected (and actual) totals; players out in every simulation listed once. Finals: Projected / Actual / Actual vs projected (default; green/red outside the period's 10th–90th percentile). Actual periods come from play-by-play |
| Team view (drivers) | Full game, engine worlds: per team **who drives the result** — for the eight most-used players, team win % on his big night (top quarter of his simulated points) and quiet night (bottom quarter), without him (share of worlds he does not play), correlation of his points with the margin; teammates' points correlation matrix (top six scorers); "if X sits" — the teammates who gain minutes and points when a maybe sits |
| Team view | Per-period team box (PTS, win, REB, AST, STL, BLK, TOV, FG/3P/FT) projected and actual, linescore for finals, then team points ×2, total and margin distributions with editable lines (tap a bar), over/under and N+ ladders; actual value and percentile for finals |
| Scenarios (20 Nov) | **Grouping (owner, 20 Nov):** the "what" dropdown is grouped (player: Availability · Scoring · Rebounding · Handling · Defense; team: Result · Points · Periods won · Leads · Flow; game: Totals · Margin & flow · Overtime); quick scenarios and duels sit in labelled rows (Availability · Result · Totals · Game flow · Quarters · Stars; Players · Teams); player variables are makes and main stats (FGM, FTM, OREB/DREB where stored) — no combos or attempts. `#/game/<id>/scenario[/<conditions>]` (engine games with stored worlds): stack conditions as chips — any player (plays, sits, minutes, points, rebounds, assists, threes, PRA, steals, blocks, turnovers, attempts, FG% ≥/≤ N), either team (wins, loses, points, margin, half-time margin, Q1/Q4/2nd-half points) or the game (total, margin either way, overtime); quick scenarios incl. "X sits" for every player who sits in 1–99% of worlds, close game, blowout, shootout, star big/quiet nights. Shows the scenario's chance (worlds matching) and, with two or more conditions, the chance if independent and the correlation lift; team points, win, total, margin, OT under the scenario v all; both box scores (MIN, PTS, REB, AST, 3PM, STL, BLK, TOV, FG%) under the scenario with Δ v all. Conditions live in the route (shareable). **Game flow (20 Nov, D32 chunk; owner idea "Given… quarter outcomes and leads", generalised):** conditions on every quarter and half (points, wins Q1–Q4, wins a half, margin after Q1 / at half-time / after Q3, Q4 margin, leads at each break, quarters won), the flow (wins from behind at half-time, loses after leading at half-time, wire to wire, wins every quarter) and the game (Q1, half and Q4 totals, leader changes at the breaks, half-time leader loses, within 5 after Q3); a **Quarter by quarter · game flow** panel under every scenario (each side's points and period wins, the lead and the chance of leading at every break, comeback/flip/sweep/lead-change tiles, Δ v all); quick scenarios for comebacks, wire to wire, flips, close after Q3, lead changes, Q1 winners. **Duel** (owner idea "player A v player B", generalised): any two numeric outcomes (player, team or game) head to head under the scenario — chance A more / level / B more (v all), the distribution of A − B, each team's win chance when A wins the duel; quick duels for the top scorers, rebounders, passers, three-point shooters, Q1 and second-half points |
| Matchup | Season-to-date team comparison (records, ratings with ranks, four factors, quarter scoring) as of the projection's cutoff. **Who guards whom (20 Nov, D32):** real NBA matchups — for each attacker, his three main defenders among tonight's opponents in earlier meetings (games before the date only, last 365 days, players' meetings on any team): share of his partial possessions against these players, his points, FG and threes while guarded, meetings; once final, also **this game's** real matchups (`views.duels`, from `data/derived/nbastats/matchups.parquet`) |
| Player sheet | `#/game/<id>/player/<pid>/<period>`: period selector; tiles (MIN MM:SS, PTS, REB, AST, FG, plays %, double-double in FG); **Given…** (full game, engine worlds): one condition on anyone in the game redraws the selected stat as bars over the all-simulations outline, with mean, median, 10–90% and over the current line given v all; **joint outcomes**: the selected stat against any other numeric outcome (his own, another player's, a team's, the game's) as a heat grid of shares with the mean per band and the correlation; **Tonight v his averages** (projected v season and last-10, games played, as of the cutoff); **minutes basis** (engine v1.2+, D29): healthy role, share of available games played (when below 95%), target if the listed roster plays, return ramp after missed games, projected starter; stat picker (16 stats in FG, 8 per period) with histogram, line, ladder, actual and percentile; season per-period splits (selected period highlighted) and points by game; **20 Nov (owner): tiles** Minutes · Points · Rebounds · Assists · **Shooting** (FG, 3P, FT stacked) · **Chances** (plays, double-, triple-double, quadruple/quintuple-double when above 0.1%, 5×5 — any of points, rebounds, assists, steals, blocks; counted in the stored worlds); **stat picker grouped** Scoring (PTS, FGM, 3PM, FTM) · Rebounding (ALL, OFF, DEF) · Handling (AST, TOV) · Defense (STL, BLK) · Time (MIN) — on a phone, groups share rows by size — makes and main stats only (no combos or attempts), a stat shown once its distribution is stored (OREB/DREB from the nightly after 20 Nov; FGM/FTM backfilled from the worlds); **head-to-head (20 Nov, D32)**: who guarded him in earlier meetings with tonight's opponents (and in this game once final) and whom he guards — real NBA matchups, share of partial possessions and the attacker's line while guarded; Given… accepts the game-flow conditions (quarters, leads, comebacks) |
| Standings | East / West / League × Forecast / Seeds / Ratings. Forecast: current record, GB, L10, streak, net, projected W–L, Top 6, Play-in, Out, #1 seed (League: best/worst record). Seeds: 1–15 heat matrix, Exactly / At least, ordered by average seed. Ratings: ORtg/DRtg/Net/Pace/four factors with ranks. Phones hide GB/L10/Strk/Net | **20 Nov (owner):** a **Wins** tab in the Seeds format (`#/standings/wins`): columns in 5-win bands from high to low (top band open, bottom band everything below), Exactly = the band, At least = that many or more, ordered by average wins; the **Forecast** table also has grouped pickers — *Final wins* (at least / exactly N) and *Seed* (N or better / exactly N, conferences only) — each adding a column (remembered per viewer). Tabs are linkable (`#/standings/<forecast|seeds|wins|ratings>`). **Forecast table (owner, 20 Nov):** current group (W, L, W%, GB, L10, Strk, Net) and projected group (Proj W, Proj L, the pickers' columns, Top 6 / Play-in / Out / #1 seed or Best / Worst record) split by a dotted line; every numeric column sortable (first click natural direction, second reverses, third back to standings order; # stays the standing; seed lines only in standings order).
| Teams | Directory by conference and division; team page with ratings and ranks, forecast tiles, simulated final-wins histogram, roster (season per-game), schedule (results; win % from game sims or the season sim's team estimate) |
| Players | Sortable table: Per game / Totals / Per 36, search, team filter, minimum games; player page with season tiles + last 5, next game with projection, by-quarter per-game splits (play-by-play), points-by-game chart, game log |
| Search | `/` or Search: teams and players, diacritic-insensitive; Enter opens the first result |
| Lab (20 Nov) | `#/lab` — **Forecast Lab**: the engines' trust tests as logged. Players first (D28): per backtest run and tier (stars, starters, bench) minutes and points real v simulated, bias (green within ±2%), 10–90% coverage (green within 75–85%), rebound/assist bias, points CRPS; then team strength (defence and offence loading v real games, margin slope, margin/total CRPS and win log loss v the team-rating model on the same games, total bias and coverage); the nightly projected-v-actual starters record; the minutes allocator check. Phones hide secondary columns. Built by `views.lab()` from `analysis/experiments` and `data/derived/lineups` (serving never computes) |
| Model & data | Closed panel: model label, sims, data coverage, snapshot list (pre-game v retrospective) |

## Conventions

- **Owner, 22 Nov:** changing facts in dashboard copy (dates, games played, simulation counts, model versions, sample thresholds) are derived from loaded data/configuration. Stable definitions can be fixed text; model assumptions come from retained season notes.

- **Owner, 22 Nov:** comparable card groups come in multiples of three, filling three-across desktop rows; adapt to two at half width and one on phones. Season insights live inside Standings (no separate main-nav Season tab).

- Slates are US Eastern dates; tip-offs show UK time (weekday when it differs) with ET.
- Periods: quarters and halves are regulation only; FG includes overtime. Spread = projected mean margin
  (so team points, total and spread add up); lines use the full distributions.
- **Over/under lines are always x.5** (owner, 20 Nov) — team points, totals, margins and every player prop: the default
  is the x.5 below the median, tapping a bar sets the x.5 below it, a typed integer moves to the x.5 above (the same
  "over" chance), so there are no pushes (`halfLine` in `ui.mjs`). Everything else about how figures are shown stays.
- Probabilities: one decimal in the game and player views, whole percent in heat cells; `<0.1%`/`>99.9%`
  at the extremes; zero shows as "–". Over means strictly more than the line.
- Pre-game snapshot = generated before tip-off with recorded origin/report provenance. Current retrospective
  backfills use the placeholder and have no historic injury news; always labelled. Planned A1 S13 engine
  reconstructions retain their version, origin, report coverage and retrospective kind, even if dated reports exist.
- Availability per simulation: Out 0, Doubtful 0.15, Questionable 0.5, Day-To-Day 0.7, Probable 0.9.
  Distributions include simulations where a player sits.
- Theme: automatic, dark or light (toggle; per device). Logos switch to dark variants on dark themes.

## Architecture

`views.py` writes API-ready JSON; `serve.py` serves it read-only. The PWA bundle retains distribution views and logos;
`phone_record` removes world files and their dependent flags/duels (D36). Routes are hash-based for static hosting.
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

## Upgrade programme (owner, 21 Nov — "one top shop for NBA insights")

Run item by item; each item ends with browser checks at 1440/960/390 (both themes) on the touched pages, its status here
(✅ + one line), and a commit + push — so the docs and repo are never more than one item behind. Items are of similar size;
everything is read from stored snapshots, worlds, finals and derived tables (serving never computes; `views.py` aggregates).

| # | Item | Low-level parts | Status |
|---|---|---|---|
| U1 | **Today: slate header strip** | slate tiles (games, projected points per game, closest margin, first/last tip) · tip-time timeline (each game placed on a UK clock axis) · phone stacking | ✅ tiles + UK tip timeline (stacked markers), 2-up tiles on phones (`today.slateStrip`) |
| U2 | **Today: game card upgrades** | favourite margin pill · injury/maybe count per side (from projection statuses) · "closest game" badge · quick links (Scenarios, Matchup) · layout check | ✅ report line per card (maybes as simulated, names on hover; ruled-out players are not in the sims) + Closest badge; quick links dropped (cards are one link) |
| U3 | **Today: role change badges** | players gaining/losing ≥ 4 projected minutes v season (views) · why (teammate out / return ramp from minutes basis) · strip of badges per slate · link to sheet | ✅ Role changes tonight strip (top 5 risers + 5 fallers, ≥ 4 min v season) with the minutes model's reason (availability, rotation share, return ramp, short-handed, healthy role) |
| U4 | **Results review for finished slates ("How we did")** | per finished slate: favourites' record, Brier and log loss of win %, total/margin errors · biggest player surprises (actual v projection, percentile) · card on Today for past dates | ✅ How the projections did on finished slates (pre-game projections only): favourites, Brier/log loss, total/margin error, players inside 10–90%, biggest overs/unders by percentile (`views.slate_review`) |
| U5 | **Game Centre: lead-by-quarter fan chart** | from team-period worlds: median home lead after Q1/H/Q3/final with 25–75 and 10–90 bands (views) · SVG fan · in Team view | ✅ Game flow panel (Team view): home lead at Q1/half/Q3/final — median, 25–75 and 10–90 bands, chance of leading (`views.lead_fan` from stored worlds) |
| U6 | **Game Centre: quarter score chart** | each side's projected points per quarter with 10–90 whiskers · actual overlay for finals · in Team view above distributions | ✅ points per quarter per side: mean bars, 10–90 whiskers, actual dots on finals (same panel) |
| U7 | **Game Centre: availability panel** | who is out / questionable / probable per side with projected minutes and the minutes shift to teammates · "if X sits" summary · in Player view | ✅ Availability panel (Player view, FG, pre-tip): report status + comment, chance he plays in the sims, minutes if he plays, season minutes, expected return (`views.availability`) |
| U8 | **Matchup view: four-factor bars** | paired bars per factor (offence v the other side's defence) with league-average markers · ranks · replaces the plain table's top half on wide screens | ✅ Four factors · matchup (Matchup view): per direction (attack v defence) a dot plot per factor — attack rate, defence allowed, league line — with the edge |
| U9 | **Player page: header and trend chart** | season tiles · game-log chart (points with 5-game rolling line, rebounds/assists toggles) · last 10 v season deltas | ✅ player page: L10 v season Δ in the tiles; trend chart (last 30 team games: bars, 5-game rolling line, season average, DNP gaps) with a PTS/REB/AST/3PM/MIN toggle; next-game card without PRA |
| U10 | **Player page: shot profile** | zone mix and FG% by zone v league (from the latest profile) on a half-court diagram · three-point rate and FT rate · labelled as pre-game profile | ✅ Shot profile on a half court (zones as the engine's): share of shots and FG% by zone shaded v the league, table v league, assisted share and FT% (`views.shot_profile_table` from latest profiles) |
| U11 | **Player page: defensive profile (real matchups)** | whom he guards most (attackers, partial possessions) · points allowed per partial possession v those attackers' own rate · three-point attempt share allowed (deterrence) · labelled with seasons | ✅ Defence · real matchups (player page, last 365 days): points allowed per 100 partial possessions v the same attackers elsewhere, edge, three-point share allowed v their normal, FG% allowed, whom he guards most (`views.defence_profiles`) |
| U12 | **Player page: v tonight's opponent** | his past games v the next opponent (box lines, averages) · real matchups v that team's players · next-game projection card | ✅ Next-game card: his history v that opponent since 2022-23 (averages v overall, recent meetings) and their current players who guarded him most (`views.opponent_history`) |
| U13 | **Players tab: trending and leaders** | last-10 v season deltas column · per-36 toggle check · top risers/fallers strip · sparkline of last 10 points | ✅ Players tab: sortable L10 trend column (sparkline of last-10 points + Δ v season), heating up / cooling off strip (8+ games, 15+ min) (`views.trend_fields`) |
| U14 | **Team page: ratings trend and schedule strip** | net rating (rolling 10) chart from team games · upcoming schedule with projected win % (season sim's team estimate) · rest/back-to-back markers | ✅ Team page form panel: margin by game (W/L bars, 5-game rolling line) and the next ten games with win chance heat and back-to-back markers |
| U15 | **Team page: roster minutes and roles** | minutes share bars (season) · projected minutes tonight · starters v bench · injury status chips | ✅ Roster grouped into projected starters, bench, rotation fringe and reported out; season minute bars against next-game projections, minute deltas and injury details. Six size/theme cases passed; desktop/phone screenshots inspected. |
| U16 | **Standings: playoff picture** | most likely seeds 1–10 per conference with probabilities · projected first-round pairings (modal seeds) · play-in bracket view | ✅ Playoff picture tab: seed 1–10 favourites and alternatives, a unique-team illustrative first-round field and play-in paths; marginal probabilities explicitly distinguished from pairing odds. Six responsive/theme checks passed and screenshots inspected. |
| U17 | **Standings: wins distributions per team** | mini histogram per row in the Wins tab (10k seasons) · median and 10–90 · sort by spread | ✅ Wins tab adds per-team mini histograms on a shared axis derived from scheduled games, median and 10–90% ranges, and widest-range sorting. Six responsive/theme checks passed; screenshots reviewed. |
| U18 | **Standings insights: races** | conference race chart (projected wins with 10–90 bands, sorted) · tank race (worst-record and bottom-3 chances) · #1 seed race | ✅ Standings Races (merged at owner request, 22 Nov): conference/league win-range race, #1 seed races and worst-record race. Bottom-three record counts added to the season simulation (no changes to draws); populated by close-out nightly. Six browser cases passed, screenshots reviewed; Season included in PWA caches/export. |
| U19 | **Season tab: movers since the last snapshot** | change in projected wins and playoff odds v the previous snapshot's season · biggest risers/fallers with the results that moved them | ✅ Movers compares distinct season cutoffs (30 teams; 20→21 Nov, nine results), projected-win and Top 6/play-in/#1 changes, risers/fallers and linked interval results. Races/Movers/Leaders merged under Standings per owner; /season redirects. Six Movers cases and twelve merged-navigation cases passed; screenshots inspected. |
| U20 | **Season tab: season leaders to date** | per-game leaders (PTS, REB, AST, 3PM, STL, BLK, FG%) with minimum games · team leaders | ✅ Standings Leaders: nine player leaderboards (PTS/REB/AST/3PM/STL/BLK/FG%/3P%/FT%) and six team leaderboards (offence/defence/net/pace/scoring/rebounding). Explicit minimum-games and shooting-attempt filters; current data qualifies at 12 GP. Distinct from forecast Races; six size/theme checks passed and screenshots reviewed. |
| U21 | **About the model page (new)** | plain-language explainer of the two engines (play-by-play, team pathway), what 10,000 worlds means, how to read ranges, decision log highlights, data sources and freshness · linked from the model chip | ✅ About the model guide: two engines, 10k worlds, ranges and probability changes, cutoff safety, decision highlights, known limitations, sources and live retained-data freshness. Linked from engine/season chips and Model & data; PWA included. Six size/theme checks passed and screenshots reviewed. |
| U22 | **Global polish** | season insights merged under Standings · grouped controls · loading/empty states · dynamic copy · responsive card grids · full sweep | ✅ grouped Standings/Season insights controls; 9 player + 6 team leader cards; data-driven counts, thresholds and chart scales; explicit loading/missing-projection states; rounded-zero formatting; PWA module inventory fixed (including Spotlight). Full sweep 130/130 + 30 additional targeted checks; PWA import/offline/dynamic-data checks 14/14. Personal Pages/iCloud setup follows MusSim (owner, 22 Nov). |

## Completion details — U15–U22 (22 Nov 2026)

- **Team roster:** next projected game date/opponent and simulation count, season → projected minute values/bars,
  projected starters, bench, rotation fringe, reported out and explicit missing-projection groups. No projection falls
  back to season start share; injury descriptions and expected return dates remain sourced from the report.
- **Standings:** Forecast · Seeds · Wins · Ratings · Playoff picture, grouped beside Season insights: Races · Movers · Leaders.
  Legacy `#/season` links redirect to `#/standings/races`; main navigation remains five destinations.
- **Playoff picture:** seeds 1–10 marginal favourites/alternatives, plus a unique-team illustrative field (assignment
  maximises the sum of marginal seed chances). Regular-season seeds 7/8 are provisional playoff opponents pending the
  play-in; no joint pairing probability or postseason simulation is claimed.
- **Wins/Races:** row histograms with median and 10–90% range, widest-range sorting; race chart with mean, middle 50%
  and 80% bands, conference/league filters, #1 races, worst-record/bottom-three chances. The common win scale comes
  from scheduled games. Bottom-three counts are additive season summaries and preserve all existing simulation draws.
- **Movers:** compare earlier distinct season cutoffs using the same season model (tomorrow's duplicate is skipped).
  Every team's wins/Top 6/play-in/#1 changes, risers/fallers and linked results in the interval. Changes are not labelled
  as the causal contribution of individual games; missing comparisons have a clear empty state.
- **Leaders:** nine player cards (PTS, REB, AST, 3PM, STL, BLK, FG%, 3P%, FT%) and six team cards (offence, defence, net,
  pace, scoring, rebounding). Dashboard qualifiers: 70% of maximum team games played, rounded up; shooting attempts
  per game 5/3/2 respectively. Values and explanatory text use the same settings. These are not official NBA qualifiers.
- **About:** `#/about`, linked from model chips and Model & data. Two engines, interpreting probabilities/ranges,
  promotion principles, data freshness and sources. Changing numbers come from metadata; forecast assumptions from
  retained season notes. Layout uses existing theme tokens, 1440/960/390 checks and offline module caching.
- **PWA:** data-free static shell, retained-data import with checksum validation and previous-generation preservation;
  successful nightly exports via `nightly_musnba.py` to iCloud Drive/MusNBA. Owner approved public source + personal
  GitHub Pages on 22 Nov, following MusSim. No simulation data enters the public repo or shell.

**Final checkpoint (22 Nov):** refreshed 13 games × 10,000 worlds + 10,000 seasons; smoke 102/102, fault run detects
22 injected failures, browser 156/156 plus 12/12 final phone-layout cases, live PWA 15/15. Team form/fixtures stack on a
phone (geometry asserted, screenshots inspected). Personal Pages live at https://musamoholo.github.io/MusNBA/; source
public by explicit owner approval. iCloud delivery confirmed on the phone. Exporter uses non-dot staging names and
clears Finder's hidden flag before/after rename; the first hidden export was repaired and the regression is checked.

## Next accuracy chunk: planned app/PWA work, not shipped

U1–U22 stay complete. A1 S08 adds local explicit lineup branches with coherent Expected output; S12 adds stored
rotation maps and sampled-world event playback. Keep existing U3 role badges, U11 defence profiles and merged
Standings navigation; don't create duplicate pages. Card groups remain multiples of three and changing text is dynamic.

A1 S13 preserves each day's Today forecast and labels Tomorrow previews. With a new accepted model, the owner
expects a season-start→now rebuild and one consistent **active-version history** in Today/results, Game Centre,
Movers and review metrics. Preserve previous versions and original live forecasts in archives. Historical rebuilds
are labelled retrospective, with the original generation time/input cutoff/coverage available; never present them
as forecasts actually issued then. Actuals join stored predictions; browsing never fits or simulates. Model-version
switches must not silently splice incompatible histories or count Tomorrow's copied season twice.

**PWA delivery is part of every affected subtask, not just S14** (owner, 22 Nov). Promoted model or output changes
require refreshed accepted forecasts/views and a new iCloud bundle; asset changes require a rebuilt/published
data-free shell and cache update. Verify model/cutoff/world metadata, fresh import, older-bundle handling, offline
routes, and the phone's Expected-only contract. Keep large world files/branches local; compact replay summaries
may ship only after measuring bundle cost. Report delivery and the need to import on each device separately from
actual owner phone acceptance. Research-only checkpoints leave the served bundle unchanged and say so in docs.
S14 finishes with a new nightly, integrated browser/PWA checks and the successor chunk documented at 0%.
