#!/usr/bin/env node
// Produce research-only view data from previously audited inputs.
import {createHash} from 'node:crypto';
import {readFileSync, writeFileSync} from 'node:fs';
import {selectedGameView} from './a1_game_view_contract.mjs';

const [gamePath, payloadPath, summaryPath, viewPath, reportPath] = process.argv.slice(2);
if (!gamePath || !payloadPath || !summaryPath || !viewPath || !reportPath) {
  throw new Error('Provide game, payload, summary, new view and new report paths');
}
const hash = data => createHash('sha256').update(data).digest('hex');
const read = path => JSON.parse(readFileSync(path));
const game = read(gamePath).game, payload = read(payloadPath), summary = read(summaryPath);
const view = selectedGameView(game, payload, summary);
const output = JSON.stringify(view);
writeFileSync(viewPath, output, {flag: 'wx'});
const paths = [gamePath, payloadPath, summaryPath, 'analysis/a1_game_view_contract.mjs',
  'analysis/a1_game_view_contract_probe.mjs'];
writeFileSync(reportPath, JSON.stringify({
  kind: 'isolated selected game view contract; not a forecast or browser test',
  game: gamePath, payload: payloadPath, summary: summaryPath, view: viewPath, view_sha256: hash(output),
  source_sha256: Object.fromEntries(paths.map(path => [path, hash(readFileSync(path))])),
  selected_worlds: view.research.selected_worlds, selected_mass: view.research.selected_mass,
}, null, 2) + '\n', {flag: 'wx'});
console.log(`${view.research.selected_worlds} worlds, ${view.research.selected_mass} mass units adapted`);
