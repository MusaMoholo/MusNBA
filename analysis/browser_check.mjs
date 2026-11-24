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
const EXPECT = {'legacy-season': 'Season races', season: 'Season races', 'season-leaders': 'Season leaders · to date',  about: 'About the model', 'standings-picture': 'playoff picture'};
const only = args.only ? String(args.only).split(',') : null;

// name, hash, sizes, themes
const CASES = [
  ['c5-cup', '#/cup', ['desktop','half','phone'], ['dark','light']],
  ['c5-playoffs', '#/playoffs', ['desktop','half','phone'], ['dark','light']],
  ['c5-regular', '#/standings/forecast', ['desktop','half','phone'], ['dark','light']],
  ['c4-analysis', '#/game/' + (args['lineup-game'] || '401910036') + '/analysis', ['desktop','half','phone'], ['dark','light']],
  ['c4-projected', '#/game/' + (args['lineup-game'] || '401910036') + '/analysis', ['desktop','half','phone'], ['dark','light']],
  ['c4-observed', '#/game/' + (args['lineup-game'] || '401910036') + '/analysis', ['desktop','half','phone'], ['dark','light']],
  ['c4-lineup', '#/game/' + (args['lineup-game'] || '401910037') + '/analysis', ['desktop','half','phone'], ['dark','light']],
  ['c4-replay', '#/game/' + (args['lineup-game'] || '401910036') + '/replay', ['desktop','half','phone'], ['dark','light']],
  ['u24-roster-sort', '#/team/14', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['u24-players-sort', '#/players', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['u24-scenario', '#/game/' + (args['lineup-game'] || '401910036') + '/scenario', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['u24-advanced', '#/game/' + (args['lineup-game'] || '401910036') + '/player/' + (args['lineup-player'] || '4065733') + '/fg', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['u24-lineup-compare', '#/game/' + (args['lineup-game'] || '401910036') + '/fg/team', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['u24-standings-controls', '#/standings/forecast', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['boot-retry', '#/', ['desktop', 'half', 'phone'], ['dark', 'light']],
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
  ['future-game', '#/game/' + (args.future || ''), ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['standings', '#/standings/forecast', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['standings-seeds', '#/standings/seeds', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['standings-ratings', '#/standings/ratings', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['standings-wins', '#/standings/wins', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['standings-picture', '#/standings/picture', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['season', '#/standings/races', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['season-movers', '#/standings/movers', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['season-leaders', '#/standings/leaders', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['about', '#/about', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['teams', '#/teams', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['team', '#/team/14', ['desktop', 'half', 'phone'], ['light', 'dark']],
  ['team-no-proj', '#/team/20', ['desktop', 'half', 'phone'], ['light', 'dark']],
  ['legacy-season', '#/season', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['lineup-game', '#/game/' + (args['lineup-game'] || ''), ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['lineup-sits', '#/game/' + (args['lineup-game'] || ''), ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['lineup-scenario', '#/game/' + (args['lineup-game'] || '') + '/scenario', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['lineup-sheet', '#/game/' + (args['lineup-game'] || '') + '/player/' + (args['lineup-player'] || ''), ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['player-search', '#/players', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['today-headshots', '#/today/2026-11-23', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['players', '#/players', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['player', '#/player/3032977', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['lab', '#/lab', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['scenario', '#/game/401909305/scenario', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['scenario-set', '#/game/401909305/scenario/' + encodeURIComponent(JSON.stringify([{subj: 'p:4701230', v: 'pts', op: 'ge', x: 30}, {subj: 't:home', v: 'win'}])), ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['team-drivers', '#/game/401909305/fg/team', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['team-stories', '#/game/401909305/fg/team', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['game-flow', '#/game/401910029/fg/team', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['game-advanced', '#/game/401910029/fg/team', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['sheet-advanced', '#/game/401910030/player/4278053/fg', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['players-house', '#/players', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['player-house', '#/player/3032977', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['today-house', '#/today/2026-11-22', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['game-house', '#/game/401910029', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['availability-slices', '#/game/401910034', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['availability-archived', '#/game/401910034', ['desktop'], ['light']],
  ['game-final-house', '#/game/401910009', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['team-house', '#/team/14', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['team-no-proj-house', '#/team/20', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['sheet-whatif', '#/game/401909305/player/4701230/fg', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['today-leaders', '#/today/2026-11-21', ['desktop', 'half', 'phone'], ['dark', 'light']],
  ['tomorrow', '#/today/2026-11-22', ['desktop', 'half', 'phone'], ['dark']],
].filter(c => (!only || only.includes(c[0])) && !(c[0] === 'future-game' && !args.future) && (!c[0].startsWith('lineup-') || args['lineup-game']) && (c[0] !== 'lineup-sheet' || args['lineup-player']));

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
      if (msg.method === 'Log.entryAdded' && msg.params.entry.level === 'error') {
        const entry = msg.params.entry;
        if (!(name === 'boot-retry' && entry.url?.endsWith('/assets/league.mjs') && entry.text.includes('ERR_BLOCKED_BY_CLIENT'))) errors.push(entry.text + ' ' + (entry.url || ''));
      }
    };
    listeners.push(onMsg);
    await send('Page.enable', {}, sessionId);
    await send('Runtime.enable', {}, sessionId);
    await send('Log.enable', {}, sessionId);
    await send('Emulation.setDeviceMetricsOverride', {width, height, deviceScaleFactor: scale, mobile}, sessionId);
    if (mobile) await send('Emulation.setTouchEmulationEnabled', {enabled: true, maxTouchPoints: 5}, sessionId);
    await send('Emulation.setEmulatedMedia', {features: [{name: 'prefers-color-scheme', value: theme}]}, sessionId);
    if (name === 'availability-slices' || name === 'availability-archived') await send('Page.addScriptToEvaluateOnNewDocument', {source: `{
      const RealDate = Date, fixed = RealDate.parse(${JSON.stringify(name === 'availability-slices' ? '2026-11-22T18:00:00Z' : '2026-11-23T18:00:00Z')});
      globalThis.Date = class extends RealDate {
        constructor(...args) { super(...(args.length ? args : [fixed])); }
        static now() { return fixed; }
      };
    }`}, sessionId);
    if (name === 'boot-retry') {
      await send('Network.enable', {}, sessionId);
      await send('Network.setBlockedURLs', {urls: ['*/assets/league.mjs']}, sessionId);
    }
    await send('Page.navigate', {url: BASE + '/' + hash}, sessionId);
    let ready = false;
    for (let i = 0; i < 60 && !ready; i++) {
      await sleep(150);
      const {result} = await send('Runtime.evaluate', {expression: "document.readyState === 'complete' && !document.querySelector('#view[aria-busy]') && !document.querySelector('#view .loading') && !!document.querySelector('#view > *')", returnByValue: true}, sessionId).catch(() => ({result: {}}));
      ready = result.value === true;
    }
    let interaction = true;
    if(name==='season-movers') interaction=(await send('Runtime.evaluate',{expression:`(async()=>{const ui=await import('./assets/ui.mjs'),d=await ui.api('season_movers'),text=document.querySelector('#view').textContent;return d.from?text.includes('Since the previous forecast'):text.includes('A previous season forecast')&&!document.querySelector('.mover-card');})()`,awaitPromise:true,returnByValue:true},sessionId)).result.value===true;
    if (name.startsWith('c5-')) {
      interaction = (await send('Runtime.evaluate', {expression: `(async()=>{
        const ui=await import('./assets/ui.mjs'),data=await ui.api('competitions/'+ui.meta().latest);
        if(!data.schema)return false;
        if(${JSON.stringify(name)}==='c5-regular')return [...document.querySelectorAll('a[data-nav]')].length===6 && document.querySelector('#view').textContent.includes('Top 6');
        const helper=await import('./assets/competition-paths.mjs'),paths=helper.decodePaths(data);
        if(!paths||document.querySelectorAll('[data-competition-stages] tbody tr').length!==30)return false;
        document.querySelector('.competition-condition').open=true;
        const select=document.querySelector('[data-condition]');select.value='title';select.dispatchEvent(new Event('change'));
        const tid=document.querySelector('[data-condition-team]').value,expected=helper.stageSummary(paths,helper.conditionMask(paths,tid,'title'));
        if(!document.querySelector('.competition-support').textContent.includes(expected.count.toLocaleString()+' matching paths'))return false;
        const reset=document.querySelector('[data-reset]');reset.click();
        const stage=document.querySelector('[data-stage]');stage.value=${JSON.stringify(name==='c5-cup'?'cup_final':'finals')};stage.dispatchEvent(new Event('change'));
        const expectedMatches=helper.matchups(paths,stage.value);
        if(document.querySelectorAll('[data-competition-matchups] tbody tr').length!==expectedMatches.rows.length)return false;
        await Promise.resolve();
        const th=document.querySelector('[data-competition-stages] th:nth-child(2)');th.click();
        if(!th.hasAttribute('aria-sort'))return false;
        const selector=${JSON.stringify(Boolean(args['all-c5-targets']))}?'.mainnav a,#view select,#view button,#view summary,#view th[role=button]':'.mainnav a,.competition-condition select,.competition-condition button,.competition-condition summary';
        return [...document.querySelectorAll(selector)].filter(el=>el.getClientRects().length&&el.getBoundingClientRect().height>0).every(el=>el.getBoundingClientRect().height>=44);
      })()`,awaitPromise:true,returnByValue:true},sessionId)).result.value===true;
    }
    if (name.startsWith('c4-')) {
      interaction = (await send('Runtime.evaluate', {expression: `(async () => {
        const kind=${JSON.stringify(name)}, gid=${JSON.stringify(args['lineup-game'] || (name==='c4-lineup'?'401910037':'401910036'))};
        const ui=await import('./assets/ui.mjs'), data=await ui.api('game/'+gid);
        if([...document.querySelectorAll('[data-view="analysis"],[data-view="replay"],[data-analysis-tab]')].some(el=>el.getBoundingClientRect().height<44))return false;
        if(kind==='c4-lineup') {
          const O=await import('./assets/outcomes.mjs'),G=await import('./assets/game.mjs'),R=await import('./assets/replay.mjs');
          const source=await ui.api(data.court.path),payload=await ui.api(data.replay.path),pid=data.projection.sim.lineups?.selected_players?.[0]?.player_id;
          if(!pid)return false;
          for(const choice of [false,true]) {
            O.chooseLineup(gid,pid,choice);await G.render(document.querySelector('#view'),{rest:[gid,'analysis'],current:()=>true});
            const subject=document.querySelector('[data-metric-subject]');subject.value='t:home';subject.dispatchEvent(new Event('change'));
            const expected=Object.values(source.cases).find(c=>Object.keys(c.choices).length===1&&c.choices[pid]===choice);
            const row=document.querySelector('[data-court-body] tbody tr'),shown=Number(row?.cells[2].textContent);
            if(!expected||Math.abs(shown-expected.home.attempts[0])>.051)return false;
            await G.render(document.querySelector('#view'),{rest:[gid,'replay'],current:()=>true});
            const compatible=payload.examples.filter(e=>R.compatibleExample(e,{[pid]:choice})),select=document.querySelector('[data-replay-example]');
            if(compatible.length ? select?.options.length!==compatible.length : !document.querySelector('#game-body').textContent.includes('other lineup cases'))return false;
          }
          O.chooseLineup(gid,pid,null);await G.render(document.querySelector('#view'),{rest:[gid,'analysis'],current:()=>true});return true;
        }
        if(kind==='c4-replay') {
          const input=document.querySelector('[data-replay-seek]');if(!input)return false;
          const payload=await ui.api(data.replay.path), helper=await import('./assets/replay.mjs');
          if(payload.examples.length!==5)return false;
          for(const example of payload.examples) {
            const state=helper.replayState(example,example.events.length,payload.players);
            if(JSON.stringify(state.score)!==JSON.stringify(example.final_score))return false;
            for(const p of payload.players) {
              const actual=state.lines[p.id],expected=example.final_box[p.id];
              if(Math.abs(actual.min-expected.min)>1e-8)return false;
              for(const key of helper.BOX)if(actual[key]!== (key==='reb'?expected.oreb+expected.dreb:expected[key]))return false;
            }
          }
          document.querySelector('[data-replay-next]').click();if(Number(input.value)!==1)return false;
          document.querySelector('[data-replay-back]').click();if(Number(input.value)!==0)return false;
          input.value=input.max;input.dispatchEvent(new Event('input',{bubbles:true}));
          const expected=payload.examples[0].final_score;
          if(!document.querySelector('[data-replay-score]').textContent.includes(String(expected[0]))||!document.querySelector('[data-replay-score]').textContent.includes(String(expected[1])))return false;
          const quarter=document.querySelector('[data-replay-quarter]');quarter.value='2';quarter.dispatchEvent(new Event('change',{bubbles:true}));
          if(!document.querySelector('[data-replay-score]').textContent.includes('Q2'))return false;
          document.querySelector('[data-replay-play]').click();await new Promise(r=>setTimeout(r,350));document.querySelector('[data-replay-play]').click();
          const log=document.querySelector('[data-replay-log] table');if(!log||!log.hasAttribute('data-no-sort')||log.querySelector('th.sortable'))return false;
          globalThis.__c4Audit={stage:'sort'};ui.wireSortableTables(document.querySelector('#game-body'));
          const box=document.querySelector('[data-replay-box] table'),heads=[...box.tBodies[0].rows].filter(r=>r.classList.contains('group')).map(r=>r.textContent);
          box.tHead.rows[0].cells[2].click();
          let prior=Infinity,groups=0;
          for(const row of box.tBodies[0].rows){if(row.classList.contains('group')){prior=Infinity;groups++;}else{const points=Number(row.cells[2].textContent);if(points>prior)return false;prior=points;}}
          if(groups!==2||JSON.stringify(heads)!==JSON.stringify([...box.tBodies[0].rows].filter(r=>r.classList.contains('group')).map(r=>r.textContent)))return false;
          globalThis.__c4Audit={stage:'timeline'};document.querySelector('[data-replay-timeline]').closest('details').open=true;
          if(document.querySelectorAll('.replay-rotation-team').length!==2||document.querySelectorAll('.replay-rotation-axis>span').length<5)return false;
          const tracks=[...document.querySelectorAll('.replay-rotation-track')];if(tracks.length!==payload.players.length)return false;
          const example=payload.examples[0],last=example.events.at(-1),end=last.period<=4?last.period*720:2880+(last.period-4)*300;
          for(let i=0;i<tracks.length;i++){const bars=[...tracks[i].querySelectorAll('i')],percent=bars.reduce((sum,bar)=>sum+Number.parseFloat(bar.style.width),0);const error=Math.abs(percent*end/6000-example.final_box[payload.players[i].id].min);// CSS percentages are serialized with finite decimal precision; raw event seconds are audited separately.
            if(error>bars.length*1e-5*end/6000+1e-8){globalThis.__c4Audit={stage:'timeline',error,percent,end,player:payload.players[i].id};return false;}}
          globalThis.__c4Audit={stage:'jump'};const jump=document.querySelector('[data-replay-jump="3"]');jump.click();if(Number(input.value)!==3)return false;
          return [...document.querySelectorAll('.replay-controls button,.replay-controls select,[data-replay-seek]')].every(e=>e.getBoundingClientRect().height>=44);
        }
        document.querySelector('[data-analysis-tab="metrics"]')?.click();
        const subject=document.querySelector('[data-metric-subject]');if(!subject)return false;
        const query=document.querySelector('[data-metric-query]');query.value='true shooting';query.dispatchEvent(new Event('input',{bubbles:true}));
        if(document.querySelectorAll('[data-metric-cards] article').length!==1)return false;
        query.value='';query.dispatchEvent(new Event('input',{bubbles:true}));
        const cols=getComputedStyle(document.querySelector('.metric-catalogue')).gridTemplateColumns.split(' ').length;
        if(cols!==(innerWidth<=600?1:innerWidth<=1000?2:3))return false;
        if(kind==='c4-projected') {
          document.querySelector('[data-analysis-tab="shooting"]')?.click();
          const body=document.querySelector('[data-court-body]');if(!body?.querySelector('svg'))return false;
          const color=document.querySelector('[data-court-metric]');if(!color)return false;
          color.value='fg';color.dispatchEvent(new Event('change',{bubbles:true}));
          if(!body.querySelector('figcaption').textContent.includes('make percentage'))return false;
          const button=body.querySelector('[data-zone-button="0"]');if(!button)return false;button.click();
          return !!body.querySelector('[data-zone="0"].selected') && [...document.querySelectorAll('[data-court-analysis] select,[data-court-analysis] button')].filter(e=>e.getBoundingClientRect().width).every(e=>e.getBoundingClientRect().height>=44);
        }
        if(kind==='c4-observed') {
          document.querySelector('[data-analysis-tab="shooting"]')?.click();
          const display=document.querySelector('[data-court-display]');if(!display)return false;
          display.value='defense';display.dispatchEvent(new Event('change',{bubbles:true}));
          if(document.querySelectorAll('[data-court-body] tbody tr').length!==22||!document.querySelector('[data-court-body] svg'))return false;
          document.querySelector('[data-court-analysis]').scrollIntoView();
          return document.querySelector('[data-court-body]').textContent.includes('not nearest-defender');
        }
        const O=await import('./assets/outcomes.mjs'), Wd=await O.load(gid), court=await ui.api(data.court.path);
        const averageOf=values=>Wd.weights?O.branchCalculations(Wd).mean(values):O.mean(values);
        if(!Wd.hasZones)return false;
        for(const side of ['home','away']) {
          const fga=Wd.values('t:'+side,'fga'),all=['rim','paint','mid','corner3','above3'].map(z=>Wd.values('t:'+side,'zone_'+z+'_fga'));
          for(let w=0;w<Wd.W;w++)if(all.reduce((a,c)=>a+c[w],0)!==fga[w])return false;
          for(let z=0;z<5;z++)if(Math.abs(averageOf(all[z])-court.expected[side].attempts[z])>1e-10)return false;
          for(const [metric,d] of Object.entries(data.projection.sim[side].advanced)) {
            const key=metric==='two'?'twoPct':['oreb','dreb'].includes(metric)?metric+'Share':metric;
            const values=Wd.values('t:'+side,key);if(!values)return false;
            const average=averageOf(values);if(d.defined&&Math.abs(average-d.exact_mean)>.000501)return false;
          }
        }
        document.querySelector('[data-metric-chart]')?.setAttribute('open','');
        await new Promise(r=>setTimeout(r,100));
        return !!document.querySelector('[data-metric-chart] svg');
      })()`, returnByValue: true, awaitPromise: true}, sessionId)).result.value === true;
    }
    if(!interaction && name.startsWith('c4-')) console.log('C4 audit',JSON.stringify((await send('Runtime.evaluate',{expression:'globalThis.__c4Audit',returnByValue:true},sessionId)).result));
    if (name === 'boot-retry') interaction = (await send('Runtime.evaluate', {expression: `document.querySelector('#view [role="alert"]')?.textContent.includes('couldn’t load') && document.querySelector('#boot-retry')?.getBoundingClientRect().height >= 44`, returnByValue: true}, sessionId)).result.value === true;
    if (name === 'team-stories') {
      interaction = (await send('Runtime.evaluate', {expression: `(async () => {
        for (let i = 0; i < 80 && !document.querySelector('[data-game-stories]'); i++) await new Promise(r => setTimeout(r, 100));
        const ui = await import('./assets/ui.mjs'), O = await import('./assets/outcomes.mjs');
        const Wd = await O.load('401909305'), groups = [...document.querySelectorAll('[data-game-stories]')];
        if (groups.length !== 2) return false;
        const columns = innerWidth <= 600 ? 1 : innerWidth <= 1000 ? 2 : 3;
        for (const group of groups) {
          if (getComputedStyle(group).gridTemplateColumns.split(' ').length !== columns) return false;
          const links = [...group.querySelectorAll('a.story-card')];
          if (links.length !== 3) return false;
          const win = Wd.values('t:' + group.dataset.gameStories, 'win');
          for (let k = 0; k < links.length; k++) {
            const conditions = JSON.parse(decodeURIComponent(links[k].getAttribute('href').split('/').at(-1)));
            const values = conditions.map(c => Wd.values(c.subj, c.v));
            let n = 0, wins = 0;
            for (let w = 0; w < Wd.W; w++) if (conditions.every((c, i) => c.op === 'ge' ? values[i][w] >= c.x : values[i][w] <= c.x)) { n++; wins += win[w]; }
            const expected = k === 0 ? n / Wd.W : n ? wins / n : null;
            if (links[k].querySelector('b').textContent !== ui.pct(expected, 1)
                || (n && !links[k].textContent.includes(n.toLocaleString() + ' matching worlds'))
                || links[k].getBoundingClientRect().height < 44) return false;
          }
        }
        const href = groups[0].querySelector('a').getAttribute('href');
        location.hash = href;
        for (let i = 0; i < 80 && !document.querySelector('#game-body .chip'); i++) await new Promise(r => setTimeout(r, 100));
        if (document.querySelectorAll('#game-body .chip').length !== 2) return false;
        location.hash = '#/game/401909305/fg/team';
        for (let i = 0; i < 80 && !document.querySelector('[data-game-stories]'); i++) await new Promise(r => setTimeout(r, 100));
        document.querySelector('[data-game-stories]')?.closest('section').scrollIntoView();
        return !!document.querySelector('[data-game-stories]');
      })()`, returnByValue: true, awaitPromise: true}, sessionId)).result.value === true;
    }
    if (name === 'availability-slices' || name === 'availability-archived') {
      interaction = (await send('Runtime.evaluate', {expression: `(async () => {
        const panel = document.querySelector('details[data-player-availability]');
        if (!panel) return false;
        panel.open = true;
        const links = [...panel.querySelectorAll('.av-slices a')];
        if (${JSON.stringify(name)} === 'availability-archived') return links.length === 0;
        const ui = await import('./assets/ui.mjs'), O = await import('./assets/outcomes.mjs');
        const data = await ui.api('game/401910034'), Wd = await O.load('401910034');
        const eligible = ['away', 'home'].flatMap(side => data.availability[side].filter(r =>
          r.assumed_availability > 0 && r.assumed_availability < 1
          && data.projection.sim[side].players.some(p => String(p.id) === String(r.id) && p.periods)));
        if (!eligible.length || links.length !== 2 * eligible.length) return false;
        const player = eligible.find(r => r.id === '3149673');
        if (!player) return false;
        for (const v of ['plays', 'sits']) {
          const href = '#/game/401910034/scenario/' + encodeURIComponent(JSON.stringify([{subj: 'p:' + player.id, v}]));
          const link = links.find(a => a.getAttribute('href') === href);
          if (!link || !link.getAttribute('aria-label').includes(player.name)) return false;
          const n = O.count(O.mask(Wd, [{subj: 'p:' + player.id, v}]));
          location.hash = href;
          for (let i = 0; i < 80 && !document.querySelector('#game-body .chip'); i++) await new Promise(r => setTimeout(r, 100));
          const body = document.querySelector('#game-body');
          if (!body?.textContent.includes(player.name) || !body.textContent.includes('not causal lineup what-ifs')
              || (n ? !body.textContent.includes(n.toLocaleString() + ' of ' + Wd.W.toLocaleString() + ' saved worlds')
                    : !body.textContent.includes('No simulated game matches'))) return false;
          location.hash = '#/game/401910034';
          for (let i = 0; i < 80 && !document.querySelector('details[data-player-availability]'); i++) await new Promise(r => setTimeout(r, 100));
        }
        const restored = document.querySelector('details[data-player-availability]');
        if (!restored) return false;
        restored.open = true;
        restored.scrollIntoView();
        return true;
      })()`, returnByValue: true, awaitPromise: true}, sessionId)).result.value === true;
    }
    if (name === 'future-game') {
      interaction = (await send('Runtime.evaluate', {expression: `(async () => {
        const ui = await import('./assets/ui.mjs');
        const game = await ui.api('game/' + ${JSON.stringify(args.future || '')});
        const dist = game.team_model?.regulation;
        const blocks = [...document.querySelectorAll('.pathway-grid [data-block]')];
        const awayPoints = document.querySelector('.bz-team.away .bz-stats b')?.textContent;
        const homePoints = document.querySelector('.bz-team.home .bz-stats b')?.textContent;
        const input = document.querySelector('[data-line="pathway-total"]');
        if (game.projection || !dist || blocks.length !== 3 || !input
            || awayPoints !== ui.f1(dist.away.mean) || homePoints !== ui.f1(dist.home.mean)
            || document.querySelector('[data-view="player"], [data-view="team"], [data-view="scenario"]')
            || !document.querySelector('#game-body').textContent.includes('the distributions shown here exclude overtime')) return false;
        input.value = '200.5';
        input.dispatchEvent(new Event('change', {bubbles: true}));
        if (document.querySelector('[data-block="pathway-total"] output')?.textContent !== 'Over: ' + ui.pct(ui.over(dist.total, 200.5))) return false;
        document.querySelector('[data-pathway-metric="margin"]').click();
        const margin = document.querySelector('[data-line="pathway-margin"]');
        if (!margin || document.querySelectorAll('.pathway-grid [data-block]').length !== 3) return false;
        margin.value = '-1.5';
        margin.dispatchEvent(new Event('change', {bubbles: true}));
        return document.querySelector('[data-block="pathway-margin"] output')?.textContent.endsWith(': ' + ui.pct(ui.over(dist.margin, -1.5)));
      })()`, returnByValue: true, awaitPromise: true}, sessionId)).result.value === true;
    }
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
        const log = document.querySelector('details[data-game-log]');
        if (!log || log.open || !log.querySelector('tr[data-gid]')) return false;
        log.open = true;
        if (!log.querySelector('tr[data-gid]').getBoundingClientRect().height) return false;
        if (history) { if (history.open) return false; history.open = true; if (!history.querySelector('table')) return false; }
        return !!next && !!advanced && !advanced.open
          && !!(next.compareDocumentPosition(advanced) & Node.DOCUMENT_POSITION_FOLLOWING);
      })()`, returnByValue: true}, sessionId)).result.value === true;
    }
    if (name === 'today-house') {
      interaction = (await send('Runtime.evaluate', {expression: `(async () => {
        const ui = await import('./assets/ui.mjs'), slate = await ui.api('slate/2026-11-22');
        const note = document.querySelector('#view .model-note')?.textContent || '';
        if (slate.completed_at && (!note.includes('snapshot updated ' + ui.stamp(slate.completed_at))
            || !note.includes('game forecast times may differ'))) return false;
        const games = document.querySelector('#view .games:not(.spot-grid)'), insights = document.querySelector('#view .spot-grid');
        const jump = document.querySelector('[data-insights]');
        if (!jump) return false;
        jump.click();
        await new Promise(resolve => setTimeout(resolve, 800));
        return !!games?.querySelector('.game-card') && !!insights
          && !!(games.compareDocumentPosition(insights) & Node.DOCUMENT_POSITION_FOLLOWING) && scrollY > 0;
      })()`, returnByValue: true, awaitPromise: true}, sessionId)).result.value === true;
    }
    if (name === 'game-house' || name === 'game-final-house') {
      interaction = (await send('Runtime.evaluate', {expression: `(() => {
        const availability = document.querySelector('details[data-player-availability]');
        const benches = [...document.querySelectorAll('details[data-bench-side]')];
        if (!benches.length || benches.some(x => x.open || !x.querySelector('tr[data-pid]'))) return false;
        if (${JSON.stringify(name)} === 'game-house' && (!availability || availability.open)) return false;
        const insights = document.querySelector('#game-insights'), jump = document.querySelector('[data-game-insights]');
        if (${JSON.stringify(name)} === 'game-house' && (!insights || !jump
            || !(benches[0].compareDocumentPosition(insights) & Node.DOCUMENT_POSITION_FOLLOWING))) return false;
        jump?.click();
        if (availability) availability.open = true;
        benches.forEach(x => { x.open = true; });
        if (benches.some(x => x.querySelector('tr[data-pid]').getBoundingClientRect().height === 0)) return false;
        const mode = [...document.querySelectorAll('[data-mode]')].find(x => x.getAttribute('aria-pressed') !== 'true');
        if (mode) {
          mode.click();
          if (availability && !document.querySelector('details[data-player-availability]')?.open) return false;
          if ([...document.querySelectorAll('details[data-bench-side]')].some(x => !x.open)) return false;
        }
        document.querySelector('details[data-bench-side]').scrollIntoView();
        return !!document.querySelector('table.box tbody .sep');
      })()`, returnByValue: true}, sessionId)).result.value === true;
    }
    if (name === 'team-house' || name === 'team-no-proj-house') {
      interaction = (await send('Runtime.evaluate', {expression: `(() => {
        const bench = document.querySelector('[data-roster-group="Bench"]');
        const rows = [...document.querySelectorAll('tr[data-roster-member="Bench"]')];
        if (!bench || bench.getAttribute('aria-expanded') !== 'false' || !rows.length
            || rows.some(x => !x.hidden || x.getBoundingClientRect().height)) return false;
        bench.click();
        if (bench.getAttribute('aria-expanded') !== 'true' || rows.some(x => x.hidden || !x.getBoundingClientRect().height)) return false;
        document.querySelector('[data-tt="schedule"]').click();
        document.querySelector('[data-tt="roster"]').click();
        const restored = document.querySelector('[data-roster-group="Bench"]');
        restored.scrollIntoView();
        return restored.getAttribute('aria-expanded') === 'true'
          && [...document.querySelectorAll('tr[data-roster-member="Bench"]')].every(x => !x.hidden);
      })()`, returnByValue: true}, sessionId)).result.value === true;
    }
    if (name.startsWith('lineup-')) {
      interaction = (await send('Runtime.evaluate', {expression: `(async () => {
        const select = document.querySelector('[data-lineup]'); if (!select) return false;
        const ui = await import(new URL('assets/ui.mjs',location.href)), O = await import(new URL('assets/outcomes.mjs',location.href));
        const gid = ${JSON.stringify(args['lineup-game'] || '')};
        const game = await ui.api('game/'+gid), raw = await ui.api('game/'+gid+'/worlds');
        const initial = await O.load(gid);
        if (initial.W !== game.projection.sim.sims || O.branchCalculations(initial).mass(null) !== game.projection.sim.probability_mass) return false;
        if (${JSON.stringify(name)} !== 'lineup-sits') return !document.querySelector('#view').textContent.includes('Research · not a forecast');
        const pid = select.dataset.lineup; select.value='unavailable'; select.dispatchEvent(new Event('change',{bubbles:true}));
        for(let i=0;i<100;i++) { await new Promise(r=>setTimeout(r,50)); if(document.querySelector('[data-lineup]')?.value === 'unavailable' && !document.querySelector('[data-lineup]').disabled) break; }
        const choice = raw.selected_players.map(p=>p.player_id===pid?'0':'x').join(''), expected=raw.cases[choice].sim;
        const loaded=await O.load(gid), C=O.branchCalculations(loaded);
        return document.querySelector('[data-lineup]').value==='unavailable'
          && C.mass(null)===expected.probability_mass
          && C.mean(loaded.minuteValues(pid,'fg'))===0
          && Math.abs(C.mean(loaded.values('t:home','pts'))-expected.periods.fg.home.pts.mean)<.000501
          && document.querySelector('.bz-team.home .bz-stats b')?.textContent === ui.f1(expected.periods.fg.home.pts.mean);
      })()`, returnByValue:true, awaitPromise:true}, sessionId)).result.value === true;
    }
    if (name === 'player-search') {
      interaction = (await send('Runtime.evaluate', {expression: `(async () => {
        document.querySelector('#search-open').click();
        const input = document.querySelector('#search-input'); input.value = 'james'; input.dispatchEvent(new Event('input', {bubbles:true}));
        for (let i=0;i<40 && !document.querySelector('#search-results .player-face img');i++) await new Promise(r=>setTimeout(r,100));
        return document.querySelector('#search-dialog').open && !!document.querySelector('#search-results .player-face img');
      })()`, returnByValue:true, awaitPromise:true}, sessionId)).result.value === true;
    }
    if (name === 'today-headshots') {
      interaction = (await send('Runtime.evaluate', {expression: `(() => {
        const panel = document.querySelector('#slate-insights'); if (!panel) return false;
        panel.scrollIntoView(); return panel.querySelectorAll('.player-face').length >= 6;
      })()`, returnByValue:true}, sessionId)).result.value === true;
    }
    if (name.startsWith('u24-')) {
      interaction = (await send('Runtime.evaluate', {expression: `(async () => {
        const kind = ${JSON.stringify(name)};
        const wait = async test => { for (let i=0;i<100;i++) { if (test()) return true; await new Promise(r=>setTimeout(r,100)); } return false; };
        if (kind === 'u24-roster-sort') {
          const form=document.querySelector('[data-disclosure^="team-form-"]'); if(form) {form.open=true;await new Promise(r=>setTimeout(r,30));}
          const table=document.querySelector('table.roster'); if (!table) return false;
          const headers=[...table.tHead.rows[0].cells], index=headers.findIndex(h=>h.dataset.sortHeading==='PTS');
          if (index<0) return false;
          const groups=[...table.querySelectorAll('tr.grp')].map(r=>r.textContent);
          const check = direction => { let last=null; for (const row of table.tBodies[0].rows) {
            if (row.classList.contains('grp')) { last=null; continue; }
            const value=Number(row.cells[index].textContent); if (Number.isNaN(value)) continue;
            if(last!=null && direction*(value-last)<0) return false; last=value;
          } return true; };
          headers[index].click(); if (!check(-1)) return false;
          headers[index].dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
          if (!check(1) || JSON.stringify(groups)!==JSON.stringify([...table.querySelectorAll('tr.grp')].map(r=>r.textContent))) return false;
          const bench=table.querySelector('[data-roster-group="Bench"]'); bench?.click();
          return !bench || [...table.querySelectorAll('tr[data-roster-member="Bench"]')].every(r=>!r.hidden);
        }
        if (kind === 'u24-players-sort') {
          const heading=document.querySelector('th[data-sort="name"]'); if (!heading) return false;
          heading.click();
          const names=[...document.querySelectorAll('#ptable tbody .player-label > span:last-child')].map(e=>e.textContent);
          if(names.length<3 || names.some((n,i)=>i && names[i-1].localeCompare(n)>0)) return false;
          const team=document.querySelector('th[data-sort="team"]'); team.dispatchEvent(new KeyboardEvent('keydown',{key:' ',bubbles:true}));
          return document.querySelector('th[data-sort="team"]').getAttribute('aria-sort')==='ascending';
        }
        if (kind === 'u24-standings-controls') {
          let d=document.querySelector('[data-disclosure="forecast-controls"]'); if (!d || d.open) return false;
          d.open=true; await new Promise(r=>setTimeout(r,30));
          const input=document.querySelector('[data-fwins]'); input.value='45'; input.dispatchEvent(new Event('change'));
          d=document.querySelector('[data-disclosure="forecast-controls"]');
          if(!d.open || !d.textContent.includes('45')) return false;
          document.querySelector('th[data-fsort="name"]').click();
          return document.querySelector('th[data-fsort="name"]').getAttribute('aria-sort')==='ascending';
        }
        const ui=await import('./assets/ui.mjs'), O=await import('./assets/outcomes.mjs');
        const gid=location.hash.split('/')[2], data=await ui.api('game/'+gid);
        if (kind === 'u24-scenario') {
          const player=['home','away'].flatMap(s=>data.projection.sim[s].players).find(p=>p.periods && p.periods.fg.mean.pts>10);
          const root=document.querySelector('[data-builder="scn"]'); if(!root || !player) return false;
          const select=(key,value)=>{const el=root.querySelector('[data-b="'+key+'"]');el.value=value;el.dispatchEvent(new Event('change'));};
          select('subj','p:'+player.id);select('v','fga');select('op','eq');
          root.querySelector('[data-b="x"]').value='10';root.querySelector('[data-b="add"]').click();
          if(!await wait(()=>document.querySelector('#game-body .chip'))) return false;
          const W=await O.load(gid), C=W.weights?O.branchCalculations(W):O;
          const m=O.mask(W,[{subj:'p:'+player.id,v:'fga',op:'eq',x:10}]), base=O.mask(W,[]);
          const expected=ui.pct((C.mass?C.mass(m):C.count(m))/(C.mass?C.mass(base):C.count(base)),1);
          const chance=[...document.querySelectorAll('#game-body .tile')].find(e=>e.textContent.includes('Chance of this scenario'));
          if(!chance || chance.querySelector('b').textContent!==expected) return false;
          document.querySelector('[data-scenario-box="efficiency"]').click();
          return [...document.querySelectorAll('#game-body table.box th')].some(e=>e.textContent.includes('TS%'));
        }
        if (kind === 'u24-advanced') {
          const panel=document.querySelector('[data-advanced-panel]'); if(!panel) return false; panel.open=true;
          const player=data.projection.sim.home.players.concat(data.projection.sim.away.players).find(p=>p.id===location.hash.split('/')[4]);
          if(!player) return false;
          const d=player.periods.fg.advanced.efg;
          if(!panel.textContent.includes(d.worlds.toLocaleString()+' saved worlds') || /100,000.*worlds/.test(panel.textContent)) return false;
          const dist=panel.querySelector('details[data-metric="efg"]');dist.open=true;
          return await wait(()=>dist.querySelector('svg')) && [...panel.querySelectorAll('a[href*="/scenario/"]')].every(a=>a.getBoundingClientRect().height>=44);
        }
        if (kind === 'u24-lineup-compare') {
          const detail=document.querySelector('.lineup-compare');if(!detail) return false;detail.open=true;
          const buttons=[...detail.querySelectorAll('[data-lineup-case]')];if(buttons.length<3) return false;
          buttons.find(b=>!b.dataset.lineupCase.includes('x')).click();
          if(!await wait(()=>document.querySelector('[data-research-lineups] p')?.textContent.includes('Selected lineup'))) return false;
          const panels=[...document.querySelectorAll('[data-advanced-panel]')];if(panels.length!==2) return false;
          panels.forEach(p=>p.open=true);
          const compare=document.querySelector('.lineup-compare');compare.open=true;
          return panels.every(p=>p.querySelectorAll('.advanced-grid > .tile').length===18);
        }
        return false;
      })()`,returnByValue:true,awaitPromise:true},sessionId)).result.value===true;
    }
    await sleep(250);
    const {result: dims} = await send('Runtime.evaluate', {returnByValue: true, expression: `(() => {
      const wide = [...document.querySelectorAll('body *')].filter(el => { const r = el.getBoundingClientRect(); return r.right > innerWidth + 1 && !el.closest('.scroll') && getComputedStyle(el).position !== 'fixed'; }).slice(0, 5).map(el => el.tagName.toLowerCase() + (el.className ? '.' + String(el.className).split(' ')[0] : ''));
      return {scrollWidth: document.documentElement.scrollWidth, innerWidth, height: document.documentElement.scrollHeight, wide, title: document.querySelector('#view h2')?.textContent || ''};
    })()`}, sessionId);
    const d = dims.value;
    const overflow = d.scrollWidth > d.innerWidth + 1;
    const u24Focus = args.focus || {'c4-lineup':'[data-court-analysis]', 'c4-projected':'[data-court-analysis]', 'c4-observed':'[data-court-analysis]', 'c4-analysis':'[data-metric-cards]', 'c4-replay':'[data-replay-score]', 'u24-roster-sort':'table.roster','u24-players-sort':'#ptable','u24-standings-controls':'[data-disclosure="forecast-controls"]','u24-advanced':'[data-advanced-panel]','u24-scenario':'[data-scenario-box]','u24-lineup-compare':'.lineup-compare'}[name];
    const focusedTop = u24Focus ? (await send('Runtime.evaluate',{expression:`Math.max(0,document.querySelector(${JSON.stringify(u24Focus)})?.getBoundingClientRect().top + scrollY - 20 || 0)`,returnByValue:true},sessionId)).result.value : 0;
    const panelTop = u24Focus ? focusedTop : ['game-advanced', 'team-stories', 'today-headshots'].includes(name) ? (await send('Runtime.evaluate', {expression: `document.querySelector(${JSON.stringify(name === 'team-stories' ? '[data-game-stories]' : name === 'today-headshots' ? '#slate-insights' : '#view details.panel')})?.getBoundingClientRect().top + scrollY || 0`, returnByValue: true}, sessionId)).result.value : 0;
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
