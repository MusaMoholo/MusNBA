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
export function forecastTiming(kind, preTip, completedAt) {
  if (kind === 'retrospective') return 'Retrospective';
  if (kind !== 'prospective' || !completedAt) return 'Timing unverified';
  if (preTip === true) return 'Pre-game';
  if (preTip === false) return 'Built after tip-off';
  return 'Timing unverified';
}

// ------------------------------------------------------------------ numbers
const ok = v => typeof v === 'number' && Number.isFinite(v);
export const f1 = v => ok(v) ? v.toFixed(1) : '—';
export const f0 = v => ok(v) ? Math.round(v).toString() : '—';
export const signed = (v, d = 1) => {
  if (!ok(v)) return '—';
  const value = Math.abs(v).toFixed(d);
  return (Number(value) === 0 ? '±' : v > 0 ? '+' : '−') + value;
};
export const rate = (v, d = 1) => ok(v) ? (100 * v).toFixed(d) + '%' : '—';
export function advancedRates(line) {
  const calc = (keys, numerator, denominator) => {
    if (!line || keys.some(k => !Number.isFinite(line[k]))) return null;
    const den = denominator(line);
    return den > 0 ? numerator(line) / den : null;
  };
  return {
    efg: calc(['fgm', 'fg3m', 'fga'], x => x.fgm + 0.5 * x.fg3m, x => x.fga),
    ts: calc(['pts', 'fga', 'fta'], x => x.pts, x => 2 * (x.fga + 0.44 * x.fta)),
    two: calc(['fgm', 'fg3m', 'fga', 'fg3a'], x => x.fgm - x.fg3m, x => x.fga - x.fg3a),
    threeShare: calc(['fg3a', 'fga'], x => x.fg3a, x => x.fga),
    ftRate: calc(['fta', 'fga'], x => x.fta, x => x.fga),
    astTov: calc(['ast', 'tov'], x => x.ast, x => x.tov),
  };
}
export function teamAdvancedRates(line, opponent) {
  const poss = x => x && ['fga', 'oreb', 'tov', 'fta'].every(k => Number.isFinite(x[k]))
    ? x.fga - x.oreb + x.tov + 0.44 * x.fta : null;
  const ratio = (a, b) => Number.isFinite(a) && Number.isFinite(b) && b > 0 ? a / b : null;
  const sum = (a, b) => Number.isFinite(a) && Number.isFinite(b) ? a + b : null;
  const ownPoss = poss(line), oppPoss = poss(opponent);
  const offense = ratio(line?.pts, ownPoss), defense = ratio(opponent?.pts, oppPoss);
  return {
    poss: ownPoss,
    ortg: offense == null ? null : 100 * offense,
    drtg: defense == null ? null : 100 * defense,
    net: offense == null || defense == null ? null : 100 * (offense - defense),
    oreb: ratio(line?.oreb, sum(line?.oreb, opponent?.dreb)),
    dreb: ratio(line?.dreb, sum(line?.dreb, opponent?.oreb)),
    assist: ratio(line?.ast, line?.fgm),
    turnover: ratio(line?.tov, ownPoss),
    steals: ratio(line?.stl, oppPoss),
  };
}
export function advancedPanel(line, actual, label, options = {}) {
  if (!line && !actual) return '';
  const values = advancedRates(line), observed = advancedRates(actual);
  const metrics = [['efg', 'Effective FG%', '(FGM + 0.5 × 3PM) / FGA', true],
                   ['ts', 'True shooting%', 'PTS / (2 × (FGA + 0.44 × FTA))', true],
                   ['two', '2-point FG%', '(FGM − 3PM) / (FGA − 3PA)', true],
                   ['threeShare', '3-point attempt rate', '3PA / FGA', true],
                   ['ftRate', 'Free-throw attempt rate', 'FTA / FGA', true],
                   ['astTov', 'Assists per turnover', 'AST / TOV', false]];
  if (options.team) {
    Object.assign(values, teamAdvancedRates(line, options.opponent));
    Object.assign(observed, teamAdvancedRates(actual, options.actualOpponent));
    metrics.push(['poss', 'Estimated possessions', 'FGA − OREB + TOV + 0.44 × FTA', false],
                 ['ortg', 'Offensive rating · estimate', 'PTS / estimated possessions × 100', false],
                 ['drtg', 'Defensive rating · estimate', 'Opponent PTS / their estimated possessions × 100', false],
                 ['net', 'Net rating · estimate', 'Offensive rating − defensive rating', false],
                 ['oreb', 'Offensive rebound share', 'OREB / (OREB + opponent DREB)', true],
                 ['dreb', 'Defensive rebound share', 'DREB / (DREB + opponent OREB)', true],
                 ['assist', 'Assisted field goals', 'AST / FGM', true],
                 ['turnover', 'Turnover rate · estimate', 'TOV / estimated possessions', true],
                 ['steals', 'Steal rate · estimate', 'STL / opponent estimated possessions', true]);
  }
  const format = (v, percent) => percent ? rate(v) : f1(v);
  const element = options.collapsible ? 'details' : 'section';
  const title = esc(options.title || 'Advanced box-score rates');
  return `<${element} class="panel">${options.collapsible ? `<summary><b>${title}</b> · ${metrics.length} metrics</summary>` : `<h3>${title}</h3>`}<div class="advanced-grid">
    ${metrics.map(([key, title, formula, percent]) => `<div class="tile"><span>${esc(title)}</span>
      <div class="lines">${line ? `<em>${esc(label)}</em><b>${format(values[key], percent)}</b>` : ''}
      ${actual ? `<em>Actual</em><b>${format(observed[key], percent)}</b>` : ''}</div><small>${esc(formula)}</small></div>`).join('')}</div>
    <p class="note">${line && actual ? 'Projected values are ratios of simulated mean totals, not means of the individual-game rates. '
      : line && label === 'Projected' ? 'Ratios of simulated mean totals, not means of the individual-game rates. ' : ''}
      True shooting uses the conventional 0.44 free-throw approximation.
      ${options.team ? 'Possessions and ratings are box-score estimates, not counted possessions; player totals can exclude team rebounds and turnovers. ' : ''}
      — means missing data or a zero denominator.</p></${element}>`;
}
export function usageProfilePanel(profile) {
  if (!profile) return '';
  return `<section class="panel"><h3>Offensive action share · latest model profile</h3>
    <p><b>${rate(profile.rate)}</b> · through ${esc(dayLabel(profile.through))}</p>
    <p class="note">Estimated share of offensive segments on court ending with this player's non-heave shot, turnover,
    shooting foul or free-throw foul. The model combines decayed history with a prior
    (${f1(profile.off_segments_eff)} effective offensive segments). This latest profile is not conventional
    possession-based USG% or a game forecast; it may differ from the forecast's saved inputs.</p></section>`;
}
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
export function statusTag(status, availability, basis) {
  const raw = (status || '').trim();
  const s = (raw || 'Unknown').toLowerCase();
  const uncertain = ok(availability) && availability > 0 && availability < 1;
  if ((s === 'active' && !uncertain) || s.startsWith('unknown (retrospective)')) return '';
  const cls = s === 'out' || s.startsWith('susp') ? 'status-out' : 'status-q';
  const label = s === 'active' && uncertain ? 'Recent inactivity' :
    ({'day-to-day': 'DTD', questionable: 'Q', doubtful: 'D', probable: 'P', out: 'OUT'}[s] || raw || 'Unknown');
  const known = ['active', 'probable', 'day-to-day', 'questionable', 'doubtful', 'out', 'suspension', 'suspended', 'injured reserve'];
  const fallback = s === 'unknown' || s === 'active' || basis === 'unknown_status' || basis === 'recent_inactivity'
    || (!basis && !known.includes(s));
  const extra = uncertain ? ` · ${fallback ? 'fallback' : 'assumed available'} ${Math.round(availability * 100)}%` : '';
  const title = uncertain || s === 'unknown'
    ? `${raw || 'Unknown'} — uncalibrated ${fallback ? 'fallback' : 'status assumption'}` : raw;
  return `<span class="tag ${cls}" title="${esc(title)}">${esc(label)}${extra}</span>`;
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
    ? `<a href="#/about" class="pill good" title="${esc(model.label)} · About the model">Engine ${esc(model.version || 'v1')}</a>`
    : `<a href="#/about" class="pill accent" title="${esc(model ? model.label : '')} · About the model">Placeholder model</a>`;
}

// Shared Standings sections: all season insights stay within one destination.
export const standingsTabs = [['forecast', 'Forecast'], ['seeds', 'Seeds'], ['wins', 'Wins'], ['ratings', 'Ratings'], ['picture', 'Playoff picture'], ['races', 'Races'], ['movers', 'Movers'], ['leaders', 'Leaders']];

export const standingsNav = active => segGroups([['Standings', standingsTabs.slice(0, 5)], ['Season insights', standingsTabs.slice(5)]], active, 'data-view');
