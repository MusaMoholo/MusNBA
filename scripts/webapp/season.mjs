// Season insights from retained season counts and cutoff-safe season statistics.
import {playerFace, playerLabel, api, dayLabel, esc, f1, heat, pct, seg, signed, standingsNav, store, team, teamLink} from './ui.mjs';
const state = {conf: store.get('season-conf', 'East')};
export async function render(view, {meta, current, rest}) {
  const tab = ['races', 'movers', 'leaders'].includes(rest?.[0]) ? rest[0] : 'races';
  const data = await api('standings/' + meta.latest);
  const moves = tab === 'movers' ? await api('season_movers') : null;
  const leadersData = tab === 'leaders' ? await api('players') : null;
  if (!current()) return;
  const paint = () => {
    view.innerHTML = `<section class="panel"><h2>Standings &amp; season forecast</h2><p class="note">As of ${esc(dayLabel(data.season_model?.as_of || data.date))} · ${data.sims.toLocaleString()} simulated seasons · only scheduled fixtures included</p>
      <div class="controls" style="margin-top:12px">${standingsNav(tab)}</div></section>
      ${tab === 'leaders' ? leaders(leadersData, data) : tab === 'movers' ? movers(moves) : `<section class="panel"><h2>Season races</h2><div class="controls">${seg([['East', 'East'], ['West', 'West'], ['League', 'League']], state.conf, 'data-season-conf')}</div>
      ${raceChart(data.teams.filter(t => state.conf === 'League' || t.conf === state.conf))}</section>
      <div class="season-grid">${['East', 'West'].map(conf => probabilityRace(data.teams.filter(t => t.conf === conf), 'first', conf + ' · #1 seed')).join('')}</div>
      ${probabilityRace(data.teams, 'worst_record', 'The bottom of the standings', true)}
      <p class="note">Ranges are the 10th–90th percentiles of final wins. Top 6 means a direct playoff place. <a href="#/about">Read the current forecast assumptions</a>. <a href="#/standings/picture">Open the playoff picture →</a></p>`}`;
    view.querySelectorAll('[data-view]').forEach(b => b.onclick = () => location.replace('#/standings/' + b.dataset.view));
    view.querySelectorAll('[data-season-conf]').forEach(b => b.onclick = () => { state.conf = b.dataset.seasonConf; store.set('season-conf', state.conf); paint(); });
  };
  paint();
}
function raceChart(rows) {
  const sorted = rows.slice().sort((a, b) => b.forecast.mean_w - a.forecast.mean_w);
  const maxWins = Math.max(1, ...rows.map(t => t.forecast.scheduled));
  return `<div class="race-axis"><span>Final wins</span><div class="race-scale">${[0, .25, .5, .75, 1].map(f => Math.round(f * maxWins)).map(v => `<span style="left:${v / maxWins * 100}%">${v}</span>`).join('')}</div><span></span></div><div class="race-list">${sorted.map(t => {
    const w = t.forecast.wins, q = w.q;
    return `<div class="race-row">${teamLink(t.id, {short: true})}<div class="race-track" role="img" aria-label="${esc(t.name)}: average ${f1(w.mean)} wins, 10–90 percent ${q[0]} to ${q[4]}"><i class="race-band" style="left:${q[0] / maxWins * 100}%;width:${(q[4] - q[0]) / maxWins * 100}%"></i><i class="race-iqr" style="left:${q[1] / maxWins * 100}%;width:${(q[3] - q[1]) / maxWins * 100}%"></i><i class="race-mean" style="left:${w.mean / maxWins * 100}%"></i></div><span><b>${f1(w.mean)}</b> <small>${q[0]}–${q[4]}</small></span></div>`;
  }).join('')}</div><p class="note">Dot = average · thick band = middle 50% · thin band = middle 80% · common 0–${maxWins} win scale (scheduled games).</p>`;
}
function probabilityRace(rows, key, title, bottom = false) {
  const sorted = rows.slice().sort((a, b) => b.forecast[key] - a.forecast[key]);
  return `<section class="panel"><h2>${esc(title)}</h2><div class="scroll"><table><thead><tr><th class="name">Team</th><th>Proj W</th><th>${bottom ? 'Worst record' : '#1 seed'}</th>${bottom ? '<th>Bottom 3</th>' : '<th>Top 6</th>'}</tr></thead><tbody>${sorted.slice(0, bottom ? 10 : 6).map(t => `<tr><td class="name">${teamLink(t.id)}</td><td>${f1(t.forecast.mean_w)}</td>${heat(t.forecast[key])}${heat(bottom ? t.forecast.bottom3 : t.forecast.top6)}</tr>`).join('')}</tbody></table></div>
    ${bottom ? '<p class="note">League record ranks, before any draft lottery. Bottom 3 counts exactly three teams per simulated season using the same random tiebreak as the best/worst-record race; older snapshots without these counts show —.</p>' : ''}</section>`;
}

function movers(data) {
  if (!data?.from || !data.teams.length) return '<section class="panel"><h2>Movers</h2><p class="note">A previous season forecast with an earlier cutoff and the same model is needed. Tomorrow’s copy of today’s forecast is not a second observation.</p></section>';
  const changed = data.teams.slice().sort((a, b) => b.delta.mean_w - a.delta.mean_w);
  const card = (rows, title) => `<section class="panel"><h2>${title}</h2>${rows.slice(0, 5).map(t => `<div class="mover-card">${teamLink(t.id)}<b class="${t.delta.mean_w >= 0 ? 'up' : 'down'}">${signed(t.delta.mean_w)} wins</b></div>`).join('')}</section>`;
  return `<section class="panel"><h2>Since the previous forecast</h2><p class="note">${esc(dayLabel(data.from))} → ${esc(dayLabel(data.to))} · same season model · ${data.results.length} results in this interval${data.from_kind === 'retrospective' ? ' · previous forecast is retrospective' : ''}. Changes include results, updated inputs and simulation variation; no individual result is assigned a causal contribution.</p></section>
    <div class="season-grid">${card(changed, 'Biggest risers')}${card(changed.slice().reverse(), 'Biggest fallers')}</div>
    <section class="panel"><h2>Every team · forecast changes</h2><div class="scroll"><table><thead><tr><th class="name">Team</th><th>Previous W</th><th>Now W</th><th>Δ W</th><th>Δ Top 6</th><th>Δ Play-in</th><th>Δ #1</th></tr></thead><tbody>${changed.map(t => `<tr><td class="name">${teamLink(t.id)}</td><td>${f1(t.before.mean_w)}</td><td>${f1(t.now.mean_w)}</td><td class="${t.delta.mean_w >= 0 ? 'up' : 'down'}">${signed(t.delta.mean_w)}</td>${['top6', 'playin', 'first'].map(k => `<td class="${t.delta[k] >= 0 ? 'up' : 'down'}">${signed(100 * t.delta[k])} pp</td>`).join('')}</tr>`).join('')}</tbody></table></div><p class="note">Top 6 = direct playoff place; Play-in = regular-season seeds 7–10. Probability changes are percentage points.</p></section>
    <section class="panel"><h2>Results between forecasts</h2>${data.results.length ? `<div class="result-list">${data.results.map(g => `<a href="#/game/${g.id}"><small>${esc(dayLabel(g.date))}</small><span>${esc(team(g.away).abbr)} <b>${g.away_pts}–${g.home_pts}</b> ${esc(team(g.home).abbr)}</span></a>`).join('')}</div>` : '<p class="note">No new results between these cutoffs; any movement comes from inputs or simulated paths.</p>'}</section>`;
}

function leaders(players, standings) {
  const teamGP = Math.max(0, ...standings.teams.map(t => t.gp || t.w + t.l));
  const gamesShare = .7;
  const minGP = Math.max(1, Math.ceil(teamGP * gamesShare));
  const eligible = players.players.filter(p => p.gp >= minGP);
  const cats = [['pts', 'Points'], ['reb', 'Rebounds'], ['ast', 'Assists'], ['fg3m', 'Threes made'], ['stl', 'Steals'], ['blk', 'Blocks'], ['fg_pct', 'Field-goal percentage'], ['fg3_pct', 'Three-point percentage'], ['ft_pct', 'Free-throw percentage']];
  const shooting = {fg_pct: ['fgm', 'fga', 5], fg3_pct: ['fg3m', 'fg3a', 3], ft_pct: ['ftm', 'fta', 2]};
  const value = (p, key) => shooting[key] ? p.tot[shooting[key][0]] / p.tot[shooting[key][1]] : p.tot[key] / p.gp;
  const cards = cats.map(([key, label]) => {
    const rows = eligible.filter(p => !shooting[key] || p.tot[shooting[key][1]] / p.gp >= shooting[key][2]).slice().sort((a, b) => value(b, key) - value(a, key) || b.gp - a.gp || a.id.localeCompare(b.id)).slice(0, 5);
    return `<section class="panel"><h2>${label}</h2>${rows.length ? `<ol class="leader-list">${rows.map(p => `<li><a href="#/player/${p.id}"><span>${playerLabel(p.id, p.name)}<small>${esc(team(p.team).abbr)} · ${p.gp} GP</small></span><b>${shooting[key] ? pct(value(p, key)) : f1(value(p, key))}</b></a></li>`).join('')}</ol>` : '<p class="note">No qualifying players yet.</p>'}${shooting[key] ? `<p class="note">At least ${shooting[key][2]} ${shooting[key][1].toUpperCase()} per game.</p>` : ''}</section>`;
  }).join('');
  const teamCats = [['ortg', 'Offensive rating', -1], ['drtg', 'Defensive rating', 1], ['net', 'Net rating', -1], ['pace', 'Pace', -1], ['scoring', 'Points per game', -1], ['rebounding', 'Rebounds per game', -1]];
  const teamValue = (t, k) => k === 'scoring' ? t.per_game?.pts : k === 'rebounding' ? t.per_game?.reb : t[k];
  return `<section class="panel"><h2>Season leaders · to date</h2><p class="note">Games before ${esc(dayLabel(players.date))} · per game · minimum ${minGP} games (${pct(gamesShare, 0)} of the most games played by any team, rounded up). Shooting minimums per game: FG% ${shooting.fg_pct[2]} FGA, 3P% ${shooting.fg3_pct[2]} attempts, FT% ${shooting.ft_pct[2]} attempts. These are dashboard filters, not official NBA leaderboard qualifications.</p></section>
    <div class="leaders-grid">${cards}</div><section class="panel"><h2>Team leaders</h2><p class="note">Ratings are per 100 estimated possessions; pace is possessions per 48 minutes. Points and rebounds are per game. Lower is better for defensive rating.</p></section><div class="leaders-grid">${teamCats.map(([key, label, dir]) => `<section class="panel"><h2>${label}</h2><ol class="leader-list">${standings.teams.filter(t => teamValue(t, key) != null).slice().sort((a, b) => dir * (teamValue(a, key) - teamValue(b, key))).slice(0, 5).map(t => `<li><div>${teamLink(t.id)}<b>${f1(teamValue(t, key))}</b></div></li>`).join('')}</ol></section>`).join('')}</div>`;
}
