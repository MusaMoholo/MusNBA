import assert from 'node:assert/strict';
import {branchGameSummary} from '../analysis/a1_branch_game_summary.mjs';
import {selectedGameView} from '../analysis/a1_game_view_contract.mjs';

const hash = 'a'.repeat(64);
const selected = [
  {team_id: '1', player_id: '10', probability: 0.75, status: 'Day-To-Day'},
  {team_id: '2', player_id: '20', probability: 0.5, status: 'Questionable'},
];
const values = {
  home: {pts: [10, 20, 0, 40], min: [10.1, 20.2, 0, 40.5], fgm: [4, 8, 0, 16], fga: [8, 10, 0, 20]},
  away: {pts: [8, 10, 40, 50], min: [10, 20, 30, 40], fgm: [2, 3, 10, 12], fga: [5, 6, 20, 25]},
};
const source = {
  worlds: 4, weights: Float64Array.from([1, 3, 1, 3]), denominator: 8, game: '123', origin: '2026-11-22',
  selected, weightAssumptions: 'Uncalibrated; independence unvalidated.', players: ['10', '20'], side: [0, 1],
  selection: choices => Uint8Array.from(choices['10'] === true ? [1, 1, 0, 0] : [1, 1, 1, 1]),
  overtimePeriods: () => Uint8Array.from([0, 1, 0, 2]),
  teamPoints: (team, period) => Float64Array.from(['q1', 'h1', 'fg'].includes(period) ? values[team].pts : [0, 0, 0, 0]),
  playerValues: (id, stat, period = 'fg') => {
    const player = values[id === '10' ? 'home' : 'away'];
    if (stat === 'available') return Float64Array.from([1, 1, 1, 1]);
    if (stat === 'plays') return Float64Array.from(id === '10' ? [1, 1, 0, 1] : [1, 1, 1, 1]);
    if (stat === 'starts') return Float64Array.from(id === '10' ? [1, 1, 0, 0] : [1, 1, 1, 1]);
    return Float64Array.from(['q1', 'h1', 'fg'].includes(period) ? (player[stat] || [0, 0, 0, 0]) : [0, 0, 0, 0]);
  },
};
const payload = {
  game: source.game, origin: source.origin, engine: 'engine-v1.3', model: 'v1.3', fixture_sha256: hash,
  selected_players: selected, weight_assumptions: source.weightAssumptions, limitations: ['Research only.'],
  roster: {players: ['10', '20'], side: [0, 1]},
  player_metadata: [{id: '10', name: 'Home', starter: true, minutes_basis: {target: 42}},
    {id: '20', name: 'Away'}],
};
const game = {id: '123', date: '2026-11-22', home: {id: '1'}, away: {id: '2'},
  spotlight: {unconditional: true}};
const make = choices => ({fixture_sha256: hash, result: branchGameSummary(source, choices)});
const fullSummary = make({});
const full = selectedGameView(game, payload, fullSummary);
const partial = selectedGameView(game, payload, make({'10': true}));
assert.equal(full.research.selected_worlds, 4);
assert.equal(full.research.selected_mass, 8);
assert.equal(partial.research.selected_worlds, 2);
assert.equal(partial.research.selected_mass, 4);
assert.equal(full.sim.home.players[0].periods.fg.mean.pts, 23.75);
assert.equal(partial.sim.home.players[0].periods.fg.mean.pts, 17.5);
assert.equal(full.sim.home.players[0].periods.fg.sec, (10.1 + 3 * 20.2 + 3 * 40.5) / 8 * 60);
assert.equal(full.sim.home.players[0].selected_availability, 1);
assert.equal(full.sim.home.players[0].availability, undefined);
assert.equal(full.sim.home.players[0].played, 7 / 8);
assert.equal(full.sim.home.players[0].opening_share, 1 / 2);
assert.equal(full.sim.home.players[0].periods.fg.stats.fgpct.defined_mass, 7);
assert.equal(full.sim.home.players[0].periods.fg.stats.fgpct.total_mass, 8);
assert.equal(full.game.spotlight, undefined);
assert.equal(full.sim.home.players[0].starter, undefined);
assert.equal(full.sim.home.players[0].minutes_basis, undefined);
assert.equal(full.sim.home.players[0].periods.fg.stats.fgpct.defined, undefined);
assert.equal(full.research.label, 'Research only; not a validated forecast');
full.sim.home.players[0].periods.fg.stats.pts.hist[0] = 999;
assert.notEqual(fullSummary.result.home.players[0].periods.fg.stats.pts.hist[0], 999);

for (const corrupt of [
  (g, p, s) => { s.fixture_sha256 = 'b'.repeat(64); },
  (g, p, s) => { s.result.choices = {'99': true}; },
  (g, p, s) => { s.result.selected_mass = 0; },
  (g, p, s) => { p.roster.side[0] = 1; },
  (g, p, s) => { s.result.home.players[0].periods.fg.stats.pts.hist[0]++; },
  (g, p, s) => { s.result.home.players[0].periods.fg.stats.fgpct.total_mass = 7; },
  (g, p, s) => { s.result.home.players[0].availability = 0; },
  (g, p, s) => { s.result.home.box.fg.pts++; },
]) {
  const g = structuredClone(game), p = structuredClone(payload), s = make({});
  corrupt(g, p, s);
  assert.throws(() => selectedGameView(g, p, s));
}
console.log('research selected game view: focused cases passed');
