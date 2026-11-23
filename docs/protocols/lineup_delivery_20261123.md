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

The backend's summary functions should gain optional exact integer masses while preserving the existing
unweighted code path. Distinguish **saved world count** from **probability-mass denominator**; histogram sums
and conditional shooting denominators use mass, displayed simulation counts use real worlds. All app areas
reading Expected—slate, game, leaders, roster, comparisons and season—must use its same source/generation.
An isolated game-page override is insufficient for full S08 acceptance.

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

## PWA and acceptance

Laptop includes all supported saved branches and stored selection summaries. Phone includes Expected,
its honest assumption/provenance labels and precise marginals; no branch/joint tools or hidden world payload.
Normal routes register only source-verified stored providers. Generation changes invalidate cached providers;
rapid selection/navigation cannot render stale choices. Retain unaffected actual results and dated context;
hide or explicitly label summary panels that are not valid under the selected assumption.

The branch decoder and summary now have shared app modules (`lineup-worlds.mjs`, `lineup-summary.mjs`), with
old research import paths re-exporting them. Original 15% probabilities pass exact-weight tests. They are
not registered on normal routes yet; their existence is no app/PWA delivery claim. Update the explicit shell
module inventory/service-worker list when wiring. Test arbitrary original probabilities, corrupt/mismatched
sources, exact partial conditions, player/period/team/season identities, all touched pages at 1440/960/390
in both themes, import/offline/upgrade and the stripped phone profile. Inspect screenshots and disclose any
scope limitation. Archive old outputs before replacing; final nightly and both iCloud exports remain required.
