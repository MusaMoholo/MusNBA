// Pooled model-zone diagrams. Geometry is schematic, with no inferred tracking locations.
import {esc, f1, pct} from './ui.mjs';
export const ZONES = ['Rim', 'Paint outside rim', 'Midrange', 'Corner three', 'Above-break three'];
const PATHS = [
  '<circle cx="250" cy="440" r="40"/>',
  '<path d="M170 440V250H330V440H290A40 40 0 0 0 210 440Z"/>',
  '<path d="M30 440V350A237.5 237.5 0 0 1 470 350V440H330V250H170V440Z"/>',
  '<path d="M4 350H30V488H4ZM470 350H496V488H470Z"/>',
  '<path d="M4 24H496V350H470A237.5 237.5 0 0 0 30 350H4Z"/>',
];
export function zoneRate(attempts, makes) {
  return Number.isFinite(attempts) && Number.isFinite(makes) && attempts > 0 ? makes / attempts : null;
}
export function courtMap(values, {highlight = null, label = 'Shooting by pooled model zone', metric = 'mix'} = {}) {
  const attempts = values.attempts, makes = values.makes;
  if (!Array.isArray(attempts) || !Array.isArray(makes) || attempts.length !== 5 || makes.length !== 5) throw new Error('Five exact model-zone bins required');
  const total = attempts.reduce((a,b) => a+b,0);
  const metricValues = attempts.map((a,i) => metric === 'fg' ? zoneRate(a,makes[i]) : total > 0 ? a/total : null);
  const labels = [[250,425],[250,280],[120,333],[17,403],[250,105]];
  return `<figure class="court-figure"><svg viewBox="0 0 500 525" role="img" aria-label="${esc(label)}; schematic pooled zones"><title>${esc(label)}</title>${[4,2,3,1,0].map(i => `<g class="court-zone${highlight === i ? ' selected' : ''}" data-zone="${i}" aria-label="${esc(ZONES[i])}: ${attempts[i]} attempts, ${makes[i]} makes" style="--zone-opacity:${metricValues[i] == null ? .04 : .12 + .8*metricValues[i]}"><title>${esc(ZONES[i])}: ${makes[i]}/${attempts[i]} · ${metricValues[i] == null ? 'undefined' : pct(metricValues[i],1)}</title>${PATHS[i]}</g>`).join('')}<g class="court-lines"><path d="M4 24H496V492H4Z M170 440V250H330V440 M30 492V350 A237.5 237.5 0 0 1 470 350V492 M220 451H280"/><circle cx="250" cy="440" r="7.5"/></g>${labels.map(([x,y],i) => `<text x="${x}" y="${y}" class="court-value${i===3?' corner':''}">${metricValues[i] == null?'—':pct(metricValues[i],0)}</text>`).join('')}</svg><figcaption>${esc(label)} · ${metric === 'fg' ? 'make percentage' : 'share of attempts'}. ${total ? f1(total)+' attempts' : 'No attempts'}. Left/right are pooled; shapes are schematic.</figcaption></figure>`;
}
export function zoneTable(values, {projected = false} = {}) {
  const total=values.attempts.reduce((a,b)=>a+b,0);
  return `<div class="scroll"><table><thead><tr><th class="name">Zone</th><th>FGM</th><th>FGA</th><th>FG%</th><th>Attempt share</th></tr></thead><tbody>${ZONES.map((name,i)=>`<tr data-zone-row="${i}"><td class="name"><button class="ghost" data-zone-button="${i}" style="min-height:44px">${esc(name)}</button></td><td>${projected?f1(values.makes[i]):values.makes[i]}</td><td>${projected?f1(values.attempts[i]):values.attempts[i]}</td><td>${zoneRate(values.attempts[i],values.makes[i]) == null ? '—' : pct(zoneRate(values.attempts[i],values.makes[i]),1)}</td><td>${total>0?pct(values.attempts[i]/total,1):'—'}</td></tr>`).join('')}</tbody></table></div>`;
}
export function wireCourt(root) {
  root.querySelectorAll('[data-zone-button]').forEach(region => {
    const select = () => {
      root.querySelectorAll('[data-zone-row]').forEach(row => row.classList.toggle('court-row-selected', row.dataset.zoneRow === region.dataset.zoneButton));
      root.querySelectorAll('[data-zone]').forEach(el => el.classList.toggle('selected', el.dataset.zone === region.dataset.zoneButton));
    };
    region.onclick=select;region.onkeydown=e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();select();}};
  });
}

export function observedMap(observed,subject,scope='offense') {
  const selected=observed.subjects?.[subject],indices=selected?.[scope]||[];
  const shots=indices.map(i=>observed.shots[i]),known=shots.filter(p=>Number.isFinite(p.x)&&Number.isFinite(p.y));
  const full=known.some(p=>p.y>41.75),height=full?940:470,basket=full?887.5:417.5;
  const counts=observed.cells.map(()=>({a:0,m:0,known:0}));
  for(const p of shots){counts[p.cell].a++;if(p.made!=null){counts[p.cell].known++;counts[p.cell].m+=Number(p.made);}}
  const knownOutcomes=shots.filter(p=>p.made!=null),made=knownOutcomes.reduce((sum,p)=>sum+Number(p.made),0);
  const outline=cy=>`<path d="M170 ${cy+52.5}V${cy-137.5}H330V${cy+52.5} M30 ${cy+52.5}V${cy-89.5}A237.5 237.5 0 0 1 470 ${cy-89.5}V${cy+52.5} M220 ${cy+12.5}H280"/><circle cx="250" cy="${cy}" r="7.5"/>`;
  const figure=`<figure class="court-figure"><svg viewBox="0 0 500 ${height}" role="img" aria-label="Recorded ESPN shot coordinates; ${shots.length} attempts, ${known.length} plottable"><g class="court-lines"><rect x="1" y="1" width="498" height="${height-2}"/>${outline(basket)}${full?'<line x1="0" x2="500" y1="470" y2="470"/>':''}</g>${known.map(p=>`<circle cx="${p.x*10}" cy="${basket-p.y*10}" r="4.5" fill="${p.made?'var(--accent)':'none'}" stroke="${p.made?'var(--accent)':'var(--dim)'}" stroke-width="1.8" ${p.made==null?'stroke-dasharray="2 2"':''} opacity=".7"><title>${esc(p.date)} · ${p.made==null?'unknown outcome':p.made?'made':'missed'} ${p.value}PT · ${esc(observed.cells[p.cell].basic)} / ${esc(observed.cells[p.cell].area)}; source (${p.x}, ${p.y})ft</title></circle>`).join('')}</svg><figcaption>● made · ○ missed · dashed unknown result · ${known.length} / ${shots.length} coordinates plotted. ${shots.length-known.length} missing/invalid coordinates remain in counts. Positions are source-rounded, without jitter.</figcaption></figure>`;
  const table=`<div><h3>${scope==='defense'?'Opponent shots in recorded on-court exposure':'Recorded shots taken'}</h3><p><b>${made}/${knownOutcomes.length}</b> with known result · ${knownOutcomes.length?pct(made/knownOutcomes.length,1):'—'}<br>${shots.length} attempts · ${shots.length-knownOutcomes.length} unknown outcomes</p>${scope==='defense'?`<p class="note">${selected?.unassigned_defense_attempts??'Unknown'} opponent attempts in this team window lack a legal recorded five; they cannot be assigned to a player's exposure.</p>`:''}<p class="note">${esc(observed.definition)} ${selected?.window?.games??0} team games${selected?.window?.through?' through '+esc(selected.window.through):''}.</p><details><summary>Derived regions · counts and support</summary><div class="scroll"><table><thead><tr><th class="name">Basic region</th><th>Area</th><th>Range</th><th>Known makes</th><th>Attempts</th><th>FG% known</th></tr></thead><tbody>${observed.cells.map((cell,i)=>`<tr><td class="name">${esc(cell.basic)}</td><td>${esc(cell.area)}</td><td>${esc(cell.range)}</td><td>${counts[i].m}</td><td>${counts[i].a}</td><td>${counts[i].known?pct(counts[i].m/counts[i].known,1):'—'}</td></tr>`).join('')}</tbody></table></div></details><p class="note">${esc(observed.limits)}</p></div>`;
  return `<div class="replay-grid">${figure}${table}</div>`;
}
