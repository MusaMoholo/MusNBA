# Handoff — current state and next actions

Updated **23 November 2026**. Previous pushed checkpoint: **d11ac5f**; `git log -1` identifies this checkpoint.
Read [AGENTS](AGENTS.md), then this file and [PLAN](PLAN.md). Detailed history is indexed in
[docs/README](docs/README.md); do not read archives as current instructions.

## State

- **Published/iCloud:** qualified **engine-v1.3-r1** (Rule3, unchanged v1.3 nodes), D29 targets/pool0;
  10k worlds per branch and team-pathway-v1 10k seasons. Public shell31317f8/cache318fb2858f9d58651de0.
  Lineups/photos are delivered; each device must refresh its shell and manually import its own iCloud bundle.
- **Scope:** original 14-task A1 programme **64.0%** (S01–S08 complete, S13 deferred). Separate D42
  **Chunk A 48.0%** = A1 lineups **90% (reopened D51)** × 30% + A2 form **60%** × 35% + A3 replay **0%** × 35%.
  Chunk B **0%**. Do not reset/double-credit the original ledger; see PLAN §6.
- **D56:** independent fitter corrects a reproduced batch-wide fit decision; protected v2 result42/44,
  with two unresolved star-cohort bias bounds. All27 proper-score checks pass. Independent reconstruction
  confirms arithmetic; a general counterexample exposes a cohort-bias veto conflicting with individual error.
  [V3 policy](docs/protocols/promotion_v3_20261123.md) is frozen after known results, with a fresh200 F4
  confirmation required. Original final remains unchanged, never repeated. Candidate fitter/queue stay off.
- **A1:** qualified r1 lineups, exact Expected, photos and phone CDFs are published. Availability weights
  remain assumptions; historical prior-roster coverage is limited. Fresh nightly/delivery checkpoint pending.
- **A2 60%:** contextual late-clock candidate passed frozen F1–F3 and separate F4 analytical screens against
  legacy and clean-bridge controls; 600 empirical distributions independently audited. No engine integration
  yet. Shared shooting has no confirmed missing pooled scoring covariance; pace/minute gaps remain separate.
- **Execution authorised:** finish A1/A2 only; A3/B and historical forecast backfill remain outside this
  session. Startup smoke108/108 and baseline focused checks passed. Current checks/jobs are below;
  measured earlier pilots and rule evidence belong in FINDINGS §7 and linked reports.
- **D52:** repository Actions workflows removed; checks run locally through `.githooks`. Pages hosts only
  the data-free shell. Do not reintroduce CI.

## Latest published PWA delivery

- Fresh r1 generation **2026-11-23T16:43:38Z**: fetch63 requests/0failures, rebuild156.3s through22Nov;
  snapshot1,465.33s,10 games/15×10k batches. Season80,337 weighted paths/mass100k/952 games.
  Exact weighted refinement preserves all near-term atoms; this is not a claim of80k independent histories.
- Public shell **31317f88**, cache **318fb2858f9d58651de0**. Latest iCloud laptop~213.3MB/2,557 records;
  phone~107.5MB/2,827. Both exports complete. Each device must manually refresh/import its own file.
- Hosted **29/29 laptop,27/27 phone** on the final refreshed files; installed old bundle→new shell→new bundle **32/32**.
  Branch routes24/24 at1440/960/390/both themes inspected.
  Final replay smoke108/108; deliberate fault86/108, exit1.
  Delivery receipt: `analysis/experiments/20261123_a1_r1_delivery_v2.json`.

## Next actions

1. **S08/r1 delivery checkpoint complete:** receipt `20261123_a1_r1_delivery_v2.json`; public shell,
   current iCloud files, all10 live games/15batches,53,732 histogram checks, exact season atoms, hosted
   imports29/27, upgrade32, smoke108/108 and fault86/108 exit1. Full log
   `/tmp/musnba_a1_qualified_r1_delivery_nightly_20261123_v2.log`. No need to repeat completed checks.
   A1 remains90 while the additional D56 fitter/queue decision below is completed; no candidate default.
2. **Frozen v3 fresh confirmation:** initial12 pairs cleanly saved/audited; resumed session88301 with
   eight single-thread workers (replay checks now complete), clean stop after40 more pairs, log
   `/tmp/musnba_rotation_policy_confirmation_20261123_v2.log`. Manifest
   `20261123_rotation_policy_confirmation_manifest_v1.json`; source-frozen runner
   `analysis/rotation_policy_confirmation.py run --jobs 8 --resume --stop-after 40`.
   After clean stop, `run --jobs 10 --resume` (all other heavy checks are finished). In-worker independent audits
   count inside worker budget. Unseen200 F4 IDs; never repeat protected r2. Do not edit fingerprinted
   engine/model/input/gate/runner files while active. Need fresh27/27 proper bounds/no demonstrated
   coverage harm plus existing correctness/stream/stress/determinism. New evidence failure ends attempt.
   Preserve old42/44 protected outcome; no release from retrospective reclassification alone.
3. **A1 completion:** after the fixed fitter decision, record evidence/fallback and checkpoint before A2.
   Candidate r2, if qualified, still needs proper Engine hook/raw parity, retained replay/season checks,
   a fresh nightly and PWA export. r1's known coupled fitting remains a limitation until then. Old protected
   r2 result246pairs/284,432,368 legal fives is retained under `independent_rotation_final_20261123_v1*`.
4. **A2 after A1 checkpoint:** no clock engine outcome yet. The new prospective
   [development plan](docs/protocols/a2_clock_v3_development_20261123.md) freezes baseline selection from
   A1, explicit v3 checks and the original staged panels/pools/primary loss. Read original
   [stages](docs/protocols/a2_clock_engine_20261123.md) too. Reuse exact matching controls; finish staged
   compatibility/confirmation or measured fallback, then fresh full nightly/PWA/iCloud, docs, commit/push.
   Stop before A3/B. No arbitrary form factor, new source or historical forecast backfill.
5. **D54 successor:** complete10k per-game bundle publication/resume;
   [contract](docs/protocols/incremental_catchup.md). Nightly collects missed results and forecasts today.

First commands (do not duplicate jobs or alter source-frozen producers):

```sh
git status --short --branch
tail -n 8 /tmp/musnba_a1_qualified_r1_delivery_nightly_20261123_v2.log
tail -n 8 /tmp/musnba_rotation_policy_confirmation_20261123_v2.log
.venv/bin/python scripts/check_docs.py
```

Review :8767; owner :8766 must remain running. No A3, Chunk B, new provider or forecast backfill here.

## Progress ladders — Chunk A

Headliners: lineup-aware player/game distributions; form/late-game realism; five saved games and 2-D replay.
Dependencies/acceptance are in PLAN §6a; methods/gates belong to ENGINE/TRAINING. Ten cumulative rungs/module;
100 includes evidence, necessary delivery, checks, docs and commit/push. Report every new 10% module/5% overall mark.

```text
Chunk A  ██████████░░░░░░░░░░ 48.0%
A1       ██████████████████░░ 90% (D51 review)
A2       ████████████░░░░░░░░ 60%
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

A1's previous fallback was reopened by D51; 10–80 remain research milestones, not production passes. A2 70–100 and A3 all remain
open. Chunk B's full predeclared ladders and the original S01–S14 ladders are preserved in
[the frozen planning record](docs/archive/2026-11-23-before-lean/HANDOFF_NEXT.md); open only the relevant section
when preparing that chunk, and copy its current ladder here before execution.
