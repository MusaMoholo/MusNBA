// Scenarios, conditional and joint outcomes (owner, 20 Nov: "player A given player B", outcomes given minutes, matchup
// deltas). Everything is read from the game's stored simulated worlds (outcomes.mjs) — the app slices, never simulates.
import {esc, f1, heat, pct, signed, team} from './ui.mjs';
import * as O from './outcomes.mjs';

const memory = new Map();  // game id → conditions (also kept in the route)
const BOX = [['min', 'MIN'], ['pts', 'PTS'], ['reb', 'REB'], ['ast', 'AST'], ['fg3m', '3PM'], ['stl', 'STL'], ['blk', 'BLK'], ['tov', 'TOV'], ['fgpct', 'FG%']];

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
  const d = vals ? O.dist(vals) : null;
  const value = x ?? (d ? d.q[3] : 0);
  return `<div class="builder" data-builder="${prefix}"${variableOnly ? ' data-only="1"' : ''}>
    <select data-b="subj" aria-label="Who">${O.subjectOptions(data, subj)}</select>
    <select data-b="v" aria-label="What">${O.varOptions(subj, v)}</select>
    <select data-b="op" aria-label="Comparison"${O.isFlag(v) || variableOnly ? ' hidden' : ''}><option value="ge"${op === 'ge' ? ' selected' : ''}>at least</option><option value="le"${op === 'le' ? ' selected' : ''}>at most</option></select>
    <input data-b="x" type="number" step="1" value="${value}" aria-label="Value"${O.isFlag(v) || variableOnly ? ' hidden' : ''}>
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
    if (!flag) { const d = O.dist(Wd.values(subj.value, v.value) || []); if (d) input.value = d.q[3]; }
  };
  subj.onchange = () => { v.innerHTML = O.varOptions(subj.value, subj.value.startsWith('p:') ? 'pts' : subj.value === 'g' ? 'total' : 'win'); refreshValue(); onChange?.(readBuilder(root)); };
  v.onchange = () => { refreshValue(); onChange?.(readBuilder(root)); };
  root.querySelector('[data-b="op"]').onchange = () => onChange?.(readBuilder(root));
  root.querySelector('[data-b="x"]').onchange = () => onChange?.(readBuilder(root));
  const add = root.querySelector('[data-b="add"]');
  if (add) add.onclick = () => onAdd?.(readBuilder(root));
}

function presets(data, Wd) {
  const out = [], A = abbrs(data);
  for (const p of played(data)) {
    const sits = O.mean(Wd.values('p:' + p.id, 'sits'));
    if (sits != null && sits > 0.01 && sits < 0.99) {
      out.push([`${p.name} sits (${pct(sits, 0)})`, [{subj: 'p:' + p.id, v: 'sits'}]]);
      out.push([`${p.name} plays`, [{subj: 'p:' + p.id, v: 'plays'}]]);
    }
  }
  const total = O.dist(Wd.values('g', 'total'));
  out.push([`${A.home} wins`, [{subj: 't:home', v: 'win'}]], [`${A.away} wins`, [{subj: 't:away', v: 'win'}]],
    ['Close game (≤ 5)', [{subj: 'g', v: 'absm', op: 'le', x: 5}]], ['Blowout (15+)', [{subj: 'g', v: 'absm', op: 'ge', x: 15}]],
    ['Overtime', [{subj: 'g', v: 'ot'}]], [`Shootout (total ${total.q[3]}+)`, [{subj: 'g', v: 'total', op: 'ge', x: total.q[3]}]],
    [`Grind (total ≤ ${total.q[1]})`, [{subj: 'g', v: 'total', op: 'le', x: total.q[1]}]]);
  const stars = played(data).sort((a, b) => b.periods.fg.mean.pts - a.periods.fg.mean.pts).slice(0, 2);
  for (const p of stars) {
    const d = O.dist(Wd.values('p:' + p.id, 'pts'));
    out.push([`${p.name} ${d.q[4]}+ pts`, [{subj: 'p:' + p.id, v: 'pts', op: 'ge', x: d.q[4]}]], [`${p.name} ≤ ${d.q[0]} pts`, [{subj: 'p:' + p.id, v: 'pts', op: 'le', x: d.q[0]}]]);
  }
  return out;
}

// ------------------------------------------------------------------ Scenarios tab
export async function scenarioView(el, data, encoded) {
  const Wd = await O.load(data.game.id);
  let conds = encoded ? decode(encoded) : (memory.get(data.game.id) || []);
  const N = names(data), A = abbrs(data), base = new Uint8Array(Wd.W).fill(1);
  const setConds = next => {
    conds = next;
    memory.set(data.game.id, conds);
    location.replace(`#/game/${data.game.id}/scenario${conds.length ? '/' + encode(conds) : ''}`);
  };
  const paint = () => {
    const m = O.mask(Wd, conds), n = O.count(m);
    const indep = conds.length > 1 ? conds.reduce((p, c) => p * O.count(O.mask(Wd, [c])) / Wd.W, 1) : null;
    const chips = conds.map((c, i) => `<button type="button" class="chip" data-del="${i}" title="Remove">${esc(O.label(c, N, A))} ×</button>`).join('');
    const pre = presets(data, Wd).map(([l, cs], i) => `<button type="button" class="ghost sm" data-pre="${i}">${esc(l)}</button>`).join('');
    let body = '';
    if (!n) body = '<section class="panel"><p class="note">No simulated game matches every condition — remove one.</p></section>';
    else {
      const teamRows = ['away', 'home'].map(side => {
        const pts = Wd.values('t:' + side, 'pts'), win = Wd.values('t:' + side, 'win');
        const s = O.mean(pts, m), b = O.mean(pts, base), ws = O.mean(win, m), wb = O.mean(win, base);
        return `<tr><td class="l">${esc(team(data.game[side].id).name)}</td><td><b>${f1(s)}</b>${delta(s - b)}</td>${heat(ws, {digits: 1})}<td class="dim">${pct(wb, 1)}</td></tr>`;
      }).join('');
      const tot = Wd.values('g', 'total'), mar = Wd.values('t:home', 'margin'), ot = Wd.values('g', 'ot');
      const game = `<tr class="sep"><td class="l">Total</td><td><b>${f1(O.mean(tot, m))}</b>${delta(O.mean(tot, m) - O.mean(tot, base))}</td><td></td><td></td></tr>
        <tr><td class="l">Margin (${esc(A.home)} − ${esc(A.away)})</td><td><b>${signed(O.mean(mar, m))}</b>${delta(O.mean(mar, m) - O.mean(mar, base))}</td><td></td><td></td></tr>
        <tr><td class="l">Overtime</td><td><b>${pct(O.mean(ot, m), 1)}</b><span class="sub">all ${pct(O.mean(ot, base), 1)}</span></td><td></td><td></td></tr>`;
      const boxes = ['away', 'home'].map(side => {
        const ps = data.projection.sim[side].players.filter(p => p.periods).slice().sort((a, b) => b.periods.fg.sec - a.periods.fg.sec);
        const rows = ps.map(p => {
          const subj = 'p:' + p.id, sits = O.mean(Wd.values(subj, 'sits'), m);
          return `<tr><td class="name">${esc(p.name)}${sits > 0.995 ? ' <span class="tag">sits</span>' : sits > 0.005 ? ` <span class="tag">sits ${pct(sits, 0)}</span>` : ''}</td>${BOX.map(([k]) => {
            const vals = Wd.values(subj, k);
            if (!vals) return '<td>—</td>';
            const s = O.mean(vals, m), b = O.mean(vals, base);
            return `<td>${s == null ? '—' : k === 'fgpct' ? f1(s) : f1(s)}${s == null || b == null ? '' : delta(s - b, 1)}</td>`;
          }).join('')}</tr>`;
        }).join('');
        return `<section class="panel"><h3 style="margin-top:0">${esc(team(data.game[side].id).name)} under this scenario</h3><div class="scroll"><table class="box"><thead><tr><th class="name">Player</th>${BOX.map(([, l]) => `<th>${l}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></div></section>`;
      }).join('');
      body = `<section class="panel"><div class="tiles"><div class="tile"><span>Chance of this scenario</span><b>${pct(n / Wd.W, 1)}</b><small>${n.toLocaleString()} of ${Wd.W.toLocaleString()} worlds</small></div>
          ${indep != null ? `<div class="tile"><span>If the conditions were independent</span><b>${pct(indep, 1)}</b><small>${indep > 0 ? `×${(n / Wd.W / indep).toFixed(2)} correlation lift` : ''}</small></div>` : ''}</div>
        ${n < 60 ? `<p class="note warn">Only ${n} simulated games match — read the numbers below as rough.</p>` : ''}
        <div class="scroll" style="margin-top:10px"><table><thead><tr><th class="l">Team</th><th>Points (Δ)</th><th>Win given</th><th>Win, all</th></tr></thead><tbody>${teamRows}${game}</tbody></table></div></section>${boxes}`;
    }
    el.innerHTML = `<section class="panel"><h2 style="margin-top:0">Scenarios</h2>
        <p class="note" style="margin-top:0">Pick conditions; the game is re-read from the ${Wd.W.toLocaleString()} simulated games where all of them happen. Small grey numbers: change from all simulations.</p>
        <div class="chips left">${chips || '<span class="note" style="margin:0">No conditions — all simulations.</span>'}${conds.length ? '<button type="button" class="ghost sm" data-clear>Clear</button>' : ''}</div>
        ${builder(data, Wd, 'scn')}
        <details style="margin-top:8px"><summary class="note" style="cursor:pointer">Quick scenarios</summary><div class="chips left" style="margin-top:6px">${pre}</div></details></section>${body}`;
    const pres = presets(data, Wd);
    el.querySelectorAll('[data-del]').forEach(b => b.onclick = () => setConds(conds.filter((_, i) => i !== Number(b.dataset.del))));
    el.querySelector('[data-clear]')?.addEventListener('click', () => setConds([]));
    el.querySelectorAll('[data-pre]').forEach(b => b.onclick = () => setConds([...conds, ...pres[Number(b.dataset.pre)][1]]));
    wireBuilder(el.querySelector('[data-builder="scn"]'), data, Wd, null, c => setConds([...conds, c]));
  };
  paint();
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
  try { Wd = await O.load(data.game.id); } catch { return; }
  const subj = 'p:' + pid, xVals = Wd.values(subj, stat);
  if (!xVals) { el.innerHTML = ''; return; }
  const N = names(data), A = abbrs(data), side = played(data).find(p => p.id === pid)?.side || 'home';
  let given = {subj: 't:' + side, v: 'win'};
  let other = {subj, v: stat === 'min' ? 'pts' : 'min'};
  const paint = () => {
    const m = O.mask(Wd, [given]), n = O.count(m);
    const all = O.dist(xVals), cond = n ? O.dist(xVals, m) : null;
    const pAll = O.share(xVals, null, v => v > line), pCond = n ? O.share(xVals, m, v => v > line) : null;
    const yVals = Wd.values(other.subj, other.v);
    const r = yVals ? O.corr(xVals, yVals) : null;
    const yName = O.label({...other, op: 'ge', x: ''}, N, A).replace(/ ≥ $/, '');
    const xName = (O.PLAYER_VARS.find(([k]) => k === stat) || [stat, stat.toUpperCase()])[1];
    el.innerHTML = `<section class="panel"><h3 style="margin-top:0">Given…</h3>
        ${builder(data, Wd, 'given', {...given, button: ''})}
        <p class="note">${n ? `${esc(O.label(given, N, A))}: ${pct(n / Wd.W, 1)} of simulations (${n.toLocaleString()}).` : 'No simulation matches.'}</p>
        ${cond ? `<div class="dist" style="margin-top:6px"><div>${O.overlay(all, cond, {line})}
          <p class="note"><span class="legend-bar"></span> given the condition · <span class="legend-line"></span> all simulations</p></div>
          <div class="scroll"><table><thead><tr><th class="l"></th><th>Given</th><th>All</th></tr></thead><tbody>
            <tr><td class="l">Mean</td><td><b>${f1(cond.mean)}</b></td><td>${f1(all.mean)}</td></tr>
            <tr><td class="l">Median</td><td>${cond.q[2]}</td><td>${all.q[2]}</td></tr>
            <tr><td class="l">10–90%</td><td>${cond.q[0]}–${cond.q[4]}</td><td>${all.q[0]}–${all.q[4]}</td></tr>
            <tr><td class="l">Over ${line}</td>${heat(pCond, {digits: 1})}${heat(pAll, {digits: 1})}</tr></tbody></table></div></div>` : ''}</section>
      <section class="panel"><h3 style="margin-top:0">Joint outcomes</h3>
        <p class="note" style="margin-top:0">${esc(xName)} (across) against:</p>
        ${builder(data, Wd, 'joint', {subj: other.subj, v: other.v, button: '', variableOnly: true})}
        ${yVals ? `${O.grid(xVals, yVals, null, {xName, yName})}<p class="note">Each cell: share of all simulations with both. Correlation ${r == null ? '—' : r.toFixed(2)}${r != null ? (Math.abs(r) < 0.1 ? ' (little link)' : r > 0 ? ' (they rise together)' : ' (one rises as the other falls)') : ''}.</p>` : '<p class="note">Choose a numeric outcome (not a yes/no) to see the grid.</p>'}</section>`;
    wireBuilder(el.querySelector('[data-builder="given"]'), data, Wd, c => { given = c; paint(); });
    wireBuilder(el.querySelector('[data-builder="joint"]'), data, Wd, c => { if (!O.isFlag(c.v)) { other = c; paint(); } });
  };
  paint();
}

// ------------------------------------------------------------------ team view: who drives the result
export async function driversPanel(el, data) {
  let Wd;
  try { Wd = await O.load(data.game.id); } catch { el.innerHTML = ''; return; }
  const sections = ['away', 'home'].map(side => {
    const win = Wd.values('t:' + side, 'win'), margin = Wd.values('t:' + side, 'margin'), base = O.mean(win);
    const ps = data.projection.sim[side].players.filter(p => p.periods).slice().sort((a, b) => b.periods.fg.sec - a.periods.fg.sec).slice(0, 8);
    const rows = ps.map(p => {
      const pts = Wd.values('p:' + p.id, 'pts'), sits = Wd.values('p:' + p.id, 'sits'), d = O.dist(pts);
      const qx = Math.max(0, d.q[1] - 1), bx = Math.max(qx + 1, d.q[3] + 1);
      const big = O.mask(Wd, [{subj: 'p:' + p.id, v: 'pts', op: 'ge', x: bx}]), quiet = O.mask(Wd, [{subj: 'p:' + p.id, v: 'pts', op: 'le', x: qx}]);
      const sitShare = O.mean(sits), sitMask = O.mask(Wd, [{subj: 'p:' + p.id, v: 'sits'}]);
      const wb = O.count(big) ? O.mean(win, big) : null, wq = O.count(quiet) ? O.mean(win, quiet) : null;
      const ws = sitShare > 0.01 ? O.mean(win, sitMask) : null;
      return `<tr><td class="name">${esc(p.name)}</td><td class="dim">${bx}+ / ${qx ? '≤' + qx : '0'}</td>${heat(wb, {digits: 0})}${heat(wq, {digits: 0})}
        <td>${ws == null ? '<span class="dim">—</span>' : `${pct(ws, 0)} <span class="dim">(${pct(sitShare, 0)})</span>`}</td><td>${(O.corr(pts, margin) ?? 0).toFixed(2)}</td></tr>`;
    }).join('');
    // teammates' points: correlation matrix (top six by projected points)
    const top = data.projection.sim[side].players.filter(p => p.periods).slice().sort((a, b) => b.periods.fg.mean.pts - a.periods.fg.mean.pts).slice(0, 6);
    const cols = top.map(p => Wd.values('p:' + p.id, 'pts'));
    const short = p => p.name.split(' ').slice(-1)[0];
    const mat = top.map((p, i) => `<tr><td class="l">${esc(short(p))}</td>${top.map((q, j) => {
      if (i === j) return '<td class="dim">·</td>';
      const r = O.corr(cols[i], cols[j]) ?? 0;
      return `<td class="corr" style="--r:${Math.abs(r).toFixed(3)}" data-sign="${r < 0 ? 'neg' : 'pos'}">${r.toFixed(2)}</td>`;
    }).join('')}</tr>`).join('');
    // who gains when a maybe sits
    const gains = ps.filter(p => { const s = O.mean(Wd.values('p:' + p.id, 'sits')); return s > 0.02 && s < 0.98; }).map(p => {
      const sitM = O.mask(Wd, [{subj: 'p:' + p.id, v: 'sits'}]), playM = O.mask(Wd, [{subj: 'p:' + p.id, v: 'plays'}]);
      const mates = data.projection.sim[side].players.filter(q => q.periods && q.id !== p.id).map(q => {
        const mn = Wd.values('p:' + q.id, 'min'), pt = Wd.values('p:' + q.id, 'pts');
        return {q, dm: O.mean(mn, sitM) - O.mean(mn, playM), dp: O.mean(pt, sitM) - O.mean(pt, playM)};
      }).sort((a, b) => b.dm - a.dm).slice(0, 5);
      return `<p class="note"><b>If ${esc(p.name)} sits</b> (${pct(O.mean(Wd.values('p:' + p.id, 'sits')), 0)} of simulations): ${mates.map(x => `${esc(x.q.name)} ${signed(x.dm)} min, ${signed(x.dp)} pts`).join(' · ')}.</p>`;
    }).join('');
    return `<section class="panel"><h3 style="margin-top:0">${esc(team(data.game[side].id).name)} — who drives the result</h3>
      <div class="scroll"><table><thead><tr><th class="name">Player</th><th>Big / quiet night (pts)</th><th>Win if big</th><th>Win if quiet</th><th>Win if he does not play (share)</th><th>r with margin</th></tr></thead><tbody>${rows}</tbody></table></div>
      <p class="note">Team win chance overall ${pct(base, 1)}. Big night = his top quarter of simulated points, quiet = bottom quarter. "Does not play" counts every simulated game without him — injury availability and nights the rotation leaves him out.</p>
      <h3>Teammates' points — correlation</h3><div class="scroll" style="max-width:560px"><table class="grid"><thead><tr><th class="l"></th>${top.map(p => `<th>${esc(short(p))}</th>`).join('')}</tr></thead><tbody>${mat}</tbody></table></div>
      <p class="note">Negative: they compete for the same shots and minutes; positive: they rise together (pace, a good offensive night).</p>${gains}</section>`;
  });
  el.innerHTML = sections.join('');
}
