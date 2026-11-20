// Standings (season simulation), Teams directory and team pages.
import {api, dayLabel, esc, f1, heat, histogram, logo, pct, rate, record, seg, signed, statusTag, store, team, teamLink, tipTimes} from './ui.mjs';

const state = {conf: store.get('conf', 'East'), view: store.get('standings-view', 'forecast'), seedMode: 'exact', sort: null, teamTab: 'roster'};

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

async function standings(view, {meta, current}) {
  const data = await api('standings/' + meta.latest);
  if (!current()) return;
  const paint = () => {
    const confs = [['East', 'East'], ['West', 'West'], ['League', 'League']];
    const views = [['forecast', 'Forecast'], ['seeds', 'Seeds'], ['ratings', 'Ratings']];
    let rows = data.teams.filter(t => state.conf === 'League' || t.conf === state.conf);
    rows.sort((a, b) => (b.pct ?? 0) - (a.pct ?? 0) || (b.w - a.w) || (b.forecast.mean_w - a.forecast.mean_w) || a.abbr.localeCompare(b.abbr));
    let body;
    if (state.view === 'forecast') body = forecastTable(rows, state.conf === 'League');
    else if (state.view === 'seeds') body = state.conf === 'League' ? '<p class="note">Seeds are within a conference: choose East or West.</p>' : seedsTable(rows);
    else body = ratingsTable(rows);
    view.innerHTML = `<section class="panel"><div class="row" style="justify-content:space-between;margin-bottom:10px">
        <div><h2 style="margin:0">Standings &amp; season forecast</h2><p class="note" style="margin:0">Through ${esc(dayLabel(data.date))} · ${data.sims.toLocaleString()} simulated seasons of every unplayed fixture</p></div>
        ${seasonPill(data.season_model)}</div>
      <div class="controls">${seg(confs, state.conf, 'data-conf')}${seg(views, state.view, 'data-view')}
        ${state.view === 'seeds' && state.conf !== 'League' ? seg([['exact', 'Exactly'], ['atleast', 'At least']], state.seedMode, 'data-seed') : ''}</div>
      ${body}
      <details style="margin-top:12px"><summary class="note" style="cursor:pointer">How the forecast works</summary>
        <p class="note">${data.season_model && data.season_model.kind === 'team-pathway'
          ? "Today's and tomorrow's games come from the possession engine: each simulated season takes one of its simulated games. Every later game is played in date order with that season's own offensive and defensive rating for each team (pace and home court included), and after every game both teams' ratings move by how much they beat or missed that season's expectation — so a March game is played with ratings each season's own path produced, not today's."
          : 'Each unplayed game gets a home-win chance from shrunk team ratings (offence, defence, pace, home court); tonight\'s games use their full game simulation, including injuries.'} One simulated season settles every fixture once; standings come from ${data.sims.toLocaleString()} seasons. Top 6 = direct playoff seed; play-in = seeds 7–10. ${data.notes.map(esc).join(' ')}</p></details></section>`;
    view.querySelectorAll('[data-conf]').forEach(b => b.onclick = () => { state.conf = b.dataset.conf; store.set('conf', state.conf); paint(); });
    view.querySelectorAll('[data-view]').forEach(b => b.onclick = () => { state.view = b.dataset.view; store.set('standings-view', state.view); paint(); });
    view.querySelectorAll('[data-seed]').forEach(b => b.onclick = () => { state.seedMode = b.dataset.seed; paint(); });
    view.querySelectorAll('tr[data-team]').forEach(tr => tr.onclick = e => { if (!e.target.closest('a')) location.hash = '#/team/' + tr.dataset.team; });
  };
  paint();
}

function forecastTable(rows, league) {
  const head = `<tr><th>#</th><th class="name">Team</th><th>W</th><th>L</th><th class="opt">GB</th><th class="opt">L10</th><th class="opt">Strk</th><th class="opt">Net</th><th>Proj W–L</th>
    ${league ? '<th>Best record</th><th>Worst record</th>' : '<th>Top 6</th><th>Play-in</th><th>Out</th><th>#1 seed</th>'}</tr>`;
  const body = rows.map((t, i) => {
    const f = t.forecast, zone = !league && (i === 5 || i === 9) ? ' class="zone link"' : ' class="link"';
    return `<tr${zone} data-team="${t.id}"><td class="dim">${i + 1}</td><td class="name">${teamLink(t.id)}</td><td>${t.w}</td><td>${t.l}</td>
      <td class="dim opt">${t.gb ? f1(t.gb).replace('.0', '') : '—'}</td><td class="dim opt">${record(t.last10)}</td><td class="dim opt">${esc(t.streak || '')}</td>
      <td class="opt ${t.net >= 0 ? 'up' : 'down'}">${signed(t.net)}</td><td><b>${f1(f.mean_w)}</b>–${f1(f.mean_l)}</td>
      ${league ? `${heat(f.best_record)}${heat(f.worst_record)}` : `${heat(f.top6)}${heat(f.playin)}${heat(f.out)}${heat(f.first)}`}</tr>`;
  }).join('');
  return `<div class="scroll"><table><thead>${head}</thead><tbody>${body}</tbody></table></div>
    <p class="note">Proj W–L covers ${rows[0]?.forecast.scheduled ?? '—'} scheduled games per team; the two NBA Cup-determined games join once scheduled. Lines mark seeds 6 and 10.</p>`;
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
