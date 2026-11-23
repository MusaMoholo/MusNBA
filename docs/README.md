# Documentation map

Read **AGENTS → HANDOFF → PLAN** at startup, then only the specialist sections needed for the task.
Do not load historical archives routinely. Root documents describe the present; linked reports preserve evidence.

| Canonical home | Keep here |
|---|---|
| [AGENTS](../AGENTS.md) | Owner preferences, safeguards, compute, checkpoint/documentation rules. |
| [HANDOFF](../HANDOFF_NEXT.md) | Current systems/delivery, blockers, jobs, exact next action and active progress ladders. |
| [PLAN](../PLAN.md) | Scope, dependencies, milestone ledger, completion criteria and product backlog. |
| [ENGINE_PLAN](../ENGINE_PLAN.md) | Current design, D1–D54 decision index, implemented/planned boundaries. |
| [TRAINING_PLAN](../TRAINING_PLAN.md) | Folds, cutoffs, frozen numerical gates, confirmation/release requirements. |
| [FINDINGS](../FINDINGS.md) | Concise measured conclusions and negative decisions, with population and report links. |
| [DASHBOARD_PLAN](../DASHBOARD_PLAN.md) | Current shipped UI, definitions, constraints and pending product contracts. |
| [README](../README.md) | Runnable setup/daily/export/check commands and compact code map. |

## Focused references

- [A1 branch runbook](research/a1_branches.md): current research components, retained outputs, remaining gate and safe reproduction.
- [A1 delivery design](protocols/lineup_delivery_20261123.md): original probabilities, stored selections, exact Expected/season and PWA boundaries.
- [A1 no-release decision](research/a1_no_release_20261123.md): measured prior-roster rejection and every unpassed production gate.
- [Active promotion v2](protocols/promotion_v2_20261123.md): D51 change classes, core margins, calibrated diagnostics and independent confirmation.
- [Rule-level final](protocols/rule3_final_20261123.md): fixed current-season adapter, dated fills/minutes and one formal protected evaluation.
- [Historical promotion v1](protocols/promotion_v1_20261122.md): verbatim original S01 gate, retained for old experiment reproduction.
- [Frozen A2 protocols](protocols/a2_form_20261122.md): verbatim preregistered residual/form methods.
- [A2 contextual clock](protocols/a2_late_clock_20261123.md): earlier-fold learned-clock screen, component removal and confirmation boundaries.
- [Incremental delivery/catch-up](protocols/incremental_catchup.md): immediate successor priority and proposed historical reconstruction boundary.
- [Cleanup audit](maintenance/2026-11-23-lean-docs.md): before/after counts, preservation checks and checkpoint validation.
- Experiment JSON/text under `analysis/experiments/` contains exact configurations, outcomes, uncertainty and fingerprints;
  arrays/captures remain ignored under `data/derived/experiments/`.

## Historical archive — consult selectively

[23 Nov pre-cleanup originals](archive/2026-11-23-before-lean/manifest.json), source commit `aa3d25d`.
All eight originals are preserved byte-for-byte with SHA-256/size/word/line counts. They contain superseded
instructions and stale states. Current root docs take precedence; the archive is evidence, not another handoff.

| Needed detail | Open only this reference |
|---|---|
| Original S01–S14 and future B1–B3 ten-step ladders; old run commands | [Archived HANDOFF](archive/2026-11-23-before-lean/HANDOFF_NEXT.md), corresponding named section. |
| Earlier scope, full milestone descriptions and dated log | [Archived PLAN](archive/2026-11-23-before-lean/PLAN.md). |
| Exact dated decision wording or deferred history safety design | [Archived ENGINE](archive/2026-11-23-before-lean/ENGINE_PLAN.md), decision row or §17. |
| Completed S02–S07 frozen experiment methods | [Archived TRAINING](archive/2026-11-23-before-lean/TRAINING_PLAN.md), named protocol in §8. |
| Older measurements, quirks, corrections and source fingerprints | [Archived FINDINGS](archive/2026-11-23-before-lean/FINDINGS.md), relevant task/date. |
| Old UI delivery notes or exhaustive research script map | [Archived DASHBOARD](archive/2026-11-23-before-lean/DASHBOARD_PLAN.md) / [archived README](archive/2026-11-23-before-lean/README.md). |

## Keep it lean at every commit

Replace current state rather than prepend another checkpoint narrative. Record a completed experiment once as
outcome, population, limitation, decision and evidence link. Put long methods/runbooks in a focused topic file;
keep only material recent log entries in PLAN. Archive completed ladders when activating a successor. Preserve
frozen protocols and never erase negative results. Link between canonical homes instead of copying paragraphs.

Run `.venv/bin/python scripts/check_docs.py` before committing. The stdlib-only checker enforces per-root and total
word budgets, focused-reference budgets, local links/anchors, fenced blocks and archive integrity. Its source owns
the budgets. A justified budget change needs a recorded reason, not an automatic increase when a file grows.
The local `.githooks/pre-commit` also runs it on every commit (enabled here via `core.hooksPath=.githooks`).
Fresh clones must inspect existing hooks before enabling it. D52 removes repository CI workflows;
checks stay local, while GitHub Pages continues serving the data-free `gh-pages` shell.
