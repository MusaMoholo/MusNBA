// Standings (season simulation), Teams directory and team pages.
import {api, dayLabel, esc, f1, heat, histogram, logo, pct, rate, record, seg, signed, statusTag, store, team, teamLink, tipTimes} from './ui.mjs';

const state = {conf: store.get('conf', 'East'), view: store.get('standings-view', 'forecast'), seedMode: 'exact', sort: null, teamTab: 'roster',
               winsMode: store.get('wins-mode', 'exact'), fWinsN: Number(store.get('f-wins-n', 41)) || 41, fWinsMode: store.get('f-wins-mode', 'atleast'),
               fSeedN: Number(store.get('f-seed-n', 6)) || 6, fSeedMode: store.get('f-seed-mode', 'atleast')};

export async function render(view, ctx) {
  if (ctx.name === 'standings') return standings(view, ctx);
  if (ctx.name === 'teams') return directory(view, ctx);
  return teamPage(view, ctx);
}

// ------------------------------------------------------------------ standings
function seasonPill(m) {  // which model made the season forecast (D25/D26: the team pathway; else the placeholder's)
  return m && m.kind === 'team-pathway'
    ? `<span class="pill good" title="${esc(m.label)}">Team pathway ${esc((m.id || '').replace('team-pathway-', ''))}</span>`
    : `<span class="pill accent" title="${esc(m ? m.label : '')}">Placeholder model</span>`;
}

async function standings(view, {meta, current, rest}) {
  if (['forecast', 'seeds', 'wins', 'ratings'].includes(rest?.[0])) state.view = rest[0];  // #/standings/<tab> (linkable)
  const data = await api('standings/' + meta.latest);
  if (!current()) return;
  const paint = () => {
    const confs = [['East', 'East'], ['West', 'West'], ['League', 'League']];
    const views = [['forecast', 'Forecast'], ['seeds', 'Seeds'], ['wins', 'Wins'], ['ratings', 'Ratings']];
    let rows = data.teams.filter(t => state.conf === 'League' || t.conf === state.conf);
    rows.sort((a, b) => (b.pct ?? 0) - (a.pct ?? 0) || (b.w - a.w) || (b.forecast.mean_w - a.forecast.mean_w) || a.abbr.localeCompare(b.abbr));
    let body;
    if (state.view === 'forecast') body = forecastTable(rows, state.conf === 'League');
    else if (state.view === 'wins') body = winsTable(rows);
    else if (state.view === 'seeds') body = state.conf === 'League' ? '<p class="note">Seeds are within a conference: choose East or West.</p>' : seedsTable(rows);
    else body = ratingsTable(rows);
    view.innerHTML = `<section class="panel"><div class="row" style="justify-content:space-between;margin-bottom:10px">
        <div><h2 style="margin:0">Standings &amp; season forecast</h2><p class="note" style="margin:0">Through ${esc(dayLabel(data.date))} · ${data.sims.toLocaleString()} simulated seasons of every unplayed fixture</p></div>
        ${seasonPill(data.season_model)}</div>
      <div class="controls">${seg(confs, state.conf, 'data-conf')}${seg(views, state.view, 'data-view')}
        ${state.view === 'seeds' && state.conf !== 'League' ? seg([['exact', 'Exactly'], ['atleast', 'At least']], state.seedMode, 'data-seed') : ''}
        ${state.view === 'wins' ? seg([['exact', 'Exactly'], ['atleast', 'At least']], state.winsMode, 'data-wmode') : ''}</div>
      ${state.view === 'forecast' ? `<div class="seg-groups">
        <div class="seg-group"><span class="seg-label">Final wins</span><div class="wins-pick">${seg([['atleast', 'At least'], ['exact', 'Exactly']], state.fWinsMode, 'data-fwmode')}
          <label class="sr" for="fwins-n">Wins</label><input id="fwins-n" type="number" min="0" max="82" step="1" value="${state.fWinsN}" data-fwins></div></div>
        ${state.conf !== 'League' ? `<div class="seg-group"><span class="seg-label">Seed</span><div class="wins-pick">${seg([['atleast', 'Or better'], ['exact', 'Exactly']], state.fSeedMode, 'data-fsmode')}
          <label class="sr" for="fseed-n">Seed</label><input id="fseed-n" type="number" min="1" max="15" step="1" value="${state.fSeedN}" data-fseed></div></div>` : ''}</div>` : ''}
      ${body}
      <details style="margin-top:12px"><summary class="note" style="cursor:pointer">How the forecast works</summary>
        <p class="note">${data.season_model && data.season_model.kind === 'team-pathway'
          ? "Today's and tomorrow's games come from the possession engine: each simulated season takes one of its simulated games. Every later game is played in date order with that season's own offensive and defensive rating for each team (pace and home court included), and after every game both teams' ratings move by how much they beat or missed that season's expectation — so a March game is played with ratings each season's own path produced, not today's."
          : 'Each unplayed game gets a home-win chance from shrunk team ratings (offence, defence, pace, home court); tonight\'s games use their full game simulation, including injuries.'} One simulated season settles every fixture once; standings come from ${data.sims.toLocaleString()} seasons. Top 6 = direct playoff seed; play-in = seeds 7–10. ${data.notes.map(esc).join(' ')}</p></details></section>`;
    view.querySelectorAll('[data-conf]').forEach(b => b.onclick = () => { state.conf = b.dataset.conf; store.set('conf', state.conf); paint(); });
    view.querySelectorAll('[data-view]').forEach(b => b.onclick = () => { state.view = b.dataset.view; store.set('standings-view', state.view); location.replace('#/standings/' + state.view); });
    view.querySelectorAll('[data-seed]').forEach(b => b.onclick = () => { state.seedMode = b.dataset.seed; paint(); });
    view.querySelectorAll('[data-wmode]').forEach(b => b.onclick = () => { state.winsMode = b.dataset.wmode; store.set('wins-mode', state.winsMode); paint(); });
    view.querySelectorAll('[data-fwmode]').forEach(b => b.onclick = () => { state.fWinsMode = b.dataset.fwmode; store.set('f-wins-mode', state.fWinsMode); paint(); });
    view.querySelectorAll('th[data-fsort]').forEach(th => th.onclick = th.onkeydown = e => {
      if (e.type === 'keydown' && e.key !== 'Enter') return;
      const k = th.dataset.fsort, def = ['l', 'gb', 'pl', 'out', 'worst'].includes(k) ? 1 : -1;
      state.fSort = state.fSort?.key === k ? (state.fSort.dir === def ? {key: k, dir: -def} : null) : {key: k, dir: def};  // third click: standings order
      paint();
    });
    view.querySelectorAll('[data-fsmode]').forEach(b => b.onclick = () => { state.fSeedMode = b.dataset.fsmode; store.set('f-seed-mode', state.fSeedMode); paint(); });
    const num = (sel, lo, hi, key, prop) => view.querySelector(sel)?.addEventListener('change', e => {
      state[prop] = Math.max(lo, Math.min(hi, Math.round(Number(e.target.value) || lo))); store.set(key, state[prop]); paint(); });
    num('[data-fwins]', 0, 82, 'f-wins-n', 'fWinsN');
    num('[data-fseed]', 1, 15, 'f-seed-n', 'fSeedN');
    view.querySelectorAll('tr[data-team]').forEach(tr => tr.onclick = e => { if (!e.target.closest('a')) location.hash = '#/team/' + tr.dataset.team; });
  };
  paint();
}

/** Share of simulated seasons with final wins in [lo, hi] (inclusive) from {min, hist} counts. */
function winsShare(w, lo, hi) {
  if (!w?.hist) return null;
  const tot = w.hist.reduce((a, b) => a + b, 0);
  let n = 0;
  w.hist.forEach((c, i) => { const v = i + (w.min || 0); if (v >= lo && v <= hi) n += c; });
  return tot ? n / tot : null;
}

// Wins tab (owner, 20 Nov): the Seeds format for final wins — columns in steps of 5 from high to low; Exactly = that
// 5-win band (top band open-ended, bottom band everything below), At least = that many wins or more.
function winsTable(rows) {
  const ordered = rows.slice().sort((a, b) => b.forecast.mean_w - a.forecast.mean_w || a.abbr.localeCompare(b.abbr));
  const qs = ordered.map(t => t.forecast.wins?.q || [0, 0, 0, 0, 0]);
  const top = Math.min(80, Math.max(45, Math.ceil(Math.max(...qs.map(q => q[4])) / 5) * 5));
  const bottom = Math.max(10, Math.min(35, Math.floor(Math.min(...qs.map(q => q[0])) / 5) * 5));
  const cuts = [];
  for (let k = top; k >= bottom; k -= 5) cuts.push(k);
  const exact = state.winsMode !== 'atleast';
  const label = (k, i) => (exact ? (i === 0 ? `${k}+` : i === cuts.length - 1 ? `≤${k + 4}` : `${k}–${k + 4}`) : `${k}+`);
  const head = `<tr><th class="name">Team</th><th>Avg</th>${cuts.map((k, i) => `<th class="c">${label(k, i)}</th>`).join('')}</tr>`;
  const body = ordered.map(t => {
    const w = t.forecast.wins;
    const cells = cuts.map((k, i) => {
      const p = exact ? (i === 0 ? winsShare(w, k, 999) : i === cuts.length - 1 ? winsShare(w, -1, k + 4) : winsShare(w, k, k + 4)) : winsShare(w, k, 999);
      return heat(p);
    }).join('');
    return `<tr class="link" data-team="${t.id}"><td class="name">${teamLink(t.id)}</td><td class="dim">${f1(t.forecast.mean_w)}</td>${cells}</tr>`;
  }).join('');
  return `<div class="scroll"><table><thead>${head}</thead><tbody>${body}</tbody></table></div>
    <p class="note">${exact ? 'Chance the final win total lands in each 5-win band.' : 'Chance of at least that many wins.'} Final wins over the ${ordered[0]?.forecast.scheduled ?? '—'} scheduled games, from the ${'10,000'} simulated seasons; ordered by average wins.</p>`;
}

// Forecast table (owner, 20 Nov): current (W, L, W%, GB, L10, Strk, Net) and projected groups split by a dotted line;
// Proj W and Proj L separate; every numeric column sortable (click again to reverse); seed lines only in standings order.
function forecastTable(rows, league) {
  const wN = state.fWinsN, wEx = state.fWinsMode === 'exact', sN = state.fSeedN, sEx = state.fSeedMode === 'exact';
  const strk = t => { const m = String(t.streak || '').match(/^([WL])(\d+)/); return m ? (m[1] === 'W' ? 1 : -1) * Number(m[2]) : 0; };
  const winsCol = t => (wEx ? winsShare(t.forecast.wins, wN, wN) : winsShare(t.forecast.wins, wN, 999));
  const seedCol = t => (sEx ? t.forecast.seeds?.[sN - 1] : Math.min(1, (t.forecast.seeds || []).slice(0, sN).reduce((a, b) => a + b, 0)));
  // key, header, value, default direction (−1: high first), cell, classes
  const cols = [
    ['w', 'W', t => t.w, -1, t => t.w, ''], ['l', 'L', t => t.l, 1, t => t.l, ''],
    ['pct', 'W%', t => t.pct, -1, t => (t.pct == null ? '—' : t.pct.toFixed(3).replace(/^0/, '')), ''],
    ['gb', 'GB', t => t.gb ?? 0, 1, t => (t.gb ? f1(t.gb).replace('.0', '') : '—'), 'dim opt'],
    ['l10', 'L10', t => t.last10?.[0] ?? 0, -1, t => record(t.last10), 'dim opt'],
    ['strk', 'Strk', strk, -1, t => esc(t.streak || ''), 'dim opt'],
    ['net', 'Net', t => t.net, -1, t => `<span class="${t.net >= 0 ? 'up' : 'down'}">${signed(t.net)}</span>`, 'opt'],
    ['pw', 'Proj W', t => t.forecast.mean_w, -1, t => `<b>${f1(t.forecast.mean_w)}</b>`, 'grp'],
    ['pl', 'Proj L', t => t.forecast.mean_l, 1, t => f1(t.forecast.mean_l), ''],
    ['wins', `${wEx ? '=' : '≥'} ${wN} W`, winsCol, -1, null, ''],
    ...(league ? [] : [['seed', `${sEx ? 'Seed' : 'Seed ≤'} ${sN}`, seedCol, -1, null, '']]),
    ...(league ? [['best', 'Best record', t => t.forecast.best_record, -1, null, ''], ['worst', 'Worst record', t => t.forecast.worst_record, -1, null, '']]
               : [['top6', 'Top 6', t => t.forecast.top6, -1, null, ''], ['playin', 'Play-in', t => t.forecast.playin, -1, null, ''],
                  ['out', 'Out', t => t.forecast.out, -1, null, ''], ['first', '#1 seed', t => t.forecast.first, -1, null, '']]),
  ];
  const rank = new Map(rows.map((t, i) => [t.id, i + 1]));
  const sort = state.fSort && cols.find(c => c[0] === state.fSort.key) ? state.fSort : null;
  const sorted = sort ? rows.slice().sort((a, b) => { const c = cols.find(x => x[0] === sort.key)[2]; return sort.dir * ((c(a) ?? -1) - (c(b) ?? -1)) || rank.get(a.id) - rank.get(b.id); }) : rows;
  const th = ([k, label, , , , cls]) => `<th data-fsort="${k}" tabindex="0" class="${cls}" aria-sort="${sort?.key === k ? (sort.dir < 0 ? 'descending' : 'ascending') : 'none'}">${esc(label)}${sort?.key === k ? `<span class="arrow">${sort.dir < 0 ? '▼' : '▲'}</span>` : ''}</th>`;
  const head = `<tr><th>#</th><th class="name">Team</th>${cols.map(th).join('')}</tr>`;
  const body = sorted.map((t, i) => {
    const zone = !sort && !league && (i === 5 || i === 9) ? ' class="zone link"' : ' class="link"';
    return `<tr${zone} data-team="${t.id}"><td class="dim">${rank.get(t.id)}</td><td class="name">${teamLink(t.id)}</td>${cols.map(([, , v, , cell, cls]) =>
      cell ? `<td class="${cls}">${cell(t)}</td>` : heat(v(t), {digits: v === winsCol && wEx ? 1 : 0})).join('')}</tr>`;
  }).join('');
  return `<div class="scroll"><table class="forecast"><thead>${head}</thead><tbody>${body}</tbody></table></div>
    <p class="note">Current record left of the dotted line, the simulated season right of it. Proj W and Proj L cover ${rows[0]?.forecast.scheduled ?? '—'} scheduled games per team; the two NBA Cup-determined games join once scheduled. Tap a header to sort (again to reverse); # is the standing${sort ? '' : '; lines mark seeds 6 and 10'}.</p>`;
}

function seedsTable(rows) {
  const ordered = rows.slice().sort((a, b) => a.forecast.seed_mean - b.forecast.seed_mean || a.abbr.localeCompare(b.abbr));
  const n = 15;
  const head = `<tr><th class="name">Team</th><th>Avg</th>${Array.from({length: n}, (_, k) => `<th class="c">${state.seedMode === 'atleast' ? '≤' : ''}${k + 1}</th>`).join('')}</tr>`;
  const body = ordered.map(t => {
    const s = t.forecast.seeds;
    let cum = 0;
    const cells = s.map(p => { cum += p; return heat(state.seedMode === 'atleast' ? Math.min(1, cum) : p); }).join('');
    return `<tr class="link" data-team="${t.id}"><td class="name">${teamLink(t.id)}</td><td class="dim">${f1(t.forecast.seed_mean)}</td>${cells}</tr>`;
  }).join('');
  return `<div class="scroll"><table><thead>${head}</thead><tbody>${body}</tbody></table></div>
    <p class="note">${state.seedMode === 'atleast' ? 'Chance of finishing that seed or better.' : 'Chance of finishing exactly that seed.'} Ordered by average seed. Ties are broken at random until NBA tiebreakers are implemented.</p>`;
}

function ratingsTable(rows) {
  const keys = [['ortg', 'ORtg', f1], ['drtg', 'DRtg', f1], ['net', 'Net', signed], ['pace', 'Pace', f1], ['efg', 'eFG%', rate], ['opp_efg', 'Opp eFG%', rate],
                ['tov_pct', 'TOV%', rate], ['oreb_pct', 'OREB%', rate], ['ftr', 'FT rate', rate], ['fg3a_rate', '3PA rate', rate], ['fg3_pct', '3P%', rate]];
  const sorted = state.sort ? rows.slice().sort((a, b) => (state.sort.dir) * ((a[state.sort.key] ?? 0) - (b[state.sort.key] ?? 0))) : rows;
  return `<div class="scroll"><table><thead><tr><th class="name">Team</th><th>W–L</th>${keys.map(([k, l]) => `<th>${l}</th>`).join('')}</tr></thead><tbody>
    ${sorted.map(t => `<tr class="link" data-team="${t.id}"><td class="name">${teamLink(t.id)}</td><td>${t.w}-${t.l}</td>${keys.map(([k, , fmt]) => `<td>${fmt(t[k])}${t.ranks?.[k] ? ` <span class="tag">${t.ranks[k]}</span>` : ''}</td>`).join('')}</tr>`).join('')}
    </tbody></table></div><p class="note">Per 100 possessions; possessions estimated as FGA − OREB + TOV + 0.44 × FTA. Small numbers are league ranks.</p>`;
}

// ------------------------------------------------------------------ directory
async function directory(view, {meta, current}) {
  const data = await api('standings/' + meta.latest);
  if (!current()) return;
  const byId = new Map(data.teams.map(t => [t.id, t]));
  const divisions = {East: ['Atlantic', 'Central', 'Southeast'], West: ['Northwest', 'Pacific', 'Southwest']};
  view.innerHTML = `<div class="confs">${Object.entries(divisions).map(([conf, divs]) => `<section class="panel"><h2>${conf}ern Conference</h2>
    <div class="divs">${divs.map(div => `<div><h3>${div}</h3><ul>${data.teams.filter(t => t.div === div).sort((a, b) => b.w - a.w || a.l - b.l).map(t =>
      `<li><a href="#/team/${t.id}">${logo(t.id)}<span>${esc(t.short)}</span><small>${t.w}-${t.l}</small></a></li>`).join('')}</ul></div>`).join('')}</div></section>`).join('')}</div>`;
  void byId;
}

// ------------------------------------------------------------------ team page
// U14: form and fixtures — margin by game (W/L bars, 5-game rolling line) and the next ten games (home/away, the season
// simulation's win chance, back-to-backs), from the team view's schedule
function formPanel(data) {
  const sch = data.schedule || [];
  const done = sch.filter(g => g.status === 'final' && g.pts != null);
  const next = sch.filter(g => g.status !== 'final').slice(0, 10);
  let chart = '';
  if (done.length) {
    const m = done.map(g => g.pts - g.opp_pts), W = 640, H = 170, pl = 28, pr = 8, pt = 8, pb = 20;
    const hi = Math.max(10, ...m.map(Math.abs)) * 1.1, x = i => pl + (i + 0.5) * (W - pl - pr) / m.length, y = v => pt + (hi - v) * (H - pt - pb) / (2 * hi);
    const roll = m.map((_, i) => { const w = m.slice(Math.max(0, i - 4), i + 1); return w.reduce((a, b) => a + b, 0) / w.length; });
    const bars = m.map((v, i) => `<rect class="${v > 0 ? 'w' : 'l'}" x="${(x(i) - 6).toFixed(1)}" y="${Math.min(y(v), y(0)).toFixed(1)}" width="12" height="${Math.abs(y(v) - y(0)).toFixed(1)}"><title>${done[i].date} ${done[i].home ? 'vs' : '@'} ${team(done[i].opp).abbr}: ${done[i].pts}–${done[i].opp_pts}</title></rect>`).join('');
    const line = roll.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
    chart = `<div><h4>Margin by game</h4><svg class="trend" viewBox="0 0 ${W} ${H}" role="img" aria-label="Margin by game">
      <line class="season" x1="${pl}" x2="${W - pr}" y1="${y(0).toFixed(1)}" y2="${y(0).toFixed(1)}"></line>${bars}<path class="roll" d="${line}"></path>
      <text x="${pl - 4}" y="${(y(hi / 1.1) + 3).toFixed(1)}" text-anchor="end">+${Math.round(hi / 1.1)}</text><text x="${pl - 4}" y="${(y(-hi / 1.1) + 3).toFixed(1)}" text-anchor="end">−${Math.round(hi / 1.1)}</text></svg>
      <p class="note">Bars = final margin (green wins, red losses) · line = 5-game rolling average.</p></div>`;
  }
  const dates = sch.map(g => g.date);
  const b2b = g => { const d = new Date(g.date + 'T12:00:00Z'); const prev = new Date(d - 864e5).toISOString().slice(0, 10); return dates.includes(prev); };
  const fx = next.length ? `<div><h4>Coming up</h4><div class="fx">${next.map(g => `<a class="fx-g" href="#/game/${g.game_id}">
      <span class="fx-d">${esc(dayLabel(g.date))}${b2b(g) ? ' <span class="pill warn" title="Second night of a back-to-back">B2B</span>' : ''}</span>
      <span class="fx-o">${g.home ? 'vs' : '@'} ${logo(g.opp, 'sm')} ${esc(team(g.opp).abbr)}</span>${g.p_win != null ? heatSpan(g.p_win) : '<span class="dim">—</span>'}</a>`).join('')}</div>
      <p class="note">Win chance from the game simulation for today/tomorrow, else the season simulation's team estimate.</p></div>` : '';
  return chart || fx ? `<section class="panel"><div class="form-grid">${chart}${fx}</div></section>` : '';
}
const heatSpan = p => `<span class="fx-p" style="--a:${Math.abs(p - 0.5) * 2}" data-side="${p >= 0.5 ? 'w' : 'l'}">${pct(p, 0)}</span>`;

async function teamPage(view, {rest, current}) {
  const tid = rest[0];
  const data = await api('team/' + encodeURIComponent(tid));
  if (!current()) return;
  const t = data.team, s = data.stats, f = data.forecast;
  const paint = () => {
    const tiles = [['ORtg', f1(s.ortg), s.ranks?.ortg], ['DRtg', f1(s.drtg), s.ranks?.drtg], ['Net', signed(s.net), s.ranks?.net], ['Pace', f1(s.pace), s.ranks?.pace]]
      .map(([l, v, r]) => `<div class="tile"><span>${l}</span><b>${v}</b>${r ? `<small>${ordinal(r)}</small>` : ''}</div>`).join('');
    view.innerHTML = `<section class="panel"><div class="row">${logo(t.id, 'lg')}<div class="grow"><h2 style="margin:0;font-size:20px">${esc(t.name)}</h2>
      <p class="note" style="margin:0">${record(data.record)} · ${esc(t.conf)} · ${esc(t.div)} · home ${record(s.home)} · away ${record(s.away)} · last 10 ${record(s.last10)} ${esc(s.streak || '')}</p></div></div>
      <div class="tiles" style="margin-top:12px">${tiles}
        <div class="tile"><span>Proj W–L</span><b>${f1(f.mean_w)}</b><small>–${f1(f.mean_l)}</small></div>
        <div class="tile"><span>Top 6</span><b>${pct(f.top6, 0)}</b></div><div class="tile"><span>Play-in</span><b>${pct(f.playin, 0)}</b></div>
        <div class="tile"><span>#1 seed</span><b>${pct(f.first, 0)}</b></div></div>
      <div style="margin-top:12px"><h3>Simulated final wins (of ${f.scheduled} scheduled)</h3>${histogram(f.wins, {height: 120})}</div></section>
      ${formPanel(data)}
      <div class="controls">${seg([['roster', 'Roster'], ['schedule', 'Schedule']], state.teamTab, 'data-tt')}</div>
      ${state.teamTab === 'roster' ? roster(data) : schedule(data)}`;
    view.querySelectorAll('[data-tt]').forEach(b => b.onclick = () => { state.teamTab = b.dataset.tt; paint(); });
    view.querySelectorAll('tr[data-pid]').forEach(tr => tr.onclick = () => { location.hash = '#/player/' + tr.dataset.pid; });
    view.querySelectorAll('tr[data-gid]').forEach(tr => tr.onclick = () => { location.hash = '#/game/' + tr.dataset.gid; });
  };
  paint();
}

function roster(data) {
  const pg = (p, k) => p.gp ? (p.tot[k] / p.gp).toFixed(1) : '—';
  const pctOf = (m, a) => a ? (100 * m / a).toFixed(1) : '—';
  return `<section class="panel"><div class="scroll"><table><thead><tr><th class="name">Player</th><th>Pos</th><th>GP</th><th>GS</th><th>MIN</th><th>PTS</th><th>REB</th><th>AST</th><th>3PM</th><th>STL</th><th>BLK</th><th>TOV</th><th>FG%</th><th>3P%</th><th>FT%</th></tr></thead><tbody>
    ${data.roster.map(p => `<tr class="link" data-pid="${p.id}"><td class="name">${esc(p.name)}${p.jersey ? ` <span class="tag">#${esc(p.jersey)}</span>` : ''}${statusTag(p.status)}</td><td class="c dim">${esc(p.pos || '')}</td>
      <td>${p.gp}</td><td>${p.gs}</td><td>${pg(p, 'min')}</td><td><b>${pg(p, 'pts')}</b></td><td>${pg(p, 'reb')}</td><td>${pg(p, 'ast')}</td><td>${pg(p, 'fg3m')}</td><td>${pg(p, 'stl')}</td><td>${pg(p, 'blk')}</td><td>${pg(p, 'tov')}</td>
      <td>${pctOf(p.tot.fgm, p.tot.fga)}</td><td>${pctOf(p.tot.fg3m, p.tot.fg3a)}</td><td>${pctOf(p.tot.ftm, p.tot.fta)}</td></tr>`).join('')}
    </tbody></table></div><p class="note">Current roster with season per-game averages (all teams this season). Injury status from the latest report.</p></section>`;
}

function schedule(data) {
  const rows = data.schedule.map(g => {
    const t = tipTimes(g.tip_utc, g.date);
    const result = g.status === 'final' ? `<b class="${g.pts > g.opp_pts ? 'up' : 'down'}">${g.pts > g.opp_pts ? 'W' : 'L'}</b> ${g.pts}–${g.opp_pts}` : g.status === 'postponed' ? 'Postponed' : esc(t.uk);
    return `<tr class="link" data-gid="${g.game_id}"><td class="l">${esc(dayLabel(g.date))}</td><td class="l">${g.home ? 'vs' : '@'} ${teamLink(g.opp)}</td><td class="l">${result}</td>${g.status === 'final' ? '<td></td>' : heat(g.p_win, {title: g.p_source === 'game' ? 'Game simulation' : 'Team-strength estimate'})}</tr>`;
  }).join('');
  return `<section class="panel"><div class="scroll"><table><thead><tr><th class="l">Date</th><th class="l">Opponent</th><th class="l">Result / tip (UK)</th><th>Win</th></tr></thead><tbody>${rows}</tbody></table></div>
    <p class="note">Win chances for future games come from the season simulation's team-strength estimate; tonight's games use the full game simulation.</p></section>`;
}

const ordinal = n => n + ({1: 'st', 2: 'nd', 3: 'rd'}[n % 100 > 10 && n % 100 < 14 ? 0 : n % 10] || 'th');
