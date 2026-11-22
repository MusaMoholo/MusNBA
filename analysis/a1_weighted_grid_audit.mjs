#!/usr/bin/env node
// Compare research browser grids and correlations with the independent Python reconstruction.
import {createHash} from 'node:crypto';
import {readFileSync, writeFileSync} from 'node:fs';
import {branchWeights, correlation, grid} from './a1_weighted_browser.mjs';

const [fixturePath, referencePath, output] = process.argv.slice(2);
if (!fixturePath || !referencePath || !output || process.argv.length !== 5) throw new Error('Provide fixture, grid reference and new output paths');
const read = p => JSON.parse(readFileSync(p, 'utf8'));
const sha = p => createHash('sha256').update(readFileSync(p)).digest('hex');
const fixture = read(fixturePath), reference = read(referencePath);
if (fixture.game !== reference.game || fixture.source_sha256 !== reference.source_sha256) throw new Error('Grid sources differ');
const {weights} = branchWeights(fixture.branches.map(b => ({worlds: b.worlds.worlds, weight: b.weight})));
const x = new Float64Array(weights.length), y = new Float64Array(weights.length);
let offset = 0;
for (const branch of fixture.branches) {
  const raw = branch.worlds, index = raw.players.indexOf(reference.player);
  if (index < 0 || raw.players.lastIndexOf(reference.player) !== index) throw new Error('Grid player missing or duplicated');
  const minutes = Buffer.from(raw.minutes_f64_le, 'base64'), periods = Buffer.from(raw.team_periods, 'base64');
  if (minutes.length !== raw.worlds * raw.players.length * 8 || periods.length !== raw.worlds * 10) throw new Error('Malformed packed worlds');
  for (let w = 0; w < raw.worlds; w++) {
    x[offset + w] = minutes.readDoubleLE((w * raw.players.length + index) * 8);
    for (let q = 0; q < 5; q++) y[offset + w] += periods[w * 10 + q];
  }
  offset += raw.worlds;
}
const result = grid(x, y, weights, [-Infinity, reference.x_threshold_minutes, Infinity],
  [-Infinity, reference.y_threshold_home_points, Infinity]);
const r = correlation(x, y, weights);
if (r == null || Math.abs(r - reference.correlation) > 1e-12 || weights.length !== reference.worlds) {
  throw new Error('Weighted correlation or world count differs');
}
for (let row = 0; row < 2; row++) for (let col = 0; col < 2; col++) {
  const expected = reference.cells[row][col];
  if (BigInt(result.cells[row][col]) * BigInt(expected.denominator) !== BigInt(result.total) * BigInt(expected.numerator)) {
    throw new Error('Exact grid cell differs');
  }
}
const sources = [fixturePath, referencePath, 'analysis/a1_weighted_browser.mjs', 'analysis/a1_weighted_grid_audit.mjs'];
writeFileSync(output, JSON.stringify({
  kind: 'isolated browser weighted grid/correlation accounting; not a forecast or browser integration',
  source_sha256: Object.fromEntries(sources.map(p => [p, sha(p)])),
  worlds: weights.length, cells: result.cells, total: result.total, correlation: r,
  limitations: ['One research game; not an accuracy or dependence validation.',
    'No phone or UI test is implied.'],
}, null, 2) + '\n', {flag: 'wx'});
console.log(`${weights.length} worlds: exact grid cells and weighted correlation match`);
