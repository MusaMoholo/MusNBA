#!/usr/bin/env node
// Record adaptive weighted grid bins for independent comparison; research only.
import {createHash} from 'node:crypto';
import {readFileSync, writeFileSync} from 'node:fs';
import {branchWorldSource} from './a1_branch_world_source.mjs';
import {grid, gridEdges} from './a1_weighted_browser.mjs';

const [fixturePath, output] = process.argv.slice(2);
if (!fixturePath || !output) throw new Error('Provide fixture and new output paths');
const read = p => readFileSync(p);
const hash = data => createHash('sha256').update(data).digest('hex');
const file = read(fixturePath), fixture = JSON.parse(file), source = branchWorldSource(fixture);
const player = fixture.selected_players[0].player_id;
const x = source.playerValues(player, 'min'), y = source.teamPoints('home');
const xEdges = gridEdges(x, source.weights), yEdges = gridEdges(y, source.weights);
const result = grid(x, y, source.weights, xEdges, yEdges);
if (result.total !== source.denominator) throw new Error('Adaptive grid lost world mass');
writeFileSync(output, JSON.stringify({
  kind: 'isolated adaptive weighted grid; not a forecast or browser integration',
  fixture: fixturePath, fixture_sha256: hash(file), source: fixture.source, source_sha256: fixture.source_sha256,
  source_code_sha256: hash(read('analysis/a1_branch_world_source.mjs')),
  arithmetic_sha256: hash(read('scripts/webapp/weighted-worlds.mjs')),
  probe_sha256: hash(read('analysis/a1_dynamic_grid_probe.mjs')),
  worlds: source.worlds, player, denominator: source.denominator,
  x_edges: xEdges.map(x => Number.isFinite(x) ? x : null),
  y_edges: yEdges.map(y => Number.isFinite(y) ? y : null),
  cells: result.cells,
}, null, 2) + '\n', {flag: 'wx'});
console.log(`${source.worlds} worlds: ${xEdges.length - 1} × ${yEdges.length - 1} bins preserve all weighted mass`);
