import assert from 'node:assert/strict';
import {branchWorldSource} from '../analysis/a1_branch_world_source.mjs';
import {joint} from '../analysis/a1_weighted_browser.mjs';

const encode = a => Buffer.from(a).toString('base64');
const minutes = values => {
  const bytes = Buffer.alloc(values.length * 8);
  values.forEach((v, i) => bytes.writeDoubleLE(v, i * 8));
  return encode(bytes);
};
const fixture = {
  selected_players: [{team_id: '1', player_id: '10', probability: 0.75}],
  branches: [
    {assignments: [['1', '10', true]], weight: {numerator: '3', denominator: '4'}, worlds: {
      worlds: 2, players: ['10', '20'], side: [0, 1], stats: ['min', 'pts'],
      lines: encode([0, 2, 10, 1, 0, 0, 0, 0]),
      minutes_f64_le: minutes([0.1, 10, 0, 0]), availability: encode([1, 1, 1, 0]), played: encode([1, 1, 0, 0]),
      team_periods: encode([2, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]),
    }},
    {assignments: [['1', '10', false]], weight: {numerator: '1', denominator: '4'}, worlds: {
      worlds: 2, players: ['10', '20'], side: [0, 1], stats: ['min', 'pts'],
      lines: encode([0, 0, 10, 1, 0, 0, 10, 1]),
      minutes_f64_le: minutes([0, 10, 0, 10]), availability: encode([0, 1, 0, 1]), played: encode([0, 1, 0, 1]),
      team_periods: encode([0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0]),
    }},
  ],
};
for (const branch of fixture.branches) {
  const raw = branch.worlds;
  const lines = Buffer.from(raw.lines, 'base64'), mins = Buffer.from(raw.minutes_f64_le, 'base64');
  const periodLines = [], periodMinutes = [];
  for (let cell = 0; cell < 4; cell++) for (let q = 0; q < 5; q++) {
    periodLines.push(q === 0 ? lines[cell * 2 + 1] : 0);
    periodMinutes.push(q === 0 ? mins.readDoubleLE(cell * 8) : 0);
  }
  raw.period_stats = ['pts'];
  raw.periods = ['q1', 'q2', 'q3', 'q4', 'ot'];
  raw.period_lines = encode(periodLines);
  raw.period_minutes_f64_le = minutes(periodMinutes);
  raw.final_period = encode([5, 4]);
}
const source = branchWorldSource(fixture);
assert.deepEqual([...source.playerValues('10', 'min')], [0.1, 0, 0, 0]);
assert.deepEqual([...source.playerValues('10', 'plays')], [1, 0, 0, 0]);
assert.deepEqual([...source.playerValues('10', 'available')], [1, 1, 0, 0]);
assert.deepEqual([...source.playerValues('10', 'sits')], [0, 1, 1, 1]);
assert.deepEqual([...source.teamPoints('home')], [2, 0, 0, 0]);
assert.deepEqual([...source.playerValues('10', 'min', 'h1')], [0.1, 0, 0, 0]);
assert.deepEqual([...source.playerValues('10', 'pts', 'q1')], [2, 0, 0, 0]);
assert.deepEqual([...source.playerValues('10', 'pts', 'q2')], [0, 0, 0, 0]);
assert.deepEqual([...source.teamPoints('home', 'q1')], [2, 0, 0, 0]);
assert.deepEqual([...source.overtimePeriods()], [1, 0, 1, 0]);
assert.deepEqual([...source.selection({'10': false})], [0, 0, 1, 1]);
assert.equal(joint(source.weights, [1, 0, 0, 0], [1, 0, 0, 0]).event, 3 / 8);
assert.throws(() => source.selection({'10': 'sits'}), /choices/);
assert.throws(() => source.playerValues('99', 'min'), /Unknown/);
assert.throws(() => source.playerValues('10', 'plays', 'q1'), /unavailable/);
assert.throws(() => source.playerValues('10', 'starts'), /unavailable/);
assert.throws(() => source.playerValues('10', 'min', 'constructor'), /period/);
for (const corrupt of [
  f => { f.branches[1].assignments[0][2] = true; },
  f => { f.branches[0].weight.numerator = '1'; },
  f => { f.branches[0].worlds.minutes_f64_le = ''; },
  f => { f.branches[0].worlds.lines += ' '; },
  f => { f.branches[0].worlds.played = encode([0, 1, 0, 0]); },
  f => { f.branches[1].worlds.availability = encode([1, 1, 0, 1]); },
  f => { f.branches[0].worlds.period_lines = encode(Array(20).fill(0)); },
  f => { f.branches[0].worlds.period_minutes_f64_le = minutes(Array(20).fill(0)); },
  f => { delete f.branches[1].worlds.period_lines; },
  f => { f.branches[0].worlds.team_periods = encode(Array(20).fill(0)); },
  f => { f.branches[0].worlds.final_period = encode([3, 4]); },
  f => { delete f.branches[1].worlds.final_period; },
  f => { f.branches[0].worlds.periods.reverse(); },
]) {
  const bad = structuredClone(fixture);
  corrupt(bad);
  assert.throws(() => branchWorldSource(bad));
}
const openingFixture = structuredClone(fixture);
for (const [b, branch] of openingFixture.branches.entries()) {
  const raw = branch.worlds;
  raw.worlds = 1;
  raw.players = ['10', '11', '12', '13', '14', '15', '20', '21', '22', '23', '24'];
  raw.side = [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1];
  const lineup = b === 0 ? [0, 1, 2, 3, 4, 6, 7, 8, 9, 10] : [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
  raw.opening_lineups = encode(lineup);
  raw.availability = encode(raw.players.map((_, i) => Number(b === 0 || i !== 0)));
  raw.played = encode(raw.players.map((_, i) => Number(lineup.includes(i))));
  raw.minutes_f64_le = minutes(raw.players.map((_, i) => Number(lineup.includes(i))));
  raw.lines = encode(raw.players.flatMap((_, i) => [Number(lineup.includes(i)), 0]));
  raw.team_periods = encode(Array(10).fill(0));
  raw.final_period = encode([4]);
  delete raw.period_stats;
  delete raw.period_lines;
  delete raw.period_minutes_f64_le;
}
const openingSource = branchWorldSource(openingFixture);
assert.deepEqual([...openingSource.playerValues('10', 'starts')], [1, 0]);
assert.deepEqual([...openingSource.playerValues('15', 'starts')], [0, 1]);
assert.throws(() => openingSource.playerValues('10', 'starts', 'q1'), /unavailable/);
for (const corrupt of [
  f => { f.branches[0].worlds.opening_lineups = encode([0, 0, 2, 3, 4, 6, 7, 8, 9, 10]); },
  f => { f.branches[0].worlds.opening_lineups = encode([6, 1, 2, 3, 4, 0, 7, 8, 9, 10]); },
  f => { f.branches[1].worlds.opening_lineups = encode([0, 2, 3, 4, 5, 6, 7, 8, 9, 10]); },
  f => { delete f.branches[0].worlds.opening_lineups; },
]) {
  const bad = structuredClone(openingFixture);
  corrupt(bad);
  assert.throws(() => branchWorldSource(bad));
}
const two = structuredClone(fixture);
two.selected_players.push({team_id: '2', player_id: '20', probability: 0.25});
two.branches = fixture.branches.flatMap(original => [true, false].map(available => {
  const branch = structuredClone(original), raw = branch.worlds;
  branch.assignments.push(['2', '20', available]);
  branch.weight = {numerator: String(Number(branch.weight.numerator) * (available ? 1 : 3)),
    denominator: String(Number(branch.weight.denominator) * 4)};
  const availability = Buffer.from(raw.availability, 'base64'), played = Buffer.from(raw.played, 'base64');
  const lines = Buffer.from(raw.lines, 'base64'), mins = Buffer.from(raw.minutes_f64_le, 'base64');
  const periodLines = Buffer.from(raw.period_lines, 'base64'), periodMinutes = Buffer.from(raw.period_minutes_f64_le, 'base64');
  const teamPeriods = Buffer.from(raw.team_periods, 'base64');
  for (let w = 0; w < 2; w++) {
    const cell = w * 2 + 1;
    availability[cell] = Number(available);
    if (!available) {
      played[cell] = 0;
      lines.fill(0, cell * 2, cell * 2 + 2);
      mins.writeDoubleLE(0, cell * 8);
      periodLines.fill(0, cell * 5, cell * 5 + 5);
      periodMinutes.fill(0, cell * 5 * 8, (cell + 1) * 5 * 8);
      teamPeriods.fill(0, w * 10 + 5, w * 10 + 10);
    }
  }
  Object.assign(raw, {availability: encode(availability), played: encode(played), lines: encode(lines),
    minutes_f64_le: encode(mins), period_lines: encode(periodLines),
    period_minutes_f64_le: encode(periodMinutes), team_periods: encode(teamPeriods)});
  return branch;
}));
const sourceTwo = branchWorldSource(two);
const wrongSide = structuredClone(two);
for (const branch of wrongSide.branches) branch.worlds.side = [0, 0];
assert.throws(() => branchWorldSource(wrongSide), /metadata/);
for (const home of [null, true, false]) for (const away of [null, true, false]) {
  const choices = {};
  if (home !== null) choices['10'] = home;
  if (away !== null) choices['20'] = away;
  const expected = (home === null ? 1 : home ? 0.75 : 0.25) * (away === null ? 1 : away ? 0.25 : 0.75);
  const mask = sourceTwo.selection(choices);
  const mass = mask.reduce((sum, yes, i) => sum + yes * sourceTwo.weights[i], 0);
  assert.equal(mass / sourceTwo.denominator, expected);
}
console.log('branch world source: focused cases passed');
