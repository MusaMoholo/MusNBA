// Joint and conditional outcomes from a game's stored simulated worlds (views → api/game/<id>/worlds).
// Every world is one simulated game; a condition selects worlds, and any outcome's distribution is read from the
// selected worlds. Nothing is simulated or fitted here: the app only slices the engine's own worlds.
import {api, esc, pct, team} from './ui.mjs';
import {correlation as weightedCorrelation, distribution as weightedDistribution, grid as weightedGrid,
  gridEdges, selectedMass, weightedMean, weightedShare} from './weighted-worlds.mjs';

const cache = new Map();
const b64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));

// Owner (20 Nov): makes and the main stats (no combos or attempts); OREB/DREB where the stored worlds carry them
export const PLAYER_VARS = [['available', 'Available'], ['unavailable', 'Unavailable'], ['plays', 'Plays'], ['sits', 'Sits (does not play)'], ['min', 'Minutes'], ['pts', 'Points'], ['reb', 'Rebounds'],
  ['oreb', 'Offensive rebounds'], ['dreb', 'Defensive rebounds'], ['ast', 'Assists'], ['fg3m', 'Threes made'], ['fgm', 'Field goals made'],
  ['ftm', 'Free throws made'], ['stl', 'Steals'], ['blk', 'Blocks'], ['tov', 'Turnovers'], ['fgpct', 'FG% (of attempts)']];
export const TEAM_VARS = [['win', 'Wins'], ['lose', 'Loses'], ['pts', 'Points'], ['margin', 'Margin'],
  ['q1', 'Q1 points'], ['q2', 'Q2 points'], ['q3', 'Q3 points'], ['q4', 'Q4 points'], ['h1', '1st-half points'], ['h2', '2nd-half points'],
  ['wq1', 'Wins Q1'], ['wq2', 'Wins Q2'], ['wq3', 'Wins Q3'], ['wq4', 'Wins Q4'], ['wh1', 'Wins the 1st half'], ['wh2', 'Wins the 2nd half'],
  ['q1m', 'Margin after Q1'], ['h1m', 'Half-time margin'], ['q3m', 'Margin after Q3'], ['q4m', 'Q4 margin'],
  ['lead1', 'Leads after Q1'], ['leadh', 'Leads at half-time'], ['lead3', 'Leads after Q3'],
  ['comeback', 'Wins from behind at half-time'], ['blown', 'Loses after leading at half-time'], ['wire', 'Leads at every break and wins'],
  ['sweep', 'Wins every quarter'], ['qwins', 'Quarters won (of 4)']];
export const GAME_VARS = [['total', 'Total points'], ['absm', 'Margin either way'], ['ot', 'Goes to overtime'], ['not', 'No overtime'],
  ['t1', 'Q1 total'], ['th1', '1st-half total'], ['th2', '2nd-half total'], ['t4', 'Q4 total'],
  ['changes', 'Leader changes at the breaks'], ['flip', 'Half-time leader loses'], ['close3', 'Within 5 after Q3']];
const FLAGS = new Set(['plays', 'sits', 'available', 'unavailable', 'win', 'lose', 'ot', 'not', 'wq1', 'wq2', 'wq3', 'wq4', 'wh1', 'wh2', 'lead1', 'leadh', 'lead3',
  'comeback', 'blown', 'wire', 'sweep', 'flip', 'close3']);
export const isFlag = v => FLAGS.has(v);

export async function load(gid) {
  if (cache.has(gid)) return cache.get(gid);
  const raw = await api(`game/${encodeURIComponent(gid)}/worlds`);
  const result = worldData(raw);
  cache.set(gid, result);
  return result;
}

/** Adapt a validated research source without changing the saved production-world path. */
export function branchWorldData(source, choices = {}) {
  const raw = {worlds: source.worlds, players: source.players, side: source.side, stats: source.stats};
  return worldData(raw, {
    weights: source.weights, baseMask: source.selection(choices),
    player: (id, stat) => source.playerValues(id, stat),
    team: (side, q) => source.teamPoints(side, ['q1', 'q2', 'q3', 'q4', 'ot'][q]),
    overtime: () => source.overtimePeriods(),
  });
}

function worldData(raw, source = null) {
  const W = raw.worlds, n = raw.players.length, k = raw.stats.length;
  const lines = source ? null : b64(raw.lines), tp = source ? null : b64(raw.team_periods);
  const idx = new Map(raw.players.map((p, i) => [p, i]));
  const memo = new Map();
  const statCol = (i, s) => {
    const j = raw.stats.indexOf(s), out = new Float64Array(W);
    if (j < 0) return null;
    if (source) return source.player(raw.players[i], s);
    for (let w = 0; w < W; w++) out[w] = lines[(w * n + i) * k + j];
    return out;
  };
  const add = (...cols) => { const out = new Float64Array(W); for (const c of cols) for (let w = 0; w < W; w++) out[w] += c[w]; return out; };
  const teamCol = (side, q) => {
    if (source) {
      const key = `team-column|${side}|${q}`;
      if (!memo.has(key)) memo.set(key, source.team(side, q));
      return memo.get(key);
    }
    const s = side === 'home' ? 0 : 1, out = new Float64Array(W);
    for (let w = 0; w < W; w++) out[w] = tp[(w * 2 + s) * 5 + q];
    return out;
  };
  const W_ = {W, ids: raw.players, side: raw.side.map(s => (s === 0 ? 'home' : 'away')), stats: raw.stats};
  if (source) Object.assign(W_, {weights: source.weights, baseMask: source.baseMask});
  /** Side's cumulative margin after the first k quarters (k = 1..4), every world. */
  W_.lead = (side, k) => {
    const key = 'lead|' + side + '|' + k;
    if (memo.has(key)) return memo.get(key);
    const other = side === 'home' ? 'away' : 'home', out = new Float64Array(W);
    for (let q = 0; q < k; q++) { const a = teamCol(side, q), b = teamCol(other, q); for (let w = 0; w < W; w++) out[w] += a[w] - b[w]; }
    memo.set(key, out);
    return out;
  };
  /** Values of variable `v` for subject `subj` ('p:<id>', 't:home', 't:away', 'g') in every world, or null. */
  W_.values = (subj, v) => {
    const key = subj + '|' + v;
    if (memo.has(key)) return memo.get(key);
    let out = null;
    if (subj.startsWith('p:')) {
      const i = idx.get(subj.slice(2));
      if (i == null) return null;
      const c = s => W_.values(subj, s);
      if (source && ['plays', 'sits', 'available', 'unavailable'].includes(v)) out = source.player(subj.slice(2), v);
      else if (v === 'plays' || v === 'sits') { const m = c('min'); out = m.map(x => (v === 'plays' ? x > 0 : x === 0) ? 1 : 0); }
      else if (v === 'pra') out = add(c('pts'), c('reb'), c('ast'));
      else if (v === 'pr') out = add(c('pts'), c('reb'));
      else if (v === 'pa') out = add(c('pts'), c('ast'));
      else if (v === 'ra') out = add(c('reb'), c('ast'));
      else if (v === 'stocks') out = add(c('stl'), c('blk'));
      else if (v === 'fgpct') { const m = c('fgm'), a = c('fga'); out = m.map((x, w) => (a[w] > 0 ? Math.round(100 * x / a[w]) : NaN)); }
      else if (v === 'ftm' && !raw.stats.includes('ftm')) { const p_ = c('pts'), m = c('fgm'), t = c('fg3m'); out = p_.map((x, w) => Math.max(0, x - 2 * m[w] - t[w])); }
      else out = statCol(i, v);
    } else if (subj.startsWith('t:')) {
      const side = subj.slice(2), other = side === 'home' ? 'away' : 'home';
      const pts = s => add(teamCol(s, 0), teamCol(s, 1), teamCol(s, 2), teamCol(s, 3), teamCol(s, 4));
      if (v === 'pts') out = pts(side);
      else if (v === 'margin' || v === 'win' || v === 'lose') {
        const a = pts(side), b = pts(other);
        out = a.map((x, w) => (v === 'margin' ? x - b[w] : v === 'win' ? (x > b[w] ? 1 : 0) : (x < b[w] ? 1 : 0)));
      } else if (v === 'h2') out = add(teamCol(side, 2), teamCol(side, 3));
      else if (v === 'h1') out = add(teamCol(side, 0), teamCol(side, 1));
      else if (/^q[1-4]$/.test(v)) out = teamCol(side, Number(v[1]) - 1);
      else if (/^wq[1-4]$/.test(v)) { const q = Number(v[2]) - 1, a = teamCol(side, q), b = teamCol(other, q); out = a.map((x, w) => (x > b[w] ? 1 : 0)); }
      else if (v === 'q4m') { const a = teamCol(side, 3), b = teamCol(other, 3); out = a.map((x, w) => x - b[w]); }
      else if (v === 'wh1' || v === 'wh2') { const qs = v === 'wh1' ? [0, 1] : [2, 3]; const a = add(...qs.map(q => teamCol(side, q))), b = add(...qs.map(q => teamCol(other, q))); out = a.map((x, w) => (x > b[w] ? 1 : 0)); }
      else if (['q1m', 'h1m', 'q3m'].includes(v)) out = W_.lead(side, {q1m: 1, h1m: 2, q3m: 3}[v]);
      else if (['lead1', 'leadh', 'lead3'].includes(v)) out = W_.lead(side, {lead1: 1, leadh: 2, lead3: 3}[v]).map(x => (x > 0 ? 1 : 0));
      else if (v === 'comeback' || v === 'blown') {
        const h = W_.lead(side, 2), win = W_.values(subj, 'win');
        out = h.map((x, w) => (v === 'comeback' ? (x < 0 && win[w]) : (x > 0 && !win[w])) ? 1 : 0);
      } else if (v === 'wire') {
        const l1 = W_.lead(side, 1), l2 = W_.lead(side, 2), l3 = W_.lead(side, 3), win = W_.values(subj, 'win');
        out = l1.map((x, w) => (x > 0 && l2[w] > 0 && l3[w] > 0 && win[w]) ? 1 : 0);
      } else if (v === 'qwins' || v === 'sweep') {
        const qs = [1, 2, 3, 4].map(q => W_.values(subj, 'wq' + q));
        out = qs[0].map((_, w) => qs.reduce((a, c) => a + c[w], 0));
        if (v === 'sweep') out = out.map(x => (x === 4 ? 1 : 0));
      }
    } else if (subj === 'g') {
      const h = W_.values('t:home', 'pts'), a = W_.values('t:away', 'pts');
      if (v === 'total') out = h.map((x, w) => x + a[w]);
      else if (v === 'absm') out = h.map((x, w) => Math.abs(x - a[w]));
      else if (v === 'ot' || v === 'not') { const o = source ? source.overtime() : add(teamCol('home', 4), teamCol('away', 4)); out = o.map(x => (v === 'ot' ? x > 0 : x === 0) ? 1 : 0); }
      else if (v === 't1' || v === 't4') { const q = v === 't1' ? 0 : 3; out = add(teamCol('home', q), teamCol('away', q)); }
      else if (v === 'th1' || v === 'th2') { const qs = v === 'th1' ? [0, 1] : [2, 3]; out = add(...qs.flatMap(q => [teamCol('home', q), teamCol('away', q)])); }
      else if (v === 'changes') {  // the leader changes between consecutive breaks (Q1, half, Q3, final); ties keep the leader
        const L = [1, 2, 3].map(k => W_.lead('home', k)), fin = W_.values('t:home', 'margin');
        out = fin.map((f, w) => { let n = 0, prev = Math.sign(L[0][w]); for (const x of [L[1][w], L[2][w], f]) { const s_ = Math.sign(x); if (s_ && prev && s_ !== prev) n++; if (s_) prev = s_; } return n; });
      } else if (v === 'flip') { const h = W_.lead('home', 2), fin = W_.values('t:home', 'margin'); out = h.map((x, w) => (x * fin[w] < 0 ? 1 : 0)); }
      else if (v === 'close3') out = W_.lead('home', 3).map(x => (Math.abs(x) <= 5 ? 1 : 0));
    }
    memo.set(key, out);
    return out;
  };
  return W_;
}

/** Worlds selected by every condition (AND). A condition: {subj, v, op ('ge' | 'le'), x} or a flag variable. */
export function mask(Wd, conds) {
  const m = Wd.baseMask ? Wd.baseMask.slice() : new Uint8Array(Wd.W).fill(1);
  for (const c of conds) {
    if (Wd.baseMask && (!c || typeof c.subj !== 'string' || typeof c.v !== 'string'
        || (!isFlag(c.v) && (!['ge', 'le'].includes(c.op) || !Number.isFinite(c.x))))) {
      throw new Error('Invalid condition for selected worlds');
    }
    const vals = Wd.values(c.subj, c.v);
    if (!vals) {
      if (Wd.baseMask || ['available', 'unavailable'].includes(c.v)) throw new Error('Condition is unavailable in the selected worlds');
      continue;
    }
    for (let w = 0; w < Wd.W; w++) {
      if (!m[w]) continue;
      const x = vals[w];
      m[w] = isFlag(c.v) ? (x === 1 ? 1 : 0) : Number.isNaN(x) ? 0 : (c.op === 'le' ? x <= c.x : x >= c.x) ? 1 : 0;
    }
  }
  return m;
}
export const count = m => m.reduce((a, b) => a + b, 0);

/** Arithmetic bound to one selected branch mixture; counts and probability mass remain distinct. */
export function branchCalculations(Wd) {
  if (!Wd.weights || !Wd.baseMask || Wd.weights.length !== Wd.W || Wd.baseMask.length !== Wd.W) {
    throw new Error('Weighted selected worlds required');
  }
  const selected = mask => {
    if (mask == null) return Wd.baseMask;
    if (mask.length !== Wd.W || mask.some(v => v !== 0 && v !== 1)) throw new Error('Invalid world mask');
    return Uint8Array.from(mask, (v, i) => v && Wd.baseMask[i] ? 1 : 0);
  };
  const distribution = (values, mask = null) => {
    const m = selected(mask), exact = weightedDistribution(values, Wd.weights, m);
    if (!exact.defined) return null;
    const rounded = weightedDistribution(values.map(v => Math.round(v)), Wd.weights, m);
    const lo = rounded.histogram[0][0], hi = rounded.histogram.at(-1)[0], hist = new Array(hi - lo + 1).fill(0);
    for (const [value, mass] of rounded.histogram) hist[value - lo] = mass;
    return {min: lo, hist, mean: exact.mean, q: exact.quantiles, n: exact.n, mass: exact.defined};
  };
  return {
    count: mask => count(selected(mask)),
    mass: mask => selectedMass(Wd.weights, selected(mask)),
    dist: distribution,
    mean: (values, mask = null) => weightedMean(values, Wd.weights, selected(mask)),
    share: (values, mask, test) => weightedShare(values, Wd.weights, test, selected(mask)),
    corr: (a, b, mask = null) => weightedCorrelation(a, b, Wd.weights, selected(mask)),
    grid: (x, y, mask, names) => weightedGridView(x, y, Wd.weights, selected(mask), names),
  };
}

/** Distribution of integer outcomes over the selected worlds, in the app's histogram format ({min, hist, mean, q}). */
export function dist(vals, m = null) {
  const xs = [];
  for (let w = 0; w < vals.length; w++) if ((!m || m[w]) && !Number.isNaN(vals[w])) xs.push(Math.round(vals[w]));
  if (!xs.length) return null;
  xs.sort((a, b) => a - b);
  const lo = xs[0], hi = xs[xs.length - 1], hist = new Array(hi - lo + 1).fill(0);
  let sum = 0;
  for (const x of xs) { hist[x - lo]++; sum += x; }
  const q = [0.1, 0.25, 0.5, 0.75, 0.9].map(p => xs[Math.min(xs.length - 1, Math.floor(p * xs.length))]);
  return {min: lo, hist, mean: sum / xs.length, q, n: xs.length};
}
export function mean(vals, m = null) {
  let s = 0, n = 0;
  for (let w = 0; w < vals.length; w++) if ((!m || m[w]) && !Number.isNaN(vals[w])) { s += vals[w]; n++; }
  return n ? s / n : null;
}
export function share(vals, m, test) {
  let s = 0, n = 0;
  for (let w = 0; w < vals.length; w++) if (!m || m[w]) { n++; if (test(vals[w])) s++; }
  return n ? s / n : null;
}
export function corr(a, b, m = null) {
  let n = 0, sa = 0, sb = 0, saa = 0, sbb = 0, sab = 0;
  for (let w = 0; w < a.length; w++) {
    if ((m && !m[w]) || Number.isNaN(a[w]) || Number.isNaN(b[w])) continue;
    n++; sa += a[w]; sb += b[w]; saa += a[w] * a[w]; sbb += b[w] * b[w]; sab += a[w] * b[w];
  }
  if (n < 3) return null;
  const va = saa / n - (sa / n) ** 2, vb = sbb / n - (sb / n) ** 2;
  return va > 0 && vb > 0 ? (sab / n - (sa / n) * (sb / n)) / Math.sqrt(va * vb) : null;
}

/** Condition label for chips and notes. names: id → player name; teams: side → abbreviation. */
export function label(c, names, teams) {
  const subj = c.subj.startsWith('p:') ? (names.get(c.subj.slice(2)) || 'Player') : c.subj.startsWith('t:') ? teams[c.subj.slice(2)] : 'Game';
  const vars = c.subj.startsWith('p:') ? PLAYER_VARS : c.subj.startsWith('t:') ? TEAM_VARS : GAME_VARS;
  const name = (vars.find(([k]) => k === c.v) || [c.v, c.v])[1];
  const lc = t => (/^[A-Z][a-z]/.test(t) ? t[0].toLowerCase() + t.slice(1) : t);  // "Wins Q1" → "wins Q1", keep "Q1 points"
  if (isFlag(c.v)) return c.subj === 'g' ? name : `${subj} ${lc(name)}`;
  return `${subj} ${lc(name)} ${c.op === 'le' ? '≤' : '≥'} ${c.x}`;
}

/** Overlaid histogram: the conditional distribution as bars, the baseline as a step outline (both as shares). */
export function overlay(base, cond, {line = null, height = 170} = {}) {
  const lo = Math.min(base.min, cond ? cond.min : base.min);
  const hi = Math.max(base.min + base.hist.length - 1, cond ? cond.min + cond.hist.length - 1 : 0);
  const totB = base.hist.reduce((a, b) => a + b, 0), totC = cond ? cond.hist.reduce((a, b) => a + b, 0) : 1;
  const shareOf = (d, tot, v) => (d && v >= d.min && v < d.min + d.hist.length ? d.hist[v - d.min] / tot : 0);
  let first = lo, last = hi;
  while (first < last && shareOf(base, totB, first) < 0.0005 && shareOf(cond, totC, first) < 0.0005) first++;
  while (last > first && shareOf(base, totB, last) < 0.0005 && shareOf(cond, totC, last) < 0.0005) last--;
  const n = last - first + 1, Wd = 640, H = height, pad = {l: 6, r: 6, t: 10, b: 22};
  const bw = (Wd - pad.l - pad.r) / n;
  let max = 0;
  for (let v = first; v <= last; v++) max = Math.max(max, shareOf(base, totB, v), shareOf(cond, totC, v));
  const y = s => H - pad.b - (H - pad.t - pad.b) * s / (max || 1);
  const x = v => pad.l + (v - first) * bw;
  let bars = '', step = '', hits = '';
  for (let v = first; v <= last; v++) {
    const sc = shareOf(cond, totC, v), sb = shareOf(base, totB, v);
    if (cond) bars += `<rect class="b${line != null && v > line ? ' on' : ''}" x="${(x(v) + 0.6).toFixed(1)}" y="${y(sc).toFixed(1)}" width="${Math.max(0.5, bw - 1.2).toFixed(1)}" height="${(H - pad.b - y(sc)).toFixed(1)}"></rect>`;
    step += `${v === first ? 'M' : 'L'}${x(v).toFixed(1)},${y(sb).toFixed(1)} L${(x(v) + bw).toFixed(1)},${y(sb).toFixed(1)} `;
    hits += `<rect class="hit" data-v="${v}" x="${x(v).toFixed(1)}" y="${pad.t}" width="${bw.toFixed(1)}" height="${H - pad.t - pad.b}"><title>${v}: ${cond ? pct(sc) + ' given · ' : ''}${pct(sb)} all worlds</title></rect>`;
  }
  const tick = Math.max(1, Math.ceil(n / 8 / 5) * 5 || 1);
  let ticks = '';
  for (let v = Math.ceil(first / tick) * tick; v <= last; v += tick) ticks += `<text x="${(x(v) + bw / 2).toFixed(1)}" y="${H - 6}" text-anchor="middle">${v}</text>`;
  const marker = line != null && line >= first - 1 && line <= last + 1
    ? `<line class="t" x1="${(x(line) + bw / 2).toFixed(1)}" x2="${(x(line) + bw / 2).toFixed(1)}" y1="${pad.t - 4}" y2="${H - pad.b}"></line>` : '';
  return `<svg class="hist" viewBox="0 0 ${Wd} ${H}" role="img" aria-label="Conditional distribution against all simulations">
    <line class="ax" x1="${pad.l}" x2="${Wd - pad.r}" y1="${H - pad.b}" y2="${H - pad.b}"></line>${bars}
    <path class="base" d="${step}" fill="none"></path>${marker}${hits}${ticks}</svg>`;
}

/** Bins for an integer variable: up to `max` bins of a round width covering the 2nd–98th percentile. */
export function bins(vals, m = null, max = 7) {
  const xs = [];
  for (let w = 0; w < vals.length; w++) if ((!m || m[w]) && !Number.isNaN(vals[w])) xs.push(vals[w]);
  if (!xs.length) return [];
  xs.sort((a, b) => a - b);
  const lo = xs[Math.floor(0.02 * xs.length)], hi = xs[Math.min(xs.length - 1, Math.floor(0.98 * xs.length))];
  const span = Math.max(1, hi - lo + 1);
  const width = [1, 2, 3, 4, 5, 6, 8, 10, 15, 20, 25].find(s => Math.ceil(span / s) <= max) || Math.ceil(span / max);
  const start = Math.floor(lo / width) * width, out = [];
  for (let a = start; a <= hi; a += width) out.push([a, a + width - 1]);
  out[0][0] = -Infinity;
  out[out.length - 1][1] = Infinity;
  return out;
}
const binLabel = ([a, b], i, all) => (a === -Infinity ? `≤${b}` : b === Infinity ? `${a}+` : a === b ? `${a}` : `${a}–${b}`);

function weightedGridView(x, y, weights, m, {xName, yName}) {
  const bx = gridEdges(x, weights, m), by = gridEdges(y, weights, m);
  if (!bx.length || !by.length) return '<p class="note">Not enough worlds.</p>';
  const {cells, total, columnMass, columnMean} = weightedGrid(x, y, weights, bx, by, m);
  const label = (edges, i) => edges.length === 2 ? 'All' : edges[i] === -Infinity ? `<${edges[i + 1]}`
    : edges[i + 1] === Infinity ? `≥${edges[i]}` : `${edges[i]}–<${edges[i + 1]}`;
  const maxCell = Math.max(1, ...cells.flat());
  const head = `<tr><th class="l">${esc(yName)} ↓ · ${esc(xName)} →</th>${columnMass.map((_, i) => `<th>${esc(label(bx, i))}</th>`).join('')}</tr>`;
  const rows = cells.map((row, j) => `<tr><td class="l">${esc(label(by, j))}</td>${row.map(mass => {
    const s = mass / (total || 1);
    return `<td class="heat${mass / maxCell > 0.55 ? ' hi' : ''}" style="--a:${(mass / maxCell).toFixed(3)}">${mass ? (100 * s < 0.5 ? '<1' : (100 * s).toFixed(0)) + '%' : '–'}</td>`;
  }).join('')}</tr>`).reverse().join('');
  const means = `<tr class="sep"><td class="l">Mean ${esc(yName.toLowerCase())}</td>${columnMean.map(v => `<td>${v == null ? '—' : v.toFixed(1)}</td>`).join('')}</tr>`;
  const shares = `<tr><td class="l dim">Share of probability</td>${columnMass.map(v => `<td class="dim">${pct(v / (total || 1), 0)}</td>`).join('')}</tr>`;
  return `<div class="scroll"><table class="grid"><thead>${head}</thead><tbody>${rows}${means}${shares}</tbody></table></div>`;
}

/** Joint heat grid of two variables over the selected worlds: rows y (high at the top), columns x; each cell the share
 * of worlds; the last row the mean of y given each x band. */
export function grid(x, y, m, {xName, yName}) {
  const bx = bins(x, m), by = bins(y, m).reverse();
  if (!bx.length || !by.length) return '<p class="note">Not enough worlds.</p>';
  const inBin = (v, [a, b]) => v >= a && v <= b;
  let total = 0;
  const cells = by.map(() => bx.map(() => 0)), ysum = bx.map(() => 0), ycnt = bx.map(() => 0);
  for (let w = 0; w < x.length; w++) {
    if ((m && !m[w]) || Number.isNaN(x[w]) || Number.isNaN(y[w])) continue;
    const i = bx.findIndex(b => inBin(x[w], b)), j = by.findIndex(b => inBin(y[w], b));
    if (i < 0 || j < 0) continue;
    cells[j][i]++; total++; ysum[i] += y[w]; ycnt[i]++;
  }
  const maxCell = Math.max(1, ...cells.flat());
  const head = `<tr><th class="l">${esc(yName)} ↓ · ${esc(xName)} →</th>${bx.map((b, i) => `<th>${binLabel(b, i, bx)}</th>`).join('')}</tr>`;
  const rows = by.map((b, j) => `<tr><td class="l">${binLabel(b, j, by)}</td>${bx.map((_, i) => {
    const s = cells[j][i] / (total || 1);
    return `<td class="heat${cells[j][i] / maxCell > 0.55 ? ' hi' : ''}" style="--a:${(cells[j][i] / maxCell).toFixed(3)}">${cells[j][i] ? (100 * s < 0.5 ? '<1' : (100 * s).toFixed(0)) + '%' : '–'}</td>`;
  }).join('')}</tr>`).join('');
  const means = `<tr class="sep"><td class="l">Mean ${esc(yName.toLowerCase())}</td>${bx.map((_, i) => `<td>${ycnt[i] ? (ysum[i] / ycnt[i]).toFixed(1) : '—'}</td>`).join('')}</tr>`;
  const shares = `<tr><td class="l dim">Share of worlds</td>${bx.map((_, i) => `<td class="dim">${pct(ycnt[i] / (total || 1), 0)}</td>`).join('')}</tr>`;
  return `<div class="scroll"><table class="grid"><thead>${head}</thead><tbody>${rows}${means}${shares}</tbody></table></div>`;
}

/** Subject options for a condition builder: the game, both teams, then each team's players (projected minutes order). */
export function subjectOptions(data, selected) {
  const sim = data.projection.sim, g = data.game;
  const opt = (v, t) => `<option value="${esc(v)}"${v === selected ? ' selected' : ''}>${esc(t)}</option>`;
  const players = side => sim[side].players.filter(p => p.periods).slice().sort((a, b) => b.periods.fg.sec - a.periods.fg.sec);
  return `<optgroup label="Game">${opt('g', 'Game')}</optgroup><optgroup label="Teams">${opt('t:away', team(g.away.id).abbr)}${opt('t:home', team(g.home.id).abbr)}</optgroup>`
    + ['away', 'home'].map(side => `<optgroup label="${esc(team(g[side].id).abbr)} players">${players(side).map(p => opt('p:' + p.id, p.name)).join('')}</optgroup>`).join('');
}
// Grouped "what" options (owner: grouping in dropdowns); every variable belongs to one group
const VAR_GROUPS = {
  p: [['Availability and participation', ['available', 'unavailable', 'plays', 'sits', 'min']], ['Scoring', ['pts', 'fgm', 'fg3m', 'ftm', 'fgpct']], ['Rebounding', ['reb', 'oreb', 'dreb']],
      ['Handling', ['ast', 'tov']], ['Defense', ['stl', 'blk']]],
  t: [['Result', ['win', 'lose', 'margin']], ['Points', ['pts', 'h1', 'h2', 'q1', 'q2', 'q3', 'q4']],
      ['Periods won', ['wq1', 'wq2', 'wq3', 'wq4', 'wh1', 'wh2', 'qwins', 'sweep']],
      ['Leads', ['q1m', 'h1m', 'q3m', 'q4m', 'lead1', 'leadh', 'lead3']], ['Flow', ['comeback', 'blown', 'wire']]],
  g: [['Totals', ['total', 'th1', 'th2', 't1', 't4']], ['Margin & flow', ['absm', 'close3', 'changes', 'flip']], ['Overtime', ['ot', 'not']]],
};
export function varOptions(subj, selected, Wd) {
  const kind = subj.startsWith('p:') ? 'p' : subj.startsWith('t:') ? 't' : 'g';
  const vars = new Map((kind === 'p' ? PLAYER_VARS.filter(([k]) =>
    !['oreb', 'dreb', 'available', 'unavailable'].includes(k)
      || (['available', 'unavailable'].includes(k) ? Boolean(Wd.weights) : Wd.stats.includes(k))) : kind === 't' ? TEAM_VARS : GAME_VARS));
  const opt = k => `<option value="${k}"${k === selected ? ' selected' : ''}>${esc(vars.get(k))}</option>`;
  return VAR_GROUPS[kind].map(([label, ks]) => { const o = ks.filter(k => vars.has(k)).map(opt).join(''); return o ? `<optgroup label="${esc(label)}">${o}</optgroup>` : ''; }).join('');
}
