# Rule 3 correction — implementation contract

Frozen before new candidate simulations, after D51 framework audit. The candidate remains opt-in until
v2 confirmation and delivery. No fitted nodes, targets, starter selection or ordinary substitution policy changes.

Normally replace a six-foul player with the available non-disqualified teammate outside the five having
largest existing D29 target (stable player-order ties). When fewer than five remain, retain only the necessary
currently playing newly disqualified player; never revive an earlier removed player. Assess a technical on
that disqualifying foul and each subsequent personal foul by retained players. Technical attempts use the
highest known prior FT% among the opposing five, a disclosed coaching assumption and separately seeded stream.
Preserve unavailable status; missing/corrupt required inputs fail explicitly, no rejection sampling.

**Additional correction versus the old continuation:** an offensive foul by a retained offender must increment
the offending team's foul count. Ordinary offensive fouls remain excluded; ordinary defensive fouls are already
counted by the engine and must not be double-counted. Sources: [Rule 3-I](https://official.nba.com/rule-no-3-players-substitutes-and-coaches/)
and [Rule 12B-VII](https://official.nba.com/rule-no-12-fouls-and-penalties/). The old code omitted this exception.

Return a world-local changed-lineup mask through the existing engine hook. Main RNG draws and all no-correction
states remain untouched; do not claim independent world paths after a vector event divergence. No injury/ejection
or other exception not simulated is claimed. No policy silently activates unavailable players.

Tests cover both sides, normal/retained offensive and defensive fouls, sixth/subsequent fouls, scheduled
re-entry attempts, unavailable substitutes, multiple-world isolation, technical shooter eligibility/missingness,
correct box/team/period/FT accounting and deterministic replay. New source hashes are frozen with the runner
before the three-game pilot and fresh independent panel in the rule3 confirmation manifest.
