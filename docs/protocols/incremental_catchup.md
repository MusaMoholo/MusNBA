# Incremental delivery and missed days — successor contract

Owner D54 (23 November): make a game's complete checked **10,000 worlds** available in the laptop/phone
`.musnba.gz` exports when that game finishes, while other games continue. Prioritise after current A1/A2;
this document records planned behaviour, not an implementation or a replay run authorisation.

## Current behaviour, verified in code

`fetch_espn.collect` reads all team schedules for the configured season/type and fetches every missing final
summary it discovers, not just yesterday's games. Failures remain reported and can leave gaps. Nightly
rebuilds inputs from retained completed games before today's ET origin, projects today's possession slate,
then a season pathway. It does not recreate missed possession forecasts. `--backfill-days` creates older
placeholder-model snapshots and is not the proposed engine replay. `nightly_musnba.py` exports both devices
only after the entire nightly succeeds.

## Per-game publication

Persist and independently reconcile a complete game (and all required branches if enabled) before exposing
it. Use temporary files plus atomic activation and explicit generation/model/origin identities. Keep the
previous readable export if interrupted; resume verified completed games without duplicates or changed draws.
The existing importer expects complete bundles: appending gzip members alone is insufficient. Choose the
smallest compatible complete-bundle/checkpoint design after measuring export cost and iCloud traffic.

Both device profiles advance from the same checked game generation, with a manifest detecting partial pair
replacement. Show per-game freshness and a clear in-progress slate. A season remains explicitly from its
own coherent generation until refreshed; never imply that old season worlds used newly published games.
Stored worlds only while browsing. Test early import, successive import, interruption/resume, offline use,
old-bundle compatibility and phone/laptop payload limits. Exporting does not auto-import either installed PWA.

## Historical reconstruction proposal

Useful question: **what would this frozen model predict, given the players who actually participated?**
Condition on that declared roster (and actual starters only if explicitly included/labeled); let the engine
predict minutes, rotations and performance. Never feed actual minutes or in-game outcomes into its inputs.
This removes availability guessing for a conditional engine diagnostic, not a genuine pre-tip forecast.

Every other input and every fitted parameter must precede that game's ET origin. Current fitted models cannot
be applied to dates before their training cutoff and labelled historical forecasts. Preserve original forecasts
unchanged; store reconstruction kind, roster assumption, recipe/version/cutoff, coverage and missingness separately.
Freeze date coverage and resume rules; do not tune against the protected final season. Existing D39 safety
requirements apply. D40 historical execution remains deferred while this proposal is assessed; no backfill started.
