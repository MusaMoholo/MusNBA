# Start here — working on MusNBA

You are picking up a project mid-flight. Assume nothing from memory; the repository docs are the source of truth.
At every checkpoint the next session may be a different agent, so leave the docs so that it can continue without you.

## 1. Read in this order

1. **This file** — rules, owner preferences, checkpoint protocol.
2. **[HANDOFF_NEXT.md](HANDOFF_NEXT.md)** — the current state and the exact next actions. Start working from there.
3. **[PLAN.md](PLAN.md)** — goal, phases, milestone table (§6), open owner decisions, log.
4. **[ENGINE_PLAN.md](ENGINE_PLAN.md)** — engine design and the owner's decisions D1–D22. Do not reopen a decision
   without new evidence; if evidence contradicts one, say so to the owner and record it.
5. **[TRAINING_PLAN.md](TRAINING_PLAN.md)** — models, inputs, decay, folds, experiment protocol.
6. **[FINDINGS.md](FINDINGS.md)** — measured facts and data quirks. Do not re-derive them; extend them.
7. [DASHBOARD_PLAN.md](DASHBOARD_PLAN.md) (app behaviour) and [README.md](README.md) (commands) as needed.

## 2. First actions in a new session

```sh
git status && git log --oneline -5      # clean tree expected; the last commit is the last checkpoint
.venv/bin/python scripts/smoke.py        # must pass (73+ checks) before you change anything
ls analysis/experiments/                 # latest experiment logs: what was last measured
```

Then do the first open item in HANDOFF_NEXT.md § Next actions. If smoke fails, fix or report that first.

## 3. The owner and how to work with them

- Wants the most accurate model possible, built bottom-up from possessions; trusts measured evidence over intuition
  and is happy to be told an idea is wrong when data shows it.
- Wants rich data, but every input must earn its place by ablation on the folds.
- Keep **PLAN.md detailed and current**; report progress in short, plain bullets with real numbers.
- Develops on **localhost** (`.venv/bin/python scripts/serve.py`, :8766 — the owner runs it; never stop it, use
  :8767 for your own checks). The PWA build is for the phone later.
- UK-based; displayed times are UK with ET alongside. Slates are US Eastern dates.
- Prefers you make engineering decisions yourself and explain them; ask only for real product choices (PLAN §9).
- **The product is two engines in one daily flow (ENGINE_PLAN D26, PLAN §1):** the play-by-play engine for today's and
  tomorrow's games (or the next slate), with inputs carried over from every game before the date, then a MusSim-style
  team engine for every later game — per-world offensive/defensive ratings updated after each simulated game, so
  March is played from each world's own path, never today's ratings. **Every chunk of work has one or two headliners**
  that move these engines toward a state he trusts against real outcomes, each with clear ideas of what comes next;
  smoke, docs and plumbing ride along. Open each chunk by stating your understanding and the headliners.
- **Every chunk ends with the dashboard on the newest, best systems** (owner, 20 Nov): rerun the nightly so today's and
  tomorrow's games and a fresh 10,000-world season come from the latest engines that passed their tests. A chunk always
  brings new findings; when it cannot improve an engine (negative results happen), its headliner is a dashboard
  improvement from the owner's UX backlog (PLAN §9b) instead.
- Likes short status bullets with real numbers. For multi-step work he wants a **visual progress board** — an overall
  bar for the chunk plus a bar per subtask (text bars, e.g. `██████░░░░░░░░░░░░░░ 30%`) — **printed in the reply whenever a subtask reaches a new 10% mark or the chunk a new 5% mark**
  (owner, 20 Nov; finished jobs dropped from per-job bars). He sets explicit stop points mid-session ("stop when X is done") —
  finish X, checkpoint, and leave the rest to HANDOFF. He is happy to see new data in the dashboard before it is
  validated, if labelled.
- His goal (20 Nov): **a ground-up simulation as accurate as possible against real outcomes** — not betting. He checks
  projections against bookmaker lines; the market is a reference, not the target (ENGINE_PLAN D8): judge every change on
  real results, use market gaps as signals to investigate, never fit to lines. (Measured: DraftKings' closing lines are
  unbiased against 2026-27 results, FINDINGS §3m — so today's gaps are ours.)

## 4. Rules

- Use `.venv/bin/python`. Dependencies: NumPy, pandas, pyarrow, LightGBM. Node is optional (browser checks only).
- **The engine is the floor (D22)**: today's and tomorrow's projections (D24) come from the possession engine — model
  **v1.1** since D23 (`ENGINE['version']` in `scripts/engine.py`, `models/v1.1.json`). Replace it
  (new nodes, settings, rules or model version) only when the measured tests say the change is better — paired fold
  comparisons (`scripts/compare.py`), M6a (`scripts/aggregate.py`) and, once built, the M9 backtest — and record it.
- **Serving never computes**: `serve.py`, `views.py` and the PWA never fetch, fit or simulate.
- **Cutoff safety**: anything for a game on date D uses only games before D. Retrospective snapshots stay labelled.
- **Final test stays untouched**: the 2026-27 season (from 2026-07-01) is scored once per model version, at
  promotion — never for choosing features, decay or hyperparameters. Choices use folds F1–F4 (`scripts/evaluate.py`).
- **Log every experiment** (`analysis/experiments/`), and record wins *and* negative results in FINDINGS.
- Raw data is never modified; archive outside the repo (`~/Basketball_archive_ops`) before replacing snapshots,
  shells or bundles. Deterministic simulations: re-running identical inputs must reproduce stored results.
- Missing data stays missing; never clamp; placeholders are labelled in the app.
- NBA Stats/CDN with browser-imitating headers only if the owner authorises it (PLAN §9). ESPN requests stay polite.
- **Git (owner's standing instruction, 19 Nov 2026): commit and push at every checkpoint** — see §5 step 7. The repo is
  private, `MusaMoholo/MusNBA`, branch `main`. Its local git config carries the owner's personal identity (MusaMoholo,
  GitHub no-reply email) and a personal credential helper: never use the global identity, never change these
  settings, never force-push or rewrite history. Data, the virtualenv and exports stay out of git (`.gitignore`);
  check `git status` before committing and never add secrets or `data/`.

## 5. Checkpoint protocol — do this at the end of every milestone or work session

Write as if you will not be the one to continue.

1. **HANDOFF_NEXT.md**: rewrite *State* (what exists, what is running, what changed) and *Next actions* (numbered,
   concrete, with commands and done-when criteria). Remove anything stale.
2. **PLAN.md**: milestone table status (§6), phase bar (§5), a dated log line with the key numbers.
3. **FINDINGS.md**: every new measured fact, data quirk and negative result, with the population it was measured on.
4. **ENGINE_PLAN / TRAINING_PLAN**: record any new owner decision (next D-number) or design change, with the reason.
5. **README / HANDOFF file map**: new scripts, outputs and commands.
6. Run `.venv/bin/python scripts/smoke.py`; add a smoke check for every new output with an accounting identity, and
   confirm `--fault` still fails.
7. **Dashboard on the newest systems**: `.venv/bin/python scripts/nightly.py` (or `--offline --no-rebuild` when nothing
   new was collected) so the slates and the 10k season come from the latest promoted engines; browser checks on :8767.
8. **Commit and push**: `git add -A && git status` (review: no `data/`, no secrets), then
   `git commit -m "<milestone>: <what changed, key numbers>"` and `git push`. One commit per checkpoint at least; record
   the commit in HANDOFF_NEXT.md's header on the next checkpoint. Follow any commit-trailer rules your harness gives.
9. Tell the owner, in a few bullets, what changed, what was measured and what is next.

## 6. Conventions worth knowing

- Game time: periods 720 s (OT 300 s); elapsed game time t = 0–2880 in regulation.
- Segments: a possession can have several (offensive rebounds and defensive fouls without free throws continue it).
- Candidate nodes (player choices): one row per player on the floor, softmax within the segment, temperature fitted
  on the latest 10% of the training window.
- Shot coordinates: raw feet with the basket at (25, 0); zones rim ≤ 4 ft, paint |x−25| ≤ 8 and y ≤ 19, corner 3
  |x−25| ≥ 21.8 and y ≤ 14.
- App conventions (bezel, periods, MM:SS, spreads as projected margins): DASHBOARD_PLAN.md.
