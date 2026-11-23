# D54 successor — complete-game bundle publication

Planned successor to the authorised A1/A2 work; **0%, no execution yet**. This is an interlude before
A3/Chunk B, not a reset of either accuracy ledger. See the [owner contract](incremental_catchup.md).

Headliners: a completed, checked 10k-world game reaches both device bundles while the remaining slate
continues; each imported game and season clearly identifies its own generation. Historical forecast
reconstruction, new models, automatic device import and View Centre execution remain outside this chunk.

Dependencies: A2 decision/checkpoint; retained accepted engine and ten-worker deterministic queue;
current full-bundle importer and laptop/phone profiles; archive and independent accounting tools.
Use up to ten total compute threads, including compression/export. Measure whether reserving a worker
or serialising export gives the shorter whole-nightly time; never silently add an eleventh heavy worker.

## Weighted modules and ten cumulative rungs

| Rung | P1 checked game checkpoints — 40% | P2 bundles and visible freshness — 35% | P3 integrated delivery — 25% |
|---:|---|---|---|
| 10 | Trace queue → branch → game → snapshot completion. | Trace both exporters/importers and current generation labels. | Freeze interruption, concurrency, device-profile and accounting matrix. |
| 20 | Freeze completion/generation schema and independent acceptance checks. | Benchmark one complete re-export and bytes copied to iCloud. | Select retained small ordinary/branched fixtures; pin source identities. |
| 30 | Persist immutable completed branch chunks with source/seed identities. | Choose smallest compatible complete-bundle/checkpoint format from measurements. | Prove ordinary and branched early publication against original worlds. |
| 40 | Recognise a game only after all required branches/mixture reconcile. | Build checked laptop and phone temporary exports from one game manifest. | Verify clean resume skips completed simulations and preserves arrays. |
| 50 | Expose an independently checked game-completion event to the nightly. | Atomically activate exports with a paired-generation receipt. | Interrupt during simulation, compression and pair activation; preserve readable state. |
| 60 | Queue completed games without blocking unrelated simulation work. | Preserve prior readable bundles on failed or partial activation. | Verify peak total compute threads and memory on mixed simulation/export load. |
| 70 | Resume verified completions; reject changed-input or partial checkpoints. | Display current game generations and explicit in-progress slate state. | Check imported early → later bundles, old bundles and offline use. |
| 80 | Test clean-stop and hard-interruption paths without duplicate worlds. | Keep season generation explicit until coherent pathway refresh. | Inspect touched routes at1440/960/390, both themes; verify phone payload. |
| 90 | Independently reconcile game/Expected totals and unchanged seeds. | Validate successive imports, missing-game states and legacy compatibility. | Run fresh full accepted-engine nightly; publish each completed10k game and final season. |
| 100 | Check evidence/docs and checkpoint commit/push. | Publish changed data-free shell, evidence/docs and checkpoint commit/push. | Audit final exports, manual-import notice, successor plan; commit/push. |

P1 precedes P2 activation; independent inspection and benchmark work can overlap. P3 fixtures and test
design can start early, but integrated acceptance follows P1/P2. Fixed weighted sum owns progress;
report each10% module and5% overall boundary. Do not count launched work as completed acceptance.

## Acceptance and fallback

Before the last slate game completes, a real earlier game's complete required10k branches must be
importable in both new bundles and match saved source worlds exactly. Interrupted activation retains
a readable prior generation or a clearly detected recoverable partial pair. Resume changes no draws,
does not recompute accepted games, and rejects incompatible input/recipe identities. Early game updates
must never imply an old season incorporates them. Browsing remains stored-only. Both profile import,
successive upgrade, offline, screen-size and independent accounting checks pass. No data reaches Pages.

If incremental delivery cannot meet those guarantees within the budget, retain the current end-of-nightly
publisher, record the measured blocker and ship a useful player-facing freshness improvement. Do not
claim export as proof of real-device import. Every module checkpoints; final P3 runs a new full nightly
on accepted systems and constructs the next authorised/planned chunk with the same complete format.

## First commands and artifacts

```sh
git status --short --branch
.venv/bin/python scripts/smoke.py
rg -n 'export|snapshot|branch|completed' scripts/nightly_musnba.py scripts/nightly.py scripts/live_forecast.py
rg -n 'generation|importBundle|musnba.gz' scripts/export_musnba.py scripts/webapp
.venv/bin/python scripts/check_docs.py
```

First inspect the files resolved by `rg`; names here are search hints, not permission to assume a callback
already exists. Freeze the implementation/test plan before edits. Store aggregate receipts/logs in
`analysis/experiments/`; worlds, temporary bundles and interrupted fixtures stay ignored under `data/`
or scratch. Archive replaced live outputs outside the repository. HANDOFF owns exact commands/jobs.
