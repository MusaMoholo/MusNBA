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
writeFileSync(output, JSON.stringify({
  kind: 'isolated browser source period accounting; not a forecast or browser integration',
  fixture: fixturePath, fixture_sha256: hash(fixtureBytes),
  reference: referencePath, reference_sha256: hash(read(referencePath)),
  source_sha256: hash(read('analysis/a1_branch_world_source.mjs')),
  audit_sha256: hash(read('analysis/a1_branch_period_browser_audit.mjs')),
  worlds: source.worlds, player, checks,
}, null, 2) + '\n', {flag: 'wx'});
console.log(`${source.worlds} worlds: 21 weighted player/team period means match independently decoded captures`);
