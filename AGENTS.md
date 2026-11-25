# Working on MusNBA

We inherited a working NBA simulation product. Improve its predictive skill and reliability through evidence-led chunks.
The operating plan starts here; previous roadmaps and unfinished tasks have no authority.

## Start and canonical homes

Read [HANDOFF_NEXT](HANDOFF_NEXT.md), [PLAN](PLAN.md), relevant [MODEL](MODEL.md) sections and [README](README.md).
These five core docs are the live handover: rules here, current executable charter in HANDOFF, strategy in PLAN,
model/evaluation contracts in MODEL, user behaviour/commands in README. Replace stale text; do not append session diaries.

```sh
git status --short --branch
git --no-pager log --oneline -5
.venv/bin/python scripts/smoke.py
ls -t analysis/experiments/ | head -15
```

Baseline smoke must pass before changes (currently 118 checks). C01 may replace the test entry points/scopes after validation;
command names and counts are not sacred. Honour planning-only requests and explicit stops.
Historical receipts, configurations and qualification contracts are evidence, never a backlog. Read only what the task needs.

## Product and judgment

- Primary outcome: more accurate, calibrated player and team forecasts from coherent play-by-play worlds.
  Judge player minutes/performance and joint team outcomes together. Real results are truth; market lines are diagnostic references.
- Architecture, data preparation, learners, labels, metrics, tests, gates and workflow are all reviewable.
  The existing architecture is an incumbent, not a requirement. Simple baselines and alternative coherent models must compete fairly.
  Do not spend chunks on a plausible mechanism without evidence of material recoverable error.
- Accuracy gains cannot be guaranteed. Every charter must precommit a substantial reusable accuracy capability as well as a bounded
  modelling decision. Cosmetic UI work cannot compensate for a failed model. Knowledge alone cannot fulfil a promised capability.
- Keep one main bottleneck in progress. Evidence determines the next chunk; later directions stay provisional.
  Make routine choices independently. Ask only for genuine product/source decisions unavailable in connected evidence.

## Chunks and checkpoints

Only the next chunk is executable and detailed. HANDOFF must specify its question, committed deliverables, evidence boundaries,
3–5 modular checkpoints, dependencies, acceptance, failure route, compute limits and exact first actions.
Checkpoint weights total 100%; report accepted deliverables separately from accuracy gains. No inherited overall percentage,
artificial ten-rung ladders or acceptance credit for launching jobs. Print progress at accepted checkpoints and long-job milestones.
Estimate time only from measured logs.

Each checkpoint: relevant tests/accounting, refresh affected canonical docs, inspect staged changes, commit and push before dependent work.
Session stops checkpoint resumable commands, log/session/namespace, completed counts, blockers and the exact next action.
At chunk closure: state skill change, capability delivered, limitations and model/release status; replace HANDOFF with the next
concrete 0% charter. PLAN keeps only conditional future directions. If neither promised outcome is earned, the chunk is unfinished.

## Evidence and safety

- Use `.venv/bin/python` and the existing NumPy/pandas/pyarrow/LightGBM stack; Node for browser checks.
- Follow MODEL's truth, population, cutoff and evaluation-exposure contracts. Freeze candidate recipes, primary benefit,
  practical harm/support limits, multiplicity and stopping before outcomes. Old explored games never become fresh tests.
  C01 accesses no reserved/protected outcomes. New splits/policies are prospective; no result rescue by changed criteria.
- Legal clocks/fives/fouls, scoring/minute identities, exact weights and deterministic worker/resume behaviour are invariants.
  No fabricated tracking/truth, market fitting, final-score offsets/clamps or unsupported variance inflation.
- Raw responses and completed evidence namespaces are immutable. Store aggregate evidence in `analysis/experiments/`; private fits,
  row arrays/worlds stay ignored under `data/`. Preserve replaced outputs/dependencies at `~/Basketball_archive_ops` before replacement.
- ESPN/sportsdataverse/NBA Stats are authorised. New providers require owner sign-off. No forbidden scraping.
  NBA Stats uses one polite resumable retained-manifest stream, about one request/second; pause history during nightly fetching.
- Serving reads stored results: no collection, fitting, simulation or reconstruction while browsing.

## Proportionate validation and delivery

Docs-only: baseline smoke and docs checks; no model/data jobs or app publication.
Isolated research: targeted tests, cutoff/noise checks and independent accounting appropriate to the changed component;
keep production unchanged. Do not rerun/export unchanged production as a ritual after each failed experiment.
Code/data safeguards must include a deliberate meaningful fault check at the affected validation boundary.

A production model/input/generation change needs the prospectively frozen release evidence, affected forecasts/views/bundles,
full smoke/fault/accounting, and one fresh full online nightly at release: required rebuild, current ET-day 10k worlds/branch and
fresh season worlds on accepted engines. Existing full-nightly ceiling is 3600 seconds; benchmark rather than promise runtimes.
`--offline --no-rebuild` needs recorded unchanged-input justification. Cache reuse alone is not fresh generation.
UI changes need relevant browser checks; changed assets publish the tested data-free PWA shell. Avoid unrelated UI scope.

Current delivery is a PWA: laptop is primary/full worlds, phone is stripped. Platform choices can be revisited for measured user benefit;
no platform rewrite is planned in C01. Both devices import manually; desktop automation/iCloud exports do not
prove real-device acceptance. Keep boxes/insights first, controls grouped, secondary detail expandable; comparable cards 3/2/1 across.
Inspect touched pages at 1440/960/390 in both themes with screenshots. Counts/versions come from data. Sort meaningful table columns
without corrupting groups, axes, exact keys or missingness. UK times with ET alongside; slate dates are ET.
Owner server 8766 stays running; use 8767 for review.

Run `scripts/check_docs.py`; preserve link/word/file/archive checks. Keep docs live and lean at every commit, with one home per fact.
Review `git add -A`/status for data/secrets. Public repo `MusaMoholo/MusNBA`, main: existing personal identity/helper, no force-push,
history rewrite, repository CI workflows, secrets/data/exports on main or data on Pages. Report commit/push and manual-import needs.

## Compute

Use up to ten total heavy threads on the 14-core/48 GiB Mac; leave headroom and reduce under memory pressure.
Identify independent compute/I/O first. Count workers × inner threads across simultaneous fitting/compression/validation jobs.
Keep queues occupied, overlap safe I/O, detach long logs and preserve canonical seeds/chunk grouping. No agent delegation is implied.
`train.py --threads`; `backtest.py --jobs 10` gives one OMP thread/worker, `--jobs 5` two; default four gives twelve and exceeds budget.
Cap BLAS separately, avoid nested pools/OMP, and wait for pool shutdown before large parent work. Scratch stays outside the repo;
resumable evidence stays locatable in HANDOFF. Reuse audited artifacts without reusing purportedly untouched outcomes.
