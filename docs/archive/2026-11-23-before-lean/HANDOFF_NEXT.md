# Handoff — state and next actions

Updated **23 November 2026 — Chunk A A1 at 80%, A2 at 30%; S01–S07 remain complete**.
The preceding pushed checkpoint was **4d58ff9** (participation slices and audited live slate); use `git log -1` for the current checkpoint.

## Read this first — live handoff

- **Compute-use clarification (owner, 23 Nov; documentation-only checkpoint):** actively use the existing
  ten-process/thread allowance for every heavy workload, using measured process/inner-thread splits and
  asynchronous independent work to reduce elapsed time. Keep the combined heavy-compute count within ten,
  protect memory headroom and respect provider limits; see AGENTS §6 and TRAINING_PLAN. This is execution
  guidance, not a new candidate or scope authorisation. Baseline smoke **108/108**; documentation links
  and whitespace checked. No new experiment, model, forecast, bundle, shell or nightly was produced;
  A1/A2 progress and the next actions below are unchanged. Eight-doc review: AGENTS, HANDOFF, PLAN and
  TRAINING_PLAN updated; ENGINE_PLAN needs no design change, FINDINGS has no new experimental evidence,
  DASHBOARD_PLAN has no shipped UI change and README has no command change.
- **A1 blocked-fallback checkpoint (23 Nov ET; module NOT complete):** today's availability panel links
  eligible uncertain players to positive-/zero-minute slices of saved worlds. These are observational, not
  forced-availability branches, causal lineup forecasts or an Expected mixture. Phone bundles omit worlds
  and show the limitation. Production branches remain blocked by the unresolved representative retry/bias
  and dated-availability gates; the vector penalty candidate failed its F4 screen below. A1 remains **80%**,
  Chunk A **34.5%**, A2 **30%**, A3 **0%**. This is a safe interim dashboard improvement, not completion of
  A1 or all requested uncertainties. The owner asked to stop at the end of A1; do not silently advance to
  A2/A3 or Chunk B while its 90% gate is open. If continuing A1, define a materially new candidate or
  representative pre-origin evidence before running more experiments; do not rerun the rejected candidate.
- **Fresh live delivery:** the today-only nightly exited **0** after 68 requests, five new finals and
  zero collection failures; inputs rebuilt through 22 Nov in **228.7s**. The 23 Nov snapshot used
  **engine-v1.3**, 10 games × 10,000 worlds, and **team-pathway-v1**, 10,000 season worlds over 952 games;
  snapshot stage **1,415.78s**. Log `/tmp/musnba_a1_availability_nightly_20261123.log`. Independent
  `analysis/experiments/20261123_a1_live_slate_minutes_audit_v1.json` checked **14,700,000** minute
  values, **20,580,000** phone marginals and **200,000** team scores; 2,822/100,000 worlds had OT.
  Maximum team-quarter minute error **4.26e−14**, overtime error **2.84e−14**, marginal error **0**.
  This is accounting, not an accuracy or OT-calibration test.
- **Delivery verification:** iCloud laptop and phone bundles are **111,413,527 / 86,886,931 bytes**.
  Hosted fresh-import/offline checks passed **24/24 laptop / 23/23 phone**, including today’s model/origin
  and uncertainty limitations; measured renderer JS heap at that check **15.9 / 5.5 MiB**, not peak,
  whole-browser or device memory. Responsive interaction checks **13/13**, screenshots inspected in both
  themes/three widths; installed-shell upgrade **24/24**. Data-free Pages shell `fd367b9`, cache
  `d9ebff876348239a7a58`, is pushed and its hosted asset hash matches source. The 111/87 MB bundle sizes
  require a real phone import/memory acceptance check; iCloud export is not proof of phone import.
  Smoke **108/108**; deliberate fault **86/108** and exit 1. No per-game iCloud streaming is implemented.
  Checkpoint doc review: HANDOFF, PLAN, FINDINGS, DASHBOARD_PLAN and README changed; AGENTS standing
  rules, ENGINE_PLAN accepted design and TRAINING_PLAN cutoff/promotion rules need no change.
- **A1 90% partial — vector matched-penalty F4 screen (23 Nov ET):** the predeclared isolated candidate
  completed the fixed **200 games × 1,000 worlds** with actual-participant oracle rosters in **1,756.325s**
  at eight single-thread workers. The sum of worker peak RSS was **13.39 GB**, excluding parent, OS and
  other processes; a spot memory-pressure check during the run showed zero swap activity, not a continuous
  monitor. Independent capture accounting reconciled **98,276,074** lineup fives, **50** technicals and
  **21,730** player sample means/CRPS values across **4,346** scored player-games. Independent
  game-cluster bootstrap reconstruction matched **15** pooled metrics (maximum error **1.75e−15**) and
  established **10/10** pooled bias/coverage bounds. Against the frozen S01 control, pooled minute CRPS
  **3.566159 → 3.564896**, change **−0.001262 [−0.003540, +0.001033]**, below the **0.026341**
  seed-noise floor: the uncorrected primary screen **failed**. **67/69** non-inferiority bounds were
  established; Q3 and Q4 margin coverage were not. Pooled point CRPS change **+0.000691
  [−0.002957, +0.004274]**; team margin CRPS change **−0.041181 [−0.093283, +0.010238]**.
  Intervals are unadjusted 95% paired game-cluster bootstrap, not Holm-adjusted. Retain the current
  model: this is an F4-only oracle-roster screen, not proof either continuation is more accurate under
  actual pre-game availability. It does not show production retries are safe or complete A1's 90% rung.
  Reports `analysis/experiments/20261123_a1_vector_penalty_f4_200_v1{,_audit,_compare,_gate,_pooled_audit}.json`;
  ignored player/game rows and captures `data/derived/experiments/20261123_a1_vector_penalty_f4_200_v1*`.
  Focused tests **50/50**, smoke **107/107**, deliberate fault **86/107** and exit 1. No job remains;
  no production model, forecast, bundle or shell changed. A1 **80%**, Chunk A **34.5%**. HANDOFF, PLAN
  and FINDINGS updated; README already maps the commands, AGENTS the standing rules, ENGINE_PLAN the
  accepted design, TRAINING_PLAN the unchanged gates and DASHBOARD_PLAN the unchanged UI. Continue A1;
  the owner requested a stop only at its end.
- **A1 90% partial — candidate concurrency measurement (23 Nov ET):** after revalidating the three-game
  preflight with the worker-aware source, the same fixed **10-game × 1,000-world** F4 oracle-roster sample
  ran sequentially at four and eight single-thread workers. Elapsed times were **204.265 / 138.004s**
  (eight **32.4%** shorter); summed per-worker peak RSS **5.80 / 11.72 GB**, excluding parent, OS and
  other applications, on a **51.54 GB** physical-memory machine. A post-run memory-pressure check reported
  zero swap-ins/outs; it does not measure continuous system pressure. Independent audits each reconciled
  **4,983,286** lineup fives, **205** players, **1,025** player statistics and **1** technical; a separate
  comparison matched all world contents and game/player outputs across worker counts. Use **8** workers
  for the frozen 200-game candidate screen, reducing under competing load; total heavy threads remain capped
  at ten. Ten games are not a full-slate benchmark, accuracy result or proof that eight is globally optimal.
  Reports `analysis/experiments/20261123_a1_vector_penalty_{pilot_v2,pilot_v2_audit,scale4_v1,scale4_v1_audit,scale8_v1,scale8_v1_audit,scaling_v1_compare}.json`.
  The earlier pilot's source hashes refer to checkpoint **fd9091e**; the worker-aware source and new
  reports must be kept together. Focused tests **50/50**, smoke **107/107**, deliberate fault **86/107**
  and exit 1. No job remains; production model, forecast, bundle and shell unchanged. A1 **80%**, Chunk A
  **34.5%**. HANDOFF, PLAN, FINDINGS and README updated; AGENTS (standing rules), ENGINE_PLAN (design),
  TRAINING_PLAN (gates) and DASHBOARD_PLAN (shipped UI) require no change.
- **Next A1 90% concurrency measurement, frozen before runs:** repeat the vector candidate's verified
  F4 preflight under fresh names after adding an explicit worker count. Then run the same first **10**
  ordered fixed-panel games at **1,000 worlds/game**, first with **4** and then **8** single-thread
  workers, never concurrently. Record elapsed time, world/accounting audit and each worker's peak resident
  set; sum per-worker peaks as a conservative bound for those processes, explicitly excluding the parent,
  operating system and unrelated workloads. Select **8** only if it improves observed throughput and
  leaves reasonable physical-memory headroom; otherwise use **4**. Both experiments are runtime/wiring
  diagnostics on fixed oracle rosters, not feature-selection or accuracy tests. Never exceed ten total
  compute threads, never overwrite prior captures or reports, and preserve the original source at its
  preceding commit. The resulting 200-game run remains the previously frozen F4 diagnostic.
- **A1 90% partial — vector matched-penalty wiring and real-outcome preflight (23 Nov ET):** the isolated
  vector candidate reused the audited matched continuation without changing its fingerprinted source.
  Its **1,000** single-world traces matched the independently audited saved references, including **190**
  failed-first-seed states, **490,824** lineup fives and **331** technicals. A fixed synthetic **100-world**
  vector run replayed identically and reconciled **48,968** fives and **26** technicals. The no-exception
  check matched both worlds; two earlier four-world preflights exhausted, as expected for this selected
  short roster, so they were not treated as no-exception samples. Focused two-world tests also check that
  an exhaustion changes only its own lineup/score at the repair step. The three fixed F4 oracle-roster games,
  **1,000** worlds each, ran in **71.0s** with four single-thread workers; independent accounting checked
  **3,000** worlds, **1,473,288** lineup fives, **64** players and **320** player means/CRPS values, with
  **0** technical events. The paired comparison against S01 has only three games and explicitly reports
  insufficient samples; it is wiring, not a real-outcome gain. Vector engine draws share RNG, so distinct
  world paths are not claimed independent after event divergence. Reports
  `analysis/experiments/20261123_a1_vector_matched_penalty_probe_v1.json` and
  `analysis/experiments/20261123_a1_vector_penalty_pilot_v1{,_audit,_compare}.json`; ignored pilot
  captures and output parquet are under `data/derived/experiments/20261123_a1_vector_penalty_pilot_v1*`.
  Focused tests **49/49**, smoke **107/107**, intentional fault **86/107** and exit 1. No job remains;
  no production model, forecast, bundle or shell changed. A1 **80%**, Chunk A **34.5%**. HANDOFF, PLAN,
  FINDINGS and README updated; AGENTS (standing rules), ENGINE_PLAN (design), TRAINING_PLAN (gates) and
  DASHBOARD_PLAN (shipped UI) require no change. Next: measure safe worker/memory scaling and then run the
  frozen 200-game F4 candidate only with a fresh source/output namespace; independently audit and compare
  to the retained S01 control. Reject or retain based on the frozen player-first gates, not this pilot.
  The measured worker choice is **8**. The first fixed 200-game candidate screen is complete and failed
  the registered primary screen above; do not rerun it unchanged as a route to promotion. Its command,
  using a fresh name if reproduction is necessary:
  `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv/bin/python -u analysis/a1_vector_penalty_backtest.py --jobs 8 --name <fresh-200-game-name>`.
  It is not resumable: preserve an interrupted world directory and use a new name after inspection.
  Independently audit the complete report with `analysis/a1_vector_penalty_backtest_audit.py`, then run
  `scripts/a1_compare.py 20261122T022323Z_a1_s01_control <fresh-200-game-name> --game-ids data/derived/experiments/20261122_a1_s03_f4_game_ids.json --output analysis/experiments/<fresh-comparison>.json`
  and the existing registered non-inferiority/seed-noise checks. Never mistake the diagnostic F4 result
  for multi-fold or protected-final promotion.
- **Next A1 90% matched-penalty vector candidate protocol, frozen before implementation:** the measured
  six-player retry shifts make blind replacement unsuitable as an assumed neutral repair. Test a separate
  research-only vectorized D29 branch repair with the already studied foul-penalty continuation: replace
  fouled-out players while five eligible remain; when fewer than five remain, retain only the necessary
  currently on-court disqualified players and assess the separately seeded technical for the disqualifying
  and subsequent fouls. Never revive a removed player, never hide invalid initial rosters or unrelated
  errors, and preserve the original no-exception branch behavior and random streams. Do not edit the
  completed experiments' fingerprinted source; create a new isolated candidate. First prove equality to
  the independently replayed single-world matched reference for fixed surviving and exhausted seeds,
  then test multi-world isolation, lineups, box/score/technical accounting and deterministic replay.
  Validate a fixed three-game paired backtest against same-seed controls before attempting the existing
  fixed **200-game F4** panel, **1,000 worlds/game**, actual-participant oracle rosters and earlier-fold
  fitted artifacts. Compare player tiers/minutes/points/rebounds/assists/3PM first, then team scores,
  using the existing game-clustered A1 comparison and preregistered uncertainty/non-inferiority bounds.
  The F4 screen is diagnostic, not promotion: no F1–F3 confirmation, protected final outcomes, live
  forecasts or production wiring. If equivalence, accounting, cutoff, finite-output, runtime or the
  paired screen fails, retain the accepted model, record the failure and do not claim a validated scenario.
  Freeze fresh input/model/source fingerprints and output namespaces before execution. This is a
  continuation assumption, not proof of the unknowable no-exception outcome or a real-world injury model.
- **A1 90% partial — real-retry 10k scale (23 Nov ET):** the selected F4 six-player synthetic
  oracle-roster run combined the previously audited **1,000** slots with **9,000** new slots, accepting
  **10,000** worlds after **2,330** typed rejections (including **1,893** failed first attempts).
  Independent replay checked all accepted and rejected attempts and all matched first-failure continuations:
  **4,883,622 / 4,904,688** retry/continuation fives and **3,235** continuation technicals. Retry versus
  continuation total averaged **223.897 / 224.980**, difference **−1.083 [−1.297, −0.873]**; player
  `4431714` minutes **36.891 / 37.482**, difference **−0.591 [−0.663, −0.520]**. These are unadjusted
  paired-slot 95% percentile bootstrap intervals (5,000 resamples). New generation took **1,942.686s**
  at ten workers, excluding the previous 1,000, which took **233.798s** at eight workers; independent
  full replay and bootstrap took **834.285s** at ten workers. Neither is a measured full-slate runtime.
  The clean-stop/resume pilot matched **200** new first/accepted captures, failure states, seeds and
  rejection order against an uninterrupted run; its resumed **1,200**-slot run was independently replayed.
  Orphans and non-contiguous partial batches fail closed; this is a single-operator clean-stop protocol,
  not a guarantee of resuming a hard-interrupted batch. Reports
  `analysis/experiments/20261123_a1_retry_scale_{full_v1,full_v1_audit,resume_pilot_v1,resume_pilot_v1_audit,control_pilot_v1,resume_compare_v1}.json`;
  ignored captures `data/derived/experiments/20261123_a1_retry_scale_{full_v1,resume_pilot_v1,control_pilot_v1}/`.
  This is one selected stress case and one continuation assumption, not a population rate, prediction
  test or production gate. It strengthens the evidence that blind retry can change distributions. Focused
  tests **32/32**, smoke **107/107**, deliberate fault **86/107** and exit 1. No job remains; no production
  model, forecast, bundle or shell changed. A1 **80%**, Chunk A **34.5%**. HANDOFF, PLAN, FINDINGS and
  README updated; AGENTS (standing rules), ENGINE_PLAN (design), TRAINING_PLAN (gates) and DASHBOARD_PLAN
  (shipped UI) require no change. Continue A1; the owner requested a stop only at its end.
- **Next A1 90% real-retry scale protocol, frozen before implementation:** extend the independently audited
  1,000-slot actual-retry F4 stress above to **10,000 accepted slots**, preserving the first 1,000 saved
  outcomes and seed scheme. Generate slots in ordered 100-world batches with at most ten single-thread
  workers. Keep the ten-attempt per-slot limit and cap total rejected attempts at **5,000**; a cap or
  unclassified error fails explicitly, never returns a partial 10k result. Persist every first/accepted
  capture and rejection, source hashes and complete per-batch records; a restart may use only an independently
  replayed contiguous complete prefix and must reject orphan/partial files. Before the full run, compare an
  uninterrupted two-new-batch run against a clean stop after one new batch and resume, with matching saved
  captures, seeds, failure states and rejection order. Independently audit all final slots and replay accepted,
  rejected and matched first-failure worlds; preserve per-slot identities and paired player/team metrics.
  Report runtime, rejections and unadjusted 5,000 paired-slot bootstrap intervals; this remains a selected
  synthetic six-player roster and one continuation assumption, not a population rate, accuracy test,
  full-slate benchmark, production gate or permission to expose controls. Use fresh namespaces and never
  overwrite partial files; no protected actual outcomes or historical forecasts.
- **A1 actual retry pilot and full comparison (23 Nov UTC):** isolated paired retry implementation
  and auditor passed **34/34** focused tests. The 20-slot pilot produced **20** accepted worlds, **7**
  rejections and **4** first-seed exhaustions in **11.0s**; independent replay checked all **20** accepted
  worlds, all **7** rejected attempts and **4** matched failure continuations (**9,772 / 9,706** retry /
  paired lineup fives and **4** technicals), audit **8.459s**. Reports
  `analysis/experiments/20261123_a1_real_retry_paired_pilot_v1{,_audit}.json`, logs
  `/tmp/musnba_a1_real_retry_paired_pilot_v1{,_audit}.log`, ignored captures
  `data/derived/experiments/20261123_a1_real_retry_paired_pilot_v1/`. The predeclared **1,000-slot**
  generation finished with **230** rejections (**190** failed first seeds) in **233.798s**; its first **20** slots matched the pilot's
  first/accepted captures, seeds, failures and retry records. Log `/tmp/musnba_a1_real_retry_paired_full_v1.log`.
  Generation command:
  `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -u analysis/a1_real_retry_paired.py --worlds-dir data/derived/experiments/20261123_a1_real_retry_paired_full_v1 --output analysis/experiments/20261123_a1_real_retry_paired_full_v1.json`.
  It is not resumable: on failure retain its partial directory/log and use a fresh namespace after inspection.
  Independent audit finished in **103.319s**, replaying all **230** rejections, **1,000** accepted worlds
  and **190** first-failure continuations; it checked **488,802 / 490,824** retry/paired fives and **331**
  technicals. Retry versus continuation total **224.379 / 225.183**, difference **−0.804**
  [**−1.433, −0.184**]; home player `4431714` minutes **37.160 / 37.685**, difference **−0.525**
  [**−0.746, −0.300**]. Intervals are unadjusted 95% paired-slot percentile bootstrap, 5,000 draws.
  Audit log `/tmp/musnba_a1_real_retry_paired_full_v1_audit.log`; reproduce with a fresh output using:
  `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -u analysis/a1_real_retry_paired_audit.py analysis/experiments/20261123_a1_real_retry_paired_full_v1.json --output analysis/experiments/20261123_a1_real_retry_paired_full_v1_audit.json`.
  Reports `analysis/experiments/20261123_a1_real_retry_paired_full_v1{,_audit}.json`. This is one selected
  synthetic oracle-roster case and continuation assumption, not a population rate, actual-outcome score,
  10k run or production gate. Focused tests **34/34**, smoke **107/107**, deliberate fault **86/107**
  and exit 1 (`/tmp/musnba_a1_real_retry_{smoke,fault}_v1.log`). No job remains; production model,
  forecast and bundle unchanged. A1 **80%**, Chunk A **34.5%**. HANDOFF, PLAN, FINDINGS and README
  updated; AGENTS (standing rules), ENGINE_PLAN (design), TRAINING_PLAN (gates) and DASHBOARD_PLAN
  (shipped UI) require no change. Continue A1; the owner requested a stop only at its end.
- **Next A1 90% actual retry pilot, frozen before implementation:** on the previously selected F4
  six-player synthetic-absence game `401811022`, run **1,000** independent world slots with fixed base seed
  `20261123`, eight single-thread processes and the existing deterministic retry coordinator. Retry only
  the typed D29 fewer-than-five-eligible failure; other errors propagate. Cap at **10** attempts per slot and
  **500** rejections overall; crossing either limit fails, not a partial success. On each slot's first
  seed, preserve its D29 survivor capture or, if exhausted, its complete original failure state/trace and
  a matched D29-plus-foul-penalty continuation from that same seed. Save every accepted retry capture,
  rejected seed/reason and paired first-seed continuation; independently verify seeds, no unclassified
  errors, lineup/box/minute/technical accounting, state identities and unchanged first-seed survivors.
  Compare actual accepted retry outcomes against paired first-seed continuations for all six available home
  players' points/minutes and home/away/total/margin using **5,000** paired slot-bootstrap percentile 95%
  intervals (seed 20261123, unadjusted). This deliberately extreme oracle-roster case and explicit penalty
  assumption do not establish an NBA failure rate, production retry gate or real-result predictive accuracy.
  Start with a small wiring pilot and use fresh immutable paths; 1,000 accepted slots are not a 10k acceptance
  test. No production integration, historical forecast backfill or protected-season actual outcomes.
- **A1 90% partial — complete earlier-fold screen accounting (23 Nov UTC):** the three fixed F1/F2/F3
  200-game screens contained **1,900 / 1,900 / 1,790** attempts and **1 / 0 / 0** exhaustions. Reusing
  the independently audited matching F1 continuation only for its lone failure, survivor-minus-all pooled
  total means are **−0.01789 / 0 / 0** points; paired game-cluster bootstrap 95% intervals
  **[−0.05715, 0] / [0, 0] / [0, 0]**, unadjusted 5,000 resamples. An independent reconstruction checked
  **5,590** attempted captures, 12 score estimates, and all seven home players in the affected branch
  (four survivors versus five continuations). The latter are far too few to establish an individual effect.
  Generation/audit took **12.446 / 3.241s**, each one thread. Report and audit:
  `analysis/experiments/20261122_a1_dated_screen_selection_v1{,_audit}.json`; logs
  `/tmp/musnba_a1_dated_screen_selection_v1{,_audit}.log`. These five-draw oracle-roster screens and one
  assumed continuation are not predictive tests or population gates; zero observed failures does not imply
  zero risk. Focused tests **40/40**, smoke **107/107**, intentional fault **86/107** and exit 1
  (`/tmp/musnba_a1_screen_selection_{smoke,fault}_v1.log`). No protected outcomes scored, no running job
  and no production model, forecast or bundle change. A1 **80%**, Chunk A **34.5%**. HANDOFF, PLAN,
  FINDINGS and README updated; AGENTS (standing rules), ENGINE_PLAN (design), TRAINING_PLAN (gates) and
  DASHBOARD_PLAN (shipped UI) require no change. Continue A1; the owner requested a stop only at its end.
- **Next A1 90% research accounting, specified before calculation:** retrospectively reconcile the
  already-audited F1/F2/F3 200-game, five-draw-per-feasible-branch screens with their saved D29 captures.
  Reuse the independently audited matching F1 continuation for the sole original exhausted attempt;
  all other screen attempts already survived and are unchanged by this continuation. Validate source,
  manifest and capture hashes, game/branch/draw/seed identities and saved accounting; do not generate
  replacement seeds, alter any historical files or score actual outcomes. For each fold report the pooled
  survivor-versus-all continuation home/away/total/margin means and, for the affected F1 branch, every
  available home player's points and minutes. Use 5,000 paired game-cluster bootstrap replicates, seed
  20261122, with percentile intervals and no multiplicity correction; zero failures means identical samples,
  not zero underlying selection. Independently reconstruct the aggregates and retain both reports. This is
  post-hoc descriptive accounting on oracle rosters and only five attempts per branch; the lone failure makes
  uncertainty especially fragile. It is not representative availability, real-outcome prediction, a retry
  gate or permission to expose the research controls. Use fresh output names and keep earlier reports intact.
- **A1 90% partial — earlier-fold matched continuations (23 Nov UTC):** on the three frozen selected
  seven-home-player synthetic branches below, F1/F2/F3 generated and audited **1,000** attempts each.
  Original D29 exhausted **22 / 2 / 7** times; generation matched each full failure state/trace before
  continuation and reproduced all **978 / 998 / 993** survivor trajectories. Independent replay and
  saved-world accounting checked **491,390 / 475,010 / 478,362** fives and **27 / 2 / 8** technicals.
  Survivor-minus-all total means were **−0.240 / −0.049 / −0.004** points; unadjusted 95% paired-seed
  intervals **[−0.432, −0.070] / [−0.147, 0.000] / [−0.078, 0.075]**. Player estimates and intervals
  are in the audits. Generation **172.860 / 165.957 / 178.206s**, audit **89.038 / 88.598 / 89.825s**;
  eight one-thread workers, folds sequential. These selected oracle cases and one continuation assumption
  do not establish population failure rates, real-world forecast bias or a predictive/promotion gate.
  Reports `analysis/experiments/20261122_a1_dated_matched_f{1,2,3}_{pilot,full}_v1{,_audit}.json`;
  ignored captures `data/derived/experiments/20261122_a1_dated_matched_f{1,2,3}_{pilot,full}_v1/`;
  full logs `/tmp/musnba_a1_dated_matched_f{1,2,3}_full_v1.log`. Focused tests **47/47**, smoke
  **107/107**, deliberate fault **86/107** and exit 1 (`/tmp/musnba_a1_dated_matched_{smoke,fault}_v1.log`).
  No job remains running; no protected-season outcomes were scored; production model, forecasts and bundles
  unchanged. A1 **80%**, Chunk A **34.5%**. Documentation review: HANDOFF, PLAN, FINDINGS and README
  updated; AGENTS (standing rules), ENGINE_PLAN (design), TRAINING_PLAN (gates) and DASHBOARD_PLAN (shipped
  UI) require no change. Continue A1; the owner requested a stop only at its end.
- **A1 90% partial — matched-state continuation (23 Nov UTC):** an isolated D29 policy now uses the existing
  five-player foul-penalty assumption only after D29 would exhaust, with an independent technical-FT stream.
  On the same selected synthetic F4 six-player case, **798/798** previously successful saved trajectories
  matched exactly; **202/202** failure states matched the complete original engine state, five and prior trace
  before continuation. All **1,000** attempts completed in **164.8s** with four single-thread workers.
  Separate saved-file audit re-simulated all 202 original failure states and checked **492,616** lineup fives,
  **371** technicals and all survivor hashes in **93.018s**. Survivors averaged **223.54** total points versus
  **225.19** for all attempts under this explicit continuation, difference **−1.66** with unadjusted paired-seed
  95% bootstrap interval **[−2.28, −1.07]**. One home player's minutes averaged **36.82 vs 37.33**, difference
  **−0.51** [**−0.71, −0.31**]. This quantifies selection under *that* continuation for one intentionally
  selected oracle-roster case, not an NBA rate, population accuracy, unknowable no-exception outcomes or a
  production retry/promotion gate. Reports `analysis/experiments/20261122_a1_matched_penalty_{pilot,full}_v1{,_audit}.json`,
  log `/tmp/musnba_a1_matched_penalty_full_v1.log`, ignored captures
  `data/derived/experiments/20261122_a1_matched_penalty_{pilot,full}_v1/`.
  The source uses its own explicit exception implementation to preserve previously fingerprinted S06 code;
  it remains research-only. Focused tests **35/35**, smoke **107/107**, deliberate fault **86/107** and exit 1
  (`/tmp/musnba_a1_matched_penalty_{tests,smoke,fault}_v1.log`). No protected-season outcomes were scored, and
  accepted models, live forecasts and bundles did not change. A1 **80%**, Chunk A **34.5%**. Documentation
  review: HANDOFF, PLAN, FINDINGS and README updated; AGENTS (standing rules), ENGINE_PLAN (design),
  TRAINING_PLAN (gates) and DASHBOARD_PLAN (shipped UI) need no changes.
- **A1 90% partial — full-game selected policy comparison (23 Nov UTC):** using the same fixed F4
  six-player synthetic-absence case, S06 completed the **798** original D29-survivor seeds in **100.1s**
  with four single-thread workers; the earlier **202** D29-rejected seeds were reused. Independent
  saved-file accounting checked all **1,000** S06 worlds, **500,536** lineup fives and **325** technical
  events, plus all **798** D29 survivors. D29 survivors averaged **223.54** total points versus **225.86**
  for all S06 worlds, difference **−2.33** (unadjusted paired-seed bootstrap 95% interval **[−3.74, −0.91]**);
  home-player minutes differed by **−1.57 to +1.47** depending on player. These are different policies and
  random paths on one selected oracle roster: the difference does **not** isolate retry bias or establish a
  league rate, accuracy or a promotion gate. Reports `analysis/experiments/20261122_a1_f4_six_roster_full_v2{,_audit}.json`,
  log `/tmp/musnba_a1_f4_six_roster_full_v2.log`, ignored captures
  `data/derived/experiments/20261122_a1_f4_six_roster_full_v2/`. The preserved `_v1` generation completed
  798 worlds but its audit failed on absolute/relative path comparison; the corrected auditor changed the
  frozen source hash, so `_v1` is invalid and `_v2` was generated afresh. Focused tests **13/13**, smoke
  **107/107**, intentional fault **86/107** and exit 1. No protected-season outcomes were scored, no
  accepted model or served bundle changed. A1 **80%**, Chunk A **34.5%**. Documentation review: HANDOFF,
  PLAN, FINDINGS and README updated; AGENTS (standing rules), ENGINE_PLAN (design and decisions),
  TRAINING_PLAN (evaluation gates) and DASHBOARD_PLAN (shipped behaviour) need no changes.
- **A1 90% matched-state diagnostic, frozen before implementation:** test a separate research-only D29
  continuation which is identical to `BranchFoulOutPolicy` until the first fewer-than-five-eligible state,
  then applies the previously specified S06 five-player foul-penalty exception without S06's substitution
  model. Retain only the minimum currently on-court disqualified players; never introduce an unavailable
  or previously removed player. Use the existing specified independent technical-FT stream, trace the full
  roster's fouls, and independently audit lineups, technicals, scores and minutes. Verify all **798** original
  survivor worlds reproduce their full saved outputs and traces and all **202** original rejected attempts
  reach the same failure period and clock before continuing. Then compare the 798 survivor distribution to
  all 1,000 continuation worlds for the same prespecified score and six-player outcomes with seed-cluster
  bootstrap intervals. This continuation is a candidate assumption, not the unknowable no-exception
  counterfactual, real availability, a predictive result or permission to promote. If exact survivor/failure
  identity or accounting fails, stop and retain the evidence. Use no protected-season results.
- **A1 90% earlier-fold matched-state cases, frozen before new draws:** take F1's sole observed exhausted
  branch `401585382/sits` (selected because it failed), and in F2/F3 take the lowest game ID among feasible
  sits branches having the smallest observed home participant count (`401705024/sits`, `401810091/sits`).
  Each starts with seven available home players after the synthetic absence. Use their audited dated
  body-free diagnostic engines, source fingerprints and original single-world seed scheme; draws 0–4
  must reproduce the existing screen, then extend the same scheme through draw 999. Independently run
  ordinary D29 and the matched penalty continuation for each seed; check survivor capture identities and
  full state/trace at each failure, persist all continuations and audit their fives, technicals and scores.
  Compare survivors with all continuations for home/away/total/margin and each available home player's
  points and minutes, with 5,000 unadjusted seed-bootstrap intervals. Run one fold at a time with at most
  eight single-thread workers and fail on unclassified errors. These are three deliberately selected
  synthetic oracle-roster cases with different dated diagnostic models, not representative fold estimates
  or a production/promotion gate. Zero failures gives zero observed selection, not zero population risk.
- **A1 90% partial — earlier-fold screens complete (23 Nov UTC):** fixed **200**-game F1/F2/F3 panels
  respectively had **1 / 0 / 0** exhausted attempts out of **1,900 / 1,900 / 1,790**, **0 / 0 / 0**
  invalid allocations and **20 / 20 / 42** unsupported missing-position branches. F1's game-cluster
  95% bootstrap interval for its attempt fraction is **[0, 0.001667]** (5,000 resamples); zero observed
  in F2/F3 does not prove zero risk. The dated body-free diagnostic engines differ from v1.3 and F4,
  actual-participant rosters are oracle inputs, and five draws per feasible branch are not a league rate,
  availability calibration or full-game retry-bias gate. Eight one-thread workers per fold took
  **170.774 / 165.973 / 161.707s** sequentially. Separate audits checked **1,899 / 1,900 / 1,790** saved
  worlds and **458,247 / 457,952 / 439,772** lineup snapshots. Reports
  `analysis/experiments/20261122_a1_dated_f1_screen_v2{,_audit}.json` and
  `analysis/experiments/20261122_a1_dated_f{2,3}_screen_v1{,_audit}.json`; corresponding logs
  `/tmp/musnba_a1_dated_f1_screen_v2.log` and `/tmp/musnba_a1_dated_f{2,3}_screen_v1.log`, captures
  in matching ignored `data/derived/experiments/` folders. No screen job remains running.
  F1 v1 failed on missing positions and remains partial; see frozen correction below. Focused tests
  **11/11**, smoke **107/107**, deliberate fault **86/107** and exit 1
  (`/tmp/musnba_a1_dated_screens_{smoke,fault}_v1.log`). HANDOFF, PLAN, FINDINGS and README record the
  work; AGENTS, ENGINE_PLAN, TRAINING_PLAN and DASHBOARD_PLAN need no changes: rules, accepted engine,
  evaluation gates and shipped UI remain unchanged. No protected-season outcomes were scored; production
  model, forecasts and bundles unchanged. A1 **80%**, Chunk A **34.5%**.
- **A1 90% partial — dated-fold preparation (23 Nov UTC):** F1/F2/F3 isolated S02-style body-free
  engines are fitted through **2023-12-31 / 2024-12-31 / 2025-09-30**. Each has all **16** cached node
  datasets independently accounted and **18** model artifacts fingerprinted. Preparation took
  **245.971 / 283.903 / 336.321s**, including cache builds/audits, using eight fitting threads and one
  BLAS thread, sequentially. A one-game F1 wiring check produced both five-attempt branches. Reports
  `analysis/experiments/20261122_a1_dated_f{1,2,3}_exhaustion_v1{,_nodes_audit}.json`, logs
  `/tmp/musnba_a1_dated_f{1,2,3}_exhaustion_v1.log`. No fold job remains running. Each namespace refuses
  overwrite; interrupted files require inspection and a fresh name. The F1–F3 diagnostic engines differ
  from accepted v1.3 and the genuinely dated injury-report gate remains unavailable. No protected-season
  outcomes were scored. Focused tests **10/10**, smoke **107/107**, deliberate fault **86/107** and exit 1
  (`/tmp/musnba_a1_dated_prepare_{smoke,fault}_v1.log`). HANDOFF, PLAN, FINDINGS and README record the work;
  AGENTS, ENGINE_PLAN, TRAINING_PLAN and DASHBOARD_PLAN need no changes: rules, accepted engine, gates and
  shipped UI remain unchanged. A1 **80%**, Chunk A **34.5%**. The predeclared conditional-roster screens
  and saved-file audits subsequently completed, as recorded above.
- **A1 90% partial — halftime selection diagnostic (23 Nov UTC):** replayed all **1,000** original
  six-player D29 attempts, matching the **798** complete-world digests and **202** exact failure reasons.
  At halftime, the **798** eventual survivors averaged **9.391** home fouls versus **9.888** over all
  attempts; survivor-minus-all **−0.497**, unadjusted attempt-bootstrap 95% interval **[−0.600, −0.396]**.
  Home players with at least three fouls averaged **1.243 vs 1.409**, difference **−0.166**
  **[−0.202, −0.131]**. Halftime home score difference was **−0.304 [−0.569, −0.044]**; away score
  **−0.044 [−0.311, 0.222]**. The four percentile intervals are not multiplicity-adjusted.
  A separate saved-file audit reconciled all **1,000** halftime player/team minute, point and foul arrays,
  seeds, outcomes and estimates in **3.106s**; generation took **98.301s**, six one-thread workers.
  This directly demonstrates selection of *pre-failure* states in one extreme selected oracle-roster case,
  not the missing full-game counterfactual, a league rate or a predictive gate. Failed final outcomes remain
  unknown; do not wire retry to production on this evidence. Reports
  `analysis/experiments/20261122_a1_f4_six_roster_halftime_v1{,_audit}.json`, ignored captures
  `data/derived/experiments/20261122_a1_f4_six_roster_halftime_v1/`, log
  `/tmp/musnba_a1_f4_six_roster_halftime_v1.log`. Focused tests **8/8**, smoke **107/107**, intentional
  fault **86/107** and exit 1 (`/tmp/musnba_a1_halftime_{smoke,fault}_v1.log`). HANDOFF, PLAN, FINDINGS
  and README record the work; AGENTS, ENGINE_PLAN, TRAINING_PLAN and DASHBOARD_PLAN need no changes:
  standing rules, accepted engine, evaluation gates and shipped UI remain unchanged. No protected-season
  outcomes were scored; accepted model and bundles remain unchanged. A1 **80%**, Chunk A **34.5%**.
- **A1 90% partial — six-player S06 comparison (23 Nov UTC):** the separate selected-timeout/foul-penalty
  policy completed **202/202** single-world attempts using the exact seeds rejected by the D29 repair on the
  selected synthetic-absence F4 case. **46** worlds had technicals, **85** technical events total; four
  one-thread workers took **31.717s**. Independent saved-file audit reconciled all **202** seeds,
  **101,962** lineup fives and all technical records in **1.237s**. The first audit invocation transiently
  reported missing NumPy; a subsequent interpreter import and the repeat audit succeeded without installing
  or changing dependencies. This is a deliberately selected extreme oracle roster, not a league rate or
  predictive/retry-bias result: policies and random paths differ, and **156/202** S06 worlds had no
  technical at all, so their states are not matched to D29's rejected states.
  Reports `analysis/experiments/20261122_a1_f4_six_roster_penalty_v1{,_audit}.json`, ignored traces
  `data/derived/experiments/20261122_a1_f4_six_roster_penalty_v1/`, log
  `/tmp/musnba_a1_f4_six_roster_penalty_v1.log`. Focused tests **6/6**, smoke **107/107**, deliberate
  fault **86/107** and exit 1 (`/tmp/musnba_a1_six_penalty_{smoke,fault}_v1.log`). HANDOFF, PLAN,
  FINDINGS and README record the work; AGENTS, ENGINE_PLAN, TRAINING_PLAN and DASHBOARD_PLAN need no changes:
  standing rules, accepted engine, evaluation gates and shipped UI remain unchanged. No protected-season
  outcomes were scored; accepted model and bundles remain unchanged. A1 **80%**, Chunk A **34.5%**.
- **A1 90% partial — targeted six-player exhaustion (23 Nov UTC):** after the F4 screen, deliberately
  selected its sole seven-home-participant game `401811022`, then synthetically sat the top projected
  home-minute player. Of **1,000** independent single-world attempts with the isolated D29 repair,
  **202** exhausted eligible home players and **798** completed. Failures occurred in periods
  **3/4/5/6 = 23/173/5/1**. Ten one-thread workers took **64.486s**. Separate replay checked all seeds,
  **798** saved captures and **195,435** lineup snapshots in **4.32s**; rejected trajectories themselves
  were not saved. Reports `analysis/experiments/20261122_a1_f4_six_roster_v1{,_audit}.json`, per-attempt
  records and captures ignored in `data/derived/experiments/20261122_a1_f4_six_roster_v1/`. This is a
  selected extreme oracle roster with a synthetic absence, **not** an NBA rejection rate or proof of retry
  bias. It does show retries can discard a substantial, game-state-selected fraction rather than merely
  occasional random failures. Subsequent distinct-S06 and matched-continuation comparisons are recorded
  above; the candidate remains isolated and their limitations still apply.
  The served model and bundles are unchanged; no protected-season actual outcomes were scored. Focused
  tests **4/4**, smoke **107/107**, deliberate `--fault` **86/107** and exit 1. HANDOFF, PLAN, FINDINGS
  and README record the work; AGENTS, ENGINE_PLAN, TRAINING_PLAN and DASHBOARD_PLAN need no changes because
  standing rules, accepted engine, evaluation gates and shipped UI did not change.
- **A1 90% partial — fixed F4 exhaustion screen (23 Nov UTC):** the 200-game S01 development panel,
  using oracle actual-participant rosters and a synthetic top-home-player plays/sits split, completed **2,000**
  separately seeded attempts (five per branch), with **0** invalid initial allocations and **0** typed
  exhaustion events. Ten one-thread workers took **134.686s**, including startup. A separate saved-file replay
  checked all **2,000** worlds and **491,500** lineup snapshots, seeds, hashes and accounting in **3.488s**.
  Home participant sets contained **7–15** players; away **7–14**. These artificially conditioned rosters
  are not pre-game availability, the screen is F4 only with five attempts per branch, and zero observed
  exhaustions does not establish a retry rate, unbiasedness or production readiness. Failed trajectories
  were not retained because none occurred. Reports
  `analysis/experiments/20261122_a1_f4_exhaustion_v1{,_audit}.json`; per-game detail and traces are ignored in
  `data/derived/experiments/20261122_a1_f4_exhaustion_v1/`. **7/7** focused screen/retry/audit tests,
  smoke **107/107** and deliberate fault **86/107** with exit 1 passed; logs
  `/tmp/musnba_a1_f4_exhaustion_{smoke,fault}_v1.log`. HANDOFF, PLAN, FINDINGS and README record the work;
  AGENTS, ENGINE_PLAN, TRAINING_PLAN and DASHBOARD_PLAN need no changes because standing rules, accepted
  engine, evaluation gates and shipped UI did not change.
  No protected-season actual outcomes were scored; accepted models and served forecasts remain unchanged.
- **A1 90% partial — short-roster evidence (23 Nov UTC):** across the three saved research games'
  **80,000** completed branch worlds, every team started with at least **12** available players and finished
  with at least **9** eligible after six-foul disqualifications. In each branch/team cell, **842–2,021 / 10,000**
  worlds had at least one simulated six-foul player. Thus those captures do **not** stress the fewer-than-five
  failure motivating retry; completed batches alone cannot count failed attempts. Branch-specific uncalibrated
  weights and full counts are retained in `analysis/experiments/20261122_a1_branch_roster_pressure_v1.json`.
  This is simulation accounting, not an NBA injury/foul-out rate or predictive gate; no protected actual
  outcomes were scored, and no forecast or model changed. Continue representative earlier-fold and bias work.
  Focused branch tests **9/9**, smoke **107/107**, deliberate fault **86/107** and exit 1
  (`/tmp/musnba_a1_pressure_{smoke,fault}_v1.log`). HANDOFF, PLAN, FINDINGS and README record the audit;
  AGENTS, ENGINE_PLAN, TRAINING_PLAN and DASHBOARD_PLAN need no changes because standing rules, accepted
  engine, evaluation gates and shipped UI did not change.
- **A1 90% partial — multi-game branch runtime/accounting (23 Nov UTC):** independent manifest/box
  accounting rechecked **80,000** research worlds across **3** games and **8** branches, including unavailable
  players and exact weights; **19,437,436** recorded lineup snapshots. Branch-time sums were
  **626.4 / 1,201.5 / 616.1s** for the three jobs, excluding startup; the jobs were run concurrently with
  three numerical threads each. Original logs and hashes are preserved in
  `analysis/experiments/20261122_a1_branch_{033,034,035}_runtime_v1.txt`; independent report
  `analysis/experiments/20261122_a1_branch_runtime_audit_v2.json`. A malformed copied log failed without
  writing an output. These timings do not establish full-slate elapsed time, memory, retry rates or accuracy;
  some captures began post-tip and are not publishable forecasts. No model or bundle changed.
  Existing branch regressions **8/8**, smoke **107/107**, deliberate fault **86/107** and exit 1
  (`/tmp/musnba_a1_branch_runtime_{smoke,fault}_v1.log`). HANDOFF, PLAN, FINDINGS and README record the audit;
  AGENTS, ENGINE_PLAN, TRAINING_PLAN and DASHBOARD_PLAN need no changes because standing rules, accepted
  engine, evaluation gates and shipped UI did not change.
- **A1 90% partial — isolated restart (23 Nov UTC):** an opt-in fixed-game capture now resumes only a
  contiguous complete batch prefix after checking run configuration/source fingerprints and independently
  auditing all saved seeds, retries, player/lineup accounting and hashes. An uninterrupted and clean-stopped
  then resumed **200-world** F4 run matched all hashes, seeds and the one injected rejection; each audited
  **50,817** lineup snapshots. Control generation took **20.235s**, resumed second invocation **12.414s**
  (excluding the first invocation and prefix audit), not a 10k or slate estimate. A deliberately corrupted
  temporary batch was rejected before further simulation; incomplete/gapped/config-changed prefixes fail in
  focused tests. This was a clean stop after a whole batch, not a hard kill mid-write. Partial files fail closed
  for manual inspection; concurrent resume operators are not coordinated and must not run. The prior pilot's
  `scripts/projection.py` hash changed under D50, so the first attempted reuse failed safely; fresh
  fingerprinted provenance and pilot were generated rather than relaxing that check.
  Reports `analysis/experiments/20261122_a1_restart_{provenance,pilot20,control,resume,compare}_v1.json`
  and `{control,resume}_v1_audit.json`; captures remain ignored under
  `data/derived/experiments/20261122_a1_restart_{control,resume}_v1/`.
  To repeat with fresh names: `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -u
  analysis/a1_parallel_capture_scale.py --pilot analysis/experiments/20261122_a1_restart_pilot20_v1.json
  --worlds-dir data/derived/experiments/<new-dir> --output analysis/experiments/<new-report>.json
  --batches 2 --stop-after-batches 1`; run the same command with `--resume` replacing
  `--stop-after-batches 1`, then audit and compare both outputs with the scripts listed in README.
  This is research only, not a representative failure/bias rate, production integration or model promotion.
  Focused retry/capture tests **11/11**, smoke **107/107**, deliberate fault **86/107** and exit 1
  (`/tmp/musnba_a1_restart_{smoke,fault}_v1.log`). HANDOFF, PLAN, FINDINGS and README record the work;
  AGENTS, ENGINE_PLAN, TRAINING_PLAN and DASHBOARD_PLAN need no changes because standing rules, accepted
  engine, evaluation gates and shipped UI did not change.
  A1 stays **80%**, Chunk A **34.5%**; remaining 90% and actual dashboard controls still need the gates below.
- **A1 production-minute format checkpoint (23 Nov UTC; still 22 Nov ET):** new simulations now retain
  five float64 period-minute values per player/world in versioned snapshot schema 1; older snapshots decode
  as rounded and cannot acquire lost precision. The laptop retains world identity for precise sheets,
  participation, Given and Joint. The phone retains sorted, independent seven-period minute marginals, not
  world identities or conditional scenarios. Invalid/incomplete precise data fails explicitly. This changes
  storage and presentation, not the engine, availability assumptions or predictive accuracy.
  Three isolated 10,000-world captures each independently checked **2.1 million** exact laptop values,
  **2.1 million** sorted phone values, **210** player-period distributions and **1,470** conditional
  thresholds; reports `analysis/experiments/20261122_a1_production_minutes_{033,034,035}_v1.json`.
  The phone minute-only record compressed to **6.54–6.94 MB per 30-player game**; real-device memory
  and rendering remain unmeasured. A private synthetic precise bundle passed **22/22 phone / 23/23 laptop**
  offline tests; it combines research captures and unrelated metadata and must never be published as a forecast.
  Focused tests **38 Python** plus four JS suites, responsive **37/37** and injected research **6/6**
  passed; screenshots inspected. After refreshing views from unchanged retained snapshots, final smoke
  **107/107**, deliberately injected fault **86/107** and exit 1. No fresh simulation was run.
  All **7** today games remain the original pre-tip rounded-minute forecasts and all **10** tomorrow games
  use the team pathway; neither their missing precision nor an accuracy gain is claimed. Views archived at
  `~/Basketball_archive_ops/archive_20261123T021731Z_8258`; prior Pages tree archived at
  `~/Basketball_archive_ops/archive_20261123T021910Z_8409`.
  Actual iCloud phone/laptop bundles are **12,634,136 / 42,906,219 bytes**, SHA-256
  `8a82f10f4dc577d6c61a9fa1b40d86c96e66e5cf5d36cafb32f9e39cab6a9a9f` /
  `43cdebf878627cca30b48c731d9d1dc0a82543abb7100f9a151ef2cceef3098b`;
  hosted import/offline checks **23/23 / 24/24**. Data-free `gh-pages` **e3c7798**, cache
  `113ddcd01405374c5573`, deployed; four changed hosted files match the reviewed shell. Actual retained bundles
  do not contain the new precise data. Manual physical-phone import remains unconfirmed; no per-game iCloud
  streaming exists. Engine **v1.3** and team-pathway **v1** remain unchanged; A1 **80%**, Chunk A **34.5%**.
  Documentation review: HANDOFF, PLAN, FINDINGS, DASHBOARD_PLAN and README updated; AGENTS standing rules,
  ENGINE_PLAN model design and TRAINING_PLAN cutoff/promotion gates need no change.
- **Owner's latest horizon change (22 Nov; delivered):** stop possession-engine forecasts for
  tomorrow and later: simulate today's ET games only; tomorrow onward belongs to the season team engine.
  Exclude tomorrow's old possession forecasts and future player/possession sensitivities from the active dashboard
  while preserving original forecasts/archives; future team-level score distributions come from season worlds,
  labelled regulation because pathway ties are resolved separately without overtime points. Still produce a
  fresh season on days with no games. Existing pre-tip-only "How we did"
  retrospective summaries should remain available where forecasts were actually retained; do not invent older
  forecasts or backfill. A fresh season, updated app, iCloud exports and data-free Pages shell were delivered;
  physical device import remains manual. This owner's request supersedes D24/D26's two-day horizon.
- **A1 dashboard acceptance clarification (owner, 22 Nov):** complete and deliver the uncertainty/lineup
  experience in the actual dashboard as A1 closes, not merely in injection-only research. Do not pass off
  fixed research fixtures as today's live data; enforce origin provenance, keep assumptions explicitly
  uncalibrated and all affected views coherent, validate fresh outputs, bundles and normal routes, and keep
  the accepted model unless its promotion gates pass. Existing current availability panels and
  participation-based Given/Joint are not the full plays/sits control.
- **Live D50 refresh (23 Nov 01:30 UTC, still 22 Nov ET):** after the last listed tip, all
  **7/7** original pre-tip games were selected for retention. Immediately before collection, the independent
  audit again matched **246** availability entries and all seven source-timing records:
  `analysis/experiments/20261122_a1_retained_raw_report_audit_v5.json`. Existing views were copied and verified
  at `~/Basketball_archive_ops/archive_20261123T012536Z_99705/data/views`. Started
  `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=8 .venv/bin/python -u scripts/nightly_musnba.py` with log
  `/tmp/musnba_d50_live_20261122_v1.log`; check that process and log before any restart. Its collection,
  Collection finished:
  **30/30** schedules and rosters, **65** requests, **2** new finals and **0** failures; input rebuilding
  completed in **230.1s** through 21 Nov. After collection, an independent cutoff recomputation matched the
  retained snapshot's team, league and player tables exactly. The new snapshot contains **7** retained games
  and a **959-game / 10,000-world** season; it archived the original at
  `~/Basketball_archive_ops/archive_20261123T013445Z_121`. An independent post-publication comparison found
  all seven original summaries, placeholders, provenance, player and team worlds identical, and another raw
  audit matched **246** entries (`analysis/experiments/20261122_a1_retained_raw_report_audit_v6.json`).
  Views were rebuilt (**1,960** files); both bundles were exported to iCloud (**42.9 / 12.6 MB** laptop/phone).
  Independent full-season/view replay succeeded using `analysis/d50_today_only_probe.py`, scratch
  `data/derived/experiments/20261122_d50_live_audit_v1`, report
  `analysis/experiments/20261122_d50_live_audit_v1.json`, log `/tmp/musnba_d50_live_audit_v1.log`;
  the replayed season exactly equals the live `season.json`, with **952** future games and **3,808**
  independently checked regulation distributions. Browser checks passed **36/36** and screenshots were
  inspected. The previous private shell passed actual-bundle offline tests, but a
  slate timing-label fix was then needed: snapshot refresh time is no longer presented as game forecast time.
  The corrected private shell is `/tmp/musnba-d50-public-shell-timing-33cddc8`, cache `871e52f6e7a2ca20b58b`,
  previously served privately at :18871; actual-bundle local offline checks passed **22/22 phone, 23/23 laptop**. The data-free
  shell is now published as `gh-pages` **1b4cc6c** and hosted actual-bundle import/offline checks passed
  **24/24 phone, 25/25 laptop**, logs `/tmp/musnba_d50_hosted_{phone,laptop}_pwa.log`.
  All six changed hosted files match the reviewed local shell. The :8767 review server remains up; the
  task's temporary :18870 / :18871 servers and detached Pages worktree have been stopped/removed. The old
  Pages tree is archived at `~/Basketball_archive_ops/gh-pages-before-d50-0c0447a.tar`. Do not touch the
  owner's :8766 or any other user's jobs.
  Post-delivery smoke initially caught two obsolete assumptions: replay was including discarded preview
  worlds and checking a hidden preview game view. Corrected smoke selects the active same-origin snapshot and
  only the season's declared worlds; missing or duplicate world sets fail explicitly. Focused tests **33/33**,
  corrected full smoke **107/107**, deliberate fault **86/107** and exit 1; logs
  `/tmp/musnba_d50_live_fixed_{smoke,fault}.log`. The count is one lower than before because changed input
  hashes correctly skip re-simulating a retained old game. **D50 100% complete after this checkpoint.**
  Documentation review: HANDOFF, PLAN, ENGINE_PLAN, FINDINGS, DASHBOARD_PLAN and README reflect the delivery;
  AGENTS and TRAINING_PLAN need no changes because standing rules and model/promotion gates remain unchanged.
- **D50 delivery ladder (supplemental, no change to Chunk A weights; complete):** 10% freeze today's-only and archive
  contract; 20% trace stale previews and existing pre-tip reviews; 30% implement today's/no-game nightly;
  40% exclude future possession sensitivities and expose honest team distributions; 50% update app copy and preserve past reviews;
  60% pass focused cutoff, archive and no-game tests; 70% pass responsive/browser tests and inspect screenshots;
  80% run fresh nightly and verify team-pathway boundary; 90% verify iCloud export and PWA/offline shell;
  100% review all docs, smoke/fault, commit and push. Phone import remains a separate manual owner check.
- **D50 70% isolated preview:** from seven retained today engine games, the fixed-origin 10,000-season
  preview audited all **952** future games and **3,808** regulation distributions independently; all
  seven current game views remained present. Final-source report `analysis/experiments/20261122_d50_today_only_preview_v4.json`;
  this is not a new nightly or production delivery. Browser checks passed **36/36** across future game,
  today, current game, standings, team and about at 1440/960/390 in both themes; after screenshot review
  corrected displayed rounding and removed unavailable player/team controls, the future page passed **6/6**
  again. A later total/margin switch also passed **6/6** viewport/theme checks, with screenshots inspected at
  `/tmp/musnba-d50-margin-check/`. Focused horizon/origin/timing tests **22/22**.
  At 23:46 UTC two games had already tipped: preserve the prior seven verified pre-tip forecasts and their
  individual timing when deciding how to deliver; a standard late nightly would archive and replace them.
- **Late-nightly safety, partial mixed-provenance implementation:** `nightly.py` can now retain previously
  verified forecasts that cannot safely be regenerated, preserving their game summary, player/team worlds,
  placeholder and original per-game metadata. It fails if the old and new stats context or model differ,
  world accounting fails, or a fresh game crosses tip during staging/archival; no automatic retry is wired.
  Views, lineup scoring and branch source checks use the per-game provenance. The original snapshots remain
  untouched until publication; rollback and interrupted recovery remain in place. Completion is the
  staged-file time, refreshed after archival, not proof of publication before tip.
  In a **temporary copy** of the real 22 Nov slate, all **7** original forecasts / **70,000** worlds were
  retained, and a **10,000**-world season of **959** games replayed bit-for-bit. This rehearsal did not run
  collection, regenerate untipped games, publish, or verify PWA delivery. On the real retained snapshot,
  all 7 player/team-world point totals, score means and win rates reconciled independently. The single-registry
  `a1_snapshot_availability_audit.py` explicitly rejects mixed snapshots. The separate
  `analysis/a1_mixed_availability_audit.py` independently parses raw source rosters, injuries and schedules per
  game's recorded origin; it reconciled **246** report entries and seven source-timing records from the original
  collection. A synthetic test covers two distinct collection origins and mismatches. The integrated mixed
  rehearsal passed the raw audit and seven rendered-view checks; both retained and regenerated games used
  the **same** retained collection, so it did not test a newly fetched collection. If a tip
  crosses, the run fails safely and needs a retry; old/new cutoff stats must be checked again after collection.
  The original 22 Nov `registry_run` directory exists with **30** roster files, an injury report, the origin
  scoreboard and collection start/finish metadata; existence alone does not establish report correctness or
  publication timing. A direct raw-scoreboard read found **7/7** games with valid tip, pre-event status, and
  collection finish and staged snapshot completion before the original listed tip. This does not independently
  establish publication time or verify every availability entry.
  The earlier checkpoint's focused retention, branch provenance, lineup timing and audit tests were **47/47**; Pylance found
  all **9** `project_slate` callers signature-compatible. Aggregate all-retained rehearsal and source hashes:
  `analysis/experiments/20261122_d50_retained_snapshot_rehearsal_v1.json`.
  Earlier-checkpoint smoke **108/108**, deliberate fault **86/108**, underlying exit 1:
  `/tmp/musnba_a1_retention_final_{smoke,fault}.log`.
  A mixed-slate rehearsal with an explicitly artificial `2026-11-23T00:55:00Z` clock completed: **5** retained
  and **2** regenerated games, **10,000** worlds per game; its **959**-game season replayed bit-for-bit.
  `OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=1` took **309.67s** total; log
  `/tmp/musnba_d50_mixed_rehearsal_v2.log`, report
  `analysis/experiments/20261122_d50_mixed_retention_rehearsal_v1.json`. The earlier single-thread attempt
  was stopped after **9m 22s** with **0/2** completed games; its identified temporary directory was removed.
  Reproduce with `OMP_NUM_THREADS=8 OPENBLAS_NUM_THREADS=1 .venv/bin/python -u analysis/a1_mixed_retention_rehearsal.py --day 2026-11-22 --synthetic-completed 2026-11-23T00:55:00Z --output analysis/experiments/<new-report>.json`.
  The temporary snapshot was not a live forecast, the synthetic clock is not proof of pre-tip publication,
  and the new raw-origin audit was not run on this now-deleted temporary output.
  The integrated replacement passed with the same artificial clock and eight-thread budget in **349.13s**:
  five retained and two regenerated games, **246** raw-report entries, **7** rendered game views, and exact
  959-game season replay. Log `/tmp/musnba_d50_mixed_rehearsal_v3.log`, report
  `analysis/experiments/20261122_d50_mixed_retention_rehearsal_v2.json`. It used one retained collection
  and did not publish live data or establish actual publication time.
  A regression reproduced six false pre-tip labels for missing, unknown, suspended, postponed, cancelled and
  delayed statuses. The nightly now returns unknown for all six; only scheduled can be pre-tip, and live/final
  remain non-pre-tip. **50/50** focused tests and final-source smoke **108/108** pass. Deliberate fault
  returned **86/108** and exit 1, as required; logs `/tmp/musnba_a1_mixed_final_{smoke,fault}.log`.
  Pylance syntax checks passed for the nightly, both new analysis scripts and the new audit test.
  Documentation review: HANDOFF, PLAN, ENGINE_PLAN, FINDINGS and README describe this partial implementation;
  AGENTS, TRAINING_PLAN and DASHBOARD_PLAN need no change because standing rules, predictive gates and shipped UI
  have not changed. No live nightly, model promotion, iCloud export or Pages update has occurred.
  The earlier fail-closed guard refused game `401910029` before modifying data; focused
  horizon/origin/timing tests were **22/22**. That guard alone did not produce a fresh nightly, update
  the dashboard, or support mixed provenance; the later partial implementation above addresses the last issue.
  Temporary-directory regressions exposed and now verify fixes for failed staged-directory publication,
  interruption after moving the previous directory, tip passing during archival, and invalid or missing tip
  validity. Failed publication restores the previous snapshot; restart restores an orphaned `.previous`, while
  simultaneous active and `.previous` directories fail closed for review. Views fail rather than silently fall
  back to an older snapshot if any `.previous` is present. Unknown timing remains unknown and a game
  marked live/final cannot be labelled pre-tip just because its listed tip is later. Missing ESPN `timeValid`
  now stays unknown in master-fixture generation and the S07 coverage audit and independent checker, rather
  than being assumed valid. All **32** retained 19–21 Nov scoreboard observations used by S07 had an
  explicit true flag, so that correction does not change those inventoried origins. A fresh coverage-only
  regression on all **7** retained archives independently reconciled **1,585** roster snapshots and **880**
  unique player-games; no protected outcomes were scored. Detailed reports are ignored under
  `data/derived/experiments/20261122_a1_s07_validity_regression{,_check}_v1.json`. The checker requires an
  absolute `--report` path. Four of the original five archive inventories match exactly; the fifth's
  previously missing **175** roster final-box coverage records now split into **125** listed and **50**
  unlisted as additional final boxes became available. Its origin classifications are unchanged; listing
  is not a play/DNP outcome. **38/38** focused
  today-only/origin/availability/report-audit tests passed at that checkpoint. A hard interruption between directory
  renames can still leave the active path absent until the next recovery. The mixed-provenance implementation has not
  been delivered or tested against a genuinely mixed live slate.
  Final-source smoke passed **108/108**; deliberate fault produced **86/108** and exit 1, logs
  `/tmp/musnba_a1_snapshot_recovery_current_{smoke,fault}.log`.
  Before another collection, the 22 Nov snapshot's team, league and player stats each exactly matched a
  cutoff-safe recomputation from the current retained box-score inputs. Recheck after collection; this observation
  does not establish mixed provenance or justify replacing any retained game.
  Documentation review: AGENTS standing rules, ENGINE_PLAN decisions/design and DASHBOARD_PLAN shipped
  behaviour need no change for this safety/research checkpoint; no model, dashboard or bundle was promoted.
- The first D50 smoke run exposed a **legacy schema mismatch**, not a changed forecast: the saved season
  has no regulation distributions while a fresh replay does. New seasons now identify the distribution
  schema; smoke strips added fields only when comparing a completely legacy season, while new/mixed
  seasons still require matching distributions. Added a focused regression; **22/22** targeted tests pass.
  Normal smoke **108/108** and deliberate fault **86/108** (nonzero underlying exit), logs
  `/tmp/musnba_d50_final_{smoke,fault}.log`.
- A synthetic empty-slate fault run completed without crashing (**50/69** checks passed under deliberate
  corruption, expected nonzero from the smoke function); `--fault` now skips game/season perturbations
  when the relevant set is empty. Final-source reruns passed **108/108** normal and **86/108** under deliberate
  fault, with the fault command confirming a nonzero underlying exit (`/tmp/musnba_d50_checkpoint_{smoke,fault}.log`).
- **Private D50 PWA rehearsal only:** shell cache `de1d8c19040399e187cc`, based on isolated
  preview `v4`, passed **22/22 phone** and **23/23 laptop** import/offline checks, including future
  regulation total and margin distributions, interactive lines and no future player projection. Latest
  privately built shell cache **fa9aa9b6ad13c1d06528**; private phone/laptop bundles
  are `/tmp/musnba-d50-private-{phone,laptop}-v4.musnba.gz` (**12.6 / 42.9 MB**). No iCloud export,
  Pages update, live nightly or real-device import occurred; these checks do not advance the delivery rungs.
- **A1 current-game inventory:** all seven 22 Nov games passed `a1_branch_persist.checked_snapshot`
  against their retained origin inputs. One-world-per-branch research probes completed sequentially with one
  numerical thread: **5/7** games have a qualifying uncertainty, **7** selected players total and **14**
  branch captures. Aggregate report `analysis/experiments/20261122_a1_origin_inventory_summary_v1.json`;
  player-level reports and captures stay ignored under `data/derived/experiments/20261122_a1_inventory_reports_v1/`
  and `data/derived/experiments/20261122_a1_origin_inventory_<game>_v1/`. They assess which
  pinned games have qualifying uncertainties, not predictive performance, realistic distributions, promotion,
  production or a pre-tip publication time. These captures are far too small for dashboard distributions.
- **Pinned-input captures completed:** three isolated research
  jobs captured 10,000 worlds per branch for games `401910033`, `401910034` and `401910035`, respectively
  2, 4 and 2 branches. Each used `OMP_NUM_THREADS=3 OPENBLAS_NUM_THREADS=1` (nine heavy threads total);
  logs `/tmp/musnba_a1_live_branch_{033,034,035}_v1.log`, captures and manifests
  `data/derived/experiments/20261122_a1_live_branch_{033,034,035}_v1[.json]`. All exited successfully.
  `033` and `035` completed and independently reconciled
  **20,000 worlds each**, with **4,932,579 / 4,857,339** lineup snapshots and weights exactly one.
  Their full-mixture research summaries independently reconciled **3,958 distributions each** and
  **3,709 / 3,714 means** against the captures using the current whole-minute histogram convention;
  that agreement did not resolve the minute-precision blocker described below.
  Separate browser decoding checks reconciled **21 weighted period means and 60 opening-lineup counts**
  per game, plus all **4 / 5** overtime-period masses.
  `034` completed **4/4 branches**, independently reconciled **40,000 worlds** and **9,647,518** lineup
  snapshots, with weights exactly one. Its browser fixture reconciled 18m player-stat values, 84m player-period
  stats and 6m exact player-period minutes; the full-mixture summary reconciled 3,958 distributions and
  3,719 means using the current rounded-minute convention. The separate period-decoding check reconciled
  21 weighted means, 120 opening-lineup counts and all five overtime-period masses.
  At least one began post-tip; none is a verified published pre-tip forecast, and all are research only.
  Their fingerprint covers **all** `scripts/*.py` and origin inputs: no such input changed during capture.
  Subsequent snapshot-safety edits change the current source hash, not the completed captures' stored fingerprint.
  The two other qualifying games already have D47 10k branch captures.
- **Minute-precision blocker at the earlier research checkpoint (partly addressed above):** the branch source preserves float64 per-world and period minutes, and weighted
  Given conditions use those values, but `analysis/a1_branch_game_summary.mjs` still rounds minute histograms to
  whole minutes. Do not ship that inconsistency as the owner's requested seconds-sensitive dashboard. Reconcile
  stored-minute precision, histogram/line units, the Given/Joint consumers and their independent accounting;
  the then-current production `engine_players.npz` also rounded to whole minutes.
  A new encoding probe on four saved branches of game `401910034` (**40,000** worlds, 30 players) measured
  **21** 30-minute classification changes from float32, **227** from rounded whole seconds and **126**
  positive cells rounded to zero. Float64 preserved the exact values. Its gzip-compressed full-game minute
  arrays totalled **4,824,857 bytes** across all four branches; this is not the final bundle size.
  Independently checked counts and per-branch source hashes:
  `analysis/experiments/20261122_a1_minute_encodings_034_v1.json`. The separate research probe is
  `analysis/a1_minute_encoding_probe.py`; it does not change forecasts or score real outcomes.
  An isolated on-demand exact weighted distribution now retains float64 support and integer cumulative mass;
  one-minute display bins are half-open and split at the actual line, so a bin cannot silently assign all of
  its mass to one side. Independent NumPy reconstruction from the original captures checked **210**
  player-period distributions and six thresholds each for the full **40,000**-world mixture and again for a
  **20,000**-world selected mixture. Node measured **2.14 s / 1.25 s** distribution calculation, respectively,
  after **0.72 s / 0.70 s** fixture decode; peak process RSS **909,920 / 843,600 KiB** includes the entire
  207 MB fixture and is not a browser or phone measurement. The outputs were aggregate-only and did not store
  full support; this is not a bundle-size or predictive test. Reports and independent audits:
  `analysis/experiments/20261122_a1_precise_minutes_034_{all,available}_v1_{probe,audit}.json`.
  At that checkpoint the helper was not wired into the research view or production; the old rounded summary
  still exists. Those earlier probes pinned the original helper location and can be reproduced at checkpoint
  **79c02b2**. The helper is now shared as `scripts/webapp/precise-minutes.mjs`.
  Focused JS distribution, weighted-arithmetic and source tests plus **2/2** Python encoding tests passed;
  final-source smoke **107/107**, deliberate fault **86/107** and exit 1, logs
  `/tmp/musnba_a1_precision_checkpoint_{smoke,fault}.log`. Pylance found no syntax errors in the new Python
  analysis scripts. Documentation review: HANDOFF, PLAN, FINDINGS and README record the research; AGENTS,
  ENGINE_PLAN, TRAINING_PLAN and DASHBOARD_PLAN need no changes because standing rules, accepted design,
  predictive gates and shipped UI did not change.
  **Further research-only integration:** an explicitly injected branch player sheet now calculates exact selected
  period-minute distributions on demand, with fractional line input, exact split-bin mass and the same threshold
  in Given. Its legacy Expected-only fallback explicitly says its minute histogram is rounded. Research results
  shown alongside a final game are labelled research, not pre-tip. Independent reconstruction of the second
  fixture (`401910030`, **40,000** worlds, 28 players) checked **196** player-period distributions, seven
  thresholds, split bins and **196** team-win conditional thresholds; reports
  `analysis/experiments/20261122_a1_precise_minutes_030_all_v4_probe.json` and
  `analysis/experiments/20261122_a1_precise_minutes_030_all_v5_audit.json`.
  The injected browser check reconciled full-game over 30.25 minutes, its split bin and Given against that
  audit, plus first-half over 10 minutes and the rounded Expected-only label. **6/6** viewport/theme cases
  passed with screenshots inspected; **30/30** normal Game Centre/scenario checks passed. Report
  `analysis/experiments/20261122_a1_precise_game_browser_v4.json`. No normal route registers this provider,
  production snapshots at that checkpoint rounded player worlds, and legacy minutes cannot be recovered.
  Four-branch, 30-player **minute-only** JSON/gzip sizing from game `401910034` measured **18,713,888 bytes**
  for five per-world periods and **26,348,197 bytes** for sorted seven-period marginals. The latter discards
  world identities, so it cannot support Given or Joint. These are not full bundle sizes or phone benchmarks;
  both byte counts were independently reconstructed. Report
  `analysis/experiments/20261122_a1_minute_payload_034_v1.json`.
  The changed data-free shell is `gh-pages` **5144f35**, cache **52fb655ed8e21314249a**; its five hosted
  changed files match the locally tested shell. Existing actual iCloud bundles passed hosted import/offline
  checks **23/23 phone / 24/24 laptop**; no bundle was regenerated, and manual device import remains unconfirmed.
  Previous shell archive: `~/Basketball_archive_ops/gh-pages-before-a1-precision-1b4cc6c.tar`.
  Focused JS arithmetic/source/summary/view tests and **8/8** Python PWA/precision tests passed; Pylance
  syntax checks passed for the new/changed Python scripts. Final-source smoke **107/107**, deliberate fault
  **86/107** and exit 1 (`/tmp/musnba_a1_precise_view_{smoke,fault}.log`). The private shell server and the
  task's clean Pages worktree were stopped/removed; the other user's worktree and :8766 were untouched.
  Documentation review: HANDOFF, PLAN, FINDINGS, DASHBOARD_PLAN and README cover the change; AGENTS,
  ENGINE_PLAN and TRAINING_PLAN need no changes because standing rules, accepted model design and predictive
  gates are unchanged.
  One isolated 10k branch had **527,727/1,250,000** player-period cells at fractional seconds (maximum
  deviation **0.5 s** from an integer second); report `analysis/experiments/20261122_a1_minute_precision_v1.json`.
  The `033` and `035` browser fixtures each independently reconcile 20k worlds, 9m player-stat values,
  42m player-period stats and 3m exact player-period minutes; detailed audits remain under ignored
  `data/derived/experiments/20261122_a1_live_branch_{033,035}_fixture_audit_v1.json`. Their selected-player
  30-minute exact-versus-rounded thresholds disagree in **301 / 444** worlds respectively, and positive
  player-world minutes round to zero in **6,178 / 6,225** cells. No production precision change has shipped.
  The existing byte-packed production `lines` schema cannot hold seconds: introduce a versioned, separately
  packed precise-minute array rather than silently changing the meaning of its `min` column; keep an explicit
  legacy decoder for older snapshots. Audit player-world values and participation against original engine
  minutes, then reconcile sheet histograms, threshold inputs and Given/Joint with the same units. Research
  summaries currently round minutes before building their integer histograms, even though their source and
  weighted Given conditions retain float64 values. Do not solve only the display or only the stored worlds.
- **Compute budget (owner, 22 Nov):** on this 14-core Mac, cap simultaneous heavy work at **10 total compute
  threads/workers**, including nested threads; leave at least four cores' worth of aggregate capacity for normal
  use, and reduce when busy or memory pressure rises. This is not a guaranteed affinity/responsiveness reservation.
  Follow the script-specific controls in AGENTS §6, including the backtest's internal OpenMP override. The
  owner-requested 8/10/12 short comparison is a specific exception; run it without other heavy jobs.
- **Slate parallelism (owner, 22 Nov):** investigate scheduling multiple independent game computations concurrently
  under the same 10-thread total budget instead of assuming serial slate time is game count × standalone time.
  `nightly.project_slate` currently runs games serially and its engine has mutable `last` state: isolate engines
  per process, retain per-game seeds and exact outputs, join safely before the existing season coupling, and
  benchmark throughput/memory at different game/thread splits before shipping. Computational independence
  given fixed inputs does not establish real-world cross-game injury/form independence. This is future work,
  not implemented or a reason to bypass A1 promotion or cutoff gates.
- **Forecast reuse question (owner, 22 Nov):** consider carrying yesterday's tomorrow forecast into today and
  selectively rerunning games when new roster, availability, role, minute or other material inputs are not covered
  by stored branches. Research only: freeze a cutoff-safe stale-versus-fresh fold comparison and explicit
  invalidation rules before adopting; compare player-first accuracy, availability coverage, runtime and season
  consistency. One selected uncertain per team cannot cover a newly injured/traded player or all multiple
  uncertainties, and the branch weights remain uncalibrated. The rest-days node ablation was neutral/worse for
  possession decisions, not proof back-to-backs have no effect on minutes, injuries or whole-game performance.
  Keep today's current fresh forecast until a candidate passes gates. No historical forecast backfill authorised.
- **Team-pathway overtime question (owner, 22 Nov):** do not multiply every game's score/time by a flat 2%:
  the pathway currently resolves tied regulation worlds' winners without overtime points. Future team score
  charts must say regulation. Later test a candidate that simulates overtime only in tied worlds, including
  repeated ties, against prior-fold overtime/score and season-path calibration; preserve the current pathway
  until the established gates pass.
- **Current action:** D50 is delivered; continue A1 90%: finish representative accounting,
  restart, cutoff and runtime gates; the isolated retry passed a synthetic single-game 10k audit but is not
  integrated or validated as a representative production policy, and dated development injury
  reports are absent. Do not equate wiring tests with predictive promotion. **Owner's latest stop:
  stop at the end of A1**, checkpoint/push and report gains and limitations; do not start A2, A3 or Chunk B in
  this run. The earlier dashboard house pass was already delivered; no nightly merely for this research checkpoint.
- **A1 90% restart experiment, frozen before implementation:** add explicit opt-in resume to the isolated
  fixed-F4 batched capture, not the nightly. Persist the requested run configuration and input/source hashes;
  accept only a contiguous prefix of complete batch pairs. Before scheduling further worlds, independently
  replay and audit the entire prefix, its hashes, seeds, rejection order, pilot identities and lineup/score
  accounting. Reject missing/extra/partial files, changed configuration or source, output collisions and all
  unclassified failures without deleting or overwriting them. Preserve deterministic per-batch seeds and the
  global retry cap. Compare uninterrupted and interrupted/resumed captures and independent audit results;
  test interrupted/invalid prefixes and changed inputs. This is a fixed-game restart check, not a fold, runtime,
  unbiased-retry or promotion gate, and it must not change accepted forecasts.
- **A1 90% observed branch-runtime audit, frozen before measurement:** re-read the existing three independent
  10k-per-branch current-origin research captures and their original logs. Validate capture hashes, assignments,
  exact weights, saved box scores and unavailable players using the independent manifest auditor, then extract
  per-branch elapsed times and report each game's sum of recorded branch times. These three captures shared
  nine numerical threads; startup, full-slate duration, serial/parallel scheduling and unobserved rejection
  rates are not established by branch-time sums. Never publish these post-tip research captures as forecasts
  or use protected-season outcomes.
- **A1 90% roster/foul pressure diagnostic, frozen before measurement:** for those same three research
  games, independently count each team-world by initial available players and final six-foul players, plus
  how many finish with exactly five eligible. Verify player/foul/availability dimensions, capture hashes,
  unavailable-player fouls, nonnegative counts and every world's two team records. Stratify by branch rather
  than pool branches as equally likely; preserve exact mixture weights. These are simulated outcomes, not
  protected real-game outcome scores. Completed vectorised batches cannot reveal rejected or missing attempts,
  so they do not establish a retry rate, unbiasedness or representative development-fold gate.
- **A1 90% fixed-F4 exhaustion screen, frozen before implementation:** on the **200** predeclared S01 F4
  games, use their actual-participant team sets (an oracle, not pre-game availability) and unchanged F4
  possession inputs. For each game, choose the home player with largest pre-origin D29 expected minutes
  (player ID breaks ties), set synthetic 50% availability and examine plays/sits separately. Before drawing,
  record any branch that cannot form five players or legal D29 240-minute targets as an explicit input
  failure, not a retry. For each feasible branch run **five** independently seeded single-world attempts
  (`a1-f4-exhaustion-v1`, game, branch, draw); count only the typed post-foul-out exhausted-roster exception.
  Persist successful traces and seeds, independently audit their legality, minutes and scores, log all input
  failures and classified rejections, and fail immediately on any other exception. Use at most ten one-thread
  workers total, retain source/input hashes, and report 20 completed games per progress mark. This is a fixed
  F4 conditional-roster stress screen with synthetic selected status, not F1–F3 confirmation, a pre-game
  failure rate, matched penalty-policy bias test, accuracy result or production retry. Do not score any
  protected 2026–27 results. Preserve every partial result if interrupted.
- **A1 90% targeted six-player stress, frozen after the F4 screen and before its draws:** select the
  unique F4 screen game with seven actual home participants (`401811022`); synthetically sit the same
  highest-expected-minute home player, yielding six. Run **1,000** independently seeded single-world first
  attempts with the isolated D29 repair, ten one-thread workers, no retries, recording each typed exhaustion
  and independently auditing every completed saved trace. Report every 100 attempts. This deliberately
  selects an extreme oracle-roster case and must not be presented as an NBA failure rate or an F1–F3 gate.
  If any attempts exhaust, retain their seeds for a separately disclosed S06 penalty-policy comparison;
  that policy changes substitutions and random paths, so the comparison cannot by itself prove counterfactual
  retry bias. Unexpected input, cutoff, accounting and unknown errors must stop, not be retried.
- **A1 90% six-player penalty comparison, frozen before its draws:** use exactly the **202** exhausted
  draw/seed pairs from the independently audited six-player stress, same reconstructed input and selected
  absence, with the frozen F4 S06 selected-timeout/foul-penalty candidate and no retries. Four one-thread
  workers bound shared-machine load. Save each full trace, audit each at creation and again from saved files,
  reconcile seeds, legal fives and technicals, and fingerprint sources and inputs. Count completions and
  technicals only; this deliberately selects D29 failures, and changed policy/random paths prevent treating
  same-seed results as matched states, estimating retry bias, league rates or predictive accuracy. Stop on
  any unexpected error and retain partial records. No model or forecast promotion.
- **A1 90% six-player halftime selection diagnostic, frozen before replay:** replay all **1,000** original
  six-player D29 attempts with unchanged seeds and a read-only halftime observer. Record halftime home/away
  score and home personal fouls plus the count of available home players with at least three fouls; all
  recorded failures were after halftime. Verify each of the **798** successful complete-world digests and
  each of the **202** exact classified failure reasons against the original manifest. Independently audit
  saved halftime player/period minutes and points against team totals, and foul values/availability. Compare all attempts to the
  successful subset for these prespecified halftime measures, with 5,000 seeded bootstrap resamples over
  attempts and 95% percentile intervals. This can measure selection in the common pre-failure state of this
  selected synthetic case, not estimate missing final-game outcomes, production rates or general predictive
  accuracy. Unexpected errors or changed replay identities stop the run; retain partial files.
- **A1 90% earlier-fold prerequisite, frozen before fitting:** prepare isolated F1–F3 engines using the
  already-built S02 guarded dated/body-free assignment feature snapshots and the S02 diagnostic node
  settings. Each fold uses its own assignment schedule and fits through its own training cutoff; build
  missing node caches sequentially, independently audit each 16-node cache, then fit each 16-node engine
  sequentially with at most eight compute threads and BLAS capped at one. Use fresh version namespaces and
  record source, feature, schedule, node-cache and model fingerprints. These are research engines, not the
  accepted v1.3 or comparable identical baselines; static source publication times remain unverified.
  Their sole initial purpose is to enable earlier-fold conditional-roster exhaustion diagnostics, not
  promote models or score the protected season. Preserve partial outputs on any failure.
- **A1 90% earlier-fold conditional-roster screen, frozen before its draws:** once the corresponding dated
  F1–F3 diagnostic engine is ready, use each fold's **200** predeclared confirmation games and actual
  participant rosters. For each, construct top-projected-home-minute player plays/sits branches as in the
  earlier F4 screen; record invalid initial allocations, then run **five** independently seeded single-world
  attempts per feasible branch. Save and independently replay completed traces; record typed exhaustions,
  stop on any other error, and fingerprint sources, dated models and inputs. Treat each game/branch as a
  cluster when reporting uncertainty; ten attempts from one game are not independent game samples.
  S02's body-free diagnostic differs from the accepted engine and its oracle participant roster is not
  pre-game availability. Do not compare its raw failure rate to F4 as if the models were identical, infer a
  league rate or claim the missing dated-availability or full-game retry-bias gates.
- **A1 90% selected full-game policy comparison, frozen before its draws:** for the already selected F4
  six-player synthetic-absence case, retain the audited 202 S06 worlds for D29-rejected seeds and run S06
  once for each of the other 798 original seeds, with no retries. Independently audit all 1,000 S06 traces
  and the 798 saved D29 survivor traces, including identities and accounting. Prespecify home and away
  final score, total and margin, and each available home player's points and minutes. Compare the D29
  survivor mean with the S06 mean over all 1,000 seeds, using 5,000 seed-cluster bootstrap resamples and
  unadjusted 95% percentile intervals. This is a deliberately selected synthetic oracle-roster case and
  the two policies have different substitutions and random paths: the differences combine policy and
  survivor selection and **cannot identify retry bias** or substitute for fold/pregame/promotion gates.
  Use four one-thread workers, new output names, verify source hashes, and fail on unexpected errors.
  The first `_v1` generation completed 798 worlds, but its saved-file audit failed because it compared
  absolute and relative capture paths. Preserve its files as an invalid, unaudited run; correct the auditor
  and generate `_v2` afresh because the audit source hash is part of the frozen run fingerprint.
- **Earlier-fold F1 screen correction (before rerun):** the first screen stopped with an `AttributeError`
  on a missing historical position used by projected-starter selection. Its pool shut down only after
  queued jobs finished, leaving **190** complete game records and **1,899** partial capture files in
  `data/derived/experiments/20261122_a1_dated_f1_screen_v1/`; no summary or valid aggregate was emitted.
  Keep those files. Before a fresh run, mark a branch explicitly unsupported when its projected-starter
  candidate pool contains a missing/empty position, rather than inventing a position, and cancel queued
  work immediately on unexpected failures. The screen must separately count these unsupported branches.
  Test both cases and rerun into a new `_v2` namespace; do not score or silently omit unsupported cases.
- **A1 80% complete, injection-only:** a single shared research lineup control now drives selected player, team,
  sheet, scenario/Given/Joint and driver views; branch-unavailable metadata/cards are omitted. Available and
  positive-minute participation are distinct; shooting-defined mass is weighted. No normal route registers the
  research provider and the production forecast, v1.3, pathway v1 and iCloud bundle remain unchanged. Independent
  adaptation accounting reconciled **25 / 28** players and **3,275 / 3,667** distributions for the full mixtures,
  and **28 / 3,645** for a 20k-world fixed-player selection. Injected Chrome matched every player row and selected
  team/sheet/empty scenario; six 1440/960/390 theme screenshots were inspected. Normal responsive suite **234/234**;
  private research laptop and Expected-only phone bundle offline checks **34/34 / 32/32**; actual retained bundle
  offline checks **31/31 laptop / 30/30 phone**; installed-shell upgrade **30/30**. The private laptop and phone
  research bundles are **113,538,014 / 14,154,406 bytes**, respectively, in `/tmp`; test injection is required,
  not a production bundle contract or a real-device acceptance. An old test expected “worlds” while the UI now
  says “saved worlds”; corrected the assertion. Normal smoke **108/108** and deliberate fault **86/108**, exit 1,
  logs `/tmp/musnba_a1_view_{smoke,fault}.log`. Data-free `gh-pages` **0c0447a**, cache
  **6324344ab602b7c6502c**; hosted source hash matches and hosted laptop/phone import/offline checks passed
  **31/31 / 30/30**. Previous shell archived as
  `~/Basketball_archive_ops/gh-pages-before-a1-game-view-b399409.tar`. Device import remains manual. Game identity
  context comes from the existing game view; the later audit below checks only these retained fixtures. Browser/source evidence
  `analysis/experiments/20261122_chunk_a_a1_d47_game_view_browser_two_v4.json` and
  `20261122_chunk_a_a1_d47_game_view_{one_full,two_full,two_home_sits}_v2_{probe,audit}.json`.
- **A1 90% partial:** a fixed F4 game with actual participants and synthetic selected availability ran **20**
  control and **20** retry worlds, with one deliberately injected rejection: **41** audited attempts in **21.449 s**,
  all 19 unaffected worlds and seeds identical. This is not a real rejection rate, predictive bias or 10k runtime
  test; the coordinator remains unwired. Report
  `analysis/experiments/20261122_chunk_a_a1_d48_isolated_world_probe_20_v1.json`; **46** retry/selection/availability
  tests pass. The 41 logged attempts averaged **0.521 s** with concurrent validation; extrapolating linearly gives
  **86.8 minutes / 10k attempts** on one core, not a measured 10k or parallel runtime. Do not assume the sequential
  prototype fits the **60-minute** nightly budget. No 90% credit until the rung's remaining checks pass or the
  limitation is explicitly resolved.
  The owner flagged Luka's **10/10,000** worlds at 65+ points as a concern that tails may be too narrow; that is a
  hypothesis, not a calibrated target. Existing F4 control team-total 10–90% coverage was **69%** over **200** games.
  Investigate player and team variance later under A2's pre-existing fold gates, without fitting to market lines.
  HANDOFF, PLAN, FINDINGS, DASHBOARD_PLAN and README document this checkpoint. AGENTS, ENGINE_PLAN and
  TRAINING_PLAN need no edit: standing rules, decisions, promotion and cutoff gates are unchanged.
- **A1 90% context audit:** the two captured research views (`401910029` and `401910030`) match the retained
  snapshot-pinned master and team records reconstructed strictly before the **22 Nov** origin; snapshot completion
  preceded both valid tips. Synthetic same-day-result contamination, post-tip and changed-score cases fail.
  Report `analysis/experiments/20261122_chunk_a_a1_context_cutoff_v1.json`. This checks only these retained views;
  the research adapter does **not** enforce snapshot provenance for future views. Do not treat it as a general
  cutoff-safety or promotion pass. `analysis/a1_game_context_audit.py` documents the reproducible check.
  The two payload hashes match their earlier independent audits; **3** focused tests pass, normal smoke **108/108**
  and deliberate fault **86/108**, exit 1 (`/tmp/musnba_a1_context_{smoke,fault}.log`).
  HANDOFF, PLAN, FINDINGS and README record the audit; AGENTS, ENGINE_PLAN and TRAINING_PLAN need no changes
  (standing rules, design and gates unchanged); DASHBOARD_PLAN needs no change (no shipped behaviour changed).
- **A1 90% parallel experiment, frozen before implementation:** test a research-only process-parallel isolated-world
  coordinator using the existing D48 per-world/attempt seeds and typed recovery. Process results in world order,
  bound in-flight jobs, enforce the same per-world/global rejection caps, and propagate every unclassified error;
  speculative work must never count as accepted or hide errors. Preserve existing sequential behavior and prove
  parallel/sequential equality of accepted results, seeds and rejection records across worker counts and injected
  failures before any engine run. First measure a small fixed F4 engine pilot with independent per-world audits and
  explicit process count/threads, source/input fingerprints and throughput; do not infer 10k or promote from it.
  Then decide whether a persisted, audited 10k run and actual-rejection/bias tests fit the measured budget.
  Different seeds remain different from the vectorised production stream. This is not a change to the nightly.
- **A1 90% scaling experiment, frozen before implementation:** after the 20-world 1/4-process pilot, compare
  8, 10 and 12 processes sequentially on the same 120 independently seeded, audited F4 worlds, one numerical
  thread per process. Report each 12 completed worlds, startup-inclusive elapsed time and per-worker peak RSS.
  Check every result across worker counts and the first 20 against the prior single-process control. This is a
  fixed-game throughput/identity probe, not a 10k runtime, retry-bias, memory-capacity or promotion gate; avoid
  overlapping other heavy work, and do not alter its fingerprinted sources while it is running.
- **A1 90% parallel results:** the fixed F4 20-control/20-retry world pilot matched across one and four processes,
  including all 19 unaffected worlds after one injected rejection; times were **24.681 / 11.174 s**. The
  subsequent 120-control-world scaling test matched every hash, audit and seed across **8 / 10 / 12** processes
  and matched its first 20 to the single-process pilot. Times were **13.938 / 12.841 / 13.263 s**; maximum
  individual worker peak RSS was **1,041 / 1,045 / 1,046 MB**, not total memory. Reports
  `analysis/experiments/20261122_chunk_a_a1_d48_parallel_{pilot20,scaling120}_v1.json`. The 12-process test was
  an explicitly requested brief above-budget comparison, run after both smoke jobs finished; future heavy work
  stays within the 10-thread shared budget. These isolated prototypes do not persist captures, measure actual
  rejection/selection bias, prove a 10k runtime, or change the nightly. Ten focused retry/context tests passed;
  smoke **108/108** and deliberate fault **86/108** (`/tmp/musnba_a1_parallel_{smoke,fault}.log`).
  AGENTS, HANDOFF, PLAN, TRAINING_PLAN, FINDINGS and README record the budget, work and evidence; ENGINE_PLAN
  needs no change (model decisions and gates unchanged); DASHBOARD_PLAN needs no change (no UI shipped).
- **A1 90% persisted-scale design, frozen before implementation:** run a research-only fixed F4, one-player
  plays-branch test using the pinned parallel pilot inputs and ten single-thread workers. Generate 10,000
  accepted independently seeded worlds in 100 batches of 100; batch 0 uses the pilot's base seed, later
  batch seeds are deterministically derived from the base seed and batch index. Inject one explicitly labelled
  rejection at batch 0/world 1 and record every rejection and accepted seed with finite per-world/global caps.
  Persist each batch of captured traces, scores and minutes under a fresh ignored directory, fingerprint every
  file, then independently read and audit every batch and verify the first 20 against the serial pilot except
  for the replaced world. Report at each 1,000 accepted worlds, record generation and separate audit times,
  source/input hashes, storage and limitations. Refuse existing outputs and fail explicitly on any unclassified
  or accounting error. Do not treat this synthetic single-game experiment as a representative failure rate,
  unbiased retry, predictive gain, calibrated availability, full-slate runtime or production promotion.
  If interrupted, retain completed batch files and logs; start a fresh run rather than overwrite them unless a
  verified resume mechanism is added. A successful test does not clear the remaining A1 cutoff and fold gates.
- **A1 persisted-scale result:** 10,000 worlds, synthetic selected availability, ten single-thread workers,
  generated in **676.162 s**, with one intentionally injected rejection and no others on this one F4 game.
  Independent saved-file replay passed **10,000** per-world hashes/seeds and **2,546,803** lineup snapshots,
  including minutes/points and the first 20 serial-pilot identities, in **18.013 s**. Compressed `.npz` batches
  total **18,348,870 bytes** in ignored `data/derived/experiments/20261122_chunk_a_a1_parallel_capture10000_v1/`;
  report/audit `analysis/experiments/20261122_chunk_a_a1_parallel_capture10000_v1{,_audit}.json`. First 100-world
  rehearsal found trace dtype promotion; corrected v2 and regression test preserve the original dtype. The v1
  rehearsal's intermediate source was not committed. This is not full player-box accounting, a full-slate
  benchmark, a representative rejection rate, cross-fold bias comparison or calibrated availability. Research
  remains unwired and production is unchanged. Focused capture/retry/context checks **12/12**, smoke **108/108**,
  deliberate fault **86/108** (nonzero exit), logs `/tmp/musnba_a1_capture_{smoke,fault}.log`. Before the newly requested D50 implementation, preserve this
  checkpoint; after D50, return to A1's explicit gate/fallback decision and the owner's stop-at-A1 boundary.
- **A1 80% shared-scenario groundwork, partial:** `outcomes.mjs` now adapts an explicitly supplied validated
  research source and binds weighted probability mass, counts, distributions, means, correlations and half-open
  grids to one selected world set. `scenario.mjs` uses those calculations when injected, otherwise the existing
  equal-world source; no app code supplies a branch source or exposes a lineup selector. Availability and
  participation are separate, exact-minute conditions retain float64 precision, OTs use final periods and invalid
  branch conditions fail closed. Shared arithmetic lives in `scripts/webapp/weighted-worlds.mjs`; the old analysis
  module re-exports it, and current probes hash the actual arithmetic. Scenario copy now says Participation
  rather than calling non-participation availability.
  Independent Python-reference audits on **20k / 40k** research worlds matched full/fixed/empty conditional masses,
  **90** home-point bins, and **1,800 / 1,830-second** conditions. A local Chrome injection on the 40k fixture matched
  the independently audited **42** rendered Joint cells, Given, a 30-minute scenario (**56.6%**, home win given
  **57.2%**) and a fixed-lineup empty condition; one run measured **0.68 s** JSON parse, **0.67 s** decode,
  **1.25 s** scenario and **0.09 s** Given/grid rendering, **615 MB** JS heap after the sequence, with other
  audit jobs running. This is one desktop research run, not device acceptance or a full coherent Game Centre.
  Reports `analysis/experiments/20261122_chunk_a_a1_d47_shared_{adapter*,scenario_browser_two_v1}.json`.
  Full-mixture summary and Expected-payload audits were re-run after the shared-source hash change using suffix
  `_shared_v1`; the prior reports remain historical evidence tied to their original source.
  **Still open:** integrate the single common either/available/unavailable control across coherent selected
  player/team/sheet views, derive or omit unconditional-dependent cards and metadata, finish phone Expected-only
  bundle contract and actual import/offline testing, runtime/fold/promotion checks and fallback. Never expose the
  injection hook as a production selector until all consumers agree. A1 remains **70%**, Chunk A **31.5%**.
  Focused JS and 4 bundle-profile tests pass; smoke **108/108**, deliberate fault **86/108** exit **1**;
  unconditional responsive checks **24/24** and reviewed screenshots at 1440/960/390 in both themes.
  Final data-free shell `gh-pages` **b399409**, cache **b39817708fcf4bc9accb**; local laptop/phone import/offline
  **25/25** each, final-shell update **27/27**, hosted forced-bypass laptop/phone **29/29** each.
  `--export-only` refreshed unchanged retained views to iCloud:
  phone **1,999 records / 13.9 MB** SHA-256 `8bd5ec9396e60aadd4c519bccd5a66cbdf4f21a98484e480abfad54acba2d709`;
  laptop **2,031 / 65.3 MB** SHA-256 `41eff00bcc79b51128e8d4480c174e2c23bf5f79a64ad0e3c1708db3770379c6`.
  Manual phone import is still required; an export does not prove device acceptance. No model or forecast changed.
  HANDOFF/PLAN/FINDINGS/DASHBOARD_PLAN/README record this change; AGENTS, ENGINE_PLAN and TRAINING_PLAN do not
  change because standing rules, decisions and gates are unchanged.
- **A1 80% Expected-only payload groundwork:** fixtures now include independently checked origin-snapshot player
  identity/status fields, model/engine identifiers and snapshot file hashes; branch-specific starter and minute
  targets are not copied from the unconditional snapshot. `analysis/a1_expected_payload.mjs` accepts only an
  unfixed Expected summary and produces a compact, explicitly research-only payload without raw branch worlds.
  Separate Python accounting matched all summaries and **25 / 28** identities to the audited **20k / 40k**
  inputs. Payloads were **626,499 / 734,772 bytes** raw and **194,699 / 230,821 bytes** gzip-6 in Python
  (**190,705 / 226,047** in Node).
  They have not been integrated into an app bundle or imported into a browser or phone; no Given/Joint capability
  is implied by these compact files. Inputs and evidence:
  `data/derived/experiments/20261122_chunk_a_a1_d47_{browser_fixture,game_summary}_{one,two}_identity_v1.json`,
  `data/derived/experiments/20261122_chunk_a_a1_d47_expected_payload_{one,two}_v1.json`,
  `analysis/experiments/20261122_chunk_a_a1_d47_browser_fixture_{one,two}_identity_v1_audit.json`,
  `analysis/experiments/20261122_chunk_a_a1_d47_game_summary_{one,two}_identity_v1_{probe,audit}.json`, and
  `analysis/experiments/20261122_chunk_a_a1_d47_expected_payload_{one,two}_v1_{probe,audit}.json`.
  UI, real browser/phone/offline checks and model gates remain open; A1 **70%**, Chunk A **31.5%**. The production
  model, forecasts, bundles and shell are unchanged. HANDOFF/PLAN/FINDINGS record evidence and README maps scripts;
  AGENTS, ENGINE_PLAN and TRAINING_PLAN need no change (rules, decisions and gates unchanged); DASHBOARD_PLAN needs
  no change (no UI shipped).
  Synthetic tests reject fixed selections and inconsistent provenance; a mismatched real fixture/audit failed
  explicitly without creating output, log `/tmp/musnba_a1_payload_reject.log`. Focused Python/JS tests pass;
  normal smoke **108/108** and deliberate fault **86/108**, exit **1**, with four OpenMP threads per process,
  logs `/tmp/musnba_a1_payload_{smoke,fault}.log`.
- **A1 80% weighted game-summary groundwork:** `analysis/a1_branch_game_summary.mjs` derives team/player
  period means, distributions, shooting-attempt mass, exact mean seconds, availability, participation,
  simulated opening-five shares, multi-doubles and if-plays values from one selected weighted world set.
  It carries selected-player status/source, impact metadata and the uncalibrated weight assumptions. A separate
  original-capture reconstruction checked **3,303** distributions and **3,124** means for the 20k full
  sample, and **3,696** distributions plus **3,453–3,488** means for **each** of the nine two-player
  either/plays/sits selections (10k, 20k or 40k saved worlds). All matched. Integer histograms use rounded
  minutes, while mean seconds and the underlying world values retain original precision; filters must continue
  using the latter. Selected/defined histogram masses are integer weight units, **not simulation counts**.
  On one Node process per two-player selection, the **202.7 MB** raw fixture took **6.01–8.20 s** to summarize;
  outputs were **614,544–728,558 bytes**, with peak RSS up to **722,144 KiB**. Other smoke jobs ran concurrently.
  These are Node measurements,
  not browser/phone benchmarks. Reports use
  `analysis/experiments/20261122_chunk_a_a1_d47_game_summary_two_*_v{3_probe,4_audit}.json` and
  `game_summary_one_full_v{3_probe,5_audit}.json`; full summaries are ignored in `data/derived/experiments/`.
  This is **not** a complete Game Centre contract: wire weighted Given/Joint, grids, lead-fan, advanced/spotlight
  and other dependent cards or explicitly omit them, handle branch-specific minute-basis metadata, and verify
  laptop/phone UI and offline behavior. No app, production model or bundle changed; A1 **70%**, Chunk A **31.5%**.
  HANDOFF/PLAN/FINDINGS record evidence and README maps scripts. AGENTS, ENGINE_PLAN and TRAINING_PLAN need no
  change (rules, decisions and gates unchanged); DASHBOARD_PLAN needs no change (no UI shipped).
  Focused Python/JS tests pass; normal smoke **108/108** and deliberate fault **86/108**, exit **1**, with four
  OpenMP threads per process; logs `/tmp/musnba_a1_summary_{smoke,fault}_v2.log`.
- **A1 80% opening-five groundwork:** the research fixtures now retain each world's first captured Q1 12:00
  lineup, with five distinct available teammates per side. These are simulated opening fives, not official
  starters. Independent original-trace replay reconciled **200,000 / 400,000** lineup entries on **20k / 40k**
  worlds; JS matched **50 / 112** per-branch player counts. In the two-player case, **4** players' opening-five
  counts changed between branches (two selected players and two replacements), proving unconditional starter
  metadata is unsafe. Fixtures are **90,562,924 / 202,725,520 bytes** raw, not phone benchmarks. Reports
  `analysis/experiments/20261122_chunk_a_a1_d47_browser_fixture_{one,two}_opening_v2_audit.json` and
  `analysis/experiments/20261122_chunk_a_a1_d47_source_{one,two}_opening_v1_audit.json`; ignored fixtures are
  `data/derived/experiments/20261122_chunk_a_a1_d47_browser_fixture_{one,two}_opening_v1.json`.
  This supports deriving the selected worlds' opening fives; it does not reconstruct branch minute-target
  metadata or integrate a view. HANDOFF/PLAN/FINDINGS record results; README maps the source. AGENTS,
  ENGINE_PLAN and TRAINING_PLAN need no change (rules, decisions and gates unchanged); DASHBOARD_PLAN needs no
  change (no UI shipped). The production model, bundle and shell remain unchanged; A1 **70%**, Chunk A **31.5%**.
  Focused Python/JS tests pass; normal smoke **108/108** and deliberate fault **86/108**, exit **1**,
  logs `/tmp/musnba_a1_opening_{smoke,fault}.log`.
- **A1 80% overtime and adaptive-grid groundwork:** research fixtures now retain each world's actual final period,
  not an overtime flag inferred from points. Independent capture accounting reconciles **20,000 / 40,000**
  values and all four weighted overtime-count categories (0–3 OTs) in each sample. The branch source fails
  explicitly if final-period data is absent instead of guessing. Its selected-player minute grid uses weighted
  2nd/98th-percentile edges and half-open continuous intervals: independent reconstruction of **49 / 42** cells
  preserved all exact mass for the one-/two-player captures, including fractional minutes. Synthetic tests include
  all 9 two-player selections, corruption and fractional boundary cases. Reports
  `analysis/experiments/20261122_chunk_a_a1_d47_browser_fixture_{one,two}_period_v3_audit.json`,
  `source_{one,two}_period_v{4_audit,7_crosscheck}.json`,
  `dynamic_grid_{one,two}_v{2,3_audit}.json`.
  New ignored fixtures use `data/derived/experiments/20261122_chunk_a_a1_d47_browser_fixture_{one,two}_period_v2.json`.
  Normal smoke **108/108** and deliberate fault **86/108**, exit **1**, logs
  `/tmp/musnba_a1_ot_grid_{smoke,fault}.log`. HANDOFF/PLAN/FINDINGS record evidence and README maps scripts;
  AGENTS, ENGINE_PLAN and TRAINING_PLAN need no change (rules, decisions and gates unchanged); DASHBOARD_PLAN
  needs no change (no UI shipped). This is isolated accounting, not browser integration, calibration or
  promotion. A1 **70%**, Chunk A **31.5%**. Live model, bundles and shell remain unchanged.
- **A1 80% period-aware source, research only:** the fixture now preserves all five original player-period boxes
  and float64 minutes, and checks player/team score identity in each period. Independent capture audits reconcile
  **35,000,000 / 78,400,000** period-stat values and **2,500,000 / 5,600,000** exact period minutes on the
  **20k / 40k** one-/two-player worlds. An isolated JS source checks branch weights, assignments, participation,
  period-to-game totals and period scores; its seven periods' **21** player/team weighted means agree with the
  separate capture audit for each game. Synthetic tests cover all **9** two-player either/plays/sits selections
  and corrupt data. Full/partial/empty Given masses and **90** home-point bins still agree with prior independent
  reports. `analysis/a1_branch_world_source.mjs` and the audit are not connected to the app or bundle.
  The new fixtures are **90,269,502 / 202,138,676 bytes** raw, **23,633,263 / 47,709,803 bytes** in gzip-6
  stream probes, not phone bundles. On the 40k fixture, one isolated Node run initially peaked at
  **2,608,368 KiB**, taking **5.28 s** to decode/validate; bounded decoding then peaked at **835,328 KiB**,
  taking **0.55 s**, with another audit running concurrently. These are single process samples, not browser,
  phone, full-dashboard or predictive benchmarks. Outputs: `analysis/experiments/20261122_chunk_a_a1_d47_`
  `browser_fixture_{one,two}_period_v2_audit.json`, `source_{one,two}_period_v2_audit.json`,
  `source_{one,two}_period_v3_crosscheck.json`, `source_two_period_v{1,2}_benchmark.json`.
  A1 remains **70%**, Chunk A **31.5%**. Doc review: HANDOFF/PLAN/FINDINGS record the partial evidence and
  next work; README maps the new scripts. AGENTS, ENGINE_PLAN and TRAINING_PLAN need no change because standing
  rules, design decisions and promotion gates are unchanged; DASHBOARD_PLAN needs no change because no UI shipped.
  Focused Python/JS checks pass; normal smoke **108/108** and deliberate fault **86/108**, exit **1**, logs
  `/tmp/musnba_a1_period_{smoke,fault}.log`. Existing forecasts, bundles and Pages shell are unchanged;
  device import remains a separate manual action.
- **A1 60% research accounting:** a common-interval prototype preserves exact per-game score vectors through
  weighted season paths, without duplicate near-term games. A reproducible independent replay checked all
  **17** near-term game score-vector marginals and per-path scores/wins, **959** game win probabilities, and
  **30** teams' full win/seed distributions. Two games use branch mixtures; the other **15** use retained
  unconditional worlds, including games that could require branches. It is not complete branch integration.
  At seed 20261122, **122,428** weighted paths with denominator **160,000** took **6.86 s** in the team pathway
  plus **4.75 s** for weighted summaries (1.68 GB maximum RSS in this run); the independent replay took **12.44 s**.
  Across **32** seeds and **136** game pairs, joint-win covariance ranged **−0.0071245 to +0.00728455**;
  mean absolute covariance averaged **0.001403**, versus **0.001843** for a separate 10,000-independent-draw
  reference. This comparison does not establish realistic predictive dependence or accept the method. A research
  **200,000-path** default limit fails explicitly before coupled score arrays are built, but is not a full memory
  guarantee. Preserve the existing production pathway. Reports
  `analysis/experiments/20261122_chunk_a_a1_d47_season_{coupling_17_provenance,dependence_17_provenance,audit_17_provenance}.json`;
  full weighted results remain ignored in `data/derived/experiments/20261122_chunk_a_a1_d47_season_pathway_17_mixed.json`;
  the committed audit is a compact summary.
  Earlier `_mixed`, `_bounded` and `_labelled` runs predate final helper hashes; use `_provenance` for current
  source-hashed reproduction. No model, snapshot, bundle or shell changed.
- **A1 70% research labels:** weighted Expected reports now retain selected players' status/source, role basis,
  missing fields and uncalibrated weight assumptions. Season coupling also retains these assumptions and explicitly
  labels unvalidated within-/across-game dependence and unconditional inputs. Synthetic missing-status and
  cold-role cases retain `Unknown`, null source and prior/missing labels; short rosters already fail explicitly.
  The two 10k branch cases had **71** ranked player records, **4** prior roles, and **48** unlisted-active
  assumptions; their **3** selected players had no missing role/usage fields. This is coverage, not calibrated
  health. **33** focused tests pass; the 40k-world labelled Expected distribution equals the prior report exactly.
  The re-run source-hashed labelled coupling reproduced **17** marginal/per-path, **959** game and **30** team
  identities; its 32-seed dependence report reproduced the research comparison. Reports use suffix `_labelled`.
  Labels are in research outputs, **not yet in the dashboard**; no production model or bundle changed.
- **A1 80% partial accounting:** the isolated `weighted_joint` computes exact event, Given and intersection
  probability masses from the same weighted branch worlds and returns an explicit empty-condition state.
  Independent reconstructions of the four-branch sample (**40,000** worlds) and two partial lineup selections
  (**20,000** worlds each) matched every rational probability. For the sample home-win event given positive
  minutes by player `3032977`, the full mixture yielded **281/500**; fixing him unavailable produced an empty
  condition, while fixing the other selected player unavailable yielded **6877/10000**. These are isolated
  accounting examples, not current delivered forecasts. Branch availability and positive minutes remain
  different conditions. Reports `analysis/experiments/20261122_chunk_a_a1_d47_joint_{full,empty,other_sits}_v2.json`.
  The shared UI still counts equally weighted worlds and the 80% rung remains open.
- **A1 80% isolated browser fixture:** `analysis/a1_branch_browser_fixture.py` packs independently audited branch
  captures into existing browser column order, carrying exact branch weights, assignments, status/source labels,
  explicit per-world availability and **exact positive-minutes participation** separately from rounded minutes.
  It rejects unrepresentable bytes instead of clipping. The saved four-branch fixture has **40,000** worlds and
  is ignored at `data/derived/experiments/20261122_chunk_a_a1_d47_browser_fixture_two_v3.json`. The independent
  decoder `analysis/a1_branch_browser_fixture_audit.py` reconciled **16,800,000** player-stat, **1,120,000**
  availability, **1,120,000** participation and **400,000** team-period values with exact weight sum **1**.
  Among those unweighted player-world records, **6,527** positive appearances rounded to zero displayed minutes
  and **182,738** available players did not play. Existing `outcomes.mjs` infers plays from rounded minutes;
  that is not interchangeable with exact participation or availability. This fixture is **25,924,636 bytes**
  uncompressed; an in-memory gzip-6 probe was **8,238,264 bytes**, not a transfer or phone benchmark, for the
  earlier v2. **D49:** the owner requested better time sensitivity; v3 preserves the original full-precision
  float64 minutes (with second-level filtering) in addition to the legacy rounded column. The v3 two-player
  fixture is **37,871,388 bytes** raw, **13,715,049** in a gzip-6 memory probe. A 30-minute threshold differs
  from filtering rounded minutes in **963 / 40,000** worlds for the first selected player; the one-player game
  differs in **187 / 20,000**. Python and JS agree exactly on condition masses at **30 and 30.5 minutes**.
  `analysis/a1_weighted_browser.mjs` and its separate audit reproduce the Python full/partial/empty Given/Joint
  masses and all **90** home-points bins for each of the **20,000 / 40,000** one-/two-player worlds using exact
  integer masses. The one-player fixture has **3,712** additional positive appearances rounded to zero and
  **39,675** available non-appearances across **500,000** player-world records; the v3 full-precision fixture
  is **16,935,858 bytes** raw, **6,633,644** in a gzip-6 memory probe.
  Reports `analysis/experiments/20261122_chunk_a_a1_d47_{browser_fixture_one_v5_audit,browser_fixture_two_v5_audit,
  browser_weighted_one_v5_audit,browser_weighted_two_v5_audit,browser_weighted_one_1800sec_v3_audit,
  browser_weighted_two_1800sec_v3_audit}.json`; prior fixture/audits are superseded.
  These are experimental and **not** connected
  to the app or bundle; 80% remains open. **76** targeted Python tests pass; normal smoke **108/108**
  (`/tmp/musnba_a1_precision_smoke.log`), deliberate fault **86/108** with exit **1**
  (`/tmp/musnba_a1_70_fault_v3.log`).
- **A1 80% weighted grid groundwork:** isolated browser arithmetic now also handles exact-mass 2-D cells and
  weighted correlation without rounding player minutes. A separate Python reconstruction and JS audit matched
  all four cells and the correlation within `1e-12` for the **20k / 40k** research worlds, using a 30-minute
  and 115-home-point split. Report
  `analysis/experiments/20261122_chunk_a_a1_d47_browser_grid_{one,two}_v2_audit.json`. The split is a fixed
  accounting example, not a forecast or calibrated dependence claim. Actual scenario bins, grids and all other
  existing consumers still need integration and browser/phone tests before this rung can be credited.
- **Smoke integration:** newly retained weighted-season `.npz` files exposed that smoke previously treated every
  root experiment `.npz` as a training-loss file. Smoke now selects the timestamped filenames written by
  `train.py`; a focused regression test includes both a loss file and an unrelated season array. No accounting
  check was disabled. After the fix, normal smoke passed **108/108** and deliberate fault exited **1** with
  **86/108** checks passing, logs `/tmp/musnba_a1_70_smoke_v2.log` and `/tmp/musnba_a1_70_fault_v3.log`.
- **D48 partial retry research, not a rung or production change:** `scripts/a1_world_retry.py` runs independently
  seeded, single-world callbacks, catches only explicitly classified recoverable failures, records attempt seeds
  and reasons, and enforces both per-world and total rejection caps. The branch-only repair now raises the specific
  `ExhaustedEligiblePlayers` type only when fewer than five players remain after foul-outs; ordinary roster, input,
  accounting and unknown errors are not classified as retryable. The coordinator is **not wired to the engine or
  nightly**. In fixed development-fold game `401810327`, a deliberately injected post-audit rejection produced
  three accepted worlds in seven attempts across control+retry; all arrays and seeds of the two unaffected worlds
  were identical. Seven single-world attempts took **3.35 s** combined (0.44–0.52 s each); this small pilot does
  not establish 10k runtime. A 10,000-draw synthetic example rejected **495** attempts affecting **472** worlds
  and shifted the mean **0.49810 → 0.52300** (theoretical **0.500 → 0.525**), demonstrating conditional-sampling
  bias, **not an NBA failure rate or forecast bias**. Current source-hashed reports
  `analysis/experiments/20261122_chunk_a_a1_d48_{isolated_world_probe_v3,synthetic_bias_v2}.json`.
  Before any use: prove real failure classification/isolation and audited persisted outputs at scale; measure
  observed rejection rates and bias on earlier folds; compare against the existing S06 penalty candidate with
  policy differences disclosed; validate retry limits and runtime. Do not mask input/system failures.
- **D48 artificial short-roster stress:** the first five-player preparation with original D29 roles failed its
  240-minute legality check before simulation; this is the known allocator limitation, not a world to retry.
  With the five retained players given explicitly synthetic 48-minute roles, actual simulated foul-outs produced
  **18** specifically classified rejections in **28** attempts for **10** independently audited valid worlds;
  **12.13 s** elapsed. A second run with a maximum of two rejections stopped on the third rejection and retained
  its reasons. This deliberately extreme **18/28** rate is not an NBA estimate; frequent failures must stop rather
  than be hidden in production. Reports `analysis/experiments/20261122_chunk_a_a1_d48_five_player_{initial_failure,
  stress10,stress_cap}.json`. The existing S06 foul-penalty comparison and predictive bias remain open.
- **Existing S06 comparison context:** its alternative player-foul-penalty rule retained an otherwise-disqualified
  player and recorded a technical in the earlier eight-player F4 failure. Its **200-game** fixed screen improved
  pooled minutes CRPS **3.5662 → 3.5309** but established only **66/69** non-inferiority bounds, so it was not
  promoted. At this earlier checkpoint no matched retry-versus-penalty comparison had been run; the later
  research-only comparison above uses a D29-matched penalty continuation, not this selected-timeout policy.
  See FINDINGS S06; do not treat the two as the same simulation policy.
- **D48 artificial S06 comparison:** on the **18** seeds rejected in the extreme synthetic five-player D29
  stress, the distinct S06 selected-timeout/foul-penalty policy completed **18/18** single-world attempts.
  **13** worlds recorded technicals, **35** technical events total. Independent saved-trace replay reconciled
  **10,698** fives and all technicals. Different substitution policies and random streams mean the matched seeds
  are **not** matched game states: five S06 worlds had no technical at all. This is neither an NBA failure rate
  nor the missing retry-versus-penalty predictive/bias comparison. The first unsaved-capture run is
  `analysis/experiments/20261122_chunk_a_a1_d48_penalty_five_player_compare.json`; reproducible saved-world
  report/audit use `_compare_v2{,_audit}.json`, with ignored captures in
  `data/derived/experiments/20261122_chunk_a_a1_d48_penalty_five_player_compare_v2/`. Reproduce the independent
  audit under a new name with `.venv/bin/python analysis/a1_retry_penalty_stress_audit.py analysis/experiments/20261122_chunk_a_a1_d48_penalty_five_player_compare_v2.json --output analysis/experiments/<new-audit>.json`.
- **Research checkpoint doc review:** HANDOFF and PLAN record progress and stop point; ENGINE_PLAN and
  TRAINING_PLAN record D48/D49 and their gates; FINDINGS records observations and limits; README maps the research
  scripts. AGENTS needs no change because standing rules are unchanged; DASHBOARD_PLAN needs no change because
  the isolated fixture is not served or shipped. The production engine, snapshot, bundle and Pages shell remain
  unchanged; the previous iCloud bundle still requires manual phone import.
- **D47 owner clarification:** candidate prospective lineup certainty uses 0/25/50/75/100%, mapping to nearest
  quarter with halfway ties up and preserving uncertain values inside 25–75%. This applies consistently to
  selected weights and other per-world availability draws; original inputs/sources remain recorded. Probable's
  current 90% becomes 75%, not 100%. These are uncalibrated assumptions. The interrupted pre-D47 capture remains
  wiring evidence. D47 is implemented in the isolated branch path: **27** focused tests pass and two 32-world
  pilots passed independent auditing, with **128 / 64** branch worlds and exact unit weights for two / one
  selected players. Reports: `analysis/experiments/20261122_chunk_a_a1_d47_32_{two,one}.json`.
  The one-player 10k run passed independent auditing: **20,000** worlds, **4,997,124** lineup snapshots, exact
  weight sum **1**, branch times **157.5 / 155.6 s**. Report
  `analysis/experiments/20261122_chunk_a_a1_d47_10000_one.json`, log `/tmp/musnba_a1_d47_10000_one.log`,
  captures `data/derived/experiments/20261122_chunk_a_a1_d47_10000_one/`.
  The four-thread production-scale replay also passed independent auditing; all **31** saved arrays per branch,
  both capture hashes, assignments, weights, seeds, rankings and input hashes match the eight-thread run.
  Its branch times were **236.5 / 232.3 s**, log `/tmp/musnba_a1_d47_10000_one_threads4.log`, with
  corresponding `_threads4` report/capture paths. The two-player 10k run for the previously failed game completed
  under D47: **40,000** worlds, **9,999,905** lineup snapshots, exact weight sum **1**, branch times
  **162.4 / 158.4 / 160.7 / 157.6 s**; independent saved-box/weight audit passed. A separate replay of saved
  traces checked **19,999,810** team fives (not distinct lineups), minutes and points (maximum minute error
  **1.78e-15**). Report
  `analysis/experiments/20261122_chunk_a_a1_d47_10000_two.json`. This success does not resolve the earlier
  unsupported short-roster failure. The four-thread replay matched all **31** arrays and capture hashes in all
  four branches, as well as input hashes, selection, assignments, weights and seeds; independent box/weight
  audit passed. Branch times **246.1 / 244.8 / 245.6 / 237.1 s**, report/capture suffix `_threads4`, log
  `/tmp/musnba_a1_d47_10000_two_threads4.log`. **77** branch/availability/rotation tests passed; smoke **108/108**,
  deliberate fault exited **1** (86/108), logs `/tmp/musnba_a1_d47_{smoke,fault}.log`. No branch job is running.
  Keep production unchanged until its gates pass.
  Doc review: HANDOFF and PLAN record the live progress and next actions; ENGINE_PLAN and TRAINING_PLAN record
  D47 and its gates; FINDINGS records measured evidence and the failed pre-D47 case; DASHBOARD_PLAN records the
  planned weighted Given/Joint design; README maps the research scripts. AGENTS needs no change because standing
  rules are unchanged. No nightly, bundle, shell or served model changed.
- **A1 50%:** `scripts/a1_expected.py` forms exact-weight empirical distributions from every audited branch world,
  including either/plays/sits marginalisation and undefined shooting denominators. **32** focused branch and
  mixture tests pass, including the **1/20,000** indivisibility counterexample. Independent reconstruction of
  game `401910030` checked full/one-player-conditioned home points and player FG%: **40,000 / 20,000 / 40,000**
  worlds, **90 / 88 / 209** exact histogram bins, means, quantiles and missing masses. The full team-points CLI
  took **0.55 s** warm-cache, report **8,718 bytes**, not a full pipeline benchmark. Experiment reports are
  `analysis/experiments/20261122_chunk_a_a1_d47_expected_{home_pts,home_pts_sits,player_fgpct}.json`.
  This is isolated accounting, not an accepted forecast. Season identity, foul exception, dashboard and promotion
  remain open. No model, snapshot, bundle or shell changed.
- **Dashboard house follow-up:** game player pages put box scores first, with a shortcut to player insights;
  availability and each bench are expandable. Team rosters collapse bench, fringe, no-projection and out groups,
  keeping starters visible. Player game logs also expand on demand. Expanded game sections survive mode changes;
  roster groups survive the schedule/roster toggle. **61/61** responsive cases passed with screenshots inspected;
  local laptop/phone import and offline **29/29 / 28/28**, installed-shell upgrade **31/31**. A fresh-import
  race on Pages was reproduced with service-worker bypass: the API shim missed `URL` inputs and hit a 404.
  The shim now handles URL, string and Request inputs; forced-bypass local and hosted laptop/phone checks passed
  **31/31 / 30/30**, and the installed-shell upgrade passed **31/31**. Bypass deliberately excludes image
  interception; the test reloads after restoring the worker before checking logos. The data-free Pages shell is
  **1fa44ca**, cache **5da19e194a1a5b297b5d**; hosted module hash matches the built shell. Prior shell archived at
  `~/Basketball_archive_ops/gh-pages-before-pwa-url-fix-331323d.tar`. No model, snapshot or bundle changed; a device with the existing
  data needs an **app update**, not another data import. Manual imports from the previous data export remain
  unconfirmed. Final normal smoke **108/108**; deliberate fault exited **1** (86/108), logs
  `/tmp/musnba_house_pwa_url_{smoke,fault}.log`. Doc review: HANDOFF, PLAN, FINDINGS and DASHBOARD_PLAN record the
  hierarchy and startup evidence; README maps the research helper
  and existing update workflow; AGENTS, ENGINE_PLAN and TRAINING_PLAN retain standing rules and model gates.
- **A1 40% partial (superseded selection):** isolated origin-aware selection applies the old healthy-role/usage thresholds and labels
  unknown usage or prior-only roles, preserving status source and effective probability; mismatched rosters,
  invalid values and non-prior minutes history fail. The caller must supply cutoff-safe roster and profiles.
  **60** branch/selection/rotation/availability tests passed;
  on current-origin game `401910029` the retained inputs select **3** players, with **1** prior-only role and
  **1** missing usage, producing **4** unweighted sensitivities. This is an input sanity check, not a forecast
  or calibration. Normal smoke **108/108**; deliberate fault exited **1** (86/108), logs
  `/tmp/musnba_a1_40_selection_{smoke,fault}.log`. This initial selection check did not simulate worlds;
  the later persistence probes and D47 40% completion are recorded above.
- **A1 persistence in progress:** `scripts/a1_branch_persist.py` is an isolated research path, not wired to
  serving/nightly. It requires a matching prospective snapshot and current retained origin inputs, records exact
  branch seeds/weights, selection and source/model hashes, audits lineups and retains complete player boxes.
  `analysis/a1_branch_persist_audit.py` independently checks assignments, rational weights, fixed availability
  and shooting/score accounting. Current-origin game `401910029`: **4 × 32** unweighted sensitivities passed,
  **32,123** lineup snapshots; replay was identical across every saved array with 8 versus 4 LightGBM threads.
  One-player game `401910043` and two-player game `401910033` each passed **32** worlds per branch and exact
  independent weight totals of **1**. **30** focused tests passed. Preliminary report
  `analysis/experiments/20261122_chunk_a_a1_persist32.json` predates the capture-source hardening;
  use `_v2`, `_replay` and `_threads4` for reproducibility. No outcome was scored against the protected season.
  Checkpoint smoke **108/108**; deliberate fault exited **1** (86/108), logs
  `/tmp/musnba_a1_persist_checkpoint_{smoke,fault}.log`. AGENTS and DASHBOARD_PLAN need no change: this is
  isolated research and no serving, model, bundle or presentation behaviour changed.
  The earlier **10,000-world** four-sensitivity test passed: **40,000** worlds, **20,020,614** legal fives and
  independent saved-box accounting; max replayed-minute error **3.55e-15**. Per-branch elapsed **158.5 / 156.3 /
  155.1 / 157.4 s**, log `/tmp/musnba_a1_persist10000.log`, report
  `analysis/experiments/20261122_chunk_a_a1_persist10000.json`, captures
  `data/derived/experiments/20261122_chunk_a_a1_persist10000/`. **D46 supersedes that selection**; it remains
  wiring evidence, not the new design. The old 10k two-player run was stopped at **2/4** when D46 arrived:
  log `/tmp/musnba_a1_persist10000_two.log`, partial captures
  `data/derived/experiments/20261122_chunk_a_a1_persist10000_two/`; no completed report. The prior source was
  preserved in **368a1de**. The D46 revision now ranks the full origin roster by the documented offensive proxy,
  selects at most one top-three uncertainty per team, records all ranks, and treats no qualifying players as a
  valid no-branch result. The median-input cutoff guard rejects missing dates and any games on/after origin; this
  origin's maximum was **2026-11-21**. Across **17** current two-slate games, **4** have two selections,
  **6** have one and **7** have none. New 32-world one-/two-player and no-branch captures passed independent
  checks, exact branch-weight totals **1**, and **32** focused tests. Reports
  `analysis/experiments/20261122_chunk_a_a1_d46_32_{none,one_v2,two_v2}.json`. Earlier `_one`/`_two`
  are preliminary pre-hardening probes. A 10k run was stopped before the first branch to add an overflow guard;
  its empty capture directory is `data/derived/experiments/20261122_chunk_a_a1_d46_10000_two/`.
  The hardened pre-D47 10k two-player test stopped in branch 2/4: game `401910030`, world **1430**, side **1**,
  period 4 at 11.7 seconds remaining had fewer than five eligible players after fouls. Branch 1/4 finished in
  **163.1 s** and its 10,000-world capture is retained at
  `data/derived/experiments/20261122_chunk_a_a1_d46_10000_two_v2/branch-000.npz`; the error is in
  `data/derived/experiments/20261122_chunk_a_a1_d46_10000_two_v2/failure.log` (also in
  `/tmp/musnba_a1_d46_10000_two_v2.log`). No complete manifest was written. This is the explicitly unsupported
  NBA short-roster exception, not a successful capture. Preserve both artifacts and do not silently activate
  an illegal player; the later D47 representative case passed, but the general limitation remains. On the failed
  team's retained source roster all **18/18** unique players reached the registry (seven out, one uncertain,
  ten assumed available). This does not independently establish official active-list completeness. The owner
  asked about bench depth: the policy already substitutes eligible bench players; investigate source coverage
  and reuse/test the existing S06 foul-penalty candidate rather than inventing additional players.
- **D48 owner fallback proposal:** generally replace explicitly identified world-local recoverable failures until
  10,000 valid worlds remain, counting rejected attempts/reasons and capping retries. Missing/corrupt input,
  cutoff/accounting violations, unknown exceptions and systematic failures must still stop immediately. No
  production implementation or promotion yet. The engine
  uses shared vectorised random streams and currently aborts the batch, so first isolate individual invalid worlds
  and prove deterministic replacement without changing survivors. Rejection is conditional sampling and can bias
  forecasts; measure the failure rate/effect, compare with the isolated S06 foul-penalty rule and keep explicit
  failure for frequent errors. Do not silently reactivate unavailable players or claim the NBA exception is solved.
- **Dashboard house pass:** Today puts games first with a shortcut to the still-accessible slate insights. Players
  keeps its table visible and movers expandable; player pages prioritise the next forecast and collapse opponent
  history and advanced rates. Game-player sheets put conditional/joint outcomes and comparisons before collapsible
  advanced rates; advanced panels and charts retain their open state across stat/line edits. Responsive browser
  **43/43** with screenshots inspected; local and hosted offline laptop **26/26**, phone **25/25**, old-to-new upgrade
  **28/28**. Smoke **108/108**; deliberate fault exited **1** (86/108). Data-free Pages **8dfbbd7**, cache
  **5fcf7fcb83ffae8939a5**; hosted HTML, service worker and four changed modules match the reviewed shell byte-for-byte.
  Existing iCloud bundles are unchanged;
  no new nightly or model change. Manual imports from the previous per-world export remain unconfirmed.
  Doc review: HANDOFF, PLAN and DASHBOARD_PLAN record the changed hierarchy; AGENTS, ENGINE_PLAN, TRAINING_PLAN,
  FINDINGS and README need no changes because standing rules, engine/gates, empirical results and commands are unchanged.
- **A1 30%:** the isolated `scripts/a1_lineup_branches.py` enumerates one/two-player assignments with exact
  rational products from the game input probabilities, sorted IDs and validated unit total. More than two yields
  only all-play/one-out assignments with no weights. `prepare_branch` fixes all selected players simultaneously
  before the existing D29 re-solve; impossible short rosters fail. **57** focused branch, availability, rotation
  and accounting tests passed, including long-decimal arithmetic, order-independent IDs/seeds and original-input
  immutability; an independent **100-input** exact marginal-accounting check also passed. Normal smoke passed
  **108/108**; deliberate fault exited **1** (86/108), logs `/tmp/musnba_a1_30_{smoke,fault}.log`. Selection is
  supplied by the research caller, not yet derived from origin status/role/usage;
  no branch artifacts, calibrated independence, Expected mixture or production integration are claimed.
  Doc review: HANDOFF and PLAN record progress and README updates the script map; AGENTS, ENGINE_PLAN and
  TRAINING_PLAN retain the existing contract/gates; FINDINGS has no new real-game measurement and DASHBOARD_PLAN
  has no shipped behaviour to document. The served engine, forecasts and bundles remain unchanged.
- **Per-world advanced visibility:** six player and 15 team metrics derive full-game distributions from retained
  worlds, showing median, 10–90%, middle half, mean, expandable histogram and defined-world counts. Zero
  denominators are undefined; period/legacy worlds are explicitly unavailable. Team possessions/ratings are
  box estimates; simulated on-court ratings and possession-based USG% are not invented. Independent audit:
  `.venv/bin/python -m analysis.advanced_world_audit` passed **32 games, 935 player-game entries, 6,300 metric
  distributions**. Local responsive checks **15/15**, screenshots inspected; laptop/phone offline import
  **24/24 / 23/23**, upgrade **26/26**. Full smoke **108/108**, deliberate fault exited **1** (86/108).
  Hosted laptop/phone imports passed **24/24 / 23/23**. Every **1,971 / 1,939** API record and **60** logos
  reconciled to retained views (phone transform applied); laptop includes **32** world files, phone none.
  iCloud laptop **65,278,420 bytes**, created **18:25:15Z**, SHA-256
  `3f2edb6f2bff7d1707618571194f97ed284966b4b660c164fbac9370243a630f`; phone **13,919,192 bytes**, created
  **18:25:31Z**, SHA-256 `ae7ec89f4546e6ef10827b70b5104d141d2d1c161c1343f8060d921d596a5979`.
  Pages shell **857183b**, cache **66c38a0008086053c0d8**. Manual device imports remain unconfirmed. No nightly,
  production model or simulation changed. Doc review: HANDOFF, PLAN, FINDINGS, DASHBOARD_PLAN and README record
  delivery; AGENTS, ENGINE_PLAN and TRAINING_PLAN need no changes because standing rules, engine and gates did not change.
- **Interim advanced game visibility delivered:** six player ratios of means, OREB/DREB/TOV in player boxes, real full-game
  +/− when available, dated decayed/shrunk offensive-action share and 15 collapsible team metrics per side.
  Team ratings and possessions are box-derived estimates; player rates are ratios of means, not averages of
  per-world rates; the profile is not conventional USG% or a game forecast. **17** current-origin games contain
  **487** player profiles; **516** player pages have one. Older origins do not receive today's profile.
  Local responsive checks passed **24/24**, screenshots inspected; hosted PWA import/offline checks passed
  **24/24 laptop** and **23/23 phone**. A reproduced upgrade failure showed the new service worker could fill
  its new cache with old HTTP-cached assets; its install now fetches assets with `cache: reload`. An old-to-new
  upgrade plus offline checks passed **26/26**. Data-free `gh-pages` **3567ed9**, cache **d820ceb526834e4c703a**.
  iCloud laptop bundle **64,276,315 bytes**, SHA-256
  `e28db4734c5bed1077428d39abd8b5ca9abddb8bb842f550bfdc9eeaf5ea2eb5`; phone **12,917,112 bytes**, SHA-256
  `1cf6520311c399e3845c56448f9721d9c4ceb341140cdf16abe243528979e95a`. Laptop includes 32 world files, phone
  none; all **1,971/1,939** API records match retained views/phone transforms. Each device requires a manual
  import; no real-device import has been verified. The served engine and forecasts remain unchanged.
  A mistaken `views.py --help` rebuilt views before archiving; the previous full laptop bundle was intact and
  archived with both previous bundles at `~/Basketball_archive_ops/archive_20261122T180132Z_27364`. All
  **1,971** prior API records reconciled apart from new profile fields and the build timestamp. The CLI now
  handles `--help` safely; always archive views before rebuilding them.
  Final smoke passed **108/108**; deliberate fault exited **1** (86/108), logs
  `/tmp/musnba_advanced_{smoke,fault}.log`. Doc review: HANDOFF, PLAN, FINDINGS, DASHBOARD_PLAN and README
  record delivery, evidence and next action; AGENTS, ENGINE_PLAN and TRAINING_PLAN need no changes because
  standing rules, engine design and training gates are unchanged.
- **A1 20% completed:** the frozen repaired F4 replay (game `401810327`, 32 worlds per branch, synthetic
  availability and actual participants) passed in both branches. An independent reconstruction of both retained
  captures checked 16,130 and 16,336 fives, 10 and 13 post-foul snapshots, every side's minutes and scores,
  and player-minute replay to a maximum error of 1.78e-15 minutes. Tracing preserved all outputs exactly;
  59 focused branch/availability/accounting tests passed; normal smoke passed 108/108 and deliberate fault exited
  1 with 86/108 checks passing (`/tmp/musnba_a1_rung20_{smoke,fault}.log`). This is wiring evidence, not availability calibration,
  model accuracy or promotion; short-roster NBA foul exceptions remain unsupported. Report:
  `analysis/experiments/20261122_chunk_a_a1_branch_repair.json`; captures remain in
  `data/derived/experiments/20261122_chunk_a_a1_branch_repair/`. Served model, forecasts, bundle and shell unchanged.
  Doc review: HANDOFF, PLAN, FINDINGS and ENGINE_PLAN record the result and next step; AGENTS and TRAINING_PLAN
  retain unchanged rules and gates, while DASHBOARD_PLAN and README require no change for this research-only
  checkpoint because neither shipped behaviour nor commands changed.
- **Owner UX requests delivered locally (22 Nov):** replace the Players fixed 3+/8+ game filter with a season-progress
  minutes-share benchmark; group player-game FG/3P/FT makes, attempts and shooting-percentage distributions.
  Percentages condition on at least one attempt and explicitly show the no-attempt chance. Source and focused tests
  were pushed in `4dce4a3`; the live nightly and iCloud export succeeded, Pages shell `707f6e9` was pushed and
  the hosted shell passed PWA **19/19** with the new bundle. The new bundle also passed local PWA **19/19**, updated pages **18/18**
  at three widths and two themes, with representative screenshots inspected; full smoke passed **108/108**.
  The independent output audits cover **17** games, **340,000** player/team world totals, **4,509** full-game
  shooting histograms and **10,521** period/player/shooting triplets. The iCloud file is delivered, but the
  owner must manually import it on each phone. Earlier focused Python **27/27**, Node
  **2/2**, isolated view browser **19/19** plus **6/6** on a player with no-attempt worlds, and old-bundle isolated
  PWA **18/18** passed; final normal smoke **108/108** passed after schema-aware legacy replay, and deliberate fault
  exited **1** with **86/108** checks passing. Logs: `/tmp/musnba_user_ux_final_smoke.log` and
  `/tmp/musnba_user_ux_fault.log`. Review servers :8767, :8768 and :8769 belong to this session; never touch :8766.
  The guarded A1 replay sources and JSON are included in this partial checkpoint, not a completed rung.
- **Laptop PWA correction (D45):** the actual installed app was already on the updated shell, but every export
  used the stripped phone profile. The laptop bundle now contains the full saved-world views; the phone remains
  stripped. Isolated laptop PWA **28/28**, phone **21/21**, old-to-new installed-shell upgrade **6/6** and
  responsive player pages **12/12** passed. The final hosted shell passed laptop **22/22** and phone **21/21**;
  an archived pre-profile bundle passed **20/20** on the new shell. The old shell visibly displayed its disabled-in-practice Update app
  button because CSS overrode `hidden`; the corrected shell hides it unless an update waits. Both devices need
  their own manual import; the owner laptop window was not manipulated after user input interrupted inspection.
  Deliberate fault exited **1** with **86/108** passing (`/tmp/musnba_d44_delivery_fault.log`).
  Review servers :8767, :8768 and :8769 belong to this session; never touch :8766.
- **Completed UX audit:** `scripts/a1_snapshot_shooting_audit.py` and focused tests
  independently reconcile new full-game shooting histograms against retained player worlds, and check all period
  histograms, means, quantiles and conditional/no-attempt counts; period worlds themselves are not retained.
  It passed on the newly completed snapshots; report `analysis/experiments/20261122_d44_shooting_audit.json`.
  **A1 source freeze:** the isolated `RepairedTrace` and `BranchFoulOutPolicy` are not selected in production.
  The engine hook now accepts a validated per-active-world boolean mask, refreshes only changed worlds and fails
  explicitly for unsupported mismatch features; legacy boolean and no-policy paths remain unchanged.
  Controlled tests first reproduced the prior ambiguous-array error and now pass, including rejection of an omitted
  changed lineup. The combined branch, availability, substitution and accounting suite passed **73/73**.
  Normal smoke passed **108/108** and deliberate fault exited **1** (**86/108** passing), logs
  `/tmp/musnba_a1_mask_{smoke,fault}.log`. The subsequent fixed repaired replay passed as recorded above.
- **Nightly completed:** former shell **2955**, log `/tmp/musnba_d44_nightly.log`. Collection had **63 requests,
  0 failures, 0 new finals**; NBA Stats had no new requests. Inputs rebuilt in **235.2 s**; **7 + 10** games and
  **10,000** season paths over **959** games were saved. Old snapshots and bundle were archived under
  `~/Basketball_archive_ops`; views and the iCloud export completed successfully.
- **Independent A2 research:** rung **10%** completed on the fixed S01 F4 control and fingerprinted prior-only
  S05 roles; protocol/source were pushed before scoring (`3ce6dec`/`aac8c92`). Of **4,346** player-games, **26**
  lacked a role join, **12** had unknown roles and **704** more fell below the minutes threshold, leaving **3,604**
  across **200 games**. Teammate scoring-rate residual covariance was **−1.215** (95% **−1.999 to −0.424**);
  opponent covariance was **+0.462** (95% **−0.410 to +1.283**). This is exploratory observed association,
  not simulated-world covariance or a candidate. The report is
  `analysis/experiments/20261122_a2_residual_dependence_f4.json`; a separate raw-pair reconstruction verified
  all **12** point estimates, two focused tests passed, and the report reproduced byte-for-byte. Normal smoke
  passed **107/107** with one bit-for-bit replay skipped because the running nightly rebuilt newer inputs; deliberate
  fault exited **1** (86/107). Repeat full smoke after the nightly finishes. Rung **20%** freezes talent,
  form and shared-factor hypotheses and no-double-count controls in TRAINING_PLAN before any fitting. F4 was
  already inspected and cannot be called untouched confirmation.
- **A2 earlier-fold feasibility:** S04 control-shot predictions cover **136,578 F1**, **139,660 F2** and
  **87,671 F3** validation shots; stronger source/cache clock/coordinate and prior-role checks passed. The first
  teacher-forced within-game screen saved `analysis/experiments/20261122_a2_shot_residuals_f1_f3.json`;
  an independent ordered-pair audit reproduced all **16** estimates and bootstrap intervals. Its role table covers
  only **200/773 F1**, **200/782 F2** and **195/490 F3** validation games; `_v2.json` makes those exclusions
  explicit and reproduces the first report's estimates exactly. On **595** games / **11,217** player-games, pooled
  shot-residual covariance is **0.001368** (95% **−0.000104 to +0.002874**), inconclusive and unable to identify
  latent talent/form components. Preserve both reports. The cross-game persistence feasibility
  screen and two-way player/game bootstrap are frozen in TRAINING_PLAN. On **595 games / 10,977 player-games**,
  pooled cross-game shot-residual covariance is **−0.000066** (95% **−0.002095 to +0.001786**); F3's star
  cohort has only 29 player-role groups and is insufficient. A separate sparse-matrix reconstruction independently
  reconciled all **15** supported point estimates and 10,000-replicate two-way intervals. Saved report:
  `analysis/experiments/20261122_a2_shot_persistence_f1_f3.json`. This result is inconclusive, cannot identify
  a talent component and does not justify adding a calibrated draw. A separately frozen synthetic-only draw
  mechanics prototype can test mean preservation and deterministic streams without asserting any fitted variance
  or changing the engine; its specification is in TRAINING_PLAN. A2 rung **30%** now has this synthetic-only
  prototype and tests: the analytical probability mean is unchanged, named streams reproduce across player
  order/worker slices, and zero strength consumes no draw. At 10,000 synthetic worlds, mean deviations for
  baseline probabilities 0.5 and 0.9 were **+0.001567 / −0.000420**, respectively; finite samples are not
  claimed to have exact means. Component identification and registered gates remain necessary before any
  candidate is used. Next A2 rung: freeze and test shared pace/shooting factors against actual and simulated
  fold dependence, retaining explicit unsupported results. No F4 or final-test outcomes entered.
- **Pages shell:** isolated worktree `/tmp/musnba-user-ux-pages` pushed reviewed data-free shell `614f3061d9dc69a41bc4`
  as `gh-pages` **707f6e9**. The build completed and both local and hosted new-bundle PWA checks passed **19/19**.
- **Doc review:** `DASHBOARD_PLAN`, `ENGINE_PLAN`, `FINDINGS`, `PLAN`, `README`, `AGENTS` and this handoff record
  D44/D45 behaviour, evidence, device instructions, revised standing rule and next action. `TRAINING_PLAN`
  needs no change: D45 alters delivery, not model training, validation or cutoff gates.
- **A1 source-freeze doc review:** HANDOFF, PLAN, ENGINE_PLAN and README record the opt-in hook, focused checks
  and exact next probe. AGENTS, TRAINING_PLAN, FINDINGS and DASHBOARD_PLAN need no new change: the standing
  rules, frozen evaluation gates, empirical results and served dashboard remain unchanged.
- **Progress:** original A1 **58.0%**, S01–S07 complete; S08–S12/S14 open, S13 historical forecast backfill
  deferred. New independent chunk boards: **A 19.5%** (A1 30%, A2 30%, A3 0%) and **B 0%** (B1/B2/B3 all 0%). Keep
  the original A1 weights intact; new within-chunk weights do not reset or double-count A1.
- **Remaining advanced stats:** simulated on-court +/−, per-world possession-based USG%, individual on-court
  ratings and modelled BPM require additional honest capture/definitions and remain unimplemented; see PLAN §9b.
- **Production:** possession engine **v1.3/D29**, team pathway **v1**. S04's two defence candidates did not pass;
  S05's minute candidates did not meet the primary gate. S06's 200-game candidate improved minute CRPS
  **3.5662→3.5309** but only **66/69** non-inferiority bounds were established, so it was not promoted. Those
  engine diagnostics supplied actual participants, not forecast availability. No new model has been promoted.
- **Remaining model risks:** defensive differences are under-expressed on the fixed 200-game control; a controlled
  probe exposed an unupdated foul-out mask; dated development injury reports are insufficient to calibrate
  availability. Do not present status fallbacks as validated or replay estimates as live forecasts.
- **Last delivery:** origin **22 Nov 2026 ET**, **7 Today + 10 Tomorrow** games × **10,000** worlds and **10,000**
  season paths. The current iCloud laptop bundle was generated **17:40:42Z**, SHA-256
  `6d59a668ba91b9408b67ec1cc89b9ecc5ea61213b639a77a6ededd97fb2a48df`; the phone bundle **17:41:08Z**, SHA-256
  `d1593bfe09dc44f35b6820fa16fa92bab3ac091146774c8984b00f69e89c622a`. Data-free `gh-pages` **c83fa1c**,
  cache `cf2ed4489761b16812cd`. Neither device import is confirmed. This is a dated delivery, not a claim that the
  forecasts are current on a later date. Nightlies export both bundles at the end, not per game.
- **Chunk A:** lineup branches/Expected (A1), form/end-game research (A2), five selected worlds and a 2-D View
  Centre (A3). Chunk B: defence/foul-outs (B1), season pathway (B2), integrated confirmation/rotation map (B3).
  Each chunk ends with a fresh nightly and a useful dashboard improvement if no model passes. View Centre initially
  replays saved simulated events; the same interface is designed for later actual-game playback. Neither exists yet.
- **Baseline:** clean `main` at `e35fbe2`, smoke **108/108**. The A1 10% contract is below, pushed in
  `3f0d67c`; the initial helper is `633fe47`. The first full-game F4 branch probe failed its independent foul-out
  audit in both 32-world branches; these branches are not safe to serve. A1 remains at 10%; no model or delivery
  changed. Start :8767 only for presentation work; never stop :8766.
- **At every completed module/subtask:** update the live ledger and affected docs with results, negatives,
  limitations, tests, production/PWA impact and next action; verify, review, **commit and push before moving on**.
  Update the live log as work proceeds and checkpoint unfinished state at any stop. The detailed protocol is in
  AGENTS §5 and PLAN §6c.
- **Checkpoint orientation:** S07 delivery was **aa21515**; two-chunk planning **2a3155f**; View Centre planning
  **16893d9**. This live-handoff refresh is the subsequent docs-only checkpoint; use `git log -1` for its hash.
  Earlier chronology below is historical evidence, not the current action list. Session-owned review servers are
  listed above; no nightly, backtest or separate history download is running.

## Earlier checkpoints and supporting evidence

Dashboard U1–U22 complete and published.
Dashboard close-out checkpoint **86c2a46**, A1 planning checkpoint **00a0731**; S01 checkpoint **c9d8008**
and S02 checkpoint **93b3e1d** are committed and pushed (S01's exact control source is **c6d5db4**).
The original S03/S05 experiment snapshot is **ab32eda**, committed and pushed before the candidate repair;
the completed S03 diagnosis is **ce9481f**, committed and pushed.
The immutable original S04 F4 screen and corrected S05 historical accounting snapshot is **c0605da**, committed and
pushed before restaging the corrected rim-screen source.
The separate tracking-defence node protocol was frozen and pushed before its test in **5e30f4**.
The original S04 defence evidence and first S05 engine screen, including their exact source hashes, were committed and
pushed in **00a51cc** before the typed tracking-source repair.
The byte-identical typed tracking rebuild and original v2 minute-gate source/report were preserved in pushed
partial checkpoint **890bee3** before correcting the gate's seed-noise definition.
The completed S04 defence checkpoint and corrected minute-gate report are committed and pushed as **38155fc**.
The completed S05 minutes checkpoint and original S06 pilot sources are committed and pushed as **417f3f5**.
S06 partial checkpoints **637a025**, **70709ab**, **bdedeed** and **d77ac5e** are pushed and preserve the initial
corrected replay, frozen fold protocol, exact v2 sources/reports, audited v3 inputs and native screen implementation.
Partial checkpoint **2f05d47** preserves the independently audited outgoing result, incoming coverage and original
foul-out probe; **08cd659** preserves the type-correct probe. Both are pushed.
The first incoming-screen implementation and protocol were pushed as **89f6dc4**, and progress logging as **2229066**,
before any incoming fit.
The audited incoming screen and S06 50% ledger were pushed as **1ecc78a**.
The first selected-timeout engine protocol was frozen before an engine result in **b88840b**.
The model-artifact builder was preserved before fitting in **19b34bc**.
The isolated policy source, model reconstruction and smoke evidence were pushed before real-game wiring in **74e3e71**.
The three-game wiring rung and pre-audit S07 source were pushed as **9a0c178**.
The S07 archive audit and S06 trace source were pushed before world replay as **785a034**.
The audited world replay and S07 label evidence were pushed as **4260521**.
The failed fixed screen, independently audited four-fold availability baselines and dated-cohort gate were preserved
in pushed partial checkpoint **5fd5e00**.
The typed accounting repair, foul-state probe and pre-run sequence builder were pushed as **8c8a50f**.
The first independent sequence reconstruction and its exact auditor source were pushed as **1dcfd6b**.
The frozen fold-screen source and corrected independent reconstruction were pushed as **4c6ba5f** before scoring.
The independently audited S07 60% screen was pushed as **76f7cf5**.
The isolated S06 foul-penalty source was pushed as **bf9cd21** before the probe; S07's spell/starter follow-up
protocol was frozen as **857cc78**.
The audited spell/starter follow-up and unrun S06 direct-state source were pushed as **d7e00aa**.
S06 completion and the then-undelivered S07 source changes were pushed as **45a6df4**; S07 delivery was
subsequently committed and pushed as **aa21515**. Historical source-freeze/progress notes below
describe their state at the time and are superseded by the current delivery summary in § State.
**Owner scope change D40 (22 Nov):** “forget nightly backfill. lets just get nightly for next slate (today and
tomorrow relative to this date). since were probably not at a perfect model yet”. Defer S13 and do not implement or
run a historical forecast replay in this A1 execution. The required pre-origin input rebuild and future-season
simulation remain in scope. Preserve existing
snapshots/archives; D39/§17 remains a future safety contract. S13's original 5% weight and ladder stay unchanged but
receive no progress credit, so a fully delivered remainder can reach 95%, not a falsely claimed 100%.
**Owner stop D41 (22 Nov):** “well stop after this nightly run, anything undone is future work”. The nightly,
verification and PWA delivery are complete; checkpoint and stop without starting another nightly or S08–S14 in this
session. S13 stays deferred. The owner also suggested future incremental, atomic per-game iCloud delivery with a
manifest and safe PWA import (PLAN §9b); it is not implemented, so nightlies still export both bundles at the end.
The owner has lifted the planning-only stop for this overnight A1 execution and delegated in-scope engineering and
product decisions without waiting; source, cutoff, promotion and retention gates are unchanged. **S01–S07 are complete;
A1 overall is 58.0%.** Isolated assignment candidates have event-level diagnostics and wiring only;
no defence candidate has had an engine-accuracy test and no model was promoted. S07 delivered a corrected
forecast/report contract, new iCloud bundle and updated data-free Pages shell.
The fixed S06 200-game candidate backtest failed after at least **40/200** games (last progress **378 s**) because
world **563**, side **0**, had fewer than five non-disqualified available players after a foul-out; no aggregate
outputs were written. The explicit error is a robustness failure, not a paired accuracy result or promotion.
Frozen source/log fingerprints are in `analysis/experiments/20261122_a1_s06_candidate_fixed200_failure.json`.
A same-stream ten-game replay of ordered indices 41–50 exited 1 after four completions, identifying game
**401810472** (20 Jan 2026), home team **7**, with **8** actual-participant inputs. Former shell **2150**, log
`/tmp/musnba_a1_s06_failure_probe.log`. The prior 200-game process also exited 1. An error-context-only policy
revision (no lineup/draw change) reproduced the failure in former shell **2198**, log
`/tmp/musnba_a1_s06_foulout_state_probe.log`: **4.4 seconds left in Q4**, with **four of eight** actual-participant
inputs at six fouls. The state and source fingerprints are in
`analysis/experiments/20261122_a1_s06_foulout_state_probe.json`. The separate opt-in foul-penalty candidate
reproduced the previous three games to `1e-12` and independently reconciled **3,000** worlds / **1,472,554**
fives. The formerly failing game then simulated **1,000** worlds and its capture independently reconciled
**473,544** fives, including one made technical at **4.4 s** in world 563. However, the one-game backtest exited
**1** on non-finite single-game summary serialization; the saved-world probe is not a successful complete
backtest. Reports `analysis/experiments/20261122_a1_s06_penalty_three_{output,world}_accounting.json` and
`analysis/experiments/20261122_a1_s06_penalty_probe_world_accounting.json`, logs
`/tmp/musnba_a1_s06_penalty_{three,probe}.log`. The opt-in flow capture then reproduced all **321** original
game values and **1,408** player values on those three games, independently checked **1,280** recorded
player-period values and **96** simulated team/component sums, and completed in **63 s**; reports
`analysis/experiments/20261122_a1_s06_penalty_flow_wiring_{output,flow}_accounting.json`. The flow auditor's new
optional `--reference` defaults to the prior control; existing callers remain compatible. The sequential
fixed **200-game/1,000-world** flow-instrumented screen completed in **2,004 s**, former shell **2284**, log
`/tmp/musnba_a1_s06_penalty_flow_fixed200.log`; command:
`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -u scripts/backtest.py --config models/v1.2d.json
--fold F4 --game-ids data/derived/experiments/20261122_a1_s03_f4_game_ids.json --worlds 1000 --jobs 4 --threads 8
--rotation targets --pool 0 --models folds/v1.2d_F4_all --substitution-candidate
analysis/experiments/20261122_a1_s06_engine_models_F4.json --substitution-foul-penalty --flow-diagnostics --name
a1_s06_penalty_flow_fixed200`. Its independent no-reference flow accounting passed on **200 games / 4,346**
player-games, **86,920** recorded player-period values, **6,384** team/quarter/component sums, **400** lineup
tick sets and **800** clock values, maximum difference **2.84e-14**; one team lacked a full scored-player roster.
Report `analysis/experiments/20261122_a1_s06_penalty_flow_fixed200_accounting.json`, former shell **2426**.
The fixed score, independent pooled accounting, preliminary gate and retrospective Q4 subgroup comparison finished
in former shell **2429**: pooled minute CRPS **3.5662→3.5309** (change **−0.03529**, 95% **[−0.04462,
−0.02609]**, seed-noise floor **0.02634**) passes the uncorrected primary screen, while only **66/69**
non-inferiority bounds are established. Margin, Q2-margin and Q3-total coverage remain inconclusive or worse
against their registered bounds. **15** pooled metrics and **10/10** pooled bias/coverage bounds independently
reconcile. Reports `analysis/experiments/20261122_a1_s06_penalty_fixed200_{compare,pooled_accounting,gate,retrospective}.json`.
Retrospective Q4 groups use actual historical states but unconditional simulated player-quarter means; they do not
establish within-world response. The three-game direct-state preflight completed in **210 s** and exactly
reproduced **321** game and **1,408** player values, former shell **2425**, log
`/tmp/musnba_a1_s06_state_capture_three.log`, report `analysis/experiments/20261122_a1_s06_state_capture_three.json`.
The fixed full replay completed successfully in former shell **2450**, log
`/tmp/musnba_a1_s06_state_capture_fixed200.log`; command:
`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -u scripts/a1_substitution_response_capture.py
20261122T103244Z_a1_s06_penalty_flow_fixed200 --jobs 4 --output
analysis/experiments/20261122_a1_s06_state_capture_fixed200.json --rows-output
data/derived/experiments/20261122_a1_s06_state_capture_fixed200.parquet`. Do not run another engine backtest
concurrently. It finished **200/200 games in 3,507 s**, capturing **60,659** player-state cells and reproducing
**21,400** game and **95,612** player values. The independent audit completed in former shell **2522**, log
`/tmp/musnba_a1_s06_state_capture_fixed200_audit.log`; it reconciled **800** game/state totals and compared
**191** common historical games. Its completed command was
`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/a1_substitution_response_audit.py
analysis/experiments/20261122_a1_s06_state_capture_fixed200.json
data/derived/experiments/20261122_a1_s06_state_capture_fixed200.parquet --output
analysis/experiments/20261122_a1_s06_state_capture_fixed200_accounting.json`. The paired minute screen and
audited descriptive state comparison earn S06 80%. **S06 90% decision:** retain v1.3/D29, because only **66/69**
frozen non-inferiority bounds were established despite the uncorrected pooled-minute improvement. Selected-timeout
state comparisons remain descriptive with actual participants; wider-fold/adjusted confirmation and a final-test
score were not run. See FINDINGS for the rates, limitations and runtimes. The 100% rung includes the completed
smoke/fault checks and this evidence/docs checkpoint.
TRAINING_PLAN froze a retrospective Q4-start margin/foul subgroup comparison before candidate scoring; the
comparison and focused missing/inconsistent-foul tests are complete. Saved Q4 player means average over simulated
states, so they cannot prove the policy reacts correctly within a simulated game. The separately precommitted
`scripts/a1_substitution_response_capture.py` measures selected-timeout state response without changing the serving
policy; focused synthetic tests, Pylance diagnostics, the three-game preflight, full replay and independent audit
passed. Do not claim a direct same-opportunity target-table control or a causal effect.
The working `scripts/a1_flow_audit.py --no-reference` can independently check the full candidate's flow accounting
without pretending a second full same-policy backtest exists. On the existing three-game wiring capture it matched
all **1,280** recorded-player-period checks and **96** team/component checks, with reproduction fields explicitly
null; its existing reference mode and caller signature remain compatible. The subsequent direct-state replay
established exact same-policy reproduction and the audit change is committed.
S07's first no-report/starter baseline protocol is frozen in TRAINING_PLAN §8.2 before scoring. A prior-position
coverage setup initially failed on timestamp/string merge types; after converting stored dates to ISO it found
**55/7,317** missing prior positions across **55/400** F4 team-games. This is coverage, not a starter score.
`scripts/a1_availability_baseline.py` and focused tests are prepared. Its D29 selector
uses stable player-ID tie order because the original live roster ordering is unavailable; results are a proxy.
The frozen baseline source is pushed as **6599fa6**. Its F4 run finished and was independently audited:
**7,317** candidates, **5,208** known play labels and **399/400** supported starter team-games. The attached
shell **2131** exited 0; log `/tmp/musnba_a1_s07_baseline_F4.log`; command:
`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -u scripts/a1_availability_baseline.py --fold F4
--output analysis/experiments/20261122_a1_s07_baseline_F4.json --rows-output
data/derived/experiments/20261122_a1_s07_baseline_F4.parquet --teams-output
data/derived/experiments/20261122_a1_s07_baseline_F4_teams.parquet`. F1–F3 ran sequentially under the same options
in former shell **2147**, log `/tmp/musnba_a1_s07_baseline_F1_F3.log`; F1/F2 scored **200/200** in
**68.2/106.6 s**, F3 scored **195/200** in **91.3 s**, with five games lacking prior rosters. All four folds have
passed independent accounting. The normal/fault checkpoint queue completed as former attached shell **2160**, wrapper
PID **12638**, with logs `/tmp/musnba_a1_s06_s07_partial_{unittest,smoke,fault}.log`; **15** focused unittest cases
and normal smoke **102/102** passed. The deliberate-fault run exited non-zero as required with **80/102** checks
passing, and the checking wrapper exited 0. An initial pytest command failed because pytest is not installed;
the project's existing unittest runner was used instead, with no dependency change.

**Completed S05 evidence:** the 200-game flow and its independent accounting are complete; the comparison and
two S04 hypotheses are recorded below and in FINDINGS/TRAINING_PLAN. Both corrected S05 historical screen wrappers
have exited successfully; the full four-fold audit passed with **21** input and **16** output hashes, reproducing all
**28,530** control/NBA-only candidates to `1e-12`. F3 scored 195/200 games due to five unavailable prior rosters.
Logs: `/tmp/musnba_a1_s05_unconditional_corrected.log`, `/tmp/musnba_a1_s05_no_report_corrected.log`,
`/tmp/musnba_a1_s05_minutes_accounting_corrected.log`. The normal
checkpoint smoke passed **102/102** (`/tmp/musnba_a1_s03_partial_smoke.log`); deliberate fault exited 1 with
**80/102** checks passing, as required (`/tmp/musnba_a1_s03_partial_fault.log`; checking wrapper exited 0).
The original committed `scripts/a1_minutes_candidate.py` SHA-256 is
`3bd085968d6f1a9e08b1bf5f58aaa4af75f1d81d1261e858b291d5c069d416dc`, working repaired SHA-256
`57c5efcdea56db9647830d2ba4a4509440d82ad6cb637986b5a1943d02af10cc`. The original commit's test intentionally
marks the pre-repair zero-target regression expected-failure; repaired test passes without that marker. All seven
original source hashes in the eight historical screen reports match that committed index. No `data/` or secrets
belong in checkpoints.

**S04 first F4 wiring and required repair:** `scripts/a1_rim_calibration.py` and `scripts/a1_rim_screen.py` are
isolated; neither changes the served engine. The run log `/tmp/musnba_a1_s04_rim_F4.log` and
`analysis/experiments/20261122_a1_s04_rim_F4.json` reused the independently audited guarded F4 shot model, scoring
**135,680** shots. It reproduced baseline log loss **0.7295266**; the paired full-fold loss difference was
**−0.0000312** (95% **−0.0000556 to −0.0000063**) and the fixed-200 difference **−0.0000382**
(**−0.0000836 to +0.0000058**). **The report's `training_tail_from` is wrong (1970)**: pandas dates are
microsecond-resolution but were interpreted as nanoseconds when formatting. An independent mask reconstruction
confirms **72,379** training-tail rows actually span **2025-11-02–2025-12-31**; the fitting mask itself is correct.
The original source/report was committed unchanged in **c0605da** before the label was corrected and rerun; no
promotion or all-fold conclusion follows from this pilot. The checkpoint smokes both completed, as recorded below.
**Update 06:26 UK:** the corrected working script fixes the
date-format label and its four focused tests pass. Corrected F4 reran as
`analysis/experiments/20261122_a1_s04_rim_F4_v2.json` and
`data/derived/experiments/20261122_a1_s04_rim_F4_v2.parquet`; all **135,680** original/corrected prediction rows,
calibration parameters and population metrics independently match exactly; the true tail begins 2 Nov 2025.
F1–F3 ran sequentially as former wrapper PID
**83009** (first child **83010**), log `/tmp/musnba_a1_s04_rim_f1_f3_v2.log`, using:
`for fold in F1 F2 F3; do OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -u -m scripts.a1_rim_screen
--fold "$fold" --threads 6 --output "analysis/experiments/20261122_a1_s04_rim_${fold}_v2.json" --rows-output
"data/derived/experiments/20261122_a1_s04_rim_${fold}_v2.parquet" --model-output
"data/models/folds/a1_s04_rim_${fold}_v2/shot_result.txt" || exit; done`. Reports record those source hashes.
**Update 06:49 UK:** all four corrected rim folds have completed. F1/F2/F3 scored **136,578 / 139,660 / 87,671**
shots in **44.0 / 45.5 / 50.2 s**; F4 scored **135,680**. Across full held-out folds, candidate-minus-control
shot losses were **−0.00000222 / +0.00001481 / +0.00001113 / −0.00003117**; these are provisional until the
independently verified gate, and are not an engine or promotion result. Their earlier training
tail slopes were **+0.0718 / −2.1686 / −0.8422 / +1.1315**. The independent audit's first attempt caught its own
float32-versus-float64 reconstruction error (F1 mean difference `−9.23e-11`); applying the calibration's verified
float64 conversion reproduces the mean exactly. A second attempt exposed that the reused F4 metadata does not carry
`rows_train`; the auditor now checks that field when present and verifies all other cutoff/model/prediction data.
The corrected independent audit passed as `analysis/experiments/20261122_a1_s04_rim_accounting.json`, covering
**499,589** shots, **80** supported metric populations and all source/output hashes; original and corrected F4
rows match exactly. Reproduce with:
`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -u -m scripts.a1_rim_audit --output
<new-report>`. A strictly same-input seed-8 training-noise experiment
runs one fold at a time (former wrapper PID **83928**, attached shell **1502**, log
`/tmp/musnba_a1_s04_rim_noise.log`); F1–F4 completed in **9.9/11.8/17.1/18.9 s**. Its exact command is the
`scripts.a1_rim_noise` invocation recorded per report; it never scores the protected final season. The independent
noise/gate audit passed as `analysis/experiments/20261122_a1_s04_rim_node_gate.json`: the candidate's four-fold mean
relative change is **−0.000259%**, versus the same-input seed-pair RMS floor **0.013718%**, pooled game-cluster
z **−0.283**, so the frozen shot-node gate is **neutral** and this family is not retained for an engine test.
This rejects this specific expression calibration, not player-based defence generally.
The checkpoint normal smoke passed **102/102** (`/tmp/musnba_a1_s04_partial_smoke.log`); deliberate fault exited 1
with **80/102**, as required (`/tmp/musnba_a1_s04_partial_fault.log`; wrapper exited 0). The original erroneous
F4 source and report are preserved in pushed commit **c0605da**; the corrected source is committed in **38155fc**.
Those processes had loaded the engine before the latest minute-candidate wiring. A fresh single-threaded normal
smoke on current code passed **102/102**, former wrapper PID **87718**, session **1591**, log
`/tmp/musnba_a1_s04_current_smoke.log`. Its deliberate-fault counterpart exited 1 with **80/102** checks
passing, as required (former wrapper PID **88523**, session **1613**, log `/tmp/musnba_a1_s04_current_fault.log`).

The committed `scripts/backtest.py` has opt-in `--minutes-history nba_only` and `--strict-minute-targets`
switches, with separate input fingerprints; `Game` defaults to its unchanged legacy allocator. The strict switch
also rejects an availability pattern with fewer than five rather than filling it with unavailable players. These
are isolated wiring changes, not a promotion; the candidate's history is still learned with D29.
The **69** focused A1 tests pass. A sequential three-game control/NBA-only/strict/combined wiring wrapper completed,
former PID **84110**, attached shell **1512**, log `/tmp/musnba_a1_s05_engine_wiring.log`; the first control completed
**3/3 games in 57 s** and matches `20261122T015651Z_a1_s01_repro` exactly in all **93 game** and **22 player**
columns. NBA-only, strict and combined each also completed three-game wiring sequentially. Independent accounting
passed in shell **1541**; see `analysis/experiments/*_a1_s05_*_wiring_accounting.json`. Their invocation uses `scripts/backtest.py --config models/v1.2d.json --fold F4 --game-ids
analysis/experiments/20261122_a1_reproduction_games.json --worlds 1000 --jobs 1 --threads 8 --rotation targets --pool 0
--models folds/v1.2d_F4_all`, with separate candidate flags and names. Check the default control against saved
`20261122T015651Z_a1_s01_repro`. The NBA-only fixed 200-game, 1,000-world F4 candidate ran as former wrapper PID
**85267**, attached shell **1538**, log `/tmp/musnba_a1_s05_nba_only_fixed200.log`; command as above but
`--game-ids data/derived/experiments/20261122_a1_s03_f4_game_ids.json --jobs 4 --minutes-history nba_only --name
a1_s05_nba_only_fixed200`. It completed **200/200 in 1,729 s** as
`20261122T070852Z_a1_s05_nba_only_fixed200`; accounting and comparison completed below. The previous
same-size control took **1,567 s**. Strict-runtime ran as former wrapper PID **88450**, child **90891**, attached
session **1610**, log `/tmp/musnba_a1_s05_strict_fixed200.log`; its queue waited for NBA-only Python PID **85268**
to exit and verified the successful marker, then started the same command with `--strict-minute-targets --name
a1_s05_strict_fixed200` instead of `--minutes-history nba_only`.
It finished **200/200 in 1,731 s** including startup, as
`20261122T073749Z_a1_s05_strict_fixed200`; games 181–200 took **164 s** (about **7.3 games/minute**).
The independent audit queue completed as former PID **93361**, attached session **1707**,
log `/tmp/musnba_a1_s05_strict_audit_queue.log`. After verifying the success marker it ran
`scripts.a1_output_audit --pin-current-inputs`, `scripts.a1_compare` against
`20261122T022323Z_a1_s01_control` on the fixed game IDs, and the corrected `scripts.a1_minutes_gate` sequentially;
outputs are `analysis/experiments/20261122_a1_s05_strict_fixed200_{accounting,comparison,gate}.json`.
A second queue completed as former PID **94380**, session **1728**, log
`/tmp/musnba_a1_s05_strict_pooled_queue.log`; `scripts.a1_pooled_audit` wrote
`analysis/experiments/20261122_a1_s05_strict_fixed200_bootstrap_accounting.json`.
S05's normal smoke passed **102/102**, and its deliberate-fault smoke exited **1** with **80/102** passing as
required. The sequential queue completed successfully as former PID **94558**, session **1732**, queue log
`/tmp/musnba_a1_s05_checkpoint_queue.log`, outputs `/tmp/musnba_a1_s05_checkpoint_{smoke,fault}.log`.
The S06 research checkpoint's sequential smoke/fault queue completed as former attached session **1899**, wrapper
PID **99548**, queue log `/tmp/musnba_a1_s06_partial_queue.log`, outputs
`/tmp/musnba_a1_s06_partial_{smoke,fault}.log`: normal **102/102**, deliberate-fault exit **1** with **80/102**
passing, as required. These research changes do not alter serving or the PWA.
Strict minus control pooled MIN CRPS is **+0.000268 minutes** (95% **−0.000111 to +0.000653**) against the
**0.02634** seed-noise floor; **69/69** tier/game and **10/10** pooled bias/coverage bounds are established.
The independent pooled reconstruction checked **15** metrics to **2.6e-15**; raw accounting found no quarter/3PM
mismatches, with one explicitly incomplete player/team output. All **38** shared data/model/config and four candidate
source hashes match. The known-participant panel is not an availability forecast. Neither candidate establishes the
required pooled primary win, so **retain D29 control for S06**; strict target legality remains an isolated research
candidate, not a promoted model.
The NBA-only comparison and independent accounting are
`analysis/experiments/20261122_a1_s05_nba_only_fixed200_{comparison,accounting}.json`. They cover **200** games,
**4,346** player-games, **1,600** raw quarter-score checks and **4,346** 3PM actuals, with zero mismatches;
one of 4,347 simulated player-games lacks an output, so its team 3PM sum remains explicitly incomplete.
Pooled minute CRPS changed **−0.00416** minutes (95% game-cluster interval **−0.02699 to +0.01913**) against the
registered **0.02634**-minute seed-noise floor: the primary screen does not establish a win. Stars (**284** player-games)
changed **−0.14916** (95% **−0.27174 to −0.03359**), starters (**1,578**) **−0.02295**
(**−0.04428 to −0.00263**), and bench (**2,472**) **+0.02440** (**−0.00625 to +0.05688**).
This is actual-participant diagnosis, not an availability forecast; a subgroup gain cannot override the frozen
pooled primary gate. **59/69** listed player-tier/game non-inferiority intervals sit inside their frozen bounds;
six star bias/coverage and four game/quarter coverage intervals are not established; **10/10** additional pooled
player bias/coverage intervals are inside bounds.
The original and v2 `scripts/a1_minutes_gate.py` reports used the interval half-width **0.01653**, not the registered
maximum absolute endpoint **0.02634** from the seed interval **[−0.00671, +0.02634]**. Their NBA-only primary
rejection is unchanged because its interval also crosses zero and its improvement is smaller than either floor.
The original gate source/report are preserved in **00a51cc**; the portable-path v2 source/report are in **890bee3**.
The working checker now reuses the preregistered manifest's endpoint calculation, has an asymmetric-interval
regression test and writes the corrected `analysis/experiments/20261122_a1_s05_nba_only_fixed200_gate_v3.json`:
the pooled screen is false, with **59/69** non-inferiority bounds established, unchanged from v2. An independent
direct-resampling reconstruction also matched all **15** pooled player-stat point/interval results to within
`1.5e-15` and confirmed the separate **10/10** pooled bias/coverage bounds. The reproducible independent auditor is
`scripts/a1_pooled_audit.py`, with NBA-only evidence
`analysis/experiments/20261122_a1_s05_nba_only_fixed200_bootstrap_accounting_v2.json`. Its first uncommitted
test run produced the same accounting but its source had a Pylance call-arity diagnostic; that transient output
was discarded, the source corrected and v2 rerun. These are uncorrected preliminary screens, not promotion
decisions. All four candidate source hashes match the backtest log.
The NBA-only audit also matches S01 on all **38** shared data/model/config hashes (17 model files); six shared
source files changed for isolated A1 work. The tested metadata uses the legacy feature/matchup policies, the
backtest's CRPS and PIT function ASTs are unchanged, and the old/new legacy matchup outputs match bit-for-bit on
1,000 synthetic lineups, including missing profiles. The new default engine reproduces all saved columns on three
wiring games. A new full 200-game default replay has not been run.

**S06 30%:** the S05 control decision is recorded, so sequence reconstruction started
while its checkpoint smoke ran. The S05 checkpoint preserves the original `scripts/a1_substitutions.py` and
`tests/test_a1_substitutions.py`; the initial corrected versions are in **637a025**. On game `401810498` the replay checks
**1,008** event-side scoreboards and gives margin **−3** immediately before substitution sequence 709, separating
the same-clock later reversal. Feed sequence numbers are not globally chronological in that game; replay orders
by period, descending clock, then sequence *within* a clock. In a separate raw 2025–26 preflight, two duplicate
game/sequence numbers occur at different clocks and are not by themselves ambiguous. A fixed F4 **200-game** pilot
completed as former attached session **1820**, wrapper PID **96928**, child **96929**, log
`/tmp/musnba_a1_s06_sequence_pilot.log`; it wrote
`analysis/experiments/20261122_a1_s06_sequence_pilot.json` and ignored
`data/derived/experiments/20261122_a1_s06_sequence_pilot.parquet`: **191** games retained, **9** quarantined.
An independent raw-event join found **22,224/22,577** supposed jump balls were not type 615, mainly jump shots:
`rotations.window_kind` matches the substring `jump`. The original pilot source, test and report are preserved in the S05 checkpoint;
the source SHA-256 `6605c0b7f737adc0a8a0b0fe8514d32ffb11cb46943efeb967acfa0381dc00d9` matches its report.
The working candidate now restricts jump-ball labels to actual jump-ball events and adds a regression test. The v2
pilot completed in **13.6 s** as former attached session **1834**, wrapper PID **97249**, child **97250**, log
`/tmp/musnba_a1_s06_sequence_pilot_v2.log`; it wrote `analysis/experiments/20261122_a1_s06_sequence_pilot_v2.json`
and the corresponding ignored derived parquet. It retains **191/200** games, **23,160** windows and **11,277**
substitutions, quarantining the same nine games. The independent audit completed with **46,320** scoreboard and
lineup checks, **502,773** foul values and all **11,277** raw substitutions reconciled. The first audit source
(SHA-256 `95acd7bcf9920794310a779bed62533af6150bdf9dd74881250af7bd43e6ee0b`) had a shadowed progress
counter, not an accounting failure; its original source is preserved in the S05 checkpoint and its v2 report in
**637a025**. The corrected audit v3 completed with
identical counts in **1.4 s** of window processing (session **1855**, log
`/tmp/musnba_a1_s06_sequence_audit_v3.log`, report `analysis/experiments/20261122_a1_s06_sequence_audit_v3.json`,
working-source SHA-256 `55eca6f6ffb73a9782424b26313a8e373c9bc07b2b1fdd08032dfd35bdc5fd9d`). Keep the original
replay/audit sources accessible in Git history. Of **729** no-sub timeout-labelled windows, **129**
share a clock with a substitution and need conservative exclusion or separate sequencing; **600** unique full-timeout
clocks have no substitution at that clock; the larger count is not proof of no substitution during the timeout.
Of nine quarantines, five are late-clock substitutions whose entrants are not eligible in the observed
participant set, one substitution lacks a shared roster team, two have unsupported period starters, and one is an
end-game event incorrectly marked scoring with zero points. Keep them quarantined pending defensible source repair.
The pilot does not claim that every observed stoppage is a legal opportunity; roster membership uses actual
participants and period starters are inferred. The conservative full-timeout extractor
`scripts/a1_substitution_opportunities.py` retains **1,816/1,972** timeout windows across all 191 games:
**1,216** with and **600** without any substitution; **148** other-same-clock-substitution and **8** multiple-timeout
windows are excluded. There are **1,691** changed and **1,941** unchanged team decisions. Its original source is
preserved in the S05 checkpoint (the report in **637a025**), SHA-256
`71d1fa3f3492b8c0803ae82a7e3e34b764f092287c55594527e0109b457051d9`; working v2 adds an output
fingerprint. The v1/v2 parquet bytes and population counts match exactly. An independent raw-event group-by and
every-field comparison passed (`/tmp/musnba_a1_s06_timeout_independent.log`). These are selected timeout decisions,
not an exhaustive or unbiased set of legal opportunities.

The preregistered exploratory state audit `scripts/a1_substitution_states.py` completed as
`analysis/experiments/20261122_a1_s06_timeout_states.json`, with **39,380** player decisions across 191 games; the
independent check reconciles **2,790** outgoing/incoming substitutions, **18,160** on-court decisions and **4,160**
overlapping S05 pre-game-tier records, and reproduces a direct-resampling confidence interval
(`/tmp/musnba_a1_s06_states_independent.log`). Among selected timeouts, starters with defined foul trouble left
**27.2%** of 202 observed decisions (95% game-cluster interval **21.3–34.1%**), versus **15.4%** of 8,651 decisions
without it (**14.4–16.4%**). These are descriptive, confounded and outcome-selected, not calibrated hazards or
causal effects. The fixed bins and 100-player-game/30-game support floor are in TRAINING_PLAN §8.2. The S06 10% and
20% evidence is complete. The state dataset still uses actual participants and is not suitable as a prospective
eligible pool.

The separate cutoff-safe feasibility dataset `scripts/a1_substitution_dataset.py` uses only S05's audited prior-box
cohort, strictly earlier profile dates and its all-active 1,000-draw mean target **proxy**, plus state already observed
at a reconciled timeout. It has **18,160** observed-five out rows and **48,385** possible in rows; all **45,604**
incoming non-entry labels remain unknown, and **82** candidate rows are known ineligible through prior six fouls or
ejection. **9** observed entrants were outside the pre-window candidate set, **70** out and **63** in rows lack a
prior target, and **415** overtime rows deliberately have no regulation-target deficit. This is not a validated
physical-availability model or an unbiased hazard sample. `scripts/a1_substitution_dataset_audit.py` independently
reconciled all **66,545** rows and **2,790** raw substitutions, including cutoff dates, candidate pools, labels,
fouls/ejections and target deficits; its log is `/tmp/musnba_a1_s06_prior_targets_audit.log`, report
`analysis/experiments/20261122_a1_s06_prior_target_candidates_audit.json`. Future-participant injection, same-day
targets, earlier ejection and tampered-deficit regression tests pass. Reproduce the dataset with
`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -u -m scripts.a1_substitution_dataset
analysis/experiments/20261122_a1_s06_timeout_opportunities_v2.json
analysis/experiments/20261122_a1_s05_minutes_screen_accounting_corrected.json --windows
data/derived/experiments/20261122_a1_s06_timeout_opportunities_v2.parquet --targets
data/derived/experiments/20261122_a1_s05_unconditional_F4_corrected.parquet --output <new-report> --rows-output
<new-parquet>`. Never relabel unknown incoming availability as a verified negative.

The first preregistered F1 fold-data attempt ended with **no output**: its replay processed **200** games in
**12.7 s**, and an independent audit reconciled **21,036** windows, but candidate construction correctly rejected a
retained game's ejection with no athlete ID. The raw text names a coach, but the actor's type is not reliably
structured; the safe retry explicitly quarantines such games rather than guessing. Another source's `No Foul`
without an actor was already replay-quarantined. Failed attempt and source hash are recorded in
`analysis/experiments/20261122_a1_s06_fold_F1_failed.json`, log `/tmp/musnba_a1_s06_fold_F1.log`.
The fixed retry completed (`/tmp/musnba_a1_s06_fold_F1_retry.log`): **13** games were replay-quarantined and
**1** further game excluded for the unidentified ejection. The remaining **186 games**, **1,768** selected
timeouts and **65,864** player rows independently reconcile, including **2,673** outgoing substitutions;
**45,516** incoming non-entries remain unknown and **5** entrants were outside the pre-window pool. Report
`analysis/experiments/20261122_a1_s06_fold_F1.json`; candidate/window rows are under `data/derived/experiments/`
with that stem. Its builder source SHA-256 is
`9017997d8c744eb77c0dff9dfbace3b775fe025375556b79d90666a239fb9aa8`, preserved in **637a025**.
F2 and F3 then failed safely before candidate outputs: the F2 feed leaves an ejected player in the observed five
at a later timeout, and the F3 feed calls an `Excess Timeout Technical` a timeout under substring matching.
`analysis/experiments/20261122_a1_s06_fold_F2_F3_failed.json` records both; v2 source changes in **70709ab**
quarantine the former and correct the latter at replay. Focused tests and Pylance diagnostics pass. The F2/F3 v2
retries independently reconcile **181/200** and **178/200** games with **17,370** and **17,270** outgoing rows,
respectively. F2 excludes **2** ejected-on-court conflicts; F3 has **5** games without prior rosters and **1**
unidentified ejection. Reports and ignored rows use the stems `20261122_a1_s06_fold_F2_v2` and
`20261122_a1_s06_fold_F3_v2`; the working builder SHA-256 is
`5a8c724c2eff65d29de295a23baf3e7070d98fdf25856a9ba2fb815d28152654`, preserved in **70709ab**.
F1/F4 v2 independently reconcile **186/200** and **191/200** games;
their **65,864** and **66,545** candidate rows match every field of the earlier datasets exactly.

The seed v2 attempt stopped before writing targets because its loader omitted `game_id` required by the existing NBA
team-accounting helper; replay had independently reconciled **21,896** windows. Failure and hashes are in
`analysis/experiments/20261122_a1_s06_fold_seed_v2_failed.json`, log `/tmp/musnba_a1_s06_fold_seed_v2.log`. Its
exact builder and replay Git blobs are **24bcc4b957be13cad6e9f4d2e91ca19e3311198e** and
**2353747d70f5eab63fa8305666b3619678b20c98**, reachable in **70709ab** with the four v2 reports. The v3 retry
added the missing column and passed a real-data target pilot, full seed build and independent cutoff audit. No out
model has been fitted yet.

The seed loader repair passed a real two-game pilot (**68** targets; maximum team-mean error **0.0000014**
minutes; all profile/roster dates earlier). All four v3 validation datasets have since completed with a shared
builder SHA-256 `50f674b647b7706e9d24923542d025753b869b4dcd5552ccc9c4c58a2a1e5aa1`: F1/F2/F3/F4 contain
**17,680 / 17,370 / 17,270 / 18,160** outgoing rows. The seed v3 build completed as former attached session **1978**,
wrapper PID **2637**, child **2638**, command
`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -u -m scripts.a1_substitution_fold_data --population seed
> /tmp/musnba_a1_s06_fold_seed_v3.log 2>&1`. Its target stage processed **200/200** games in **25.8 s** after replay;
**16** games failed replay, leaving **184** games and **18,320** outgoing rows, independently reconciled against
**2,600** raw substitutions. The v3 builder's Git blob is **6c74f2500d6dad93fa758e0964712eb0c8493818**.
The independent seed-target and cutoff-fit audit passes
(`analysis/experiments/20261122_a1_s06_seed_v3_audit.json`, log `/tmp/musnba_a1_s06_seed_v3_audit.log`):
**6,354** prior-box targets and profiles reconcile across **184** games; the maximum team target-sum error is
**0.0000931 minutes**. Perturbing **98,484** post-fit-cutoff player-games does not alter the dated ramp/spread;
**71** target rows in two sampled games reproduce exactly. Source/fit and all four fold inputs are still research-only.
The first out-screen attempt failed before any fit because scikit-learn is absent; the retry uses the existing native
LightGBM API with the same frozen objective and settings. The error and source fingerprint are in
`analysis/experiments/20261122_a1_s06_out_screen_wrapper_failed.json`.

**S06 40%:** the frozen outgoing screen scored **70,480** decisions in **736** games. Pooled Brier improved from
**0.127265** to **0.105985** (paired difference **−0.021280**, game-cluster 95% **−0.022412 to −0.020141**);
all four fold point differences favour the candidate. F1/F2/F3/F4 contain **17,680 / 17,370 / 17,270 / 18,160**
decisions and improved by **−0.022331 / −0.021422 / −0.020079 / −0.021262** respectively. F3 used the baseline's
overall fallback for four rows; other folds had none. The first fitting run took **2.4 s** for four folds,
`/tmp/musnba_a1_s06_out_screen_v2.log`. Independent re-fitting reproduced every prediction exactly and the direct
game bootstrap across **20** fold/tier cells and pooled results to **2.1e-16**; see
`analysis/experiments/20261122_a1_s06_out_screen{,_audit}.json` and
`data/derived/experiments/20261122_a1_s06_out_screen.parquet`. This is a promising selected-timeout node diagnostic,
not an all-opportunity hazard, known-availability forecast, engine test or promotion. Next design and freeze an
incoming/joint-selection evaluation that does not convert unconfirmed non-entries to known eligible negatives.
An independent controlled engine probe then found a tightly coupled pre-existing defect: the six-foul mask is
initialised but never updated, so a player injected with six personal fouls stays in the next segment even with an
available bench replacement (`analysis/experiments/20261122_a1_s06_foul_out_probe.json`). This is one controlled
world, not a population frequency. Its first source has type diagnostics; a type-correct v2 produces the same result
(`analysis/experiments/20261122_a1_s06_foul_out_probe_v2.json`), with the original preserved in **2f05d47**.
S06 must correct it in an isolated candidate and test foul-outs, insufficient rosters and default-path reproduction;
do not silently change the served model.

Incoming coverage and independent accounting are complete: **182,984** F1–F4 candidates, **10,711** observed in-pool
entries, **172,273** unknown non-entries, **242** known disqualifications and **22** entries outside the pool.
Prior positions are known for **179,478** candidates and **10,672** entries; **2,845** of **6,507** entry-bearing
team-timeouts have multiple entries. `analysis/experiments/20261122_a1_s06_in_coverage{,_audit}.json` records
all five populations and hashes. TRAINING_PLAN §8.2 now freezes a positive-versus-unlabelled-mixture incoming
ranking screen and its eligibility/positional limits before fitting. The pre-fit source SHA-256 is
`b63106d0866844dd1b1b5fa9006e84ff65e1a7c326f06120d35f3309e0634647`.
The checkpoint normal smoke passed **102/102** (`/tmp/musnba_a1_s06_40_smoke_default.log`); deliberate fault
exited **1**, **80/102** passing (`/tmp/musnba_a1_s06_40_fault_default.log`). Two earlier one-thread smoke
attempts were stopped without results after about four minutes; the completed runs use normal engine threading.

**S06 50%:** the frozen positive-versus-unlabelled incoming ranker scored **84,344** potential candidates and
**10,711** observed in-pool entries across **6,507** selected team-timeouts. Given the observed exits and entry
count, top-k entrant recall was **13.22%→58.10%**, paired gain **44.88 percentage points** (game-cluster 95%
**43.53–46.20 pp**); all four fold points improve. This is an over-inclusive pool with unknown physical eligibility,
and the simple deficit baseline is weak on it. Separately, under a retrospective participant-roster assumption,
**10,680** entrants in **6,493** complete team-timeouts yield **45.23%→61.71%** recall, gain **16.48 pp**
(95% **15.32–17.70 pp**). This oracle still does not prove current physical eligibility or forecast it. The joint
selector requires an explicit active roster, disqualification mask and five distinct players; its inputs include
the prior-position composition of the observed remaining lineup. Independent reconstruction/refits exactly match
all **84,344** ranking scores and all game-bootstrap metrics; **26** focused tests pass. Reports:
`analysis/experiments/20261122_a1_s06_in_screen{,_audit}.json`, retained candidate rows:
`data/derived/experiments/20261122_a1_s06_in_screen.parquet`; log `/tmp/musnba_a1_s06_in_screen_v1.log`
(**6,507** windows ranked in **24.7 s**, including fits). The audit's first syntax preflight failed before
execution; corrected audit log `/tmp/musnba_a1_s06_in_screen_audit_v2.log` passes.

**S06 60%:** TRAINING_PLAN freezes an isolated simulation protocol, not a promotion.
`scripts/a1_substitution_engine_models.py` independently refitted the frozen F4 nodes on **729** earlier games
through **2025-12-31**, reproducing both saved validation screens exactly (maximum error **0**). It saved **7,064**
selected timeouts, **729** regulation and **30** observed-overtime templates, including empty overtime periods;
the manifest is `analysis/experiments/20261122_a1_s06_engine_models_F4.json`, model/template artifacts are ignored
under `data/models/folds/a1_s06_selected_F4/`, and log is `/tmp/musnba_a1_s06_engine_models_F4.log`. Its initial
syntax preflight failed before fitting; the typo was corrected.

The new opt-in policy and engine hooks are **research wiring only**, not a promoted model. They use a
separate deterministic random stream, explicit active rosters, conditional simultaneous exits, learned incoming
ranks, deferred plan changes, overtime templates and replacement before a free-throw rebound; a short eligible roster
raises explicitly. The first hook test lacked a fake model's band table and failed before that check; the test fixture
was corrected. **36** focused tests now pass, including the controlled free-throw rebound, feature parity, repeatability
and accounting tests, and the new policy's Pylance diagnostics are clear. The F4 input loader verifies **7,317** strictly
prior player targets across all **200** fixed games. Existing production engine/backtest files retain unrelated prior
diagnostics; no new candidate-path diagnostic is reported. The unchanged default reproduced **3/3** pinned games in **51 s** (17 s/game) as
`20261122T090614Z_a1_s06_default_wiring`; independent
`analysis/experiments/20261122_a1_s06_default_wiring_accounting.json` matches all **92** non-key game columns and
**20** non-key player columns over **64** player-games to `1e-12`, plus **24** quarter and **6** team checks.
The same three-game candidate completed in **63 s** (21 s/game) as
`20261122T090745Z_a1_s06_candidate_wiring`, log `/tmp/musnba_a1_s06_candidate_wiring.log`. Independent
`analysis/experiments/20261122_a1_s06_candidate_wiring_accounting.json` checks **24** actual quarter scores,
**64** player 3PM actuals and **6** complete team 3PM sums with no mismatches. Across **3,000** worlds the policy
recorded **28,158** selected-timeout world events, **35,389** sampled exits, **1,395** foul-out replacements,
**364** coalesced and **582** expired clocks, and **88** overtime-timeout events; these are wiring counts, not
population rates or an accuracy comparison. The policy asserts team minutes and player/team points for every world;
save independent per-world accounting before awarding 70% or starting the fixed 200-game paired screen.
On this code, default smoke passed **102/102** (`/tmp/musnba_a1_s06_wiring_smoke.log`) and the deliberate fault
exited **1** with **80/102** checks passing (`/tmp/musnba_a1_s06_wiring_fault.log`). Neither run changed the served
model or PWA bundle; phone import remains unconfirmed.

**S06 70%:** a research-only `--audit-substitution-worlds` option saves player/period worlds,
availability and every segment lineup plus post-foul replacement lineups; `scripts/a1_substitution_world_audit.py`
independently replays lineup durations, checks five distinct available non-disqualified players, and reconciles each
player's minutes and each team's period/total points. Synthetic regulation, overtime, illegal-lineup, points,
missing-period and conserved-but-misallocated-minute tests pass, as do an initial four-player roster failure and
an exactly-five-player/no-eligible-replacement stress test. On `20261122T091633Z_a1_s06_world_trace_wiring` the
independent audit verified **3,000** worlds, **1,472,554** distinct-five snapshots, **1,395** post-foul changes,
**77** overtime worlds and **64** saved player means; maximum reconstructed player-minute error is **1.78e-15**.
The traced candidate reproduces all **104** original game and **20** player columns on **3 games/64 player-games**
to `1e-12` (`20261122_a1_s06_world_trace_{accounting,reproduction}.json`). The trace source was checkpointed in
**785a034** before the run. The **62 s** run and its outputs remain conditional on actual participants, not an
availability or accuracy result. Reproduce with
`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -u scripts/backtest.py --config models/v1.2d.json --fold F4
--game-ids analysis/experiments/20261122_a1_reproduction_games.json --worlds 1000 --jobs 1 --threads 8
--rotation targets --pool 0 --models folds/v1.2d_F4_all --substitution-candidate
analysis/experiments/20261122_a1_s06_engine_models_F4.json --audit-substitution-worlds --name
a1_s06_world_trace_wiring`. Then run `scripts/a1_output_audit.py <new-run> --reference
20261122T090745Z_a1_s06_candidate_wiring --output <new-accounting.json>` and
`scripts/a1_substitution_world_audit.py <new-run> --output <new-world-accounting.json>`.

**S07 10%:** the retained ESPN archive has **5** collections dated 19–21 Nov 2026, all in the protected final
season and **none** in development. Using collection-finish-before-tip gives **31** pre-tip game snapshots covering
**18** unique games and **1,093** roster/player snapshots covering **634** unique player-games; one snapshot was at
or after tip. All five collections have 30 roster teams and an injury report; **535** injury entries match a
collected team/player, with **426 Out** and **109 Day-To-Day** snapshot entries. The **2,105 Active** roster entries
are the existing missing-injury fallback, not proof of health. Of the 634 unique pre-tip player-games, **331** are
listed in retained final boxes, **128** are unlisted and **175** have no retained final box. Presence alone is not
play/DNP status. No protected-season status-versus-outcome scores were computed or used to select a model. Independent
`scripts/a1_availability_report_audit_check.py` reconstructs all **1,093** snapshot records and **634** unique
coverage states; reports are `analysis/experiments/20261122_a1_s07_report_coverage{,_audit}.json`, logs
`/tmp/musnba_a1_s07_report_coverage{,_audit}.log`. **4** focused tests and Pylance checks pass. The accepted
availability fallback remains unchanged. The partial checkpoint's normal smoke passed **102/102**
(`/tmp/musnba_a1_s07_10_smoke.log`), and the injected fault exited **1** with **80/102** checks passing
(`/tmp/musnba_a1_s07_10_fault.log`).

**S07 20%:** `scripts/a1_availability_labels_audit.py` independently reconstructs all **7,317** strictly prior-box
memberships in the fixed **200** F4 games and checks the raw labels and pre-origin team/appearance dates. There are
**4,316** known plays, **892** DNPs, **2,100** unlisted unknown and **9** listed-unknown. Of the DNPs, explicit
post-game text gives **675** coach, **6** rest, **35** injury, **9** illness, **2** injury/illness and **165**
other recorded reasons; the last category can include injuries without the word “injury” and is not assumed healthy.
All **4,316** known-play keys match the actual-participant oracle; **30** of the oracle's **4,346** player-games
are outside that known-play cohort. This is coverage/label reconciliation, not a pre-tip status score. Source,
fingerprints and exact counts are in `analysis/experiments/20261122_a1_s07_labels_audit.json`; two focused tests
and Pylance diagnostics pass.

**S06 and S07 partial evidence:** the frozen S06 200-game screen failed explicitly as described above; its
player-minute CRPS and state-response comparison were unavailable at that checkpoint; the later fixed screen and
state replay above are complete and retain the D29 control. For the F4 S07 baseline, the independent
`scripts/a1_availability_baseline_audit.py` reconciled the raw five-starter labels, all proxy Brier and calibration
cells, and 10,000 game-bootstrap intervals. No-report play-proxy Brier is **0.15450** (95% **0.14162–0.16773**)
on **5,208** known labels; its log loss is genuinely infinite from **718** impossible predictions. The separate
target-positive proxy Brier is **0.13110** and its log loss is infinite from **109** impossible predictions.
Across **399** supported team-games, starter-slot accuracy is **78.05%** (95% **75.90–80.10%**) and exact-five
accuracy **30.83%** (95% **26.25–35.34%**); **4** observed starters lie outside prior-box candidates. These are
retrospective inferred-roster play/start proxies, not validated historical injury-report forecasts. The F4 report
and accounting are `analysis/experiments/20261122_a1_s07_baseline_F4{,_accounting}.json`. The independent auditor
ran successfully, but Pylance reports three pandas `Scalar` argument-type diagnostics in its current typed numeric
helper; that original source and its reports are preserved in **5fd5e00**. A guarded numeric check now removes
the diagnostics and rejects infinite values; focused tests and Pylance pass, and the independent accounting was
repeated for all four folds as `analysis/experiments/20261122_a1_s07_baseline_F{1,2,3,4}_accounting_v2.json`.
TRAINING_PLAN §8.2 now freezes an exploratory, development-only recorded-DNP return/rest sequence protocol before
building or scoring it. Unlisted next games, trades, ambiguous labels and season ends must censor spells; its
conditional play proxy cannot establish physical recovery or the genuinely dated availability promotion gate.
The isolated `scripts/a1_availability_sequences.py` builder and **3** synthetic chronology/censoring tests are
preserved in **8c8a50f**. Its four-season build completed as former shell **2214**, wrapper PID **14887**, Python
PID **14888**, log `/tmp/musnba_a1_s07_sequences.log`: **9,846** team-games and **128,321** prior-state observations.
An earliest-season preflight checked **2,460** team-games, **31,551** player listings and **31,471** observations;
box/segment side coverage matched there. The build used
`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -u scripts/a1_availability_sequences.py --output
analysis/experiments/20261122_a1_s07_sequences.json --rows-output
data/derived/experiments/20261122_a1_s07_sequences.parquet`. Independent vectorised reconstruction matches **128,321** rows and **11**
fields each (`analysis/experiments/20261122_a1_s07_sequences_accounting.json`, log
`/tmp/musnba_a1_s07_sequences_audit.log`). It found **6,137** left-censored prior DNP observations and **8,490**
unlisted next games; **15,543** return and **97,808** recorded-rest known-outcome exposures remain. Across the
**17,261** non-left-censored return observations, prior reasons are **14,889** coach, **1,798** other recorded,
**494** explicit injury/illness and **80** exact rest. These are counts, not physical absence or calibrated hazard.
The first auditor source/report is preserved in **1dcfd6b**; its `np.select` type diagnostics were fixed and a
second independent reconstruction passed with no Pylance diagnostics as
`analysis/experiments/20261122_a1_s07_sequences_accounting_v2.json`. The frozen
`scripts/a1_availability_sequence_screen.py` runner and five focused sequence/cutoff/smoothing tests were pushed
before fitting. The four-fold screen completed with:
`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -u scripts/a1_availability_sequence_screen.py --output
analysis/experiments/20261122_a1_s07_sequence_screen.json --rows-output
data/derived/experiments/20261122_a1_s07_sequence_screen.parquet`. Independent dictionary-based refitting,
population reconstruction and direct 10,000-game bootstrap checking passed for all **18,612** predictions
(`analysis/experiments/20261122_a1_s07_sequence_screen_accounting.json`; source
`scripts/a1_availability_sequence_screen_audit.py`, log `/tmp/musnba_a1_s07_sequence_screen_audit.log`).

**S07 30%:** the four independently audited fixed baselines cover **28,530** inferred candidates, **20,665** known
play/DNP labels and **7,865** unknowns. Across F1–F4, supported starter team-games are **399/400/376/399**; five
F3 games lack both prior rosters, **15** team-games lack a required prior position, and **1** has incomplete starter
truth. Slot accuracy is **83.91/78.35/79.84/78.05%** and exact-five accuracy **42.36/31.25/29.79/30.83%**.
No-report play-proxy Brier is **0.14565/0.17460/0.14566/0.15450**; all four log losses are infinite
(**673/815/664/718** impossible outcomes). Target-positive Brier is **0.12116/0.13919/0.11205/0.13110**; its
losses are also infinite. These are incomplete-roster retrospective proxies, not evidence that the fallback is a
physical injury probability or a deployable forecast. Reports and independently reconstructed intervals are
`analysis/experiments/20261122_a1_s07_baseline_F{1,2,3,4}{,_accounting}.json`. The production model/bundle did not change.

**S07 40%:** the previously independently reconstructed inventory has **0** dated development report origins for
training and **0** for validation in each F1–F4 fold. All **5** retained collections are in the protected season.
Consequently no genuinely dated status-to-play/start split can be built from retained data; the existing fallback and
the future pre-tip collection gate remain. This is a coverage conclusion, not proof no older reports ever existed.
The checked fold dates, counts and fingerprints are recorded in
`analysis/experiments/20261122_a1_s07_dated_cohort_gate.json`. Do not score the protected reports' outcomes.

**S07 50%:** no genuinely dated development status cohort exists, so report-status play/start candidate calibration
is unsupported; the fixed status/no-report fallback remains untouched. TRAINING_PLAN §8.2 records the collection
gate: timestamped pre-tip rosters/reports, known outcomes with unknowns and coach DNPs separate, chronological splits,
at least **100 player-games / 30 games** for each assessed subgroup, paired uncertainty and all promotion gates.
Those are minimum support conditions, not a promise of promotion. The F1–F4 prior-box proxy scores cannot substitute
for this cohort.

**S07 60%:** the frozen earlier-fold duration/return and recorded-rest play proxies are fitted and independently
audited. Return candidate minus reason-only baseline Brier is **−0.00540/−0.01368/−0.01082/−0.01380** on
**612/713/503/649** known next-listing observations (F1–F4); the F1 95% interval includes zero, while F2–F4 are
negative. Rest-role Brier changes are approximately **+0.00000008/−0.00000012/−0.00000000/−0.00000059** on
**4,051/4,005/4,001/4,078** observations. Star-return subgroups are unsupported in every fold. These are
retrospective, selected listed-player proxies, dominated by coach DNP; neither a physical recovery estimate nor a
deployable future-absence model follows. Continue with explicitly censored duration/role comparisons; fixed report
fallback, engine v1.3, forecasts and bundle remain unchanged.

**S07 follow-ups:** `scripts/a1_availability_spell_sim.py` constructs the pre-registered
five-next-game trajectories and deterministic 10,000-draw earlier-fold proxy simulations. Focused tests cover
returns, unlisted/fold-end censoring, seeded survival and unsupported subgroups with empty bootstrap samples; these
cells remain inconclusive without aborting the experiment. `scripts/a1_availability_starter_sim.py` draws independent
no-report active states, applies the as-of D29 selector to each valid active set, records five-player identities and
leaves unknown-position or short-roster worlds unsupported; a separate world-by-world audit is prepared.
**31/31** focused state-capture, rate-accounting and availability tests pass. The completed spell commands were
`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -u scripts/a1_availability_spell_sim.py --output
analysis/experiments/20261122_a1_s07_spell_sim.json --rows-output
data/derived/experiments/20261122_a1_s07_spell_sim.parquet`; then run the separately implemented
`scripts/a1_availability_spell_audit.py --output analysis/experiments/20261122_a1_s07_spell_sim_accounting.json`
to check trajectories, hazards and intervals. Run
`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -u scripts/a1_availability_starter_sim.py
--fold F1 --output analysis/experiments/20261122_a1_s07_starter_sim_F1.json --rows-output
data/derived/experiments/20261122_a1_s07_starter_sim_F1.parquet --teams-output
data/derived/experiments/20261122_a1_s07_starter_sim_F1_teams.parquet --lineups-output
data/derived/experiments/20261122_a1_s07_starter_sim_F1_lineups.parquet`, then repeat F2–F4 and run
`scripts/a1_availability_starter_audit.py --fold F1 --output
analysis/experiments/20261122_a1_s07_starter_sim_F1_accounting.json` for each fold.
The source was committed and pushed as **eb63126** before scoring. The spell simulation has since completed
**1,493** anchors across F1–F4 (371/439/308/375) and its independent audit reconciled **29,860** survival values
and **80** role/horizon cells, with 10,000 bootstrap replicates; reports
`analysis/experiments/20261122_a1_s07_spell_sim{,_accounting}.json`, retained rows
`data/derived/experiments/20261122_a1_s07_spell_sim.parquet`, logs `/tmp/musnba_a1_s07_spell_{sim,audit}.log`.
All star/starter role horizons are below the 100-at-risk/30-game support floor. Unlisted right censoring is common
and may be informative; these results do not validate physical absence. The precommitted F1–F4 starter simulations
and independent replays all finished: **200/200, 200/200, 195/200 and 200/200** rostered games;
**7,398/7,390/6,199/7,299** player-games; and **769/805/569/904** distinct fives. The audits reconciled
**14,106,556** supported worlds; **1,783,444** active-unknown-position worlds were excluded, and no inferred-roster
world had fewer than five active players. F3 lacks prior rosters for five games; one F4 team lacks complete actual
starter labels. Role frequencies, bootstrap intervals and limitations are in FINDINGS. Former sequential audit
shell **2349** exited 0; logs `/tmp/musnba_a1_s07_starter_{sim,audit}_F{1,2,3,4}.log`. S07's 70% rung is complete.
Before 80%, a synthetic stress test confirmed an existing serving bug: in a five-player pool with only four
available, `Game._target_tables` silently reinstates the unavailable fifth player for all **2,880** regulation
seconds. None of the **15,890,000** historical proxy worlds triggered it, which does not establish safety for a
short or uncertain prospective roster. The delivered engine now fails explicitly instead and preserves the pinned
valid-world RNG fingerprints.
The partial-source checkpoint's normal smoke passed **102/102** and deliberate-fault smoke passed its expected
failure check: **80/102**, nonzero fault exit, former shell **2291**. Logs
`/tmp/musnba_a1_s06_flow_partial_smoke.log` and `/tmp/musnba_a1_s06_flow_partial_fault.log`. The
**31** current focused tests and direct-state-auditor Pylance check passed. This is a source-freeze checkpoint,
not a completed S06 or S07 task.

**S07 fallback repair, source-freeze history:** missing injury files or statuses previously became
`Active`, and an injury entry for an old team could overwrite a traded player's current roster status. The
working `scripts/box_scores.py` now reports missing/conflicting statuses as `Unknown`, uses the existing
uncalibrated unknown-status probability, warns on report/roster mismatches, omits ambiguous multi-team roster
entries and rejects malformed/unidentifiable injury reports. Its rebuilt status counts exactly match all **five**
previously audited valid collections; **20** focused ingest/availability tests pass. The working dashboard
shows `Unknown` and labels its fallback as uncalibrated; other status percentages are labelled availability,
not actual simulated participation. A synthetic browser response confirmed the snapshot-source, unknown-status,
recent-inactivity, assumed-availability and actual-simulated-participation wording; at phone width, both fallback
tags have no horizontal clipping. Availability tags in game tables now wrap below the player name. The earlier
**36/36** width/theme checks passed in former shell **2414**, log `/tmp/musnba_a1_s07_browser_final.log`; desktop,
half and phone screenshots were inspected under `/tmp/musnba-a1-s07-final-shots`. The final focused Game Centre
width/theme rerun passed **6/6**, former shell **2498**, log `/tmp/musnba_a1_s07_layout_final.log`; all six
screenshots under `/tmp/musnba-a1-s07-layout-final` were inspected.
An isolated data-free preview shell built at
`/Users/moholom/.copilot/session-state/cd6afd9f-2b4e-4039-8e12-170c203c5b67/files/MusNBA`, cache version
**5902923a710631db4ca0**, imported the existing iCloud bundle and passed **15/15** local import/offline checks,
log `/tmp/musnba_a1_s07_pwa_preview.log`; its temporary :8768 server is stopped. This is not a Pages publication
or a new bundle, and does not prove phone import.
The former review server shell **2404** served `127.0.0.1:8767` (PID **22620**) and has been stopped; the owner's
:8766 was not touched.
The ingest/UI source's normal smoke passed **102/102** and its deliberate-fault run failed as expected with
**80/102**, former shell **2440**, logs `/tmp/musnba_a1_s07_ingest_{smoke,fault}.log`. The applied engine/projection
changes required a new smoke/fault check, completed in former shell **2605**; after the additional starter-score
repair, final smoke passed **102/102** and deliberate-fault smoke failed as expected **80/102**, former shell **2626**.
Before repair, `projection.availability(None)` assumed `Active` and the short-roster engine fallback activated
unavailable players; the corresponding missing/blank-status and legal-five tests now pass. On retained registry
20261121T225637Z, after the recent-DNP heuristic, all **30** teams
have at least **10** certain players; an under-five fail-fast guard would not affect that population, but this
does not establish safety for future missing reports. A new
`tests.test_a1_availability.AvailabilityCohortTests.test_short_rosters_fail_in_both_engine_rotation_paths`
now passes in both target and legacy paths. Before editing, a seeded
two-world/six-player-per-side valid-roster parity fixture hashed its tables, combinations and next 64 RNG bytes:
legacy `4f23f0626b73e64fd1821e7174475de523261cee46765c917bf5097219e4f55d`; targets
`9d1427395faedf996a9636a0169bf22f98ddcc14ce22420216dd54f39a8373eb`. The exact executable fixture and
fingerprints live in `tests.test_a1_availability.AvailabilityCohortTests.test_valid_rotation_worlds_and_random_stream_match_pre_guard`;
repeat it after the fix. An isolated copy at
`/Users/moholom/.copilot/session-state/cd6afd9f-2b4e-4039-8e12-170c203c5b67/files/a1-s07-isolated`
now has candidate fail-fast guards in both rotation paths, unknown-status handling, and a projected-starter fix
when fewer than five players are certain. A prospective placeholder fixture also returned success for **51/100**
worlds with only four available players; the isolated candidate now rejects such worlds while preserving the
retrospective path. **44** combined focused tests pass there, including both rotation fingerprints and a complete seeded valid placeholder
forecast fingerprint. These changes have since been applied and retested in the live sources. The isolated copy
symlinks the existing data and virtualenv; do not run jobs that write through its data link. At this earlier source
checkpoint no new forecasts, bundle or shell had been published; the later delivery and checks are in § State.
The report-provenance repair makes new prospective game outputs freeze their own roster/status
snapshot, including ruled-out players; views no longer substitute a later registry, and old snapshots explicitly
show only the statuses they retained. The UI distinguishes fixed/unknown/recent-inactivity assumptions from
simulated participation. The revised ingest/report also preserves a nullable reported status and its source: a
present report with no injury entry retains the existing assumed-available probability but is explicitly marked
`not_listed_assumption`, not a confirmed health status. The Game Centre discloses that distinction.
The previously served nightly metadata uses slate-start time rather than output completion, so a run crossing tip
can incorrectly claim a pre-game result. The delivered repair below addresses new snapshots; S13 must carry its
legacy-unverified distinction through versioned archives.
A separate preview-origin defect was reproduced: retained 22 Nov's preview has season origin 21 Nov but reports
cutoff 21 Nov instead of 20 Nov, and its league inputs include **236** games versus the origin snapshot's **235**.
The working `project_slate` now selects team/player/period inputs by the shared origin, writes origin/cutoff and
requires the season origin to match; a date-injection test and independent audit pass. After the S06 audit finished,
the engine guard was changed to reject post-origin profiles and use pre-origin minute fits, stints and matchup
history while retaining the target date for game context. Old previews must not be relabelled safe.
**S07 80–90%:** the isolated roster/report, unknown-status, legal-five and cold-placeholder repairs have been
transferred to the live sources after the S06 audit. **82** focused Python tests and **3** JS tests pass, including
valid-world RNG fingerprints and origin-date injection. Retain the uncalibrated fixed status/recent-inactivity
assumptions and D29 projected-starter fallback; no future physical-absence hazard is justified by the censored
coach-DNP proxies. S08's two-maybe product weights are unvalidated independence assumptions and >2 one-out cases
are non-exhaustive. S10 retains no fitted future player-absence hazard. Production snapshots and PWA were refreshed
after this source checkpoint, as recorded in § State. The pre-repair S06 `engine.py` SHA-256 `3c62f518...681414e` remains reproducible from pushed
checkpoint `d7e00aa`; rerun the hash-locked S06 audit with that source, not the modified working engine.
The delivered snapshot writer records completion after the atomic snapshot rename and computes pre-tip from
that time; legacy/incomplete outputs have unverified timing and are excluded from pre-game accuracy summaries.
Focused before/after-tip, legacy-timing and audit tests pass. Isolated shell `f79ce8eab3ebe9182d59` passed **16/16**
import/offline checks against the old bundle, including legacy timing (log
`/tmp/musnba_a1_s07_pwa_timing_old_bundle_v2.log`); its :8768 server is stopped. That preview preceded delivery.
An additional starter-score audit found that the existing **10-slate, 132-team-game** accuracy record includes
**7** retrospective slates / **104** team-games and **3** prospective slates / **28** team-games without verified
completion timestamps. The working scorer preserves its per-slate and overall legacy figures separately,
scores only explicitly pre-tip prospective games, and the Lab hides old-bundle scores lacking that timing policy.
**78** combined focused Python and **4** JS tests passed, including legacy migration and incomplete/after-tip
cases. Lab passed **6/6** width/theme checks with all six screenshots inspected in
`/tmp/musnba-a1-s07-lab-legacy`; shell `0d7693ac00bad5eb2e00` passed **17/17** old-bundle import/offline checks,
including Lab, log `/tmp/musnba_a1_s07_pwa_preview_latest_v2.log`; :8768 is stopped. The subsequent nightly,
score migration, bundle and hosted shell passed the delivery checks in § State. Post-repair normal smoke passed
**102/102** and deliberate-fault smoke failed as expected **80/102**, logs
`/tmp/musnba_a1_s06_checkpoint_{smoke,fault}.log`.
The existing local `data/views` was copied and byte-verified before the planned rebuild at
`~/Basketball_archive_ops/archive_20261122T113442Z_34262/data/views`.
S08 must address the exact-mixture counterexample in FINDINGS: 10,000 equally weighted season outcomes cannot
represent every exact blend of 10,000-world branch distributions, even for one game's win probability.
`tests.test_views_availability` and `tests/test_status_tag.mjs` pass their focused checks;
the prepared `scripts/a1_snapshot_availability_audit.py` requires `--origin YYYY-MM-DD` and independently checks
pre-origin team/player inputs, completion/tip labels, matching origin registry, view provenance, every saved
player/team point total and season/game world identities. Its
synthetic regression tests pass; run it on the newly generated live days after nightly, not on legacy snapshots.
the new report/basis fields change the forecast contract and therefore require refreshed outputs and PWA delivery.
Further synthetic cold-roster stress found the placeholder returned **101.9/102.1** mean team points with no
player minutes or displayed player lines when six players were available but all had zero minute inputs. The
isolated candidate now warns and records an uncalibrated equal-share fallback in such prospective worlds, fills
five projected starter labels, and independently reconciles quarter minutes, overtime, points and an unavailable
player across **300 worlds per side**. **45** focused Python tests now pass in the isolated copy, including the
unchanged valid-world fingerprints. The live Game Centre has an unshipped disclosure for this fallback. This
targeted repair does not validate or repair all other placeholder allocations. A synthetic phone response showed
the fallback's exact team and world counts without clipping; its screenshot is
`/tmp/musnba-a1-s07-fallback-synthetic-full.png`. The subsequent game-route sweep passed **12/12**, former shell
**2512**, log `/tmp/musnba_a1_s07_fallback_layout.log`; representative desktop, half and phone screenshots were
inspected under `/tmp/musnba-a1-s07-fallback-layout`. A freshly built isolated data-free shell, cache version
**39992ead9ae553927563**, imported the existing iCloud bundle and passed **15/15** import/offline checks, former
shell **2519**, log `/tmp/musnba_a1_s07_pwa_preview2.log`; its :8768 server is stopped. This preview is not a
Pages publication, a new bundle or proof of phone import.

The tracking family was frozen in TRAINING_PLAN §8 and built separately by
`scripts/a1_tracking_features.py`: former wrapper PID **85586**, shell **1549**, log
`/tmp/musnba_a1_s04_tracking_features.log`, output
`data/derived/experiments/20261122_a1_s04_tracking_features.parquet` and report
`analysis/experiments/20261122_a1_s04_tracking_features.json`. The builder verified all **1,692** historical source
files and saved **921,103** shot rows. It verifies source bytes, dates, NBA day-team joins and the crosswalk, uses
only dates before each target and leaves missing five-player inputs missing. The separate
`scripts/a1_tracking_screen.py` and cutoff/team/zone tests are implemented. The independent chronological auditor
passed: **1,692** source files, **146,581** distinct game-fives, **921,103** shots and **4,605,515** checked
feature values (`analysis/experiments/20261122_a1_s04_tracking_accounting.json`). **69** related A1 tests pass.
Pylance had inferred the existing `nbastats.nba_tables` as `NoReturn` at both tracking unpack sites and the
auditor's heterogeneous list as `list[bool]`. A type annotation plus explicit NumPy integer extraction clear
those diagnostics in checkpoint **38155fc**; the **112,952**-row four-season player/day/team mapping matches exactly.
Explicit missing/non-finite player-ID rejection prevents NumPy from silently converting invalid IDs; **86** focused
A1 tests pass across the five test modules. The original source that produced the tracking reports is preserved in pushed commit **00a51cc**;
do not silently rewrite old report hashes.
A full typed-source feature rebuild completed as former wrapper PID **90455**, session **1646**, log
`/tmp/musnba_a1_s04_tracking_typed.log`. Its **921,103** rows are byte-identical to the original parquet
(SHA-256 `d88e47e20f6d22226047f78f62f41f0e9802eae6b984a404ce45df7ab952866e`), with equal source/coverage counts.
Independent typed-input accounting completed as former wrapper PID **90612**, session **1651**, log
`/tmp/musnba_a1_s04_tracking_typed_audit.log`: **1,692** source files, **146,581** game-fives and **4,605,515**
feature values checked (`analysis/experiments/20261122_a1_s04_tracking_accounting_typed.json`). Its new typed feature
report is `analysis/experiments/20261122_a1_s04_tracking_features_typed.json`; original reports remain immutable.
Running the new auditor against the original feature report correctly rejects the changed source hash (expected;
`/tmp/musnba_a1_s04_tracking_old_source_guard.log`); use the original checkpoint source to reproduce the original
report, or the explicit typed report/rows flags to audit the new build.
The normal smoke on the final engine/tracking sources passed **102/102** (former wrapper PID **91963**,
session **1668**, log `/tmp/musnba_a1_s04_typed_smoke.log`); the separate current-engine deliberate-fault smoke is
session **1613**, with expected exit 1 and **80/102**. The subsequently corrected research-only gate is not imported
by smoke and passed its own regression tests.
The four-fold tracking screen completed sequentially in shell **1567**, log
`/tmp/musnba_a1_s04_tracking_folds.log`; command for each fold is
`.venv/bin/python -u -m scripts.a1_tracking_screen --fold F1 --output
analysis/experiments/20261122_a1_s04_tracking_F1.json --rows-output
data/derived/experiments/20261122_a1_s04_tracking_F1.parquet` with F1→F4. Independent reconstruction of the four
fold predictions, **112** populated metric groups and frozen same-input noise gate passed in
`analysis/experiments/20261122_a1_s04_tracking_node_gate.json`. Across the full held-out folds, candidate-minus-control
losses were **+0.00022107 / +0.00002580 / +0.00000209 / +0.00001616**. Their mean relative loss increased
**0.00906%**, pooled game-cluster z **+3.76**; F1's **+0.03021%** and z **+3.63** exceed twice the **0.01372%**
noise floor, so the existing node verdict is **worse**. This specific tracking increment is rejected; it is not an
unchanged-v1.3 engine comparison and does not disprove other player-based defence mechanisms.
The registered survivor-only engine-test set is empty: neither failed family receives a backtest or a claimed
player/team improvement, and S03's v1.3 component/total-bias control remains the relevant baseline. A separately
labelled post-hoc check composes the frozen rim and tracking log-odds adjustments on identical shots, with no refit
or promotion pathway (`analysis/experiments/20261122_a1_s04_defence_interactions.json`). Independent accounting passed
on all **499,589** shots (`analysis/experiments/20261122_a1_s04_defence_interaction_accounting.json`); the combined
full-fold loss changes were **+0.00021749 / +0.00005594 / +0.00000852 / −0.00000768**. This descriptive
interaction cannot rescue either family. There are no retained inputs requiring player-engine confirmation.
Keep original-publication and revision uncertainty explicit even though every event date is strictly before its target.

**Use the app:** https://musamoholo.github.io/MusNBA/ — data-free GitHub Pages, source branch `gh-pages` at **f2932e1**.
iPhone: Safari → Share → Add to Home Screen → launch the icon → Offline data & installation → Import data.
Bundle: **iCloud Drive/MusNBA/MusNBA.musnba.gz**, generation and SHA-256 in § State. The earlier close-out copies
in `exports/` and `~/Downloads/` matched the then-current 10,620,944-byte bundle; they have not been verified as
copies of the new iCloud generation. Earlier phone file visibility is not confirmation of this new import.

**Earlier dashboard close-out refresh:** 21 Nov (6 games) and 22 Nov (7 games), engine v1.3, **10,000 worlds per game**, one rotation table
per world; fresh **10,000-world season, 965 remaining games**, as of ET 21 Nov. Offline/no-rebuild nightly finished
22 Nov 01:04 UK; finished-code views rebuilt at 01:05 before export (nightly had loaded views before U19 was added).
Earlier snapshots/shells/bundles archived in `~/Basketball_archive_ops`. No fetch, training or model promotion in the dashboard close-out or this planning pass.

**S03 component diagnosis:** the S01 pool-0 control and manifest match exactly on **200 games / 400 team-sides**.
`data/derived/experiments/20261122_a1_s03_component_sides.parquet` and
`analysis/experiments/20261122_a1_s03_components.json` reproduce the complete archived team-rating baseline and every
rounded component loading; the report supplies **10,000** game-cluster bootstrap intervals. The simulated-minus-real
points/100 loading is **−0.417** (95% interval **−0.837 to −0.024**) for own offence and **−1.008** (**−1.395 to
−0.640**) for opponent defence. These are observational differences, not causal findings. All four focused
`tests.test_a1_signal` cases pass; the pre/post-extraction baseline summary is identical. The initial direct-script
attempt transiently failed to import NumPy; `.venv/bin/python -m scripts.a1_signal` and a subsequent direct `--help`
worked without installing anything. M6a's old branch code omitted the current chain's profile/policy attributes and
retained the original actor's matchup values after a hypothetical shooter/zone change; v1.2d uses those values.
The isolated replay now loads the exact persisted fold models without refitting and builds actor-specific matchup
features, with focused tests. Three-game wiring completed in **39 s**, log `/tmp/musnba_a1_s03_m6a_wiring.log`:
`.venv/bin/python -u -m scripts.aggregate --config models/v1.2d.json --models folds/v1.2d_F4_all --fold F4
--game-ids analysis/experiments/20261122_a1_reproduction_games.json --worlds 20 --threads 8 --components
--name a1_s03_m6a_wiring`. Run `20261122T044924Z_a1_s03_m6a_wiring` independently reconciled **180** player/team
component values and score identities; all **17** saved engine model hashes match S01. Nine real actor/lineup
mismatches were separately counted, and eligible-event actuals differ from official scores by one point on two
team-sides (`analysis/experiments/20261122_a1_s03_m6a_wiring_accounting.json`). This is wiring, not accuracy.
The 200-game IDs derived from the manifest are `data/derived/experiments/20261122_a1_s03_f4_game_ids.json` (regenerate
as the sorted `control.games[].game_id` values). Next run the same saved models and IDs at 10,000 worlds, audit all
outputs and do not treat the retained v1.1 replay as a same-model comparison. Saved `node_fit` metrics in the replay
report are historical metadata from the old fit, not newly validated accuracy evidence.
The full 200-game, 10,000-world replay completed in **705 s**, log
`/tmp/musnba_a1_s03_m6a_fixed200.log`:
`.venv/bin/python -u -m scripts.aggregate --config models/v1.2d.json --models folds/v1.2d_F4_all --fold F4
--game-ids data/derived/experiments/20261122_a1_s03_f4_game_ids.json --worlds 10000 --threads 8 --components
--name a1_s03_m6a_fixed200`. Run `20261122T050308Z_a1_s03_m6a_fixed200` passed independent accounting
`analysis/experiments/20261122_a1_s03_m6a_fixed200_accounting.json`: exactly **200 games, 400 sides, 4,346
player-games**, **17/17** S01 model files and **12,000** player/team component values match, with maximum accounting
difference `1.42e-14`. There are **487** actor/lineup mismatches, and event-filtered actual scores differ from official
scores on **110/400** sides (mean **−0.318**, range **−2 to 0** points per side). Teacher forcing is not a forecast.
The profile spread rung has passed its independent execution and accounting checks. `scripts.a1_profile_spread` produced
`analysis/experiments/20261122_a1_s03_profile_spread.json`; its **35,413** shot events and **177,060** defensive
exposures reconcile, with one invalid defensive five and **378** shooters outside the recorded offensive five.
Independent execution reproduced all cross-half groups/weights; ten focused S03 tests pass. The
`scripts.a1_shot_trace` report `analysis/experiments/20261122_a1_s03_shot_trace.json` aligns the saved node cache
against game/date/period/result, margin, clock, coordinates and shooter profiles, matches the F4 model/cache
signature and applies training-window distance bands. The shot node's mean make probability is **47.63%** versus
**47.45%** observed. At the rim, high-minus-low matchup-profile quartiles show **6.66** observed versus **3.65**
predicted percentage points; the exploratory, post hoc paired game-bootstrap gap is **3.01 pp** (95% **0.25–5.73**).
This unadjusted association is not a causal defence effect; multiple comparisons, stale lineups and historical
publication timing limit it. No model or PWA change follows from these diagnostics.
At **00:00 ET on 22 Nov** the saved local `data/views/api/meta.json` still selected the 21 Nov snapshot, so the first
post-rollover smoke reported **101/102** despite the stored game replaying bit-for-bit. The other smoke issue was
new M6a event/component files being mistaken for player output; discovery now requires the matching aggregation
report, with a regression test. The prior local views were archived at
`~/Basketball_archive_ops/20261122_a1_s03_views_before_et_rollover.tar.gz`, then `scripts/views.py` rebuilt **1,960**
local views from existing snapshots with latest date 22 Nov; it did not fetch, fit or simulate. This uses the already
stored dated preview, not a newly generated Today prediction. The served engine and phone bundle remain unchanged;
post-refresh smoke passed **102/102**, including a bit-for-bit stored-game replay (log
`/tmp/musnba_a1_s03_post_rollover_smoke.log`), and **14** focused signal tests pass. Do not claim a new phone import.
For rung 60, opt-in `--flow-diagnostics` now records scheduled fives, clock, and player/quarter components; it does not
change the default simulation path. The three-game, 1,000-world original-seed pilot completed in 53 s, run
`20261122T051535Z_a1_s03_flow_wiring`, log `/tmp/musnba_a1_s03_flow_wiring.log`:
`.venv/bin/python -u scripts/backtest.py --config models/v1.2d.json --fold F4
--game-ids analysis/experiments/20261122_a1_reproduction_games.json --worlds 1000 --jobs 1 --threads 8
--rotation targets --pool 0 --models folds/v1.2d_F4_all --flow-diagnostics --name a1_s03_flow_wiring`.
The pilot matched all **279** original game and **1,408** player values and all 17 model hashes. All four player-quarter
point sums matched game quarter scores to ≤7.2e-15, and combined player minutes were exactly 120 per regulation quarter.
Scheduled fives are before foul-out replacements and are not simulated event-level lineups.
The independent `scripts/a1_flow_audit.py` pilot now also checks **1,280** recorded player-period values, **96**
team/quarter/component sums, six real stint tick sets and 12 clock values; maximum difference **2.84e-14**. The final
pilot report is `analysis/experiments/20261122_a1_s03_flow_wiring_independent_accounting_v3.json` (v1/v2 precede
additional input guards and are superseded). For the full run, audit roster omissions explicitly: a side with a
simulated player missing from the box output cannot independently reconcile its player-level sum.
The full 200-game run completed, former wrapper PID **70914**, child **70915**, log
`/tmp/musnba_a1_s03_flow_fixed200.log`; command as above with
`--game-ids data/derived/experiments/20261122_a1_s03_f4_game_ids.json --name a1_s03_flow_fixed200`.
The comparison `analysis/experiments/20261122_a1_s03_flow_comparison.json` and independent accounting
`analysis/experiments/20261122_a1_s03_flow_fixed200_accounting.json` completed; they reconcile **18,600** game and
**95,612** player values, and **86,920** player-period values to maximum `2.84e-14`. One roster side has an
unmatched player. Teacher-forced versus free-running defence-loading errors were **−1.017 / −1.008** points per
100; their paired difference was **+0.009** (95% **−0.195 to +0.211**). These are descriptive, not causal.

**S05 concurrent progress (60%):** S01's prior-box membership accidentally included 73 All-Star box rows in four
games whose non-NBA teams were labelled `season_type=2`. The old cohort is retained; corrected
`analysis/experiments/20261122_a1_prior_box_coverage_nba_only.json` and
`data/derived/experiments/20261122_a1_prior_box_membership_nba_only.parquet` restore 12 player-game keys.
The strictly prior-date population audit `scripts/a1_minutes_audit.py` and
`analysis/experiments/20261122_a1_s05_minutes_population.json` cover 7,317 candidates, including 675 DNP-coach,
1,412 recent-minute fringe, 2,481 recent-minute core, 257 recent team changes, and 29 core returns in 24 games;
unlisted remains unknown. **21** focused availability/signal tests pass. The independent replay in
`analysis/experiments/20261122_a1_s05_minutes_diagnostic.json` matches all **892** final D29 rotation shares exactly
and quantifies the NBA-only target candidate. Its first run exposed one source contradiction (game `401468760`, player
`2999409`: coach-DNP and 119 on-court seconds); the replay preserves and reports both updates exactly as D29 does.
`analysis/experiments/20261122_a1_s05_rotation_diagnostic_reg.json` traces 240-minute targets and possible overlap
with recent-nonappearance availability; its earlier mixed-total-minutes report is explicitly superseded.
The baseline minute CRPS for pre-game stars/starters/bench is **2.891/3.024/3.980**, with coverage
**82.0/82.4/74.8%**; returners are below the gate. The NBA-only candidate changed star/bench target MAE by
**−0.328/+0.036 minutes**, not yet an engine test. The opt-in `scripts/a1_minutes_candidate.py` matches all **4,346**
independently built candidate states exactly (`analysis/experiments/20261122_a1_s05_nba_candidate_wiring_v3.json`),
rejects same-day duplicates and incomplete two-NBA-team games, and leaves production and default backtests unchanged. **23**
focused tests passed before the strict-allocation addition; now **24** pass. A separate candidate correction
`analysis/experiments/20261122_a1_s05_minutes_candidate_stress.json` preserves 240 regulation minutes to 1.43e-13,
limits players to 48 and passes **400** fixed-panel absence cascades. It does not repair the historical state-pass
allocator; both candidate switches still need isolated engine integration and scoring. Wiring v2 is superseded after
adding strict helpers; v3 completed successfully (`/tmp/musnba_a1_s05_nba_candidate_wiring_v3.log`). The fixed S03
run logged **120/200 in 1,896 s** at that earlier checkpoint and has since completed. The preregistered F1–F4 **conditional** allocator-only screen
finished 200 games per fold in **9.6 / 9.3 / 9.5 / 9.3 s**, log `/tmp/musnba_a1_s05_minutes_fold_screen.log`,
command `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -u scripts/a1_minutes_fold_eval.py`.
It compares original, NBA-only, strict-runtime and combined variants using 1,000 matched draws on **17,303**
actual-participant player-games. NBA-only changes star CRPS **−0.020/−0.081/−0.023/−0.196** and bench CRPS
**−0.001/+0.010/+0.015/+0.022** by F1–F4; the strict allocator changes conditional CRPS by <1e-6. One observed
F4 team totals 239.618 regulation minutes; other teams are within 0.002. Full intervals, sample sizes and integrity
counts: `analysis/experiments/20261122_a1_s05_minutes_fold_screen.json`. **25** focused tests and Pylance checks
passed. This cannot establish unconditional pre-game accuracy: that needs an admissible pre-origin roster and
physical availability, both limited. A separately labelled all-prior-box-candidates-active sensitivity now scores
known DNP zeroes and positive regulation minutes while retaining unknown candidates in allocations; it cannot supply
an official roster or injury forecast. `scripts/a1_minutes_unconditional.py` runs F1–F4 sequentially via shell PID
**76244** (initial child **76245**), log `/tmp/musnba_a1_s05_unconditional_folds.log`. Command:
`for fold in F1 F2 F3 F4; do OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -u
scripts/a1_minutes_unconditional.py --fold "$fold" || exit; done`. Each completed fold writes a distinct JSON report
and parquet under the `20261122_a1_s05_unconditional_F*` prefix; resume only missing folds. The independent F4
as-of rebuild exactly matched a fresh dated build's latest states, team dates, ramp and spread for both histories;
a fixed F1 team wiring had **17** candidates, 14 known actuals and 3 unknown. **27** focused tests and Pylance
diagnostics pass. Prior-box universes contain **7,423 / 7,390 / 6,400 / 7,317** candidates for F1–F4, with
**20 / 17 / 137 / 26** observed playing IDs outside those universes; F3's early-season coverage is notably limited.
F1 completed **200/200** in **128.1 s**; F2 reached **101/200** in **97.6 s**. F1 has **5,218** known labels
and **2,205** unknown; its all-active target-minute CRPS is **5.039** with **64.6%** coverage on known labels.
Do not compare this as an end-to-end availability forecast. Independent raw regulation-minute checks found no
missing or outside-0–48 values among all **17,303** fixed-fold participant records.
The all-active screen subsequently finished F2 **200/200** in **214.7 s** and reached F3 **82/200** in **81.2 s**.
F3's run is finished but evaluated **195/200** games: five season-opening games have neither team's prior
same-season box roster (10 team-sides). They appear in `candidate_coverage.team_games_without_prior_candidates` and
must not be treated as scored or silently assigned an inactive roster. F3's report's `games: 200` denotes the
requested fixed set, not scored coverage; `scripts/a1_minutes_screen_audit.py` explicitly reconciles requested versus
evaluable team-sides and games.
A complementary, preregistered no-report fallback now uses the existing 1.0/0.8/0.5 recent-nonappearance rule and
strictly earlier four-appearance EWMA; unknown prior box entries remain counted. It draws common physical-availability
patterns and reallocates each roster, resampling fewer-than-five patterns rather than pretending they are legal.
`scripts/a1_minutes_no_report.py` runs F1–F4 sequentially via shell PID **77309** (initial child **77310**), log
`/tmp/musnba_a1_s05_no_report_folds.log`; command:
`for fold in F1 F2 F3 F4; do OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -u
scripts/a1_minutes_no_report.py --fold "$fold" || exit; done`. Each completed fold writes a distinct JSON/parquet
under `20261122_a1_s05_no_report_F*`; resume only missing folds. The one-team F1 wiring had 17 candidates, eight
availability patterns, zero resamples and maximum strict team-minute error **5.68e-14** across 100 draws.
**29** focused tests and Pylance diagnostics pass. This remains a no-report, incomplete-roster sensitivity, not
reconstructed injury status or a model-promotion test.
The F1 no-report screen finished **200/200** in **142.7 s**. It scored **5,218** known labels while retaining
**2,205** unknown candidates; baseline CRPS was **4.709 minutes**, 10–90% coverage **68.8%**, and target-play Brier
**0.1212** on known labels. These numbers are not a reconstructed injury forecast. The independent F1 paired screen
audit (`analysis/experiments/20261122_a1_s05_minutes_screen_accounting_F1.json`) reconciled the control and both
variants, unknown and positive outcome populations, **19** source hashes and 240-minute team means. The strict
allocator's maximum mean team-minute error was below **3e-13**, versus **8.24e-5** for the legacy allocator;
the largest legacy error in an individual draw was **0.0752** minutes.
Its CRPS comparison tolerance has since been strengthened to `rtol=0`; the new F1–F2 paired audit
`analysis/experiments/20261122_a1_s05_minutes_screen_accounting_F1_F2_uncorrected.json` passed with **20** source
fingerprints. At 06:01 UK all-active F1–F4 had finished (F4 **200/200** in **323.3 s**); no-report F1–F2 had
finished and F3 had reached **121/200** in **116.9 s**. The S03 flow log was at **160/200** in **2,569 s**.
A single-threaded checkpoint smoke subsequently passed, former PID **78602**, log `/tmp/musnba_a1_s03_partial_smoke.log`. Resume
missing folds only if a wrapper exits; never assume a launched fold succeeded. **29** focused tests passed before
the new expected-failure regression. Next report completed fold/game counts, audit all folds honestly, then
connect separately identifiable candidate switches to isolated backtests after the S03 flow completes.
At 06:05 UK the flow reached **180/200 in 2,903 s** and no-report F1–F3 finished; F4 reached **100/200 in
150.8 s**. The F3 paired audit
`analysis/experiments/20261122_a1_s05_minutes_screen_accounting_F3_uncorrected.json` identifies all five missing
opening-day games. The original conditional screen JSON SHA-256 is
`d1cf7ee333a0fab025699a35248a9b0c22fb3f784860bf4d46fb8aefe81ca19b`, its ignored parquet is
`9082ee7f42856202d1546c1300d28aab392c07c18b71c8bb9087c526b705eb6b`, and the uncorrected candidate source is
`3bd085968d6f1a9e08b1bf5f58aaa4af75f1d81d1261e858b291d5c069d416dc`. The focused suite now has **29 pass, one
expected failure**; the marker must not survive the fix.
By 06:08 UK both original historical screens finished all four folds; the independent audit
`analysis/experiments/20261122_a1_s05_minutes_screen_accounting_uncorrected.json` verifies **21** input and
**16** output hashes. Their known regulation counts are **5,218 / 5,225 / 5,013 / 5,208** across F1–F4;
unknown-play counts are **2,205 / 2,164 / 1,387 / 2,109**. Flow reached **190/200 in 3,073 s** at that time and
has since completed. Normal and deliberate-fault smoke completed as recorded in live state; the original source is
preserved in commit `ab32eda`.
**New strict-candidate flaw, not in production:** `legal_minutes([48,48,48,48,47.9999,0])` gives the zero-minute
player **0.0000999998** minutes while an already-positive player has room. As target-play probability counts every
positive draw, strict/combined target-play Brier results are artificially altered; do not treat them as a gain.
The working candidate has since been repaired to use already-positive headroom first, retaining zero targets unless
they are needed for legal conservation. The working regression now passes without `expectedFailure`; all **30**
focused tests pass, and **400** absence cascades conserve to `1.14e-13`. Corrected conditional F1–F4 and both
corrected F1 historical screens are complete; F2–F4 remain underway above. F1 no-report strict and control
target-play Brier are both **0.1211569**; prior strict/combined Brier and coverage must not be used. Control and
NBA-only outputs are reproduced to `1e-12` for all **7,423** F1 candidates. This is not a production model change.
Independent conditional accounting `analysis/experiments/20261122_a1_s05_minutes_conditional_accounting_corrected.json`
reconciles all **17,303** participant rows, **11** control/NBA-only columns, **13** corrected input hashes and
200 fixed games/400 team-sides per fold; strict mean conservation is within `3e-13`. This does not score availability.
Independent out-of-order S03 evidence is already retained in
`analysis/experiments/20261122_a1_s03_variant_components.json`: on the original shared-pool comparison, v1.4c/e/f
increase total points by **+0.996 / +0.893 / +0.411** per game; field-goal, residual, pace, FTA and rebound changes
are recorded in FINDINGS §6b. The old same-seed wording meant game selection, not the version-dependent simulation
streams.

**History retrieval completed:** nine batches of **363/363** and a final **355/355** retained all **3,622/3,622**
original items, with no empty responses. Final log `/tmp/musnba_a1_s02_pbp_10.log` reports 355 requests, 5,162 cached,
5,518 logged games and 0 empties; the stream has exited. The independent all-source inventory
`analysis/experiments/20261122_a1_raw_inventory_completed.json` verified all **5,517/5,517** eligible logged game
IDs across five seasons, with zero missing/unindexed/corrupt/hash-mismatched manifest files. **45** older entries still
lack original URL/time. Future provider access remains one stream, paused during the final nightly.
The original isolated F4 node-cache accounting completed all 16 datasets,
log `/tmp/musnba_a1_scheduled_f4_nodes_audit.log`, report
`analysis/experiments/20261122_a1_scheduled_F4_nodes_accounting.json`. The separate F4 wiring-only model fitting and
three-game/20-world test completed in **325 s**, log `/tmp/musnba_a1_s02_causal_wiring.log`:
`.venv/bin/python -u scripts/backtest.py --config models/a1_s02_f4_causal.json --fold F4 --games 3 --worlds 20
--jobs 1 --threads 8 --rotation targets --pool 0 --known-starters --name a1_s02_causal_wiring`. Its scores are
not selection or promotion evidence. Run `20261122T041531Z_a1_s02_causal_wiring`; independent accounting
`analysis/experiments/20261122_a1_s02_wiring_accounting.json` checks **24** quarter scores, **63** player 3PM
outcomes and **6** team sums with zero mismatches, and hashes the unchanged inputs and fitted models. Its original
run log's `commit` is Git HEAD, not the dirty working-tree source; use the accounting fingerprints.
**Corruption fix and rebuild:** five synthetic bad fitted schedules (a `NaT` cutoff, non-finite match/propensity/fill
values and a missing fill) were accepted on the old source, now all rejected. Dates must be complete valid ISO dates,
and fitted parameters must be present and finite. The accepted engine does not use this candidate-only schedule.
All **46** focused A1 tests pass. Original source/evidence was committed in **6ec31d6** before the fix. The guarded
30-fit, four-fold schedule is built under `data/derived/variants/a1_assignment_schedule_20261122_v3/`, with report
`analysis/experiments/20261122_a1_assignment_monthly_schedule_v3.json` and source hash `70bbb3f...`.
Four isolated feature builds completed **sequentially** in **60 s**, log `/tmp/musnba_a1_features_guarded.log`;
command for each `F1`…`F4`:
`.venv/bin/python -u scripts/features.py --out data/derived/variants/a1_scheduled_FOLD_20261122_v3/features
--defence --defence-k-scale 0.2 --shot-types --causal-first-priors --causal-positions --history-only
--matchup data/derived/variants/a1_assignment_schedule_20261122_v3/FOLD.json
--base-pregame data/derived/variants/a1_causal_base_20261122_v4/features/pregame.parquet`
(replace both `FOLD` occurrences). Guarded parity reports `analysis/experiments/20261122_a1_scheduled_F*_parity_guarded.json`
again match **304,175/304,175** sampled comparisons. The guarded F4 node cache build completed in **62 s**, log
`/tmp/musnba_a1_nodes_build_guarded.log`:
`.venv/bin/python -u scripts/nodes.py --features data/derived/variants/a1_scheduled_F4_20261122_v3/features/pregame.parquet`.
The first accounting attempt correctly failed because that cache had not been built; after the build,
`.venv/bin/python -m scripts.a1_node_cache_audit --features data/derived/variants/a1_scheduled_F4_20261122_v3/features/pregame.parquet
--fold F4 --output analysis/experiments/20261122_a1_scheduled_F4_nodes_accounting_guarded.json` passed for all
**16 datasets / 17,814,437 rows**. Matched-seed model fitting and three-game wiring completed in **324 s**,
log `/tmp/musnba_a1_wiring_guarded.log`:
`.venv/bin/python -u scripts/backtest.py --config models/a1_s02_f4_causal_guarded.json --fold F4 --games 3 --worlds 20
--jobs 1 --threads 8 --rotation targets --pool 0 --known-starters --seed-key a1_s02_f4_causal_diagnostic_F4
--name a1_s02_causal_wiring_guarded`. Run `20261122T043405Z_a1_s02_causal_wiring_guarded` independently accounted
**24** quarter scores, **63** player 3PM outcomes and **6** team sums and matched the pre-guard run to `1e-12`
(`analysis/experiments/20261122_a1_s02_wiring_accounting_guarded.json`). Its Git HEAD is the partial checkpoint;
the accounting fingerprints pin the actual dirty source, which must be committed with S02.
The guarded real-slice injection report `analysis/experiments/20261122_a1_future_injection_guarded.json` again
preserves **3,098** earlier values while changing **42** shot and **47** minute/position later values. The partial
checkpoint's fresh smoke passed **102/102**; deliberate `--fault` exited 1 as intended (**80/102** passed after
injected corruption). After the guarded source changes, the final smoke passed **102/102** and the deliberate fault
exited 1 with **80/102** checks passing, as required. The wrapper exited successfully; logs are
`/tmp/musnba_a1_s02_guarded_smoke.log` and `/tmp/musnba_a1_s02_guarded_fault.log`. No S02 job is running.
Independent split-candidate accounting on the fixed 200 games checks **4,349 player-games**, **47,775** event labels,
**44,863** five-player shooter-choice groups and **35,397** shot-result labels with zero mismatches; **70** segments
are quarantined (`analysis/experiments/20261122_a1_split_feature_nodes_200.json`). This is not an accuracy result.
The isolated F4 assignment preprocessing audit finished (`/tmp/musnba_a1_assignment_f4.log`):
`.venv/bin/python -u -m scripts.a1_assignment_audit --through 2025-12-31 --holdout-to 2026-04-30
--output analysis/experiments/20261122_a1_assignment_f4_preprocessing.json
--model-output data/derived/variants/a1_assignments_20261122/F4.json`. It loaded **1,261,174** historical segments
and selected **195,228** usable training / **35,216** held-out credited events. With the same fitted parameters,
holdout full log likelihood changed **−1.54375→−1.54347** when preprocessing used training rather than held-out
statistics; top-1 on 2,608 on-ball credits was unchanged at **25.92%**. The fit uses the isolated causal-base
profiles; body-measurement as-of provenance remains unproven, and the dated candidate must not be used before
2026-01-01. It is not a promotion or a free-running engine-accuracy test.
F1–F3 have now also been fitted through their own training cutoffs: **78,311 / 135,404 / 172,166** usable
training credits and **33,476 / 34,586 / 23,062** held-out credits, respectively; evidence is
`analysis/experiments/20261122_a1_assignment_f{1,2,3}_preprocessing.json` and isolated models are under
`data/derived/variants/a1_assignments_20261122/`. They remain invalid before their own `valid_from` dates. A
body-free F4 experiment omits the later roster/athlete measurements entirely in training and assignment, leaving
the height-gap feature missing. On the same **35,216** held-out credits, body-included versus body-free log
likelihood is **−1.54347 vs −1.54611** and on-ball top-1 is **25.92% vs 24.88%** over 2,608 credits
(`analysis/experiments/20261122_a1_assignment_f4_bodyfree.json`). A future-body-injection test passes. These are
isolated diagnostics, not a promotion or a fully verified end-to-end pipeline.
The later isolated base `data/derived/variants/a1_causal_base_20261122_v4/features` uses positions observed strictly
before each game date. It contains **111,075** rows and **891** unknown position rows; all **877** players' first
observations are unknown. Original source publication/revision timing remains unverified. Monthly body-free θ fits
now select only fits valid for each historical date and freeze at each fold cutoff; 30 fits and four schedules were
written in **22.1 s** to `data/derived/variants/a1_assignment_schedule_20261122_v2/`, report
`analysis/experiments/20261122_a1_assignment_monthly_schedule_v2.json`. Four isolated scheduled feature builds are
complete under `data/derived/variants/a1_scheduled_F{1,2,3,4}_20261122_v2/features`. The candidate also replaces
whole-dataset relative-profile median fills with lineup-local fills, preserves all-missing values, and uses the same tie-symmetric ranks in nodes and the engine. The final sampled F1–F4 parity
reports `analysis/experiments/20261122_a1_scheduled_F{1,2,3,4}_parity_v3.json` match **304,175/304,175**
matchup, lineup and relative-input comparisons, excluding **36** actor/lineup mismatches. This compares sampled
calculations, not every model input or historical publication timing. The complete isolated F4 `nodes.py` chain
built **16/16** datasets in **59 s**, using a **9.1 GiB** variant cache
`data/derived/nodes/variant_9813f970d51d`; independent accounting found **17,814,437** rows and passed label,
shape and candidate-group checks. On a five-game real slice with explicitly isolated on-court inputs, injected
same-day/future shots and minutes left **3,098** earlier player/team feature values unchanged while changing **42**
later shot-derived and **47** later minute/position-derived values
(`analysis/experiments/20261122_a1_future_injection_real_slice.json`). Fourteen focused causal tests passed,
including real `Models` loading with a mock booster, cutoff rejection, schedule tampering and missing-profile
behavior; the real fitted models also completed the wiring test above. The legacy production path is unchanged.
Smoke after the isolated
engine changes passed **102/102**, including a bit-for-bit v1.3 stored-game replay.
The original-stream regeneration completed as
`20261122T022323Z_a1_s01_control` in **1,567 s**; independent seed `20261122T025114Z_a1_s01_seed2` completed in
**1,566 s**, with log `/tmp/musnba_a1_s01_seed2.log`. Their independent accounting and paired-noise reports are
`analysis/experiments/20261122_a1_{control_accounting,seed_accounting,seed_noise}.json`. Existing serving artifacts are not touched. Review/test
servers are closed; owner's :8766 remains untouched.
At the S01 checkpoint after the type-only annotation, smoke passed **102/102**, `--fault` deliberately failed **22**
checks (exit 1), all **15** focused A1 tests passed and the local bundle hash remained `3055d277...e5abd9ecf`.
All eight root docs were reviewed: AGENTS needs no further change because its scoped overnight authority is already
in `c6d5db4`; ENGINE and DASHBOARD only need status updates because no model design or app behaviour changed.
Before the active batch, **1,895/5,517** logged games dated before ET 21 Nov were retained; **3,622**
remained, including 235 current-season games. **45** retained manifest entries lack their original URL/fetch time.
Do not invent those fields. All eight 2022–26 hoopR parquets match their manifest hashes/bytes; ESPN game
`401810469` has 25 player-box rows but no retained hoopR play-by-play, while mapped NBA play-by-play `0022500614`
is retained. Investigate rather than inventing the missing ESPN events. Start your own :8767 server for checks.
`analysis/experiments/20261122_a1_raw_inventory.json` verifies all **10,094** retained NBA manifest entries and
files: no unindexed, missing, corrupt or hash/size-mismatched gzip; 45 lack acquisition metadata. The 236 current
ESPN final summaries have no per-file acquisition/hash manifest.
S02 also found five null-ID "matches" in the retained player crosswalk; the corrected code and regression test exclude
them, and a **temporary** full rebuild reports **118,220/118,242** matched player-games, with **22** unmatched
appearances for one player. The production mapping has not been overwritten. The completed-game
`analysis/experiments/20261122_a1_reconciliation.json` lists per-season points/seconds/possessions and excluded games;
all **118,187** known mapped player-point pairs agree, with **13** missing ESPN values.
`analysis/experiments/20261122_a1_rotation_integrity.json` audits recorded no-sub/multiple-sub windows and early matchup
attempt duplication: all five season window counts reconcile, but 22 repeated-entering rows and unclassified stoppages
need review before substitution training. Early matchup FGA / box FGA is 1.1163 / 1.1120; identical pair keys are not
duplicated. In `401810498` Q4 0:33.3, source sequence 709 occurs at home margin −3 but the stored grouped window
labels it −4 after a later free throw; repeated entrants at that clock are separated by a reversal. S06 needs
sequence-aware pre-substitution state rather than treating a clock group as one simultaneous opportunity.
The tracking audit covers all but one retained logged date per category, but **8,637/113,089** Overall rows disagree
with the dated NBA game-log team. Use the latter on a person/date join, never `PLAYER_LAST_TEAM_ABBREVIATION`; the
three categories have different attempt-column names. See `analysis/experiments/20261122_a1_tracking_coverage.json`.
Segment-start lineups are also stale after substitutions within an action-free segment: **14,235/1,216,437** known
actors across five reconciled seasons are absent from their recorded offensive lineup
(`analysis/experiments/20261122_a1_lineup_integrity.json`). A non-production `--split-substitutions` candidate splits
only action-free segments, preserves possession IDs/points/period time, and flags unresolved lineups; candidate
player features and node datasets quarantine flagged rows. On the fixed 200 F4 games, actor absence fell **489→6**
and median segment-v-rotation seconds discrepancy **13→0**, with all source replays and event identities equal.
**70** candidate segments are quarantined, 57 for rebounder-lineup conflicts, including subs after an and-one shot
before its missed free throw/rebound. Evidence: `analysis/experiments/20261122_a1_subsplit_quarantine_f4_200.json`.
This is a data-quality pilot, not an engine accuracy test, promotion, or proof all substitution situations are fixed.

An isolated historical base build at `data/derived/variants/a1_causal_base_20261122_v2/features` implements
first-season player/team priors from strictly earlier dates, same-day-safe decays/rest, and missing priors as missing;
it contains **111,075 player-games, 5,196 games**, through 13 Jun 2026 only. Its report hashes code and inputs.
Independent accounting `analysis/experiments/20261122_a1_causal_base_accounting.json` finds **zero** later-season
differences across 38 shared player and 14 team columns on **83,797** player rows; the first day's 45 player rows
have no invented usage prior. Synthetic same-day/future injection tests pass. This does **not** make assignment
fits, body measurements or the complete pipeline cutoff-safe. `matchups.mu_columns` has an opt-in
`missing_policy=retain_missing` candidate that keeps an all-missing five missing rather than borrowing unrelated
batch rows; legacy serving remains unchanged. On three fixed F4 games, after excluding 10 actor/lineup mismatches,
**4,753/4,753** shared matchup values agree (`analysis/experiments/20261122_a1_matchup_parity_after.json`).

**Last dashboard-delivery checks:** smoke **102/102**; deliberate `--fault` fails **22** checks (exit 1); full browser sweep **156/156**, then
**12/12** targeted cases for the final phone stacking correction; hosted PWA **15/15** (import, phone stacking, offline
sections, dynamic counts/qualifiers). macOS atomic export visibility regression passes. Real iPhone installation/import
still needs owner acceptance; iCloud file delivery itself is confirmed.

**Owner preferences from the dashboard chunk:** season insights belong inside Standings; comparable card groups come in
multiples of three (Leaders: 9 player + 6 team cards); changing copy/counts/dates/qualifiers/model labels must derive from
loaded data/configuration. Phone can stay stripped back (D36). The earlier D39 history design is now deferred by D40;
existing generations remain archived and the active session stops after the current nightly (D41).

**Root-doc review for the pending partial checkpoint:** HANDOFF, PLAN, FINDINGS, TRAINING and README record the
candidate work and commands; ENGINE corrects D38's stale planning-session wording. AGENTS needs no change because
the scoped overnight authority is already recorded; DASHBOARD needs no change because no app or served output changed.

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

## Execution — two chunks (D42)

The owner asked for the remaining work to be split into two outcome-led chunks and suggested five meaningful saved
games per matchup, and has now authorised execution in order. S01–S07 and their
evidence remain complete; preserve the original A1 table/weights/ladders below as the historical accounting. The new
chunk weights are **separate within-chunk progress measures**, not replacements for or double credits to A1: original
A1 stays **58.0%**, and S13 remains deferred at 0% (the possible A1 ceiling while deferred is 95%).
Update the original S08–S12/S14 status only when their original acceptance is met, without crediting work twice.
Report a chunk bar and each active module at every 10% rung and each 5% overall boundary; long jobs also report
item counts and measured rates. Current Chunk A progress is **34.5%**; Chunk B remains **0%**.

**Shared gates:** use the unchanged player-first, paired fold, seed-noise, uncertainty, non-inferiority, cutoff and
once-per-version final-test rules in PLAN §6b/TRAINING_PLAN §8. An early chunk can promote a standalone candidate
only after those applicable gates, with pathway v1 retained and integrated interactions assessed later; otherwise
keep the accepted model. Every completed module gets evidence, docs, checks, review, commit/push and a short owner
summary. A measured negative result is valid; unfinished work or an unrun test is not a pass. At each affected
model/output/app checkpoint refresh/export/publish and verify PWA compatibility; research-only checkpoints say the
served data are unchanged. Each development chunk ends with its own fresh live nightly, 10k game/season worlds,
delivery checks and a useful shipped dashboard improvement if no model is promoted. Historical forecast backfill
stays deferred; per-game iCloud streaming is separate future work, not assumed implemented.

### Chunk A — believable individual games and visible simulations

Headliners: (1) lineup-aware player/game distributions and realistic game-state response; (2) a 2-D View Centre
for five meaningful saved simulation examples per near-term game. Depends on completed S01–S07. A1 original scope: S08, S09 and the
playback portion of S12, plus a chunk-end delivery; S10/S11/S12/S14 are not thereby marked complete.

| Module | Weight | Dependencies | Acceptance / fallback |
|---|---:|---|---|
| A1 Lineups and Expected | 30% | S05–S07 | S08's exact branch/season identities and origin safety, or explicit blocked limitation; no invented availability calibration |
| A2 Form and late-game realism | 35% | S04/S06; A1 for integration | S09's paired player/game gates; retain v1.3 when unsupported or rejected |
| A3 View Centre and delivery | 35% | A1/A2 decisions | Five labelled selections, reconciled event files and an interactive 2-D court/player in the Game Centre; responsive/offline checks and fresh nightly; no fake logs or completed claim on failure |

**Live board:** Chunk A `███████░░░░░░░░░░░░░ 34.5%`; A1 `████████████████░░░░ 80%`;
A2 `██████░░░░░░░░░░░░░░ 30%`; A3 `░░░░░░░░░░░░░░░░░░░░ 0%`.
Original A1 remains 58%; do not double-count the separate board.

**A1 10% frozen branch contract (22 Nov; selection superseded by D46):**

**D46 selection revision:** at most one uncertain player per team, only if among that team's top three by the
labelled pre-origin offensive-contribution proxy in ENGINE_PLAN D46. Rank the whole origin roster including
ruled-out players; retain the highest-ranked eligible uncertainty per side. The earlier threshold and >2 selection
below are historical, not the current rule. Branch weights are still uncalibrated and independence unvalidated;
other uncertain players retain their existing per-world draws. Do not change any served model or snapshot yet.

- Use the origin's own roster, reported status, source, effective `projection.player_inputs` availability and
  pre-origin D29 state/profile. Select every uncertain rostered player (`0 < availability < 1`) whose healthy
  role is at least 15 minutes or whose prior usage is at least 0.25. When either role or usage is missing and the
  other does not establish eligibility, include the player conservatively and flag the missing criterion. This
  explicit engineering threshold is not a validated importance model. Include unknown-status and recent-inactivity
  fallbacks when they qualify; label cold-player prior roles rather than claiming observed history. Unlisted Active
  is an assumption, not a reported healthy status. Out players stay out. Sort selected players by `(team ID,
  player ID)` as strings, not roster order.
- A branch ID is `lineup-v1:` followed by sorted `team_id/player_id=plays|sits` assignments separated by commas;
  persist the structured assignments too. Require nonempty ASCII digit team and player IDs and reject duplicates
  or ambiguous IDs; never use an untrusted ID directly as a path. Derive a deterministic seed with
  `projection.seed_for('lineup-v1', engine ID, origin, slate date,
  game ID, branch ID)`; record seed, version, world count, branch assignments, source/capture provenance and hashes
  of the exact model and pre-origin input artifacts. Same assignments and inputs must reproduce regardless of worker
  count. A branch fixes its selected players' availability before re-solving starters, minutes and matchups;
  other players retain the existing per-world availability policy.
- For one or two selected players enumerate every plays/sits assignment and weight it by the product of their
  effective fixed fallback probabilities or complements. These weights are **uncalibrated**; for two players their
  independence, and the engine's treatment of other availability, are unvalidated assumptions. Use exact decimal
  or rational arithmetic for branch probabilities and verify the sum; do not silently renormalise missing branches
  or activate an ineligible player. An impossible five-player world fails explicitly.
- With more than two selected players, store an all-play reference and each one-out-alone sensitivity with every
  other selected player forced to play. These are **non-exhaustive conditional comparisons**, not weighted
  forecasts or an Expected mixture. Until an exhaustive supported mixture is available, retain and label the
  current unconditional forecast; never imply those sensitivities add to one or cover joint absences.
- A supported Expected distribution is the weighted empirical distribution of **all 10,000 worlds in each
  exhaustive branch**, not a third simulation or a rounded 10,000-world subset. Store weights and provenance;
  phone export keeps Expected only. The season must consume the same near-term mixture once per game with exact
  weighted accounting. A 10,000 equally weighted season array cannot in general represent it (FINDINGS §7);
  weighted/expanded representations and their runtime must be validated before acceptance. Do not claim this is
  solved, round it away, or promote a partial implementation.

**A1 20% foul-out repair protocol (22 Nov, before the candidate):** in an opt-in branch-only policy, repair each
scheduled five by replacing any unavailable or six-foul player with the available, not-disqualified teammate
outside that five with the largest existing D29 expected minutes, breaking ties by the engine's existing player
order. A team with fewer than five legal available players fails explicitly; no NBA short-roster technical exception
is claimed. After a sixth foul, update that world's affected five before free throws and later segments. Extend
the existing policy hook with a per-active-world changed mask, preserving the existing boolean-policy and
no-policy paths; recompute lineup-dependent context and player columns only for masked worlds. An unsupported
mismatch-feature combination must fail explicitly rather than use stale columns. Shared vectorised random streams
can still diverge after changed event counts; do not claim independent unaffected whole-game worlds or paired
common-random-number semantics. Test exact no-policy/legacy-policy behaviour, both offense/defense sides, repeated
scheduled disqualifications, multiple worlds, unavailable/short rosters, context isolation and independent legal
five/score/minute accounting. Before any branch claim, run the same fixed F4 game **401810327**, **32** worlds per
plays/sits branch and frozen seeds, with independently recorded trace; the active D44 nightly must finish before
editing `engine.py` or starting this engine replay. A passing probe is wiring evidence, not a promotion gate.
**Partial implementation:** `scripts/a1_branch_foul_out.py` repairs only illegal fives, returns a world-local
mask and fails closed on short rosters. Branch tests cover offense, defense, simultaneous repairs and unavailable
players. The now-implemented hook is reachable only through an explicitly selected policy; it preserves legacy
booleans and no-policy behavior, updates only changed worlds, and rejects mismatch features for mask changes.
The fixed repair probe below is the next step; no model or rotation policy has been promoted.

| Rung | A1 — lineups and Expected |
|---:|---|
| 10 | Freeze branch IDs, uncertain-player selection, provenance and independence caveats. |
| 20 | One-player plays/sits branches re-solve minutes and defence with valid five-player lineups. |
| 30 | Two-player branches and explicit >2-maybe non-exhaustive handling pass probability checks. |
| 40 | Deterministic 10k worlds per supported branch persist with seeds and inputs. |
| 50 | Expected distributions preserve exact branch weights; handle the 10k indivisibility counterexample explicitly. |
| 60 | Season consumption preserves the documented weighted identities without duplicate near-term games. |
| 70 | Missing status, unsupported dependence and cold rosters are visibly labelled or fail explicitly. |
| 80 | Local/laptop branch UI and phone Expected-only compatibility pass focused tests. |
| 90 | Representative-game accounting, restart, cutoff, runtime and responsive checks pass. |
| 100 | Results/limitations and any required PWA refresh are verified, committed/pushed and summarised. |

| Rung | A2 — form and late-game realism |
|---:|---|
| 10 | Quantify residual player/team covariance after role and minutes, with supported cohorts. |
| 20 | Freeze earlier-fold talent/form hypotheses and no-double-count controls. |
| 30 | Implement isolated player uncertainty draws with mean and deterministic-stream checks. |
| 40 | Test shared pace/shooting factors and realistic teammate/opponent dependence on folds. |
| 50 | Audit end-game fouls, clock, shot selection and overtime by supported historical states. |
| 60 | Test supported state corrections against fixed earlier-fold controls; retain explicit missing cases. |
| 70 | Run sequential paired player-first engine screens; report CRPS, bias, coverage and joint metrics. |
| 80 | Test surviving combinations and seed sensitivity; reject variants failing registered bounds. |
| 90 | Record a promotion/no-promotion decision with all applicable confirmation and cutoff gates. |
| 100 | Evidence, fallbacks and required PWA delivery are verified, committed/pushed and summarised. |

| Rung | A3 — five games, View Centre and delivery |
|---:|---|
| 10 | Freeze selection, event-file schema, provenance, source-neutral simulated/actual boundary, spatial honesty and data budget. |
| 20 | Select each team's maximum score-margin and highest individual fantasy-score worlds from actual saved worlds. |
| 30 | Select one representative expected-outcome world using a documented, predeclared multi-stat distance. |
| 40 | Preserve five labelled selections and validate local event-file loading, missing/invalid data and synthetic future-source contracts. |
| 50 | Capture or deterministically replay selected events with exact batch/seed/model/input/branch provenance, without changing simulation draws. |
| 60 | Independently reconcile clocks, scores, periods, player boxes, legal lineups and event order with source worlds. |
| 70 | Ship a stored-only View Centre: overhead court, supported event overlays, score/box, event list and playback controls. |
| 80 | Verify smooth playback, seek, reduced motion, accessibility, both themes/three widths, phone budget and offline import. |
| 90 | Run a fresh live 10k nightly on accepted systems, verify each slate's selections and iCloud/PWA delivery. |
| 100 | Publish any data-free shell, document findings/limitations and next chunk; review, commit/push and summarise. |

### Chunk B — stronger defence and reliable season paths

Headliners: (1) player/lineup defence and legal game-state mechanics; (2) calibrated season paths and integrated
confirmation. Depends on Chunk A's decisions and delivery. A1 original scope: S10, S11, remaining S12 and S14;
the additional defence/foul-out work follows S03/S04/S06 evidence without reopening rejected variants unchanged.

| Module | Weight | Dependencies | Acceptance / fallback |
|---|---:|---|---|
| B1 Defence and foul-outs | 30% | Chunk A, S03–S06 evidence | Test new player/lineup mechanism and the observed foul-out defect; unchanged gates, explicit rejection if unsupported |
| B2 Season pathway | 30% | Chunk A; S07 evidence | S10's 16-origin, per-date paired calibration and exact near-term-world accounting; retain pathway v1 if rejected |
| B3 Integration, visibility and delivery | 40% | B1/B2 decisions | Full S11 confirmation or recorded rejection; rotation-map dashboard improvement, S12/S14 checks and fresh nightly |

| Rung | B1 — defence and foul-outs |
|---:|---|
| 10 | Reproduce the six-foul mask defect and freeze legal-five/short-roster rules and baseline fingerprints. |
| 20 | Isolate a foul-out candidate and independently reconcile substitutions, penalties and preserved valid streams. |
| 30 | Specify a new evidence-backed player/lineup-defence hypothesis and prior-only fold data; do not repeat rejected variants. |
| 40 | Audit defender coverage, cutoffs, missingness and fitted-artifact provenance. |
| 50 | Run frozen node-level fold ablations and reject mechanisms without a supported gain. |
| 60 | Backtest surviving mechanics/defence candidates sequentially against matched player-first controls. |
| 70 | Stress foul-outs, overtime and short rosters; reconcile player/team points, seconds and eligible fives. |
| 80 | Measure player tiers, defensive expression, margins and non-inferiority with paired uncertainty. |
| 90 | Confirm or reject each candidate under the unchanged gates; record unsupported comparisons and runtime. |
| 100 | Evidence, fallback and any required delivery are checked, documented, committed/pushed and summarised. |

| Rung | B2 — season pathway |
|---:|---|
| 10 | Reconcile pathway-v1 baseline, schedules and Cup accounting across all 16 historical origins. |
| 20 | Build strictly prior carry-over/opponent-adjusted starting-rating candidates. |
| 30 | Screen start ratings by leave-one-season-out, including November cold starts. |
| 40 | Test memory/gain/drift against persistence without biased per-world rating updates. |
| 50 | Assess absence-path support; retain no-future-absence fallback when historical evidence is insufficient. |
| 60 | Consume accepted near-term Expected worlds once per game with validated mixture accounting. |
| 70 | Run eligible candidates on all 16 origin combinations at 10k worlds. |
| 80 | Report paired CRPS, dispersion, coverage and persistence by origin with uncertainty. |
| 90 | Select or reject pathway candidates and freeze interactions for integrated confirmation. |
| 100 | Results, limitations and any affected PWA delivery are checked, committed/pushed and summarised. |

| Rung | B3 — integration, visibility and delivery |
|---:|---|
| 10 | Freeze candidate/control manifests and explicit B1/B2 retain/reject decisions. |
| 20 | Screen combined effects and component removals on the fixed player-first F4 population. |
| 30 | Confirm a survivor on all eligible F4 and fixed F1–F3 samples, or record the failed gate. |
| 40 | Verify second-seed, 10k subset, legal-five, cutoff, accounting and runtime gates or document rejection. |
| 50 | Score only a frozen qualifying new version once on the final test; otherwise retain accepted systems. |
| 60 | Derive stored rotation probabilities summing to five and build the responsive rotation-map view. |
| 70 | Verify playback/rotation labels, missing/legacy states, offline import, bundle size and screenshots. |
| 80 | Run the final fresh live 10k nightly, audit outputs and deliver the iCloud bundle/data-free shell. |
| 90 | Update all affected docs and construct the next chunk with headliners, weights and ten-rung ladders. |
| 100 | Finish smoke/fault, PWA and accounting checks; review, commit/push and summarise outcomes and limitations. |

For each chunk, mark rejection-path rungs with the actual reason, never as passed. Selection examples are conditional
extremes of the 10k simulations, not likely outcomes; exact ties use a frozen deterministic rule. “Best team game”
means largest own score margin, even if every simulated game is a loss; “highest player fantasy” means maximum single-player NBA fantasy score for that team
(PTS + 1.2 REB + 1.5 AST + 3 STL + 3 BLK − TOV). The representative world must be a real world selected by a
predeclared scaled distance to Expected team/player outcomes, with missing/zero-variance handling specified before
selection; it is not a fabricated average game. Reusing an identical selected world for multiple labels is honest.
If source worlds cannot be reproduced with complete events, report the blocker rather than manufacture a replay.
The phone contract remains Expected-only for distribution/branch tools; compact playback is included only after
measured size and offline checks, and any limitation is visible.

**View Centre design (D43; future implementation):** use one source-neutral renderer and event-player interface
with explicit source kind, game/world identifiers, period, remaining clock, stable event order, participants/team,
event type, score changes, available on-court players, spatial precision and provenance/version. Load the selected
saved worlds from Game Centre and allow a validated local play-by-play file to be opened without uploading it or
overwriting saved forecasts. An invalid, unsupported or incomplete file gets a clear error or labelled incomplete
state. Simulated-world files and later resulted-game files have distinct source labels; never treat actual results as
pre-game forecasts. Future actual-game adapters may use retained ESPN play-by-play and preserve source identity,
clock/order, revisions, missing coordinates and reconciliation gaps; actual-game playback itself is not part of this
planning session or promised by Chunk A. D40's forecast-backfill deferral is unchanged.

Render a responsive overhead SVG court with period/clock, current score, cumulative box, on-court names when known,
ordered event list and overlays for recorded shot zone/band, makes/misses, fouls, rebounds, turnovers and substitutions.
Use play/pause, speed, scrub, step/event selection and quarter/OT jumps; transitions are smooth, deterministic and
respect reduced-motion settings. Compress idle time as an explicit playback mode, while preserving event order and
the recorded game clock. Update the active frame without repeatedly rebuilding the entire event list; release timers
when the view closes. Seeking and resuming must reproduce the same state and never show future events.
This is an event replay, not player-tracking footage: current simulated shots use a **zone and distance band**, not
continuous player/ball coordinates. Highlight the supported region or label any decorative placement as illustrative;
never imply inferred player movements, exact shot locations or passes were simulated. Actual x/y, if present and
validated later, are provider-reported shot coordinates, not full player tracking. Missing spatial or lineup data
remain visibly missing; timeline/box replay still works where supported. MusSim's `scripts/webapp/match-centre.mjs`
is prior art for a court/pitch, event cutoff, controls and honest coverage—not a claim that it already animates players.

The current engine batches worlds with a shared random stream: replaying only one world with the original seed is
not assumed equivalent. Capture selected events without changing draws, or rerun the original batch with its exact
world count/order/inputs and verify all relevant outputs; compare runtime and bundle size before choosing. Five
selection labels can share one event file; do not capture all 10k event logs by default. Import, rendering and
browsing never fetch, fit or simulate. Validate file structure/size and version before using it, preserve old
snapshots, and test timer cleanup, repeated seeks, period/OT transitions, simultaneous events and truncated inputs.

## Progress ladders — A1 overnight execution

**Headliners:** player accuracy (including defence, roles and responsive minutes); calibrated games/seasons.
Historical forecast replay is deferred (D40). Scope/dependencies: PLAN §6a. Acceptance: PLAN §6b, TRAINING_PLAN §8.
The owner now requests a stop after the active nightly (D41); unfinished tasks remain future work.

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
| S02 Data integrity and parity | 6% | 100% | History, integrity, guarded parity/wiring and smoke/fault checks complete; research-only checkpoint |
| S03 Offence/defence signal diagnosis | 8% | 100% | Fixed matched flow/accounting, component decomposition and two falsifiable candidate families documented; research-only checkpoint |
| S04 Defence and shot quality | 12% | 100% | Both families rejected at their frozen node gates; tracking rebuild and independent accounting verified; served model and bundle unchanged |
| S05 Roles and minute allocation | 8% | 100% | Both matched screens and independent accounting complete; neither passes pooled MIN gate, retain D29 control; smoke/fault passed |
| S06 Game-state substitutions | 12% | 100% | Fixed 200-game screen and state replay audited; D29 retained because 3 non-inferiority bounds remain unestablished; smoke/fault passed |
| S07 Availability and future absences | 6% | 100% | Fixed uncalibrated status/starter fallbacks retained; no future absence hazard; corrected origin/report/timing delivered and independently audited |
| S08 Lineup branches and Expected | 6% | 0% | Planned |
| S09 Shared form and end-game behaviour | 10% | 0% | Planned |
| S10 Season pathway calibration | 8% | 0% | Planned |
| S11 Integrated confirmation/promotion | 5% | 0% | Planned |
| S12 Model behaviour in the dashboard | 3% | 0% | Planned |
| S13 Current-model season history | 5% | 0% | Deferred by owner D40; no progress credit |
| S14 Nightly, delivery, successor | 5% | 0% | Planned |

**A1 overall: `███████████░░░░░░░░░ 58.0%`.** Both control seeds are complete; isolated assignment-event
diagnostics and three-game wiring are not engine-accuracy tests. No model candidate has been promoted;
S07's provenance/timing repair and new forecast bundle are delivered.
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
| 70 | Phone receives compact summaries/list only where size permits; world tools stay off the phone. Laptop PWA retains saved worlds (D45); branches remain planned. |
| 80 | Touched routes pass 1440/960/390 in both themes; screenshots are actually inspected. |
| 90 | Offline/import and old-snapshot fallbacks pass; limitations and shipped behaviour are in DASHBOARD_PLAN. |
| 100 | App/output changes are exported and the changed shell published/PWA-checked; docs committed/pushed; owner gets the feature summary. |

### S13 — current-model season history and daily archives (5%)

**Deferred at 0% by owner D40.** The original ladder is retained for a future reauthorisation, not a current work
queue; no rungs or weight are redistributed or credited.

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

If reauthorised, S13's default dashboard history uses the current accepted version. Historical recipes and reconstructed reports are
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
are counts over the worlds. The app slices the engine's stored worlds for joint and conditional outcomes (localhost and laptop PWA; the
phone bundle is stripped back, D36).

## State

**Current delivery (22 Nov, 12:39 UTC):** the requested live nightly completed successfully, using ESPN registry
`20261122T115324Z` and rebuilding **241** pre-origin games, **59,803** segments and **26,308** stints in **230.9 s**.
The 22/23 Nov ET slates contain **7/10** games, **10,000** worlds per game; the shared-origin future season has
**10,000** paths over **959** games. Both snapshots use origin **2026-11-22**, cutoff **2026-11-21**, and completed
pre-tip for all **17** games. The independent audit
`analysis/experiments/20261122_a1_s07_live_snapshot_audit.json` reconciles **599** origin-report entries,
**340,000** player/team-world point totals and **17** season/game identities; all **32** recorded input hashes
still match. These are provenance/accounting
checks, not a measured model-accuracy improvement. Engine **v1.3/D29** and **team-pathway-v1** remain accepted;
there is no supported future physical-absence model, and fixed status/start assumptions remain uncalibrated.

The iCloud bundle `~/Library/Mobile Documents/com~apple~CloudDocs/MusNBA/MusNBA.musnba.gz` was generated at
**2026-11-22T12:39:01Z**, has **1,999** records and **11,752,334** bytes, and SHA-256
`8f8026e7b01febbbf9416c23faaa1e794bd94a116e29d3c22b6e1513cb12579a`. All record hashes, current game
origin/cutoff/model/10k metadata, both season views and omission of phone per-world files were independently
verified. The data-free `gh-pages` shell is **f2932e1**, cache **0d7693ac00bad5eb2e00**, and the hosted
import/offline check passed **17/17** (`/tmp/musnba_a1_s07_pwa_hosted.log`); all eight changed hosted files
match the reviewed shell byte for byte. The bundle is readable in iCloud with its Finder-hidden flag clear,
but each device still needs manual import; no new phone import has been confirmed. Earlier snapshots, views,
bundle and shell remain archived under `~/Basketball_archive_ops`; the previous snapshot and bundle archives are
`archive_20261122T123805Z_37780` and `archive_20261122T123906Z_42352`.

Final checks: **12** focused timing/empty-score tests, normal smoke **108/108**, deliberate fault **86/108**
with exit 1 as expected, and **72/72** touched/live-slate browser checks; representative desktop/half/phone
screenshots in both themes were inspected. Logs: `/tmp/musnba_a1_s07_live_nightly.log`,
`/tmp/musnba_a1_s07_final_{focused,smoke,fault}.log`. Review/preview servers :8767/:8768 were stopped; the
owner's :8766 was not touched. No nightly, backtest or history job is left running by this session.

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
`gh-pages` at `f2932e1`, 24 data-free files (no simulation data). Hosted import/offline **17/17**, including phone layout. Model source stays on `main`;
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

## Next actions — Chunk A in progress

0. **A1 blocked fallback, before any A2/A3 or Chunk B:** the live 23 Nov slate now carries schema-1
   precise minutes and has passed independent accounting and hosted import/offline checks above. A real phone
   import and memory acceptance check remains manual. No normal route supplies precise *branch* worlds.
   Do not recover invented precision from retained legacy worlds. Reassess the failed 90% gate only with a
   materially new, preregistered candidate or representative pre-origin evidence, preserving cutoff,
   player-first fold and promotion rules. The owner requested a stop at the A1 boundary; this checkpoint is
   an explicitly blocked fallback, not a claim that the module or chunk has completed. To repeat the
   existing two-player probe, use
   `node --max-old-space-size=4096 analysis/a1_precise_minutes_probe.mjs data/derived/experiments/20261122_a1_live_branch_034_fixture_v1.json '{}' data/derived/experiments/<new-output>.json analysis/experiments/<new-probe>.json`
   then `.venv/bin/python analysis/a1_precise_minutes_audit.py analysis/experiments/<new-probe>.json --output analysis/experiments/<new-audit>.json`;
   use `'{"3149673":true}'` for the previously tested partial selection. Run
   `node tests/test_a1_precise_minutes.mjs` and `.venv/bin/python -m unittest tests.test_a1_minute_encoding_probe`.
   To independently repeat the production decoder audit, use
   `.venv/bin/python analysis/a1_production_minutes_audit.py data/derived/experiments/20261122_a1_live_branch_034_v1.json --output analysis/experiments/<new-audit>.json`.
1. **A1 90%:** continue from the audited 10k isolated-retry test in State. Independently verify representative
   branch accounting, source cutoff provenance and restart behavior; quantify runtime and rejection/selection
   bias on earlier folds. Do not equate its synthetic fixed-game benchmark with a
   representative development-fold failure-rate, a full-slate budget or a successful production gate. The completed scaling probe
   can be reproduced under a new filename with
   `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -u analysis/a1_parallel_world_scaling.py --pilot analysis/experiments/20261122_chunk_a_a1_d48_parallel_pilot20_v1.json --output analysis/experiments/<new-scaling-report>.json`.
   The retained
   20-world synthetic-rejection pilot is reproducible with
   `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -u analysis/a1_world_retry_probe.py --game 401810327 --worlds 20 --seed 20261122 --output analysis/experiments/<new-retry-report>.json`.
   It does not persist the full captures and does not prove a 10k runtime or real failure rate. The branch
   10k deterministic captures, isolated 200-world clean-stop/resume comparison, 200-game F4 exhaustion
   screen and independent audits are listed above. The targeted six-player stress has now identified
   **202** exhausted seeds in its selected F4 case; the S06 comparison is complete and independently
   audited, with different policies/paths and no isolated selection conclusion. Later matched continuations
   and actual retries quantify full-game differences under an explicit assumption in this selected case;
   the real-world bias and predictive effects remain unknown.
   All three earlier-fold conditional-roster screens and audits are complete. The selected full-game
   F4 comparison against S06 has different policies; the matched D29 continuation additionally quantifies
   selection under one explicit penalty assumption in that case and three selected earlier-fold cases, not a
   population-wide gate. The complete earlier-fold five-draw screen is now accounted against the single
   matching failure continuation; its sparse outcomes do not answer the full predictive comparison.
   Actual retries are now paired against first-seed matched continuations in one selected F4 case; the
   player-first differences and uncertainty are recorded above. Alternative continuation assumptions and
   comparisons against real outcomes on development folds remain open. The retry prototype remains
   unwired; no predictive or production gate has been passed.
   The selected real-retry 10k run and replay above add scale, not representativeness. Reproduce in a fresh
   namespace with `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -u analysis/a1_real_retry_scale.py --worlds-dir data/derived/experiments/<new-dir> --output analysis/experiments/<new-report>.json`,
   then `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -u analysis/a1_real_retry_scale_audit.py analysis/experiments/<new-report>.json --output analysis/experiments/<new-audit>.json`.
   A deliberate clean stop uses `--stop-after-batches N`; resume the same paths with `--resume` after
   inspecting the directory. Resume independently replays the complete new-batch prefix; any orphan
   fails closed and must be retained for inspection rather than overwritten.
   The separate vector continuation's three-game real-outcome preflight is complete above. Reproduce with
   `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -u analysis/a1_vector_penalty_backtest.py --pilot --name <fresh-name>`,
   then `.venv/bin/python analysis/a1_vector_penalty_backtest_audit.py analysis/experiments/<fresh-name>.json --output analysis/experiments/<fresh-audit>.json`.
   The measured eight-worker 200-game screen has already failed the primary gate; do not repeat it unchanged.
   For a materially new candidate, refreeze/revalidate any changed source under new names, never exceed ten
   total compute threads, and compare on exactly matched games and initial seeds using the registered
   player-first gate. A clean pilot is not promotion.
   Genuinely dated
   pre-game report cohorts remain unavailable for fitting or calibrating an availability model; labelled
   fixed scenario weights themselves remain permitted. The resume prototype
   is single-operator only, and an orphaned partial batch fails for manual inspection. Source evidence and missing dated
   injury-report cohorts are documented there and in FINDINGS; do not score protected-season outcomes.
   The retry coordinator is deliberately unwired: prove world-local classification and survivor isolation,
   audit persisted outputs, cap and record retries, compare predictive effects to the distinct S06 penalty
   policy on development folds, and do not retry input/cutoff/accounting/unknown errors. Keep the existing
   forecast if those gates cannot be met. The two retained research contexts now pass the independent snapshot
   check above; enforce equivalent origin-safe provenance for any future view before enabling the research path.
   The full-game selected comparison can be repeated under fresh names with
   `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -u analysis/a1_f4_six_roster_full_comparison.py --worlds-dir data/derived/experiments/<new-dir> --output analysis/experiments/<new-report>.json`,
   then `.venv/bin/python analysis/a1_f4_six_roster_full_audit.py analysis/experiments/<new-report>.json --output analysis/experiments/<new-audit>.json`.
   To repeat the matched-state run under fresh names:
   `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -u analysis/a1_matched_penalty_run.py --worlds-dir data/derived/experiments/<new-dir> --output analysis/experiments/<new-report>.json`
   and `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -u analysis/a1_matched_penalty_audit.py analysis/experiments/<new-report>.json --output analysis/experiments/<new-audit>.json`;
   use `--pilot` for the fixed ten-seed wiring check. To reproduce a selected earlier-fold run use
   `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -u analysis/a1_dated_matched_penalty.py --fold F1 --worlds-dir data/derived/experiments/<new-dir> --output analysis/experiments/<new-report>.json`
   and `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -u analysis/a1_dated_matched_penalty_audit.py analysis/experiments/<new-report>.json --output analysis/experiments/<new-audit>.json`;
   change `--fold` to F2 or F3, run folds sequentially, and use `--pilot` to replay the first five draws.
   Reproduce the complete saved-screen accounting with
   `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -u analysis/a1_dated_screen_selection.py --output analysis/experiments/<new-report>.json`
   and `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -u analysis/a1_dated_screen_selection_audit.py analysis/experiments/<new-report>.json --output analysis/experiments/<new-audit>.json`.
   Alternative continuation sensitivity and the player-first/promotion and live-slate checks remain unresolved.
   Reproduce with `.venv/bin/python analysis/a1_game_context_audit.py data/snapshots/2026-11-22/meta.json data/master_fixtures.csv data/derived/experiments/20261122_chunk_a_a1_d47_game_view_one_full_v2.json data/derived/experiments/20261122_chunk_a_a1_d47_game_view_two_full_v2.json --payloads data/derived/experiments/20261122_chunk_a_a1_d47_expected_payload_one_shared_v1.json data/derived/experiments/20261122_chunk_a_a1_d47_expected_payload_two_shared_v1.json --output analysis/experiments/<new-context-audit>.json`.
2. Finish A1 only after the actual rung requirements or the explicitly documented blocked fallback are resolved,
   review all root docs, smoke/fault, commit and push. Stop at the owner's A1 boundary; leave A2/A3 and Chunk B
   unchanged. A new full nightly belongs at the end of Chunk A, not this isolated research checkpoint.

## Previous A1 80% commands — historical context

1. **A1 80%:** implement/test a gated branch UI only against fully audited isolated fixtures and preserve the
   existing unconditional production fallback; no unvalidated Expected data may be published. Research labels
   must carry through to any view. Check laptop/phone import and offline compatibility before claiming delivery.
   The shared consumers now have a research-only injection path, but **no code in `game.mjs` sets it**. First
   adapt the independently audited selected summary to the Game Centre contract, removing or rederiving every
   branch-dependent unconditional field (especially starter/minute-basis metadata, availability panel,
   lead fan, spotlight, shooting-defined counts and advanced distributions); implement one common selection
   across player/team/sheet/scenario views. Do not copy unconditional data into a selected branch. Include
   true availability separate from positive-minute participation and distinguish mass units from world counts.
   Reproduce the current browser check with a local review server and a new output:
   `node analysis/a1_scenario_browser_check.mjs http://127.0.0.1:8767 data/derived/experiments/20261122_chunk_a_a1_d47_browser_fixture_two_identity_v1.json analysis/experiments/20261122_chunk_a_a1_d47_joint_full_v2.json analysis/experiments/20261122_chunk_a_a1_d47_joint_two_1800sec.json analysis/experiments/20261122_chunk_a_a1_d47_joint_empty_v2.json analysis/experiments/20261122_chunk_a_a1_d47_dynamic_grid_two_v2.json analysis/experiments/20261122_chunk_a_a1_d47_dynamic_grid_two_v3_audit.json analysis/experiments/<new-browser-check>.json`.
   It injects only the scenario pane and retains unconditional game metadata; it is **not** full-view acceptance.
   The current independently checked full-mixture summaries and payloads use suffix `_shared_v1`. Previous
   `_identity_v1` probes contain earlier source/audit hashes and must be reproduced at their original commit or
   regenerated and re-audited with new names before use in a new payload.
   The ignored opening-five/period-aware two-player fixture and compact audit are recorded above. To rebuild under a new name, run
   `.venv/bin/python analysis/a1_branch_browser_fixture.py analysis/experiments/20261122_chunk_a_a1_d47_10000_two.json --output data/derived/experiments/<new-fixture>.json`,
   then `.venv/bin/python analysis/a1_branch_browser_fixture_audit.py data/derived/experiments/<new-fixture>.json --output analysis/experiments/<new-audit>.json`;
   never overwrite the existing evidence. Period-aware fixtures now have the player-period inputs, but they are
   not a completed Game Centre contract: wire and test coherent derived summaries, all shared weighted consumers
   and phone fallback without exposing an unvalidated switch. To compare period summaries with original captures,
   run    `node analysis/a1_branch_period_browser_audit.mjs data/derived/experiments/20261122_chunk_a_a1_d47_browser_fixture_two_opening_v1.json analysis/experiments/20261122_chunk_a_a1_d47_browser_fixture_two_opening_v2_audit.json analysis/experiments/<new-period-crosscheck>.json`.
   Run `node tests/test_a1_branch_world_source.mjs` for all nine synthetic lineup selections and corruption cases.
   The derived team/player summaries above can be reproduced with
   `node analysis/a1_branch_game_summary_probe.mjs data/derived/experiments/20261122_chunk_a_a1_d47_browser_fixture_two_opening_v1.json '{}' data/derived/experiments/<new-summary>.json analysis/experiments/<new-probe>.json`
   and `.venv/bin/python analysis/a1_branch_game_summary_audit.py analysis/experiments/<new-probe>.json --output analysis/experiments/<new-audit>.json`;
   use JSON player-ID-to-boolean choices for partial and fully fixed selections. Run
   `node tests/test_a1_branch_game_summary.mjs` for summary edge cases. Keep expected weighted units separate from
   actual simulation counts and preserve precise world-minute filters.
   The Expected-only research payload is produced only from the independently audited identity fixture and
   full-mixture summary, e.g.
   `node analysis/a1_expected_payload_probe.mjs data/derived/experiments/20261122_chunk_a_a1_d47_browser_fixture_two_identity_v1.json analysis/experiments/20261122_chunk_a_a1_d47_browser_fixture_two_identity_v1_audit.json analysis/experiments/20261122_chunk_a_a1_d47_game_summary_two_shared_v1_probe.json analysis/experiments/20261122_chunk_a_a1_d47_game_summary_two_shared_v1_audit.json data/derived/experiments/<new-payload>.json analysis/experiments/<new-probe>.json`
   followed by `.venv/bin/python analysis/a1_expected_payload_audit.py analysis/experiments/<new-probe>.json --output analysis/experiments/<new-audit>.json`.
   Run `node tests/test_a1_expected_payload.mjs`; serialization is not an import/offline test or permission to
   ship. Verify labels and actual PWA compatibility only after integrating a fully coherent gated UI.
   Run `node tests/test_a1_weighted_browser.mjs` for arithmetic edge cases; the real-fixture audit takes the
   fixture, a new audit output, Expected report and one or more matching Given reports, e.g.
   `node analysis/a1_weighted_browser_audit.mjs data/derived/experiments/20261122_chunk_a_a1_d47_browser_fixture_one_v3.json analysis/experiments/<new-audit>.json analysis/experiments/20261122_chunk_a_a1_d47_expected_one_home_pts.json analysis/experiments/20261122_chunk_a_a1_d47_joint_one_full.json analysis/experiments/20261122_chunk_a_a1_d47_joint_one_empty.json`.
   The existing production path continues to use equally weighted worlds; the injected branch adapter supports
   exact weighted conditions across scenario, Given/Joint and drivers but is not yet a full Game Centre source.
   Integrate **all** dependent consumers before exposing a lineup switch. Preserve availability separately from
   positive minutes, selected branch identity, and fail closed on missing/corrupt worlds. Continue D48 research above and the
   short-roster penalty comparison without masking failures.
   The completed **A1 60%** accounting task was to design and independently validate a season representation that consumes each near-term game once
   and preserves every supported exact branch-weighted world marginal and win identity, including the 1/20,000
   counterexample. Do not silently round or resample to 10,000 equal-weight universes; measure memory/runtime and
   retain existing pathway if the representation is infeasible or changes predictive dependence. The unsupported
   foul exception remains explicit: keep the unconditional forecast and do not promote or publish a partial
   mixture. Then follow A1 rungs 80–100; stop after the A1 checkpoint under the owner's latest instruction.
   A2/A3 and Chunk B remain documented for a later agent, and Chunk A must finish before Chunk B starts.
   The planned Game Centre presentation is recorded in DASHBOARD_PLAN: one shared either/plays/sits control,
   coherent team/player views and compact comparison, not separate uncertainty tabs; ship Expected only after
   its gates, including exact marginalisation when only one player's status is fixed. Given and Joint must slice
   those same selected worlds with the correct weights and an explicit empty-condition state.
   Candidate to test (not accepted): couple each game's exact discrete world mass to a shared unit interval,
   using a game-seeded permutation and circular offset; partition at the union of all game boundaries and carry
   each interval's exact rational weight through one pathway universe. This can preserve all per-game marginals
   without an exponential Cartesian product, but may induce artificial cross-game dependence; quantify that
   explicitly against independent draws and existing pathway behaviour before deciding viability. Fail explicitly
   if denominator/array limits or a roster make the representation infeasible.
2. Keep the existing player-first gates, protected final test and D40 history deferral. No production model or
   branch policy changes without the documented evidence and promotion checks.

## Prior actions — A1 20% history (superseded)

The owner has authorised both D42 chunks in order, superseding D41's earlier stop. The dashboard programme is done;
do not resume U1–U22.

1. **A1 20% (partial):** run the frozen repair replay below and its independent accounting before crediting the rung:
   `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=8 .venv/bin/python -u scripts/a1_branch_world_probe.py --game 401810327
   --worlds 32 --repair --output analysis/experiments/20261122_chunk_a_a1_branch_repair.json --worlds-dir
   data/derived/experiments/20261122_chunk_a_a1_branch_repair`. This uses fixed seeds and actual participants;
   it is wiring evidence only. `scripts/a1_lineup_branches.py::one_player` copies a D29 game, fixes one uncertain player's
   availability, re-solves starters and targets, and rejects invalid regulation allocations. Synthetic tests in
   `tests/test_a1_lineup_branches.py` exercise plays/sits, scheduled legal fives and actual `_mu` defender inputs;
   the original game remains untouched. Run `.venv/bin/python -m unittest tests.test_a1_lineup_branches
   tests.test_projection_availability tests.test_a1_availability -q` (36 passed). This does **not** establish
   legality after foul-outs or test a complete branch engine run. Next, exercise the isolated branch path on
   development-fold game inputs with independently audited full-world/lineup accounting; fail explicitly if the
   known v1.3 foul-out-mask defect yields a disqualified lineup, without silently changing the serving policy.
   Record the exact reproducible commands, seeds, populations and results. Do not credit 20% until complete-branch
   validity is established or its limitation resolved; do not score protected-season outcomes.
   **Frozen development probe, completed with failure:** fixed F4 game `401810327`, 32 worlds per branch, home player
   with the largest D29 mean target (string-ID tie break), with synthetic 0.5 pre-branch availability and all
   actual participants supplied. For each plays/sits branch, run once without capture and once with a no-op
   observational trace using the same D31 branch seed. Compare all saved player box arrays, minutes, scores
   and periods exactly, then use `a1_substitution_world_audit.audit_worlds` on the captured worlds. Treat a
   disqualified five, unequal outputs or failed accounting as a failure, not a model score. Command:
   `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=8 .venv/bin/python -u scripts/a1_branch_world_probe.py --game 401810327
   --worlds 32 --output analysis/experiments/20261122_chunk_a_a1_branch_probe.json --worlds-dir
   data/derived/experiments/20261122_chunk_a_a1_branch_probe`. The report fingerprints source, model config
   and captures; this is a single known-participant wiring probe, not evidence of availability calibration or
   accuracy. The audit never repairs a foul-out or rewrites a result. Attached shell **2860** exited **1**;
   log `/tmp/musnba_chunk_a1_branch_probe.log` and the report/captures above are retained. Both replay traces
   preserve every checked output exactly; both fail on players accumulating more than six fouls. Independent
   accounting found disqualified lineups in **14/32 plays** worlds (**298/16,080** fives) and **16/32 sits**
   worlds (**548/16,248** fives); team/player points and team minutes reconcile. These are one synthetic
   conditioning example, not a population-wide foul-out rate. An isolated `BranchLegalityGuard` now rejects
   invalid fives and any sixth foul before proceeding, including the reproduced engine defect; it does not
   implement the legal five-player exception or change production. **25** focused tests pass. The guarded
   fixed F4 replay subsequently failed as detailed below. A proper repair
   needs the unchanged model gates before allowing production branches; do not claim A1 20% without evidence.
   Sequential normal/fault smoke finished as shell **2864**: **108/108** normal checks passed, and the deliberate
   fault exited **1** with **86/108** passing; logs `/tmp/musnba_a1_probe_{smoke,fault}.log`. No session-owned
   process remains running.
   **Guarded replay frozen before execution:** repeat the same game, 32-world branches and exact seeds with
   `--guarded`; retain distinct report and capture paths:
   `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=8 .venv/bin/python -u scripts/a1_branch_world_probe.py --game 401810327
   --worlds 32 --guarded --output analysis/experiments/20261122_chunk_a_a1_branch_guarded.json --worlds-dir
   data/derived/experiments/20261122_chunk_a_a1_branch_guarded`. An unsupported sixth foul must be reported
   as a failed branch rather than producing a forecast. Original unguarded probe source is checkpoint `a3baeab`.
   The guarded replay finished as attached shell **2882**, exit **1**; log
   `/tmp/musnba_chunk_a1_branch_guarded.log`. Both branches stopped explicitly at a sixth foul in Q3, and no
   forecast or world capture was emitted; report `analysis/experiments/20261122_chunk_a_a1_branch_guarded.json`.
   **Subsequent source freeze:** an isolated foul-out-only candidate preserves D29 schedules and normal random streams until
   a legal substitution is required. Reject    unhandled short-roster cases explicitly; do not pretend this is the NBA
   technical-penalty exception. Independently audit legal fives and score/minute accounting, then test against the
   frozen player-first control and applicable promotion gates. Important implementation hazard: the existing
   `engine.py` `after_fouls` hook returns one boolean and recomputes lineup context for **every** active world
   when any substitution occurs, after in-game state has changed. The new mask hook avoids this whole-batch
   refresh, with controlled isolation tests. Retain existing policy compatibility and the no-policy baseline.
   The guard remains the safe fallback if the replay fails.
   **Document review:** HANDOFF, PLAN, FINDINGS, ENGINE_PLAN and README record the experiment, guard and next
   action. AGENTS, TRAINING_PLAN and DASHBOARD_PLAN need no change: standing rules, frozen gates and shipped UI
   are unchanged.
2. **S08–S10** map into Chunks A/B as above. S08 must solve the exact weighted-mixture/10,000-unweighted-world
   counterexample without rounding away discrepancies; S10 must not infer a future physical-absence hazard from
   recorded-DNP proxies. Keep actual-participant diagnostics separate from pre-game availability.
3. **S11 freezes the tested combination before promotion.** Confirm on the fixed wider folds and second seed, protect
   the final test and use player outcomes first.
4. **S12 implements model visibility. S13 is deferred by D40:** do not build or run historical forecast replay;
   preserve existing forecasts and prior-version archives. Its unchanged 5% weight receives no progress credit.
5. **S14 remains unfinished:** when the remaining development is completed, run its fresh nightly and
   iCloud/PWA checks, then construct the successor chunk in the documented weighted, ten-rung format.
6. **Incremental iCloud delivery is a separate future item** (PLAN §9b): design atomic per-game publication,
   incomplete/complete generation labels, resume and safe import/offline handling. Current exports remain batch-only;
   never claim iCloud sync is a phone import.

**Prior live-handoff document review (22 Nov):** HANDOFF then led with the current state, dated delivery, risks and
first future rung; AGENTS and PLAN explicitly require a live log and a verified commit/push at each completed
module/subtask. ENGINE_PLAN and TRAINING_PLAN need no change because decisions and promotion/cutoff gates are
unchanged; FINDINGS has no new experiment to record; DASHBOARD_PLAN and README need no change because shipped
behaviour and commands are unchanged. Baseline smoke **108/108**. No model, dashboard, forecast, bundle or public
shell changed; no nightly or data job was run.

**Chunk A A1 contract checkpoint document review (22 Nov):** HANDOFF, PLAN, ENGINE_PLAN and TRAINING_PLAN
record the active scope and frozen design. AGENTS and README correct the now-superseded stop wording. FINDINGS
needs no change because no new experiment or data measurement was performed; DASHBOARD_PLAN needs no change because
no app behaviour shipped. Baseline smoke **108/108**. No model, dashboard, forecast, bundle or public shell changed;
no nightly or data job was run. No session-owned background job was started.

**Chunk A A1 partial implementation:** isolated helper and synthetic tests only; see FINDINGS for the exact
population and limitations. HANDOFF, PLAN, FINDINGS and README describe this partial work. AGENTS, ENGINE_PLAN,
TRAINING_PLAN and DASHBOARD_PLAN need no change: standing rules, accepted design, promotion gates and shipped UI
are unchanged. Normal smoke **108/108** (`/tmp/musnba_chunk_a1_partial_smoke.log`); deliberate fault exited **1**
with **86/108** passing (`/tmp/musnba_chunk_a1_partial_fault_retry.log`). The first concurrent fault check was
stopped to avoid competing with normal smoke and was repeated sequentially. Both new Python files have zero
Pylance diagnostics. No session-owned background job remains. No model, dashboard, forecast, bundle or public shell
changed. This is a partial checkpoint, not A1 20% or module completion.

**D43 planning document review:** HANDOFF and PLAN describe the future source-neutral View Centre, the simulated
first release and later actual-game adapter; DASHBOARD_PLAN and ENGINE_PLAN record presentation and design; AGENTS
and README point to the changed plan. TRAINING_PLAN needs no changes because model gates remain unchanged; FINDINGS
needs no change because this planning session ran no experiment. Baseline smoke **108/108**. No model, dashboard,
forecast, bundle or public shell changed; no nightly or data job was run.

**D42 planning document review:** HANDOFF and PLAN contain both future chunk contracts and unchanged original A1
accounting; ENGINE_PLAN records the owner proposal; DASHBOARD_PLAN describes the planned selected-world feature;
AGENTS and README point to the split. TRAINING_PLAN needs no changes because its promotion/cutoff gates remain
unchanged; FINDINGS needs no changes because this planning session made no new measurements. No model, dashboard,
forecast, bundle or public shell changed, and no nightly or data job was run. Planning baseline smoke **108/108**.

**S07 checkpoint document review:** HANDOFF records state, stop and future actions; PLAN records S07 completion,
weights and the streaming backlog; FINDINGS records measured results and negatives; ENGINE_PLAN and TRAINING_PLAN
record the delivered shared-origin/fallback design; DASHBOARD_PLAN records the shipped UI, shell and checks; README
documents batch export and manual import. AGENTS already records the scoped overnight authority and D40, so its
standing rules need no additional change. No model promotion or final-test scoring occurred.

**S02 checkpoint document review:** HANDOFF records state, evidence, limitations and S03's next action; PLAN records
the completion and measured totals; FINDINGS holds the population-specific audits; TRAINING_PLAN and README document
the guarded candidate and commands. AGENTS needs no change because the scoped overnight authority is already recorded;
ENGINE_PLAN needs no design decision because no model was accepted; DASHBOARD_PLAN needs no change because no app,
forecast, bundle or shell changed. The accepted engine and bundle remain v1.3 and the existing generation; phone import
is still unconfirmed.

**S03 checkpoint document review:** HANDOFF has the current ledger and resume commands; PLAN has the weighted status,
diagnosis and frozen candidate matrix; FINDINGS has populations, accounting and negative results; TRAINING_PLAN
states the two cutoff-safe tests; README documents the diagnostic commands. ENGINE_PLAN and DASHBOARD_PLAN update
their status only: no serving design, app, forecast, bundle or shell changed. AGENTS needs no change because the
scoped overnight authority and checkpoint protocol are already recorded. v1.3 and the existing PWA generation remain
served; phone import is unconfirmed.

**S06 checkpoint document review:** HANDOFF records the completed decision, evidence, checks and S07 resume;
PLAN updates the phase, milestone and log; FINDINGS holds the paired and state-specific results and the starter
timing audit; TRAINING_PLAN freezes the gate and timing exclusion; ENGINE_PLAN records the unpromoted policy and
remaining foul-out limitation; DASHBOARD_PLAN and README document the tested but undelivered S07 changes and commands.
AGENTS needs no change because the scoped overnight authority and checkpoint protocol are already recorded. The
hosted model, Pages shell and iCloud bundle remain unchanged; local source assets may be visible, and phone import
is unconfirmed.

**S04 checkpoint document review:** HANDOFF records both defence decisions, source checkpoints and the active S05
queue; PLAN records weighted completion and measured results; FINDINGS holds the fold populations, negative findings
and independent checks; TRAINING_PLAN records the frozen protocols and corrected preliminary minute gate; README
describes the research tools. ENGINE_PLAN and DASHBOARD_PLAN update status only because no model, app, forecast,
bundle or shell changed. AGENTS needs no change because the scoped overnight authority and checkpoint protocol
already apply. The v1.3 bundle's three copies still match; phone import remains unconfirmed.

**S05 checkpoint document review:** HANDOFF records both candidate decisions, the smoke/fault checks and S06 resume
state; PLAN records weighted completion and the negative results; FINDINGS holds population-specific evidence and
limitations; TRAINING_PLAN records the frozen gates and S06 descriptive protocol; README maps the research scripts.
ENGINE_PLAN and DASHBOARD_PLAN update status only because no model, app, forecast, bundle or shell changed. AGENTS
needs no change because the scoped overnight authority and checkpoint protocol already apply. The served engine and
PWA bundle remain unchanged; phone import is still unconfirmed.

**S06 partial document review:** HANDOFF carries the live ledger, data limitations and exact resume commands; PLAN
records the 70% rung; FINDINGS records the populations, screens and independent world replay; TRAINING_PLAN freezes the protocols;
README maps the research scripts. ENGINE_PLAN and DASHBOARD_PLAN need no design/behaviour change because no accepted
model, app, forecast, bundle or shell changed. AGENTS needs no change because the scoped overnight authority already applies. The served
v1.3/pathway-v1 model and bundle remain unchanged; phone import is unconfirmed.

**S07 partial document review:** HANDOFF and PLAN record the 20% archive/label rungs and next action; FINDINGS records
origin, status, box coverage and retrospective labels; TRAINING_PLAN freezes the protected-season-safe inventory; README maps the
audit scripts. ENGINE_PLAN and DASHBOARD_PLAN require no change because no design, forecast or app changed; AGENTS
already records the overnight authority. The model and bundle remain unchanged.

**S06/S07 failure-and-baseline partial review:** HANDOFF records both failures/running jobs and the next checks; PLAN
and FINDINGS record the measured F4 proxies and unsuccessful engine screen; TRAINING_PLAN freezes the subsequent
censored sequence protocol; README maps the independent scorer/auditor. ENGINE_PLAN and DASHBOARD_PLAN need no
change because no accepted design, app, forecast, shell or bundle changed. AGENTS already contains the scoped overnight
authority. The v1.3/pathway-v1 model and PWA generation remain unchanged; phone import is unconfirmed.

**S06 flow/S07 spell-source partial review:** HANDOFF records the running fixed screen, its log and the unscored
spell follow-up; PLAN and FINDINGS record the independently reconciled three-game preflight without claiming an
accuracy result. README maps the prepared research script. TRAINING_PLAN's frozen follow-up and acceptance rules
are unchanged; ENGINE_PLAN and DASHBOARD_PLAN need no change because no production design or presentation changed;
AGENTS already records this overnight authority. The v1.3/pathway-v1 forecasts and PWA bundle remain unchanged;
phone import is unconfirmed.

**S06 state-protocol/S07 70% partial review:** HANDOFF records both active rungs, exact running jobs and the
unresolved short-roster bug; PLAN records weighted progress and the negative proxy result; FINDINGS records the
audited populations and stress reproduction; TRAINING_PLAN freezes the state-conditioned comparison before
scoring; README maps the new research tools. ENGINE_PLAN and DASHBOARD_PLAN need no change because neither an
accepted design nor app, forecast, shell or bundle has changed. AGENTS already contains the scoped overnight
authority. The v1.3/pathway-v1 model and existing PWA generation remain served; phone import is unconfirmed.

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
to delete candidate data blindly. NBA history retrieval is complete; future provider access remains one polite stream.

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
| `scripts/a1_minutes_gate.py`, `scripts/a1_pooled_audit.py` | Preliminary minute bounds and independent pooled bootstrap accounting; neither is promotion confirmation |
| `scripts/a1_substitutions.py`, `scripts/a1_substitution_{audit,opportunities,states,dataset,dataset_audit}.py` | Isolated sequential timeout replay, state diagnostics, strictly prior target candidates and independent accounting; eligibility remains uncertain |
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
