# MusNBA — scope and progress

Updated **23 November 2026**. [HANDOFF](HANDOFF_NEXT.md) owns live state, jobs, next actions and active ladders;
[AGENTS](AGENTS.md) owns working rules. This file owns scope, dependencies, milestone accounting and backlog.
Detailed prior plans/logs: [archive index](docs/README.md).

## 1. Goal

A local-first NBA simulator, built from players and possessions, accurate against real outcomes. Each of today's
games has 10,000 coherent player/team/period worlds; a 10,000-world season uses those results, then updates its
own offensive/defensive team ratings after every later game. Laptop PWA is primary; phone retains distributions.
No fetching, fitting or simulation while browsing. Market lines are a diagnostic benchmark, never the target.

## 5. Phases

| Phase | State |
|---|---|
| Data, application shell and canonical history | Delivered; raw retention/reconciliation remain mandatory. |
| Possession model | Rule3 r1/unchanged v1.3 nodes accepted; D29 minutes, D30 defence, pool 0, 10k worlds. Accuracy gaps remain. |
| Feedback/evaluation | Node/fold/backtest harness and timing-aware result views exist; automatic refit/promotion is not built. |
| Season | Pathway v1 delivered; calibration, future absences and complete postseason/Cup mechanics remain. |
| Product | U1–U23, lineup branches and offline photos delivered; View Centre remains open. Device acceptance is manual. |

## 6. Original A1 milestone ledger

This is the **14-task accuracy programme**, distinct from **Chunk A module A1** below. Original weights are
unchanged and sum to 100%; **64.0% complete**. Do not credit D42 module progress twice. S13 remains deferred,
so the completion ceiling without reauthorisation is 95%. Full original scopes/ladders remain in the
[frozen PLAN](docs/archive/2026-11-23-before-lean/PLAN.md) and
[frozen HANDOFF](docs/archive/2026-11-23-before-lean/HANDOFF_NEXT.md).

| ID | Scope | Weight | Status / outcome |
|---|---|---:|---|
| S01 | Reproducible baseline/evaluation | 6% | 100%; both seeds, manifests, noise floors and populations frozen. |
| S02 | Data integrity/train–serve parity | 6% | 100%; history/audits complete; corrected inputs remain research-only. |
| S03 | Locate lost offence/defence signal | 8% | 100%; matched diagnosis and two candidate families specified. |
| S04 | Player defence/shot quality | 12% | 100%; rim-expression and tracking increments failed node gates. |
| S05 | Roles/membership/minutes | 8% | 100%; both screens failed pooled minute gate; retain D29. |
| S06 | State-responsive substitutions | 12% | 100%; candidate failed 3 non-inferiority bounds; retain production. |
| S07 | Availability/starts/future absences | 6% | 100%; fixed fallbacks, origin/report/timing corrections delivered; no fitted injury hazard. |
| S08 | Branches/coherent Expected | 6% | 100%; qualified r1 branches/Expected/season accounting and PWA delivery; assumptions labelled. |
| S09 | Form/talent/end-game | 10% | 0% original acceptance; diagnostics/prototype exist. |
| S10 | Season calibration | 8% | 0%; D42 B2. |
| S11 | Integrated confirmation | 5% | 0%; D42 B3. |
| S12 | Rotation/event/branch visibility | 3% | 0% original acceptance; A3/B3 divide delivery. |
| S13 | Versioned historical forecast replay | 5% | 0%; deferred by owner D40, preserve archives. |
| S14 | Final nightly/delivery/successor | 5% | 0%; final integrated delivery remains. |

M1–M5b/M6a ingest, profiles, sixteen-node models and aggregation were completed before this programme. M6 is
the served engine; M7 substitutions, M8 form, M9 promotion, M10 playback, M11 availability and M12 pathway
remain the relevant accuracy/product milestones. A research rejection does not mean the modelling problem is solved.

### 6a. Authorised D42 execution split

**Chunk A: believable games and visible simulations — 48.0%.** Headliners: lineup-aware player/game outcomes;
form and late-game realism; five actual saved-world examples with a reusable 2-D View Centre. Depends on S01–S07.
Owner (23 Nov) now authorises completing A1 and A2, lifting the earlier A1 stop; A3 and Chunk B remain outside this session.

| Module | Weight | Progress | Dependency and acceptance/fallback |
|---|---:|---:|---|
| A1 Lineups/Expected | 30% | 90% D51 review | Prior no-release fallback reopened by owner-authorised gate redesign; v2 separates mechanics/scenarios from learned accuracy changes. Qualified r1 branches/photos delivered; D56 fitter/queue decision and final checkpoint remain. |
| A2 Form/late game | 35% | 60% | Contextual late clock passes earlier-fold and separate F4 analytical screens; engine compatibility remains. No calibrated form factor/promotion. |
| A3 View Centre/delivery | 35% | 0% | A1/A2 decisions. Five labelled real worlds, reconciled event files, 2-D court/player, responsive/offline checks and fresh nightly. |

**Chunk B: stronger defence and reliable season paths — 0%.** Depends on Chunk A decisions/delivery. Do not
repeat rejected mechanisms unchanged. Full ten-rung/module planning contracts are preserved in the frozen HANDOFF;
activate and refresh them before execution, without changing their weights silently.

| Module | Weight | Acceptance/fallback |
|---|---:|---|
| B1 Defence/foul-outs | 30% | New evidence-backed player/lineup mechanism and legal mechanics, dated inputs, node/engine gates; retain accepted model on failure. |
| B2 Season pathway | 30% | Prior/opponent-adjusted starts, memory/drift/absence support; all 16 historical origins and exact near-term mixture; retain pathway v1 if rejected. |
| B3 Integration/visibility/delivery | 40% | Combined/removal screens, eligible all-fold confirmation, seed/10k stress, final score only for qualifying frozen version; rotation map and final nightly. |

Every completed module checkpoints before the next. Each chunk ends with a fresh live nightly on accepted systems,
10k games/seasons, necessary PWA delivery and a useful dashboard improvement if no model promotes. Incremental
delivery is immediate successor work (D54); historical replay remains deferred. S11/S14 need their own acceptance.

### 6b. What earns promotion

[TRAINING_PLAN §8](TRAINING_PLAN.md#8-a1-acceptance-and-reproducibility) links versioned D51/v2 and explicit D57/v3 policies:
pre-game player tiers first, then team/joint outcomes, frozen paired uncertainty/non-inferiority/noise,
class-specific confirmation, simulation-resolution checks, stress and exact identities/cutoffs/runtime, then a frozen final evaluation where applicable. Legacy numerical margins remain; D51 permits redesigning inapplicable blocking requirements.
Actual-participant diagnostics do not establish pre-game availability accuracy. Redesign requires a recorded
methodological reason and frozen independent confirmation; do not move thresholds merely to pass a known candidate.

Ambitions: ≥5% better minute CRPS, ≥2% better PTS/REB/AST in affected supported tiers, beat the team benchmark,
coverage toward 80%, and better season calibration at every start date. These are aims, not promises or substitute gates.

### 6c. Checkpoint and successor

Follow AGENTS §5. Each completed subtask/module and session stop records a concise result, remaining limitation,
evidence link, delivery impact and next action, then commits/pushes. Keep HANDOFF current; detailed experiment logs
belong under `analysis/experiments/`, not repeated across root docs. Every final development-chunk checkpoint
constructs its successor: headliners, dependencies, weights totalling 100%, ten concrete rungs/module,
acceptance/fallback, first commands, artifacts and a final live nightly. Docs-only maintenance starts no nightly.

## 9. Decisions still requiring the owner

No new product choice currently blocks the authorised scope. A new data provider needs sign-off. Real-device PWA
installation/import/memory acceptance remains an owner check; exporting to iCloud is not acceptance.

### 9b. Product backlog

| Work | Current boundary |
|---|---|
| Full lineup selector | Delivered in A1; laptop/local saved branches, phone Expected-only. Later localhost lineup/minute editor uses a separate stored what-if runner. |
| Five-game View Centre | A3; own-margin extreme and highest individual fantasy world per team, plus a real representative world. Source-neutral event replay; actual-game adapter later. |
| Rotation map | B3/S12; stored probabilities sum to five. |
| Deeper outcome visualisations | Extend existing conditional/joint distributions, percentile bands and exceedance views; extremes stay labelled. |
| Competition tabs | Regular season/Cup/playoffs with per-world play-in/brackets; not currently a complete postseason simulation. |
| Incremental iCloud export — next priority (D54) | Publish after each complete checked 10k game; safe per-game generations, coherent season freshness, resumable exports and PWA import/offline validation. Current export remains end-of-nightly. [Contract](docs/protocols/incremental_catchup.md). |
| Missed-day reconstruction proposal | Nightly already collects missing finals; it does not regenerate missed possession forecasts. Future labelled actual-participant reconstruction needs pre-origin inputs AND fits, predicted minutes and immutable originals; D40 replay execution remains deferred. |
| Advanced player stats | Actual +/−, six box-derived rates and dated action-share input exist. True simulated possession USG%, on-court ratings, simulated +/− and BPM need honest capture/definitions/validation. |
| Code simplification (owner, 23 Nov) | After A1/A2, inventory production dependencies, duplicate logic and research-only files; target proven maintenance/runtime costs. Preserve reproducibility and View Centre scope; no line-count-driven wholesale rewrite or blind deletion. |
| Shooting geography (owner hypothesis, 23 Nov) | Start from NBA source-defined basic/advanced zones; the owner's dunker/post/wing/slot examples are illustrative, not a required bespoke taxonomy. Fit shooter/defender attempts and makes by zone, pooling sparse cells to broader parents and retaining supported side/direction. Compare current five zones/21 bands, source-zone-only, then within-zone distance on folds. Preserve raw data; audit source units/orientation, labels/coverage and observed versus inferred defender attribution. Version derived mappings/unknowns; extend the existing zone-choice node only after evidence. No mapping/model chosen or collection started. |
| Player headshots — active (D55) | Shared offline icons from retained ESPN roster URLs, initials fallback; cover player-bearing pages and inspect 1440/960/390 in both themes. Include required PWA asset/bundle delivery with A1/A2. |
| House design | Keep key boxes first, secondary content expandable, state preserved. Extend existing U3 role badges/U11 defence profiles. Lab polish is low priority. |

Spatial displays must follow D43: zones/bands or validated source positions; no invented tracking. All dashboard copy
reflects loaded data/configuration. These items do not authorise forecast-history backfill (D40).

## 10. Recent checkpoints

| Date | Result | Evidence |
|---|---|---|
| 23 Nov | Rule r1 final246 passes; S08 completes: r1 lineups/headshots,15×10k batches; hosted29/27, upgrade32, smoke108/fault exit1. D56 protected v2 establishes42/44 (all27 proper scores); bias-veto audit motivates frozen v3/fresh200 F4 confirmation. No r2 release. Clock engine tests await A1; D54 follows. | HANDOFF live work; FINDINGS §7/§8. |
| 23 Nov | D52 removes unwanted CI workflows; local checks and branch-based Pages hosting retained. No model/app change. | AGENTS local-check rule; README hosting commands. |
| 23 Nov | D51 reopens A1 release review; v2 compatibility/confirmation and retained defender-result audit. | [Active policy](docs/protocols/promotion_v2_20261123.md) |
| 23 Nov | A1 no-release fallback: 28,530 memberships audited, 783/800 starter contexts supported; v1.3 retained. | [Decision](docs/research/a1_no_release_20261123.md) |
| 23 Nov | Lean documentation maintenance; no model/app/data/progress change. | [Maintenance record](docs/maintenance/2026-11-23-lean-docs.md) |
| 23 Nov | Participation slices and 10-game/10k-season delivery; full branches blocked. | Commit `4d58ff9`; HANDOFF latest delivery; FINDINGS. |
| 23 Nov | Vector penalty candidate failed fixed F4 screen; retain v1.3. | Commit `8dee45a`; FINDINGS §7. |
| 22 Nov | S01–S07 decided; candidates not promoted; report/origin/timing safeguards delivered. | Original ledger above; detailed frozen history in docs index. |

Older checkpoint narratives are archived; add only material recent decisions here and rotate completed detail out.
