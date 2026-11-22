// Spotlight (owner, 20 Nov): the headliner, breakout watch, the six stat leaders and games to watch — for a slate (Today) or
// one game (Game Centre). Read from views (`spotlight`, `watch`: stored projections, worlds and season averages); nothing is
// computed here.
import {esc, f1, logo, pct, team, tipTimes} from './ui.mjs';

const STATS = [['pts', 'Points', 'PTS'], ['reb', 'Rebounds', 'REB'], ['ast', 'Assists', 'AST'], ['fg3m', 'Threes', '3PM'],
               ['stl', 'Steals', 'STL'], ['blk', 'Blocks', 'BLK']];
const sheet = p => `#/game/${p.game_id}/player/${p.id}`;
const who = (p, slate) => `${logo(p.team, 'sm')} ${esc(team(p.team).abbr)} ${p.home ? 'vs' : '@'} ${esc(team(p.opp).abbr)}${slate ? ` · ${esc(tipTimes(p.tip_utc, null).uk)} UK` : ''}`;
const signed = v => (v > 0.05 ? '+' : v < -0.05 ? '−' : '±') + Math.abs(v).toFixed(1);
const short = n => { const w = String(n || '').split(' '); return w.length > 1 ? `${w[0][0]}. ${w.slice(1).join(' ')}` : n; };

/** Small bar sparkline of a stored {min, hist} distribution (points), the mean marked. */
function spark(d, mean) {
  if (!d?.hist?.length) return '';
  const n = d.hist.length, max = Math.max(...d.hist), W = 150, H = 34, bw = W / n;
  const bars = d.hist.map((c, i) => `<rect x="${(i * bw).toFixed(1)}" y="${(H - 2 - (H - 6) * c / max).toFixed(1)}" width="${Math.max(0.6, bw - 0.6).toFixed(1)}" height="${((H - 6) * c / max).toFixed(1)}"></rect>`).join('');
  const mx = ((mean - d.min + 0.5) * bw).toFixed(1);
  return `<svg class="spark" viewBox="0 0 ${W} ${H + 10}" role="img" aria-label="Points distribution">${bars}<line x1="${mx}" x2="${mx}" y1="0" y2="${H}"></line>
    <text x="0" y="${H + 9}" class="lo">${d.min}</text><text x="${mx}" y="${H + 9}" text-anchor="middle">avg ${mean.toFixed(1)}</text><text x="${W}" y="${H + 9}" class="hi" text-anchor="end">${d.min + n - 1} pts</text></svg>`;
}

function headliner(h, slate) {
  const c = h.chances || {};
  const chance = (label, p) => (p == null ? '' : `<span><b>${pct(p, p < 0.1 ? 1 : 0)}</b> ${label}</span>`);
  // layout (owner, 20 Nov: consistent at every width): identity | sparkline + chances on top, then the six stats as one
  // fixed row of six (three-by-two on a phone) — never a ragged wrap
  return `<a class="spot wide head" href="${sheet(h)}">
    <div class="spot-id"><span class="spot-kicker">${slate ? 'Headliner of the night' : 'Headliner'}</span><b class="spot-name">${esc(h.name)}</b>
      <span class="spot-meta">${who(h, slate)}</span><span class="spot-meta">Top projected all-round line · ${f1(h.fp)} fantasy pts${h.played < 0.98 ? ` · plays ${Math.round(100 * h.played)}%` : ''}</span></div>
    <div class="spot-side">${spark(h.spark, h.mean.pts)}<div class="spot-chance">${chance('30+ pts', c.pts30)}${chance('40+ pts', c.pts40)}${chance('double-double', c.dd)}${chance('triple-double', c.td)}</div></div>
    <div class="spot-chips">${STATS.map(([k, , l]) => `<span><b>${f1(h.mean[k])}</b>${l}</span>`).join('')}</div></a>`;
}

/** Dumbbell rows: his season average (grey dot) → tonight's projection (accent dot) on each stat's own track. */
function breakout(b, slate) {
  if (!b) return '';
  const rows = [['pts', 'PTS'], ['reb', 'REB'], ['ast', 'AST'], ['fg3m', '3PM'], ['min', 'MIN']];
  const dumb = rows.map(([k, l]) => {
    const t = b.mean[k] || 0, s = b.season[k] || 0, top = Math.max(t, s, 0.5) * 1.12;
    const xs = 100 * s / top, xt = 100 * t / top, d = t - s;
    return `<div class="db-row"><span class="db-l">${l}</span><span class="db-track"><i class="db-line" style="left:${Math.min(xs, xt).toFixed(1)}%;width:${Math.abs(xt - xs).toFixed(1)}%"></i>
        <i class="db-s" style="left:${xs.toFixed(1)}%"></i><i class="db-t" style="left:${xt.toFixed(1)}%"></i></span>
      <span class="db-v">${f1(s)} → <b>${f1(t)}</b> <em class="${d > 0.05 ? 'up' : d < -0.05 ? 'down' : ''}">${signed(d)}</em></span></div>`;
  }).join('');
  return `<a class="spot wide" href="${sheet(b)}">
    <div class="spot-id"><span class="spot-kicker">Breakout watch</span><b class="spot-name">${esc(b.name)}</b><span class="spot-meta">${who(b, slate)}</span>
      <span class="spot-meta">${f1(b.fp)} fantasy pts tonight v ${f1(b.fp_season)} on the season (${b.gp} games)</span>
      ${b.why ? `<span class="spot-why">Why: ${esc(b.why)}</span>` : ''}</div>
    <div class="spot-dumb" aria-label="His season average against tonight's projection">${dumb}<p class="db-key"><i class="db-s"></i> season <i class="db-t"></i> tonight</p></div></a>`;
}

function leaderCards(L, scope) {
  return STATS.map(([k, label]) => {
    const [first, ...rest] = L[k] || [];
    if (!first) return '';
    const lead = p => (p.lead == null ? '' : `<small class="ld-p" title="Chance he leads the ${scope} in ${label.toLowerCase()} (paired simulations)">${pct(p.lead, 0)}</small>`);
    return `<div class="spot lead"><span class="spot-kicker">${label}</span>
      <a class="ld-top" href="${sheet(first)}" title="${esc(first.name)}">${logo(first.team, 'sm')}<b class="spot-name">${esc(short(first.name))}</b><b class="ld-v">${f1(first.value)}</b></a>
      ${first.lead != null ? `<small class="ld-lead">Leads the ${scope} ${pct(first.lead, 0)}</small>` : ''}
      ${rest.map((p, i) => `<a class="ld-row" href="${sheet(p)}" title="${esc(p.name)}"><span class="dim">${i + 2}</span>${logo(p.team, 'sm')}<span class="ld-n">${esc(short(p.name))}</span>${lead(p)}<b>${f1(p.value)}</b></a>`).join('')}</div>`;
  }).join('');
}

/** Games to watch (Today): closest finish, highest-scoring game, likeliest overtime. */
function watchStrip(w) {
  if (!w) return '';
  const g = (label, x, value) => `<a class="watch" href="#/game/${x.game_id}"><span class="spot-kicker">${label}</span>
    <span class="watch-teams">${logo(x.away, 'sm')} ${esc(team(x.away).abbr)} @ ${esc(team(x.home).abbr)} ${logo(x.home, 'sm')}</span><b>${value}</b></a>`;
  return `<div class="watch-strip">${g('Closest finish', w.closest, `${pct(w.closest.close, 0)} within 5`)}${g('Highest-scoring', w.shootout, `${f1(w.shootout.total)} total`)}${g('Likeliest overtime', w.overtime, `${pct(w.overtime.ot, 1)} OT`)}</div>`;
}

/** U3: role changes tonight — players ≥ 4 projected minutes off their season average, with the minutes model's reason. */
function roleStrip(roles) {
  if (!roles?.length) return '';
  return `<section class="spot roles"><span class="spot-kicker">Role changes tonight</span><div class="role-list">${roles.map(r =>
    `<a class="role" href="${sheet(r)}">${logo(r.team, 'sm')}<b>${esc(short(r.name))}</b><em class="${r.delta > 0 ? 'up' : 'down'}">${r.delta > 0 ? '▲' : '▼'} ${signed(r.delta)} min</em>
      <small>${f1(r.season)} → ${f1(r.proj)} · ${esc(r.why)}</small></a>`).join('')}</div></section>`;
}

/** The slate's spotlight for Today. */
export function slateSpotlight(s, watch, roles) {
  if (!s) return '';
  return `<div class="spot-pair">${headliner(s.headliner, true)}${breakout(s.breakout, true)}</div>${watchStrip(watch)}<div class="spot-leaders compact">${leaderCards(s.leaders, 'night')}</div>${roleStrip(roles)}`;
}

/** One game's spotlight for the Game Centre (projected games). */
export function gameSpotlight(s) {
  if (!s) return '';
  return `<section class="panel spot-panel"><h3 style="margin-top:0">Spotlight</h3><div class="spot-pair">${headliner(s.headliner, false)}${breakout(s.breakout, false)}</div>
    <div class="spot-leaders compact">${leaderCards(s.leaders, 'game')}</div></section>`;
}
