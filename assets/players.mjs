// Players: sortable league table (per game / totals / per 36) and player pages with game logs.
import {playerFace, playerLabel, advancedPanel, api, barChart, dayLabel, esc, f1, logo, normalise, pct, seg, signed, statusTag, store, team, teamLink, tipTimes, usageProfilePanel} from './ui.mjs';

const COLS = [['gp', 'GP'], ['min', 'MIN'], ['pts', 'PTS'], ['trend', 'L10 trend'], ['reb', 'REB'], ['ast', 'AST'], ['stl', 'STL'], ['blk', 'BLK'], ['tov', 'TOV'],
              ['fg3m', '3PM'], ['fg_pct', 'FG%'], ['fg3_pct', '3P%'], ['ft_pct', 'FT%'], ['ts_pct', 'TS%'], ['pm', '+/−']];
const state = {mode: store.get('players-mode', 'pg'), sort: {key: 'pts', dir: -1}, q: '', team: '', minMinutesShare: 0.1, limit: 60};

export function minutesBenchmark(standings) {
  if (!standings.teams.length || standings.teams.some(t => !Number.isInteger(t.gp) || t.gp < 0))
    throw new Error('Season team games are unavailable for the minutes filter.');
  return 48 * Math.max(...standings.teams.map(t => t.gp));
}

export function qualifiesMinutes(player, share, benchmark) {
  return player.gp > 0 && (!share || (benchmark > 0 && Number.isFinite(player.tot.min) && player.tot.min >= share * benchmark));
}

export async function render(view, ctx) {
  if (ctx.name === 'player') return playerPage(view, ctx);
  return table(view, ctx);
}

function value(p, key, mode) {
  const t = p.tot, gp = p.gp;
  if (!gp) return null;
  if (key === 'gp') return gp;
  if (key === 'trend') return p.l10 ? p.l10.pts - t.pts / gp : null;  // U13: last-10 points per game minus the season's
  if (key === 'fg_pct') return t.fga ? t.fgm / t.fga : null;
  if (key === 'fg3_pct') return t.fg3a ? t.fg3m / t.fg3a : null;
  if (key === 'ft_pct') return t.fta ? t.ftm / t.fta : null;
  if (key === 'ts_pct') return (t.fga + 0.44 * t.fta) ? t.pts / (2 * (t.fga + 0.44 * t.fta)) : null;
  const v = t[key] ?? 0;
  if (mode === 'tot') return v;
  if (mode === 'p36') return key === 'min' ? v / gp : t.min ? 36 * v / t.min : null;
  return v / gp;
}
// U13: sparkline of the last 10 points totals + the last-10 v season change
const sparkCell = p => {
  if (!p.spark?.length) return '—';
  const m = Math.max(...p.spark, 1), W = 60, H = 18, bw = W / p.spark.length;
  const d = p.l10.pts - p.tot.pts / p.gp;
  return `<svg class="mini" viewBox="0 0 ${W} ${H}" aria-hidden="true">${p.spark.map((v, i) => `<rect x="${(i * bw).toFixed(1)}" y="${(H - H * v / m).toFixed(1)}" width="${Math.max(1, bw - 1).toFixed(1)}" height="${(H * v / m).toFixed(1)}"></rect>`).join('')}</svg>
    <em class="${d > 0.5 ? 'up' : d < -0.5 ? 'down' : 'dim'}">${d > 0 ? '+' : ''}${d.toFixed(1)}</em>`;
};
const fmt = (key, v, mode) => v == null ? '—' : /_pct$/.test(key) ? (100 * v).toFixed(1) : key === 'gp' ? v : key === 'pm' ? signed(v, mode === 'tot' ? 0 : 1) : mode === 'tot' ? Math.round(v) : v.toFixed(1);

async function table(view, {meta, current}) {
  const [data, standings] = await Promise.all([api('players'), api('standings/' + encodeURIComponent(meta.latest))]);
  if (!current()) return;
  if (data.date !== standings.date) throw new Error('Player and team season cutoffs do not match.');
  const benchmark = minutesBenchmark(standings);
  const teams = Object.values(meta.teams).sort((a, b) => a.name.localeCompare(b.name));
  view.innerHTML = `<section class="panel"><div class="row" style="justify-content:space-between;margin-bottom:10px"><div><h2 style="margin:0">Players</h2>
      <p class="note" style="margin:0">Season to date through ${esc(dayLabel(data.date))} (exclusive)</p></div></div>
    <div class="controls"><input type="search" id="pq" placeholder="Filter players" aria-label="Filter players" value="${esc(state.q)}">
      <select id="pt" aria-label="Team"><option value="">All teams</option>${teams.map(t => `<option value="${t.id}"${t.id === state.team ? ' selected' : ''}>${esc(t.name)}</option>`).join('')}</select>
      <select id="pg" aria-label="Minimum share of season minutes"><option value="0"${state.minMinutesShare === 0 ? ' selected' : ''}>All players with a game</option>${[10, 25, 50].map(n => `<option value="${n / 100}"${state.minMinutesShare === n / 100 ? ' selected' : ''}>${n}%+ minutes</option>`).join('')}</select>
      ${seg([['pg', 'Per game'], ['tot', 'Totals'], ['p36', 'Per 36']], state.mode, 'data-mode')}</div>
    <p class="note">${benchmark ? `Minutes share = season minutes ÷ ${benchmark.toLocaleString()} regulation minutes (48 × ${benchmark / 48} games, the most played by any team). League-wide benchmark, not roster eligibility; overtime and trades can put a player above 100%.` : 'Minutes-share filters are unavailable until a team has played a game.'}</p>
    <div id="ptable"></div></section>`;
  const paint = () => {
    const moversOpen = view.querySelector('#player-movers')?.open || false;
    const q = normalise(state.q);
    let rows = data.players.filter(p => qualifiesMinutes(p, state.minMinutesShare, benchmark) && (!state.team || p.team === state.team) && (!q || normalise(p.name).includes(q)));
    const {key, dir} = state.sort;
    rows = rows.map(p => ({p, v: value(p, key, state.mode)})).sort((a, b) => (a.v == null) - (b.v == null) || dir * ((a.v ?? 0) - (b.v ?? 0)) || a.p.name.localeCompare(b.p.name)).map(x => x.p);
    const shown = rows.slice(0, state.limit);
    const movers = data.players.filter(p => p.gp >= 8 && p.l10 && p.tot.min / p.gp >= 15).map(p => ({p, d: p.l10.pts - p.tot.pts / p.gp})).sort((a, b) => b.d - a.d);
    const mv = x => `<a class="mv" href="#/player/${x.p.id}">${logo(x.p.team, 'sm')}<span>${playerLabel(x.p.id, x.p.name)}</span><em class="${x.d > 0 ? 'up' : 'down'}">${x.d > 0 ? '+' : ''}${x.d.toFixed(1)}</em><small>${(x.p.tot.pts / x.p.gp).toFixed(1)} → ${x.p.l10.pts.toFixed(1)}</small></a>`;
    const moversHtml = movers.length > 10 ? `<details class="panel" id="player-movers"${moversOpen ? ' open' : ''}><summary><b>Heating up &amp; cooling off</b> · last 10 v season points</summary>
      <div class="movers"><div><span class="spot-kicker">Heating up</span>${movers.slice(0, 5).map(mv).join('')}</div>
      <div><span class="spot-kicker">Cooling off</span>${movers.slice(-5).reverse().map(mv).join('')}</div></div></details>` : '';
    view.querySelector('#ptable').innerHTML = `${moversHtml}<div class="scroll"><table><thead><tr><th>#</th><th class="name">Player</th><th class="l">Team</th>${COLS.map(([k, l]) => `<th data-sort="${k}" tabindex="0" aria-sort="${key === k ? (dir < 0 ? 'descending' : 'ascending') : 'none'}">${l}${key === k ? `<span class="arrow">${dir < 0 ? '▼' : '▲'}</span>` : ''}</th>`).join('')}</tr></thead><tbody>
      ${shown.map((p, i) => `<tr class="link" data-pid="${p.id}"><td class="dim">${i + 1}</td><td class="name">${playerLabel(p.id, p.name)} <span class="tag">${esc(p.pos || '')}</span>${statusTag(p.status)}</td><td class="l">${teamLink(p.team, {short: true})}</td>
        ${COLS.map(([k]) => `<td${k === 'trend' ? ' class="trend-c"' : ''}>${k === 'trend' ? sparkCell(p) : fmt(k, value(p, k, state.mode), state.mode)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>
      <div class="row" style="margin-top:10px"><span class="note" style="margin:0">${shown.length} of ${rows.length} players</span>${rows.length > shown.length ? '<button class="ghost" id="more">Show more</button>' : ''}</div>`;
    view.querySelectorAll('th[data-sort]').forEach(th => th.onclick = th.onkeydown = e => {
      if (e.type === 'keydown' && e.key !== 'Enter') return;
      const k = th.dataset.sort;
      state.sort = {key: k, dir: state.sort.key === k ? -state.sort.dir : (k === 'tov' ? 1 : -1)};
      paint();
    });
    view.querySelectorAll('tr[data-pid]').forEach(tr => tr.onclick = e => { if (!e.target.closest('a')) location.hash = '#/player/' + tr.dataset.pid; });
    const more = view.querySelector('#more');
    if (more) more.onclick = () => { state.limit += 60; paint(); };
  };
  view.querySelector('#pq').oninput = e => { state.q = e.target.value; state.limit = 60; paint(); };
  view.querySelector('#pt').onchange = e => { state.team = e.target.value; paint(); };
  view.querySelector('#pg').onchange = e => { state.minMinutesShare = Number(e.target.value); state.limit = 60; paint(); };
  view.querySelectorAll('[data-mode]').forEach(b => b.onclick = () => {
    state.mode = b.dataset.mode; store.set('players-mode', state.mode);
    view.querySelectorAll('[data-mode]').forEach(x => x.setAttribute('aria-pressed', x === b));
    paint();
  });
  paint();
}

async function playerPage(view, {rest, current}) {
  const pid = rest[0];
  const data = await api('player/' + encodeURIComponent(pid));
  if (!current()) return;
  const p = data.player, s = data.season, log = data.log;
  const played = log.filter(r => !r.dnp);
  const avg = (rows, k) => rows.length ? rows.reduce((a, r) => a + (r[k] || 0), 0) / rows.length : null;
  const tiles = s ? [['PTS', 'pts'], ['REB', 'reb'], ['AST', 'ast'], ['3PM', 'fg3m'], ['STL', 'stl'], ['BLK', 'blk'], ['MIN', 'min']]
    .map(([l, k]) => {  // U9: last 10 v season, coloured
      const sv = s.tot[k] / s.gp, l10 = avg(played.slice(-10), k), d = l10 == null ? null : l10 - sv;
      return `<div class="tile"><span>${l}</span><b>${f1(sv)}</b><small>L10 ${f1(l10)}${d == null ? '' : ` <em class="${d > 0.25 ? 'up' : d < -0.25 ? 'down' : 'dim'}">${d > 0 ? '+' : ''}${d.toFixed(1)}</em>`}</small></div>`;
    }).join('') : '';
  const shoot = s ? `FG ${pctOf(s.tot.fgm, s.tot.fga)} · 3P ${pctOf(s.tot.fg3m, s.tot.fg3a)} · FT ${pctOf(s.tot.ftm, s.tot.fta)} · TS ${s.tot.fga + 0.44 * s.tot.fta ? (100 * s.tot.pts / (2 * (s.tot.fga + 0.44 * s.tot.fta))).toFixed(1) + '%' : '—'}` : '';
  const next = data.next;
  let nextHtml = '';
  if (next) {
    const t = tipTimes(next.tip_utc, next.date);
    const pr = next.projection;
    nextHtml = `<section class="panel"><div class="row" style="justify-content:space-between"><div><h3 style="margin:0">Next game</h3>
      <p style="margin:4px 0 0">${esc(dayLabel(next.date))} · ${next.home ? 'vs' : '@'} ${teamLink(next.opp)} · ${esc(t.label)}</p></div>
      <a class="btn${pr ? '' : ' ghost'}" href="#/game/${next.game_id}${pr ? '/player/' + pid : ''}">${pr ? 'Open simulation' : 'Game page'}</a></div>
      ${pr ? `<div class="tiles" style="margin-top:10px">${[['PTS', 'pts'], ['REB', 'reb'], ['AST', 'ast'], ['3PM', 'fg3m'], ['PRA', 'pra'], ['MIN', 'min']].map(([l, k]) => `<div class="tile"><span>${l}</span><b>${f1(pr[k].mean)}</b><small>${pr[k].q[0]}–${pr[k].q[4]}</small></div>`).join('')}</div>
        <p class="note">Projected means with 10th–90th percentile ranges${pr.played < 0.999 ? ` · plays in ${pct(pr.played, 0)} of simulations` : ''}.</p>` : '<p class="note">Player projections appear on the morning of the game.</p>'}
      ${vsOpp(next)}</section>`;
  }
  const items = log.slice(-20).map(r => ({v: r.dnp ? null : r.pts, label: r.date.slice(8), title: `${r.date} ${r.home ? 'vs' : '@'} ${team(r.opp).abbr}: ${r.dnp ? (r.reason || 'DNP') : r.pts + ' pts'}`}));
  view.innerHTML = `<section class="panel"><div class="row">${playerFace(p.id, p.name, 'lg')}<div class="grow"><h2 style="margin:0;font-size:20px">${esc(p.name)}</h2>
      <p class="note" style="margin:0">${p.team ? `<a href="#/team/${p.team}">${esc(team(p.team).name)}</a> · ` : ''}${esc(p.pos || '')}${p.jersey ? ' · #' + esc(p.jersey) : ''}${p.age ? ' · age ' + p.age : ''}${p.height ? ' · ' + esc(p.height) : ''}${p.on_roster === false ? ' · not on a current roster' : ''} ${statusTag(p.status)}</p>
      ${p.injury?.comment ? `<p class="note status-q" style="margin:4px 0 0">${esc(p.injury.comment)}</p>` : ''}</div></div>
      ${s ? `<div class="tiles" style="margin-top:12px">${tiles}</div><p class="note">${s.gp} games (${s.gs} starts) · ${shoot} · per-game season averages; L10 = last 10 games played, with the change v the season</p>` : '<p class="note">No games played this season.</p>'}</section>
    ${nextHtml}
    ${advancedPanel(s?.tot, null, 'Season', {collapsible: true})}
    ${usageProfilePanel(data.usage_profile)}
    ${shotPanel(data.shots)}
    ${defencePanel(data.defence)}
    ${quartersPanel(data.quarters)}
    ${log.length ? `<section class="panel" id="trend">${trendPanel(log, s)}</section>
    <details class="panel" data-game-log><summary><b>Game log</b> · ${log.length} ${log.length === 1 ? 'entry' : 'entries'}</summary><div class="scroll"><table><thead><tr><th class="l">Date</th><th class="l">Opp</th><th>MIN</th><th>PTS</th><th>REB</th><th>AST</th><th>3PM</th><th>STL</th><th>BLK</th><th>TOV</th><th>FG</th><th>3P</th><th>FT</th><th>+/−</th></tr></thead><tbody>
      ${log.slice().reverse().map(r => `<tr class="link" data-gid="${r.game_id}"><td class="l">${esc(dayLabel(r.date))}</td><td class="l">${r.home ? 'vs' : '@'} ${esc(team(r.opp).abbr)}</td>
        ${r.dnp ? `<td class="l dim" colspan="12">${esc(r.reason || 'Did not play')}</td>` : `<td>${r.min}</td><td><b>${r.pts}</b></td><td>${r.reb}</td><td>${r.ast}</td><td>${r.fg3m}</td><td>${r.stl}</td><td>${r.blk}</td><td>${r.tov}</td><td>${r.fgm}-${r.fga}</td><td>${r.fg3m}-${r.fg3a}</td><td>${r.ftm}-${r.fta}</td><td>${signed(r.pm, 0)}</td>`}</tr>`).join('')}
      </tbody></table></div></details>` : ''}`;
  view.querySelectorAll('tr[data-gid]').forEach(tr => tr.onclick = () => { location.hash = '#/game/' + tr.dataset.gid; });
  const wire = () => view.querySelectorAll('[data-trend]').forEach(b => b.onclick = () => {
    trendStat = b.dataset.trend; store.set('trend-stat', trendStat); view.querySelector('#trend').innerHTML = trendPanel(log, s); wire(); });
  wire();
}

// U9: trend chart — game-by-game values (DNP = gap), 5-game rolling average and the season average, for a chosen stat
let trendStat = store.get('trend-stat', 'pts');
function trendPanel(log, s) {
  const stats = [['pts', 'PTS'], ['reb', 'REB'], ['ast', 'AST'], ['fg3m', '3PM'], ['min', 'MIN']];
  const k = stats.some(([x]) => x === trendStat) ? trendStat : 'pts';
  const rows = log.slice(-30);
  const vals = rows.map(r => (r.dnp ? null : Number(r[k]) || 0));
  const got = vals.filter(v => v != null);
  if (!got.length) return '<h3>Trend</h3><p class="note">No games played.</p>';
  const W = 640, H = 200, pl = 28, pr = 8, pt = 10, pb = 22, hi = Math.max(...got) * 1.1 || 1;
  const x = i => pl + (i + 0.5) * (W - pl - pr) / rows.length, y = v => pt + (hi - v) * (H - pt - pb) / hi;
  const roll = vals.map((_, i) => { const w = vals.slice(Math.max(0, i - 4), i + 1).filter(v => v != null); return w.length ? w.reduce((a, b) => a + b, 0) / w.length : null; });
  const path = (arr) => arr.map((v, i) => (v == null ? null : `${x(i).toFixed(1)},${y(v).toFixed(1)}`)).filter(Boolean).map((p, i) => (i ? 'L' : 'M') + p).join(' ');
  const season = s ? s.tot[k] / s.gp : null;
  const bars = vals.map((v, i) => v == null ? `<rect class="dnp" x="${(x(i) - 3).toFixed(1)}" y="${H - pb - 4}" width="6" height="4"><title>${rows[i].date}: ${esc(rows[i].reason || 'DNP')}</title></rect>`
    : `<rect class="bar" x="${(x(i) - 5).toFixed(1)}" y="${y(v).toFixed(1)}" width="10" height="${(H - pb - y(v)).toFixed(1)}"><title>${rows[i].date} ${rows[i].home ? 'vs' : '@'} ${team(rows[i].opp).abbr}: ${v}</title></rect>`).join('');
  const dates = rows.map((r, i) => (i % Math.ceil(rows.length / 8) === 0 ? `<text x="${x(i).toFixed(1)}" y="${H - 6}" text-anchor="middle">${r.date.slice(5)}</text>` : '')).join('');
  return `<div class="row" style="justify-content:space-between;align-items:center"><h3 style="margin:0">Trend · last ${rows.length} team games</h3>
    ${seg(stats, k, 'data-trend')}</div>
    <svg class="trend" viewBox="0 0 ${W} ${H}" role="img" aria-label="Trend">${bars}
      ${season != null ? `<line class="season" x1="${pl}" x2="${W - pr}" y1="${y(season).toFixed(1)}" y2="${y(season).toFixed(1)}"></line><text x="${pl + 4}" y="${(y(season) - 4).toFixed(1)}" text-anchor="start" class="lab">season ${f1(season)}</text>` : ''}
      <path class="roll" d="${path(roll)}"></path>${dates}<text x="${pl - 4}" y="${(y(hi / 1.1) + 3).toFixed(1)}" text-anchor="end">${Math.round(hi / 1.1)}</text></svg>
    <p class="note">Bars = each game · line = 5-game rolling average · dashed = season average · grey ticks = did not play.</p>`;
}
// U10: shot profile on a half court — zones as in the engine (rim ≤ 4 ft, paint, mid-range, corner 3, above-the-break 3),
// shaded by FG% v the league (green above, red below; ±8 points = full colour), labelled share of shots · FG%
function shotPanel(sh) {
  if (!sh) return '';
  const Z = Object.fromEntries(sh.zones.map(z => [z.zone, z]));
  const shade = z => { const d = Math.max(-1, Math.min(1, (z.fg - z.lg_fg) / 0.08)); return d >= 0 ? `rgba(80,170,110,${(0.15 + 0.55 * d).toFixed(2)})` : `rgba(210,90,80,${(0.15 + 0.55 * -d).toFixed(2)})`; };
  const lab = (z, x, y, a = 'middle') => `<text x="${x}" y="${y}" text-anchor="${a}"><tspan class="m">${Math.round(100 * Z[z].mix)}%</tspan><tspan x="${x}" dy="14">${(100 * Z[z].fg).toFixed(0)}% FG</tspan></text>`;
  const court = `<svg class="court" viewBox="0 0 500 360" role="img" aria-label="Shot profile by zone">
    <rect x="0" y="0" width="500" height="350" fill="${shade(Z.above3)}"></rect>
    <rect x="0" y="210" width="30" height="140" fill="${shade(Z.corner3)}"></rect><rect x="470" y="210" width="30" height="140" fill="${shade(Z.corner3)}"></rect>
    <path d="M30,350 L30,210 A237.5,237.5 0 0 1 470,210 L470,350 Z" fill="${shade(Z.mid)}"></path>
    <rect x="170" y="160" width="160" height="190" fill="${shade(Z.paint)}"></rect>
    <circle cx="250" cy="297.5" r="40" fill="${shade(Z.rim)}"></circle>
    <path class="lines" d="M30,350 L30,210 A237.5,237.5 0 0 1 470,210 L470,350 M170,350 L170,160 L330,160 L330,350 M0,350 L500,350"></path>
    <circle class="lines" cx="250" cy="297.5" r="7.5"></circle>
    ${lab('above3', 250, 50)}${lab('mid', 250, 125)}${lab('paint', 250, 205)}${lab('rim', 250, 292)}${lab('corner3', 4, 255, 'start')}${lab('corner3', 496, 255, 'end')}</svg>`;
  const rows = sh.zones.map(z => `<tr><td class="l">${{rim: 'Rim', paint: 'Paint', mid: 'Mid-range', corner3: 'Corner 3', above3: 'Above-break 3'}[z.zone]}</td><td>${Math.round(100 * z.mix)}%</td><td class="dim">${Math.round(100 * z.lg_mix)}%</td>
    <td><b>${(100 * z.fg).toFixed(1)}%</b></td><td class="dim">${(100 * z.lg_fg).toFixed(1)}%</td></tr>`).join('');
  return `<section class="panel"><h3 style="margin-top:0">Shot profile</h3><div class="shot-grid">${court}
    <div><div class="scroll"><table><thead><tr><th class="l">Zone</th><th>His shots</th><th>League</th><th>His FG%</th><th>League</th></tr></thead><tbody>${rows}</tbody></table></div>
    <p class="note">Assisted on ${Math.round(100 * sh.assisted)}% of his makes · FT ${(100 * sh.ft_pct).toFixed(1)}%.
    The pre-game profile the engine uses (decayed and shrunk toward his position group), through his last game (${esc(dayLabel(sh.as_of))}) — green zones beat the league's FG% there, red trail it.</p></div></div></section>`;
}
// U12: his history against the next opponent — averages v his overall, recent meetings, and their current players who
// guarded him most (real matchups)
function vsOpp(next) {
  const h = next?.history;
  if (!h) return '';
  const cell = (k, l) => { const d = h.avg[k] - h.overall[k]; return `<div class="tile"><span>${l}</span><b>${f1(h.avg[k])}</b><small>overall ${f1(h.overall[k])} <em class="${d > 0.5 ? 'up' : d < -0.5 ? 'down' : 'dim'}">${d > 0 ? '+' : ''}${d.toFixed(1)}</em></small></div>`; };
  const games = h.games.map(g => `<tr><td class="l">${esc(dayLabel(g.date))}</td><td>${g.min}</td><td><b>${g.pts}</b></td><td>${g.reb}</td><td>${g.ast}</td></tr>`).join('');
  const guards = h.guards.length ? `<p class="note" style="margin-top:6px">Guarded most by: ${h.guards.map(gd => `<a href="#/player/${gd.id}">${esc(gd.name)}</a> (${gd.pposs} poss, ${gd.pts} pts, ${gd.fgm}/${gd.fga})`).join(' · ')}</p>` : '';
  return `<details class="sub"><summary>History v ${esc(team(next.opp).name)} · ${h.n} game${h.n > 1 ? 's' : ''} since 2022-23</summary>
    <div class="tiles">${cell('pts', 'PTS')}${cell('reb', 'REB')}${cell('ast', 'AST')}${cell('min', 'MIN')}</div>
    <div class="scroll" style="margin-top:6px"><table><thead><tr><th class="l">Recent meetings</th><th>MIN</th><th>PTS</th><th>REB</th><th>AST</th></tr></thead><tbody>${games}</tbody></table></div>${guards}</details>`;
}

// U11: defensive profile from real NBA matchups — what his man does against him v what the same attackers do elsewhere
function defencePanel(d) {
  if (!d) return '';
  const dd = d.exp_100 != null ? d.pts_100 - d.exp_100 : null, d3 = d.exp_fg3a_share != null ? d.fg3a_share - d.exp_fg3a_share : null;
  const tile = (label, v, sub, good) => `<div class="tile"><span>${label}</span><b class="${good == null ? '' : good ? 'up' : 'down'}">${v}</b><small>${sub}</small></div>`;
  const tiles = [
    tile('Points allowed / 100 poss', f1(d.pts_100), d.exp_100 != null ? `those attackers elsewhere ${f1(d.exp_100)}` : '', dd == null ? null : dd < 0),
    tile('Edge v expected', dd == null ? '—' : `${dd > 0 ? '+' : ''}${dd.toFixed(1)}`, 'points per 100 (negative = stingy)', dd == null ? null : dd < 0),
    tile('Three-point share allowed', d.fg3a_share == null ? '—' : `${(100 * d.fg3a_share).toFixed(1)}%`, d.exp_fg3a_share != null ? `their normal ${(100 * d.exp_fg3a_share).toFixed(1)}%` : '', d3 == null ? null : d3 < 0),
    tile('FG% allowed', d.fg_allowed == null ? '—' : `${(100 * d.fg_allowed).toFixed(1)}%`, `${d.pposs.toLocaleString()} partial possessions`, null)].join('');
  const top = d.top.map(t => `<tr><td class="l"><a href="#/player/${t.id}">${esc(t.name)}</a></td><td>${t.pposs}</td><td>${t.pts}</td><td>${t.fgm}/${t.fga}</td></tr>`).join('');
  return `<section class="panel"><h3 style="margin-top:0">Defence · real matchups</h3><div class="tiles">${tiles}</div>
    <h4 class="sub-h">Whom he guards most</h4><div class="scroll"><table><thead><tr><th class="l">Attacker</th><th>Partial poss</th><th>His points</th><th>FG</th></tr></thead><tbody>${top}</tbody></table></div>
    <p class="note">NBA tracking matchups since ${esc(dayLabel(d.since))}. "Expected" = the same attackers' scoring rate against everyone else, weighted by how much he guarded each. A three-point share below their normal = he keeps shooters off the line (the most stable defensive trait we measured). Team scheme is in these numbers too.</p></section>`;
}
const pctOf = (m, a) => a ? (100 * m / a).toFixed(1) + '%' : '—';
const mmss = sec => { const t = Math.round(sec); return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, '0')}`; };
function quartersPanel(q) {
  if (!q || !q[0].games) return '';
  const g = q[0].games;
  const row = (label, idx) => {
    const sum = k => idx.reduce((s, i) => s + q[i][k], 0) / g;
    const fga = sum('fga');
    return `<tr><td class="l">${label}</td><td>${mmss(sum('sec'))}</td><td><b>${sum('pts').toFixed(1)}</b></td><td>${(sum('oreb') + sum('dreb')).toFixed(1)}</td><td>${sum('ast').toFixed(1)}</td><td>${sum('fg3m').toFixed(1)}</td><td>${sum('stl').toFixed(1)}</td><td>${sum('blk').toFixed(1)}</td><td>${sum('fgm').toFixed(1)}-${fga.toFixed(1)} <small class="dim">(${fga ? (100 * sum('fgm') / fga).toFixed(1) : '—'}%)</small></td></tr>`;
  };
  return `<section class="panel"><h3>By quarter · per game</h3><div class="scroll"><table><thead><tr><th class="l">Period</th><th>MIN</th><th>PTS</th><th>REB</th><th>AST</th><th>3PM</th><th>STL</th><th>BLK</th><th>FG</th></tr></thead><tbody>
    ${['Q1', 'Q2', 'Q3', 'Q4'].map((l, i) => row(l, [i])).join('')}${row('1st half', [0, 1])}${row('2nd half', [2, 3])}</tbody></table></div>
    <p class="note">From play-by-play over ${g} games; overtime excluded.</p></section>`;
}
