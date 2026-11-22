#!/usr/bin/env node
// Exercise the explicitly injected research Game Centre against independently audited summaries.
import {createHash} from 'node:crypto';
import {createReadStream, mkdtempSync, readFileSync, rmSync, writeFileSync} from 'node:fs';
import {createServer} from 'node:http';
import {spawn} from 'node:child_process';
import {tmpdir} from 'node:os';
import {join} from 'node:path';

const [base, fixturePath, payloadPath, fullPath, partialPath, fullAuditPath, partialAuditPath, output] = process.argv.slice(2);
if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(base || '') || !output || !partialAuditPath) {
  throw new Error('Provide local URL, fixture, payload, full/partial summaries and audits, and new report path');
}
const hash = path => createHash('sha256').update(readFileSync(path)).digest('hex');
const read = path => JSON.parse(readFileSync(path));
const payload = read(payloadPath), full = read(fullPath), partial = read(partialPath);
const fullAudit = read(fullAuditPath), partialAudit = read(partialAuditPath);
if (hash(fixturePath) !== payload.fixture_sha256 || full.fixture_sha256 !== payload.fixture_sha256
    || partial.fixture_sha256 !== payload.fixture_sha256 || hash(fullPath) !== fullAudit.summary_sha256
    || hash(partialPath) !== partialAudit.summary_sha256 || Object.keys(full.result.choices).length
    || Object.keys(partial.result.choices).length !== 1
    || Object.values(partial.result.choices)[0] !== false) throw new Error('Audited inputs differ');
const id = Object.keys(partial.result.choices)[0], game = payload.game;
const side = payload.selected_players.find(p => p.player_id === id)?.team_id;
const files = {'/fixture': fixturePath, '/payload': payloadPath,
  '/source.mjs': 'analysis/a1_branch_world_source.mjs', '/summary.mjs': 'analysis/a1_branch_game_summary.mjs',
  '/contract.mjs': 'analysis/a1_game_view_contract.mjs',
  '/a1_weighted_browser.mjs': 'analysis/a1_weighted_browser.mjs',
  '/scripts/webapp/weighted-worlds.mjs': 'scripts/webapp/weighted-worlds.mjs'};
const server = createServer((request, response) => {
  const file = files[request.url];
  if (!file) { response.writeHead(404).end(); return; }
  response.setHeader('Access-Control-Allow-Origin', base);
  response.setHeader('Content-Type', request.url.endsWith('.mjs') ? 'text/javascript' : 'application/json');
  createReadStream(file).on('error', () => response.destroy()).pipe(response);
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const fixtureOrigin = `http://127.0.0.1:${server.address().port}`;
const profile = mkdtempSync(join(tmpdir(), 'musnba-a1-game-'));
const chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check', 'about:blank'],
  {stdio: ['ignore', 'ignore', 'pipe']});
let ws;
try {
  const url = await new Promise((resolve, reject) => {
    let text = '';
    chrome.stderr.on('data', data => { text += data; const match = text.match(/DevTools listening on (ws:\/\/\S+)/); if (match) resolve(match[1]); });
    chrome.once('exit', code => reject(new Error(`Chrome exited: ${code}`)));
    setTimeout(() => reject(new Error('Chrome did not start')), 15000).unref();
  });
  ws = new WebSocket(url);
  await new Promise(resolve => ws.addEventListener('open', resolve, {once: true}));
  let seq = 0;
  const pending = new Map(), errors = [];
  ws.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (pending.has(message.id)) {
      const promise = pending.get(message.id); pending.delete(message.id);
      message.error ? promise.reject(new Error(message.error.message)) : promise.resolve(message.result);
    } else if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text);
    else if (message.method === 'Runtime.consoleAPICalled' && message.params.type === 'error') errors.push(message.params.args.map(a => a.value ?? a.description).join(' '));
  });
  const send = (method, params = {}, sessionId) => new Promise((resolve, reject) => {
    const requestId = ++seq; pending.set(requestId, {resolve, reject});
    ws.send(JSON.stringify({id: requestId, method, params, ...(sessionId ? {sessionId} : {})}));
  });
  const {targetId} = await send('Target.createTarget', {url: 'about:blank'});
  const {sessionId} = await send('Target.attachToTarget', {targetId, flatten: true});
  await send('Page.enable', {}, sessionId);
  await send('Runtime.enable', {}, sessionId);
  await send('Emulation.setDeviceMetricsOverride', {width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false}, sessionId);
  await send('Page.navigate', {url: `${base}/#/game/${game}`}, sessionId);
  const evaluate = async expression => {
    const result = await send('Runtime.evaluate', {expression, awaitPromise: true, returnByValue: true}, sessionId);
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
    return result.result.value;
  };
  for (let n = 0; n < 100; n++) {
    if (await evaluate("!!document.querySelector('#game-body')")) break;
    await new Promise(resolve => setTimeout(resolve, 100));
    if (n === 99) throw new Error('Game did not load');
  }
  const initialise = async (fixtureUrl, gameId) => {
    const [fixture, payload, original] = await Promise.all([
      fetch(fixtureUrl + '/fixture').then(r => r.json()),
      fetch(fixtureUrl + '/payload').then(r => r.json()),
      fetch('./api/game/' + gameId).then(r => r.json()),
    ]);
    const {branchWorldSource} = await import(fixtureUrl + '/source.mjs');
    const {branchGameSummary} = await import(fixtureUrl + '/summary.mjs');
    const {selectedGameView} = await import(fixtureUrl + '/contract.mjs');
    const O = await import('./assets/outcomes.mjs'), G = await import('./assets/game.mjs');
    window.__a1 = {payload, game: original.game, selectedGameView, G};
    const source = branchWorldSource(fixture), cache = new Map();
    G.setResearchGame(gameId, async choices => {
      const key = JSON.stringify(choices);
      if (!cache.has(key)) {
        const summary = {fixture_sha256: payload.fixture_sha256, result: branchGameSummary(source, choices)};
        cache.set(key, {view: selectedGameView(original.game, payload, summary), worlds: O.branchWorldData(source, choices)});
      }
      return cache.get(key);
    });
    await G.render(document.querySelector('#view'), {rest: [gameId], current: () => true});
    return true;
  };
  await evaluate(`(${initialise})(${JSON.stringify(fixtureOrigin)},${JSON.stringify(game)})`);
  const snapshot = () => ({
    selected: document.querySelector('[data-lineup]')?.value,
    home: document.querySelector('.bz-team.home .bz-stats b')?.textContent,
    research: document.querySelector('[data-research-lineups]')?.innerText,
    body: document.querySelector('#view')?.innerText,
    overflow: document.documentElement.scrollWidth > innerWidth,
  });
  const expectedHome = r => r.periods.fg.home.pts.mean.toFixed(1);
  const rows = () => Object.fromEntries([...document.querySelectorAll('tr[data-pid]')].map(row => [
    row.dataset.pid, {minutes: row.cells[1].textContent, points: row.cells[2].textContent},
  ]));
  const compareRows = (actual, summary) => {
    for (const player of [...summary.home.players, ...summary.away.players]) {
      const secs = Math.round(player.periods.fg.sec);
      const minutes = `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, '0')}`;
      if (actual[player.id]?.minutes !== minutes || actual[player.id]?.points !== player.periods.fg.mean.pts.toFixed(1)) {
        throw new Error(`Selected player row differs: ${player.id}`);
      }
    }
  };
  const initial = await evaluate(`(${snapshot})()`);
  if (initial.home !== expectedHome(full.result) || !initial.research?.toLowerCase().includes('not a forecast')
      || !initial.body.toLowerCase().includes('top five by simulated opening-five chance')) {
    throw new Error(`Full-mixture game differs: ${JSON.stringify({home: initial.home, expected: expectedHome(full.result),
      research: initial.research, body: initial.body.slice(0, 1000), errors})}`);
  }
  compareRows(await evaluate(`(${rows})()`), full.result);
  const gameShot = await send('Page.captureScreenshot', {format: 'png'}, sessionId);
  writeFileSync(join(tmpdir(), 'musnba-a1-selected-game.png'), Buffer.from(gameShot.data, 'base64'));
  await evaluate(`(() => {const e=document.querySelector('[data-lineup="${id}"]'); e.value='unavailable'; e.dispatchEvent(new Event('change'));})()`);
  for (let n = 0; n < 400; n++) {
    if (await evaluate(`document.querySelector('[data-lineup="${id}"]')?.value === 'unavailable' && !document.querySelector('[data-lineup="${id}"]')?.disabled`)) break;
    await new Promise(resolve => setTimeout(resolve, 100));
    if (n === 399) throw new Error('Selected branch did not render');
  }
  const fixed = await evaluate(`(${snapshot})()`);
  if (fixed.home !== expectedHome(partial.result) || !fixed.research.includes('20,000 saved worlds')) {
    throw new Error(`Selected game differs: ${JSON.stringify({home: fixed.home, research: fixed.research})}`);
  }
  compareRows(await evaluate(`(${rows})()`), partial.result);
  await evaluate(`location.hash=${JSON.stringify(`#/game/${game}/player/${id}/fg`)}`);
  for (let n = 0; n < 200; n++) {
    if (await evaluate("!!document.querySelector('#stat-block') && !!document.querySelector('#what-if [data-builder=\"joint\"]')")) break;
    await new Promise(resolve => setTimeout(resolve, 100));
    if (n === 199) throw new Error('Player sheet did not load');
  }
  const sheet = await evaluate(`(${snapshot})()`);
  if (!sheet.research?.includes('20,000 saved worlds') || !sheet.body.toLowerCase().includes('available') || !sheet.body.toLowerCase().includes('plays')
      || !sheet.body.toLowerCase().includes('given…') || !sheet.body.toLowerCase().includes('joint outcomes')) {
    throw new Error(`Selected sheet differs: ${JSON.stringify({research: sheet.research, body: sheet.body.slice(0, 2500), errors})}`);
  }
  const sizes = [];
  for (const [width, height] of [[1440, 1000], [960, 1000], [390, 844]]) for (const theme of ['dark', 'light']) {
    await send('Emulation.setDeviceMetricsOverride', {width, height, deviceScaleFactor: 1, mobile: width === 390}, sessionId);
    const result = await evaluate(`(() => {document.documentElement.dataset.theme=${JSON.stringify(theme)}; return (${snapshot})();})()`);
    const shot = await send('Page.captureScreenshot', {format: 'png'}, sessionId);
    writeFileSync(join(tmpdir(), `musnba-a1-selected-${width}-${theme}.png`), Buffer.from(shot.data, 'base64'));
    if (result.overflow) throw new Error(`Research sheet overflows ${width} ${theme}`);
    sizes.push({width, theme});
  }
  await send('Emulation.setDeviceMetricsOverride', {width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false}, sessionId);
  await evaluate(`location.hash=${JSON.stringify(`#/game/${game}/fg/team`)}`);
  for (let n = 0; n < 200; n++) {
    if (await evaluate("!!document.querySelector('#game-body table.box') && !!document.querySelector('#drivers table')")) break;
    await new Promise(resolve => setTimeout(resolve, 100));
    if (n === 199) throw new Error('Selected team view did not load');
  }
  const teamView = await evaluate(`(${snapshot})()`);
  if (teamView.home !== expectedHome(partial.result) || !teamView.research.includes('20,000 saved worlds')) {
    throw new Error('Selected team view lost its selection');
  }
  const teamShot = await send('Page.captureScreenshot', {format: 'png'}, sessionId);
  writeFileSync(join(tmpdir(), 'musnba-a1-selected-team.png'), Buffer.from(teamShot.data, 'base64'));
  const condition = encodeURIComponent(JSON.stringify([{subj: `p:${id}`, v: 'plays'}]));
  await evaluate(`location.hash=${JSON.stringify(`#/game/${game}/scenario/${condition}`)}`);
  for (let n = 0; n < 200; n++) {
    if (await evaluate("document.querySelector('#game-body')?.innerText.includes('No simulated game matches every condition')")) break;
    await new Promise(resolve => setTimeout(resolve, 100));
    if (n === 199) throw new Error('Selected scenario did not show an empty condition');
  }
  const scenario = await evaluate(`(${snapshot})()`);
  if (!scenario.research.includes('20,000 saved worlds') || scenario.home !== expectedHome(partial.result)) {
    throw new Error('Selected scenario lost its selection');
  }
  const scenarioShot = await send('Page.captureScreenshot', {format: 'png'}, sessionId);
  writeFileSync(join(tmpdir(), 'musnba-a1-selected-scenario.png'), Buffer.from(scenarioShot.data, 'base64'));
  await evaluate(`(async () => {
    const {payload, game: g, selectedGameView, G} = window.__a1;
    G.setResearchGame(g.id, async () => ({view: selectedGameView(g, payload,
      {fixture_sha256: payload.fixture_sha256, result: payload.expected}), worlds: null}));
    await G.render(document.querySelector('#view'), {rest: [g.id], current: () => true});
  })()`);
  const expectedOnly = await evaluate(`(${snapshot})()`);
  if (expectedOnly.home !== expectedHome(full.result) || !expectedOnly.research.toLowerCase().includes('expected only')
      || await evaluate("!!document.querySelector('[data-lineup], [data-view=\"scenario\"]')")) {
    throw new Error('Expected-only research view exposes branches or differs from the audited full mixture');
  }
  compareRows(await evaluate(`(${rows})()`), full.result);
  if (errors.length) throw new Error(`Browser errors: ${errors.join('; ')}`);
  const paths = [fixturePath, payloadPath, fullPath, partialPath, fullAuditPath, partialAuditPath,
    'analysis/a1_game_view_browser_check.mjs', 'analysis/a1_game_view_contract.mjs', 'analysis/a1_branch_game_summary.mjs',
    'analysis/a1_branch_world_source.mjs', 'scripts/webapp/game.mjs', 'scripts/webapp/scenario.mjs',
    'scripts/webapp/outcomes.mjs', 'scripts/webapp/weighted-worlds.mjs'];
  writeFileSync(output, JSON.stringify({
    kind: 'isolated injected research Game Centre browser check; not a forecast or phone import',
    source_sha256: Object.fromEntries(paths.map(path => [path, hash(path)])), game, player: id, team: side,
    full_home_points: initial.home, selected_home_points: fixed.home, selected_worlds: partial.result.selected_worlds,
    sizes, expected_only_without_worlds: true, limitations: ['Research source was injected explicitly, not served to users.',
      'Phone viewport emulation is not a phone bundle import or real-device acceptance.'],
  }, null, 2) + '\n', {flag: 'wx'});
  console.log(`Full and fixed selections, team, sheet, empty scenario, Expected-only and ${sizes.length} viewport/theme cases passed`);
} finally {
  if (ws) ws.close();
  chrome.kill();
  server.close();
  try { rmSync(profile, {recursive: true, force: true}); } catch (error) { console.error(`Could not remove browser profile ${profile}: ${error.message}`); }
}
