// Render stored all-world on-court probabilities; no simulated/reconstructed rotations.
import {esc,pct,f1,team,wireSortableTables} from './ui.mjs';
export function validateRotation(map,sim) {
  if (!map) return false;
  if(map.schema!=='rotation-midpoints-v1'||map.seconds?.length!==48||map.seconds.some((s,i)=>s!==30+60*i)||!Number.isSafeInteger(map.worlds)||map.worlds<1||!Number.isSafeInteger(map.probability_mass)||map.probability_mass<1||!map.source_id)throw Error('Invalid stored rotation map');
  if(sim.lineups&&map.source_id!==sim.lineups.source_id)throw Error('Rotation source differs from lineup');
  for(const [s,side] of ['home','away'].entries()) {
    const players=sim[side].players;
    for(const p of players) {
      const v=map.players[p.id];
      if(!v||v.side!==s||v.probability?.length!==48||v.on_court_mass?.length!==48||v.probability.some((x,i)=>!Number.isFinite(x)||x<0||x>1||!Number.isSafeInteger(v.on_court_mass[i])||v.on_court_mass[i]<0||v.on_court_mass[i]>map.probability_mass||x!==v.on_court_mass[i]/map.probability_mass))throw Error('Invalid stored player rotation probabilities');
    }
    for(let j=0;j<48;j++)if(players.reduce((sum,p)=>sum+map.players[p.id].on_court_mass[j],0)!==5*map.probability_mass)throw Error('Stored rotation probabilities do not sum to five');
  }
  return true;
}
const clock=i=>`Q${Math.floor(i/12)+1} · ${String(11-i%12).padStart(2,'0')}:30 left`;
export function rotationView(root,data,getSelected) {
  const sim=data.projection?.sim,map=sim?.rotation_map;
  if(!validateRotation(map,sim)) {
    root.innerHTML='<section class="panel"><h2>Rotation probabilities</h2><p class="note">Unavailable in this older snapshot. Full-world rotation capture was not saved; selected replay examples cannot establish these probabilities.</p></section>';return ()=>{};
  }
  let index=0;
  root.innerHTML=`<section class="panel" data-rotation-map><h2>Who is likely to be on court?</h2><p class="note">Choose a moment to compare the whole roster. These are probabilities across all ${map.worlds.toLocaleString()} saved worlds, including worlds where a player sits.</p><div class="rotation-controls"><label>Quarter<select data-rotation-quarter>${[1,2,3,4].map(q=>`<option value="${q-1}">Q${q}</option>`).join('')}</select></label><label class="rotation-seek">Moment · <output data-rotation-clock></output><input type="range" data-rotation-time min="0" max="47" value="0" step="1" aria-label="Regulation minute midpoint"></label></div><div data-rotation-body></div><details><summary>How to read this map</summary><p class="note">${esc(map.definition)} The roster probabilities sum to five at every saved moment. Availability and rotations remain model assumptions. A player's usual minutes and this sampled timeline describe different things. The minutes column includes overtime. These probabilities use all worlds, rather than the five selected Saved worlds examples.</p><p class="note">${map.probability_mass.toLocaleString()} exact probability-weight units · source ${esc(map.source_id.slice(0,12))}.</p></details></section>`;
  const get=s=>root.querySelector(s);
  function paint() {
    const selected=getSelected(),side=selected.side,players=sim[side].players,q=Math.floor(index/12),quarter=Array.from({length:12},(_,j)=>q*12+j);
    get('[data-rotation-clock]').textContent=clock(index);get('[data-rotation-time]').value=index;get('[data-rotation-time]').setAttribute('aria-valuetext',clock(index));get('[data-rotation-quarter]').value=q;
    const player=selected.kind==='player'?players.find(p=>String(p.id)===selected.id.slice(2)):null;
    const curve=player?`<figure class="rotation-curve"><figcaption>${esc(player.name)} · chance of being on court</figcaption><svg viewBox="0 0 500 145" role="img" aria-label="${esc(player.name)} regulation on-court probability, zero to one hundred percent"><title>${esc(player.name)}: ${map.players[player.id].probability.map((p,j)=>`${clock(j)} ${pct(p)}`).join('; ')}</title>${[0,.5,1].map(p=>`<line x1="36" x2="484" y1="${112-96*p}" y2="${112-96*p}" stroke="var(--line)"/><text x="30" y="${116-96*p}" text-anchor="end">${p*100}%</text>`).join('')}<polyline points="${map.players[player.id].probability.map((p,j)=>`${36+j*448/47},${112-96*p}`).join(' ')}" fill="none" stroke="var(--accent)" stroke-width="3"/><line x1="${36+index*448/47}" x2="${36+index*448/47}" y1="12" y2="116" stroke="var(--ink)" stroke-dasharray="3 3"/>${[1,2,3,4].map((q,j)=>`<text x="${85+j*114}" y="137" text-anchor="middle">Q${q}</text>`).join('')}</svg></figure>`:'';
    get('[data-rotation-body]').innerHTML=`<h3>${esc(team(data.game[side].id).name)} · ${esc(clock(index))}</h3>${curve}<div class="table-wrap"><table data-rotation-table><thead><tr><th class="l">Player</th><th>On court</th><th>Forecast min</th></tr></thead>${[['Projected starters',true],['Bench / other players',false]].map(([label,start])=>`<tbody><tr class="grp"><td class="l" colspan="3">${label}</td></tr>${players.filter(p=>Boolean(p.starter)===start).map(p=>{const value=map.players[p.id].probability[index],mins=Number.isFinite(p.periods?.fg?.sec)?p.periods.fg.sec/60:null;return `<tr${player?.id===p.id?' class="rotation-selected"':''}><td class="l" data-sort-value="${esc(p.name)}">${esc(p.name)}</td><td data-sort-value="${value}"><span class="rotation-chance"><span style="--chance:${value*100}%"></span><b>${pct(value)}</b></span></td><td data-sort-value="${Number.isFinite(mins)?mins:''}">${Number.isFinite(mins)?f1(mins):'—'}</td></tr>`;}).join('')}</tbody>`).join('')}</table></div><details data-rotation-heatmap><summary>Quarter rotation map · Q${q+1}</summary><p class="note">Brighter means more likely to be on court. Each column is a minute midpoint, ordered from 11:30 to 00:30 left. Exact values appear when you select that moment above.</p><div class="rotation-map-axis"><span>Player</span><span>11:30 → 00:30 left</span></div>${players.map(p=>`<div class="rotation-map-row"><span>${esc(p.name)}</span><div>${quarter.map(j=>`<i style="--chance:${map.players[p.id].probability[j]}" title="${esc(p.name)} · ${clock(j)} · ${pct(map.players[p.id].probability[j])}" aria-label="${clock(j)} ${pct(map.players[p.id].probability[j])}"></i>`).join('')}</div></div>`).join('')}</details>`;
    wireSortableTables(root);
  }
  get('[data-rotation-time]').oninput=e=>{index=Number(e.target.value);paint();};get('[data-rotation-quarter]').onchange=e=>{index=Number(e.target.value)*12;paint();};paint();return paint;
}
