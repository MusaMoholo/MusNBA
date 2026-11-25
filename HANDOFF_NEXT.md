# Handoff — C01 benchmark delivered; connected diagnosis next

Updated 25 November 2026. C01 conditional research benchmark complete; no production change, forecast refresh or app release. Incumbent: engine-v1.3-r3, its accepted rotations/foul/timing rules, report-bands-v1 availability and team-pathway-v1.
PWA/bundles unchanged. Owner 8766/review 8767 remain local servers; Git owns the checkpoint identity.

[PLAN](PLAN.md) is the new strategy; [MODEL](MODEL.md) defines evidence and limitations; [AGENTS](AGENTS.md) defines the new workflow.
Old roadmaps and the unstarted possession-fix plan are removed. Historical measurements/configurations remain evidence only.
No old task or future chunk is an obligation. The first chunk below is the sole detailed executable plan; its successors are conditional.

## Active chunk: C01 — rebuild measurement and locate the largest accuracy bottleneck

**Status: checkpoints 1–2 accepted; 50% of committed capability delivered. Production accuracy gain: none claimed.**

Accepted [contract](analysis/c01_contract_v1.json), [foundation](analysis/experiments/20261125_c01_checkpoint1_v1.json) and
[benchmark](analysis/experiments/20261125_c01_benchmark_v1.json). On 200 explored games, team-points CRPS (a distribution error in
points; lower is better) is 6.415 incumbent, 7.759 player-rate and 6.789 team-strength. The latter's extra error is .374 points,
95% whole-game interval .163–.586. Shared minutes and older baseline history limit architecture attribution. All 45,320 score rows
agree with independent arithmetic; serial/two-worker repeats agree. Twenty-seven targeted tests and 118/118 baseline checks pass.

Private namespaces: `data/derived/experiments/c01_accuracy_workbench_v2` and `data/derived/experiments/c01_benchmark_v1`.
No running jobs. All 200 games support official box accounting; 501/49,002 segments have actors outside recorded fives, requiring
row-level event support. Stored worlds lack zone counts. No historical operational population is certified.
Initial adapter v1 stays immutable; original dependencies are at `~/Basketball_archive_ops/20261125_c01_initial_adapter_v1`.
Continue directly through checkpoints 3–4; report accepted percentages and do not stop at another intermediate checkpoint.

Question: which observable/input/model failures create the largest recoverable player and team error, and how much value does
our complex generator add over credible simpler alternatives?

Committed advance: one repeatable, source-bound accuracy workbench with common scoring, competing baselines, connected event/game
diagnostics and an immutable prospective forecast ledger. An aggregate audit or a ranked list without working tools is insufficient.
No production model change is required or authorised by a diagnostic win. Do not begin by assuming `other`, long shots or any
previous favourite is the answer. Reuse prior source reconciliation and retained worlds instead of repeating them.

### Evidence and compute boundary

- Historical diagnostic panel: the exact 200 IDs in `analysis/experiments/20261124_b1_development_v2.json` → `game_ids`.
  They are known development games, not fresh validation. Hash IDs/receipts and enumerate all exclusions before new model scores.
  Reuse compatible incumbent captures from that study's control lineage; replay only for missing diagnostics/source compatibility.
- Fit each new baseline/auxiliary strictly before its evaluation origin, including opponent ratings, residual distributions,
  normalization, missing-value priors and any calibration. Training-only chronological selection; no panel-driven baseline tuning.
- Inventory earlier chronological folds for future confirmation, but do not select a production recipe on them in this chunk.
  Inventory prior exposure; do not open reserved confirmation/protected outcomes. No protected 2026–27 scoring or incumbent rescore.
- Keep separate populations for original pre-tip forecasts, causal hindcasts, actual-participant diagnostics and realised-input oracles.
  Historical operational support is measured, not assumed. Missing injury/roster publication evidence cannot be supplied by final participants.
- Use ≤10 total heavy threads with explicit inner caps; canonical 1k simulation chunks and deterministic seeds. Benchmark first.
  Start on 20 fixed games (first 20 of the frozen ID order) for wiring/noise, then all 200. Diagnostics use 1k worlds only where new
  generation is needed; reuse larger stored worlds fairly or use an explicitly common deterministic prefix. No broad parameter sweep.
- Initial namespace v1 is retained; active namespace v2 above also refuses overwrite. Aggregate completion receipt:
  `analysis/experiments/<actualETdate>_c01_workbench_v1.json`. Private row arrays/fits stay under data.

### Modular checkpoints — each commits, pushes and refreshes docs

Weights are 20/30/35/15; accepted checkpoints determine capability progress. Accuracy improvement is a separate measured result.
Dependencies are sequential; overlap independent source/fixture work and bounded fitting/I/O.

|Checkpoint|Weight|Concrete deliverables|Acceptance before its commit/push|
|---|---:|---|---|
|1. Truth and comparison contract — accepted|20%|Test inventory by failure mode/independence/cost; shared game/player/event schema; source/cutoff/exposure manifest; explicit definitions of possessions, periods, scoring and forecast populations; prospective numerical scoring/diagnostic contract|Known accounting cases cover ordinary games, OT, technical FT, DNP/unknown and broken clocks/IDs. Valid fixtures reconcile; deliberate corruption/leakage and known-bad forecasts fail for the intended reason. Map legacy tests to retain/replace/remove; replace their real coverage before removal. Record support and unsupported fields for all 200 games. Freeze baseline recipes and evaluation settings before scores.|
|2. Common benchmark and challengers — accepted|30%|Independent reference scorer and small deterministic unit/property suite; one runner/scorer for incumbent, a prior-only player-rate model with documented shared minutes input, and a regularised direct team-strength model with joint residual uncertainty; cached per-game/player outputs|Same IDs/origins/truth/metric semantics. Team baseline is team-only diagnostic; player baseline sums its own players. Self-comparison gives zero; perfect/known-bad forecasts and outside-support/missing-data cases score correctly. Repeated seeds/workers reproduce; independent calculation agrees; report 200-game support, simulation noise and wall time. All fit/residual inputs pass cutoff injection.|
|3. Connected error localisation|35%|Training/runtime feature parity on identical recorded history; observed-context next-event scoring versus free-running evaluation; per-player/team/context error budget; realised-input diagnostic adapters for minutes/on-court support and opportunity counts; distributions/joint checks|Source scoring identities remain exact. Oracle scope/estimand and unsupported cases are explicit; diagnostics are not live forecasts or additive causal attributions. Show how conclusions change across predeclared contexts and simulation noise. Reproduce on the wiring panel and complete the fixed 200-game analysis.|
|4. Repeatable operation and next decision|15%|Separate fast unit, source/integration, statistical and browser/release commands with explicit scope; one documented command recreates the comparison from pinned inputs; prospective ledger captures model/input/report/retrieval times and pre-tip provenance; ranked bottlenecks and next charter|An independent run reproduces aggregate conclusions; ledger never overwrites original forecasts, uses only truly captured pre-tip state, and fails closed on unknown timing. Select the next bottleneck with effect/support/cost/uncertainty and architecture alternatives. Deliver working tools and a concrete 0% successor; keep later plans provisional.|

Baseline recipes are frozen in the linked contract: shrunk player rates with shared incumbent minutes; ridge team strength with
paired chronological residuals. All new training/auxiliary outcomes stop at 31 December 2025 to avoid reserved outcomes. Disclose
that age restriction versus the incumbent's later prior-feature history; a difference cannot alone identify the value of architecture.
Neither comparator invents play-by-play or claims independent minutes validation.

Checkpoint 3 explicitly covers opponent defence and shot zones: prior-strength-adjusted predicted versus observed scoring response,
zone attempt shares/conversion, turnovers, fouls and rebounds, with game-level uncertainty and support. Recheck MODEL's historical
defence diagnostic on the common panel; do not target a coefficient of 100% by decree. Controlled opponent/lineup swaps hold offence
and seeds fixed and test sensitivity only; real-game comparisons establish predictive value. Freeze these diagnostics at checkpoint 1.

Use MODEL’s common player/event/joint-team metrics and population/uncertainty definitions; means alone cannot establish skill.
The connected workbench and independently checked test architecture, not a copy of existing mean-component tables or a higher test count, are the acceptance targets. All test/gate designs may be replaced prospectively; existing green checks are not presumed sufficient.

### Failure routes and stopping

Unsupported historical operational inputs: deliver the conditional track and prospective capture with explicit source gaps/denominators;
no pre-tip skill claim. Unsupported oracle: implement/test the supported adapter and observable-context diagnosis; no fabricated result.
If uncertainty prevents ranking a bottleneck, run a predeclared precision extension on development data within measured limits;
otherwise choose the source/measurement capability that resolves the ambiguity. No invented winner, endless sweeps or unrelated UI fallback.
An incomplete workbench remains incomplete. No model-promotion, season-tuning or cosmetic redesign in C01.

### First actions and release boundary

Checkpoint 3 first actions: use the pinned benchmark; implement source-bound observed-context prediction/parity, realised-input
adapters and connected defence/zone/joint error analysis in new modules. Preserve completed source dependencies before any
replacement. Existing signatures must never silently accept changed code. Source verification uses all four thread caps:

```sh
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
.venv/bin/python -m unittest discover -s tests -p 'test_c01_*.py'
.venv/bin/python analysis/c01_workbench.py verify
.venv/bin/python scripts/check_docs.py
```

Benchmark stages `analysis/c01_benchmark.py prepare`, `wiring`, `development`, `verify` have completed in order; their immutable
receipts refuse overwrite. Do not rerun them in place. Keep foundation `verify` repeatable. Start diagnosis on the first 20 IDs,
then all 200; no reserved/protected outcome reads or panel tuning. Production remains unchanged throughout isolated research.
Pure research checkpoints need targeted tests/fault injection/accounting, not a production nightly. A generation/provenance hook
change must pass integration checks and one fresh full release nightly at chunk end, before it becomes live:
`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -u scripts/nightly_musnba.py --engine 10000 --sims 10000`.
That means authorised online fetch/rebuild, current ET-day 10k worlds/branch, fresh season, ≤3600 seconds, independent accounting,
full smoke/fault and affected bundles. PWA assets publish only if actually changed. No UI change is planned.
