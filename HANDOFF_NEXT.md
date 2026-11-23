# Handoff — current state and next actions

Updated **23 November 2026**. Previous pushed checkpoint: **0eeebd5**; `git log -1` identifies this checkpoint.
Read [AGENTS](AGENTS.md), then this file and [PLAN](PLAN.md). Detailed history is indexed in
[docs/README](docs/README.md); do not read archives as current instructions.

## State

- **Accepted production:** possession **engine-v1.3**, D29 minutes, pool 0, **10,000 worlds/game**;
  **team-pathway-v1**, **10,000 seasons**. Today's ET games use possessions; tomorrow onward uses pathway.
- **Scope:** original 14-task A1 programme **58.0%** (S01–S07 complete, S13 deferred). Separate D42
  **Chunk A 37.5%** = A1 lineups **90% (reopened D51)** × 30% + A2 form **30%** × 35% + A3 replay **0%** × 35%.
  Chunk B **0%**. Do not reset/double-credit the original ledger; see PLAN §6.
- **A1 release decision reopened under D51 (owner, 23 Nov).** The earlier no-release fallback at
  `f19d15e` remains a historical decision; the owner authorised redesigning potentially over-restrictive
  gates. Progress returns from 100% fallback to **90% review**, explicitly reflecting added scope.
  [Promotion v2](docs/protocols/promotion_v2_20261123.md) separates mechanical corrections, learned
  predictors and stored scenarios. The existing repair establishes all **44 core score/bias bounds**;
  two quarter-coverage diagnostics are unresolved, not demonstrated harm. No production change yet.
  A fresh **200 F4 games outside the old panel**, 30 stream-1 games and three 10k stress games are frozen
  in `analysis/experiments/20261123_rule3_confirmation_manifest_v1.json`. Rule correctness, independent
  confirmation and delivery remain required; no automatic resurrection of rejected model variants.
  The prior-roster census is now a coverage limitation of that historical pipeline, not a universal live gate.
- **A2:** earlier player-form/persistence screens are inconclusive; shared-shot F1–F3 evidence is positive,
  F4 teammate-minus-opponent excess is unresolved. Accepted-control world/late-state diagnostics are pending.
  A synthetic mean-preserving prototype exists; no fitted factor, engine wiring or A2 promotion.
- **Execution authorised:** owner requests completion of A1 and A2 (23 Nov), lifting the prior A1 stop.
  A3/Chunk B are not part of this request. Startup smoke **108/108**, log
  `/tmp/musnba_a1_a2_start_smoke_20261123.log`. Gate/rule/coverage/A2 preflight **19/19** focused checks.
  Pilot: **1,556 unchanged control fields**, **1,725,578 candidate fives** independently reconciled; report
  `analysis/experiments/rule3_pilot_20261123_v1_audit.json`. The legacy auditor needed a signed phase adapter
  for NumPy's -1 sentinel; capture bytes and simulation outputs were unchanged. Engine recipes unchanged.
  Smoke **108/108**, fault **86/108**, exit 1; `/tmp/musnba_rule3_preflight_{smoke,fault}_20261123.log`.
  Active A1 method: [rule confirmation](docs/protocols/rule3_implementation_20261123.md).
- **D52:** removed both repository Actions workflows after unwanted failure emails. Checks run locally through
  `core.hooksPath=.githooks`; GitHub Pages still serves `gh-pages`. Do not reintroduce CI. The workflow-disable API
  returned 403 for this credential, so removing their trigger files is the supported fix; no queued runs existed.

## Latest live delivery

23 Nov ET origin: fetch exited 0 (68 requests, five new finals, zero failures); rebuilt inputs through 22 Nov
in **228.7s**. Snapshot stage **1,415.78s**: **10 games × 10k**, **10k seasons / 952 remaining games**.
Log `/tmp/musnba_a1_availability_nightly_20261123.log`.

- Independent precision/accounting: **14.7M** minute values, **20.58M** phone marginals, **200k** team scores;
  marginal error 0, maximum team-quarter minute error **4.27e−14**. This is accounting, not accuracy.
- Each device imports its own bundle manually; real phone import/memory acceptance remains unverified.
  No incremental streaming.
- PWA-only update **9f09eb4**, cache **fbf36cdfebb84d7e3865**: six saved-world outcome cards and a bootstrap
  download-failure reload action. Browser **30/30** across regression/cards/retry cases; inspected 3/2/1-column
  screenshots. Hosted import/offline **24/24 laptop, 23/23 phone**, installed upgrade **26/26**. Phone includes a
  deliberate blocked-download recovery. Evidence: `analysis/experiments/20261123_a2_stories_delivery_v1.json`.
  Export-only refresh: laptop **111,413,488 bytes / 2,031 records**; phone **86,886,931 / 2,009**. Snapshot/model
  payloads unchanged; existing imports support the cards. A new simulation bundle is still imported manually.
- Latest smoke **108/108**, deliberate fault exited 1 (**86/108**); `/tmp/musnba_rule3_preflight_{smoke,fault}_20261123.log`.

## Next actions

1. **Running:** `rule3_confirmation_20261123_v1`, eight one-thread workers, session **99485**, log
   `/tmp/musnba_rule3_confirmation_20261123_v1.log`; per-game pairs and frozen 60-file identity in
   `data/derived/experiments/rule3_confirmation_20261123_v1/plan.json`. Do not change fingerprinted engine/model/
   input files or run the nightly until complete. Runner: `analysis/rule3_confirmation.py`; auditor:
   `analysis/rule3_capture_audit.py`; scorecard: `analysis/rule3_scores.py`. All are opt-in; no release enabled.
2. Resume pilot passed: all canonical world digests equal the uninterrupted pilot; **1,556 legacy fields** equal.
   Stress `rule3_stress_20261123_v1` session **1015**, worker **65017**, log `/tmp/musnba_rule3_stress_20261123_v1.log`;
   stream `rule3_stream_20261123_v1` session **35390**, worker **65027**, log `/tmp/musnba_rule3_stream_20261123_v1.log`.
   Both workers resumed after smoke/export; no worker remains SIGSTOP'd. Normal total **8+1+1=10**.
   Stress/stream wall times include this checkpoint pause; don't claim unpaused pace.
   Reuse captured control dependence/late states for A2. Shared-shot report is `20261123_a2_shared_shooting_v1.json`;
   no factor fitted. PWA delivery is complete above; export log `/tmp/musnba_a2_stories_export_20261123.log`.
   :8767 review session **58196**; static/upgrade servers :8768/**35424**, :8769/**18564**.
   Temporary retry-shell server :8770/**19954**. All eight root docs reviewed/updated; no CI workflows exist.
3. Independently audit outputs; assess unchanged core harm margins and required rule/stress/stream evidence.
   If compatible, freeze a rule-level final recipe before reading protected outcomes. A current-season adapter
   is required (`backtest._init` is historical-only); non-fold `Models` medians need strict prior-origin filtering
   in both arms. Retain the old node final score. Release only after all applicable v2 gates.
   Wire structurally valid 10k branches/Expected/season views with
   explicit availability assumptions; unsupported individual games fail visibly. The common-interval season
   prototype's joint dependence remains unaccepted; inspect it before wiring. A1 checkpoints before A2.
4. Complete A2 shared-factor/late-game evidence and any supported candidates with v2's learned-change gate.
   Finish with a fresh accepted-system nightly, independent accounting and required dashboard/PWA/iCloud
   delivery, commit/push and stop. A3 and repository-wide cleanup remain successor work; preserve View Centre scope.

First commands (read-only setup; do not launch old candidates):

```sh
git status --short --branch
git --no-pager log --oneline -5
.venv/bin/python scripts/smoke.py
.venv/bin/python scripts/check_docs.py
ls -t analysis/experiments/ | head -15
```

Startup baseline passed. No historical forecast backfill, extra provider or A3/Chunk B work is authorised.

## Progress ladders — Chunk A

Headliners: lineup-aware player/game distributions; form/late-game realism; five saved games and 2-D replay.
Dependencies/acceptance are in PLAN §6a; methods/gates belong to ENGINE/TRAINING. Ten cumulative rungs/module;
100 includes evidence, necessary delivery, checks, docs and commit/push. Report every new 10% module/5% overall mark.

```text
Chunk A  ████████░░░░░░░░░░░░ 37.5%
A1       ██████████████████░░ 90% (D51 review)
A2       ██████░░░░░░░░░░░░░░ 30%
A3       ░░░░░░░░░░░░░░░░░░░░ 0%
```

| Rung | A1 lineups / Expected (30%) | A2 form / late game (35%) | A3 View Centre / delivery (35%) |
|---:|---|---|---|
| 10 | Freeze IDs, selection, provenance, dependence caveats. | Quantify residual covariance after roles/minutes. | Freeze five-world selection, schema, provenance, spatial/data budget. |
| 20 | One-player branches re-solve minutes/defence with legal fives. | Freeze prior-fold talent/form hypotheses and no-double-count controls. | Select each team's maximum margin and maximum individual fantasy worlds. |
| 30 | Two-player probabilities and unsupported-selection handling pass. | Isolated uncertainty draws preserve means/streams (synthetic only so far). | Select a real representative world using frozen multi-stat distance. |
| 40 | Persist deterministic 10k worlds/branch with seeds/inputs. | Test shared pace/shooting and dependence on folds. | Persist five labels; validate local files and invalid/future-source contracts. |
| 50 | Exact Expected weights handle 10k indivisibility. | Audit late fouls, clock, shot selection and OT by supported states. | Capture/replay exact original batch events without changing draws. |
| 60 | Weighted season identities; no duplicate near-term games. | Test supported state corrections against earlier-fold controls. | Independently reconcile event order, clocks, scores, boxes and legal fives. |
| 70 | Label/fail missing reports, unsupported dependence, cold rosters. | Sequential player-first screens: CRPS, bias, coverage, joint metrics. | Ship stored-only court, overlays, box, event list and playback controls. |
| 80 | Laptop branch/phone Expected compatibility (research injection only). | Test survivors together and under independent seeds. | Check seek/playback/accessibility, themes/widths, phone budget/offline. |
| 90 | **D51 reopened:** applicable rule/compatibility/confirmation gates under v2; prior fallback remains archived. | Freeze promote/reject decision under all applicable gates. | Fresh live 10k nightly; audit selections and iCloud/PWA delivery. |
| 100 | Verify results/limitations, required delivery, commit/push. | Verify evidence/fallback/delivery, commit/push. | Publish shell; construct successor; checks, commit/push and summary. |

A1's previous fallback was reopened by D51; 10–80 remain research milestones, not production passes. A2 40–100 and A3 all remain
open. Chunk B's full predeclared ladders and the original S01–S14 ladders are preserved in
[the frozen planning record](docs/archive/2026-11-23-before-lean/HANDOFF_NEXT.md); open only the relevant section
when preparing that chunk, and copy its current ladder here before execution.
