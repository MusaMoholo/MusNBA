#!/usr/bin/env node
// Cross-check browser arithmetic against separately reconstructed Python reports.
import {createHash} from 'node:crypto';
import {readFileSync, statSync, writeFileSync} from 'node:fs';
import {branchWeights, distribution, joint} from './a1_weighted_browser.mjs';

const [fixturePath, output, expectedPath, ...paths] = process.argv.slice(2);
if (!fixturePath || !output || !expectedPath || !paths.length) throw new Error('Provide fixture, new output, Expected and Given report paths');
const read = p => JSON.parse(readFileSync(p, 'utf8'));
const sha = p => createHash('sha256').update(readFileSync(p)).digest('hex');
const fixture = read(fixturePath);
const expected = read(expectedPath);
if (fixture.source_sha256 !== expected.source_sha256 || expected.side !== 'home'
    || expected.player !== null || expected.stat !== 'pts' || Object.keys(expected.conditions).length) {
  throw new Error('Wrong source or Expected report');
}
const controls = paths.map(read);
const match = /^player ([0-9]+) has (?:positive simulated minutes|at least ([0-9]+(?:\.[0-9]+)?) simulated seconds)$/.exec(controls[0].given);
if (!match || controls.some(c => c.given !== controls[0].given || c.event !== 'home team wins')) {
  throw new Error('Joint reports must use the same supported event and condition');
}
const playerId = match[1];
const minimumSeconds = match[2] == null ? null : Number(match[2]);
const specs = fixture.branches.map(b => ({worlds: b.worlds.worlds, weight: b.weight}));
const {weights, denominator} = branchWeights(specs);
const event = new Uint8Array(weights.length), given = new Uint8Array(weights.length);
const homePoints = new Uint16Array(weights.length);
const starts = [];
let offset = 0;
for (const branch of fixture.branches) {
  const raw = branch.worlds, player = raw.players.indexOf(playerId);
  if (player < 0 || raw.players.lastIndexOf(playerId) !== player) throw new Error('Given player missing or duplicated');
  const points = Buffer.from(raw.team_periods, 'base64'), played = Buffer.from(raw.played, 'base64');
  const minutes = Buffer.from(raw.minutes_f64_le, 'base64');
  if (points.length !== raw.worlds * 10 || played.length !== raw.worlds * raw.players.length
      || minutes.length !== raw.worlds * raw.players.length * 8) throw new Error('Malformed packed worlds');
  starts.push(offset);
  for (let w = 0; w < raw.worlds; w++) {
    let home = 0, away = 0;
    for (let q = 0; q < 5; q++) {
      home += points[w * 10 + q];
      away += points[w * 10 + 5 + q];
    }
    homePoints[offset + w] = home;
    event[offset + w] = home > away ? 1 : 0;
    const position = w * raw.players.length + player;
    given[offset + w] = minimumSeconds == null ? played[position]
      : (minutes.readDoubleLE(position * 8) * 60 >= minimumSeconds ? 1 : 0);
  }
  offset += raw.worlds;
}
const compare = (num, den, expectedFraction) => {
  if (BigInt(num) * BigInt(expectedFraction.denominator) !== BigInt(den) * BigInt(expectedFraction.numerator)) {
    throw new Error('Exact weighted fraction differs from independent Python report');
  }
};
const checks = [];
for (const [index, path] of paths.entries()) {
  const control = controls[index], selection = new Uint8Array(weights.length);
  if (control.game !== fixture.game || control.source_sha256 !== fixture.source_sha256) throw new Error('Joint report source differs');
  fixture.branches.forEach((b, i) => {
    const yes = Object.entries(control.lineup_conditions).every(([pid, plays]) =>
      b.assignments.some(([, id, flag]) => id === pid && flag === plays));
    if (yes) selection.fill(1, starts[i], starts[i] + b.worlds.worlds);
  });
  const actual = joint(weights, event, given, selection), ref = control.result;
  if (actual.status !== ref.status) throw new Error('Conditional status differs');
  compare(actual.eventMass, actual.selected, ref.event);
  compare(actual.conditionMass, actual.selected, ref.condition);
  compare(actual.jointMass, actual.selected, ref.joint);
  if (ref.given === null ? actual.given !== null : actual.given === null) throw new Error('Empty conditional state differs');
  if (ref.given) compare(actual.jointMass, actual.conditionMass, ref.given);
  checks.push({report: path, worlds: selection.reduce((a, b) => a + b, 0), status: actual.status});
}
const dist = distribution(homePoints, weights), reference = expected.distribution;
if (dist.histogram.length !== reference.histogram.length || Math.abs(dist.mean - reference.mean) > 1e-10
    || JSON.stringify(dist.quantiles) !== JSON.stringify(reference.quantiles)) throw new Error('Expected distribution differs');
dist.histogram.forEach(([value, mass], i) => {
  const row = reference.histogram[i];
  if (value !== row.value) throw new Error('Histogram values differ');
  compare(mass, dist.defined, row);
});
const sources = [fixturePath, ...paths, expectedPath, 'analysis/a1_weighted_browser.mjs', 'analysis/a1_weighted_browser_audit.mjs'];
writeFileSync(output, JSON.stringify({
  kind: 'isolated browser arithmetic against Python accounting; not a forecast or browser integration',
  source_sha256: Object.fromEntries(sources.map(p => [p, sha(p)])),
  fixture_bytes: statSync(fixturePath).size, worlds: weights.length, denominator,
  joint_checks: checks, home_points_bins: dist.histogram.length, home_points_mean: dist.mean,
  limitations: ['Current dashboard still uses equal-weight consumers.',
    'Availability assumptions and independence are uncalibrated.', 'No phone or UI test is implied.'],
}, null, 2) + '\n', {flag: 'wx'});
console.log(`${weights.length} worlds: exact browser/Python conditional masses and ${dist.histogram.length} histogram bins match`);
