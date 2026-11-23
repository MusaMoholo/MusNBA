# Handoff — next executable chunk

Updated 23 November 2026. Previous checkpoint **5560d6b**; `git log -1` identifies this planning checkpoint.
Read [AGENTS](AGENTS.md), this file and [PLAN](PLAN.md); [MODEL](MODEL.md) owns methods/evidence, [README](README.md) commands/app.

## State

- **A1/A2 complete.** Accepted **engine-v1.3-r3**, unchanged v1.3 nodes, independent D29 minutes/rotations,
  Rule 3 foul-outs, pool 0, ten-worker canonical 1k queue; pathway v1 starts tomorrow. No heavy jobs running.
- Last delivered generation **2026-11-23T21:53:15Z**: 10 games/15×10k branches, 150k worlds; full pipeline≤1610.4s.
  Smoke 108/108; both hosted PWA imports pass. Detailed accounting/checks: `analysis/experiments/20261123_r3_{integrated_delivery,live_accounting,season_accounting}_v1.json`.
- iCloud bundles **213,682,423B laptop  / 110,595,723B phone**; both still need manual device import.
  Shell31317f88/cache318fb2858f9d58651de0 unchanged. Real-device acceptance remains unverified.
- R3 improves supported late timing, with small overall score regressions; no calibrated form factor. The 400-game
  development audit finds high totals/narrow bench PTS ranges; oracle rosters cannot establish live DNP overuse.
  Old S06 merits a current-baseline retest, not automatic promotion. MODEL records all limits/evidence.
- Original programme 74%; D42 Chunk A 65% (A1/A2 complete,A3 open), B0. **New Chunk C 0%** is a separate execution ledger.
  No original weight/status resets. This turn plans only: production, forecasts and bundles stay unchanged.

## Execution trigger and first actions

The owner's next **“go with the next chunk”** means execute **all of Chunk C below**, beginning C1, through final delivery
and commit/push. It lifts the previous A1/A2 stop for this scope; do not ask for another routine planning approval.
This integrated plan supersedes the standalone D54 interlude. D54 remains first; A3 and targeted B1 work follow inside C.

1. Run the commands below. Confirm smoke passes; preserve current outputs and existing protected results.
2. Start C1 rung 10: trace actual queue/export boundaries, reproduce interrupted publication/failure handling on retained
   ordinary and branched games, then freeze schema/tests. No new fetch/model jobs are needed for that first inspection.
3. Before model compute, freeze the bounded experiment manifest in MODEL's contract: sources, safe inputs/fits, exact IDs,
   recipe/variant cap, primary claims, explicit v3, reuse/parity, exclusions, streams/stress, stopping rules and cost estimate from pilots.
4. Complete/checkpoint each module before its dependent module. Keep this ledger/current jobs updated; completed detail goes
   to aggregate experiment JSON/Git, without adding narrative docs. Stop after C4 and construct its successor at 0%.

```sh
git status --short --branch
git --no-pager log --oneline -3
.venv/bin/python scripts/smoke.py
.venv/bin/python scripts/check_docs.py
rg -n 'completed|yield|export|snapshot' scripts/live_forecast.py scripts/nightly.py scripts/nightly_musnba.py scripts/export_musnba.py
rg -n 'zone|location|MU_SHOT' scripts/engine.py scripts/nodes.py scripts/features.py
```

## Chunk C — believable player games you can inspect

**Headliners:** better shot opportunities/conversion and minutes decisions; a useful on-court PWA view of real saved worlds,
with checked games arriving before the slate finishes. Target meaningful improvements, never promise a model promotion.
Dependencies: qualified r3/retained raw worlds, permitted ESPN/NBA sources, cutoff-safe folds, precise weighted branches,
local PWA/importer and ten-thread budget. No full-repo rewrite, season retune, history backfill or new provider.

```text
Chunk C  ░░░░░░░░░░░░░░░░░░░░ 0%
C1       ░░░░░░░░░░░░░░░░░░░░ 0%  weight15%
C2       ░░░░░░░░░░░░░░░░░░░░ 0%  weight35%
C3       ░░░░░░░░░░░░░░░░░░░░ 0%  weight20%
C4       ░░░░░░░░░░░░░░░░░░░░ 0%  weight30%
```

Fixed sum: .15C1+.35C2+.20C3+.30C4. Every row is a cumulative done-when;100 includes evidence/docs/checks/commit/push.

| Rung | C1 early PWA delivery 15% | C2 court-aware shots 35% | C3 realistic rotations 20% | C4 View Centre/release 30% |
|---:|---|---|---|---|
| 10 | Trace completion/export; pin real fixtures and costs. | Audit existing zones, labels, source access and joins. | Recover exact S06 recipe/evidence; identify r3 interactions. | Freeze five-world selection, event schema and size budget. |
| 20 | Freeze complete-game/generation and interruption contracts. | Freeze versioned mapping, unknowns, exposure/pooling rules. | Freeze causal pre-event inputs and fold fits. | Select five real positive-mass worlds; record branch/chunk IDs. |
| 30 | Persist verified completions and bounded pending queue. | Build isolated prior-only shooter/defender zone profiles. | Port unchanged policy alongside independent r3 fitting. | Replay original full chunks with read-only event capture. |
| 40 | Fail promptly; cancel pending work and preserve completed chunks. | Audit counts/units/cutoffs and matched-data control parity. | Audit legal fives, seconds, foul-outs and state response. | Prove raw parity and reconcile events/boxes/clocks/minutes. |
| 50 | Resume rejects changed inputs; no duplicate worlds. | Fit at most 3 declared node variants versus control. | Run one paired 200-game development screen. | Ship court, event list, box and five example labels. |
| 60 | Publish checked game/Expected with explicit season freshness. | Pick at most 1 supported recipe; otherwise reject. | Grade MIN primary and all required proper/coverage checks. | Add play/pause/speed/seek/step, quarters and rotation timeline. |
| 70 | Export/import both profiles before remaining games finish. | Run one paired 200-game engine screen. | Separate uncertainty from harm; retain/reject without retuning. | Add zone attempts/makes, sample-aware player/defender comparisons. |
| 80 | Test interrupted exports/activation, legacy imports and offline. | Audit PTS, totals, tails, dependence and bench coverage. | Freeze survivor/removal contribution for combined testing. | Pass browser, keyboard, themes/widths and phone budget. |
| 90 | Fresh r3 nightly proves early import, exact worlds and≤60min. | Freeze survivor and broad-confirmation inputs for C4. | Validate provenance/replay; freeze independent checks for C4. | Confirm frozen survivors/removals; one protected final for qualifier. |
| 100 | Publish necessary shell/bundles; checkpoint results. | Research decision/source receipt; checkpoint, no early promotion. | Research decision/source receipt; checkpoint, no early promotion. | Fresh best-engine nightly, early exports/PWA audit, successor/checkpoint. |

## Dependencies, acceptance and stop rules

C1 precedes new output contracts. C2 and C3 use **r3 controls separately**, not each other's unqualified changes; share verified
controls and input work. C4 schema/UX work may overlap independent model compute after C1, within ten total heavy threads.
Two learned families only: zone shots and the existing S06 substitution recipe. No arbitrary form/variance multiplier,
zone-form model, decision-order search, new substitution family or extra rescue candidate. MODEL fixes the test budget.
A pure wiring/accounting repair can repeat an unchanged development recipe; it earns no predictive claim and never repeats a protected score.

- **C1:** a real complete 10k game with every required branch/Expected is importable in both new bundles before the last slate
  game finishes. Interrupted activation retains readable prior data or a detected recoverable partial pair; changed-input resume fails.
  Preserve original pre-tip forecasts, per-game model/generation and coherent season freshness. Measure compression inside the ten-thread cap.
  If unsafe/too costly, retain end-of-nightly export and deliver clear per-game progress/freshness; record D54 as blocked, not delivered.
- **C2/C3:** a measured negative or unsupported result closes that fixed attempt. No gain is assumed from better-looking zones or
  wider ranges. Source/roster/cutoff/comparator failures are setup failures, not rejection evidence. No blanket bench-minute cut.
- **C4:** five honest selected examples/game, reconciled event court/score/box/rotation playback plus useful zone insights;
  no invented tracking, passes or trajectories. If event capture cannot reproduce worlds, ship stored period/rotation/zone exploration
  and record A3 replay incomplete. Phone retains compact supported tools; oversized playback stays laptop-only with a clear explanation.
- Model release needs the frozen player-first benefits/compatibility, independent evidence and one final test; retain r3 on failure.
  UX still ships on accepted r3 if no model improves. C4's final full nightly uses authorised fetch/rebuild, 10k worlds/branch and fresh season;
  both imports/offline/upgrades, inspected 1440/960/390/both themes, dynamic labels, accounting and data-free shell publication when changed.
  Tip-crossing games retain original forecasts honestly. No data/models/bundles on Pages; no CI or device-import claim.

## Records and completion accounting

Use `analysis/experiments/20261123_chunk_c_plan_v1.json` for this plan's source/rationale; execution creates a new dated
frozen run manifest and immutable receipts. Fits/rows/worlds stay ignored under `data/`; scratch elsewhere, replacements archived externally.
Every checkpoint updates these same five docs. Count progress from accepted rungs, report 10% module/5% chunk boundaries and measured job rates.
D54 completes only with actual early publication; A3 only with full replay acceptance. B1/S11/S12/S14 receive no automatic completion credit;
season calibration, full programme integration and historical replay remain outside this chunk. No execution jobs were launched by this plan.
