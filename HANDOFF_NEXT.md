# Handoff — state and next actions

Updated **22 November 2026 — A1 overnight execution, S01 complete; S02 next**. Dashboard U1–U22 complete and published.
Dashboard close-out checkpoint **86c2a46**, A1 planning checkpoint **00a0731**; S01 partial source checkpoint
**c6d5db4** is committed and pushed.
The owner has lifted the planning-only stop for this overnight A1 execution and delegated in-scope engineering and
product decisions without waiting; source, cutoff, promotion and retention gates are unchanged. **S01 is complete;
S02 starts at 0%; A1 overall is 6.0%.** No candidate, model promotion, forecast or PWA change has been made.

**Use the app:** https://musamoholo.github.io/MusNBA/ — data-free GitHub Pages, source branch `gh-pages` at **e302d27**.
iPhone: Safari → Share → Add to Home Screen → launch the icon → Offline data & installation → Import data.
Bundle: **iCloud Drive/MusNBA/MusNBA.musnba.gz**, also `exports/MusNBA.musnba.gz` and `~/Downloads/MusNBA.musnba.gz`.
All three copies match (10,620,944 bytes, SHA-256
`3055d277fc5e3c1b392d0b06466ec1b6a8c34de3313144b4fc856e1e5abd9ecf`, rechecked during S01). Owner confirmed on 22 Nov
that the file now appears on the phone; visibility is not confirmation of import.

**Refresh complete:** 21 Nov (6 games) and 22 Nov (7 games), engine v1.3, **10,000 worlds per game**, one rotation table
per world; fresh **10,000-world season, 965 remaining games**, as of ET 21 Nov. Offline/no-rebuild nightly finished
22 Nov 01:04 UK; finished-code views rebuilt at 01:05 before export (nightly had loaded views before U19 was added).
Earlier snapshots/shells/bundles archived in `~/Basketball_archive_ops`. No fetch, training or model promotion in the dashboard close-out or this planning pass.

**Running:** no A1 simulation or download. The original-stream regeneration completed as
`20261122T022323Z_a1_s01_control` in **1,567 s**; independent seed `20261122T025114Z_a1_s01_seed2` completed in
**1,566 s**, with log `/tmp/musnba_a1_s01_seed2.log`. Their independent accounting and paired-noise reports are
`analysis/experiments/20261122_a1_{control_accounting,seed_accounting,seed_noise}.json`. Existing serving artifacts are not touched. Review/test
servers are closed; owner's :8766 remains untouched.
At the S01 checkpoint after the type-only annotation, smoke passed **102/102**, `--fault` deliberately failed **22**
checks (exit 1), all **15** focused A1 tests passed and the local bundle hash remained `3055d277...e5abd9ecf`.
All eight root docs were reviewed: AGENTS needs no further change because its scoped overnight authority is already
in `c6d5db4`; ENGINE and DASHBOARD only need status updates because no model design or app behaviour changed.
NBA Stats pbp history remains paused: **1,895/5,517** logged games dated before ET 21 Nov are retained; **3,622**
remain, including 235 current-season games. **45** retained manifest entries lack their original URL/fetch time.
Do not invent those fields. All eight 2022–26 hoopR parquets match their manifest hashes/bytes; ESPN game
`401810469` has 25 player-box rows but no retained hoopR play-by-play, while mapped NBA play-by-play `0022500614`
is retained. Investigate rather than inventing the missing ESPN events. Start your own :8767 server for checks.

**Last dashboard-delivery checks:** smoke **102/102**; deliberate `--fault` fails **22** checks (exit 1); full browser sweep **156/156**, then
**12/12** targeted cases for the final phone stacking correction; hosted PWA **15/15** (import, phone stacking, offline
sections, dynamic counts/qualifiers). macOS atomic export visibility regression passes. Real iPhone installation/import
still needs owner acceptance; iCloud file delivery itself is confirmed.

**Owner preferences from the dashboard chunk:** season insights belong inside Standings; comparable card groups come in
multiples of three (Leaders: 9 player + 6 team cards); changing copy/counts/dates/qualifiers/model labels must derive from
loaded data/configuration. Phone can stay stripped back (D36). A1 S01 is underway below. The latest owner instruction makes the active dashboard
history consistent with the current accepted model: retain daily Today forecasts, and support a season-start→now
rebuild per model version with strictly dated inputs/fits. Earlier generations remain archived (ENGINE_PLAN D39).

**How the owner wants a chunk run (AGENTS §3):** state your understanding and **one or two headliners**; **plan every subtask as
a ladder of ten 10% steps with done-when criteria** and weights for the chunk %, keep the ladders below, and print the board
(active subtasks + overall, text bars) **in your messages to him** at every subtask 10% / overall 5% mark — during long jobs and
while answering his questions too. **Give time estimates from measured job rates** (he says agents overestimate). He sends
many UX requests mid-chunk; do them, check every touched page at 1440 / 960 / 390 in both themes and look at the screenshots.

## Planning checkpoint record (22 Nov 2026; separate from A1)

This session prepares the next chunk only; it does not start experiments, downloads, promotion or a nightly.
One subtask, **Planning (100% weight)**; overall = Planning. Ten concrete steps:
10 baseline docs/code audit + smoke pass; 20 MusSim and MusNBA historical-workflow contracts checked;
30 fourteen scopes/dependencies/weights drafted; 40 promotion and historical-run gates specified;
50 fourteen ten-step ladders written; 60 actionable handoff rewritten; 70 PLAN/ENGINE/TRAINING current;
80 AGENTS/README/DASHBOARD/FINDINGS current; 90 doc links/weights/commands/contradictions checked;
100 final docs reviewed, committed, pushed and owner shown the chunk.
Completion at this named checkpoint: **Planning 100%; next engine chunk 0% (not started)**.
Commit/push status is verified by the checkpoint commit and its remote branch; no A1 execution is included.

**Planning checks:** baseline smoke rerun **102/102**; all 14 task weights agree between PLAN/HANDOFF and total 100%;
all 140 rungs are ordered 10→100; all A1 statuses are 0%; 19 local Markdown links resolve; fences and diff whitespace
checks pass. Only the eight root Markdown docs changed. No new model experiment, fetch, training, final-test score,
nightly, app build, PWA export or publication was performed. Existing public shell/model/bundle remain as above.

## Progress ladders — A1 overnight execution

**Headliners:** player accuracy (including defence, roles and responsive minutes); calibrated games/seasons with
current-model historical predictions. Scope/dependencies: PLAN §6a. Acceptance: PLAN §6b, TRAINING_PLAN §8.
The prior planning-only stop has been lifted for this overnight execution; the original scopes and gates still apply.

For each S, p is its completed-rung percentage. Overall = Σ(weight × p) / 100. Weights below are fixed and total
100%; they are progress weights, not runtime estimates. Post active-task bars and overall immediately after **every
10% subtask rung** and when overall crosses **each 5% boundary**. Drop completed tasks from the per-task display, not
from the denominator. Show the exact weighted percentage; never award progress for elapsed time or a launched job.
Long jobs also get item-count bars (games/files/dates complete) at each 10%, logs and measured throughput; a job's
partial completion does not imply its enclosing acceptance rung is done. Record any scope change before changing
weights, with the old and new accounting; do not hide unfinished tasks by deleting their weight.

| Task | Weight | Progress | State / latest checkpoint |
|---|---:|---:|---|
| S01 Baseline and evaluation contract | 6% | 100% | Both controls audited; final manifest, seed floors and cutoff limits pinned; no candidate promoted |
| S02 Data integrity and parity | 6% | 0% | Planned |
| S03 Offence/defence signal diagnosis | 8% | 0% | Planned |
| S04 Defence and shot quality | 12% | 0% | Planned |
| S05 Roles and minute allocation | 8% | 0% | Planned |
| S06 Game-state substitutions | 12% | 0% | Planned |
| S07 Availability and future absences | 6% | 0% | Planned |
| S08 Lineup branches and Expected | 6% | 0% | Planned |
| S09 Shared form and end-game behaviour | 10% | 0% | Planned |
| S10 Season pathway calibration | 8% | 0% | Planned |
| S11 Integrated confirmation/promotion | 5% | 0% | Planned |
| S12 Model behaviour in the dashboard | 3% | 0% | Planned |
| S13 Current-model season history | 5% | 0% | Planned |
| S14 Nightly, delivery, successor | 5% | 0% | Planned |

**A1 overall: `█░░░░░░░░░░░░░░░░░░░ 6.0%`.** Both control seeds are complete; no candidate fit, model promotion or
production/PWA change has started.
Each rung below is cumulative; 100% always includes updated docs, necessary PWA model/data/shell delivery, reviewed
commit and push, plus the owner summary. See AGENTS §3/§5 and PLAN §6c for the per-subtask PWA checklist; research-only
checkpoints record that the served bundle is unchanged. Delivery is not proof of manual phone import.

### S01 — baseline and evaluation contract (6%)

| % | Done when |
|---:|---|
| 10 | Startup smoke passes; current code/model/data hashes and running-job state are recorded. |
| 20 | Pool-0 v1.3 control, same-game team benchmark and pathway-v1 evidence are pinned with exact run IDs. |
| 30 | Game IDs, seeds, model cutoffs, known-participant/known-starter assumptions and tier definitions are audited. |
| 40 | Training-tail early stopping, fold boundaries and every auxiliary model's cutoff are verified. |
| 50 | Primary metrics, non-inferiority margins, comparison families and minimum usable subgroup counts are preregistered. |
| 60 | Paired game-clustered comparisons and seed/noise estimates are available on the pinned control population. |
| 70 | Conditional-engine versus pre-game-availability evaluation populations and report coverage are defined separately. |
| 80 | Baseline inputs/outputs reproduce on a fixed small game subset; any mismatch is explained before candidates. |
| 90 | Baseline manifest and confirmation-game plan are committed-ready, with run commands and compute schedule. |
| 100 | Docs capture the contract and limitations; checkpoint committed/pushed; owner receives baseline summary. |

### S02 — data integrity and train/serve parity (6%)

| % | Done when |
|---:|---|
| 10 | Retained NBA/ESPN files, manifests, coverage and outstanding history count are inventoried by season. |
| 20 | Resumable one-stream pbp retrieval is configured/logged; parser and crosswalk audit cases are selected. |
| 30 | At least half the outstanding history items are retained or explicitly classified unavailable; progress reported. |
| 40 | Every queued history item is retained or has a documented source failure; retries/resume status are explicit. |
| 50 | NBA/ESPN points, seconds, possession conventions and excluded games reconcile per season. |
| 60 | DNP/zero minutes, substitution opportunities, simultaneous subs and early matchup duplication are audited. |
| 70 | Tracking-defence/report/roster date coverage is mapped; safe joins and missing-input fallbacks are specified. |
| 80 | Fold and serving inputs agree on sampled identical states, with no future games or fold-external fitted priors. |
| 90 | Meaningful corrupted-input/future-date tests fail; approved data changes and usable populations are documented. |
| 100 | Smoke and relevant checks pass; facts, gaps and exact build commands saved; commit/push and owner summary. |

### S03 — trace lost offence and defence signal (8%)

| % | Done when |
|---:|---|
| 10 | Fixed matched-game component dataset and coefficient definitions are specified from S01. |
| 20 | Existing free-running component loadings/levels are reproduced with game-clustered uncertainty. |
| 30 | M6a uses those games and the same candidate inputs; teacher-forced quantities are labelled diagnostic. |
| 40 | Player/shooter/defender profile spread and reliability are compared with observed historical spread. |
| 50 | Node predictions are traced by shooter, defence, zone, usage and reliability bins, with sample counts. |
| 60 | Teacher-forced versus free-running clock, lineups, usage and component effects isolate where signal is lost. |
| 70 | Rejected real-matchup variants' extra total bias is decomposed into shots, FTs, pace and rebounds. |
| 80 | At least two plausible mechanism families are selected, with predicted effects and disconfirming tests. |
| 90 | Diagnostic report links each hypothesis to evidence; no causal or forecast claim is made from teacher forcing. |
| 100 | FINDINGS and candidate matrix are current; checkpoint committed/pushed and diagnosis summarised. |

### S04 — player-based defence and shot quality (12%)

| % | Done when |
|---:|---|
| 10 | S03's two or three levers are frozen as bounded experiments with unchanged v1.3 controls. |
| 20 | First family (profile shrinkage/reliability or node expression) is implemented behind candidate settings. |
| 30 | First family completes paired fold screening; losses, calibration and sample-size buckets are recorded. |
| 40 | Second family (shot-type/defender/help/attempt deterrence or rebound/foul mechanism) is implemented. |
| 50 | Retained tracking defence has a cutoff-safe incremental ablation, or a measured reason it cannot enter. |
| 60 | Second family completes paired fold screening; unchanged negative variants are not recycled as new evidence. |
| 70 | Surviving candidates complete sequential fixed-game backtests, including component levels and total-bias accounting. |
| 80 | Player-first comparisons and all-fold confirmation for retained inputs are complete; interactions are checked. |
| 90 | Retain/reject decisions, fitted-artifact cutoffs and next falsifiable defence questions are documented. |
| 100 | Candidate specs/logs/checks and docs are checkpointed/pushed; owner hears what defence work actually gained. |

### S05 — roles, rotation membership and minutes (8%)

| % | Done when |
|---:|---|
| 10 | Active/rotation/start/minutes-conditional/healthy-role definitions and evaluation populations are separated. |
| 20 | Historical DNP-CD, fringe, absent-core, recent-trade and returning-player cases are audited for leakage. |
| 30 | Richardson-like shrinkage failures are traced across a population; double application of play chance is checked. |
| 40 | D29 baseline minutes and membership calibration are measured by tier and situation with minimum counts. |
| 50 | Candidate membership/allocation/ramp correction is implemented without changing unrelated engine nodes. |
| 60 | Deterministic allocator checks pass: exactly 240 regulation team minutes, legal player limits and absence cascades. |
| 70 | Unconditional and conditional-on-playing minute distributions complete historical fold evaluation. |
| 80 | Candidate completes a paired engine backtest; player minutes and downstream stats are checked first. |
| 90 | Control or candidate is selected for S06; biases, uncertainty and remaining low-sample risks are recorded. |
| 100 | Code/tests/docs and experiment evidence committed/pushed; owner receives the minutes result. |

### S06 — game-state substitutions (12%)

| % | Done when |
|---:|---|
| 10 | Legal dead-ball opportunities, no-sub cases and state-before-sub labels reconcile with history. |
| 20 | Historical blowout/close, foul-trouble, stint/rest and quarter responses are measured by pre-game role tier. |
| 30 | Out/in datasets include S05 target deficit and eligible players without future totals or final-margin inputs. |
| 40 | Out-model fold results beat or justify retention against a simple conditional sub-rate baseline. |
| 50 | In-model fold results and joint lineup selection respect eligibility, player limits and positional context. |
| 60 | Engine integration handles simultaneous changes, foul-outs, period boundaries and OT with five distinct players. |
| 70 | Every-world seconds/points identities and short-roster/no-eligible-sub stress cases pass without silent repairs. |
| 80 | Sequential backtests measure minute CRPS and state response against target tables; pull strength uses folds only. |
| 90 | Combined S05/S06 decision, runtime and deviations from history are written; old path remains reproducible. |
| 100 | Evidence and docs checkpointed/pushed; owner gets the substitution/realism summary. |

### S07 — availability, starts and future absences (6%)

| % | Done when |
|---:|---|
| 10 | Timestamped report archive is audited by origin, status and outcome with missing coverage explicit. |
| 20 | Prior-day roster eligibility and DNP/rest/injury labels are separated from actual-participant oracle inputs. |
| 30 | Fixed-status and projected-start baselines are scored only on permissible historical development populations. |
| 40 | Play/start training and chronological scoring splits are built, or insufficient development coverage is proven. |
| 50 | Candidate play/start calibration is tested where supported; otherwise the fixed fallback and data-collection gate are retained. |
| 60 | Historical absence duration, return and rest hazard candidates are fitted using only earlier sequences. |
| 70 | Simulated games missed, return timing and starter frequencies are compared by role with uncertainty. |
| 80 | Cold starts, unknown reports, trades and missing rosters have honest fallbacks; no actual-lineup leak in forecasts. |
| 90 | Available models/fallbacks are selected; D31 branch probabilities and S10 absence contracts are explicit. |
| 100 | Coverage limitations, results and next data threshold saved; commit/push and owner summary. |

### S08 — lineup branches and Expected mixtures (6%)

| % | Done when |
|---:|---|
| 10 | Branch IDs, uncertainty selection, probabilities and D31's >2-maybe limits are written as a data contract. |
| 20 | One-player plays/sits branches re-solve roles, minute targets and opponent assignments correctly. |
| 30 | Two-player joint branches, probability normalisation and missing-status fallback are implemented. |
| 40 | Deterministic 10k-world branch runs persist independently with model/origin/input provenance. |
| 50 | Expected distributions are formed from the stored exhaustive branches with explicit mixture weights. |
| 60 | Season worlds consume that same Expected mixture; probability/mean/count identities pass. |
| 70 | More-than-two one-out cases are labelled non-exhaustive; unsupported joint assumptions stay explicit. |
| 80 | Local branch selection renders stored results; phone export contains only Expected and its provenance. |
| 90 | Representative games, absence cascades, restart/runtime and UI size/theme checks pass. |
| 100 | Branch limitations and commands documented; checkpoint committed/pushed and owner summary delivered. |

### S09 — shared form, talent and end-game behaviour (10%)

| % | Done when |
|---:|---|
| 10 | Residual player/team variance and covariance are measured after conditional minutes and role effects. |
| 20 | Persistent low-sample talent and game-night form are separated, with historical estimation/shrinkage specified. |
| 30 | Candidate per-world player usage/efficiency/selection draws are implemented with mean-preservation checks. |
| 40 | Shared pace/shooting factors are tested against player-only draws and the no-form control. |
| 50 | Conditional teammate/opponent dependence and tail coverage are scored; double-counted minute variance is excluded. |
| 60 | Late-game state bins expose foul/clock/shot-selection/OT gaps with historical sample sizes. |
| 70 | Supported end-game corrections complete fold tests and mechanical boundary/OT checks. |
| 80 | Sequential engine backtests compare form/end-game components and their combined effect on CRPS and calibration. |
| 90 | Retained form/talent/end-game settings, seed sensitivity and runtime are recorded; no interval-only win claimed. |
| 100 | Logs/specs/tests/docs committed/pushed; owner gets the joint-outcome and realism result. |

### S10 — season pathway calibration (8%)

| % | Done when |
|---:|---|
| 10 | Pathway-v1 16-origin baseline and schedule/Cup/final-win definitions reconcile on identical populations. |
| 20 | Candidate carry-over/opponent-adjusted starting estimates are built strictly before each origin. |
| 30 | Starting-rating changes complete leave-one-season-out screening, including November cold starts. |
| 40 | Memory/gain/drift alternatives test flat surprise persistence without biased rating drift. |
| 50 | Supported S07 absence paths enter player availability; unsupported histories retain explicit fallbacks. |
| 60 | Near-term Expected worlds feed the pathway exactly once; ratings update from each world's expectation. |
| 70 | Candidate variants complete all 16 season/start-date combinations with 10k season worlds. |
| 80 | Leave-one-season-out CRPS, dispersion, coverage and persistence are reported separately by start date. |
| 90 | Pathway selection and its interaction with the possession engine are frozen for S11; negative results recorded. |
| 100 | Season evidence, settings and identities documented, committed/pushed and summarised to owner. |

### S11 — integrated confirmation and promotion (5%)

| % | Done when |
|---:|---|
| 10 | Every S04–S10 component has an evidence-backed retain/reject decision and a reproducible control. |
| 20 | Integrated candidate settings are frozen; individual removals test interactions rather than assume additive gains. |
| 30 | The matched 200-game F4 comparison passes the preregistered player and game gates. |
| 40 | All eligible F4 games are scored with a matched control, or a failed gate rejects the candidate explicitly. |
| 50 | Fixed F1–F3 confirmation samples complete, with fitted artifacts respecting each fold's cutoff. |
| 60 | Second-seed and 10k-world subset comparisons separate simulation noise from claimed improvements. |
| 70 | Availability-aware evidence, stress/cutoff/identity tests and whole-night resource measurements pass. |
| 80 | Frozen release manifest selects accepted components or retains v1.3/pathway v1 with a rejection report. |
| 90 | Only an accepted frozen new version gets its one final score; production artifacts/fallbacks are retained and decision recorded. |
| 100 | Promotion/no-promotion is documented; any new model is refreshed/exported to iCloud and PWA-checked; commit/push and owner summary. |

For S11 a failing candidate follows the **rejection branch**: finish the decision report and checks that support
keeping the control; do not run later expensive confirmation just to fill a bar. Mark each unrun rung's rejection
reason explicitly, not “passed”. This completes a decision task, never certifies an untested candidate.

### S12 — model behaviour in the dashboard (3%)

| % | Done when |
|---:|---|
| 10 | Stored-output contracts for rotation probabilities and sampled events are written; phone budget stated. |
| 20 | Rotation summaries are derived from saved simulations; per-side probabilities sum to five at each time. |
| 30 | Five sampled worlds' events reconcile to their scores, periods, player stats and on-court identities. |
| 40 | Rotation-map view presents probabilities and supported state slices with dynamic copy and missing states. |
| 50 | Watch-a-sim list supports period jumps, clock, team, event and cumulative score from stored logs only. |
| 60 | Branch/origin/version labels and existing player/game navigation work together without duplicated controls. |
| 70 | Phone receives compact summaries/list only where size permits; world tools and branches remain localhost-only. |
| 80 | Touched routes pass 1440/960/390 in both themes; screenshots are actually inspected. |
| 90 | Offline/import and old-snapshot fallbacks pass; limitations and shipped behaviour are in DASHBOARD_PLAN. |
| 100 | App/output changes are exported and the changed shell published/PWA-checked; docs committed/pushed; owner gets the feature summary. |

### S13 — current-model season history and daily archives (5%)

| % | Done when |
|---:|---|
| 10 | Existing snapshots/archives are inventoried; model/origin/run identity and Today/preview/replay rules are frozen. |
| 20 | Immutable original forecasts, explicit same-day revisions and separate result joins pass a multi-day test. |
| 30 | Season-start→latest-completed-origin plan enumerates every expected date/game and historical coverage. |
| 40 | Isolated dated profiles, rotations, matchups, availability and fitted-artifact selection reject future cutoffs. |
| 50 | Versioned runner reuses the nightly flow at 10k worlds; resume/cache identity includes origin and all dependency hashes. |
| 60 | Development-date replay passes later-data-injection, interrupted-resume and worker-count determinism tests. |
| 70 | S11/S13 trust gate is recorded; an accepted full-season rebuild has completed at least half its planned origins, or a gate failure is explicitly deferred. |
| 80 | All required origins are completed/reconciled with honest gaps, or the failed gate and remaining production work are recorded without claiming a rebuild. |
| 90 | Atomic active-version switch, results review, Movers and PWA provenance checks pass; older generations remain recoverable. |
| 100 | History/capability/deferrals are documented; activated history is exported and PWA-checked; commit/push and owner summary. |

S13's default dashboard history uses the current accepted version. Historical recipes and reconstructed reports are
labelled retrospective; no mixed-version or invented prospective accuracy claim. A **running** full-season rebuild
is unfinished work, not a gate deferral. Log per-date completion at each 10% throughout; do not go silent between 70/80.

### S14 — final nightly, delivery and successor (5%)

| % | Done when |
|---:|---|
| 10 | Release manifests, prior archives, input rebuild needs and history-fetch pause are verified. |
| 20 | Live nightly collects authorised updates, rebuilds the selected inputs and logs the actual game/branch count. |
| 30 | At least half of the live game/branch runs are complete; item counts and measured throughput reported. |
| 40 | All today/tomorrow (or next-slate) games/branches and the new 10k season complete on the accepted engines. |
| 50 | Final views/active-version history and visible iCloud bundle publish; manifests/checksums/counts reconcile. |
| 60 | Smoke passes all checks and deliberate fault run fails for the expected independent identities. |
| 70 | Final touched-route browser/screenshots and hosted PWA import/offline checks pass; static shell updated if changed. |
| 80 | PLAN/FINDINGS/ENGINE/TRAINING/DASHBOARD/README and handoff state reflect measured results and limitations. |
| 90 | Successor chunk is fully constructed with headliners, dependencies, weights, ten-step ladders, first commands and final-nightly rule. |
| 100 | Final docs/source/logs reviewed, committed/pushed; successor is active at 0%, own jobs closed/handed off, owner gets final result and next chunk. |


## The product in one paragraph (ENGINE_PLAN D26)

On any date D: every game before D is resulted; the **play-by-play engine** (v1.3) simulates today's and tomorrow's games
— or the next slate if neither has games — with inputs carried over from every game before D, **10,000 worlds per game**; the
**team engine** (team pathway v1) plays every later game in each of 10,000 worlds with that world's own ratings. Season outputs
are counts over the worlds. The app slices the engine's stored worlds for joint and conditional outcomes (localhost only; the
phone bundle is stripped back, D36).

## State

**S01 startup (22 Nov, 01:49 UTC):** clean `main` at `00a0731db855a31b83dbdeffa303c7fd4b06969d`;
startup `.venv/bin/python scripts/smoke.py` **102/102**, including a bit-for-bit 10k-world game and season replay.
The only other matching long-lived project process observed was the owner's server; no backtest, nightly or NBA
history fetch was running. No review server started because presentation is not being changed.
SHA-256: `scripts/backtest.py` **1f3ba182b03f1b521c314a38c047df9de9bf1e59836a57e10c377bc82c813052**;
`scripts/engine.py` **48d09c8e5fa7f10a84fafc9ec61b38aae65d225b00f60b2775387963b75737e8**;
`models/v1.3.json` **f85ca77418990f702b8e6dbe3eb0be1c35b1830649517a760d000bd6b4c1d09e**;
retained pool-0 game results **c4d29755292599be2f62c7cd726742d54eec7ae0c49e0dd0d4ca4050e3b41876**;
current matchup `pregame.parquet` **d4da5f071de3ddcbc72bbb4899a77f9b4f22d899a3a54bcfb76baf0097594d0e**;
fold model `config.json` **1617769cb52f2c750e0f1276071b39fc21254ef53fc97ccc646869aaa50f5e71**.
The 16 fold model text files, sorted by name and hashed as `name sha256\n`, have SHA-256
**c08ae09f13ea1470e964a488e01fb9f7e4c5604b06fef3b65d1a51dd6a79958c**. The folded model's recorded feature-file
size/mtime differ from the current refreshed files; original-data equivalence must be demonstrated, not assumed.

**S01 controls pinned:** conditional, pool-0 engine run
`analysis/experiments/20261120T162930Z_v1.3_pool_per_world_F4.json` and its same-game team benchmark: margin/total
CRPS **9.415/11.723** and win log loss **0.5738**, versus **9.322/11.353/0.5584** respectively, 200 F4 games ×
1,000 worlds. Team pathway-v1 evidence: `analysis/experiments/20261120T093320Z_season_backtest.json` and
`analysis/experiments/20261120T093809Z_season_calibration.json`; 16 season/start origins × 10,000 worlds.
These are retained development results, not a new experiment or a pre-game-availability evaluation.

**S01 population/seed audit:** eligible reconciled regular-season games in F1/F2/F3/F4 are **731/738/490/718**.
The retained F4 control's 200 IDs are in its game parquet, and exactly match sorted sampling without replacement by
NumPy `default_rng(20261119)` from the 718 sorted IDs. The old log does not record its selection seed, so that match
is evidence for the default, not an independently recorded invocation. Its 1,000-world simulation seed per game is
`projection.seed_for('backtest', 'v1.2d_F4', date_et, game_id)`; `--seed` changes the selected games, not that
simulation stream. Different model-config version strings therefore do **not** automatically share random streams.
Inputs use actual participants, while the default targets path projects starters. Legacy scorecard tiers use actual
starter status; across 4,346 retained player-games, switching to usage ≥0.25 for stars and otherwise pre-game
`start_share >= 0.5` changes **485** classifications, including **12 unknowns** (kept unknown, not forced to bench).
Pre-game groups: 284 star, 1,578 starter, 2,472 bench, 12 unknown. The exact fixed F1–F3 and F4 confirmation IDs and
seed list will be saved in the S01 manifest; no candidate has yet been evaluated.

**S01 fit-cutoff audit:** node early stopping and candidate temperatures use the latest 10% of the *training* window;
fold validation is separate. Fold engine clock/band/penalty tables and missing-profile medians filter at the declared
training cutoff; D29 ramp and spread fit strictly before the validation start. The F4 soft-assignment theta is fitted
through **2025-12-31**, safe for F4 validation and for the pre-season-trained v1.3 final test. It is **not safe for
F1–F3**: the same theta also affects historical matchup feature construction, so earlier-fold tests require dated
assignment fits **and** rebuilt fold-specific features, not merely a different engine config. `priors_by_season` and
team-style priors use the whole first retained season as their first-season fallback; training rows inside that season
therefore do not satisfy strict per-origin input cutoffs. Later-season priors use earlier seasons. Non-fold engine
missing-profile medians currently read all rows of the feature file; an isolated historical runner must date-filter
those medians too. Static athlete measurements lack a demonstrated as-of provenance and need S02 review. No same-day
multiple-game player or team groups were found in the current matchup feature table. These are audit findings, not
claims that a corrected model has been evaluated.

**S01 frozen evaluation:** TRAINING_PLAN §8.2's 22 Nov preregistration records pre-game tiers and unknowns, 100
player-games/30-game subgroup minimum, family primaries, game-cluster bootstrap, multiplicity and numerical
non-inferiority margins. The 4,346 matched pool-400/pool-0 player-game comparison supports the scale of the margins,
but is not an independent seed-noise estimate. The regenerated control supplies per-player 3PM CRPS; its independent
seed supplies the preregistered noise floor. No candidate has been scored.

**Play-by-play engine v1.3 (D34; `ENGINE` in `scripts/engine.py`, `models/v1.3.json`, models `data/models/v1.3/`)** — unchanged
models; **10,000 worlds** (`ENGINE['sims']`, nightly default) and **one rotation table per world** (`ENGINE['pool'] = 0`;
backtest: players level, totals level, +5% time; FINDINGS §3v). D29 minutes, D30 defence inputs as before.

**NBA Stats (D32) — ingested, retained, refreshed nightly.** Counts below describe the 20 Nov ingest audit unless
otherwise dated; the 22 Nov planning smoke verifies the later crosswalk at **5,518 games / 935 people**. S02 inventories
current endpoint coverage before resuming history; do not treat the old 5,508 denominator as a permanent target.
- `scripts/fetch_nbastats.py`: stdlib urllib with Chrome fetch headers (`Sec-Fetch-*`, `sec-ch-ua` — without them stats.nba.com
  connects and never answers), ~1 request/s with jitter, retries with backoff, stops after 5 failures in a row, resumable
  (present files skipped; un-flushed files recorded in the manifest on resume). Raw: `data/raw/nbastats/<endpoint>/<season>/`
  (gzip + `manifest.json` with sha256). A 22 Nov inventory finds 54 season-log files and `boxscorematchupsv3`
  files for 5,517 logged games (2022-23 → ET 21 Nov);
  `leaguedashptdefend` per date (Overall, <6 ft, threes; 2,628), `playbyplayv3` 1,895 games (paused). Hustle (`--hustle`, per
  date) coded, not fetched. The nightly fetches new finals (`fetch_nba_stats`: ~10–15 requests; failures never stop it).
- `scripts/nbastats.py`: crosswalk 5,508/5,508 games (ET date + team pair), 118,024/118,041 player-games (17 unmatched: Lachlan
  Olbrich has no ESPN id); reconciliation (points identical, our minutes within 60 s of NBA's in 99.87%, possessions +0.9);
  matchups → `data/derived/nbastats/matchups.parquet` (1.04M rows, ESPN ids). 2022-24 matchups over-count FGA (111%) — FINDINGS §3t.
- `scripts/realmatch.py`: pre-game assignment on real shares (top-1 36.4% → 50.2%, top-2 75%; θ `models/realmatch_2025-12-31.json`,
  `realmatch_top2_…`), per-game pair history (`pair_history.parquet`). The nightly refreshes crosswalk, matchups and pair history
  (`refresh_real_matchups`) whenever NBA files are retained.

**Defence on real matchups — measured, not promoted (D37; FINDINGS §3s′, §3u, §3w).** v1.3's gap is shot-making (FG% 37%, 3P%
18% of the real effect; turnovers 95%). Candidates on the 200-game F4 backtest: v1.4c (real-share defender quality + θ), v1.4e
(+ deterrence: 3P% → 30%, FTA → 48% of real), v1.4f (+ top-1/top-2 defenders, owner's idea) — all level or worse on margins,
totals and players. Switch hunting (D35) not visible (v1.4d not run). Defender traits: 3PA share allowed r 0.77, 2P% 0.49, 3P%
allowed noise (−0.05). **Reading: the engine compresses team differences generally** (shared-pool loadings offence 0.73 v 1.14 real,
defence 0.69 v 1.69; these are coefficients, not ratios; most components except turnovers at 20–40%). Specs `models/v1.4{c,d,e,f}.json` (status NOT PROMOTED / NOT RUN), variants
`data/derived/variants/realmatch{,_dx,_top2,_hunt}/`, fold models `data/models/folds/v1.4{c,e,f}_F4_all`.

**Team engine (team pathway v1, D25)** — unchanged.

**Dashboard upgrade programme complete (22 Nov):** U1–U22 all shipped. This session finished U15 roster minutes/roles;
U16 playoff picture; U17 row win distributions; U18 races; U19 forecast movers; U20 nine player + six team leader cards;
U21 model guide; U22 grouped controls, dynamic copy, loading/missing-data states and PWA fixes. Races/Movers/Leaders are
inside Standings (owner request); old `/season` links redirect. No engine promotion. Season bottom-three counts are
summary-only: all existing fields exactly unchanged on 10k worlds / 965 remaining fixtures / 13 engine games.

**PWA:** public https://musamoholo.github.io/MusNBA/ (source also public, explicitly approved 22 Nov), branch-source
`gh-pages` at `e302d27`, 24 data-free files (no simulation data). Hosted import/offline 15/15, including phone layout. Model source stays on `main`;
simulation data/bundles stay ignored and on laptop/iCloud. `nightly_musnba.py` defaults to iCloud Drive/MusNBA; export-only
reuses finished snapshots. `.github/workflows/pages.yml` is MusSim's optional manual Actions alternative, not the active
branch deployment. Real iPhone installation/import remains owner acceptance.

**App core retained (see DASHBOARD_PLAN for all shipped behaviour):** Today/Game Centre **Spotlight** (headliner with points sparkline and 30+/40+/double/
triple chances; breakout watch as a season→tonight dumbbell with the why; six leaders with each one's chance to lead the night
or game; Today's games to watch: closest finish, highest-scoring, likeliest overtime);
**who guards whom** (Matchup view, real matchups, earlier meetings + this game) and **player head-to-head** on sheets; Scenarios
**game flow** (quarters, leads, comebacks, sweeps, lead changes) and **Duels**, grouped dropdowns and quick-scenario rows; Today
**duel of the night**, stacked leaders with suffixes; Standings **Wins** tab (5-win bands), Forecast **wins/seed pickers**, W%,
Proj W / Proj L, sortable, current | projected split; player sheet **Shooting/Chances tiles** (multi-doubles, 5×5), grouped
picker (Scoring · Rebounding ALL/OFF/DEF · Handling · Defense · Time; makes and main stats only); box score Δ v season (incl.
STL/BLK, shooting x/y (z%) coloured per part); bezel points Δ v season (above the value; no win/total Δ); player page "Open
simulation" for tomorrow's games; phone bundle stripped back (D36).

## Next actions — start S02

**Owner's overnight authority:** execute S01–S14 without waiting for input; the earlier planning-only stop is lifted.
The dashboard programme is done. Do not resume U1–U22, repeat rejected defence variants unchanged or begin at S13.

1. **Inventory S02 data by season.** Extend the measured NBA/ESPN counts in FINDINGS §7 with a reproducible manifest,
   hash/file-coverage report and explicit missing game/metadata counts. In particular investigate ESPN box-only game
   `401810469` without inventing play-by-play. The current PBP queue is **3,622**, subject to a fresh dated inventory.
2. **Fix and test ingestion before resuming the single polite history stream.** `fetch_games`, `fetch_ptdefend` and
   `fetch_hustle` eagerly construct a `Store` on every `setdefault`; `fetch_logs` also fails to flush on an exception.
   Reproduce both in isolated temporary storage, fix all affected paths, test resume and metadata retention, then use
   `.venv/bin/python -u scripts/fetch_nbastats.py --pbp --max 363` in sequential logged batches. Recalculate each
   10% item threshold from the actual queue, report measured throughput, and pause the stream during the final nightly.
   Preserve the 45 entries with unknown original URL/time rather than inventing provenance.
3. **Complete S02 reconciliation and train/serve parity.** Audit NBA/ESPN points, seconds, possession conventions,
   unmatched/excluded games and historical publication limits; test cutoff-safe training/serving feature equality,
   including first-season priors, dated assignment fits, missing-profile medians and the all-missing batch-fill risk.
   Isolate corrections from v1.3 and do not claim a promotion gate until supported dated inputs exist.
4. **Continue S03–S10 in dependency order.** Diagnose player/lineup offence and defence before selecting bounded
   candidate families; keep conditional-engine and actual pre-game availability populations separate. Record
   negative results and preserve the accepted control.
5. **S11 freezes the tested combination before promotion.** Confirm on the fixed wider folds and second seed, protect
   the final test and use player outcomes first.
6. **S12/S13 implement model visibility and versioned daily history.** Preserve original and previous-version
   forecasts, reject future-trained inputs/fits and label retrospective histories; record any failed trust gate.
7. **Finish S14** with a fresh live nightly, 10k games/branches and season, iCloud/PWA delivery and all checks. Build
   the successor chunk in the same weighted, ten-rung format before the final commit/push.

## Completed S01 audit and reproduction

The exact source used in both controls was partial-committed/pushed as `c6d5db4`; the final manifest
`analysis/experiments/20261122_a1_manifest.json` was generated before the type-only annotation. Existing
   `backtest.py`/`backtest_compare.py` use actual starter labels for their legacy
   scorecard: on the retained 4,346 player-games, 485 change tier under a pre-game start-share definition (including
   12 unknowns). Preserve the historical scorecard and use pre-game tiers for selection. Despite the F4 control's
   changed feature-file signature, its fixed three-game replay (`20261122T015651Z_a1_s01_repro`, 46 s, one worker)
   reproduced **all** shared game/player fields to absolute tolerance 1e-12 on 3 games and 64 player-games. After
   the full control finished, all 59 legacy game fields and 16 legacy player fields matched on **200 games / 4,346
   scored player-games** to 1e-12. Its independent accounting matched **1,600** quarter scores, **4,346** player 3PM
   actuals and **399/400** team 3PM sums. The other team has one simulated player present in the play-by-play but absent
   from the raw player box; the report explicitly lists the missing outcome rather than inventing it. The second
   simulation stream completed on the same 200 IDs and inputs; its independent audit found the same one missing box
   outcome and no quarter, player-3PM or complete-team-3PM mismatches. The baseline uses
   `--games 200 --seed 20261119`, 1,000 worlds,
   4 workers, targets and pool 0; append `--simulation-stream 1 --name a1_s01_seed2` for the second seed. New
   `--game-ids` accepts an explicit digit-string JSON list, and `--seed-key` deliberately shares a namespace across
   models; the default simulation seed is unchanged. The fixed three-game selection is
   `analysis/experiments/20261122_a1_reproduction_games.json`. No rung is awarded for a launched job.
   - Actual quarter scores must come from `data/derived/history/<season>/player_periods.csv.gz`, not segment totals:
     segment sums omit other points in 56 home and 54 away games of the retained 200-game panel, up to 2 points.
     Grouping the player-period points by game/team/period and including overtime exactly matches both box scores in
     all **2,677** eligible regular-season games across F1–F4 (731/738/490/718). Independent explicit end-period
     scoreboard snapshots match every one of **21,702 team-period totals** (including OT) in these games, with no
     missing regulation quarter ends. Do not select the numerically last event blindly: some later sequence numbers
     are backfilled earlier-clock plays. The new backtest rejects an unreconciled or missing period before recording
     quarter scores. Reproduce the independent check with `scripts/a1_quarter_audit.py`; the retained experiment
     report is `analysis/experiments/20261122_a1_quarter_audit.json`.
   - `scripts/a1_compare.py` now enforces identical game/player keys and observed outcomes, uses pre-game tiers with
     explicit unknowns, and computes 10,000 paired game-cluster bootstrap intervals (including bias/coverage harm).
     It labels sparse/missing metrics inconclusive and explicitly does not make Holm-adjusted promotion decisions.
     Fifteen focused tests pass: `.venv/bin/python -m unittest discover -s tests -p 'test_a1*.py' -v`; the
     three-game integration also verifies that a metric present in only one run is attributed to the correct side.
     `scripts/a1_output_audit.py` independently checks quarter totals/margins against raw scoreboard period ends,
     3PM actuals against raw boxes, valid scores and all shared legacy columns; the three-game run passed 24 quarter
     and 64 3PM checks (`analysis/experiments/20261122_a1_repro_accounting.json`), and the full control passed with
     the one explicitly reported missing player outcome above. The same audit on seed 2 also passed all comparable
     identities and reported the identical unscored player.
   - Conditional and pre-game availability populations are separately defined in TRAINING_PLAN §8.2. The five
     retained ESPN collection origins (19–21 Nov 2026) have complete injury + both-roster files before scheduled tip
     for **4/4, 9/9 and 5/6** games respectively. This is file-presence coverage only, inside the protected final
     season; no outcomes were scored, and this cannot justify tuning or replace a dated development cohort.
     The separate F4 prior-box diagnostic (`scripts/a1_availability_cohort.py`) has **7,305** candidates, **5,201**
     known play/DNP labels, **2,104** unknowns and **32** positive-minute arrivals outside the universe in **24**
     games. Its row-level artifact is `data/derived/experiments/20261122_a1_prior_box_membership.parquet`; the report
     is `analysis/experiments/20261122_a1_prior_box_coverage.json`. It is coverage only, not a fitted forecast.
   - Before any candidate, the 20-game **10,000-world stress subset** is fixed in
     `analysis/experiments/20261122_a1_10k_stress_games.json`: from the retained F4 panel, take five OT games, five
     non-OT shortest-participant-roster games, five remaining smallest actual margins, then five remaining largest
     actual margins, ties by game ID. This is intentionally outcome-stratified diagnostic confirmation, not an
     unbiased population or a tuning panel. It has 26 star, 155 starter, 216 bench and 1 unknown player-games;
     its 26 stars cannot independently pass the 100-player-game tier gate.
   - `scripts/a1_manifest.py` has frozen 200 F1, 200 F2, 200 F3 and all 718 F4 confirmation IDs and streams in
     `analysis/experiments/20261122_a1_pre_candidate_manifest.json`, together with 67 input/model fingerprints
     (including static athlete measurements and the retained M6a diagnostic). F1–F3 remain blocked on dated θ and
     rebuilt features. An independent check confirms 1,318 unique selected IDs within their fold dates and 2,636
     unique confirmation-stream seeds. The final result manifest includes both run IDs and checks all input
     fingerprints against this pre-candidate manifest. It also fingerprints
     upstream feature/history/ingestion code, dependency and data-build reports; the upstream source files were
     verified unchanged from the planning checkpoint. The original manifest omitted production-model hashes, so
     `analysis/experiments/20261122_a1_production_baseline.json` separately pins 17 model artifacts, 11 upstream
     inputs and the unchanged local bundle before any candidate; the final manifest now rejects changes in any of
     these or the 67 original inputs. All 67 original input
     fingerprints were unchanged during seed 2. Both controls used `scripts/backtest.py` SHA-256
     `480d3c8f92a3f1e61ed610254ef36a82a6a7ec8b87812f796652e7f7a024405a`, pinned in commit `c6d5db4`; the final
     manifest identifies that source commit. A later local type annotation resolves the new seed-list Pylance error
     without changing any of 13 compared semantic code fields or any of **3,036** frozen seeds; raw `co_code` SHA-256
     is `aa7233f20022d729a98acf25cb1b321678a83a3cfa33167ffc12f7b86db7e8c6`. The earlier marshalled-tuple digest
     `90ab9314...b1cc7dd4` was not stable across processes and is not used as proof. F1–F4 confirmation seed keys
     are fixed; a shared initial seed does not prove event-by-event RNG alignment.
     S02 must also quantify a newly reproduced batch-leakage risk: an all-missing defender metric in
     `matchups.mu_columns` is filled from the whole batch. A synthetic unrelated row changing from 0.4 to 0.6 changes
     the missing row's `mu_fg_rim` from 0.4 to 0.6. None of 45,110 actor segments with five recorded defenders in the
     fixed 200-game F4 panel had all five `m_fg_*`, `m_tov_rate` or `m_foul_rate` values missing; audit other
     populations/body and simulation lineups too. Training can borrow held-out/future values and differ from serving;
     isolate and validate any correction rather than silently changing v1.3.
**First commands (existing interfaces, no candidates or replay flags invented):**

```sh
git status --short && git log --oneline -5
.venv/bin/python scripts/smoke.py
ls analysis/experiments/
.venv/bin/python scripts/backtest.py --help
.venv/bin/python scripts/backtest_compare.py --help
```

The full baseline rerun was required because the old output omitted 3PM and quarter CRPS. Both it and its
independent-seed partner are complete. Do not launch either again without a new reason. Their commands were:

```sh
.venv/bin/python -u scripts/backtest.py --config models/v1.2d.json --models folds/v1.2d_F4_all --fold F4 --games 200 --seed 20261119 --worlds 1000 --jobs 4 --rotation targets --pool 0 --name a1_s01_control > /tmp/musnba_a1_s01_control.log 2>&1
.venv/bin/python -u scripts/backtest.py --config models/v1.2d.json --models folds/v1.2d_F4_all --fold F4 --games 200 --seed 20261119 --worlds 1000 --jobs 4 --rotation targets --pool 0 --simulation-stream 1 --name a1_s01_seed2 > /tmp/musnba_a1_s01_seed2.log 2>&1
```

Record the process/log/output paths and measured games/second in this handoff while it runs. One 200-game control
previously took **1,365 seconds** (including its recorded work); do not multiply old rates into a promised completion
time for new substitutions, branches or a full-season rebuild. Measure the first completed units of each job.

**Not silently discarded:** face cards, richer court playback, competition tabs and the localhost lineup editor stay
in PLAN §9b. U3 already provides role-change badges and U11 real-matchup defence profiles: extend existing behaviour,
do not rebuild them. Tracking defence enters S04 only if it earns its place; its UI is secondary to measured accuracy.

**Housekeeping:** node caches can be ~9 GB each; inventory dependencies before pruning, archive replaceable artifacts
outside the repo, and never remove files a retained run needs to reproduce. Existing `nodes.py --prune` is not licence
to delete candidate data blindly. NBA history remains paused until S02 deliberately resumes it.

## How to judge a change

Use **TRAINING_PLAN §8** and **PLAN §6b** as the current gate. Node ablation on F1–F4 is necessary; a complete engine
needs paired player-first game tests, joint/coverage checks and integrated confirmation too. Minutes get the cheap
`minutes.py --evaluate` pass first; the team pathway uses `season_backtest.py` with per-start-date evidence.

Current serving-setting control: `20261120T162930Z_v1.3_pool_per_world_F4` (known participants, projected starters,
200 F4 games × 1,000 worlds, pool 0). Margin/total CRPS **9.415/11.723**, win log loss **0.5738**, total bias **+1.81**,
total coverage **69%**. Defence loading **0.678 v 1.685 real (40.2%)**, offence **0.727 v 1.144 (63.5%)**. The older
`20261120T133953Z_v1.3_components_F4` shares rotation tables; retain it for diagnosis, not a mixed-setting comparison.
No known-participant result proves pre-game availability forecasting. Do not repeatedly tune to the 200-game panel.

## PWA export visibility — important operational fix (22 Nov)

The first iCloud export existed but Finder set `UF_HIDDEN` (flags 32832), making it absent from Finder and the phone's
file picker despite a successful export. Clearing it made the file visible; the owner confirmed phone delivery. The
exporter now uses **non-dot staging names** (`MusNBA-export-*.partial`) and clears the hidden flag both before and after
atomic rename. `analysis/export_visibility_check.py` verifies publication preserves bytes and clears the flag. The final
new export remained visible after completion; local/Downloads copies are also explicitly unhidden. Do not restore the
old dot-prefixed staging name. `nightly_musnba.py --export-only` retries export without a new nightly.

## File map

| Files | Responsibility |
|---|---|
| `basketball_common.py` | Paths, ET/UK time, conferences/divisions, NBA franchise ids, atomic JSON, archives |
| `scripts/fetch_espn.py` | Live collection: `data/raw/espn/runs/<UTC>/`, finals `data/raw/espn/final/`, logos |
| `scripts/fetch_nbastats.py` | **D32** NBA Stats adapter (Chrome fetch headers, ~1 req/s, resumable): logs, matchups, tracking defence, pbp v3, hustle; `recent()` in the nightly |
| `scripts/nbastats.py` | **D32** crosswalk, reconciliation v ESPN, matchups in ESPN ids → `data/derived/nbastats/` (`games`, `players`, `matchups`, `pair_history`, `report.json`, `unmatched.json`) |
| `scripts/realmatch.py` | **D32** assignment on real shares (`--fit [--save --set]`), pair history (`--history`), `pair_matrix` for the engine |
| `scripts/master_fixtures.py`, `scripts/box_scores.py` | Live master fixtures; player/team game logs (DNP reasons); player registry |
| `scripts/plays.py`, `scripts/history.py` | Canonical play schema and adapters; history download and reconciliation |
| `scripts/pbp.py`, `scripts/possessions.py` | Per-period box scores and on-court seconds; segments (M2, D23 convention) |
| `scripts/rotations.py` | Stints, windows, substitutions, on-court shares; replay templates (shapes for the engine's tables) |
| `scripts/minutes.py` | **D29**: healthy roles, priority, 240 allocation, ramp, rotation share, per-world draws, projected starters, `--evaluate` |
| `scripts/matchups.py` | **D30**: soft assignment (`--fit`); `mu_columns` (soft or real θ; top-2 and deterrence outputs) shared by datasets and engine; shot types |
| `scripts/lineups.py` | Projected v actual starters per finished snapshot (nightly; D33) |
| `scripts/athletes.py`, `scripts/features.py` | Heights/weights; profiles and variants (`--defence`, `--matchup`, `--real-matchups` (REAL_MATCHUP_K, stopper, deterrence), `--shot-types`, `--body`, `--archetypes`) |
| `scripts/evaluate.py`, `scripts/nodes.py`, `scripts/train.py` | Folds; datasets (`mu_*`, top-2, deterrence, who-mismatch columns by report flags); LightGBM per node, `--final` |
| `scripts/compare.py`, `scripts/buckets.py`, `scripts/calibration.py`, `scripts/aggregate.py` | Paired node comparisons; calibration; M6a |
| `scripts/engine.py` | The engine (v1.3): `ENGINE` (`models`, `rotation`, `sims` 10,000, `pool` 0), target rotation tables, matchup inputs |
| `scripts/backtest.py`, `scripts/backtest_compare.py` | M9 (`--rotation`, `--models`, `--known-starters`, `--pool`; component loadings); paired comparison |
| `scripts/pathway.py`, `scripts/season_backtest.py` | Team engine and its walk-forward test |
| `models/*.json` | Version settings (v1.1–v1.3 promoted; v1.4c/d/e/f not promoted), matchup θ (soft `matchup_…`, real `realmatch_…`) |
| `scripts/season_stats.py`, `scripts/projection.py` | Live season stats; placeholder; `simulate_season`; `package()` (OREB/DREB/FGM/FTM distributions, multi-doubles, 5×5) |
| `scripts/nightly.py`, `scripts/views.py` | Nightly: ESPN + NBA Stats fetch → input rebuild (+ real matchups) → engine days (10k worlds) → season → snapshots → views (spotlight, duels, who-guards-whom, multi, averages, worlds, lab) |
| `scripts/serve.py`, `scripts/export_musnba.py`, `scripts/nightly_musnba.py` | Local server; static shell + bundle (`phone_record`: stripped back, D36); iCloud export |
| `scripts/webapp/` | The app; `spotlight.mjs` (headliner, breakout, leaders), `outcomes.mjs` (worlds, conditions, grouped variables), `scenario.mjs` (Scenarios, game flow, duels, Given…, drivers), `league.mjs` (standings/teams), `season.mjs` (Races/Movers/Leaders), `about.mjs` (guide) |
| `analysis/export_visibility_check.py` | Atomic export bytes/visibility regression (macOS hidden-flag check) |
| `scripts/smoke.py`, `analysis/*.mjs` | Accounting/model checks (fault run must fail); browser checks (`--only`; cases incl. game-proj, game-duels, standings-wins) |

## Commands

```sh
git status && git log --oneline -5                                    # start of session; commit + push at checkpoints
.venv/bin/python scripts/smoke.py [--fault]                           # all checks (the fault run must fail)
.venv/bin/python scripts/nightly.py [--offline] [--no-rebuild] [--engine 10000] [--ahead N]
.venv/bin/python scripts/serve.py --port 8767                         # your own review server (owner uses :8766)
node analysis/browser_check.mjs --base http://127.0.0.1:8767 [--only a,b]
.venv/bin/python scripts/fetch_nbastats.py --recent | --logs | --matchups | --ptdefend | --pbp | --hustle
.venv/bin/python scripts/nbastats.py --crosswalk --reconcile --matchups
.venv/bin/python scripts/realmatch.py --history; .venv/bin/python scripts/realmatch.py --fit [--save --set +pair_history]
.venv/bin/python scripts/features.py --out data/derived/variants/realmatch/features --defence --defence-k-scale 0.2 --matchup models/matchup_2025-12-31.json --shot-types --real-matchups data/derived/nbastats/matchups.parquet
.venv/bin/python scripts/nodes.py --features <variant>/pregame.parquet
.venv/bin/python scripts/train.py --config models/v1.3.json [--folds F4 | --final]
```

Rebuild order after new data or a parser change: history → possessions → rotations → features (default, then the
variant) → nodes → train (the nightly does the current-season part itself). The laptop: 14 cores, 48 GB; a chain build ~20 GB.
