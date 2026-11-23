// Scenarios, conditional and joint outcomes (owner, 20 Nov: "player A given player B", outcomes given minutes, matchup
// deltas). Everything is read from the game's stored simulated worlds (outcomes.mjs) — the app slices, never simulates.
import {esc, f1, heat, pct, signed, team} from './ui.mjs';
import * as O from './outcomes.mjs';

const memory = new Map();  // game id → conditions (also kept in the route)
const BOX = [['min', 'MIN'], ['pts', 'PTS'], ['reb', 'REB'], ['ast', 'AST'], ['fg3m', '3PM'], ['stl', 'STL'], ['blk', 'BLK'], ['tov', 'TOV'], ['fgpct', 'FG%']];
const calculations = Wd => Wd.weights ? O.branchCalculations(Wd) : O;
const worldData = data => data._branchWorldData || O.load(data.game.id);
const memoryKey = data => (data._branchWorldData ? 'research|' : '') + data.game.id;

const names = data => new Map(['home', 'away'].flatMap(s => data.projection.sim[s].players.map(p => [p.id, p.name])));
const abbrs = data => ({home: team(data.game.home.id).abbr, away: team(data.game.away.id).abbr});
const played = data => ['away', 'home'].flatMap(s => data.projection.sim[s].players.filter(p => p.periods).map(p => ({...p, side: s})));
const delta = (v, d = 1, good = null) => {
  if (v == null || !Number.isFinite(v) || Math.abs(v) < 0.05) return '<span class="sub">±0</span>';
  const cls = good == null ? '' : (v > 0) === good ? ' up' : ' down';
  return `<span class="sub${cls}">${signed(v, d)}</span>`;
};

export function encode(conds) { return conds.length ? encodeURIComponent(JSON.stringify(conds)) : ''; }
export function decode(text) {
  try { const c = JSON.parse(decodeURIComponent(text || '')); return Array.isArray(c) ? c.filter(x => x && x.subj && x.v) : []; } catch { return []; }
}

/** Condition builder: subject → variable → (≥ / ≤ value). `prefix` keeps several builders on one page apart. */
function builder(data, Wd, prefix, {subj = 't:home', v = 'win', op = 'ge', x = null, button = 'Add', variableOnly = false} = {}) {
  const vals = O.isFlag(v) ? null : Wd.values(subj, v);
  const exactMinute = v === 'min' && (Wd.weights || Wd.preciseMinutes);
  const d = vals ? (Wd.preciseMinutes && exactMinute ? O.preciseCalculations(Wd) : calculations(Wd)).dist(vals) : null;
  const value = x ?? (d ? exactMinute ? Number(d.q[3].toFixed(4)) : d.q[3] : 0);
  return `<div class="builder" data-builder="${prefix}"${variableOnly ? ' data-only="1"' : ''}>
    <select data-b="subj" aria-label="Who">${O.subjectOptions(data, subj)}</select>
    <select data-b="v" aria-label="What">${O.varOptions(subj, v, Wd)}</select>
    <select data-b="op" aria-label="Comparison"${O.isFlag(v) || variableOnly ? ' hidden' : ''}><option value="ge"${op === 'ge' ? ' selected' : ''}>at least</option><option value="le"${op === 'le' ? ' selected' : ''}>at most</option></select>
    <input data-b="x" type="number" step="${exactMinute ? 'any' : '1'}" value="${value}" aria-label="Value"${O.isFlag(v) || variableOnly ? ' hidden' : ''}>
    ${button ? `<button type="button" data-b="add">${esc(button)}</button>` : ''}</div>`;
}
function readBuilder(root) {
  const g = k => root.querySelector(`[data-b="${k}"]`);
  const c = {subj: g('subj').value, v: g('v').value};
  if (!O.isFlag(c.v)) { c.op = g('op').value; c.x = Number(g('x').value); }
  return c;
}
function wireBuilder(root, data, Wd, onChange, onAdd) {
  const subj = root.querySelector('[data-b="subj"]'), v = root.querySelector('[data-b="v"]');
  const variableOnly = root.dataset.only === '1';
  const refreshValue = () => {
    const flag = O.isFlag(v.value) || variableOnly;
    root.querySelector('[data-b="op"]').hidden = flag;
    const input = root.querySelector('[data-b="x"]');
    input.hidden = flag;
    const exactMinute = v.value === 'min' && (Wd.weights || Wd.preciseMinutes);
    input.step = exactMinute ? 'any' : '1';
    if (!flag) { const values = Wd.values(subj.value, v.value), d = values ? (Wd.preciseMinutes && exactMinute ? O.preciseCalculations(Wd) : calculations(Wd)).dist(values) : null; if (d) input.value = exactMinute ? Number(d.q[3].toFixed(4)) : d.q[3]; }
  };
  subj.onchange = () => { v.innerHTML = O.varOptions(subj.value, subj.value.startsWith('p:') ? 'pts' : subj.value === 'g' ? 'total' : variableOnly ? 'pts' : 'win', Wd); refreshValue(); onChange?.(readBuilder(root)); };
  v.onchange = () => { refreshValue(); onChange?.(readBuilder(root)); };
  root.querySelector('[data-b="op"]').onchange = () => onChange?.(readBuilder(root));
  root.querySelector('[data-b="x"]').onchange = () => onChange?.(readBuilder(root));
  const add = root.querySelector('[data-b="add"]');
  if (add) add.onclick = () => onAdd?.(readBuilder(root));
}

/** Quick scenarios as [label, conditions, group]; shown in labelled rows (owner: grouping). */
function presets(data, Wd) {
  const out = [], A = abbrs(data), C = calculations(Wd);
  for (const p of played(data)) {
    const sits = C.mean(Wd.values('p:' + p.id, 'sits'));
    if (sits != null && sits > 0.01 && sits < 0.99) {
      out.push([`${p.name} sits (${pct(sits, 0)})`, [{subj: 'p:' + p.id, v: 'sits'}], 'Participation']);
      out.push([`${p.name} plays`, [{subj: 'p:' + p.id, v: 'plays'}], 'Participation']);
    }
  }
  const total = C.dist(Wd.values('g', 'total'));
  out.push([`${A.away} wins`, [{subj: 't:away', v: 'win'}], 'Result'], [`${A.home} wins`, [{subj: 't:home', v: 'win'}], 'Result'],
    ['Close game (≤ 5)', [{subj: 'g', v: 'absm', op: 'le', x: 5}], 'Result'], ['Blowout (15+)', [{subj: 'g', v: 'absm', op: 'ge', x: 15}], 'Result'],
    ['Overtime', [{subj: 'g', v: 'ot'}], 'Result'],
    [`Shootout (${total.q[3]}+)`, [{subj: 'g', v: 'total', op: 'ge', x: total.q[3]}], 'Totals'],
    [`Grind (≤ ${total.q[1]})`, [{subj: 'g', v: 'total', op: 'le', x: total.q[1]}], 'Totals'],
    [`${A.away} comes back from behind at half-time`, [{subj: 't:away', v: 'comeback'}], 'Game flow'], [`${A.home} comes back from behind at half-time`, [{subj: 't:home', v: 'comeback'}], 'Game flow'],
    [`${A.away} wire to wire`, [{subj: 't:away', v: 'wire'}], 'Game flow'], [`${A.home} wire to wire`, [{subj: 't:home', v: 'wire'}], 'Game flow'],
    ['Half-time leader loses', [{subj: 'g', v: 'flip'}], 'Game flow'], ['Within 5 after Q3', [{subj: 'g', v: 'close3'}], 'Game flow'],
    ['Lead changes 2+ times at the breaks', [{subj: 'g', v: 'changes', op: 'ge', x: 2}], 'Game flow'],
    [`${A.away} wins Q1`, [{subj: 't:away', v: 'wq1'}], 'Quarters'], [`${A.home} wins Q1`, [{subj: 't:home', v: 'wq1'}], 'Quarters'],
    [`${A.away} wins Q4`, [{subj: 't:away', v: 'wq4'}], 'Quarters'], [`${A.home} wins Q4`, [{subj: 't:home', v: 'wq4'}], 'Quarters']);
  const stars = played(data).sort((a, b) => b.periods.fg.mean.pts - a.periods.fg.mean.pts).slice(0, 2);
  for (const p of stars) {
    const d = C.dist(Wd.values('p:' + p.id, 'pts'));
    out.push([`${p.name} ${d.q[4]}+ pts`, [{subj: 'p:' + p.id, v: 'pts', op: 'ge', x: d.q[4]}], 'Stars'], [`${p.name} ≤ ${d.q[0]} pts`, [{subj: 'p:' + p.id, v: 'pts', op: 'le', x: d.q[0]}], 'Stars']);
  }
  return out;
}
const PRESET_GROUPS = ['Participation', 'Result', 'Totals', 'Game flow', 'Quarters', 'Stars'];
function presetRows(pres) {
  return `<div class="preset-groups">${PRESET_GROUPS.map(g => {
    const items = pres.map((p, i) => [p, i]).filter(([p]) => p[2] === g);
    return items.length ? `<span class="seg-label">${g}</span><div class="chips left">${items.map(([p, i]) => `<button type="button" class="ghost sm" data-pre="${i}">${esc(p[0])}</button>`).join('')}</div>` : '';
  }).join('')}</div>`;
}

// ------------------------------------------------------------------ Scenarios tab
export async function scenarioView(el, data, encoded) {
  const Wd = await worldData(data), C = calculations(Wd);
  let conds = encoded ? decode(encoded) : (memory.get(memoryKey(data)) || []);
  const N = names(data), A = abbrs(data), base = O.mask(Wd, []);
  const setConds = next => {
    conds = next;
    memory.set(memoryKey(data), conds);
    location.replace(`#/game/${data.game.id}/scenario${conds.length ? '/' + encode(conds) : ''}`);
  };
  const paint = () => {
    const m = O.mask(Wd, conds), n = C.count(m), total = C.mass ? C.mass(base) : C.count(base);
    const selected = C.mass ? C.mass(m) : n, chance = selected / total;
    const indep = conds.length > 1 ? conds.reduce((p, c) => p * (C.mass ? C.mass(O.mask(Wd, [c])) : C.count(O.mask(Wd, [c]))) / total, 1) : null;
    const chips = conds.map((c, i) => `<button type="button" class="chip" data-del="${i}" title="Remove">${esc(O.label(c, N, A))} ×</button>`).join('');
    const pre = presetRows(presets(data, Wd));
    let body = '';
    if (!n) body = '<section class="panel"><p class="note">No simulated game matches every condition — remove one.</p></section>';
    else {
      const teamRows = ['away', 'home'].map(side => {
        const pts = Wd.values('t:' + side, 'pts'), win = Wd.values('t:' + side, 'win');
        const s = C.mean(pts, m), b = C.mean(pts, base), ws = C.mean(win, m), wb = C.mean(win, base);
        return `<tr><td class="l">${esc(team(data.game[side].id).name)}</td><td><b>${f1(s)}</b>${delta(s - b)}</td>${heat(ws, {digits: 1})}<td class="dim">${pct(wb, 1)}</td></tr>`;
      }).join('');
      const tot = Wd.values('g', 'total'), mar = Wd.values('t:home', 'margin'), ot = Wd.values('g', 'ot');
      const game = `<tr class="sep"><td class="l">Total</td><td><b>${f1(C.mean(tot, m))}</b>${delta(C.mean(tot, m) - C.mean(tot, base))}</td><td></td><td></td></tr>
        <tr><td class="l">Margin (${esc(A.home)} − ${esc(A.away)})</td><td><b>${signed(C.mean(mar, m))}</b>${delta(C.mean(mar, m) - C.mean(mar, base))}</td><td></td><td></td></tr>
        <tr><td class="l">Overtime</td><td><b>${pct(C.mean(ot, m), 1)}</b><span class="sub">all ${pct(C.mean(ot, base), 1)}</span></td><td></td><td></td></tr>`;
      const boxes = ['away', 'home'].map(side => {
        const ps = data.projection.sim[side].players.filter(p => p.periods).slice().sort((a, b) => b.periods.fg.sec - a.periods.fg.sec);
        const rows = ps.map(p => {
          const subj = 'p:' + p.id, sits = C.mean(Wd.values(subj, 'sits'), m);
          return `<tr><td class="name">${esc(p.name)}${sits > 0.995 ? ' <span class="tag">sits</span>' : sits > 0.005 ? ` <span class="tag">sits ${pct(sits, 0)}</span>` : ''}</td>${BOX.map(([k]) => {
            const vals = Wd.values(subj, k);
            if (!vals) return '<td>—</td>';
            const s = C.mean(vals, m), b = C.mean(vals, base);
            return `<td>${s == null ? '—' : k === 'fgpct' ? f1(s) : f1(s)}${s == null || b == null ? '' : delta(s - b, 1)}</td>`;
          }).join('')}</tr>`;
        }).join('');
        return `<section class="panel"><h3 style="margin-top:0">${esc(team(data.game[side].id).name)} under this scenario</h3><div class="scroll"><table class="box"><thead><tr><th class="name">Player</th>${BOX.map(([, l]) => `<th>${l}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></div></section>`;
      }).join('');
      const flow = flowPanel(data, Wd, m, base, A);
      body = `<section class="panel"><div class="tiles"><div class="tile"><span>Chance of this scenario</span><b>${pct(chance, 1)}</b><small>${n.toLocaleString()} of ${C.count(base).toLocaleString()} saved worlds${Wd.weights ? ' · weighted chance' : ''}</small></div>
          ${indep != null ? `<div class="tile"><span>If the conditions were independent</span><b>${pct(indep, 1)}</b><small>${indep > 0 ? `×${(chance / indep).toFixed(2)} correlation lift` : ''}</small></div>` : ''}</div>
        ${n < 60 ? `<p class="note warn">Only ${n} simulated games match — read the numbers below as rough.</p>` : ''}
        <div class="scroll" style="margin-top:10px"><table><thead><tr><th class="l">Team</th><th>Points (Δ)</th><th>Win given</th><th>Win, all</th></tr></thead><tbody>${teamRows}${game}</tbody></table></div></section>${flow}<div id="duel-slot"></div>${boxes}`;
    }
    el.innerHTML = `<section class="panel"><h2 style="margin-top:0">Scenarios</h2>
        <p class="note" style="margin-top:0">Pick conditions to filter the ${C.count(base).toLocaleString()} saved simulated games to those where every condition happens${Wd.weights ? ', using their branch weights' : ''}. Small grey numbers: change from all selected simulations.</p>
        <div class="chips left">${chips || '<span class="note" style="margin:0">No conditions — all simulations.</span>'}${conds.length ? '<button type="button" class="ghost sm" data-clear>Clear</button>' : ''}</div>
        ${builder(data, Wd, 'scn')}
        <details style="margin-top:8px"><summary class="note" style="cursor:pointer">Quick scenarios</summary>${pre}</details></section>${body}`;
    const pres = presets(data, Wd);
    el.querySelectorAll('[data-del]').forEach(b => b.onclick = () => setConds(conds.filter((_, i) => i !== Number(b.dataset.del))));
    el.querySelector('[data-clear]')?.addEventListener('click', () => setConds([]));
    el.querySelectorAll('[data-pre]').forEach(b => b.onclick = () => setConds([...conds, ...pres[Number(b.dataset.pre)][1]]));
    wireBuilder(el.querySelector('[data-builder="scn"]'), data, Wd, null, c => setConds([...conds, c]));
    const slot = el.querySelector('#duel-slot');
    if (slot) duelPanel(slot, data, Wd, m, base, conds.length > 0);
  };
  paint();
}

// ------------------------------------------------------------------ duels: any two outcomes head to head
const duels = new Map();  // game id → {a, b}
function duelPresets(data) {
  const lead = (side, k) => data.projection.sim[side].players.filter(p => p.periods).slice().sort((a, b) => (b.periods.fg.mean[k] ?? 0) - (a.periods.fg.mean[k] ?? 0))[0];
  const reb = p => (p.periods.fg.mean.oreb ?? 0) + (p.periods.fg.mean.dreb ?? 0);
  const topReb = side => data.projection.sim[side].players.filter(p => p.periods).slice().sort((a, b) => reb(b) - reb(a))[0];
  const out = [];
  for (const [label, k, pick] of [['Top scorers', 'pts', s => lead(s, 'pts')], ['Top rebounders', 'reb', topReb], ['Top passers', 'ast', s => lead(s, 'ast')], ['Top shooters (threes)', 'fg3m', s => lead(s, 'fg3m')]]) {
    const a = pick('away'), b = pick('home');
    if (a && b) out.push([`${label}: ${a.name} v ${b.name}`, {a: {subj: 'p:' + a.id, v: k}, b: {subj: 'p:' + b.id, v: k}}]);
  }
  const A = abbrs(data);
  out.push([`Q1 points: ${A.away} v ${A.home}`, {a: {subj: 't:away', v: 'q1'}, b: {subj: 't:home', v: 'q1'}}],
           [`2nd half: ${A.away} v ${A.home}`, {a: {subj: 't:away', v: 'h2'}, b: {subj: 't:home', v: 'h2'}}]);
  return out;
}
function duelPanel(el, data, Wd, m, base, scenario) {
  const pres = duelPresets(data);
  const st = duels.get(data.game.id) || pres[0][1];
  const N = names(data), A = abbrs(data), C = calculations(Wd);
  const name = c => O.label({...c, op: 'ge', x: ''}, N, A).replace(/ ≥ $/, '');
  const paint = () => {
    const a = Wd.values(st.a.subj, st.a.v), b = Wd.values(st.b.subj, st.b.v);
    const diff = a && b ? a.map((x, w) => x - b[w]) : null;
    const res = mk => diff ? {gt: C.share(diff, mk, d => d > 0), eq: C.share(diff, mk, d => d === 0), lt: C.share(diff, mk, d => d < 0), ma: C.mean(a, mk), mb: C.mean(b, mk)} : null;
    const r = res(m), r0 = res(base);
    const sideOf = c => (c.subj.startsWith('t:') ? c.subj.slice(2) : played(data).find(p => 'p:' + p.id === c.subj)?.side);
    const sa = sideOf(st.a), sb = sideOf(st.b);
    const winA = diff ? O.mask(Wd, []).map((x, w) => (m[w] && diff[w] > 0 ? 1 : 0)) : null;
    const tw = (side, mk) => (side && C.count(mk) ? C.mean(Wd.values('t:' + side, 'win'), mk) : null);
    const minute = (Wd.weights || Wd.preciseMinutes) && (st.a.v === 'min' || st.b.v === 'min');
    const D = Wd.preciseMinutes && minute ? O.preciseCalculations(Wd) : C;
    const dAll = diff ? D.dist(diff, null, {minute}) : null, dCond = diff && scenario ? D.dist(diff, m, {minute}) : null;
    const btn = ([l], i) => `<button type="button" class="ghost sm" data-duel="${i}">${esc(l)}</button>`;
    const pre = `<div class="preset-groups"><span class="seg-label">Players</span><div class="chips left">${pres.map(btn).filter((_, i) => pres[i][1].a.subj.startsWith('p:')).join('')}</div>
      <span class="seg-label">Teams</span><div class="chips left">${pres.map(btn).filter((_, i) => pres[i][1].a.subj.startsWith('t:')).join('')}</div></div>`;
    el.innerHTML = `<section class="panel"><h3 style="margin-top:0">Duel${scenario ? ' · under this scenario' : ''}</h3>
      <div class="duel-pick"><span class="note" style="margin:0">A</span>${builder(data, Wd, 'duel-a', {subj: st.a.subj, v: st.a.v, button: '', variableOnly: true})}
        <span class="note" style="margin:0">B</span>${builder(data, Wd, 'duel-b', {subj: st.b.subj, v: st.b.v, button: '', variableOnly: true})}</div>
      ${pre}
      ${r ? `<div class="tiles" style="margin-top:8px">
          <div class="tile"><span>${esc(name(st.a))} more</span><b>${pct(r.gt, 1)}</b><small>${scenario ? `all ${pct(r0.gt, 1)}` : `mean ${f1(r.ma)}`}</small></div>
          <div class="tile"><span>Level</span><b>${pct(r.eq, 1)}</b><small>${scenario ? `all ${pct(r0.eq, 1)}` : ''}</small></div>
          <div class="tile"><span>${esc(name(st.b))} more</span><b>${pct(r.lt, 1)}</b><small>${scenario ? `all ${pct(r0.lt, 1)}` : `mean ${f1(r.mb)}`}</small></div></div>
        <div class="dist" style="margin-top:8px"><div>${O.overlay(dAll, dCond, {line: 0, minute})}
          <p class="note">A − B in every simulation${scenario ? ': <span class="legend-bar"></span> under the scenario · <span class="legend-line"></span> all simulations' : ''} · right of the line: A more.</p></div>
          <div class="scroll"><table><thead><tr><th class="l"></th><th>${scenario ? 'Given' : 'Mean'}</th>${scenario ? '<th>All</th>' : ''}</tr></thead><tbody>
            <tr><td class="l">${esc(name(st.a))}</td><td><b>${f1(r.ma)}</b></td>${scenario ? `<td>${f1(r0.ma)}</td>` : ''}</tr>
            <tr><td class="l">${esc(name(st.b))}</td><td><b>${f1(r.mb)}</b></td>${scenario ? `<td>${f1(r0.mb)}</td>` : ''}</tr>
            ${sa && C.count(winA) ? `<tr class="sep"><td class="l">${esc(A[sa])} win when A wins the duel</td>${heat(tw(sa, winA), {digits: 0})}${scenario ? '<td></td>' : ''}</tr>` : ''}
            ${sb && sb !== sa && C.count(winA) ? `<tr><td class="l">${esc(A[sb])} win when A wins the duel</td>${heat(tw(sb, winA), {digits: 0})}${scenario ? '<td></td>' : ''}</tr>` : ''}
          </tbody></table></div></div>` : '<p class="note">Pick two numeric outcomes.</p>'}</section>`;
    const set = (k, c) => { if (!O.isFlag(c.v)) { st[k] = {subj: c.subj, v: c.v}; duels.set(data.game.id, st); paint(); } };
    wireBuilder(el.querySelector('[data-builder="duel-a"]'), data, Wd, c => set('a', c));
    wireBuilder(el.querySelector('[data-builder="duel-b"]'), data, Wd, c => set('b', c));
    el.querySelectorAll('[data-duel]').forEach(btn => btn.onclick = () => { const p_ = pres[Number(btn.dataset.duel)][1]; st.a = {...p_.a}; st.b = {...p_.b}; duels.set(data.game.id, st); paint(); });
  };
  paint();
}

/** Quarter by quarter and the game's flow under the scenario: each side's points and period wins, the lead at every
 * break, comebacks and lead changes — all as chances over the matching worlds, with the change from all worlds. */
function flowPanel(data, Wd, m, base, A) {
  const C = calculations(Wd);
  const g = (subj, v, mk) => C.mean(Wd.values(subj, v), mk);
  const chance = (subj, v) => { const s = g(subj, v, m), b = g(subj, v, base); return `<td><b>${pct(s, 0)}</b>${delta(100 * (s - b), 0)}</td>`; };
  const pts = (side, v) => { const s = g('t:' + side, v, m), b = g('t:' + side, v, base); return `<td><b>${f1(s)}</b>${delta(s - b)}</td>`; };
  const lead = k => { const s = C.mean(Wd.lead('home', k), m), b = C.mean(Wd.lead('home', k), base); return `<td><b>${signed(s)}</b>${delta(s - b)}</td>`; };
  const rows = [['Q1', 'q1', 'wq1', 1, 'lead1'], ['Q2', 'q2', 'wq2', 2, 'leadh'], ['Q3', 'q3', 'wq3', 3, 'lead3'], ['Q4', 'q4', 'wq4', 4, null]].map(([lab, q, wq, k, ld]) =>
    `<tr><td class="l">${lab}</td>${pts('away', q)}${pts('home', q)}${chance('t:home', wq)}${chance('t:away', wq)}${lead(k)}${ld ? chance('t:home', ld) : chance('t:home', 'win')}</tr>`).join('');
  const halves = [['1st half', 'h1', 'wh1'], ['2nd half', 'h2', 'wh2']].map(([lab, h, wh]) =>
    `<tr><td class="l">${lab}</td>${pts('away', h)}${pts('home', h)}${chance('t:home', wh)}${chance('t:away', wh)}<td></td><td></td></tr>`).join('');
  const tile = (label, subj, v, fmt = x => pct(x, 1)) => { const s = g(subj, v, m), b = g(subj, v, base); return `<div class="tile"><span>${esc(label)}</span><b>${fmt(s)}</b><small>all ${fmt(b)}</small></div>`; };
  return `<section class="panel"><h3 style="margin-top:0">Quarter by quarter · game flow</h3>
    <div class="scroll"><table><thead><tr><th class="l">Period</th><th>${esc(A.away)} pts</th><th>${esc(A.home)} pts</th><th>${esc(A.home)} wins it</th><th>${esc(A.away)} wins it</th><th>${esc(A.home)} lead at the end</th><th>${esc(A.home)} ahead</th></tr></thead>
    <tbody>${rows}${halves}</tbody></table></div>
    <p class="note">Leads are ${esc(A.home)} − ${esc(A.away)} after each quarter (Q4 row: final, regulation); "ahead" is the chance ${esc(A.home)} leads at that break (Q4 row: wins). Small numbers: change from all simulations (points; percentage points).</p>
    <div class="tiles" style="margin-top:8px">${tile(`${A.away} wins from behind at half-time`, 't:away', 'comeback')}${tile(`${A.home} wins from behind at half-time`, 't:home', 'comeback')}
      ${tile('Half-time leader loses', 'g', 'flip')}${tile('Leader changes at the breaks', 'g', 'changes', x => f1(x))}${tile(`${A.home} wins every quarter`, 't:home', 'sweep')}${tile(`${A.away} wins every quarter`, 't:away', 'sweep')}</div></section>`;
}

// ------------------------------------------------------------------ player sheet panels
export function averagesPanel(data, pid, proj) {
  const a = data.averages?.[pid];
  if (!a || !proj) return '';
  const rows = [['min', 'Minutes'], ['pts', 'Points'], ['reb', 'Rebounds'], ['ast', 'Assists'], ['fg3m', 'Threes'], ['stl', 'Steals'], ['blk', 'Blocks'], ['tov', 'Turnovers']].map(([k, l]) => {
    const p = k === 'min' ? proj.sec / 60 : proj.mean[k] ?? (k === 'reb' ? proj.mean.oreb + proj.mean.dreb : null);
    const s = a.season[k], t = a.last10?.[k];
    const d = (x, y) => (x == null || y == null ? '<td class="dim">—</td>' : `<td class="${x - y > 0.05 ? 'up' : x - y < -0.05 ? 'down' : 'dim'}">${signed(x - y)}</td>`);
    return `<tr><td class="l">${l}</td><td><b>${f1(p)}</b></td><td>${f1(s)}</td>${d(p, s)}<td>${f1(t)}</td>${d(p, t)}</tr>`;
  }).join('');
  return `<section class="panel"><h3 style="margin-top:0">Tonight v his averages</h3><div class="scroll"><table><thead><tr><th class="l">Stat</th><th>Projected</th><th>Season</th><th>Δ</th><th>Last ${a.last10_n}</th><th>Δ</th></tr></thead><tbody>${rows}</tbody></table></div>
    <p class="note">Season and last-10 averages over games played, as of the projection's cutoff (${a.gp} games). The projection is the mean over all simulations — tonight's opponent, minutes, teammates on the floor and the chance he sits are all in it.</p></section>`;
}

/** "Given…" and joint panels for one player's stat (full game). */
export async function sheetPanels(el, data, pid, stat, line) {
  let Wd;
  try { Wd = await worldData(data); } catch (error) { if (data._branchWorldData) throw error; return; }
  const C = Wd.preciseMinutes && stat === 'min' ? O.preciseCalculations(Wd) : calculations(Wd);
  const subj = 'p:' + pid, xVals = Wd.values(subj, stat);
  if (!xVals) { el.innerHTML = ''; return; }
  const N = names(data), A = abbrs(data), side = played(data).find(p => p.id === pid)?.side || 'home';
  let given = {subj: 't:' + side, v: 'win'};
  let other = {subj, v: stat === 'min' ? 'pts' : 'min'};
  const paint = () => {
    const m = O.mask(Wd, [given]), n = C.count(m), total = C.mass ? C.mass(null) : Wd.W;
    const mass = C.mass ? C.mass(m) : n;
    const minute = Boolean((Wd.weights || Wd.preciseMinutes) && stat === 'min');
    const all = minute ? C.dist(xVals, null, {minute: true}) : C.dist(xVals);
    const cond = n ? (minute ? C.dist(xVals, m, {minute: true}) : C.dist(xVals, m)) : null;
    const pAll = C.share(xVals, null, v => v > line), pCond = n ? C.share(xVals, m, v => v > line) : null;
    const yVals = Wd.values(other.subj, other.v);
    const r = yVals ? C.corr(xVals, yVals) : null;
    const yName = O.label({...other, op: 'ge', x: ''}, N, A).replace(/ ≥ $/, '');
    const xName = (O.PLAYER_VARS.find(([k]) => k === stat) || [stat, stat.toUpperCase()])[1];
    const quantile = value => {
      if (!minute) return value;
      const seconds = Math.round(value * 60);
      return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
    };
    el.innerHTML = `<section class="panel"><h3 style="margin-top:0">Given…</h3>
        ${builder(data, Wd, 'given', {...given, button: ''})}
        <p class="note">${n ? `${esc(O.label(given, N, A))}: ${pct(mass / total, 1)}${Wd.weights ? ' weighted chance' : ' of simulations'} (${n.toLocaleString()} saved worlds).` : 'No simulation matches.'}</p>
        ${cond ? `<div class="dist" style="margin-top:6px"><div>${O.overlay(all, cond, {line, minute})}
          <p class="note"><span class="legend-bar"></span> given the condition · <span class="legend-line"></span> all simulations</p></div>
          <div class="scroll"><table><thead><tr><th class="l"></th><th>Given</th><th>All</th></tr></thead><tbody>
            <tr><td class="l">Mean</td><td><b>${f1(cond.mean)}</b></td><td>${f1(all.mean)}</td></tr>
            <tr><td class="l">Median</td><td>${quantile(cond.q[2])}</td><td>${quantile(all.q[2])}</td></tr>
            <tr><td class="l">10–90%</td><td>${quantile(cond.q[0])}–${quantile(cond.q[4])}</td><td>${quantile(all.q[0])}–${quantile(all.q[4])}</td></tr>
            <tr><td class="l">Over ${line}</td>${heat(pCond, {digits: 1})}${heat(pAll, {digits: 1})}</tr></tbody></table></div></div>
          ${minute ? '<p class="note">Minute quantiles are shown as MM:SS; conditions use full stored precision. Each chart bar spans one minute, inclusive of its lower bound and exclusive of its upper bound.</p>' : ''}` : ''}</section>
      <section class="panel"><h3 style="margin-top:0">Joint outcomes</h3>
        <p class="note" style="margin-top:0">${esc(xName)} (across) against:</p>
        ${builder(data, Wd, 'joint', {subj: other.subj, v: other.v, button: '', variableOnly: true})}
        ${yVals ? `${(Wd.preciseMinutes && (stat === 'min' || other.v === 'min') ? O.preciseCalculations(Wd) : C).grid(xVals, yVals, null, {xName, yName})}<p class="note">Each cell: share of all selected simulations with both${Wd.weights ? ', weighted by branch' : ''}. Correlation ${r == null ? '—' : r.toFixed(2)}${r != null ? (Math.abs(r) < 0.1 ? ' (little link)' : r > 0 ? ' (they rise together)' : ' (one rises as the other falls)') : ''}.</p>` : '<p class="note">Choose a numeric outcome (not a yes/no) to see the grid.</p>'}</section>`;
    wireBuilder(el.querySelector('[data-builder="given"]'), data, Wd, c => { given = c; paint(); });
    wireBuilder(el.querySelector('[data-builder="joint"]'), data, Wd, c => { if (!O.isFlag(c.v)) { other = c; paint(); } });
  };
  paint();
}

// ------------------------------------------------------------------ team view: who drives the result
export async function driversPanel(el, data) {
  let Wd;
  try { Wd = await worldData(data); } catch (error) { if (data._branchWorldData) throw error; el.innerHTML = ''; return; }
  const C = calculations(Wd);
  const sections = ['away', 'home'].map(side => {
    const win = Wd.values('t:' + side, 'win'), margin = Wd.values('t:' + side, 'margin'), base = C.mean(win);
    const ps = data.projection.sim[side].players.filter(p => p.periods).slice().sort((a, b) => b.periods.fg.sec - a.periods.fg.sec).slice(0, 8);
    const rows = ps.map(p => {
      const pts = Wd.values('p:' + p.id, 'pts'), sits = Wd.values('p:' + p.id, 'sits'), d = C.dist(pts);
      const qx = Math.max(0, d.q[1] - 1), bx = Math.max(qx + 1, d.q[3] + 1);
      const big = O.mask(Wd, [{subj: 'p:' + p.id, v: 'pts', op: 'ge', x: bx}]), quiet = O.mask(Wd, [{subj: 'p:' + p.id, v: 'pts', op: 'le', x: qx}]);
      const sitShare = C.mean(sits), sitMask = O.mask(Wd, [{subj: 'p:' + p.id, v: 'sits'}]);
      const wb = C.count(big) ? C.mean(win, big) : null, wq = C.count(quiet) ? C.mean(win, quiet) : null;
      const ws = sitShare > 0.01 ? C.mean(win, sitMask) : null;
      return `<tr><td class="name">${esc(p.name)}</td><td class="dim">${bx}+ / ${qx ? '≤' + qx : '0'}</td>${heat(wb, {digits: 0})}${heat(wq, {digits: 0})}
        <td>${ws == null ? '<span class="dim">—</span>' : `${pct(ws, 0)} <span class="dim">(${pct(sitShare, 0)})</span>`}</td><td>${(C.corr(pts, margin) ?? 0).toFixed(2)}</td></tr>`;
    }).join('');
    // teammates' points: correlation matrix (top six by projected points)
    const top = data.projection.sim[side].players.filter(p => p.periods).slice().sort((a, b) => b.periods.fg.mean.pts - a.periods.fg.mean.pts).slice(0, 6);
    const cols = top.map(p => Wd.values('p:' + p.id, 'pts'));
    const short = p => p.name.split(' ').slice(-1)[0];
    const mat = top.map((p, i) => `<tr><td class="l">${esc(short(p))}</td>${top.map((q, j) => {
      if (i === j) return '<td class="dim">·</td>';
      const r = C.corr(cols[i], cols[j]) ?? 0;
      return `<td class="corr" style="--r:${Math.abs(r).toFixed(3)}" data-sign="${r < 0 ? 'neg' : 'pos'}">${r.toFixed(2)}</td>`;
    }).join('')}</tr>`).join('');
    // who gains when a maybe sits
    const gains = ps.filter(p => { const s = C.mean(Wd.values('p:' + p.id, 'sits')); return s > 0.02 && s < 0.98; }).map(p => {
      const sitM = O.mask(Wd, [{subj: 'p:' + p.id, v: 'sits'}]), playM = O.mask(Wd, [{subj: 'p:' + p.id, v: 'plays'}]);
      const mates = data.projection.sim[side].players.filter(q => q.periods && q.id !== p.id).map(q => {
        const mn = Wd.values('p:' + q.id, 'min'), pt = Wd.values('p:' + q.id, 'pts');
        return {q, dm: C.mean(mn, sitM) - C.mean(mn, playM), dp: C.mean(pt, sitM) - C.mean(pt, playM)};
      }).sort((a, b) => b.dm - a.dm).slice(0, 5);
      return `<p class="note"><b>If ${esc(p.name)} sits</b> (${pct(C.mean(Wd.values('p:' + p.id, 'sits')), 0)} of simulations): ${mates.map(x => `${esc(x.q.name)} ${signed(x.dm)} min, ${signed(x.dp)} pts`).join(' · ')}.</p>`;
    }).join('');
    return `<section class="panel"><h3 style="margin-top:0">${esc(team(data.game[side].id).name)} — who drives the result</h3>
      <div class="scroll"><table><thead><tr><th class="name">Player</th><th>Big / quiet night (pts)</th><th>Win if big</th><th>Win if quiet</th><th>Win if he does not play (share)</th><th>r with margin</th></tr></thead><tbody>${rows}</tbody></table></div>
      <p class="note">Team win chance overall ${pct(base, 1)}. Big night = his top quarter of simulated points, quiet = bottom quarter. "Does not play" counts every simulated game without him — injury availability and nights the rotation leaves him out.</p>
      <h3>Teammates' points — correlation</h3><div class="scroll" style="max-width:560px"><table class="grid"><thead><tr><th class="l"></th>${top.map(p => `<th>${esc(short(p))}</th>`).join('')}</tr></thead><tbody>${mat}</tbody></table></div>
      <p class="note">Negative: they compete for the same shots and minutes; positive: they rise together (pace, a good offensive night).</p>${gains}</section>`;
  });
  el.innerHTML = sections.join('');
}
