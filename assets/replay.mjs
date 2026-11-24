// Stored original-chunk segments, with no simulation or interpolation in the browser.
import {api, esc, team, f1} from './ui.mjs';
import {courtMap, wireCourt} from './court.mjs';

export const BOX = ['pts', 'reb', 'ast', 'stl', 'blk', 'tov', 'fgm', 'fga', 'fg3m', 'fg3a', 'ftm', 'fta', 'pf'];
const elapsed = (period, clock) => period <= 4 ? (period - 1) * 720 + 720 - clock : 2880 + (period - 5) * 300 + 300 - clock;
const clock = value => Number.isFinite(value) && value >= 0 ? `${Math.floor(value / 60)}:${String(Math.floor(value % 60)).padStart(2, '0')}` : '—';
export function compatibleExample(example, choices = {}) {
  return Object.entries(choices).every(([id, value]) => value == null || example.choices?.[id] === value);
}
export function replayState(example, count, players) {
  if (!Number.isInteger(count) || count < 0 || count > example.events.length) throw new Error('Invalid replay position');
  const lines = Object.fromEntries(players.map(p => [p.id, {min: 0, ...Object.fromEntries(BOX.map(k => [k, 0]))}]));
  const zones = {attempts: [0,0,0,0,0], makes: [0,0,0,0,0]};
  for (const event of example.events.slice(0, count)) {
    for (const [id, stat, amount] of event.credits || []) {
      if (!lines[id] || !Number.isFinite(amount) || amount < 0) throw new Error('Unknown replay credit');
      lines[id][stat] = (lines[id][stat] || 0) + amount;
    }
    for (const [id, seconds] of event.seconds || []) {
      if (!lines[id] || !Number.isFinite(seconds) || seconds < 0) throw new Error('Invalid replay seconds');
      lines[id].min += seconds / 60;
    }
    if (event.shot) { zones.attempts[event.shot.zone]++; zones.makes[event.shot.zone] += Number(event.shot.made); }
  }
  for (const row of Object.values(lines)) row.reb = (row.oreb || 0) + (row.dreb || 0);
  const event = count ? example.events[count - 1] : null;
  return {lines, zones, event, score: event?.score_after || [0, 0], period: event?.period || 1,
    clock: event?.after_clock ?? 720, lineups: event?.lineups_after || example.events[0]?.lineups};
}
function timeline(example, players, end, names) {
  const intervals = Object.fromEntries(players.map(p => [p.id, []]));
  for (const e of example.events) {
    const start = elapsed(e.period, e.before_clock), action = elapsed(e.period, e.action_clock), stop = elapsed(e.period, e.after_clock);
    for (const [lineups, a, b] of [[e.lineups, start, action], [e.lineups_after, action, stop]]) {
      if (b > a) for (const id of lineups.flat()) intervals[id]?.push([a, b]);
    }
  }
  const ticks=[0,720,1440,2160,2880];for(let second=3180;second<=end;second+=300)ticks.push(second);
  const axis=`<div class="replay-rotation-row"><span>Elapsed minutes</span><div class="replay-rotation-axis">${ticks.map((second,i)=>`<span style="left:${100*second/end}%;transform:translateX(${i===0?'0':second===end?'-100%':'-50%'})">${second/60}</span>`).join('')}</div></div>`;
  return axis+[0,1].map(side=>`<h4 class="replay-rotation-team">${esc(names[side])}</h4>`+players.filter(p=>p.side===side).map(p => `<div class="replay-rotation-row"><span title="${esc(p.name)}">${esc(p.name)}</span><div class="replay-rotation-track" aria-label="${esc(p.name)} on-court stints">${ticks.slice(1,-1).map(second=>`<em class="replay-period-boundary" style="left:${100*second/end}%"></em>`).join('')}${intervals[p.id].map(([a,b]) => `<i class="side-${p.side}" style="left:${100*a/end}%;width:${100*(b-a)/end}%" title="${f1(a/60)}–${f1(b/60)} elapsed minutes"></i>`).join('')}<b data-replay-cursor></b></div></div>`).join('')).join('');
}
function eventLabel(e, players) {
  if (!e) return 'Opening lineups';
  if (e.description) return e.description;
  const name = id => players.find(p => p.id === id)?.name || id;
  if (e.shot) return `${name(e.shot.player)} · ${e.shot.made ? 'made' : 'missed'} ${e.shot.value}-point attempt`;
  const credits = (e.credits || []).filter(([,stat]) => ['tov','pf','fta'].includes(stat));
  return credits.length ? credits.map(([id,stat,n]) => `${name(id)} · ${n} ${stat.toUpperCase()}`).join(' · ') : 'Game segment';
}
export async function replayView(root, data, current) {
  root.classList.add('replay-view');
  const descriptor = data.replay;
  if (!descriptor || !data.worlds) {
    root.innerHTML = '<section class="panel"><h2>Saved examples</h2><p class="note">Full saved-world playback is available in laptop bundles with reconciled examples.</p></section>'; return;
  }
  const payload = await api(descriptor.path || `game/${data.game.id}/replay`);
  if (!current()) return;
  if (payload.schema !== 'visible-worlds-v1' || payload.game_id !== data.game.id || payload.source_id !== descriptor.source_id) throw new Error('Replay source differs from this game');
  const examples = payload.examples.filter(e => compatibleExample(e, data._lineup?.choices));
  if (!examples.length) {
    root.innerHTML = '<section class="panel"><h2>Saved examples</h2><p class="note">The five Expected examples use other lineup cases. Select Expected above to explore them.</p></section>'; return;
  }
  let selected = 0, step = 0, playing = false, speed = 4, timer;
  const players = payload.players;
  root.innerHTML = `<section class="panel"><div class="replay-heading"><div><h2>Inside a saved world</h2><p class="note">${examples.length} compatible examples · ${payload.examples.length} selected outcomes. Each is one real saved simulation, not a forecast average.</p></div><label>Example<select data-replay-example aria-label="Saved example">${examples.map((e,i) => `<option value="${i}">${esc(e.label)}</option>`).join('')}</select></label></div><div class="replay-score" data-replay-score aria-live="polite"></div><div class="replay-controls replay-transport"><button data-replay-back aria-label="Previous segment">‹ Step</button><button data-replay-play>Play</button><button data-replay-next aria-label="Next segment">Step ›</button><label>Speed<select data-replay-speed><option value="1">1 segment/s</option><option value="4" selected>4 segments/s</option><option value="12">12 segments/s</option></select></label><label>Period<select data-replay-quarter></select></label></div><label class="replay-seek">Game progress<input data-replay-seek type="range" min="0" value="0" step="1" aria-label="Seek saved game"></label><div class="replay-grid"><div data-replay-court></div><div><h3>Recorded segment</h3><p data-replay-event></p><div data-replay-five></div><p class="note">Shot marks identify the model’s pooled zone. Player locations, passes and trajectories are not recorded. Free throws and other credits within a segment share its recorded action interval.</p></div></div><details><summary>Source world and selection</summary><p data-replay-source class="note"></p></details></section><section class="panel"><h3>Box at this point</h3><div class="scroll" data-replay-box></div></section><details class="panel"><summary>Recorded event log</summary><p class="note">Original source order; each row is one generated segment and its recorded credits.</p><div class="scroll" data-replay-log></div></details><details class="panel"><summary>Rotation timeline · every on-court stint</summary><p class="note">Elapsed minutes; bars follow the exact before-action and after-foul lineups. The cursor follows the selected segment.</p><div data-replay-timeline></div></details>`;
  const get = key => root.querySelector(`[data-replay-${key}]`);
  const stop = () => { playing = false; clearTimeout(timer); get('play').textContent = 'Play'; };
  function paint() {
    if (!current()) { stop(); return; }
    const e = examples[selected], s = replayState(e, step, players);
    const end = elapsed(e.events.at(-1).period, e.events.at(-1).after_clock);
    get('seek').value = step;
    get('score').innerHTML = `<strong>${esc(team(data.game.away.id).abbr)} ${s.score[1]} <span>–</span> ${s.score[0]} ${esc(team(data.game.home.id).abbr)}</strong><span>${s.period <= 4 ? 'Q' + s.period : 'OT' + (s.period - 4)} · ${clock(s.clock)}</span>`;
    get('event').textContent = `${step}/${e.events.length} · ${eventLabel(s.event, players)}`;
    get('court').innerHTML = courtMap(s.zones, {highlight: s.event?.shot?.zone, label: 'Attempts in this saved world so far'});
    wireCourt(get('court'));
    get('five').innerHTML = [1,0].map(side => `<h4>${esc(team(data.game[side ? 'away':'home'].id).abbr)} on court</h4><p>${s.lineups?.[side]?.map(id => esc(players.find(p => p.id === id)?.name || id)).join(' · ') || '—'}</p>`).join('');
    get('box').innerHTML = `<table><thead><tr><th class="name">Player</th><th>MIN</th>${BOX.map(k => `<th>${k.toUpperCase()}</th>`).join('')}</tr></thead><tbody>${[1,0].map(side => `<tr class="group"><th class="name" colspan="${BOX.length+2}">${esc(team(data.game[side?'away':'home'].id).name)}</th></tr>${players.filter(p => p.side === side).map(p => { const b=s.lines[p.id];return `<tr><td class="name">${esc(p.name)}${s.lineups?.[side]?.includes(p.id)?' ●':''}</td><td>${clock(b.min*60)}</td>${BOX.map(k => `<td>${b[k] ?? '—'}</td>`).join('')}</tr>`;}).join('')}`).join('')}</tbody></table>`;
    root.querySelectorAll('[data-replay-cursor]').forEach(el => el.style.left = `${100*elapsed(s.period,s.clock)/end}%`);
    get('back').disabled = step === 0; get('next').disabled = step === e.events.length;
    get('quarter').value = s.period;
    if (step === e.events.length) stop();
  }
  function choose() {
    stop();step=0;
    const e=examples[selected];get('seek').max=e.events.length;
    const periods=[...new Set(e.events.map(x => x.period))];
    get('quarter').innerHTML=periods.map(p => `<option value="${p}">${p<=4?'Q'+p:'OT'+(p-4)}</option>`).join('');
    get('source').textContent=`${payload.model} · ${payload.runtime} · branch ${e.branch_id} · world ${e.world_index} · canonical chunk ${e.chunk_start}–${e.chunk_stop}. ${e.selection_definition || ''} Source ${payload.source_id}. ${payload.spatial_precision || ''}`;
    get('timeline').innerHTML=timeline(e,players,elapsed(e.events.at(-1).period,e.events.at(-1).after_clock),[team(data.game.home.id).name,team(data.game.away.id).name]);
    get('log').innerHTML=`<table data-no-sort><thead><tr><th>Period</th><th>Clock interval</th><th>Away–home</th><th class="name">Recorded segment</th></tr></thead><tbody>${e.events.map((event,i)=>`<tr><td>${event.period<=4?'Q'+event.period:'OT'+(event.period-4)}</td><td><button class="ghost" style="min-height:44px" data-replay-jump="${i+1}">${clock(event.before_clock)} → ${clock(event.after_clock)}</button></td><td>${event.score_after[1]}–${event.score_after[0]}</td><td class="name">${esc(eventLabel(event,players))}</td></tr>`).join('')}</tbody></table>`;
    root.querySelectorAll('[data-replay-jump]').forEach(button=>button.onclick=()=>{stop();step=Number(button.dataset.replayJump);paint();});paint();
  }
  function tick() { if (!playing || !current()) return stop();step=Math.min(step+1,examples[selected].events.length);paint();if(playing)timer=setTimeout(tick,1000/speed); }
  get('example').onchange=e=>{selected=Number(e.target.value);choose();};
  get('back').onclick=()=>{stop();step--;paint();};get('next').onclick=()=>{stop();step++;paint();};
  get('seek').oninput=e=>{stop();step=Number(e.target.value);paint();};
  get('speed').onchange=e=>{speed=Number(e.target.value);};
  get('quarter').onchange=e=>{stop();step=examples[selected].events.findIndex(x=>x.period===Number(e.target.value))+1;paint();};
  get('play').onclick=()=>{if(playing)return stop();if(step===examples[selected].events.length)step=0;playing=true;get('play').textContent='Pause';tick();};
  choose();
}
