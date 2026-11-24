// Discover every supported stored advanced distribution in the current lineup context.
import {ADVANCED_METRICS, api, esc, f1, pct, histogram, team} from './ui.mjs';
import {courtMap, zoneTable, wireCourt, observedMap} from './court.mjs';
import {scenarioMetricKey} from './box-metrics.mjs';
export function metricSearch(metrics, text) {
  const terms = String(text || '').toLowerCase().split(/\s+/).filter(Boolean);
  return metrics.filter(m => terms.every(term => [m[0],m[1],m[2]].join(' ').toLowerCase().includes(term)));
}
export async function exploreView(root, data, current, initialSubject = null) {
  const sim = data.projection?.sim;
  if (!sim) {root.innerHTML='<section class="panel"><h2>Game analysis</h2><p class="note">Stored possession worlds are needed for player and team metric exploration.</p></section>';return;}
  const subjects = ['away','home'].flatMap(side => [
    {id:`t:${side}`,name:team(data.game[side].id).name,kind:'team',values:sim[side].advanced},
    ...sim[side].players.map(p=>({id:`p:${p.id}`,name:p.name,kind:'player',values:p.advanced})),
  ]);
  let selected=subjects.find(s=>s.id===initialSubject)||subjects[0],query='',paintCourt=null;
  root.classList.add('analysis-view');
  root.innerHTML=`<section class="panel"><h2>Game analysis</h2><p class="note">Explore stored worlds and recorded shot support. The lineup selection above applies throughout.</p><div class="metric-search"><label>Team or player<select data-metric-subject aria-label="Metric subject">${subjects.map(s=>`<option value="${esc(s.id)}"${s.id===selected.id?' selected':''}>${esc(s.name)}</option>`).join('')}</select></label><div class="seg" role="group" aria-label="Analysis tool">${data.court?'<button data-analysis-tab="shooting">Shooting zones</button>':''}<button data-analysis-tab="metrics">Metrics</button></div></div></section><section class="panel" data-analysis-metrics><h3>Explore the numbers</h3><label class="metric-search">Find a metric<input type="search" data-metric-query placeholder="Try shooting, rebounds or rating" aria-label="Find a metric"></label><p class="note" data-metric-count></p><div class="metric-catalogue" data-metric-cards></div></section><div data-court-analysis></div>`;
  const get=s=>root.querySelector(s);
  function chooseTool(tool) {
    get('[data-analysis-metrics]').hidden=tool!=='metrics';get('[data-court-analysis]').hidden=tool!=='shooting';
    root.querySelectorAll('[data-analysis-tab]').forEach(button=>{const active=button.dataset.analysisTab===tool;button.classList.toggle('on',active);button.setAttribute('aria-pressed',String(active));});
  }
  root.querySelectorAll('[data-analysis-tab]').forEach(button=>button.onclick=()=>chooseTool(button.dataset.analysisTab));
  chooseTool(data.court?'shooting':'metrics');
  function paint() {
    const allowed=ADVANCED_METRICS.filter(m=>!m[4]||selected.kind==='team');
    const matching=metricSearch(allowed,query);
    get('[data-metric-count]').textContent=`${matching.length} of ${allowed.length} metrics · ${selected.name}. A zero denominator remains undefined.`;
    get('[data-metric-cards]').innerHTML=matching.map(([key,title,formula,percent])=>{
      const d=selected.values?.[key],format=x=>Number.isFinite(x)?f1(x)+(percent?'%':''):'—';
      const supported=d&&Number.isFinite(d.defined_worlds??d.defined)&&(d.defined_worlds??d.defined)>0;
      const median=d?.exact_q?.[2];
      return `<article data-metric="${esc(key)}"><h4>${esc(title)}</h4><p>${esc(formula)}</p>${supported?`<strong>${format(median)}</strong> median<p>10–90%: ${format(d.exact_q[0])}–${format(d.exact_q[4])}<br>Mean ${format(d.exact_mean)}</p><p>Defined in ${(d.defined_worlds??d.defined).toLocaleString()} / ${(d.worlds??d.total).toLocaleString()} saved worlds${d.weighted?` · ${pct(d.defined/d.total)} weighted probability`:''}.</p><details data-metric-chart="${esc(key)}"><summary>Show distribution</summary><div></div><p>Chart values are rounded; summaries use all defined worlds.</p></details>${data.worlds?`<a href="#/game/${encodeURIComponent(data.game.id)}/scenario/${encodeURIComponent(JSON.stringify([{subj:selected.id,v:scenarioMetricKey(key,selected.kind),op:'ge',x:median}]))}">Condition on ${format(median)} or more →</a>`:''}`:'<p>Distribution unavailable in this snapshot, or no defined denominator.</p>'}</article>`;
    }).join('')||'<p class="note">No metrics match. Try fewer search terms.</p>';
    root.querySelectorAll('[data-metric-chart]').forEach(el=>el.addEventListener('toggle',()=>{
      if(!el.open||el.dataset.ready)return;
      const key=el.dataset.metricChart,d=selected.values[key],def=ADVANCED_METRICS.find(m=>m[0]===key);
      el.querySelector('div').innerHTML=histogram(d,{height:120,label:v=>f1(v/d.scale)+(def[3]?'%':'')});el.dataset.ready='true';
    }));
  }
  get('[data-metric-query]').oninput=e=>{query=e.target.value;paint();};
  get('[data-metric-subject]').onchange=e=>{selected=subjects.find(s=>s.id===e.target.value);paint();paintCourt?.();};paint();
  if (data.court) {
    const court=await api(data.court.path||`game/${data.game.id}/court`);
    if(!current())return;
    if(court.source_id!==data.court.source_id)throw new Error('Court analysis source differs');
    const el=get('[data-court-analysis]');
    // Backend supplies exactly the active lineup summary; historical regions retain their own source taxonomy.
    const choices=data._lineup?.choices||{};
    const chosen=Object.values(court.cases||{}).find(c=>Object.keys(c.choices||{}).length===Object.keys(choices).length&&Object.entries(choices).every(([pid,value])=>c.choices?.[pid]===value))||(!Object.keys(choices).length?court.expected:null);
    if(!chosen){el.innerHTML='<section class="panel"><h2>Shooting zones</h2><p class="note">This saved court summary is unavailable for the selected lineup.</p></section>';return;}
    let metric='mix',display='projected';
    el.innerHTML=`<section class="panel"><h2>Shooting zones · <span data-court-name></span></h2><div class="replay-controls"><label>Source<select data-court-display><option value="projected">Forecast shots</option>${court.observed?'<option value="offense">Observed shots taken</option><option value="defense">Observed opponent exposure</option>':''}</select></label><label data-court-colour>Colour<select data-court-metric><option value="mix">Share of attempts</option><option value="fg">Make percentage</option></select></label></div><p class="note">Forecast and observed regions keep their own geometry. The team/player selection above applies to both.</p><div data-court-body></div><details><summary>Source, unknowns and spatial support</summary><p class="note">${esc(court.spatial_precision)} ${esc(court.missingness)}</p></details></section>`;
    paintCourt=()=>{
      el.querySelector('[data-court-name]').textContent=selected.name;
      el.querySelector('[data-court-colour]').hidden=display!=='projected';
      if(display!=='projected') {el.querySelector('[data-court-body]').innerHTML=observedMap(court.observed,selected.id,display);return;}
      const values=selected.kind==='team'?chosen[selected.id.slice(2)]:chosen.players?.[selected.id.slice(2)];
      if(!values){el.querySelector('[data-court-body]').innerHTML='<p class="note">No stored zone counts for this subject.</p>';return;}
      const attemptsLinks=data.worlds?`<div class="replay-controls">${['rim','paint','mid','corner3','above3'].map((key,i)=>{const line=Math.floor(values.attempts[i])+1;return `<a class="btn ghost sm" href="#/game/${encodeURIComponent(data.game.id)}/scenario/${encodeURIComponent(JSON.stringify([{subj:selected.id,v:'zone_'+key+'_fga',op:'ge',x:line}]))}">${esc(['Rim','Paint','Midrange','Corner3','Above3'][i])}: ${line}+ attempts →</a>`;}).join('')}</div>`:'';
      el.querySelector('[data-court-body]').innerHTML=`<div class="replay-grid"><div>${courtMap(values,{metric,label:'Projected shots · '+selected.name})}</div><div>${zoneTable(values,{projected:true})}<p class="note">Counts are exact weighted mean attempts/makes. Percentages use those totals. ${values.worlds.toLocaleString()} saved worlds; probabilities and no-attempt support remain in the stored source.</p></div></div>${attemptsLinks}`;wireCourt(el);
    };
    el.querySelector('[data-court-display]').onchange=e=>{display=e.target.value;paintCourt();};el.querySelector('[data-court-metric]').onchange=e=>{metric=e.target.value;paintCourt();};paintCourt();
  }
}
