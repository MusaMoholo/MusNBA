// Focused rotation/research browser acceptance, reading saved API only.
import {spawn} from 'node:child_process';
import {mkdirSync,mkdtempSync,rmSync,writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
const args=Object.fromEntries(process.argv.slice(2).reduce((a,v,i,all)=>v.startsWith('--')?[...a,[v.slice(2),all[i+1]]]:a,[]));
if(!args.url||!args.game||!args.out)throw Error('--url --game --out required');
mkdirSync(args.out,{recursive:true});
const CHROME = args.chrome || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const profile = mkdtempSync(join(tmpdir(), 'musnba-pwa-'));
const chrome = spawn(CHROME, ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check', 'about:blank'], {stdio: ['ignore', 'ignore', 'pipe']});
process.once('exit', () => { chrome.kill(); try { rmSync(profile, {recursive: true, force: true}); } catch { /* best effort */ } });
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
for (const d of ['Page', 'Runtime', 'DOM', 'Network', 'Performance']) await send(d + '.enable', {}, s);
if (args['bypass-service-worker']) await send('Network.setBypassServiceWorker', {bypass: true}, s);
await send('Emulation.setDeviceMetricsOverride', {width: 390, height: 844, deviceScaleFactor: 2, mobile: true}, s);
const evaluate = async expression => {
  const result = await send('Runtime.evaluate', {expression, returnByValue: true, awaitPromise: true}, s);
  if (result.exceptionDetails) throw Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
  return result.result.value;
};
const waitFor = async (expression, ms = 20000) => { for (const end = Date.now() + ms; Date.now() < end; await sleep(200)) if (await evaluate(expression).catch(() => false)) return true; return false; };
const results = [];
const check = (name, ok, detail = '') => { results.push({name, ok, detail}); console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  ' + detail : ''}`); };


await send('Page.navigate',{url:args.url+'#/game/'+args.game+'/analysis'},s);
check('analysis loads',await waitFor(`!!document.querySelector('[data-analysis-tab="rotation"]')`));
await evaluate(`document.querySelector('[data-analysis-tab="rotation"]').click()`);
check('stored full-world rotation renders',await waitFor(`!!document.querySelector('[data-rotation-table]')`));
const provenance=await evaluate(`(async()=>{const ui=await import('./assets/ui.mjs'),g=await ui.api('game/'+${JSON.stringify(args.game)});return {game:g.game.id,source_id:g.projection.sim.rotation_map.source_id,worlds:g.projection.sim.rotation_map.worlds,model:g.projection.sim.model};})()`);
check('time and quarter controls, team/player, exact probabilities and sortable groups',await evaluate(`(async()=>{
 const slider=document.querySelector('[data-rotation-time]');slider.value='47';slider.dispatchEvent(new Event('input'));
 if(!document.querySelector('[data-rotation-clock]').textContent.includes('00:30'))return false;
 const q=document.querySelector('[data-rotation-quarter]');q.value='1';q.dispatchEvent(new Event('change'));
 if(slider.value!=='12')return false;
 const detail=document.querySelector('[data-rotation-heatmap]');detail.open=true;slider.value='13';slider.dispatchEvent(new Event('input'));if(!document.querySelector('[data-rotation-heatmap]').open)return false;
 const ui=await import('./assets/ui.mjs'),g=await ui.api('game/'+${JSON.stringify(args.game)}),side=document.querySelector('[data-analysis-team]').value;
 const rows=[...document.querySelectorAll('[data-rotation-table] tbody tr:not(.grp)')];
 if(!rows.length||!rows.every(r=>{const p=g.projection.sim[side].players.find(p=>p.name===r.cells[0].textContent);return p&&Number(r.cells[1].dataset.sortValue)===g.projection.sim.rotation_map.players[p.id].probability[13]&&(!Number.isFinite(p.periods?.fg?.sec)||Number(r.cells[2].dataset.sortValue)===p.periods.fg.sec/60);}))return false;
 document.querySelector('[data-subject-kind="player"]').click();
 if(!document.querySelector('.rotation-curve svg'))return false;
 document.querySelector('[data-analysis-team]').value='home';document.querySelector('[data-analysis-team]').dispatchEvent(new Event('change'));
 return document.querySelector('[data-rotation-table] thead th[aria-sort]')!==null&&document.querySelectorAll('[data-rotation-table] tbody').length===2;
})()`));
for(const [name,route,selector] of [['rotations','game/'+args.game+'/analysis','[data-rotation-map]'],['evidence','about','[data-research-evidence] [data-study="B2"]']]) {
 await send('Page.navigate',{url:args.url+'#/'+route},s);check(name+' ready',await waitFor(`!!document.querySelector(${JSON.stringify(selector)})`));
 if(name==='rotations')await evaluate(`document.querySelector('[data-analysis-tab="rotation"]').click();document.querySelector('[data-subject-kind="player"]').click();document.querySelector('[data-rotation-heatmap]').open=true`);
 else await evaluate(`document.querySelectorAll('[data-research-evidence] details').forEach(d=>d.open=true)`);
 for(const [size,width,height,mobile] of [['desktop',1440,1000,false],['half',960,1000,false],['phone',390,844,true]])for(const theme of ['dark','light']) {
  await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile},s);await evaluate(`document.documentElement.dataset.theme=${JSON.stringify(theme)}`);
  await evaluate(`document.querySelector(${JSON.stringify(name==='rotations'?'.analysis-header':'[data-research-evidence]')}).scrollIntoView()`);
  const layout=await evaluate(`({fits:document.documentElement.scrollWidth<=innerWidth,bad:[...document.querySelectorAll('${name==='rotations'?'[data-rotation-map]':'[data-research-evidence]'} button,${name==='rotations'?'[data-rotation-map]':'[data-research-evidence]'} select,${name==='rotations'?'[data-rotation-map]':'[data-research-evidence]'} input')].filter(e=>e.checkVisibility()&&e.getBoundingClientRect().height<43.9).map(e=>e.outerHTML)})`);
  check(name+' '+size+' '+theme,layout.fits&&!layout.bad.length,JSON.stringify(layout));
  const shot=await Promise.race([send('Page.captureScreenshot',{format:'png'},s),sleep(15000).then(()=>{throw Error('screenshot timeout')})]);writeFileSync(join(args.out,name+'-'+size+'-'+theme+'.png'),Buffer.from(shot.data,'base64'));
 }
}
await send('Page.navigate',{url:args.url+'#/game/'+args.game+'/analysis'},s);await waitFor(`!!document.querySelector('[data-analysis-tab="rotation"]')`);await evaluate(`document.querySelector('[data-analysis-tab="rotation"]').click();document.querySelector('[data-rotation-heatmap]').open=true`);
for(const [size,width,height,mobile] of [['desktop',1440,1000,false],['half',960,1000,false],['phone',390,844,true]])for(const theme of ['dark','light']) {
 await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile},s);await evaluate(`document.documentElement.dataset.theme=${JSON.stringify(theme)}`);
 await evaluate(`document.querySelector('[data-rotation-heatmap]').scrollIntoView({block:'end'})`);
 check('quarter map '+size+' '+theme,await evaluate(`document.documentElement.scrollWidth<=innerWidth&&document.querySelectorAll('.rotation-map-row').length>0&&[...document.querySelectorAll('.rotation-map-row>div')].every(r=>r.children.length===12)`));
 const shot=await Promise.race([send('Page.captureScreenshot',{format:'png'},s),sleep(15000).then(()=>{throw Error('screenshot timeout')})]);writeFileSync(join(args.out,'quarter-map-'+size+'-'+theme+'.png'),Buffer.from(shot.data,'base64'));
}
if(args.legacy) {
 await send('Page.navigate',{url:args.url+'#/game/'+args.legacy+'/analysis'},s);await waitFor(`!!document.querySelector('[data-analysis-tab="rotation"]')`);await evaluate(`document.querySelector('[data-analysis-tab="rotation"]').click()`);
 check('legacy rotation missingness explicit',await waitFor(`document.querySelector('[data-rotation-analysis]').textContent.includes('Unavailable in this older snapshot')`));
}
check('no uncaught errors',errors.length===0,errors.join(' | '));writeFileSync(join(args.out,'report.json'),JSON.stringify({results,errors,provenance},null,2));ws.close();console.log(results.filter(r=>r.ok).length+'/'+results.length+' passed');process.exit(results.some(r=>!r.ok)?1:0);
