# Handoff — current state and next actions

Updated **23 November 2026**. Previous pushed checkpoint: **22238f2**; `git log -1` identifies this checkpoint.
Read [AGENTS](AGENTS.md), then this file and [PLAN](PLAN.md). Detailed history is indexed in
[docs/README](docs/README.md); do not read archives as current instructions.

## State

- **Delivered:** engine-v1.3-r2 (unchanged v1.3 nodes), Rule3, D29 targets/pool0, row-local rotation fit;
  10k worlds/branch through canonical1k chunks on ten workers. Team-pathway-v1 starts tomorrow.
- **Scope/progress:** original14-task programme64% (S01–S08 complete; S13 deferred). D42 Chunk A
  **51%** = A1 **100%**×30% + A2 **60%**×35% + A3 **0%**×35%; B0. Finish A2 only, then stop.
- A1 outcomes/ten-rung ledger: [completed checkpoint](docs/checkpoints/2026-11-23-a1.md).
  [Release receipt](analysis/experiments/20261123_r2_release_v1.json). Fresh200 F4 establishes27/27
  proper bounds plus all bias/coverage diagnostics; original protected v2 42/44 preserved, never repeated.
  Post-result v3 revision is explicit; no universal player-accuracy or learned availability claim.
- **A2:** analytical contextual-clock screens/confirmation passed; no clock engine outcome yet. Shared
  shooting has no confirmed pooled missing PTS covariance, so no calibrated form factor was added.
- **No running compute jobs.** Last full nightly and final controller exited0; exact commands/logs below.
  Do not repeat completed A1 simulations. Review server:8767; never stop owner:8766. D52: no CI workflows.

## Latest published PWA delivery

- Origin23Nov, generation**2026-11-23T18:06:16Z**;63requests/0failures, required advanced rebuild231.9s.
  10games/15×10k batches; snapshot1184.0s. All53,732 histogram checks pass. Season80,337 weighted
  paths/mass100k/952games; every original near-term atom exact. No iid-season/calibration claim.
- Public data-free shell31317f88/cache318fb2858f9d58651de0 is unchanged. New iCloud laptop
  **215,095,062 bytes**, phone**110,224,058**. Both require manual device import; real-device acceptance
  is unverified. No incremental bundle publication yet. Assets support r2 through loaded metadata.
- Hosted final imports/offline**29/29 laptop,27/27 phone**; smoke**108/108**, fault**86/108/exit1**.
  Original asset delivery also passed installed upgrade32/32 and inspected normal-route24/24 at
  1440/960/390 in both themes. Live output/model/bundle contracts are verified; no further asset push needed.
- Receipts `20261123_r2_{integrated_delivery,live_accounting,season_accounting}_v1.json`.
  Logs `/tmp/musnba_a1_r2_world_queue_nightly_20261123_v1.log` and
  `/tmp/musnba_r2_delivery_{checks,smoke,fault,pwa_phone,pwa_laptop}_20261123_v1.log`.
  Live root `data/derived/live_runs/2026-11-23-1795455992573123000` retained for replay.

## Next actions

1. **A2 headliner:** test the frozen contextual late-clock correction in the engine against real outcomes.
   Use qualified r2 in both arms, reserve r3 for clock; no new form/variance factor or feature selection.
   Read [original engine stages](docs/protocols/a2_clock_engine_20261123.md) and the prospective
   [v3 development plan](docs/protocols/a2_clock_v3_development_20261123.md). Pools are already frozen
   under `data/derived/experiments/20261123_a2_late_clock_{screen,confirmation}_v1/F*_pools.json`;
   IDs in `20261123_a2_clock_engine_panels_v1.json`. Freeze driver/source/input/seed identities before results.
2. Add the optional hook after legacy last24s draws, using `ContextClock`; None must consume no draws.
   Prove hook-off parity on the three retained independent-fit pilots before a candidate. Reuse r2
   development controls from `independent_rotation_f4_20261123_v1`; simulate only the clock arm first.
   Conditional joint time/no-action loss is the frozen learned primary benefit, not an invented pooled
   PTS target. Explicit v3 engine compatibility:27 proper bounds; report17 bias/25 coverage, block
   demonstrated material coverage harm. All counts/uncertainty/unsupported groups remain explicit.
3. Only a survivor runs original100-per-fold F1–F3 dated/body-free controls, separate200 F4 confirmation,
   independent-stream30 and three10k stresses. Candidate/control share exact fitter/models/priors/seeds.
   Fresh r2 confirmation captures already supply the independent F4 baseline:
   `independent_rotation_policy_confirmation_20261123_v1` candidate outputs. Never regenerate matching
   controls for convenience. Use ten total compute threads, independent accounting inside that budget.
   No protected r3 evaluation until all required stages qualify; only once, no threshold/recipe rescue.
4. All12 archived/current input files are byte-identical after the rebuild; report
   `20261123_r2_profile_refresh_identity_v1.json`. Exact controls remain reusable after parity. Archive
   `/Users/moholom/Basketball_archive_ops/archive_20261123T174020Z_91228` remains backup; never restore
   over production. Frozen r2 confirmation source31-file archive is under
   `data/derived/experiments/independent_rotation_policy_confirmation_20261123_v1_sources/`.
5. Finish A2 with a measured accept/reject decision and limitations; required fresh full nightly on accepted
   engines, PWA/iCloud verification, eight-doc review, commit/push. If clock fails, retain accepted timing;
   do not add arbitrary variance. U23 outcome stories already provide A2's delivered player-facing improvement.
   Construct the D54 successor fully (weights/ten rungs/acceptance/commands/final nightly), then stop before
   A3/B/replay. [D54 contract](docs/protocols/incremental_catchup.md). No forecast backfill authorised.

First commands (A1 has finished; do not restart its jobs):

```sh
git status --short --branch
git --no-pager log --oneline -3
cat docs/protocols/a2_clock_v3_development_20261123.md
.venv/bin/python -m unittest tests.test_late_clock -v
.venv/bin/python scripts/check_docs.py
```

## Progress ladders — Chunk A

Headliners: lineup-aware player/game distributions; form/late-game realism; five saved games and 2-D replay.
Dependencies/acceptance are in PLAN §6a; methods/gates belong to ENGINE/TRAINING. Ten cumulative rungs/module;
100 includes evidence, necessary delivery, checks, docs and commit/push. Report every new 10% module/5% overall mark.

```text
Chunk A  ██████████░░░░░░░░░░ 51.0%
A2       ████████████░░░░░░░░ 60%
A3       ░░░░░░░░░░░░░░░░░░░░ 0%
```

| Rung | A2 form / late game (35%) | A3 View Centre / delivery (35%) |
|---:|---|---|
| 10 | Quantify residual covariance after roles/minutes. | Freeze five-world selection, schema, provenance, spatial/data budget. |
| 20 | Freeze prior-fold talent/form hypotheses and no-double-count controls. | Select each team's maximum margin and maximum individual fantasy worlds. |
| 30 | Isolated uncertainty draws preserve means/streams (synthetic only so far). | Select a real representative world using frozen multi-stat distance. |
| 40 | Test shared pace/shooting and dependence on folds. | Persist five labels; validate local files and invalid/future-source contracts. |
| 50 | Audit late fouls, clock, shot selection and OT by supported states. | Capture/replay exact original batch events without changing draws. |
| 60 | Test supported state corrections against earlier-fold controls. | Independently reconcile event order, clocks, scores, boxes and legal fives. |
| 70 | Sequential player-first screens: CRPS, bias, coverage, joint metrics. | Ship stored-only court, overlays, box, event list and playback controls. |
| 80 | Test survivors together and under independent seeds. | Check seek/playback/accessibility, themes/widths, phone budget/offline. |
| 90 | Freeze promote/reject decision under all applicable gates. | Fresh live 10k nightly; audit selections and iCloud/PWA delivery. |
| 100 | Verify evidence/fallback/delivery, commit/push. | Publish shell; construct successor; checks, commit/push and summary. |

A1 is complete; its ladder/outcome is archived above. A2 70–100 and A3 all remain open. Chunk B's full predeclared ladders and the original S01–S14 ladders are preserved in
[the frozen planning record](docs/archive/2026-11-23-before-lean/HANDOFF_NEXT.md); open only the relevant section
when preparing that chunk, and copy its current ladder here before execution.
