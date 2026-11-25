# Working on MusNBA

The repository is the handover. Keep current decisions, evidence and exact next actions here, independent of chat history.

## Start

Read this file, [HANDOFF_NEXT](HANDOFF_NEXT.md), then [PLAN](PLAN.md). Read relevant sections of
[MODEL](MODEL.md) for design/tests/evidence and [README](README.md) for commands/app behaviour.
These are the five core docs. Completed history is in the verified archive described in README; never load it by default.

```sh
git status --short --branch
git --no-pager log --oneline -5
.venv/bin/python scripts/smoke.py
ls -t analysis/experiments/ | head -15
```

Smoke must pass before changes (118 checks at this checkpoint). Follow HANDOFF's first open action.
Planning-only requests stay planning-only; honour explicit stops. Read-only/docs work needs no review server.

## Owner and product

- **Players first (D28):** accurate minutes and per-possession performance against defenders should produce accurate team sums.
  Judge player tiers before team outcomes. Fit to real results; market lines are diagnostic references.
- Make routine engineering choices independently; ask for genuine product/source choices. Keep updates short, with measured numbers.
- Each chunk has one or two model/product headliners. A measured negative result can close research; an unfinished investigation cannot.
  If no model improves, deliver a useful dashboard improvement. Record important knowledge in the docs.
- **PWA only (D45/D53):** laptop is primary/full worlds; phone is stripped. App changes require tested/published shell assets and
  needed bundles. Both devices import manually; an iCloud export proves neither import nor real-device acceptance.
- Keep boxes/insights first, controls grouped, secondary detail expandable. Comparable cards: three/two/one across.
  Inspect touched pages at 1440/960/390 in both themes, including screenshots. Dynamic numbers/versions come from data.
  Make meaningful table columns sortable; preserve group/axis semantics, exact keys and missingness.
- UK times with ET alongside; slate dates are ET. Owner's server:8766 must remain running; use:8767 for review.
- Audit stale scorer rules and simplify proven duplication. Distinguish demonstrated harm, imprecision and unsupported data.
  Preserve realistic probabilities/uncertainty; do not reject an idea because its experiment setup failed.

## Scope and progress

Before executing a multi-step chunk, HANDOFF must have dependencies, weights totalling 100%, ten concrete 10% rungs/module,
acceptance/fallback, first commands and final nightly. Progress is the fixed weighted sum. Use chunk ledgers only; the owner retired the unfinished S-item queue on25 November2026.
Print overall/active-module bars at every new 10% module or 5% overall boundary; report long-job counts at each 10%.
Estimate time only from measured logs. Launched work earns no acceptance credit. Construct a fully specified 0% successor at closure.

## Safeguards

- Use `.venv/bin/python`; existing NumPy/pandas/pyarrow/LightGBM stack, Node for browser checks.
- Accepted runtime/limits live in HANDOFF/MODEL. Production changes need frozen, class-appropriate evidence under an **explicit**
  versioned policy. Preserve old results and sources; never move criteria just to pass a known candidate.
- Serving (`serve.py`, `views.py`, PWA) only reads stored results. Never fetch, fit, simulate or reconstruct while browsing.
- All inputs **and fitted auxiliary parameters** for origin D precede ET D. Missing data stays missing; no fabricated/clamped truth or tracking.
- Protected 2026–27 test from 2026-07-01 is once per frozen recipe at promotion, never feature/parameter selection.
- Log positive/negative experiments in `analysis/experiments/`; per-row arrays/fits remain ignored under `data/`.
  Identical inputs/seeds reproduce results independently of worker assignment. Do not overwrite immutable reports/namespaces.
- Raw responses are immutable. Archive replaced snapshots/views/bundles/shells and inventoried dependencies outside the repo at
  `~/Basketball_archive_ops` before replacement/removal.
- ESPN/sportsdataverse/NBA Stats are authorised; new providers require owner sign-off. No forbidden scraping.
  NBA Stats: one polite resumable stream, about 1 request/s, retained raw manifest; pause history during nightly fetching.
- D40 defers historical forecast backfill; rebuilding prior-game inputs is required. D50: possession engine today, pathway tomorrow onward.
- Public repo `MusaMoholo/MusNBA`, main. Preserve local personal identity/helper; no force-push/history rewrite.
  Never commit data/secrets/exports or publish them to Pages. **No repository CI workflows (D52).** Pages hosts the data-free shell.

## Every checkpoint

Complete each chunk module with its own checkpoint before starting the next. Session stops also checkpoint resumable state.

1. Review all five core docs. Update affected state/scope/design/evidence/behaviour/commands before committing; avoid repeated review narratives.
   HANDOFF owns exact running command/session/log/namespace, resume rules, blockers and next actions.
2. Code/data: smoke, deliberate `--fault` failure, independent accounting and relevant model/browser/PWA checks.
   Docs-only: baseline smoke and docs checks; launch no model/data jobs for tidying.
3. Promoted model/output changes refresh affected forecasts/views/bundles; changed app assets publish the data-free shell.
   Verify dynamic model labels, import, legacy compatibility and offline use. Research-only checkpoints say production is unchanged.
4. Each actual development chunk ends with a **fresh full nightly**, authorised fetch/required rebuild, today's10k worlds/branch
   and fresh 10k season simulations on accepted engines. `--offline --no-rebuild` requires recorded current/unchanged-input justification.
5. Run `scripts/check_docs.py`. Review `git add -A`/status for data/secrets, commit and push using existing identity.
6. Report changes, measured result/limits, model/PWA impact, manual-import requirement, commit/push and next action.

Keep docs lean **in file count and words at every commit**. Replace stale state; each fact has one canonical home.
Use aggregate experiment JSON and Git history rather than new narrative files per run. Preserve frozen contracts/history in the verified archive.
The local pre-commit hook enforces links, live file/word budgets and archive hashes. Fresh clones: inspect existing hooks before
`git config --local core.hooksPath .githooks`. Raise a budget only with a documented need.

## Compute

Actively use up to **ten total heavy compute threads** on the 14-core/48 GiB Mac; leave headroom and reduce under memory pressure.
For every task, identify independent compute/I/O first. Count process workers × inner threads across simultaneous jobs, including fitting/compression.
Keep shared queues occupied; parallelise independent work and overlap I/O;
use detached logs for long jobs. No agent delegation is implied by CPU parallelism.

Verify actual controls: `train.py --threads`; `backtest.py --jobs 10` gives one OMP thread/worker, `--jobs 5` two,
default four gives twelve and exceeds budget. Cap BLAS separately. Avoid nested pools/OMP; parent large-array work follows pool shutdown.
Canonical 1k world chunks keep the shared queue occupied even for one remaining game. Preserve world independence, seeds and exact grouping.
Benchmark new workloads; old runtime estimates are not promises. Scratch lives outside the repo; resumable evidence stays locatable in HANDOFF.
