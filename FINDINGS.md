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
- **Research scale/accounting:** three prospective games produced **80k branch worlds** with no post-foul
  eligible roster below nine. Exact Expected/browser arithmetic and two-game branch season coupling were audited.
  The season prototype used **122,428 weighted paths / denominator 160k**, 17 near-term games, 959 total games;
  only two games had branches, so it is not full integration or validated dependence.
- **Representative gap:** fixed 200-game F4 oracle-roster screen had **0/2,000** typed exhaustion attempts;
  five draws/branch and known participants do not estimate actual pre-game risk. Earlier-fold screens are also
  conditional and sparse. Dated development injury-status calibration remains unavailable.
- **Actual retry stress:** one selected synthetic six-player F4 roster produced **10k accepted worlds** after
  **2,330 rejections**, including 1,893 failed first attempts. Against matched penalty continuations, total
  Δ **−1.083 [−1.297,−0.873]** and player 4431714 minutes Δ **−0.591 [−0.663,−0.520]**. These unadjusted
  paired-slot 95% intervals show distribution changes under one continuation assumption; not real-world bias,
  a population failure rate or an accuracy test. Clean-stop resume reproduced; hard-interrupted batches fail closed.
  [Independent audit](analysis/experiments/20261123_a1_retry_scale_full_v1_audit.json).
- **Latest vector penalty screen:** 200 fixed F4 games × 1,000 worlds, actual-participant oracle rosters:
  MIN CRPS Δ **−0.001262 [−0.003540,+0.001033]**; **67/69** non-inferiority bounds, Q3/Q4 margin coverage
  inconclusive. PTS Δ **+0.000691 [−0.002957,+0.004274]**, margin Δ **−0.041181 [−0.093283,+0.010238]**.
  Unadjusted 95% game-cluster intervals; primary screen failed, no multi-fold/final promotion. Independent
  accounting checked **98,276,074** fives, **50** technicals and **21,730** player means/CRPS values.
  [Gate](analysis/experiments/20261123_a1_vector_penalty_f4_200_v1_gate.json),
  [audit](analysis/experiments/20261123_a1_vector_penalty_f4_200_v1_audit.json). Do not rerun unchanged.
- **Worker benchmark:** fixed ten-game/1k candidate took **204.265s at four / 138.004s at eight** single-thread
  workers (32.4% shorter), identical outputs; summed worker peak RSS **5.80/11.72 GB**, excluding parent/OS.
  Full 200-game run at eight: **1,756.325s**, summed worker peaks **13.39 GB**. Spot zero swap activity is
  not continuous memory monitoring or proof eight is globally optimal.

## 8. A2 form evidence

Frozen methods: [A2 protocols](docs/protocols/a2_form_20261122.md). No factor is fitted or promoted.

| Diagnostic / population | Result and limitation |
|---|---|
| F4 residual dependence: 200 games, 3,604 eligible player-games, role-centred | Teammate/opponent minute covariance −1.121/+0.850; PTS/36 covariance −1.215/+0.462; difference −1.676 [−2.740,−0.500]. Actual-minute selection/ratio-of-means limit interpretation; these are observed errors, not baseline simulated dependence. |
| Within-player-game shot residuals: 595 fixed-panel F1–F3 games / 11,217 known-role player-games | Covariance 0.001368 [−0.000104,+0.002874]. Panel coverage 200/773, 200/782, 195/490 validation games. Pooled excess inconclusive and cannot separate talent/form/shared misspecification. |
| Cross-game shot residuals: same 595 games / 10,977 player-games / 1,557 player-role-fold groups | −0.000066 [−0.002095,+0.001786], two-way player/game bootstrap. F3 stars unsupported at 29 groups against minimum 30. No identified talent posterior. |
| Synthetic draw prototype | `p + s*z*p*(1-p)`, uniform z∈[−1,1], preserves mean/boundaries analytically; namespaced streams/zero-strength no-draw tests pass. Shape/strength arbitrary, no engine wiring or empirical calibration. |

Reports: `analysis/experiments/20261122_a2_residual_dependence_f4.json`,
`20261122_a2_shot_residuals_f1_f3_v2.json`, `20261122_a2_shot_persistence_f1_f3.json` in the same directory.
All reported intervals are exploratory 95%; no protected final outcomes were used.

## 9. Latest storage/delivery facts

23 Nov slate, **10 games × 10k worlds**: independently checked **14.7M** float64 minute values,
**20.58M** phone marginal values and **200k** team scores; maximum team-quarter minute error **4.27e−14**,
OT error **2.85e−14**, phone marginal error zero. **2,822/100k** worlds reached OT: simulation frequency,
not a real NBA rate or calibration test. [Audit](analysis/experiments/20261123_a1_live_slate_minutes_audit_v1.json).
Legacy rounded minutes cannot be recovered; availability, positive participation and rounded minutes are distinct.

Hosted fresh imports: **24/24 laptop, 23/23 phone**; measured renderer heaps **15.9/5.5 MiB** were single
readings, not peak/browser/device memory. Bundles ~111/87 MB require manual device import/acceptance; exact
current generation/shell/bytes live in HANDOFF. Finder-hidden export flags were fixed with non-dot staging and
flag clearing; preserve that behaviour. Service-worker precaching uses reload to avoid stale HTTP-cache assets.
No new delivery or predictive measurement occurred during documentation cleanup.
