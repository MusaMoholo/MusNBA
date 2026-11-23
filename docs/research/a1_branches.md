# A1 branches — research runbook

Current status: **90% release review under D51; production branches unshipped**.
[Completion decision](a1_no_release_20261123.md) records failed/unpassed gates. Read [HANDOFF](../../HANDOFF_NEXT.md) for the next action and
[TRAINING](../../TRAINING_PLAN.md#8-a1-acceptance-and-reproducibility) for gates. This file locates work already
done; it does not authorise repeating old candidates or promoting a partial implementation.

## What exists

| Component | Files / boundary |
|---|---|
| Selection/IDs/weights | `scripts/a1_lineup_branches.py`; D46 full-roster top-three offensive proxy, one uncertainty/team. D47 quarter-scaling is a candidate. |
| Legal-five repair | `scripts/a1_branch_foul_out.py`, `a1_branch_world_probe.py`; opt-in, world-local mask, fail on insufficient eligible players; not NBA short-roster exception support. |
| Stored branches/Expected | `scripts/a1_branch_persist.py`, `a1_expected.py`; exact weighted empirical distributions/provenance, isolated captures only. |
| Season mixture | `scripts/a1_season_mixture.py`, `analysis/a1_season_mixture_audit.py`, `a1_season_dependence.py`; common-interval weighted paths, no duplicated games, not accepted joint dependence. |
| Laptop browser/summary source | `analysis/a1_branch_browser_fixture.py`, `a1_branch_world_source.mjs`, `a1_branch_game_summary.mjs`, `a1_game_view_contract.mjs`; private injected source, no normal route registers it. |
| Phone research payload | `analysis/a1_expected_payload.mjs`, `a1_research_bundle.py`; Expected-only serialization, not production branch delivery. |
| Weighted/precise helpers | `scripts/webapp/weighted-worlds.mjs`, `precise-minutes.mjs`; exact mass/threshold mechanics shared with research. Production precise unconditional minutes shipped separately. |
| Retry coordinator | `scripts/a1_world_retry.py`, `analysis/a1_parallel_world_retry.py`, `a1_real_retry_{paired,scale}.py`; typed local exhaustion only, capped/persisted attempts, unwired. |
| Matched penalty candidate | `analysis/a1_vector_matched_penalty.py`, `a1_vector_penalty_backtest.py` and auditors; fixed F4 screen rejected. |

The full historical command/file map is in [archived README](../archive/2026-11-23-before-lean/README.md).
Inspect `--help` or source before a runner; many completed experiments fingerprint exact historical source.

## Evidence to reuse

Reports live under `analysis/experiments/`; ignored captures under `data/derived/experiments/`.

| Question | Retained reports |
|---|---|
| Baseline/confirmation IDs, seeds, floors and hashes | `20261122_a1_{manifest,pre_candidate_manifest,production_baseline}.json`; S01 source `c6d5db4`. |
| Exact branch mixture / partial season coupling | `20261122_chunk_a_a1_d47_season_{coupling,dependence,audit}_17_provenance.json`; prefer `_provenance`, older `_mixed/_bounded/_labelled` predate final helper hashes. |
| Branch captures/browser fixtures | `20261122_a1_live_branch_034_v1.json` capture manifest, `20261122_a1_live_branch_034_fixture_v1.json` browser fixture (ignored). Original four-branch captures have exact minutes; legacy production worlds do not. |
| Earlier-fold exhaustion | `20261122_a1_dated_f{1,2,3}_screen_v*.json`, matched continuation and saved-screen selection audits; conditional/oracle rosters, not dated injury cohorts. |
| 10k real retry stress and resume | `20261123_a1_retry_scale_{full_v1,full_v1_audit,resume_compare_v1}.json`; one selected synthetic six-player case. |
| Rejected real-outcome repair | `20261123_a1_vector_penalty_f4_200_v1{,_audit,_compare,_gate,_pooled_audit}.json`; no qualifying primary gain. |
| Current precise-minute slate | `20261123_a1_live_slate_minutes_audit_v1.json`; unconditional production accounting, not branch acceptance. |

## Remaining acceptance

Freeze a **new falsifiable hypothesis or representative pre-origin evidence** before more runs. A new cohort
must state official versus inferred rosters/reports and fit/input dates. Actual participants plus synthetic
plays/sits remain conditional research; protected-season outcomes are not selection data. No dated development
injury-report cohort currently supports calibration. Fixed, labelled scenario assumptions remain permitted.

Account for each rejected world and any conditioning effect, compare predictive outcomes with matched controls,
and preserve exact legal-five/player/team/Expected/season identities. Do not retry unknown/input/cutoff/accounting
errors or disguise a systemic roster problem. Independent streams differ from production vector streams;
shared vector RNG diverges after changed events. Passing a selected stress case proves neither a population
failure rate nor representative runtime. The failed vector repair is not rerun unchanged.

Season path expansion has a research 200,000-path cap before coupled arrays; this is not a full memory guarantee.
The 17-game coupling prototype branched only two games; it is not complete D31 production integration. D50 now
requires today's possession games only. Validate current source/origin before reusing any old research context.

## Read-only reproduction examples

Use new output paths and original source/capture hashes. These audits inspect existing captures; they do not
generate replacement forecasts. An interrupted world directory is retained, never overwritten.

```sh
.venv/bin/python analysis/a1_vector_penalty_backtest_audit.py analysis/experiments/20261123_a1_vector_penalty_f4_200_v1.json --output /tmp/a1-vector-penalty-audit.json
.venv/bin/python analysis/a1_production_minutes_audit.py data/derived/experiments/20261122_a1_live_branch_034_v1.json --output /tmp/a1-production-minute-audit.json
node tests/test_a1_precise_minutes.mjs
.venv/bin/python -m unittest tests.test_a1_minute_encoding_probe
```

For retry-scale generation, clean-stop/resume and exact old commands, consult archived HANDOFF's “Next actions”
and corresponding report fingerprints, then freeze a fresh namespace. Resume supports one operator and a
contiguous independently replayed complete prefix; orphan/partial batches fail for inspection. Do not call it
hard-kill-safe or run the full rejected screen merely to recreate an old report.
