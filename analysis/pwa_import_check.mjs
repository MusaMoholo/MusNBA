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
check('forecast timing is honest for imported data', await evaluate(`(async () => {
  const ui = await import('./assets/ui.mjs'), game = await ui.api('game/401910009'), p = game.projection;
  if (!p) return false;
  let label = 'Timing unverified';
  if (p.kind === 'retrospective') label = 'Retrospective';
  else if (p.kind === 'prospective' && p.completed_at) {
    const before = new Date(p.completed_at) < new Date(game.game.tip_utc);
    if (p.pre_tip !== before) return false;
    label = before ? 'Pre-game' : 'Built after tip-off';
  }
  return document.querySelector('.bezel').textContent.includes(label);
})()`));
await send('Page.navigate', {url: args.url + '#/team/14'}, s);
check('phone team form stacks chart and fixtures', await waitFor(`(() => { const items = [...document.querySelectorAll('.form-grid > div')]; return items.length === 2 && items[1].getBoundingClientRect().top >= items[0].getBoundingClientRect().bottom - 1; })()`));
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
await send('Page.navigate', {url: args.url + '#/players'}, s);
check('offline player minutes filter follows the loaded season', await waitFor(`!!document.querySelector('#pg')`) && await evaluate(`(async () => {
  const ui = await import('./assets/ui.mjs'), players = await ui.api('players'), standings = await ui.api('standings/' + ui.meta().latest);
  const benchmark = 48 * Math.max(...standings.teams.map(t => t.gp));
  const expected = players.players.filter(p => p.gp > 0 && benchmark > 0 && Number.isFinite(p.tot.min) && p.tot.min >= 0.25 * benchmark).length;
  const select = document.querySelector('#pg'); select.value = '0.25'; select.dispatchEvent(new Event('change', {bubbles: true}));
  return document.querySelector('#ptable .row .note')?.textContent.includes('of ' + expected + ' players')
    && document.querySelector('#view').textContent.includes(benchmark.toLocaleString() + ' regulation minutes');
})()`));
const shootingTarget = await evaluate(`(async () => {
  const ui = await import('./assets/ui.mjs'), slate = await ui.api('slate/' + ui.meta().latest);
  for (const fixture of slate.games) {
    const game = await ui.api('game/' + fixture.id), sim = game.projection?.sim;
    if (sim?.shooting_distribution_schema !== 1 || game.worlds) continue;
    for (const side of ['home', 'away']) for (const p of sim[side].players) {
      const stats = p.periods?.q1?.stats, d = stats?.fgpct;
      if (d && stats.fg3pct && stats.ftpct) return {game: fixture.id, player: p.id, defined: d.defined, total: d.total};
    }
  }
  return null;
})()`);
if (shootingTarget) {
  await send('Page.navigate', {url: args.url + '#/game/' + shootingTarget.game + '/player/' + shootingTarget.player + '/q1'}, s);
  const ready = await waitFor(`!!document.querySelector('[data-stat="fgpct"]')`);
  check('offline period shooting distribution preserves no-attempt worlds', ready && await evaluate(`(async () => {
    document.querySelector('[data-stat="fgpct"]').click();
    const ui = await import('./assets/ui.mjs'), text = document.querySelector('#stat-block').textContent;
    return ['fgm', 'fga', 'fgpct', 'fg3m', 'fg3a', 'fg3pct', 'ftm', 'fta', 'ftpct']
      .every(stat => !!document.querySelector('[data-stat="' + stat + '"]'))
      && text.includes('conditional on an attempt')
      && text.includes('No field-goal attempts in ' + ui.pct((${shootingTarget.total} - ${shootingTarget.defined}) / ${shootingTarget.total}, 1))
      && text.includes(${JSON.stringify(shootingTarget.defined.toLocaleString())} + ' of ' + ${JSON.stringify(shootingTarget.total.toLocaleString())});
  })()`));
} else if (args['require-shooting']) check('offline period shooting distribution present in new bundle', false);
await send('Page.navigate', {url: args.url + '#/about'}, s);
check('model guide works offline', await waitFor(`document.querySelector('#view').textContent.includes('Reading the numbers')`));
await send('Page.navigate', {url: args.url + '#/lab'}, s);
check('starter-score timing stays honest offline', await waitFor(`document.querySelector('#view').textContent.includes('Projected starters — nightly record')`)
  && await evaluate(`(async () => {
    const ui = await import('./assets/ui.mjs'), lab = await ui.api('lab'), lineups = lab.lineups;
    const text = [...document.querySelectorAll('#view section')].find(x => x.querySelector('h2')?.textContent.includes('Projected starters'))?.textContent || '';
    const verified = lineups?.timing_policy === 'completed_before_tip-v1' && !!lineups?.overall;
    return verified ? text.includes('Verified pre-tip projected starters') : text.includes('No verified pre-tip starter forecasts scored yet.');
  })()`));
await send('Page.navigate', {url: args.url + '#/about'}, s);
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
