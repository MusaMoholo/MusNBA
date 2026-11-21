#!/usr/bin/env node
// Optional browser acceptance: real device metrics, both colour schemes, console errors,
// horizontal overflow and full-page screenshots. Uses Chrome's DevTools protocol directly
// (Node 22+ global WebSocket) — no npm packages. Node is never a runtime dependency of the app.
//
//   node analysis/browser_check.mjs --base http://127.0.0.1:8767 --out /tmp/shots [--only today,game]
import {spawn} from 'node:child_process';
import {mkdirSync, mkdtempSync, writeFileSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';

const args = Object.fromEntries(process.argv.slice(2).reduce((acc, a, i, all) => a.startsWith('--') ? [...acc, [a.slice(2), all[i + 1]?.startsWith('--') ? true : all[i + 1] ?? true]] : acc, []));
const BASE = args.base || 'http://127.0.0.1:8767';
const OUT = args.out || join(tmpdir(), 'musnba-shots');
const CHROME = args.chrome || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const SIZES = {desktop: [1440, 1000, 1, false], half: [960, 1000, 1, false], phone: [390, 844, 2, true]};
const only = args.only ? String(args.only).split(',') : null;

// name, hash, sizes, themes
const CASES = [
  ['today', '#/today/2026-11-19', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['results', '#/today/2026-11-18', ['desktop', 'phone'], ['light']],
  ['game-box', '#/game/401910019', ['desktop', 'phone'], ['dark', 'light']],
  ['game-q1-player', '#/game/401910019/q1', ['desktop', 'phone'], ['dark']],
  ['game-h2-team', '#/game/401910019/h2/team', ['desktop', 'phone'], ['light']],
  ['game-final', '#/game/401910009', ['desktop', 'phone'], ['dark']],
  ['game-final-q4', '#/game/401910009/q4', ['phone'], ['light']],
  ['game-final-team', '#/game/401910009/fg/team', ['desktop'], ['dark']],
  ['game-matchup', '#/game/401910019/matchup', ['phone'], ['light']],
  ['game-duels', '#/game/401910009/matchup', ['desktop', 'phone'], ['dark', 'light']],
  ['game-proj', '#/game/401910029', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['sheet', '#/game/401910009/player/3032977', ['desktop', 'phone'], ['dark', 'light']],
  ['sheet-q1', '#/game/401910019/player/5041935/q1', ['phone'], ['dark']],
  ['future-game', '#/game/' + (args.future || ''), ['phone'], ['dark']],
  ['standings', '#/standings/forecast', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['standings-wins', '#/standings/wins', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['teams', '#/teams', ['desktop', 'phone'], ['dark']],
  ['team', '#/team/14', ['desktop', 'phone'], ['light']],
  ['players', '#/players', ['desktop', 'phone'], ['dark']],
  ['player', '#/player/3032977', ['desktop', 'phone'], ['dark']],
  ['lab', '#/lab', ['desktop', 'phone'], ['dark', 'light']],
  ['scenario', '#/game/401909305/scenario', ['desktop', 'phone'], ['dark', 'light']],
  ['scenario-set', '#/game/401909305/scenario/' + encodeURIComponent(JSON.stringify([{subj: 'p:4701230', v: 'pts', op: 'ge', x: 30}, {subj: 't:home', v: 'win'}])), ['desktop', 'phone'], ['dark']],
  ['team-drivers', '#/game/401909305/fg/team', ['desktop', 'phone'], ['light']],
  ['sheet-whatif', '#/game/401909305/player/4701230/fg', ['desktop', 'phone'], ['dark', 'light']],
  ['today-leaders', '#/today/2026-11-21', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['tomorrow', '#/today/2026-11-22', ['desktop', 'half', 'phone'], ['dark']],
].filter(c => (!only || only.includes(c[0])) && !(c[0] === 'future-game' && !args.future));

const profile = mkdtempSync(join(tmpdir(), 'musnba-chrome-'));
const chrome = spawn(CHROME, ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`, '--no-first-run',
  '--no-default-browser-check', '--disable-extensions', '--hide-scrollbars', 'about:blank'], {stdio: ['ignore', 'ignore', 'pipe']});
const wsUrl = await new Promise((resolve, reject) => {
  let buffer = '';
  chrome.stderr.on('data', d => { buffer += d; const m = buffer.match(/DevTools listening on (ws:\/\/\S+)/); if (m) resolve(m[1]); });
  setTimeout(() => reject(new Error('Chrome did not start')), 15000);
});
const ws = new WebSocket(wsUrl);
await new Promise(r => ws.addEventListener('open', r, {once: true}));
let seq = 0;
const pending = new Map(), listeners = [];
ws.addEventListener('message', e => {
  const msg = JSON.parse(e.data);
  if (msg.id && pending.has(msg.id)) { const {resolve, reject} = pending.get(msg.id); pending.delete(msg.id); msg.error ? reject(new Error(msg.error.message)) : resolve(msg.result); }
  else for (const l of listeners) l(msg);
});
const send = (method, params = {}, sessionId) => new Promise((resolve, reject) => {
  const id = ++seq; pending.set(id, {resolve, reject});
  ws.send(JSON.stringify({id, method, params, ...(sessionId ? {sessionId} : {})}));
});
const sleep = ms => new Promise(r => setTimeout(r, ms));

mkdirSync(OUT, {recursive: true});
const report = [];
let failures = 0;
for (const [name, hash, sizes, themes] of CASES) {
  for (const size of sizes) for (const theme of themes) {
    const [width, height, scale, mobile] = SIZES[size];
    const {targetId} = await send('Target.createTarget', {url: 'about:blank'});
    const {sessionId} = await send('Target.attachToTarget', {targetId, flatten: true});
    const errors = [];
    const onMsg = msg => {
      if (msg.sessionId !== sessionId) return;
      if (msg.method === 'Runtime.exceptionThrown') errors.push(msg.params.exceptionDetails.exception?.description || msg.params.exceptionDetails.text);
      if (msg.method === 'Runtime.consoleAPICalled' && ['error', 'assert'].includes(msg.params.type)) errors.push(msg.params.args.map(a => a.value ?? a.description).join(' '));
      if (msg.method === 'Log.entryAdded' && msg.params.entry.level === 'error') errors.push(msg.params.entry.text + ' ' + (msg.params.entry.url || ''));
    };
    listeners.push(onMsg);
    await send('Page.enable', {}, sessionId);
    await send('Runtime.enable', {}, sessionId);
    await send('Log.enable', {}, sessionId);
    await send('Emulation.setDeviceMetricsOverride', {width, height, deviceScaleFactor: scale, mobile}, sessionId);
    if (mobile) await send('Emulation.setTouchEmulationEnabled', {enabled: true, maxTouchPoints: 5}, sessionId);
    await send('Emulation.setEmulatedMedia', {features: [{name: 'prefers-color-scheme', value: theme}]}, sessionId);
    await send('Page.navigate', {url: BASE + '/' + hash}, sessionId);
    let ready = false;
    for (let i = 0; i < 60 && !ready; i++) {
      await sleep(150);
      const {result} = await send('Runtime.evaluate', {expression: "document.readyState === 'complete' && !document.querySelector('#view[aria-busy]') && !document.querySelector('#view .loading') && !!document.querySelector('#view > *')", returnByValue: true}, sessionId).catch(() => ({result: {}}));
      ready = result.value === true;
    }
    await sleep(250);
    const {result: dims} = await send('Runtime.evaluate', {returnByValue: true, expression: `(() => {
      const wide = [...document.querySelectorAll('body *')].filter(el => { const r = el.getBoundingClientRect(); return r.right > innerWidth + 1 && !el.closest('.scroll') && getComputedStyle(el).position !== 'fixed'; }).slice(0, 5).map(el => el.tagName.toLowerCase() + (el.className ? '.' + String(el.className).split(' ')[0] : ''));
      return {scrollWidth: document.documentElement.scrollWidth, innerWidth, height: document.documentElement.scrollHeight, wide, title: document.querySelector('#view h2')?.textContent || ''};
    })()`}, sessionId);
    const d = dims.value;
    const overflow = d.scrollWidth > d.innerWidth + 1;
    const shot = await send('Page.captureScreenshot', {format: 'png', captureBeyondViewport: true,
      clip: {x: 0, y: args.from ? Math.max(0, d.height - Number(args.from)) : 0, width, height: Math.min(args.from ? Number(args.from) : d.height, mobile ? 3200 : 2600), scale: 1}}, sessionId);
    const file = join(OUT, `${name}-${size}-${theme}.png`);
    writeFileSync(file, Buffer.from(shot.data, 'base64'));
    const ok = ready && !overflow && errors.length === 0;
    if (!ok) failures++;
    report.push({name, size, theme, ok, ready, overflow, scrollWidth: d.scrollWidth, wide: d.wide, errors});
    console.log(`${ok ? 'PASS' : 'FAIL'}  ${name.padEnd(14)} ${size.padEnd(7)} ${theme.padEnd(5)} ${ready ? '' : 'not-ready '}${overflow ? `overflow ${d.scrollWidth}>${d.innerWidth} ${d.wide.join(',')} ` : ''}${errors.length ? 'errors: ' + errors.slice(0, 2).join(' | ') : ''}`);
    listeners.splice(listeners.indexOf(onMsg), 1);
    await send('Target.closeTarget', {targetId});
  }
}
writeFileSync(join(OUT, 'report.json'), JSON.stringify(report, null, 1));
console.log(`\n${report.length - failures}/${report.length} passed · screenshots in ${OUT}`);
ws.close();
chrome.kill();
try { rmSync(profile, {recursive: true, force: true}); } catch { /* profile cleanup is best-effort */ }
process.exit(failures ? 1 : 0);
