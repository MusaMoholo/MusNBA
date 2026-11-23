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
  game: '123', origin: '2026-11-22',
  selected_players: [{team_id: '1', player_id: '10', probability: 0.75}],
  weight_assumptions: 'Uncalibrated availability; independence unvalidated.',
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
// Original status assumptions must remain exact; they need no quarter-probability remapping.
const originalProbability = structuredClone(fixture);
originalProbability.selected_players[0].probability = .15;
originalProbability.branches[0].weight = {numerator: '3', denominator: '20'};
originalProbability.branches[1].weight = {numerator: '17', denominator: '20'};
const originalSource = branchWorldSource(originalProbability);
assert.equal(joint(originalSource.weights, [1, 1, 0, 0], [1, 1, 1, 1]).event, .15);
assert.throws(() => branchWorldSource({...originalProbability, selected_players: [{...originalProbability.selected_players[0], probability: NaN}]}), /probability/);
globalThis.location = {href: 'http://localhost/'};
const {branchCalculations, branchWorldData, mask, minuteMarginalData, preciseCalculations, varOptions, worldData} = await import('../scripts/webapp/outcomes.mjs');
const adapted = branchWorldData(source);
assert.deepEqual([...adapted.values('p:10', 'min')], [0.1, 0, 0, 0]);
assert.deepEqual([...adapted.minuteValues('10', 'q1')], [0.1, 0, 0, 0]);
assert.deepEqual([...adapted.values('p:10', 'plays')], [1, 0, 0, 0]);
assert.deepEqual([...adapted.values('p:10', 'available')], [1, 1, 0, 0]);
assert.deepEqual([...adapted.values('g', 'ot')], [1, 0, 1, 0]);
assert.deepEqual([...mask(adapted, [{subj: 'p:10', v: 'min', op: 'ge', x: 0.05}])], [1, 0, 0, 0]);
assert.deepEqual([...mask(adapted, [{subj: 'p:10', v: 'available'}])], [1, 1, 0, 0]);
const fixed = branchWorldData(source, {'10': false});
assert.match(varOptions('p:10', 'plays', adapted), /value="available"/);
assert.doesNotMatch(varOptions('p:10', 'plays', {stats: ['min'], W: 1}), /value="available"/);
assert.deepEqual([...mask(fixed, [])], [0, 0, 1, 1]);
assert.deepEqual([...mask(fixed, [{subj: 'p:10', v: 'plays'}])], [0, 0, 0, 0]);
assert.throws(() => mask(fixed, [{subj: 'p:99', v: 'pts', op: 'ge', x: 1}]), /unavailable/);
assert.throws(() => mask(fixed, [{subj: 'p:10', v: 'min', op: 'bad', x: 30}]), /Invalid condition/);
assert.throws(() => mask(fixed, [{subj: 'p:10', v: 'min', op: 'ge', x: NaN}]), /Invalid condition/);
const calculations = branchCalculations(adapted);
const pts = adapted.values('p:10', 'pts'), plays = mask(adapted, [{subj: 'p:10', v: 'plays'}]);
assert.equal(calculations.mass(null), 8);
assert.equal(calculations.mass(plays), 3);
assert.equal(calculations.count(plays), 1);
assert.equal(calculations.mean(pts), 0.75);
assert.equal(calculations.mean(pts, plays), 2);
assert.equal(calculations.share(pts, null, x => x > 0), 3 / 8);
assert.equal(calculations.dist(adapted.values('p:10', 'min')).mean, 0.037500000000000006);
assert.deepEqual(calculations.dist(Float64Array.from([29.999, 30, 30.001, 31]), null, {minute: true}).hist, [3, 4, 1]);
assert.deepEqual(calculations.dist(pts).hist, [5, 0, 3]);
assert.match(calculations.grid(adapted.values('p:10', 'min'), pts, null, {xName: 'Minutes', yName: 'Points'}), /Share of probability/);
assert.match(calculations.grid([1, 1, 1, 1], pts, null, {xName: 'Minutes', yName: 'Points'}), /<th>All<\/th>/);
assert.equal(branchCalculations(fixed).mass(null), 2);
assert.equal(branchCalculations(fixed).mass(plays), 0);
assert.equal(branchCalculations(fixed).mean(pts, plays), null);
assert.throws(() => calculations.mass([0, 1]), /mask/);
assert.throws(() => calculations.mass([0, 1, 2, 0]), /mask/);
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
assert.equal(source.weightAssumptions, fixture.weight_assumptions);
assert.equal(source.game, fixture.game);
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
  f => { delete f.weight_assumptions; },
  f => { f.origin = 'unknown'; },
  f => { f.origin = '2026-02-30'; },
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
  const Wd = branchWorldData(sourceTwo, choices), C = branchCalculations(Wd);
  const points = Wd.values('p:10', 'pts'), plays = Wd.values('p:10', 'plays');
  const playMask = mask.map((yes, i) => Number(yes && plays[i]));
  const playingMass = playMask.reduce((sum, yes, i) => sum + yes * sourceTwo.weights[i], 0);
  const scoreMass = mask.reduce((sum, yes, i) => sum + yes * sourceTwo.weights[i] * points[i], 0);
  assert.equal(C.mass(null), mass);
  assert.equal(C.mass(playMask), playingMass);
  assert.equal(C.mean(points), scoreMass / mass);
  assert.equal(C.share(plays, null, value => value === 1), playingMass / mass);
  assert.equal(C.count(playMask), playMask.reduce((sum, yes) => sum + yes, 0));
}
const production = {
  worlds: 3, players: ['10', '20'], side: [0, 1], stats: ['min', 'pts'],
  periods: ['q1', 'q2', 'q3', 'q4', 'ot'],
  lines: encode([0, 0, 0, 0, 30, 10, 0, 0, 30, 20, 0, 0]),
  team_periods: encode(Array(30).fill(0)),
  minutes_schema: 1,
  period_minutes_f64_le: minutes([.1, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    10, 19.9999, 0, 0, 0, 0, 0, 0, 0, 0, 10, 20.0001, 0, 0, 0, 0, 0, 0, 0, 0]),
};
const exactWorlds = worldData(production), exactCalc = preciseCalculations(exactWorlds);
assert.deepEqual([...exactWorlds.minuteValues('10', 'h1')], [.1, 29.9999, 30.0001]);
assert.deepEqual([...exactWorlds.values('p:10', 'plays')], [1, 1, 1]);
assert.deepEqual([...mask(exactWorlds, [{subj: 'p:10', v: 'min', op: 'ge', x: 30}])], [0, 0, 1]);
assert.equal(exactCalc.share(exactWorlds.values('p:10', 'min'), null, v => v > 30), 1 / 3);
assert.deepEqual(exactCalc.dist(exactWorlds.values('p:10', 'min'), null, {minute: true}).hist.slice(29), [1, 1]);
assert.match(exactCalc.grid(exactWorlds.values('p:10', 'min'), exactWorlds.values('p:10', 'pts'), null,
  {xName: 'Minutes', yName: 'Points'}), /Share of probability/);
const legacy = structuredClone(production);
delete legacy.minutes_schema;
delete legacy.period_minutes_f64_le;
assert.equal(worldData(legacy).preciseMinutes, undefined);
assert.deepEqual([...worldData(legacy).values('p:10', 'plays')], [0, 1, 1]);
const marginalValues = [];
for (let w = 0; w < 3; w++) for (const id of production.players) for (const period of ['q1', 'q2', 'q3', 'q4', 'h1', 'h2', 'fg']) {
  marginalValues.push([...exactWorlds.minuteValues(id, period)].sort((a, b) => a - b)[w]);
}
const marginal = {schema: 1, worlds: 3, players: production.players,
  periods: ['q1', 'q2', 'q3', 'q4', 'h1', 'h2', 'fg'], minutes_f64_le: minutes(marginalValues)};
const phone = minuteMarginalData(marginal);
assert.deepEqual([...phone.minuteValues('10', 'fg')], [.1, 29.9999, 30.0001]);
assert.deepEqual([...phone.minuteValues('10', 'h1')], [.1, 29.9999, 30.0001]);
assert.throws(() => phone.minuteValues('99', 'fg'), /Unknown/);
for (const corrupt of [
  raw => { raw.schema = 2; },
  raw => { raw.minutes_f64_le = minutes([0]); },
  raw => { raw.periods.reverse(); },
  raw => { raw.players = ['10', '10']; },
  raw => { raw.minutes_f64_le = minutes(marginalValues.map((v, i) => i === 0 ? -0.5 : v)); },
  raw => { raw.minutes_f64_le = minutes(marginalValues.map((v, i) => i === 0 ? NaN : v)); },
  raw => { raw.minutes_f64_le = minutes([...marginalValues].reverse()); },
]) {
  const bad = structuredClone(marginal);
  corrupt(bad);
  assert.throws(() => minuteMarginalData(bad), /minute/i);
}
for (const corrupt of [
  raw => { raw.minutes_schema = 2; },
  raw => { delete raw.period_minutes_f64_le; },
  raw => { raw.period_minutes_f64_le = minutes([0]); },
  raw => { raw.periods.reverse(); },
  raw => { raw.lines = encode(Array(12).fill(0)); },
  raw => { raw.period_minutes_f64_le = minutes(Array(30).fill(NaN)); },
]) {
  const bad = structuredClone(production);
  corrupt(bad);
  assert.throws(() => worldData(bad), /minute/i);
}
console.log('branch world source: focused cases passed');
