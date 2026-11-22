#!/usr/bin/env node
// Cross-check browser arithmetic against separately reconstructed Python reports.
import {createHash} from 'node:crypto';
import {readFileSync, statSync, writeFileSync} from 'node:fs';
import {distribution, joint} from './a1_weighted_browser.mjs';
import {branchWorldSource} from './a1_branch_world_source.mjs';

globalThis.location = {href: 'http://localhost/'};
const {branchCalculations, branchWorldData, mask} = await import('../scripts/webapp/outcomes.mjs');
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
const source = branchWorldSource(fixture), {weights, denominator} = source;
const homePoints = source.teamPoints('home'), awayPoints = source.teamPoints('away');
const event = homePoints.map((value, i) => value > awayPoints[i] ? 1 : 0);
const given = minimumSeconds == null ? source.playerValues(playerId, 'plays')
  : source.playerValues(playerId, 'min').map(value => value * 60 >= minimumSeconds ? 1 : 0);
const compare = (num, den, expectedFraction) => {
  if (BigInt(num) * BigInt(expectedFraction.denominator) !== BigInt(den) * BigInt(expectedFraction.numerator)) {
    throw new Error('Exact weighted fraction differs from independent Python report');
  }
};
const checks = [];
for (const [index, path] of paths.entries()) {
  const control = controls[index];
  if (control.game !== fixture.game || control.source_sha256 !== fixture.source_sha256) throw new Error('Joint report source differs');
  const selection = source.selection(control.lineup_conditions);
  const actual = joint(weights, event, given, selection), ref = control.result;
  const adapted = branchWorldData(source, control.lineup_conditions), C = branchCalculations(adapted);
  const eventMask = mask(adapted, [{subj: 't:home', v: 'win'}]);
  const condition = minimumSeconds == null ? {subj: 'p:' + playerId, v: 'plays'}
    : {subj: 'p:' + playerId, v: 'min', op: 'ge', x: minimumSeconds / 60};
  const givenMask = mask(adapted, [condition]), bothMask = mask(adapted, [condition, {subj: 't:home', v: 'win'}]);
  if (C.mass(null) !== actual.selected || C.mass(eventMask) !== actual.eventMass
      || C.mass(givenMask) !== actual.conditionMass || C.mass(bothMask) !== actual.jointMass
      || C.count(null) !== control.worlds) throw new Error('Shared outcome adapter differs from exact branch accounting');
  if (actual.status !== ref.status) throw new Error('Conditional status differs');
  compare(actual.eventMass, actual.selected, ref.event);
  compare(actual.conditionMass, actual.selected, ref.condition);
  compare(actual.jointMass, actual.selected, ref.joint);
  if (ref.given === null ? actual.given !== null : actual.given === null) throw new Error('Empty conditional state differs');
  if (ref.given) compare(actual.jointMass, actual.conditionMass, ref.given);
  checks.push({report: path, worlds: selection.reduce((a, b) => a + b, 0), status: actual.status});
}
const dist = distribution(homePoints, weights), reference = expected.distribution;
const adapted = branchWorldData(source), adaptedDist = branchCalculations(adapted).dist(adapted.values('t:home', 'pts'));
if (dist.histogram.length !== reference.histogram.length || Math.abs(dist.mean - reference.mean) > 1e-10
    || JSON.stringify(dist.quantiles) !== JSON.stringify(reference.quantiles)
    || Math.abs(adaptedDist.mean - reference.mean) > 1e-10
    || JSON.stringify(adaptedDist.q) !== JSON.stringify(reference.quantiles)) throw new Error('Expected distribution differs');
dist.histogram.forEach(([value, mass], i) => {
  const row = reference.histogram[i];
  if (value !== row.value) throw new Error('Histogram values differ');
  compare(mass, dist.defined, row);
  compare(adaptedDist.hist[value - adaptedDist.min], adaptedDist.mass, row);
});
const sources = [fixturePath, ...paths, expectedPath, 'analysis/a1_branch_world_source.mjs',
  'scripts/webapp/weighted-worlds.mjs', 'scripts/webapp/outcomes.mjs', 'analysis/a1_weighted_browser_audit.mjs'];
writeFileSync(output, JSON.stringify({
  kind: 'isolated browser arithmetic against Python accounting; not a forecast or browser integration',
  source_sha256: Object.fromEntries(sources.map(p => [p, sha(p)])),
  fixture_bytes: statSync(fixturePath).size, worlds: weights.length, denominator,
  joint_checks: checks, home_points_bins: dist.histogram.length, home_points_mean: dist.mean,
  limitations: ['The weighted adapter is not connected to a selectable dashboard forecast.',
    'Availability assumptions and independence are uncalibrated.', 'No phone or UI test is implied.'],
}, null, 2) + '\n', {flag: 'wx'});
console.log(`${weights.length} worlds: exact browser/Python conditional masses and ${dist.histogram.length} histogram bins match`);
