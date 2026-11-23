# Handoff — current state and next actions

Updated **23 November 2026**. Previous pushed checkpoint: **d8ae76f**; `git log -1` identifies this checkpoint.
Read [AGENTS](AGENTS.md), then this file and [PLAN](PLAN.md). Detailed history is indexed in
[docs/README](docs/README.md); do not read archives as current instructions.

## State

- **Accepted production:** possession **engine-v1.3**, D29 minutes, pool 0, **10,000 worlds/game**;
  **team-pathway-v1**, **10,000 seasons**. Today's ET games use possessions; tomorrow onward uses pathway.
- **Scope:** original 14-task A1 programme **58.0%** (S01–S07 complete, S13 deferred). Separate D42
  **Chunk A 40.5%** = A1 lineups **100% (no release)** × 30% + A2 form **30%** × 35% + A3 replay **0%** × 35%.
  Chunk B **0%**. Do not reset/double-credit the original ledger; see PLAN §6.
- **A1 fallback decision complete; full branches remain unshipped.** The new 800-game pre-origin
  roster census supports 783 contexts; independent raw reconstruction checked 28,530 memberships.
  The historical readiness route failed; the frozen representative simulation was not run. The earlier
  vector repair still fails its primary accuracy gate. [Decision/unpassed gates](docs/research/a1_no_release_20261123.md).
  No branch selector/Expected mixture or retry policy is enabled. Original S08 remains 0%/undelivered;
  production keeps labelled participation slices. This is completion of the documented no-release fallback,
  not a claim that blocked production requirements passed.
- **A2:** residual-dependence diagnostics and a synthetic mean-preserving draw prototype exist. No fitted latent
  factor, engine wiring or accuracy gain; within-/cross-game residual evidence is inconclusive. No A2 promotion.
- **Execution authorised:** owner requests completion of A1 and A2 (23 Nov), lifting the prior A1 stop.
  A3/Chunk B are not part of this request. Startup smoke **108/108**, log
  `/tmp/musnba_a1_a2_start_smoke_20261123.log`. A1 checks: 8/8 focused, smoke 108/108; deliberate fault 86/108 and exit 1. No jobs running; production unchanged.
  Active A1 protocol: [prior-roster screen](docs/protocols/a1_prior_roster_20261123.md).
- Local pre-commit documentation enforcement is enabled (`core.hooksPath=.githooks`). Hosted documentation CI
  could not start because GitHub reports an account billing lock; this does not invalidate local checks.

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

1. **A2 40%:** freeze the shared-factor and accepted-control world-dependence/late-state estimands
   before measurement, using [frozen A2 methods](docs/protocols/a2_form_20261122.md). Reuse retained
   predictions/models; do not add uncalibrated variance or use the rejected A1 repair as the control.
2. Test shared shooting/pace support on prior folds and measure dependence already produced by v1.3.
   Audit late fouls, clock, shot mix and OT on matched historical states; report unsupported cases.
   Only separately supported/fitted factors or corrections get a frozen candidate engine screen.
3. Apply the unchanged player-first/noise/non-inferiority and confirmation gates to survivors, otherwise
   retain v1.3 with a measured no-promotion decision. Ship a useful outcome-facing dashboard improvement
   if no model qualifies, with responsive screenshots and required PWA checks/delivery.
4. Finish A2 with a fresh accepted-system live nightly (today's 10k games and 10k seasons), independent
   accounting, iCloud export and any changed data-free shell; update lean docs, commit/push and stop.
   A3/Chunk B remain open. Construct the next authorised work in the existing weighted format.

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
Chunk A  ████████░░░░░░░░░░░░ 40.5%
A1       ████████████████████ 100% (no-release fallback)
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
| 90 | **Rejected route:** input readiness failed; remaining production gates unpassed (decision linked above). | Freeze promote/reject decision under all applicable gates. | Fresh live 10k nightly; audit selections and iCloud/PWA delivery. |
| 100 | Verify results/limitations, required delivery, commit/push. | Verify evidence/fallback/delivery, commit/push. | Publish shell; construct successor; checks, commit/push and summary. |

A1 is closed on its documented no-release fallback; 10–80 remain research milestones, not production passes. A2 40–100 and A3 all remain
open. Chunk B's full predeclared ladders and the original S01–S14 ladders are preserved in
[the frozen planning record](docs/archive/2026-11-23-before-lean/HANDOFF_NEXT.md); open only the relevant section
when preparing that chunk, and copy its current ladder here before execution.
