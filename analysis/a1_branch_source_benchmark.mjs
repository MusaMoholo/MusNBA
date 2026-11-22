#!/usr/bin/env node
// Isolated Node benchmark of saved branch loading; not a browser or forecast benchmark.
import {createHash} from 'node:crypto';
import {readFileSync, statSync, writeFileSync} from 'node:fs';
import {branchWorldSource} from './a1_branch_world_source.mjs';
import {distribution} from './a1_weighted_browser.mjs';

const [path, output] = process.argv.slice(2);
if (!path || !output) throw new Error('Provide fixture and new output paths');
const start = performance.now(), bytes = readFileSync(path);
const fixture = JSON.parse(bytes.toString('utf8')), parsed = performance.now();
const source = branchWorldSource(fixture), loaded = performance.now();
const player = fixture.selected_players[0].player_id, summaries = {};
for (const period of ['q1', 'q2', 'q3', 'q4', 'h1', 'h2', 'fg']) {
  const mins = source.playerValues(player, 'min', period);
  const points = source.playerValues(player, 'pts', period);
  const teamPoints = source.teamPoints('home', period);
  summaries[period] = {
    minutes_mean: distribution(mins, source.weights).mean,
    player_points_mean: distribution(points, source.weights).mean,
    home_points_mean: distribution(teamPoints, source.weights).mean,
  };
}
const ended = performance.now();
writeFileSync(output, JSON.stringify({
  kind: 'isolated Node branch source benchmark; not a browser, phone or forecast benchmark',
  fixture: path, fixture_sha256: createHash('sha256').update(bytes).digest('hex'),
  source_sha256: createHash('sha256').update(readFileSync('analysis/a1_branch_world_source.mjs')).digest('hex'),
  script_sha256: createHash('sha256').update(readFileSync('analysis/a1_branch_source_benchmark.mjs')).digest('hex'),
  fixture_bytes: statSync(path).size, worlds: source.worlds, player,
  seconds: {read_parse: (parsed - start) / 1000, load_validate: (loaded - parsed) / 1000,
    seven_period_summaries: (ended - loaded) / 1000},
  max_rss_kb: process.resourceUsage().maxRSS, summaries,
}, null, 2) + '\n', {flag: 'wx'});
console.log(`${source.worlds} worlds: read/parse ${((parsed - start) / 1000).toFixed(2)}s, ` +
  `load/validate ${((loaded - parsed) / 1000).toFixed(2)}s, seven period summaries ${((ended - loaded) / 1000).toFixed(2)}s`);
