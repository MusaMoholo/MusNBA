# D56 — independent worlds and efficient scheduling

Owner (23 November) requires a shared queue of simulation work, including splitting a game's 10,000 worlds
across available workers. Ten total heavy threads remain the cap. Preserve complete forecasts; publish no
partial game and do not confuse worker count with Monte Carlo sample count.

## Independence defect

The legacy D29 `_fit_offsets` chooses one iteration for every table using the batch's maximum minute error.
One world can therefore change another's retained rotation. This is a code-level dependency, not evidence
that it explains particular histogram peaks or measured calibration gaps. Counts are intrinsically discrete.

An opt-in fitter applies precisely the existing single-world algorithm independently: same targets, curves,
step, 80-iteration limit and 0.4-minute tolerance; each world retains its own best iteration and stops at its
own tolerance. Require exact equality to separate legacy one-world fits, including regrouping/permutation,
and legal fives/240-minute accounting. Inspect other preparation steps for shared decisions before claiming
full independence. Fitted historical parameters shared across worlds are fixed inputs, not this defect.

## Qualification before default changes

Treat the fitter as a mechanical correction under promotion v2, not a learned minutes predictor. Reuse the
qualified Rule 3 corrected captures as controls after off-hook parity. Freeze 200 fresh F4 development IDs,
independent confirmation, stream and three 10k stress IDs before results. Require the unchanged 44 supported
core compatibility bounds, report 25 coverage diagnostics and block demonstrated harm; no invented primary
gain requirement. Only a qualifying frozen recipe receives its single protected evaluation. Runtime IDs and
the later clock protocol must distinguish each additional correction. Never retune on protected outcomes.

## Work queue and benchmarks

Schedule `(origin, game, lineup branch, chunk index, world range, seed)` work through a shared process queue.
Each worker takes the next unsimulated chunk; retain a canonical chunk layout/seed namespace independent of
worker count and completion order. Reassemble by world range, require exactly 10k unique complete worlds per
branch, and then form Expected and seasons. Missing/duplicate/failed chunks fail; no retry selection.

Benchmark 1k, 2.5k and 5k chunks against retained unsplit timing, plus eight versus ten workers where useful.
Measure single-game latency, whole-slate throughput, parent/worker CPU and memory, not utilisation alone.
Use at most ten compute threads, cap inner BLAS/OpenMP and avoid competing heavy jobs during timing arms.
Use legal, reconciled retained inputs, frozen IDs/seeds and raw output digests. Changing worker count/order
must reproduce identical chunks and merged arrays. Different chunk layouts use explicit different sampling
identities; they are not byte-identical legacy streams. Account independently for player/team/period scores,
minutes, availability, opening fives, exact Expected masses and season atoms. No model auto-promotion.

The completed r1 nightly remains retained; its exact 31 runtime/model files are archived under
`~/Basketball_archive_ops/qualified_r1_sources_20261123T1405`. No source or protected result is overwritten.
