# Clock execution semantics — source clarification

Recorded during the early F4 run, after its first20 completed pairs and before aggregate forecast-quality
scoring. Only progress/accounting has been inspected. No recipe, population, margin or acceptance criterion changes.

`Engine._end_period` advances only the indexed worlds that ended their period; there is no global
quarter barrier. The old design note saying quarter-synchronous was inaccurate. The clock sampler
returns original values for locally ineligible states, and the hook still consumes all legacy main-RNG
draws before applying its separate namespaced sampler. Once a clock-on trajectory diverges, vector
sizes/draw assignments in subsequent iterations can change for other worlds, including earlier periods.

Therefore require the declared **hook-off full raw parity** and local sampler fallback tests. Do not
invent a requirement that every clock-on Q1–Q3 world remain bit-identical to its control. Unaffected
period distributions still undergo all original proper-score compatibility checks. This observation is
not evidence of iid PRNG quality, a new release exemption, or a claim that the clock improves forecasts.
The fixed27 proper bounds, coverage-harm rule, learned primary and survivor stages remain unchanged.

Source inspection also finds no separate shot-clock state in `Worlds`: only period time is explicit.
The old engine design's24/14-enforcement claim overstates the implementation. Segment timing is learned
from coarse event timestamps, including the retained miss-clock rebound convention. Current clock
accounting proves period/minute identities, not unrecorded tracking-level shot-clock compliance. Record
this existing design gap; do not manufacture control timestamps, add a blind14-second segment cap, or
claim the contextual candidate resolves it. A future explicit-clock mechanism needs its own source/reset
audit and validation. No candidate parameter or release threshold changes in response to this inspection.
