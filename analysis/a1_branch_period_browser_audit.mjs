#!/usr/bin/env node
// Compare research-source period summaries with independently decoded original captures.
import {createHash} from 'node:crypto';
import {readFileSync, writeFileSync} from 'node:fs';
import {branchWorldSource} from './a1_branch_world_source.mjs';
import {distribution} from './a1_weighted_browser.mjs';

const [fixturePath, referencePath, output] = process.argv.slice(2);
if (!fixturePath || !referencePath || !output) throw new Error('Provide fixture, independent audit and new output paths');
const read = p => readFileSync(p);
const fixtureBytes = read(fixturePath), fixture = JSON.parse(fixtureBytes);
const reference = JSON.parse(read(referencePath));
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
if (hash(fixtureBytes) !== reference.fixture_sha256 || !reference.player_period_stat_values
    || !reference.player_period_exact_minute_values) throw new Error('Fixture or independently checked period data differs');
const source = branchWorldSource(fixture), player = reference.threshold_player, checks = {};
const periods = ['q1', 'q2', 'q3', 'q4', 'h1', 'h2', 'fg'];
if (!reference.selected_period_means_from_captures
    || Object.keys(reference.selected_period_means_from_captures).length !== periods.length
    || periods.some(p => !reference.selected_period_means_from_captures[p])) throw new Error('Incomplete period reference');
for (const period of periods) {
  const expected = reference.selected_period_means_from_captures[period];
  const actual = {
    minutes: distribution(source.playerValues(player, 'min', period), source.weights).mean,
    player_points: distribution(source.playerValues(player, 'pts', period), source.weights).mean,
    home_points: distribution(source.teamPoints('home', period), source.weights).mean,
  };
  for (const key of Object.keys(actual)) {
    if (!Number.isFinite(expected[key]) || Math.abs(actual[key] - expected[key]) > 1e-10) {
      throw new Error(`${period} ${key} differs from independently decoded captures`);
    }
  }
  checks[period] = actual;
}
let overtimeChecks = 0;
if (reference.final_period_values) {
  if (reference.final_period_values !== source.worlds) throw new Error('Incomplete final-period data');
  const counts = new Map();
  source.overtimePeriods().forEach((value, i) => counts.set(value, (counts.get(value) || 0) + source.weights[i]));
  const expected = reference.overtime_period_mass_from_captures;
  if (counts.size !== Object.keys(expected).length) throw new Error('Overtime categories differ');
  for (const [value, mass] of counts) {
    const ref = expected[value];
    if (!ref || BigInt(mass) * BigInt(ref.denominator) !== BigInt(ref.numerator) * BigInt(source.denominator)) {
      throw new Error('Overtime-period mass differs from independently decoded captures');
    }
    overtimeChecks++;
  }
}
let openingChecks = 0;
if (reference.opening_lineup_values) {
  if (reference.opening_lineup_values !== source.worlds * 10
      || reference.opening_branch_starts_from_captures?.length !== fixture.branches.length) throw new Error('Incomplete opening-lineup reference');
  for (let b = 0; b < fixture.branches.length; b++) {
    const branch = fixture.branches[b], ref = reference.opening_branch_starts_from_captures[b];
    if (ref.branch_id !== branch.branch_id || ref.players.join(',') !== branch.worlds.players.join(',')
        || ref.counts.length !== ref.players.length) throw new Error('Opening-lineup reference differs');
    const choices = Object.fromEntries(branch.assignments.map(([, id, plays]) => [id, plays]));
    const mask = source.selection(choices);
    for (let p = 0; p < ref.players.length; p++) {
      const starts = source.playerValues(ref.players[p], 'starts');
      const count = mask.reduce((sum, yes, i) => sum + yes * starts[i], 0);
      if (count !== ref.counts[p]) throw new Error('Opening starter count differs from independently decoded captures');
      openingChecks++;
    }
  }
}
writeFileSync(output, JSON.stringify({
  kind: 'isolated browser source period accounting; not a forecast or browser integration',
  fixture: fixturePath, fixture_sha256: hash(fixtureBytes),
  reference: referencePath, reference_sha256: hash(read(referencePath)),
  source_sha256: hash(read('analysis/a1_branch_world_source.mjs')),
  arithmetic_sha256: hash(read('analysis/a1_weighted_browser.mjs')),
  audit_sha256: hash(read('analysis/a1_branch_period_browser_audit.mjs')),
  worlds: source.worlds, player, checks, overtime_period_categories_checked: overtimeChecks,
  opening_starter_counts_checked: openingChecks,
}, null, 2) + '\n', {flag: 'wx'});
console.log(`${source.worlds} worlds: 21 weighted period means, ${overtimeChecks} overtime masses and ${openingChecks} starter counts match independently decoded captures`);
