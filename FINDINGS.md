# Findings — evidence that affects current work

Updated **23 November 2026**. Measured facts/decisions only; [HANDOFF](HANDOFF_NEXT.md) owns live state.
These summaries retain the populations and limitations needed for the next decision. Full older measurements,
corrections, hashes and reproduction detail are in the [frozen findings](docs/archive/2026-11-23-before-lean/FINDINGS.md)
and linked reports. Do not rederive established facts or repeat rejected variants unchanged.

## 1. Data conventions and pitfalls

- **Rebound clocks:** live 2026–27 ESPN stamps rebounds at the miss clock; use this convention across seasons.
  Five-game adapter parity reproduced identical segments. The resulting v1.1 aggregation improved most player stats.
- **Quarter truth:** on **2,677** eligible reconciled F1–F4 regular-season games (731/738/490/718), player-period
  points reconcile to boxes and **21,702** explicit period-end scoreboard totals, including OT. Segment sums
  differ from boxes in **56 home / 54 away** games of the 200-game panel by up to two points. Backfilled later
  sequence numbers may have earlier clocks: use explicit period-end snapshots, not numerically last events.
  [Quarter audit](analysis/experiments/20261122_a1_quarter_audit.json).
- **Historical sources:** S02 retained all **3,622** queued NBA PBP responses; logged-game coverage was
  **1,320/1,319/1,321/1,322/235** across 2022–23 through 2026–27 at its 22 Nov inventory. No missing/corrupt/
  unindexed/hash-mismatched files; **45** older entries lack original fetch URL/time, which remain unknown.
  [Completed inventory](analysis/experiments/20261122_a1_raw_inventory_completed.json).
- **Substitution labels:** same-clock windows can expose a later free throw's score to an earlier substitution;
  repeated entries can be real reversals. Use sequence-aware pre-event state, not deduplication/clock-group ends.
  Reproduction: game 401810498, Q4 0:33.3, old window margin −4 versus pre-sub −3.
- **Tracking teams:** **8,637/113,089** Overall rows (7.64%) had latest-team labels inconsistent with that day's
  NBA log. Join identity/date to the dated log; never use `PLAYER_LAST_TEAM_ABBREVIATION` as historical team.
  Strictly earlier response dates still do not prove original publication/revision or crosswalk timing.
- **Other retained quirks:** 2022–24 NBA matchup FGA overcount (~111%); box-only ESPN game 401810469;
  73 All-Star rows were misflagged as NBA in minute history. First-season whole-season priors, undated body data
  and whole-batch missing-defender fills need causal guards; isolated corrected inputs are not promoted.
  Detailed S02/S05 correction populations remain in frozen findings.

## 2. Accepted controls and noise

**Possession engine:** v1.3, targets/pool 0, known actual participants/projected starters. The retained **200 F4
games × 1,000 worlds** control has margin/total CRPS **9.415/11.723**, win log loss **0.5738**, total bias
**+1.81**, total/margin coverage **69%/75.5%**. Same-game team benchmark: **9.322/11.353/0.5584**.
Offence loading **0.727 versus 1.144 real (63.5%)**, defence **0.678 versus 1.685 (40.2%)**.
[Original control](analysis/experiments/20261120T162930Z_v1.3_pool_per_world_F4.json).

S01 regenerated the same legacy outputs and added quarter/3PM accounting. **4,346 scored player-games**:
284 pre-game stars, 1,578 starters, 2,472 bench, 12 unknown; **485** differ from legacy actual-starter tiers.
Pooled MIN/PTS/REB/AST/3PM CRPS **3.5662/3.1614/1.3033/0.9006/0.5889**. One simulated player lacks raw-box
truth, so only **399/400** team 3PM sums are fully scoreable. Missing truth was listed, not fabricated.

Independent-seed pooled CRPS floors are **0.02634/0.00919/0.00384/0.00213/0.00158**; total/margin floors
**0.09372/0.08323**. These are noise thresholds, not candidate gains.
[Manifest](analysis/experiments/20261122_a1_manifest.json),
[seed noise](analysis/experiments/20261122_a1_seed_noise.json),
[production pins](analysis/experiments/20261122_a1_production_baseline.json). S01 control source is pinned at
`c6d5db4`; later type-only seed annotation preserved behavior. Do not rerun completed controls without new reason.

**Team pathway v1:** original 16 season/start origins / **480 team-starts**, 10k worlds: final-win CRPS
**2.611 versus 2.727** fixed-probability baseline, dispersion **1.00 versus 1.53**, 10–90% coverage **84.2%
versus 65%**. November is too wide; simulated surprise persistence fades **0.52→0.18**, observed near **0.40**.
[Calibration](analysis/experiments/20261120T093809Z_season_calibration.json). This is first-cut historical
calibration, not completion of B2/S10.

## 6b. Completed S03–S07 decisions

| Work / population | Measured result | Decision/evidence |
|---|---|---|
| S03 signal, same 200 F4 games | Defence points/100 loading error already −1.017 under teacher forcing versus −1.008 free-running; contrast +0.009 [−0.195,+0.211]. | Bottleneck already exists in conditional replay; rotations are not proved irrelevant. [Matched diagnosis](analysis/experiments/20261122_a1_s03_components.json). |
| S04 rim expression, guarded F1–F4 actual-shot nodes | Mean relative loss Δ −0.000259%, pooled z −0.283; training-noise floor 0.013718%. | Reject; [node gate](analysis/experiments/20261122_a1_s04_rim_node_gate.json). |
| S04 lagged tracking defence, guarded F1–F4 shot nodes | Mean loss worsened 0.00906%, pooled z +3.76; F1 +0.03021%, z +3.63. | Reject; [node gate](analysis/experiments/20261122_a1_s04_tracking_node_gate.json). Not proof all richer defence fails. |
| S05 NBA-only minute history, 200 F4 games/4,346 scored players | Pooled MIN CRPS Δ −0.00416; below noise. | Retain D29; [corrected gate](analysis/experiments/20261122_a1_s05_nba_only_fixed200_gate_v3.json). |
| S05 strict allocation, same population | Pooled MIN CRPS Δ +0.000268 [−0.000111,+0.000653]. | Retain D29; [gate](analysis/experiments/20261122_a1_s05_strict_fixed200_gate.json). Feasibility repair alone is not predictive improvement. |
| S06 timeout substitutions/penalty, same population | MIN CRPS 3.5662→3.5309, Δ −0.03529 [−0.04462,−0.02609]; only 66/69 non-inferiority bounds established. | Do not promote: margin, Q2-margin and Q3-total coverage gates unresolved. [Gate](analysis/experiments/20261122_a1_s06_penalty_fixed200_gate.json). |
| S06 state response, 191 supported recorded games | Close exits 15.31% recorded/11.91% simulated; foul trouble 26.98%/20.15%; 48/70 supported role/state cells. | Descriptive differing opportunities, not causal/pre-game accuracy. [Accounting](analysis/experiments/20261122_a1_s06_state_capture_fixed200_accounting.json). |
| S07 availability | Zero genuinely dated development-report origins; five retained report collections were protected-season only. | Fixed uncalibrated status/start fallbacks; no fitted future physical-absence hazard. Origin/report/timing fixes delivered. |

Earlier v1.4c/e/f real-matchup candidates also failed to beat production on matched F4 player/team outcomes (D37);
v1.4d hunting was not run. These outcomes close those experiments, not the overall defence problem. The December-2025
assignment fit cannot be reused for F1–F3; corrected fold inputs need dated fits and rebuilds.

## 7. A1 branch evidence and remaining gate

- **D51 framework audit (23 Nov):** the unchanged model's independent simulation stream establishes
  only **61/69** legacy non-inferiority bounds (one score and seven coverage bounds unresolved), without
  demonstrated material harm. This is a precision/power warning, not proof that confidence intervals are
  mathematically wrong. The prior mechanical repair establishes **44/44** core score/bias bounds; two
  quarter-coverage diagnostics remain unresolved. V2 removes the inapplicable primary-gain requirement
  for mechanical fixes, retains core margins and requires correctness plus fresh confirmation. It does
  not auto-promote the old repair. Report `analysis/experiments/20261123_gate_framework_audit_v1.json`.
  The NBA rule audit also identifies an additional issue to test: retained offenders' offensive fouls
  must charge a team foul under Rule 3-I/Rule 12-VII's exception; the old continuation omits that increment.
- **D51 old-defender reanalysis:** same 200 F4 games / 4,346 scored player-games, pre-game tiers;
  v1.4c/e/f pooled PTS CRPS changes **+0.007504 [−0.004064,+0.018665]**, **+0.006684
  [−0.003903,+0.017161]**, **+0.006195 [−0.004761,+0.017297]** (unadjusted 95% game-bootstrap).
  None establishes a pooled scoring improvement; these are not proof of pooled harm. Original model
  version streams differ, old rows omit quarter/3PM outputs, and this is no new promotion confirmation.
  Reports `analysis/experiments/20261123_gate_review_v14{c,e,f}.json`; no simulation reruns or final-test use.

- **Rule 3 integration/resume pilot:** three original wiring games × 1,000 worlds/branch. Unchanged control
  reproduces **1,556 game/player fields to 1e−12**; **1,725,578 candidate fives** reconcile, maximum replayed
  player-minute error **1.78e−15**. Stop/resume canonical arrays match uninterrupted execution exactly.
  No exhaustion exception occurred in these games; synthetic fixtures cover it. These are correctness checks,
  not population accuracy evidence. Reports `rule3_{pilot,resume}_20261123_v1_audit.json` in experiments.
- **23 Nov prior-roster readiness census:** on the fixed 800 F1–F4 games, inferred source rosters cover
  795 and required starter pools are supported in **783/800** (199/200/184/200 by fold). **371/28,530**
  candidates lack a prior profile/position; 19 required-pool positions affect 12 games, plus five missing
  roster contexts. Independent raw-prior reconstruction checked all 28,530 memberships and 1,590 pools.
  The frozen probe has 124/128 supported contexts and was not simulated after its readiness failure.
  No outcomes were read or accuracy claimed. [Decision and unpassed gates](docs/research/a1_no_release_20261123.md).
  Reports `analysis/experiments/a1_prior_roster_20261123_v2{,_audit}.json`; existing systems retained.
- **Legal-five defect:** fixed F4 game 401810327, 32 worlds/branch, synthetic uncertainty/actual participants:
  original run had disqualified fives in **14/32 plays and 16/32 sits** worlds; isolated repair reconciled
  **16,130/16,336** fives. This is one diagnostic, not a population rate or promotion.
- **Qualified Rule 3 (D51):** fresh 200 F4 pairs establish **44/44 core bounds**; independent stream
  establishes 34/34 supported bounds (ten star bounds unsupported). All three 10k stress pairs reconcile.
  Frozen final: **246 games / 5,492 scored player-games**, all **44/44** core bounds; Q3-margin coverage
  remains imprecise, no demonstrated harm. Independent audit **142,218,382 legal fives / 455 exhaustion
  penalties**, maximum replayed minute error 3.56e−15. Unchanged fitted nodes; no availability-skill claim.
  Reports `rule3_{confirmation,final}_20261123_v1{,_compare,_compare_gate,_audit}.json` in experiments; r1 PWA delivery is complete (HANDOFF).
- **Mixture/storage accounting:** current23Nov r2:10games/15×10k batches,80,337 weighted season
  paths/mass100k, every atom exact,53,732 histogram checks. Max cross-game correlation.02283 versus
  32 naive independent references.00868–.01897: descriptive, not a calibrated coupling-null/dependence
  test. Reports `20261123_r2_{live,season}_accounting_v1.json`. Earlier generations retained. Minute
  codec:3,780 exact threshold checks; byte shuffling gzip29.1→18.2MB, maxrecord4.01MB
  (`20261123_a1_minute_cdf_probe_v{1,2}.json`). Not real-device acceptance.
- **Representative gap:** fixed 200-game F4 oracle-roster screen had **0/2,000** typed exhaustion attempts;
  five draws/branch and known participants do not estimate actual pre-game risk. Earlier-fold screens are also
  conditional and sparse. Dated development injury-status calibration remains unavailable.
- **Retry stress:** one artificial six-player F4 roster needed **2,330 rejections** for 10k accepted worlds.
  Matched penalty continuations have different scoring/minute distributions: a selection effect under one
  assumption, not measured real-world bias or a population failure rate. Clean-stop resume reproduced;
  hard-interrupted batches fail closed. Full counts/effects:
  [Independent audit](analysis/experiments/20261123_a1_retry_scale_full_v1_audit.json).
- **Historical vector penalty screen:** 200 F4 games × 1k, oracle rosters; **67/69** bounds, Q3/Q4 coverage
  inconclusive, primary screen failed. No multi-fold/final promotion. Independent accounting passed.
  [Gate](analysis/experiments/20261123_a1_vector_penalty_f4_200_v1_gate.json),
  [audit](analysis/experiments/20261123_a1_vector_penalty_f4_200_v1_audit.json). Do not rerun unchanged.
- **D56 independence/performance:** legacy D29 chooses one fit iteration from batch-maximum error;
  another world can affect retained rotations. No histogram steps were observed. Canonical row-local
  correction matches separate one-world fits/regrouping; three preparation checks pass. One10k game/1k
  chunks took74.441s at10 versus134.063s at8 workers, identical arrays; repeat72.381s. Queue probe
  (one ordinary/one branched,1k each) passes9,440 histogram checks across worker counts. Reports
  `20261123_world_{chunk_workers_compare,queue_workers_compare}_v1.json`; candidate remains off.
  Development200 F4 pairs:44/44 core,25/25 coverage; MIN/PTS CRPS∆−.02876/−.00854. Stream30:
  28 established/six imprecise/ten unsupported. Stress3×10k:34,512,482 independently checked fives.
  Protected246:42/44, all27 proper scores; unresolved star MIN/PTS cohort-bias increases+.34253min
  [+.02442,+.44989]/+.24087PTS[−.25976,+.31726], margins.30. No demonstrated material harm;
  one imprecise star-minute coverage diagnostic. Audit284,432,368 legal fives. Preserved reports
  `independent_rotation_{f4,stream,stress,final}_20261123_v1*`; protected score never repeated.
- **D57:** independent reconstruction reproduces protected bias/10k-bootstrap intervals to1e−12.
  A synthetic all-player improvement breaches the old cohort-bias margin through reduced cancellation;
  arithmetic is correct, universal veto conflicts with individual accuracy. A/A v2 establishes43/44.
  [Audit](analysis/experiments/20261123_independent_rotation_gate_sanity_v1.json),
  [prospective v3](docs/protocols/promotion_v3_20261123.md). Fresh200 F4/4,297 scored player-games:
  all27 proper,17 bias and25 coverage bounds established; audit227,809,516 legal fives. MIN/PTS CRPS∆
  −.02345[−.04275,−.00640]/−.00806[−.01540,−.00129], conditional actual participants,5 missing-box
  player-games excluded. Reports `independent_rotation_policy_confirmation_20261123_v1*`. Qualified
  for integration, not universal accuracy improvement; original protected result preserved.

- **Runtime recipe lookup:** r1/r2 aliases skipped advanced-profile rebuilds. Resolve fitted-node config;
  missing recipes now fail. Both935-row current tables reach22Nov (no date gap). Regression2/2 passes;
  exact old code fails3 subcases. Report `20261123_nightly_runtime_recipe_audit_v1.json`.

## 8. A2 form evidence

Frozen methods: [A2 protocols](docs/protocols/a2_form_20261122.md). No factor is fitted or promoted.

| Diagnostic / population | Result and limitation |
|---|---|
| F4 residual dependence: 200 games, 3,604 eligible player-games, role-centred | Teammate/opponent minute covariance −1.121/+0.850; PTS/36 covariance −1.215/+0.462; difference −1.676 [−2.740,−0.500]. Actual-minute selection/ratio-of-means limit interpretation; these are observed errors, not baseline simulated dependence. |
| Within-player-game shot residuals: 595 fixed-panel F1–F3 games / 11,217 known-role player-games | Covariance 0.001368 [−0.000104,+0.002874]. Panel coverage 200/773, 200/782, 195/490 validation games. Pooled excess inconclusive and cannot separate talent/form/shared misspecification. |
| Cross-game shot residuals: same 595 games / 10,977 player-games / 1,557 player-role-fold groups | −0.000066 [−0.002095,+0.001786], two-way player/game bootstrap. F3 stars unsupported at 29 groups against minimum 30. No identified talent posterior. |
| Different-player shared shooting: 139,534 aligned eligible shots, fixed F1–F4 panels | Earlier F1–F3 teammate-minus-opponent residual product **+0.000540 [0.000211,0.000894]**; F4 **+0.000020 [−0.000509,+0.000589]**. Shot-weighted fold/cohort centres refit per game bootstrap. This association mixes talent/form/conditions/misspecification; it does not identify a factor strength. |
| Fresh F4 accepted-control worlds: 200 games / 3,625 eligible player-games, 1k worlds/game | Observed-minus-world PTS covariance: teammates **−0.107 [−0.488,+0.272]**, opponents **+0.027 [−0.203,+0.240]**. No clear pooled missing scoring dependence. Stars/starters' MIN teammate gap **+7.487 [5.078,9.893]**; possession-error variance ~22.6–23.2 versus simulated ~15.4–15.5. This motivates earlier-fold pace/minute investigation, not arbitrary variance widening; mean/rotation misspecification remains possible. |
| Late states: same 200 games, 2,333 actual opportunities / 16 excluded; eight of 21 clock/margin cells supported | Trailing 4–8 with ≤24s: actual action time **4.14s**, simulated **6.04s**, gap **+1.91 [1.37,2.41]s**; actual three share **68.6%**, simulated **57.0%**. State visitation differs. The existing ≤24s clock sampler pools periods/margins; test prior-fitted contextual timing before adding latent shooting variation. OT 4.0% actual / 2.72% simulated, difference interval crosses zero. |
| Contextual late clock, frozen earlier-fold screen / separate F4 confirmation | F1–F3: **1,932 games / 5,382 opportunities**, joint time/no-action loss **0.19856→0.12849**, Δ −0.07007 [−0.07538,−0.06485]. F4: **199 games / 474**, **0.21633→0.13415**, Δ −0.08218 [−0.10119,−0.06556]. Also beats clean bridge; both components improve. Independent squared-CDF audit checks 600 distributions (max error 8.53e−15). Conditional node evidence, not simulated-game improvement. Reports `20261123_a2_late_clock_{screen,confirmation,audit}_v1.json`. |
| Synthetic draw prototype | `p + s*z*p*(1-p)`, uniform z∈[−1,1], preserves mean/boundaries analytically; namespaced streams/zero-strength no-draw tests pass. Shape/strength arbitrary, no engine wiring or empirical calibration. |

Reports: `analysis/experiments/20261122_a2_residual_dependence_f4.json`,
`20261122_a2_shot_residuals_f1_f3_v2.json`, `20261122_a2_shot_persistence_f1_f3.json` in the same directory.
Shared-shooting report: `analysis/experiments/20261123_a2_shared_shooting_v1.json`.
Fresh-world report: `analysis/experiments/20261123_a2_world_diagnostics_v1.json`; captures pass independent accounting.
All reported intervals are exploratory 95%; no protected final outcomes were used.

## 9. Legacy v1.3 storage/delivery facts

23 Nov slate, **10 games × 10k worlds**: independently checked **14.7M** float64 minute values,
**20.58M** phone marginal values and **200k** team scores; maximum team-quarter minute error **4.27e−14**,
OT error **2.85e−14**, phone marginal error zero. **2,822/100k** worlds reached OT: simulation frequency,
not a real NBA rate or calibration test. [Audit](analysis/experiments/20261123_a1_live_slate_minutes_audit_v1.json).
Legacy rounded minutes cannot be recovered; availability, positive participation and rounded minutes are distinct.

Historical delivery/hidden-flag/cache evidence remains in the archived findings and original delivery
reports. Current r2 snapshot1184.0s versus r1's1465.33s (observed19.2% shorter); required advanced
rebuild231.9s, all12 prior input files byte-identical. Six raw runtime replays and three queue branches
match retained references; live53,732 checks, smoke108/108, deliberate fault86/108 exit1, hosted29/27.
Receipts `20261123_r2_{release,integrated_delivery,profile_refresh_identity}_v1.json`; manual imports
remain required. Existing shell assets unchanged; no iid-season or universal accuracy claim.
