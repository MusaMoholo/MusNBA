# Historical promotion v1 — frozen S01 preregistration

Superseded for release classification by [v2](promotion_v2_20261123.md), owner decision D51.
The original methods below are preserved verbatim; old decisions remain historical.

#### S01 preregistration — 22 Nov, before A1 candidates

The fixed development screen is the 200 retained F4 games in `20261120T162930Z_v1.3_pool_per_world_F4`, 1,000 worlds,
known actual participants and projected starters, pool 0. The independent pre-game-availability track is separate.
For player selection tiers, **star** means pre-game usage ≥0.25; otherwise **starter** means pre-game start share
≥0.5 and **bench** is below 0.5. Missing usage or start share is **unknown**, never silently bench. The older logged
scorecard uses actual game starters and remains a historical reference, not a selection gate. The screen has 284 star,
1,578 starter, 2,472 bench and 12 unknown player-games. A reportable tier/subgroup needs **at least 100 player-games
in 30 distinct games**; rarer cases are inconclusive, and required sparse tiers block a promotion claim rather than
being dropped. Game/season populations and exclusions must match exactly.

Player non-inferiority margins below are increases in CRPS in the statistic's own units. They are **2% of the
pre-game-tier pool-0 control**, rounded to four decimals; 3PM is fixed in advance at **0.0200 made threes** because the
old saved player output omitted 3PM. Its matched control must be regenerated before any 3PM decision.

| Pre-game tier | MIN CRPS (minutes) | PTS CRPS (points) | REB CRPS (rebounds) | AST CRPS (assists) | 3PM CRPS (makes) |
|---|---:|---:|---:|---:|---:|
| Star | 0.0578 | 0.0898 | 0.0304 | 0.0261 | 0.0200 |
| Starter | 0.0605 | 0.0711 | 0.0290 | 0.0207 | 0.0200 |
| Bench | 0.0796 | 0.0553 | 0.0237 | 0.0155 | 0.0200 |

The 2% bound is a small, meaningful loss relative to prediction error; a paired pool-400 versus pool-0 check on all
4,346 matched player-games had 95% game-clustered CRPS difference intervals narrower than these margins for these
four retained statistics. This is **not** a pure seed-noise experiment; S01 still measures an independent simulation
seed. If noise or the confidence interval is too large to demonstrate non-inferiority, increase worlds/games or report
inconclusive; **do not widen margins**.

Additional maximum harms: margin and total CRPS **0.20 points**, each quarter CRPS **0.10 points**, win log loss
**0.010 nats/game**, Brier **0.005**, and 10–90% coverage's absolute deviation from 0.80 **0.03**. For absolute signed
bias, the allowable increase in its magnitude is **0.30 minutes**, **0.30 points**, **0.10 rebounds**, **0.10 assists**
or **0.05 made threes** per player-game; team total/margin biases may grow by **1.0/0.5 points**. Season final-win CRPS
may worsen by at most **0.10 wins** on each supported start date; absolute dispersion, coverage and persistence error
may grow by at most **0.10, 0.05 and 0.05**, respectively. These are maximum harms, not desired target values.

Families and primary outcomes, frozen before candidate results: S04 defence/shot quality → pooled PTS CRPS;
S05/S06 membership/minutes/substitutions → pooled MIN CRPS; S07 availability → pre-game play Brier on a genuinely
dated cohort; S09 form/end-game → pooled PTS CRPS plus the prespecified joint-dependence checks; S10 pathway → pooled
final-win CRPS across the 16 matched season/start origins with each date separately reported. S08 is an accounting and
coherence change, not by itself an accuracy win. Pooled player CRPS weights eligible player-games equally; all three
supported tiers and the other core stats must pass their non-inferiority gates. Claims across multiple tested primary
families use Holm's 0.05 correction; exploratory within-family variants and all rejected runs are recorded.

Use **10,000 paired game-cluster bootstrap replicates**, NumPy seed **20261122**, sampling complete game IDs with
replacement and retaining all player rows from each sampled game; report the 2.5/97.5 percentiles. Required
non-inferiority passes only if the upper 97.5% bound of candidate-minus-control harm is strictly inside its frozen
margin. A primary win requires its corrected 95% upper bound below zero **and** its observed improvement larger than
the independently measured simulation-noise floor. For coverage/bias use the paired change in the absolute deviation,
not the signed change. Report sample sizes, point differences and intervals. Different model names alter the current
simulation seed; common streams may be used only when their semantics are explicitly fixed and valid, never assumed.
For each primary CRPS, define the 1,000-world simulation-noise floor conservatively as the larger absolute endpoint
of the 95% paired game-cluster bootstrap interval comparing the same control and inputs under its original stream and
an independent stream on the entire pinned 200-game panel. This rule is frozen before that comparison; it is not a
licence to discard an inconclusive interval or to lower the registered harm margins.
Win Brier and log loss use the empirical simulated probability without modification. A zero probability assigned to
the observed winner has genuinely infinite log loss: the report marks it explicitly instead of inventing a finite
value or an interval. This differs from the legacy backtest summary's numerical boundary safeguard.
The second-seed result, exact confirmation IDs, 10k subset and reproducibility manifest are recorded in
`analysis/experiments/20261122_a1_manifest.json`, pinned to source checkpoint `c6d5db4`; the later seed-list type
annotation preserves the compiled function and all 3,036 recorded seeds.

Source: `aa3d25d:TRAINING_PLAN.md`, S01 preregistration.
