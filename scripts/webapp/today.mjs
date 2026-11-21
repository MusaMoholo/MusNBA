// Today: the slate for one ET game date, each game a card that opens Game Centre.
import {modelPill, api, esc, etToday, f1, logo, longDay, pct, record, stamp, team, tipTimes, dayLabel} from './ui.mjs';
import {slateSpotlight} from './spotlight.mjs';

// Card surname with its suffix ("Michael Porter Jr." → "Porter Jr."): the last word that is not a suffix, then the suffixes.
const SUFFIX = /^(jr\.?|sr\.?|ii|iii|iv|v)$/i;
const surname = name => {
  const w = String(name || '').split(' ').filter(Boolean), tail = [];
  while (w.length > 1 && SUFFIX.test(w[w.length - 1])) tail.unshift(w.pop());
  return [w[w.length - 1] || '', ...tail].join(' ');
};

export function defaultDay(meta) {
  const day = etToday();
  if (day < meta.first_date) return meta.first_date;
  if (day > meta.last_date) return meta.last_date;
  return day;
}

function neighbour(meta, day, direction) {
  const dates = Object.keys(meta.dates).filter(d => meta.dates[d] > 0).sort();
  if (direction < 0) return dates.filter(d => d < day).at(-1) || null;
  return dates.find(d => d > day) || null;
}

export async function render(view, {rest, meta, current}) {
  const day = /^\d{4}-\d{2}-\d{2}$/.test(rest[0] || '') ? rest[0] : defaultDay(meta);
  let slate;
  try {
    slate = await api('slate/' + day);
  } catch (error) {
    if (error.status !== 404) throw error;
    slate = {date: day, games: [], snapshot: null};
  }
  if (!current()) return;
  const prev = neighbour(meta, day, -1), next = neighbour(meta, day, 1), todayEt = defaultDay(meta);
  const games = slate.games;
  const firstTip = games.find(g => g.time_valid);
  view.innerHTML = `
    <section class="panel daybar">
      <div>
        <h2>${esc(longDay(day))}${day === etToday() ? ' <span class="pill accent">Today</span>' : ''}</h2>
        <p class="note">${games.length ? `${games.length} game${games.length > 1 ? 's' : ''}${firstTip ? ` · first tip ${esc(tipTimes(firstTip.tip_utc, day).label)}` : ''}` : 'No games scheduled'}</p>
      </div>
      <div class="daynav">
        <button class="ghost" data-go="${prev || ''}" ${prev ? '' : 'disabled'} aria-label="Previous game day">‹</button>
        <input type="date" aria-label="Choose date" value="${day}" min="${meta.first_date}" max="${meta.last_date}">
        <button class="ghost" data-go="${next || ''}" ${next ? '' : 'disabled'} aria-label="Next game day">›</button>
        ${day !== todayEt ? `<button class="ghost" data-go="${todayEt}">Today</button>` : ''}
      </div>
    </section>
    ${modelNote(slate)}
    ${slate.spotlight ? `<div class="games spot-grid">${slateSpotlight(slate.spotlight, slate.watch)}</div>` : ''}
    <div class="games">${games.map(card).join('')}</div>`;
  view.querySelectorAll('[data-go]').forEach(b => b.onclick = () => { if (b.dataset.go) location.hash = '#/today/' + b.dataset.go; });
  view.querySelector('input[type=date]').onchange = e => { if (e.target.value) location.hash = '#/today/' + e.target.value; };
}

function modelNote(slate) {
  if (slate.snapshot) {
    const kind = slate.kind === 'prospective' ? '<span class="pill good">Pre-game snapshot</span>' : '<span class="pill warn" title="Rebuilt after the fact from box scores before this date; no injury news">Retrospective</span>';
    return `<div class="model-note">${modelPill(slate.model)}${kind}<span>${slate.model.sims.toLocaleString()} sims per game · built ${esc(stamp(slate.generated))}</span></div>`;
  }
  if (slate.games.some(g => g.team_model)) return '<div class="model-note"><span class="pill">Team-strength estimate only</span><span>Game sims run on the morning of each slate.</span></div>';
  if (slate.games.length) return '<div class="model-note"><span class="pill">No projection retained for this date</span></div>';
  return '';
}

function card(g) {
  const final = g.status === 'final', live = g.status === 'live';
  const pr = g.proj, tm = g.team_model;
  const pA = pr ? pr.p_away : tm ? 1 - tm.p_home : null, pH = pr ? pr.p_home : tm ? tm.p_home : null;
  const t = tipTimes(g.tip_utc, g.date, g.time_valid);
  const scored = (final || live) && g.away.score != null;
  const winner = final ? (g.home.score > g.away.score ? 'home' : 'away') : null;
  const side = (key, p, proj) => {
    const s = g[key], info = team(s.id);
    const cls = winner ? (winner === key ? 'won' : 'lost') : '';
    const pts = scored ? s.score : proj != null ? f1(proj) : '';
    return `<div class="side ${cls}">${logo(s.id)}<span class="nm">${esc(info.short)}<small>${record(s.record)}</small></span><span class="p">${p != null ? pct(p, 0) : ''}</span><span class="pts${scored ? '' : ' proj'}">${pts}</span></div>`;
  };
  const muA = pr ? pr.mu_away : tm?.mu_away, muH = pr ? pr.mu_home : tm?.mu_home;
  let foot;
  if (final) {
    const fav = pr ? (pr.p_home >= pr.p_away ? 'home' : 'away') : null;
    foot = `<span>Final${g.periods > 4 ? (g.periods > 5 ? `/${g.periods - 4}OT` : '/OT') : ''}</span>` +
      (pr ? `<span>Pre-game: ${esc(team(g[fav].id).abbr)} ${pct(Math.max(pr.p_home, pr.p_away), 0)} ${fav === winner ? '<span class="up" title="Favourite won">✓</span>' : '<span class="down" title="Underdog won">✗</span>'}</span><span>Proj total ${f1(pr.total)} · actual ${g.home.score + g.away.score}</span>` : '<span>No pre-game projection retained</span>');
  } else if (pr) {
    const m = pr.margin_mean ?? pr.margin_median, fav = m >= 0 ? g.home : g.away;
    foot = `<span>Total ${f1(pr.total)}</span><span>${Math.abs(m) < 0.05 ? 'PK' : `${esc(team(fav.id).abbr)} −${Math.abs(m).toFixed(1)}`}</span><span>OT ${pct(pr.ot, 0)}</span>`;
  } else if (tm) foot = '<span>Team-strength estimate</span>';
  else foot = '<span>No projection</span>';
  const right = live ? `<span class="pill bad">${esc(g.detail)}</span>` : final ? '' : esc(g.tv[0] || '');
  return `<a class="game-card" href="#/game/${g.id}" aria-label="${esc(team(g.away.id).name)} at ${esc(team(g.home.id).name)}">
    <div class="when"><span>${esc(t.label)}</span><span>${right}</span></div>
    ${side('away', pA, muA)}${side('home', pH, muH)}
    ${pA != null ? `<div class="winbar" aria-hidden="true"><i class="a" style="width:${(100 * pA).toFixed(1)}%"></i><i class="h" style="width:${(100 * pH).toFixed(1)}%"></i></div>` : ''}
    ${pr?.leaders && !final ? `<div class="leaders">${['away', 'home'].map(k => (pr.leaders[k] || []).map(l => `<span><b>${esc(surname(l.name))}</b> ${f1(l.pts)} pts · ${f1(l.reb)} reb · ${f1(l.ast)} ast</span>`).join('')).join('')}</div>` : ''}
    ${pr?.duel && !final ? (() => { const last = k => esc(surname(pr.leaders[k][0].name)); return `<div class="duel-line" title="Chance each top scorer outscores the other, over the engine's simulated games">Duel: <b>${last('away')}</b> outscores ${pct(pr.duel.p_a, 0)} · <b>${last('home')}</b> ${pct(pr.duel.p_b, 0)} · level ${pct(pr.duel.p_level, 0)}</div>`; })() : ''}
    <div class="foot">${foot}</div></a>`;
}

export {dayLabel};
