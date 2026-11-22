# Handoff — state and next actions

Updated **22 November 2026 — Chunk A execution started; A1 contract frozen at 10%; S01–S07 remain complete**.
Partial source checkpoint **4dce4a3** was pushed before the UX-delivery nightly.

## Read this first — live handoff

- **Current action:** the owner has requested both D42 chunks in order. Chunk A has started at A1; implement and
  verify the isolated one-player branches at rung 20% using the frozen contract below. Do not start Chunk B before
  Chunk A's delivery and checkpoint.
- **Owner UX requests in progress (22 Nov):** replace the Players fixed 3+/8+ game filter with a season-progress
  minutes-share benchmark; group player-game FG/3P/FT makes, attempts and shooting-percentage distributions.
  Percentages condition on at least one attempt and explicitly show the no-attempt chance. Source and focused tests
  are in the worktree; the affected stored-output contract requires a live nightly, iCloud bundle, Pages shell,
  import/offline checks and browser inspection before this UX work is delivered. Focused Python **27/27**, Node
  **2/2**, isolated view browser **19/19** plus **6/6** on a player with no-attempt worlds, and old-bundle isolated
  PWA **18/18** passed; final normal smoke **108/108** passed after schema-aware legacy replay, and deliberate fault
  exited **1** with **86/108** checks passing. Logs: `/tmp/musnba_user_ux_final_smoke.log` and
  `/tmp/musnba_user_ux_fault.log`. Review servers :8767, :8768 and :8769 belong to this session; never touch :8766.
  The guarded A1 replay sources and JSON are included in this partial checkpoint, not a completed rung.
- **UX delivery next:** after tests/fault pass, checkpoint source and this in-progress ledger; run
  `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=8 .venv/bin/python -u scripts/nightly_musnba.py` with a log, no history
  backfill and no offline/no-rebuild shortcut. Require success before export, verify the newly stored period
  distributions and their no-attempt accounting, rebuild the data-free shell and run
  `node analysis/pwa_import_check.mjs --url http://127.0.0.1:8768/MusNBA/ --bundle "$HOME/Library/Mobile Documents/com~apple~CloudDocs/MusNBA/MusNBA.musnba.gz" --require-shooting yes`.
  Recheck touched pages on :8767, publish only the reviewed shell to `gh-pages`, and record iCloud delivery separately
  from manual phone import. Then checkpoint before continuing A1's isolated foul-out work.
- **Active nightly:** shell **2955**, wrapper PID **14660**, nightly PID **14661**, log
  `/tmp/musnba_d44_nightly.log`. Launched at current ET origin with the default 10,000 game worlds and season
  paths. Collection completed with **63 requests, 0 failures, 0 new finals**; NBA Stats had no new requests.
  Input rebuilding is underway. Read the full result when done. Do not start a second NBA Stats stream. If it fails,
  preserve the previous iCloud bundle and record the precise blocker before retrying.
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
  already inspected and cannot be called untouched confirmation. Next A2 rung is an isolated, calibrated
  player-uncertainty candidate only if strictly earlier fitted predictions support an identifiable component;
  otherwise record the unsupported result. A1 remains 10%.
- **A2 feasibility preparation:** retained S04 control-shot predictions cover **136,578 F1**, **139,660 F2**
  and **87,671 F3** validation shots. A source-order check matched game/date/zone/result and found no missing
  shooter IDs; stronger cache/clock/coordinate and role-cutoff verification is still required. The exact
  teacher-forced within-game residual screen is frozen in TRAINING_PLAN before measurement; it cannot by itself
  distinguish persistent talent from nightly or shared form. No F4 or final-test outcomes will enter it.
- **Prepared, unpublished Pages shell:** isolated worktree `/tmp/musnba-user-ux-pages`, `gh-pages` at `f2932e1`,
  has only `assets/game.mjs`, `assets/players.mjs` and `sw.js` changed from the reviewed data-free shell
  `614f3061d9dc69a41bc4`. The shell passed **18/18** checks with the previous bundle. Do not publish until the new
  bundle and its period-shooting import/offline check pass; never add data or bundles to Pages.
- **Doc review:** `DASHBOARD_PLAN` and `ENGINE_PLAN` record D44 behaviour and decisions; `FINDINGS`, `PLAN` and
  this handoff carry the A2 measurement and live state. `TRAINING_PLAN` freezes the A2 descriptive screen without
  changing selection gates; `README` maps the research command; `AGENTS.md` standing rules are unchanged.
- **Progress:** original A1 **58.0%**, S01–S07 complete; S08–S12/S14 open, S13 historical forecast backfill
  deferred. New independent chunk boards: **A 10%** (A1 10%, A2 20%, A3 0%) and **B 0%** (B1/B2/B3 all 0%). Keep
  the original A1 weights intact; new within-chunk weights do not reset or double-count A1.
- **Production:** possession engine **v1.3/D29**, team pathway **v1**. S04's two defence candidates did not pass;
  S05's minute candidates did not meet the primary gate. S06's 200-game candidate improved minute CRPS
  **3.5662→3.5309** but only **66/69** non-inferiority bounds were established, so it was not promoted. Those
  engine diagnostics supplied actual participants, not forecast availability. No new model has been promoted.
- **Remaining model risks:** defensive differences are under-expressed on the fixed 200-game control; a controlled
  probe exposed an unupdated foul-out mask; dated development injury reports are insufficient to calibrate
  availability. Do not present status fallbacks as validated or replay estimates as live forecasts.
- **Last delivery:** origin **22 Nov 2026 ET**, **7 Today + 10 Tomorrow** games × **10,000** worlds and **10,000**
  season paths. iCloud bundle generated **2026-11-22T12:39:01Z** (SHA-256
  `8f8026e7b01febbbf9416c23faaa1e794bd94a116e29d3c22b6e1513cb12579a`); published data-free `gh-pages`
  **f2932e1**, cache `0d7693ac00bad5eb2e00`. Phone import is **not confirmed**. This is a dated delivery, not a
  claim that the forecasts are current on a later date. New nightlies still export **one batch at the end**.
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
  Earlier chronology below is historical evidence, not the current action list. Session-owned review servers and
  the active nightly are listed above; no backtest or separate history download is running.

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
manifest and safe PWA import (PLAN §9b); it is not implemented, so nightlies still export one batch at the end.
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
item counts and measured rates. Current Chunk A progress is **10%**; Chunk B remains **0%**.

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

**Live board:** Chunk A `██░░░░░░░░░░░░░░░░░░ 10%`; A1 `██░░░░░░░░░░░░░░░░░░ 10%`;
A2 `████░░░░░░░░░░░░░░░░ 20%`; A3 `░░░░░░░░░░░░░░░░░░░░ 0%`.
Original A1 remains 58%; do not double-count the separate board.

**A1 10% frozen branch contract (22 Nov; design, not implemented):**

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
mask and fails closed on short rosters. **10/10** combined branch/covariance unit tests pass; it is deliberately
not wired to the engine because its mask hook does not yet exist. Next: finish and verify the D44 nightly and
delivery, then add the backwards-compatible mask hook and focused world-local context tests before the probe.

| Rung | A1 — lineups and Expected |
|---:|---|
| 10 | Freeze branch IDs, uncertain-player selection, provenance and independence caveats. |
| 20 | One-player plays/sits branches re-solve minutes and defence with valid five-player lineups. |
| 30 | Two-player branches and explicit >2-maybe non-exhaustive handling pass probability checks. |
| 40 | Deterministic 10k worlds per supported branch persist with seeds and inputs. |
| 50 | Expected distributions preserve exact branch weights; handle the 10k indivisibility counterexample explicitly. |
| 60 | Season consumption preserves the documented weighted identities without duplicate near-term games. |
| 70 | Missing status, unsupported dependence and cold rosters are visibly labelled or fail explicitly. |
| 80 | Local branch UI and phone Expected-only compatibility pass focused tests. |
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
| 70 | Phone receives compact summaries/list only where size permits; world tools and branches remain localhost-only. |
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
are counts over the worlds. The app slices the engine's stored worlds for joint and conditional outcomes (localhost only; the
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

The owner has authorised both D42 chunks in order, superseding D41's earlier stop. The dashboard programme is done;
do not resume U1–U22.

1. **A1 20% (partial):** `scripts/a1_lineup_branches.py::one_player` copies a D29 game, fixes one uncertain player's
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
   implement the legal five-player exception or change production. **25** focused tests pass. Next replay the
   fixed F4 branches with this guard and log the explicit outcome, then decide the A1 fallback. A proper repair
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
   **Next:** develop an isolated foul-out-only candidate preserving D29 schedules and normal random streams until
   a legal substitution is required. Reject unhandled short-roster cases explicitly; do not pretend this is the NBA
   technical-penalty exception. Independently audit legal fives and score/minute accounting, then test against the
   frozen player-first control and applicable promotion gates. Important implementation hazard: the existing
   `engine.py` `after_fouls` hook returns one boolean and recomputes lineup context for **every** active world
   when any substitution occurs, after in-game state has changed. A foul-out-only repair cannot claim unaffected
   worlds are unchanged if it uses that hook unmodified. Prove world-local context refresh or fail closed; retain
   existing policy compatibility and the no-policy baseline. The guard remains the safe fallback if it fails.
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
