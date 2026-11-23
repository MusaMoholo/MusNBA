# Working on MusNBA

The repository is the handover. Keep enough current information for a new agent to continue without chat
history, while keeping startup reading short. Updated 23 November 2026.

## 1. Start here

1. Read this file, [HANDOFF_NEXT.md](HANDOFF_NEXT.md), then [PLAN.md](PLAN.md).
2. Read only the task-relevant parts of [ENGINE_PLAN.md](ENGINE_PLAN.md),
   [TRAINING_PLAN.md](TRAINING_PLAN.md), [FINDINGS.md](FINDINGS.md),
   [DASHBOARD_PLAN.md](DASHBOARD_PLAN.md) and [README.md](README.md).
3. Use [docs/README.md](docs/README.md) to find detailed protocols/history when needed. Do not load archives
   by default; their old state, commands and next actions are historical, not current instructions.

```sh
git status --short --branch
git --no-pager log --oneline -5
.venv/bin/python scripts/smoke.py
ls -t analysis/experiments/ | head -15
```

Baseline smoke must pass before changes (108 checks at the latest checkpoint). Start with HANDOFF's first
open action. Planning-only requests stay planning-only. Read-only/docs work needs no review server.
Authorised A1 work continues only within its recorded boundary; do not silently advance modules at a stop.

## 2. Owner preferences

- **Players first (D28):** minutes and per-possession performance against the actual defenders determine team
  outcomes. Judge player tiers before team sums. The goal is accuracy against real outcomes, not betting;
  bookmaker closing lines are a diagnostic reference, never a fitting target.
- Make in-scope engineering choices independently. Ask only for genuine product/source decisions. Record
  important assumptions/blockers in the appropriate document.
- Each development chunk has one or two engine/product headliners. A measured negative result is valid;
  unfinished research is not completion. If no engine improves, ship a useful dashboard improvement.
- Laptop PWA is primary; phone is stripped (D45). Serving and browsing read stored data only.
- Dashboard: smooth at 1440/960/390 in both themes; group controls and secondary detail. Comparable cards
  form rows of three, then two/one as width shrinks. Changing dates/counts/versions/thresholds come from data.
- UK display times with ET alongside; slate dates are ET. Keep the owner's server on :8766 running;
  use :8767 for review. Inspect screenshots, not just browser-check pass counts.
- Honour explicit stops. Current model/delivery/progress belongs in HANDOFF, never only in chat.

## 3. Progress and scope

Before a multi-step chunk, put weights totalling 100% and ten concrete 10% done-when rungs per module in
HANDOFF. Dependencies, acceptance/fallback, first commands and final live nightly must be clear. Progress is
the fixed weighted sum, not elapsed time. Original A1 and the D42 A/B chunk ledgers are separate; never double-count.

Print overall and active-module text bars immediately at every new 10% module rung and every 5% overall
boundary. Drop completed modules from displayed per-module bars, not from the denominator. Long jobs also
report completed items and measured throughput at each 10%; a launched job earns no acceptance rung.
Estimate durations only from measured logs, naming the population/rate.

## 4. Non-negotiable safeguards

- Use `.venv/bin/python`. Existing dependencies: NumPy, pandas, pyarrow, LightGBM; Node for browser checks.
- **Accepted floor:** possession engine v1.3, 10,000 worlds, D29 targets, rotation pool 0; team pathway v1.
  Change production models/settings/rules only through the frozen paired player-first gates in TRAINING_PLAN.
- **Serving never computes:** `serve.py`, `views.py` and PWA never fetch, fit or simulate; conditions slice saved worlds.
- Inputs and fitted auxiliary parameters for origin D precede ET D. Never silently use later reports/profiles.
- Final test is 2026–27 from 2026-07-01: once per frozen version at promotion, never for selection/tuning.
- Log every experiment under `analysis/experiments/`; per-row results stay ignored under `data/derived/experiments/`.
  Preserve negative results. Missing data stays missing; no invented/clamped outcomes or tracking.
- Raw responses are immutable. Archive replaced snapshots/views/bundles/shells outside the repo under
  `~/Basketball_archive_ops`. Never remove retained-run dependencies without an inventory and archive.
- ESPN, sportsdataverse history and NBA Stats are authorised. New providers need owner sign-off; no forbidden
  scraping. NBA Stats uses one polite stream (~1 request/s), raw manifests and resume; pause history for nightly fetches.
- S13 historical forecast backfill is deferred (D40). Pre-origin input rebuilds remain required. D50 uses today's
  possession games only, team pathway from tomorrow; preserve original forecasts and archives.
- Never publish data/models/bundles to Pages. No force-push, history rewrite or git identity/credential changes.

## 5. Every checkpoint: verify, update, commit and push

A completed S task/D42 module and every session stop gets its own checkpoint before the next module.

1. Update HANDOFF state/next action, affected scope/design/evidence/behaviour/commands, and any running job's
   exact command, PID/log, namespace and resume rule. Review all eight docs; edit only affected ones.
2. Run appropriate checks. Code/data: smoke, deliberate `--fault` must fail, independent accounting and relevant
   model/browser/PWA checks. Docs-only: baseline smoke and documentation checks suffice; start no model/data jobs.
3. Promoted models or changed outputs require affected refresh/export; app assets require data-free shell publication.
   Verify dynamic metadata, fresh import, legacy compatibility and offline use. Each affected subtask delivers;
   do not defer necessary PWA work to chunk end. Research-only checkpoints say production is unchanged.
4. Every actual development chunk ends with a fresh full nightly: authorised fetch, required input rebuild,
   today's 10k game worlds and 10k seasons on accepted systems. `--offline --no-rebuild` only with recorded
   current/unchanged-input justification. Docs-only/research-only checkpoints need no repeated nightly.
5. Review `git add -A` and `git status`: no `data/`, secrets, virtualenv or exports. Commit and push `main`
   (`MusaMoholo/MusNBA`, public) using existing local identity/helper. `gh-pages` holds only the shell.
6. Report concise changes, measured outcome, limitations, model/PWA impact, commit/push and next step.
   iCloud export never proves import: each device must import manually; real-device acceptance is the owner's check.
7. At final development-chunk closure, archive its finished ladder and construct the successor at 0% with
   headliners, dependencies, weights, ten rungs/module, acceptance/fallback, commands and a final nightly.

**Keep docs lean at every commit (owner, 23 Nov).** Replace stale state; do not prepend another mini-handoff.
Each fact has one canonical home (docs index). Completed work gets a short outcome + evidence link, with
long protocols/reproduction detail in `docs/`. Keep recent log entries only; link older history. Preserve
frozen decisions/protocols and evidence when condensing. Do not duplicate long logs, old commands, all-eight-doc
review narratives or progress boards across files. Run `.venv/bin/python scripts/check_docs.py` before committing;
word budgets are review gates, raised only with a recorded reason. History is consulted, not mandatory startup reading.

## 6. Use compute efficiently

On this 14-core Mac (10 performance + 4 efficiency, 48 GiB), actively use up to **10 total compute threads**
whenever useful work is ready. Count process workers × inner threads across all concurrent heavy jobs.
Parallelise independent work and overlap I/O/checks asynchronously; detach long jobs with logs. Reuse measured
worker choices; benchmark new workloads briefly. Reduce concurrency under memory pressure/competing use.
This is a scheduling budget, not CPU affinity or permission to expand scope.

Verify actual controls: LightGBM `train.py --threads`; `backtest.py --jobs` sets OMP internally. On this Mac,
`--jobs 5` means two OMP threads each, `--jobs 10` one each; default four implies twelve, over budget.
Cap BLAS separately. Do not run independent backtests concurrently unless their combined inner-thread count
and memory fit; sequential paired comparisons remain required. Existing vector-candidate timing favoured eight
single-thread workers, not proof ten is always faster. Above-budget runs need explicit owner authorisation.

Scratch goes outside the repo; resumable logs/results must be locatable from HANDOFF. Never use old runtime
estimates as a promise for new branches/mechanics. Sibling MusSim (`../Football`) provides PWA/UI conventions.
