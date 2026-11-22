#!/usr/bin/env node
// Run an isolated selected-world summary; this is not a forecast or serving contract.
import {createHash} from 'node:crypto';
import {readFileSync, writeFileSync} from 'node:fs';
import {performance} from 'node:perf_hooks';
import {branchWorldSource} from './a1_branch_world_source.mjs';
import {branchGameSummary} from './a1_branch_game_summary.mjs';

const [fixturePath, choicesText, summaryPath, reportPath] = process.argv.slice(2);
if (!fixturePath || !choicesText || !summaryPath || !reportPath) {
  throw new Error('Provide fixture, JSON lineup choices, new summary path and new report path');
}
const hash = data => createHash('sha256').update(data).digest('hex');
const start = performance.now(), bytes = readFileSync(fixturePath), fixture = JSON.parse(bytes);
const source = branchWorldSource(fixture), decoded = performance.now(), choices = JSON.parse(choicesText);
const result = branchGameSummary(source, choices), finished = performance.now();
const output = JSON.stringify({kind: 'isolated research summary; not a forecast', fixture: fixturePath,
  fixture_sha256: hash(bytes), choices, result});
writeFileSync(summaryPath, output, {flag: 'wx'});
writeFileSync(reportPath, JSON.stringify({
  kind: 'isolated game-summary performance probe; not a browser or phone benchmark',
  fixture: fixturePath, fixture_sha256: hash(bytes), choices, summary: summaryPath, summary_sha256: hash(output),
  source_sha256: hash(readFileSync('analysis/a1_branch_world_source.mjs')),
  arithmetic_sha256: hash(readFileSync('scripts/webapp/weighted-worlds.mjs')),
  algorithm_sha256: hash(readFileSync('analysis/a1_branch_game_summary.mjs')),
  probe_sha256: hash(readFileSync('analysis/a1_branch_game_summary_probe.mjs')),
  worlds: source.worlds, selected_worlds: result.selected_worlds, selected_mass: result.selected_mass,
  total_mass: result.total_mass, summary_bytes: Buffer.byteLength(output),
  decode_seconds: (decoded - start) / 1000, summary_seconds: (finished - decoded) / 1000,
  max_rss_kib: process.resourceUsage().maxRSS,
}, null, 2) + '\n', {flag: 'wx'});
console.log(`${result.selected_worlds}/${source.worlds} worlds summarized in ${((finished - decoded) / 1000).toFixed(2)}s`);
