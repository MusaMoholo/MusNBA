#!/usr/bin/env node
// Optional end-to-end check of the static PWA: fresh profile → shell asks for data → import a
// bundle through the real file input → app renders → service worker controls the page → reload
// offline still renders from IndexedDB. DevTools protocol only; no npm packages.
//
//   node analysis/pwa_import_check.mjs --url http://127.0.0.1:8768/MusNBA/ --bundle /path/MusNBA.musnba.gz [--out dir]
import {spawn} from 'node:child_process';
import {cpSync, mkdtempSync, rmSync, writeFileSync} from 'node:fs';
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
if (args['bypass-service-worker']) await send('Network.setBypassServiceWorker', {bypass: true}, s);
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
await waitFor(`document.querySelector('#pwa-status')?.textContent.includes('Saved data through')
  && (!!document.querySelector('.game-card') || document.querySelector('#view')?.textContent.includes('Not available'))`, 120000);
const imported = await evaluate(`!!document.querySelector('.game-card') && document.querySelector('#pwa-status')?.textContent.includes('Saved data through')`);
const importDetail = imported ? '' : ' · ' + JSON.stringify(await evaluate(`(async () => {
  const ui = await import('./assets/ui.mjs');
  const response = await fetch(new URL('api/slate/' + (ui.meta()?.latest || ''), ui.BASE));
  return {status: document.querySelector('#pwa-status')?.textContent, error: document.querySelector('#pwa-error')?.textContent,
    view: document.querySelector('#view')?.textContent.slice(0, 300), location: location.href, base: ui.BASE.href,
    static: window.MUSNBA_STATIC, response: response.status, url: response.url, body: (await response.text()).slice(0, 200)};
})()`));
check('import completes and app renders slate', imported, `${((Date.now() - started) / 1000).toFixed(1)}s${importDetail}`);
if (!imported) {
  ws.close(); chrome.kill();
  try { rmSync(profile, {recursive: true, force: true}); } catch { /* best effort */ }
  process.exit(1);
}
if (args['bypass-service-worker']) {
  check('static API accepts URL, string and Request without service-worker control', await evaluate(`(async () => {
    const url = new URL('./api/meta', location.href);
    const results = await Promise.all([url, url.href, new Request(url)].map(input => fetch(input)));
    const bodies = await Promise.all(results.map(response => response.json()));
    return results.every(response => response.ok) && bodies.every(body => body.latest === bodies[0].latest);
  })()`));
}
if (args['bypass-service-worker']) {
  await send('Network.setBypassServiceWorker', {bypass: false}, s);
  // Image requests do not pass through the fetch shim; retry them after restoring the worker.
  await send('Page.reload', {}, s);
  check('app renders after service-worker bypass is lifted', await waitFor(`!!document.querySelector('.game-card')`, 30000));
}
if (args['panel-check']) {
  await evaluate(`document.querySelector('#offline-panel').open = true; document.querySelector('#offline-panel details').open = true`);
  for (const [label, width, height, scale, mobile] of [['desktop', 1440, 1000, 1, false], ['half', 960, 1000, 1, false], ['phone', 390, 844, 2, true]]) {
    await send('Emulation.setDeviceMetricsOverride', {width, height, deviceScaleFactor: scale, mobile}, s);
    for (const theme of ['light', 'dark']) {
      await send('Emulation.setEmulatedMedia', {features: [{name: 'prefers-color-scheme', value: theme}]}, s);
      check(`offline panel fits ${label} ${theme}`, await evaluate(`document.documentElement.scrollWidth <= innerWidth`));
      if (args.out) {
        const shot = await send('Page.captureScreenshot', {format: 'png'}, s);
        writeFileSync(join(args.out, `pwa-panel-${label}-${theme}.png`), Buffer.from(shot.data, 'base64'));
      }
    }
  }
  await send('Emulation.setDeviceMetricsOverride', {width: 390, height: 844, deviceScaleFactor: 2, mobile: true}, s);
  await evaluate(`document.querySelector('#offline-panel').open = false`);
}
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
check('app update button is visible only for a waiting update', await evaluate(`(async () => {
  const registration = await navigator.serviceWorker.getRegistration(), button = document.querySelector('#pwa-update');
  return registration?.waiting ? !button.hidden && getComputedStyle(button).display !== 'none'
    : button.hidden && getComputedStyle(button).display === 'none';
})()`));
if (args['upgrade-shell'] && args['upgrade-target'] && args['upgrade-version']) {
  cpSync(args['upgrade-shell'], args['upgrade-target'], {recursive: true});
  await evaluate(`(async () => { const registration = await navigator.serviceWorker.getRegistration(); await registration.update(); })()`);
  const waiting = await waitFor(`(async () => {
    const registration = await navigator.serviceWorker.getRegistration(), button = document.querySelector('#pwa-update');
    return !!registration?.waiting && !button.hidden && getComputedStyle(button).display !== 'none';
  })()`, 30000);
  check('new shell waits with visible update action', waiting);
  if (waiting) await evaluate(`document.querySelector('#pwa-update').click()`);
  const activated = waiting && await waitFor(`(async () => {
    const ui = await import('./assets/ui.mjs');
    return typeof ui.wireAdvancedPanels === 'function'
      && (await caches.keys()).some(key => key.endsWith(${JSON.stringify(args['upgrade-version'])}))
      && !!document.querySelector('#view .form-grid')
      && document.querySelector('#pwa-status')?.textContent.includes('Saved data through');
  })()`, 30000);
  const detail = activated ? '' : JSON.stringify(await evaluate(`(async () => {
    const r = await navigator.serviceWorker.getRegistration(), ui = await import('./assets/ui.mjs');
    const names = await caches.keys(), cache = await caches.open(names.find(name => name.endsWith(${JSON.stringify(args['upgrade-version'])})));
    const response = await cache.match(new URL('./assets/ui.mjs', location.href).pathname);
    return {waiting: r?.waiting?.state, active: r?.active?.state, caches: names,
      cachedAdvanced: response ? (await response.text()).includes('function advancedRates') : null,
      advanced: typeof ui.wireAdvancedPanels, team: !!document.querySelector('#view .form-grid')};
  })()`));
  check('app update activates the new shell and keeps imported data', activated, detail);
}
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
if (args['require-house']) {
  check('offline player directory keeps movers expandable through sorting', await evaluate(`(() => {
    const movers = document.querySelector('#player-movers'), table = document.querySelector('#ptable table');
    if (!movers || movers.open || !table || !(movers.compareDocumentPosition(table) & Node.DOCUMENT_POSITION_FOLLOWING)) return false;
    movers.open = true;
    document.querySelector('#ptable th[data-sort="pts"]').click();
    return document.querySelector('#player-movers')?.open && !!document.querySelector('#player-movers .mv');
  })()`));
  const today = await evaluate(`(async () => { const ui = await import('./assets/ui.mjs'); return ui.meta().latest; })()`);
  await send('Page.navigate', {url: args.url + '#/today/' + today}, s);
  check('offline slate puts games before accessible insights', await waitFor(`!!document.querySelector('.game-card')`) && await evaluate(`(() => {
    const games = document.querySelector('.games:not(.spot-grid)'), insights = document.querySelector('#slate-insights');
    return !!games && !!insights && !!document.querySelector('[data-insights]')
      && !!(games.compareDocumentPosition(insights) & Node.DOCUMENT_POSITION_FOLLOWING);
  })()`));
}
const shootingTarget = await evaluate(`(async () => {
  const ui = await import('./assets/ui.mjs'), slate = await ui.api('slate/' + ui.meta().latest);
  for (const fixture of slate.games) {
    const game = await ui.api('game/' + fixture.id), sim = game.projection?.sim;
    if (sim?.shooting_distribution_schema !== 1) continue;
    for (const side of ['home', 'away']) for (const p of sim[side].players) {
      const stats = p.periods?.q1?.stats, d = stats?.fgpct;
      if (d && stats.fg3pct && stats.ftpct && (!${Boolean(args['require-advanced'])} || game.usage_profiles?.[p.id]))
        return {game: fixture.id, player: p.id, defined: d.defined, total: d.total};
    }
  }
  return null;
})()`);
if (shootingTarget) {
  if (args['require-house']) {
    await send('Page.navigate', {url: args.url + '#/game/' + shootingTarget.game}, s);
    check('offline game availability and bench remain accessible', await waitFor(`!!document.querySelector('details[data-bench-side]')`) && await evaluate(`(() => {
      const availability = document.querySelector('details[data-player-availability]'), bench = document.querySelector('details[data-bench-side]');
      if (!availability || availability.open || bench.open || !bench.querySelector('tr[data-pid]')) return false;
      const insights = document.querySelector('#game-insights');
      if (!insights || !document.querySelector('[data-game-insights]')
          || !(bench.compareDocumentPosition(insights) & Node.DOCUMENT_POSITION_FOLLOWING)) return false;
      availability.open = true; bench.open = true;
      return !!availability.querySelector('.av-grid') && bench.querySelector('tr[data-pid]').getBoundingClientRect().height > 0;
    })()`));
    const teamId = await evaluate(`(async () => { const ui = await import('./assets/ui.mjs'); const game = await ui.api('game/' + ${JSON.stringify(shootingTarget.game)}); return game.game.home.id; })()`);
    await send('Page.navigate', {url: args.url + '#/team/' + teamId}, s);
    check('offline team bench expands', await waitFor(`!!document.querySelector('[data-roster-group="Bench"]')`) && await evaluate(`(() => {
      const button = document.querySelector('[data-roster-group="Bench"]'), rows = [...document.querySelectorAll('tr[data-roster-member="Bench"]')];
      if (button.getAttribute('aria-expanded') !== 'false' || !rows.length || rows.some(x => !x.hidden)) return false;
      button.click();
      return button.getAttribute('aria-expanded') === 'true' && rows.every(x => !x.hidden && x.getBoundingClientRect().height > 0);
    })()`));
    await send('Page.navigate', {url: args.url + '#/player/3032977'}, s);
    check('offline player game log expands', await waitFor(`!!document.querySelector('details[data-game-log]')`) && await evaluate(`(() => {
      const log = document.querySelector('details[data-game-log]');
      if (log.open || !log.querySelector('tr[data-gid]')) return false;
      log.open = true;
      return log.querySelector('tr[data-gid]').getBoundingClientRect().height > 0;
    })()`));
  }
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
if (args['require-advanced'] && shootingTarget) {
  await send('Page.navigate', {url: args.url + '#/game/' + shootingTarget.game + '/player/' + shootingTarget.player + '/fg'}, s);
  check('offline player advanced rates and action-share profile', await waitFor(`document.querySelector('#view').textContent.includes('Offensive action share')`) && await evaluate(`(async () => {
    const ui = await import('./assets/ui.mjs'), game = await ui.api('game/' + ${JSON.stringify(shootingTarget.game)});
    const player = ['home', 'away'].flatMap(side => game.projection.sim[side].players).find(p => p.id === ${JSON.stringify(shootingTarget.player)});
    const profile = game.usage_profiles?.[player.id], dist = player.periods.fg.advanced?.efg;
    const panel = document.querySelector('details[data-advanced-panel]');
    if (!panel || panel.open) return false;
    panel.open = true;
    const chart = panel.querySelector('details[data-metric="efg"]');
    if (!chart) return false;
    chart.open = true;
    await new Promise(resolve => setTimeout(resolve, 100));
    const text = document.querySelector('#view').textContent;
    return !!profile && text.includes(ui.rate(profile.rate)) && text.includes('not conventional')
      && !!dist?.defined && text.includes('Each projected value is calculated in each saved world')
      && text.includes(ui.f1(dist.exact_q[2]) + '%') && text.includes('Defined in ' + dist.defined.toLocaleString())
      && !!chart.querySelector('svg.hist');
  })()`));
  await send('Page.navigate', {url: args.url + '#/game/' + shootingTarget.game + '/fg/team'}, s);
  check('offline team advanced distributions open and match saved worlds', await waitFor(`document.querySelectorAll('#view details.panel').length >= 2`) && await evaluate(`(async () => {
    const ui = await import('./assets/ui.mjs'), game = await ui.api('game/' + ${JSON.stringify(shootingTarget.game)});
    const panel = document.querySelector('#view details.panel'); panel.open = true;
    const dist = game.projection.sim.away.advanced?.ortg;
    const chart = panel.querySelector('details[data-distribution]');
    chart.open = true;
    await new Promise(resolve => setTimeout(resolve, 100));
    return panel.open && panel.textContent.includes('not counted possessions') && !!dist?.defined
      && panel.textContent.includes(ui.f1(dist.exact_q[2])) && !!chart.querySelector('svg.hist');
  })()`));
} else if (args['require-advanced']) check('offline advanced-stat source is available', false);
if (args.profile) {
  check('imported bundle profile and world availability', await evaluate(`(async () => {
    const storage = await import('./assets/pwa-storage.mjs'), ui = await import('./assets/ui.mjs');
    const info = await storage.read('meta', await storage.read('meta', 'active'));
    const game = await ui.api('game/' + ${JSON.stringify(shootingTarget?.game || '')});
    if (info.profile !== ${JSON.stringify(args.profile)} || !document.querySelector('#pwa-status').textContent.includes(ui.stamp(info.created))
        || !document.querySelector('#pwa-status').textContent.includes(ui.tipTimes(info.created, info.latest).et)) return false;
    if (${JSON.stringify(args.profile)} === 'phone') return game.worlds === false;
    const worlds = await ui.api('game/' + ${JSON.stringify(shootingTarget?.game || '')} + '/worlds');
    const outcomes = await import('./assets/outcomes.mjs'), loaded = await outcomes.load(${JSON.stringify(shootingTarget?.game || '')});
    return game.worlds === true && worlds.worlds === game.projection.sim.sims && loaded.W === worlds.worlds
      && loaded.values('t:home', 'pts').length === worlds.worlds;
  })()`));
  if (args.profile === 'laptop' && shootingTarget) {
    await send('Page.navigate', {url: args.url + '#/game/' + shootingTarget.game + '/scenario'}, s);
    check('laptop scenarios render from saved worlds offline', await waitFor(`!!document.querySelector('[data-builder="scn"]') && document.querySelector('#view').textContent.includes(${JSON.stringify('of ' + shootingTarget.total.toLocaleString() + ' saved worlds')})`, 30000));
  }
}
if (args['research-game']) {
  const gid = args['research-game'];
  await send('Page.navigate', {url: args.url + '#/game/' + gid}, s);
  const inject = `(async () => {
    const ui = await import('./assets/ui.mjs'), game = await import('./assets/game.mjs');
    const view = await ui.api('research/a1/' + ${JSON.stringify(gid)});
    game.setResearchGame(${JSON.stringify(gid)}, async () => ({view, worlds: null}));
    await game.render(document.querySelector('#view'), {rest: [${JSON.stringify(gid)}], current: () => true});
    const home = document.querySelector('.bz-team.home .bz-stats b')?.textContent;
    const missingWorlds = await fetch(new URL('./api/game/' + ${JSON.stringify(gid)} + '/worlds', location.href));
    const gameOk = home === view.sim.periods.fg.home.pts.mean.toFixed(1)
      && document.querySelector('[data-research-lineups]')?.textContent.includes('Expected only')
      && !document.querySelector('[data-lineup], [data-view="scenario"]')
      && !missingWorlds.ok;
    const player = view.sim.home.players.find(p => p.periods.fg.stats.fgpct);
    if (!player) return false;
    await game.render(document.querySelector('#view'), {rest: [${JSON.stringify(gid)}, 'player', player.id, 'fg'], current: () => true});
    const button = document.querySelector('[data-stat="fgpct"]');
    if (!button) return false;
    button.click();
    const d = player.periods.fg.stats.fgpct;
    return gameOk && document.querySelector('#stat-block').textContent.includes(ui.pct(d.defined_mass / d.total_mass, 1) + ' weighted chance of an attempt')
      && !document.querySelector('#what-if, [data-lineup]');
  })()`;
  check('research Expected-only data imports and renders offline without worlds', await waitFor(`!!document.querySelector('#game-body')`)
    && await evaluate(inject));
  await send('Page.reload', {}, s);
  check('research Expected-only data survives offline reload', await waitFor(`!!document.querySelector('#game-body')`)
    && await evaluate(inject));
}
if (args['research-laptop']) {
  const gid = args['research-laptop'];
  await send('Page.navigate', {url: args.url + '#/game/' + gid}, s);
  const setup = `(async () => {
    const ui = await import('./assets/ui.mjs'), G = await import('./assets/game.mjs'), O = await import('./assets/outcomes.mjs');
    const item = await ui.api('research/a1/' + ${JSON.stringify(gid)});
    const load = text => import(URL.createObjectURL(new Blob([text], {type: 'text/javascript'})));
    const weighted = new URL('./assets/weighted-worlds.mjs', location.href).href;
    const sourceModule = await load(item.modules.source.replace('./a1_weighted_browser.mjs', weighted));
    const {branchGameSummary} = await load(item.modules.summary);
    const {selectedGameView} = await load(item.modules.contract);
    const source = sourceModule.branchWorldSource(item.fixture), cache = new Map();
    G.setResearchGame(${JSON.stringify(gid)}, async choices => {
      const key = JSON.stringify(choices);
      if (!cache.has(key)) {
        const result = branchGameSummary(source, choices);
        cache.set(key, {view: selectedGameView(item.view.game, item.payload,
          {fixture_sha256: item.payload.fixture_sha256, result}), worlds: O.branchWorldData(source, choices)});
      }
      return cache.get(key);
    });
    await G.render(document.querySelector('#view'), {rest: [${JSON.stringify(gid)}], current: () => true});
    return document.querySelector('.bz-team.home .bz-stats b')?.textContent === item.view.sim.periods.fg.home.pts.mean.toFixed(1)
      && document.querySelectorAll('[data-lineup]').length === item.payload.selected_players.length;
  })()`;
  const start = Date.now();
  check('research laptop branches import and render offline', await waitFor(`!!document.querySelector('#game-body')`)
    && await evaluate(setup), `${((Date.now() - start) / 1000).toFixed(1)}s`);
  const chosen = args['research-player'];
  const expected = args['research-home-points'];
  if (!chosen || expected == null) throw new Error('Research laptop check requires player and independently audited home points');
  await evaluate(`(() => {const e=document.querySelector('[data-lineup="${chosen}"]'); if (!e) return false; e.value='unavailable'; e.dispatchEvent(new Event('change')); return true;})()`);
  check('research laptop branch selection updates offline', await waitFor(`document.querySelector('[data-lineup="${chosen}"]')?.value === 'unavailable'
    && !document.querySelector('[data-lineup="${chosen}"]')?.disabled
    && document.querySelector('.bz-team.home .bz-stats b')?.textContent === ${JSON.stringify(expected)}`, 120000));
  await send('Page.reload', {}, s);
  check('research laptop branch inputs survive offline reload', await waitFor(`!!document.querySelector('#game-body')`)
    && await evaluate(setup));
}
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
