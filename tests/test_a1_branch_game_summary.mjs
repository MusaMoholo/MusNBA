import assert from 'node:assert/strict';
import {branchGameSummary} from '../analysis/a1_branch_game_summary.mjs';

const records = {
  home: {pts: [10, 20, 0, 40], min: [10.1, 20.2, 0, 40.5], fgm: [4, 8, 0, 16], fga: [8, 10, 0, 20],
    oreb: [1, 2, 0, 3], dreb: [4, 8, 0, 9], ast: [2, 10, 0, 12]},
  away: {pts: [8, 10, 40, 50], min: [10, 20, 30, 40], fgm: [2, 3, 10, 12], fga: [5, 6, 20, 25]},
};
const source = {
  worlds: 4, weights: Float64Array.from([1, 3, 1, 3]), denominator: 8,
  game: '123', origin: '2026-11-22',
  selected: [{player_id: 'h', status: 'Day-To-Day', status_source: 'injury_report', impact_rank: 1}],
  weightAssumptions: 'Uncalibrated availability; independence unvalidated.',
  players: ['h', 'a'], side: [0, 1],
  selection: choices => Uint8Array.from(choices.home === true ? [1, 1, 0, 0] : [1, 1, 1, 1]),
  overtimePeriods: () => Uint8Array.from([0, 1, 0, 2]),
  teamPoints: (team, period) => Float64Array.from(['q1', 'h1', 'fg'].includes(period) ? records[team].pts : [0, 0, 0, 0]),
  playerValues: (id, stat, period = 'fg') => {
    const r = records[id === 'h' ? 'home' : 'away'];
    if (stat === 'available') return Float64Array.from([1, 1, 1, 1]);
    if (stat === 'plays') return Float64Array.from(id === 'h' ? [1, 1, 0, 1] : [1, 1, 1, 1]);
    if (stat === 'starts') return Float64Array.from(id === 'h' ? [1, 1, 0, 0] : [1, 1, 1, 1]);
    return Float64Array.from(['q1', 'h1', 'fg'].includes(period) ? (r[stat] || [0, 0, 0, 0]) : [0, 0, 0, 0]);
  },
};

const expected = branchGameSummary(source);
const home = expected.home.players[0], fg = home.periods.fg;
assert.equal(expected.selected_mass, 8);
assert.equal(expected.selected_worlds, 4);
assert.equal(expected.game, source.game);
assert.equal(expected.origin, source.origin);
assert.deepEqual(expected.selected_players, source.selected);
assert.equal(expected.weight_assumptions, source.weightAssumptions);
assert.equal(home.availability, 1);
assert.equal(home.played, 7 / 8);
assert.equal(home.opening_share, 1 / 2);
assert.equal(fg.mean.pts, 23.75);
assert.equal(fg.sec, (10.1 + 3 * 20.2 + 3 * 40.5) / 8 * 60);
assert.equal(fg.stats.min.hist[40], 3);
assert.equal(fg.stats.fgpct.defined_mass, 7);
assert.equal(fg.stats.fgpct.total_mass, 8);
assert.equal(fg.stats.fgpct.mean, 530 / 7);
assert.equal(home.double_double, 6 / 8);
assert.equal(home.triple_double, 6 / 8);
assert.equal(home.if_plays.pts, 190 / 7);
assert.equal(expected.home.box.fg.pts, expected.periods.fg.home.pts.mean);
assert.equal(expected.periods.q2.home.pts.mean, 0);
assert.equal(expected.ot, 6 / 8);
assert.deepEqual(expected.ot_periods, [2, 3, 3]);
const selected = branchGameSummary(source, {home: true});
assert.deepEqual(selected.choices, {home: true});
assert.equal(selected.selected_mass, 4);
assert.equal(selected.selected_worlds, 2);
assert.equal(selected.home.players[0].periods.fg.mean.pts, 17.5);
assert.equal(selected.home.players[0].played, 1);
assert.equal(selected.home.players[0].if_plays, undefined);
assert.equal(selected.periods.fg.home.win, 1);
const bad = {...source, playerValues: (id, stat, period) => stat === 'fga'
  ? Float64Array.from([0, 0, 0, 0]) : source.playerValues(id, stat, period)};
assert.throws(() => branchGameSummary(bad), /Made shots exceed attempts/);
console.log('branch game summary: focused cases passed');
