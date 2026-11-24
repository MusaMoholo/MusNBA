# Model contract and evidence

State/jobs/next commands: [HANDOFF](HANDOFF_NEXT.md). Scope: [PLAN](PLAN.md). App/commands: [README](README.md).
Historical protocols/results remain in Git and the verified [archive](README.md#documentation-history); load only relevant sections.

## Accepted systems

**engine-v1.3-r3**, nodes `models/v1.3.json`, D29 rotations, Rule3 foul-outs, independent per-world rotation fitting,
contextual late timing;10k worlds/explicit branch in deterministic1k chunks. Today uses possessions; tomorrow onward uses
pathway-v1: K8, initial uncertainty.4, gain1, memory cap20. Each path updates its own offence/defence from regulation score surprises.
No learned future injury/rest/travel hazard. Weighted near-term coupling preserves every original atom; paths are not certified iid.
Serving reads saved results only. Release freshness requires new season chunks in an empty namespace; guarded cache reuse alone earns no fresh-generation credit. U25 changes presentation/controls; no forecasting parameters or protected scores change.

Sixteen LightGBM decisions: duration,event,who,what,location,shot-result,assisted,assister,blocked,blocker,turnover-type,
stealer,fouler,free-throw,rebound,rebounder. Candidate-player nodes softmax the current five. Latest10% training supplies
validation/temperature. Player/lineup defence uses role/size soft assignments, individual quality, help and matchup/shot-type history;
no team-strength rating enters possession nodes.

D29 healthy-core role/start/usage and learned return ramp allocate240 regulation minutes/team (+25/OT), with independent target
variation/fitting per world. Availability does not guarantee positive minutes. State-responsive substitutions remain unpromoted.
Rule3 replaces disqualified players and handles exhausted rosters/technical penalties without rejecting worlds.
Periods720s/OT300s. Segments can continue after offensive rebounds/non-shooting fouls. **No explicit24/14-second shot-clock state exists.**

## Inputs, defence and court meaning

For ET origin D, all inputs **and fitted auxiliary parameters** precede D; rebuild prior-game profiles/minutes/rotations/matchups/ratings.
December2025 assignment fits are unsafe for F1–F3. Whole-season priors, undated body data and batch defender fills require causal guards;
missing-profile medians are fitted before origin, never from validation. Backtests require the fold-matched `--clock-recipe`.
Input readiness is outcome-blind: frozen A2 panels have190/190/179 supported games per earlier fold, selecting first100 in fixed order.

Existing `features.matchup_counts` already distributes shot responsibility over likely defenders and builds broad zone histories.
Ranks mean estimated likelihood, **not physical proximity**. Retained ESPN segments have shot coordinates/on-court fives, not every
defender's location at shot release. The top2 research hook is not proof of accepted activation. NBA aggregate matchups are useful
validation/support, not event-level nearest-defender truth. B1 must establish a distinct supported improvement before fitting/testing.
Inferred responsibilities sumone per eligible shot; missing fives/exclusions remain explicit. Never use a validation shot's made/missed
outcome to choose its defender. Separate primary/help roles only where evidence supports them; otherwise retain uncertainty.

Coordinates are feet, basket(25,0); rim≤4ft, paint|x−25|≤8/y≤19, corner3|x−25|≥21.8/y≤14. Forecasts pool rim/paint/mid/corner3/above3,
with21 distance bands and training-band mean distance/lateral offset. Defensive conversion groups rim/paint/mid/combined3.
Recorded22 regions derive from rounded ESPN coordinates, including unknown2/3. Three pre-burn-in native games validate geometry:
529/530 native-coordinate and505/530 rounded-coordinate matches. Official shot value wins conflicts; no tracking is fabricated.
Observed maps use each team's last10 recorded current-season regular games before origin. Player defence maps are on-court exposure,
not individual attribution. Missing coordinates remain counted. Lineup forecast filters do not alter historical observations.

## Availability and exact worlds

D46 selects≤one uncertain player/team, within top3 by prior healthy minutes×(points+.7assists)/minute, deterministic ID ties.
Two/four10k branches force plays/sits before minutes/starters/matchups. Stable `lineup-v1:` IDs encode sorted assignments.
Expected is the exact weighted empirical mixture, without rounding/resimulation. Preserve float64 minutes, mass, source/seed/origin hashes
through Given/Joint/season operations. Availability/independence assumptions remain uncalibrated.

**D60 report-bands-v1:** out/suspended/IR0%, doubtful25%, questionable50%, probable75%, active100%. Generic DTD/unknown reports use
explicit target-weekday or publication-day today/tonight wording, age0–6 ET dates; contradictory/stale/undated/ambiguous remains50%.
Unlisted active is an assumption;≥3 recent games absent reduces prior20+minute roles to75%, others50%; confirmed availability is preserved.
Retain report comment/reason/policy/date/weights. Older forecasts keep original semantics; actual-participant tests do not validate live DNPs.

C1 early-complete-game-v1 publishes checked complete branches/Expected while queue continues; retained-season freshness stays explicit.
Partial bundles require early-delivery-v1. Exact-input chunk resume/cancellation and per-game original provenance protect pre-tip forecasts.

## Validation and promotion

|Fold|Fit through|Validation|
|---|---|---|
|F1|2023-12-31|Jan–Apr2024|
|F2|2024-12-31|Jan–Apr2025|
|F3|2025-09-30|Oct–Dec2025|
|F4|2025-12-31|Jan–Apr2026|

Burn-inDec2022. Protected2026–27 begins2026-07-01: once per prospectively frozen qualifying recipe, never selection or r3 rescoring.
`train.py --final` fits through2026-06-30. Feature decay begins near5 games roles/15mix/40shooting/80FT attempts with archetype shrinkage;
accepted fitting weights have no time decay. Use decayed offensive segments for low-sample buckets, not role games_eff.

Explicit policies: [v1](docs/protocols/promotion_v1_20261122.md), [v2](docs/protocols/promotion_v2_20261123.md),
[v3](docs/protocols/promotion_v3_20261123.md). V3 keeps27 proper/25 coverage safeguards and reports17 bias diagnostics separately;
it followed known r2v2 failure, requiring newly frozen independent evidence rather than rewriting old gates.
Known usage≥.25 means star; otherwise start_share≥.5 starter, else bench; missing unknown. Tier support≥100player-games/30games.
Pair identical games/inputs; bootstrap complete games10000times,seed20261122. Worlds/players are not independent historical observations.
Grade complete distributions, bias/PIT80%coverage and joint/tail/pace diagnostics. No probability clipping; zero winner probability means infinite log loss.

CRPS harm limits star/starter/bench: MIN.0578/.0605/.0796,PTS.0898/.0711/.0553,REB.0304/.0290/.0237,
AST.0261/.0207/.0155,3PM.0200 each; game total/margin.20,quarter total/margin.10,win Brier.005/logloss.010.
Upper paired95% bound must be below margin; coverage-harm lower bound>.03 vetoes. Signed cohort bias is diagnostic underv3.
Learned promotion needs a frozen primary benefit and independent confirmation; mechanics need correctness/compatibility.
Node screens require gains beyond seed-only noise, pooled2SE and no fold materially worse than twice noise. Node wins alone cannot promote engines.

Freeze component/removal/independent/seed/stress evidence before confirmation. A2's100/F1–F3+200F4+30seed+3×10k protocol is candidate-specific.
Pathway changes need16origins/four seasons and per-date paired CRPS/dispersion/coverage/persistence. Do not hide bad dates behind pooled means.
Player/team/period points/seconds, distinct legal fives, clocks/order/OT/fouls, short rosters, cutoff injection, worker/resume/raw identities
and≤3600s fresh full nightly remain required. Capture must preserve draws. Divergent vector worlds need not preserve Q1–Q3 RNG parity.

## Frozen evidence and limits

- 2,677 reconciled F1–F4 games/21,702 period ends. Use rebound-at-miss clocks and ordered substitutions. Latest-team NBA labels misattribute
8,637/113,089 tracking rows: use dated logs. Source dates do not establish original publication/revision times.
- C2 fixed three-variant court study found no player PTS benefit; no rescue/relabel. `20261124_c2_research_decision_v1.json`.
- S06 independent200games/4287player-games: MIN CRPS gain.03694[.02546,.05002],25/27 proper bounds clear, win Brier/logloss unresolved;
MIN80%coverage78.00→76.65%. Retainr3; no broader rescue/stress/protected run. `20261124_c4_s06_independent_decision_v1.json`.
- `20261124_c4_qualifier_v1.json` freezes no learned qualifier. Protectedr3 once-only246games/5492player-games clears27proper/25coverage/17bias;
small total CRPS regression+.04910[+.01256,+.08451] was accepted for supported timing gains, not a universal accuracy win.
- A2 found no supported shooting-form factor; synthetic variance is not calibration. Prior closing400-game audit: total bias+2.75,
PTS80%coverage76.3%,10.21 versus10.72 positive-minute players/team. No blanket bench cut follows. Earlier scoring neutrality/panel defects
were repaired prospectively; no proof a real old candidate failed because of them. `20261123_closing_{scorer_precheck,controls,scorer_audit}_v1.json`.

## Saved analysis and competitions

Five positive-mass Expected examples/game: each team's max own margin, each team's max individual fantasy score
(PTS+1.2REB+1.5AST+3STL+3BLK−TOV), and one frozen multi-stat representative; labels may share a world.
Store original branch/chunk/world IDs/weights. Replay the full original canonical chunk with read-only observers, never that world alone.
Reconcile events, clocks, boxes, minutes, legal fives and zone counters. No invented tracking/passes/trajectories. Preserve lineup compatibility.
U25 uses stored full-game player metrics (`periods.fg.advanced`), exact quantiles, probabilities and means; unsupported values stay unavailable.

**nba-competitions-2026-v1:**1200 base fixtures/80team +30world-local regular fixtures =1230/82team.
Group/QF/SF count; Cup final/play-in/playoffs excluded. Known fixtures independently replace slots once in actual date order; contradictions fail closed.
Six verified groups: wins/H2H/regulation differential/points/prior regular record/drawing; wildcard only runners-up, without H2H.
Higher seed hostsQF/SF; neutral Hinkle final. [2026 rules](https://www.nba.com/news/nba-cup-101).
22nonqualifiers play twice:20intra/two bottom-finisher cross games. Minimum-cost pairings favour existing three-game pairs; cycle orientation
provides1home/1away. QF losers pair within conference, favour prior away hosts. Alternative pairing/orientation is descriptive sensitivity.
No unpublished travel algorithm claimed. Partial nonqualifier draws fail closed.
[Official standings ties](https://www.nba.com/standings) restart after partial splits; division winners first; eligibility includes tied10th.
Play-in7hosts8,9hosts10,winner visits7/8loser. Fixed bracket/no reseeding/2-2-1-1-1/stop4wins; conference home follows original regular rank.
Finals home follows record/H2H/opposite-conference/drawing; source precedence: `20261124_c5_homecourt_clarification_v1.json`.
Unpublished postseason dates use two-day/global-round slots. Synthetic nonnegative conditional OT preserves pathway tied-game winner probability;
never clamps. Saved engine final scores remain exact; combined engine OT period count unknown. Cup ties use regulation, standings differential final.
Initial postseason/OT uncalibrated. `20261124_c5_completion_v1.json` owns accepted mechanical/release evidence and earlier failed attempts.
2025–26 hoopR labels include Cup final401809839 (NY/SA83games); C5 priors exclude it. Audit historical Cup finals/calendar leakage before B2.

D40 historical forecast backfill remains deferred; reconstruction needs pre-origin inputs **and fits**, immutable originals and explicit versioning.
