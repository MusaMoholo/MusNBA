#!/usr/bin/env node
// Isolated browser check against retained branch captures; never exposes a production switch.
import {createHash} from 'node:crypto';
import {createReadStream, mkdtempSync, readFileSync, rmSync, writeFileSync} from 'node:fs';
import {createServer} from 'node:http';
import {spawn} from 'node:child_process';
import {tmpdir} from 'node:os';
import {join} from 'node:path';

const [base, fixturePath, fullPath, minutePath, emptyPath, gridPath, gridAuditPath, output] = process.argv.slice(2);
if (!base || !fixturePath || !fullPath || !minutePath || !emptyPath || !gridPath || !gridAuditPath || !output
    || !/^http:\/\/127\.0\.0\.1:\d+$/.test(base)) {
  throw new Error('Provide local URL, fixture, full/minute/empty references, grid probe/audit and new report path');
}
const hash = path => createHash('sha256').update(readFileSync(path)).digest('hex');
const read = path => JSON.parse(readFileSync(path));
const full = read(fullPath), minute = read(minutePath), empty = read(emptyPath);
const grid = read(gridPath), gridAudit = read(gridAuditPath);
if (full.source_sha256 !== minute.source_sha256 || full.source_sha256 !== empty.source_sha256
    || grid.source_sha256 !== full.source_sha256 || gridAudit.probe !== gridPath || gridAudit.probe_sha256 !== hash(gridPath)
    || gridAudit.cells_checked !== grid.cells.length * grid.cells[0].length
    || full.event !== 'home team wins' || full.given !== empty.given
    || minute.event !== full.event || !/^player \d+ has positive simulated minutes$/.test(full.given)
    || !/^player \d+ has at least 1800 simulated seconds$/.test(minute.given)
    || empty.result.status !== 'no matching condition worlds') throw new Error('References do not match');
const game = full.game, player = /^player (\d+)/.exec(full.given)[1];
if (minute.game !== game || empty.game !== game || !minute.given.startsWith(`player ${player} `)) {
  throw new Error('Reference game or player differs');
}
const files = {'/fixture': fixturePath, '/source.mjs': 'analysis/a1_branch_world_source.mjs',
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
const profile = mkdtempSync(join(tmpdir(), 'musnba-a1-browser-'));
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
    } else if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails.text);
  });
  const send = (method, params = {}, sessionId) => new Promise((resolve, reject) => {
    const id = ++seq; pending.set(id, {resolve, reject});
    ws.send(JSON.stringify({id, method, params, ...(sessionId ? {sessionId} : {})}));
  });
  const {targetId} = await send('Target.createTarget', {url: 'about:blank'});
  const {sessionId} = await send('Target.attachToTarget', {targetId, flatten: true});
  for (const domain of ['Page', 'Runtime']) await send(domain + '.enable', {}, sessionId);
  await send('Emulation.setDeviceMetricsOverride', {width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false}, sessionId);
  await send('Page.navigate', {url: `${base}/#/game/${game}/scenario`}, sessionId);
  const evaluate = async expression => {
    const result = await send('Runtime.evaluate', {expression, awaitPromise: true, returnByValue: true}, sessionId);
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
    return result.result.value;
  };
  for (let n = 0; n < 100; n++) {
    if (await evaluate("!!document.querySelector('#game-body')")) break;
    await new Promise(resolve => setTimeout(resolve, 100));
    if (n === 99) throw new Error('Game view did not load');
  }
  const exercise = async (fixtureUrl, gameId, id, sourceHash, choices) => {
    const start = performance.now(), response = await fetch(fixtureUrl + '/fixture');
    if (!response.ok) throw new Error('Fixture fetch failed');
    const fixture = await response.json(), parsed = performance.now();
    if (fixture.game !== gameId || fixture.source_sha256 !== sourceHash) throw new Error('Fixture provenance differs');
    const {branchWorldSource} = await import(fixtureUrl + '/source.mjs');
    const source = branchWorldSource(fixture), decoded = performance.now();
    const O = await import('./assets/outcomes.mjs'), S = await import('./assets/scenario.mjs');
    const dataResponse = await fetch('./api/game/' + gameId);
    if (!dataResponse.ok) throw new Error('Game fetch failed');
    const data = await dataResponse.json(), el = document.querySelector('#game-body');
    data._branchWorldData = O.branchWorldData(source);
    const condition = [{subj: 'p:' + id, v: 'min', op: 'ge', x: 30}];
    await S.scenarioView(el, data, S.encode(condition));
    const rendered = performance.now(), scenario = el.querySelector('.tile')?.innerText;
    const home = el.querySelectorAll('table tbody tr')[1];
    const scenarioText = el.innerText;
    await S.sheetPanels(el, data, id, 'min', 30.5);
    const subject = el.querySelector('[data-builder="joint"] [data-b="subj"]');
    subject.value = 't:home';
    subject.dispatchEvent(new Event('change'));
    const sheet = el.innerText, sheetFinished = performance.now();
    const gridRows = [...el.querySelectorAll('table.grid tbody tr')].slice(0, -2).reverse()
      .map(row => [...row.querySelectorAll('td')].slice(1).map(cell => cell.textContent));
    data._branchWorldData = O.branchWorldData(source, choices);
    await S.scenarioView(el, data, S.encode([{subj: 'p:' + id, v: 'plays'}]));
    return {worlds: source.worlds, scenario, home: home?.innerText, scenarioText: scenarioText.slice(0, 300),
      sheetGiven: sheet.match(/wins: [^\n]*/)?.[0], gridRows, weightedGrid: sheet.includes('Share of probability'),
      empty: el.innerText.includes('No simulated game matches every condition'),
      seconds: {parse: (parsed - start) / 1000, decode: (decoded - parsed) / 1000,
        scenario: (rendered - decoded) / 1000, sheet: (sheetFinished - rendered) / 1000},
      heap_bytes: performance.memory?.usedJSHeapSize ?? null};
  };
  const result = await evaluate(`(${exercise})(${JSON.stringify(fixtureOrigin)},${JSON.stringify(game)},${JSON.stringify(player)},${JSON.stringify(full.source_sha256)},${JSON.stringify(empty.lineup_conditions)})`);
  const percent = fraction => (100 * Number(fraction.numerator) / Number(fraction.denominator)).toFixed(1) + '%';
  const gridLabels = grid.cells.map(row => row.map(mass => mass
    ? (100 * mass / grid.denominator < 0.5 ? '<1' : (100 * mass / grid.denominator).toFixed(0)) + '%' : '–'));
  if (result.worlds !== full.worlds || !result.scenario.includes(percent(minute.result.condition))
      || !result.scenario.includes('weighted chance') || !result.home?.includes(percent(minute.result.given))
      || !result.sheetGiven?.includes(percent(full.result.event)) || !result.weightedGrid
      || JSON.stringify(result.gridRows) !== JSON.stringify(gridLabels) || !result.empty || errors.length) {
    throw new Error(`Browser results differ from independent references: ${JSON.stringify({result, errors})}`);
  }
  const paths = [fixturePath, fullPath, minutePath, emptyPath, gridPath, gridAuditPath, 'analysis/a1_scenario_browser_check.mjs',
    'analysis/a1_branch_world_source.mjs', 'scripts/webapp/weighted-worlds.mjs',
    'scripts/webapp/outcomes.mjs', 'scripts/webapp/scenario.mjs'];
  writeFileSync(output, JSON.stringify({
    kind: 'isolated local browser scenario check; not a forecast or phone acceptance',
    source_sha256: Object.fromEntries(paths.map(path => [path, hash(path)])), result,
    limitations: ['Research source was injected only for this check; no branch control is shipped.',
      'Original game metadata and player ordering were retained; this does not prove a coherent full Game Centre.',
      'One desktop browser run is not a phone or offline benchmark.'],
  }, null, 2) + '\n', {flag: 'wx'});
  console.log(`${result.worlds} worlds: exact-minute scenario, Given, ${gridAudit.cells_checked} Joint cells and empty branch matched`);
} finally {
  if (ws) ws.close();
  chrome.kill();
  server.close();
  try { rmSync(profile, {recursive: true, force: true}); } catch (error) { console.error(`Could not remove browser profile ${profile}: ${error.message}`); }
}
