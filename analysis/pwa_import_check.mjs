#!/usr/bin/env node
// Optional end-to-end check of the static PWA: fresh profile → shell asks for data → import a
// bundle through the real file input → app renders → service worker controls the page → reload
// offline still renders from IndexedDB. DevTools protocol only; no npm packages.
//
//   node analysis/pwa_import_check.mjs --url http://127.0.0.1:8768/MusNBA/ --bundle /path/MusNBA.musnba.gz [--out dir]
import {spawn} from 'node:child_process';
import {mkdtempSync, rmSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';

const args = Object.fromEntries(process.argv.slice(2).reduce((acc, a, i, all) => a.startsWith('--') ? [...acc, [a.slice(2), all[i + 1]]] : acc, []));
if (!args.url || !args.bundle) { console.error('usage: --url <shell url> --bundle <file.musnba.gz> [--out dir]'); process.exit(2); }
const CHROME = args.chrome || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const profile = mkdtempSync(join(tmpdir(), 'musnba-pwa-'));
const chrome = spawn(CHROME, ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check', 'about:blank'], {stdio: ['ignore', 'ignore', 'pipe']});
const wsUrl = await new Promise((resolve, reject) => {
  let b = ''; chrome.stderr.on('data', d => { b += d; const m = b.match(/DevTools listening on (ws:\/\/\S+)/); if (m) resolve(m[1]); });
  setTimeout(() => reject(new Error('Chrome did not start')), 15000);
});
const ws = new WebSocket(wsUrl);
await new Promise(r => ws.addEventListener('open', r, {once: true}));
let seq = 0; const pending = new Map(); const errors = [];
ws.addEventListener('message', e => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.reject(new Error(m.error.message)) : p.resolve(m.result); }
  else if (m.method === 'Runtime.exceptionThrown') errors.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text);
});
const send = (method, params = {}, sessionId) => new Promise((resolve, reject) => { const id = ++seq; pending.set(id, {resolve, reject}); ws.send(JSON.stringify({id, method, params, ...(sessionId ? {sessionId} : {})})); });
const sleep = ms => new Promise(r => setTimeout(r, ms));
const {targetId} = await send('Target.createTarget', {url: 'about:blank'});
const {sessionId: s} = await send('Target.attachToTarget', {targetId, flatten: true});
for (const d of ['Page', 'Runtime', 'DOM', 'Network']) await send(d + '.enable', {}, s);
await send('Emulation.setDeviceMetricsOverride', {width: 390, height: 844, deviceScaleFactor: 2, mobile: true}, s);
const evaluate = async expression => (await send('Runtime.evaluate', {expression, returnByValue: true, awaitPromise: true}, s)).result.value;
const waitFor = async (expression, ms = 20000) => { for (const end = Date.now() + ms; Date.now() < end; await sleep(200)) if (await evaluate(expression).catch(() => false)) return true; return false; };
const results = [];
const check = (name, ok, detail = '') => { results.push({name, ok, detail}); console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  ' + detail : ''}`); };

await send('Page.navigate', {url: args.url}, s);
check('fresh install asks for data', await waitFor(`document.querySelector('#pwa-status')?.textContent.includes('Import your')`));
const {root} = await send('DOM.getDocument', {}, s);
const {nodeId} = await send('DOM.querySelector', {nodeId: root.nodeId, selector: '#pwa-file'}, s);
const started = Date.now();
await send('DOM.setFileInputFiles', {nodeId, files: [args.bundle]}, s);
check('import completes and app renders slate', await waitFor(`!!document.querySelector('.game-card') && document.querySelector('#pwa-status')?.textContent.includes('Saved data through')`, 120000), `${((Date.now() - started) / 1000).toFixed(1)}s`);
check('logo served from imported data', await waitFor(`[...document.querySelectorAll('img.logo')].some(i => i.complete && i.naturalWidth > 0)`, 15000));
await send('Page.navigate', {url: args.url + '#/game/401910009'}, s);
check('game centre renders from storage', await waitFor(`document.querySelector('.bezel') && !!document.querySelector('[data-mode=cmp]')`));
check('service worker controls page', await waitFor(`!!navigator.serviceWorker.controller`, 15000) || (await send('Page.reload', {}, s), await waitFor(`!!navigator.serviceWorker.controller`, 15000)));
await send('Network.emulateNetworkConditions', {offline: true, latency: 0, downloadThroughput: -1, uploadThroughput: -1}, s);
await send('Page.navigate', {url: args.url + '#/standings'}, s);
check('offline reload renders standings', await waitFor(`document.body.textContent.includes('Standings & season forecast') && !!document.querySelector('td.heat')`));
await send('Page.navigate', {url: args.url + '#/standings/races'}, s);
check('offline races render their own forecast content', await waitFor(`!!document.querySelector('.race-row') && document.body.textContent.includes('Season races')`));
await send('Page.navigate', {url: args.url + '#/standings/leaders'}, s);
check('offline leaders have nine player and six team cards', await waitFor(`document.querySelectorAll('.leaders-grid')[0]?.children.length === 9 && document.querySelectorAll('.leaders-grid')[1]?.children.length === 6 && !document.querySelector('.race-row')`));
check('leader qualification copy follows loaded games played', await evaluate(`(async () => {
  const ui = await import('./assets/ui.mjs'), page = await import('./assets/season.mjs');
  const data = await ui.api('standings/' + ui.meta().latest);
  data.teams.forEach(t => t.gp = 40);
  await page.render(document.querySelector('#view'), {meta: ui.meta(), current: () => true, rest: ['leaders']});
  return document.querySelector('#view').textContent.includes('minimum 28 games') && document.querySelector('#view').textContent.includes('No qualifying players yet');
})()`));
await send('Page.navigate', {url: args.url + '#/standings/movers'}, s);
check('offline movers read imported comparisons', await waitFor(`document.querySelector('#view').textContent.includes('Since the previous forecast')`));
await send('Page.navigate', {url: args.url + '#/about'}, s);
check('model guide works offline', await waitFor(`document.querySelector('#view').textContent.includes('Reading the numbers')`));
check('model guide numbers follow loaded simulation counts', await evaluate(`(async () => {
  const ui = await import('./assets/ui.mjs'), page = await import('./assets/about.mjs');
  ui.meta().model.sims = 1234;
  (await ui.api('standings/' + ui.meta().latest)).sims = 4321;
  await page.render(document.querySelector('#view'), {meta: ui.meta(), current: () => true});
  const text = document.querySelector('#view').textContent;
  return text.includes('1,234 possible outcomes') && text.includes('740 of 1,234') && text.includes('4,321 possible seasons');
})()`));
const repeat = await evaluate(`(async () => { const {importBundle} = await import('./assets/pwa-storage.mjs'); return 'ok'; })()`).catch(e => String(e));
check('storage module loads offline', repeat === 'ok', repeat === 'ok' ? '' : repeat);
if (args.out) { const shot = await send('Page.captureScreenshot', {format: 'png'}, s); writeFileSync(join(args.out, 'pwa-offline-standings.png'), Buffer.from(shot.data, 'base64')); }
check('no uncaught exceptions', errors.length === 0, errors.slice(0, 2).join(' | '));
ws.close(); chrome.kill();
try { rmSync(profile, {recursive: true, force: true}); } catch { /* best effort */ }
const failed = results.filter(r => !r.ok).length;
console.log(`\n${results.length - failed}/${results.length} passed`);
process.exit(failed ? 1 : 0);
