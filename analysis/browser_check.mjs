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
const EXPECT = {'legacy-season': 'Season races', season: 'Season races', 'season-leaders': 'Season leaders · to date', 'season-movers': 'Since the previous forecast', about: 'About the model', 'standings-picture': 'playoff picture'};
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
  ['game-matchup', '#/game/401910029/matchup', ['desktop', 'half', 'phone'], ['light', 'dark']],
  ['game-duels', '#/game/401910009/matchup', ['desktop', 'phone'], ['dark', 'light']],
  ['game-proj', '#/game/401910029', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['sheet', '#/game/401910009/player/3032977', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['sheet-shooting', '#/game/' + (args.shootGame || '401910030') + '/player/' + (args.shootPlayer || '4278053') + '/fg', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['sheet-q1', '#/game/401910019/player/5041935/q1', ['phone'], ['dark']],
  ['future-game', '#/game/' + (args.future || ''), ['phone'], ['dark']],
  ['standings', '#/standings/forecast', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['standings-seeds', '#/standings/seeds', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['standings-ratings', '#/standings/ratings', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['standings-wins', '#/standings/wins', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['standings-picture', '#/standings/picture', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['season', '#/standings/races', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['season-movers', '#/standings/movers', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['season-leaders', '#/standings/leaders', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['about', '#/about', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['teams', '#/teams', ['desktop', 'phone'], ['dark']],
  ['team', '#/team/14', ['desktop', 'half', 'phone'], ['light', 'dark']],
  ['team-no-proj', '#/team/20', ['desktop', 'half', 'phone'], ['light', 'dark']],
  ['legacy-season', '#/season', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['players', '#/players', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['player', '#/player/3032977', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['lab', '#/lab', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['scenario', '#/game/401909305/scenario', ['desktop', 'phone'], ['dark', 'light']],
  ['scenario-set', '#/game/401909305/scenario/' + encodeURIComponent(JSON.stringify([{subj: 'p:4701230', v: 'pts', op: 'ge', x: 30}, {subj: 't:home', v: 'win'}])), ['desktop', 'phone'], ['dark']],
  ['team-drivers', '#/game/401909305/fg/team', ['desktop', 'phone'], ['light']],
  ['game-flow', '#/game/401910029/fg/team', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['game-advanced', '#/game/401910029/fg/team', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['sheet-advanced', '#/game/401910030/player/4278053/fg', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['players-house', '#/players', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['player-house', '#/player/3032977', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['today-house', '#/today/2026-11-22', ['desktop', 'half', 'phone'], ['dark', 'light']],
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
    let interaction = true;
    if (name === 'sheet-shooting') {
      interaction = (await send('Runtime.evaluate', {expression: `(async () => {
        const button = document.querySelector('[data-stat="fgpct"]');
        if (!button) return false;
        button.click();
        const ui = await import('./assets/ui.mjs'), game = await ui.api('game/' + ${JSON.stringify(args.shootGame || '401910030')});
        const sim = game.projection.sim, player = [...sim.home.players, ...sim.away.players].find(p => p.id === ${JSON.stringify(args.shootPlayer || '4278053')});
        const d = player?.periods?.fg?.stats?.fgpct, text = document.querySelector('#stat-block').textContent;
        return !!d && text.includes('conditional on an attempt')
          && text.includes('No field-goal attempts in ' + ui.pct((d.total - d.defined) / d.total, 1))
          && text.includes(d.defined.toLocaleString() + ' of ' + d.total.toLocaleString());
      })()`, returnByValue: true, awaitPromise: true}, sessionId)).result.value === true;
    }
    if (name === 'game-advanced') {
      interaction = (await send('Runtime.evaluate', {expression: `(async () => {
        const panel = document.querySelector('#view details.panel');
        if (!panel) return false;
        panel.open = true;
        const chart = panel.querySelector('details[data-distribution]');
        if (!chart) return false;
        chart.open = true;
        await new Promise(resolve => setTimeout(resolve, 150));
        if (!chart.querySelector('svg.hist') || !panel.textContent.includes('not counted possessions')) return false;
        const input = document.querySelector('#view input[data-line]');
        if (!input) return false;
        input.value = '120.5';
        input.dispatchEvent(new Event('change', {bubbles: true}));
        await new Promise(resolve => setTimeout(resolve, 150));
        const next = document.querySelector('#view details[data-advanced-panel]');
        next.scrollIntoView();
        return next.open && next.querySelector('details[data-metric="efg"]').open
          && !!next.querySelector('details[data-metric="efg"] svg.hist');
      })()`, returnByValue: true, awaitPromise: true}, sessionId)).result.value === true;
    }
    if (name === 'sheet-advanced') {
      interaction = (await send('Runtime.evaluate', {expression: `(async () => {
        const panel = document.querySelector('details[data-advanced-panel]');
        if (!panel || panel.open || !document.querySelector('[data-stat="fgm"]')) return false;
        panel.open = true;
        const chart = panel.querySelector('details[data-metric="efg"]');
        if (!chart) return false;
        chart.open = true;
        await new Promise(resolve => setTimeout(resolve, 150));
        if (!chart.querySelector('svg.hist')) return false;
        document.querySelector('[data-stat="fgm"]').click();
        await new Promise(resolve => setTimeout(resolve, 150));
        const next = document.querySelector('details[data-advanced-panel]');
        return next.open && next.querySelector('details[data-metric="efg"]').open
          && !!next.querySelector('details[data-metric="efg"] svg.hist');
      })()`, returnByValue: true, awaitPromise: true}, sessionId)).result.value === true;
    }
    if (name === 'players-house') {
      interaction = (await send('Runtime.evaluate', {expression: `(() => {
        const table = document.querySelector('#ptable table'), movers = document.querySelector('#player-movers');
        if (!table || !movers || movers.open || !(movers.compareDocumentPosition(table) & Node.DOCUMENT_POSITION_FOLLOWING)) return false;
        movers.open = true;
        document.querySelector('#ptable th[data-sort="pts"]').click();
        const next = document.querySelector('#player-movers'), cols = next.querySelectorAll('.movers > div');
        return next.open && !!next.querySelector('.mv')
          && (innerWidth > 600 || cols[1].getBoundingClientRect().top >= cols[0].getBoundingClientRect().bottom - 1);
      })()`, returnByValue: true}, sessionId)).result.value === true;
    }
    if (name === 'player-house') {
      interaction = (await send('Runtime.evaluate', {expression: `(() => {
        const next = [...document.querySelectorAll('#view section.panel')].find(x => x.querySelector('h3')?.textContent === 'Next game');
        const advanced = document.querySelector('details[data-advanced-panel]');
        const history = next?.querySelector('details.sub');
        if (history) { if (history.open) return false; history.open = true; if (!history.querySelector('table')) return false; }
        return !!next && !!advanced && !advanced.open
          && !!(next.compareDocumentPosition(advanced) & Node.DOCUMENT_POSITION_FOLLOWING);
      })()`, returnByValue: true}, sessionId)).result.value === true;
    }
    if (name === 'today-house') {
      interaction = (await send('Runtime.evaluate', {expression: `(async () => {
        const games = document.querySelector('#view .games:not(.spot-grid)'), insights = document.querySelector('#view .spot-grid');
        const jump = document.querySelector('[data-insights]');
        if (!jump) return false;
        jump.click();
        await new Promise(resolve => setTimeout(resolve, 800));
        return !!games?.querySelector('.game-card') && !!insights
          && !!(games.compareDocumentPosition(insights) & Node.DOCUMENT_POSITION_FOLLOWING) && scrollY > 0;
      })()`, returnByValue: true, awaitPromise: true}, sessionId)).result.value === true;
    }
    await sleep(250);
    const {result: dims} = await send('Runtime.evaluate', {returnByValue: true, expression: `(() => {
      const wide = [...document.querySelectorAll('body *')].filter(el => { const r = el.getBoundingClientRect(); return r.right > innerWidth + 1 && !el.closest('.scroll') && getComputedStyle(el).position !== 'fixed'; }).slice(0, 5).map(el => el.tagName.toLowerCase() + (el.className ? '.' + String(el.className).split(' ')[0] : ''));
      return {scrollWidth: document.documentElement.scrollWidth, innerWidth, height: document.documentElement.scrollHeight, wide, title: document.querySelector('#view h2')?.textContent || ''};
    })()`}, sessionId);
    const d = dims.value;
    const overflow = d.scrollWidth > d.innerWidth + 1;
    const panelTop = name === 'game-advanced' ? (await send('Runtime.evaluate', {expression: `document.querySelector('#view details.panel')?.getBoundingClientRect().top + scrollY || 0`, returnByValue: true}, sessionId)).result.value : 0;
    const shot = await send('Page.captureScreenshot', {format: 'png', captureBeyondViewport: true,
      clip: {x: 0, y: args.from ? Math.max(0, d.height - Number(args.from)) : panelTop, width, height: Math.min(args.from ? Number(args.from) : d.height - panelTop, mobile ? 3200 : 2600), scale: 1}}, sessionId);
    const file = join(OUT, `${name}-${size}-${theme}.png`);
    writeFileSync(file, Buffer.from(shot.data, 'base64'));
    const expected = EXPECT[name];
    const content = !expected || (await send('Runtime.evaluate', {expression: `document.querySelector('#view').textContent.includes(${JSON.stringify(expected)})`, returnByValue: true}, sessionId)).result.value === true;
    const stacked = !(['team', 'team-no-proj'].includes(name) && size === 'phone') || (await send('Runtime.evaluate', {expression: `(() => { const items = [...document.querySelectorAll('.form-grid > div')]; return items.length < 2 || items[1].getBoundingClientRect().top >= items[0].getBoundingClientRect().bottom - 1; })()`, returnByValue: true}, sessionId)).result.value === true;
    const ok = ready && interaction && content && stacked && !overflow && errors.length === 0;
    if (!ok) failures++;
    report.push({name, size, theme, ok, ready, interaction, content, stacked, overflow, scrollWidth: d.scrollWidth, wide: d.wide, errors});
    console.log(`${ok ? 'PASS' : 'FAIL'}  ${name.padEnd(14)} ${size.padEnd(7)} ${theme.padEnd(5)} ${ready ? '' : 'not-ready '}${interaction ? '' : 'interaction-failed '}${content ? '' : 'wrong-content '}${stacked ? '' : 'not-stacked '}${overflow ? `overflow ${d.scrollWidth}>${d.innerWidth} ${d.wide.join(',')} ` : ''}${errors.length ? 'errors: ' + errors.slice(0, 2).join(' | ') : ''}`);
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
