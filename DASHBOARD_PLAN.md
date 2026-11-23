# Dashboard — current behaviour and product contract

Updated **23 November 2026**. U1–U22 are delivered. [HANDOFF](HANDOFF_NEXT.md) owns current shell/bundle IDs,
checks and delivery; [PLAN §9b](PLAN.md#9b-product-backlog) owns backlog. Full previous release notes:
[frozen dashboard record](docs/archive/2026-11-23-before-lean/DASHBOARD_PLAN.md).

## Current boundaries

- Laptop PWA is primary and imports full saved worlds; phone imports distributions without world-dependent tools.
  Both browse offline after manual import. Pages carries only the data-free shell. An app update and data import
  are separate; iCloud export is not proof of device import.
- Today's games use possession projections. Tomorrow onward has team-pathway home/away/total/margin regulation
  distributions, with a separately resolved winner for ties, no simulated OT points and no player projections.
  Future cards come in three, with total/margin switching in the third.
- **Full lineup branches/Expected mixture are not shipped.** Today's availability panel can link an eligible
  uncertain player to positive-/zero-minute slices of saved worlds. These are observational participation
  conditions, not a forced-lineup forecast or causal effect. Phone explains the absence of saved worlds.
- Schema-1 snapshots preserve original float64 period minutes. Laptop sheets/Given/Joint use exact world values;
  phone sheets use independently sorted marginals without world identity. Display rounds to seconds; conditions
  use stored precision. Old rounded snapshots are labelled and cannot recover lost values.
- Actual/simulated, model, origin/report cutoff and pre-tip/after-tip/retrospective/unverified timing stay explicit.
  Saved per-game forecast time differs from snapshot refresh time. Unverified/after-tip forecasts are excluded
  from verified pre-game accuracy. Browsing never fetches, fits, simulates or reconstructs missing history.

## Navigation and shipped features

| Area | Behaviour |
|---|---|
| Today | Game cards first; expandable slate insights: headliner, breakout, six stat leaders, closest/highest-scoring/OT games, duel of the night when worlds exist. Cards show team/player forecasts or labelled actual-versus-stored projections. |
| Game Centre | Shared period selector (Q1–Q4/H1/H2/FG), Player/Team/Matchup. Bezel shows points/win/total/projected margin, ranges and timing/model. Player boxes precede insights; availability/bench are collapsible. Finals have Actual/Projected/comparison modes. |
| Player box/sheet | Period minutes, counting/shooting stats, deltas versus season; MIN/PTS/REB/AST/shooting/chance distributions and editable thresholds. Given/Joint and comparisons precede expandable advanced panels. Player/stat changes preserve expanded panels. |
| Team view | Team box, distributions/lines and 15 expandable metrics; box-estimated possessions/ratings disclose omissions. With worlds: result drivers, teammate correlations, big/quiet nights and participation-conditioned changes. |
| Scenarios | Saved-world conditions on players, teams and game/period flow; Given/intersections, independence lift, joint grids, duels and conditional boxes. Conditions are shareable routes. Small/empty selections warn. “Plays” means positive simulated minutes, not available. |
| Matchup | Cutoff-date team comparison; real who-guards-whom shares/outcomes in earlier meetings, and this game once final. Player sheets show real opponent-matchup history. |
| Standings | Forecast/Seeds/Wins/Ratings, current/projected split, sortable fields, win/seed pickers, heat tables; Playoff picture/Races/Movers/Leaders live inside Standings. Marginal seeds/illustrative paths are not simulated playoff winners. |
| Teams | Ratings/forecast, win distribution, schedule/results, roster role/minute groups; secondary bench/fringe/out groups collapse. |
| Players | Sortable/searchable per-game/total/per-36 table first, team/minute-share filters, expandable trends. Player pages put next available forecast first, logs/opponent/advanced detail expandable. |
| About/Lab | Dynamic model guide; Lab reflects stored evaluation and verified timing. Lab polish has lower priority than player/game insight. |

Routes are hash-based: `#/game/<id>/<period>[/team]`, `#/game/<id>/matchup`,
`#/game/<id>/player/<pid>/<period>`, `#/game/<id>/scenario[/<conditions>]`,
`#/standings/<forecast|seeds|wins|ratings>`. Old `/season` links redirect into Standings.

## Definitions and presentation

- Slates are ET dates; tip-offs display UK with ET. Quarters/halves are regulation, FG includes OT for possession
  games. Spread means projected mean margin, consistent with team-point means/total.
- Over/under lines are x.5; default/tapped bar uses the half below median/value, typed integer moves to half above.
  Over is strictly greater. Probabilities show one decimal in game/player views, whole % in heat cells;
  extreme nonzero values use <0.1%/>99.9%, zero displays “–”.
- Dynamic dates/sample sizes/counts/model versions/thresholds come from loaded data/config. Fixed teaching examples
  are labelled. Comparable cards group by threes on desktop, two at half width, one on phone. Both themes and
  1440/960/390 screenshots must be inspected on touched pages; 44px touch targets and grouped controls remain.
- Player season filters use 10/25/50% of 48 × the most games played by any team at that cutoff, default 10%.
  This is a season-minute share benchmark, not roster eligibility; OT/trades can exceed 100%.
- Shooting percentages condition on at least one attempt and separately show no-attempt mass. Tile ratio of
  mean makes/attempts differs from mean simulated game percentage. Undefined advanced-rate denominators stay
  undefined; old periods lacking saved inputs are unavailable. Six advanced player rates are eFG%, TS%, 2P%,
  3PA/FGA, FTA/FGA, AST/TOV. Action share is a dated model input, not conventional possession USG%.
- Availability assumptions remain uncalibrated: Out 0, Doubtful .15, Questionable .5, Day-to-day .7, Probable .9;
  unknown .6 and recent-inactivity .8 where applicable. An unlisted injury is an assumption, not reported health.
  Distinguish availability from positive minutes. D47 quarter-scaling is not shipped.

## Pending branch and replay UI

One compact team-grouped lineup control should follow selected player/team/sheet/scenario views once A1 qualifies.
Expected is default; “either status” exactly marginalises remaining branch weights. Given/Joint use the same
selected weighted worlds and exact numerator/denominator; zero-mass conditions are unavailable. No branch control
appears without supported stored branches. Avoid retaining incompatible unconditional cards/targets after selection.
Research injection hooks, weighted adapters and private bundles exist; normal routes do not register them.

A3's five saved-world labels and 2-D View Centre follow ENGINE_PLAN D42/D43: real selected worlds, reconciled
events, supported spatial precision, court/score/clock/box/event list and smooth play/pause/speed/seek/step/jumps.
Validate local files without uploading or replacing forecasts; actual-game adapter comes later. Test missing/invalid/
truncated files, deterministic seek, timer cleanup, reduced motion, keyboard use, widths/themes, size and offline use.
No invented player tracking or simulation during playback. Rotation maps belong to B3. History replay stays deferred.

## Delivery contract

`views.py` writes API-ready JSON; `serve.py` reads it. Static `pwa.mjs` serves imported API records from IndexedDB;
service worker caches shell/logos. Imports stage and verify a generation before active-pointer switch. Keep
non-dot export staging and Finder hidden-flag clearing; precache reload avoids stale HTTP-cache shell assets.

Affected output/model changes require refreshed accepted views/bundles and metadata/import/offline checks;
asset changes require data-free shell/cache publication and upgrade checks. Research-only checkpoints leave
production unchanged. Compact phone playback is conditional on measured size/performance. Each development
chunk still ends with a fresh nightly and final integrated delivery; manual device acceptance stays separate.
