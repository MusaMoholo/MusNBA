// Season insights from retained season counts and cutoff-safe season statistics.
import {api, dayLabel, esc, f1, heat, pct, seg, store, teamLink} from './ui.mjs';
const state = {conf: store.get('season-conf', 'East')};
export async function render(view, {meta, current, rest}) {
  const data = await api('standings/' + meta.latest);
  if (!current()) return;
  const paint = () => {
    view.innerHTML = `<section class="panel"><h2>Season · the races</h2><p class="note">As of ${esc(dayLabel(data.season_model?.as_of || data.date))} · ${data.sims.toLocaleString()} simulated seasons · only scheduled fixtures included</p>
      <div class="controls" style="margin-top:12px">${seg([['East', 'East'], ['West', 'West'], ['League', 'League']], state.conf, 'data-season-conf')}</div>
      ${raceChart(data.teams.filter(t => state.conf === 'League' || t.conf === state.conf))}</section>
      <div class="season-grid">${['East', 'West'].map(conf => probabilityRace(data.teams.filter(t => t.conf === conf), 'first', conf + ' · #1 seed')).join('')}</div>
      ${probabilityRace(data.teams, 'worst_record', 'The bottom of the standings', true)}
      <p class="note">Ranges are the 10th–90th percentiles of final wins. Top 6 means a direct playoff place; play-in and playoff rounds are not yet simulated. Ties are broken at random. <a href="#/standings/picture">Open the playoff picture →</a></p>`;
    view.querySelectorAll('[data-season-conf]').forEach(b => b.onclick = () => { state.conf = b.dataset.seasonConf; store.set('season-conf', state.conf); paint(); });
  };
  paint();
}
function raceChart(rows) {
  const sorted = rows.slice().sort((a, b) => b.forecast.mean_w - a.forecast.mean_w);
  return `<div class="race-axis"><span>Final wins</span><span>0</span><span>20</span><span>40</span><span>60</span><span>82</span></div><div class="race-list">${sorted.map(t => {
    const w = t.forecast.wins, q = w.q;
    return `<div class="race-row">${teamLink(t.id, {short: true})}<div class="race-track" role="img" aria-label="${esc(t.name)}: average ${f1(w.mean)} wins, 10–90 percent ${q[0]} to ${q[4]}"><i class="race-band" style="left:${q[0] / 82 * 100}%;width:${(q[4] - q[0]) / 82 * 100}%"></i><i class="race-iqr" style="left:${q[1] / 82 * 100}%;width:${(q[3] - q[1]) / 82 * 100}%"></i><i class="race-mean" style="left:${w.mean / 82 * 100}%"></i></div><span><b>${f1(w.mean)}</b> <small>${q[0]}–${q[4]}</small></span></div>`;
  }).join('')}</div><p class="note">Dot = average · thick band = middle 50% · thin band = middle 80% · common 0–82 win scale.</p>`;
}
function probabilityRace(rows, key, title, bottom = false) {
  const sorted = rows.slice().sort((a, b) => b.forecast[key] - a.forecast[key]);
  return `<section class="panel"><h2>${esc(title)}</h2><div class="scroll"><table><thead><tr><th class="name">Team</th><th>Proj W</th><th>${bottom ? 'Worst record' : '#1 seed'}</th>${bottom ? '<th>Bottom 3</th>' : '<th>Top 6</th>'}</tr></thead><tbody>${sorted.slice(0, bottom ? 10 : 6).map(t => `<tr><td class="name">${teamLink(t.id)}</td><td>${f1(t.forecast.mean_w)}</td>${heat(t.forecast[key])}${heat(bottom ? t.forecast.bottom3 : t.forecast.top6)}</tr>`).join('')}</tbody></table></div>
    ${bottom ? '<p class="note">League record ranks, before any draft lottery. Bottom 3 counts exactly three teams per simulated season using the same random tiebreak as the best/worst-record race; older snapshots without these counts show —.</p>' : ''}</section>`;
}
