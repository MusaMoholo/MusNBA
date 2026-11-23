# Promotion v3 — individual accuracy and explicit calibration diagnostics

Owner authority: D51 and the subsequent request to audit possibly faulty rejection tests. This is a
methodology revision **after** the independent-fit r2 protected result was known. It is not retrospective
preregistration. Preserve v1/v2 decisions and the original protected result: r2 established 42/44 v2
bounds, with two unresolved star-cohort bias bounds. Do not repeat that protected evaluation, retune the
fitter from it, or describe it as a v2 pass.

## Why revise the policy

The independent reconstruction in `20261123_independent_rotation_gate_sanity_v1.json` reproduces the
existing bias estimates and complete-game bootstrap intervals to 1e-12. The arithmetic is correct.
The policy conflates individual prediction quality with the magnitude of a signed cohort mean. Opposite
individual errors can cancel. A synthetic team-minute-preserving counterexample improves every player's
absolute error (and point-mass CRPS), but breaches the old cohort-bias margin. That is a general conflict
with the players-first objective, not evidence that this particular candidate improves every player.

Unchanged-model independent-seed evidence establishes only 43/44 v2 bounds. This indicates finite-sample
precision/Monte Carlo limitations, not invalid confidence intervals or a licence to waive proper scores.

## Changes and safeguards

Keep v2 change classes, cutoffs, source permissions, provenance, exact identities, support thresholds,
10k complete-game bootstrap replicates/seed, frozen recipes, proper-score margins, primary-benefit
requirements, stress, independent accounting, streams, final-test protection and delivery requirements.

The **27 mandatory compatibility checks** are the same 15 player-tier/stat CRPS, ten game/quarter
CRPS and win Brier/log-loss checks, with exactly the original numerical margins. Every applicable
upper paired 97.5% harm bound must be below its margin. Unsupported mandatory groups or unresolved
proper-score bounds require more information; demonstrated material proper-score harm blocks release.

Report all **17 signed-cohort-mean bias diagnostics**, including old margins, point estimates, intervals
and statuses, separately. They are not universal vetoes on individual-distribution improvement. A claimed
cohort-calibration improvement still needs a frozen relevant benefit test; no such claim is made for r2.
All **25 coverage diagnostics** remain, and demonstrated material coverage harm (lower 95% harm bound
above .03) still blocks release. State unresolved limitations explicitly. Learned changes still need their
single frozen proper-score primary improvement and relevant calibration/joint benefits; no weakening of
those requirements follows from moving descriptive bias into diagnostics. Default CLI policy stays v2;
v3 must be selected explicitly and identified in the evidence/release manifest.

## Fresh independent-fit confirmation before any revised release

Return to development. The unique row-local fitter and all model inputs/parameters remain unchanged.
Freeze the already selected, previously unrun **200 F4 confirmation IDs** from
`20261123_independent_rotation_panels_v2.json`, disjoint from the 200 development games. They were
reserved before r2 outcomes and are not chosen in response to the failure. Clock work may reuse the
resulting baseline captures, but clock outcomes may not select the fitter or this policy.

Compare corrected qualified r1 against corrected r1 plus the canonical independent fitter at 1,000
worlds per arm, existing deterministic seeds, unchanged F4 dated models and conditional actual-participant
loader. Record source/input/policy hashes before generation. Require all 27 proper-score bounds and no
demonstrated coverage harm on this fresh panel, independently audit every pair, and retain all bias results.
Original development/seed/stress/determinism evidence remains required and reported; neither the old
protected result alone nor this policy change alone authorises release. Do not rerun or relabel protected
scoring. A failed fresh confirmation ends this fixed attempt; no further panel or margin changes to rescue it.

Any release decision must describe this post-result policy revision, the original v2 failure, fresh
confirmation, remaining star-bias/coverage uncertainty and known conditional-roster limitation. No
automatic shipping: runtime-hook parity, complete live-output accounting, smoke/fault, fresh nightly and
PWA/iCloud delivery still precede a production default.
