// Shared data access, formatters, small components and SVG charts. No framework, no build step.
export const BASE = new URL('./', location.href);
const TZ_UK = 'Europe/London', TZ_ET = 'America/New_York';

export const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));

// ------------------------------------------------------------------ data
const cache = new Map();
export function api(path) {
  if (cache.has(path)) return cache.get(path);
  const promise = fetch(new URL('api/' + path, BASE)).then(async response => {
    const value = await response.json().catch(() => ({error: 'Unreadable response'}));
    if (!response.ok) throw Object.assign(new Error(value.error || response.statusText), {status: response.status});
    return value;
  });
  cache.set(path, promise);
  promise.catch(() => cache.delete(path));
  return promise;
}

let META = null;
export const setMeta = meta => { META = meta; };
export const meta = () => META;
export const team = id => META?.teams?.[id] || {id, abbr: '?', name: 'Unknown team', short: '?'};

// ------------------------------------------------------------------ storage (per-device conveniences only)
export const store = {
  get(key, fallback = null) { try { const v = localStorage.getItem('musnba:' + key); return v == null ? fallback : JSON.parse(v); } catch { return fallback; } },
  set(key, value) { try { localStorage.setItem('musnba:' + key, JSON.stringify(value)); } catch { /* storage blocked: keep going */ } },
};

// ------------------------------------------------------------------ time
const ymd = (date, timeZone) => new Intl.DateTimeFormat('en-CA', {timeZone, year: 'numeric', month: '2-digit', day: '2-digit'}).format(date);
export const etToday = () => ymd(new Date(), TZ_ET);
export const dayLabel = (day, options = {weekday: 'short', day: 'numeric', month: 'short'}) =>
  new Intl.DateTimeFormat('en-GB', {...options, timeZone: 'UTC'}).format(new Date(day + 'T12:00:00Z'));
export const longDay = day => dayLabel(day, {weekday: 'long', day: 'numeric', month: 'long'});
export function tipTimes(tipUtc, slateDay, valid = true) {
  if (!valid) return {uk: 'TBD', et: '', label: 'Time TBD'};
  const date = new Date(tipUtc);
  const uk = new Intl.DateTimeFormat('en-GB', {timeZone: TZ_UK, hour: '2-digit', minute: '2-digit'}).format(date);
  const et = new Intl.DateTimeFormat('en-US', {timeZone: TZ_ET, hour: 'numeric', minute: '2-digit'}).format(date) + ' ET';
  const ukDay = ymd(date, TZ_UK) !== slateDay
    ? new Intl.DateTimeFormat('en-GB', {timeZone: TZ_UK, weekday: 'short'}).format(date) + ' ' : '';
  return {uk: ukDay + uk, et, label: `${ukDay}${uk} UK · ${et}`};
}
export function stamp(utc) {
  if (!utc) return '—';
  return new Intl.DateTimeFormat('en-GB', {timeZone: TZ_UK, weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'}).format(new Date(utc)) + ' UK';
}

// ------------------------------------------------------------------ numbers
const ok = v => typeof v === 'number' && Number.isFinite(v);
export const f1 = v => ok(v) ? v.toFixed(1) : '—';
export const f0 = v => ok(v) ? Math.round(v).toString() : '—';
export const signed = (v, d = 1) => ok(v) ? (v > 0 ? '+' : v < 0 ? '−' : '±') + Math.abs(v).toFixed(d) : '—';
export const rate = (v, d = 1) => ok(v) ? (100 * v).toFixed(d) + '%' : '—';
export function pct(p, d = 1) {
  if (!ok(p)) return '—';
  if (p <= 0) return '0%';
  if (p >= 1) return '100%';
  if (p < 0.001) return '<0.1%';
  if (p > 0.999) return '>99.9%';
  return (100 * p).toFixed(d) + '%';
}
export const ordinal = n => {
  const s = ['th', 'st', 'nd', 'rd'], v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
};
export const record = r => Array.isArray(r) ? `${r[0]}-${r[1]}` : '—';
export const per = (total, n, d = 1) => n ? (total / n).toFixed(d) : '—';
export const share = (a, b) => b ? a / b : null;

// ------------------------------------------------------------------ theme and logos
export function effectiveTheme() {
  const set = document.documentElement.dataset.theme;
  if (set) return set;
  return matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}
export const logoUrl = id => new URL(`logos/${id}${effectiveTheme() === 'dark' ? '-dark' : ''}.png`, BASE).href;
export const logo = (id, cls = '') =>
  `<img class="logo ${cls}" data-team="${esc(id)}" src="${logoUrl(id)}" alt="" width="28" height="28" loading="lazy" decoding="async">`;
export function refreshLogos(root = document) {
  for (const img of root.querySelectorAll('img.logo[data-team]')) img.src = logoUrl(img.dataset.team);
}
export const teamLink = (id, {short = false, cls = 'sm'} = {}) => {
  const t = team(id);
  return `<a class="teamcell" href="#/team/${esc(id)}" title="${esc(t.name)}">${logo(id, cls)}<span>${esc(short ? t.abbr : t.short || t.name)}</span></a>`;
};

// ------------------------------------------------------------------ status
export function statusTag(status, availability) {
  const s = (status || '').toLowerCase();
  if (!s || s === 'active' || s.startsWith('unknown')) return '';
  const cls = s === 'out' || s.startsWith('susp') ? 'status-out' : 'status-q';
  const label = {'day-to-day': 'DTD', questionable: 'Q', doubtful: 'D', probable: 'P', out: 'OUT'}[s] || status;
  const extra = ok(availability) && availability > 0 && availability < 1 ? ` · plays ${Math.round(availability * 100)}%` : '';
  return `<span class="tag ${cls}" title="${esc(status)}">${esc(label)}${extra}</span>`;
}

// ------------------------------------------------------------------ probability cells
export function heat(p, {digits = 0, title = ''} = {}) {
  if (!ok(p)) return '<td class="heat z">—</td>';
  if (p <= 0) return `<td class="heat z"${title ? ` title="${esc(title)}"` : ''}>–</td>`;
  const label = p < 0.005 ? '<1%' : p > 0.995 && p < 1 ? '>99%' : (100 * p).toFixed(digits) + '%';
  return `<td class="heat${p >= 0.55 ? ' hi' : ''}" style="--a:${Math.min(1, p).toFixed(3)}"${title ? ` title="${esc(title)}"` : ''}>${label}</td>`;
}

// ------------------------------------------------------------------ distributions
export const histTotal = d => d.hist.reduce((a, b) => a + b, 0);
export function probWhere(d, test) {
  let n = 0, total = 0;
  d.hist.forEach((c, i) => { total += c; if (test(d.min + i)) n += c; });
  return total ? n / total : null;
}
export const over = (d, line) => probWhere(d, v => v > line);
export const atLeast = (d, k) => probWhere(d, v => v >= k);
export const percentileOf = (d, v) => {
  const below = probWhere(d, x => x < v), equal = probWhere(d, x => x === v);
  return below + equal / 2;
};
/** Over/under lines are always x.5 (owner, 20 Nov: no pushes): the x.5 at or above-and-nearest a value, so a typed 4
 * becomes 4.5 — the same "over" chance, since over means strictly more. */
export const halfLine = v => Math.floor(v) + 0.5;
export const defaultLine = d => halfLine(Math.max(0.5, d.q[2] - 0.5));

/** Histogram of integer outcomes. Bars right of `line` are highlighted; `side` colours by sign. */
export function histogram(d, {line = null, actual = null, side = false, height = 170, label = v => v} = {}) {
  const total = histTotal(d);
  let lo = 0, hi = d.hist.length - 1;
  while (lo < hi && d.hist[lo] < total * 0.0004) lo++;
  while (hi > lo && d.hist[hi] < total * 0.0004) hi--;
  const values = d.hist.slice(lo, hi + 1), first = d.min + lo, n = values.length;
  const W = 640, H = height, pad = {l: 6, r: 6, t: 10, b: 22};
  const bw = (W - pad.l - pad.r) / n, max = Math.max(...values, 1);
  const x = v => pad.l + (v - first) * bw;
  let bars = '', hits = '';
  values.forEach((c, i) => {
    const v = first + i, h = (H - pad.t - pad.b) * c / max;
    const cls = side ? (v < 0 ? 'away' : v > 0 ? 'home' : '') : (line != null && v > line ? 'on' : '');
    bars += `<rect class="b ${cls}" x="${(x(v) + 0.6).toFixed(1)}" y="${(H - pad.b - h).toFixed(1)}" width="${Math.max(0.5, bw - 1.2).toFixed(1)}" height="${h.toFixed(1)}"></rect>`;
    hits += `<rect class="hit" data-v="${v}" x="${x(v).toFixed(1)}" y="${pad.t}" width="${bw.toFixed(1)}" height="${H - pad.t - pad.b}"><title>${esc(label(v))}: ${pct(c / total)}</title></rect>`;
  });
  const step = Math.max(1, Math.ceil(n / 8 / 5) * 5 || 1);
  let ticks = '';
  for (let v = Math.ceil(first / step) * step; v <= first + n - 1; v += step)
    ticks += `<text x="${(x(v) + bw / 2).toFixed(1)}" y="${H - 6}" text-anchor="middle">${esc(label(v))}</text>`;
  const marker = line != null && line >= first - 1 && line <= first + n
    ? `<line class="t" x1="${(x(line) + bw / 2).toFixed(1)}" x2="${(x(line) + bw / 2).toFixed(1)}" y1="${pad.t - 4}" y2="${H - pad.b}"></line>` : '';
  const act = actual != null && actual >= first && actual <= first + n - 1
    ? `<line class="t" style="stroke:var(--good);stroke-dasharray:none;stroke-width:2.5" x1="${(x(actual) + bw / 2).toFixed(1)}" x2="${(x(actual) + bw / 2).toFixed(1)}" y1="${pad.t - 4}" y2="${H - pad.b}"><title>Actual ${esc(label(actual))}</title></line>` : '';
  return `<svg class="hist" viewBox="0 0 ${W} ${H}" role="img" aria-label="Distribution of simulated outcomes"><line class="ax" x1="${pad.l}" x2="${W - pad.r}" y1="${H - pad.b}" y2="${H - pad.b}"></line>${bars}${marker}${act}${hits}${ticks}</svg>`;
}

/** Simple per-game bar chart; values are integers, null means did not play. */
export function barChart(items, {height = 140} = {}) {
  const W = 640, H = height, pad = {l: 22, r: 6, t: 10, b: 20};
  const n = Math.max(1, items.length), bw = (W - pad.l - pad.r) / n;
  const max = Math.max(5, ...items.map(i => i.v ?? 0));
  const y = v => H - pad.b - (H - pad.t - pad.b) * v / max;
  let out = '';
  items.forEach((item, i) => {
    const x = pad.l + i * bw;
    if (item.v == null) out += `<rect class="dnp" x="${(x + 1).toFixed(1)}" y="${H - pad.b - 3}" width="${(bw - 2).toFixed(1)}" height="3"><title>${esc(item.title)}</title></rect>`;
    else out += `<rect x="${(x + 1).toFixed(1)}" y="${y(item.v).toFixed(1)}" width="${Math.max(1, bw - 2).toFixed(1)}" height="${(H - pad.b - y(item.v)).toFixed(1)}"><title>${esc(item.title)}</title></rect>`;
    if (n <= 20 || i % 2 === 0) out += `<text x="${(x + bw / 2).toFixed(1)}" y="${H - 6}" text-anchor="middle">${esc(item.label)}</text>`;
  });
  const grid = [0, Math.round(max / 2), max].map(v => `<line x1="${pad.l}" x2="${W - pad.r}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"></line><text x="2" y="${(y(v) + 3).toFixed(1)}">${v}</text>`).join('');
  return `<svg class="bars" viewBox="0 0 ${W} ${H}" role="img" aria-label="Per-game values">${grid}${out}</svg>`;
}

// ------------------------------------------------------------------ misc
export const normalise = s => String(s || '').normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase().trim();
/** Grouped segmented controls: [[label, [[value, text], …]], …] — one labelled group per row unit (owner: stacking/grouping). */
export const segGroups = (groups, active, attr = 'data-v') => `<div class="seg-groups">${groups.filter(([, items]) => items.length)
  .map(([label, items]) => `<div class="seg-group" style="--n:${items.length}"><span class="seg-label">${esc(label)}</span>${seg(items, active, attr)}</div>`).join('')}</div>`;
export const seg = (items, active, attr = 'data-v') =>
  `<div class="seg" role="group">${items.map(([v, label]) => `<button type="button" ${attr}="${esc(v)}" aria-pressed="${v === active}">${esc(label)}</button>`).join('')}</div>`;
export function errorPanel(error) {
  const missing = error?.status === 404;
  return `<section class="panel"><h2>${missing ? 'Not available' : 'Something went wrong'}</h2><p class="note">${esc(error?.message || error)}</p>${missing ? '<p class="note">This view is built by the nightly pipeline on the laptop.</p>' : ''}<p><a class="btn ghost" href="#/">Back to today</a></p></section>`;
}

// Model chip: the possession engine (default, D22) or the placeholder (backfills); full label in the tooltip.
export function modelPill(model) {
  return model && (model.kind === 'engine' || model.kind === 'preview')
    ? `<span class="pill good" title="${esc(model.label)}">Engine ${esc(model.version || 'v1')}</span>`
    : `<span class="pill accent" title="${esc(model ? model.label : '')}">Placeholder model</span>`;
}
