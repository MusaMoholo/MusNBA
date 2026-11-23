# Handoff — current state and next actions

Updated **23 November 2026**. Previous pushed checkpoint: **aa3d25d**; `git log -1` identifies this checkpoint.
Read [AGENTS](AGENTS.md), then this file and [PLAN](PLAN.md). Detailed history is indexed in
[docs/README](docs/README.md); do not read archives as current instructions.

## State

- **Accepted production:** possession **engine-v1.3**, D29 minutes, pool 0, **10,000 worlds/game**;
  **team-pathway-v1**, **10,000 seasons**. Today's ET games use possessions; tomorrow onward uses pathway.
- **Scope:** original 14-task A1 programme **58.0%** (S01–S07 complete, S13 deferred). Separate D42
  **Chunk A 34.5%** = A1 lineups **80%** × 30% + A2 form **30%** × 35% + A3 replay **0%** × 35%.
  Chunk B **0%**. Do not reset/double-credit the original ledger; see PLAN §6.
- **A1 remains blocked, not complete.** Branch/Expected/weighted-season/browser mechanics exist only in research.
  No normal route supplies branch worlds. Production exposes positive-/zero-minute participation slices,
  not forced-availability scenarios. A1's 80% includes injection-only UI evidence, not a delivered selector.
- **Why blocked:** representative pre-origin retry/bias evidence and applicable player-first gates remain open.
  Dated development injury-report calibration is unavailable; labelled fixed scenario weights are permitted,
  but cannot be called calibrated forecasts. Invalid-world retry is unwired and can select different outcomes.
- **Latest candidate rejected:** vector matched-penalty repair, 200 fixed F4 oracle-roster games × 1,000 worlds:
  pooled minute CRPS Δ **−0.001262 [−0.003540, +0.001033]**, below **0.026341** noise floor;
  **67/69** non-inferiority bounds established (Q3/Q4 margin coverage inconclusive). Do not rerun unchanged.
- **A2:** residual-dependence diagnostics and a synthetic mean-preserving draw prototype exist. No fitted latent
  factor, engine wiring or accuracy gain; within-/cross-game residual evidence is inconclusive. No A2 promotion.
- **No model/download jobs running at this checkpoint.** Documentation cleanup changes no models, snapshots,
  bundle contract, app assets or progress. Baseline smoke **108/108**; final documentation audit is in
  [the cleanup record](docs/maintenance/2026-11-23-lean-docs.md).

## Latest live delivery

23 Nov ET origin: fetch exited 0 (68 requests, five new finals, zero failures); rebuilt inputs through 22 Nov
in **228.7s**. Snapshot stage **1,415.78s**: **10 games × 10k**, **10k seasons / 952 remaining games**.
Log `/tmp/musnba_a1_availability_nightly_20261123.log`.

- Independent precision/accounting: **14.7M** minute values, **20.58M** phone marginals, **200k** team scores;
  marginal error 0, maximum team-quarter minute error **4.27e−14**. This is accounting, not accuracy.
- iCloud `MusNBA-laptop.musnba.gz` **111,413,527 bytes**; phone `MusNBA.musnba.gz` **86,886,931 bytes**.
  Each device imports manually; real phone import/memory acceptance remains unverified. No incremental streaming.
- Data-free Pages shell **fd367b9**, cache **d9ebff876348239a7a58**. Hosted import/offline **24/24 laptop,
  23/23 phone**; responsive interactions **13/13**, screenshots inspected; installed-shell upgrade **24/24**.
- Last code checkpoint smoke **108/108**, deliberate fault exited 1 (**86/108**). Production unchanged since then.

## Next actions

1. **Resume A1 at its 90% gate only when execution resumes.** Read [the branch runbook](docs/research/a1_branches.md)
   and [TRAINING §8](TRAINING_PLAN.md#8-a1-acceptance-and-reproducibility). Define representative historical
   pre-origin evidence or a materially new candidate before more runs; record hypothesis, population, actual
   versus inferred roster/report coverage, cutoffs, hashes, outcomes and stop rule. Reuse saved evidence;
   do not repeat selected stress tests as a route to promotion. Done when the next falsifiable test is frozen.
2. Measure representative failure/selection effects and independently audit legal fives, exact player/team/season
   accounting, restart and runtime. Historical actual-participant tests stay labelled conditional. Missing
   dated injury cohorts remain explicit; no protected-season outcome tuning. Keep current forecasts if a gate fails.
3. If qualified, wire complete 10k branches, exact Expected/season consumption and coherent laptop views;
   phone stays Expected-only. Validate precise minutes, selected/partial/empty conditions, origin provenance,
   responsive screenshots, import/offline and runtime. Finish A1 only with actual acceptance or a resolved,
   explicitly documented fallback. A blocked interim UI is not completion.
4. Update affected docs and evidence, run required checks, commit/push and summarise. **Honour the owner's
   stop at the A1 boundary; do not silently start A2/A3/Chunk B.** A fresh final nightly belongs at Chunk A end;
   affected model/output/app deliveries still occur at their own checkpoints.

First commands (read-only setup; do not launch old candidates):

```sh
git status --short --branch
git --no-pager log --oneline -5
.venv/bin/python scripts/smoke.py
.venv/bin/python scripts/check_docs.py
ls -t analysis/experiments/ | head -15
```

The baseline already passed for this docs-only checkpoint. No historical forecast backfill, extra provider,
model run or new nightly is authorised merely by cleaning docs.

## Progress ladders — Chunk A

Headliners: lineup-aware player/game distributions; form/late-game realism; five saved games and 2-D replay.
Dependencies/acceptance are in PLAN §6a; methods/gates belong to ENGINE/TRAINING. Ten cumulative rungs/module;
100 includes evidence, necessary delivery, checks, docs and commit/push. Report every new 10% module/5% overall mark.

```text
Chunk A  ███████░░░░░░░░░░░░░ 34.5%
A1       ████████████████░░░░ 80%
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
| 90 | **Open:** representative accounting, restart, cutoff, runtime, responsive gates. | Freeze promote/reject decision under all applicable gates. | Fresh live 10k nightly; audit selections and iCloud/PWA delivery. |
| 100 | Verify results/limitations, required delivery, commit/push. | Verify evidence/fallback/delivery, commit/push. | Publish shell; construct successor; checks, commit/push and summary. |

A1 10–80 are retained research milestones, not evidence that production gates passed. A2 40–100 and A3 all remain
open. Chunk B's full predeclared ladders and the original S01–S14 ladders are preserved in
[the frozen planning record](docs/archive/2026-11-23-before-lean/HANDOFF_NEXT.md); open only the relevant section
when preparing that chunk, and copy its current ladder here before execution.
