#!/usr/bin/env node
// Measure an on-demand exact minute distribution against saved branch fixtures.
import {createHash} from 'node:crypto';
import {existsSync, readFileSync, writeFileSync} from 'node:fs';
import {performance} from 'node:perf_hooks';
import {branchWorldSource} from './a1_branch_world_source.mjs';
import {minuteBins, minuteDistribution, minuteThreshold} from './a1_precise_minutes.mjs';

const [fixturePath, choicesText, outputPath, reportPath] = process.argv.slice(2);
if (!fixturePath || !choicesText || !outputPath || !reportPath) {
  throw new Error('Provide fixture, JSON choices, new output path and new report path');
}
if (existsSync(outputPath) || existsSync(reportPath)) throw new Error('Refusing to overwrite an experiment');
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const start = performance.now(), bytes = readFileSync(fixturePath), fixture = JSON.parse(bytes);
const source = branchWorldSource(fixture), decoded = performance.now();
const choices = JSON.parse(choicesText), mask = source.selection(choices), rows = [];
for (const player of source.players) for (const period of ['q1', 'q2', 'q3', 'q4', 'h1', 'h2', 'fg']) {
  const d = minuteDistribution(source.playerValues(player, 'min', period), source.weights, mask);
  if (!d) throw new Error('No selected worlds');
  rows.push({player, period, mass: d.mass, worlds: d.worlds, mean: d.mean, quantiles: d.quantiles,
    thresholds: Object.fromEntries([0, 10, 20, 30, 40, 48].map(line => [line, minuteThreshold(d, line)])),
    bins: minuteBins(d, 30)});
}
const done = performance.now();
const output = JSON.stringify({fixture: fixturePath, fixture_sha256: hash(bytes), choices, rows});
writeFileSync(outputPath, output, {flag: 'wx'});
writeFileSync(reportPath, JSON.stringify({
  kind: 'isolated precise-minute distribution probe; not a forecast or browser/phone benchmark',
  fixture: fixturePath, fixture_sha256: hash(bytes), choices, output: outputPath, output_sha256: hash(output),
  source_sha256: hash(readFileSync('analysis/a1_branch_world_source.mjs')),
  arithmetic_sha256: hash(readFileSync('scripts/webapp/weighted-worlds.mjs')),
  algorithm_sha256: hash(readFileSync('analysis/a1_precise_minutes.mjs')),
  probe_sha256: hash(readFileSync('analysis/a1_precise_minutes_probe.mjs')),
  distributions: rows.length, selected_worlds: rows[0].worlds, selected_mass: rows[0].mass,
  decode_seconds: (decoded - start) / 1000, distribution_seconds: (done - decoded) / 1000,
  output_bytes: Buffer.byteLength(output), max_rss_kib: process.resourceUsage().maxRSS,
}, null, 2) + '\n', {flag: 'wx'});
console.log(`${rows.length} distributions in ${((done - decoded) / 1000).toFixed(2)}s`);
