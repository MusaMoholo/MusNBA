# Start here — working on MusNBA

You are picking up a project mid-flight. Assume nothing from memory; the repository docs are the source of truth.
At every checkpoint the next session may be a different agent — any model, any tool or environment — so leave the docs so
that it can continue without you. Never leave knowledge only in a chat, a private memory or a tool's notes: if it matters
for the next session, it goes in these files.

## 1. Read in this order

1. **This file** — rules, owner preferences, checkpoint protocol.
2. **[HANDOFF_NEXT.md](HANDOFF_NEXT.md)** — the current state and the exact next actions. Start working from there.
3. **[PLAN.md](PLAN.md)** — goal, phases, milestone table (§6), open owner decisions, log.
4. **[ENGINE_PLAN.md](ENGINE_PLAN.md)** — engine design and the owner's decisions D1–D43. Do not reopen a decision
   without new evidence; if evidence contradicts one, say so to the owner and record it.
5. **[TRAINING_PLAN.md](TRAINING_PLAN.md)** — models, inputs, decay, folds, experiment protocol.
6. **[FINDINGS.md](FINDINGS.md)** — measured facts and data quirks. Do not re-derive them; extend them.
7. [DASHBOARD_PLAN.md](DASHBOARD_PLAN.md) (app behaviour) and [README.md](README.md) (commands) as needed.

## 2. First actions in a new session

```sh
git status && git --no-pager log --oneline -5  # clean tree expected; the last commit is the last checkpoint
.venv/bin/python scripts/smoke.py        # must pass (108 at latest 22 Nov checkpoint; count grows) before changes
ls analysis/experiments/                 # latest experiment logs: what was last measured
```

Then do the first open item in HANDOFF_NEXT.md § Next actions. If smoke fails, fix or report that first.
A planning-only request stays planning-only. **Overnight A1 execution (owner, 22 Nov):** the prior planning-only
stop was lifted for that run, but the owner subsequently stopped execution after the nightly (D41). Remaining work
was future work until requested; the owner has since authorised the two D42 chunks in order. When executing an authorised
chunk, make in-scope engineering and product decisions without waiting; document assumptions and blockers. Model
gates, source permissions, cutoffs and data retention remain mandatory.
Read-only/docs work needs no review server; start :8767 when inspecting or changing presentation.

## 3. The owner and how to work with them

- Wants the most accurate model possible, built bottom-up from possessions; trusts measured evidence over intuition
  and is happy to be told an idea is wrong when data shows it.
- Wants rich data, but every input must earn its place by ablation on the folds.
- Keep **PLAN.md detailed and current**; report progress in short, plain bullets with real numbers.
- Develops on **localhost** (`.venv/bin/python scripts/serve.py`, :8766 — the owner runs it; never stop it, use
  :8767 for your own checks). The laptop PWA is the primary app (D45); its full saved-world bundle is
  `MusNBA-laptop.musnba.gz`. The phone uses the stripped `MusNBA.musnba.gz`. The public shell is live at
  https://musamoholo.github.io/MusNBA/; each device must import its own iCloud bundle. Real-device acceptance
  remains an owner check. Keep necessary PWA updates with model/app work.
- UK-based; displayed times are UK with ET alongside. Slates are US Eastern dates.
- Prefers you make engineering decisions yourself and explain them; ask only for real product choices (PLAN §9).
- **Guiding light (owner, 20 Nov, D28): players first.** The play-by-play engine exists to show how individual players
  perform; a team's results are the aggregation of its players. Get minutes and per-possession performance (against the
  defenders actually faced) right and team results, short and long term, follow. Judge engine work on player outcomes
  first, then on the team sums.
- **The product is two engines in one daily flow (ENGINE_PLAN D26, D50):** the play-by-play engine for today's games
  only, with inputs carried over from every game before the date, then a MusSim-style team engine from tomorrow onward
  — per-world offensive/defensive ratings updated after each simulated game, so
  March is played from each world's own path, never today's ratings. **Every chunk of work has one or two headliners**
  that move these engines toward a state he trusts against real outcomes, each with clear ideas of what comes next;
  smoke, docs and plumbing ride along. Open each chunk by stating your understanding and the headliners.
- **Every chunk ends with the dashboard on the newest, best systems** (owner, 20 Nov): rerun the nightly so today's
  games and a fresh 10,000-world season come from the latest engines that passed their tests. A chunk always
  brings new findings; when it cannot improve an engine (negative results happen), its headliner is a dashboard
  improvement from the owner's UX backlog (PLAN §9b) instead.
- **Larger modular chunks (owner, 22 Nov, D38):** A1 replaces the old four tasks with 14 weighted subtasks. Each
  completed subtask gets a high-level summary (what changed/was added, measured outcome, limitations, next action),
  current docs and a **commit and push** under the standing Git rule. A measured negative result is valid; unfinished
  research is not completion. Preserve resumable state at partial-session stops. Every development chunk ends by
  **constructing the next chunk in these docs in the same format**: headliners, dependencies, weights totalling 100%,
  ten concrete rungs per subtask, acceptance/fallback, first commands and a final live nightly. Docs are the source
  of truth for any next agent; no important knowledge lives only in chat or private memory.
- **History deferred (owner, 22 Nov, D40):** do not backfill historical forecasts or build a season-to-date replay
  for this A1 run; focus the nightly on today relative to its ET origin (D50). Rebuilding
  model inputs from completed games before the origin is still required and is not a forecast backfill. Preserve
  existing forecasts and archives. D39/ENGINE_PLAN §17 remains the safety contract if replay is reauthorised:
  historical inputs **and fitted parameters** must precede the origin, reconstructions must be labelled, versions
  must not be silently mixed, serving never recomputes, and the final test stays protected.
- **Two future chunks (D42):** the remaining A1 work is planned in HANDOFF with independent chunk weights/ladders,
  without resetting the original A1 ledger. Each chunk ends with a fresh nightly and a useful dashboard improvement
  if no model promotes; selected real simulated games must be labelled and reconciled, not invented.
- **View Centre (D43):** plan one event-based 2-D court/player for saved simulation worlds and, later, resulted games.
  Keep sources and spatial precision explicit; no invented player tracking or simulation during browsing.
- **PWA at relevant checkpoints (owner, 22 Nov):** a promoted model, changed forecast/bundle contract or shipped app
  change includes the necessary refreshed outputs and iCloud export, dynamic model/version metadata, import/offline
  checks and a data-free `gh-pages` shell update if assets changed. Do this at the affected subtask, not only at the
  final chunk. Research-only checkpoints explicitly record that the served model/bundle remains unchanged. A new
  bundle on iCloud is not proof either device imported it: report that manual import is needed. Never publish models,
  raw data or simulation bundles to Pages. S14 repeats final integrated delivery after the last nightly.
- **Dashboard taste (owner, 20 Nov):** he cares about player and team game-outcome presentation (scenarios, joint and
  conditional outcomes, deltas v averages); internal evaluation pages (the Lab) are not a priority. His examples are
  illustrations — generalise the idea rather than building only the example. He wants it **smooth and sleek at full width
  (1440), half width (960) and phone (390)**, both themes, with grouped and stacked controls; he often sends UX requests
  mid-chunk — do them alongside the headliners, run `node analysis/browser_check.mjs --base http://127.0.0.1:8767` on every
  touched page and look at the screenshots (a pass only means no errors or overflow). Record every change in DASHBOARD_PLAN.
- **Card-grid preference (owner, 22 Nov):** comparable insight cards should come in multiples of three for full three-across desktop rows; adapt to two across at half width and one on phones.
- **Dynamic dashboard copy (owner, 22 Nov):** dates, sample sizes, simulation counts, model versions, results so far and qualification thresholds must come from the loaded data/configuration; fixed teaching examples must be labelled and never imply current measured values.
- Likes short status bullets with real numbers. For multi-step work he wants a **visual progress board** — an overall
  bar for the chunk plus a bar per subtask (text bars, e.g. `██████░░░░░░░░░░░░░░ 30%`) — **printed in the reply whenever a subtask reaches a new 10% mark or the chunk a new 5% mark**
  (owner, 20 Nov; finished jobs dropped from per-job bars). He is **critically dependent on these updates** (owner, 20 Nov,
  third reminder), so **plan for them before working**: at the chunk's opening, write each subtask as a **ladder of ten
  10% steps, each with a concrete done-when** (a background download counts per 10% of its items), give each subtask a
  weight so the chunk % is a fixed weighted sum, and put the ladders in HANDOFF_NEXT.md § Progress ladders. Between steps
  you then know which one you are on; post the board in your message to him right after the step that crosses a mark,
  also during long builds, background jobs and while answering his questions. Never jump past marks. **Time estimates
  come from measured rates** (a job's log: items done, seconds elapsed) and say so — he finds padded guesses unhelpful. He sets explicit stop points mid-session ("stop when X is done") —
  finish X, checkpoint, and leave the rest to HANDOFF. He is happy to see new data in the dashboard before it is
  validated, if labelled.
- His goal (20 Nov): **a ground-up simulation as accurate as possible against real outcomes** — not betting. He checks
  projections against bookmaker lines; the market is a reference, not the target (ENGINE_PLAN D8): judge every change on
  real results, use market gaps as signals to investigate, never fit to lines. (Measured: DraftKings' closing lines are
  unbiased against 2026-27 results, FINDINGS §3m — so today's gaps are ours.)

## 4. Rules

- Use `.venv/bin/python`. Dependencies: NumPy, pandas, pyarrow, LightGBM. Node is optional (browser checks only).
- **The engine is the floor (D22)**: today's projections (D50) come from the possession engine — model
  **v1.3** since D34 (`ENGINE` in `scripts/engine.py`: `version`, node `models`, `rotation`, `sims` 10,000, `pool` 0 — D36;
  `models/v1.3.json`; real-matchup candidates v1.4c/e/f not promoted, D37). Replace it
  (new nodes, settings, rules or model version) only when the measured tests say the change is better — paired fold
  comparisons (`scripts/compare.py`) and the M9 backtest on the same games (`scripts/backtest.py`,
  `scripts/backtest_compare.py`: player tiers first, D28, then team sums) — and record it.
- **Serving never computes**: `serve.py`, `views.py` and the PWA never fetch, fit or simulate. (The app's Scenarios and
  Given… views only slice the engine's stored worlds.)
- **Cutoff safety**: anything for a game on date D uses only games before D. Retrospective snapshots stay labelled.
- **Final test stays untouched**: the 2026-27 season (from 2026-07-01) is scored once per model version, at
  promotion — never for choosing features, decay or hyperparameters. Choices use folds F1–F4 (`scripts/evaluate.py`).
- **Log every experiment** (`analysis/experiments/`), and record wins *and* negative results in FINDINGS.
- Raw data is never modified; archive outside the repo (`~/Basketball_archive_ops`) before replacing snapshots,
  shells or bundles. Deterministic simulations: re-running identical inputs must reproduce stored results.
- Missing data stays missing; never clamp; placeholders are labelled in the app.
- NBA Stats API: **authorised by the owner (20 Nov, D32) and in use** — `scripts/fetch_nbastats.py` (Chrome fetch headers,
  ~1 request/s, one stream at a time, resumable, raw retention + manifest); pause the history download while the nightly
  fetches. No other new source without his sign-off. Never scrape a site whose terms forbid automated access (D33). ESPN
  requests stay polite.
- **Git (owner's standing instruction, 19 Nov 2026): commit and push at every checkpoint** — see §5 step 8. The repo is
  **public** (`MusaMoholo/MusNBA`, owner approved 22 Nov, matching MusSim), branch `main`; `gh-pages` publishes only the data-free shell. Its local git config carries the owner's personal identity (MusaMoholo,
  GitHub no-reply email) and a personal credential helper: never use the global identity, never change these
  settings, never force-push or rewrite history. Data, the virtualenv and exports stay out of git (`.gitignore`);
  check `git status` before committing and never add secrets or `data/`.

## 5. Checkpoint protocol — every completed subtask and work-session stop

Write as if you will not be the one to continue. Update documentation **before** the checkpoint commit, not as
an uncommitted afterthought. Review all eight root docs; edit affected ones and record why the others need no change.
HANDOFF owns the live ledger/next action; PLAN scope/status/log; ENGINE design/decisions; TRAINING tests/cutoffs;
FINDINGS measured evidence; DASHBOARD shipped behaviour; README runnable commands; this file standing rules.
Keep HANDOFF's first-screen summary and the active progress ladder current as evidence arrives; record exact
commands, logs, running jobs and blockers before a context/session stop. **Every completed subtask or D42 module
is its own checkpoint:** refresh affected docs and run its checks, then review, commit and push before starting the
next. Do not defer those updates to the end of the chunk or report an unfinished job as complete.

1. **HANDOFF_NEXT.md**: rewrite *State* (what exists, what is running, what changed) and *Next actions* (numbered,
   concrete, with commands and done-when criteria). Remove anything stale.
2. **PLAN.md**: milestone table status (§6), phase bar (§5), a dated log line with the key numbers.
3. **FINDINGS.md**: every new measured fact, data quirk and negative result, with the population it was measured on.
4. **ENGINE_PLAN / TRAINING_PLAN**: record any new owner decision (next D-number) or design change, with the reason.
5. **README / HANDOFF file map**: new scripts, outputs and commands.
6. At code/data checkpoints run `.venv/bin/python scripts/smoke.py`; add an independent accounting check for new
   outputs and confirm `--fault` still fails. Run relevant model/browser/PWA checks. For a documentation-only planning
   session, baseline smoke plus doc consistency/link checks suffice; do not launch data/model jobs to tidy docs.
7. **Delivery when affected, always at chunk end:** after a promoted model or changed stored-output contract, refresh
   the affected forecasts/views and export with `scripts/nightly_musnba.py` (or `--export-only` for already-current
   completed outputs). Validate the PWA bundle/model labels and publish a changed data-free shell; record generation,
   version, checks and phone import requirement. At the end of actual development always run a new full nightly:
   today and 10k seasons on the latest accepted engines. `--offline --no-rebuild` is only for
   current, unchanged retained inputs, with the reason recorded; never bypass required feature rebuilds. Browser
   checks use :8767. Research-only subtasks need no repeated live nightly; the planning-only session starts none.
8. **Commit and push**: `git add -A && git status` (review: no `data/`, no secrets), then
   `git commit -m "<milestone>: <what changed, key numbers>"` and `git push`. One commit per checkpoint at least; record
   the commit in HANDOFF_NEXT.md's header on the next checkpoint. If your environment asks for commit trailers or
   attribution lines, add them; never change the repo's git identity.
9. Tell the owner, in a few bullets, what changed/was added, what was measured, model/PWA impact, commit/push status
   and what is next. At the final chunk checkpoint, first archive its completed progress and construct the successor
   chunk at 0% in HANDOFF/PLAN with the same full format. Do not end with an unstructured backlog.

## 6. Running long jobs (any environment)

**Interactive compute budget (owner, 22 Nov):** on the owner's 14-core Mac (10 performance + 4 efficiency
cores, 48 GiB RAM), use at most **10 compute workers/threads in total** across concurrent heavy jobs, leaving
approximately four cores' worth of capacity for ordinary use. This is a conservative budget, not CPU affinity:
macOS decides scheduling and responsiveness is not guaranteed. Reduce the budget if the machine is busy,
memory pressure or swapping rises, or the owner needs more headroom. Apply it to simulation, research,
training and other CPU-heavy work; choose fewer workers when benchmarks favour them. Count process workers
times their inner compute threads, plus concurrent jobs; prevent nested OpenMP/BLAS oversubscription. Verify
each tool's actual controls rather than assuming environment variables win: `train.py --threads` controls
LightGBM, and `backtest.py --jobs` sets `OMP_NUM_THREADS` internally from CPU count. On this 14-core Mac,
`--jobs 5` (two OpenMP threads per worker) or `--jobs 10` (one each) stays within the 10-thread budget;
the default `--jobs 4` implies 12 OpenMP threads. Also cap fitting with `--threads 10` or less and BLAS
threads separately. Document any explicitly authorised brief above-budget comparison and do not run it
alongside other heavy jobs. Respect existing model gates and deterministic-input requirements.

**Use the budget actively (owner, 23 Nov):** make the most of the available cores: aim to keep the
10-thread compute allowance occupied whenever useful independent work is ready. Parallelise heavy work
across processes, within a job, or across independent jobs as measured throughput and memory permit;
overlap independent I/O and checks asynchronously and keep long jobs detached with logs. This applies to
all heavy compute, not only simulations. Benchmark new workloads briefly and reuse measured worker choices;
do not leave work serial by default or assume ten processes beat fewer multithreaded workers. Keep the
combined process-times-inner-thread count within ten, respect dependencies/provider limits and reduce
concurrency for memory pressure or the owner's use. This does not authorise additional modelling scope.

Long jobs run detached with a log, e.g. `nohup .venv/bin/python -u scripts/backtest.py … > /tmp/bt.log 2>&1 &`, and you read
the log's progress lines (`game N/200 Ts`, `engine <id>: …`) to report measured pace. Measured on the owner's laptop
(14 cores, 48 GB): a 200-game backtest alone ≈ 22–27 min (two at once oversubscribe the CPU — each worker predicts on every
core — and both take ~50 min); fitting 16 fold models ≈ 5 min; a node-dataset build ≈ 1–2 min and ~20 GB RAM; the nightly
≈ 4 min of input rebuild + ~2 min per game at 10,000 worlds (≈ 30 min for 15 games). The NBA Stats history download is
one polite stream (~1 request/s); pause it (it resumes) while the nightly fetches. Scratch files go outside the repo (a
temp folder); experiment logs go to `analysis/experiments/` (committed) and their per-row data to `data/derived/experiments/`.

## 7. Conventions worth knowing

- Sibling project: the owner's **MusSim** football app (`../Football`, public github.com/MusaMoholo/MusSim) — MusNBA copies
  its conventions (laptop pipeline + data-free static PWA, bundle import, serving never computes, raw retention, cutoff-safe
  snapshots, deterministic sims, colour tokens, 1440/960/390 checks in both themes).

- Game time: periods 720 s (OT 300 s); elapsed game time t = 0–2880 in regulation.
- Segments: a possession can have several (offensive rebounds and defensive fouls without free throws continue it).
- Candidate nodes (player choices): one row per player on the floor, softmax within the segment, temperature fitted
  on the latest 10% of the training window.
- Shot coordinates: raw feet with the basket at (25, 0); zones rim ≤ 4 ft, paint |x−25| ≤ 8 and y ≤ 19, corner 3
  |x−25| ≥ 21.8 and y ≤ 14.
- App conventions (bezel, periods, MM:SS, spreads as projected margins): DASHBOARD_PLAN.md.
