# A1 delivery — implementation boundary

The D51 rule correction must qualify before becoming the default. Scenario controls themselves are a
stored-data/assumption change: structural correctness and honest assumptions, not a learned injury-model claim.
This records the integration design before new live branch outputs; it does not qualify old research fixtures.

## One source for Expected and each selection

Keep original status probabilities; D47 quarter remapping has not earned promotion. Select D46's at-most-one
top-three offensive-proxy uncertainty per team from the full roster. Forced availability precedes minute/
starter/matchup solving. Each exhaustive branch stores 10k complete worlds and the exact original independent
status-product weight. Retain missing/cold source provenance and all other uncertainty. No retry selection.

Expected uses every branch/world at its exact rational weight. A selection renormalises the compatible
branches; it never runs another simulation. Precompute the nine possible selections for two uncertainties
(four fixed, four single-player conditions, Expected), or three for one. Use these same summaries in the UI
and saved raw worlds in Given/joint tools. Persist player/team/period distributions, precise minute marginals,
availability, actual simulated opening shares and conditional-on-playing summaries. Expected must not present
one branch's minute target or opening five as certain. Unsupported games stay visibly unsupported.

Use the full Expected integer world masses even when filtering a selection; divide by their selected sum.
Backend histograms, conditional shooting denominators, raw-world tools and marginal CDFs then share the same
numerator units. Fully fixed cases can reuse a branch summary with every histogram/conditional count scaled
by that branch's per-world mass. Partial/Expected cases need the weighted packager. Put all precomputed cases
alongside laptop branch worlds under the existing `/api/game/<id>/worlds` record so phone stripping excludes
them together; its game record retains Expected and a separate weighted minute-CDF record only.

The backend's summary functions should gain optional exact integer masses while preserving the existing
unweighted code path. Distinguish **saved world count** from **probability-mass denominator**; histogram sums
and conditional shooting denominators use mass, displayed simulation counts use real worlds. All app areas
reading Expected—slate, game, leaders, roster, comparisons and season—must use its same source/generation.
An isolated game-page override is insufficient for full S08 acceptance.

Keep runtime component identity separate from the unchanged fitted-node version. Snapshot replay must use
its own recorded foul/clock rules and output ID, rather than today's global `ENGINE` ID; verify old and new
replay paths. Phone precise minutes use weighted marginal CDF schema 2 (exact support/cumulative integer mass),
not an invented ordering of independent marginal samples. Schema 1 remains readable. Split CDF records by
player and validate their source/world/mass identity against the game metadata. Measure byte shuffling before
delivery: the retained four-branch fixture's monolithic record is 86 MB JSON. Conditional/weighted payloads need
a bundle version/capability guard so old shells reject them safely; keep importing legacy version-1 bundles.

## Season consumption

Inspect/reuse `a1_season_mixture.couple` rather than assume it sorts branches contiguously: it independently
permutes all branch/world atoms and randomly offsets each game's interval. It preserves each game's complete
weighted marginal exactly. Independent offsets make the product distribution correct in expectation over
coupling seeds; any fixed finite coupling retains numerical cross-game dependence. Existing 32-seed diagnostics
cover only two branched games among 17 and do not prove realistic availability dependence.

Before adopting this route, measure the actual whole-slate path count, effective mass/ESS, time and memory,
check every marginal/conditional identity, and compare residual cross-game dependence with independent draws.
The prototype can expand beyond 10k paths and has a 200k-path guard. Never call expanded weighted paths 10k
equal-weight seasons, silently relax the cap or fall back to the original unconditional season. If expansion
is unacceptable, explicitly revise the season approximation contract using measured evidence before wiring;
do not claim that a sampled 10k subset equals the complete empirical mixture. Every near-term game is used
once and each future path updates its own ratings. Store weighted counts/denominator separately from paths.

23 Nov planning probe: original 70% probabilities select four one-player games among ten, hence **14** 10k
batches. Repeating existing unconditional score arrays only to test layout/runtime yields **84,212 weighted
paths**, denominator 100k, with every full joint score marginal exact. Pathway time **4.96s**, versus **0.40s**
for 10k unweighted paths, under concurrent evaluation load. This supports tractability, not branch accuracy or
final runtime acceptance; source/probe reports are `20261123_a1_live_branch_plan_v2.json` and
`20261123_a1_season_delivery_probe_v1.json` in experiments. Check the actual post-fetch slate again at delivery.

## PWA and acceptance

Laptop includes all supported saved branches and stored selection summaries. Phone includes Expected,
its honest assumption/provenance labels and precise marginals; no branch/joint tools or hidden world payload.
Normal routes register only source-verified stored providers. Generation changes invalidate cached providers;
rapid selection/navigation cannot render stale choices. Retain unaffected actual results and dated context;
hide or explicitly label summary panels that are not valid under the selected assumption.

The branch decoder is shared (`lineup-worlds.mjs`), with its old research import path re-exporting it.
Original 15% probabilities pass exact-weight tests. The browser research summary calculator stays in
`analysis/`; production reads precomputed cases. Normal routes do not register branches yet; these helpers
are no app/PWA delivery claim. Shell inventories include the decoder. Test original probabilities, corrupt/mismatched
sources, exact partial conditions, player/period/team/season identities, all touched pages at 1440/960/390
in both themes, import/offline/upgrade and the stripped phone profile. Inspect screenshots and disclose any
scope limitation. Archive old outputs before replacing; final nightly and both iCloud exports remain required.
